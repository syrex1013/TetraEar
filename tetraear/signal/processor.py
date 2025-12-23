"""
Signal processing module for TETRA demodulation.

Implements π/4-DQPSK demodulation according to TETRA specifications:
- ETSI EN 300 392-2 V3.2.1 (Air Interface)
- Symbol rate: 18 kHz
- Channel bandwidth: 25 kHz
- Modulation: π/4-DQPSK with phase transitions per Table 5.1
"""

import numpy as np
from scipy import signal
import logging

logger = logging.getLogger(__name__)


class SignalProcessor:
    """Processes raw IQ samples for TETRA demodulation."""
    
    def __init__(self, sample_rate=2.4e6):
        """
        Initialize signal processor.
        
        Args:
            sample_rate: Sample rate in Hz (default: 2.4 MHz per TETRA spec)
        """
        self.sample_rate = sample_rate
        # TETRA uses π/4-DQPSK modulation at 18 kHz symbol rate
        self.symbol_rate = 18000  # Hz (TETRA standard symbol rate)
        self.samples_per_symbol = int(sample_rate / self.symbol_rate)
        # Store symbols for voice extraction
        self.symbols = None
        
    def resample(self, samples, target_rate):
        """
        Resample signal to target rate.
        
        Args:
            samples: Input samples
            target_rate: Target sample rate
            
        Returns:
            Resampled samples
        """
        num_samples = len(samples)
        new_num_samples = int(num_samples * target_rate / self.sample_rate)
        resampled = signal.resample(samples, new_num_samples)
        return resampled
    
    def filter_signal(self, samples, bandwidth=25000, sample_rate=None):
        """
        Apply bandpass filter to isolate TETRA signal channel.
        
        TETRA channels use 25 kHz bandwidth. For baseband IQ signals,
        a lowpass filter is applied to remove out-of-band noise.
        
        Args:
            samples: Input samples
            bandwidth: Filter bandwidth in Hz (default: 25 kHz for TETRA)
            sample_rate: Sample rate in Hz (optional, defaults to self.sample_rate)
            
        Returns:
            Filtered samples
        """
        if len(samples) == 0:
            return samples
        
        fs = sample_rate if sample_rate is not None else self.sample_rate
        nyquist = fs / 2
        
        # Design Butterworth lowpass filter for baseband signal
        # Filter should pass TETRA channel bandwidth (25 kHz)
        cutoff = (bandwidth / 2) / nyquist
        cutoff = min(0.99, max(0.01, cutoff))  # Ensure valid range
        
        try:
            b, a = signal.butter(4, cutoff, btype='low')
            filtered = signal.filtfilt(b, a, samples)
            return filtered
        except Exception as e:
            logger.warning(f"Filter design failed, using unfiltered samples: {e}")
            return samples
    
    def frequency_shift(self, samples, freq_offset, sample_rate=None):
        """
        Apply frequency correction.
        
        Args:
            samples: Input samples
            freq_offset: Frequency offset in Hz
            sample_rate: Sample rate in Hz (optional, defaults to self.sample_rate)
            
        Returns:
            Frequency-shifted samples
        """
        fs = sample_rate if sample_rate is not None else self.sample_rate
        t = np.arange(len(samples)) / fs
        shift = np.exp(-1j * 2 * np.pi * freq_offset * t)
        return samples * shift
    
    def demodulate_dqpsk(self, samples):
        """
        Demodulate π/4-DQPSK signal according to TETRA specifications.
        
        TETRA uses π/4-DQPSK with phase transitions:
        - Bits (1,1) -> -3π/4
        - Bits (0,1) -> +3π/4  
        - Bits (0,0) -> +π/4
        - Bits (1,0) -> -π/4
        
        Reference: ETSI EN 300 392-2 V3.2.1, Table 5.1
        
        Args:
            samples: Input complex samples
            
        Returns:
            Demodulated symbols (0-3 mapping to bit pairs)
        """
        if len(samples) < 2:
            return np.array([], dtype=np.uint8)
        
        # Normalize samples to prevent overflow
        sample_power = np.abs(samples)
        max_power = np.max(sample_power)
        if max_power > 0:
            samples = samples / max_power
        
        # Differential detection: phase difference between consecutive symbols
        symbols = []
        prev_sample = samples[0]
        
        # TETRA π/4-DQPSK uses 8 constellation points at multiples of π/4
        # Phase transitions are: ±π/4, ±3π/4
        for sample in samples[1:]:
            # Calculate differential phase: Δφ = arg(sample * conj(prev_sample))
            diff = sample * np.conj(prev_sample)
            phase_diff = np.angle(diff)
            
            # Normalize phase to [-π, π]
            phase_diff = np.arctan2(np.imag(diff), np.real(diff))
            
            # Map phase difference to TETRA symbol according to spec
            # Quantize to nearest valid phase transition
            # Valid transitions: -3π/4, -π/4, +π/4, +3π/4
            # Mapping to bits (MSB, LSB) for symbols_to_bits (val >> 1, val & 1):
            # +π/4  -> Bits (0,0) -> Symbol 0
            # +3π/4 -> Bits (0,1) -> Symbol 1
            # -π/4  -> Bits (1,0) -> Symbol 2
            # -3π/4 -> Bits (1,1) -> Symbol 3
            
            if phase_diff < -5*np.pi/8:
                symbol = 3  # Closest to -3π/4 (bits: 1,1)
            elif phase_diff < -3*np.pi/8:
                symbol = 2  # Closest to -π/4 (bits: 1,0)
            elif phase_diff < 3*np.pi/8:
                symbol = 0  # Closest to +π/4 (bits: 0,0)
            elif phase_diff < 5*np.pi/8:
                symbol = 1  # Closest to +3π/4 (bits: 0,1)
            else:
                symbol = 3  # Wrap around to -3π/4
            
            symbols.append(symbol)
            prev_sample = sample
        
        return np.array(symbols, dtype=np.uint8)
    
    def extract_symbols(self, samples, sample_rate=None):
        """
        Extract symbols from samples at symbol rate with simple timing recovery.
        
        Args:
            samples: Input samples
            sample_rate: Sample rate in Hz (optional, defaults to self.sample_rate)
            
        Returns:
            Symbol stream (complex samples at symbol rate)
        """
        if len(samples) == 0:
            return np.array([], dtype=complex)
        
        fs = sample_rate if sample_rate is not None else self.sample_rate
        samples_per_symbol = int(fs / self.symbol_rate)
        
        # Downsample to symbol rate using decimation
        if samples_per_symbol > 1:
            # Simple timing recovery: Find the phase with maximum average power
            # This helps align with the symbol centers (RRC pulse peaks)
            best_phase = 0
            max_power = -1
            
            # Check a few phases to find the best alignment
            # We don't need to check every sample, just enough to find the peak
            step = max(1, samples_per_symbol // 8)
            
            for phase in range(0, samples_per_symbol, step):
                # Extract symbols at this phase
                num_symbols = (len(samples) - phase) // samples_per_symbol
                if num_symbols <= 0:
                    continue
                    
                indices = phase + np.arange(num_symbols) * samples_per_symbol
                phase_samples = samples[indices]
                
                # Calculate average power for this phase
                power = np.mean(np.abs(phase_samples)**2)
                
                if power > max_power:
                    max_power = power
                    best_phase = phase
            
            # Extract using the best phase
            num_symbols = (len(samples) - best_phase) // samples_per_symbol
            indices = best_phase + np.arange(num_symbols) * samples_per_symbol
            symbols = samples[indices]
        else:
            symbols = samples
        
        return symbols
    
    def process(self, samples, freq_offset=0):
        """
        Complete signal processing pipeline for TETRA demodulation.
        
        Processing steps:
        1. Decimation (if sample rate is high)
        2. Frequency offset correction (if needed)
        3. Bandpass filtering to isolate TETRA channel (25 kHz bandwidth)
        4. Symbol extraction at 18 kHz symbol rate
        5. π/4-DQPSK differential demodulation
        
        Args:
            samples: Raw IQ samples
            freq_offset: Frequency offset correction in Hz
            
        Returns:
            Demodulated symbols (0-3 representing bit pairs)
        """
        if len(samples) == 0:
            self.symbols = np.array([], dtype=complex)
            return np.array([], dtype=np.uint8)
            
        # Handle high sample rates by decimating first
        # Target ~240 kHz which is sufficient for TETRA (25kHz BW) and allows for some frequency offset
        target_rate = 240000
        current_rate = self.sample_rate
        
        if current_rate > target_rate * 2:
            decimation_factor = int(current_rate / target_rate)
            if decimation_factor > 1:
                # Use scipy.signal.decimate which includes a low-pass filter to prevent aliasing
                # This is much more efficient than processing at full rate
                try:
                    samples = signal.decimate(samples, decimation_factor)
                    current_rate = current_rate / decimation_factor
                except Exception as e:
                    logger.warning(f"Decimation failed: {e}")
        
        # Apply frequency correction if needed
        if freq_offset != 0:
            samples = self.frequency_shift(samples, freq_offset, sample_rate=current_rate)
        
        # Filter signal to isolate TETRA channel (25 kHz bandwidth)
        filtered = self.filter_signal(samples, bandwidth=25000, sample_rate=current_rate)
        
        # Extract symbols at symbol rate (18 kHz)
        symbols = self.extract_symbols(filtered, sample_rate=current_rate)
        self.symbols = symbols  # Store for voice extraction
        
        # Demodulate using π/4-DQPSK
        demodulated = self.demodulate_dqpsk(symbols)
        
        return demodulated
