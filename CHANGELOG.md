# TetraEar Changelog

## Version 2.1.1 - December 2025

### 🐛 Bug Fixes
- **GSM7 Decoding**: Correct GSM 03.38 7-bit unpacking for SDS text messages.
- **SDS Display**: Keep frames `Description` clean by showing SDS/text in a dedicated `Message` column.

### ✨ Improvements
- **Binary SDS (Clear)**: `[BIN]` output includes PID + richer previews to help interpret open-air binary payloads.

## Version 2.1 - December 2024

### 🐛 Bug Fixes
- **Fixed Signal Detection**: Improved signal detection logic to prevent false positives on every frequency
- **Fixed Status Indicators**: Resolved issue where "No Signal" and "TETRA Signal Detected" appeared simultaneously
- **Fixed Sample Rate Validation**: Added validation for RTL-SDR sample rates to prevent access violations
- **Fixed Sync Detection**: Implemented adaptive thresholding based on max correlation to prevent dropping frames
- **Fixed TETRA Status Updates**: Improved detection criteria to show TETRA status when frames are decoded with auto-decrypt enabled

### ✨ New Features
- **Build System**: Added `tetraear/tools/build_exe.py` for creating standalone Windows executables
- **Custom Assets**: Added support for custom icon and banner from `tetraear/assets/` folder
- **About Dialog**: Added About dialog displaying banner image and application information
- **Debounced Status**: Added 5-second minimum delay before showing "TETRA Signal Detected" to prevent rapid status changes
- **Adaptive Sync Threshold**: Sync detection now uses adaptive thresholds based on max correlation found

### 🔧 Improvements
- **Removed .bat Files**: Replaced batch files with Python build script
- **Icon Support**: Application icon loaded from `tetraear/assets/icon_preview.png` or `tetraear/assets/icon.ico`
- **Sample Rate Slider**: Updated to only allow valid RTL-SDR sample rates (1.8, 1.92, 2.048, 2.4, 2.56, 2.88, 3.2 MHz)
- **Error Handling**: Improved error handling for RTL-SDR access violations and device errors
- **Status Updates**: More frequent status updates when frames are actively being decoded

### 📝 Documentation
- **BUILD_INSTRUCTIONS.md**: Added comprehensive build instructions for creating executables
- **README.md**: Updated with banner image and improved formatting

## Version 2.0 - Complete Rewrite (December 2023)

### 🎨 UI/UX Improvements
- **Modern Dark Theme**: Professional dark UI with neon accents
- **Draggable Window**: Frameless window with custom title bar
- **Spectrum Analyzer**: Real-time waterfall display with customizable zoom/threshold
- **Signal Detection**: Visual indicators for TETRA signal presence (green/red status)
- **Recording Status**: Live recording indicator with time, file size, and "LIVE" badge
- **Filter Dropdowns**: Smart dropdowns populated from decoded data (Groups, Users, Calls)
- **Settings Dialog**: Comprehensive settings with audio device selection, AFC, silence removal
- **Frequency Manager**: Save favorite frequencies with labels and descriptions
- **Status Panels**: Fixed layout to prevent UI squishing, proper spacing

### 🔐 Decryption & Security
- **Auto-Decrypt**: Automatic brute-force of 29 common TETRA keys (TEA1-4)
- **Key Management**: Load custom encryption keys from `keys.txt`
- **Decryption Status**: Clear indication of encrypted vs decrypted frames
- **Multi-algorithm Support**: TEA1, TEA2, TEA3, TEA4 encryption algorithms

### 📡 Signal Processing
- **Improved Sync Detection**: Multi-threshold correlation (0.9, 0.85, 0.8) with stricter validation
- **CRC Validation**: Proper CRC-16-CCITT validation of frames
- **SNR-based Detection**: Signal detection requires >15dB SNR above noise floor
- **Hysteresis Logic**: Prevent signal flapping (5-frame hold)
- **AFC (Auto Frequency Control)**: Automatic frequency correction to center on TETRA spike
- **Sample Rate Optimization**: Throttled processing for high sample rates (>2.5 MSPS)

### 🗨️ SDS (Short Data Service)
- **Multi-frame Assembly**: Proper reassembly of fragmented SDS messages
- **Text Decoding**: Support for 7-bit GSM, UTF-8, and binary formats
- **Protocol Analysis**: MAC-RESOURCE, MAC-BROADCAST, MAC-FRAG, MAC-DATA frame types
- **Readable Filter**: Filter for text-only messages (excludes binary/garbage)

### 🎤 Voice Decoding
- **TETRA Codec Integration**: Automatic compilation and integration of TETRA voice codec
- **ACELP Decoder**: Proper ACELP frame structure with 137-byte encoding
- **Amplitude Validation**: Discard silent/corrupt audio (amplitude > 0.0)
- **Live Audio Monitoring**: Real-time playback of decoded voice
- **Recording Management**: Auto-save recordings with silence removal option

### 📊 Statistics & Logging
- **Comprehensive Stats**: Frame counts, encryption breakdown, sync quality, CRC success rate
- **Detailed Logging**: Debug logging to `logs/tetra_ear_YYYYMMDD_HHMMSS.log`
- **Codec I/O Logging**: Log all TETRA codec inputs/outputs for debugging
- **Color-coded CLI**: Rich console output with ANSI colors (Windows compatible)

### 🖥️ CLI Mode
- **Headless Operation**: Run without GUI using `--no-gui` flag
- **Command-line Args**: Frequency, gain, sample rate, auto-start, monitor audio
- **Frequency Scanner**: Built-in scanner with `--scan START STOP` option
- **Color Output**: ANSI color-coded console output (signal, frames, errors)
- **Unicode Safe**: Handles Windows console encoding issues

### 🛠️ Developer Features
- **Modular Architecture**: Separate modules for capture, decoding, protocol, crypto
- **Signal-based Communication**: PyQt signals for thread-safe event handling
- **Extensible Protocol**: Easy addition of new TETRA frame types
- **Build System**: PyInstaller spec for Windows .exe generation
- **Git Integration**: Proper .gitignore, moved build artifacts to `.codecbuild/`

### 🐛 Bug Fixes
- **False Positives**: Fixed detection of non-TETRA signals (noise, other protocols)
- **Sync Correlation**: Increased thresholds to reduce false sync detections
- **CRC Validation**: Fixed CRC calculation and validation
- **Frame Classification**: Proper detection of encrypted vs open frames
- **UI Layout**: Fixed squished panels, proper sizing and spacing
- **Unicode Errors**: Fixed Windows console encoding issues in CLI mode
- **Sample Rate**: Fixed hang-ups at high sample rates (>2.5 MSPS)

### 📚 Documentation
- **README.md**: Professional README with emojis, features, installation guide
- **BUILD_INSTRUCTIONS.md**: Step-by-step build and codec compilation guide
- **CHANGELOG.md**: This file - comprehensive change log

### 🔗 References & Research
- ETSI EN 300 395-2: TETRA Air Interface Specification
- https://github.com/sq5bpf/telive - Telive TETRA decoder
- https://github.com/itds-consulting/tetra-multiframe-sds - Multi-frame SDS reference
- https://www.etsi.org/security-algorithms-and-codes/codes - TETRA security codes
- https://dsplog.com - TETRA DSP documentation

### ⚠️ Known Issues
- Voice amplitude sometimes 0.0 (codec input format issues)
- CRC at 0% on some signals (need better demodulation)
- Multi-frame SDS not fully tested on live traffic
- Some encrypted frames shown when "Decrypted/Text Only" filter applied

### 🚀 Future Enhancements
- DMO (Direct Mode Operation) support
- TETRA 2 (TEDS) support
- GPS/Location decoding
- Network topology visualization
- Call recording with automatic speaker separation
- Export to various formats (CSV, JSON, PCAP)
- Integration with external decoders (OP25, etc.)

---

**Project**: TetraEar  
**Author**: syrex1013  
**License**: Educational/Research Use Only  
**Repository**: https://github.com/syrex1013/TetraEar
