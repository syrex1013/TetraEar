"""
Build script to compile TETRA Decoder Modern GUI to standalone .exe
Uses PyInstaller to create a single-file executable with all dependencies.
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path
from datetime import datetime
import re

def check_pyinstaller():
    """Check if PyInstaller is installed, install if not."""
    try:
        import PyInstaller
        print("[OK] PyInstaller is installed")
        return True
    except ImportError:
        print("PyInstaller not found. Installing...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
            print("[OK] PyInstaller installed successfully")
            return True
        except subprocess.CalledProcessError:
            print("[ERROR] Failed to install PyInstaller")
            return False

def get_project_root():
    """Get the project root directory."""
    return Path(__file__).resolve().parents[2]


def get_version():
    """
    Extract version from git tag, __version__, or use timestamp.
    
    Returns:
        Version string (e.g., "2.1.0" or "2.1.0.dev20231223")
    """
    # Try to get version from git tag
    try:
        result = subprocess.run(
            ["git", "describe", "--tags", "--always", "--dirty"],
            capture_output=True,
            text=True,
            timeout=5,
            cwd=get_project_root()
        )
        if result.returncode == 0 and result.stdout.strip():
            version = result.stdout.strip()
            # Remove 'v' prefix if present
            version = re.sub(r'^v', '', version)
            # Remove commit hash suffix for clean tags
            version = re.sub(r'-g[0-9a-f]+$', '', version)
            # Remove -dirty suffix for CI/CD
            version = re.sub(r'-dirty$', '', version)
            return version
    except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.SubprocessError):
        pass
    
    # Try to get version from package __version__
    try:
        import tetraear

        if hasattr(tetraear, "__version__"):
            return tetraear.__version__
    except Exception:
        pass
    
    # Fallback to timestamp-based version
    timestamp = datetime.now().strftime("%Y%m%d")
    return f"2.1.0.dev{timestamp}"


def get_git_commit_hash():
    """Get current git commit hash (short)."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
            cwd=get_project_root()
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.SubprocessError):
        pass
    return None

def build_exe():
    """
    Build the executable.
    
    Returns:
        tuple: (success: bool, version: str, metadata: dict)
    """
    project_root = get_project_root()
    # Use the package entrypoint so `tetraear` is the app root.
    script_path = project_root / "tetraear" / "__main__.py"
    
    # Get version and metadata
    version = get_version()
    commit_hash = get_git_commit_hash()
    build_timestamp = datetime.now().isoformat()
    
    # Support environment variable overrides
    build_output_dir = os.environ.get("BUILD_OUTPUT_DIR")
    if build_output_dir:
        dist_dir = Path(build_output_dir)
    else:
        dist_dir = project_root / "dist"
    
    if not script_path.exists():
        print(f"[ERROR] {script_path} not found!")
        return False, version, {}
    
    print("=" * 60)
    print("TETRA Decoder Modern GUI - Build Script")
    print("=" * 60)
    print(f"Version: {version}")
    if commit_hash:
        print(f"Commit: {commit_hash}")
    print(f"Build Time: {build_timestamp}")
    print()
    
    # Check PyInstaller
    if not check_pyinstaller():
        return False
    
    # Prepare build directory
    build_dir = project_root / "build"
    # dist_dir already set above from environment variable or default
    
    print(f"Project root: {project_root}")
    print(f"Script: {script_path}")
    print()
    
    # Collect data files to include
    data_files = []
    
    # Determine path separator for PyInstaller (semicolon on Windows, colon on Unix)
    path_sep = ";" if sys.platform == "win32" else ":"
    
    # Helper function to normalize path for PyInstaller
    # PyInstaller prefers forward slashes even on Windows
    def normalize_path(path):
        """Convert Path object to string with forward slashes for PyInstaller."""
        return str(path).replace("\\", "/")
    
    # DLLs - use absolute paths for better reliability
    dlls = ["librtlsdr.dll", "libusb-1.0.dll"]
    dll_dir = project_root / "tetraear" / "bin"
    for dll in dlls:
        dll_path = dll_dir / dll
        if dll_path.exists():
            # PyInstaller format: source_path;destination_path
            # Use absolute path with forward slashes
            src_path = normalize_path(dll_path.absolute())
            data_files.append(f"--add-data={src_path}{path_sep}tetraear/bin")
            print(f"[OK] Including DLL: {dll}")
        else:
            print(f"[WARN] DLL not found: {dll}")
    
    # TETRA codec executables
    codec_dir = project_root / "tetraear" / "tetra_codec" / "bin"
    if codec_dir.exists():
        codec_files = list(codec_dir.glob("*.exe"))
        for codec_file in codec_files:
            # Use absolute path for source, relative path for destination
            # PyInstaller format: source_path;destination_path
            src_path = normalize_path(codec_file.absolute())
            dst_path = "tetraear/tetra_codec/bin"
            data_files.append(f"--add-data={src_path}{path_sep}{dst_path}")
            print(f"[OK] Including codec: {codec_file.name}")
    else:
        print("[WARN] Codec directory not found")

    # UI assets (icons/banner)
    assets_dir = project_root / "tetraear" / "assets"
    if assets_dir.exists():
        for asset_file in assets_dir.glob("*"):
            if not asset_file.is_file():
                continue
            src_path = normalize_path(asset_file.absolute())
            data_files.append(f"--add-data={src_path}{path_sep}tetraear/assets")
        print("[OK] Including tetraear/assets/ directory files")
    else:
        print("[WARN] tetraear/assets/ directory not found")
    
    # Python modules to include (hidden imports)
    hidden_imports = [
        "tetraear",
        "tetraear.audio.export",
        "tetraear.audio.voice",
        "tetraear.core.crypto",
        "tetraear.core.decoder",
        "tetraear.core.protocol",
        "tetraear.signal.capture",
        "tetraear.signal.processor",
        "tetraear.signal.scanner",
        "tetraear.ui.modern",
        "numpy",
        "scipy",
        "PyQt6",
        "PyQt6.QtCore",
        "PyQt6.QtGui",
        "PyQt6.QtWidgets",
        "sounddevice",
        "rtlsdr",
        "bitstring",
    ]
    
    # Build PyInstaller command
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name=TETRA_Decoder_Modern",
        "--onefile",  # Single executable file
        "--windowed",  # No console window (GUI app)
        "--clean",  # Clean cache
        "--noconfirm",  # Overwrite without asking
    ]
    
    # Add data files
    cmd.extend(data_files)
    
    # Add hidden imports
    for imp in hidden_imports:
        cmd.append(f"--hidden-import={imp}")
    
    # Add icon if available (optional)
    # Try .ico first, then .png from assets folder
    icon_path = None
    icon_ico = project_root / "tetraear" / "assets" / "icon.ico"
    icon_png = project_root / "tetraear" / "assets" / "icon_preview.png"
    
    if icon_ico.exists():
        icon_path = icon_ico
        cmd.append(f"--icon={icon_path}")
        print(f"[OK] Using icon: {icon_path}")
    elif icon_png.exists():
        # PyInstaller can use PNG files as icons
        icon_path = icon_png
        cmd.append(f"--icon={icon_path}")
        print(f"[OK] Using icon (PNG): {icon_path}")
    else:
        print("[INFO] No icon found in tetraear/assets/ directory - building without icon")
    
    # Add the main script
    cmd.append(str(script_path))
    
    print()
    print("Building executable...")
    print("Command:", " ".join(cmd))
    print()
    
    try:
        # Run PyInstaller
        result = subprocess.run(cmd, cwd=project_root, check=True)
        
        # Check if exe was created
        exe_path = dist_dir / "TETRA_Decoder_Modern.exe"
        if exe_path.exists():
            print()
            print("=" * 60)
            print("[OK] Build successful!")
            print("=" * 60)
            print(f"Executable location: {exe_path}")
            print(f"Size: {exe_path.stat().st_size / (1024*1024):.2f} MB")
            print()
            print("Note: The executable includes all dependencies.")
            print("You can distribute this single .exe file.")
            print()
            
            # Copy DLLs to dist folder (PyInstaller might not bundle them correctly)
            print("Copying additional files to dist folder...")
            for dll in dlls:
                src = dll_dir / dll
                if src.exists():
                    dst = dist_dir / dll
                    shutil.copy2(src, dst)
                    print(f"  [OK] Copied {dll}")
            
            # Copy codec directory
            if codec_dir.exists():
                codec_dst = dist_dir / "tetra_codec" / "bin"
                codec_dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copytree(codec_dir, codec_dst, dirs_exist_ok=True)
                print(f"  [OK] Copied codec directory")
            
            # Build metadata
            metadata = {
                'version': version,
                'commit_hash': commit_hash,
                'build_timestamp': build_timestamp,
                'exe_path': str(exe_path),
                'exe_size_mb': exe_path.stat().st_size / (1024*1024),
            }
            
            # Write metadata to file for CI/CD
            metadata_file = dist_dir / "build_metadata.txt"
            with open(metadata_file, 'w') as f:
                f.write(f"Version: {version}\n")
                f.write(f"Commit: {commit_hash or 'unknown'}\n")
                f.write(f"Build Time: {build_timestamp}\n")
                f.write(f"Executable: {exe_path}\n")
                f.write(f"Size: {metadata['exe_size_mb']:.2f} MB\n")
            
            return True, version, metadata
        else:
            print("[ERROR] Executable not found after build")
            return False, version, {}
            
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] Build failed with error code {e.returncode}")
        return False, version, {}
    except Exception as e:
        print(f"[ERROR] Build error: {e}")
        import traceback
        traceback.print_exc()
        return False, version, {}

def main():
    """Main entry point."""
    # Check if running in CI/CD (no TTY)
    is_ci = not sys.stdin.isatty() or os.environ.get("CI") == "true"
    
    success, version, metadata = build_exe()
    if not success:
        sys.exit(1)
    
    # In CI/CD, don't wait for user input
    if not is_ci:
        print("Press Enter to exit...")
        try:
            input()
        except:
            pass
    
    # Print version for CI/CD scripts
    if is_ci:
        print(f"BUILD_VERSION={version}")
        if metadata.get('commit_hash'):
            print(f"BUILD_COMMIT={metadata['commit_hash']}")
    
    sys.exit(0)

if __name__ == "__main__":
    main()
