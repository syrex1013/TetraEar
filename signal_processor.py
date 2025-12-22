"""
Signal processing module for TETRA demodulation.
"""

import numpy as np
from scipy import signal
import logging

logger = logging.getLogger(__name__)


class SignalProcessor:
    """Processes raw IQ samples for TETRA demodulation."""
    
    def __init__(self, sample_rate=1.8e6):
        """
        Initialize signal processor.
        
        Args:
            sample_rate: Sample rate in Hz
        """
        self.sample_rate = sample_rate
        # TETRA uses π/4-DQPSK modulation at 18 kHz symbol rate
        self.symbol_rate = 18000  # Hz
        self.samples_per_symbol = int(sample_rate / self.symbol_rate)
        
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
    
    def filter_signal(self, samples, bandwidth=25000):
        """
        Apply bandpass filter to isolate TETRA signal.
        
        Args:
            samples: Input samples
            bandwidth: Filter bandwidth in Hz
            
        Returns:
            Filtered samples
        """
        nyquist = self.sample_rate / 2
        # Normalize frequencies to [0, 1] range for butter filter
        low = max(0.01, (nyquist - bandwidth / 2) / nyquist)
        high = min(0.99, (nyquist + bandwidth / 2) / nyquist)
        
        # Design Butterworth bandpass filter (centered at DC for baseband)
        # For baseband signals, use lowpass filter
        cutoff = bandwidth / 2 / nyquist
        cutoff = min(0.99, max(0.01, cutoff))
        b, a = signal.butter(4, cutoff, btype='low')
        filtered = signal.filtfilt(b, a, samples)
        
        return filtered
    
    def frequency_shift(self, samples, freq_offset):
        """
        Apply frequency correction.
        
        Args:
            samples: Input samples
            freq_offset: Frequency offset in Hz
            
        Returns:
            Frequency-shifted samples
        """
        t = np.arange(len(samples)) / self.sample_rate
        shift = np.exp(-1j * 2 * np.pi * freq_offset * t)
        return samples * shift
    
    def demodulate_dqpsk(self, samples):
        """
        Demodulate π/4-DQPSK signal.
        
        Args:
            samples: Input complex samples
            
        Returns:
            Demodulated symbols
        """
        # Normalize samples
        samples = samples / np.abs(samples).max()
        
        # Differential detection
        symbols = []
        prev_sample = samples[0]
        
        for sample in samples[1:]:
            # Differential phase detection
            diff = sample * np.conj(prev_sample)
            phase = np.angle(diff)
            
            # Map phase to symbol (π/4-DQPSK has 8 possible phases)
            # Normalize to [0, 2π]
            phase = (phase + 2 * np.pi) % (2 * np.pi)
            
            # Quantize to nearest symbol
            symbol = int(round(phase / (np.pi / 4))) % 8
            symbols.append(symbol)
            
            prev_sample = sample
        
        return np.array(symbols)
    
    def extract_symbols(self, samples):
        """
        Extract symbols from samples at symbol rate.
        
        Args:
            samples: Input samples
            
        Returns:
            Symbol stream
        """
        # Downsample to symbol rate
        if self.samples_per_symbol > 1:
            symbols = samples[::self.samples_per_symbol]
        else:
            symbols = samples
        
        return symbols
    
    def process(self, samples, freq_offset=0):
        """
        Complete signal processing pipeline.
        
        Args:
            samples: Raw IQ samples
            freq_offset: Frequency offset correction
            
        Returns:
            Demodulated symbols
        """
        # Apply frequency correction if needed
        if freq_offset != 0:
            samples = self.frequency_shift(samples, freq_offset)
        
        # Filter signal
        filtered = self.filter_signal(samples)
        
        # Extract symbols
        symbols = self.extract_symbols(filtered)
        
        # Demodulate
        demodulated = self.demodulate_dqpsk(symbols)
        
        return demodulated
