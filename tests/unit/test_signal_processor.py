"""
Unit tests for signal processing module.
"""

import pytest
import numpy as np
from tetraear.signal.processor import SignalProcessor


@pytest.mark.unit
class TestSignalProcessor:
    """Test SignalProcessor class."""
    
    def test_processor_initialization(self):
        """Test processor initialization."""
        processor = SignalProcessor()
        assert processor.sample_rate == 2.4e6
        assert processor.symbol_rate == 18000
        assert processor.samples_per_symbol > 0
    
    def test_processor_custom_sample_rate(self):
        """Test processor with custom sample rate."""
        processor = SignalProcessor(sample_rate=1.0e6)
        assert processor.sample_rate == 1.0e6
        assert processor.symbol_rate == 18000
    
    def test_resample(self, sample_iq_samples):
        """Test signal resampling."""
        processor = SignalProcessor()
        target_rate = 1.2e6
        result = processor.resample(sample_iq_samples, target_rate)
        assert len(result) > 0
        assert isinstance(result, np.ndarray)
        assert np.iscomplexobj(result)
    
    def test_filter_signal_empty(self):
        """Test filtering empty signal."""
        processor = SignalProcessor()
        samples = np.array([])
        result = processor.filter_signal(samples)
        assert len(result) == 0
    
    def test_filter_signal(self, sample_iq_samples):
        """Test signal filtering."""
        processor = SignalProcessor()
        result = processor.filter_signal(sample_iq_samples, bandwidth=25000)
        assert len(result) == len(sample_iq_samples)
        assert isinstance(result, np.ndarray)
    
    def test_filter_signal_custom_bandwidth(self, sample_iq_samples):
        """Test filtering with custom bandwidth."""
        processor = SignalProcessor()
        result = processor.filter_signal(sample_iq_samples, bandwidth=50000)
        assert len(result) == len(sample_iq_samples)
    
    def test_frequency_shift(self, sample_iq_samples):
        """Test frequency shifting."""
        processor = SignalProcessor()
        freq_offset = 1000  # 1 kHz
        result = processor.frequency_shift(sample_iq_samples, freq_offset)
        assert len(result) == len(sample_iq_samples)
        assert isinstance(result, np.ndarray)
        assert np.iscomplexobj(result)
    
    def test_frequency_shift_zero(self, sample_iq_samples):
        """Test frequency shifting with zero offset."""
        processor = SignalProcessor()
        result = processor.frequency_shift(sample_iq_samples, 0)
        # Should return original (or very close)
        assert len(result) == len(sample_iq_samples)
    
    def test_demodulate_dqpsk_empty(self):
        """Test DQPSK demodulation with empty samples."""
        processor = SignalProcessor()
        samples = np.array([])
        result = processor.demodulate_dqpsk(samples)
        assert len(result) == 0
        assert isinstance(result, np.ndarray)
    
    def test_demodulate_dqpsk_single_sample(self):
        """Test DQPSK demodulation with single sample."""
        processor = SignalProcessor()
        samples = np.array([1.0 + 1.0j])
        result = processor.demodulate_dqpsk(samples)
        # Should return empty (needs at least 2 samples)
        assert len(result) == 0
    
    def test_demodulate_dqpsk(self, sample_iq_samples):
        """Test DQPSK demodulation."""
        processor = SignalProcessor()
        result = processor.demodulate_dqpsk(sample_iq_samples)
        assert len(result) > 0
        assert isinstance(result, np.ndarray)
        assert result.dtype == np.uint8
        assert all(0 <= s <= 3 for s in result)
    
    def test_extract_symbols_empty(self):
        """Test symbol extraction with empty samples."""
        processor = SignalProcessor()
        samples = np.array([])
        result = processor.extract_symbols(samples)
        assert len(result) == 0
    
    def test_extract_symbols(self, sample_iq_samples):
        """Test symbol extraction."""
        processor = SignalProcessor()
        result = processor.extract_symbols(sample_iq_samples)
        assert len(result) > 0
        assert isinstance(result, np.ndarray)
        assert np.iscomplexobj(result)
    
    def test_extract_symbols_custom_rate(self, sample_iq_samples):
        """Test symbol extraction with custom sample rate."""
        processor = SignalProcessor()
        result = processor.extract_symbols(sample_iq_samples, sample_rate=1.0e6)
        assert len(result) > 0
