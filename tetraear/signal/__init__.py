"""
Signal processing and capture modules.

This package contains modules for:
- Signal processing (demodulation, filtering)
- RTL-SDR device capture
- Frequency scanning and signal detection
"""

# Lazy imports to avoid DLL loading issues during import
def __getattr__(name):
    """Lazy import for signal modules."""
    if name == "SignalProcessor":
        from tetraear.signal.processor import SignalProcessor
        return SignalProcessor
    elif name == "RTLCapture":
        from tetraear.signal.capture import RTLCapture
        return RTLCapture
    elif name == "TetraSignalDetector":
        from tetraear.signal.scanner import TetraSignalDetector
        return TetraSignalDetector
    elif name == "FrequencyScanner":
        from tetraear.signal.scanner import FrequencyScanner
        return FrequencyScanner
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = [
    "SignalProcessor",
    "RTLCapture",
    "TetraSignalDetector",
    "FrequencyScanner",
]
