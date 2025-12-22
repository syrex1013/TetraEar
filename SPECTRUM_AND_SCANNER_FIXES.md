# Spectrum & Scanner Fixes

## 1. Spectrum Display Fixed
**Problem**: Spectrum trace was pegged at the top (0 dB) and waterfall was solid blue.
**Cause**: 
1. **Incorrect Normalization**: The FFT power calculation was `10 * log10(abs(fft))`. Since the FFT magnitude scales with the number of points (N), this resulted in very large positive values (e.g., +30 dB), which clipped to the top of the graph.
2. **Decimation**: The signal was being decimated by 100x before FFT, reducing the effective bandwidth to ~18 kHz and causing severe aliasing/noise, preventing any real signal spikes from being seen.

**Solution**:
- **Proper Normalization**: Changed to `20 * log10(abs(fft) / N)`. This normalizes the power relative to full scale (0 dBFS).
- **Removed Decimation**: Now computing FFT on a full-bandwidth slice of 2048 samples. This restores the full 1.8 MHz bandwidth view and allows seeing actual signal spikes.
- **Fixed Range**: The display range of -120 dB to 0 dB now correctly matches the calculated values.

## 2. Scanner Fixed
**Problem**: `TypeError` when scanning and `AttributeError` when stopping.
**Solution**:
- **Method Calls**: The GUI now correctly iterates through frequencies manually and calls `scan_frequency` instead of the problematic `scan_range` call.
- **Stop Logic**: Removed the call to the non-existent `scanner.stop()` method and properly closes the capture device instead.

## 3. UI Improvements
- **SDR# Style**: The spectrum now uses the requested black background, filled blue trace, and "Jet" colormap for the waterfall.
- **Live Updates**: The spectrum updates at ~60 FPS for a smooth, real-time feel.

## How to Run
```bash
python tetra_gui_modern.py
```
