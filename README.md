# TETRA Decoder Pro

A modern, professional TETRA (Terrestrial Trunked Radio) decoder and analyzer for RTL-SDR.

![TETRA Decoder Pro](https://i.imgur.com/placeholder.png)

## Features

- **Modern GUI**: Professional dark theme interface (shadcn/ui style) with real-time waterfall spectrum.
- **Real-time Decoding**: Decodes TETRA frames (MAC, Traffic, Control, Broadcast) from RTL-SDR.
- **Voice Support**: Integrated ACELP codec for voice decoding (requires `cdecoder.exe`).
- **Encryption Handling**: 
  - Auto-detection of encryption (TEA1/TEA2/TEA3).
  - Bruteforce support for common/weak keys.
  - Key management system.
- **Spectrum Analyzer**:
  - High-performance waterfall display (~60 FPS).
  - Zoom and range controls.
  - Click-to-tune functionality.
  - Bandwidth visualization.
- **Data Analysis**:
  - SDS (Short Data Service) text decoding.
  - Call metadata extraction (Talkgroups, SSI).
  - Detailed frame inspection.

## Requirements

- Python 3.8+
- RTL-SDR dongle (with drivers installed)
- `librtlsdr` (included or installed in system)
- TETRA Codec binaries (optional, for voice)

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/tetra-decoder.git
   cd tetra-decoder
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. (Optional) Install TETRA Codec:
   - Place `cdecoder.exe` and `sdecoder.exe` in `tetra_codec/bin/`.
   - Or run `python install_tetra_codec.py` (if available).

## Usage

Run the modern GUI:

```bash
python tetra_gui_modern.py
```

### Controls

- **Frequency**: Enter frequency in MHz (e.g., 390.000) or select a preset.
- **Gain**: Adjust RTL-SDR gain.
- **Sample Rate**: Select sample rate (1.8 MHz recommended).
- **Spectrum**:
  - **Zoom**: Zoom in/out of the spectrum.
  - **Top/Bottom**: Adjust dynamic range (dB).
  - **Click**: Tune to frequency.
  - **Ctrl+Click**: Center frequency.
- **Decoding**:
  - **Auto-Decrypt**: Attempt to decrypt frames using known keys.
  - **Monitor Audio**: Listen to decoded voice traffic.

## Troubleshooting

- **No Signal**: Check antenna connection and gain settings. Ensure you are tuned to a valid TETRA frequency.
- **Decoding Errors**: Weak signals may cause CRC failures. Try adjusting the antenna or gain.
- **Voice Not Working**: Ensure `cdecoder.exe` is correctly installed in `tetra_codec/bin/`.

## License

MIT License
