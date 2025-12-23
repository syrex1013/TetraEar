"""
Frequency scanner for TETRA signal detection.
Automatically scans frequency ranges to find active TETRA channels.
"""

import numpy as np
from scipy import signal
import logging
import time
from typing import List, Dict, Tuple, Optional

logger = logging.getLogger(__name__)

# Import decoder for frame validation
try:
    from tetraear.signal.processor import SignalProcessor
    from tetraear.core.decoder import TetraDecoder
    DECODER_AVAILABLE = True
except ImportError:
    DECODER_AVAILABLE = False
    logger.warning("Decoder not available for frame validation")


class TetraSignalDetector:
    """Detects TETRA signals in captured samples."""
    
    def __init__(self, sample_rate=2.4e6, noise_floor=-45, bottom_threshold=-85):
        """
        Initialize signal detector.
        
        Args:
            sample_rate: Sample rate in Hz (default: 2.4 MHz per TETRA spec)
            noise_floor: Noise floor threshold in dB (default: -45 dB)
            bottom_threshold: Bottom power threshold in dB (default: -85 dB)
        """
        self.sample_rate = sample_rate
        self.symbol_rate = 18000  # TETRA symbol rate (18 kHz)
        self.channel_bandwidth = 25000  # TETRA channel bandwidth (25 kHz)
        self.noise_floor = noise_floor
        self.bottom_threshold = bottom_threshold
        
    def calculate_power(self, samples: np.ndarray) -> float:
        """
        Calculate signal power.
        
        Args:
            samples: Complex IQ samples
            
        Returns:
            Power in dB
        """
        if samples.size == 0:
            return float(self.bottom_threshold)
        power = np.mean(np.abs(samples) ** 2)
        return 10 * np.log10(power + 1e-10)  # Add small value to avoid log(0)
    
    def detect_tetra_modulation(self, samples: np.ndarray) -> Tuple[bool, float]:
        """
        Detect if signal appears to be TETRA (π/4-DQPSK).
        
        Args:
            samples: Complex IQ samples
            
        Returns:
            (is_tetra, confidence) tuple
        """
        if len(samples) < 1000:
            return False, 0.0
        
        # Normalize samples
        samples = samples / (np.abs(samples).max() + 1e-10)
        
        # Calculate phase differences (characteristic of DQPSK)
        phase_diffs = np.diff(np.angle(samples))
        phase_diffs = (phase_diffs + np.pi) % (2 * np.pi) - np.pi
        
        # TETRA uses π/4-DQPSK, so phase differences should cluster around
        # multiples of π/4
        expected_phases = np.array([-np.pi, -3*np.pi/4, -np.pi/2, -np.pi/4, 
                                    0, np.pi/4, np.pi/2, 3*np.pi/4])
        
        # Count how many phase differences are close to expected values
        matches = 0
        tolerance = np.pi / 8
        
        for phase_diff in phase_diffs:
            distances = np.abs(expected_phases - phase_diff)
            if np.min(distances) < tolerance:
                matches += 1
        
        confidence = matches / len(phase_diffs)
        
        # Stricter threshold for TETRA detection (was 0.3, now 0.4)
        is_tetra = confidence > 0.4
        
        return is_tetra, confidence
    
    def detect_sync_pattern(self, samples: np.ndarray) -> Tuple[bool, float]:
        """
        Attempt to detect TETRA sync pattern in signal.
        
        Args:
            samples: Complex IQ samples
            
        Returns:
            (found_sync, correlation) tuple
        """
        # Downsample to approximate symbol rate
        downsample_factor = max(1, int(self.sample_rate / self.symbol_rate / 10))
        symbols = samples[::downsample_factor]
        
        if len(symbols) < 100:
            return False, 0.0
        
        # Convert to phase differences
        phase_diffs = np.diff(np.angle(symbols))
        phase_diffs = (phase_diffs + np.pi) % (2 * np.pi) - np.pi
        
        # Convert phase differences to bits (simplified)
        # This is a rough approximation
        bits = []
        for phase in phase_diffs:
            # Quantize to nearest π/4 multiple
            quantized = round(phase / (np.pi / 4)) * (np.pi / 4)
            # Convert to bit pattern (simplified)
            bit_val = 1 if abs(quantized) < np.pi / 8 else 0
            bits.append(bit_val)
        
        if len(bits) < 31:
            return False, 0.0
        
        # TETRA sync pattern (31 bits)
        sync_pattern = np.array([0, 1, 0, 1, 1, 0, 0, 1, 1, 1, 0, 0, 0, 1, 0, 0,
                                 1, 0, 1, 1, 0, 0, 1, 1, 1, 0, 0, 0, 1, 0, 0])
        
        # Search for sync pattern
        max_correlation = 0.0
        for i in range(len(bits) - len(sync_pattern)):
            window = np.array(bits[i:i+len(sync_pattern)])
            correlation = np.sum(window == sync_pattern) / len(sync_pattern)
            max_correlation = max(max_correlation, correlation)
        
        # Lower threshold for sync detection (was 0.85, now 0.75)
        # Real-world signals often have noise or multipath fading
        found_sync = max_correlation > 0.75
        
        return found_sync, max_correlation
    
    def validate_frames(self, samples: np.ndarray) -> Tuple[bool, float]:
        """
        Attempt to decode frames and validate CRC to confirm TETRA signal.
        
        Args:
            samples: Complex IQ samples
            
        Returns:
            (frames_valid, crc_pass_rate) tuple
        """
        if not DECODER_AVAILABLE or len(samples) < 10000:
            return False, 0.0
        
        try:
            # Process signal through decoder
            processor = SignalProcessor(sample_rate=self.sample_rate)
            demodulated = processor.process(samples)
            
            if len(demodulated) < 255:  # Need at least one TETRA slot
                return False, 0.0
            
            # Try to decode frames
            decoder = TetraDecoder(auto_decrypt=False)  # Don't try decryption for validation
            frames = decoder.decode(demodulated)
            
            if len(frames) == 0:
                return False, 0.0
            
            # Check CRC pass rate
            crc_pass_count = 0
            total_frames = 0
            
            for frame in frames:
                total_frames += 1
                # Check if frame has valid CRC (from protocol parser)
                if frame.get('burst_crc') is True:
                    crc_pass_count += 1
                elif frame.get('burst_crc') is False:
                    pass  # CRC failed
                else:
                    # If CRC status unknown, assume valid if frame structure is correct
                    if 'type' in frame and 'number' in frame:
                        crc_pass_count += 0.5  # Partial credit
            
            crc_rate = crc_pass_count / max(total_frames, 1)
            
            # Require at least 2 frames and >50% CRC pass rate
            is_valid = total_frames >= 2 and crc_rate > 0.5
            
            return is_valid, crc_rate
            
        except Exception as e:
            logger.debug(f"Frame validation error: {e}")
            return False, 0.0
    
    def check_power_stability(self, samples: np.ndarray, num_windows: int = 5) -> bool:
        """
        Check if signal power is stable (not transient noise).
        
        Args:
            samples: Complex IQ samples
            num_windows: Number of windows to check
            
        Returns:
            True if power is stable
        """
        if len(samples) < num_windows * 1000:
            return False
        
        window_size = len(samples) // num_windows
        powers = []
        
        for i in range(num_windows):
            window = samples[i * window_size:(i + 1) * window_size]
            power = self.calculate_power(window)
            powers.append(power)
        
        # Check if power variation is reasonable (std dev < 10 dB)
        if len(powers) > 1:
            power_std = np.std(powers)
            return power_std < 10.0
        
        return True
    
    def analyze_signal(self, samples: np.ndarray) -> Dict:
        """
        Analyze signal to determine if it's TETRA.
        Uses stricter validation requiring BOTH modulation AND sync detection.
        
        Args:
            samples: Complex IQ samples
            
        Returns:
            Analysis dictionary with detection results
        """
        power = self.calculate_power(samples)
        is_tetra_mod, mod_confidence = self.detect_tetra_modulation(samples)
        has_sync, sync_correlation = self.detect_sync_pattern(samples)
        
        # Require BOTH modulation detection AND sync pattern (not OR)
        # This reduces false positives significantly
        basic_tetra_match = is_tetra_mod and has_sync
        
        # Additional validation: try to decode frames
        frames_valid, crc_rate = self.validate_frames(samples)
        
        # Check power stability
        power_stable = self.check_power_stability(samples)
        
        # Overall confidence calculation
        if has_sync and is_tetra_mod:
            # Both detected - high confidence
            confidence = (mod_confidence * 0.4 + sync_correlation * 0.4 + crc_rate * 0.2)
        elif has_sync:
            # Only sync - medium confidence
            confidence = sync_correlation * 0.6
        elif is_tetra_mod:
            # Only modulation - low confidence
            confidence = mod_confidence * 0.5
        else:
            confidence = 0.0
        
        # Final decision: require BOTH modulation AND sync, plus frame validation if available
        is_tetra = basic_tetra_match and power_stable
        if frames_valid:
            # Frame validation confirms it's TETRA
            is_tetra = True
            confidence = max(confidence, 0.7)  # Boost confidence if frames validate
        
        return {
            'power_db': power,
            'is_tetra': is_tetra,
            'confidence': confidence,
            'modulation_confidence': mod_confidence,
            'sync_detected': has_sync,
            'sync_correlation': sync_correlation,
            'frames_validated': frames_valid,
            'crc_pass_rate': crc_rate,
            'power_stable': power_stable,
            'signal_present': power > self.bottom_threshold  # Use bottom_threshold for signal presence
        }


class FrequencyScanner:
    """Scans frequency ranges to find TETRA signals."""
    
    # Poland TETRA frequency ranges (MHz)
    # Primary range around 392.5 MHz with 25 kHz channel spacing
    POLAND_RANGES = [
        (390.0, 395.0),   # Primary range (includes 392.5 MHz)
        (380.0, 385.0),   # Additional emergency services
        (410.0, 430.0),   # Civilian use
    ]
    
    # Default TETRA channel spacing (kHz)
    CHANNEL_SPACING = 25.0  # 25 kHz
    
    def __init__(self, rtl_capture, sample_rate=2.4e6, scan_step=25e3, noise_floor=-45, bottom_threshold=-85):
        """
        Initialize frequency scanner.
        
        Args:
            rtl_capture: RTLCapture instance
            sample_rate: Sample rate in Hz (default: 2.4 MHz per TETRA spec)
            scan_step: Frequency step size for scanning (default: 25 kHz - TETRA channel spacing)
            noise_floor: Noise floor threshold in dB (default: -45 dB)
            bottom_threshold: Bottom power threshold in dB (default: -85 dB)
        """
        self.capture = rtl_capture
        self.sample_rate = sample_rate
        self.scan_step = scan_step
        self.noise_floor = noise_floor
        self.bottom_threshold = bottom_threshold
        self.detector = TetraSignalDetector(sample_rate, noise_floor=noise_floor, bottom_threshold=bottom_threshold)
        self.found_channels = []  # List of found TETRA channels
        
    def scan_frequency(self, frequency: float, dwell_time: float = 0.5) -> Dict:
        """
        Scan a single frequency for TETRA signals.
        
        Args:
            frequency: Frequency to scan in Hz
            dwell_time: Time to spend on frequency in seconds
            
        Returns:
            Detection result dictionary
        """
        try:
            # Tune to frequency
            if hasattr(self.capture, 'sdr') and self.capture.sdr:
                self.capture.sdr.center_freq = frequency
            elif hasattr(self.capture, 'set_frequency'):
                self.capture.set_frequency(frequency)
            
            # Wait for PLL to lock (shorter wait)
            time.sleep(0.05)
            
            # Capture samples (limit to prevent hanging)
            num_samples = min(int(self.sample_rate * dwell_time), 256 * 1024)  # Max 256k samples
            try:
                samples = self.capture.read_samples(num_samples)
            except Exception as e:
                logger.debug(f"Error reading samples at {frequency/1e6:.3f} MHz: {e}")
                samples = np.array([], dtype=complex)
            
            # Analyze signal if we have samples
            if len(samples) > 100:
                analysis = self.detector.analyze_signal(samples)
            else:
                # Not enough samples - return default
                analysis = {
                    'power_db': -100,
                    'is_tetra': False,
                    'confidence': 0.0,
                    'signal_present': False
                }
            
            analysis['frequency'] = frequency
            analysis['frequency_mhz'] = frequency / 1e6
            
            return analysis
        
        except Exception as e:
            logger.debug(f"Error scanning {frequency/1e6:.3f} MHz: {e}")
            return {
                'frequency': frequency,
                'frequency_mhz': frequency / 1e6,
                'power_db': -100,
                'is_tetra': False,
                'confidence': 0.0,
                'signal_present': False,
                'error': str(e)
            }
    
    def scan_range(self, start_freq: float, end_freq: float, 
                   min_power: float = -70, min_confidence: float = 0.4) -> List[Dict]:
        """
        Scan a frequency range for TETRA signals.
        
        Args:
            start_freq: Start frequency in Hz
            end_freq: End frequency in Hz
            min_power: Minimum power threshold in dB
            min_confidence: Minimum confidence threshold
            
        Returns:
            List of detected TETRA channels
        """
        logger.info(f"Scanning range: {start_freq/1e6:.3f} - {end_freq/1e6:.3f} MHz")
        
        found = []
        num_steps = int((end_freq - start_freq) / self.scan_step)
        
        for step in range(num_steps + 1):
            freq = start_freq + step * self.scan_step
            
            # Skip if outside range
            if freq > end_freq:
                break
            
            result = self.scan_frequency(freq, dwell_time=0.3)
            
            # Check if TETRA signal detected (stricter criteria)
            is_tetra = result.get('is_tetra', False)
            power_db = result.get('power_db', -100)
            confidence = result.get('confidence', 0)
            sync_detected = result.get('sync_detected', False)
            frames_validated = result.get('frames_validated', False)
            power_stable = result.get('power_stable', False)
            
            # Require: TETRA match, sufficient power, confidence, AND sync detection
            # Frame validation is optional but boosts confidence
            if (is_tetra and 
                power_db > min_power and
                confidence > min_confidence and
                sync_detected and
                power_stable):
                
                found.append(result)
                validation_info = ""
                if frames_validated:
                    crc_rate = result.get('crc_pass_rate', 0)
                    validation_info = f", CRC: {crc_rate:.1%}"
                
                logger.info(
                    f"Found TETRA signal at {freq/1e6:.3f} MHz - "
                    f"Power: {power_db:.1f} dB, "
                    f"Confidence: {confidence:.2f}, "
                    f"Sync: {sync_detected}{validation_info}"
                )
            
            # Progress update
            if step % 10 == 0:
                progress = (step / num_steps) * 100
                logger.debug(f"Scan progress: {progress:.1f}%")
        
        return found
    
    def scan_around_392_5(self, range_mhz: float = 2.5, 
                          min_power: float = -70, min_confidence: float = 0.4) -> List[Dict]:
        """
        Scan specifically around 392.5 MHz (Poland primary TETRA frequency).
        
        Args:
            range_mhz: Range to scan around 392.5 MHz in MHz (default: 2.5 MHz = 390-395 MHz)
            min_power: Minimum power threshold in dB
            min_confidence: Minimum confidence threshold
            
        Returns:
            List of detected TETRA channels
        """
        center_freq = 392.5e6  # 392.5 MHz
        start_freq = center_freq - (range_mhz * 1e6 / 2)
        end_freq = center_freq + (range_mhz * 1e6 / 2)
        
        logger.info(f"Scanning around 392.5 MHz (±{range_mhz/2:.1f} MHz, 25 kHz steps)...")
        
        found = self.scan_range(
            start_freq,
            end_freq,
            min_power=min_power,
            min_confidence=min_confidence
        )
        
        self.found_channels = found
        
        logger.info(f"Scan complete. Found {len(found)} TETRA channel(s) around 392.5 MHz")
        
        return found
    
    def scan_poland(self, min_power: float = -70, min_confidence: float = 0.4) -> List[Dict]:
        """
        Scan Poland TETRA frequency ranges.
        Focuses on 390-395 MHz range (includes 392.5 MHz primary frequency).
        
        Args:
            min_power: Minimum power threshold in dB
            min_confidence: Minimum confidence threshold
            
        Returns:
            List of detected TETRA channels
        """
        logger.info("Starting scan of Poland TETRA frequency ranges...")
        logger.info("Primary range: 390-395 MHz (includes 392.5 MHz with 25 kHz channels)")
        all_found = []
        
        # Start with primary range around 392.5 MHz
        primary_start = 390.0
        primary_end = 395.0
        logger.info(f"Scanning primary range: {primary_start}-{primary_end} MHz (25 kHz steps)...")
        found = self.scan_range(
            primary_start * 1e6,
            primary_end * 1e6,
            min_power=min_power,
            min_confidence=min_confidence
        )
        all_found.extend(found)
        
        # Scan additional ranges
        for start_mhz, end_mhz in self.POLAND_RANGES:
            if (start_mhz, end_mhz) == (primary_start, primary_end):
                continue  # Already scanned
            
            logger.info(f"Scanning {start_mhz}-{end_mhz} MHz range...")
            found = self.scan_range(
                start_mhz * 1e6,
                end_mhz * 1e6,
                min_power=min_power,
                min_confidence=min_confidence
            )
            all_found.extend(found)
        
        # Sort by frequency
        all_found.sort(key=lambda x: x['frequency'])
        
        self.found_channels = all_found
        
        logger.info(f"Scan complete. Found {len(all_found)} TETRA channel(s)")
        
        return all_found
    
    def get_found_channels(self) -> List[Dict]:
        """Get list of found TETRA channels."""
        return self.found_channels
    
    def print_found_channels(self):
        """Print found channels in a formatted table."""
        if not self.found_channels:
            logger.info("No TETRA channels found")
            return
        
        logger.info("\n" + "=" * 80)
        logger.info("Found TETRA Channels:")
        logger.info("=" * 80)
        logger.info(f"{'Frequency (MHz)':<18} {'Power (dB)':<12} {'Confidence':<12} {'Sync':<8}")
        logger.info("-" * 80)
        
        for channel in self.found_channels:
            freq = channel['frequency_mhz']
            power = channel['power_db']
            conf = channel['confidence']
            sync = "Yes" if channel.get('sync_detected', False) else "No"
            
            logger.info(f"{freq:>15.3f}     {power:>8.1f}     {conf:>8.2f}     {sync:>6}")
        
        logger.info("=" * 80 + "\n")
