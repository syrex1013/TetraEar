"""
Test script to verify RTL-SDR access after driver installation.
"""

import os
import sys

# Add DLL directory to PATH
dll_dir = os.path.dirname(os.path.abspath(__file__))
if dll_dir not in os.environ.get('PATH', ''):
    os.environ['PATH'] = dll_dir + os.pathsep + os.environ.get('PATH', '')

print("=" * 60)
print("Testing RTL-SDR After Driver Installation")
print("=" * 60)
print("\nIMPORTANT: After installing WinUSB driver with Zadig:")
print("1. UNPLUG your RTL-SDR device")
print("2. Wait 5 seconds")
print("3. PLUG IT BACK IN")
print("4. Then run this test again\n")

try:
    from rtlsdr import RtlSdr
    
    print("Attempting to access RTL-SDR...")
    sdr = RtlSdr()
    
    try:
        devices = sdr.get_device_serial_addresses()
        print(f"SUCCESS! Found {len(devices)} device(s)")
        
        # Try to configure
        sdr.sample_rate = 1.8e6
        sdr.center_freq = 392.5e6
        sdr.gain = 'auto'
        print("Device configured successfully!")
        
        # Try to read samples
        samples = sdr.read_samples(1024)
        print(f"SUCCESS! Read {len(samples)} samples!")
        print("\n" + "=" * 60)
        print("RTL-SDR IS WORKING! You can now run the decoder.")
        print("=" * 60)
        
        sdr.close()
        
    except Exception as e:
        print(f"\nERROR: {e}")
        print("\nPossible issues:")
        print("1. Device not unplugged/replugged after driver install")
        print("2. Multiple interfaces need drivers (check Zadig for Interface 1)")
        print("3. Another program is using the device")
        print("4. Windows needs restart")
        
        sdr.close()
        
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
