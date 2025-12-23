#!/usr/bin/env python3
"""
Capture with auto-decryption using common keys.
"""
import json
import time
import wave
from datetime import datetime
from pathlib import Path
import numpy as np

from tetraear.signal.capture import RTLCapture
from tetraear.signal.processor import SignalProcessor
from tetraear.core.decoder import TetraDecoder
from tetraear.audio.voice import VoiceProcessor

def load_keys(path):
    """Load keys from file"""
    keys = []
    with open(path, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if ':' in line:
                parts = line.split(':')
                if len(parts) == 3:
                    key_hex = parts[2].strip()
                    # Fix odd-length keys
                    if len(key_hex) % 2 == 1:
                        key_hex += '0'
                    keys.append(key_hex)
    return keys

def score_text(text):
    """Score text readability"""
    if not text or len(text) < 4:
        return 0.0
    
    clean = text.replace('[GSM7]', '').replace('[TXT]', '').strip()
    if not clean:
        return 0.0
    
    # ASCII alphanumeric + space
    good = sum(1 for c in clean if 32 <= ord(c) < 127 and (c.isalnum() or c in ' .,!?-'))
    # High-byte chars
    bad = sum(1 for c in clean if ord(c) > 127)
    
    total = len(clean)
    score = (good / total) * 3.0 - (bad / total) * 2.0
    
    # Bonus for spaces
    if ' ' in clean:
        score += 1.0
    
    # Penalty for too many @
    if clean.count('@') > total * 0.3:
        score -= 1.0
    
    return max(0, score)

def main():
    frequency_hz = 392.241e6
    sample_rate_hz = 2.4e6
    chunk_size = 256 * 1024
    
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    frames_log = log_dir / f"decrypt_{run_id}.jsonl"
    found_log = log_dir / f"readable_{run_id}.txt"
    
    print("[*] Loading common keys...")
    keys = load_keys('common_keys.txt')
    print(f"[*] Loaded {len(keys)} keys")
    
    capture = RTLCapture(frequency=frequency_hz, sample_rate=sample_rate_hz, gain="auto")
    if not capture.open():
        print("[FAIL] Could not open RTL-SDR")
        return 1
    
    decoder = TetraDecoder(auto_decrypt=True)
    decoder.set_keys(keys)
    print(f"[*] Set {len(keys)} decryption keys")
    
    processor = SignalProcessor(sample_rate=sample_rate_hz)
    
    print(f"[INFO] Capturing at 392.241 MHz with auto-decryption")
    print(f"[INFO] Frames log: {frames_log}")
    print(f"[INFO] Press Ctrl+C to stop\n")
    
    frame_count = 0
    encrypted_count = 0
    decrypted_count = 0
    readable_count = 0
    best_score = 0.0
    
    with frames_log.open("w", encoding="utf-8") as fp, found_log.open("w", encoding="utf-8") as found_fp:
        try:
            while True:
                samples = capture.read_samples(chunk_size)
                demodulated = processor.process(samples)
                if demodulated is None or len(demodulated) < 255:
                    continue
                
                frames = decoder.decode(demodulated)
                if not frames:
                    continue
                
                for frame in frames:
                    frame_count += 1
                    
                    # Log frame
                    def convert_value(v):
                        if isinstance(v, np.ndarray):
                            return v.tolist()
                        elif isinstance(v, (np.bool_, np.integer)):
                            return int(v)
                        elif isinstance(v, np.floating):
                            return float(v)
                        elif isinstance(v, bytes):
                            return v.hex()
                        elif isinstance(v, dict):
                            return {k: convert_value(val) for k, val in v.items()}
                        elif isinstance(v, list):
                            return [convert_value(item) for item in v]
                        return v
                    
                    serializable = {k: convert_value(v) for k, v in frame.items()}
                    fp.write(json.dumps(serializable, ensure_ascii=False) + "\n")
                    fp.flush()
                    
                    # Check encryption status
                    if frame.get("encrypted"):
                        encrypted_count += 1
                        
                        if frame.get("decrypted"):
                            decrypted_count += 1
                            text = frame.get('decoded_text', '') or frame.get('sds_message', '')
                            
                            if text:
                                score = score_text(text)
                                
                                if score > 2.0:  # Looks readable!
                                    readable_count += 1
                                    print(f"\n[READABLE!] Frame {frame_count}, Score: {score:.2f}")
                                    print(f"  Algorithm: {frame.get('encryption_algorithm')}")
                                    print(f"  Key: {frame.get('best_key')}")
                                    print(f"  Confidence: {frame.get('decrypt_confidence')}")
                                    print(f"  Text: {text[:100]}")
                                    
                                    found_fp.write(f"\n{'='*70}\n")
                                    found_fp.write(f"Frame: {frame_count}, Score: {score:.2f}\n")
                                    found_fp.write(f"Algorithm: {frame.get('encryption_algorithm')}\n")
                                    found_fp.write(f"Key: {frame.get('best_key')}\n")
                                    found_fp.write(f"Confidence: {frame.get('decrypt_confidence')}\n")
                                    found_fp.write(f"Text: {text}\n")
                                    found_fp.flush()
                                    
                                if score > best_score:
                                    best_score = score
                    
                    if frame_count % 200 == 0:
                        print(f"[STATUS] Frames: {frame_count}, Encrypted: {encrypted_count}, "
                              f"Decrypted: {decrypted_count}, Readable: {readable_count}, "
                              f"Best score: {best_score:.2f}")
        
        except KeyboardInterrupt:
            print(f"\n[DONE] Captured {frame_count} frames")
            print(f"  Encrypted: {encrypted_count}")
            print(f"  Successfully decrypted: {decrypted_count}")
            print(f"  Readable text: {readable_count}")
            print(f"  Best score: {best_score:.2f}")
    
    capture.close()
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
