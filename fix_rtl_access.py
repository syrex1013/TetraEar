"""
Comprehensive RTL-SDR access troubleshooting and fix script.
"""

import sys
import os
import ctypes
from pathlib import Path

def is_admin():
    """Check if script is running with admin privileges."""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def check_dll_files():
    """Check if required DLL files are present."""
    print("\n" + "="*60)
    print("DLL FILES CHECK")
    print("="*60)
    
    current_dir = Path(__file__).parent.absolute()
    
    dlls = ['librtlsdr.dll', 'libusb-1.0.dll']
    all_found = True
    
    for dll in dlls:
        dll_path = current_dir / dll
        if dll_path.exists():
            print(f"✓ {dll}: Found at {dll_path}")
        else:
            print(f"✗ {dll}: NOT FOUND")
            all_found = False
    
    return all_found

def check_device_access():
    """Try to access RTL-SDR device with detailed error reporting."""
    print("\n" + "="*60)
    print("RTL-SDR DEVICE ACCESS TEST")
    print("="*60)
    
    # Set up DLL path
    current_dir = Path(__file__).parent.absolute()
    dll_path = str(current_dir)
    if dll_path not in os.environ.get('PATH', ''):
        os.environ['PATH'] = dll_path + os.pathsep + os.environ.get('PATH', '')
    if hasattr(os, 'add_dll_directory'):
        os.add_dll_directory(dll_path)
    
    try:
        from rtlsdr import RtlSdr
        print("✓ rtlsdr library imported successfully")
        
        # Try to create device object
        try:
            sdr = RtlSdr()
            print("✓ RTL-SDR device object created")
            
            # Try to get device info
            try:
                serial = sdr.get_device_serial_addresses()
                print(f"✓ Device serial: {serial}")
                
                # Try to configure device
                sdr.sample_rate = 1.8e6
                sdr.center_freq = 400e6
                sdr.gain = 'auto'
                print("✓ Device configured successfully")
                
                # Try to read samples
                samples = sdr.read_samples(1024)
                print(f"✓ Successfully read {len(samples)} samples")
                
                sdr.close()
                print("\n✓✓✓ SUCCESS! RTL-SDR is working correctly! ✓✓✓")
                return True
                
            except Exception as e:
                print(f"✗ Device operation failed: {e}")
                try:
                    sdr.close()
                except:
                    pass
                return False
                
        except Exception as e:
            error_str = str(e)
            print(f"✗ Cannot create RTL-SDR device: {e}")
            
            # Detailed error analysis
            if "LIBUSB_ERROR_ACCESS" in error_str or "Access denied" in error_str:
                print("\n" + "!"*60)
                print("DIAGNOSIS: USB DRIVER ISSUE")
                print("!"*60)
                print("The device is detected but the driver is incorrect.")
                print("\nYour RTL-SDR device is using the wrong USB driver.")
                print("It needs WinUSB driver, but it's likely using:")
                print("  - Bulk-In, Interface driver")
                print("  - WinUSB (incorrect configuration)")
                print("  - Or another incompatible driver")
                
            elif "LIBUSB_ERROR_NOT_FOUND" in error_str or "No such device" in error_str:
                print("\n" + "!"*60)
                print("DIAGNOSIS: DEVICE NOT FOUND")
                print("!"*60)
                print("The RTL-SDR device is not detected at all.")
                print("Make sure:")
                print("  - Device is plugged in")
                print("  - USB cable is working")
                print("  - Device appears in Device Manager")
                
            elif "LIBUSB_ERROR_BUSY" in error_str or "Resource busy" in error_str:
                print("\n" + "!"*60)
                print("DIAGNOSIS: DEVICE IN USE")
                print("!"*60)
                print("Another program is using the RTL-SDR device.")
                print("Close these programs:")
                print("  - SDR#, HDSDR, or other SDR software")
                print("  - Other Python scripts using RTL-SDR")
                
            return False
            
    except ImportError as e:
        print(f"✗ Cannot import rtlsdr library: {e}")
        print("\nInstall with: pip install pyrtlsdr")
        return False

def print_fix_instructions():
    """Print detailed fix instructions."""
    print("\n" + "="*60)
    print("FIX INSTRUCTIONS")
    print("="*60)
    print("""
STEP 1: Download Zadig
    Go to: https://zadig.akeo.ie/
    Download the latest version

STEP 2: Run Zadig as Administrator
    Right-click zadig.exe → Run as administrator

STEP 3: Configure Zadig
    1. Options → List All Devices (enable this!)
    2. In the dropdown, select one of:
       - "Bulk-In, Interface (Interface 0)"
       - "RTL2838UHIDIR"
       - Your RTL-SDR device name
    
STEP 4: Install WinUSB Driver
    1. In the driver box (middle), select: WinUSB (NOT libusbK)
    2. Click "Install Driver" or "Replace Driver"
    3. Wait for completion message

STEP 5: Verify Installation
    1. Unplug your RTL-SDR device
    2. Wait 5 seconds
    3. Plug it back in
    4. Run this script again AS ADMINISTRATOR

STEP 6: If Still Failing
    1. Open Device Manager (devmgmt.msc)
    2. Look for your RTL-SDR under:
       - Universal Serial Bus devices
       - Or unknown devices
    3. Right-click → Update Driver → Browse → Pick from list
    4. Select "WinUSB Device" or "Universal Serial Bus devices"
    5. Try different WinUSB options until it works
""")

def main():
    """Main diagnostic function."""
    print("\n" + "="*60)
    print("RTL-SDR ACCESS TROUBLESHOOTER")
    print("="*60)
    
    # Check admin privileges
    admin = is_admin()
    print(f"\nAdministrator privileges: {'YES ✓' if admin else 'NO ✗'}")
    
    if not admin:
        print("WARNING: Some USB operations may fail without admin rights!")
        print("         Recommend running as administrator.")
    
    # Check DLL files
    dlls_ok = check_dll_files()
    
    if not dlls_ok:
        print("\n✗ Missing DLL files! Cannot proceed.")
        print("  Make sure librtlsdr.dll and libusb-1.0.dll are in the script directory.")
        return
    
    # Check device access
    device_ok = check_device_access()
    
    if not device_ok:
        print_fix_instructions()
        print("\n" + "="*60)
        print("After following the steps above, run this script again.")
        print("="*60)
    else:
        print("\n" + "="*60)
        print("Everything is working! You can now use your RTL-SDR device.")
        print("="*60)

if __name__ == "__main__":
    main()
    input("\nPress Enter to exit...")
