#!/usr/bin/env python3
"""
Simple Curve Viewer - Uses minimal SQLite database
Displays hyperbolic curve T = a/R + b with data points from database
Includes file monitoring daemon for raceresults.txt (runs silently in background)
Includes Autopilot mode for automatic AIW ratio adjustment
Shows both Qualifying and Race curves on the same graph
"""

import sys
import threading
import logging
from pathlib import Path
from typing import List, Tuple, Optional, Dict, Any
from datetime import datetime

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout, QSplitter,
    QLabel, QPushButton, QTextEdit, QDialog, QVBoxLayout, QTabWidget,
    QCheckBox, QSpinBox, QGroupBox, QComboBox
)
from PyQt5.QtCore import Qt, pyqtSignal, QObject
import pyqtgraph as pg
import numpy as np

from db_funcs import CurveDatabase
from formula_funcs import fit_curve, calculate_derived_values, get_formula_string
from gui_funcs import (
    create_control_panel, setup_dark_theme, show_error_dialog, 
    show_info_dialog, show_warning_dialog, MultiTrackSelectionDialog
)
from cfg_funcs import (
    get_config_with_defaults, get_results_file_path, get_poll_interval,
    get_db_path, create_default_config_if_missing, get_base_path,
    get_autopilot_enabled, get_autopilot_silent,
    update_autopilot_enabled, update_autopilot_silent
)
from data_extraction import DataExtractor, RaceData
from autopilot import AutopilotManager, Formula


# Set up logging
logger = logging.getLogger(__name__)


class LogWindow(QDialog):
    """Separate window for displaying logs on demand"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Live AI Tuner - Log Viewer")
        self.setGeometry(200, 200, 800, 500)
        
        self.log_buffer = []
        self.max_lines = 1000
        self.current_level = "INFO"
        
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Controls at top
        control_layout = QHBoxLayout()
        
        # Log level filter
        control_layout.addWidget(QLabel("Show level:"))
        self.level_combo = QComboBox()
        self.level_combo.addItems(["ERROR", "WARNING", "INFO", "DEBUG", "ALL"])
        self.level_combo.setCurrentText("INFO")
        self.level_combo.currentTextChanged.connect(self.on_level_changed)
        control_layout.addWidget(self.level_combo)
        
        control_layout.addWidget(QLabel("Max lines:"))
        self.max_lines_spin = QSpinBox()
        self.max_lines_spin.setRange(100, 10000)
        self.max_lines_spin.setValue(1000)
        self.max_lines_spin.valueChanged.connect(self.on_max_lines_changed)
        control_layout.addWidget(self.max_lines_spin)
        
        control_layout.addStretch()
        
        # Clear button
        self.clear_btn = QPushButton("Clear")
        self.clear_btn.clicked.connect(self.clear_log)
        control_layout.addWidget(self.clear_btn)
        
        # Auto-scroll checkbox
        self.auto_scroll_cb = QCheckBox("Auto-scroll")
        self.auto_scroll_cb.setChecked(True)
        control_layout.addWidget(self.auto_scroll_cb)
        
        layout.addLayout(control_layout)
        
        # Log text area
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFontFamily("Courier New")
        self.log_text.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #d4d4d4;
                font-size: 10px;
            }
        """)
        layout.addWidget(self.log_text)
        
    def add_log(self, level: str, message: str):
        """Add a log message to the buffer and display"""
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        formatted = f"[{timestamp}] [{level:7}] {message}"
        
        self.log_buffer.append((level, formatted))
        
        # Trim buffer
        if len(self.log_buffer) > self.max_lines:
            self.log_buffer = self.log_buffer[-self.max_lines:]
        
        # Update display if level matches filter
        self._update_display()
        
    def _update_display(self):
        """Update the display based on current filter"""
        level_map = {
            "ERROR": 40,
            "WARNING": 30,
            "INFO": 20,
            "DEBUG": 10,
            "ALL": 0
        }
        min_level = level_map.get(self.current_level, 20)
        
        level_values = {
            "ERROR": 40,
            "WARNING": 30,
            "INFO": 20,
            "DEBUG": 10
        }
        
        # Color mapping
        color_map = {
            "ERROR": "#f44336",
            "WARNING": "#ff9800",
            "INFO": "#4caf50",
            "DEBUG": "#9e9e9e"
        }
        
        html_lines = []
        for level, formatted in self.log_buffer:
            if self.current_level == "ALL" or level_values.get(level, 0) >= min_level:
                color = color_map.get(level, "#ffffff")
                html_lines.append(f'<span style="color: {color};">{formatted}</span>')
        
        if self.auto_scroll_cb.isChecked():
            self.log_text.setHtml("<br>".join(html_lines))
            # Scroll to bottom
            scrollbar = self.log_text.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())
        else:
            self.log_text.setHtml("<br>".join(html_lines))
        
    def on_level_changed(self, level: str):
        """Handle log level change"""
        self.current_level = level
        self._update_display()
        
    def on_max_lines_changed(self, value: int):
        """Handle max lines change"""
        self.max_lines = value
        if len(self.log_buffer) > self.max_lines:
            self.log_buffer = self.log_buffer[-self.max_lines:]
        self._update_display()
        
    def clear_log(self):
        """Clear the log buffer and display"""
        self.log_buffer.clear()
        self.log_text.clear()


class LogHandler(logging.Handler):
    """Custom logging handler that sends logs to the GUI window"""
    
    def __init__(self, log_window: LogWindow):
        super().__init__()
        self.log_window = log_window
        
    def emit(self, record):
        try:
            level = record.levelname
            message = self.format(record)
            self.log_window.add_log(level, message)
        except Exception:
            pass


class FileChangeSignal(QObject):
    """Signal for thread-safe GUI updates"""
    file_changed = pyqtSignal(object)


class FileMonitorDaemon(QObject):
    """Daemon that monitors a file for changes and extracts data"""
    
    def __init__(self, file_path: Path, base_path: Path, poll_interval: float = 5.0):
        super().__init__()
        self.file_path = file_path
        self.base_path = base_path
        self.poll_interval = poll_interval
        self.running = False
        self.last_mtime = None
        self.last_size = None
        self.timer = None
        self.signal = FileChangeSignal()
        self.extractor = DataExtractor(base_path)
        
    def start(self):
        """Start monitoring"""
        if not self.file_path.exists():
            logger.warning(f"File does not exist yet: {self.file_path}")
            self.file_path.parent.mkdir(parents=True, exist_ok=True)
        
        self._update_file_state()
        self.running = True
        self._schedule_check()
        logger.info(f"Started monitoring: {self.file_path}")
        logger.info(f"Poll interval: {self.poll_interval} seconds")
        
    def stop(self):
        """Stop monitoring"""
        self.running = False
        if self.timer:
            self.timer.cancel()
        logger.info("Stopped monitoring")
    
    def _schedule_check(self):
        """Schedule the next file check"""
        if self.running:
            self.timer = threading.Timer(self.poll_interval, self._check_file)
            self.timer.daemon = True
            self.timer.start()
    
    def _update_file_state(self):
        """Update stored file state"""
        try:
            if self.file_path.exists():
                stat = self.file_path.stat()
                self.last_mtime = stat.st_mtime
                self.last_size = stat.st_size
        except Exception:
            pass
    
    def _check_file(self):
        """Check if file has changed and extract data"""
        try:
            if not self.running:
                return
            
            if not self.file_path.exists():
                self._schedule_check()
                return
            
            try:
                stat = self.file_path.stat()
                current_mtime = stat.st_mtime
                current_size = stat.st_size
            except OSError:
                self._schedule_check()
                return
            
            changed = (
                self.last_mtime is None
                or current_mtime != self.last_mtime
                or current_size != self.last_size
            )
            
            if changed:
                race_data = self.extractor.parse_race_results(self.file_path)
                if race_data and race_data.has_data():
                    self.signal.file_changed.emit(race_data)
                else:
                    self.signal.file_changed.emit(None)
                
                self.last_mtime = current_mtime
                self.last_size = current_size
            
        except Exception as e:
            logger.error(f"Error checking file: {e}")
        finally:
            self._schedule_check()


class SimpleCurveViewer(QMainWindow):
    """Lightweight GUI for viewing hyperbolic curves"""
    
    def __init__(self, db_path: str = "ai_data.db", config_file: str = "cfg.yml"):
        super().__init__()
        self.setWindowTitle("Live AI Tuner - Curve Viewer")
        self.setGeometry(100, 100, 1200, 700)
        
        # Config
        self.config_file = config_file
        self.config = get_config_with_defaults(config_file)
        
        # Database handler
        self.db = CurveDatabase(db_path)
        
        # Set up log window
        self.log_window = LogWindow(self)
        log_handler = LogHandler(self.log_window)
        log_handler.setFormatter(logging.Formatter('%(message)s'))
        logging.getLogger().addHandler(log_handler)
        logging.getLogger().setLevel(logging.DEBUG)
        
        # Autopilot
        self.autopilot_manager = AutopilotManager(self.db)
        self.autopilot_enabled = get_autopilot_enabled(config_file)
        self.autopilot_silent = get_autopilot_silent(config_file)
        self.autopilot_manager.set_enabled(self.autopilot_enabled)
        self.autopilot_manager.set_silent(self.autopilot_silent)
        
        # Current formulas (updated by autopilot or manual fit)
        self.qual_a: float = 30.0
        self.qual_b: float = 70.0
        self.race_a: float = 30.0
        self.race_b: float = 70.0
        self.formula_source: str = "Default"
        
        # Filter state
        self.show_qualifying: bool = True
        self.show_race: bool = True
        self.show_unknown: bool = True
        
        # Currently selected curve for manual editing
        self.selected_curve = "qual"  # "qual" or "race"
        
        # Track selection state
        self.current_track: str = ""
        self.multi_track_mode: bool = False
        self.selected_tracks: List[str] = []
        
        # Cache for tracks and vehicles
        self.all_tracks: List[str] = []
        self.all_vehicles: List[str] = []
        
        # Daemon
        self.daemon = None
        
        self.setup_ui()
        self.load_data()
        self.update_display()
        self.update_manual_controls()
        
        # Auto-start daemon if base path is configured
        base_path = get_base_path(config_file)
        if base_path:
            self.start_daemon()
    
    def setup_ui(self):
        """Setup the user interface"""
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(5, 5, 5, 5)
        
        # Create control panel
        controls = create_control_panel(self)
        self.controls = controls
        
        # Store references to controls
        self.track_list = controls['track_list']  # Hidden, kept for compatibility
        self.current_track_display = controls['current_track_display']
        self.multi_track_btn = controls['multi_track_btn']
        self.vehicle_list = controls['vehicle_list']
        self.qual_btn = controls['qual_btn']
        self.race_btn = controls['race_btn']
        self.unkn_btn = controls['unkn_btn']
        self.stats_label = controls['stats_label']
        
        # Manual curve controls
        self.curve_selector = controls.get('curve_selector')
        self.current_formula_label = controls.get('current_formula_label')
        self.a_spin = controls['a_spin']
        self.b_spin = controls['b_spin']
        self.k_label = controls['k_label']
        self.m_label = controls['m_label']
        self.apply_btn = controls.get('apply_btn')
        
        # Connect manual curve signals
        if self.curve_selector:
            self.curve_selector.currentIndexChanged.connect(self.on_curve_selected)
        if self.apply_btn:
            self.apply_btn.clicked.connect(self.on_apply_manual_curve)
        
        # Connect track selection signals
        self.multi_track_btn.clicked.connect(self.open_multi_track_dialog)
        
        # Autopilot controls
        self.autopilot_enable_btn = controls.get('autopilot_enable_btn')
        self.autopilot_silent_btn = controls.get('autopilot_silent_btn')
        self.autopilot_status_label = controls.get('autopilot_status')
        
        # Connect signals
        self.vehicle_list.itemSelectionChanged.connect(self.on_selection_changed)
        self.qual_btn.clicked.connect(self.on_filter_buttons)
        self.race_btn.clicked.connect(self.on_filter_buttons)
        self.unkn_btn.clicked.connect(self.on_filter_buttons)
        controls['fit_btn'].clicked.connect(self.auto_fit)
        controls['reset_btn'].clicked.connect(self.reset_view)
        controls['exit_btn'].clicked.connect(self.close)
        controls['select_all_vehicles'].clicked.connect(lambda: self.vehicle_list.selectAll())
        controls['clear_vehicles'].clicked.connect(lambda: self.vehicle_list.clearSelection())
        
        # Connect autopilot signals
        if self.autopilot_enable_btn:
            self.autopilot_enable_btn.setChecked(self.autopilot_enabled)
            self.autopilot_enable_btn.clicked.connect(self.toggle_autopilot)
            self._update_autopilot_button_text()
        
        if self.autopilot_silent_btn:
            self.autopilot_silent_btn.setChecked(self.autopilot_silent)
            self.autopilot_silent_btn.clicked.connect(self.toggle_autopilot_silent)
        
        self._update_autopilot_status()
        
        # Add Log button to control panel
        log_btn = QPushButton("Show Log Window")
        log_btn.setStyleSheet("background-color: #2196F3;")
        controls['panel'].layout().insertWidget(controls['panel'].layout().count() - 2, log_btn)
        log_btn.clicked.connect(self.show_log_window)
        
        # Create plot widget
        self.plot_widget = pg.GraphicsLayoutWidget()
        self.plot_widget.setBackground('#2b2b2b')
        self.plot = self.plot_widget.addPlot()
        self.plot.setLabel('bottom', 'Ratio (R)', color='white', size='11pt')
        self.plot.setLabel('left', 'Lap Time (seconds)', color='white', size='11pt')
        self.plot.setTitle('Hyperbolic Curves: T = a / R + b', color='#FFA500', size='12pt')
        self.plot.showGrid(x=True, y=True, alpha=0.3)
        self.plot.setXRange(0.4, 2.0)
        self.plot.setYRange(50, 200)
        
        # Style axes
        self.plot.getAxis('bottom').setPen('white')
        self.plot.getAxis('bottom').setTextPen('white')
        self.plot.getAxis('left').setPen('white')
        self.plot.getAxis('left').setTextPen('white')
        
        # Store plot items
        self.qual_curve = None
        self.race_curve = None
        self.qual_scatter = None
        self.race_scatter = None
        self.unknown_scatter = None
        self.legend = None
        
        # Splitter
        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(controls['panel'])
        splitter.addWidget(self.plot_widget)
        splitter.setSizes([340, 860])
        main_layout.addWidget(splitter)
    
    def open_multi_track_dialog(self):
        """Open dialog to select multiple tracks"""
        if not self.all_tracks:
            show_warning_dialog(self, "No Tracks", "No tracks found in database.")
            return
        
        dialog = MultiTrackSelectionDialog(self.all_tracks, self.current_track, self)
        if dialog.exec_() == QDialog.Accepted:
            selected = dialog.get_selected_tracks()
            if selected:
                self.selected_tracks = selected
                self.multi_track_mode = len(selected) > 1
                self.current_track = selected[0] if selected else ""
                self.update_track_display()
                self.on_selection_changed()
    
    def update_track_display(self):
        """Update the track display label"""
        if self.multi_track_mode and len(self.selected_tracks) > 1:
            self.current_track_display.setText(f"{len(self.selected_tracks)} tracks selected")
            self.current_track_display.setStyleSheet("color: #FF9800; font-family: monospace; font-weight: bold;")
        elif self.current_track:
            self.current_track_display.setText(self.current_track)
            self.current_track_display.setStyleSheet("color: #4CAF50; font-family: monospace; font-weight: bold;")
        else:
            self.current_track_display.setText("-")
            self.current_track_display.setStyleSheet("color: #888; font-family: monospace;")
    
    def get_selected_tracks(self) -> List[str]:
        """Get the list of selected tracks"""
        if self.multi_track_mode and self.selected_tracks:
            return self.selected_tracks
        elif self.current_track:
            return [self.current_track]
        return []
    
    def show_log_window(self):
        """Show the log window"""
        self.log_window.show()
        self.log_window.raise_()
    
    def _update_autopilot_button_text(self):
        """Update the autopilot button text based on state"""
        if self.autopilot_enable_btn:
            if self.autopilot_enabled:
                self.autopilot_enable_btn.setText("Autopilot is ON")
                self.autopilot_enable_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #4CAF50;
                        color: white;
                        font-weight: bold;
                    }
                    QPushButton:checked {
                        background-color: #FF9800;
                    }
                """)
            else:
                self.autopilot_enable_btn.setText("Autopilot is OFF")
                self.autopilot_enable_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #555;
                        color: white;
                    }
                    QPushButton:checked {
                        background-color: #FF9800;
                    }
                """)
    
    def _update_autopilot_status(self):
        """Update autopilot status label"""
        if self.autopilot_status_label:
            if self.autopilot_enabled:
                count = self.autopilot_manager.formula_manager.get_formula_count()
                self.autopilot_status_label.setText(f"Status: Active ({count} formulas)")
                self.autopilot_status_label.setStyleSheet("color: #4CAF50; font-size: 10px;")
            else:
                self.autopilot_status_label.setText("Status: Disabled")
                self.autopilot_status_label.setStyleSheet("color: #888; font-size: 10px;")
    
    def update_manual_controls(self):
        """Update the manual control panel with current formula values"""
        if self.selected_curve == "qual":
            a = self.qual_a
            b = self.qual_b
            curve_name = "Qualifying"
            color = "#FFFF00"
        else:
            a = self.race_a
            b = self.race_b
            curve_name = "Race"
            color = "#FF6600"
        
        # Update spin boxes without triggering signals
        self.a_spin.blockSignals(True)
        self.b_spin.blockSignals(True)
        self.a_spin.setValue(a)
        self.b_spin.setValue(b)
        self.a_spin.blockSignals(False)
        self.b_spin.blockSignals(False)
        
        # Update formula display
        formula_str = get_formula_string(a, b)
        self.current_formula_label.setText(f"Current {curve_name}: {formula_str}")
        self.current_formula_label.setStyleSheet(f"color: {color}; font-family: monospace; font-size: 11px;")
        
        # Update derived values
        M = a + b
        k = a / M if M > 0 else 0
        self.m_label.setText(f"Time at R=1.0 = a+b = {M:.3f}s")
        self.k_label.setText(f"Steepness k = a/(a+b) = {k:.3f}")
    
    def on_curve_selected(self, index):
        """Handle curve selector change"""
        self.selected_curve = self.curve_selector.currentData()
        self.update_manual_controls()
    
    def on_apply_manual_curve(self):
        """Apply manually edited curve parameters"""
        a = self.a_spin.value()
        b = self.b_spin.value()
        
        if self.selected_curve == "qual":
            self.qual_a = a
            self.qual_b = b
            logger.info(f"Manually updated qualifying curve: {get_formula_string(a, b)}")
        else:
            self.race_a = a
            self.race_b = b
            logger.info(f"Manually updated race curve: {get_formula_string(a, b)}")
        
        self.formula_source = "Manual Edit"
        self.update_manual_controls()
        self.update_display()
    
    def toggle_autopilot(self):
        """Toggle autopilot mode"""
        self.autopilot_enabled = not self.autopilot_enabled
        self.autopilot_manager.set_enabled(self.autopilot_enabled)
        update_autopilot_enabled(self.autopilot_enabled, self.config_file)
        
        self._update_autopilot_button_text()
        self._update_autopilot_status()
        
        status = "ENABLED" if self.autopilot_enabled else "DISABLED"
        logger.info(f"Autopilot {status}")
        self.statusBar().showMessage(f"Autopilot {status}", 3000)
        
        if self.autopilot_enabled:
            self.autopilot_manager.reload_formulas()
            self._update_formulas_from_autopilot()
            count = self.autopilot_manager.formula_manager.get_formula_count()
            logger.info(f"Autopilot enabled with {count} stored formulas")
            self.update_display()
            self.update_manual_controls()
    
    def toggle_autopilot_silent(self):
        """Toggle autopilot silent mode"""
        self.autopilot_silent = not self.autopilot_silent
        self.autopilot_manager.set_silent(self.autopilot_silent)
        update_autopilot_silent(self.autopilot_silent, self.config_file)
        
        mode = "SILENT" if self.autopilot_silent else "VERBOSE"
        logger.info(f"Autopilot {mode} mode")
        self.statusBar().showMessage(f"Autopilot {mode} mode", 2000)
    
    def start_daemon(self):
        """Start the file monitoring daemon"""
        file_path = get_results_file_path(self.config_file)
        if not file_path:
            logger.warning("No base path configured - daemon not started")
            return
        
        base_path = get_base_path(self.config_file)
        if not base_path:
            logger.warning("Base path not configured - daemon not started")
            return
        
        poll_interval = get_poll_interval(self.config_file)
        
        self.daemon = FileMonitorDaemon(file_path, base_path, poll_interval)
        self.daemon.signal.file_changed.connect(self.on_file_changed)
        self.daemon.start()
        logger.info(f"Daemon started - monitoring: {file_path}")
    
    def stop_daemon(self):
        """Stop the file monitoring daemon"""
        if self.daemon:
            self.daemon.stop()
            self.daemon = None
    
    def _update_formulas_from_autopilot(self):
        """Update current formulas from autopilot for selected track/vehicle"""
        selected_tracks = self.get_selected_tracks()
        selected_vehicles = [item.text() for item in self.vehicle_list.selectedItems()]
        
        if not selected_tracks or not selected_vehicles:
            return
        
        # For multi-track mode, use the first track for formula selection
        track = selected_tracks[0]
        vehicle = selected_vehicles[0]
        
        logger.debug(f"Updating formulas from autopilot for {track}/{vehicle}")
        
        # Get qualifying formula - try exact match first
        qual_formula = self.autopilot_manager.formula_manager.get_formula(track, vehicle, "qual")
        
        # If no exact match, try to get ANY qualifying formula for this track
        if not qual_formula:
            track_formulas = self.autopilot_manager.formula_manager.get_all_formulas_for_track(track)
            for f in track_formulas:
                if f.session_type == "qual" and f.is_valid():
                    qual_formula = f
                    logger.info(f"Using fallback qualifying formula from class '{f.vehicle_class}'")
                    break
        
        if qual_formula and qual_formula.is_valid():
            self.qual_a = qual_formula.a
            self.qual_b = qual_formula.b
            self.formula_source = f"Autopilot ({qual_formula.vehicle_class})"
            logger.debug(f"QUALIFYING formula loaded: {qual_formula.get_formula_string()}")
        
        # Get race formula - try exact match first
        race_formula = self.autopilot_manager.formula_manager.get_formula(track, vehicle, "race")
        
        # If no exact match, try to get ANY race formula for this track
        if not race_formula:
            track_formulas = self.autopilot_manager.formula_manager.get_all_formulas_for_track(track)
            for f in track_formulas:
                if f.session_type == "race" and f.is_valid():
                    race_formula = f
                    logger.info(f"Using fallback race formula from class '{f.vehicle_class}'")
                    break
        
        if race_formula and race_formula.is_valid():
            self.race_a = race_formula.a
            self.race_b = race_formula.b
            logger.debug(f"RACE formula loaded: {race_formula.get_formula_string()}")
    
    def on_file_changed(self, race_data: RaceData):
        """Handle file change event - run autopilot and update display"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        if race_data:
            logger.info(f"New race data detected: {race_data.track_name}")
            logger.debug(f"User vehicle: {race_data.user_vehicle}")
            logger.debug(f"Qual ratio: {race_data.qual_ratio}, Race ratio: {race_data.race_ratio}")
            
            # Save race session
            race_dict = race_data.to_dict()
            race_id = self.db.save_race_session(race_dict)
            
            if race_id:
                # Add data points from ALL AI drivers
                points_added = 0
                for track, ratio, lap_time, session_type in race_data.to_data_points():
                    vehicle = race_data.user_vehicle or "Unknown"
                    if self.db.add_data_point(track, vehicle, ratio, lap_time, session_type):
                        points_added += 1
                        logger.debug(f"Added {session_type} point: {track} R={ratio:.4f} T={lap_time:.3f}s")
                
                logger.info(f"Added {points_added} new data points")
                
                # Reload data (refresh track list)
                self.load_data()
                
                # Auto-select the track that was just detected (only if not in multi-track mode)
                if race_data.track_name and race_data.track_name in self.all_tracks:
                    if not self.multi_track_mode:
                        self.current_track = race_data.track_name
                        self.update_track_display()
                        logger.info(f"Auto-selected track: {race_data.track_name}")
                    
                    # Auto-select the vehicle that was used
                    vehicle_items = self.vehicle_list.findItems(race_data.user_vehicle or "Unknown", Qt.MatchExactly)
                    if vehicle_items:
                        self.vehicle_list.clearSelection()
                        vehicle_items[0].setSelected(True)
                    else:
                        self.vehicle_list.selectAll()
                
                # Run autopilot if enabled
                if self.autopilot_enabled and race_data.aiw_path:
                    logger.info("Running autopilot...")
                    
                    # Reload formulas to include new data
                    self.autopilot_manager.reload_formulas()
                    
                    # Process the data
                    result = self.autopilot_manager.process_new_data(race_data, race_data.aiw_path)
                    
                    if result["success"]:
                        logger.info("Autopilot completed successfully")
                        if result.get("qual_updated"):
                            logger.info(f"Qualifying: {result['qual_old_ratio']:.6f} -> {result['qual_new_ratio']:.6f}")
                        if result.get("race_updated"):
                            logger.info(f"Race: {result['race_old_ratio']:.6f} -> {result['race_new_ratio']:.6f}")
                    else:
                        logger.warning(f"Autopilot: {result.get('message', 'No updates')}")
                    
                    # Reload formulas again to get the updated ones
                    self.autopilot_manager.reload_formulas()
                
                # Update the GUI with the latest formulas
                self._update_formulas_from_autopilot()
                
                # Refresh the graph and controls
                self.update_display()
                self.update_manual_controls()
                self._update_autopilot_status()
                
                logger.debug(f"Qual formula: T = {self.qual_a:.4f}/R + {self.qual_b:.4f}")
                logger.debug(f"Race formula: T = {self.race_a:.4f}/R + {self.race_b:.4f}")
            else:
                logger.error("Failed to save race session")
        else:
            logger.warning("File changed but no race data extracted")
    
    def load_data(self):
        """Load tracks and vehicles from database"""
        if not self.db.database_exists():
            logger.warning(f"Database not found: {self.db.db_path}")
            return
        
        # Store current selection to restore later
        current_track = self.current_track
        current_vehicle = None
        if self.vehicle_list.selectedItems():
            current_vehicle = self.vehicle_list.selectedItems()[0].text()
        
        # Reload lists
        self.all_tracks = self.db.get_all_tracks()
        self.all_vehicles = self.db.get_all_vehicles()
        stats = self.db.get_stats()
        
        # Populate vehicle list
        self.vehicle_list.clear()
        for vehicle in self.all_vehicles:
            self.vehicle_list.addItem(vehicle)
        
        # Restore selection
        if current_track and current_track in self.all_tracks:
            self.current_track = current_track
            self.update_track_display()
        elif self.all_tracks:
            self.current_track = self.all_tracks[0]
            self.update_track_display()
        
        if current_vehicle and current_vehicle in self.all_vehicles:
            items = self.vehicle_list.findItems(current_vehicle, Qt.MatchExactly)
            if items:
                items[0].setSelected(True)
        elif not self.vehicle_list.selectedItems() and self.all_vehicles:
            self.vehicle_list.selectAll()
        
        # Update stats label
        type_str = ", ".join([f"{t}: {c}" for t, c in stats['by_type'].items()])
        self.stats_label.setText(f"Points: {stats['total_points']} | Races: {stats['total_races']}\n{type_str}")
        
        logger.debug(f"Loaded {stats['total_points']} points, {stats['total_races']} races")
    
    def get_selected_data(self) -> dict:
        """Get all data points from selected tracks and vehicles"""
        selected_tracks = self.get_selected_tracks()
        selected_vehicles = [item.text() for item in self.vehicle_list.selectedItems()]
        
        if not selected_tracks or not selected_vehicles:
            return {'quali': [], 'race': [], 'unknown': []}
        
        points = self.db.get_data_points(
            selected_tracks, selected_vehicles,
            self.show_qualifying, self.show_race, self.show_unknown
        )
        
        result = {'quali': [], 'race': [], 'unknown': []}
        for ratio, lap_time, session_type in points:
            if session_type == 'qual' or session_type == 'qual_midpoint':
                result['quali'].append((ratio, lap_time))
            elif session_type == 'race' or session_type == 'race_midpoint':
                result['race'].append((ratio, lap_time))
            else:
                result['unknown'].append((ratio, lap_time))
        
        return result
    
    def on_selection_changed(self):
        """Handle selection changes"""
        if self.autopilot_enabled:
            self._update_formulas_from_autopilot()
            self.update_manual_controls()
        self.update_display()
    
    def on_filter_buttons(self):
        """Handle filter button toggles"""
        self.show_qualifying = self.qual_btn.isChecked()
        self.show_race = self.race_btn.isChecked()
        self.show_unknown = self.unkn_btn.isChecked()
        self.update_display()
    
    def auto_fit(self):
        """Manually fit curves using the same fit_curve function"""
        points_data = self.get_selected_data()
        
        logger.info("Manual Auto-Fit using fit_curve()")
        
        # Fit qualifying
        if points_data['quali'] and len(points_data['quali']) >= 2:
            ratios = [p[0] for p in points_data['quali']]
            times = [p[1] for p in points_data['quali']]
            logger.info(f"Qualifying: fitting {len(ratios)} points...")
            a, b, avg_err, max_err = fit_curve(ratios, times, verbose=False)
            if a is not None and b is not None and a > 0 and b > 0:
                self.qual_a = a
                self.qual_b = b
                logger.info(f"Qualifying result: {get_formula_string(a, b)}")
                logger.info(f"Avg error: {avg_err:.3f}s, Max error: {max_err:.3f}s")
            else:
                logger.warning("Qualifying fit failed")
        else:
            logger.info(f"Qualifying: Need at least 2 points (have {len(points_data['quali'])})")
        
        # Fit race
        if points_data['race'] and len(points_data['race']) >= 2:
            ratios = [p[0] for p in points_data['race']]
            times = [p[1] for p in points_data['race']]
            logger.info(f"Race: fitting {len(ratios)} points...")
            a, b, avg_err, max_err = fit_curve(ratios, times, verbose=False)
            if a is not None and b is not None and a > 0 and b > 0:
                self.race_a = a
                self.race_b = b
                logger.info(f"Race result: {get_formula_string(a, b)}")
                logger.info(f"Avg error: {avg_err:.3f}s, Max error: {max_err:.3f}s")
            else:
                logger.warning("Race fit failed")
        else:
            logger.info(f"Race: Need at least 2 points (have {len(points_data['race'])})")
        
        self.formula_source = "Manual Fit"
        self.update_manual_controls()
        self.update_display()
    
    def update_display(self):
        """Update the plot with both curves and data points"""
        ratios = np.linspace(0.4, 2.0, 200)
        points_data = self.get_selected_data()
        
        # Calculate curve values
        qual_times = self.qual_a / ratios + self.qual_b
        race_times = self.race_a / ratios + self.race_b
        
        # Debug: Print what points we have
        quali_points = points_data.get('quali', [])
        race_points = points_data.get('race', [])
        print(f"\n[GUI] update_display:")
        print(f"  Qualifying points: {len(quali_points)}")
        for r, t in quali_points[:5]:  # Show first 5
            print(f"    R={r:.4f}, T={t:.2f}s")
        print(f"  Race points: {len(race_points)}")
        for r, t in race_points[:5]:
            print(f"    R={r:.4f}, T={t:.2f}s")
        print(f"  Qual formula: T = {self.qual_a:.4f}/R + {self.qual_b:.4f}")
        print(f"  Race formula: T = {self.race_a:.4f}/R + {self.race_b:.4f}")
        
        # Update qualifying curve (yellow) - only if qualifying data is shown
        if self.show_qualifying:
            if self.qual_curve is None:
                self.qual_curve = self.plot.plot(ratios, qual_times, 
                                                 pen=pg.mkPen(color='#FFFF00', width=2.5),
                                                 name='Qualifying')
            else:
                self.qual_curve.setData(ratios, qual_times)
                self.qual_curve.setVisible(True)
        else:
            if self.qual_curve is not None:
                self.qual_curve.setVisible(False)
        
        # Update race curve (orange) - only if race data is shown
        if self.show_race:
            if self.race_curve is None:
                self.race_curve = self.plot.plot(ratios, race_times,
                                                 pen=pg.mkPen(color='#FF6600', width=2.5),
                                                 name='Race')
            else:
                self.race_curve.setData(ratios, race_times)
                self.race_curve.setVisible(True)
        else:
            if self.race_curve is not None:
                self.race_curve.setVisible(False)
        
        # Update qualifying scatter points
        quali_points = points_data.get('quali', [])
        if self.show_qualifying and quali_points:
            r = [p[0] for p in quali_points]
            t = [p[1] for p in quali_points]
            if self.qual_scatter is None:
                self.qual_scatter = pg.ScatterPlotItem(
                    r, t, brush=pg.mkBrush('#FFFF00'), size=8,
                    symbol='o', pen=pg.mkPen('white', width=1)
                )
                self.plot.addItem(self.qual_scatter)
            else:
                self.qual_scatter.setData(r, t)
                self.qual_scatter.setVisible(True)
        elif self.qual_scatter is not None:
            self.qual_scatter.setVisible(False)
        
        # Update race scatter points
        race_points = points_data.get('race', [])
        if self.show_race and race_points:
            r = [p[0] for p in race_points]
            t = [p[1] for p in race_points]
            if self.race_scatter is None:
                self.race_scatter = pg.ScatterPlotItem(
                    r, t, brush=pg.mkBrush('#FF6600'), size=8,
                    symbol='s', pen=pg.mkPen('white', width=1)
                )
                self.plot.addItem(self.race_scatter)
            else:
                self.race_scatter.setData(r, t)
                self.race_scatter.setVisible(True)
        elif self.race_scatter is not None:
            self.race_scatter.setVisible(False)
        
        # Update unknown scatter points
        unknown_points = points_data.get('unknown', [])
        if self.show_unknown and unknown_points:
            r = [p[0] for p in unknown_points]
            t = [p[1] for p in unknown_points]
            if self.unknown_scatter is None:
                self.unknown_scatter = pg.ScatterPlotItem(
                    r, t, brush=pg.mkBrush('#FF00FF'), size=6,
                    symbol='t', pen=pg.mkPen('white', width=1)
                )
                self.plot.addItem(self.unknown_scatter)
            else:
                self.unknown_scatter.setData(r, t)
                self.unknown_scatter.setVisible(True)
        elif self.unknown_scatter is not None:
            self.unknown_scatter.setVisible(False)
        
        # Update legend - remove old and recreate
        if self.legend is not None:
            self.plot.scene().removeItem(self.legend)
        
        self.legend = self.plot.addLegend()
        
        # Only add visible curves to legend
        if self.show_qualifying and self.qual_curve is not None:
            self.legend.addItem(self.qual_curve, f'Qualifying: T = {self.qual_a:.3f}/R + {self.qual_b:.3f}')
        if self.show_race and self.race_curve is not None:
            self.legend.addItem(self.race_curve, f'Race: T = {self.race_a:.3f}/R + {self.race_b:.3f}')
        
        if self.show_qualifying and quali_points:
            self.legend.addItem(self.qual_scatter, f'Qual Data ({len(quali_points)})')
        if self.show_race and race_points:
            self.legend.addItem(self.race_scatter, f'Race Data ({len(race_points)})')
        if self.show_unknown and unknown_points:
            self.legend.addItem(self.unknown_scatter, f'Unknown ({len(unknown_points)})')
        
        # Update title with source info and multi-track indicator
        track_info = f" - {len(self.get_selected_tracks())} track(s)" if self.multi_track_mode else ""
        if self.autopilot_enabled and "Autopilot" in self.formula_source:
            self.plot.setTitle(f'[AUTO] Autopilot - {self.formula_source}{track_info}', color='#4CAF50', size='12pt')
        else:
            self.plot.setTitle(f'Manual - {self.formula_source}{track_info}', color='#FFA500', size='12pt')
        
        # Update status bar
        selected_tracks = len(self.get_selected_tracks())
        selected_vehicles = len(self.vehicle_list.selectedItems())
        total_points = len(quali_points) + len(race_points) + len(unknown_points)
        
        mode = "[AUTO] Autopilot" if self.autopilot_enabled else "Manual"
        track_mode = "Multi-track" if self.multi_track_mode else "Single track"
        self.statusBar().showMessage(
            f"{mode} | {track_mode}: {selected_tracks} | Vehicles: {selected_vehicles} | Points: {total_points}"
        )
    
    def reset_view(self):
        """Reset the plot to default view"""
        self.plot.setXRange(0.4, 2.0)
        self.plot.setYRange(50, 200)
    
    def closeEvent(self, event):
        """Handle close event"""
        self.stop_daemon()
        event.accept()


def main():
    create_default_config_if_missing()
    db_path = get_db_path()
    
    if not Path(db_path).exists():
        print(f"\nDatabase '{db_path}' does not exist.")
        response = input("Create empty database? (y/n): ").lower().strip()
        if response == 'y':
            CurveDatabase(db_path)
            print(f"Created empty database: {db_path}\n")
        else:
            print("\nExiting.\n")
            return
    
    app = QApplication(sys.argv)
    setup_dark_theme(app)
    
    window = SimpleCurveViewer(db_path)
    window.show()
    
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
