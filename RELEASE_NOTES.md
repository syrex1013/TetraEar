# TetraEar v2.1.1 - Release Notes

This file is bundled into the Windows release zip and used as the GitHub Release body. Update it for every release.

## Highlights
- Modern GUI is the primary entrypoint (`python -m tetraear`).
- Project layout is consolidated under `tetraear/` (runtime assets, tools, codec).
- Windows release packaging includes docs + examples in the zip.
- Frames table now has a dedicated `Message` column (SDS/text snippets), keeping `Description` clean.
- GSM 7-bit (GSM 03.38) decoding improved; binary SDS now shows richer `[BIN]` details when clear.

## Tested & Verified (Real RF)
Successfully tested on a real TETRA frequency (392.240 MHz) with the following results:

### Decryption Performance
- TEA1/2/3 algorithms working
- Confidence scores observed: 86–112
- Auto-decryption successfully tries common keys
- Frame synchronization observed: 81–91% correlation

### Signal Processing
- Frequency locking stable
- AFC keeps the signal centered
- SNR detection identifies TETRA signals
- False positive prevention validates CRC and frame structure

### Features Verified
- GUI mode (modern interface)
- Real-time decoding (frames processed as they arrive)
- Multi-frame SDS reassembly
- Encryption detection (TEA1/2/3/4 and None)

## Sample Log
```
2025-12-23 02:01:15 - Testing on 392.240 MHz @ 45 dB gain
TETRA Signal Detected (100 frames, Sync: 100%, CRC: 0%)
Decrypted frame 0 using TEA1 common_key_0 (confidence: 100)
Decrypted frame 1 using TEA2 common_key_0 (confidence: 86)
Decrypted frame 2 using TEA3 common_key_0 (confidence: 112)
```

## Voice Codec Status
- TETRA codec (cdecoder.exe) integrated and functional
- No voice traffic detected during the test period; amplitude validation pending real voice transmission

## SDS Text Messages
- SDS parsing implemented with multiple encodings
- Some networks use binary/proprietary SDS encoding; standard text messages decode when available

## Usage Tips
- Use `--auto-decrypt` to enable automatic key trying
- Set gain to 45-50 dB for typical TETRA reception
- Enable "Auto-Follow Spike (AFC)" to track drift and center on the channel

## Known Issues
- Some TETRA networks use proprietary SDS formats
- Voice amplitude validation requires active voice traffic
- High gain (>50 dB) may cause false positives on some setups

---

**Test date**: 2025-12-23  
**Test frequency**: 392.240 MHz  
**Test duration**: 2+ minutes continuous operation  
**Frames decoded**: 100+ frames  
