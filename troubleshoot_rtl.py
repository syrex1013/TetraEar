#!/usr/bin/env python3
"""
Comprehensive RTL-SDR USB Driver Troubleshooting Script
"""

import os
import sys
import subprocess
import platform
import ctypes

def run_command(cmd, description=""):
    """Run a command and return the result."""
    print(f"\n{'='*60}")
    print(f"Running: {description}")
    print(f"Command: {cmd}")
    print('='*60)

    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
        print("STDOUT:")
        print(result.stdout)
        if result.stderr:
            print("STDERR:")
            print(result.stderr)
        print(f"Exit code: {result.returncode}")
        return result.returncode == 0, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        print("Command timed out")
        return False, "", "Timeout"
    except Exception as e:
        print(f"Error running command: {e}")
        return False, "", str(e)

def check_admin_privileges():
    """Check if running with administrator privileges."""
    print("\n1. Checking Administrator Privileges")
    print("-" * 40)

    try:
        if platform.system() == 'Windows':
            is_admin = ctypes.windll.shell32.IsUserAnAdmin()
            print(f"Administrator privileges: {'YES' if is_admin else 'NO'}")
            if not is_admin:
                print("WARNING: Not running as administrator!")
                print("Solution: Right-click script and 'Run as administrator'")
            return is_admin
        else:
            # For non-Windows systems
            result = subprocess.run(['id', '-u'], capture_output=True, text=True)
            is_admin = result.stdout.strip() == '0'
            print(f"Root privileges: {'YES' if is_admin else 'NO'}")
            return is_admin
    except Exception as e:
        print(f"Could not check privileges: {e}")
        return False

def check_dlls():
    """Check for required DLL files."""
    print("\n2. Checking Required DLL Files")
    print("-" * 40)

    dll_dir = os.path.dirname(os.path.abspath(__file__))
    required_dlls = ['librtlsdr.dll', 'libusb-1.0.dll']

    all_found = True
    for dll in required_dlls:
        dll_path = os.path.join(dll_dir, dll)
        found = os.path.exists(dll_path)
        print(f"{dll}: {'Found' if found else 'NOT FOUND'}")
        if found:
            try:
                file_size = os.path.getsize(dll_path)
                print(f"  Size: {file_size} bytes")
            except:
                pass
        else:
            all_found = False

    if all_found:
        print("[OK] All required DLLs found")
    else:
        print("[ERROR] Missing DLLs - download from https://www.rtl-sdr.com/")

    return all_found

def check_python_packages():
    """Check Python packages."""
    print("\n3. Checking Python Packages")
    print("-" * 40)

    required_packages = ['rtlsdr', 'numpy', 'scipy', 'bitstring']

    all_ok = True
    for package in required_packages:
        try:
            __import__(package)
            print(f"{package}: [OK] Available")
        except ImportError as e:
            print(f"{package}: [ERROR] Import failed - {e}")
            all_ok = False

    return all_ok

def check_usb_devices():
    """Check USB devices using Windows tools."""
    print("\n4. Checking USB Devices")
    print("-" * 40)

    if platform.system() == 'Windows':
        # Check Device Manager for RTL-SDR devices
        print("Checking Device Manager for RTL-SDR devices...")

        # Try to find RTL-SDR in device manager
        success, stdout, stderr = run_command(
            'powershell "Get-PnpDevice | Where-Object {$_.Name -like \'*RTL*\' -or $_.Name -like \'*SDR*\' -or $_.Name -like \'*Bulk*\' -or $_.Name -like \'*USB Receiver*\'} | Format-Table -Property Name, Status, InstanceId"',
            "Check USB devices in Device Manager"
        )

        if not success:
            print("Could not query Device Manager. Try running as administrator.")

        # Check if WinUSB driver is installed
        print("\nChecking for WinUSB driver...")
        success, stdout, stderr = run_command(
            'driverquery | findstr -i "WinUSB"',
            "Check if WinUSB driver is installed"
        )

        if "WinUSB" in stdout:
            print("[OK] WinUSB driver appears to be installed")
        else:
            print("[ERROR] WinUSB driver not found in driver list")

    return True

def test_rtl_access():
    """Test RTL-SDR access."""
    print("\n5. Testing RTL-SDR Access")
    print("-" * 40)

    try:
        # Add DLL directory to PATH
        dll_dir = os.path.dirname(os.path.abspath(__file__))
        if dll_dir not in os.environ.get('PATH', ''):
            os.environ['PATH'] = dll_dir + os.pathsep + os.environ.get('PATH', '')

        from rtlsdr import RtlSdr
        print("[OK] rtlsdr library imported successfully")

        try:
            sdr = RtlSdr()
            print("[OK] RtlSdr object created")

            try:
                devices = sdr.get_device_serial_addresses()
                print(f"[OK] Found {len(devices)} device(s)")
                for i, dev in enumerate(devices):
                    print(f"  Device {i}: {dev}")

                # Try to set parameters
                sdr.sample_rate = 1.8e6
                sdr.center_freq = 392.5e6
                sdr.gain = 'auto'
                print("[OK] Device parameters set successfully")

                # Try to read samples
                samples = sdr.read_samples(1024)
                print(f"[OK] Successfully read {len(samples)} samples")
                print("[SUCCESS] RTL-SDR is fully accessible!")

                sdr.close()
                return True

            except Exception as e:
                error_msg = str(e)
                print(f"[ERROR] Cannot access device: {e}")

                if "LIBUSB_ERROR_ACCESS" in error_msg or "Access denied" in error_msg:
                    print("\n" + "="*60)
                    print("ACCESS DENIED ERROR - DRIVER ISSUE")
                    print("="*60)
                    print("The RTL-SDR device driver is not configured correctly.")
                    print("\nSOLUTIONS:")
                    print("1. Install WinUSB driver using Zadig")
                    print("2. Make sure device appears in Device Manager under 'libusb devices'")
                    print("3. Unplug and replug the RTL-SDR device")
                    print("4. Restart computer")
                    print("5. Try different USB port")
                    print("\nDetailed instructions in FIX_USB_DRIVER.md")
                elif "LIBUSB_ERROR_NOT_FOUND" in error_msg:
                    print("No RTL-SDR device found. Check USB connection.")
                else:
                    print(f"Unknown error: {e}")

                sdr.close()
                return False

        except Exception as e:
            print(f"[ERROR] Cannot create RtlSdr object: {e}")
            return False

    except ImportError as e:
        print(f"[ERROR] Cannot import rtlsdr: {e}")
        return False

def main():
    """Main troubleshooting function."""
    print("=" * 80)
    print("RTL-SDR USB Driver Troubleshooting")
    print("=" * 80)
    print(f"Platform: {platform.system()} {platform.release()}")
    print(f"Python: {sys.version}")
    print(f"Working directory: {os.getcwd()}")

    # Run all checks
    admin_ok = check_admin_privileges()
    dlls_ok = check_dlls()
    packages_ok = check_python_packages()
    usb_ok = check_usb_devices()
    rtl_ok = test_rtl_access()

    # Summary
    print("\n" + "=" * 80)
    print("TROUBLESHOOTING SUMMARY")
    print("=" * 80)

    checks = [
        ("Administrator privileges", admin_ok),
        ("Required DLLs present", dlls_ok),
        ("Python packages", packages_ok),
        ("USB device detection", usb_ok),
        ("RTL-SDR access", rtl_ok)
    ]

    for check_name, status in checks:
        status_icon = "[OK]" if status else "[FAIL]"
        print(f"{status_icon} {check_name}: {'PASS' if status else 'FAIL'}")

    if rtl_ok:
        print("\n[SUCCESS] RTL-SDR is working correctly!")
        print("You can now run: python tetra_decoder_main.py --scan-poland")
    else:
        print("\n[FAILED] RTL-SDR access failed.")
        if not admin_ok:
            print("\nCRITICAL: Run this script as administrator!")
        elif not dlls_ok:
            print("\nISSUE: Missing DLL files. Download from https://www.rtl-sdr.com/")
        else:
            print("\nISSUE: WinUSB driver not installed correctly.")
            print("Follow FIX_USB_DRIVER.md for detailed driver installation.")

    print("\n" + "=" * 80)

if __name__ == "__main__":
    main()