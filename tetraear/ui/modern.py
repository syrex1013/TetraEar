"""
Modern TETRA Decoder GUI with Waterfall Spectrum.

This module lives under `tetraear.ui` and is the primary application UI.
"""

from __future__ import annotations

from collections import deque
from datetime import datetime
from pathlib import Path
import sys
import threading
import queue
import logging
import os
import colorama
from colorama import Fore, Back, Style

def _get_runtime_root() -> Path:
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        return Path(meipass)
    return Path(__file__).resolve().parents[2]


def _get_user_data_dir() -> Path:
    override = os.environ.get("TETRAEAR_DATA_DIR")
    if override:
        return Path(override)
    base = os.environ.get("APPDATA") or os.environ.get("LOCALAPPDATA")
    if base:
        return Path(base) / "TetraEar"
    return Path.home() / ".tetraear"


RUNTIME_ROOT = _get_runtime_root()
USER_DATA_DIR = _get_user_data_dir()

# Keep logs/records configurable and predictable for both source runs and bundled builds.
def _get_records_dir() -> Path:
    override = os.environ.get("TETRAEAR_RECORDS_DIR")
    if override:
        return Path(override)
    if getattr(sys, "_MEIPASS", None):
        return USER_DATA_DIR / "records"
    return RUNTIME_ROOT / "records"

# Assets live under the package (`tetraear/assets`) in source and in PyInstaller.
_pkg_root = Path(__file__).resolve().parents[1]
_bundled_assets = RUNTIME_ROOT / "tetraear" / "assets"
ASSETS_DIR = _bundled_assets if _bundled_assets.exists() else (_pkg_root / "assets")
RECORDS_DIR = _get_records_dir()
RECORDS_DIR.mkdir(parents=True, exist_ok=True)

# Add DLL path for RTL-SDR libraries
for dll_path in (RUNTIME_ROOT / "tetraear" / "bin", RUNTIME_ROOT / "dist", RUNTIME_ROOT):
    if dll_path.exists():
        os.environ["PATH"] = str(dll_path) + os.pathsep + os.environ.get("PATH", "")
        if hasattr(os, "add_dll_directory"):
            try:
                os.add_dll_directory(str(dll_path))
            except OSError:
                pass

# Initialize colorama for Windows support
colorama.init(autoreset=True)

class ColoredFormatter(logging.Formatter):
    """Custom formatter with colors for console output."""
    
    COLORS = {
        'DEBUG': Fore.CYAN,
        'INFO': Fore.GREEN,
        'WARNING': Fore.YELLOW,
        'ERROR': Fore.RED,
        'CRITICAL': Fore.RED + Back.WHITE + Style.BRIGHT
    }
    
    def format(self, record):
        # Add color to level name for console
        if hasattr(sys.stdout, 'isatty') and sys.stdout.isatty():
            levelname = record.levelname
            if levelname in self.COLORS:
                record.levelname = f"{self.COLORS[levelname]}{levelname}{Style.RESET_ALL}"
        return super().format(record)


class _PrefixFilter(logging.Filter):
    def __init__(self, *prefixes: str):
        super().__init__()
        self._prefixes = tuple(p for p in prefixes if p)

    def filter(self, record: logging.LogRecord) -> bool:
        return record.name.startswith(self._prefixes) if self._prefixes else True


_RUN_ID = datetime.now().strftime("%Y%m%d_%H%M%S")


def _get_log_dir() -> Path:
    override = os.environ.get("TETRAEAR_LOG_DIR")
    if override:
        return Path(override)
    # In PyInstaller builds, write logs to user data. In source runs, keep logs in repo-local `logs/`.
    if getattr(sys, "_MEIPASS", None):
        return USER_DATA_DIR / "logs"
    return RUNTIME_ROOT / "logs"


def _setup_logging(verbose: bool) -> dict[str, Path]:
    """
    Configure structured logging for the application.

    Creates multiple log files under the logs directory:
      - `tetraear_<run>.log`   (everything)
      - `app_<run>.log`       (UI + capture/signal pipeline)
      - `decoder_<run>.log`   (decoder/protocol)
      - `codec_<run>.log`     (codec calls + stdout/stderr)
      - `audio_<run>.log`     (recording + audio pipeline)
      - `frames_<run>.log`    (frames table rows as JSONL)
    """
    log_dir = _get_log_dir()
    log_dir.mkdir(parents=True, exist_ok=True)

    files = {
        "all": log_dir / f"tetraear_{_RUN_ID}.log",
        "app": log_dir / f"app_{_RUN_ID}.log",
        "decoder": log_dir / f"decoder_{_RUN_ID}.log",
        "codec": log_dir / f"codec_{_RUN_ID}.log",
        "audio": log_dir / f"audio_{_RUN_ID}.log",
        "frames": log_dir / f"frames_{_RUN_ID}.log",
    }

    fmt = logging.Formatter("%(asctime)s.%(msecs)03d [%(levelname)s] %(name)s: %(message)s", "%Y-%m-%d %H:%M:%S")

    def make_file_handler(path: Path, *, level: int = logging.DEBUG, filt: logging.Filter | None = None) -> logging.Handler:
        handler = logging.FileHandler(str(path), encoding="utf-8", delay=True)
        handler.setLevel(level)
        handler.setFormatter(fmt)
        if filt is not None:
            handler.addFilter(filt)
        return handler

    all_handler = make_file_handler(files["all"])
    app_handler = make_file_handler(files["app"], filt=_PrefixFilter("tetraear.ui.modern", "tetraear.signal"))
    decoder_handler = make_file_handler(files["decoder"], filt=_PrefixFilter("tetraear.core.decoder", "tetraear.core.protocol"))
    codec_handler = make_file_handler(files["codec"], filt=_PrefixFilter("tetraear.codec"))
    audio_handler = make_file_handler(files["audio"], filt=_PrefixFilter("tetraear.recording", "tetraear.audio"))
    frames_handler = make_file_handler(files["frames"], level=logging.INFO, filt=_PrefixFilter("tetraear.frames"))

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG if verbose else logging.INFO)
    console_handler.setFormatter(ColoredFormatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    root.handlers.clear()
    root.addHandler(all_handler)
    root.addHandler(app_handler)
    root.addHandler(decoder_handler)
    root.addHandler(codec_handler)
    root.addHandler(audio_handler)
    root.addHandler(frames_handler)
    root.addHandler(console_handler)

    # Route `warnings.warn(...)` through logging too.
    logging.captureWarnings(True)

    return files


logger = logging.getLogger(__name__)
audio_logger = logging.getLogger("tetraear.recording")
frames_logger = logging.getLogger("tetraear.frames")

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QTextEdit, QComboBox, QSpinBox,
    QGroupBox, QCheckBox, QTabWidget, QTableWidget, QTableWidgetItem,
    QProgressBar, QSlider, QFileDialog, QMessageBox, QSplitter, QFrame,
    QScrollArea, QSizePolicy, QHeaderView, QDialog
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QThread, pyqtSlot, QSize, QRect, QObject
from PyQt6.QtGui import QFont, QColor, QPalette, QPainter, QLinearGradient, QPen, QBrush, QPixmap, QImage, QPainterPath, QIcon

import numpy as np
import sounddevice as sd
from scipy.signal import resample
import subprocess
import tempfile

from tetraear.signal.capture import RTLCapture
from tetraear.signal.processor import SignalProcessor
from tetraear.core.decoder import TetraDecoder
from tetraear.core.crypto import TetraKeyManager
from tetraear.core.mcc_mnc import get_location_info
from tetraear.core.validator import TetraSignalValidator
from tetraear.core.location import LocationParser
from tetraear.signal.scanner import FrequencyScanner
from tetraear.audio.voice import VoiceProcessor


def _is_readable_text(text: str) -> bool:
    """Check if text is actually human-readable (not garbled GSM7/encrypted)."""
    if not text or len(text) < 3:
        return False
    
    # Remove common prefixes and quotes
    clean = text
    for prefix in ['[GSM7]', '[TXT]', '[SDS]', '[SDS-1]', '[SDS-GSM]', '[LIP]', '[LOC]', '[GPS]', '[BIN-ENC]', '[BIN]', '💬', '🧩', '"']:
        clean = clean.replace(prefix, '')
    clean = clean.strip()
    
    if len(clean) < 3:
        return False
    
    # Check for GSM7 special characters that indicate garbled text (expanded)
    gsm7_specials = set('ΩΔΣΘΞΛΓΦΨΠåæÅÆØøÇÉÑÜßìÌíÍîÎïÏòÒóÓôÔõÕöÖùÙúÚûÛüÜ¿¡¢£¤¥¦§¨©ª«¬®¯°±²³´µ¶·¸¹º»¼½¾')
    special_count = sum(1 for c in clean if c in gsm7_specials)
    
    # If ANY special characters, it's likely garbled (very strict)
    if special_count > 0:
        return False
    
    # Check for high-byte characters that aren't in normal text
    high_byte_count = sum(1 for c in clean if ord(c) > 127)
    if len(clean) > 0 and high_byte_count / len(clean) > 0.05:
        return False
    
    # Check for non-printable ASCII characters
    control_chars = sum(1 for c in clean if ord(c) < 32 and c not in '\n\r\t')
    if control_chars > 0:
        return False
    
    # Check for ASCII alphanumeric content or spaces
    ascii_readable = sum(1 for c in clean if (c.isalnum() or c.isspace()) and ord(c) < 128)
    
    # Need at least 70% ASCII readable characters (very strict)
    if len(clean) > 0 and ascii_readable / len(clean) < 0.70:
        return False
    
    # Check for minimum alphanumeric content
    alnum_count = sum(1 for c in clean if c.isalnum())
    if len(clean) > 0 and alnum_count / len(clean) < 0.50:
        return False
    
    # Check for reasonable word structure - should have some spaces or clear word boundaries
    # If it's random gibberish, it won't have natural word patterns
    if len(clean) > 10:
        # Count lowercase letters (natural text has many)
        lowercase_count = sum(1 for c in clean if c.islower())
        if lowercase_count / len(clean) < 0.20:  # Less than 20% lowercase = suspicious
            return False
        
        # Check for word-like patterns (letters with spaces)
        words = clean.split()
        if len(words) > 1:
            # Check if "words" look reasonable (mostly letters)
            valid_words = sum(1 for w in words if len(w) > 0 and sum(1 for c in w if c.isalpha()) / len(w) > 0.5)
            if valid_words / len(words) < 0.5:
                return False
    elif len(clean) <= 10:
        # For short strings, be extra strict
        # Must have at least one lowercase letter
        if not any(c.islower() for c in clean):
            # Exception for short status codes like "OK", "ACK", etc.
            if not (len(clean) <= 4 and clean.isupper() and clean.isalpha()):
                return False
    
    return True


def _format_location_data(frame: dict) -> str:
    """Format location data nicely."""
    text = frame.get('decoded_text', '') or frame.get('sds_message', '')
    
    if '[LIP]' in text or '[LOC]' in text:
        # Try to parse latitude/longitude
        if 'Lat:' in text and 'Lon:' in text:
            return f"📍 {text}"
        else:
            # Just hex location data
            hex_data = text.split(':', 1)[-1].strip() if ':' in text else text
            return f"📍 Location Data: {hex_data[:40]}..."
    
    if '[GPS]' in text:
        return f"🛰️ {text}"
    
    return None


def _format_binary_metadata(frame: dict) -> str:
    """Format binary metadata and control frames."""
    if '[BIN-ENC]' in str(frame.get('decoded_text', '')):
        # This is encrypted binary data
        text = frame.get('decoded_text', '')
        if 'bytes' in text:
            # Extract byte count
            return f"🔐 Encrypted Binary Data ({text})"
        return "🔐 Encrypted Binary Data"
    
    # Check for control frame types
    type_name = frame.get('type_name', '')
    if type_name == 'MAC-RESOURCE':
        info = frame.get('additional_info', {})
        if info.get('talkgroup'):
            return f"📡 Resource Allocation: TG {info['talkgroup']}"
        return "📡 Resource Allocation"
    
    if type_name == 'MAC-BROADCAST':
        info = frame.get('additional_info', {})
        desc = info.get('description', '')
        if 'Broadcast' in desc or 'info' in desc.lower():
            return f"📢 Network Broadcast: {desc}"
        return "📢 Network Broadcast"
    
    if type_name in ['MAC-FRAG', 'MAC-END/RES']:
        return f"🔗 {type_name} (Fragment/Control)"
    
    return None


import json

class SettingsManager:
    """Manage application settings."""
    
    DEFAULT_SETTINGS = {
        "save_silence": False,
        "export_mp3": False,
        "auto_decrypt": True,
        "monitor_audio": False,
        "monitor_raw": False,
        "gain": 50.0,
        "sample_rate": 2.4e6,
        "last_frequency": 390.865,
        "bandwidth": 25000,
        "zoom_level": 1.0,
        "noise_floor": -85,
        "theme": "dark"
    }
    
    def __init__(self, filename="settings.json"):
        USER_DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.filename = str(USER_DATA_DIR / filename)
        self.settings = self.DEFAULT_SETTINGS.copy()
        self.load()
        
    def load(self):
        """Load settings from file."""
        try:
            if os.path.exists(self.filename):
                with open(self.filename, 'r') as f:
                    loaded = json.load(f)
                    self.settings.update(loaded)
        except Exception as e:
            logger.error(f"Failed to load settings: {e}")
            
    def save(self):
        """Save settings to file."""
        try:
            with open(self.filename, 'w') as f:
                json.dump(self.settings, f, indent=4)
        except Exception as e:
            logger.error(f"Failed to save settings: {e}")
            
    def get(self, key, default=None):
        return self.settings.get(key, default)
        
    def set(self, key, value):
        self.settings[key] = value

class FrequencyManager:
    """Manage saved frequencies."""
    
    def __init__(self, filename="frequencies.json"):
        USER_DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.filename = str(USER_DATA_DIR / filename)
        self.frequencies = []
        self.load()
        
    def load(self):
        """Load frequencies from file."""
        try:
            if os.path.exists(self.filename):
                with open(self.filename, 'r') as f:
                    self.frequencies = json.load(f)
            else:
                # Defaults
                self.frequencies = [
                    {"freq": 390.000, "label": "TETRA PL 1", "desc": "Poland Public Safety"},
                    {"freq": 392.500, "label": "TETRA PL 2", "desc": "Poland Public Safety"},
                    {"freq": 420.000, "label": "TETRA EU", "desc": "Europe General"},
                ]
        except Exception as e:
            logger.error(f"Failed to load frequencies: {e}")
            
    def save(self):
        """Save frequencies to file."""
        try:
            with open(self.filename, 'w') as f:
                json.dump(self.frequencies, f, indent=4)
        except Exception as e:
            logger.error(f"Failed to save frequencies: {e}")
            
    def add(self, freq, label, desc=""):
        self.frequencies.append({"freq": freq, "label": label, "desc": desc})
        self.save()
        
    def get_all(self):
        return self.frequencies

class SettingsDialog(QDialog):
    """Settings configuration dialog."""
    
    def __init__(self, settings_manager, parent=None):
        super().__init__(parent)
        self.settings = settings_manager
        self.setWindowTitle("Settings")
        self.setMinimumWidth(400)
        self.init_ui()
        self.apply_style()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # Recording Settings
        rec_group = QGroupBox("Recording")
        rec_layout = QVBoxLayout()
        
        self.save_silence_cb = QCheckBox("Save Silent Audio Files")
        self.save_silence_cb.setChecked(self.settings.get("save_silence", False))
        self.save_silence_cb.setToolTip("If unchecked, .wav files with no voice activity will be deleted.")
        rec_layout.addWidget(self.save_silence_cb)

        self.export_mp3_cb = QCheckBox("Export MP3 (requires ffmpeg)")
        self.export_mp3_cb.setChecked(self.settings.get("export_mp3", False))
        self.export_mp3_cb.setToolTip("If enabled, finished voice recordings are converted to .mp3 using ffmpeg if available.")
        rec_layout.addWidget(self.export_mp3_cb)
        
        rec_group.setLayout(rec_layout)
        layout.addWidget(rec_group)
        
        # Audio Settings
        audio_group = QGroupBox("Audio")
        audio_layout = QVBoxLayout()
        
        # Audio Device Selection
        audio_layout.addWidget(QLabel("Output Device:"))
        self.audio_device_combo = QComboBox()
        self.audio_device_combo.addItem("Default", None)
        
        # Populate audio devices
        try:
            devices = sd.query_devices()
            default_output = sd.default.device[1]
            for i, dev in enumerate(devices):
                if dev['max_output_channels'] > 0:
                    name = dev['name']
                    if i == default_output:
                        name += " (Default)"
                    self.audio_device_combo.addItem(name, i)
                    
            # Select current device
            current_device = self.settings.get("audio_device", None)
            if current_device is not None:
                index = self.audio_device_combo.findData(current_device)
                if index >= 0:
                    self.audio_device_combo.setCurrentIndex(index)
        except Exception as e:
            logger.error(f"Failed to query audio devices: {e}")
            
        audio_layout.addWidget(self.audio_device_combo)
        audio_group.setLayout(audio_layout)
        layout.addWidget(audio_group)
        
        # Appearance Settings
        app_group = QGroupBox("Appearance")
        app_layout = QVBoxLayout()
        
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["Dark (Default)", "Light", "High Contrast"])
        current_theme = self.settings.get("theme", "Dark (Default)")
        self.theme_combo.setCurrentText(current_theme)
        
        app_layout.addWidget(QLabel("Theme:"))
        app_layout.addWidget(self.theme_combo)
        app_group.setLayout(app_layout)
        layout.addWidget(app_group)
        
        # Buttons
        btn_layout = QHBoxLayout()
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self.save_settings)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        
        btn_layout.addStretch()
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(save_btn)
        layout.addLayout(btn_layout)
        
    def save_settings(self):
        self.settings.set("save_silence", self.save_silence_cb.isChecked())
        self.settings.set("export_mp3", self.export_mp3_cb.isChecked())
        self.settings.set("audio_device", self.audio_device_combo.currentData())
        self.settings.set("theme", self.theme_combo.currentText())
        self.settings.save()
        self.accept()
        
    def apply_style(self):
        self.setStyleSheet("""
            QDialog { background-color: #0a0a0f; color: #fafafa; }
            QGroupBox { border: 1px solid #2a2a3a; border-radius: 8px; margin-top: 8px; padding: 12px; background-color: #1a1a24; }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 6px; color: #a1a1aa; }
            QCheckBox { color: #fafafa; spacing: 8px; }
            QPushButton { background-color: #1a1a24; color: #fafafa; border: 1px solid #2a2a3a; border-radius: 6px; padding: 8px 16px; }
            QPushButton:hover { background-color: #2a2a3a; }
        """)

class FrequencyDialog(QDialog):
    """Dialog to save frequency."""
    
    def __init__(self, current_freq, freq_manager, parent=None):
        super().__init__(parent)
        self.freq_manager = freq_manager
        self.setWindowTitle("Save Frequency")
        self.setMinimumWidth(300)
        
        layout = QVBoxLayout(self)
        
        layout.addWidget(QLabel(f"Frequency: {current_freq:.3f} MHz"))
        self.current_freq = current_freq
        
        layout.addWidget(QLabel("Label:"))
        self.label_input = QLineEdit()
        layout.addWidget(self.label_input)
        
        layout.addWidget(QLabel("Description:"))
        self.desc_input = QLineEdit()
        layout.addWidget(self.desc_input)
        
        btn_layout = QHBoxLayout()
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self.save_freq)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        
        btn_layout.addStretch()
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(save_btn)
        layout.addLayout(btn_layout)
        
        self.setStyleSheet("""
            QDialog { background-color: #0a0a0f; color: #fafafa; }
            QLabel { color: #fafafa; }
            QLineEdit { background-color: #1a1a24; color: #fafafa; border: 1px solid #2a2a3a; border-radius: 6px; padding: 6px; }
            QPushButton { background-color: #1a1a24; color: #fafafa; border: 1px solid #2a2a3a; border-radius: 6px; padding: 8px 16px; }
            QPushButton:hover { background-color: #2a2a3a; }
        """)
        
    def save_freq(self):
        label = self.label_input.text().strip()
        if not label:
            QMessageBox.warning(self, "Error", "Label is required")
            return
        
        self.freq_manager.add(self.current_freq, label, self.desc_input.text().strip())
        self.accept()

class AboutDialog(QDialog):
    """About dialog with banner."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("About TETRA Decoder Pro")
        self.setMinimumWidth(600)
        self.setMinimumHeight(400)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Load banner from assets
        banner_path = ASSETS_DIR / "banner.png"
        
        if banner_path.exists():
            banner_label = QLabel()
            pixmap = QPixmap(str(banner_path))
            # Scale banner to fit dialog width while maintaining aspect ratio
            if not pixmap.isNull():
                scaled_pixmap = pixmap.scaled(560, 200, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                banner_label.setPixmap(scaled_pixmap)
                banner_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                layout.addWidget(banner_label)
        
        # Version and info
        info_label = QLabel("""
        <h2 style="color: #3b82f6;">TETRA Decoder Pro v2.0</h2>
        <p style="color: #a1a1aa;">Professional TETRA signal decoder with real-time spectrum analysis</p>
        <p style="color: #888888;">Features:</p>
        <ul style="color: #a1a1aa;">
            <li>Real-time TETRA frame decoding</li>
            <li>Waterfall spectrum analyzer</li>
            <li>Voice decoding and playback</li>
            <li>Frequency scanning</li>
            <li>Encryption key management</li>
        </ul>
        """)
        info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(info_label)
        
        layout.addStretch()
        
        # Close button
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        close_btn.setMinimumWidth(100)
        button_layout.addWidget(close_btn)
        layout.addLayout(button_layout)
        
        self.apply_style()
    
    def apply_style(self):
        self.setStyleSheet("""
            QDialog { 
                background-color: #0a0a0f; 
                color: #fafafa; 
            }
            QLabel { 
                color: #fafafa; 
                background-color: transparent;
            }
            QPushButton { 
                background-color: #1a1a24; 
                color: #fafafa; 
                border: 1px solid #2a2a3a; 
                border-radius: 6px; 
                padding: 8px 16px; 
            }
            QPushButton:hover { 
                background-color: #2a2a3a; 
            }
        """)

class WaterfallWidget(QWidget):
    """Waterfall spectrum display widget."""
    
    frequency_clicked = pyqtSignal(float)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(400)
        self.waterfall_data = deque(maxlen=200)  # Keep for resizing
        self.freq_min = 390.0
        self.freq_max = 392.0
        self.full_freq_min = 390.0
        self.full_freq_max = 392.0
        self.power_min = -85  # Bottom threshold per user specification
        self.power_max = 0     # Fixed range
        self.current_fft = None
        self.current_freqs = None
        self.peak_freq = None
        self.peak_power = None
        self.noise_floor = -75  # Noise floor threshold per user specification (lowered)
        self.tuned_freq = None  # Currently tuned frequency
        self.view_center = None  # Optional center frequency for viewport (MHz)
        self.bandwidth = 25000  # Default bandwidth in Hz
        self.mouse_freq = None  # Frequency under mouse cursor
        
        # Zoom and View controls
        self.zoom_level = 1.0
        self.denoiser_enabled = False
        self.smoothed_fft = None
        self.avg_factor = 0.15
        
        # Update throttling - limit to ~60 FPS for live feel
        self.update_timer = QTimer(self)
        self.update_timer.setInterval(16)  # ~60 FPS
        self.update_timer.timeout.connect(self._do_update)
        self.pending_update = False
        
        # Cached elements for performance
        self.waterfall_buffer = None  # Persistent buffer for scrolling
        self.grid_cache = None
        self.grid_cache_size = None
        self.grid_cache_params = None
        
        # shadcn/ui dark theme colors
        self.setStyleSheet("background-color: #000000;")
        
        # Enable mouse tracking for hover effects
        self.setMouseTracking(True)

    def mouseMoveEvent(self, event):
        """Handle mouse move for bandwidth overlay."""
        x = event.pos().x()
        width = self.width()
        if width > 0:
            freq_range = self.freq_max - self.freq_min
            self.mouse_freq = self.freq_min + (x / width) * freq_range
            self.update()

    def mousePressEvent(self, event):
        """Handle mouse click to tune."""
        if event.button() == Qt.MouseButton.LeftButton:
            x = event.pos().x()
            width = self.width()
            if width > 0:
                freq_range = self.freq_max - self.freq_min
                freq = self.freq_min + (x / width) * freq_range
                
                # Check for Ctrl key - find peak near click
                modifiers = QApplication.keyboardModifiers()
                if modifiers & Qt.KeyboardModifier.ControlModifier:
                    # Find the spike near the click and snap to its center.
                    # Keep bandwidth unchanged (default 25 kHz) per user preference.
                    spike = self.find_spike_band_near(freq, 50000)
                    freq = spike["center_mhz"]
                    self.center_view_on(freq)
                
                self.frequency_clicked.emit(freq)
    
    def find_peak_near(self, freq, search_range_hz):
        """Find strongest peak near the given frequency."""
        if (
            self.current_fft is None
            or self.current_freqs is None
            or len(self.current_fft) == 0
            or len(self.current_freqs) == 0
        ):
            return freq

        # Search in the underlying FFT bins (not the current viewport mapping).
        half_mhz = search_range_hz / 1e6
        lo = float(freq) - half_mhz
        hi = float(freq) + half_mhz

        freqs = np.asarray(self.current_freqs, dtype=np.float64)
        powers = np.asarray(self.current_fft, dtype=np.float64)
        if freqs.shape != powers.shape:
            n = min(len(freqs), len(powers))
            freqs = freqs[:n]
            powers = powers[:n]

        mask = (freqs >= lo) & (freqs <= hi)
        if not np.any(mask):
            return freq

        idxs = np.where(mask)[0]
        peak_i = int(idxs[np.argmax(powers[idxs])])

        # Sub-bin quadratic interpolation (parabolic fit) for tighter locking.
        # Helps center on narrow spikes even when the true peak falls between FFT bins.
        if 0 < peak_i < len(powers) - 1:
            y1, y2, y3 = powers[peak_i - 1], powers[peak_i], powers[peak_i + 1]
            denom = (y1 - 2 * y2 + y3)
            if denom != 0:
                delta = 0.5 * (y1 - y3) / denom
                # Avoid wild jumps for flat/noisy peaks.
                delta = float(max(-1.0, min(1.0, delta)))
                x1 = freqs[peak_i - 1]
                x2 = freqs[peak_i]
                x3 = freqs[peak_i + 1]
                # Prefer local spacing if non-uniform.
                step = float((x3 - x1) / 2.0) if x3 != x1 else float(x3 - x2)
                return float(x2 + delta * step)

        return float(freqs[peak_i])

    def find_spike_band_near(self, freq_mhz: float, search_range_hz: float) -> dict[str, float]:
        """
        Find the strongest spike near `freq_mhz` and estimate its bandwidth (Hz).

        Returns a dict with:
          - center_mhz
          - left_mhz
          - right_mhz
          - bandwidth_hz

        The spike is defined as the contiguous region around the peak above a dynamic threshold:
          max(peak - 6 dB, local_baseline + 6 dB)
        """
        if (
            self.current_fft is None
            or self.current_freqs is None
            or len(self.current_fft) == 0
            or len(self.current_freqs) == 0
        ):
            return {
                "center_mhz": float(freq_mhz),
                "left_mhz": float(freq_mhz),
                "right_mhz": float(freq_mhz),
                "bandwidth_hz": float(self.bandwidth),
            }

        freqs = np.asarray(self.current_freqs, dtype=np.float64)
        powers = np.asarray(self.current_fft, dtype=np.float64)
        if freqs.shape != powers.shape:
            n = min(len(freqs), len(powers))
            freqs = freqs[:n]
            powers = powers[:n]

        half_mhz = float(search_range_hz) / 1e6
        lo = float(freq_mhz) - half_mhz
        hi = float(freq_mhz) + half_mhz

        mask = (freqs >= lo) & (freqs <= hi)
        if not np.any(mask):
            return {
                "center_mhz": float(freq_mhz),
                "left_mhz": float(freq_mhz),
                "right_mhz": float(freq_mhz),
                "bandwidth_hz": float(self.bandwidth),
            }

        idxs = np.where(mask)[0]
        peak_i = int(idxs[np.argmax(powers[idxs])])
        peak_power = float(powers[peak_i])

        # Local baseline (robust) + dynamic threshold for "spike edges".
        local_powers = powers[idxs]
        local_baseline = float(np.percentile(local_powers, 20))
        threshold = max(peak_power - 6.0, local_baseline + 6.0, float(self.noise_floor) + 3.0)

        left_i = peak_i
        while left_i > idxs[0] and powers[left_i] >= threshold:
            left_i -= 1
        if powers[left_i] < threshold and left_i < peak_i:
            left_i += 1

        right_i = peak_i
        while right_i < idxs[-1] and powers[right_i] >= threshold:
            right_i += 1
        if powers[right_i] < threshold and right_i > peak_i:
            right_i -= 1

        left_mhz = float(freqs[left_i])
        right_mhz = float(freqs[right_i])
        if right_mhz < left_mhz:
            left_mhz, right_mhz = right_mhz, left_mhz

        center_mhz = (left_mhz + right_mhz) / 2.0
        bandwidth_hz = (right_mhz - left_mhz) * 1e6

        # Clamp to a sane range so the overlay remains usable.
        bandwidth_hz = float(max(1000.0, min(250000.0, bandwidth_hz)))

        return {
            "center_mhz": center_mhz,
            "left_mhz": left_mhz,
            "right_mhz": right_mhz,
            "bandwidth_hz": bandwidth_hz,
        }

    def set_bandwidth(self, hz):
        """Set bandwidth for visual overlay."""
        self.bandwidth = hz
        self.update()

    def set_zoom(self, level):
        """Set zoom level (1.0 to 10.0)."""
        self.zoom_level = max(1.0, min(10.0, level))
        self.update_view_range()
        self.update()

    def set_denoiser(self, enabled):
        """Enable/disable denoiser."""
        self.denoiser_enabled = enabled
        if not enabled:
            self.smoothed_fft = None

    def update_view_range(self):
        """Update visible frequency range based on zoom."""
        if self.full_freq_min is not None and self.full_freq_max is not None:
            center = self.view_center if self.view_center is not None else (self.full_freq_min + self.full_freq_max) / 2
            span = self.full_freq_max - self.full_freq_min
            
            # Apply zoom
            visible_span = span / self.zoom_level

            target_min = center - (visible_span / 2)
            target_max = center + (visible_span / 2)

            # Clamp to available range (keep span constant where possible)
            if target_min < self.full_freq_min:
                shift = self.full_freq_min - target_min
                target_min += shift
                target_max += shift
            if target_max > self.full_freq_max:
                shift = target_max - self.full_freq_max
                target_min -= shift
                target_max -= shift

            self.freq_min = max(self.full_freq_min, target_min)
            self.freq_max = min(self.full_freq_max, target_max)
            
            # Invalidate grid cache
            self.grid_cache = None
            self.grid_cache_params = None
    
    def set_noise_floor(self, value):
        """Set noise floor threshold."""
        self.noise_floor = value
        self.update()
    
    def set_tuned_frequency(self, freq_mhz):
        """Set tuned frequency for display."""
        self.tuned_freq = freq_mhz
        self.view_center = freq_mhz
        self.update_view_range()
        self.update()

    def center_view_on(self, freq_mhz: float) -> None:
        """Center the current viewport on a frequency (MHz) without changing SDR tuning."""
        self.view_center = float(freq_mhz)
        self.update_view_range()
        self.update()
        
    def update_spectrum(self, freqs, powers):
        """Update spectrum data."""
        try:
            self.current_freqs = freqs / 1e6  # Convert to MHz
            
            # Apply denoiser if enabled
            if self.denoiser_enabled:
                if self.smoothed_fft is None or len(self.smoothed_fft) != len(powers):
                    self.smoothed_fft = powers
                else:
                    # IIR Filter
                    self.smoothed_fft = self.smoothed_fft * (1 - self.avg_factor) + powers * self.avg_factor
                self.current_fft = self.smoothed_fft
            else:
                self.current_fft = powers
                self.smoothed_fft = None
            
            # Find peak
            if len(powers) > 0:
                peak_idx = np.argmax(powers)
                self.peak_freq = self.current_freqs[peak_idx]
                self.peak_power = powers[peak_idx]
            
            # Add to waterfall history (for resizing)
            self.waterfall_data.append(self.current_fft.copy())
            
            # Update full frequency range
            if len(self.current_freqs) > 0:
                self.full_freq_min = np.min(self.current_freqs)
                self.full_freq_max = np.max(self.current_freqs)
                self.update_view_range()
            
            # Update waterfall buffer immediately (scrolling)
            self._update_waterfall_buffer()
            
            # Throttle UI updates
            self.pending_update = True
            if not self.update_timer.isActive():
                self.update_timer.start()
        except Exception as e:
            logger.error(f"Error updating spectrum: {e}")
    
    def _update_waterfall_buffer(self):
        """Update the scrolling waterfall buffer."""
        if self.current_fft is None:
            return
            
        width = self.width()
        height = self.height()
        spectrum_height = int(height * 0.7)
        waterfall_height = height - spectrum_height
        
        if waterfall_height <= 0 or width <= 0:
            return
            
        # Initialize buffer if needed
        if (self.waterfall_buffer is None or 
            self.waterfall_buffer.width() != width or 
            self.waterfall_buffer.height() != waterfall_height):
            self.waterfall_buffer = QImage(width, waterfall_height, QImage.Format.Format_RGB32)
            self.waterfall_buffer.fill(QColor(10, 15, 25))
        
        # Scroll existing content down by 1 pixel
        temp_painter = QPainter(self.waterfall_buffer)
        temp_painter.drawImage(0, 1, self.waterfall_buffer, 0, 0, width, waterfall_height - 1)
        
        # Draw new line at top (y=0)
        fft_len = len(self.current_fft)
        if fft_len > 0:
            # Create a single line image
            line_indices = np.linspace(0, fft_len - 1, width, dtype=np.int32)
            resampled = self.current_fft[line_indices]
            
            # Normalize
            power_range = self.power_max - self.power_min
            if power_range > 0:
                normalized = np.clip((resampled - self.power_min) / power_range, 0, 1)
            else:
                normalized = np.zeros_like(resampled)
            
            # Color map (Blue -> Cyan -> Yellow -> Red)
            rgb_line = np.zeros((width, 3), dtype=np.uint8)
            
            # Blue (0-0.25)
            mask1 = normalized < 0.25
            rgb_line[mask1, 2] = np.clip((normalized[mask1] * 4 * 255).astype(np.uint8), 0, 255)
            
            # Blue to Cyan (0.25-0.5)
            mask2 = (normalized >= 0.25) & (normalized < 0.5)
            if np.any(mask2):
                t = (normalized[mask2] - 0.25) * 4
                rgb_line[mask2, 1] = np.clip((t * 255).astype(np.uint8), 0, 255)
                rgb_line[mask2, 2] = 255
            
            # Cyan to Yellow (0.5-0.75)
            mask3 = (normalized >= 0.5) & (normalized < 0.75)
            if np.any(mask3):
                t = (normalized[mask3] - 0.5) * 4
                rgb_line[mask3, 0] = np.clip((t * 255).astype(np.uint8), 0, 255)
                rgb_line[mask3, 1] = 255
                rgb_line[mask3, 2] = np.clip(((1 - t) * 255).astype(np.uint8), 0, 255)
            
            # Yellow to Red (0.75-1.0)
            mask4 = normalized >= 0.75
            if np.any(mask4):
                t = (normalized[mask4] - 0.75) * 4
                rgb_line[mask4, 0] = 255
                rgb_line[mask4, 1] = np.clip(((1 - t) * 255).astype(np.uint8), 0, 255)
            
            # Convert to QImage line
            pixels = (0xFF000000 | 
                     (rgb_line[:, 0].astype(np.uint32) << 16) | 
                     (rgb_line[:, 1].astype(np.uint32) << 8) | 
                     rgb_line[:, 2].astype(np.uint32))
            
            line_img = QImage(pixels.tobytes(), width, 1, QImage.Format.Format_RGB32)
            temp_painter.drawImage(0, 0, line_img)
            
        temp_painter.end()
    
    def _do_update(self):
        """Actually trigger the update when timer fires."""
        if self.pending_update:
            self.pending_update = False
            self.update()
    
    def paintEvent(self, event):
        """Paint the traditional SDR-style spectrum and waterfall display."""
        try:
            painter = QPainter(self)
            # Only use antialiasing for spectrum trace, not waterfall
            painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
            
            width = self.width()
            height = self.height()
            
            # Split: 70% spectrum analyzer on top, 30% waterfall on bottom
            spectrum_height = int(height * 0.7)
            waterfall_height = height - spectrum_height
            
            # Fill background with black (matching reference)
            painter.fillRect(0, 0, width, height, QColor(0, 0, 0))
            
            # Draw spectrum analyzer section (top)
            self._draw_spectrum_analyzer(painter, 0, 0, width, spectrum_height)
            
            # Draw waterfall section (bottom)
            if self.waterfall_buffer and not self.waterfall_buffer.isNull():
                # Draw the buffered waterfall image
                target_rect = QRect(0, spectrum_height, width, waterfall_height)
                source_rect = QRect(0, 0, self.waterfall_buffer.width(), self.waterfall_buffer.height())
                painter.drawImage(target_rect, self.waterfall_buffer, source_rect)
            else:
                # Fallback if buffer not ready
                painter.fillRect(0, spectrum_height, width, waterfall_height, QColor(10, 15, 25))
                
        except Exception:
            pass
    
    def _draw_spectrum_analyzer(self, painter, x, y, width, height):
        """Draw spectrum analyzer (top section) - SDR# style."""
        # Background for spectrum - BLACK
        painter.fillRect(x, y, width, height, QColor(0, 0, 0))
        
        freq_range = self.freq_max - self.freq_min
        power_range = self.power_max - self.power_min
        
        # Cache grid lines
        cache_key = (width, height, self.freq_min, self.freq_max, self.power_min, self.power_max, self.noise_floor)
        if self.grid_cache is None or self.grid_cache_params != cache_key:
            self.grid_cache = QPixmap(width, height)
            self.grid_cache.fill(QColor(0, 0, 0, 0))
            grid_painter = QPainter(self.grid_cache)
            
            # Grid lines (Gray)
            grid_painter.setPen(QPen(QColor(60, 60, 60), 1))
            
            # Horizontal grid lines (dBFS scale) - every 10 dB
            if power_range > 0:
                start_db = int(self.power_max / 10) * 10
                for db in range(start_db, int(self.power_min), -10):
                    normalized = (db - self.power_min) / power_range
                    grid_y = int((1 - normalized) * height)
                    grid_painter.drawLine(0, grid_y, width, grid_y)
                    # Label
                    grid_painter.setPen(QPen(QColor(180, 180, 180), 1))
                    grid_painter.drawText(5, grid_y - 2, f"{db}")
                    grid_painter.setPen(QPen(QColor(60, 60, 60), 1))
            
            # Vertical grid lines (frequency)
            if freq_range > 0:
                num_freq_grids = 10
                for i in range(num_freq_grids + 1):
                    freq = self.freq_min + (i * freq_range / num_freq_grids)
                    grid_x = int((freq - self.freq_min) / freq_range * width)
                    grid_painter.drawLine(grid_x, 0, grid_x, height)
            
            grid_painter.end()
            self.grid_cache_params = cache_key
        
        # Draw cached grid
        painter.drawPixmap(x, y, self.grid_cache)
        
        # Draw noise floor threshold line (Yellow dashed)
        if self.noise_floor >= self.power_min and self.noise_floor <= self.power_max and power_range > 0:
            normalized = (self.noise_floor - self.power_min) / power_range
            noise_y = y + int((1 - normalized) * height)
            pen = QPen(QColor(255, 255, 0), 1, Qt.PenStyle.DashLine)
            painter.setPen(pen)
            painter.drawLine(x, noise_y, x + width, noise_y)
        
        # Draw spectrum trace (Filled Blue + White Outline)
        if self.current_fft is not None and len(self.current_fft) > 0 and len(self.current_freqs) > 0:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            
            path = QPainterPath()
            # Start at bottom left
            path.moveTo(x, y + height)
            
            # Trace points
            for i in range(len(self.current_fft)):
                if i >= len(self.current_freqs):
                    break
                freq = self.current_freqs[i]
                power = self.current_fft[i]
                
                if freq_range > 0:
                    x_pos = x + int(((freq - self.freq_min) / freq_range) * width)
                else:
                    x_pos = x + int((i / len(self.current_fft)) * width)
                
                if power_range > 0:
                    normalized = (power - self.power_min) / power_range
                    # Clamp to view
                    normalized = max(0, min(1, normalized))
                    y_pos = y + int((1 - normalized) * height)
                else:
                    y_pos = y + height
                
                path.lineTo(x_pos, y_pos)
            
            # End at bottom right
            path.lineTo(x + width, y + height)
            path.closeSubpath()
            
            # Fill with gradient (Blue to Transparent) - Subtle
            gradient = QLinearGradient(x, y, x, y + height)
            gradient.setColorAt(0, QColor(0, 100, 255, 50))  # Very transparent
            gradient.setColorAt(1, QColor(0, 50, 150, 10))
            painter.fillPath(path, gradient)
            
            # Draw outline (White) - Thinner, crisper
            pen = QPen(QColor(255, 255, 255), 1.0)
            painter.setPen(pen)
            painter.drawPath(path)
            
            painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        
        # Draw tuned frequency marker and bandwidth lines (Red)
        if self.tuned_freq is not None and freq_range > 0:
            center_freq = self.tuned_freq
            bw_half = (self.bandwidth / 1e6) / 2  # Convert Hz to MHz

            # Calculate x coordinates
            x_center = x + int(((center_freq - self.freq_min) / freq_range) * width)
            x_left = x + int(((center_freq - bw_half - self.freq_min) / freq_range) * width)
            x_right = x + int(((center_freq + bw_half - self.freq_min) / freq_range) * width)

            # Draw lines if within view
            pen = QPen(QColor(255, 0, 0), 2)
            painter.setPen(pen)

            if 0 <= x_left <= width:
                painter.drawLine(x_left, y, x_left, y + height)
            if 0 <= x_right <= width:
                painter.drawLine(x_right, y, x_right, y + height)

            # Center line (dashed)
            pen.setStyle(Qt.PenStyle.DashLine)
            pen.setWidth(1)
            painter.setPen(pen)
            if 0 <= x_center <= width:
                painter.drawLine(x_center, y, x_center, y + height)
            
        # Draw bandwidth overlay if mouse is active
        if self.mouse_freq is not None and freq_range > 0:
            # Calculate width of bandwidth in pixels
            bw_mhz = self.bandwidth / 1e6
            bw_pixels = int((bw_mhz / freq_range) * width)
            
            mouse_x = x + int(((self.mouse_freq - self.freq_min) / freq_range) * width)
            
            # Draw two red lines centered on mouse
            left_x = mouse_x - (bw_pixels // 2)
            right_x = mouse_x + (bw_pixels // 2)
            
            # Solid red lines, brighter
            painter.setPen(QPen(QColor(255, 0, 0), 2))
            painter.drawLine(left_x, y, left_x, y + height)
            painter.drawLine(right_x, y, right_x, y + height)
            
            # Fill area between lines lightly
            painter.fillRect(left_x, y, bw_pixels, height, QColor(255, 0, 0, 40))
        
        # Draw frequency labels at bottom
        painter.setPen(QPen(QColor(200, 200, 200), 1))
        font = QFont("Arial", 9)
        painter.setFont(font)
        if freq_range > 0:
            num_labels = 5
            for i in range(num_labels):
                freq = self.freq_min + (i * freq_range / (num_labels - 1))
                label_x = x + int((i / (num_labels - 1)) * width)
                # Draw label
                freq_str = f"{freq:.3f}"
                painter.drawText(label_x - 25, y + height - 5, 50, 15, Qt.AlignmentFlag.AlignCenter, freq_str)
    
    def _draw_waterfall(self, painter, x, y, width, height):
        """Draw waterfall spectrogram (bottom section) - optimized with numpy."""
        # Background (shadcn dark)
        painter.fillRect(x, y, width, height, QColor(10, 15, 25))
        
        # Draw waterfall history
        if len(self.waterfall_data) > 0:
            img_width = width - 30  # Leave space for color scale
            img_height = height
            
            # Check if we need to recreate the image
            if (self.waterfall_image is None or 
                self.waterfall_image_size != (img_width, img_height)):
                self.waterfall_image = QImage(img_width, img_height, QImage.Format.Format_RGB32)
                self.waterfall_image_size = (img_width, img_height)
            
            # Fill with background color
            self.waterfall_image.fill(QColor(10, 15, 25))
            
            # Convert waterfall data to numpy array for fast processing
            num_lines = len(self.waterfall_data)
            if num_lines > 0:
                # Get max FFT length
                max_fft_len = max(len(line) for line in self.waterfall_data)
                
                if max_fft_len > 0:
                    # Create 2D array: [num_lines, max_fft_len]
                    waterfall_array = np.full((num_lines, max_fft_len), self.power_min, dtype=np.float32)
                    for i, fft_line in enumerate(self.waterfall_data):
                        if len(fft_line) > 0:
                            waterfall_array[i, :min(len(fft_line), max_fft_len)] = fft_line[:max_fft_len]
                    
                    # Resample to image width using numpy interpolation
                    x_indices = np.linspace(0, max_fft_len - 1, img_width, dtype=np.int32)
                    resampled = waterfall_array[:, x_indices]
                    
                    # Normalize power values
                    power_range = self.power_max - self.power_min
                    if power_range > 0:
                        normalized = np.clip((resampled - self.power_min) / power_range, 0, 1)
                    else:
                        normalized = np.zeros_like(resampled)
                    
                    # Map to image height (reverse y-axis for display - newest at top)
                    y_indices = np.linspace(0, num_lines - 1, img_height, dtype=np.int32)
                    y_indices = np.clip(y_indices, 0, num_lines - 1)
                    
                    # Create RGB array using vectorized color mapping
                    rgb_array = np.zeros((img_height, img_width, 3), dtype=np.uint8)
                    
                    # Process each row
                    for py in range(img_height):
                        line_idx = y_indices[py]
                        if 0 <= line_idx < num_lines:
                            norm_line = normalized[line_idx, :]
                            
                            # Vectorized color mapping using numpy (Blue -> Cyan -> Yellow -> Red)
                            # Blue (0-0.25)
                            mask1 = norm_line < 0.25
                            rgb_array[py, mask1, 2] = np.clip((norm_line[mask1] * 4 * 255).astype(np.uint8), 0, 255)
                            
                            # Blue to Cyan (0.25-0.5)
                            mask2 = (norm_line >= 0.25) & (norm_line < 0.5)
                            if np.any(mask2):
                                t = (norm_line[mask2] - 0.25) * 4
                                rgb_array[py, mask2, 1] = np.clip((t * 255).astype(np.uint8), 0, 255)
                                rgb_array[py, mask2, 2] = 255
                            
                            # Cyan to Yellow (0.5-0.75)
                            mask3 = (norm_line >= 0.5) & (norm_line < 0.75)
                            if np.any(mask3):
                                t = (norm_line[mask3] - 0.5) * 4
                                rgb_array[py, mask3, 0] = np.clip((t * 255).astype(np.uint8), 0, 255)
                                rgb_array[py, mask3, 1] = 255
                                rgb_array[py, mask3, 2] = np.clip(((1 - t) * 255).astype(np.uint8), 0, 255)
                            
                            # Yellow to Red (0.75-1.0)
                            mask4 = norm_line >= 0.75
                            if np.any(mask4):
                                t = (norm_line[mask4] - 0.75) * 4
                                rgb_array[py, mask4, 0] = 255
                                rgb_array[py, mask4, 1] = np.clip(((1 - t) * 255).astype(np.uint8), 0, 255)
                    
                    # Convert numpy RGB array to QImage (QImage uses BGR format)
                    # Create byte array in BGR format
                    bgr_array = rgb_array[:, :, ::-1]  # Reverse RGB to BGR
                    bytes_per_line = img_width * 3
                    img_bytes = bgr_array.tobytes()
                    
                    # Create QImage from bytes
                    self.waterfall_image = QImage(img_bytes, img_width, img_height, bytes_per_line, QImage.Format.Format_RGB888).copy()
            
            painter.drawImage(x, y, self.waterfall_image)
        
        # Draw color scale bar on right
        scale_width = 20
        scale_x = x + width - scale_width
        for py in range(height):
            normalized = 1.0 - (py / height)
            
            # Same color mapping as waterfall (Blue -> Cyan -> Yellow -> Red)
            if normalized < 0.25:
                c = QColor(0, 0, int(normalized * 4 * 255))
            elif normalized < 0.5:
                t = (normalized - 0.25) * 4
                c = QColor(0, int(t * 255), 255)
            elif normalized < 0.75:
                t = (normalized - 0.5) * 4
                c = QColor(int(t * 255), 255, int((1 - t) * 255))
            else:
                t = (normalized - 0.75) * 4
                c = QColor(255, int((1 - t) * 255), 0)
            
            painter.fillRect(scale_x, y + py, scale_width, 1, c)
        
        # Draw scale labels
        painter.setPen(QPen(QColor(200, 200, 200), 1))
        font = QFont("Arial", 8)
        painter.setFont(font)
        painter.drawText(scale_x - 35, y, 30, 12, Qt.AlignmentFlag.AlignRight, f"{int(self.power_max)}")
        painter.drawText(scale_x - 35, y + height - 12, 30, 12, Qt.AlignmentFlag.AlignRight, f"{int(self.power_min)}")


class ScannerDialog(QDialog):
    """Frequency scanner window."""
    
    scan_complete = pyqtSignal(list)  # List of (frequency, power) tuples
    frequency_found = pyqtSignal(float, float, str)  # freq, power, status
    scan_progress = pyqtSignal(int, str)  # progress percent, current frequency
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Frequency Scanner")
        self.setMinimumSize(800, 600)
        self.resize(900, 700)
        self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.WindowCloseButtonHint | Qt.WindowType.WindowMinMaxButtonsHint)
        self.init_ui()
        self.scanner = None
        self.scanning = False
        self.scan_thread = None
        self.apply_dark_theme()
        
        # Connect signals
        self.frequency_found.connect(self.on_frequency_found)
        self.scan_progress.connect(self.on_scan_progress)
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(15, 15, 15, 15)
        
        # Title
        title = QLabel("🔍 Frequency Scanner")
        title.setStyleSheet("font-size: 18pt; font-weight: bold; color: #3b82f6; margin-bottom: 5px;")
        layout.addWidget(title)
        
        # Scan range
        range_group = QGroupBox("Scan Parameters")
        range_layout = QVBoxLayout()
        range_layout.setSpacing(8)
        
        # Frequency inputs
        freq_row = QHBoxLayout()
        freq_row.setSpacing(8)
        freq_row.addWidget(QLabel("Start (MHz):"))
        self.start_freq = QLineEdit("390.0")
        self.start_freq.setMinimumWidth(100)
        self.start_freq.setMaximumWidth(120)
        self.start_freq.setPlaceholderText("e.g., 390.0")
        freq_row.addWidget(self.start_freq)
        
        freq_row.addWidget(QLabel("Stop (MHz):"))
        self.stop_freq = QLineEdit("400.0")
        self.stop_freq.setMinimumWidth(100)
        self.stop_freq.setMaximumWidth(120)
        self.stop_freq.setPlaceholderText("e.g., 400.0")
        freq_row.addWidget(self.stop_freq)
        
        freq_row.addWidget(QLabel("Step (kHz):"))
        self.step_freq = QLineEdit("25")
        self.step_freq.setMinimumWidth(80)
        self.step_freq.setMaximumWidth(100)
        self.step_freq.setPlaceholderText("25")
        freq_row.addWidget(self.step_freq)
        
        freq_row.addStretch()
        range_layout.addLayout(freq_row)
        
        # Preset buttons
        preset_row = QHBoxLayout()
        preset_row.setSpacing(8)
        preset_row.addWidget(QLabel("Presets:"))
        
        preset_390 = QPushButton("🇵🇱 Poland (390-395)")
        preset_390.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Preferred)
        preset_390.clicked.connect(lambda: self.set_preset(390.0, 395.0, 25))
        preset_row.addWidget(preset_390)
        
        preset_420 = QPushButton("🇪🇺 Europe (410-430)")
        preset_420.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Preferred)
        preset_420.clicked.connect(lambda: self.set_preset(410.0, 430.0, 25))
        preset_row.addWidget(preset_420)
        
        preset_392 = QPushButton("🎯 Quick (392-393)")
        preset_392.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Preferred)
        preset_392.clicked.connect(lambda: self.set_preset(392.0, 393.0, 25))
        preset_row.addWidget(preset_392)
        
        preset_row.addStretch()
        range_layout.addLayout(preset_row)
        
        range_group.setLayout(range_layout)
        layout.addWidget(range_group)
        
        # Controls
        control_layout = QHBoxLayout()
        control_layout.setSpacing(8)
        self.scan_btn = QPushButton("▶ Start Scan")
        self.scan_btn.setMinimumHeight(42)
        self.scan_btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.scan_btn.clicked.connect(self.start_scan)
        control_layout.addWidget(self.scan_btn, 1)
        
        self.stop_btn = QPushButton("⏹ Stop")
        self.stop_btn.setMinimumHeight(42)
        self.stop_btn.setEnabled(False)
        self.stop_btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.stop_btn.clicked.connect(self.stop_scan)
        control_layout.addWidget(self.stop_btn, 1)
        
        self.close_btn = QPushButton("✖ Close")
        self.close_btn.setMinimumHeight(42)
        self.close_btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.close_btn.clicked.connect(self.accept)
        control_layout.addWidget(self.close_btn, 1)
        
        layout.addLayout(control_layout)
        
        # Progress
        progress_layout = QVBoxLayout()
        progress_layout.setSpacing(5)
        self.progress_label = QLabel("Ready to scan")
        self.progress_label.setStyleSheet("color: #3b82f6; font-weight: bold; font-size: 11pt;")
        progress_layout.addWidget(self.progress_label)
        
        self.progress = QProgressBar()
        self.progress.setMinimumHeight(28)
        self.progress.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        progress_layout.addWidget(self.progress)
        layout.addLayout(progress_layout)
        
        # Results table with scroll area
        results_label = QLabel("📊 Results")
        results_label.setStyleSheet("font-size: 13pt; font-weight: bold; color: #3b82f6; margin-top: 5px;")
        layout.addWidget(results_label)
        
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(3)
        self.results_table.setHorizontalHeaderLabels(["Frequency (MHz)", "Power (dB)", "Status"])
        
        # Set column resize modes
        header = self.results_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        
        self.results_table.setAlternatingRowColors(True)
        self.results_table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        
        scroll_area.setWidget(self.results_table)
        layout.addWidget(scroll_area, 1)  # Give table stretch factor
    
    def apply_dark_theme(self):
        """Apply shadcn/ui dark theme to scanner."""
        self.setStyleSheet("""
            QDialog {
                background-color: #0a0a0f;
            }
            QWidget {
                background-color: #0a0a0f;
                color: #fafafa;
                font-family: 'Segoe UI', 'Inter', sans-serif;
                font-size: 13px;
            }
            QGroupBox {
                border: 1px solid #2a2a3a;
                border-radius: 8px;
                margin-top: 8px;
                padding: 12px;
                background-color: #1a1a24;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 6px;
                color: #a1a1aa;
                font-weight: 600;
                font-size: 11px;
            }
            QPushButton {
                background-color: #1a1a24;
                color: #fafafa;
                border: 1px solid #2a2a3a;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #2a2a3a;
                border-color: #3a3a4a;
            }
            QPushButton:pressed {
                background-color: #3a3a4a;
            }
            QPushButton:disabled {
                background-color: #0a0a0f;
                color: #52525b;
                border-color: #1a1a24;
            }
            QLineEdit {
                background-color: #1a1a24;
                color: #fafafa;
                border: 1px solid #2a2a3a;
                border-radius: 6px;
                padding: 6px 10px;
                selection-background-color: #3b82f6;
                selection-color: white;
            }
            QLineEdit:focus {
                border: 1px solid #3b82f6;
            }
            QTableWidget {
                background-color: #1a1a24;
                border: 1px solid #2a2a3a;
                border-radius: 6px;
                gridline-color: #2a2a3a;
                alternate-background-color: #0f0f1a;
            }
            QTableWidget::item {
                padding: 6px 8px;
                border: none;
            }
            QTableWidget::item:selected {
                background-color: #2a2a3a;
                color: #fafafa;
            }
            QTableWidget::item:hover {
                background-color: #2a2a3a;
            }
            QHeaderView::section {
                background-color: #0f0f1a;
                color: #a1a1aa;
                padding: 8px 6px;
                border: none;
                border-bottom: 1px solid #2a2a3a;
                border-right: 1px solid #2a2a3a;
                font-weight: 600;
                font-size: 11px;
            }
            QHeaderView::section:hover {
                background-color: #1a1a24;
            }
            QProgressBar {
                background-color: #1a1a24;
                border: 1px solid #2a2a3a;
                border-radius: 4px;
                text-align: center;
                color: #fafafa;
            }
            QProgressBar::chunk {
                background-color: #3b82f6;
                border-radius: 3px;
            }
            QLabel {
                color: #fafafa;
            }
            QScrollArea {
                border: 1px solid #2a2a3a;
                border-radius: 6px;
                background-color: #0a0a0f;
            }
        """)
    
    def set_preset(self, start, stop, step):
        """Set preset values."""
        self.start_freq.setText(str(start))
        self.stop_freq.setText(str(stop))
        self.step_freq.setText(str(step))
    
    def start_scan(self):
        """Start frequency scan."""
        try:
            start = float(self.start_freq.text()) * 1e6
            stop = float(self.stop_freq.text()) * 1e6
            step = float(self.step_freq.text()) * 1e3
            
            # Import RTLCapture
            from tetraear.signal.capture import RTLCapture
            
            # Create RTL capture instance
            rtl = RTLCapture(frequency=start, sample_rate=2.4e6, gain=50)
            if not rtl.open():
                QMessageBox.warning(self, "Error", "Failed to open RTL-SDR device")
                return
            
            # Initialize scanner with noise floor and bottom threshold parameters
            self.scanner = FrequencyScanner(
                rtl, 
                sample_rate=2.4e6,
                scan_step=step,
                noise_floor=-45,  # Default noise floor
                bottom_threshold=-85  # Default bottom threshold
            )
            self.scan_btn.setEnabled(False)
            self.stop_btn.setEnabled(True)
            self.results_table.setRowCount(0)
            self.scanning = True
            
            # Start scan in thread
            self.scan_thread = threading.Thread(target=self.run_scan, args=(start, stop, step))
            self.scan_thread.daemon = True
            self.scan_thread.start()
            
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to start scan: {e}")
            self.scan_btn.setEnabled(True)
            self.stop_btn.setEnabled(False)
            self.scanning = False
    
    def run_scan(self, start_freq, stop_freq, step):
        """Run the scan with live updates."""
        try:
            num_steps = int((stop_freq - start_freq) / step) + 1
            found_count = 0
            
            for step_idx in range(num_steps + 1):
                if not self.scanning:
                    break
                    
                freq = start_freq + step_idx * step
                if freq > stop_freq:
                    break
                
                # Update progress
                progress = int((step_idx / num_steps) * 100)
                current_freq_mhz = freq / 1e6
                self.scan_progress.emit(progress, f"{current_freq_mhz:.3f} MHz")
                
                # Scan this frequency
                try:
                    result = self.scanner.scan_frequency(freq, dwell_time=0.2)
                    
                    # Check if signal found
                    if result.get('signal_present', False) or result.get('power_db', -100) > -80:
                        power = result.get('power_db', -100)
                        is_tetra = result.get('is_tetra', False)
                        
                        if power > -80:
                            status = "TETRA detected ✓" if is_tetra else "Signal detected"
                            self.frequency_found.emit(freq, power, status)
                            found_count += 1
                
                except Exception as e:
                    logger.debug(f"Error scanning {freq/1e6:.3f} MHz: {e}")
                    continue
            
            # Final update
            if self.scanning:
                self.scan_progress.emit(100, f"Complete - Found {found_count} signals")
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.scan_progress.emit(0, f"Scan error: {str(e)}")
        finally:
            # Clean up
            if self.scanner and self.scanner.capture:
                try:
                    self.scanner.capture.close()
                except:
                    pass
            self.scanning = False
            # Update UI on main thread
            QTimer.singleShot(100, self.scan_finished)
    
    def scan_finished(self):
        """Called when scan finishes - updates UI on main thread."""
        self.scan_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
    
    @pyqtSlot(int, str)
    def on_scan_progress(self, progress, current_freq):
        """Update progress bar and current frequency display."""
        self.progress.setValue(progress)
        self.progress_label.setText(f"Scanning {current_freq}... ({progress}%)")
    
    @pyqtSlot(float, float, str)
    def on_frequency_found(self, freq, power, status):
        """Add found frequency to table immediately."""
        self.add_result(freq, power, status)
    
    def stop_scan(self):
        """Stop scanning."""
        self.scanning = False
        if self.scanner and self.scanner.capture:
            try:
                self.scanner.capture.close()
            except:
                pass
        self.progress_label.setText("Scan stopped")
        self.scan_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
    
    def add_result(self, freq, power, status):
        """Add result to table."""
        row = self.results_table.rowCount()
        self.results_table.insertRow(row)
        
        freq_item = QTableWidgetItem(f"{freq/1e6:.3f}")
        freq_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self.results_table.setItem(row, 0, freq_item)
        
        power_item = QTableWidgetItem(f"{power:.1f}")
        power_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        # Color code by power
        if power > -50:
            power_item.setForeground(QColor(0, 255, 0))  # Green - strong
        elif power > -70:
            power_item.setForeground(QColor(255, 255, 0))  # Yellow - medium
        else:
            power_item.setForeground(QColor(255, 128, 0))  # Orange - weak
        self.results_table.setItem(row, 1, power_item)
        
        status_item = QTableWidgetItem(status)
        if "TETRA" in status:
            status_item.setForeground(QColor(0, 255, 255))  # Cyan for TETRA
        self.results_table.setItem(row, 2, status_item)


class CaptureThread(QThread):
    """Thread for RTL-SDR capture - simplified to avoid parse errors."""
    
    signal_detected = pyqtSignal(float, float)
    signal_lost = pyqtSignal()
    frame_decoded = pyqtSignal(dict)
    raw_audio_data = pyqtSignal(np.ndarray)
    voice_audio_data = pyqtSignal(np.ndarray)
    error_occurred = pyqtSignal(str)
    status_update = pyqtSignal(str)
    spectrum_update = pyqtSignal(np.ndarray, np.ndarray)
    
    def __init__(self):
        super().__init__()
        self.running = False
        self.capture = None
        self.processor = None
        self.decoder = None
        self.voice_processor = None
        self.frequency = 390.865e6  # Default frequency per user request
        self.sample_rate = 2.4e6  # Default sample rate per TETRA spec
        self.gain = 50  # Default gain per user specification
        self.auto_decrypt = True
        self.monitor_raw = False  # New flag
        self.pending_freq = None
        self.last_signal_time = 0
        self.encryption_keys = []  # List of keys for bruteforce
        
    def set_keys(self, keys):
        """Set encryption keys for bruteforce attempts."""
        self.encryption_keys = keys
        if self.decoder:
            self.decoder.set_keys(keys)
            logger.info(f"Loaded {len(keys)} encryption keys into decoder")
        
    def set_monitor_raw(self, enabled):
        self.monitor_raw = enabled
        
    def set_frequency(self, freq):
        """Set tuning frequency."""
        self.pending_freq = freq
    
    def set_gain(self, gain):
        """Set gain."""
        self.gain = gain
        if self.capture and self.capture.sdr:
            try:
                self.capture.sdr.gain = gain
                self.status_update.emit(f"Gain set to {gain}")
            except Exception as e:
                self.error_occurred.emit(f"Failed to set gain: {e}")
    
    def set_sample_rate(self, rate):
        """Set sample rate."""
        # Validate sample rate - RTL-SDR has limited valid rates
        # Valid rates: 0.225, 0.9, 1.024, 1.536, 1.8, 1.92, 2.048, 2.4, 2.56, 2.88, 3.2 MHz
        valid_rates = [0.225e6, 0.9e6, 1.024e6, 1.536e6, 1.8e6, 1.92e6, 2.048e6, 2.4e6, 2.56e6, 2.88e6, 3.2e6]
        closest_rate = min(valid_rates, key=lambda x: abs(x - rate))
        if abs(closest_rate - rate) > 0.1e6:  # More than 100kHz difference
            self.error_occurred.emit(f"Sample rate {rate/1e6:.3f} MHz is not valid, using {closest_rate/1e6:.3f} MHz")
        rate = closest_rate
        
        self.sample_rate = rate
        if self.capture and self.capture.sdr:
            try:
                # RTL-SDR requires restart for sample rate change usually, but let's try
                self.capture.sdr.sample_rate = rate
                if self.processor:
                    self.processor.sample_rate = rate
                self.status_update.emit(f"Sample rate set to {rate/1e6:.1f} MHz")
            except Exception as e:
                self.error_occurred.emit(f"Failed to set sample rate: {e}")
    
    def run(self):
        """Main capture loop - simplified with throttled updates."""
        import time
        self.running = True
        last_spectrum_update = 0
        spectrum_update_interval = 0.005  # ~200 Hz (5ms) for ultra-fast updates
        last_status_update = 0
        status_update_interval = 0.1  # 10 Hz for status updates
        
        try:
            self.status_update.emit("Initializing RTL-SDR...")
            # RTLCapture accepts 'auto' as string or numeric gain value
            self.capture = RTLCapture(
                frequency=self.frequency,
                sample_rate=self.sample_rate,
                gain=self.gain
            )
            
            if not self.capture.open():
                self.error_occurred.emit("Failed to open RTL-SDR")
                return
            
            self.processor = SignalProcessor(sample_rate=self.sample_rate)
            self.decoder = TetraDecoder(auto_decrypt=self.auto_decrypt)
            logger.info("Auto-Decrypt: %s", "ON" if self.auto_decrypt else "OFF")
             
            # Pass encryption keys to decoder if we have them
            if self.encryption_keys:
                self.decoder.set_keys(self.encryption_keys)
                logger.info(f"Passed {len(self.encryption_keys)} encryption keys to decoder")
            else:
                logger.info("No user keys loaded (using common keys only)")
             
            self.voice_processor = VoiceProcessor()
            
            self.status_update.emit(f"✓ Started - {self.frequency/1e6:.3f} MHz")
            
            while self.running:
                try:
                    # Handle pending frequency change
                    if self.pending_freq is not None:
                        try:
                            new_freq = self.pending_freq
                            self.pending_freq = None
                            self.frequency = new_freq
                            self.capture.set_frequency(new_freq)
                            # Only emit status if change is large (> 1kHz) to avoid spamming log during AFC
                            # self.status_update.emit(f"Tuned to {new_freq/1e6:.6f} MHz")
                        except Exception as e:
                            self.error_occurred.emit(f"Failed to set frequency: {e}")

                    # Read larger chunk to ensure full TETRA frames (which are ~14ms long)
                    # 32k was too small (~13ms), causing frame splitting and decode failure
                    # 128k is ~54ms (at 2.4MSps), containing ~3-4 full frames
                    try:
                        samples = self.capture.read_samples(128*1024)
                    except RuntimeError as e:
                        # Device error - stop capture
                        self.error_occurred.emit(f"RTL-SDR device error: {e}. Please restart the application.")
                        self.running = False
                        break
                    
                    # Compute spectrum with proper windowing
                    # Use a fixed FFT size for consistent display resolution
                    n_fft = 2048
                    if len(samples) >= n_fft:
                        # Take a slice for spectrum analysis
                        fft_samples = samples[:n_fft]
                        window = np.hanning(n_fft)
                        
                        # Compute FFT
                        fft = np.fft.fftshift(np.fft.fft(fft_samples * window))
                        freqs = np.fft.fftshift(np.fft.fftfreq(n_fft, 1/self.sample_rate))
                        
                        # Power in dBFS (normalized)
                        # 20*log10(abs(fft)/N) gives dB relative to full scale sine wave
                        # Add epsilon to avoid log(0)
                        power = 20 * np.log10(np.abs(fft) / n_fft + 1e-20)
                        
                        # Shift to actual frequency
                        freqs_actual = freqs + self.frequency
                        
                        # Throttle spectrum updates to ~60 Hz for live feel
                        current_time = time.time()
                        if current_time - last_spectrum_update >= spectrum_update_interval:
                            self.spectrum_update.emit(freqs_actual, power)
                            last_spectrum_update = current_time
                    
                    # Detect signal (using the computed power)
                    signal_present = False
                    if len(samples) >= n_fft:
                        # Calculate average power in the center frequency range (TETRA bandwidth)
                        center_idx = len(power) // 2
                        bandwidth_hz = 25000  # 25 kHz TETRA bandwidth
                        freq_resolution = self.sample_rate / n_fft
                        bandwidth_bins = int(bandwidth_hz / freq_resolution)
                        start_idx = max(0, center_idx - bandwidth_bins // 2)
                        end_idx = min(len(power), center_idx + bandwidth_bins // 2)
                        
                        if end_idx > start_idx:
                            signal_power = np.mean(power[start_idx:end_idx])
                            peak_power = np.max(power[start_idx:end_idx])
                            
                            # Calculate frequency offset for AFC
                            # Find peak bin index
                            peak_idx_local = np.argmax(power[start_idx:end_idx])
                            peak_idx = start_idx + peak_idx_local
                            
                            # Calculate offset from center frequency (0 Hz in baseband)
                            # freqs array is centered at 0
                            peak_freq_offset = freqs[peak_idx]
                            
                            # Calculate noise floor from outside the center channel
                            # Use 100kHz offset to be safe (approx 4x bandwidth)
                            noise_bins_start = 0
                            noise_bins_end = max(0, start_idx - 10)
                            noise_bins_start2 = min(len(power), end_idx + 10)
                            noise_bins_end2 = len(power)
                            
                            noise_power_list = []
                            if noise_bins_end > noise_bins_start:
                                noise_power_list.extend(power[noise_bins_start:noise_bins_end])
                            if noise_bins_end2 > noise_bins_start2:
                                noise_power_list.extend(power[noise_bins_start2:noise_bins_end2])
                                
                            if noise_power_list:
                                noise_floor = np.mean(noise_power_list)
                            else:
                                noise_floor = -100 # Fallback
                                
                            # SNR check
                            snr = signal_power - noise_floor
                            
                            # Use peak power for detection - require clear signal spike
                            detection_power = peak_power
                            
                            # Stricter detection: Require SNR > 15dB AND Peak Power > -70dB
                            # This prevents detecting noise floor or weak interference as signal
                            # Also require peak is significantly above average (at least 3dB) to ensure it's a real spike
                            peak_above_avg = peak_power - signal_power
                            
                            # Signal detection logic
                            is_signal_strong = (snr > 15 and detection_power > -70 and peak_above_avg > 3)
                            
                            if is_signal_strong:
                                self.last_signal_time = current_time
                                signal_present = True
                            
                            # Throttle status updates
                            if current_time - last_status_update >= status_update_interval:
                                if is_signal_strong:
                                    self.signal_detected.emit(self.frequency, signal_power)
                                elif current_time - getattr(self, 'last_signal_time', 0) > 0.5:
                                    # Only emit lost if no signal for 0.5 seconds (hysteresis)
                                    self.signal_lost.emit()
                                last_status_update = current_time
                    
                    # Only attempt to process and decode TETRA frames when signal is actually present
                    # This prevents false positives from noise or non-TETRA signals
                    if signal_present:
                        try:
                            # Demodulate signal with AFC
                            # Use calculated offset if signal is strong enough, otherwise 0
                            # Lower AFC threshold to -70 dB to help with weaker signals
                            afc_offset = peak_freq_offset if signal_present and peak_power > -70 else 0
                            demodulated = self.processor.process(samples, freq_offset=afc_offset)
                            
                            # Store demodulated symbols for voice extraction
                            # Get symbols from processor if available
                            if hasattr(self.processor, 'symbols'):
                                self.demodulated_symbols = self.processor.symbols
                            elif hasattr(self.processor, 'get_symbols'):
                                self.demodulated_symbols = self.processor.get_symbols()
                            else:
                                # Extract symbols from demodulated (if it's symbol stream)
                                # For now, store demodulated as symbols (may need adjustment)
                                self.demodulated_symbols = demodulated if isinstance(demodulated, np.ndarray) else None
                            
                            # Calculate samples per symbol (typically 4 for π/4-DQPSK at 18k samples/sec)
                            # TETRA symbol rate is 18k symbols/sec, so at 180k samples/sec: 10 samples/symbol
                            symbol_rate = 18000  # TETRA symbol rate
                            self.samples_per_symbol = int(self.sample_rate / symbol_rate) if symbol_rate > 0 else 10
                            
                            # FM Demodulation for raw audio recording (for offline decoding)
                            if self.monitor_raw:
                                try:
                                    # Record raw FM demodulated audio at 48kHz for TETRA decoding
                                    # This is the "buzz/rasp" sound that can be processed offline
                                    target_rate = 48000  # TETRA tools expect 48kHz
                                    decimation = int(self.sample_rate / target_rate)
                                    if decimation > 0:
                                        audio_samples = samples[::decimation]
                                        if len(audio_samples) > 1:
                                            # FM demod: angle of product of sample and conjugate of previous sample
                                            audio = np.angle(audio_samples[1:] * np.conj(audio_samples[:-1]))
                                            # Normalize volume
                                            audio = audio / np.pi * 0.5
                                            
                                            # Record to WAV file for offline processing
                                            self._record_raw_audio(audio, target_rate)
                                            
                                            # Also emit for monitoring
                                            self.raw_audio_data.emit(audio)
                                except Exception as audio_err:
                                    pass
                        
                            # Decode TETRA frames (only when signal is present)
                            # This prevents false positives from noise or non-TETRA signals
                            try:
                                # Ensure we have enough symbols to decode (need at least one frame = 255 symbols)
                                if demodulated is None or len(demodulated) < 255:
                                    frames = []
                                else:
                                    frames = self.decoder.decode(demodulated)
                                    # Log when frames are found (but limit logging frequency)
                                    if len(frames) > 0:
                                        import time
                                        if not hasattr(self, '_last_frame_log_time'):
                                            self._last_frame_log_time = 0
                                        current_time = time.time()
                                        if current_time - getattr(self, '_last_frame_log_time', 0) > 5.0:
                                            logger.info(f"✓ Decoded {len(frames)} TETRA frame(s) from signal")
                                            self._last_frame_log_time = current_time
                            except Exception as decode_err:
                                logger.debug(f"Decode error: {decode_err}")
                                frames = []
                            
                            # Emit all decoded frames
                            for frame in frames:
                                    # Try to extract and decode voice from frames
                                    try:
                                        if self.voice_processor and self.voice_processor.working:
                                            # Check if this might be a voice frame
                                            # Voice is typically in clear MAC-FRAG frames or Traffic frames
                                            mac_pdu = frame.get('mac_pdu', {})
                                            pdu_type = str(mac_pdu.get('type', ''))
                                            is_encrypted = frame.get('encrypted', False)
                                            
                                            # Voice candidates: MAC-FRAG/traffic. Allow encrypted frames only if
                                            # they were successfully decrypted (so we can feed clear bits to the codec).
                                            is_voice_candidate = (
                                                ('FRAG' in pdu_type or frame.get('type') == 1)
                                                and (not is_encrypted or frame.get('decrypted'))
                                            )
                                            
                                            if is_voice_candidate:
                                                # Extract raw bits from the frame
                                                # TETRA voice is encoded in the payload bits
                                                voice_bits = None
                                                
                                                # Try to get bits from frame
                                                if 'bits' in frame:
                                                    voice_bits = frame['bits']
                                                elif 'mac_pdu' in frame and 'data' in mac_pdu:
                                                    # Convert MAC data to bits
                                                    data = mac_pdu['data']
                                                    if isinstance(data, bytes):
                                                        # Convert bytes to bit array
                                                        bit_list = []
                                                        for byte_val in data:
                                                            for bit_idx in range(8):
                                                                bit_list.append((byte_val >> (7 - bit_idx)) & 1)
                                                        voice_bits = np.array(bit_list, dtype=np.uint8)
                                                
                                                # Check if frame is encrypted and decrypted - OVERRIDE bits
                                                if frame.get('decrypted') and 'decrypted_payload' in frame:
                                                    try:
                                                        payload_str = frame['decrypted_payload']
                                                        # Convert string '0101...' to list of ints
                                                        voice_bits = np.array([int(b) for b in payload_str], dtype=np.uint8)
                                                    except Exception as e:
                                                        logger.debug(f"Error using decrypted payload: {e}")

                                                # Try to extract voice slot from symbol stream (preferred method)
                                                codec_input = None
                                                # Only use symbols if NOT encrypted (symbols are raw/encrypted)
                                                if not frame.get('encrypted') and hasattr(self, 'demodulated_symbols') and self.demodulated_symbols is not None:
                                                    codec_input = self._extract_voice_slot_from_symbols(frame, self.demodulated_symbols, self.samples_per_symbol)
                                                
                                                # If extraction from symbols failed, try alternative method
                                                if codec_input is None and voice_bits is not None and len(voice_bits) >= 432:
                                                    # Build codec input format from 432 soft bits
                                                    # cdecoder expects 690 shorts with specific structure
                                                    import struct
                                                    
                                                    # Create 690-short block structure for TETRA ACELP codec
                                                    # The codec expects quantized ACELP parameters, not raw bits
                                                    # We need to extract and properly format the codec parameters
                                                    
                                                    # TETRA ACELP frame structure (137 bits per subframe, 4 subframes):
                                                    # - Frame energy: 6 bits
                                                    # - Pitch delay: 7 bits
                                                    # - Pitch gain: 3 bits
                                                    # - Grid index: 2 bits
                                                    # - 4x Pulse positions: 9 bits each
                                                    # - 4x Pulse signs: 4 bits
                                                    # - Adaptive codebook gain: 5 bits
                                                    # - Fixed codebook gain: 5 bits
                                                    
                                                    block = [0] * 690
                                                    block[0] = 0x6B21  # Header marker
                                                    
                                                    # Convert bits to proper codec parameters
                                                    # Use stronger quantization to generate actual audio
                                                    # Map voice_bits to ACELP parameter space
                                                    
                                                    if len(voice_bits) >= 432:
                                                        # Process 4 subframes (108 bits each)
                                                        for subframe in range(4):
                                                            offset = subframe * 108
                                                            sub_bits = voice_bits[offset:offset+108]
                                                            base_idx = 1 + subframe * 172  # Each subframe uses ~172 shorts
                                                            
                                                            if len(sub_bits) >= 108:
                                                                # Extract ACELP parameters from bits
                                                                # Energy (6 bits) -> scale to codec range
                                                                energy_bits = sub_bits[0:6]
                                                                energy = sum(b << i for i, b in enumerate(energy_bits))
                                                                block[base_idx] = int((energy / 63.0) * 1000) - 500  # Scale to ±500
                                                                
                                                                # Pitch delay (7 bits)
                                                                pitch_bits = sub_bits[6:13]
                                                                pitch = sum(b << i for i, b in enumerate(pitch_bits))
                                                                block[base_idx+1] = int((pitch / 127.0) * 200) + 20  # Range: 20-220
                                                                
                                                                # Pitch gain (3 bits)
                                                                gain_bits = sub_bits[13:16]
                                                                gain = sum(b << i for i, b in enumerate(gain_bits))
                                                                block[base_idx+2] = int((gain / 7.0) * 150)  # 0-150
                                                                
                                                                # Fill remaining with quantized bit values
                                                                for i, bit in enumerate(sub_bits[16:108]):
                                                                    if base_idx + 3 + i < 690:
                                                                        # Use stronger quantization: ±300 instead of ±127
                                                                        block[base_idx + 3 + i] = 300 if bit else -300
                                                    
                                                    # Pack as binary (little-endian signed shorts)
                                                    codec_input = struct.pack('<' + 'h' * 690, *block)
                                                
                                                # Process codec input if we have it
                                                if codec_input is not None and len(codec_input) == 1380:
                                                    # Save raw frame to file for debugging/offline processing
                                                    try:
                                                        import os
                                                        from datetime import datetime
                                                        records_dir = str(RECORDS_DIR)
                                                        os.makedirs(records_dir, exist_ok=True)
                                                        
                                                        # Save with timestamp for easier identification
                                                        if not hasattr(self, 'raw_frames_file') or not self.raw_frames_file:
                                                            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                                                            freq_mhz = self.frequency / 1e6
                                                            self.raw_frames_file = os.path.join(records_dir, f"tetra_frames_{freq_mhz:.3f}MHz_{timestamp}.bin")
                                                            audio_logger.info("Recording raw frames: %s", os.path.basename(self.raw_frames_file))
                                                        
                                                        with open(self.raw_frames_file, 'ab') as f:  # Append mode
                                                            f.write(codec_input)
                                                    except Exception as e:
                                                        logger.debug(f"Failed to save raw frame: {e}")
                                                    
                                                    # Decode with TETRA codec
                                                    audio_segment = self.voice_processor.decode_frame(codec_input)
                                                    if len(audio_segment) > 0:
                                                        self.voice_audio_data.emit(audio_segment)
                                                        frame['has_voice'] = True
                                                        logger.info(f"[OK] Decoded voice: {len(audio_segment)} samples from frame {frame.get('number')}")
                                                        audio_logger.info("Decoded voice: %s samples from frame %s", len(audio_segment), frame.get('number'))
                                                    else:
                                                        logger.debug(f"Codec returned empty audio for frame {frame.get('number')}")
                                                        audio_logger.debug("Codec returned empty audio for frame %s", frame.get('number'))
                                                else:
                                                    logger.debug(f"Frame has insufficient data: voice_bits={len(voice_bits) if voice_bits is not None else 0}, codec_input={len(codec_input) if codec_input else 0}")
                                    except Exception as voice_err:
                                        logger.debug(f"Voice decode error: {voice_err}")
                            
                                    self.frame_decoded.emit(frame)
                            
                            # Don't generate test frames - only show real decoded frames
                            # Test frames cause false positives and confusion
                    
                        except Exception as decode_err:
                            # Log error but don't spam
                            if not hasattr(self, '_decode_error_logged'):
                                self.error_occurred.emit(f"Decode error: {decode_err}")
                                self._decode_error_logged = True
                    
                except Exception as e:
                    self.error_occurred.emit(f"Capture error: {e}")
                    import traceback
                    traceback.print_exc()
                    break
        
        except Exception as e:
            self.error_occurred.emit(f"Fatal error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            if self.capture:
                self.capture.close()
            self.status_update.emit("Stopped")
    
    def _record_raw_audio(self, audio_data, sample_rate):
        """Record raw FM demodulated audio for offline TETRA decoding."""
        import wave
        import os
        from datetime import datetime
        
        try:
            # Start new recording if not active
            if not hasattr(self, 'raw_audio_recording') or not self.raw_audio_recording:
                records_dir = str(RECORDS_DIR)
                os.makedirs(records_dir, exist_ok=True)
                
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                freq_mhz = self.frequency / 1e6
                self.raw_audio_file = os.path.join(records_dir, f"tetra_raw_{freq_mhz:.4f}MHz.wav")
                
                # Open WAV file for writing (48kHz, 16-bit, mono)
                self.raw_wav_file = wave.open(self.raw_audio_file, 'wb')
                self.raw_wav_file.setnchannels(1)
                self.raw_wav_file.setsampwidth(2)
                self.raw_wav_file.setframerate(sample_rate)
                
                self.raw_audio_recording = True
                audio_logger.info("Started raw audio recording: %s", os.path.basename(self.raw_audio_file))
            
            # Write audio data
            if self.raw_audio_recording and hasattr(self, 'raw_wav_file'):
                audio_int16 = (audio_data * 32767).astype(np.int16)
                self.raw_wav_file.writeframes(audio_int16.tobytes())
                
        except Exception as e:
            logger.debug(f"Raw audio recording error: {e}")
    
    def _stop_raw_audio_recording(self):
        """Stop raw audio recording."""
        if hasattr(self, 'raw_audio_recording') and self.raw_audio_recording:
            try:
                if hasattr(self, 'raw_wav_file'):
                    self.raw_wav_file.close()
                self.raw_audio_recording = False
                audio_logger.info("Stopped raw audio recording: %s", os.path.basename(self.raw_audio_file))
            except Exception as e:
                logger.debug(f"Error stopping raw audio recording: {e}")

    def _extract_voice_slot_from_symbols(self, frame, demodulated_symbols, samples_per_symbol):
        """
        Extract TETRA voice slot from symbol stream for codec.
        Returns soft bits (16-bit integers) in TETRA format (690 shorts = 1380 bytes).
        """
        try:
            import struct
            
            # Get frame position in symbol stream (in bits, not symbols)
            pos = frame.get('position')
            if pos is None:
                return None
            
            # Convert bit position to symbol position (3 bits per symbol for π/4-DQPSK)
            symbol_pos = pos // 3
                
            # TETRA slot is 255 symbols (510 bits)
            if symbol_pos + 255 > len(demodulated_symbols):
                return None
                
            slot_symbols = demodulated_symbols[symbol_pos:symbol_pos+255]
            
            # Convert symbols to soft bits for codec
            # π/4-DQPSK has 2 bits per symbol (dibits)
            soft_bits = []
            
            # Normal burst structure:
            # First block: 108 symbols (216 bits)
            # Training: 11 symbols (22 bits)
            # Second block: 108 symbols (216 bits)
            # Total: 227 symbols before tail
            
            # Extract first block (108 symbols = 216 bits)
            for i in range(108):
                if i >= len(slot_symbols):
                    break
                sym = int(slot_symbols[i])
                # Extract 2 bits from symbol (MSB first)
                bit1 = (sym >> 1) & 1
                bit0 = sym & 1
                # Convert to soft bits: 1 -> +16384, 0 -> -16384
                soft_bits.append(16384 if bit1 else -16384)
                soft_bits.append(16384 if bit0 else -16384)
            
            # Skip training sequence (11 symbols at position 108-118)
            
            # Extract second block (108 symbols = 216 bits)
            for i in range(119, 227):
                if i >= len(slot_symbols):
                    break
                sym = int(slot_symbols[i])
                bit1 = (sym >> 1) & 1
                bit0 = sym & 1
                soft_bits.append(16384 if bit1 else -16384)
                soft_bits.append(16384 if bit0 else -16384)
            
            # Now we have 432 soft bits (216 from each block)
            # cdecoder expects 690 shorts with specific structure matching Write_Tetra_File format
            # Soft bits must be in range -127 to +127 (masked with 0x00FF)
            
            # Create 690-short block structure
            block = [0] * 690
            
            # Header: 0x6B21 for speech frame
            block[0] = 0x6B21
            
            # Convert soft bits to proper range (-127 to +127)
            # Current soft_bits are ±16384, need to scale to ±127
            scaled_soft_bits = []
            for sb in soft_bits:
                # Scale from ±16384 to ±127 range
                scaled = int((sb / 16384.0) * 127)
                # Clamp to valid range
                scaled = max(-127, min(127, scaled))
                scaled_soft_bits.append(scaled)
            
            # Place 432 soft bits in correct positions according to Write_Tetra_File structure
            # Block 1: positions 1-114 (114 bits)
            # Block 2: positions 116-229 (114 bits) 
            # Block 3: positions 231-344 (114 bits)
            # Block 4: positions 346-435 (90 bits)
            
            idx = 0
            # Block 1: positions 1-114
            for i in range(1, 115):
                if idx < len(scaled_soft_bits):
                    block[i] = scaled_soft_bits[idx]  # No mask for signed short
                    idx += 1
            
            # Block 2: positions 116-229 (161-45=116)
            for i in range(116, 230):
                if idx < len(scaled_soft_bits):
                    block[i] = scaled_soft_bits[idx]
                    idx += 1
            
            # Block 3: positions 231-344 (321-45-45=231)
            for i in range(231, 345):
                if idx < len(scaled_soft_bits):
                    block[i] = scaled_soft_bits[idx]
                    idx += 1
            
            # Block 4: positions 346-435 (481-45-45-45=346, 90 values)
            for i in range(346, 436):
                if idx < len(scaled_soft_bits):
                    block[i] = scaled_soft_bits[idx]
                    idx += 1
            
            # Pack as little-endian signed shorts
            return struct.pack(f'<{len(block)}h', *block)
            
        except Exception as e:
            logger.debug(f"Error extracting voice slot: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            return None
    
    def _generate_synthetic_frame(self):
        """Generate synthetic frame for display (avoids parse errors)."""
        import random
        
        frame_types = ['Broadcast', 'Traffic', 'Control', 'MAC']
        frame_type = random.choice([0, 1, 2, 3])
        
        frame = {
            'number': random.randint(0, 255),
            'type': frame_type,
            'encrypted': random.choice([True, False, False]),  # 33% encrypted
            'decrypted': False,
            'additional_info': {}
        }
        
        # Generate rich descriptions based on frame type
        if frame_type == 0:  # Broadcast
            frame['additional_info']['description'] = random.choice([
                'System broadcast - Network sync',
                'System broadcast - Time sync',
                'System broadcast - Cell info',
                'Network information',
            ])
            frame['additional_info']['network_id'] = random.randint(1000, 9999)
            frame['additional_info']['channel'] = random.choice(['Main', 'Control', 'Backup'])
            
        elif frame_type == 1:  # Traffic
            frame['additional_info']['description'] = random.choice([
                'Traffic channel - Voice call',
                'Traffic channel - Data transfer',
                'Voice transmission',
                'Data packet',
            ])
            frame['additional_info']['channel'] = random.choice(['Voice', 'Data'])
            if random.random() < 0.7:  # 70% have talkgroup
                frame['additional_info']['talkgroup'] = random.randint(1, 9999)
                frame['additional_info']['source_ssi'] = random.randint(100000, 999999)
                frame['additional_info']['dest_ssi'] = random.randint(100000, 999999)
                
        elif frame_type == 2:  # Control
            frame['additional_info']['description'] = random.choice([
                'Control channel - Call setup',
                'Control channel - Call teardown',
                'Registration request',
                'Authentication',
                'Channel assignment',
            ])
            frame['additional_info']['control'] = random.choice([
                'Call setup', 
                'Call teardown', 
                'Registration',
                'Location update',
                'Group call request',
            ])
            if random.random() < 0.5:
                frame['additional_info']['talkgroup'] = random.randint(1, 9999)
                
        elif frame_type == 3:  # MAC
            frame['additional_info']['description'] = random.choice([
                'MAC frame - Access control',
                'MAC frame - Resource grant',
                'Medium access request',
                'Slot allocation',
            ])
        
        # Simulate decryption attempts
        if frame['encrypted'] and random.random() < 0.4:  # 40% success rate
            frame['decrypted'] = True
            frame['key_used'] = random.choice([
                'TEA1 common_key_0 (null)',
                'TEA1 common_key_3 (sequential)',
                'TEA2 common_key_1',
                'TEA1 weak_key',
            ])
            frame['decrypt_confidence'] = random.randint(50, 99)
            frame['decrypted_bytes'] = ''.join(random.choices('0123456789ABCDEF', k=32))
        
        return frame
    
    def stop(self):
        """Stop capture."""
        self.running = False
        # Stop raw audio recording if active
        if hasattr(self, 'raw_audio_recording') and self.raw_audio_recording:
            try:
                if hasattr(self, 'raw_wav_file'):
                    self.raw_wav_file.close()
                self.raw_audio_recording = False
                audio_logger.info("Stopped raw audio recording")
            except Exception as e:
                logger.debug(f"Error stopping raw audio recording: {e}")


class ModernTetraGUI(QMainWindow):
    """Modern TETRA decoder GUI."""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("TetraEar - Professional TETRA Decoder v2.0")
        self.setGeometry(100, 100, 1600, 1100)
        
        # Set application icon
        self.set_app_icon()

        self.capture_thread = None
        self.frame_count = 0
        self.decrypted_count = 0
        self.scanner_dialog = None
        self.encryption_keys = []
        self.auto_spectrum_enabled = False
        self._last_auto_spectrum_time = 0.0
        
        # Filter data sets
        self.known_call_groups = set()
        self.known_call_clients = set()
        self.known_user_groups = set()
        
        # TETRA signal detection tracking
        self.tetra_sync_count = 0
        self.tetra_frame_count = 0
        self.tetra_valid_frames = 0
        self.last_tetra_update = 0.0
        self.signal_present = False  # Track if signal is currently present
        self.first_frame_time = None  # Track when first frame was detected
        self.min_detection_time = 5.0  # Minimum seconds before showing "TETRA Signal Detected"
        
        # SDS reassembly tracking
        self.sds_fragments = {}  # Key: (src, dst, msg_id), Value: {fragments, timestamp}
        self.sds_timeout = 30  # seconds
        
        # Continuous audio recording
        self.continuous_recording = True
        self.audio_buffer = []
        self.recording_active = False
        self.recording_enabled = False  # Manual recording toggle
        self.recording_start_time = None
        self.recording_has_audio = False  # Track if valid audio was recorded
        
        # Managers
        self.settings_manager = SettingsManager()
        self.freq_manager = FrequencyManager()
        
        # TETRA signal validator (expect Poland MCC 260)
        self.signal_validator = TetraSignalValidator(expected_country_mcc=260)
        
        self.init_ui()
        self.apply_modern_style()
        
        # Load settings
        self.load_settings()
        
        # Update timer
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_displays)
        self.update_timer.start(100)
        
        # Initialize audio
        self.init_audio()

        # Auto-size table columns periodically (throttled) so columns fit content.
        self._autosize_state: dict[str, int] = {}
        self._autosize_timer = QTimer(self)
        self._autosize_timer.timeout.connect(self._autosize_tables)
        self._autosize_timer.start(2000)
        QTimer.singleShot(0, self._autosize_tables)

    def _autosize_table(self, table: QTableWidget, *, max_width: int = 520) -> None:
        """Resize columns to fit contents, clamping overly wide columns."""
        try:
            table.resizeColumnsToContents()
            for col in range(table.columnCount()):
                if table.columnWidth(col) > max_width:
                    table.setColumnWidth(col, max_width)
        except Exception:
            pass

    def _autosize_tables(self) -> None:
        """Auto-size all tables when row count changes."""
        tables: list[tuple[str, QTableWidget, int]] = []
        if hasattr(self, "frames_table"):
            tables.append(("frames_table", self.frames_table, 600))
        if hasattr(self, "calls_table"):
            tables.append(("calls_table", self.calls_table, 320))
        if hasattr(self, "groups_table"):
            tables.append(("groups_table", self.groups_table, 320))
        if hasattr(self, "users_table"):
            tables.append(("users_table", self.users_table, 360))

        for name, table, cap in tables:
            try:
                rows = table.rowCount()
                if self._autosize_state.get(name) == rows:
                    continue
                self._autosize_state[name] = rows
                self._autosize_table(table, max_width=cap)
            except Exception:
                continue
    
    def load_settings(self):
        """Load initial settings."""
        s = self.settings_manager
        self.freq_input.setText(str(s.get("last_frequency", 390.865)))
        self.auto_decrypt_cb.setChecked(s.get("auto_decrypt", True))
        self.hear_voice_cb.setChecked(s.get("monitor_audio", True))
        self.monitor_raw_cb.setChecked(s.get("monitor_raw", False))
        
        # Update presets
        self.update_presets()

    def update_presets(self):
        """Update preset combo box."""
        self.freq_preset.clear()
        self.freq_preset.addItem("Custom")
        for item in self.freq_manager.get_all():
            self.freq_preset.addItem(f"{item['freq']:.3f} MHz - {item['label']}")

    def open_settings(self):
        """Open settings dialog."""
        dlg = SettingsDialog(self.settings_manager, self)
        if dlg.exec():
            # Apply settings immediately if needed
            pass

    def save_current_freq(self):
        """Open save frequency dialog."""
        try:
            freq = float(self.freq_input.text())
            dlg = FrequencyDialog(freq, self.freq_manager, self)
            if dlg.exec():
                self.update_presets()
        except ValueError:
            pass
    
    def show_about(self):
        """Show about dialog with banner."""
        dlg = AboutDialog(self)
        dlg.exec()

    def set_app_icon(self):
        """Load and set application icon from assets folder."""
        # Try to load icon from assets folder
        icon_paths = [
            ASSETS_DIR / "icon.ico",
            ASSETS_DIR / "icon_preview.png",
            ASSETS_DIR / "icon.png"
        ]
        
        icon_loaded = False
        for icon_path in icon_paths:
            if icon_path.exists():
                try:
                    icon = QIcon(str(icon_path))
                    if not icon.isNull():
                        self.setWindowIcon(icon)
                        logger.debug(f"Loaded icon from: {icon_path}")
                        icon_loaded = True
                        break
                except Exception as e:
                    logger.debug(f"Failed to load icon from {icon_path}: {e}")
        
        # Fallback: create icon programmatically if assets not found
        if not icon_loaded:
            logger.debug("Creating fallback icon programmatically")
            size = 64
            pixmap = QPixmap(size, size)
            pixmap.fill(Qt.GlobalColor.transparent)
            
            painter = QPainter(pixmap)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            
            # Draw background circle
            painter.setBrush(QBrush(QColor(40, 60, 100)))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(2, 2, size-4, size-4)
            
            # Draw signal wave
            path = QPainterPath()
            path.moveTo(10, size/2)
            path.cubicTo(size/3, size/4, 2*size/3, 3*size/4, size-10, size/2)
            
            pen = QPen(QColor(0, 255, 255))
            pen.setWidth(4)
            painter.setPen(pen)
            painter.drawPath(path)
            
            # Draw text
            painter.setPen(QColor(255, 255, 255))
            font = QFont("Arial", 10, QFont.Weight.Bold)
            painter.setFont(font)
            painter.drawText(QRect(0, 0, size, size), Qt.AlignmentFlag.AlignCenter, "TETRA")
            
            painter.end()
            
            self.setWindowIcon(QIcon(pixmap))

    def init_ui(self):
        """Initialize UI with compact layout."""
        central = QWidget()
        self.setCentralWidget(central)
        # Use QSplitter for resizable panels
        main_splitter = QSplitter(Qt.Orientation.Vertical)
        main_splitter.setChildrenCollapsible(False)
        self._main_splitter = main_splitter
        
        # Top controls - with proper size policy
        control_panel = self.create_control_panel()
        control_panel.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        control_panel.setMinimumHeight(300)
        self._control_panel = control_panel
        main_splitter.addWidget(control_panel)
        
        # Waterfall spectrum - with proportional sizing
        spectrum_group = QGroupBox("Spectrum Analyzer")
        spectrum_layout = QVBoxLayout()
        spectrum_layout.setContentsMargins(5, 5, 5, 5)
        self.waterfall = WaterfallWidget()
        self.waterfall.setMinimumHeight(200)
        self.waterfall.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        spectrum_layout.addWidget(self.waterfall)
        spectrum_group.setLayout(spectrum_layout)
        spectrum_group.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        main_splitter.addWidget(spectrum_group)
        
        # Tabs - with scroll area for table
        tabs = QTabWidget()
        
        # Frames tab with scrollable table
        frames_widget = self.create_frames_tab()
        tabs.addTab(frames_widget, "📡 Decoded Frames")
        
        # Calls tab
        calls_widget = self.create_calls_tab()
        tabs.addTab(calls_widget, "📞 Calls")
        
        # Groups tab
        groups_widget = self.create_groups_tab()
        tabs.addTab(groups_widget, "👥 Groups")
        
        # Users tab
        users_widget = self.create_users_tab()
        tabs.addTab(users_widget, "👤 Users")
        
        # Log tab
        log_widget = QWidget()
        log_layout = QVBoxLayout()
        log_layout.setContentsMargins(5, 5, 5, 5)
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Consolas", 9))
        log_layout.addWidget(self.log_text)
        log_widget.setLayout(log_layout)
        tabs.addTab(log_widget, "📋 Log")
        
        # Stats tab
        stats_widget = self.create_stats_tab()
        tabs.addTab(stats_widget, "📊 Statistics")
        
        tabs.setMinimumHeight(200)
        main_splitter.addWidget(tabs)
        
        # Set initial sizes after layout is realized (make sure the full control panel is visible).
        main_splitter.setStretchFactor(0, 1)
        main_splitter.setStretchFactor(1, 1)
        main_splitter.setStretchFactor(2, 1)
        QTimer.singleShot(0, self._apply_initial_splitter_sizes)
        
        # Add splitter to main layout
        main_layout = QVBoxLayout(central)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.addWidget(main_splitter)
        
        # Status bar
        self.statusBar().showMessage("Ready")

    def _apply_initial_splitter_sizes(self) -> None:
        splitter = getattr(self, "_main_splitter", None)
        control_panel = getattr(self, "_control_panel", None)
        if splitter is None or control_panel is None:
            return

        total_h = splitter.size().height()
        if total_h <= 0:
            total_h = self.height()

        # Aim to show all top control groups without scrolling.
        control_hint = control_panel.sizeHint().height()
        control_target = min(max(control_hint + 40, 520), int(total_h * 0.62))

        # Keep spectrum and tabs usable too.
        spectrum_min = 220
        tabs_min = 260
        remaining = max(0, total_h - control_target)

        spectrum_target = max(spectrum_min, int(remaining * 0.45))
        tabs_target = max(tabs_min, remaining - spectrum_target)

        splitter.setSizes([control_target, spectrum_target, tabs_target])
    
    def create_control_panel(self):
        """Create modern control panel with redesigned layout."""
        # Main container with horizontal layout - compact
        main_widget = QWidget()
        main_layout = QHBoxLayout(main_widget)
        main_layout.setSpacing(12)  # Increased spacing
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        # Left column: Frequency and tuning - compact
        left_col = QVBoxLayout()
        left_col.setSpacing(8)  # Increased spacing
        
        # Frequency group
        freq_group = QGroupBox("Frequency")
        freq_layout = QVBoxLayout()
        freq_layout.setSpacing(6)
        freq_row1 = QHBoxLayout()
        freq_label = QLabel("Frequency (MHz):")
        freq_label.setMinimumWidth(100)
        freq_row1.addWidget(freq_label)
        self.freq_input = QLineEdit("390.865")  # Default frequency per user specification
        self.freq_input.setMinimumWidth(100)
        self.freq_input.setMaximumWidth(150)
        self.freq_input.setPlaceholderText("390.000")
        freq_row1.addWidget(self.freq_input, 1)  # Stretch factor
        
        # Save Freq Button
        self.save_freq_btn = QPushButton("💾")
        self.save_freq_btn.setToolTip("Save Frequency")
        self.save_freq_btn.setMaximumWidth(40)
        self.save_freq_btn.clicked.connect(self.save_current_freq)
        freq_row1.addWidget(self.save_freq_btn)
        
        self.tune_btn = QPushButton("⚡ Tune")
        self.tune_btn.clicked.connect(self.on_tune)
        self.tune_btn.setMinimumWidth(80)
        freq_row1.addWidget(self.tune_btn)
        freq_layout.addLayout(freq_row1)
        
        freq_row2 = QHBoxLayout()
        preset_label = QLabel("Preset:")
        preset_label.setMinimumWidth(100)
        freq_row2.addWidget(preset_label)
        self.freq_preset = QComboBox()
        # Items populated by update_presets()
        self.freq_preset.currentTextChanged.connect(self.on_preset_changed)
        freq_row2.addWidget(self.freq_preset, 1)  # Stretch factor
        freq_layout.addLayout(freq_row2)
        
        # Bandwidth input
        bw_row = QHBoxLayout()
        bw_label = QLabel("Bandwidth (Hz):")
        bw_label.setMinimumWidth(100)
        bw_row.addWidget(bw_label)
        self.bw_input = QLineEdit("25000")
        self.bw_input.setMinimumWidth(100)
        self.bw_input.setMaximumWidth(150)
        self.bw_input.textChanged.connect(self.on_bandwidth_changed)
        bw_row.addWidget(self.bw_input, 1)
        freq_layout.addLayout(bw_row)
        
        freq_group.setLayout(freq_layout)
        left_col.addWidget(freq_group)
        
        # Action buttons
        button_group = QGroupBox("Actions")
        button_layout = QVBoxLayout()
        button_layout.setSpacing(6)
        button_row1 = QHBoxLayout()
        button_row1.setSpacing(6)
        self.start_btn = QPushButton("▶ START")
        self.start_btn.clicked.connect(self.on_start)
        self.start_btn.setMinimumHeight(40)
        self.start_btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        button_row1.addWidget(self.start_btn, 1)  # Stretch factor
        
        self.stop_btn = QPushButton("⏹ STOP")
        self.stop_btn.clicked.connect(self.on_stop)
        self.stop_btn.setEnabled(False)
        self.stop_btn.setMinimumHeight(40)
        self.stop_btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        button_row1.addWidget(self.stop_btn, 1)  # Stretch factor
        
        self.record_btn = QPushButton("🔴 REC")
        self.record_btn.setCheckable(True)
        self.record_btn.clicked.connect(self.toggle_recording)
        self.record_btn.setMinimumHeight(40)
        self.record_btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.record_btn.setStyleSheet("QPushButton:checked { background-color: #7f1d1d; border-color: #ef4444; }")
        button_row1.addWidget(self.record_btn, 1)
        
        button_layout.addLayout(button_row1)
        
        button_row2 = QHBoxLayout()
        button_row2.setSpacing(6)
        self.scan_btn = QPushButton("🔍 SCAN")
        self.scan_btn.clicked.connect(self.on_scan)
        self.scan_btn.setMinimumHeight(36)
        self.scan_btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        button_row2.addWidget(self.scan_btn, 1)  # Stretch factor
        
        self.load_keys_btn = QPushButton("🔑 Load Keys")
        self.load_keys_btn.clicked.connect(self.on_load_keys)
        self.load_keys_btn.setMinimumHeight(36)
        self.load_keys_btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        button_row2.addWidget(self.load_keys_btn, 1)  # Stretch factor
        
        # Settings Button
        self.settings_btn = QPushButton("⚙️ Settings")
        self.settings_btn.clicked.connect(self.open_settings)
        self.settings_btn.setMinimumHeight(36)
        self.settings_btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        button_row2.addWidget(self.settings_btn, 1)
        
        # About button
        about_btn = QPushButton("ℹ About")
        about_btn.clicked.connect(self.show_about)
        about_btn.setMinimumHeight(36)
        about_btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        button_row2.addWidget(about_btn, 1)
        
        button_layout.addLayout(button_row2)

        # Moved Spectrum Display toggles here for easier access
        toggles_layout = QVBoxLayout()
        toggles_layout.setSpacing(4)

        self.auto_spectrum_cb = QCheckBox("Auto Spectrum Sliders")
        self.auto_spectrum_cb.setToolTip("Dynamically adjust zoom, top, bottom, and threshold based on live signal")
        self.auto_spectrum_cb.toggled.connect(self.on_auto_spectrum_toggled)
        toggles_layout.addWidget(self.auto_spectrum_cb)

        self.denoiser_cb = QCheckBox("Denoiser (Smooth)")
        self.denoiser_cb.toggled.connect(self.on_denoiser_toggled)
        toggles_layout.addWidget(self.denoiser_cb)

        # Auto frequency correction (spike locking)
        self.follow_freq_cb = QCheckBox("Auto-Follow Spike (AFC)")
        self.follow_freq_cb.setChecked(False)
        self.follow_freq_cb.setToolTip("Automatically adjust tuning to keep the main spike centered")
        toggles_layout.addWidget(self.follow_freq_cb)

        button_layout.addLayout(toggles_layout)
        button_group.setLayout(button_layout)
        left_col.addWidget(button_group)
        
        left_col.addStretch()
        main_layout.addLayout(left_col, 1)  # Stretch factor
        
        # Middle column: Gain and Sample Rate - compact
        middle_col = QVBoxLayout()
        middle_col.setSpacing(6)
        
        # Gain slider
        gain_group = QGroupBox("Gain")
        gain_layout = QVBoxLayout()
        gain_row = QHBoxLayout()
        gain_row.setSpacing(8)
        gain_label = QLabel("Gain:")
        gain_label.setMinimumWidth(50)
        gain_row.addWidget(gain_label)
        self.gain_slider = QSlider(Qt.Orientation.Horizontal)
        self.gain_slider.setMinimum(0)
        self.gain_slider.setMaximum(100)  # 0-50 with 0.5 steps
        self.gain_slider.setValue(100)  # Default 50.0 (100/2 = 50)
        self.gain_slider.valueChanged.connect(self.on_gain_slider_changed)
        self.gain_slider.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        gain_row.addWidget(self.gain_slider, 1)  # Stretch factor
        self.gain_label = QLabel("50.0 dB")
        self.gain_label.setMinimumWidth(70)
        self.gain_label.setMaximumWidth(80)
        self.gain_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.gain_label.setStyleSheet("font-weight: bold; font-size: 12px;")
        gain_row.addWidget(self.gain_label)
        gain_layout.addLayout(gain_row)
        gain_group.setLayout(gain_layout)
        middle_col.addWidget(gain_group)
        
        # Sample Rate slider - with 0.1 MHz steps from 1.8 to 10.0 MHz
        sample_rate_group = QGroupBox("Sample Rate")
        sample_rate_layout = QVBoxLayout()
        sample_rate_row = QHBoxLayout()
        sample_rate_row.setSpacing(8)
        rate_label = QLabel("Rate:")
        rate_label.setMinimumWidth(50)
        sample_rate_row.addWidget(rate_label)
        self.sample_rate_slider = QSlider(Qt.Orientation.Horizontal)
        # RTL-SDR valid rates: 0.225, 0.9, 1.024, 1.536, 1.8, 1.92, 2.048, 2.4, 2.56, 2.88, 3.2 MHz
        # Map slider to most common rates: 1.8, 1.92, 2.048, 2.4, 2.56, 2.88, 3.2
        valid_rates_mhz = [1.8, 1.92, 2.048, 2.4, 2.56, 2.88, 3.2]
        self.valid_sample_rates = valid_rates_mhz
        self.sample_rate_slider.setMinimum(0)
        self.sample_rate_slider.setMaximum(len(valid_rates_mhz) - 1)
        self.sample_rate_slider.setValue(3)  # Default 2.4 MHz (index 3)
        self.sample_rate_slider.setSingleStep(1)
        self.sample_rate_slider.valueChanged.connect(self.on_sample_rate_slider_changed)
        self.sample_rate_slider.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        sample_rate_row.addWidget(self.sample_rate_slider, 1)  # Stretch factor
        self.sample_rate_label = QLabel("2.4 MHz")
        self.sample_rate_label.setMinimumWidth(70)
        self.sample_rate_label.setMaximumWidth(80)
        self.sample_rate_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.sample_rate_label.setStyleSheet("font-weight: bold; font-size: 12px;")
        sample_rate_row.addWidget(self.sample_rate_label)
        sample_rate_layout.addLayout(sample_rate_row)
        sample_rate_group.setLayout(sample_rate_layout)
        middle_col.addWidget(sample_rate_group)
        
        # Options group (Moved from right column)
        options_group = QGroupBox("Options")
        options_layout = QVBoxLayout()
        self.auto_decrypt_cb = QCheckBox("Auto-Decrypt")
        self.auto_decrypt_cb.setChecked(True)
        self.auto_decrypt_cb.toggled.connect(self.on_auto_decrypt_toggled)
        options_layout.addWidget(self.auto_decrypt_cb)
        
        self.hear_voice_cb = QCheckBox("🔊 Monitor Audio")
        self.hear_voice_cb.setChecked(False)  # Disable by default
        self.hear_voice_cb.setToolTip("Listen to decoded voice (if available)")
        options_layout.addWidget(self.hear_voice_cb)
        
        self.monitor_raw_cb = QCheckBox("📻 Raw Signal (FM)")
        self.monitor_raw_cb.setChecked(False)
        self.monitor_raw_cb.setToolTip("Listen to raw FM demodulated audio (debug)")
        self.monitor_raw_cb.toggled.connect(self.on_monitor_raw_toggled)
        options_layout.addWidget(self.monitor_raw_cb)
        
        options_group.setLayout(options_layout)
        middle_col.addWidget(options_group)
        
        middle_col.addStretch()
        main_layout.addLayout(middle_col, 1)  # Stretch factor
        
        # Right column: Spectrum Display Controls
        right_col = QVBoxLayout()
        right_col.setSpacing(8)
        
        # Display Controls Group (Combined with Noise Floor)
        display_group = QGroupBox("Spectrum Display")
        display_layout = QVBoxLayout()
        display_layout.setSpacing(14)  # Increased spacing between sliders
        display_layout.setContentsMargins(10, 20, 10, 14)  # Add more top/bottom margin
        
        # Zoom Slider
        zoom_row = QHBoxLayout()
        zoom_label = QLabel("Zoom:")
        zoom_label.setMinimumWidth(60)
        zoom_row.addWidget(zoom_label)
        self.zoom_slider = QSlider(Qt.Orientation.Horizontal)
        self.zoom_slider.setMinimum(10)
        self.zoom_slider.setMaximum(100)
        self.zoom_slider.setValue(10)
        self.zoom_slider.valueChanged.connect(self.on_zoom_changed)
        zoom_row.addWidget(self.zoom_slider)
        display_layout.addLayout(zoom_row)
        
        # Range Slider (Top dB)
        range_row = QHBoxLayout()
        range_label = QLabel("Top:")
        range_label.setMinimumWidth(60)
        range_row.addWidget(range_label)
        self.range_slider = QSlider(Qt.Orientation.Horizontal)
        self.range_slider.setMinimum(-100)
        self.range_slider.setMaximum(20)
        self.range_slider.setValue(0)
        self.range_slider.valueChanged.connect(self.on_range_changed)
        range_row.addWidget(self.range_slider)
        
        self.range_label = QLabel("0 dB")
        self.range_label.setMinimumWidth(50)
        range_row.addWidget(self.range_label)
        
        display_layout.addLayout(range_row)
        
        # Noise Floor Slider (Visual Bottom)
        noise_floor_row = QHBoxLayout()
        threshold_label = QLabel("Bottom:")
        threshold_label.setMinimumWidth(60)
        noise_floor_row.addWidget(threshold_label)
        self.noise_floor_slider = QSlider(Qt.Orientation.Horizontal)
        self.noise_floor_slider.setMinimum(-140)
        self.noise_floor_slider.setMaximum(-40)
        self.noise_floor_slider.setValue(-85)  # Default bottom threshold per user specification
        self.noise_floor_slider.valueChanged.connect(self.on_noise_floor_changed)
        noise_floor_row.addWidget(self.noise_floor_slider)
        
        self.noise_floor_label = QLabel("-85 dB")
        self.noise_floor_label.setMinimumWidth(50)
        noise_floor_row.addWidget(self.noise_floor_label)
        
        display_layout.addLayout(noise_floor_row)
        
        # Threshold Slider (Yellow Line)
        threshold_row = QHBoxLayout()
        threshold_label = QLabel("Threshold:")
        threshold_label.setMinimumWidth(60)
        threshold_row.addWidget(threshold_label)
        self.threshold_slider = QSlider(Qt.Orientation.Horizontal)
        self.threshold_slider.setMinimum(-100)
        self.threshold_slider.setMaximum(-20)
        self.threshold_slider.setValue(-75)  # Default threshold
        self.threshold_slider.valueChanged.connect(self.on_threshold_changed)
        threshold_row.addWidget(self.threshold_slider)
        
        self.threshold_label = QLabel("-75 dB")
        self.threshold_label.setMinimumWidth(50)
        threshold_row.addWidget(self.threshold_label)
        
        display_layout.addLayout(threshold_row)
        
        # (spectrum display toggles moved to Actions panel)
        
        display_group.setLayout(display_layout)
        right_col.addWidget(display_group)
        
        # Status indicators (Moved from right column bottom)
        status_group = QGroupBox("Status")
        status_layout = QVBoxLayout() # Changed to vertical for TETRA status
        status_layout.setSpacing(12)
        status_layout.setContentsMargins(10, 20, 10, 14)
        
        status_row1 = QHBoxLayout()
        self.signal_label = QLabel("⚫ No Signal")
        self.signal_label.setStyleSheet("font-weight: bold; padding: 5px;")
        status_row1.addWidget(self.signal_label)
        
        self.decrypt_label = QLabel("🔒 0/0")
        self.decrypt_label.setStyleSheet("font-weight: bold; padding: 5px;")
        status_row1.addWidget(self.decrypt_label)
        status_layout.addLayout(status_row1)
        
        # Recording status
        self.recording_status_label = QLabel("⚫ Not Recording")
        self.recording_status_label.setStyleSheet("font-weight: bold; padding: 5px; color: #888888;")
        status_layout.addWidget(self.recording_status_label)
        
        # TETRA signal detection status
        self.tetra_status_label = QLabel("⚫ No TETRA Signal")
        self.tetra_status_label.setStyleSheet(
            "font-weight: bold; padding: 5px; color: #888888;"
        )
        status_layout.addWidget(self.tetra_status_label)
        
        status_group.setLayout(status_layout)
        right_col.addWidget(status_group)
        
        right_col.addStretch()
        main_layout.addLayout(right_col, 1)  # Stretch factor
        
        return main_widget
    
    def create_frames_tab(self):
        """Create frames tab."""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Controls
        control_layout = QHBoxLayout()
        
        # Filter
        control_layout.addWidget(QLabel("Filter:"))
        self.type_filter = QComboBox()
        self.type_filter.addItems(["All Types", "Traffic", "Control", "Broadcast", "MAC", "SDS", "Audio"])
        self.type_filter.currentTextChanged.connect(self.apply_filter)
        control_layout.addWidget(self.type_filter)
        
        self.decrypted_only_cb = QCheckBox("Decrypted/Text Only")
        self.decrypted_only_cb.toggled.connect(lambda: self.apply_filter(self.type_filter.currentText()))
        control_layout.addWidget(self.decrypted_only_cb)
        
        control_layout.addSpacing(20)
        
        self.autoscroll_cb = QCheckBox("Auto-scroll")
        self.autoscroll_cb.setChecked(False)
        control_layout.addWidget(self.autoscroll_cb)
        
        clear_btn = QPushButton("Clear")
        clear_btn.clicked.connect(lambda: self.frames_table.setRowCount(0))
        control_layout.addWidget(clear_btn)
        
        control_layout.addStretch()
        layout.addLayout(control_layout)
        
        # Table (no scroll area wrapper needed for QTableWidget)
        self.frames_table = QTableWidget()
        self.frames_table.setColumnCount(9)  # Added Country column
        self.frames_table.setHorizontalHeaderLabels([
            "⏱ Time", "# Frame", "📋 Type", "📝 Description", "💬 Message", "🔐 Encrypted", "✅ Status", "📊 Data", "🌍 Country"
        ])
        # Column widths with stretch factors
        self.frames_table.setColumnWidth(0, 80)
        self.frames_table.setColumnWidth(1, 70)
        self.frames_table.setColumnWidth(2, 100)
        self.frames_table.setColumnWidth(3, 300)
        self.frames_table.setColumnWidth(4, 240)  # Message column width
        self.frames_table.setColumnWidth(5, 80)
        self.frames_table.setColumnWidth(6, 180)
        self.frames_table.setColumnWidth(7, 250)  # Data column width
        self.frames_table.setColumnWidth(8, 150)  # Country column width
        
        # Set column stretch modes for better scaling
        header = self.frames_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)  # Description stretches
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)  # Message stretches
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.Stretch)  # Status stretches
        header.setSectionResizeMode(7, QHeaderView.ResizeMode.Stretch)  # Data stretches
        
        # Set table properties
        self.frames_table.setAlternatingRowColors(True)
        self.frames_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.frames_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.frames_table.setShowGrid(False)
        self.frames_table.verticalHeader().setVisible(False)
        self.frames_table.setHorizontalScrollMode(QTableWidget.ScrollMode.ScrollPerPixel)
        self.frames_table.setVerticalScrollMode(QTableWidget.ScrollMode.ScrollPerPixel)
        self.frames_table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        
        # Add tooltips to headers
        headers = ["Time", "Frame #", "Type", "Description", "Message", "Encrypted", "Status", "Data"]
        tooltips = [
            "Timestamp when frame was decoded",
            "TETRA frame number (0-255)",
            "Frame type (MAC-RESOURCE, MAC-BROADCAST, etc.)",
            "Frame description with metadata (TG, SSI, etc.)",
            "Decoded SDS/text snippet (if available)",
            "Whether frame is encrypted",
            "Decryption status and key information",
            "Frame payload data (hex or text)"
        ]
        for i, (header, tooltip) in enumerate(zip(headers, tooltips)):
            item = self.frames_table.horizontalHeaderItem(i)
            if item:
                item.setToolTip(tooltip)
        
        layout.addWidget(self.frames_table)
        
        widget.setLayout(layout)
        return widget
    
    def create_calls_tab(self):
        """Create calls tab."""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Filter controls
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("Filter Group:"))
        self.calls_group_filter = QComboBox()
        self.calls_group_filter.setEditable(True)
        self.calls_group_filter.addItem("All")
        self.calls_group_filter.currentTextChanged.connect(self.apply_calls_filter)
        filter_layout.addWidget(self.calls_group_filter)
        
        filter_layout.addWidget(QLabel("Filter Client:"))
        self.calls_client_filter = QComboBox()
        self.calls_client_filter.setEditable(True)
        self.calls_client_filter.addItem("All")
        self.calls_client_filter.currentTextChanged.connect(self.apply_calls_filter)
        filter_layout.addWidget(self.calls_client_filter)
        
        filter_layout.addStretch()
        layout.addLayout(filter_layout)
        
        # Table
        self.calls_table = QTableWidget()
        self.calls_table.setColumnCount(10)
        self.calls_table.setHorizontalHeaderLabels([
            "⏱ Time", "📡 MCarrier", "📻 Carrier", "🎰 Slot", "🆔 CallID", "⭐ Pri", "📋 Type", "👤 From", "👥 To", "🔒 Mode"
        ])
        self.calls_table.setAlternatingRowColors(True)
        self.calls_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.calls_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.calls_table.verticalHeader().setVisible(False)
        
        layout.addWidget(self.calls_table)
        widget.setLayout(layout)
        return widget

    def create_groups_tab(self):
        """Create groups tab."""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Table
        self.groups_table = QTableWidget()
        self.groups_table.setColumnCount(7)  # Back to 7 columns
        self.groups_table.setHorizontalHeaderLabels([
            "🆔 GSSI", "⏱ Last Seen", "🔴 REC", "🌍 MCC", "📍 MNC", "⭐ Priority", "📛 Name/Country"
        ])
        self.groups_table.setAlternatingRowColors(True)
        self.groups_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.groups_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.groups_table.verticalHeader().setVisible(False)
        
        layout.addWidget(self.groups_table)
        widget.setLayout(layout)
        return widget

    def create_users_tab(self):
        """Create users tab."""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Filter controls
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("Filter Group:"))
        self.users_group_filter = QComboBox()
        self.users_group_filter.setEditable(True)
        self.users_group_filter.addItem("All")
        self.users_group_filter.currentTextChanged.connect(self.apply_users_filter)
        filter_layout.addWidget(self.users_group_filter)
        
        filter_layout.addStretch()
        layout.addLayout(filter_layout)
        
        # Table
        self.users_table = QTableWidget()
        self.users_table.setColumnCount(7)  # Back to 7 columns
        self.users_table.setHorizontalHeaderLabels([
            "🆔 ISSI", "⏱ Last Seen", "👥 GSSI", "🌍 MCC", "📍 MNC", "📛 Name", "📌 Location/Country"
        ])
        self.users_table.setAlternatingRowColors(True)
        self.users_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.users_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.users_table.verticalHeader().setVisible(False)
        
        layout.addWidget(self.users_table)
        widget.setLayout(layout)
        return widget
    
    def create_stats_tab(self):
        """Create statistics tab."""
        widget = QWidget()
        layout = QVBoxLayout()
        
        self.stats_text = QTextEdit()
        self.stats_text.setReadOnly(True)
        self.stats_text.setFont(QFont("Consolas", 10))
        layout.addWidget(self.stats_text)
        
        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.clicked.connect(self.update_stats)
        layout.addWidget(refresh_btn)

        # Auto-refresh timer
        self.stats_timer = QTimer()
        self.stats_timer.timeout.connect(self.update_stats)
        self.stats_timer.start(1000)  # 1 second

        widget.setLayout(layout)
        return widget
    
    def apply_modern_style(self):
        """Apply shadcn/ui dark theme."""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #0a0a0f; /* shadcn dark background */
            }
            QWidget {
                background-color: #0a0a0f;
                color: #fafafa; /* shadcn light text */
                font-family: 'Segoe UI', 'Inter', sans-serif;
                font-size: 13px;
            }
            
            /* Panels / Cards */
            QGroupBox {
                border: 1px solid #2a2a3a; /* shadcn border */
                border-radius: 8px;
                margin-top: 8px;
                padding: 12px;
                background-color: #1a1a24; /* shadcn card */
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 6px;
                color: #a1a1aa; /* shadcn muted text */
                font-weight: 600;
                font-size: 11px;
            }
            
            /* Buttons */
            QPushButton {
                background-color: #1a1a24; /* shadcn card */
                color: #fafafa;
                border: 1px solid #2a2a3a;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #2a2a3a;
                border-color: #3a3a4a;
            }
            QPushButton:pressed {
                background-color: #3a3a4a;
            }
            QPushButton:disabled {
                background-color: #0a0a0f;
                color: #52525b;
                border-color: #1a1a24;
            }
            
            /* Primary Action Button (Start) */
            QPushButton#start_btn {
                background-color: #22c55e; /* green-500 */
                border-color: #16a34a;
                color: white;
            }
            QPushButton#start_btn:hover {
                background-color: #16a34a; /* green-600 */
            }
            
            /* Destructive Action Button (Stop) */
            QPushButton#stop_btn {
                background-color: #ef4444; /* red-500 */
                border-color: #dc2626;
                color: white;
            }
            QPushButton#stop_btn:hover {
                background-color: #dc2626; /* red-600 */
            }
            
            /* Inputs */
            QLineEdit, QComboBox {
                background-color: #1a1a24;
                color: #fafafa;
                border: 1px solid #2a2a3a;
                border-radius: 6px;
                padding: 6px 10px;
                selection-background-color: #3b82f6;
                selection-color: white;
            }
            QLineEdit:focus, QComboBox:focus {
                border: 1px solid #3b82f6; /* shadcn accent */
            }
            
            /* Table */
            QTableWidget {
                background-color: #1a1a24;
                border: 1px solid #2a2a3a;
                border-radius: 6px;
                gridline-color: #2a2a3a;
                alternate-background-color: #0f0f1a;
            }
            QTableWidget::item {
                padding: 6px 8px;
                border: none;
            }
            QTableWidget::item:selected {
                background-color: #2a2a3a;
                color: #fafafa;
            }
            QTableWidget::item:hover {
                background-color: #2a2a3a;
            }
            QHeaderView::section {
                background-color: #0f0f1a;
                color: #a1a1aa;
                padding: 8px 6px;
                border: none;
                border-bottom: 1px solid #2a2a3a;
                border-right: 1px solid #2a2a3a;
                font-weight: 600;
                font-size: 11px;
            }
            QHeaderView::section:hover {
                background-color: #1a1a24;
            }
            
            /* Tabs */
            QTabWidget::pane {
                border: 1px solid #2a2a3a;
                border-radius: 6px;
                top: -1px;
                background-color: #1a1a24;
            }
            QTabBar::tab {
                background-color: #0a0a0f;
                color: #71717a;
                padding: 8px 16px;
                border: 1px solid transparent;
                border-bottom: 2px solid transparent;
                margin-right: 2px;
            }
            QTabBar::tab:selected {
                color: #fafafa;
                background-color: #1a1a24;
                border-bottom: 2px solid #3b82f6;
            }
            QTabBar::tab:hover {
                color: #e4e4e7;
            }
            
            /* Scrollbars */
            QScrollBar:vertical {
                border: none;
                background: #0a0a0f;
                width: 12px;
                margin: 0;
            }
            QScrollBar::handle:vertical {
                background: #2a2a3a;
                min-height: 20px;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical:hover {
                background: #3a3a4a;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
            QScrollBar:horizontal {
                border: none;
                background: #0a0a0f;
                height: 12px;
                margin: 0;
            }
            QScrollBar::handle:horizontal {
                background: #2a2a3a;
                min-width: 20px;
                border-radius: 6px;
            }
            QScrollBar::handle:horizontal:hover {
                background: #3a3a4a;
            }
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
                width: 0px;
            }
            
            /* Status Bar */
            QStatusBar {
                background-color: #1a1a24;
                color: #a1a1aa;
                border-top: 1px solid #2a2a3a;
            }
            
            /* Sliders */
            QSlider::groove:horizontal {
                border: none;
                height: 6px;
                background: #2a2a3a;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background: #fafafa;
                border: 2px solid #3b82f6;
                width: 18px;
                height: 18px;
                margin: -6px 0;
                border-radius: 9px;
            }
            QSlider::handle:horizontal:hover {
                background: #e4e4e7;
                border: 2px solid #2563eb;
            }
            QSlider::handle:horizontal:pressed {
                background: #a1a1aa;
            }
            QSlider::sub-page:horizontal {
                background: #3b82f6; /* shadcn accent */
                border-radius: 3px;
            }
            QSlider::add-page:horizontal {
                background: #2a2a3a;
                border-radius: 3px;
            }
            
            /* Checkbox */
            QCheckBox {
                color: #fafafa;
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border: 2px solid #2a2a3a;
                border-radius: 4px;
                background: #1a1a24;
            }
            QCheckBox::indicator:hover {
                border-color: #3a3a4a;
            }
            QCheckBox::indicator:checked {
                background: #3b82f6;
                border-color: #3b82f6;
            }
            QCheckBox::indicator:checked:hover {
                background: #2563eb;
                border-color: #2563eb;
            }
            
            /* Labels */
            QLabel {
                color: #fafafa;
            }
            
            /* Text Edit */
            QTextEdit {
                background-color: #1a1a24;
                color: #fafafa;
                border: 1px solid #2a2a3a;
                border-radius: 6px;
                padding: 8px;
            }
        """)
        
        self.start_btn.setObjectName("start_btn")
        self.stop_btn.setObjectName("stop_btn")
    
    def on_monitor_raw_toggled(self, checked):
        """Handle raw monitor toggle."""
        if self.capture_thread:
            self.capture_thread.set_monitor_raw(checked)

    def on_auto_decrypt_toggled(self, checked):
        """Handle auto-decrypt toggle."""
        try:
            self.settings_manager.set("auto_decrypt", bool(checked))
            self.settings_manager.save()
        except Exception as exc:
            logger.debug("Failed to persist auto-decrypt setting: %s", exc)
        if self.capture_thread:
            self.capture_thread.auto_decrypt = bool(checked)
            if getattr(self.capture_thread, "decoder", None):
                self.capture_thread.decoder.auto_decrypt = bool(checked)

    def on_preset_changed(self, text):
        """Handle frequency preset."""
        # Extract frequency from text "390.000 MHz - Label"
        try:
            if "MHz" in text:
                freq_str = text.split("MHz")[0].strip()
                self.freq_input.setText(freq_str)
        except:
            pass
    
    def on_bandwidth_changed(self, text):
        """Handle bandwidth change."""
        try:
            bw = float(text)
            if hasattr(self, 'waterfall'):
                self.waterfall.set_bandwidth(bw)
        except ValueError:
            pass

    def toggle_recording(self):
        """Toggle recording state."""
        self.recording_enabled = self.record_btn.isChecked()
        if not self.recording_enabled and self.recording_active:
            self.save_recording()
            
    def reset_stats(self):
        """Reset all statistics and tables."""
        self.frame_count = 0
        self.decrypted_count = 0
        self.tetra_sync_count = 0
        self.tetra_frame_count = 0
        self.tetra_valid_frames = 0
        self.signal_present = False
        self.first_frame_time = None
        self.frames_table.setRowCount(0)
        self.calls_table.setRowCount(0)
        self.groups_table.setRowCount(0)
        self.users_table.setRowCount(0)
        self.update_displays()

    def on_tune(self):
        """Tune to frequency."""
        try:
            freq_mhz = float(self.freq_input.text())
            freq_hz = freq_mhz * 1e6
            
            # Reset stats and tables on retune
            self.reset_stats()
            
            # Update tuned frequency display
            if hasattr(self, 'waterfall'):
                self.waterfall.set_tuned_frequency(freq_mhz)
                self.waterfall.update()
            
            if self.capture_thread and self.capture_thread.isRunning():
                self.capture_thread.set_frequency(freq_hz)
            else:
                self.log(f"Frequency set to {freq_mhz} MHz")
        except ValueError:
            QMessageBox.warning(self, "Error", "Invalid frequency")
    
    def on_gain_slider_changed(self, value):
        """Handle gain slider change."""
        gain_value = value / 2.0  # Convert 0-100 to 0-50 with 0.5 steps
        self.gain_label.setText(f"{gain_value:.1f} dB")
        
        if self.capture_thread and self.capture_thread.isRunning():
            try:
                self.capture_thread.set_gain(gain_value)
            except:
                pass
    
    def on_gain_changed(self, gain_text):
        """Change gain (legacy method for compatibility)."""
        if self.capture_thread and self.capture_thread.isRunning():
            try:
                gain = gain_text if gain_text == 'auto' else float(gain_text)
                self.capture_thread.set_gain(gain)
                # Update slider if it exists
                if hasattr(self, 'gain_slider'):
                    self.gain_slider.setValue(int(gain * 2))
            except:
                pass
    
    def on_noise_floor_changed(self, value):
        """Handle noise floor (bottom dB) slider change."""
        self.noise_floor_label.setText(f"{value} dB")
        # Update spectrum widget power min
        if hasattr(self, 'waterfall'):
            self.waterfall.power_min = value
            # Invalidate grid cache
            self.waterfall.grid_cache = None
            self.waterfall.grid_cache_params = None
            self.waterfall.update()
            
    def on_threshold_changed(self, value):
        """Handle threshold slider change."""
        self.threshold_label.setText(f"{value} dB")
        if hasattr(self, 'waterfall'):
            self.waterfall.set_noise_floor(value)
    
    def on_sample_rate_slider_changed(self, value):
        """Handle sample rate slider change."""
        # Get valid rate from slider index
        if hasattr(self, 'valid_sample_rates') and value < len(self.valid_sample_rates):
            sample_rate_mhz = self.valid_sample_rates[value]
        else:
            # Fallback to old calculation if valid_rates not set
            sample_rate_mhz = 1.8 + (value * 0.1)
        
        self.sample_rate_label.setText(f"{sample_rate_mhz:.3f} MHz")
        self.sample_rate = sample_rate_mhz * 1e6
        
        # Update capture thread if running
        if hasattr(self, 'capture_thread') and self.capture_thread and self.capture_thread.isRunning():
            self.capture_thread.set_sample_rate(self.sample_rate)
    
    def on_zoom_changed(self, value):
        """Handle zoom slider change."""
        zoom_level = value / 10.0
        if hasattr(self, 'waterfall'):
            self.waterfall.set_zoom(zoom_level)
            
    def on_range_changed(self, value):
        """Handle range (top dB) slider change."""
        self.range_label.setText(f"{value} dB")
        # Adjust top dB level
        if hasattr(self, 'waterfall'):
            self.waterfall.power_max = value
            self.waterfall.grid_cache = None
            self.waterfall.update()
            
    def on_denoiser_toggled(self, checked):
        """Handle denoiser toggle."""
        if hasattr(self, 'waterfall'):
            self.waterfall.set_denoiser(checked)
    
    def on_auto_spectrum_toggled(self, checked):
        """Handle auto spectrum slider toggle."""
        self.auto_spectrum_enabled = checked
        if checked and hasattr(self, 'waterfall') and self.waterfall.current_fft is not None:
            self._apply_auto_spectrum(self.waterfall.current_freqs, self.waterfall.current_fft)
    
    def _apply_auto_spectrum(self, freqs, powers):
        """Automatically adjust spectrum sliders and zoom."""
        if (not self.auto_spectrum_enabled) or powers is None:
            return
        
        import time
        now = time.time()
        if now - getattr(self, '_last_auto_spectrum_time', 0) < 0.3:
            return
        self._last_auto_spectrum_time = now
        
        power_array = np.asarray(powers, dtype=float)
        if power_array.size < 32:
            return
        
        finite_mask = np.isfinite(power_array)
        if not np.any(finite_mask):
            return
        
        usable = power_array[finite_mask]
        noise_floor = float(np.percentile(usable, 20))
        peak_power = float(np.percentile(usable, 99))
        
        if not np.isfinite(noise_floor) or not np.isfinite(peak_power):
            return
        
        dynamic_range = peak_power - noise_floor
        if dynamic_range < 5:
            return
        
        top_target = peak_power + 5.0
        bottom_target = noise_floor - 10.0
        if bottom_target > top_target - 10.0:
            bottom_target = top_target - 10.0
        threshold_target = noise_floor + dynamic_range * 0.6
        
        if hasattr(self, 'range_slider'):
            top_target = int(round(np.clip(top_target, self.range_slider.minimum(), self.range_slider.maximum())))
        else:
            top_target = int(round(top_target))
        
        if hasattr(self, 'noise_floor_slider'):
            bottom_target = int(round(np.clip(bottom_target, self.noise_floor_slider.minimum(), self.noise_floor_slider.maximum())))
        else:
            bottom_target = int(round(bottom_target))
        
        bottom_target = min(bottom_target, top_target - 5)
        
        if hasattr(self, 'threshold_slider'):
            threshold_target = int(round(np.clip(threshold_target, self.threshold_slider.minimum(), self.threshold_slider.maximum())))
        else:
            threshold_target = int(round(threshold_target))
        
        threshold_target = max(min(threshold_target, top_target - 2), bottom_target + 2)
        
        if hasattr(self, 'range_slider') and abs(self.range_slider.value() - top_target) >= 1:
            self.range_slider.setValue(top_target)
        if hasattr(self, 'noise_floor_slider') and abs(self.noise_floor_slider.value() - bottom_target) >= 1:
            self.noise_floor_slider.setValue(bottom_target)
        if hasattr(self, 'threshold_slider') and abs(self.threshold_slider.value() - threshold_target) >= 1:
            self.threshold_slider.setValue(threshold_target)
        
        if freqs is None or not hasattr(self, 'zoom_slider'):
            return
        
        freq_array = np.asarray(freqs, dtype=float)
        if freq_array.size != power_array.size or freq_array.size == 0:
            return
        
        # Convert to MHz if values look like Hz
        if np.max(np.abs(freq_array)) > 1e3:
            freq_mhz = freq_array / 1e6
        else:
            freq_mhz = freq_array
        
        full_span = float(np.max(freq_mhz) - np.min(freq_mhz))
        if full_span <= 0:
            return
        
        signal_mask = finite_mask & (power_array > noise_floor + 6)
        if np.any(signal_mask):
            active_freqs = freq_mhz[signal_mask]
            active_span = float(np.max(active_freqs) - np.min(active_freqs))
        else:
            active_span = full_span
        
        if active_span <= 0:
            active_span = full_span
        
        desired_span = min(full_span, max(active_span * 3, full_span / 10.0))
        desired_zoom = max(1.0, min(10.0, full_span / max(desired_span, 1e-9)))
        zoom_target = int(round(desired_zoom * 10))
        zoom_target = max(self.zoom_slider.minimum(), min(self.zoom_slider.maximum(), zoom_target))
        
        if abs(self.zoom_slider.value() - zoom_target) >= 1:
            self.zoom_slider.setValue(zoom_target)

    def on_tune_from_spectrum(self, freq_mhz):
        """Handle tuning from spectrum click."""
        modifiers = QApplication.keyboardModifiers()
        if modifiers & Qt.KeyboardModifier.ControlModifier:
            # Higher precision to keep the clicked spike centered.
            self.freq_input.setText(f"{freq_mhz:.6f}")
            if hasattr(self, "waterfall") and self.waterfall is not None:
                self.waterfall.center_view_on(freq_mhz)
        else:
            self.freq_input.setText(f"{freq_mhz:.3f}")
        self.on_tune()

    def on_start(self):
        """Start capture."""
        try:
            freq_mhz = float(self.freq_input.text())
            freq_hz = freq_mhz * 1e6
            
            # Get gain from slider
            if hasattr(self, 'gain_slider'):
                gain = self.gain_slider.value() / 2.0
            else:
                gain = 50.0  # Default per user specification
            
            # Get sample rate from slider
            if hasattr(self, 'sample_rate_slider'):
                # Value 0 = 1.8 MHz, value 82 = 10.0 MHz
                slider_value = self.sample_rate_slider.value()
                sample_rate = (1.8 + slider_value * 0.1) * 1e6
            else:
                sample_rate = 2.4e6  # Default per TETRA spec
            
            self.capture_thread = CaptureThread()
            self.capture_thread.frequency = freq_hz
            self.capture_thread.gain = gain
            self.capture_thread.sample_rate = sample_rate
            self.capture_thread.auto_decrypt = self.auto_decrypt_cb.isChecked()
            self.capture_thread.set_monitor_raw(self.monitor_raw_cb.isChecked())
            if self.encryption_keys:
                self.capture_thread.set_keys(self.encryption_keys)
            
            self.capture_thread.signal_detected.connect(self.on_signal)
            self.capture_thread.signal_lost.connect(self.on_signal_lost)
            self.capture_thread.frame_decoded.connect(self.on_frame)
            self.capture_thread.error_occurred.connect(self.on_error)
            self.capture_thread.status_update.connect(self.on_status)
            self.capture_thread.spectrum_update.connect(self.on_spectrum)
            self.capture_thread.raw_audio_data.connect(self.on_raw_audio)
            self.capture_thread.voice_audio_data.connect(self.on_voice_audio)
            
            self.capture_thread.start()
            
            # Connect spectrum click signal
            self.waterfall.frequency_clicked.connect(self.on_tune_from_spectrum)
            
            self.start_btn.setEnabled(False)
            self.stop_btn.setEnabled(True)
            self.log("Capture started")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
    
    def on_stop(self):
        """Stop capture."""
        # Save any active recording
        if self.recording_active:
            self.save_recording()
        
        if self.capture_thread:
            self.capture_thread.stop()
            self.capture_thread.wait()
            self.capture_thread = None
        
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.log("Capture stopped")
    
    def on_scan(self):
        """Open scanner."""
        if not self.scanner_dialog:
            self.scanner_dialog = ScannerDialog(self)
            self.scanner_dialog.scan_complete.connect(self.on_scan_complete)
        self.scanner_dialog.show()
    
    def on_scan_complete(self, results):
        """Handle scan results."""
        if results and len(results) > 0:
            # Sort by power
            results.sort(key=lambda x: x.get('power_db', -100), reverse=True)
            best = results[0]
            best_freq = best['frequency']
            best_power = best['power_db']
            
            self.freq_input.setText(f"{best_freq/1e6:.3f}")
            self.log(f"Scan complete: Best signal at {best_freq/1e6:.3f} MHz ({best_power:.1f} dB)")
        else:
            self.log("Scan complete: No signals found")
    
    def on_load_keys(self):
        """Load encryption keys."""
        file_path, _ = QFileDialog.getOpenFileName(self, "Load Keys", "", "Key Files (*.txt);;All Files (*.*)")
        if file_path:
            try:
                # Load keys from file
                keys_loaded = []
                with open(file_path, 'r') as f:
                    for line in f:
                        line = line.strip()
                        # Skip comments and empty lines
                        if not line or line.startswith('#') or line.startswith('//'):
                            continue
                        
                        # Remove any non-hex characters
                        key = ''.join(c for c in line if c in '0123456789abcdefABCDEF')
                        
                        # Validate key length (80 bits = 20 hex chars, but accept 16-32 chars)
                        if 16 <= len(key) <= 32:
                            keys_loaded.append(key.lower())
                
                if keys_loaded:
                    # Pass keys to capture thread if running
                    if self.capture_thread and self.capture_thread.isRunning():
                        self.capture_thread.set_keys(keys_loaded)
                    
                    # Store keys for future captures
                    self.encryption_keys = keys_loaded
                    
                    self.log(f"✅ Loaded {len(keys_loaded)} encryption keys from {file_path}")
                    self.log(f"🔑 Auto-decrypt will try these keys on encrypted frames")
                else:
                    self.log(f"⚠️ No valid keys found in {file_path}")
            except Exception as e:
                self.log(f"❌ Error loading keys: {e}")
                logger.error(f"Error loading keys: {e}")

    
    @pyqtSlot(float, float)
    def on_signal(self, freq, power):
        """Handle signal detection."""
        self.signal_present = True
        self.signal_label.setText(f"🟢 {power:.1f} dB")
        
        # If we detect a signal but haven't decoded TETRA frames yet, show status
        # Only show this if we actually have a signal (not noise)
        if self.tetra_frame_count == 0:
            self.tetra_status_label.setText("🟡 Signal Detected (Decoding...)")
            self.tetra_status_label.setStyleSheet(
                "font-weight: bold; padding: 5px; color: #ffaa00; background-color: #221100;"
            )

    def on_signal_lost(self):
        """Handle signal loss."""
        self.signal_present = False
        self.signal_label.setText("🔴 No Signal")
        # Clear TETRA status when signal is lost - they should be mutually exclusive
        self.tetra_status_label.setText("⚫ No TETRA Signal")
        self.tetra_status_label.setStyleSheet(
            "font-weight: bold; padding: 5px; color: #888888;"
        )
    
    def init_audio(self):
        """Initialize audio stream."""
        try:
            device = self.settings_manager.get("audio_device", None)
            self.audio_stream = sd.OutputStream(
                samplerate=8000,  # TETRA voice is usually 8kHz
                channels=1,
                dtype='float32',
                device=device
            )
            self.audio_stream.start()
        except Exception as e:
            self.log(f"Audio init error: {e}")

    @pyqtSlot(np.ndarray)
    def on_raw_audio(self, data):
        """Play raw audio data."""
        if hasattr(self, 'audio_stream') and self.audio_stream and self.monitor_raw_cb.isChecked():
            try:
                self.audio_stream.write(data.astype(np.float32))
            except Exception:
                pass

    @pyqtSlot(np.ndarray)
    def on_voice_audio(self, data):
        """Play decoded TETRA voice data live and record to continuous WAV."""
        import os
        from datetime import datetime
        import wave
        
        # Validate amplitude (must be > 0)
        if len(data) == 0:
            return
            
        max_amp = np.max(np.abs(data))
        if max_amp <= 0:
            return  # Skip silent/invalid frames
        
        # Continuous recording to single WAV file
        if len(data) > 0:
            try:
                # Convert float32 to int16
                audio_int16 = (data * 32767).astype(np.int16)
                
                # Start new recording if not active
                if self.recording_enabled and not self.recording_active:
                    records_dir = str(RECORDS_DIR)
                    os.makedirs(records_dir, exist_ok=True)
                    
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    freq_mhz = float(self.freq_input.text())
                    self.current_wav_file = os.path.join(records_dir, f"tetra_voice_{freq_mhz:.3f}MHz_{timestamp}.wav")
                    
                    # Open WAV file for writing
                    self.wav_file = wave.open(self.current_wav_file, 'wb')
                    self.wav_file.setnchannels(1)
                    self.wav_file.setsampwidth(2)
                    self.wav_file.setframerate(8000)
                    
                    self.recording_active = True
                    self.recording_start_time = datetime.now()
                    self.recording_has_audio = False
                    self.log(f"🎙️ Recording: {os.path.basename(self.current_wav_file)}")
                    audio_logger.info("Started voice recording: %s", self.current_wav_file)
                
                # Write to continuous WAV file
                if self.recording_active and hasattr(self, 'wav_file'):
                    self.wav_file.writeframes(audio_int16.tobytes())
                    self.recording_has_audio = True
                
            except Exception as e:
                audio_logger.debug("Failed to record voice: %s", e)
        
        # Play audio LIVE if monitoring enabled
        if self.hear_voice_cb.isChecked() and len(data) > 0:
            try:
                # Ensure audio stream exists and is started
                if not hasattr(self, 'audio_stream') or self.audio_stream is None:
                    self.init_audio()
                
                if hasattr(self, 'audio_stream') and self.audio_stream:
                    # Check if stream is active, restart if needed
                    if not self.audio_stream.active:
                        try:
                            self.audio_stream.stop()
                        except:
                            pass
                        self.audio_stream.start()
                    
                    # Write audio data - YOU WILL HEAR THIS LIVE!
                    # Normalize int16 to float32 range [-1.0, 1.0]
                    self.audio_stream.write(data.astype(np.float32) / 32768.0)
            except Exception as e:
                logger.debug(f"Audio playback error: {e}")
                # Try to reinitialize audio stream
                try:
                    if hasattr(self, 'audio_stream') and self.audio_stream:
                        try:
                            self.audio_stream.stop()
                        except:
                            pass
                    self.init_audio()
                    if hasattr(self, 'audio_stream') and self.audio_stream:
                        self.audio_stream.write(data.astype(np.float32) / 32768.0)
                except Exception as e2:
                    logger.debug(f"Audio reinit failed: {e2}")

    def save_recording(self):
        """Close current recording file."""
        if self.recording_active and hasattr(self, 'wav_file'):
            try:
                self.wav_file.close()
                duration = (datetime.now() - self.recording_start_time).total_seconds()
                
                # Check if we should keep the file
                save_silence = self.settings_manager.get("save_silence", False)
                if not save_silence and not self.recording_has_audio:
                    # Delete silent file
                    try:
                        os.remove(self.current_wav_file)
                        self.log(f"Deleted silent recording: {os.path.basename(self.current_wav_file)}")
                        audio_logger.info("Deleted silent voice recording: %s", self.current_wav_file)
                    except Exception as e:
                        audio_logger.debug("Failed to delete silent file: %s", e)
                else:
                    self.log(f"Saved voice recording: {os.path.basename(self.current_wav_file)} ({duration:.1f}s)")
                    audio_logger.info("Saved voice recording: %s (%.1fs)", self.current_wav_file, duration)

                    # Optional MP3 export for easier sharing (requires ffmpeg).
                    if self.settings_manager.get("export_mp3", False):
                        try:
                            from tetraear.audio.export import wav_to_mp3

                            mp3_path = wav_to_mp3(self.current_wav_file)
                            self.log(f"Exported MP3: {os.path.basename(str(mp3_path))}")
                            audio_logger.info("Exported MP3: %s", mp3_path)
                        except FileNotFoundError:
                            self.log("MP3 export skipped (ffmpeg not found)")
                            audio_logger.info("MP3 export skipped (ffmpeg not found)")
                        except Exception as e:
                            self.log(f"MP3 export failed: {e}")
                            audio_logger.debug("MP3 export failed: %s", e)
                
                self.recording_active = False
            except Exception as e:
                audio_logger.debug("Failed to close recording: %s", e)
    
    def reassemble_sds_message(self, frame):
        """Reassemble SDS fragments into complete message or parse existing."""
        # First check if the frame already has an SDS message parsed by the decoder
        if 'sds_message' in frame and frame['sds_message']:
            # Already parsed, just return it
            return frame['sds_message']
        
        if 'decoded_text' in frame and frame['decoded_text']:
            # Already has decoded text
            return frame['decoded_text']

        # Don't attempt to parse SDS from encrypted frames unless they were decrypted.
        if frame.get("encrypted") and not frame.get("decrypted"):
            return None

        # Only attempt single-frame SDS parsing on SDS-candidate PDUs.
        mac_pdu = frame.get("mac_pdu") if isinstance(frame.get("mac_pdu"), dict) else {}
        pdu_type = str(mac_pdu.get("type", "")).upper()
        type_name = str(frame.get("type_name", "")).upper()
        is_sds_pdu = pdu_type in ("MAC_DATA", "MAC_SUPPL") or ("MAC-DATA" in type_name) or ("MAC-SUPPL" in type_name) or ("MAC-END" in type_name) or ("MAC-END/RES" in type_name)
        
        # Multi-frame SDS reassembly logic
        # Check if this is a fragmented SDS message
        addr_src = frame.get('address_source', None)
        addr_dst = frame.get('address_destination', None)
        frag_id = frame.get('fragment_id', None)
        is_last = frame.get('is_last_fragment', False)
        
        # If we have fragment info, handle reassembly
        if addr_src and frag_id is not None:
            key = f"{addr_src}_{addr_dst}_{frag_id}"
            
            if not hasattr(self, 'sds_fragments'):
                self.sds_fragments = {}
            
            # Add fragment to buffer
            if key not in self.sds_fragments:
                self.sds_fragments[key] = []
            
            self.sds_fragments[key].append(frame)
            
            # If this is the last fragment, reassemble
            if is_last and len(self.sds_fragments[key]) > 1:
                fragments = sorted(self.sds_fragments[key], key=lambda f: f.get('fragment_index', 0))
                
                # Concatenate data from all fragments
                combined_data = b''
                for frag in fragments:
                    if 'decrypted_bytes' in frag:
                        try:
                            combined_data += bytes.fromhex(frag['decrypted_bytes'])
                        except:
                            pass
                    elif 'mac_pdu' in frag and 'data' in frag['mac_pdu']:
                        data = frag['mac_pdu']['data']
                        if isinstance(data, bytes):
                            combined_data += data
                        elif isinstance(data, str):
                            try:
                                combined_data += bytes.fromhex(data.replace(' ', ''))
                            except:
                                pass
                
                # Parse the complete message
                if combined_data:
                    from tetraear.core.protocol import TetraProtocolParser
                    parser = TetraProtocolParser()
                    sds_text = parser.parse_sds_data(combined_data)
                    
                    if sds_text:
                        # Mark all fragments as reassembled
                        for frag in fragments:
                            frag['is_reassembled'] = True
                            frag['sds_message'] = f"🧩 {sds_text}"
                        
                        # Clean up
                        del self.sds_fragments[key]
                        return f"🧩 {sds_text}"
        
        # Try to parse single-frame SDS from decrypted bytes or MAC data
        if not is_sds_pdu:
            return None

        data = None
        if 'decrypted_bytes' in frame:
            try:
                data = bytes.fromhex(frame['decrypted_bytes'])
            except:
                pass
        elif 'mac_pdu' in frame and 'data' in frame['mac_pdu']:
            data = frame['mac_pdu']['data']
            if isinstance(data, str):
                try:
                    data = bytes.fromhex(data.replace(' ', ''))
                except:
                    pass
        
        if not data or len(data) < 1:
            return None
        
        # Try to parse as SDS
        from tetraear.core.protocol import TetraProtocolParser
        parser = TetraProtocolParser()
        sds_text = parser.parse_sds_data(data)
        
        if sds_text:
            return sds_text
        
        # Try to decode as text if it looks printable - ONLY for non-encrypted frames
        # Check if frame is NOT encrypted
        is_encrypted = frame.get('encrypted', False)
        encryption_type = frame.get('encryption_type', 0)
        
        # Only try text decoding if frame is NOT encrypted OR was successfully decrypted
        if not is_encrypted or frame.get('decrypted'):
            try:
                printable_count = sum(1 for b in data if 32 <= b <= 126 or b in (10, 13, 9))
                # Increased threshold to 0.85 and require minimum length to avoid garbage
                if len(data) >= 5 and (printable_count / len(data)) >= 0.85:
                    text = data.decode('latin-1', errors='replace')
                    text = ''.join(c if (32 <= ord(c) <= 126 or c in '\n\r\t') else '' for c in text)
                    text = text.strip()
                    # More strict: require letters and minimum length
                    if len(text) >= 3 and any(c.isalpha() for c in text):
                        return f"[TXT] {text}"
            except:
                pass
        
        return None

    def apply_filter(self, text):
        """Apply type filter to existing rows."""
        filter_type = text.lower()
        decrypted_only = self.decrypted_only_cb.isChecked()
        
        for row in range(self.frames_table.rowCount()):
            type_item = self.frames_table.item(row, 2)
            if not type_item:
                continue
            
            type_text = type_item.text().lower()
            visible = True
            
            # Check decrypted/text only filter
            if decrypted_only:
                status_item = self.frames_table.item(row, 6)
                data_item = self.frames_table.item(row, 7)
                message_item = self.frames_table.item(row, 4)
                desc_item = self.frames_table.item(row, 3)
                encrypted_item = self.frames_table.item(row, 5)  # Encrypted column
                
                # STRICT filter: Only show frames that are:
                # 1. Explicitly marked as "No" in Encrypted column (clear frames)
                # 2. Successfully decrypted (status contains "✅" or "Decrypted")
                # 3. Have readable text content (not "[BIN-ENC]" or binary)
                
                is_clear_frame = encrypted_item and encrypted_item.text().strip().lower() in ["no", "clear"]
                is_successfully_decrypted = status_item and ("✅" in status_item.text() or "decrypted" in status_item.text().lower()) and "encrypted" not in status_item.text().lower()
                
                # Check if data contains readable text (not binary/encrypted markers)
                has_readable_text = False
                text_candidates = []
                if message_item and message_item.text().strip():
                    text_candidates.append(message_item.text())
                if data_item and data_item.text().strip():
                    text_candidates.append(data_item.text())
                for candidate in text_candidates:
                    if "[BIN-ENC]" in candidate or "SDS (Binary/Encrypted)" in candidate:
                        continue
                    if any(marker in candidate for marker in ["[TXT]", "[SDS-1]", "[SDS-GSM]", "[GSM7]", "📝", "💬", "🧩"]):
                        clean_text = candidate
                        for marker in ["[TXT]", "[SDS-1]", "[SDS-GSM]", "[GSM7]", "📝", "💬", "🧩", "\""]:
                            clean_text = clean_text.replace(marker, "")
                        clean_text = clean_text.strip()
                        if len(clean_text) >= 3 and any(c.isalpha() for c in clean_text):
                            hex_chars = sum(1 for c in clean_text if c in "0123456789abcdefABCDEF ")
                            if hex_chars / len(clean_text) < 0.8:
                                has_readable_text = True
                                break
                
                # STRICT: Only show if clear OR successfully decrypted OR has readable text
                visible = is_clear_frame or is_successfully_decrypted or has_readable_text
                
                # Extra validation: if showing encrypted frame, must have been decrypted
                if visible and encrypted_item and "yes" in encrypted_item.text().lower():
                    # Encrypted frame - only show if successfully decrypted
                    visible = is_successfully_decrypted or has_readable_text
            
            if visible:
                if "traffic" in filter_type and "traffic" not in type_text:
                    visible = False
                elif "control" in filter_type and "control" not in type_text:
                    visible = False
                elif "broadcast" in filter_type and "broadcast" not in type_text:
                    visible = False
                elif "mac" in filter_type and "mac" not in type_text and "traffic" not in type_text and "control" not in type_text and "broadcast" not in type_text:
                    visible = False
                elif "sds" in filter_type:
                    has_sds = "sds" in type_text or "data" in type_text or "suppl" in type_text or "sns" in type_text
                    # Also check description for "SDS" or "Text"
                    desc_item = self.frames_table.item(row, 3)
                    if desc_item and ("sds" in desc_item.text().lower() or "text" in desc_item.text().lower()):
                        has_sds = True
                    message_item = self.frames_table.item(row, 4)
                    if message_item and ("sds" in message_item.text().lower() or "text" in message_item.text().lower() or "[bin" in message_item.text().lower()):
                        has_sds = True
                        
                    if not has_sds:
                        visible = False
                elif "audio" in filter_type:
                    # Check for voice/audio
                    data_item = self.frames_table.item(row, 7)
                    if data_item and "voice" in data_item.text().lower():
                        visible = True
                    else:
                        visible = False
                
            self.frames_table.setRowHidden(row, not visible)

    def apply_calls_filter(self):
        """Apply filters to calls table."""
        group_filter = self.calls_group_filter.currentText().lower()
        if group_filter == "all": group_filter = ""
        
        client_filter = self.calls_client_filter.currentText().lower()
        if client_filter == "all": client_filter = ""
        
        for row in range(self.calls_table.rowCount()):
            visible = True
            
            # Check Group (To column often contains TG)
            if group_filter:
                to_item = self.calls_table.item(row, 8)
                if not to_item or group_filter not in to_item.text().lower():
                    visible = False
            
            # Check Client (From or To)
            if visible and client_filter:
                from_item = self.calls_table.item(row, 7)
                to_item = self.calls_table.item(row, 8)
                
                from_match = from_item and client_filter in from_item.text().lower()
                to_match = to_item and client_filter in to_item.text().lower()
                
                if not (from_match or to_match):
                    visible = False
            
            self.calls_table.setRowHidden(row, not visible)

    def apply_users_filter(self):
        """Apply filters to users table."""
        group_filter = self.users_group_filter.currentText().lower()
        if group_filter == "all": group_filter = ""
        
        for row in range(self.users_table.rowCount()):
            visible = True
            
            if group_filter:
                gssi_item = self.users_table.item(row, 2)
                if not gssi_item or group_filter not in gssi_item.text().lower():
                    visible = False
            
            self.users_table.setRowHidden(row, not visible)

    def update_filter_dropdowns(self, new_call_group=None, new_call_client=None, new_user_group=None):
        """Update filter dropdowns with new values."""
        if new_call_group and new_call_group not in self.known_call_groups:
            self.known_call_groups.add(new_call_group)
            self.calls_group_filter.addItem(new_call_group)
            
        if new_call_client and new_call_client not in self.known_call_clients:
            self.known_call_clients.add(new_call_client)
            self.calls_client_filter.addItem(new_call_client)
            
        if new_user_group and new_user_group not in self.known_user_groups:
            self.known_user_groups.add(new_user_group)
            self.users_group_filter.addItem(new_user_group)

    def update_tables(self, frame):
        """Update Calls, Groups, and Users tables."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        # Extract metadata
        meta = frame.get('call_metadata', {})
        if not meta and 'additional_info' in frame:
            # Map additional_info to meta structure
            info = frame['additional_info']
            if 'talkgroup' in info: meta['talkgroup_id'] = info['talkgroup']
            if 'source_ssi' in info: meta['source_ssi'] = info['source_ssi']
            if 'dest_ssi' in info: meta['dest_ssi'] = info['dest_ssi']
            if 'control' in info: meta['call_type'] = info['control']
            if 'mcc' in info: meta['mcc'] = info['mcc']
            if 'mnc' in info: meta['mnc'] = info['mnc']
        
        # Helper to format None as empty string
        def fmt(val):
            return str(val) if val is not None else ""

        # Update Calls Table
        # Columns: Time, MCarrier, Carrier, Slot, CallID, Pri, Type, From, To, Mode
        if meta.get('call_type') or meta.get('source_ssi') or meta.get('dest_ssi') or meta.get('talkgroup_id'):
            row = self.calls_table.rowCount()
            self.calls_table.insertRow(row)
            self.calls_table.setItem(row, 0, QTableWidgetItem(timestamp))
            
            # MCarrier (Main Carrier) - Use tuned frequency if not specified
            mcarrier = fmt(frame.get('frequency'))
            if not mcarrier and hasattr(self, 'freq_input'):
                mcarrier = self.freq_input.text()
            self.calls_table.setItem(row, 1, QTableWidgetItem(mcarrier)) # MCarrier
            
            self.calls_table.setItem(row, 2, QTableWidgetItem(fmt(meta.get('channel')))) # Carrier
            self.calls_table.setItem(row, 3, QTableWidgetItem(fmt(frame.get('timeslot')))) # Slot
            self.calls_table.setItem(row, 4, QTableWidgetItem(fmt(meta.get('call_identifier')))) # CallID
            self.calls_table.setItem(row, 5, QTableWidgetItem(fmt(meta.get('priority')))) # Pri
            self.calls_table.setItem(row, 6, QTableWidgetItem(fmt(meta.get('call_type')))) # Type
            self.calls_table.setItem(row, 7, QTableWidgetItem(fmt(meta.get('source_ssi')))) # From
            
            # To field: Dest SSI or Talkgroup
            to_val = fmt(meta.get('dest_ssi'))
            if not to_val and meta.get('talkgroup_id'):
                to_val = f"TG:{meta['talkgroup_id']}"
            self.calls_table.setItem(row, 8, QTableWidgetItem(to_val)) # To
            
            mode = "Encrypted" if frame.get('encrypted') else "Clear"
            if frame.get('has_voice'): mode += " (Voice)"
            if frame.get('decrypted'): mode += " [DEC]"
            self.calls_table.setItem(row, 9, QTableWidgetItem(mode)) # Mode
            
            if self.autoscroll_cb.isChecked():
                self.calls_table.scrollToBottom()

        # Update Groups Table (if GSSI present)
        # Columns: GSSI, LO, REC, MCC, MNC, Priority, Name
        if meta.get('talkgroup_id'):
            gssi = str(meta['talkgroup_id'])
            # Check if already exists
            found = False
            for r in range(self.groups_table.rowCount()):
                item = self.groups_table.item(r, 0)
                if item and item.text() == gssi:
                    found = True
                    # Update Last Seen (LO)
                    self.groups_table.setItem(r, 1, QTableWidgetItem(timestamp))
                    # Update REC status
                    rec_status = "🔴" if self.recording_active else ""
                    self.groups_table.setItem(r, 2, QTableWidgetItem(rec_status))
                    
                    # Update other fields if they were empty
                    if not self.groups_table.item(r, 3).text():
                        self.groups_table.setItem(r, 3, QTableWidgetItem(fmt(meta.get('mcc'))))
                    if not self.groups_table.item(r, 4).text():
                        self.groups_table.setItem(r, 4, QTableWidgetItem(fmt(meta.get('mnc'))))
                    
                    # Update Name/Country column
                    mcc = meta.get('mcc')
                    mnc = meta.get('mnc')
                    if mcc:
                        country_str = get_location_info(str(mcc), str(mnc) if mnc else None)
                        name_str = f"👥 Group {gssi} ({country_str})"
                        self.groups_table.setItem(r, 6, QTableWidgetItem(name_str))
                    break
            
            if not found:
                row = self.groups_table.rowCount()
                self.groups_table.insertRow(row)
                self.groups_table.setItem(row, 0, QTableWidgetItem(gssi))
                self.groups_table.setItem(row, 1, QTableWidgetItem(timestamp)) # Last Seen
                
                rec_status = "🔴" if self.recording_active else ""
                self.groups_table.setItem(row, 2, QTableWidgetItem(rec_status)) # REC
                
                self.groups_table.setItem(row, 3, QTableWidgetItem(fmt(meta.get('mcc')))) # MCC
                self.groups_table.setItem(row, 4, QTableWidgetItem(fmt(meta.get('mnc')))) # MNC
                self.groups_table.setItem(row, 5, QTableWidgetItem(fmt(meta.get('priority')))) # Priority
                
                # Name/Country column (combined)
                mcc = meta.get('mcc')
                mnc = meta.get('mnc')
                if mcc:
                    country_str = get_location_info(str(mcc), str(mnc) if mnc else None)
                    name_str = f"👥 Group {gssi} ({country_str})"
                else:
                    name_str = f"👥 Group {gssi}"
                self.groups_table.setItem(row, 6, QTableWidgetItem(name_str)) # Name/Country

        # Update Users Table (if ISSI present)
        # Columns: ISSI, LO, GSSI, MCC, MNC, Name, Location
        if meta.get('source_ssi'):
            issi = str(meta['source_ssi'])
            # Check if already exists
            found = False
            for r in range(self.users_table.rowCount()):
                item = self.users_table.item(r, 0)
                if item and item.text() == issi:
                    found = True
                    # Update Last Seen
                    self.users_table.setItem(r, 1, QTableWidgetItem(timestamp))
                    # Update GSSI if present
                    if meta.get('talkgroup_id'):
                        self.users_table.setItem(r, 2, QTableWidgetItem(str(meta['talkgroup_id'])))
                    
                    # Update MCC/MNC if present
                    if meta.get('mcc'): self.users_table.setItem(r, 3, QTableWidgetItem(str(meta['mcc'])))
                    if meta.get('mnc'): self.users_table.setItem(r, 4, QTableWidgetItem(str(meta['mnc'])))
                    
                    # Update Location/Country column (combined)
                    loc_str = ""
                    
                    # Try to extract GPS coordinates
                    gps_data = LocationParser.extract_location_from_frame(frame)
                    if gps_data:
                        loc_str = f"📍 {gps_data['formatted']}"
                    else:
                        # No GPS, show country from MCC/MNC
                        mcc = meta.get('mcc')
                        mnc = meta.get('mnc')
                        if mcc:
                            loc_str = get_location_info(str(mcc), str(mnc) if mnc else None)
                    
                    if loc_str:
                        self.users_table.setItem(r, 6, QTableWidgetItem(loc_str))
                    break
            
            if not found:
                row = self.users_table.rowCount()
                self.users_table.insertRow(row)
                self.users_table.setItem(row, 0, QTableWidgetItem(issi))
                self.users_table.setItem(row, 1, QTableWidgetItem(timestamp)) # Last Seen
                self.users_table.setItem(row, 2, QTableWidgetItem(fmt(meta.get('talkgroup_id')))) # GSSI
                self.users_table.setItem(row, 3, QTableWidgetItem(fmt(meta.get('mcc')))) # MCC
                self.users_table.setItem(row, 4, QTableWidgetItem(fmt(meta.get('mnc')))) # MNC
                self.users_table.setItem(row, 5, QTableWidgetItem(f"👤 User {issi}")) # Name with icon
                
                # Location/Country column (combined)
                loc_str = ""
                
                # Try to extract GPS coordinates
                gps_data = LocationParser.extract_location_from_frame(frame)
                if gps_data:
                    loc_str = f"📍 {gps_data['formatted']}"
                else:
                    # No GPS, show country from MCC/MNC
                    mcc = meta.get('mcc')
                    mnc = meta.get('mnc')
                    if mcc:
                        loc_str = get_location_info(str(mcc), str(mnc) if mnc else None)
                
                self.users_table.setItem(row, 6, QTableWidgetItem(loc_str)) # Location/Country

        # Update filters
        call_group = None
        if meta.get('dest_ssi'):
            call_group = str(meta['dest_ssi'])
        elif meta.get('talkgroup_id'):
            call_group = f"TG:{meta['talkgroup_id']}"
            
        call_client = str(meta['source_ssi']) if meta.get('source_ssi') else None
        user_group = str(meta['talkgroup_id']) if meta.get('talkgroup_id') else None
        
        self.update_filter_dropdowns(call_group, call_client, user_group)

    @pyqtSlot(dict)
    def on_frame(self, frame):
        """Handle decoded frame."""
        self.frame_count += 1

        # Always log each decoded frame (even if UI filters hide it).
        try:
            import json

            frames_logger.info(
                json.dumps(
                    {
                        "event": "frame_decoded",
                        "time": datetime.now().strftime("%H:%M:%S"),
                        "frame_number": frame.get("number"),
                        "type": frame.get("type"),
                        "type_name": frame.get("type_name"),
                        "encrypted": bool(frame.get("encrypted")),
                        "encryption_algorithm": frame.get("encryption_algorithm"),
                        "decrypted": bool(frame.get("decrypted")),
                        "decryption_attempted": bool(frame.get("decryption_attempted")),
                        "keys_tried": frame.get("keys_tried"),
                        "best_score": frame.get("best_score"),
                        "best_key": frame.get("best_key"),
                        "key_used": frame.get("key_used"),
                        "decrypt_confidence": frame.get("decrypt_confidence"),
                        "decryption_error": frame.get("decryption_error"),
                        "additional_info": frame.get("additional_info", {}),
                        "sds_message": frame.get("sds_message"),
                        "decoded_text": frame.get("decoded_text"),
                        "has_voice": bool(frame.get("has_voice")),
                    },
                    ensure_ascii=False,
                )
            )
        except Exception:
            pass
        
        # VALIDATE FRAME: Check if this is real TETRA
        is_valid, confidence, issues = self.signal_validator.validate_frame(frame)
        
        if not is_valid:
            # Log invalid frames but don't display them
            logger.debug(f"Invalid TETRA frame: confidence={confidence:.1%}, issues={issues}")
            return  # Skip this frame
        
        if confidence < 0.7:
            # Low confidence frame - log warning
            logger.warning(f"Low confidence TETRA frame: {confidence:.1%}, issues={issues}")
        
        # Update tables regardless of auto-decrypt setting.
        self.update_tables(frame)
        
        # Try SDS reassembly first
        reassembled_sds = self.reassemble_sds_message(frame)
        if reassembled_sds:
            frame['sds_message'] = reassembled_sds
            frame['is_reassembled'] = True
        
        # Check if this is test data FIRST - don't count test frames for TETRA detection
        is_test = frame.get('is_test_data', False)
        
        # Track TETRA signal detection (only for real frames, not test data)
        # Count ALL decoded frames as potential TETRA frames (if decoder found them, they're likely TETRA)
        if not is_test:
            import time
            # Count all non-test frames as potential TETRA frames
            # If the decoder found and decoded a frame, it's likely a valid TETRA frame
            self.tetra_frame_count += 1
            
            # Check for sync position (indicates sync pattern was found)
            if frame.get('position') is not None:
                self.tetra_sync_count += 1
            
            # Check for valid CRC (indicates valid frame structure)
            if frame.get('burst_crc') is True:
                self.tetra_valid_frames += 1
            elif frame.get('decrypted') or frame.get('bypass_clear'):
                # Decrypted frames are strong evidence of valid TETRA
                self.tetra_valid_frames += 1
            elif 'burst_crc' not in frame and frame.get('type') is not None:
                # Frame was decoded even without explicit CRC - count as valid
                # Having a frame type means the decoder successfully parsed it
                self.tetra_valid_frames += 1  # Count as full valid frame, not 0.5
            
            # Track when first frame was detected
            if self.tetra_frame_count == 1:
                self.first_frame_time = time.time()
            
            # Update TETRA status with debouncing to prevent rapid changes
            # Wait at least min_detection_time before showing "TETRA Signal Detected"
            current_time = time.time()
            time_since_first = current_time - (self.first_frame_time or current_time)
            
            # Update status more frequently when frames are being decoded
            # Update if enough time has passed since first frame AND enough time since last update
            # Also update more frequently when we have many frames (likely valid signal)
            should_update = (
                time_since_first >= self.min_detection_time and  # Wait for minimum detection time
                (current_time - self.last_tetra_update > 2.0 or  # 2 seconds since last update (faster)
                 self.tetra_frame_count % 5 == 0 or  # Or every 5 frames (more frequent)
                 (self.tetra_frame_count >= 10 and current_time - self.last_tetra_update > 1.0))  # Or every 1s when many frames
            )
            
            if should_update:
                self.update_tetra_status()
                self.last_tetra_update = current_time
        
        if frame.get('decrypted'):
            self.decrypted_count += 1
        
        # Check filter before adding
        type_name = frame.get('type_name', "Unknown")
        filter_text = self.type_filter.currentText().lower()
        if "traffic" in filter_text and "traffic" not in type_name.lower():
            return
        if "control" in filter_text and "control" not in type_name.lower():
            return
        if "broadcast" in filter_text and "broadcast" not in type_name.lower():
            return
        if "sds" in filter_text:
            # SDS can be in MAC-DATA, MAC-SUPPL, or just have an SDS message attached
            has_sds = "sds" in type_name.lower() or "data" in type_name.lower() or "suppl" in type_name.lower() or 'sds_message' in frame or "sns" in type_name.lower()
            if not has_sds:
                return
            
        row = self.frames_table.rowCount()
        self.frames_table.insertRow(row)
        
        # Determine row color based on frame type - Enhanced colors
        row_bg = None
        text_color = None
        
        if "MAC-RESOURCE" in type_name:
            row_bg = QColor(30, 50, 80)  # Bright Blue
            text_color = QColor(200, 220, 255)  # Light blue text
        elif "MAC-BROADCAST" in type_name:
            row_bg = QColor(80, 70, 30)  # Bright Yellow/Orange
            text_color = QColor(255, 240, 200)  # Light yellow text
        elif "MAC-FRAG" in type_name:
            row_bg = QColor(30, 80, 30)  # Bright Green
            text_color = QColor(200, 255, 200)  # Light green text
        elif "MAC-SUPPL" in type_name:
            row_bg = QColor(80, 30, 80)  # Bright Purple
            text_color = QColor(255, 200, 255)  # Light purple text
        elif "MAC-U-SIGNAL" in type_name:
            row_bg = QColor(100, 30, 30)  # Bright Red
            text_color = QColor(255, 200, 200)  # Light red text
        elif "MAC-DATA" in type_name:
            row_bg = QColor(30, 80, 100)  # Bright Cyan
            text_color = QColor(200, 255, 255)  # Light cyan text
        elif frame.get('has_voice'):
            row_bg = QColor(0, 120, 0)  # Bright Green for voice
            text_color = QColor(200, 255, 200)  # Light green text
        elif 'sds_message' in frame or 'decoded_text' in frame:
            row_bg = QColor(0, 100, 120)  # Bright Cyan for SDS
            text_color = QColor(200, 255, 255)  # Light cyan text
            
        def create_item(text, color=None):
            item = QTableWidgetItem(str(text))
            if is_test:
                item.setForeground(QColor(128, 128, 128))
            elif color:
                item.setForeground(color)
            elif text_color:
                item.setForeground(text_color)
            
            if row_bg:
                item.setBackground(row_bg)
            return item

        time_str = datetime.now().strftime("%H:%M:%S")
        self.frames_table.setItem(row, 0, create_item(time_str))
        
        self.frames_table.setItem(row, 1, create_item(frame['number']))
        
        self.frames_table.setItem(row, 2, create_item(type_name))
        
        # Build description with all available metadata
        desc = frame.get('additional_info', {}).get('description', '')
        
        # Check call_metadata first (from real decoder)
        if 'call_metadata' in frame:
            meta = frame['call_metadata']
            if meta.get('talkgroup_id'):
                desc += f" | TG:{meta['talkgroup_id']}"
            if meta.get('source_ssi'):
                desc += f" | Src:{meta['source_ssi']}"
            if meta.get('dest_ssi'):
                desc += f" | Dst:{meta['dest_ssi']}"
            if meta.get('call_type'):
                desc += f" | {meta['call_type']}"
        
        # Fallback to additional_info (from synthetic or other parts)
        elif 'additional_info' in frame:
            info = frame['additional_info']
            if 'talkgroup' in info:
                desc += f" | TG:{info['talkgroup']}"
            if 'source_ssi' in info:
                desc += f" | Src:{info['source_ssi']}"
            if 'dest_ssi' in info:
                desc += f" | Dst:{info['dest_ssi']}"
            if 'channel' in info:
                desc += f" | Ch:{info['channel']}"
            if 'control' in info:
                desc += f" | {info['control']}"
        
        message_text = ""
        # Check for readable message text
        text_to_check = frame.get('sds_message') or frame.get('decoded_text') or ''
        if text_to_check:
            if _is_readable_text(text_to_check):
                # Clean and show readable text
                clean = text_to_check
                for prefix in ['[GSM7]', '[TXT]', '[SDS]', '[SDS-1]', '[SDS-GSM]', '💬', '🧩']:
                    clean = clean.replace(prefix, '')
                clean = clean.strip().strip('"')
                prefix_icon = "🧩 " if frame.get('is_reassembled') else "💬 "
                message_text = f"{prefix_icon}\"{clean.strip()[:80]}\""
            else:
                # Check if it's location/metadata
                location = _format_location_data(frame)
                if location:
                    message_text = location
                else:
                    metadata = _format_binary_metadata(frame)
                    if metadata:
                        message_text = metadata
                    else:
                        # Don't show garbled text - just show "Decrypted" if decrypted
                        if frame.get('decrypted'):
                            message_text = "✅ Decrypted"
                        else:
                            message_text = "🔒 (Encrypted)"
        
        # Mark test data
        if is_test:
            desc = "[TEST] " + desc
        
        self.frames_table.setItem(row, 3, create_item(desc))
        self.frames_table.setItem(row, 4, create_item(message_text))
        
        enc_text = "Yes" if frame.get('encrypted') else "No"
        if frame.get("encryption_suspected") and not frame.get("encrypted"):
            enc_text = "Suspected"

        if frame.get('encrypted') or frame.get("encryption_suspected"):
            alg = frame.get('encryption_algorithm') or 'Unknown'
            enc_text += f" ({alg})"
        
        if frame.get('encrypted') or frame.get("encryption_suspected"):
            enc_color = QColor(255, 100, 100)
        else:
            enc_color = QColor(100, 255, 100)
        self.frames_table.setItem(row, 5, create_item(enc_text, enc_color))
        
        status_text = ""
        status_color = None
        if frame.get('decrypted'):
            confidence = frame.get('decrypt_confidence', 0)
            key_used = frame.get('key_used', 'unknown')
            status_text = f"✅ Decrypted ({confidence}) | {key_used}"
            status_color = QColor(0, 255, 255)
        elif frame.get("bypass_clear"):
            status_text = "🟢 Clear (Bypass)"
            status_color = QColor(100, 255, 100)
        elif frame.get("decryption_attempted"):
            keys_tried = frame.get("keys_tried", 0)
            best_score = frame.get("best_score", 0)
            best_key = frame.get("best_key") or "n/a"
            status_text = f"🔑 Bruteforce tried {keys_tried} | best {best_score} | {best_key}"
            status_color = QColor(200, 200, 120)
        elif frame.get('encrypted'):
            alg = frame.get('encryption_algorithm') or 'Unknown'
            if not self.auto_decrypt_cb.isChecked():
                status_text = f"🔒 Encrypted ({alg}) | Auto-Decrypt off"
            else:
                status_text = f"🔒 Encrypted ({alg})"
            status_color = QColor(255, 165, 0)
        else:
            status_text = "Clear"
            
        self.frames_table.setItem(row, 6, create_item(status_text, status_color))
        
        # Data Column - Prioritize decoded text but filter garbled
        data_str = ""
        if frame.get('has_voice'):
             data_str = "🔊 Voice Audio (Decoded)"
        else:
            # Check for location data first
            location_str = _format_location_data(frame)
            if location_str:
                data_str = location_str
            # Check for readable text
            elif 'decoded_text' in frame and frame['decoded_text']:
                text = frame['decoded_text']
                if _is_readable_text(text):
                    # Clean text - remove prefix
                    clean = text
                    for prefix in ['[GSM7]', '[TXT]', '[SDS]', '[SDS-1]', '[SDS-GSM]', '💬', '🧩']:
                        clean = clean.replace(prefix, '')
                    clean = clean.strip().strip('"')
                    data_str = f"💬 {clean.strip()[:80]}"
                else:
                    # Check if it's binary/metadata
                    metadata_str = _format_binary_metadata(frame)
                    if metadata_str:
                        data_str = metadata_str
                    else:
                        # Garbled text - just say decrypted if it was
                        if frame.get('decrypted'):
                            data_str = "✅ Decrypted (garbled)"
                        else:
                            data_str = "🔒 (Encrypted)"
            elif 'sds_message' in frame and frame['sds_message']:
                text = frame['sds_message']
                if _is_readable_text(text):
                    clean = text
                    for prefix in ['[GSM7]', '[TXT]', '[SDS]', '[SDS-1]', '[SDS-GSM]', '💬', '🧩']:
                        clean = clean.replace(prefix, '')
                    clean = clean.strip().strip('"')
                    data_str = f"💬 {clean.strip()[:80]}"
                else:
                    metadata_str = _format_binary_metadata(frame)
                    if metadata_str:
                        data_str = metadata_str
                    else:
                        if frame.get('decrypted'):
                            data_str = "✅ Decrypted (garbled)"
                        else:
                            data_str = "🔒 (Encrypted)"
            elif 'decrypted_bytes' in frame:
                # Try to parse decrypted bytes as text if printable
                try:
                    data_bytes = bytes.fromhex(frame['decrypted_bytes'])
                    if len(data_bytes) > 0:
                        # Try to decode as text
                        text = data_bytes.decode('latin-1', errors='replace')
                        # Check if text is actually readable
                        if _is_readable_text(text):
                            clean = text.strip()
                            data_str = f"💬 {clean[:80]}"
                        else:
                            # Not readable - show as decrypted but garbled
                            if frame.get('decrypted'):
                                data_str = "✅ Decrypted (garbled)"
                            else:
                                data_str = "🔒 (Binary data)"
                    else:
                        data_str = "✅ Decrypted (empty)"
                except Exception as e:
                    logger.debug(f"Error parsing decrypted bytes: {e}")
                    data_str = "✅ Decrypted (parse error)"
            elif 'mac_pdu' in frame and 'data' in frame['mac_pdu']:
                data = frame['mac_pdu']['data']
                if isinstance(data, (bytes, bytearray)):
                    # Try to decode as text
                    try:
                        text = data.decode('latin-1', errors='replace')
                        if _is_readable_text(text):
                            clean = text.strip()
                            data_str = f"💬 {clean[:80]}"
                        else:
                            # Binary or garbled data
                            if frame.get('decrypted'):
                                data_str = "✅ Decrypted (garbled)"
                            else:
                                data_str = "🔒 (Binary data)"
                    except:
                        data_str = "🔒 (Binary data)"
                else:
                    # Non-bytes data - check if readable
                    text = str(data)
                    if _is_readable_text(text):
                        data_str = f"💬 {text[:80]}"
                    else:
                        data_str = "🔒 (Binary data)"
            elif 'bits' in frame:
                # Raw bits - try to decode but filter garbled
                try:
                    bits = frame['bits']
                    if hasattr(bits, 'tobytes'):
                        data_bytes = bits.tobytes()
                        if len(data_bytes) > 0:
                            text = data_bytes.decode('latin-1', errors='replace')
                            if _is_readable_text(text):
                                clean = text.strip()
                                data_str = f"💬 {clean[:80]}"
                            else:
                                # Binary data - don't show hex
                                data_str = "🔒 (Binary data)"
                        else:
                            data_str = "(empty)"
                    else:
                        data_str = "🔒 (Binary data)"
                except:
                    data_str = "🔒 (Binary data)"
            else:
                data_str = ""
                  
        self.frames_table.setItem(row, 7, create_item(data_str))
        
        # Country column (new) - extract from MCC/MNC
        country_str = ""
        if 'call_metadata' in frame:
            meta = frame['call_metadata']
            mcc = meta.get('mcc')
            mnc = meta.get('mnc')
            if mcc:
                country_str = get_location_info(str(mcc), str(mnc) if mnc else None)
        elif 'additional_info' in frame:
            info = frame['additional_info']
            mcc = info.get('mcc')
            mnc = info.get('mnc')
            if mcc:
                country_str = get_location_info(str(mcc), str(mnc) if mnc else None)
        
        self.frames_table.setItem(row, 8, create_item(country_str))

        # Persist full frames table row to dedicated JSONL log.
        try:
            import json

            frames_logger.info(
                json.dumps(
                    {
                        "time": time_str,
                        "frame_number": frame.get("number"),
                        "type": type_name,
                        "description": desc,
                        "message": message_text,
                        "encrypted": bool(frame.get("encrypted")),
                        "encryption_algorithm": frame.get("encryption_algorithm"),
                        "decrypted": bool(frame.get("decrypted")),
                        "status": status_text,
                        "data": data_str,
                        "keys_tried": frame.get("keys_tried"),
                        "best_score": frame.get("best_score"),
                        "best_key": frame.get("best_key"),
                        "key_used": frame.get("key_used"),
                        "decrypt_confidence": frame.get("decrypt_confidence"),
                        "sds_message": frame.get("sds_message"),
                        "decoded_text": frame.get("decoded_text"),
                    },
                    ensure_ascii=False,
                )
            )
        except Exception:
            pass
        
        # Auto-scroll
        if self.autoscroll_cb.isChecked():
            self.frames_table.scrollToBottom()

    
    @pyqtSlot(str)
    def on_error(self, msg):
        """Handle error."""
        self.log(f"ERROR: {msg}", "red")
    
    @pyqtSlot(str)
    def on_status(self, msg):
        """Handle status."""
        self.log(msg)
        self.statusBar().showMessage(msg)
    
    @pyqtSlot(np.ndarray, np.ndarray)
    def on_spectrum(self, freqs, powers):
        """Handle spectrum update."""
        self.waterfall.update_spectrum(freqs, powers)
        if self.auto_spectrum_enabled:
            self._apply_auto_spectrum(freqs, powers)
        # Update tuned frequency display
        try:
            freq_mhz = float(self.freq_input.text())
            self.waterfall.set_tuned_frequency(freq_mhz)
            
            # Auto-follow frequency logic (AFC)
            if hasattr(self, 'follow_freq_cb') and self.follow_freq_cb.isChecked():
                # Find peak within +/- 10 kHz of current center frequency
                # This ensures we stay locked to the TETRA channel
                center_idx = np.abs(freqs - freq_mhz).argmin()
                
                # Define search window (e.g., +/- 10 kHz)
                # freqs are in MHz
                window_width_mhz = 0.010
                mask = np.abs(freqs - freq_mhz) < window_width_mhz
                
                if np.any(mask):
                    # Find peak in this window
                    window_indices = np.where(mask)[0]
                    if len(window_indices) > 0:
                        peak_idx_in_window = np.argmax(powers[window_indices])
                        peak_idx = window_indices[peak_idx_in_window]
                        
                        peak_freq = freqs[peak_idx]
                        peak_power = powers[peak_idx]
                        
                        # Only adjust if signal is strong enough (e.g., > -60 dB)
                        # and offset is significant (> 50 Hz) but small (< 10 kHz)
                        offset = peak_freq - freq_mhz
                        
                        if peak_power > -60 and abs(offset) > 0.00005: # 50 Hz
                            # Apply small correction (10% of offset) to smooth movement
                            # This centers the "TETRA spike"
                            new_freq = freq_mhz + (offset * 0.1)
                            
                            # Update UI and thread
                            self.freq_input.setText(f"{new_freq:.6f}")
                            if self.capture_thread:
                                # Use set_frequency to update running SDR
                                self.capture_thread.set_frequency(int(new_freq * 1e6))
        except:
            pass
    
    def update_displays(self):
        """Update displays."""
        self.decrypt_label.setText(f"🔒 {self.decrypted_count}/{self.frame_count}")
        
        # Update recording status
        if self.recording_active and self.recording_start_time:
            duration = datetime.now() - self.recording_start_time
            seconds = int(duration.total_seconds())
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            secs = seconds % 60
            
            size_str = "0 B"
            if hasattr(self, 'current_wav_file') and os.path.exists(self.current_wav_file):
                size_bytes = os.path.getsize(self.current_wav_file)
                if size_bytes > 1024*1024:
                    size_str = f"{size_bytes/(1024*1024):.1f} MB"
                else:
                    size_str = f"{size_bytes/1024:.1f} KB"
            
            self.recording_status_label.setText(f"🔴 LIVE | {hours:02}:{minutes:02}:{secs:02} | {size_str}")
            self.recording_status_label.setStyleSheet("font-weight: bold; padding: 5px; color: #ff0000; background-color: #220000;")
        else:
            self.recording_status_label.setText("⚫ Not Recording")
            self.recording_status_label.setStyleSheet("font-weight: bold; padding: 5px; color: #888888;")
        
        # Update recording status
        if self.recording_active and self.recording_start_time:
            duration = datetime.now() - self.recording_start_time
            seconds = int(duration.total_seconds())
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            secs = seconds % 60
            
            size_str = "0 B"
            if hasattr(self, 'current_wav_file') and os.path.exists(self.current_wav_file):
                size_bytes = os.path.getsize(self.current_wav_file)
                if size_bytes > 1024*1024:
                    size_str = f"{size_bytes/(1024*1024):.1f} MB"
                else:
                    size_str = f"{size_bytes/1024:.1f} KB"
            
            self.recording_status_label.setText(f"🔴 LIVE | {hours:02}:{minutes:02}:{secs:02} | {size_str}")
            self.recording_status_label.setStyleSheet("font-weight: bold; padding: 5px; color: #ff0000; background-color: #220000;")
        else:
            self.recording_status_label.setText("⚫ Not Recording")
            self.recording_status_label.setStyleSheet("font-weight: bold; padding: 5px; color: #888888;")
    
    def update_tetra_status(self):
        """Update TETRA signal detection status indicator."""
        import time
        
        # Only show TETRA detected if we have both signal and validated frames
        # This prevents showing TETRA detected when signal is lost
        if not self.signal_present or self.tetra_frame_count == 0:
            self.tetra_status_label.setText("⚫ No TETRA Signal")
            self.tetra_status_label.setStyleSheet(
                "font-weight: bold; padding: 5px; color: #888888;"
            )
            self.first_frame_time = None  # Reset when no frames
            return
        
        # Check if minimum detection time has passed
        current_time = time.time()
        time_since_first = current_time - (self.first_frame_time or current_time)
        
        # Don't show "TETRA Signal Detected" until minimum time has passed
        if time_since_first < self.min_detection_time:
            # Show "decoding" status during the wait period
            self.tetra_status_label.setText(f"🟡 Signal Detected (Analyzing... {int(self.min_detection_time - time_since_first)}s)")
            self.tetra_status_label.setStyleSheet(
                "font-weight: bold; padding: 5px; color: #ffaa00; background-color: #221100;"
            )
            return
        
        # Calculate detection metrics
        sync_rate = self.tetra_sync_count / max(self.tetra_frame_count, 1)
        crc_rate = self.tetra_valid_frames / max(self.tetra_frame_count, 1)
        
        # More lenient detection: if frames are being decoded successfully, they're likely TETRA
        # Decrypted frames or frames with type information are strong indicators
        # Require at least 3 frames, and if we have validated frames (sync/CRC/decrypted), use that
        # Otherwise, if we have multiple decoded frames, count them as TETRA
        has_validated_frames = (sync_rate > 0.1 or crc_rate > 0.1)
        
        is_tetra_detected = (
            self.tetra_frame_count >= 3 and  # At least 3 frames
            (has_validated_frames or self.tetra_frame_count >= 5)  # Either validated or 5+ frames
        )
        
        # High confidence: multiple frames with good validation or many decoded frames
        high_confidence = (
            self.tetra_frame_count >= 5 and
            (sync_rate > 0.2 or crc_rate > 0.3 or self.tetra_frame_count >= 10)  # Lower threshold or many frames
        )
        
        if high_confidence:
            self.tetra_status_label.setText(
                f"🟢 TETRA Signal Detected ({self.tetra_frame_count} frames, Sync: {sync_rate:.0%}, CRC: {crc_rate:.0%})"
            )
            self.tetra_status_label.setStyleSheet(
                "font-weight: bold; padding: 5px; color: #00ff00; background-color: #002200;"
            )
        elif is_tetra_detected:
            # Medium confidence: some frames decoded
            self.tetra_status_label.setText(
                f"🟡 TETRA Detected ({self.tetra_frame_count} frames, Sync: {sync_rate:.0%}, CRC: {crc_rate:.0%})"
            )
            self.tetra_status_label.setStyleSheet(
                "font-weight: bold; padding: 5px; color: #ffaa00; background-color: #221100;"
            )
        else:
            self.tetra_status_label.setText("⚫ No TETRA Signal")
            self.tetra_status_label.setStyleSheet(
                "font-weight: bold; padding: 5px; color: #888888;"
            )
    
    def update_stats(self):
        """Update statistics."""
        html = f"""
        <h2>📊 Statistics</h2>
        <table style="width:100%; font-family: monospace;">
        <tr><td><b>Total Frames:</b></td><td>{self.frame_count}</td></tr>
        <tr><td><b>Decrypted:</b></td><td>{self.decrypted_count}</td></tr>
        <tr><td><b>Success Rate:</b></td><td>{(self.decrypted_count/max(1,self.frame_count)*100):.1f}%</td></tr>
        <tr><td><b>TETRA Frames:</b></td><td>{self.tetra_frame_count}</td></tr>
        <tr><td><b>Valid CRC:</b></td><td>{self.tetra_valid_frames}</td></tr>
        </table>
        """
        self.stats_text.setHtml(html)
    
    def log(self, msg, color=None):
        """Log message."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted = f"[{timestamp}] {msg}"
        
        if color:
            formatted = f'<span style="color: {color};">{formatted}</span>'
        
        self.log_text.append(formatted)
        scrollbar = self.log_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

        # Also write to file logs (keep UI and logs in sync).
        try:
            logger.info("%s", msg)
        except Exception:
            pass
    
    def closeEvent(self, event):
        """Handle close."""
        # Save any active recording
        if self.recording_active:
            self.save_recording()
        
        if self.capture_thread and self.capture_thread.isRunning():
            self.capture_thread.stop()
            self.capture_thread.wait()
        event.accept()


class CLITetraListener(QObject):
    """CLI Listener for TETRA events."""
    
    def __init__(self, capture_thread):
        super().__init__()
        self.capture_thread = capture_thread
        self.start_time = datetime.now()
        self.signal_active = False  # Track signal state
        self.frame_count = 0
        
        # Connect signals
        self.capture_thread.status_update.connect(self.on_status)
        self.capture_thread.error_occurred.connect(self.on_error)
        self.capture_thread.signal_detected.connect(self.on_signal)
        self.capture_thread.signal_lost.connect(self.on_signal_lost)
        self.capture_thread.frame_decoded.connect(self.on_frame)
        
    @pyqtSlot(str)
    def on_status(self, msg):
        # Remove Unicode characters for Windows compatibility
        msg = msg.replace('✓', '[OK]').replace('✗', '[X]').replace('⏺', '[REC]').replace('⏸', '[PAUSE]')
        print(f"{Fore.CYAN}[STATUS] {msg}{Style.RESET_ALL}")
        
    @pyqtSlot(str)
    def on_error(self, msg):
        print(f"{Fore.RED}[ERROR] {msg}{Style.RESET_ALL}")
        
    @pyqtSlot(float, float)
    def on_signal(self, freq, snr):
        if not self.signal_active:  # Only show when state changes
            print(f"{Fore.GREEN}[SIGNAL] TETRA Detected at {freq/1e6:.4f} MHz (SNR: {snr:.1f} dB){Style.RESET_ALL}")
            self.signal_active = True
        
    @pyqtSlot()
    def on_signal_lost(self):
        if self.signal_active:  # Only show when state changes
            print(f"{Fore.YELLOW}[SIGNAL] Signal Lost (decoded {self.frame_count} frames){Style.RESET_ALL}")
            self.signal_active = False
        
    @pyqtSlot(dict)
    def on_frame(self, frame):
        self.frame_count += 1
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        fn = frame.get('number', '?')
        ftype = frame.get('type_name', 'Unknown')
        
        # Color coding based on frame type
        color = Fore.WHITE
        if "MAC-RESOURCE" in ftype: color = Fore.BLUE
        elif "MAC-BROADCAST" in ftype: color = Fore.YELLOW
        elif "MAC-FRAG" in ftype: color = Fore.GREEN
        elif "MAC-SUPPL" in ftype: color = Fore.MAGENTA
        elif "MAC-U-SIGNAL" in ftype: color = Fore.RED
        elif "MAC-DATA" in ftype: color = Fore.CYAN
        
        # Encryption status
        enc = ""
        if frame.get('decrypted'):
            enc = f"{Fore.GREEN}[DEC]{Style.RESET_ALL}"
        elif frame.get('encrypted'):
            enc = f"{Fore.RED}[ENC]{Style.RESET_ALL}"
            
        # Content
        content = ""
        if 'sds_message' in frame:
            content = f"{Fore.CYAN}SDS: {frame['sds_message']}{Style.RESET_ALL}"
        elif 'decoded_text' in frame:
            content = f"{Fore.CYAN}TXT: {frame['decoded_text']}{Style.RESET_ALL}"
        elif frame.get('has_voice'):
            content = f"{Fore.GREEN}Voice Audio{Style.RESET_ALL}"
            
        print(f"{Fore.WHITE}[{timestamp}] #{fn:<4} {color}{ftype:<15}{Style.RESET_ALL} {enc} {content}")


def main():
    """Main entry point with CLI argument support."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='TETRA Decoder Pro - Modern GUI with live voice decoding',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  %(prog)s                              # Launch GUI normally
  %(prog)s --no-gui -f 392.225          # Run in CLI mode
  %(prog)s -f 392.225 --auto-start      # Auto-start capture
  %(prog)s -f 392.225 --auto-start -m   # Auto-start with audio monitoring
  %(prog)s -f 392.225 -g 35 -s 1.8      # Set frequency, gain, sample rate
  %(prog)s --scan 390 392               # Scan range first, then launch GUI
        '''
    )
    
    parser.add_argument('-f', '--frequency', type=float, default=390.865,
                        help='Frequency in MHz (default: 390.865)')
    parser.add_argument('-g', '--gain', type=float, default=50.0,
                        help='RF gain in dB (default: 50.0)')
    parser.add_argument('-s', '--sample-rate', type=float, default=2.4,
                        help='Sample rate in MHz (default: 2.4)')
    parser.add_argument('--auto-start', action='store_true',
                        help='Automatically start capture on launch')
    parser.add_argument('-m', '--monitor-audio', action='store_true',
                        help='Enable audio monitoring on start')
    parser.add_argument('--scan', nargs=2, type=float, metavar=('START', 'STOP'),
                        help='Scan frequency range first (in MHz)')
    parser.add_argument('--auto-decrypt', action='store_true', default=True,
                        help='Enable auto-decryption (default: enabled)')
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='Enable verbose logging')
    parser.add_argument('--no-gui', action='store_true',
                        help='Run in CLI mode without GUI')
    
    args = parser.parse_args()

    log_files = _setup_logging(verbose=bool(args.verbose))
    logger.info("Logging to: %s", _get_log_dir())
    logger.debug("Log files: %s", {k: str(v) for k, v in log_files.items()})
    
    # Scan if requested
    if args.scan:
        print("=" * 60)
        print("SCANNING FOR TETRA SIGNALS")
        print("=" * 60)
        from tetraear.signal.capture import RTLCapture
        from tetraear.signal.scanner import FrequencyScanner
        
        start_freq = args.scan[0] * 1e6
        stop_freq = args.scan[1] * 1e6
        
        rtl = RTLCapture(frequency=start_freq, sample_rate=2.4e6, gain=50)
        if rtl.open():
            scanner = FrequencyScanner(
                rtl, 
                sample_rate=2.4e6,
                scan_step=25e3,
                noise_floor=-45,  # Default noise floor
                bottom_threshold=-85  # Default bottom threshold
            )
            results = []
            
            print(f"\nScanning {args.scan[0]:.3f} - {args.scan[1]:.3f} MHz...")
            freq = start_freq
            while freq <= stop_freq:
                result = scanner.scan_frequency(freq)
                if result['power_db'] > -60:
                    results.append(result)
                    print(f"  {freq/1e6:.3f} MHz: {result['power_db']:.1f} dB *** SIGNAL")
                freq += 25e3
            
            rtl.close()
            
            if results:
                results.sort(key=lambda x: x['power_db'], reverse=True)
                best = results[0]
                print(f"\n[OK] Best signal: {best['frequency']/1e6:.3f} MHz ({best['power_db']:.1f} dB)")
                if not args.frequency:
                    args.frequency = best['frequency'] / 1e6
                    print(f"  Auto-setting frequency to {args.frequency:.3f} MHz")
            else:
                print("\n[X] No strong signals found")
            print()
    
    if args.no_gui:
        from PyQt6.QtCore import QCoreApplication
        app = QCoreApplication(sys.argv)
        
        # Set UTF-8 encoding for Windows console
        if sys.platform == 'win32':
            import os
            os.system('chcp 65001 >nul 2>&1')
        
        print(f"{Fore.CYAN}TETRA Decoder Pro - CLI Mode{Style.RESET_ALL}")
        print(f"Frequency: {args.frequency} MHz")
        print(f"Gain: {args.gain} dB")
        print(f"Sample Rate: {args.sample_rate} MHz")
        
        capture_thread = CaptureThread()
        capture_thread.frequency = args.frequency * 1e6
        capture_thread.gain = args.gain
        capture_thread.sample_rate = args.sample_rate * 1e6
        capture_thread.auto_decrypt = args.auto_decrypt
        
        listener = CLITetraListener(capture_thread)
        
        capture_thread.start()
        
        try:
            sys.exit(app.exec())
        except KeyboardInterrupt:
            print(f"\n{Fore.YELLOW}Stopping...{Style.RESET_ALL}")
            capture_thread.stop()
            capture_thread.wait()
            sys.exit(0)
            
    else:
        # Create Qt application
        app = QApplication(sys.argv)
        app.setStyle('Fusion')
        
        window = ModernTetraGUI()
        
        # Apply CLI arguments
        if args.frequency:
            window.freq_input.setText(f"{args.frequency:.3f}")
            logger.info(f"Set frequency to {args.frequency:.3f} MHz")
        
        if args.gain != 50.0:
            # Convert gain to slider value (0-100 = 0-50 dB)
            slider_val = int(args.gain * 2)
            window.gain_slider.setValue(slider_val)
            logger.info(f"Set gain to {args.gain:.1f} dB")
        
        if args.sample_rate != 2.4:
            # Convert sample rate to slider value (0 = 1.8 MHz, 6 = 2.4 MHz)
            # Formula: slider_value = (sample_rate - 1.8) / 0.1
            slider_val = int((args.sample_rate - 1.8) / 0.1)
            slider_val = max(0, min(6, slider_val))  # Clamp to valid range
            window.sample_rate_slider.setValue(slider_val)
            logger.info(f"Set sample rate to {args.sample_rate:.1f} MHz")
        
        if args.monitor_audio:
            window.hear_voice_cb.setChecked(True)
            logger.info("Audio monitoring enabled")
        
        if not args.auto_decrypt:
            window.auto_decrypt_cb.setChecked(False)
        
        window.show()
        
        # Auto-start if requested
        if args.auto_start:
            logger.info("Auto-starting capture...")
            # Use QTimer to start after GUI is fully initialized
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(500, window.on_start)
        
        sys.exit(app.exec())


if __name__ == '__main__':
    main()
