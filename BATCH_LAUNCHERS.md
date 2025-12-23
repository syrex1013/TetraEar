# TETRA Decoder Pro - Batch File Launchers

This directory contains Windows batch file launchers for TETRA Decoder Pro that automatically compile Python bytecode and run the application.

## Available Launchers

### 1. `run_tetraear.bat` - Quick Launch (Recommended)

Simple launcher that compiles and runs the GUI application.

**Usage:**
```batch
run_tetraear.bat
```

**What it does:**
- Checks Python installation
- Activates virtual environment (if available)
- Compiles Python modules to bytecode (.pyc) for faster startup
- Launches the GUI application

---

### 2. `run_tetraear_advanced.bat` - Advanced Launch with Options

Full-featured launcher with command-line options support.

**Usage:**
```batch
run_tetraear_advanced.bat [OPTIONS]
```

**Options:**
- `--cli`, `--no-gui` - Run in CLI mode without GUI
- `-f FREQ`, `--frequency FREQ` - Set frequency in MHz (e.g., 392.225)
- `--auto-start` - Auto-start capture on launch
- `-m`, `--monitor-audio` - Enable audio monitoring on start
- `-v`, `--verbose` - Enable verbose logging
- `-h`, `--help` - Show help message

**Examples:**

Launch GUI normally:
```batch
run_tetraear_advanced.bat
```

Launch with frequency and auto-start:
```batch
run_tetraear_advanced.bat -f 392.225 --auto-start
```

Run in CLI mode with audio monitoring:
```batch
run_tetraear_advanced.bat --cli -f 390.865 -m
```

Launch with verbose logging:
```batch
run_tetraear_advanced.bat -v -f 392.225 --auto-start -m
```

**What it does:**
- All features of `run_tetraear.bat`
- Checks and installs dependencies if missing
- Optimizes bytecode with -OO flag
- Passes command-line arguments to the application
- Supports all application features from command line

---

### 3. `run_tetraear_silent.bat` - Silent Launch (For Shortcuts)

Minimal-output launcher ideal for desktop shortcuts. Starts the application in a new window with minimal console output.

**Usage:**
```batch
run_tetraear_silent.bat
```

**What it does:**
- Silently checks Python and activates venv
- Compiles modules without output
- Launches app in a new window titled "TETRA Decoder Pro"
- Console closes immediately after starting the app

**Best for:**
- Desktop shortcuts
- Taskbar pinning
- Start menu shortcuts
- Clean user experience

---

## Benefits of Using Batch Launchers

### Performance
- **Faster Startup**: Pre-compiled bytecode (.pyc files) load faster than source .py files
- **Optimization**: Advanced launcher uses Python's `-OO` flag for optimized bytecode
- **Caching**: Subsequent runs are even faster as bytecode is cached

### Convenience
- **One-Click Launch**: Double-click to start the application
- **Environment Setup**: Automatically activates virtual environment
- **Error Handling**: Shows clear error messages if something goes wrong
- **Dependency Check**: Advanced launcher verifies and installs dependencies

### Desktop Integration
You can create a shortcut to either batch file on your desktop:
1. Right-click on the batch file
2. Select "Create shortcut"
3. Move shortcut to Desktop
4. (Optional) Right-click shortcut → Properties → Change Icon

---

## Troubleshooting

### "Python is not installed or not in PATH"
- Make sure Python 3.8+ is installed
- Add Python to your system PATH
- Or activate your virtual environment manually first

### "Failed to install dependencies"
- Run manually: `pip install -r requirements.txt`
- Check your internet connection
- Ensure you have write permissions

### Application fails to start
- Check logs in the `logs/` directory
- Run with `--verbose` flag for detailed output
- Try running directly: `python -m tetraear`

---

## Notes

- Both batch files check for a `.venv` virtual environment
- Compilation errors are non-fatal and the app will still run
- The advanced launcher creates optimized bytecode for best performance
- Bytecode files are stored in `__pycache__` directories

---

## For Developers

To force recompilation (e.g., after code changes):
```batch
python -m compileall -f tetraear\
```

To clean bytecode cache:
```batch
python -c "import pathlib, shutil; [shutil.rmtree(p) for p in pathlib.Path('.').rglob('__pycache__')]"
```
