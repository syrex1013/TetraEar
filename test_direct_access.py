"""
Direct RTL-SDR access test with multiple attempts.
"""

import os
import sys
from pathlib import Path

# Set up DLL path
current_dir = Path(__file__).parent.absolute()
dll_path = str(current_dir)
if dll_path not in os.environ.get('PATH', ''):
    os.environ['PATH'] = dll_path + os.pathsep + os.environ.get('PATH', '')
if hasattr(os, 'add_dll_directory'):
    os.add_dll_directory(dll_path)

from rtlsdr import RtlSdr

print("="*60)
print("RTL-SDR DIRECT ACCESS TEST")
print("="*60)

# Try different device indices
for device_index in [0, 1, 2]:
    print(f"\n{'='*60}")
    print(f"Attempting to open device index: {device_index}")
    print(f"{'='*60}")
    
    try:
        # Try to open with specific device index
        if device_index == 0:
            sdr = RtlSdr()  # Default device
        else:
            sdr = RtlSdr(device_index=device_index)
        
        print(f"✓ Device {device_index} opened")
        
        # Configure
        try:
            sdr.sample_rate = 1.8e6
            sdr.center_freq = 400e6
            sdr.gain = 'auto'
            print(f"✓ Device {device_index} configured")
            
            # Get info
            try:
                serial = sdr.get_device_serial_addresses()
                print(f"✓ Serial: {serial}")
            except Exception as e:
                print(f"⚠ Serial read error: {e}")
            
            # Read samples
            try:
                print("  Attempting to read samples...")
                samples = sdr.read_samples(1024)
                print(f"✓✓✓ SUCCESS! Device {device_index} read {len(samples)} samples")
                print(f"\n{'*'*60}")
                print(f"DEVICE {device_index} IS WORKING!")
                print(f"{'*'*60}\n")
                sdr.close()
                
                print("\nYour device is working! Exiting test.")
                input("\nPress Enter to exit...")
                sys.exit(0)
                
            except Exception as e:
                print(f"✗ Sample read failed: {e}")
                sdr.close()
                
        except Exception as e:
            print(f"✗ Configuration failed: {e}")
            try:
                sdr.close()
            except:
                pass
            
    except Exception as e:
        error_str = str(e)
        print(f"✗ Failed to open device {device_index}: {e}")
        
        if "No such device" in error_str or "LIBUSB_ERROR_NOT_FOUND" in error_str:
            print(f"  → Device index {device_index} doesn't exist")
        elif "LIBUSB_ERROR_ACCESS" in error_str or "Access denied" in error_str:
            print(f"  → Driver/permission issue on device {device_index}")
        elif "LIBUSB_ERROR_BUSY" in error_str:
            print(f"  → Device {device_index} is busy (used by another program)")

print("\n" + "="*60)
print("ALL ATTEMPTS FAILED")
print("="*60)
print("""
POSSIBLE CAUSES:
1. Wrong USB driver installed
   - In Zadig, select "RTL2838UHIDIR" OR "Bulk-In, Interface"
   - Make sure it shows USB ID: 0BDA 2838
   - Install WinUSB driver on the CORRECT interface
   
2. Device is being used by another program
   - Close SDR#, HDSDR, or other SDR software
   - Check Task Manager for rtl_sdr processes
   
3. Need to run as Administrator
   - Right-click Python script and "Run as administrator"
   
4. Device needs to be unplugged and replugged
   - After installing driver, unplug device for 5 seconds
   - Then plug it back in
""")

input("\nPress Enter to exit...")
