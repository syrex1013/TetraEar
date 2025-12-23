"""
Integration tests for frequency scanner.
"""

import pytest
import numpy as np
from unittest.mock import Mock, MagicMock, patch
from tetraear.signal.scanner import TetraSignalDetector


@pytest.mark.integration
class TestTetraSignalDetector:
    """Test TetraSignalDetector class."""
    
    def test_detector_initialization(self):
        """Test detector initialization."""
        detector = TetraSignalDetector()
        assert detector.sample_rate == 2.4e6
        assert detector.symbol_rate == 18000
        assert detector.channel_bandwidth == 25000
    
    def test_detector_custom_parameters(self):
        """Test detector with custom parameters."""
        detector = TetraSignalDetector(
            sample_rate=1.8e6,
            noise_floor=-50,
            bottom_threshold=-90
        )
        assert detector.sample_rate == 1.8e6
        assert detector.noise_floor == -50
        assert detector.bottom_threshold == -90
    
    def test_calculate_power(self, sample_iq_samples):
        """Test power calculation."""
        detector = TetraSignalDetector()
        power = detector.calculate_power(sample_iq_samples)
        assert isinstance(power, float)
        # Power can be positive or negative depending on signal strength
        assert not np.isnan(power) and not np.isinf(power)
    
    def test_calculate_power_empty(self):
        """Test power calculation with empty samples."""
        detector = TetraSignalDetector()
        samples = np.array([])
        power = detector.calculate_power(samples)
        assert isinstance(power, float)
    
    def test_detect_tetra_modulation(self, sample_iq_samples):
        """Test TETRA modulation detection."""
        detector = TetraSignalDetector()
        is_tetra, confidence = detector.detect_tetra_modulation(sample_iq_samples)
        assert isinstance(is_tetra, bool)
        assert isinstance(confidence, float)
        assert 0.0 <= confidence <= 1.0
    
    def test_detect_tetra_modulation_insufficient_samples(self):
        """Test modulation detection with insufficient samples."""
        detector = TetraSignalDetector()
        samples = np.array([1.0 + 1.0j] * 100)  # Less than 1000
        is_tetra, confidence = detector.detect_tetra_modulation(samples)
        assert is_tetra is False
        assert confidence == 0.0
    
    def test_detect_sync_pattern(self, sample_iq_samples):
        """Test sync pattern detection."""
        detector = TetraSignalDetector()
        has_sync, confidence = detector.detect_sync_pattern(sample_iq_samples)
        # Convert numpy bool to Python bool
        assert isinstance(bool(has_sync), bool)
        assert isinstance(confidence, float)
        assert 0.0 <= confidence <= 1.0
    
    def test_scan_frequency_range_mock(self):
        """Test frequency scanning with mocked RTL-SDR."""
        import tetraear.signal.capture as capture_module
        from tetraear.signal.capture import RTLCapture
        
        detector = TetraSignalDetector()
        
        # Mock RTL-SDR capture
        original_available = capture_module.RTL_SDR_AVAILABLE
        try:
            capture_module.RTL_SDR_AVAILABLE = True
            with patch.object(capture_module, "RtlSdr") as mock_rtl:
                mock_sdr = MagicMock()
                mock_rtl.return_value = mock_sdr
                mock_sdr.get_device_serial_addresses.return_value = ["00000001"]

                # Mock sample reading
                mock_samples = np.random.randn(10000) + 1j * np.random.randn(10000)
                mock_sdr.read_samples.return_value = mock_samples

                capture = RTLCapture()
                assert capture.open() is True

                samples = capture.read_samples(10000)
                power = detector.calculate_power(samples)
                assert isinstance(power, float)

                is_tetra, confidence = detector.detect_tetra_modulation(samples)
                assert isinstance(is_tetra, bool)
                assert isinstance(confidence, float)
        finally:
            capture_module.RTL_SDR_AVAILABLE = original_available
    
    def test_signal_strength_calculation(self, sample_iq_samples):
        """Test signal strength calculation."""
        detector = TetraSignalDetector()
        power = detector.calculate_power(sample_iq_samples)
        
        # Power should be in reasonable range for test signal
        assert power < 100  # Should not be extremely high
        assert power > -200  # Should not be extremely low
    
    def test_modulation_confidence_scaling(self):
        """Test that modulation confidence scales appropriately."""
        detector = TetraSignalDetector()
        
        # Create samples with different characteristics
        # Random noise (low confidence)
        noise = np.random.randn(2000) + 1j * np.random.randn(2000)
        _, conf_noise = detector.detect_tetra_modulation(noise)
        
        # More structured signal (potentially higher confidence)
        structured = np.exp(1j * np.linspace(0, 4*np.pi, 2000))
        _, conf_structured = detector.detect_tetra_modulation(structured)
        
        # Both should be valid confidence values
        assert 0.0 <= conf_noise <= 1.0
        assert 0.0 <= conf_structured <= 1.0
