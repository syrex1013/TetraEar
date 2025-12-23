"""
Unit tests for voice processor module.
"""

import pytest
import numpy as np
import struct
import os
from unittest.mock import patch, MagicMock
from tetraear.audio.voice import VoiceProcessor


@pytest.mark.unit
class TestVoiceProcessor:
    """Test VoiceProcessor class."""
    
    def test_processor_initialization_no_codec(self, tmp_path):
        """Test processor initialization when codec is missing."""
        processor = VoiceProcessor(codec_path=tmp_path / "missing_cdecoder.exe")
        assert processor.working is False
    
    def test_processor_initialization_with_codec(self, mock_codec_path):
        """Test processor initialization when codec exists."""
        processor = VoiceProcessor(codec_path=mock_codec_path / "cdecoder.exe")
        assert processor.working is True
    
    def test_decode_frame_not_working(self):
        """Test decode when codec is not working."""
        processor = VoiceProcessor(codec_path="C:/this/path/does/not/exist.exe")
        result = processor.decode_frame(b'')
        assert len(result) == 0
        assert isinstance(result, np.ndarray)
    
    def test_decode_frame_empty_data(self, tmp_path):
        """Test decode with empty frame data."""
        codec = tmp_path / "cdecoder.exe"
        codec.write_bytes(b"")
        processor = VoiceProcessor(codec_path=codec)
        result = processor.decode_frame(b'')
        assert len(result) == 0
    
    def test_decode_frame_invalid_size(self, tmp_path):
        """Test decode with invalid frame size."""
        codec = tmp_path / "cdecoder.exe"
        codec.write_bytes(b"")
        processor = VoiceProcessor(codec_path=codec)
        invalid_frame = bytes([0x00] * 100)  # Not 1380 bytes
        result = processor.decode_frame(invalid_frame)
        assert len(result) == 0
    
    def test_decode_frame_invalid_header(self, tmp_path):
        """Test decode with invalid header."""
        codec = tmp_path / "cdecoder.exe"
        codec.write_bytes(b"")
        processor = VoiceProcessor(codec_path=codec)
        # Create frame with wrong header
        frame = bytearray()
        frame.extend(struct.pack('<H', 0x0000))  # Wrong header
        frame.extend(bytes([0x00] * 1378))
        result = processor.decode_frame(bytes(frame))
        assert len(result) == 0
    
    def test_decode_frame_valid_format(self, sample_tetra_frame_binary, tmp_path):
        """Test decode with valid frame format."""
        codec = tmp_path / "cdecoder.exe"
        codec.write_bytes(b"")
        processor = VoiceProcessor(codec_path=codec)
        
        # Mock subprocess to avoid actually calling codec
        with patch('tetraear.audio.voice.subprocess.run') as mock_run:
            # Mock successful codec execution
            mock_run.return_value = MagicMock(returncode=0)
            
            # Mock output file
            with patch('tetraear.audio.voice.os.path.exists', return_value=True):
                with patch('tetraear.audio.voice.os.path.getsize', return_value=552):
                    with patch('builtins.open', create=True) as mock_open:
                        # Mock file read - return PCM data
                        pcm_data = bytes([0x00] * 552)
                        mock_file = MagicMock()
                        mock_file.read.return_value = pcm_data
                        mock_open.return_value.__enter__.return_value = mock_file
                        
                        result = processor.decode_frame(sample_tetra_frame_binary)
                        # Should return audio array (may be empty if codec fails)
                        assert isinstance(result, np.ndarray)
    
    def test_decode_frame_codec_failure(self, sample_tetra_frame_binary, tmp_path):
        """Test decode when codec fails."""
        codec = tmp_path / "cdecoder.exe"
        codec.write_bytes(b"")
        processor = VoiceProcessor(codec_path=codec)
        
        with patch('tetraear.audio.voice.subprocess.run') as mock_run:
            # Mock codec failure
            mock_run.return_value = MagicMock(returncode=1)
            
            with patch('tetraear.audio.voice.os.path.exists', return_value=False):
                result = processor.decode_frame(sample_tetra_frame_binary)
                assert len(result) == 0
    
    def test_decode_frame_timeout(self, sample_tetra_frame_binary, tmp_path):
        """Test decode when codec times out."""
        codec = tmp_path / "cdecoder.exe"
        codec.write_bytes(b"")
        processor = VoiceProcessor(codec_path=codec)
        
        with patch('tetraear.audio.voice.subprocess.run') as mock_run:
            import subprocess
            mock_run.side_effect = subprocess.TimeoutExpired('cdecoder', 5)
            
            result = processor.decode_frame(sample_tetra_frame_binary)
            # Should handle timeout gracefully
            assert isinstance(result, np.ndarray)
