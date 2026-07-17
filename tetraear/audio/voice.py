"""
TETRA Voice Processor
Handles TETRA voice decoding using the ETSI TS 300 395-2 reference codec executables.

Pipeline (per time-slot block):
1) `cdecoder.exe`: channel decoder (soft bits -> serial vocoder bits)
2) `sdecoder.exe`: speech decoder (serial vocoder bits -> synthesized speech samples)
"""

from __future__ import annotations

import os
import logging
import subprocess
import tempfile
from pathlib import Path

import numpy as np

logger = logging.getLogger(__name__)
codec_logger = logging.getLogger("tetraear.codec")

# Codec per-frame timeout. A too-aggressive timeout drops otherwise
# decodable voice frames when the machine is slow or "cold" -- e.g. an
# antivirus scanning the freshly built codec executables during the first
# calls. Make it configurable via the TETRAEAR_CODEC_TIMEOUT environment
# variable (in seconds), with a more tolerant default than before.
def _codec_timeout() -> float:
    try:
        value = float(os.environ.get("TETRAEAR_CODEC_TIMEOUT", "15"))
    except (TypeError, ValueError):
        value = 15.0
    return value if value > 0 else 15.0


_CODEC_TIMEOUT = _codec_timeout()


class VoiceProcessor:
    """
    Handles TETRA voice decoding using ETSI TS 300 395-2 codec executables.
    """

    def __init__(
        self,
        codec_path: str | os.PathLike[str] | None = None,
        cdecoder_path: str | os.PathLike[str] | None = None,
        sdecoder_path: str | os.PathLike[str] | None = None,
        codec_dir: str | os.PathLike[str] | None = None,
    ):
        """
        Create a voice decoder.

        Args:
            codec_path: Back-compat alias for `cdecoder_path` (path to `cdecoder.exe`).
            cdecoder_path: Optional path to `cdecoder.exe` (channel decoder).
            sdecoder_path: Optional path to `sdecoder.exe` (speech decoder).
            codec_dir: Optional directory containing codec executables. If provided, it is used to
                locate `cdecoder.exe` and `sdecoder.exe`.
        """
        default_dir = Path(__file__).resolve().parents[1] / "tetra_codec" / "bin"

        resolved_codec_dir = None
        if codec_dir is not None:
            resolved_codec_dir = Path(codec_dir)
        elif cdecoder_path is not None or codec_path is not None:
            resolved_codec_dir = Path(cdecoder_path or codec_path).resolve().parent
        else:
            resolved_codec_dir = default_dir

        def resolve_candidate(provided: str | os.PathLike[str] | None, candidates: list[str]) -> Path:
            if provided is not None:
                return Path(provided)
            for name in candidates:
                candidate = resolved_codec_dir / name
                if candidate.exists():
                    return candidate
            return resolved_codec_dir / candidates[0]

        self.cdecoder_path = resolve_candidate(cdecoder_path or codec_path, ["cdecoder", "cdecoder.exe"])
        self.sdecoder_path = resolve_candidate(sdecoder_path, ["sdecoder", "sdecoder.exe"])

        for path in (self.cdecoder_path, self.sdecoder_path):
            if path.exists() and os.name != "nt":
                try:
                    if not os.access(path, os.X_OK):
                        path.chmod(path.stat().st_mode | 0o111)
                except Exception:
                    pass

        def is_windows_binary(path: Path) -> bool:
            try:
                with path.open("rb") as handle:
                    return handle.read(2) == b"MZ"
            except Exception:
                return False

        self.channel_decoder_available = self.cdecoder_path.exists() and os.access(self.cdecoder_path, os.X_OK)
        self.speech_decoder_available = self.sdecoder_path.exists() and os.access(self.sdecoder_path, os.X_OK)
        self.working = self.channel_decoder_available and self.speech_decoder_available

        if not self.channel_decoder_available:
            logger.warning("TETRA codec channel decoder not found at %s", self.cdecoder_path)
        else:
            if os.name != "nt" and is_windows_binary(self.cdecoder_path):
                logger.warning("Windows codec detected at %s; install native codec or use Wine", self.cdecoder_path)
            logger.debug("TETRA codec channel decoder found at %s", self.cdecoder_path)

        if not self.speech_decoder_available:
            logger.warning("TETRA codec speech decoder not found at %s", self.sdecoder_path)
        else:
            if os.name != "nt" and is_windows_binary(self.sdecoder_path):
                logger.warning("Windows codec detected at %s; install native codec or use Wine", self.sdecoder_path)
            logger.debug("TETRA codec speech decoder found at %s", self.sdecoder_path)
            
    def decode_frame(self, frame_data: bytes) -> np.ndarray:
        """
        Decode a TETRA time-slot block into synthesized audio.

        Input (`frame_data`) must be a binary file image containing 690 16-bit words:
        - First word: 0x6B21 (header marker)
        - Next 689 words: soft bits (16-bit values; typical range -127..127)

        Returns:
            Float32 numpy array of audio samples in [-1, 1]. Empty array on failure.
        """
        if not self.working or not frame_data:
            return np.zeros(0)
            
        try:
            import struct
            
            # frame_data should already be in correct format (1380 bytes = 690 shorts)
            # Verify frame size
            if len(frame_data) != 1380:
                logger.debug(f"Invalid frame size: {len(frame_data)} bytes (expected 1380)")
                return np.zeros(0)
            
            # Verify header
            header = struct.unpack('<H', frame_data[0:2])[0]
            if header != 0x6B21:
                logger.debug(f"Invalid header: 0x{header:04X} (expected 0x6B21)")
                return np.zeros(0)
            
            keep_temp = os.environ.get("TETRAEAR_KEEP_CODEC_TEMP", "").strip().lower() in ("1", "true", "yes", "y")

            # Write frame to temp file (binary) - already in correct format
            with tempfile.NamedTemporaryFile(mode="wb", delete=False, suffix=".tet") as tmp_in:
                tmp_in.write(frame_data)
                tmp_in_path = tmp_in.name

            tmp_serial_path = tmp_in_path + ".serial"
            tmp_synth_path = tmp_in_path + ".synth"
            
            # Log input data stats
            input_shorts = np.frombuffer(frame_data, dtype=np.int16)
            logger.debug(f"Codec input: {len(input_shorts)} shorts, Max: {np.max(np.abs(input_shorts))}, Header: 0x{input_shorts[0]:04X}")
            logger.debug(f"Codec input file: {tmp_in_path}")
            
            # Use absolute paths for input/output
            abs_in = os.path.abspath(tmp_in_path)
            abs_serial = os.path.abspath(tmp_serial_path)
            abs_synth = os.path.abspath(tmp_synth_path)
            
            # Step 1: channel decoding (soft bits -> serial vocoder bits)
            codec_logger.debug("Calling cdecoder: %s %s %s", self.cdecoder_path, abs_in, abs_serial)
            result = subprocess.run(
                [str(self.cdecoder_path), abs_in, abs_serial],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
                timeout=_CODEC_TIMEOUT,
                # Run the codec hidden: under a no-console launcher (pythonw)
                # each call would otherwise flash a console window per frame.
                # The flag only exists on Windows; elsewhere it is 0 (no-op).
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            
            # Log codec process output
            if result.stdout:
                codec_logger.debug("STDOUT: %s", result.stdout.decode('utf-8', errors='ignore').strip())
            if result.stderr:
                codec_logger.debug("STDERR: %s", result.stderr.decode('utf-8', errors='ignore').strip())
            
            if result.returncode != 0:
                codec_logger.debug("cdecoder failed with return code %s", result.returncode)
            else:
                codec_logger.debug("cdecoder exited 0")
            
            if not (os.path.exists(tmp_serial_path) and os.path.getsize(tmp_serial_path) > 0):
                codec_logger.debug("cdecoder produced no serial output file or empty file (return code: %s)", result.returncode)
                if not keep_temp:
                    try:
                        os.remove(tmp_in_path)
                        if os.path.exists(tmp_serial_path):
                            os.remove(tmp_serial_path)
                        if os.path.exists(tmp_synth_path):
                            os.remove(tmp_synth_path)
                    except Exception:
                        pass
                return np.zeros(0)

            serial_size = os.path.getsize(tmp_serial_path)
            codec_logger.debug("cdecoder serial output: %s (%s bytes)", tmp_serial_path, serial_size)

            # Basic sanity checks on cdecoder output: it should contain (BFI + 137) int16 words per speech frame.
            # Typical output is 2 speech frames per channel frame: 2 * 138 * 2 bytes = 552 bytes.
            try:
                import struct

                with open(tmp_serial_path, "rb") as f:
                    raw = f.read(min(serial_size, 552))
                if len(raw) >= 2:
                    bfi1 = struct.unpack("<h", raw[:2])[0]
                    bfi2 = None
                    if len(raw) >= 276 + 2:
                        bfi2 = struct.unpack("<h", raw[276:278])[0]
                    codec_logger.debug("cdecoder BFI: frame1=%s frame2=%s", bfi1, bfi2)
            except Exception:
                pass

            # Step 2: speech decoding (serial vocoder bits -> synthesized samples)
            codec_logger.debug("Calling sdecoder: %s %s %s", self.sdecoder_path, abs_serial, abs_synth)
            result2 = subprocess.run(
                [str(self.sdecoder_path), abs_serial, abs_synth],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
                timeout=_CODEC_TIMEOUT,
                # Run the codec hidden: under a no-console launcher (pythonw)
                # each call would otherwise flash a console window per frame.
                # The flag only exists on Windows; elsewhere it is 0 (no-op).
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )

            if result2.stdout:
                codec_logger.debug("SDECODER STDOUT: %s", result2.stdout.decode("utf-8", errors="ignore").strip())
            if result2.stderr:
                codec_logger.debug("SDECODER STDERR: %s", result2.stderr.decode("utf-8", errors="ignore").strip())

            if result2.returncode != 0:
                codec_logger.debug("sdecoder failed with return code %s", result2.returncode)
            else:
                codec_logger.debug("sdecoder exited 0")

            if not (os.path.exists(tmp_synth_path) and os.path.getsize(tmp_synth_path) > 0):
                codec_logger.debug("sdecoder produced no synth output file or empty file (return code: %s)", result2.returncode)
                if not keep_temp:
                    try:
                        os.remove(tmp_in_path)
                        os.remove(tmp_serial_path)
                        if os.path.exists(tmp_synth_path):
                            os.remove(tmp_synth_path)
                    except Exception:
                        pass
                return np.zeros(0)

            synth_size = os.path.getsize(tmp_synth_path)
            codec_logger.debug("sdecoder synth output: %s (%s bytes)", tmp_synth_path, synth_size)

            with open(tmp_synth_path, "rb") as f:
                pcm_data = f.read()

            audio_i16 = np.frombuffer(pcm_data, dtype=np.int16)
            if audio_i16.size == 0:
                return np.zeros(0)

            audio = audio_i16.astype(np.float32) / 32768.0
            max_amp = float(np.max(np.abs(audio))) if audio.size else 0.0
            codec_logger.debug("Codec produced %d samples (max amp %.4f)", audio.size, max_amp)

            # Many bad/incorrect inputs produce "valid" output files that are all zeros.
            # Treat near-silent output as a decode failure so the GUI can show "no voice" instead of recording silence.
            if max_amp < 1e-5:
                codec_logger.debug("Codec produced near-silent audio; treating as decode failure")
                if not keep_temp:
                    try:
                        os.remove(tmp_in_path)
                        os.remove(tmp_serial_path)
                        os.remove(tmp_synth_path)
                    except Exception:
                        pass
                return np.zeros(0)

            if not keep_temp:
                try:
                    os.remove(tmp_in_path)
                    os.remove(tmp_serial_path)
                    os.remove(tmp_synth_path)
                except Exception:
                    pass

            if audio.size > 0:
                logger.info("Decoded %d audio samples from voice frame", audio.size)
            return audio
                
        except Exception as e:
            logger.debug(f"Voice decode error: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            return np.zeros(0)
