"""
Diagnostic script to check RTL-SDR device access and driver status.
"""

import sys
import os

print("=" * 60)
print("RTL-SDR Diagnostic Check")
print("=" * 60)

# Check if running as admin
try:
    import ctypes
    is_admin = ctypes.windll.shell32.IsUserAnAdmin()
    print(f"\n1. Administrator privileges: {'YES' if is_admin else 'NO'}")
    if not is_admin:
        print("   WARNING: Not running as administrator!")
except:
    print("\n1. Administrator privileges: Unknown")

# Check for DLLs
print("\n2. Checking DLL files...")
dll_dir = os.path.dirname(os.path.abspath(__file__))
librtlsdr = os.path.join(dll_dir, "librtlsdr.dll")
libusb = os.path.join(dll_dir, "libusb-1.0.dll")

print(f"   librtlsdr.dll: {'Found' if os.path.exists(librtlsdr) else 'NOT FOUND'}")
print(f"   libusb-1.0.dll: {'Found' if os.path.exists(libusb) else 'NOT FOUND'}")

# Add DLL directory to PATH
if dll_dir not in os.environ.get('PATH', ''):
    os.environ['PATH'] = dll_dir + os.pathsep + os.environ.get('PATH', '')

# Try to import and access RTL-SDR
print("\n3. Testing RTL-SDR library access...")
try:
    from rtlsdr import RtlSdr
    print("   [OK] rtlsdr library imported")
    
    try:
        sdr = RtlSdr()
        print("   [OK] RtlSdr object created")
        
        try:
            devices = sdr.get_device_serial_addresses()
            print(f"   [OK] Found {len(devices)} device(s)")
            for i, dev in enumerate(devices):
                print(f"      Device {i}: {dev}")
            
            # Try to set basic parameters
            try:
                sdr.sample_rate = 1.8e6
                sdr.center_freq = 392.5e6
                sdr.gain = 'auto'
                print("   [OK] Device parameters set successfully")
                
                # Try to read samples
                try:
                    samples = sdr.read_samples(1024)
                    print(f"   [OK] Successfully read {len(samples)} samples!")
                    print("   [SUCCESS] RTL-SDR is fully accessible!")
                except Exception as e:
                    print(f"   [WARNING] Cannot read samples: {e}")
                    print("   This might be a driver issue or device in use")
                
            except Exception as e:
                print(f"   [ERROR] Cannot set parameters: {e}")
                
        except Exception as e:
            print(f"   [ERROR] Cannot enumerate devices: {e}")
            print("   This usually means USB driver issue")
            print("   Solution: Install WinUSB driver using Zadig")
        
        sdr.close()
        
    except Exception as e:
        print(f"   [ERROR] Cannot create RtlSdr object: {e}")
        import traceback
        traceback.print_exc()
        
except ImportError as e:
    print(f"   [ERROR] Cannot import rtlsdr: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("Diagnostic complete")
print("=" * 60)
