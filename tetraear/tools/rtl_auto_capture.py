#!/usr/bin/env python3
"""
Auto-capture TETRA frames with RTL-SDR and stop when clear data appears.

This script continuously captures IQ samples, demodulates, decodes frames,
and stops when it finds readable text or non-silent voice audio.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import wave
from datetime import datetime
from pathlib import Path

import numpy as np

from tetraear.signal.capture import RTLCapture
from tetraear.signal.processor import SignalProcessor
from tetraear.core.decoder import TetraDecoder
from tetraear.audio.voice import VoiceProcessor


def _now_id() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def _clean_key_line(line: str) -> str:
    hex_chars = "0123456789abcdefABCDEF"
    return "".join(c for c in line if c in hex_chars)


def _load_keys(path: Path) -> list[str]:
    keys: list[str] = []
    for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or line.startswith("//"):
            continue
        cleaned = _clean_key_line(line)
        if len(cleaned) >= 20:
            keys.append(cleaned)
    return keys


def _extract_codec_input_from_bits(bits: np.ndarray | list[int]) -> bytes | None:
    if bits is None:
        return None
    if isinstance(bits, list):
        bits = np.array(bits, dtype=np.uint8)
    if len(bits) < 432:
        return None

    # Use first 432 bits to build a 690-short codec frame.
    soft_bits = []
    for b in bits[:432]:
        soft_bits.append(127 if int(b) else -127)

    block = [0] * 690
    block[0] = 0x6B21

    idx = 0
    for i in range(1, 115):
        if idx >= len(soft_bits):
            break
        block[i] = soft_bits[idx]
        idx += 1
    for i in range(116, 230):
        if idx >= len(soft_bits):
            break
        block[i] = soft_bits[idx]
        idx += 1
    for i in range(231, 345):
        if idx >= len(soft_bits):
            break
        block[i] = soft_bits[idx]
        idx += 1
    for i in range(346, 436):
        if idx >= len(soft_bits):
            break
        block[i] = soft_bits[idx]
        idx += 1

    return np.array(block, dtype=np.int16).tobytes()


def _strip_prefix(text: str) -> str:
    if text.startswith("[") and "]" in text:
        return text.split("]", 1)[1].strip()
    return text


def _is_readable_text(decoder: TetraDecoder, text: str, threshold: float) -> bool:
    if not text:
        return False
    if text.startswith("[BIN"):
        return False
    check = _strip_prefix(text)
    return decoder.protocol_parser._is_valid_text(check, threshold=threshold)


def _write_wav(path: Path, audio: np.ndarray, sample_rate: int) -> None:
    audio_i16 = np.clip(audio * 32767.0, -32768, 32767).astype(np.int16)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(audio_i16.tobytes())


def main() -> int:
    parser = argparse.ArgumentParser(description="Auto-capture TETRA data with RTL-SDR.")
    parser.add_argument("--frequency", type=float, default=392.241, help="Center frequency in MHz")
    parser.add_argument("--sample-rate", type=float, default=2.4, help="Sample rate in MHz")
    parser.add_argument("--gain", default="auto", help="Gain value or 'auto'")
    parser.add_argument("--chunk", type=int, default=256 * 1024, help="Samples per read")
    parser.add_argument("--attempt-seconds", type=float, default=12.0, help="Seconds per attempt")
    parser.add_argument("--max-attempts", type=int, default=10, help="Max attempts (0 = infinite)")
    parser.add_argument("--min-text-threshold", type=float, default=0.7, help="Readable text threshold")
    parser.add_argument("--try-voice", action="store_true", help="Attempt voice decode")
    parser.add_argument("--keys-file", type=str, default="", help="Optional key file")
    parser.add_argument("--log-dir", type=str, default="logs", help="Log output directory")
    parser.add_argument("--records-dir", type=str, default="records", help="Record output directory")
    args = parser.parse_args()

    log_dir = Path(args.log_dir)
    records_dir = Path(args.records_dir)
    _ensure_dir(log_dir)
    _ensure_dir(records_dir)

    run_id = _now_id()
    frames_log = log_dir / f"auto_frames_{run_id}.jsonl"
    text_log = log_dir / f"auto_text_{run_id}.log"
    voice_wav = records_dir / f"auto_voice_{run_id}.wav"

    frequency_hz = args.frequency * 1e6
    sample_rate_hz = args.sample_rate * 1e6

    capture = RTLCapture(frequency=frequency_hz, sample_rate=sample_rate_hz, gain=args.gain)
    if not capture.open():
        print("[FAIL] Could not open RTL-SDR device.")
        return 1

    decoder = TetraDecoder(auto_decrypt=True)
    if args.keys_file:
        key_path = Path(args.keys_file)
        if key_path.exists():
            keys = _load_keys(key_path)
            if keys:
                decoder.set_keys(keys)
                print(f"[OK] Loaded {len(keys)} keys from {key_path}")
            else:
                print(f"[WARN] No valid keys found in {key_path}")
        else:
            print(f"[WARN] Keys file not found: {key_path}")

    processor = SignalProcessor(sample_rate=sample_rate_hz)
    voice = VoiceProcessor() if args.try_voice else None

    print(f"[INFO] Recording at {args.frequency:.3f} MHz, {args.sample_rate:.3f} MHz SR")
    print(f"[INFO] Frames log: {frames_log}")

    success = False
    attempt = 0
    max_attempts = args.max_attempts

    with frames_log.open("w", encoding="utf-8") as frames_fp, text_log.open("w", encoding="utf-8") as text_fp:
        while max_attempts == 0 or attempt < max_attempts:
            attempt += 1
            print(f"[INFO] Attempt {attempt}")
            attempt_start = time.time()
            audio_segments: list[np.ndarray] = []
            found_text: list[str] = []

            while time.time() - attempt_start < args.attempt_seconds:
                samples = capture.read_samples(args.chunk)
                demodulated = processor.process(samples)
                if demodulated is None or len(demodulated) < 255:
                    continue

                frames = decoder.decode(demodulated)
                if not frames:
                    continue

                for frame in frames:
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
                    serializable_frame = {k: convert_value(v) for k, v in frame.items()}
                    frames_fp.write(json.dumps(serializable_frame, ensure_ascii=False) + "\n")
                    frames_fp.flush()

                    text = frame.get("decoded_text") or frame.get("sds_message") or ""
                    if text and _is_readable_text(decoder, text, args.min_text_threshold):
                        found_text.append(text)
                        text_fp.write(text + "\n")
                        text_fp.flush()
                        success = True

                    if voice is not None and not success:
                        bits = frame.get("bits")
                        codec_input = _extract_codec_input_from_bits(bits)
                        if codec_input is None:
                            continue
                        audio = voice.decode_frame(codec_input)
                        if audio.size > 0 and float(np.max(np.abs(audio))) > 1e-4:
                            audio_segments.append(audio)
                            success = True

                if success:
                    break

            if success:
                print("[OK] Found readable data.")
                if found_text:
                    print(f"[OK] Text examples written to {text_log}")
                if audio_segments:
                    audio_out = np.concatenate(audio_segments)
                    _write_wav(voice_wav, audio_out, 8000)
                    print(f"[OK] Voice audio written to {voice_wav}")
                break

            print("[INFO] No readable data in this attempt, retrying...")

    capture.close()

    if not success:
        print("[WARN] No readable data found. Try longer capture or adjust frequency/gain.")
        return 2

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
