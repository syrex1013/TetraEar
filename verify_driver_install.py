#!/usr/bin/env python3
"""
Verify RTL-SDR WinUSB Driver Installation
Run this after installing the driver with Zadig
"""

import os
import sys
import subprocess
import platform

def run_command(cmd, description=""):
    """Run a command and return the result."""
    print(f"\n{'='*50}")
    print(f"Running: {description}")
    print(f"Command: {cmd}")
    print('='*50)

    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
        print("STDOUT:")
        print(result.stdout)
        if result.stderr:
            print("STDERR:")
            print(result.stderr)
        print(f"Exit code: {result.returncode}")
        return result.returncode == 0, result.stdout, result.stderr
    except Exception as e:
        print(f"Error: {e}")
        return False, "", str(e)

def check_device_manager():
    """Check if RTL-SDR appears under libusb devices."""
    print("\nChecking Device Manager for libusb devices...")

    if platform.system() == 'Windows':
        # Check for libusb devices
        success, stdout, stderr = run_command(
            'powershell "Get-PnpDevice | Where-Object {$_.Name -like \'*libusb*\' -or $_.InstanceId -like \'*VID_0BDA*\'} | Format-Table -Property Name, Status, InstanceId"',
            "Check for libusb devices in Device Manager"
        )

        if success and stdout.strip():
            print("[SUCCESS] Found libusb devices!")
            print("Driver installation appears successful.")
            return True
        else:
            print("[FAILED] No libusb devices found.")
            print("The WinUSB driver may not be properly installed.")
            return False
    return False

def test_rtl_access():
    """Test if RTL-SDR can be accessed."""
    print("\nTesting RTL-SDR access...")

    try:
        # Add DLL directory to PATH
        dll_dir = os.path.dirname(os.path.abspath(__file__))
        if dll_dir not in os.environ.get('PATH', ''):
            os.environ['PATH'] = dll_dir + os.pathsep + os.environ.get('PATH', '')

        from rtlsdr import RtlSdr
        print("[OK] rtlsdr library imported")

        sdr = RtlSdr()
        print("[OK] RtlSdr object created")

        devices = sdr.get_device_serial_addresses()
        print(f"[OK] Found {len(devices)} device(s)")

        # Try to set parameters and read samples
        sdr.sample_rate = 1.8e6
        sdr.center_freq = 392.5e6
        sdr.gain = 'auto'
        print("[OK] Device parameters set")

        samples = sdr.read_samples(1024)
        print(f"[SUCCESS] Successfully read {len(samples)} samples!")
        print("RTL-SDR driver installation is working correctly!")

        sdr.close()
        return True

    except Exception as e:
        error_msg = str(e)
        print(f"[FAILED] RTL-SDR access failed: {e}")

        if "LIBUSB_ERROR_ACCESS" in error_msg or "Access denied" in error_msg:
            print("\nDriver installation incomplete.")
            print("The RTL-SDR device is not using the WinUSB driver.")
            print("Please reinstall the driver using Zadig.")
        elif "LIBUSB_ERROR_NOT_FOUND" in error_msg:
            print("\nNo RTL-SDR device found.")
            print("Make sure the device is plugged in.")

        return False

def main():
    print("=" * 60)
    print("RTL-SDR WinUSB Driver Verification")
    print("=" * 60)

    device_ok = check_device_manager()
    rtl_ok = test_rtl_access()

    print("\n" + "=" * 60)
    print("VERIFICATION RESULTS")
    print("=" * 60)

    if device_ok and rtl_ok:
        print("[SUCCESS] WinUSB driver is properly installed!")
        print("You can now run: python tetra_decoder_main.py --scan-poland")
    else:
        print("[FAILED] Driver installation issues detected.")
        if not device_ok:
            print("- RTL-SDR device not found under libusb devices")
        if not rtl_ok:
            print("- Cannot access RTL-SDR device")

        print("\nTroubleshooting steps:")
        print("1. Unplug RTL-SDR device")
        print("2. Run Zadig as Administrator")
        print("3. Options -> List All Devices")
        print("4. Select 'Bulk-In, Interface' (VID_0BDA&PID_2838)")
        print("5. Select 'WinUSB' driver")
        print("6. Click 'Replace Driver'")
        print("7. Plug in RTL-SDR device")
        print("8. Run this verification script again")

    print("=" * 60)

if __name__ == "__main__":
    main()