#!/usr/bin/env python3
"""Test GSM7 decoding with known test vector"""
from tetraear.core.protocol import TetraProtocolParser

parser = TetraProtocolParser()

# Test with known hellohello vector
hex_data = bytes.fromhex("E8329BFD4697D9EC37")
decoded = parser._unpack_gsm7bit(hex_data)
print(f"Test vector E8329BFD4697D9EC37 decodes to: '{decoded}'")
print(f"Expected: 'hellohello'")
print(f"Match: {decoded == 'hellohello'}")

# Try decoding some of the captured payloads
import json
from pathlib import Path

print("\n=== Testing captured unencrypted payloads ===")
frames_file = Path('logs/continuous_20251223_214944.jsonl')

with open(frames_file, 'r', encoding='utf-8') as f:
    count = 0
    for line in f:
        frame = json.loads(line)
        if not frame.get('encrypted', True):
            mac_pdu = frame.get('mac_pdu', {})
            if mac_pdu.get('data'):
                hex_str = mac_pdu['data']
                try:
                    raw_bytes = bytes.fromhex(hex_str)
                    # Try different decoding approaches
                    decoded1 = parser._unpack_gsm7bit(raw_bytes)
                    decoded2 = parser._unpack_gsm7bit_with_udh(raw_bytes)
                    
                    if decoded1 and len(decoded1) > 5:
                        score1 = parser._score_text(decoded1)
                        if score1 > 1.5:
                            print(f"\nFrame {frame.get('number')}: score={score1:.2f}")
                            print(f"  Decoded: {decoded1[:80]}")
                            count += 1
                            if count >= 5:
                                break
                except:
                    pass
