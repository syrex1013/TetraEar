"""
Create release package script.
Packages the built executable and required files into a zip archive.
"""

import os
import sys
import shutil
import zipfile
from pathlib import Path
from datetime import datetime


def get_project_root():
    """Get the project root directory."""
    return Path(__file__).resolve().parents[2]


def get_version_from_metadata(dist_dir):
    """Extract version from build metadata file."""
    metadata_file = dist_dir / "build_metadata.txt"
    if metadata_file.exists():
        with open(metadata_file, 'r') as f:
            for line in f:
                if line.startswith("Version:"):
                    return line.split(":", 1)[1].strip()
    # Fallback to timestamp
    return datetime.now().strftime("%Y%m%d")


def create_release_package():
    """
    Create release package zip file.
    
    Returns:
        tuple: (success: bool, zip_path: Path, version: str)
    """
    project_root = get_project_root()
    dist_dir = project_root / "dist"
    release_dir = project_root / "release"
    
    # Get version
    version = get_version_from_metadata(dist_dir)
    
    # Check if executable exists
    exe_path = dist_dir / "TETRA_Decoder_Modern.exe"
    if not exe_path.exists():
        print(f"[ERROR] Executable not found: {exe_path}")
        return False, None, version
    
    print("=" * 60)
    print("Creating Release Package")
    print("=" * 60)
    print(f"Version: {version}")
    print()
    
    # Create a clean release directory (deterministic output)
    if release_dir.exists():
        shutil.rmtree(release_dir)
    release_dir.mkdir(parents=True, exist_ok=True)
    
    # Copy files to release directory
    print("Copying files to release directory...")
    
    # Copy executable
    release_exe = release_dir / "TETRA_Decoder_Modern.exe"
    shutil.copy2(exe_path, release_exe)
    print(f"  [OK] Copied executable")
    
    # Copy DLLs
    dlls = ["librtlsdr.dll", "libusb-1.0.dll"]
    for dll in dlls:
        src = dist_dir / dll
        if src.exists():
            dst = release_dir / dll
            shutil.copy2(src, dst)
            print(f"  [OK] Copied {dll}")
        else:
            # Try source tree location
            src = project_root / "tetraear" / "bin" / dll
            if src.exists():
                dst = release_dir / dll
                shutil.copy2(src, dst)
                print(f"  [OK] Copied {dll} from source tree")
            else:
                print(f"  [WARN] DLL not found: {dll}")
    
    # Copy codec directory
    codec_src = dist_dir / "tetra_codec" / "bin"
    if not codec_src.exists():
        codec_src = project_root / "tetraear" / "tetra_codec" / "bin"
    
    if codec_src.exists():
        codec_dst = release_dir / "tetra_codec" / "bin"
        codec_dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(codec_src, codec_dst, dirs_exist_ok=True)
        print(f"  [OK] Copied codec directory")
    else:
        print(f"  [WARN] Codec directory not found")
    
    # Copy README files
    if (project_root / "README.md").exists():
        shutil.copy2(project_root / "README.md", release_dir / "README.md")
        print("  [OK] Copied README.md")

    if (project_root / "CHANGELOG.md").exists():
        shutil.copy2(project_root / "CHANGELOG.md", release_dir / "CHANGELOG.md")
        print("  [OK] Copied CHANGELOG.md")

    if (project_root / "RELEASE_NOTES.md").exists():
        shutil.copy2(project_root / "RELEASE_NOTES.md", release_dir / "RELEASE_NOTES.md")
        print("  [OK] Copied RELEASE_NOTES.md")

    if (project_root / "keys.example.txt").exists():
        shutil.copy2(project_root / "keys.example.txt", release_dir / "keys.example.txt")
        print("  [OK] Copied keys.example.txt")
    
    # Create a basic README.txt (Windows-friendly quick start)
    release_readme = release_dir / "README.txt"
    with open(release_readme, "w", encoding="utf-8") as f:
        f.write("TetraEar - Windows Binary\n")
        f.write(f"Version: {version}\n\n")
        f.write("Usage:\n")
        f.write("  - Run TETRA_Decoder_Modern.exe\n\n")
        f.write("Files:\n")
        f.write("  - README.md          (full documentation)\n")
        f.write("  - CHANGELOG.md       (full history)\n")
        f.write("  - RELEASE_NOTES.md   (what changed)\n")
        f.write("  - keys.example.txt   (key file format example)\n")
    print("  [OK] Wrote README.txt")
    
    # Validate required files
    print()
    print("Validating release package...")
    required_files = [
        release_dir / "TETRA_Decoder_Modern.exe",
    ]
    
    missing_files = []
    for file_path in required_files:
        if not file_path.exists():
            missing_files.append(file_path.name)
    
    if missing_files:
        print(f"[ERROR] Missing required files: {', '.join(missing_files)}")
        return False, None, version
    
    print("  [OK] All required files present")
    
    # Create zip file
    zip_name = f"TetraEar-v{version}-Windows.zip"
    zip_path = project_root / zip_name
    
    print()
    print(f"Creating zip archive: {zip_name}")
    
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        # Add all files from release directory
        for file_path in release_dir.rglob('*'):
            if file_path.is_file():
                arcname = file_path.relative_to(release_dir)
                zipf.write(file_path, arcname)
                print(f"  [OK] Added {arcname}")
    
    zip_size_mb = zip_path.stat().st_size / (1024 * 1024)
    
    print()
    print("=" * 60)
    print("[OK] Release package created successfully!")
    print("=" * 60)
    print(f"Zip file: {zip_path}")
    print(f"Size: {zip_size_mb:.2f} MB")
    print()
    
    return True, zip_path, version


def main():
    """Main entry point."""
    success, zip_path, version = create_release_package()
    if not success:
        sys.exit(1)
    
    # Print version for CI/CD scripts
    if os.environ.get("CI") == "true" or not sys.stdin.isatty():
        print(f"RELEASE_VERSION={version}")
        print(f"RELEASE_ZIP={zip_path}")
    
    sys.exit(0)


if __name__ == "__main__":
    main()
