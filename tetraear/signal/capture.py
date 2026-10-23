"""
RTL-SDR signal capture module for TETRA decoding.
"""

import os
import sys
from pathlib import Path

# Add bundled DLL search paths (Windows).
if sys.platform == "win32":
    try:
        tetraear_root = Path(__file__).resolve().parents[1]
        dll_dir = tetraear_root / "bin"

        for dll_path in (dll_dir, tetraear_root):
            if not dll_path.exists():
                continue
            dll_path_str = str(dll_path)
            if dll_path_str not in os.environ.get("PATH", ""):
                os.environ["PATH"] = dll_path_str + os.pathsep + os.environ.get("PATH", "")
            if hasattr(os, "add_dll_directory"):
                os.add_dll_directory(dll_path_str)
    except (OSError, AttributeError):
        pass  # Fallback if methods fail

import numpy as np
import logging
import warnings

# Lazy import of RtlSdr to avoid DLL loading issues during import.
# setuptools>=82 no longer ships pkg_resources; pyrtlsdr still imports it at
# package load for version lookup only — stub it so RtlSdr remains usable.
def _ensure_pkg_resources_stub():
    try:
        import pkg_resources  # noqa: F401
        return
    except ImportError:
        pass
    import types
    stub = types.ModuleType("pkg_resources")

    def _require(*_args, **_kwargs):
        raise Exception("pkg_resources stub")

    stub.require = _require  # type: ignore[attr-defined]
    sys.modules["pkg_resources"] = stub


try:
    _ensure_pkg_resources_stub()
    with warnings.catch_warnings():
        warnings.filterwarnings(
            "ignore",
            message=r"pkg_resources is deprecated as an API\..*",
            category=UserWarning,
        )
        from rtlsdr import RtlSdr
    RTL_SDR_AVAILABLE = True
except (ImportError, OSError) as e:
    logging.getLogger(__name__).debug("RTL-SDR import failed: %s", e)
    RTL_SDR_AVAILABLE = False
    RtlSdr = None  # type: ignore

logger = logging.getLogger(__name__)


class RTLCapture:
    """Handles RTL-SDR device configuration and signal capture."""
    
    def __init__(self, frequency=400e6, sample_rate=1.8e6, gain='auto', device=None):
        """
        Initialize RTL-SDR capture.
        
        Args:
            frequency: Center frequency in Hz
            sample_rate: Sample rate in Hz
            gain: Gain setting ('auto' or numeric value)
            device: Device selector — int (index), str (serial), or None (first available)
        """
        self.frequency = frequency
        self.sample_rate = sample_rate
        self.gain = gain
        self.device = device
        self.sdr = None

    @staticmethod
    def list_devices():
        """
        List attached RTL-SDR devices.

        Returns:
            list[dict]: Each entry has ``index`` (int) and ``serial`` (str).
            Empty list if the library is unavailable or no devices are found.
        """
        if not RTL_SDR_AVAILABLE or RtlSdr is None:
            return []
        try:
            from ctypes import c_ubyte
            from rtlsdr.librtlsdr import librtlsdr

            num_devices = int(librtlsdr.rtlsdr_get_device_count())
            devices = []
            for i in range(num_devices):
                serial = ""
                try:
                    bfr = (c_ubyte * 256)()
                    r = librtlsdr.rtlsdr_get_device_usb_strings(i, None, None, bfr)
                    if r == 0:
                        serial = "".join(chr(b) for b in bfr if b > 0).strip()
                except Exception as e:
                    logger.debug("Could not read serial for RTL-SDR #%s: %s", i, e)
                if not serial:
                    try:
                        name = librtlsdr.rtlsdr_get_device_name(i)
                        if name:
                            serial = name.decode("utf-8", errors="replace")
                    except Exception:
                        pass
                devices.append({"index": i, "serial": serial})
            return devices
        except Exception as e:
            logger.error(f"Failed to list RTL-SDR devices: {e}")
            # Fallback: pyrtlsdr helper (fails entirely if any device errors)
            try:
                serials = RtlSdr.get_device_serial_addresses()
                return [
                    {"index": i, "serial": (serial or "").strip()}
                    for i, serial in enumerate(serials)
                ]
            except Exception as e2:
                logger.error(f"RTL-SDR device listing fallback failed: {e2}")
                return []

    def _open_sdr(self):
        """Open the RtlSdr handle for the configured device selector."""
        if self.device is None:
            return RtlSdr()
        if isinstance(self.device, int):
            return RtlSdr(device_index=self.device)
        if isinstance(self.device, str):
            serial = self.device.strip()
            if not serial:
                return RtlSdr()
            return RtlSdr(serial_number=serial)
        raise TypeError(f"Unsupported device selector type: {type(self.device)!r}")
        
    def open(self):
        """
        Open and configure RTL-SDR device.
        
        Returns:
            bool: True if device opened successfully, False otherwise
        
        Raises:
            RuntimeError: If RTL-SDR library is not available
        """
        if not RTL_SDR_AVAILABLE:
            logger.error("RTL-SDR library not available")
            return False
        
        try:
            self.sdr = self._open_sdr()
            
            # Validate and round sample rate to nearest valid RTL-SDR rate
            # Valid rates: 0.225, 0.9, 1.024, 1.536, 1.8, 1.92, 2.048, 2.4, 2.56, 2.88, 3.2 MHz
            valid_rates = [0.225e6, 0.9e6, 1.024e6, 1.536e6, 1.8e6, 1.92e6, 2.048e6, 2.4e6, 2.56e6, 2.88e6, 3.2e6]
            closest_rate = min(valid_rates, key=lambda x: abs(x - self.sample_rate))
            if abs(closest_rate - self.sample_rate) > 0.1e6:  # More than 100kHz difference
                logger.warning(f"Sample rate {self.sample_rate/1e6:.3f} MHz is not valid for RTL-SDR, using {closest_rate/1e6:.3f} MHz")
            self.sample_rate = closest_rate
            self.sdr.sample_rate = self.sample_rate
            self.sdr.center_freq = self.frequency
            # Handle gain: 'auto' stays as string, numeric values should be numeric
            if isinstance(self.gain, str) and self.gain.lower() == 'auto':
                self.sdr.gain = 'auto'
            elif isinstance(self.gain, str) and self.gain.isdigit():
                # Convert string numeric value to float/int
                self.sdr.gain = float(self.gain)
            else:
                self.sdr.gain = self.gain
            try:
                self.sdr.set_bias_tee(False)
            except AttributeError:
                # Older librtlsdr.dll doesn't have this function
                pass
            
            if self.device is None:
                device_desc = "default (first available)"
            else:
                device_desc = f"{self.device!r}"
            logger.info(f"RTL-SDR opened (device={device_desc})")
            
            logger.info(f"Frequency: {self.frequency/1e6:.2f} MHz")
            logger.info(f"Sample rate: {self.sample_rate/1e6:.2f} MHz")
            logger.info(f"Gain: {self.gain}")
            
            return True
        except Exception as e:
            error_msg = str(e)
            if self.device is not None:
                logger.error(f"Failed to open RTL-SDR device {self.device!r}: {e}")
            else:
                logger.error(f"Failed to open RTL-SDR: {e}")
            
            # Provide helpful error messages
            if "LIBUSB_ERROR_ACCESS" in error_msg or "Access denied" in error_msg:
                logger.error("")
                logger.error("=" * 60)
                logger.error("USB DRIVER ISSUE DETECTED")
                logger.error("=" * 60)
                logger.error("Your RTL-SDR device needs WinUSB driver installed.")
                logger.error("")
                logger.error("SOLUTION:")
                logger.error("1. Download Zadig: https://zadig.akeo.ie/")
                logger.error("2. Run Zadig as Administrator")
                logger.error("3. Options -> List All Devices")
                logger.error("4. Select your RTL-SDR device")
                logger.error("5. Select 'WinUSB' driver")
                logger.error("6. Click 'Install Driver' or 'Replace Driver'")
                logger.error("7. Unplug and replug your RTL-SDR")
                logger.error("8. Try again")
                logger.error("")
                logger.error("See FIX_USB_DRIVER.md for detailed instructions")
                logger.error("=" * 60)
            
            return False
    
    def read_samples(self, num_samples=1024*1024):
        """
        Read samples from RTL-SDR.
        
        Args:
            num_samples: Number of samples to read
            
        Returns:
            Complex numpy array of samples
        """
        if self.sdr is None:
            raise RuntimeError("RTL-SDR device not opened")
        
        try:
            samples = self.sdr.read_samples(num_samples)
            return samples
        except (OSError, RuntimeError) as e:
            error_msg = str(e)
            # Check for access violation or device errors
            if "access violation" in error_msg.lower() or "exception" in error_msg.lower():
                logger.error(f"RTL-SDR device error: {e}")
                logger.error("Device may be in invalid state. Attempting to recover...")
                # Try to close and reopen
                try:
                    self.sdr.close()
                except:
                    pass
                self.sdr = None
                raise RuntimeError("RTL-SDR device error - please restart the application")
            logger.error(f"Failed to read samples: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to read samples: {e}")
            raise
    
    def set_frequency(self, frequency: float):
        """
        Change center frequency.
        
        Args:
            frequency: New center frequency in Hz
        """
        if self.sdr is None:
            raise RuntimeError("RTL-SDR device not opened")
        
        try:
            self.frequency = frequency
            self.sdr.center_freq = frequency
            logger.debug(f"Frequency changed to {frequency/1e6:.3f} MHz")
        except Exception as e:
            logger.error(f"Failed to set frequency: {e}")
            raise
    
    def close(self):
        """Close RTL-SDR device."""
        if self.sdr is not None:
            self.sdr.close()
            self.sdr = None
            logger.info("RTL-SDR device closed")
    
    def __enter__(self):
        """Context manager entry."""
        self.open()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
