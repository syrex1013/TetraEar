"""
Audio export utilities.

Currently supports optional WAV -> MP3 conversion via `ffmpeg` (if installed).
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


def find_ffmpeg() -> str | None:
    """Return the path to ffmpeg if available on PATH."""
    return shutil.which("ffmpeg") or shutil.which("ffmpeg.exe")


def wav_to_mp3(wav_path: str | Path, mp3_path: str | Path | None = None, *, bitrate: str = "128k") -> Path:
    """
    Convert a WAV file to MP3 using ffmpeg.

    Args:
        wav_path: Path to input WAV.
        mp3_path: Optional output path. Defaults to `<wav>.mp3`.
        bitrate: MP3 bitrate (ffmpeg format), e.g. "128k".

    Returns:
        Path to the created MP3 file.

    Raises:
        FileNotFoundError: If ffmpeg is not found.
        RuntimeError: If conversion fails.
    """
    wav_path = Path(wav_path)
    if mp3_path is None:
        mp3_path = wav_path.with_suffix(".mp3")
    mp3_path = Path(mp3_path)

    ffmpeg = find_ffmpeg()
    if not ffmpeg:
        raise FileNotFoundError("ffmpeg not found on PATH")

    mp3_path.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        ffmpeg,
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        str(wav_path),
        "-codec:a",
        "libmp3lame",
        "-b:a",
        bitrate,
        str(mp3_path),
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        msg = (result.stderr or result.stdout or "").strip()
        raise RuntimeError(f"ffmpeg failed (code {result.returncode}): {msg}")

    return mp3_path

