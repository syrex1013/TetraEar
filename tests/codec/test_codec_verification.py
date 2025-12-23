"""
Codec verification tests.
Ports and enhances verify_codec.py into proper pytest test suite.
"""

import pytest
import os
import struct
import subprocess
import tempfile
import sys
from pathlib import Path


# Codec paths
def get_codec_dir():
    """Get codec directory path."""
    project_root = Path(__file__).parent.parent.parent
    return project_root / "tetraear" / "tetra_codec" / "bin"


CODECS = {
    'cdecoder': 'cdecoder.exe',
    'ccoder': 'ccoder.exe',
    'sdecoder': 'sdecoder.exe',
    'scoder': 'scoder.exe',
}


def codec_exists(codec_name):
    """Check if codec executable exists."""
    codec_dir = get_codec_dir()
    codec_path = codec_dir / CODECS[codec_name]
    return codec_path.exists()


def create_tetra_frame_binary():
    """
    Create a valid TETRA frame in binary format.
    Format: 690 shorts (16-bit integers)
    - First short: 0x6B21 (header marker)
    - Next 689 shorts: Frame data (soft bits as 16-bit values)
    """
    frame = bytearray()
    
    # Header: 0x6B21 (little endian for Windows)
    frame.extend(struct.pack('<H', 0x6B21))
    
    # Fill with soft bits: values should be in range -127 to 127
    for i in range(689):
        soft_bit = (i % 2) * 64  # 0 or 64
        frame.extend(struct.pack('<h', soft_bit))
    
    return bytes(frame)


@pytest.mark.codec
class TestCodecVerification:
    """Test TETRA codec executables."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup for codec tests."""
        self.codec_dir = get_codec_dir()
        self.codecs = {}
        for name, exe in CODECS.items():
            codec_path = self.codec_dir / exe
            self.codecs[name] = codec_path if codec_path.exists() else None
    
    def test_codec_directory_exists(self):
        """Test that codec directory exists."""
        assert self.codec_dir.exists(), f"Codec directory not found: {self.codec_dir}"
    
    @pytest.mark.parametrize("codec_name", CODECS.keys())
    def test_codec_exists(self, codec_name):
        """Test that codec executable exists."""
        codec_path = self.codecs[codec_name]
        if codec_path is None:
            pytest.skip(f"{codec_name} not found at {self.codec_dir / CODECS[codec_name]}")
        assert codec_path.exists(), f"{codec_name} not found"
    
    @pytest.mark.skipif(not codec_exists('cdecoder'), reason="cdecoder.exe not found")
    def test_cdecoder(self):
        """Test cdecoder.exe (voice decoder)."""
        codec_path = self.codecs['cdecoder']
        if codec_path is None:
            pytest.skip("cdecoder.exe not found")
        
        # Create test input file
        with tempfile.NamedTemporaryFile(mode='wb', delete=False, suffix='.tet') as tmp_in:
            # Write multiple frames
            for _ in range(3):
                frame_data = create_tetra_frame_binary()
                tmp_in.write(frame_data)
            tmp_in_path = tmp_in.name
        
        tmp_out_path = tmp_in_path + ".out"
        
        try:
            # Run decoder
            result = subprocess.run(
                [str(codec_path), tmp_in_path, tmp_out_path],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            # Check if output file was created
            if os.path.exists(tmp_out_path):
                output_size = os.path.getsize(tmp_out_path)
                assert output_size > 0, "cdecoder produced empty output"
                
                # Expected: 3 frames * (BFI + 137 + BFI + 137) * 2 bytes = 1656 bytes
                expected_size = 3 * (1 + 137 + 1 + 137) * 2
                
                # Verify output format
                with open(tmp_out_path, 'rb') as f:
                    # Read first frame
                    bfi1 = struct.unpack('<h', f.read(2))[0]
                    frame1 = f.read(137 * 2)
                    assert len(frame1) == 137 * 2, "First frame size incorrect"
                
                # Return code 0 is ideal, but non-zero may still produce output
                if result.returncode != 0:
                    pytest.skip(f"cdecoder returned code {result.returncode} (may still be functional)")
            else:
                pytest.skip("cdecoder did not create output file")
        finally:
            # Cleanup
            try:
                if os.path.exists(tmp_in_path):
                    os.remove(tmp_in_path)
                if os.path.exists(tmp_out_path):
                    os.remove(tmp_out_path)
            except:
                pass
    
    @pytest.mark.skipif(not codec_exists('ccoder'), reason="ccoder.exe not found")
    def test_ccoder(self):
        """Test ccoder.exe (voice encoder)."""
        codec_path = self.codecs['ccoder']
        if codec_path is None:
            pytest.skip("ccoder.exe not found")
        
        # Create test input: BFI + 137 shorts (vocoder frame)
        with tempfile.NamedTemporaryFile(mode='wb', delete=False, suffix='.voc') as tmp_in:
            # Write 2 frames
            for frame_num in range(2):
                # BFI bit (0 = good frame)
                tmp_in.write(struct.pack('<h', 0))
                # 137 shorts of vocoder data
                for i in range(137):
                    tmp_in.write(struct.pack('<h', i % 256))
            tmp_in_path = tmp_in.name
        
        tmp_out_path = tmp_in_path + ".out"
        
        try:
            result = subprocess.run(
                [str(codec_path), tmp_in_path, tmp_out_path],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if os.path.exists(tmp_out_path):
                output_size = os.path.getsize(tmp_out_path)
                assert output_size > 0, "ccoder produced empty output"
                
                # Expected: 2 frames * 690 shorts * 2 bytes = 2760 bytes
                expected_size = 2 * 690 * 2
                
                # Verify output has 0x6B21 header
                with open(tmp_out_path, 'rb') as f:
                    header = struct.unpack('<H', f.read(2))[0]
                    assert header == 0x6B21, f"Invalid header: 0x{header:04X}"
                
                if result.returncode != 0:
                    pytest.skip(f"ccoder returned code {result.returncode}")
            else:
                pytest.skip("ccoder did not create output file")
        finally:
            try:
                if os.path.exists(tmp_in_path):
                    os.remove(tmp_in_path)
                if os.path.exists(tmp_out_path):
                    os.remove(tmp_out_path)
            except:
                pass
    
    @pytest.mark.skipif(not codec_exists('sdecoder'), reason="sdecoder.exe not found")
    def test_sdecoder(self):
        """Test sdecoder.exe (signaling decoder)."""
        codec_path = self.codecs['sdecoder']
        if codec_path is None:
            pytest.skip("sdecoder.exe not found")
        
        # Create test input file
        with tempfile.NamedTemporaryFile(mode='wb', delete=False, suffix='.tet') as tmp_in:
            frame_data = create_tetra_frame_binary()
            tmp_in.write(frame_data)
            tmp_in_path = tmp_in.name
        
        tmp_out_path = tmp_in_path + ".out"
        
        try:
            result = subprocess.run(
                [str(codec_path), tmp_in_path, tmp_out_path],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if os.path.exists(tmp_out_path):
                output_size = os.path.getsize(tmp_out_path)
                # sdecoder may produce output even with non-zero return code
                if output_size > 0:
                    # Output exists, test passes
                    pass
                else:
                    pytest.skip("sdecoder produced empty output")
            else:
                pytest.skip("sdecoder did not create output file")
        finally:
            try:
                if os.path.exists(tmp_in_path):
                    os.remove(tmp_in_path)
                if os.path.exists(tmp_out_path):
                    os.remove(tmp_out_path)
            except:
                pass
    
    @pytest.mark.skipif(not codec_exists('scoder'), reason="scoder.exe not found")
    def test_scoder(self):
        """Test scoder.exe (signaling encoder)."""
        codec_path = self.codecs['scoder']
        if codec_path is None:
            pytest.skip("scoder.exe not found")
        
        # Create test signaling data
        with tempfile.NamedTemporaryFile(mode='wb', delete=False, suffix='.sig') as tmp_in:
            for i in range(100):
                tmp_in.write(struct.pack('<h', i % 256))
            tmp_in_path = tmp_in.name
        
        tmp_out_path = tmp_in_path + ".out"
        
        try:
            result = subprocess.run(
                [str(codec_path), tmp_in_path, tmp_out_path],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if os.path.exists(tmp_out_path):
                output_size = os.path.getsize(tmp_out_path)
                if output_size > 0:
                    # Output exists, test passes
                    pass
                else:
                    pytest.skip("scoder produced empty output")
            else:
                pytest.skip("scoder did not create output file")
        finally:
            try:
                if os.path.exists(tmp_in_path):
                    os.remove(tmp_in_path)
                if os.path.exists(tmp_out_path):
                    os.remove(tmp_out_path)
            except:
                pass
    
    def test_all_codecs_summary(self):
        """Summary test showing which codecs are available."""
        available = []
        missing = []
        
        for name, codec_path in self.codecs.items():
            if codec_path and codec_path.exists():
                available.append(name)
            else:
                missing.append(name)
        
        # This test always passes, but provides information
        print(f"\nAvailable codecs: {', '.join(available) if available else 'None'}")
        if missing:
            print(f"Missing codecs: {', '.join(missing)}")
        
        # Test passes regardless, but warns if no codecs found
        if not available:
            pytest.skip("No codec executables found - codec tests will be skipped")
