#!/usr/bin/env python3
"""
Generate common TETRA encryption keys for testing.
Includes known weak keys, test vectors, and common patterns.
"""

keys = []

# Common test keys
keys.append("TEA1:0:00000000000000000000")
keys.append("TEA1:0:11111111111111111111")
keys.append("TEA1:0:FFFFFFFFFFFFFFFF1111")
keys.append("TEA1:0:AAAAAAAAAAAAAAAAAAA0")
keys.append("TEA1:0:12345678901234567890")

keys.append("TEA2:0:00000000000000000000000000000000")
keys.append("TEA2:0:11111111111111111111111111111111")
keys.append("TEA2:0:FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF")
keys.append("TEA2:0:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA")
keys.append("TEA2:0:12345678901234567890123456789012")

keys.append("TEA3:0:00000000000000000000000000000000")
keys.append("TEA3:0:11111111111111111111111111111111")
keys.append("TEA3:0:FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF")
keys.append("TEA3:0:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA")
keys.append("TEA3:0:12345678901234567890123456789012")

# Known public safety / emergency patterns
for i in range(10):
    keys.append(f"TEA1:0:{i:020X}")
    keys.append(f"TEA2:0:{i:032X}")
    keys.append(f"TEA3:0:{i:032X}")

# Repeating patterns
for byte_val in ["00", "11", "22", "33", "44", "55", "66", "77", "88", "99", "AA", "BB", "CC", "DD", "EE", "FF"]:
    keys.append(f"TEA1:0:{byte_val * 10}")
    keys.append(f"TEA2:0:{byte_val * 16}")
    keys.append(f"TEA3:0:{byte_val * 16}")

# Sequential patterns
keys.append("TEA1:0:0123456789ABCDEF0123")
keys.append("TEA2:0:0123456789ABCDEF0123456789ABCDEF")
keys.append("TEA3:0:0123456789ABCDEF0123456789ABCDEF")
keys.append("TEA1:0:FEDCBA9876543210FEDC")
keys.append("TEA2:0:FEDCBA9876543210FEDCBA9876543210")
keys.append("TEA3:0:FEDCBA9876543210FEDCBA9876543210")

# Weak keys with low hamming weight
for i in [0x1, 0x3, 0x7, 0xF, 0x1F, 0x3F, 0x7F, 0xFF, 0x1FF, 0x3FF]:
    keys.append(f"TEA1:0:{i:020X}")
    keys.append(f"TEA2:0:{i:032X}")
    keys.append(f"TEA3:0:{i:032X}")

# Common default patterns (DEAD, BEEF, CAFE, etc.)
common_words = ["DEADBEEF", "CAFEBABE", "BAADF00D", "FEEDFACE", "C0FFEE00"]
for word in common_words:
    # Repeat to fill key length
    tea1_key = (word * 3)[:20]
    tea2_key = (word * 5)[:32]
    keys.append(f"TEA1:0:{tea1_key}")
    keys.append(f"TEA2:0:{tea2_key}")
    keys.append(f"TEA3:0:{tea2_key}")

# MCC/MNC based keys (some networks use these)
# Common European MCCs
mccs = ["262", "222", "240", "228", "214"]  # Germany, Italy, Sweden, Switzerland, Spain
for mcc in mccs:
    for mnc in range(10):
        key_base = f"{mcc}{mnc:02d}"
        keys.append(f"TEA1:0:{key_base}{'0' * 14}")
        keys.append(f"TEA2:0:{key_base}{'0' * 26}")

print(f"# Generated {len(keys)} common TETRA encryption keys")
print(f"# Use with: decoder.set_keys([key_hex])")
print()
for key in keys:
    print(key)
