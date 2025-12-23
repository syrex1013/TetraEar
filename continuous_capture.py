#!/usr/bin/env python3
"""
Continuous TETRA capture looking specifically for unencrypted frames and voice.
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

def main():
    frequency_hz = 392.241e6
    sample_rate_hz = 2.4e6
    chunk_size = 256 * 1024
    
    log_dir = Path("logs")
    records_dir = Path("records")
    log_dir.mkdir(exist_ok=True)
    records_dir.mkdir(exist_ok=True)
    
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    frames_log = log_dir / f"continuous_{run_id}.jsonl"
    
    capture = RTLCapture(frequency=frequency_hz, sample_rate=sample_rate_hz, gain="auto")
    if not capture.open():
        print("[FAIL] Could not open RTL-SDR")
        return 1
    
    decoder = TetraDecoder(auto_decrypt=False)  # Don't try decryption
    processor = SignalProcessor(sample_rate=sample_rate_hz)
    voice = VoiceProcessor()
    
    print(f"[INFO] Continuous capture at 392.241 MHz")
    print(f"[INFO] Frames log: {frames_log}")
    print(f"[INFO] Looking for unencrypted frames and voice...")
    print("[INFO] Press Ctrl+C to stop")
    
    frame_count = 0
    unencrypted_count = 0
    voice_count = 0
    
    with frames_log.open("w", encoding="utf-8") as fp:
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
                    
                    # Check if unencrypted
                    encrypted_flag = frame.get("encrypted", True)
                    if not encrypted_flag:
                        unencrypted_count += 1
                        text = frame.get('decoded_text', '') or frame.get('sds_message', '')
                        # Try to identify truly readable text
                        if text and not text.startswith('[BIN'):
                            clean = text.replace('[GSM7]', '').replace('[LOC]', '').strip()
                            # Check for common readable patterns
                            alpha_count = sum(1 for c in clean if c.isalpha() and ord(c) < 128)
                            if alpha_count > 3:
                                print(f"[READABLE!] Frame {frame_count}: {text[:100]}")
                            else:
                                print(f"[UNENCRYPTED] Frame {frame_count}: type={frame.get('type_name')}, text={text[:50]}")
                        else:
                            print(f"[UNENCRYPTED] Frame {frame_count}: type={frame.get('type_name')}, no text")
                    
                    # Try voice decode on every frame with bits
                    bits = frame.get("bits")
                    if bits is not None and len(bits) >= 432 and voice.working:
                        soft_bits = [127 if int(b) else -127 for b in bits[:432]]
                        block = [0] * 690
                        block[0] = 0x6B21
                        idx = 0
                        for i in range(1, 115):
                            if idx < len(soft_bits):
                                block[i] = soft_bits[idx]
                                idx += 1
                        for i in range(116, 230):
                            if idx < len(soft_bits):
                                block[i] = soft_bits[idx]
                                idx += 1
                        for i in range(231, 345):
                            if idx < len(soft_bits):
                                block[i] = soft_bits[idx]
                                idx += 1
                        for i in range(346, 436):
                            if idx < len(soft_bits):
                                block[i] = soft_bits[idx]
                                idx += 1
                        
                        codec_input = np.array(block, dtype=np.int16).tobytes()
                        audio = voice.decode_frame(codec_input)
                        
                        if audio.size > 0 and float(np.max(np.abs(audio))) > 1e-4:
                            voice_count += 1
                            voice_file = records_dir / f"voice_{run_id}_{voice_count:04d}.wav"
                            audio_i16 = np.clip(audio * 32767.0, -32768, 32767).astype(np.int16)
                            with wave.open(str(voice_file), 'wb') as wf:
                                wf.setnchannels(1)
                                wf.setsampwidth(2)
                                wf.setframerate(8000)
                                wf.writeframes(audio_i16.tobytes())
                            print(f"[VOICE] Frame {frame_count}: saved {voice_file.name}, max_amp={float(np.max(np.abs(audio))):.6f}")
                    
                    if frame_count % 100 == 0:
                        print(f"[STATUS] Frames: {frame_count}, Unencrypted: {unencrypted_count}, Voice: {voice_count}")
        
        except KeyboardInterrupt:
            print(f"\n[DONE] Captured {frame_count} frames, {unencrypted_count} unencrypted, {voice_count} voice")
    
    capture.close()
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
