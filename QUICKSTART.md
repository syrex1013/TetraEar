# Quick Start Guide - TETRA Decoder

## ✅ Device Working!

Your RTL-SDR is now working correctly. The LIBUSB_ERROR_ACCESS issue has been fixed.

## 🚀 Quick Commands

### 1. Scan for TETRA Signals
```bash
python tetra_decoder_main.py --scan-poland
```

### 2. Scan and Decode (with auto-decrypt)
```bash
python tetra_decoder_main.py --scan-poland --decode-found -o results.txt
```

### 3. Decode Single Frequency
```bash
python tetra_decoder_main.py -f 390000000 -o output.txt
```

### 4. Use Custom Keys
```bash
# Create keys.txt first (see format below)
python tetra_decoder_main.py --scan-poland -k keys.txt --decode-found
```

## 📝 Key File Format (keys.txt)

```
# Format: ALGORITHM:KEY_ID:HEX_KEY
TEA1:0:0123456789ABCDEF0123
TEA2:0:0123456789ABCDEF0123456789ABCDEF
```

## 🔑 Auto-Decryption

**Enabled by default!** The decoder will automatically try these common keys:

- TEA1: All zeros, all ones, test pattern
- TEA2: All zeros, all ones, test pattern

To disable: Add `--no-auto-decrypt` flag

## 📊 Expected Output

```
Found TETRA signal at 390.000 MHz - Power: -28.7 dB, Confidence: 0.88

Frame #42 (Type: 3)
  Position: 1234
  Encrypted: Yes (TEA1)
  Decrypted: Yes - TEA1 common_key_0
  Payload (hex): 48656c6c6f...
```

## 🛠️ Troubleshooting

### Device not working?
```bash
python test_direct_access.py
```

### Want to see all USB devices?
```bash
python list_usb_devices.py
```

### Full diagnostic?
```bash
python fix_rtl_access.py
```

## 📖 More Info

- **AUTO_DECRYPT.md** - Detailed auto-decryption guide
- **RECENT_CHANGES.md** - All recent fixes and features
- **README.md** - Full project documentation

## 💡 Pro Tips

1. **Start simple**: Run scan first to find active channels
2. **Save everything**: Always use `-o results.txt` to save output
3. **Combine features**: Use `--scan-poland --decode-found -k keys.txt -o results.txt`
4. **Adjust sensitivity**: Use `--min-power -80` to find weaker signals
5. **Check logs**: Look at `tetra_decoder.log` for detailed info

## ⚡ Full Featured Command

```bash
python tetra_decoder_main.py \
  --scan-poland \
  --decode-found \
  --min-power -75 \
  -k my_keys.txt \
  -o full_results.txt
```

This will:
- Scan all Poland TETRA frequencies
- Detect signals above -75 dB
- Decode all found channels
- Try your custom keys FIRST
- Try common keys if custom keys fail
- Save everything to full_results.txt

---

**Happy scanning!** 📡
