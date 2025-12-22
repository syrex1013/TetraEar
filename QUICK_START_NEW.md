# Quick Start - TETRA Decoder with Protocol Analysis

## What's New

✅ **Fixed spectrum display** (no more upside-down or overflow)
✅ **Live gain control** (adjust while running)
✅ **Full protocol parsing** (PHY/MAC/higher layers like OpenEar)
✅ **Metadata extraction** (talkgroups, SSI, call info)
✅ **Clear mode detection** (shows unencrypted traffic)
✅ **Statistics dashboard** (network analysis)
✅ **Auto-scroll control** (disabled by default)

## Launch GUI

```bash
python tetra_gui.py
```

Or use the batch file:
```bash
run_gui.bat
```

## Basic Usage

### 1. Start Capture
1. Set frequency (e.g., 390.000 MHz for Poland TETRA)
2. Choose gain (start with "auto")
3. Click **▶ Start**
4. Watch spectrum analyzer for signals

### 2. View Decoded Frames
- **Decoded Frames** tab shows all received frames
- **Green rows** = Successfully decrypted
- **Yellow rows** = Encrypted but no key worked
- **White rows** = Clear mode (not encrypted)

Look for:
- `TG:12345` = Talkgroup ID
- `SSI:67890` = Subscriber Station ID
- `💬 text` = SDS message content
- `🔓 CLEAR MODE` = No encryption

### 3. Check Statistics
1. Switch to **Statistics** tab
2. Click **Refresh Statistics**
3. See breakdown:
   - **PHY Layer**: Burst counts, CRC success
   - **Encryption**: Clear vs encrypted %
   - **Traffic**: Voice calls, data messages
   - **Key Findings**: Security analysis

### 4. Live Adjustments
- **Change gain**: Use dropdown while running
- **Change frequency**: Enter new freq, click Tune
- **Audio**: Enable/disable speaker output
- **Autoscroll**: Toggle to follow/freeze frames

## What You'll See

### Clear Mode Networks
Many TETRA networks run without encryption:
```
📞 Voice calls - 🔓 CLEAR MODE
💬 SDS messages - Text visible
🔧 Control messages - All metadata visible
```

### Encrypted Networks
Even with encryption, metadata is visible:
```
📞 Voice call detected
   - TG:4001 (Talkgroup)
   - SSI:123456 → SSI:789012 (Who's calling)
   - Channel: 15 (Frequency allocated)
   - Encryption: TEA1 (Algorithm used)
```

### Weak Keys
If network uses default/test keys:
```
🔒 Encrypted frame
✓ Decrypted with TEA1 common_key_3
   Confidence: 245 (high)
```

## Understanding the Display

### Frame Table Columns
1. **Time** - When frame received
2. **Frame #** - Frame sequence number
3. **Type** - Broadcast/Traffic/Control/MAC
4. **Description** - What's in the frame
   - 📡 System info
   - 📞 Voice/Data call
   - 🔗 Signaling
   - 📋 MAC control
5. **Encrypted** - Yes/No
6. **Decrypted** - ✓ Yes / ⚠ Maybe / ? Unsure / -
7. **Key Used** - Which key worked (if any)
8. **Data** - Payload content/hex

### Color Coding
- **Green background** = Decrypted successfully
- **Yellow background** = Encrypted, no key worked
- **White background** = Not encrypted (clear mode)

### Indicators
- 🟢 **Signal** - Signal strength detected
- 🔊 **Voice Active** - Audio energy detected
- 🔒 **Encrypted** - Frames encrypted/decrypted ratio

## Frequency Presets

Common TETRA frequencies:
- **Poland**: 390.000, 392.500, 395.000 MHz
- **EU Common**: 420.000 MHz
- **Custom**: Enter your frequency

## Troubleshooting

### No Signal
1. Check antenna connection
2. Verify frequency is correct
3. Try different gain values
4. Check spectrum analyzer for activity

### No Frames Decoded
1. Signal may be too weak (< -80 dB)
2. Wrong frequency/bandwidth
3. Not actually TETRA (try different freq)

### Spectrum Overflow Fixed
- Spectrum now auto-scales properly
- Power clamped to [-120, 0] dB range
- High power signals at top (correct)

### Driver Issues
If RTL-SDR doesn't open:
1. Install WinUSB driver with Zadig
2. See `RUN_AS_ADMIN.md` for details
3. Unplug/replug dongle after driver install

## Advanced Features

### Load Custom Keys
1. Create `keys.txt` file:
```
TEA1:0:0123456789ABCDEF0123
TEA2:1:0123456789ABCDEF0123456789ABCDEF
```
2. Click **Load Keys...** button
3. Select your key file

### Export Frame Data
- Frames are logged to console
- Copy from Log tab
- Table has 1000 frame limit (auto-trim)

### Statistics Interpretation

**High clear mode %** = Network doesn't use encryption
**High CRC fail %** = Weak signal or interference  
**Many voice calls** = Active network
**Many control msgs** = Network management activity

## What This Demonstrates (OpenEar Style)

### ✅ We Can See:
1. **Clear mode traffic** (no encryption)
2. **Talkgroup IDs** and **SSI identifiers**
3. **Call setup/teardown** metadata
4. **Channel allocations**
5. **SDS text messages** (if not encrypted)
6. **Network structure** and activity
7. **Weak/default keys** usage

### ✅ We Prove:
1. Many networks run **without encryption**
2. **Metadata always visible** even when encrypted
3. **TEA1 is weak** (export-grade algorithm)
4. **No E2EE** (end-to-end encryption)
5. **Core network is clear** (only air interface encrypted)

### ❌ We Don't Do:
1. Active key cracking (computationally intensive)
2. Network attacks (passive monitoring only)
3. Transmission/jamming (receive-only)
4. Breaking strong encryption (TEA2/3/4 with good keys)

## Documentation

- `GUI_FIXES_APPLIED.md` - Detailed fix documentation
- `PROTOCOL_IMPLEMENTATION.md` - Protocol parser details
- `QUICKSTART.md` - Original quick start
- `README.md` - Project overview

## Legal Notice

This software is for **educational purposes** only:
- Demonstrates TETRA security weaknesses
- Shows why encryption matters
- Passive monitoring of public broadcasts
- Similar to police scanner or ADS-B monitoring

**Do not use for**:
- Illegal interception
- Privacy violations  
- Network attacks
- Unauthorized access

Check your local laws regarding radio monitoring.

## Support

Issues? Check:
1. RTL-SDR driver installed correctly
2. Frequency is correct for your area
3. Antenna is connected and suitable for band
4. Signal strength is adequate (> -80 dB)
5. Gain is set appropriately (try auto first)

## Have Fun!

You're now equipped with OpenEar-style TETRA analysis tools. Watch for:
- Networks in permanent clear mode
- Metadata leaking from encrypted calls  
- Weak keys being used
- Activity patterns revealing network structure

Remember: This demonstrates **what's already broken**, not new attacks!
