#!/usr/bin/env python3
"""
Test common keys against encrypted frames using the decoder's decryption.
"""
import json
from pathlib import Path
import numpy as np

def load_keys_raw(path):
    """Load raw hex keys from file"""
    keys = []
    with open(path, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if ':' in line:
                parts = line.split(':')
                if len(parts) == 3:
                    keys.append(parts[2].strip())
    return keys

def score_text(text):
    """Score text quality - higher = more readable"""
    if not text:
        return 0.0
    
    clean = text.replace('[GSM7]', '').replace('[TXT]', '').replace('[BIN', '').strip()
    if len(clean) < 4:
        return 0.0
    
    # Count ASCII alphanumeric
    ascii_alnum = sum(1 for c in clean if 32 <= ord(c) < 127 and (c.isalnum() or c in ' .,!?-'))
    # Count high-byte chars (likely encrypted)
    high_chars = sum(1 for c in clean if ord(c) > 127)
    
    total = len(clean)
    ascii_ratio = ascii_alnum / total
    high_ratio = high_chars / total
    
    # Good text = high ASCII ratio, low high-byte ratio
    score = ascii_ratio * 3.0 - high_ratio * 2.0
    
    # Bonus for spaces (multi-word)
    if ' ' in clean and clean.count(' ') > 0:
        score += 1.0
    
    # Penalty for too many @'s (common in bad decryptions)
    at_count = clean.count('@')
    if at_count > len(clean) * 0.3:
        score -= 1.0
    
    return max(0, score)

def main():
    print("[*] Loading keys...")
    keys_raw = load_keys_raw('common_keys.txt')
    # Fix odd-length keys
    keys = [k if len(k) % 2 == 0 else k + '0' for k in keys_raw]
    print(f"[*] Loaded {len(keys)} keys")
    
    print("[*] Loading frames with existing decryption attempts...")
    frames_file = Path('logs/continuous_20251223_214944.jsonl')
    
    encrypted_with_attempts = []
    with open(frames_file, 'r', encoding='utf-8') as f:
        for line in f:
            frame = json.loads(line)
            # Look for frames that were decrypted but still garbled
            if frame.get('decrypted') and frame.get('best_key'):
                text = frame.get('decoded_text', '') or frame.get('sds_message', '')
                if text:
                    encrypted_with_attempts.append(frame)
    
    print(f"[*] Found {len(encrypted_with_attempts)} frames with decryption attempts")
    
    if len(encrypted_with_attempts) < 10:
        print("[!] Not enough test data, loading all encrypted frames...")
        with open(frames_file, 'r', encoding='utf-8') as f:
            for line in f:
                frame = json.loads(line)
                if frame.get('encrypted'):
                    encrypted_with_attempts.append(frame)
    
    test_frames = encrypted_with_attempts[:20]
    print(f"[*] Testing {len(test_frames)} frames")
    
    print("\n[*] Analyzing already-attempted decryptions...")
    best_existing = []
    for frame in test_frames:
        text = frame.get('decoded_text', '') or frame.get('sds_message', '')
        if text:
            score = score_text(text)
            if score > 0.5:
                best_existing.append({
                    'text': text[:100],
                    'score': score,
                    'key': frame.get('best_key', 'unknown'),
                    'confidence': frame.get('decrypt_confidence', 0)
                })
    
    if best_existing:
        print(f"\n[+] Found {len(best_existing)} potentially readable decryptions")
        best_existing.sort(key=lambda x: x['score'], reverse=True)
        for i, result in enumerate(best_existing[:15], 1):
            print(f"\n{i}. Score: {result['score']:.2f}, Confidence: {result['confidence']}")
            print(f"   Key: {result['key']}")
            print(f"   Text: {result['text']}")
    else:
        print("\n[-] No readable decryptions found")
        print("[-] Showing sample of what we got:")
        for i, frame in enumerate(test_frames[:5], 1):
            text = frame.get('decoded_text', '') or frame.get('sds_message', '')
            print(f"\n{i}. Algorithm: {frame.get('encryption_algorithm')}")
            print(f"   Best key: {frame.get('best_key')}")
            print(f"   Text: {text[:80]}")

if __name__ == '__main__':
    main()
