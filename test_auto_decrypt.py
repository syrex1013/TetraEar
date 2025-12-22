"""
Test auto-decryption functionality.
"""

import logging
from tetra_decoder import TetraDecoder
from tetra_crypto import TetraKeyManager

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

print("="*60)
print("TETRA AUTO-DECRYPTION TEST")
print("="*60)

# Test 1: Decoder with auto-decrypt enabled (default)
print("\n1. Testing decoder with auto-decrypt ENABLED")
decoder_auto = TetraDecoder(auto_decrypt=True)
print(f"   Common keys loaded: TEA1={len(decoder_auto.common_keys['TEA1'])}, TEA2={len(decoder_auto.common_keys['TEA2'])}")

# Test 2: Decoder with auto-decrypt disabled
print("\n2. Testing decoder with auto-decrypt DISABLED")
decoder_no_auto = TetraDecoder(auto_decrypt=False)
print(f"   Auto-decrypt: {decoder_no_auto.auto_decrypt}")

# Test 3: Decoder with key manager and auto-decrypt
print("\n3. Testing decoder with key manager + auto-decrypt")
key_manager = TetraKeyManager()
# Add a test key
test_key_tea1 = bytes.fromhex('0123456789ABCDEF0123')
key_manager.add_key('TEA1', '0', test_key_tea1)
print(f"   Added key: TEA1:0")

decoder_with_keys = TetraDecoder(key_manager=key_manager, auto_decrypt=True)
print(f"   Key manager has TEA1:0: {decoder_with_keys.key_manager.has_key('TEA1', '0')}")
print(f"   Auto-decrypt enabled: {decoder_with_keys.auto_decrypt}")

print("\n" + "="*60)
print("TEST COMPLETE")
print("="*60)
print("\nAuto-decryption is now enabled by default!")
print("\nUsage:")
print("  python tetra_decoder_main.py --scan-poland")
print("    → Scans and auto-decrypts with common keys")
print()
print("  python tetra_decoder_main.py --scan-poland -k keys.txt")
print("    → Scans and tries keys from file FIRST, then common keys")
print()
print("  python tetra_decoder_main.py --scan-poland --no-auto-decrypt")
print("    → Scans but only decrypts if keys.txt provided")
print()
