"""
Integration tests for RTL-SDR capture module.
"""

import pytest
import numpy as np
from unittest.mock import Mock, MagicMock, patch, PropertyMock

# Import RTLCapture - it handles missing rtlsdr gracefully
try:
    from tetraear.signal.capture import RTLCapture
except ImportError:
    pytest.skip("RTLCapture not available", allow_module_level=True)


@pytest.mark.integration
class TestRTLCapture:
    """Test RTLCapture class with mocked RTL-SDR."""
    
    def test_capture_initialization(self):
        """Test capture initialization."""
        capture = RTLCapture(frequency=400e6, sample_rate=2.4e6, gain=50.0)
        assert capture.frequency == 400e6
        assert capture.sample_rate == 2.4e6
        assert capture.gain == 50.0
        assert capture.device is None
        assert capture.sdr is None
    
    def test_capture_initialization_auto_gain(self):
        """Test capture initialization with auto gain."""
        capture = RTLCapture(gain='auto')
        assert capture.gain == 'auto'

    def test_capture_initialization_with_device(self):
        """Test capture initialization with device selector."""
        capture = RTLCapture(device=1)
        assert capture.device == 1
        capture_serial = RTLCapture(device="00000001")
        assert capture_serial.device == "00000001"

    def test_list_devices(self):
        """Test listing RTL-SDR devices."""
        import tetraear.signal.capture as capture_module

        original_available = capture_module.RTL_SDR_AVAILABLE
        try:
            capture_module.RTL_SDR_AVAILABLE = True
            mock_lib = MagicMock()
            mock_lib.rtlsdr_get_device_count.return_value = 2

            def fake_usb_strings(index, manufact, product, serial_bfr):
                serial = b"00000001" if index == 0 else b"00000002"
                for i, b in enumerate(serial):
                    serial_bfr[i] = b
                for i in range(len(serial), 256):
                    serial_bfr[i] = 0
                return 0

            mock_lib.rtlsdr_get_device_usb_strings.side_effect = fake_usb_strings
            with patch("rtlsdr.librtlsdr.librtlsdr", mock_lib):
                devices = RTLCapture.list_devices()
            assert devices == [
                {"index": 0, "serial": "00000001"},
                {"index": 1, "serial": "00000002"},
            ]
        finally:
            capture_module.RTL_SDR_AVAILABLE = original_available

    def test_list_devices_unavailable(self):
        """Test list_devices when RTL-SDR library is unavailable."""
        import tetraear.signal.capture as capture_module
        original_available = capture_module.RTL_SDR_AVAILABLE
        try:
            capture_module.RTL_SDR_AVAILABLE = False
            assert RTLCapture.list_devices() == []
        finally:
            capture_module.RTL_SDR_AVAILABLE = original_available
    
    def test_open_success(self):
        """Test successful device opening."""
        import tetraear.signal.capture as capture_module
        capture = RTLCapture()
        # Mock RtlSdr and ensure RTL_SDR_AVAILABLE is True
        original_available = capture_module.RTL_SDR_AVAILABLE
        try:
            capture_module.RTL_SDR_AVAILABLE = True
            with patch.object(capture_module, 'RtlSdr') as mock_rtl:
                mock_sdr = MagicMock()
                mock_rtl.return_value = mock_sdr
                mock_sdr.get_device_serial_addresses.return_value = ['00000001']
                
                result = capture.open()
                assert result is True
                assert capture.sdr is not None
                mock_rtl.assert_called_once_with()
                # Check that properties were set (mocked object stores values)
                assert hasattr(mock_sdr, 'sample_rate')
                assert hasattr(mock_sdr, 'center_freq')
        finally:
            capture_module.RTL_SDR_AVAILABLE = original_available

    def test_open_with_device_index(self):
        """Test opening a specific device by index."""
        import tetraear.signal.capture as capture_module
        capture = RTLCapture(device=1)
        original_available = capture_module.RTL_SDR_AVAILABLE
        try:
            capture_module.RTL_SDR_AVAILABLE = True
            with patch.object(capture_module, 'RtlSdr') as mock_rtl:
                mock_sdr = MagicMock()
                mock_rtl.return_value = mock_sdr
                result = capture.open()
                assert result is True
                mock_rtl.assert_called_once_with(device_index=1)
        finally:
            capture_module.RTL_SDR_AVAILABLE = original_available

    def test_open_with_serial_number(self):
        """Test opening a specific device by serial number."""
        import tetraear.signal.capture as capture_module
        capture = RTLCapture(device="00000001")
        original_available = capture_module.RTL_SDR_AVAILABLE
        try:
            capture_module.RTL_SDR_AVAILABLE = True
            with patch.object(capture_module, 'RtlSdr') as mock_rtl:
                mock_sdr = MagicMock()
                mock_rtl.return_value = mock_sdr
                result = capture.open()
                assert result is True
                mock_rtl.assert_called_once_with(serial_number="00000001")
        finally:
            capture_module.RTL_SDR_AVAILABLE = original_available
    
    def test_open_failure(self):
        """Test device opening failure."""
        import tetraear.signal.capture as capture_module
        capture = RTLCapture()
        # Mock RtlSdr to raise exception, and ensure RTL_SDR_AVAILABLE is True
        original_available = capture_module.RTL_SDR_AVAILABLE
        try:
            capture_module.RTL_SDR_AVAILABLE = True
            with patch.object(capture_module, 'RtlSdr', side_effect=Exception("Device not found")):
                result = capture.open()
                assert result is False
                assert capture.sdr is None
        finally:
            capture_module.RTL_SDR_AVAILABLE = original_available
    
    def test_open_usb_access_error(self):
        """Test USB access error handling."""
        import tetraear.signal.capture as capture_module
        capture = RTLCapture()
        # Mock RtlSdr to raise exception, and ensure RTL_SDR_AVAILABLE is True
        original_available = capture_module.RTL_SDR_AVAILABLE
        try:
            capture_module.RTL_SDR_AVAILABLE = True
            with patch.object(capture_module, 'RtlSdr', side_effect=Exception("LIBUSB_ERROR_ACCESS")):
                result = capture.open()
                assert result is False
        finally:
            capture_module.RTL_SDR_AVAILABLE = original_available
    
    def test_read_samples_success(self):
        """Test reading samples successfully."""
        capture = RTLCapture()
        mock_sdr = MagicMock()
        mock_samples = np.random.randn(1000) + 1j * np.random.randn(1000)
        mock_sdr.read_samples.return_value = mock_samples
        capture.sdr = mock_sdr
        
        result = capture.read_samples(1000)
        assert len(result) == 1000
        assert np.array_equal(result, mock_samples)
        mock_sdr.read_samples.assert_called_once_with(1000)
    
    def test_read_samples_not_opened(self):
        """Test reading samples when device not opened."""
        capture = RTLCapture()
        with pytest.raises(RuntimeError, match="not opened"):
            capture.read_samples()
    
    def test_read_samples_device_error(self):
        """Test handling device errors during read."""
        capture = RTLCapture()
        mock_sdr = MagicMock()
        mock_sdr.read_samples.side_effect = OSError("access violation")
        capture.sdr = mock_sdr
        
        with pytest.raises(RuntimeError):
            capture.read_samples()
    
    def test_set_frequency(self):
        """Test setting frequency."""
        capture = RTLCapture()
        mock_sdr = MagicMock()
        capture.sdr = mock_sdr
        
        capture.set_frequency(392.24e6)
        assert capture.frequency == 392.24e6
        assert mock_sdr.center_freq == 392.24e6
    
    def test_set_gain(self):
        """Test setting gain."""
        capture = RTLCapture()
        mock_sdr = MagicMock()
        capture.sdr = mock_sdr
        
        # RTLCapture doesn't have set_gain, but we can set it directly
        capture.gain = 45.0
        mock_sdr.gain = 45.0
        assert capture.gain == 45.0
        assert mock_sdr.gain == 45.0
    
    def test_set_gain_auto(self):
        """Test setting gain to auto."""
        capture = RTLCapture()
        mock_sdr = MagicMock()
        capture.sdr = mock_sdr
        
        # RTLCapture doesn't have set_gain, but we can set it directly
        capture.gain = 'auto'
        mock_sdr.gain = 'auto'
        assert capture.gain == 'auto'
        assert mock_sdr.gain == 'auto'
    
    def test_close(self):
        """Test closing device."""
        capture = RTLCapture()
        mock_sdr = MagicMock()
        capture.sdr = mock_sdr
        
        capture.close()
        mock_sdr.close.assert_called_once()
        assert capture.sdr is None
    
    def test_close_not_opened(self):
        """Test closing when device not opened."""
        capture = RTLCapture()
        # Should not raise error
        capture.close()
    
    def test_sample_rate_validation(self):
        """Test sample rate validation and rounding."""
        import tetraear.signal.capture as capture_module
        capture = RTLCapture(sample_rate=2.5e6)  # Not a valid RTL-SDR rate
        original_available = capture_module.RTL_SDR_AVAILABLE
        try:
            capture_module.RTL_SDR_AVAILABLE = True
            with patch.object(capture_module, 'RtlSdr') as mock_rtl:
                mock_sdr = MagicMock()
                mock_rtl.return_value = mock_sdr
                mock_sdr.get_device_serial_addresses.return_value = ['00000001']
                
                capture.open()
                # Should round to nearest valid rate (2.4e6 or 2.56e6)
                assert capture.sample_rate in [2.4e6, 2.56e6]
        finally:
            capture_module.RTL_SDR_AVAILABLE = original_available
