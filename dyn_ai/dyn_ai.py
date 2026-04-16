# dyn_ai.py - Complete fixed version with correct title and autopilot button
#!/usr/bin/env python3
"""
Live AI Tuner - Simplified GUI
Shows essential info: track, vehicle class, current ratios, formula quality
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
    QSplitter, QFrame, QSizePolicy
)
from PyQt5.QtCore import Qt, pyqtSignal, QObject
from PyQt5.QtGui import QFont

from db_funcs import CurveDatabase
from formula_funcs import get_formula_string
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
    def formula_adaptation(old_b, new_b, a, target_ratio, target_time):
        change = new_b - old_b
        direction = "↑" if change > 0 else "↓"
        return f"📐 Formula adapted: kept a={a:.2f}, {direction} b by {abs(change):.2f}s → {new_b:.2f}"
    
    @staticmethod
    def new_ratio_calculation(old_ratio, new_ratio, ratio_name):
        direction = "↑" if new_ratio > old_ratio else "↓"
        return f"🎮 {ratio_name}: {old_ratio:.4f} → {new_ratio:.4f} ({direction})"
    
    @staticmethod
    def autopilot_status(enabled):
        return f"🤖 Autopilot {'ON' if enabled else 'OFF'}"


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
    """Simplified main window with essential info only"""
    
    def __init__(self, db_path: str = "ai_data.db", config_file: str = "cfg.yml"):
        super().__init__()
        self.setWindowTitle("GTR2 Dynamic AI")
        self.setGeometry(100, 100, 500, 400)
        self.setMinimumWidth(400)
        self.setMinimumHeight(350)
        
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
        
        # Autopilot
        self.autopilot_manager = AutopilotManager(self.db)
        self.autopilot_enabled = get_autopilot_enabled(config_file)
        self.autopilot_silent = get_autopilot_silent(config_file)
        self.autopilot_manager.set_enabled(self.autopilot_enabled)
        self.autopilot_manager.set_silent(self.autopilot_silent)
        
        # AI Target settings
        self.ai_target_settings = {
            "mode": "percentage",
            "percentage": 50,
            "offset_seconds": 0.0,
            "error_margin": 0.0
        }
        
        # Current formulas
        self.qual_a: float = 30.0
        self.qual_b: float = 70.0
        self.race_a: float = 30.0
        self.race_b: float = 70.0
        self.qual_error_pct: float = 0.0
        self.race_error_pct: float = 0.0
        
        # Current selection
        self.current_track: str = ""
        self.current_vehicle: str = ""
        self.current_vehicle_class: str = ""
        
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
        self._update_autopilot_ui()
        
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
        
        # Title - just the track name
        self.title_label = QLabel("No Track")
        self.title_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #FFA500;")
        self.title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.title_label)
        
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
        
        # Formula quality
        quality_group = QGroupBox("Formula Quality")
        quality_layout = QGridLayout(quality_group)
        
        self.qual_quality_label = QLabel("-")
        self.qual_quality_label.setStyleSheet("color: #FFFF00;")
        quality_layout.addWidget(QLabel("Qualifying:"), 0, 0)
        quality_layout.addWidget(self.qual_quality_label, 0, 1)
        
        self.race_quality_label = QLabel("-")
        self.race_quality_label.setStyleSheet("color: #FF6600;")
        quality_layout.addWidget(QLabel("Race:"), 1, 0)
        quality_layout.addWidget(self.race_quality_label, 1, 1)
        
        layout.addWidget(quality_group)
        
        # Formula display
        formula_group = QGroupBox("Active Formulas")
        formula_layout = QVBoxLayout(formula_group)
        
        self.qual_formula_label = QLabel("Qualifying: T = -- / R + --")
        self.qual_formula_label.setStyleSheet("color: #FFFF00; font-family: monospace; font-size: 10px;")
        formula_layout.addWidget(self.qual_formula_label)
        
        self.race_formula_label = QLabel("Race: T = -- / R + --")
        self.race_formula_label.setStyleSheet("color: #FF6600; font-family: monospace; font-size: 10px;")
        formula_layout.addWidget(self.race_formula_label)
        
        layout.addWidget(formula_group)
        
        # Autopilot controls
        autopilot_group = QGroupBox("Autopilot")
        autopilot_layout = QHBoxLayout(autopilot_group)
        
        self.autopilot_btn = QPushButton("Autopilot is OFF")
        self.autopilot_btn.setCheckable(True)
        self.autopilot_btn.setChecked(self.autopilot_enabled)
        self.autopilot_btn.clicked.connect(self.toggle_autopilot)
        autopilot_layout.addWidget(self.autopilot_btn)
        
        self.autopilot_status = QLabel("Status: Disabled")
        self.autopilot_status.setStyleSheet("color: #888; font-size: 10px;")
        autopilot_layout.addWidget(self.autopilot_status)
        
        layout.addWidget(autopilot_group)
        
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
    
    def _update_autopilot_ui(self):
        """Update autopilot button appearance based on state"""
        if self.autopilot_enabled:
            self.autopilot_btn.setText("Autopilot is ON")
            self.autopilot_btn.setStyleSheet("""
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
            self.autopilot_status.setText("Status: Active")
            self.autopilot_status.setStyleSheet("color: #4CAF50; font-size: 10px;")
        else:
            self.autopilot_btn.setText("Autopilot is OFF")
            self.autopilot_btn.setStyleSheet("""
                QPushButton {
                    background-color: #555;
                    color: #aaa;
                    font-weight: bold;
                    padding: 8px;
                    border: none;
                    border-radius: 4px;
                }
                QPushButton:checked {
                    background-color: #555;
                }
                QPushButton:hover {
                    background-color: #666;
                }
            """)
            self.autopilot_status.setText("Status: Disabled")
            self.autopilot_status.setStyleSheet("color: #888; font-size: 10px;")
    
    def open_advanced_settings(self):
        """Open the advanced settings window with graph and data management"""
        if self.advanced_window is None:
            self.advanced_window = AdvancedSettingsDialog(self, self.db, self.log_window)
            self.advanced_window.data_updated.connect(self.on_data_updated)
        self.advanced_window.show()
        self.advanced_window.raise_()
    
    def on_data_updated(self):
        """Handle data updates from advanced settings"""
        self.load_data()
        self.update_display()
    
    def show_log_window(self):
        """Show the log window"""
        if self.log_window:
            self.log_window.show()
            self.log_window.raise_()
    
    def toggle_autopilot(self):
        """Toggle autopilot mode"""
        self.autopilot_enabled = not self.autopilot_enabled
        self.autopilot_manager.set_enabled(self.autopilot_enabled)
        update_autopilot_enabled(self.autopilot_enabled, self.config_file)
        
        self._update_autopilot_ui()
        
        logger.info(self.simplified_logger.autopilot_status(self.autopilot_enabled))
        
        if self.autopilot_enabled:
            self.autopilot_manager.reload_formulas()
            self._update_formulas_from_autopilot()
            self.update_display()
    
    def _update_formulas_from_autopilot(self):
        """Update current formulas from autopilot"""
        if not self.current_track or not self.current_vehicle:
            return
        
        # Get qualifying formula
        qual_formula = self.autopilot_manager.formula_manager.get_formula(
            self.current_track, self.current_vehicle, "qual"
        )
        if not qual_formula:
            track_formulas = self.autopilot_manager.formula_manager.get_all_formulas_for_track(self.current_track)
            for f in track_formulas:
                if f.session_type == "qual" and f.is_valid():
                    qual_formula = f
                    break
        
        if qual_formula and qual_formula.is_valid():
            self.qual_a = qual_formula.a
            self.qual_b = qual_formula.b
            self.qual_error_pct = qual_formula.avg_error / qual_formula.get_time_at_ratio(1.0) * 100 if qual_formula.avg_error > 0 else 0
        
        # Get race formula
        race_formula = self.autopilot_manager.formula_manager.get_formula(
            self.current_track, self.current_vehicle, "race"
        )
        if not race_formula:
            track_formulas = self.autopilot_manager.formula_manager.get_all_formulas_for_track(self.current_track)
            for f in track_formulas:
                if f.session_type == "race" and f.is_valid():
                    race_formula = f
                    break
        
        if race_formula and race_formula.is_valid():
            self.race_a = race_formula.a
            self.race_b = race_formula.b
            self.race_error_pct = race_formula.avg_error / race_formula.get_time_at_ratio(1.0) * 100 if race_formula.avg_error > 0 else 0
    
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
        
        # Update title with track name only
        if race_data.track_name:
            self.current_track = race_data.track_name
            self.title_label.setText(self.current_track)
            self.setWindowTitle(f"GTR2 Dynamic AI - {self.current_track}")
        
        # Log simplified message
        vehicle_class = get_vehicle_class(race_data.user_vehicle or "Unknown", self.class_mapping)
        logger.info(self.simplified_logger.new_data_detected(
            race_data.track_name, vehicle_class, "race",
            race_data.race_ratio or 0, race_data.best_ai_lap_sec or 0
        ))
        
        # Save race session with CORRECT vehicle per AI driver
        race_dict = race_data.to_dict()
        race_id = self.db.save_race_session(race_dict)
        
        if race_id:
            # Add data points with CORRECT vehicle for each AI driver
            points_added = 0
            for track, vehicle, ratio, lap_time, session_type in race_data.to_data_points_with_vehicles():
                try:
                    # Ensure ratio and lap_time are floats
                    ratio_float = float(ratio)
                    lap_time_float = float(lap_time)
                    if self.db.add_data_point(track, vehicle, ratio_float, lap_time_float, session_type):
                        points_added += 1
                except (ValueError, TypeError) as e:
                    logger.error(f"Failed to add data point: {e} - ratio={ratio}, lap_time={lap_time}")
            
            if points_added > 0:
                logger.info(f"📝 Saved {points_added} new data points")
            
            # Update vehicle info
            if race_data.user_vehicle:
                self.current_vehicle = race_data.user_vehicle
                self.current_vehicle_class = get_vehicle_class(self.current_vehicle, self.class_mapping)
                self.update_display()
            
            # Run autopilot
            if self.autopilot_enabled and race_data.aiw_path:
                logger.info("🤖 Running Autopilot...")
                self.autopilot_manager.reload_formulas()
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
                
                self.autopilot_manager.reload_formulas()
                self._update_formulas_from_autopilot()
                self.update_display()
    
    def load_data(self):
        """Load tracks and vehicles from database"""
        if not self.db.database_exists():
            return
        
        self.all_tracks = self.db.get_all_tracks()
        self.all_vehicles = self.db.get_all_vehicles()
        
        # Set defaults
        if self.all_tracks and not self.current_track:
            self.current_track = self.all_tracks[0]
            self.title_label.setText(self.current_track)
            self.setWindowTitle(f"GTR2 Dynamic AI - {self.current_track}")
        if self.all_vehicles and not self.current_vehicle:
            self.current_vehicle = self.all_vehicles[0]
        
        # Update vehicle class
        if self.current_vehicle:
            self.current_vehicle_class = get_vehicle_class(self.current_vehicle, self.class_mapping)
        
        # Update formulas from autopilot
        if self.autopilot_enabled:
            self._update_formulas_from_autopilot()
    
    def update_display(self):
        """Update all display elements"""
        # Vehicle info
        self.vehicle_class_label.setText(self.current_vehicle_class if self.current_vehicle_class else "-")
        self.vehicle_label.setText(self.current_vehicle if self.current_vehicle else "-")
        
        # Get current ratios from database if possible
        qual_ratio = None
        race_ratio = None
        
        if self.current_track and self.current_vehicle:
            conn = sqlite3.connect(self.db.db_path)
            cursor = conn.cursor()
            
            # Get latest qualifying ratio
            cursor.execute("""
                SELECT qual_ratio FROM race_sessions 
                WHERE track_name = ? 
                ORDER BY timestamp DESC LIMIT 1
            """, (self.current_track,))
            row = cursor.fetchone()
            if row and row[0]:
                qual_ratio = row[0]
            
            # Get latest race ratio
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
        
        # Formula quality
        if self.qual_error_pct > 0:
            quality = "Excellent" if self.qual_error_pct < 2 else "Good" if self.qual_error_pct < 5 else "Fair" if self.qual_error_pct < 10 else "Poor"
            self.qual_quality_label.setText(f"{quality} (±{self.qual_error_pct:.1f}%)")
        else:
            self.qual_quality_label.setText("Insufficient data")
        
        if self.race_error_pct > 0:
            quality = "Excellent" if self.race_error_pct < 2 else "Good" if self.race_error_pct < 5 else "Fair" if self.race_error_pct < 10 else "Poor"
            self.race_quality_label.setText(f"{quality} (±{self.race_error_pct:.1f}%)")
        else:
            self.race_quality_label.setText("Insufficient data")
        
        # Formulas
        self.qual_formula_label.setText(f"Qualifying: {get_formula_string(self.qual_a, self.qual_b)}")
        self.race_formula_label.setText(f"Race: {get_formula_string(self.race_a, self.race_b)}")
    
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
