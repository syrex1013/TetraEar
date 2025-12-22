"""
Test RTL-SDR device access with device selection.
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
print("RTL-SDR DEVICE SELECTION TEST")
print("="*60)

# Get device count
try:
    device_count = RtlSdr.get_device_count()
    print(f"\nNumber of RTL-SDR devices found: {device_count}")
    
    if device_count == 0:
        print("\n✗ No RTL-SDR devices detected!")
        print("  Make sure device is plugged in and has correct driver.")
        input("\nPress Enter to exit...")
        sys.exit(1)
    
    # List all devices
    print("\nAvailable devices:")
    for i in range(device_count):
        try:
            name = RtlSdr.get_device_name(i)
            print(f"  Device {i}: {name}")
        except Exception as e:
            print(f"  Device {i}: Error - {e}")
    
    # Try each device
    print("\n" + "="*60)
    print("Testing each device...")
    print("="*60)
    
    for device_id in range(device_count):
        print(f"\n--- Testing Device {device_id} ---")
        
        try:
            # Try to open this specific device
            sdr = RtlSdr(device_index=device_id)
            print(f"✓ Device {device_id} opened successfully")
            
            # Try to configure it
            try:
                sdr.sample_rate = 1.8e6
                sdr.center_freq = 400e6
                sdr.gain = 'auto'
                print(f"✓ Device {device_id} configured successfully")
                
                # Try to get serial
                try:
                    serial = sdr.get_device_serial_addresses()
                    print(f"✓ Device {device_id} serial: {serial}")
                except Exception as e:
                    print(f"⚠ Device {device_id} serial read failed: {e}")
                
                # Try to read samples
                try:
                    samples = sdr.read_samples(1024)
                    print(f"✓ Device {device_id} read {len(samples)} samples - WORKING!")
                    print(f"\n{'='*60}")
                    print(f"SUCCESS! Use device_index={device_id} in your code")
                    print(f"{'='*60}")
                except Exception as e:
                    print(f"✗ Device {device_id} sample read failed: {e}")
                
            except Exception as e:
                print(f"✗ Device {device_id} configuration failed: {e}")
            
            # Close device
            sdr.close()
            print(f"✓ Device {device_id} closed")
            
        except Exception as e:
            print(f"✗ Device {device_id} failed to open: {e}")
    
    print("\n" + "="*60)
    print("Test complete")
    print("="*60)
    
except Exception as e:
    print(f"\n✗ Fatal error: {e}")

input("\nPress Enter to exit...")
