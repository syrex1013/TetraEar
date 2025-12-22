# TETRA Codec – Full Windows Build & Installation Guide (MSYS2)

This guide documents **end‑to‑end building of the ETSI TETRA reference codec on Windows**
using **MSYS2 (UCRT64)** and the provided automated Python installer.

It reflects **real-world issues encountered on Windows** (line endings, proprietary tools,
legacy Makefiles) and the exact fixes applied by the installer.

---

## Overview

The installer script:

- Downloads the official ETSI codec archive
- Verifies checksum integrity
- Extracts sources
- Normalizes CRLF → LF line endings
- Fixes legacy ETSI Makefiles:
  - replaces proprietary `acc` compiler with `gcc`
  - removes `-Werror`
  - adds `-fcommon` for GCC ≥10
- Compiles codec binaries using `mingw32-make`
- Installs binaries locally

No admin rights required.  
No manual patching required.

---

## Supported Platform

| Component | Requirement |
|---------|------------|
| OS | Windows 10 / 11 (x64) |
| Shell | **MSYS2 UCRT64** |
| Compiler | GCC (mingw‑w64‑ucrt) |
| Build Tool | mingw32‑make |
| Python | mingw‑w64‑ucrt Python 3 |
| Privileges | User-level (no admin) |

---

## 1. Install MSYS2

Download MSYS2:

https://www.msys2.org/

After installation, **always launch**:

> **MSYS2 UCRT64**

Do NOT use:
- MSYS shell
- MinGW32 shell
- PowerShell / CMD

---

## 2. Install Required Packages (One‑Liner)

Run inside **UCRT64 shell**:

```bash
pacman -S --needed \
  mingw-w64-ucrt-x86_64-gcc \
  mingw-w64-ucrt-x86_64-make \
  mingw-w64-ucrt-x86_64-python \
  patch \
  unzip \
  ca-certificates
```

Update certificates:

```bash
update-ca-trust
```

---

## 3. Verify Environment

```bash
gcc --version
mingw32-make --version
python --version
patch --version
unzip -v | head -n 1
```

Expected paths:

```
/ucrt64/bin/gcc
/ucrt64/bin/mingw32-make
/ucrt64/bin/python
/usr/bin/patch
/usr/bin/unzip
```

---

## 4. Repository Layout

```
Tetra/
├── install_tetra_codec.py
├── install_codec.md
└── tetra_codec/        (created automatically)
```

Nothing else is required.

---

## 5. Build & Install

```bash
cd /c/Users/<username>/path/to/Tetra
python install_tetra_codec.py
```

The script handles all required fixes automatically.

---

## 6. ETSI Source Structure (Reference)

The ETSI archive contains uppercase directories:

```
AMR-Code/
C-CODE/
C-WORD/
``>

This is normal and handled by the installer.

---

## 7. Output Binaries

After successful build:

```
./tetra_codec/bin/
├── sdecoder.exe
├── scoder.exe
├── cdecoder.exe
└── ccoder.exe
```

Binaries are portable and may be copied elsewhere.

---

## 8. Common Errors & Fixes

### Python not found
You are not in UCRT64 or Python not installed.

```bash
pacman -S mingw-w64-ucrt-x86_64-python
```

---

### SSL certificate verification failed
Certificates missing.

```bash
pacman -S ca-certificates
update-ca-trust
```

---

### acc: command not found
Expected. ETSI uses a proprietary compiler.

Automatically replaced with `gcc` by installer.

---

### No targets specified and no makefile found
Handled by explicitly passing `-f MAKEFILE`.

No action needed.

---

## 9. ETSI Licensing Notice

- ETSI codec is provided for **interoperability and research**
- Usage may be restricted by ETSI terms
- You are responsible for license compliance

---

## 10. Verified Build Configuration

Successfully tested with:

- Windows 11 x64
- MSYS2 UCRT64
- GCC 13+
- Python 3.12
- mingw32-make

---

## Success Indicator

If you see:

```
[SUCCESS] Codec installed
```

the build completed correctly.

---

## Optional Next Steps

- Integrate with **OpenEar**
- Use with **tetra-rx**
- Package binaries into ZIP
- Add GitHub Actions CI (Windows)

---

Maintained by **Adrian Dacka**
