"""
List all USB devices to identify the correct RTL-SDR device.
"""

import sys
import os
from pathlib import Path

# Set up DLL path
current_dir = Path(__file__).parent.absolute()
dll_path = str(current_dir)
if dll_path not in os.environ.get('PATH', ''):
    os.environ['PATH'] = dll_path + os.pathsep + os.environ.get('PATH', '')
if hasattr(os, 'add_dll_directory'):
    os.add_dll_directory(dll_path)

print("="*60)
print("USB DEVICE ENUMERATION")
print("="*60)

try:
    import usb.core
    import usb.util
    
    print("\nSearching for all USB devices...")
    devices = usb.core.find(find_all=True)
    
    found_rtl = False
    device_count = 0
    
    for dev in devices:
        device_count += 1
        try:
            manufacturer = usb.util.get_string(dev, dev.iManufacturer) if dev.iManufacturer else "N/A"
            product = usb.util.get_string(dev, dev.iProduct) if dev.iProduct else "N/A"
            serial = usb.util.get_string(dev, dev.iSerialNumber) if dev.iSerialNumber else "N/A"
        except:
            manufacturer = "Cannot read"
            product = "Cannot read"
            serial = "Cannot read"
        
        # Check if this is likely an RTL-SDR
        is_rtl = False
        if dev.idVendor == 0x0bda and dev.idProduct == 0x2838:
            is_rtl = True
            found_rtl = True
        
        marker = " *** RTL-SDR DEVICE ***" if is_rtl else ""
        
        print(f"\nDevice {device_count}:{marker}")
        print(f"  Vendor ID:  0x{dev.idVendor:04x}")
        print(f"  Product ID: 0x{dev.idProduct:04x}")
        print(f"  Manufacturer: {manufacturer}")
        print(f"  Product:      {product}")
        print(f"  Serial:       {serial}")
        print(f"  Bus:          {dev.bus}")
        print(f"  Address:      {dev.address}")
    
    print("\n" + "="*60)
    print(f"Total devices found: {device_count}")
    
    if not found_rtl:
        print("\n⚠ WARNING: No RTL-SDR device found (VID:0x0bda, PID:0x2838)")
        print("\nCommon RTL-SDR USB IDs:")
        print("  - 0bda:2838 (RTL2838 - most common)")
        print("  - 0bda:2832 (RTL2832)")
        print("\nMake sure your device is plugged in!")
    else:
        print("\n✓ Found RTL-SDR device(s)")
        
except ImportError:
    print("\n✗ PyUSB not installed")
    print("\nTrying alternative method with rtlsdr library...")
    
    try:
        from rtlsdr import RtlSdr
        
        print("\nAttempting to enumerate RTL-SDR devices...")
        
        # Try to get device count
        try:
            count = RtlSdr.get_device_count()
            print(f"RTL-SDR device count: {count}")
            
            if count > 0:
                for i in range(count):
                    try:
                        name = RtlSdr.get_device_name(i)
                        print(f"\nDevice {i}: {name}")
                    except Exception as e:
                        print(f"\nDevice {i}: Error getting name - {e}")
            else:
                print("\n✗ No RTL-SDR devices found by rtlsdr library")
                
        except Exception as e:
            print(f"Error enumerating devices: {e}")
            
    except ImportError:
        print("✗ rtlsdr library not available")

print("\n" + "="*60)
print("\nNow checking what Zadig should show...")
print("="*60)
print("""
In Zadig, with "List All Devices" enabled, look for:

1. "Bulk-In, Interface (Interface 0)"
   - This is often the RTL-SDR device
   - Current driver should show something OTHER than WinUSB
   - If it already shows WinUSB, try interface 1 or 2

2. "RTL2838UHIDIR" or "RTL2832U"
   - Direct device name
   
3. Device with USB ID: 0BDA 2838
   - This is the VID:PID pair

IMPORTANT: 
- If multiple "Bulk-In, Interface" entries exist, you need the RIGHT one
- Usually Interface 0, but could be Interface 1 or 2
- Try each one until it works

COMMON MISTAKE:
- Installing WinUSB on the wrong interface
- Need WinUSB on the BULK interface, not HID interface
""")

input("\nPress Enter to exit...")
