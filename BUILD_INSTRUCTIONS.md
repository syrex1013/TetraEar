# Building TETRA Decoder Modern GUI Executable

This guide explains how to build a standalone `.exe` file for the TETRA Decoder Modern GUI.

## Prerequisites

- Python 3.8 or higher
- All dependencies installed (see `requirements.txt`)
- Windows OS (for .exe build)

## Quick Build

1. **Install dependencies** (if not already installed):
   ```bash
   pip install -r requirements.txt
   ```

2. **Run the build script**:
   ```bash
   python -m tetraear.tools.build_exe
   ```

The script will:
- Automatically install PyInstaller if needed
- Build a single-file executable
- Include all necessary DLLs and codec executables
- Create the executable in the `dist/` folder

## Output

After successful build, you'll find:
- **Executable**: `dist/TETRA_Decoder_Modern.exe`
- **Size**: Typically 50-100 MB (includes all dependencies)

## Distribution

The executable is standalone and includes:
- All Python dependencies
- PyQt6 libraries
- NumPy, SciPy, and other scientific libraries
- RTL-SDR libraries
- TETRA codec executables
- Required DLLs (`tetraear/bin/librtlsdr.dll`, `tetraear/bin/libusb-1.0.dll`)

You can distribute the single `.exe` file along with:
- The `tetraear/tetra_codec/bin/` directory (if not bundled correctly)
- The DLL files (if not bundled correctly)

## Troubleshooting

### Build fails with "Module not found"
- Ensure all dependencies are installed: `pip install -r requirements.txt`
- Try installing PyInstaller manually: `pip install pyinstaller`

### Executable doesn't run
- Check that DLLs are in the same directory as the .exe
- Ensure `tetraear/tetra_codec/bin/` directory exists next to the .exe
- Run from command line to see error messages

### Large file size
- This is normal - PyInstaller bundles all dependencies
- Consider using `--onedir` instead of `--onefile` for smaller size (but multiple files)

## Advanced Options

Edit `tetraear/tools/build_exe.py` to customize:
- Executable name
- Icon file
- Additional data files
- Hidden imports
- Build options

## Manual Build (Alternative)

If you prefer to build manually:

```bash
pyinstaller --name=TETRA_Decoder_Modern \
    --onefile \
    --windowed \
    --add-data="tetraear/bin/librtlsdr.dll;tetraear/bin" \
    --add-data="tetraear/bin/libusb-1.0.dll;tetraear/bin" \
    --add-data="tetraear/tetra_codec/bin/*.exe;tetraear/tetra_codec/bin" \
    --add-data="tetraear/assets/*;tetraear/assets" \
    --hidden-import=tetraear.ui.modern \
    --hidden-import=tetraear.signal.capture \
    --hidden-import=tetraear.signal.processor \
    --hidden-import=tetraear.signal.scanner \
    --hidden-import=tetraear.core.decoder \
    --hidden-import=tetraear.core.protocol \
    --hidden-import=tetraear.core.crypto \
    --hidden-import=tetraear.audio.voice \
    tetraear/__main__.py
```
