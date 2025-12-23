#!/usr/bin/env python3
"""
Listen for clear unencrypted TETRA traffic.
Requirements:
- Text: Only pure ASCII (no GSM7 special characters like Ω, Δ, Σ)
- Voice: Accumulate frames to create 3+ second audio files
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

def extract_codec_input(bits):
    if bits is None or len(bits) < 432:
        return None
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
    return np.array(block, dtype=np.int16).tobytes()

def write_wav(path, audio):
    audio_i16 = np.clip(audio * 32767.0, -32768, 32767).astype(np.int16)
    with wave.open(str(path), 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(8000)
        wf.writeframes(audio_i16.tobytes())

def is_pure_ascii(text):
    if not text or len(text) < 5:
        return False
    clean = text.replace('[GSM7]', '').replace('[TXT]', '').replace('[LOC]', '').strip()
    if len(clean) < 5:
        return False
    # Only ASCII letters, numbers, basic punctuation
    allowed = set('ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789 .,!?;:()[]/@#$%&*+-=_"\'')
    valid = sum(1 for c in clean if c in allowed)
    alnum = sum(1 for c in clean if c.isalnum())
    return (valid / len(clean) > 0.8) and (alnum / len(clean) > 0.5) and len(clean.split()) >= 2

class VoiceAccumulator:
    def __init__(self):
        self.calls = {}  # call_id -> [audio_segments]
        self.last_time = {}
    
    def add(self, call_id, audio):
        now = time.time()
        if call_id not in self.calls:
            self.calls[call_id] = []
            self.last_time[call_id] = now
        
        # If gap > 3 seconds, finalize old call
        if now - self.last_time[call_id] > 3.0 and self.calls[call_id]:
            result = self.finalize(call_id)
            self.calls[call_id] = [audio]
            self.last_time[call_id] = now
            return result
        
        self.calls[call_id].append(audio)
        self.last_time[call_id] = now
        
        # Save if duration >= 3 seconds
        total_samples = sum(len(a) for a in self.calls[call_id])
        if total_samples / 8000 >= 3.0:
            return self.finalize(call_id)
        return None
    
    def finalize(self, call_id):
        if call_id not in self.calls or not self.calls[call_id]:
            return None
        audio = np.concatenate(self.calls[call_id])
        del self.calls[call_id]
        del self.last_time[call_id]
        return audio if len(audio) / 8000 >= 1.0 else None
    
    def finalize_all(self):
        results = []
        for cid in list(self.calls.keys()):
            a = self.finalize(cid)
            if a is not None:
                results.append(a)
        return results

def main():
    log_dir = Path("logs")
    records_dir = Path("records")
    log_dir.mkdir(exist_ok=True)
    records_dir.mkdir(exist_ok=True)
    
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    text_log = log_dir / f"clear_text_{run_id}.txt"
    
    capture = RTLCapture(frequency=392.241e6, sample_rate=2.4e6, gain="auto")
    if not capture.open():
        print("[FAIL] RTL-SDR not found")
        return 1
    
    decoder = TetraDecoder(auto_decrypt=False)
    processor = SignalProcessor(sample_rate=2.4e6)
    voice = VoiceProcessor()
    voice_acc = VoiceAccumulator()
    
    print("="*70)
    print("LISTENING FOR CLEAR TEXT & VOICE")
    print("="*70)
    print("Text: Only pure ASCII (no Ω, Δ, Σ special chars)")
    print("Voice: Accumulating 3+ second calls")
    print("Press Ctrl+C to stop\n")
    
    frame_count = 0
    text_count = 0
    voice_count = 0
    voice_frames = 0
    
    with text_log.open("w") as tf:
        tf.write(f"=== CLEAR TEXT - {run_id} ===\n\n")
        tf.flush()
        
        try:
            last_status = time.time()
            while True:
                samples = capture.read_samples(256 * 1024)
                demodulated = processor.process(samples)
                if demodulated is None or len(demodulated) < 255:
                    continue
                
                frames = decoder.decode(demodulated)
                for frame in frames or []:
                    frame_count += 1
                    
                    if not frame.get("encrypted", True):
                        # Check text
                        text = frame.get('decoded_text') or frame.get('sds_message') or ''
                        if text and is_pure_ascii(text):
                            text_count += 1
                            print(f"\n[TEXT!] Frame {frame_count}: {text}")
                            tf.write(f"Frame {frame_count}: {text}\n")
                            tf.flush()
                        
                        # Collect voice
                        bits = frame.get("bits")
                        if bits is not None and len(bits) >= 432 and voice.working:
                            codec_input = extract_codec_input(bits)
                            if codec_input:
                                audio = voice.decode_frame(codec_input)
                                if audio.size > 0 and np.max(np.abs(audio)) > 1e-4:
                                    voice_frames += 1
                                    call_id = frame.get('call_metadata', {}).get('talkgroup_id') or 'unk'
                                    final = voice_acc.add(call_id, audio)
                                    if final is not None:
                                        voice_count += 1
                                        dur = len(final) / 8000
                                        vfile = records_dir / f"clear_voice_{run_id}_{voice_count:04d}.wav"
                                        write_wav(vfile, final)
                                        print(f"\n[VOICE!] Saved {vfile.name} ({dur:.1f}s, call {call_id})")
                
                if time.time() - last_status > 30:
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] {frame_count} frames, {text_count} texts, {voice_frames} vframes, {voice_count} calls")
                    last_status = time.time()
        
        except KeyboardInterrupt:
            print("\nFinalizing...")
            for audio in voice_acc.finalize_all():
                voice_count += 1
                vfile = records_dir / f"clear_voice_{run_id}_{voice_count:04d}.wav"
                write_wav(vfile, audio)
                print(f"Saved {vfile.name} ({len(audio)/8000:.1f}s)")
            
            print(f"\nDONE: {frame_count} frames, {text_count} pure texts, {voice_count} voice calls")
    
    capture.close()
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
