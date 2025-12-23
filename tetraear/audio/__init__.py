"""
Audio and voice processing modules.

This package contains modules for:
- TETRA voice decoding using ACELP codec
- Audio playback and recording
"""

from tetraear.audio.voice import VoiceProcessor

__all__ = [
    "VoiceProcessor",
]
