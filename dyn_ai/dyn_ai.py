#!/usr/bin/env python3
"""
Live AI Tuner - Simplified GUI with separate Autosave and Autoratio switches
"""

import sys
import threading
import logging
import sqlite3
from pathlib import Path
from typing import List, Tuple, Optional, Dict, Any
from datetime import datetime

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QLabel, QPushButton, QGroupBox, QGridLayout, QCheckBox,
    QSplitter, QFrame, QSizePolicy, QProgressBar, QMessageBox
)
from PyQt5.QtCore import Qt, pyqtSignal, QObject
from PyQt5.QtGui import QFont

from db_funcs import CurveDatabase
from formula_funcs import get_formula_string, hyperbolic
from gui_funcs import (
    setup_dark_theme, show_error_dialog, show_info_dialog, show_warning_dialog,
    AdvancedSettingsDialog, LogWindow, SimpleLogHandler
)
from cfg_funcs import (
    get_config_with_defaults, get_results_file_path, get_poll_interval,
    get_db_path, create_default_config_if_missing, get_base_path,
    get_autopilot_enabled, get_autopilot_silent,
    update_autopilot_enabled, update_autopilot_silent
)
from data_extraction import DataExtractor, RaceData
from autopilot import AutopilotManager, Formula, get_vehicle_class, load_vehicle_classes


logger = logging.getLogger(__name__)


class SimplifiedLogger:
    """Helper class to generate simplified, human-readable log messages"""
    
    @staticmethod
    def new_data_detected(track, vehicle_class, session_type, ratio, lap_time):
        return f"📊 New {session_type} data: {track} / {vehicle_class} | Ratio={ratio:.4f} | AI Lap={lap_time:.1f}s"
    
    @staticmethod
    def new_ratio_calculation(old_ratio, new_ratio, ratio_name):
        direction = "↑" if new_ratio > old_ratio else "↓"
        return f"🎮 {ratio_name}: {old_ratio:.4f} → {new_ratio:.4f} ({direction})"
    
    @staticmethod
    def autosave_status(enabled):
        return f"💾 Autosave {'ON' if enabled else 'OFF'}"
    
    @staticmethod
    def autoratio_status(enabled):
        return f"⚙️ Autoratio {'ON' if enabled else 'OFF'}"


class FileChangeSignal(QObject):
    file_changed = pyqtSignal(object)


class FileMonitorDaemon(QObject):
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
        if not self.file_path.exists():
            logger.warning(f"File does not exist yet: {self.file_path}")
            self.file_path.parent.mkdir(parents=True, exist_ok=True)
        
        self._update_file_state()
        self.running = True
        self._schedule_check()
        logger.info(f"Started monitoring: {self.file_path}")
        
    def stop(self):
        self.running = False
        if self.timer:
            self.timer.cancel()
        logger.info("Stopped monitoring")
    
    def _schedule_check(self):
        if self.running:
            self.timer = threading.Timer(self.poll_interval, self._check_file)
            self.timer.daemon = True
            self.timer.start()
    
    def _update_file_state(self):
        try:
            if self.file_path.exists():
                stat = self.file_path.stat()
                self.last_mtime = stat.st_mtime
                self.last_size = stat.st_size
        except Exception:
            pass
    
    def _check_file(self):
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
                
                self.last_mtime = current_mtime
                self.last_size = current_size
            
        except Exception as e:
            logger.error(f"Error checking file: {e}")
        finally:
            self._schedule_check()


class SimplifiedCurveViewer(QMainWindow):
    """Simplified main window with separate Autosave and Autoratio switches"""
    
    def __init__(self, db_path: str = "ai_data.db", config_file: str = "cfg.yml"):
        super().__init__()
        self.setWindowTitle("GTR2 Dynamic AI")
        self.setGeometry(100, 100, 500, 520)
        self.setMinimumWidth(400)
        self.setMinimumHeight(460)
        
        self.config_file = config_file
        self.config = get_config_with_defaults(config_file)
        self.db = CurveDatabase(db_path)
        
        # Setup simplified logging
        self.log_window = LogWindow(self)
        log_handler = SimpleLogHandler(self.log_window)
        log_handler.setFormatter(logging.Formatter('%(message)s'))
        logging.getLogger().addHandler(log_handler)
        logging.getLogger().setLevel(logging.INFO)
        
        self.simplified_logger = SimplifiedLogger()
        self.class_mapping = load_vehicle_classes()
        
        # Autopilot manager (handles ratio calculations)
        self.autopilot_manager = AutopilotManager(self.db)
        
        # Separate switches for Autosave and Autoratio
        self.autosave_enabled = True  # Default ON
        self.autoratio_enabled = False  # Default OFF (safer)
        self.autopilot_manager.set_enabled(self.autoratio_enabled)
        
        # AI Target settings
        self.ai_target_settings = {
            "mode": "percentage",
            "percentage": 50,
            "offset_seconds": 0.0,
            "error_margin": 0.0
        }
        
        # Current formulas
        self.qual_a: float = 32.0
        self.qual_b: float = 70.0
        self.race_a: float = 32.0
        self.race_b: float = 70.0
        self.qual_ratio_count: int = 0
        self.race_ratio_count: int = 0
        self.qual_error_pct: float = 0.0
        self.race_error_pct: float = 0.0
        
        # Current selection
        self.current_track: str = ""
        self.current_vehicle: str = ""
        self.current_vehicle_class: str = ""
        
        # User lap times
        self.user_qualifying_sec: float = 0.0
        self.user_best_lap_sec: float = 0.0
        self.last_qual_ratio: Optional[float] = None
        self.last_race_ratio: Optional[float] = None
        
        # Cache
        self.all_tracks: List[str] = []
        self.all_vehicles: List[str] = []
        
        # Advanced settings window
        self.advanced_window = None
        
        # Daemon
        self.daemon = None
        
        self.setup_ui()
        self.load_data()
        self.update_display()
        self._update_switch_ui()
        
        # Auto-start daemon
        base_path = get_base_path(config_file)
        if base_path:
            self.start_daemon()
    
    def setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setSpacing(10)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Title
        self.title_label = QLabel("GTR2 Dynamic AI")
        self.title_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #FFA500;")
        self.title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.title_label)
        
        # Current track
        track_frame = QFrame()
        track_frame.setStyleSheet("background-color: #2b2b2b; border-radius: 5px;")
        track_layout = QHBoxLayout(track_frame)
        track_layout.addWidget(QLabel("🏁 Current Track:"))
        self.track_label = QLabel("-")
        self.track_label.setStyleSheet("color: #FFA500; font-weight: bold;")
        track_layout.addWidget(self.track_label)
        track_layout.addStretch()
        layout.addWidget(track_frame)
        
        # Vehicle info
        vehicle_group = QGroupBox("Vehicle")
        vehicle_layout = QGridLayout(vehicle_group)
        
        self.vehicle_class_label = QLabel("-")
        self.vehicle_class_label.setStyleSheet("color: #4CAF50;")
        vehicle_layout.addWidget(QLabel("Class:"), 0, 0)
        vehicle_layout.addWidget(self.vehicle_class_label, 0, 1)
        
        self.vehicle_label = QLabel("-")
        self.vehicle_label.setStyleSheet("color: #888; font-size: 10px;")
        vehicle_layout.addWidget(QLabel("Model:"), 1, 0)
        vehicle_layout.addWidget(self.vehicle_label, 1, 1)
        
        layout.addWidget(vehicle_group)
        
        # Current ratios
        ratios_group = QGroupBox("Current AI Ratios")
        ratios_layout = QGridLayout(ratios_group)
        
        self.qual_ratio_label = QLabel("-")
        self.qual_ratio_label.setStyleSheet("color: #FFFF00; font-family: monospace; font-weight: bold;")
        ratios_layout.addWidget(QLabel("Qualifying:"), 0, 0)
        ratios_layout.addWidget(self.qual_ratio_label, 0, 1)
        
        self.race_ratio_label = QLabel("-")
        self.race_ratio_label.setStyleSheet("color: #FF6600; font-family: monospace; font-weight: bold;")
        ratios_layout.addWidget(QLabel("Race:"), 1, 0)
        ratios_layout.addWidget(self.race_ratio_label, 1, 1)
        
        layout.addWidget(ratios_group)
        
        # Formula display
        formula_group = QGroupBox("Active Formulas")
        formula_layout = QVBoxLayout(formula_group)
        
        self.qual_formula_label = QLabel("Qualifying: T = 32.00 / R + --")
        self.qual_formula_label.setStyleSheet("color: #FFFF00; font-family: monospace; font-size: 10px;")
        formula_layout.addWidget(self.qual_formula_label)
        
        self.race_formula_label = QLabel("Race: T = 32.00 / R + --")
        self.race_formula_label.setStyleSheet("color: #FF6600; font-family: monospace; font-size: 10px;")
        formula_layout.addWidget(self.race_formula_label)
        
        layout.addWidget(formula_group)
        
        # Control switches
        controls_group = QGroupBox("Controls")
        controls_layout = QVBoxLayout(controls_group)
        
        # Autosave switch
        autosave_layout = QHBoxLayout()
        self.autosave_btn = QPushButton("💾 Autosave is ON")
        self.autosave_btn.setCheckable(True)
        self.autosave_btn.setChecked(self.autosave_enabled)
        self.autosave_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-weight: bold;
                padding: 8px;
                border: none;
                border-radius: 4px;
            }
            QPushButton:checked {
                background-color: #4CAF50;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        self.autosave_btn.clicked.connect(self.toggle_autosave)
        autosave_layout.addWidget(self.autosave_btn)
        
        autosave_desc = QLabel("Save new race data to database")
        autosave_desc.setStyleSheet("color: #888; font-size: 10px;")
        autosave_layout.addWidget(autosave_desc)
        autosave_layout.addStretch()
        controls_layout.addLayout(autosave_layout)
        
        controls_layout.addSpacing(5)
        
        # Autoratio switch
        autoratio_layout = QHBoxLayout()
        self.autoratio_btn = QPushButton("⚙️ Autoratio is OFF")
        self.autoratio_btn.setCheckable(True)
        self.autoratio_btn.setChecked(self.autoratio_enabled)
        self.autoratio_btn.setStyleSheet("""
            QPushButton {
                background-color: #555;
                color: #aaa;
                font-weight: bold;
                padding: 8px;
                border: none;
                border-radius: 4px;
            }
            QPushButton:checked {
                background-color: #FF9800;
                color: white;
            }
            QPushButton:hover {
                background-color: #666;
            }
        """)
        self.autoratio_btn.clicked.connect(self.toggle_autoratio)
        autoratio_layout.addWidget(self.autoratio_btn)
        
        autoratio_desc = QLabel("Auto-calculate and apply new AI ratios")
        autoratio_desc.setStyleSheet("color: #888; font-size: 10px;")
        autoratio_layout.addWidget(autoratio_desc)
        autoratio_layout.addStretch()
        controls_layout.addLayout(autoratio_layout)
        
        layout.addWidget(controls_group)
        
        # Formula quality (simplified)
        quality_group = QGroupBox("Formula Quality")
        quality_layout = QGridLayout(quality_group)
        
        quality_layout.addWidget(QLabel("Qualifying:"), 0, 0)
        self.qual_quality_label = QLabel("-")
        self.qual_quality_label.setStyleSheet("color: #FFFF00;")
        quality_layout.addWidget(self.qual_quality_label, 0, 1)
        
        self.qual_progress = QProgressBar()
        self.qual_progress.setRange(0, 100)
        self.qual_progress.setValue(0)
        self.qual_progress.setFixedHeight(8)
        self.qual_progress.setTextVisible(False)
        quality_layout.addWidget(self.qual_progress, 1, 0, 1, 2)
        
        quality_layout.addWidget(QLabel("Race:"), 2, 0)
        self.race_quality_label = QLabel("-")
        self.race_quality_label.setStyleSheet("color: #FF6600;")
        quality_layout.addWidget(self.race_quality_label, 2, 1)
        
        self.race_progress = QProgressBar()
        self.race_progress.setRange(0, 100)
        self.race_progress.setValue(0)
        self.race_progress.setFixedHeight(8)
        self.race_progress.setTextVisible(False)
        quality_layout.addWidget(self.race_progress, 3, 0, 1, 2)
        
        layout.addWidget(quality_group)
        
        # Action buttons
        button_layout = QHBoxLayout()
        
        self.advanced_btn = QPushButton("Advanced Settings")
        self.advanced_btn.setStyleSheet("background-color: #9C27B0;")
        self.advanced_btn.clicked.connect(self.open_advanced_settings)
        button_layout.addWidget(self.advanced_btn)
        
        self.log_btn = QPushButton("Show Log")
        self.log_btn.setStyleSheet("background-color: #2196F3;")
        self.log_btn.clicked.connect(self.show_log_window)
        button_layout.addWidget(self.log_btn)
        
        self.exit_btn = QPushButton("Exit")
        self.exit_btn.setStyleSheet("background-color: #f44336;")
        self.exit_btn.clicked.connect(self.close)
        button_layout.addWidget(self.exit_btn)
        
        layout.addLayout(button_layout)
        
        # Status bar
        self.statusBar().showMessage("Ready")
    
    def _update_switch_ui(self):
        """Update switch button appearance"""
        if self.autosave_enabled:
            self.autosave_btn.setText("💾 Autosave is ON")
            self.autosave_btn.setStyleSheet("""
                QPushButton {
                    background-color: #4CAF50;
                    color: white;
                    font-weight: bold;
                    padding: 8px;
                    border: none;
                    border-radius: 4px;
                }
                QPushButton:hover {
                    background-color: #45a049;
                }
            """)
        else:
            self.autosave_btn.setText("💾 Autosave is OFF")
            self.autosave_btn.setStyleSheet("""
                QPushButton {
                    background-color: #555;
                    color: #aaa;
                    font-weight: bold;
                    padding: 8px;
                    border: none;
                    border-radius: 4px;
                }
                QPushButton:hover {
                    background-color: #666;
                }
            """)
        
        if self.autoratio_enabled:
            self.autoratio_btn.setText("⚙️ Autoratio is ON")
            self.autoratio_btn.setStyleSheet("""
                QPushButton {
                    background-color: #FF9800;
                    color: white;
                    font-weight: bold;
                    padding: 8px;
                    border: none;
                    border-radius: 4px;
                }
                QPushButton:hover {
                    background-color: #F57C00;
                }
            """)
        else:
            self.autoratio_btn.setText("⚙️ Autoratio is OFF")
            self.autoratio_btn.setStyleSheet("""
                QPushButton {
                    background-color: #555;
                    color: #aaa;
                    font-weight: bold;
                    padding: 8px;
                    border: none;
                    border-radius: 4px;
                }
                QPushButton:hover {
                    background-color: #666;
                }
            """)
    
    def toggle_autosave(self):
        """Toggle autosave mode (save data to database)"""
        self.autosave_enabled = not self.autosave_enabled
        self._update_switch_ui()
        logger.info(self.simplified_logger.autosave_status(self.autosave_enabled))
        self.statusBar().showMessage(f"Autosave {'ON' if self.autosave_enabled else 'OFF'}", 2000)
    
    def toggle_autoratio(self):
        """Toggle autoratio mode (calculate and apply new ratios)"""
        self.autoratio_enabled = not self.autoratio_enabled
        self.autopilot_manager.set_enabled(self.autoratio_enabled)
        self._update_switch_ui()
        logger.info(self.simplified_logger.autoratio_status(self.autoratio_enabled))
        self.statusBar().showMessage(f"Autoratio {'ON' if self.autoratio_enabled else 'OFF'}", 2000)
        
        if self.autoratio_enabled:
            self.autopilot_manager.reload_formulas()
            self._update_formulas_from_autopilot()
            self.update_display()
    
    def _get_formula_quality_text(self, ratio_count: int, error_pct: float) -> Tuple[str, str, int]:
        """Determine formula quality based on number of distinct ratios and error percentage"""
        if ratio_count == 0:
            return "No data", "#888888", 0
        if ratio_count == 1:
            return "Learning (1 ratio)", "#888888", 10
        if ratio_count < 3:
            return f"Learning ({ratio_count} ratios)", "#888888", 20
        if error_pct < 2:
            return f"Excellent (±{error_pct:.1f}%)", "#4CAF50", 90
        if error_pct < 5:
            return f"Good (±{error_pct:.1f}%)", "#4CAF50", 75
        if error_pct < 10:
            return f"Fair (±{error_pct:.1f}%)", "#FFC107", 50
        return f"Poor (±{error_pct:.1f}%)", "#F44336", 25
    
    def _calculate_formula_stats(self, track: str, vehicle_class: str, session_type: str):
        """Calculate statistics for a formula"""
        if not track or not vehicle_class:
            return 0, 0.0
        
        conn = sqlite3.connect(self.db.db_path)
        cursor = conn.cursor()
        
        session_filter = "qual" if session_type == "qual" else "race"
        
        # Get distinct ratios
        cursor.execute("""
            SELECT DISTINCT ratio, lap_time 
            FROM data_points 
            WHERE track = ? AND vehicle_class = ? AND session_type = ?
            ORDER BY ratio
        """, (track, vehicle_class, session_filter))
        rows = cursor.fetchall()
        conn.close()
        
        ratio_count = len(rows)
        
        if ratio_count < 2:
            return ratio_count, 0.0
        
        # Get formula
        formula = self.autopilot_manager.formula_manager.get_formula_by_class(track, vehicle_class, session_type)
        
        if not formula or not formula.is_valid():
            return ratio_count, 0.0
        
        # Calculate errors
        errors = []
        for ratio, lap_time in rows:
            if ratio and ratio > 0:
                predicted = formula.get_time_at_ratio(ratio)
                if predicted > 0:
                    error_pct = abs(lap_time - predicted) / lap_time * 100
                    errors.append(error_pct)
        
        avg_error_pct = sum(errors) / len(errors) if errors else 0
        return ratio_count, avg_error_pct
    
    def _update_formulas_from_autopilot(self):
        """Update current formulas from autopilot"""
        if not self.current_track or not self.current_vehicle_class:
            if self.current_vehicle:
                self.current_vehicle_class = get_vehicle_class(self.current_vehicle, self.class_mapping)
            if not self.current_vehicle_class:
                return
        
        # Get qualifying formula
        qual_formula = self.autopilot_manager.formula_manager.get_formula_by_class(
            self.current_track, self.current_vehicle_class, "qual"
        )
        if qual_formula and qual_formula.is_valid():
            self.qual_a = qual_formula.a
            self.qual_b = qual_formula.b
        else:
            self.qual_a = 32.0
            self.qual_b = 70.0
        
        # Get race formula
        race_formula = self.autopilot_manager.formula_manager.get_formula_by_class(
            self.current_track, self.current_vehicle_class, "race"
        )
        if race_formula and race_formula.is_valid():
            self.race_a = race_formula.a
            self.race_b = race_formula.b
        else:
            self.race_a = 32.0
            self.race_b = 70.0
        
        # Calculate statistics
        self.qual_ratio_count, self.qual_error_pct = self._calculate_formula_stats(
            self.current_track, self.current_vehicle_class, "qual"
        )
        self.race_ratio_count, self.race_error_pct = self._calculate_formula_stats(
            self.current_track, self.current_vehicle_class, "race"
        )
    
    def open_advanced_settings(self):
        """Open the advanced settings window"""
        if self.advanced_window is None:
            self.advanced_window = AdvancedSettingsDialog(self, self.db, self.log_window)
            self.advanced_window.data_updated.connect(self.on_data_updated)
            self.advanced_window.formula_updated.connect(self.on_formula_updated)
        
        # Update current info
        if hasattr(self.advanced_window, 'curve_graph'):
            self.advanced_window.curve_graph.update_current_info(
                track=self.current_track,
                vehicle=self.current_vehicle,
                qual_time=self.user_qualifying_sec if self.user_qualifying_sec > 0 else None,
                race_time=self.user_best_lap_sec if self.user_best_lap_sec > 0 else None,
                qual_ratio=self.last_qual_ratio,
                race_ratio=self.last_race_ratio
            )
            self.advanced_window.curve_graph.set_formulas(
                self.qual_a, self.qual_b,
                self.race_a, self.race_b
            )
            self.advanced_window.curve_graph.full_refresh()
        
        self.advanced_window.show()
        self.advanced_window.raise_()
        self.advanced_window.activateWindow()
    
    def on_data_updated(self):
        """Handle data updates from advanced settings"""
        self.load_data()
        self.update_display()
    
    def on_formula_updated(self, session_type: str, a: float, b: float):
        """Handle formula updates from advanced settings"""
        if session_type == "qual":
            self.qual_a = a
            self.qual_b = b
        else:
            self.race_a = a
            self.race_b = b
        self.update_display()
    
    def show_log_window(self):
        """Show the log window"""
        if self.log_window:
            self.log_window.show()
            self.log_window.raise_()
    
    def start_daemon(self):
        """Start file monitoring daemon"""
        file_path = get_results_file_path(self.config_file)
        base_path = get_base_path(self.config_file)
        
        if not file_path or not base_path:
            logger.warning("Base path not configured - daemon not started")
            return
        
        poll_interval = get_poll_interval(self.config_file)
        
        self.daemon = FileMonitorDaemon(file_path, base_path, poll_interval)
        self.daemon.signal.file_changed.connect(self.on_file_changed)
        self.daemon.start()
        logger.info(f"Monitoring: {file_path}")
    
    def stop_daemon(self):
        """Stop file monitoring daemon"""
        if self.daemon:
            self.daemon.stop()
            self.daemon = None
    
    def on_file_changed(self, race_data: RaceData):
        """Handle file change event"""
        if not race_data:
            return
        
        # Update track info
        if race_data.track_name:
            self.current_track = race_data.track_name
            self.track_label.setText(self.current_track)
            self.setWindowTitle(f"GTR2 Dynamic AI - {self.current_track}")
        
        # Store user lap times
        if race_data.user_qualifying_sec:
            self.user_qualifying_sec = race_data.user_qualifying_sec
        if race_data.user_best_lap_sec:
            self.user_best_lap_sec = race_data.user_best_lap_sec
        if race_data.qual_ratio:
            self.last_qual_ratio = race_data.qual_ratio
        if race_data.race_ratio:
            self.last_race_ratio = race_data.race_ratio
        
        # Update vehicle info
        if race_data.user_vehicle:
            self.current_vehicle = race_data.user_vehicle
            self.current_vehicle_class = get_vehicle_class(self.current_vehicle, self.class_mapping)
            self.vehicle_label.setText(self.current_vehicle)
            self.vehicle_class_label.setText(self.current_vehicle_class)
        
        # Log simplified message
        logger.info(self.simplified_logger.new_data_detected(
            race_data.track_name, self.current_vehicle_class, "race",
            race_data.race_ratio or 0, race_data.best_ai_lap_sec or 0
        ))
        
        # ALWAYS save race session to database (for data collection)
        race_dict = race_data.to_dict()
        race_id = self.db.save_race_session(race_dict)
        
        if race_id and self.autosave_enabled:
            # Add data points with correct vehicle class
            points_added = 0
            for track, vehicle_name, ratio, lap_time, session_type in race_data.to_data_points_with_vehicles():
                try:
                    vehicle_class = get_vehicle_class(vehicle_name, self.class_mapping)
                    ratio_float = float(ratio)
                    lap_time_float = float(lap_time)
                    if self.db.add_data_point(track, vehicle_class, ratio_float, lap_time_float, session_type):
                        points_added += 1
                except (ValueError, TypeError) as e:
                    logger.error(f"Failed to add data point: {e}")
            
            if points_added > 0:
                logger.info(f"📝 Saved {points_added} new data points")
        
        # Update formulas from database
        self.autopilot_manager.reload_formulas()
        self._update_formulas_from_autopilot()
        self.update_display()
        
        # Run autoratio if enabled
        if self.autoratio_enabled and race_data.aiw_path:
            logger.info("⚙️ Running Autoratio...")
            result = self.autopilot_manager.process_new_data(race_data, race_data.aiw_path, self.ai_target_settings)
            
            if result.get("success"):
                if result.get("qual_updated"):
                    logger.info(self.simplified_logger.new_ratio_calculation(
                        result['qual_old_ratio'], result['qual_new_ratio'], "QualRatio"
                    ))
                if result.get("race_updated"):
                    logger.info(self.simplified_logger.new_ratio_calculation(
                        result['race_old_ratio'], result['race_new_ratio'], "RaceRatio"
                    ))
                
                # Reload formulas after update
                self.autopilot_manager.reload_formulas()
                self._update_formulas_from_autopilot()
                self.update_display()
                self.statusBar().showMessage("AI ratios updated!", 3000)
            else:
                if result.get("message"):
                    logger.warning(f"Autoratio: {result['message']}")
        elif not self.autoratio_enabled and race_data.aiw_path:
            logger.info("⚙️ Autoratio is OFF - skipping ratio calculation")
        
        # Refresh advanced window if open
        if self.advanced_window and self.advanced_window.isVisible():
            if hasattr(self.advanced_window, 'curve_graph'):
                self.advanced_window.curve_graph.update_current_info(
                    track=self.current_track,
                    vehicle=self.current_vehicle,
                    qual_time=self.user_qualifying_sec if self.user_qualifying_sec > 0 else None,
                    race_time=self.user_best_lap_sec if self.user_best_lap_sec > 0 else None,
                    qual_ratio=self.last_qual_ratio,
                    race_ratio=self.last_race_ratio
                )
                self.advanced_window.curve_graph.full_refresh()
    
    def load_data(self):
        """Load tracks and vehicles from database"""
        if not self.db.database_exists():
            return
        
        self.all_tracks = self.db.get_all_tracks()
        self.all_vehicles = self.db.get_all_vehicle_classes()
        
        if self.all_tracks and not self.current_track:
            self.current_track = self.all_tracks[0]
            self.track_label.setText(self.current_track)
            self.setWindowTitle(f"GTR2 Dynamic AI - {self.current_track}")
        if self.all_vehicles and not self.current_vehicle:
            self.current_vehicle = self.all_vehicles[0]
            self.current_vehicle_class = get_vehicle_class(self.current_vehicle, self.class_mapping)
            self.vehicle_label.setText(self.current_vehicle)
            self.vehicle_class_label.setText(self.current_vehicle_class)
        
        if self.autopilot_manager:
            self._update_formulas_from_autopilot()
    
    def update_display(self):
        """Update all display elements"""
        # Current ratios
        qual_ratio = None
        race_ratio = None
        
        if self.current_track:
            conn = sqlite3.connect(self.db.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT qual_ratio FROM race_sessions 
                WHERE track_name = ? 
                ORDER BY timestamp DESC LIMIT 1
            """, (self.current_track,))
            row = cursor.fetchone()
            if row and row[0]:
                qual_ratio = row[0]
            
            cursor.execute("""
                SELECT race_ratio FROM race_sessions 
                WHERE track_name = ? 
                ORDER BY timestamp DESC LIMIT 1
            """, (self.current_track,))
            row = cursor.fetchone()
            if row and row[0]:
                race_ratio = row[0]
            
            conn.close()
        
        self.qual_ratio_label.setText(f"{qual_ratio:.6f}" if qual_ratio else "-")
        self.race_ratio_label.setText(f"{race_ratio:.6f}" if race_ratio else "-")
        
        # Formulas
        self.qual_formula_label.setText(f"Qualifying: T = {self.qual_a:.2f} / R + {self.qual_b:.2f}")
        self.race_formula_label.setText(f"Race: T = {self.race_a:.2f} / R + {self.race_b:.2f}")
        
        # Quality
        qual_text, qual_color, qual_progress = self._get_formula_quality_text(
            self.qual_ratio_count, self.qual_error_pct
        )
        self.qual_quality_label.setText(qual_text)
        self.qual_quality_label.setStyleSheet(f"color: {qual_color};")
        self.qual_progress.setValue(qual_progress)
        
        race_text, race_color, race_progress = self._get_formula_quality_text(
            self.race_ratio_count, self.race_error_pct
        )
        self.race_quality_label.setText(race_text)
        self.race_quality_label.setStyleSheet(f"color: {race_color};")
        self.race_progress.setValue(race_progress)
    
    def closeEvent(self, event):
        """Handle close event"""
        self.stop_daemon()
        if self.advanced_window:
            self.advanced_window.close()
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
    
    window = SimplifiedCurveViewer(db_path)
    window.show()
    
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
