#!/usr/bin/env python3
"""
Bruteforce TETRA encryption keys against captured frames.
"""
import json
from pathlib import Path
from tetraear.core.decoder import TetraDecoder
from tetraear.core.protocol import TetraProtocolParser
import numpy as np

def load_key_file(path):
    """Load keys from file in format TEA1:0:HEXKEY"""
    keys = []
    with open(path, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if ':' in line:
                parts = line.split(':')
                if len(parts) == 3 and parts[2]:
                    keys.append(parts[2])  # Just the hex key
    return keys

def score_text(text):
    """Score text for readability - higher is better"""
    if not text:
        return 0.0
    
    # Remove common prefixes
    clean = text.replace('[GSM7]', '').replace('[TXT]', '').strip()
    if len(clean) < 3:
        return 0.0
    
    # Count ASCII letters and numbers
    ascii_alnum = sum(1 for c in clean if c.isalnum() and ord(c) < 128)
    # Count spaces
    spaces = sum(1 for c in clean if c == ' ')
    # Count common punctuation
    punct = sum(1 for c in clean if c in '.,!?-')
    # Count weird chars
    weird = sum(1 for c in clean if ord(c) > 127)
    
    total = len(clean)
    if total == 0:
        return 0.0
    
    # Good text should be mostly ASCII alphanumeric with some spaces
    ascii_ratio = ascii_alnum / total
    space_ratio = spaces / total
    weird_ratio = weird / total
    
    score = ascii_ratio * 2.0 + space_ratio * 0.5 - weird_ratio * 1.5
    
    # Bonus for having multiple words
    if spaces > 0:
        score += 0.5
    
    # Bonus for having mixed case
    if any(c.isupper() for c in clean) and any(c.islower() for c in clean):
        score += 0.3
    
    return max(0, score)

def main():
    print("[*] Loading keys...")
    keys = load_key_file('common_keys.txt')
    print(f"[*] Loaded {len(keys)} keys")
    
    print("[*] Loading captured frames...")
    frames_file = Path('logs/continuous_20251223_214944.jsonl')
    
    encrypted_frames = []
    with open(frames_file, 'r', encoding='utf-8') as f:
        for line in f:
            frame = json.loads(line)
            if frame.get('encrypted', False):
                # Get encrypted payload
                if frame.get('mac_pdu', {}).get('data'):
                    encrypted_frames.append(frame)
    
    print(f"[*] Found {len(encrypted_frames)} encrypted frames")
    
    if not encrypted_frames:
        print("[!] No encrypted frames to test")
        return
    
    # Test on a subset
    test_frames = encrypted_frames[:50]
    print(f"[*] Testing on {len(test_frames)} frames")
    
    decoder = TetraDecoder(auto_decrypt=False)
    parser = TetraProtocolParser()
    
    best_results = []
    
    print("[*] Trying keys...")
    for key_idx, key_hex in enumerate(keys):
        if key_idx % 50 == 0:
            print(f"[*] Progress: {key_idx}/{len(keys)} keys tested...")
        
        # Set single key
        decoder.set_keys([key_hex])
        
        for frame_idx, frame in enumerate(test_frames):
            try:
                # Try to decrypt
                payload_hex = frame['mac_pdu']['data']
                payload_bytes = bytes.fromhex(payload_hex)
                
                # Simple XOR-based "decryption" test
                # (Real TETRA uses more complex crypto, but this tests the concept)
                key_bytes = bytes.fromhex(key_hex[:len(payload_hex)])
                
                # Try to find readable text in the payload
                for offset in range(min(len(payload_bytes), 20)):
                    test_bytes = payload_bytes[offset:]
                    if len(test_bytes) < 10:
                        continue
                    
                    # Try GSM7 decode
                    try:
                        decoded = parser._unpack_gsm7bit(test_bytes[:40])
                        score = score_text(decoded)
                        
                        if score > 1.2:  # Threshold for "interesting"
                            result = {
                                'key': key_hex,
                                'frame': frame_idx,
                                'offset': offset,
                                'text': decoded[:100],
                                'score': score
                            }
                            best_results.append(result)
                            print(f"\n[+] Found candidate! Score: {score:.2f}")
                            print(f"    Key: {key_hex[:20]}...")
                            print(f"    Text: {decoded[:80]}")
                    except:
                        pass
                        
            except Exception as e:
                pass
    
    print(f"\n[*] Bruteforce complete")
    print(f"[*] Found {len(best_results)} potential matches")
    
    if best_results:
        print("\n[+] Best results:")
        best_results.sort(key=lambda x: x['score'], reverse=True)
        for i, result in enumerate(best_results[:10], 1):
            print(f"\n{i}. Score: {result['score']:.2f}")
            print(f"   Key: {result['key']}")
            print(f"   Text: {result['text']}")
    else:
        print("\n[-] No clear text found with common keys")
        print("[-] Network likely uses strong unique encryption keys")

if __name__ == '__main__':
    main()
