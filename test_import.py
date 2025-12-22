"""
Test script to verify all modules can be imported.
This helps identify any missing dependencies.
"""

import sys
import os
from pathlib import Path

# Add current directory to PATH for DLL loading
current_dir = Path(__file__).parent.absolute()
os.environ['PATH'] = str(current_dir) + os.pathsep + os.environ.get('PATH', '')

print("Testing module imports...")
print(f"Current directory: {current_dir}")
print(f"PATH includes: {current_dir}\n")

try:
    print("1. Testing numpy...")
    import numpy as np
    print("   [OK] numpy imported")
except ImportError as e:
    print(f"   [FAIL] numpy failed: {e}")
    sys.exit(1)

try:
    print("2. Testing scipy...")
    import scipy
    print("   [OK] scipy imported")
except ImportError as e:
    print(f"   [FAIL] scipy failed: {e}")
    sys.exit(1)

try:
    print("3. Testing bitstring...")
    import bitstring
    print("   [OK] bitstring imported")
except ImportError as e:
    print(f"   [FAIL] bitstring failed: {e}")
    sys.exit(1)

try:
    print("4. Testing rtlsdr...")
    from rtlsdr import RtlSdr
    print("   [OK] rtlsdr imported")
except ImportError as e:
    print(f"   [FAIL] rtlsdr failed: {e}")
    print("   Note: This requires librtlsdr.dll and its dependencies")
    print("   Make sure librtlsdr.dll is in the current directory or PATH")
    sys.exit(1)

try:
    print("5. Testing signal_processor...")
    import signal_processor
    print("   [OK] signal_processor imported")
except ImportError as e:
    print(f"   [FAIL] signal_processor failed: {e}")
    sys.exit(1)

try:
    print("6. Testing tetra_decoder...")
    import tetra_decoder
    print("   [OK] tetra_decoder imported")
except ImportError as e:
    print(f"   [FAIL] tetra_decoder failed: {e}")
    sys.exit(1)

try:
    print("7. Testing tetra_crypto...")
    import tetra_crypto
    print("   [OK] tetra_crypto imported")
except ImportError as e:
    print(f"   [FAIL] tetra_crypto failed: {e}")
    sys.exit(1)

try:
    print("8. Testing frequency_scanner...")
    import frequency_scanner
    print("   [OK] frequency_scanner imported")
except ImportError as e:
    print(f"   [FAIL] frequency_scanner failed: {e}")
    sys.exit(1)

try:
    print("9. Testing rtl_capture...")
    import rtl_capture
    print("   [OK] rtl_capture imported")
except ImportError as e:
    print(f"   [FAIL] rtl_capture failed: {e}")
    sys.exit(1)

print("\n" + "="*50)
print("All modules imported successfully!")
print("="*50)
