# Running TETRA Decoder - USB Permission Fix

## Current Issue
The RTL-SDR device is detected but access is denied due to USB permissions.

## Solutions

### Option 1: Run as Administrator (Quick Fix)
1. Right-click on PowerShell or Command Prompt
2. Select "Run as Administrator"
3. Navigate to the project directory
4. Run: `python tetra_decoder_main.py --scan-poland`

### Option 2: Install WinUSB Driver (Permanent Fix)
1. Download Zadig: https://zadig.akeo.ie/
2. Connect your RTL-SDR dongle
3. Open Zadig
4. Go to Options → List All Devices
5. Select your RTL-SDR device (usually shows as "Bulk-In, Interface" or "RTL2832UHIDIR")
6. Select "WinUSB" as the driver
7. Click "Install Driver" or "Replace Driver"
8. Wait for installation to complete
9. Restart your computer (recommended)

### Option 3: Check for Other Programs Using RTL-SDR
- Close any other SDR software (SDR#, GQRX, etc.)
- The device can only be used by one program at a time

## Test Commands

Once permissions are fixed, try:

```bash
# Scan Poland TETRA frequencies (390-395 MHz)
python tetra_decoder_main.py --scan-poland

# Scan and decode found channels
python tetra_decoder_main.py --scan-poland --decode-found -o results.txt

# Decode specific frequency (392.5 MHz)
python tetra_decoder_main.py -f 392500000

# Scan with lower thresholds (more sensitive)
python tetra_decoder_main.py --scan-poland --min-power -80 --min-confidence 0.3
```

## Expected Output
When working correctly, you should see:
- "RTL-SDR opened" message
- Frequency scanning progress
- Found TETRA channels with power levels
- Decoded frames (if signals are present and unencrypted)
