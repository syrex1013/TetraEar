#!/usr/bin/env python3
import json
import numpy as np
from pathlib import Path
from tetraear.audio.voice import VoiceProcessor
import wave

# Load frame with bits
with open('logs/auto_frames_20251223_214747.jsonl', 'r') as f:
    for line in f:
        frame = json.loads(line)
        if frame.get('bits') and len(frame['bits']) >= 432:
            print(f"Found frame: type={frame.get('type_name')}, encrypted={frame.get('encrypted', True)}, bits={len(frame['bits'])}")
            
            # Extract codec input
            bits = np.array(frame['bits'], dtype=np.uint8)
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
            
            # Try to decode
            voice = VoiceProcessor()
            if voice.working:
                audio = voice.decode_frame(codec_input)
                if audio.size > 0:
                    max_amp = float(np.max(np.abs(audio)))
                    print(f"  Decoded audio: {audio.size} samples, max amplitude: {max_amp:.6f}")
                    
                    if max_amp > 1e-4:
                        # Write to WAV
                        audio_i16 = np.clip(audio * 32767.0, -32768, 32767).astype(np.int16)
                        with wave.open('test_voice.wav', 'wb') as wf:
                            wf.setnchannels(1)
                            wf.setsampwidth(2)
                            wf.setframerate(8000)
                            wf.writeframes(audio_i16.tobytes())
                        print("  Wrote test_voice.wav")
                    else:
                        print("  Audio is silent")
                else:
                    print("  No audio decoded")
            else:
                print("  Voice processor not working")
            
            break
