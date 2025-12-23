"""
TetraEar - Professional TETRA Decoder

A modern, professional TETRA (Terrestrial Trunked Radio) decoder and analyzer
for RTL-SDR with real-time voice decoding, encryption support, and an intuitive GUI.

This package provides:
- Core TETRA decoding functionality
- Signal processing and capture
- Audio/voice processing
- User interface components

Example:
    >>> from tetraear.core import TetraDecoder
    >>> from tetraear.signal import SignalProcessor
    >>> decoder = TetraDecoder()
    >>> processor = SignalProcessor()
"""

__version__ = "2.1.1"
__author__ = "TetraEar Team"
__license__ = "MIT"

# Lazy imports to avoid DLL loading issues
def __getattr__(name):
    """Lazy import for tetraear modules."""
    if name in ["TetraDecoder", "TEADecryptor", "TetraKeyManager", "TetraProtocolParser"]:
        from tetraear.core import __dict__ as core_dict
        return core_dict[name]
    elif name in ["SignalProcessor", "RTLCapture", "TetraSignalDetector"]:
        from tetraear.signal import __dict__ as signal_dict
        return signal_dict[name]
    elif name == "VoiceProcessor":
        from tetraear.audio import VoiceProcessor
        return VoiceProcessor
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = [
    "TetraDecoder",
    "TEADecryptor",
    "TetraKeyManager",
    "TetraProtocolParser",
    "SignalProcessor",
    "RTLCapture",
    "TetraSignalDetector",
    "VoiceProcessor",
]
