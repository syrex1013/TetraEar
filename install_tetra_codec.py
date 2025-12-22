#!/usr/bin/env python3
"""
TETRA Codec Installer (Windows / MSYS2)
Original bash script by sq5bpf – Python port

Requirements (MSYS2):
  pacman -S mingw-w64-x86_64-gcc make patch unzip

Output:
  ./tetra_codec/bin/*.exe
"""

import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.request
import zipfile
import ssl
import re
ssl._create_default_https_context = ssl._create_unverified_context

# ================= CONFIG =================

URL = "http://www.etsi.org/deliver/etsi_en/300300_300399/30039502/01.03.01_60/en_30039502v010301p0.zip"
CODECSUM = "a8115fe68ef8f8cc466f4192572a1e3e"

BASE_DIR = os.path.abspath("tetra_codec")
INSTALL_DIR = os.path.join(BASE_DIR, "bin")

CODEC_FILE = os.path.basename(URL)
SCRIPT_VERSION = "1.1"

WORK_DIR = tempfile.mkdtemp(prefix="tetra-codec-")

# ==========================================
def normalize_line_endings(root):
    print("[*] Normalizing line endings (CRLF → LF)...")
    for dirpath, _, filenames in os.walk(root):
        for name in filenames:
            if name.endswith((".c", ".h", "makefile", "Makefile")):
                path = os.path.join(dirpath, name)
                try:
                    with open(path, "rb") as f:
                        data = f.read()
                    data = data.replace(b"\r\n", b"\n")
                    with open(path, "wb") as f:
                        f.write(data)
                except Exception:
                    pass

def fix_makefiles(root):
    print("[*] Adjusting Makefiles for modern GCC...")
    for dirpath, _, filenames in os.walk(root):
        for name in filenames:
            if name.lower() == "makefile":
                path = os.path.join(dirpath, name)

                with open(path, "r", encoding="utf-8", errors="ignore") as f:
                    data = f.read()

                # Replace ACC variable if present
                data = re.sub(r'(?m)^ACC\s*=\s*acc\b', 'ACC = gcc', data)

                # Replace acc command at line start (after tabs/spaces)
                data = re.sub(r'(?m)^(\s*)acc\b', r'\1gcc', data)

                # Replace inline acc usage (safety net)
                data = re.sub(r'\bacc\b', 'gcc', data)

                # Add -fcommon for GCC 10+
                if "-fcommon" not in data:
                    data = re.sub(r'(?m)^CFLAGS\s*=\s*(.*)$',
                                  r'CFLAGS = -fcommon \1',
                                  data)

                # Remove -Werror
                data = data.replace("-Werror", "")

                with open(path, "w", encoding="utf-8") as f:
                    f.write(data)


def fail(msg):
    print(f"[ERROR] {msg}")
    sys.exit(1)



def check_prerequisites():
    print("[*] Checking MSYS2 toolchain...")

    if shutil.which("gcc") is None:
        fail("Missing required tool in PATH: gcc")

    if shutil.which("make") is None and shutil.which("mingw32-make") is None:
        fail("Missing required tool in PATH: make or mingw32-make")

    if shutil.which("patch") is None:
        fail("Missing required tool in PATH: patch")



def download_codec():
    if os.path.exists(CODEC_FILE):
        print(f"[*] Using existing codec archive: {CODEC_FILE}")
        return

    print(f"[*] Downloading codec from ETSI")
    try:
        urllib.request.urlretrieve(URL, CODEC_FILE)
    except Exception as e:
        fail(f"Download failed: {e}")


def check_codec_checksum():
    print("[*] Verifying checksum...")
    md5 = hashlib.md5()
    with open(CODEC_FILE, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            md5.update(chunk)

    digest = md5.hexdigest()
    if digest != CODECSUM:
        os.remove(CODEC_FILE)
        fail(f"Checksum mismatch: {digest} (expected {CODECSUM})")

    print("[+] Checksum OK")


def unzip_codec():
    print(f"[*] Extracting codec to {WORK_DIR}")
    with zipfile.ZipFile(CODEC_FILE, "r") as z:
        z.extractall(WORK_DIR)


def apply_patch():
    patch_file = os.path.abspath("codec.diff")
    if not os.path.isfile(patch_file):
        fail("codec.diff not found in current directory")

    print("[*] Applying patch...")
    subprocess.check_call(
        ["patch", "-p1", "-N", "-E"],
        cwd=WORK_DIR,
        stdin=open(patch_file, "rb"),
    )


def compile_codec():
    etsi_root = find_etsi_root(WORK_DIR)

    c_code_dir = None
    for d in os.listdir(etsi_root):
        if d.lower() == "c-code":
            c_code_dir = os.path.join(etsi_root, d)
            break

    if not c_code_dir:
        fail("C-CODE directory not found")

    make_cmd = find_make()

    makefile_path = None
    for f in os.listdir(c_code_dir):
        if f.lower() == "makefile":
            makefile_path = f
            break

    if not makefile_path:
        fail("Makefile not found in C-CODE directory")

    print(f"[*] Compiling codec ({make_cmd} -f {makefile_path}) in {c_code_dir} ...")
    subprocess.check_call(
        [make_cmd, "-f", makefile_path],
        cwd=c_code_dir
    )




def find_etsi_root(root):
    for dirpath, dirnames, _ in os.walk(root):
        for d in dirnames:
            if d.lower() == "c-code":
                return dirpath
    fail("ETSI source root directory not found (no C-CODE directory)")




def install_codec():
    etsi_root = find_etsi_root(WORK_DIR)

    c_code_dir = None
    for d in os.listdir(etsi_root):
        if d.lower() == "c-code":
            c_code_dir = os.path.join(etsi_root, d)
            break

    if not c_code_dir:
        fail("C-CODE directory not found")

    print("[*] Installing binaries to ./tetra_codec/bin")
    os.makedirs(INSTALL_DIR, exist_ok=True)

    wanted = {
        "sdecoder": None,
        "scoder": None,
        "cdecoder": None,
        "ccoder": None,
    }

    # scan produced files
    for f in os.listdir(c_code_dir):
        name = f.lower()
        if name.endswith(".exe"):
            base = name.replace(".exe", "")
            if base in wanted:
                wanted[base] = f

    missing = [k for k, v in wanted.items() if v is None]
    if missing:
        fail(f"Missing binaries after build: {', '.join(missing)}")

    for base, src_name in wanted.items():
        src = os.path.join(c_code_dir, src_name)
        dst = os.path.join(INSTALL_DIR, base + ".exe")
        shutil.copy2(src, dst)
        print(f"  + {dst}")




def find_make():
    if shutil.which("make"):
        return "make"
    if shutil.which("mingw32-make"):
        return "mingw32-make"
    fail("Neither make nor mingw32-make found in PATH")


def cleanup():
    print("[*] Cleaning up build directory")
    shutil.rmtree(WORK_DIR, ignore_errors=True)


def check_install():
    for f in ("sdecoder.exe", "scoder.exe", "cdecoder.exe", "ccoder.exe"):
        if not os.path.isfile(os.path.join(INSTALL_DIR, f)):
            return False
    return True


def main():
    print(f"====== TETRA Codec Installer v{SCRIPT_VERSION} (MSYS2) ======")

    check_prerequisites()
    download_codec()
    check_codec_checksum()
    unzip_codec()
    normalize_line_endings(WORK_DIR)
    fix_makefiles(WORK_DIR)
    #apply_patch()
    compile_codec()
    install_codec()
    cleanup()

    if check_install():
        print("[SUCCESS] Codec installed in ./tetra_codec/bin")
    else:
        fail("Installation verification failed")


if __name__ == "__main__":
    main()
