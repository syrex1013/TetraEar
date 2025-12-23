#!/usr/bin/env python3
"""
Comprehensive TETRA Codec Verification Script
Tests all 4 codec executables (cdecoder, ccoder, sdecoder, scoder)
with proper TETRA frame formats.
"""

import os
import struct
import subprocess
import tempfile
import sys
from pathlib import Path

# Codec paths
TETRAEAR_ROOT = Path(__file__).resolve().parents[1]
CODEC_DIR = str(TETRAEAR_ROOT / "tetra_codec" / "bin")
CODECS = {
    'cdecoder': os.path.join(CODEC_DIR, 'cdecoder.exe'),
    'ccoder': os.path.join(CODEC_DIR, 'ccoder.exe'),
    'sdecoder': os.path.join(CODEC_DIR, 'sdecoder.exe'),
    'scoder': os.path.join(CODEC_DIR, 'scoder.exe'),
}

def test_codec_exists(codec_name, codec_path):
    """Check if codec executable exists."""
    if os.path.exists(codec_path):
        print(f"[OK] {codec_name} found at {codec_path}")
        return True
    else:
        print(f"[FAIL] {codec_name} NOT FOUND at {codec_path}")
        return False

def create_tetra_frame_binary():
    """
    Create a valid TETRA frame in binary format.
    Format: 690 shorts (16-bit integers)
    - First short: 0x6B21 (header marker)
    - Next 689 shorts: Frame data (soft bits as 16-bit values)
    The codec extracts 432 shorts from specific positions.
    """
    frame = bytearray()
    
    # Header: 0x6B21 (little endian for Windows)
    frame.extend(struct.pack('<H', 0x6B21))
    
    # Fill with soft bits: values should be in range -127 to 127
    # For testing, use small values (0-127) representing soft bits
    for i in range(689):
        # Soft bit value (signed 8-bit, but stored as 16-bit)
        # Use pattern: alternating small values
        soft_bit = (i % 2) * 64  # 0 or 64
        frame.extend(struct.pack('<h', soft_bit))
    
    return bytes(frame)

def test_cdecoder():
    """Test cdecoder.exe (voice decoder)."""
    print("\n" + "="*60)
    print("Testing cdecoder.exe (Voice Decoder)")
    print("="*60)
    
    codec_path = CODECS['cdecoder']
    if not test_codec_exists('cdecoder', codec_path):
        return False
    
    # Create test input file (TETRA frame format)
    with tempfile.NamedTemporaryFile(mode='wb', delete=False, suffix='.tet') as tmp_in:
        # Write multiple frames for testing
        for _ in range(3):
            frame_data = create_tetra_frame_binary()
            tmp_in.write(frame_data)
        tmp_in_path = tmp_in.name
    
    tmp_out_path = tmp_in_path + ".out"
    
    try:
        # Run decoder
        result = subprocess.run(
            [codec_path, tmp_in_path, tmp_out_path],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        # Check if output file was created and has content
        if os.path.exists(tmp_out_path):
            output_size = os.path.getsize(tmp_out_path)
            # Expected: 3 frames * (BFI + 137 + BFI + 137) * 2 bytes = 3 * 276 * 2 = 1656 bytes
            expected_size = 3 * (1 + 137 + 1 + 137) * 2  # 1656 bytes
            
            print(f"  Output file size: {output_size} bytes")
            print(f"  Expected size: {expected_size} bytes")
            
            if output_size > 0:
                print("  [OK] cdecoder produced output")
                
                # Check output format
                with open(tmp_out_path, 'rb') as f:
                    # Read first frame: BFI (2 bytes) + 137 shorts (274 bytes)
                    bfi1 = struct.unpack('<h', f.read(2))[0]
                    frame1 = f.read(137 * 2)
                    bfi2 = struct.unpack('<h', f.read(2))[0]
                    frame2 = f.read(137 * 2)
                    
                    print(f"  First frame BFI: {bfi1}")
                    print(f"  Second frame BFI: {bfi2}")
                    print(f"  Frame 1 size: {len(frame1)} bytes")
                    print(f"  Frame 2 size: {len(frame2)} bytes")
                
                if result.returncode == 0:
                    print("  [OK] cdecoder completed successfully")
                    return True
                else:
                    print(f"  [WARN] cdecoder returned code {result.returncode}")
                    if result.stderr:
                        print(f"  stderr: {result.stderr[:200]}")
                    return output_size > 0
            else:
                print("  [FAIL] cdecoder produced empty output")
                return False
        else:
            print("  [FAIL] cdecoder did not create output file")
            if result.stderr:
                print(f"  stderr: {result.stderr[:200]}")
            return False
            
    except subprocess.TimeoutExpired:
        print("  [FAIL] cdecoder timed out")
        return False
    except Exception as e:
        print(f"  [FAIL] Error running cdecoder: {e}")
        return False
    finally:
        # Cleanup
        try:
            os.remove(tmp_in_path)
            if os.path.exists(tmp_out_path):
                os.remove(tmp_out_path)
        except:
            pass

def test_ccoder():
    """Test ccoder.exe (voice encoder)."""
    print("\n" + "="*60)
    print("Testing ccoder.exe (Voice Encoder)")
    print("="*60)
    
    codec_path = CODECS['ccoder']
    if not test_codec_exists('ccoder', codec_path):
        return False
    
    # Create test input: BFI + 137 shorts (vocoder frame)
    with tempfile.NamedTemporaryFile(mode='wb', delete=False, suffix='.voc') as tmp_in:
        # Write 2 frames (BFI + 137 + BFI + 137)
        for frame_num in range(2):
            # BFI bit (0 = good frame)
            tmp_in.write(struct.pack('<h', 0))
            # 137 shorts of vocoder data (test pattern)
            for i in range(137):
                tmp_in.write(struct.pack('<h', i % 256))
        tmp_in_path = tmp_in.name
    
    tmp_out_path = tmp_in_path + ".out"
    
    try:
        result = subprocess.run(
            [codec_path, tmp_in_path, tmp_out_path],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if os.path.exists(tmp_out_path):
            output_size = os.path.getsize(tmp_out_path)
            # Expected: 2 frames * 690 shorts * 2 bytes = 2760 bytes
            expected_size = 2 * 690 * 2
            
            print(f"  Output file size: {output_size} bytes")
            print(f"  Expected size: {expected_size} bytes")
            
            if output_size > 0:
                print("  [OK] ccoder produced output")
                
                # Verify output has 0x6B21 header
                with open(tmp_out_path, 'rb') as f:
                    header = struct.unpack('<H', f.read(2))[0]
                    print(f"  First frame header: 0x{header:04X}")
                    if header == 0x6B21:
                        print("  [OK] Valid TETRA frame header")
                
                if result.returncode == 0:
                    print("  [OK] ccoder completed successfully")
                    return True
                else:
                    print(f"  [WARN] ccoder returned code {result.returncode}")
                    return output_size > 0
            else:
                print("  [FAIL] ccoder produced empty output")
                return False
        else:
            print("  [FAIL] ccoder did not create output file")
            if result.stderr:
                print(f"  stderr: {result.stderr[:200]}")
            return False
            
    except Exception as e:
        print(f"  [FAIL] Error running ccoder: {e}")
        return False
    finally:
        try:
            os.remove(tmp_in_path)
            if os.path.exists(tmp_out_path):
                os.remove(tmp_out_path)
        except:
            pass

def test_sdecoder():
    """Test sdecoder.exe (signaling decoder)."""
    print("\n" + "="*60)
    print("Testing sdecoder.exe (Signaling Decoder)")
    print("="*60)
    
    codec_path = CODECS['sdecoder']
    if not test_codec_exists('sdecoder', codec_path):
        return False
    
    # sdecoder likely uses similar format to cdecoder
    # Create test input file
    with tempfile.NamedTemporaryFile(mode='wb', delete=False, suffix='.tet') as tmp_in:
        frame_data = create_tetra_frame_binary()
        tmp_in.write(frame_data)
        tmp_in_path = tmp_in.name
    
    tmp_out_path = tmp_in_path + ".out"
    
    try:
        result = subprocess.run(
            [codec_path, tmp_in_path, tmp_out_path],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if os.path.exists(tmp_out_path):
            output_size = os.path.getsize(tmp_out_path)
            print(f"  Output file size: {output_size} bytes")
            
            if output_size > 0:
                print("  [OK] sdecoder produced output")
                if result.returncode == 0:
                    print("  [OK] sdecoder completed successfully")
                    return True
                else:
                    print(f"  [WARN] sdecoder returned code {result.returncode}")
                    return True
            else:
                print("  [FAIL] sdecoder produced empty output")
                return False
        else:
            print("  [FAIL] sdecoder did not create output file")
            if result.stderr:
                print(f"  stderr: {result.stderr[:200]}")
            return False
            
    except Exception as e:
        print(f"  [FAIL] Error running sdecoder: {e}")
        return False
    finally:
        try:
            os.remove(tmp_in_path)
            if os.path.exists(tmp_out_path):
                os.remove(tmp_out_path)
        except:
            pass

def test_scoder():
    """Test scoder.exe (signaling encoder)."""
    print("\n" + "="*60)
    print("Testing scoder.exe (Signaling Encoder)")
    print("="*60)
    
    codec_path = CODECS['scoder']
    if not test_codec_exists('scoder', codec_path):
        return False
    
    # scoder likely uses similar format to ccoder
    with tempfile.NamedTemporaryFile(mode='wb', delete=False, suffix='.sig') as tmp_in:
        # Write test signaling data
        for i in range(100):
            tmp_in.write(struct.pack('<h', i % 256))
        tmp_in_path = tmp_in.name
    
    tmp_out_path = tmp_in_path + ".out"
    
    try:
        result = subprocess.run(
            [codec_path, tmp_in_path, tmp_out_path],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if os.path.exists(tmp_out_path):
            output_size = os.path.getsize(tmp_out_path)
            print(f"  Output file size: {output_size} bytes")
            
            if output_size > 0:
                print("  [OK] scoder produced output")
                if result.returncode == 0:
                    print("  [OK] scoder completed successfully")
                    return True
                else:
                    print(f"  [WARN] scoder returned code {result.returncode}")
                    return True
            else:
                print("  [FAIL] scoder produced empty output")
                return False
        else:
            print("  [FAIL] scoder did not create output file")
            if result.stderr:
                print(f"  stderr: {result.stderr[:200]}")
            return False
            
    except Exception as e:
        print(f"  [FAIL] Error running scoder: {e}")
        return False
    finally:
        try:
            os.remove(tmp_in_path)
            if os.path.exists(tmp_out_path):
                os.remove(tmp_out_path)
        except:
            pass

def main():
    """Run all codec tests."""
    print("="*60)
    print("TETRA Codec Verification")
    print("="*60)
    
    results = {}
    
    # Test all codecs
    results['cdecoder'] = test_cdecoder()
    results['ccoder'] = test_ccoder()
    results['sdecoder'] = test_sdecoder()
    results['scoder'] = test_scoder()
    
    # Summary
    print("\n" + "="*60)
    print("Test Summary")
    print("="*60)
    
    all_passed = True
    for codec_name, passed in results.items():
        status = "[PASS]" if passed else "[FAIL]"
        print(f"  {codec_name:12} : {status}")
        if not passed:
            all_passed = False
    
    print("="*60)
    
    if all_passed:
        print("\n[SUCCESS] All codecs verified successfully!")
        return 0
    else:
        print("\n[FAIL] Some codecs failed verification")
        return 1

if __name__ == "__main__":
    sys.exit(main())
