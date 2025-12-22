"""
TETRA Decoder GUI - Main Application Window
Real-time signal processing, decryption, and audio playback
"""

import sys
import threading
import queue
from datetime import datetime
from pathlib import Path

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QTextEdit, QComboBox, QSpinBox,
    QGroupBox, QCheckBox, QTabWidget, QTableWidget, QTableWidgetItem,
    QProgressBar, QSlider, QFileDialog, QMessageBox, QSplitter
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QThread, pyqtSlot
from PyQt6.QtGui import QFont, QColor, QPalette
from PyQt6.QtCharts import QChart, QChartView, QLineSeries, QValueAxis

import numpy as np
import sounddevice as sd
from scipy.signal import resample

from rtl_capture import RTLCapture
from signal_processor import SignalProcessor
from tetra_decoder import TetraDecoder
from tetra_crypto import TetraKeyManager
from frequency_scanner import FrequencyScanner


class WorkerSignals:
    """Signals for worker thread communication."""
    pass


class CaptureThread(QThread):
    """Thread for continuous RTL-SDR capture and processing."""
    
    # Signals
    signal_detected = pyqtSignal(float, float)  # frequency, power
    frame_decoded = pyqtSignal(dict)  # frame data
    audio_data = pyqtSignal(np.ndarray)  # audio samples
    error_occurred = pyqtSignal(str)  # error message
    status_update = pyqtSignal(str)  # status message
    spectrum_update = pyqtSignal(np.ndarray, np.ndarray)  # frequencies, powers
    
    def __init__(self):
        super().__init__()
        self.running = False
        self.capture = None
        self.processor = None
        self.decoder = None
        self.frequency = 400e6
        self.sample_rate = 1.8e6
        self.gain = 'auto'
        self.auto_decrypt = True
        
    def set_frequency(self, freq):
        """Set tuning frequency."""
        self.frequency = freq
        if self.capture and self.capture.sdr:
            try:
                self.capture.set_frequency(freq)
                self.status_update.emit(f"Tuned to {freq/1e6:.3f} MHz")
            except Exception as e:
                self.error_occurred.emit(f"Failed to set frequency: {e}")
    
    def set_gain(self, gain):
        """Set gain."""
        self.gain = gain
        if self.capture and self.capture.sdr:
            try:
                self.capture.sdr.gain = gain
                self.status_update.emit(f"Gain set to {gain}")
            except Exception as e:
                self.error_occurred.emit(f"Failed to set gain: {e}")
    
    def load_keys(self, key_file):
        """Load encryption keys from file."""
        try:
            key_manager = TetraKeyManager()
            key_manager.load_key_file(key_file)
            self.decoder = TetraDecoder(key_manager=key_manager, auto_decrypt=self.auto_decrypt)
            self.status_update.emit(f"Loaded keys from {key_file}")
        except Exception as e:
            self.error_occurred.emit(f"Failed to load keys: {e}")
    
    def run(self):
        """Main capture loop."""
        self.running = True
        
        try:
            # Initialize capture with proper SDR setup
            self.status_update.emit("Initializing RTL-SDR device...")
            self.capture = RTLCapture(
                frequency=self.frequency,
                sample_rate=self.sample_rate,
                gain=self.gain
            )
            
            if not self.capture.open():
                self.error_occurred.emit("Failed to open RTL-SDR device - check driver installation")
                return
            
            # Verify SDR is properly configured
            if self.capture.sdr is None:
                self.error_occurred.emit("RTL-SDR device not properly initialized")
                return
            
            self.status_update.emit("Initializing signal processor and decoder...")
            self.processor = SignalProcessor(sample_rate=self.sample_rate)
            self.decoder = TetraDecoder(auto_decrypt=self.auto_decrypt)
            
            self.status_update.emit(f"✓ Capture started - Freq: {self.frequency/1e6:.3f} MHz, Gain: {self.gain}")
            
            while self.running:
                try:
                    # Capture samples
                    samples = self.capture.read_samples(256*1024)
                    
                    # Compute spectrum for display (simplified and faster)
                    # Decimate samples for FFT
                    decimation = 100
                    samples_decimated = samples[::decimation]
                    
                    # Compute FFT with windowing for better spectrum
                    window = np.hanning(len(samples_decimated))
                    fft = np.fft.fftshift(np.fft.fft(samples_decimated * window))
                    freqs = np.fft.fftshift(np.fft.fftfreq(len(samples_decimated), 1/self.sample_rate))
                    
                    # Convert to power (dB) with proper noise floor
                    power_linear = np.abs(fft)
                    # Calculate noise floor (10th percentile)
                    noise_floor = np.percentile(power_linear, 10)
                    # Subtract noise floor for better dynamic range
                    power_linear_cleaned = np.maximum(power_linear - noise_floor, 1e-10)
                    power = 10 * np.log10(power_linear_cleaned + 1e-10)
                    
                    # Normalize to reasonable range
                    power_max = np.percentile(power, 95)  # 95th percentile as reference
                    power = power - power_max  # Normalize so peaks are near 0 dB
                    
                    # Shift to actual frequency
                    freqs_actual = freqs + self.frequency
                    
                    # Further decimate for display (every 10th point)
                    self.spectrum_update.emit(
                        freqs_actual[::10],
                        power[::10]
                    )
                    
                    # Detect signal with better threshold
                    # Use power above noise floor
                    power_above_noise = power - np.median(power)
                    max_power = np.max(power_above_noise)
                    if max_power > -40:  # Signal threshold relative to noise
                        # Convert back to absolute dB for display
                        self.signal_detected.emit(self.frequency, max_power)
                    
                    # Process for TETRA
                    demodulated = self.processor.process(samples)
                    
                    # Decode frames
                    frames = self.decoder.decode(demodulated)
                    
                    for frame in frames:
                        self.frame_decoded.emit(frame)
                    
                    # Extract audio (simplified - actual TETRA audio decoding is complex)
                    # This is a placeholder that generates audio from the signal
                    audio = self._extract_audio(samples)
                    if audio is not None and len(audio) > 0:
                        self.audio_data.emit(audio)
                    
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
            self.status_update.emit("Capture stopped")
    
    def _extract_audio(self, samples):
        """
        Extract audio from TETRA signal with voice activity detection.
        Real TETRA uses ACELP codec which requires complex decoding.
        This implementation provides FM demodulation with VAD.
        """
        try:
            # FM demodulation for audio
            phase = np.angle(samples)
            audio = np.diff(np.unwrap(phase))
            
            # Apply high-pass filter to remove DC offset
            from scipy.signal import butter, sosfilt
            sos = butter(4, 300, 'high', fs=self.sample_rate, output='sos')
            audio = sosfilt(sos, audio)
            
            # Apply low-pass filter for voice band (300-3400 Hz)
            sos_lp = butter(4, 3400, 'low', fs=self.sample_rate, output='sos')
            audio = sosfilt(sos_lp, audio)
            
            # Resample to 8 kHz (TETRA voice rate)
            target_rate = 8000
            current_rate = self.sample_rate
            num_samples = int(len(audio) * target_rate / current_rate)
            audio_resampled = resample(audio, num_samples)
            
            # Voice Activity Detection (VAD)
            # Calculate short-term energy
            frame_length = 160  # 20ms at 8kHz
            energy = np.array([
                np.sum(audio_resampled[i:i+frame_length]**2)
                for i in range(0, len(audio_resampled)-frame_length, frame_length)
            ])
            
            # Adaptive threshold based on signal statistics
            if len(energy) > 0:
                energy_mean = np.mean(energy)
                energy_std = np.std(energy)
                threshold = energy_mean + 2 * energy_std
                
                # Check if voice is present
                voice_frames = np.sum(energy > threshold)
                total_frames = len(energy)
                
                if voice_frames / total_frames < 0.1:
                    # Less than 10% voice activity - likely just noise
                    return None
            
            # Normalize with AGC (Automatic Gain Control)
            max_val = np.max(np.abs(audio_resampled))
            if max_val > 0:
                audio_resampled = audio_resampled / max_val * 0.5  # 50% max to prevent clipping
            
            return audio_resampled.astype(np.float32)
        except Exception as e:
            logger.debug(f"Audio extraction error: {e}")
            return None
    
    def stop(self):
        """Stop capture thread."""
        self.running = False


class TetraGUI(QMainWindow):
    """Main GUI window for TETRA decoder."""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("TETRA Decoder - Live Monitor")
        self.setGeometry(100, 100, 1400, 900)
        
        # Capture thread
        self.capture_thread = None
        self.audio_stream = None
        self.audio_buffer = queue.Queue(maxsize=10)
        
        # Setup UI
        self.init_ui()
        
        # Timer for updates
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_displays)
        self.update_timer.start(100)  # 10 Hz update
        
        # Frame counter
        self.frame_count = 0
        self.decrypted_count = 0
        
    def init_ui(self):
        """Initialize user interface."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout(central_widget)
        
        # Create splitter for resizable sections
        splitter = QSplitter(Qt.Orientation.Vertical)
        main_layout.addWidget(splitter)
        
        # Top section: Controls and spectrum
        top_widget = QWidget()
        top_layout = QVBoxLayout(top_widget)
        
        # Control panel
        control_group = self.create_control_panel()
        top_layout.addWidget(control_group)
        
        # Spectrum display
        spectrum_group = self.create_spectrum_display()
        top_layout.addWidget(spectrum_group)
        
        splitter.addWidget(top_widget)
        
        # Bottom section: Tabs for data
        tabs = QTabWidget()
        
        # Frames tab with controls
        frames_widget = QWidget()
        frames_layout = QVBoxLayout()
        
        # Autoscroll control
        frames_control_layout = QHBoxLayout()
        self.autoscroll_cb = QCheckBox("Auto-scroll")
        self.autoscroll_cb.setChecked(False)  # Disabled by default to prevent spam
        frames_control_layout.addWidget(self.autoscroll_cb)
        
        self.clear_frames_btn = QPushButton("Clear Frames")
        self.clear_frames_btn.clicked.connect(lambda: self.frames_table.setRowCount(0))
        frames_control_layout.addWidget(self.clear_frames_btn)
        
        frames_control_layout.addStretch()
        frames_layout.addLayout(frames_control_layout)
        
        self.frames_table = self.create_frames_table()
        frames_layout.addWidget(self.frames_table)
        
        frames_widget.setLayout(frames_layout)
        tabs.addTab(frames_widget, "Decoded Frames")
        
        # Log tab
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Courier", 9))
        tabs.addTab(self.log_text, "Log")
        
        # Audio tab
        audio_widget = self.create_audio_panel()
        tabs.addTab(audio_widget, "Audio")
        
        # Statistics tab
        stats_widget = self.create_statistics_panel()
        tabs.addTab(stats_widget, "Statistics")
        
        splitter.addWidget(tabs)
        
        # Set splitter sizes
        splitter.setSizes([400, 500])
        
        # Status bar
        self.statusBar().showMessage("Ready")
        
    def create_control_panel(self):
        """Create control panel group."""
        group = QGroupBox("Controls")
        layout = QVBoxLayout()
        
        # Row 1: Frequency control
        freq_layout = QHBoxLayout()
        freq_layout.addWidget(QLabel("Frequency (MHz):"))
        self.freq_input = QLineEdit("400.000")
        self.freq_input.setMaximumWidth(100)
        freq_layout.addWidget(self.freq_input)
        
        self.freq_preset = QComboBox()
        self.freq_preset.addItems([
            "Custom",
            "390.000 MHz (Poland)",
            "392.500 MHz (Poland)",
            "395.000 MHz (Poland)",
            "420.000 MHz (EU)",
        ])
        self.freq_preset.currentTextChanged.connect(self.on_preset_changed)
        freq_layout.addWidget(self.freq_preset)
        
        self.tune_btn = QPushButton("Tune")
        self.tune_btn.clicked.connect(self.on_tune_clicked)
        freq_layout.addWidget(self.tune_btn)
        
        freq_layout.addStretch()
        layout.addLayout(freq_layout)
        
        # Row 2: Gain and sample rate
        settings_layout = QHBoxLayout()
        settings_layout.addWidget(QLabel("Gain:"))
        self.gain_input = QComboBox()
        self.gain_input.addItems(['auto'] + [str(x) for x in range(0, 50, 5)])
        self.gain_input.setMaximumWidth(80)
        self.gain_input.currentTextChanged.connect(self.on_gain_changed)
        settings_layout.addWidget(self.gain_input)
        
        settings_layout.addWidget(QLabel("Sample Rate:"))
        self.sample_rate_input = QComboBox()
        self.sample_rate_input.addItems(['1.8 MHz', '2.4 MHz'])
        self.sample_rate_input.setMaximumWidth(100)
        settings_layout.addWidget(self.sample_rate_input)
        
        settings_layout.addStretch()
        layout.addLayout(settings_layout)
        
        # Row 3: Decryption controls
        decrypt_layout = QHBoxLayout()
        self.auto_decrypt_cb = QCheckBox("Auto-Decrypt")
        self.auto_decrypt_cb.setChecked(True)
        decrypt_layout.addWidget(self.auto_decrypt_cb)
        
        self.load_keys_btn = QPushButton("Load Keys...")
        self.load_keys_btn.clicked.connect(self.on_load_keys)
        decrypt_layout.addWidget(self.load_keys_btn)
        
        decrypt_layout.addStretch()
        layout.addLayout(decrypt_layout)
        
        # Row 4: Start/Stop buttons
        button_layout = QHBoxLayout()
        
        self.start_btn = QPushButton("▶ Start")
        self.start_btn.clicked.connect(self.on_start_clicked)
        self.start_btn.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold; padding: 10px;")
        button_layout.addWidget(self.start_btn)
        
        self.stop_btn = QPushButton("⏹ Stop")
        self.stop_btn.clicked.connect(self.on_stop_clicked)
        self.stop_btn.setEnabled(False)
        self.stop_btn.setStyleSheet("background-color: #f44336; color: white; font-weight: bold; padding: 10px;")
        button_layout.addWidget(self.stop_btn)
        
        # Quick audio toggle
        self.quick_audio_btn = QPushButton("🔊 Audio")
        self.quick_audio_btn.setCheckable(True)
        self.quick_audio_btn.setChecked(False)
        self.quick_audio_btn.clicked.connect(self.on_quick_audio_toggle)
        self.quick_audio_btn.setStyleSheet("padding: 10px;")
        button_layout.addWidget(self.quick_audio_btn)
        
        self.scan_btn = QPushButton("🔍 Scan")
        self.scan_btn.clicked.connect(self.on_scan_clicked)
        self.scan_btn.setStyleSheet("padding: 10px;")
        button_layout.addWidget(self.scan_btn)
        
        button_layout.addStretch()
        
        # Status indicators
        self.signal_indicator = QLabel("⚫ No Signal")
        button_layout.addWidget(self.signal_indicator)
        
        self.voice_indicator = QLabel("🔇 No Voice")
        button_layout.addWidget(self.voice_indicator)
        
        self.decrypt_indicator = QLabel("🔒 Encrypted: 0/0")
        button_layout.addWidget(self.decrypt_indicator)
        
        layout.addLayout(button_layout)
        
        group.setLayout(layout)
        return group
    
    def create_spectrum_display(self):
        """Create spectrum analyzer display."""
        group = QGroupBox("Spectrum Analyzer")
        layout = QVBoxLayout()
        
        # Create chart
        self.spectrum_series = QLineSeries()
        
        self.spectrum_chart = QChart()
        self.spectrum_chart.addSeries(self.spectrum_series)
        self.spectrum_chart.setTitle("Signal Spectrum")
        self.spectrum_chart.legend().hide()
        
        # Create axes
        self.spectrum_axis_x = QValueAxis()
        self.spectrum_axis_x.setTitleText("Frequency (MHz)")
        self.spectrum_axis_x.setRange(399, 401)
        
        self.spectrum_axis_y = QValueAxis()
        self.spectrum_axis_y.setTitleText("Power (dB)")
        self.spectrum_axis_y.setRange(-20, -100)  # Reversed range for correct orientation
        
        self.spectrum_chart.addAxis(self.spectrum_axis_x, Qt.AlignmentFlag.AlignBottom)
        self.spectrum_chart.addAxis(self.spectrum_axis_y, Qt.AlignmentFlag.AlignLeft)
        self.spectrum_series.attachAxis(self.spectrum_axis_x)
        self.spectrum_series.attachAxis(self.spectrum_axis_y)
        
        chart_view = QChartView(self.spectrum_chart)
        from PyQt6.QtGui import QPainter
        chart_view.setRenderHint(QPainter.RenderHint.Antialiasing)
        chart_view.setMinimumHeight(250)
        
        layout.addWidget(chart_view)
        
        group.setLayout(layout)
        return group
    
    def create_frames_table(self):
        """Create table for decoded frames."""
        table = QTableWidget()
        table.setColumnCount(8)
        table.setHorizontalHeaderLabels([
            "Time", "Frame #", "Type", "Description", "Encrypted", "Decrypted", "Key Used", "Data"
        ])
        table.setColumnWidth(0, 90)
        table.setColumnWidth(1, 70)
        table.setColumnWidth(2, 80)
        table.setColumnWidth(3, 150)
        table.setColumnWidth(4, 80)
        table.setColumnWidth(5, 80)
        table.setColumnWidth(6, 150)
        table.setColumnWidth(7, 250)
        
        return table
    
    def create_audio_panel(self):
        """Create audio control panel."""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Audio controls
        controls_layout = QHBoxLayout()
        
        self.audio_enable_cb = QCheckBox("Enable Audio Output")
        self.audio_enable_cb.setChecked(False)
        self.audio_enable_cb.stateChanged.connect(self.on_audio_enable_changed)
        controls_layout.addWidget(self.audio_enable_cb)
        
        controls_layout.addWidget(QLabel("Volume:"))
        self.volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.volume_slider.setMinimum(0)
        self.volume_slider.setMaximum(100)
        self.volume_slider.setValue(50)
        self.volume_slider.setMaximumWidth(200)
        controls_layout.addWidget(self.volume_slider)
        
        self.volume_label = QLabel("50%")
        self.volume_slider.valueChanged.connect(
            lambda v: self.volume_label.setText(f"{v}%")
        )
        controls_layout.addWidget(self.volume_label)
        
        controls_layout.addStretch()
        layout.addLayout(controls_layout)
        
        # Audio info
        info_text = QTextEdit()
        info_text.setReadOnly(True)
        info_text.setMaximumHeight(150)
        info_text.setHtml("""
        <h3>TETRA Audio Decoding</h3>
        <p><b>Note:</b> Real TETRA audio uses ACELP (Algebraic Code Excited Linear Prediction) codec
        which is proprietary and requires specialized decoding.</p>
        <p>This implementation provides basic FM demodulation as a placeholder.
        For actual voice decoding, you would need:</p>
        <ul>
        <li>ACELP decoder implementation</li>
        <li>Proper frame synchronization</li>
        <li>Voice channel identification</li>
        <li>Audio deinterleaving and error correction</li>
        </ul>
        <p>The audio output here is experimental and may not represent actual voice content.</p>
        """)
        layout.addWidget(info_text)
        
        widget.setLayout(layout)
        return widget
    
    def create_statistics_panel(self):
        """Create protocol statistics panel."""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Statistics text display
        self.stats_text = QTextEdit()
        self.stats_text.setReadOnly(True)
        self.stats_text.setFont(QFont("Courier", 10))
        layout.addWidget(self.stats_text)
        
        # Refresh button
        refresh_btn = QPushButton("Refresh Statistics")
        refresh_btn.clicked.connect(self.update_statistics_display)
        layout.addWidget(refresh_btn)
        
        widget.setLayout(layout)
        return widget
    
    def update_statistics_display(self):
        """Update statistics display."""
        if not self.capture_thread or not hasattr(self.capture_thread, 'decoder'):
            self.stats_text.setHtml("<h3>Statistics</h3><p>No active capture session</p>")
            return
        
        try:
            stats = self.capture_thread.decoder.protocol_parser.get_statistics()
            
            html = """
            <h2>📊 TETRA Protocol Statistics (OpenEar Style)</h2>
            <hr>
            
            <h3>🔵 PHY Layer (Bursts)</h3>
            <table style="width:100%; font-family: monospace;">
            <tr><td>Total Bursts:</td><td><b>{total_bursts}</b></td></tr>
            <tr><td>CRC Pass:</td><td style="color: green;"><b>{crc_pass}</b></td></tr>
            <tr><td>CRC Fail:</td><td style="color: red;"><b>{crc_fail}</b></td></tr>
            <tr><td>Success Rate:</td><td><b>{crc_success_rate:.1f}%</b></td></tr>
            </table>
            
            <h3>🔐 Encryption Status</h3>
            <table style="width:100%; font-family: monospace;">
            <tr><td>🔓 Clear Mode Frames:</td><td style="color: green;"><b>{clear_mode_frames}</b> ({clear_mode_percentage:.1f}%)</td></tr>
            <tr><td>🔒 Encrypted Frames:</td><td style="color: orange;"><b>{encrypted_frames}</b> ({encrypted_percentage:.1f}%)</td></tr>
            <tr><td>✅ Decrypted Frames:</td><td style="color: lightgreen;"><b>{decrypted_frames}</b></td></tr>
            </table>
            
            <h3>📡 Traffic Analysis</h3>
            <table style="width:100%; font-family: monospace;">
            <tr><td>📞 Voice Calls:</td><td><b>{voice_calls}</b></td></tr>
            <tr><td>💬 Data Messages:</td><td><b>{data_messages}</b></td></tr>
            <tr><td>🔧 Control Messages:</td><td><b>{control_messages}</b></td></tr>
            </table>
            
            <hr>
            <h3>🎯 Key Findings (OpenEar Methodology)</h3>
            <ul>
            """.format(**stats)
            
            # Add insights
            if stats['clear_mode_percentage'] > 50:
                html += "<li>✅ <b>Network runs primarily in CLEAR MODE</b> - No encryption on most traffic</li>"
            
            if stats['encrypted_frames'] > 0 and stats['decrypted_frames'] > 0:
                html += f"<li>🔓 <b>Weak encryption detected</b> - {stats['decrypted_frames']} frames decrypted with common keys</li>"
            
            if stats['voice_calls'] > 0:
                html += f"<li>📞 <b>{stats['voice_calls']} voice calls observed</b> - Metadata visible even if encrypted</li>"
            
            if stats['data_messages'] > 0:
                html += f"<li>💬 <b>{stats['data_messages']} SDS messages decoded</b> - Text visible in clear mode</li>"
            
            html += """
            </ul>
            
            <p><i>This demonstrates OpenEar-style analysis:</i></p>
            <ul>
            <li>✅ Decoding of clear-mode traffic (always unencrypted)</li>
            <li>✅ Metadata extraction (talkgroups, SSI, call patterns)</li>
            <li>✅ Network behavior analysis (encryption usage)</li>
            <li>✅ Weak key detection (TEA1 with common keys)</li>
            </ul>
            """
            
            self.stats_text.setHtml(html)
        except Exception as e:
            self.stats_text.setHtml(f"<h3>Statistics Error</h3><p>{e}</p>")
    
    
    def on_preset_changed(self, text):
        """Handle frequency preset change."""
        if "390.000" in text:
            self.freq_input.setText("390.000")
        elif "392.500" in text:
            self.freq_input.setText("392.500")
        elif "395.000" in text:
            self.freq_input.setText("395.000")
        elif "420.000" in text:
            self.freq_input.setText("420.000")
    
    def on_gain_changed(self, gain_text):
        """Handle gain change (live adjustment)."""
        if self.capture_thread and self.capture_thread.isRunning():
            try:
                gain = gain_text if gain_text == 'auto' else float(gain_text)
                self.capture_thread.set_gain(gain)
            except ValueError:
                pass
    
    def on_tune_clicked(self):
        """Handle tune button click."""
        try:
            freq_mhz = float(self.freq_input.text())
            freq_hz = freq_mhz * 1e6
            
            if self.capture_thread and self.capture_thread.isRunning():
                self.capture_thread.set_frequency(freq_hz)
                
                # Update spectrum axis
                self.spectrum_axis_x.setRange(freq_mhz - 1, freq_mhz + 1)
            else:
                self.log(f"Set frequency to {freq_mhz} MHz (will apply on start)")
        except ValueError:
            QMessageBox.warning(self, "Error", "Invalid frequency value")
    
    def on_load_keys(self):
        """Handle load keys button click."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Load Key File",
            "",
            "Key Files (*.txt);;All Files (*)"
        )
        
        if file_path:
            if self.capture_thread and self.capture_thread.isRunning():
                self.capture_thread.load_keys(file_path)
            else:
                self.log(f"Keys loaded from {file_path} (will apply on start)")
    
    def on_start_clicked(self):
        """Handle start button click."""
        try:
            # Get settings
            freq_mhz = float(self.freq_input.text())
            freq_hz = freq_mhz * 1e6
            
            gain = self.gain_input.currentText()
            if gain != 'auto':
                gain = float(gain)
            
            # Create and configure thread
            self.capture_thread = CaptureThread()
            self.capture_thread.frequency = freq_hz
            self.capture_thread.gain = gain
            self.capture_thread.auto_decrypt = self.auto_decrypt_cb.isChecked()
            
            # Connect signals
            self.capture_thread.signal_detected.connect(self.on_signal_detected)
            self.capture_thread.frame_decoded.connect(self.on_frame_decoded)
            self.capture_thread.audio_data.connect(self.on_audio_data)
            self.capture_thread.error_occurred.connect(self.on_error)
            self.capture_thread.status_update.connect(self.on_status_update)
            self.capture_thread.spectrum_update.connect(self.on_spectrum_update)
            
            # Update spectrum axis
            self.spectrum_axis_x.setRange(freq_mhz - 1, freq_mhz + 1)
            
            # Start thread
            self.capture_thread.start()
            
            # Update UI
            self.start_btn.setEnabled(False)
            self.stop_btn.setEnabled(True)
            self.log("Capture started")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to start capture: {e}")
    
    def on_stop_clicked(self):
        """Handle stop button click."""
        if self.capture_thread:
            self.capture_thread.stop()
            self.capture_thread.wait()
            self.capture_thread = None
        
        # Stop audio
        if self.audio_stream:
            self.audio_stream.stop()
            self.audio_stream.close()
            self.audio_stream = None
        
        # Update UI
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.signal_indicator.setText("⚫ No Signal")
        self.log("Capture stopped")
    
    def on_scan_clicked(self):
        """Handle scan button click."""
        # TODO: Implement frequency scanning in separate dialog
        QMessageBox.information(
            self,
            "Scan",
            "Frequency scanning feature coming soon!\n\n"
            "For now, use the command line:\n"
            "python tetra_decoder_main.py --scan-poland"
        )
    
    def on_quick_audio_toggle(self):
        """Quick audio on/off toggle."""
        if self.quick_audio_btn.isChecked():
            self.audio_enable_cb.setChecked(True)
            self.quick_audio_btn.setText("🔊 Audio ON")
            self.quick_audio_btn.setStyleSheet("background-color: #4CAF50; color: white; padding: 10px;")
        else:
            self.audio_enable_cb.setChecked(False)
            self.quick_audio_btn.setText("🔇 Audio OFF")
            self.quick_audio_btn.setStyleSheet("padding: 10px;")
    
    def on_audio_enable_changed(self, state):
        """Handle audio enable checkbox change."""
        if state == Qt.CheckState.Checked.value:
            self.start_audio_stream()
        else:
            if self.audio_stream:
                self.audio_stream.stop()
                self.audio_stream.close()
                self.audio_stream = None
    
    def start_audio_stream(self):
        """Start audio output stream."""
        try:
            self.audio_stream = sd.OutputStream(
                samplerate=8000,
                channels=1,
                callback=self.audio_callback,
                blocksize=1024
            )
            self.audio_stream.start()
            self.log("Audio output started")
        except Exception as e:
            self.log(f"Failed to start audio: {e}")
            self.audio_enable_cb.setChecked(False)
    
    def audio_callback(self, outdata, frames, time, status):
        """Audio stream callback."""
        try:
            if not self.audio_buffer.empty():
                data = self.audio_buffer.get_nowait()
                volume = self.volume_slider.value() / 100.0
                
                # Take only what we need
                if len(data) >= frames:
                    outdata[:] = (data[:frames] * volume).reshape(-1, 1)
                else:
                    outdata[:len(data)] = (data * volume).reshape(-1, 1)
                    outdata[len(data):] = 0
            else:
                outdata[:] = 0
        except:
            outdata[:] = 0
    
    @pyqtSlot(float, float)
    def on_signal_detected(self, frequency, power):
        """Handle signal detection."""
        self.signal_indicator.setText(f"🟢 Signal: {power:.1f} dB")
        self.signal_indicator.setStyleSheet("color: green; font-weight: bold;")
    
    @pyqtSlot(dict)
    def on_frame_decoded(self, frame):
        """Handle decoded frame."""
        self.frame_count += 1
        
        if frame.get('decrypted'):
            self.decrypted_count += 1
        
        # Update decrypt indicator
        if frame.get('encrypted'):
            self.decrypt_indicator.setText(
                f"🔒 Encrypted: {self.decrypted_count}/{self.frame_count}"
            )
        
        # Add to table
        row = self.frames_table.rowCount()
        self.frames_table.insertRow(row)
        
        time_str = datetime.now().strftime("%H:%M:%S")
        self.frames_table.setItem(row, 0, QTableWidgetItem(time_str))
        self.frames_table.setItem(row, 1, QTableWidgetItem(str(frame['number'])))
        
        # Frame type with name
        frame_type = frame['type']
        frame_type_names = {
            0: "Broadcast",
            1: "Traffic",
            2: "Control",
            3: "MAC"
        }
        type_name = frame_type_names.get(frame_type, f"Type {frame_type}")
        self.frames_table.setItem(row, 2, QTableWidgetItem(type_name))
        
        # Description with emoji and additional info
        descriptions = {
            0: "📡 System info",
            1: "📞 Voice/Data",
            2: "🔗 Signaling",
            3: "📋 MAC Control"
        }
        desc = descriptions.get(frame_type, "Unknown")
        
        # Add additional parsed info to description
        if 'additional_info' in frame:
            info = frame['additional_info']
            
            # Talkgroup ID
            if 'talkgroup' in info:
                desc += f" | TG:{info['talkgroup']}"
            
            # Source SSI
            if 'source_ssi' in info:
                desc += f" | SSI:{info['source_ssi']}"
            
            # SDS text message
            if 'sds_text' in info:
                desc += f" | 💬 {info['sds_text']}"
            
            # Legacy fields
            if 'channel' in info:
                desc += f" ({info['channel']})"
            elif 'control' in info:
                desc += f" - {info['control']}"
            elif 'network_id' in info:
                desc += f" (Net:{info['network_id']})"
        
        self.frames_table.setItem(row, 3, QTableWidgetItem(desc))
        
        self.frames_table.setItem(row, 4, QTableWidgetItem("Yes" if frame.get('encrypted') else "No"))
        
        # Decrypted column with confidence indicator (more lenient thresholds)
        decrypted_text = ""
        if frame.get('decrypted'):
            confidence = frame.get('decrypt_confidence', 0)
            if confidence > 80:
                decrypted_text = "✓ Yes"
            elif confidence > 30:
                decrypted_text = "⚠ Maybe"
            elif confidence > 10:
                decrypted_text = "? Weak"
            else:
                decrypted_text = "? Unsure"
        else:
            decrypted_text = "No" if frame.get('encrypted') else "-"
        
        self.frames_table.setItem(row, 5, QTableWidgetItem(decrypted_text))
        self.frames_table.setItem(row, 6, QTableWidgetItem(frame.get('key_used', '')))
        
        # Show meaningful data
        data_str = ""
        if frame.get('decrypted') and 'decrypted_bytes' in frame:
            confidence = frame.get('decrypt_confidence', 0)
            payload_hex = frame['decrypted_bytes'][:64]  # First 64 chars
            
            # Try to show as text if printable
            try:
                payload_bytes = bytes.fromhex(payload_hex)
                # Count printable characters
                printable_count = sum(1 for b in payload_bytes if 32 <= b <= 126)
                
                # If >50% printable, show as text
                if printable_count > len(payload_bytes) * 0.5:
                    data_str = payload_bytes.decode('ascii', errors='replace')
                    # Clean up unprintable
                    data_str = ''.join(c if 32 <= ord(c) <= 126 else '·' for c in data_str)
                else:
                    # Show as hex with confidence indicator
                    if confidence > 200:
                        data_str = payload_hex + " (high conf)"
                    elif confidence > 100:
                        data_str = payload_hex + " (med conf)"
                    else:
                        data_str = payload_hex + " (low conf)"
            except:
                data_str = payload_hex
        elif not frame.get('encrypted'):
            # Not encrypted - show raw payload
            if len(frame['bits']) > 32:
                payload_bits = frame['bits'][32:160]  # Next 128 bits
                try:
                    ba = BitArray(payload_bits)
                    data_str = ba.hex[:32] + "..."
                except:
                    data_str = "(parse error)"
        else:
            # Encrypted but not decrypted
            data_str = "(encrypted)"
        
        self.frames_table.setItem(row, 7, QTableWidgetItem(data_str))
        
        # Color code encrypted/decrypted
        if frame.get('encrypted'):
            if frame.get('decrypted'):
                # Decrypted - green
                for col in range(8):
                    item = self.frames_table.item(row, col)
                    if item:
                        item.setBackground(QColor(200, 255, 200))
                        item.setForeground(QColor(0, 0, 0))  # Black text
            else:
                # Encrypted but not decrypted - yellow
                for col in range(8):
                    item = self.frames_table.item(row, col)
                    if item:
                        item.setBackground(QColor(255, 255, 150))
                        item.setForeground(QColor(0, 0, 0))  # Black text
        
        # Scroll to bottom only if autoscroll enabled
        if self.autoscroll_cb.isChecked():
            self.frames_table.scrollToBottom()
        
        # Limit table size
        if self.frames_table.rowCount() > 1000:
            self.frames_table.removeRow(0)
        
        # Log with meaningful info
        log_msg = f"Frame #{frame['number']} ({type_name}) - "
        log_msg += f"{desc} - "
        
        # Add protocol layer info if available
        if 'call_metadata' in frame:
            meta = frame['call_metadata']
            if meta['talkgroup_id']:
                log_msg += f"TG:{meta['talkgroup_id']} "
            if meta['source_ssi']:
                log_msg += f"SSI:{meta['source_ssi']} "
            if not meta['encryption']:
                log_msg += "🔓 CLEAR MODE "
        
        log_msg += f"Encrypted: {frame.get('encrypted', False)}"
        if frame.get('encrypted'):
            log_msg += f", Decrypted: {frame.get('decrypted', False)}"
            if frame.get('decrypted') and 'key_used' in frame:
                log_msg += f" [{frame['key_used']}]"
        
        # Add SDS message if present
        if 'sds_message' in frame:
            log_msg += f"\n    💬 SDS: {frame['sds_message']}"
        
        self.log(log_msg)
    
    @pyqtSlot(np.ndarray)
    def on_audio_data(self, audio):
        """Handle audio data with voice activity indication."""
        if self.audio_enable_cb.isChecked():
            # Calculate audio energy for voice activity
            energy = np.sum(audio**2) / len(audio)
            
            # Update voice indicator based on energy
            if energy > 0.01:  # Voice threshold
                self.voice_indicator.setText("🔊 Voice Active")
                self.voice_indicator.setStyleSheet("color: green; font-weight: bold;")
            else:
                self.voice_indicator.setText("🔇 No Voice")
                self.voice_indicator.setStyleSheet("color: gray;")
            
            try:
                if not self.audio_buffer.full():
                    self.audio_buffer.put_nowait(audio)
            except:
                pass
        else:
            self.voice_indicator.setText("🔇 Audio Off")
            self.voice_indicator.setStyleSheet("color: gray;")
    
    @pyqtSlot(str)
    def on_error(self, message):
        """Handle error message."""
        self.log(f"ERROR: {message}", color="red")
        self.statusBar().showMessage(f"Error: {message}", 5000)
    
    @pyqtSlot(str)
    def on_status_update(self, message):
        """Handle status update."""
        self.log(message)
        self.statusBar().showMessage(message, 3000)
    
    @pyqtSlot(np.ndarray, np.ndarray)
    def on_spectrum_update(self, freqs, powers):
        """Handle spectrum update with proper dynamic range."""
        try:
            self.spectrum_series.clear()
            
            # Make sure we have valid data
            if len(freqs) > 0 and len(powers) > 0:
                # Filter valid points only
                valid_points = []
                for f, p in zip(freqs, powers):
                    if not np.isnan(f) and not np.isnan(p) and np.isfinite(f) and np.isfinite(p):
                        valid_points.append((float(f / 1e6), float(p)))
                
                if not valid_points:
                    return
                
                # Add points to series
                for f, p in valid_points:
                    self.spectrum_series.append(f, p)
                
                # Calculate dynamic range from actual data
                freqs_mhz = [f for f, _ in valid_points]
                powers_db = [p for _, p in valid_points]
                
                # Frequency range with margin
                freq_min = min(freqs_mhz)
                freq_max = max(freqs_mhz)
                freq_margin = (freq_max - freq_min) * 0.05  # 5% margin
                self.spectrum_axis_x.setRange(freq_min - freq_margin, freq_max + freq_margin)
                
                # Power range with adaptive scaling
                power_min = np.percentile(powers_db, 5)   # 5th percentile (noise floor)
                power_max = np.percentile(powers_db, 95)  # 95th percentile (signal peaks)
                
                # Ensure minimum dynamic range of 30 dB
                if (power_max - power_min) < 30:
                    center = (power_max + power_min) / 2
                    power_min = center - 15
                    power_max = center + 15
                
                # Add margins
                power_range = power_max - power_min
                margin = power_range * 0.15  # 15% margin
                
                # Set range (reversed for correct orientation - high at top)
                self.spectrum_axis_y.setRange(power_max + margin, power_min - margin)
                
        except Exception as e:
            self.log(f"Spectrum update error: {e}", color="red")
    
    def update_displays(self):
        """Update displays periodically."""
        # Update frame counter in status bar
        self.statusBar().showMessage(
            f"Frames: {self.frame_count} | "
            f"Decrypted: {self.decrypted_count}",
            0  # Permanent message
        )
    
    def log(self, message, color=None):
        """Add message to log."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted = f"[{timestamp}] {message}"
        
        if color:
            formatted = f'<span style="color: {color};">{formatted}</span>'
        
        self.log_text.append(formatted)
        
        # Auto-scroll
        scrollbar = self.log_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
    def closeEvent(self, event):
        """Handle window close."""
        if self.capture_thread and self.capture_thread.isRunning():
            self.capture_thread.stop()
            self.capture_thread.wait()
        
        if self.audio_stream:
            self.audio_stream.stop()
            self.audio_stream.close()
        
        event.accept()


def main():
    """Main entry point."""
    app = QApplication(sys.argv)
    
    # Set application style
    app.setStyle('Fusion')
    
    # Dark palette
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor(53, 53, 53))
    palette.setColor(QPalette.ColorRole.WindowText, Qt.GlobalColor.white)
    palette.setColor(QPalette.ColorRole.Base, QColor(35, 35, 35))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor(53, 53, 53))
    palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(25, 25, 25))
    palette.setColor(QPalette.ColorRole.ToolTipText, Qt.GlobalColor.white)
    palette.setColor(QPalette.ColorRole.Text, Qt.GlobalColor.white)
    palette.setColor(QPalette.ColorRole.Button, QColor(53, 53, 53))
    palette.setColor(QPalette.ColorRole.ButtonText, Qt.GlobalColor.white)
    palette.setColor(QPalette.ColorRole.BrightText, Qt.GlobalColor.red)
    palette.setColor(QPalette.ColorRole.Link, QColor(42, 130, 218))
    palette.setColor(QPalette.ColorRole.Highlight, QColor(42, 130, 218))
    palette.setColor(QPalette.ColorRole.HighlightedText, Qt.GlobalColor.black)
    
    app.setPalette(palette)
    
    window = TetraGUI()
    window.show()
    
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
