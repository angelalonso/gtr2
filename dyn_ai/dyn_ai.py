#!/usr/bin/env python3
"""
Live AI Tuner - Redesigned GUI matching the reference image layout
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
    QLabel, QPushButton, QFrame, QMessageBox, QSizePolicy, QDialog,
    QDoubleSpinBox, QFileDialog, QLineEdit
)
from PyQt5.QtCore import Qt, pyqtSignal, QObject
from PyQt5.QtGui import QFont

from db_funcs import CurveDatabase
from formula_funcs import get_formula_string, hyperbolic, fit_curve
from gui_funcs import (
    setup_dark_theme, show_error_dialog, show_info_dialog, show_warning_dialog,
    AdvancedSettingsDialog, LogWindow, SimpleLogHandler
)
from cfg_funcs import (
    get_config_with_defaults, get_results_file_path, get_poll_interval,
    get_db_path, create_default_config_if_missing, get_base_path,
    get_autopilot_enabled, get_autopilot_silent,
    update_autopilot_enabled, update_autopilot_silent, update_base_path
)
from data_extraction import DataExtractor, RaceData, format_time
from autopilot import AutopilotManager, Formula, get_vehicle_class, load_vehicle_classes, DEFAULT_A_VALUE


logger = logging.getLogger(__name__)


class SimplifiedLogger:
    """Helper class to generate simplified, human-readable log messages"""
    
    @staticmethod
    def new_data_detected(track, vehicle_class, session_type, ratio, lap_time):
        return f"New data received for Track {track}, {session_type} session, car class {vehicle_class}"
    
    @staticmethod
    def new_ratio_calculation(old_ratio, new_ratio, ratio_name, user_lap_time, ratio_value):
        return f"New Ratio calculated for {ratio_name} session: {new_ratio:.6f} because user laptime was {user_lap_time} at Ratio {ratio_value:.6f}"
    
    @staticmethod
    def autosave_status(enabled):
        return f"Auto-harvest Data {'ON' if enabled else 'OFF'}"
    
    @staticmethod
    def autoratio_status(enabled):
        return f"Auto-calculate Ratios {'ON' if enabled else 'OFF'}"


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
            logger.debug(f"File does not exist yet: {self.file_path}")
            self.file_path.parent.mkdir(parents=True, exist_ok=True)
        
        self._update_file_state()
        self.running = True
        self._schedule_check()
        logger.debug(f"Started monitoring: {self.file_path}")
        
    def stop(self):
        self.running = False
        if self.timer:
            self.timer.cancel()
        logger.debug("Stopped monitoring")
    
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


class BasePathSelectionDialog(QDialog):
    """Dialog to select GTR2 installation base path"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.selected_path = None
        self.setup_ui()
    
    def setup_ui(self):
        self.setWindowTitle("Select GTR2 Installation Path")
        self.setFixedSize(600, 300)
        self.setModal(True)
        
        self.setStyleSheet("""
            QDialog {
                background-color: #2b2b2b;
            }
            QLabel {
                color: white;
            }
            QLineEdit {
                background-color: #3c3c3c;
                color: white;
                border: 1px solid #4CAF50;
                border-radius: 4px;
                padding: 8px;
                font-size: 12px;
            }
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton#cancel {
                background-color: #f44336;
            }
            QPushButton#cancel:hover {
                background-color: #d32f2f;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(25, 25, 25, 25)
        
        # Title
        title = QLabel("GTR2 Installation Path")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #FFA500;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        layout.addSpacing(10)
        
        # Description
        desc = QLabel(
            "Please select the root folder of your GTR2 installation.\n\n"
            "This folder should contain the 'GameData' and 'UserData' directories.\n"
            "Example: C:\\GTR2 or /home/user/GTR2"
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #aaa; font-size: 12px;")
        desc.setAlignment(Qt.AlignCenter)
        layout.addWidget(desc)
        
        layout.addSpacing(10)
        
        # Path input row
        path_layout = QHBoxLayout()
        path_layout.addWidget(QLabel("Path:"))
        
        self.path_edit = QLineEdit()
        self.path_edit.setPlaceholderText("Select or enter GTR2 installation path...")
        path_layout.addWidget(self.path_edit)
        
        self.browse_btn = QPushButton("Browse...")
        self.browse_btn.clicked.connect(self.browse_path)
        path_layout.addWidget(self.browse_btn)
        
        layout.addLayout(path_layout)
        
        # Validation message
        self.validation_label = QLabel("")
        self.validation_label.setStyleSheet("color: #FFA500; font-size: 10px;")
        layout.addWidget(self.validation_label)
        
        layout.addSpacing(20)
        
        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setObjectName("cancel")
        self.cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self.cancel_btn)
        
        self.ok_btn = QPushButton("OK")
        self.ok_btn.clicked.connect(self.accept_path)
        btn_layout.addWidget(self.ok_btn)
        
        layout.addLayout(btn_layout)
    
    def browse_path(self):
        """Open directory browser dialog"""
        directory = QFileDialog.getExistingDirectory(
            self, "Select GTR2 Installation Directory",
            str(Path.home()), QFileDialog.ShowDirsOnly
        )
        
        if directory:
            self.path_edit.setText(directory)
            self.validate_path(directory)
    
    def validate_path(self, path_str: str) -> bool:
        """Validate that the path contains GameData and UserData directories"""
        path = Path(path_str)
        
        if not path.exists():
            self.validation_label.setText("❌ Path does not exist")
            self.validation_label.setStyleSheet("color: #f44336; font-size: 10px;")
            return False
        
        game_data = path / "GameData"
        user_data = path / "UserData"
        
        if not game_data.exists():
            self.validation_label.setText("❌ GameData directory not found in this path")
            self.validation_label.setStyleSheet("color: #f44336; font-size: 10px;")
            return False
        
        if not user_data.exists():
            self.validation_label.setText("❌ UserData directory not found in this path")
            self.validation_label.setStyleSheet("color: #f44336; font-size: 10px;")
            return False
        
        log_results = user_data / "Log" / "Results"
        if not log_results.exists():
            self.validation_label.setText("⚠️ Log/Results directory not found (may be created later)")
            self.validation_label.setStyleSheet("color: #FFA500; font-size: 10px;")
        else:
            self.validation_label.setText("✓ Valid GTR2 installation path")
            self.validation_label.setStyleSheet("color: #4CAF50; font-size: 10px;")
        
        return True
    
    def accept_path(self):
        """Accept the selected path if valid"""
        path_str = self.path_edit.text().strip()
        
        if not path_str:
            self.validation_label.setText("❌ Please select a path")
            return
        
        if self.validate_path(path_str):
            self.selected_path = Path(path_str)
            self.accept()
        else:
            # Still allow if user insists? Let's require valid
            reply = QMessageBox.question(
                self, "Continue Anyway?",
                "The selected path does not appear to be a valid GTR2 installation.\n"
                "The application may not work correctly.\n\n"
                "Continue anyway?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                self.selected_path = Path(path_str)
                self.accept()


class AccuracyIndicator(QLabel):
    """Visual indicator for formula accuracy with color coding"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignCenter)
        self.setMinimumWidth(150)
        self.setMinimumHeight(50)
        self.current_accuracy = 0
        self.confidence = 0
        self.data_points = 0
        self.outliers = 0
        self.setStyleSheet("""
            QLabel {
                background-color: #3c3c3c;
                border-radius: 8px;
                padding: 5px;
                font-family: monospace;
                font-size: 11px;
            }
        """)
        self.update_display()
    
    def set_accuracy(self, confidence: float, data_points_used: int, 
                     avg_error: float = None, max_error: float = None,
                     outliers: int = 0):
        """Set accuracy based on formula confidence and data points."""
        self.data_points = data_points_used
        self.outliers = outliers
        
        # Base accuracy from data points count
        if data_points_used == 0:
            base_accuracy = 0
            confidence_text = "No Data"
        elif data_points_used == 1:
            base_accuracy = 25
            confidence_text = "Single Point"
        elif data_points_used <= 3:
            base_accuracy = 50
            confidence_text = "Low Data"
        elif data_points_used <= 5:
            base_accuracy = 65
            confidence_text = "Fair"
        elif data_points_used <= 9:
            base_accuracy = 80
            confidence_text = "Good"
        else:
            base_accuracy = 90
            confidence_text = "High Data"
        
        # Adjust based on confidence parameter
        if confidence > 0:
            confidence_bonus = min(10, int(confidence * 10))
        else:
            confidence_bonus = 0
        
        # Error-based adjustment
        error_penalty = 0
        if avg_error is not None and avg_error > 0:
            error_penalty = min(10, int(avg_error * 10))
        
        # Outlier penalty
        outlier_penalty = min(20, outliers * 5)
        
        # Calculate final accuracy
        self.current_accuracy = base_accuracy + confidence_bonus - error_penalty - outlier_penalty
        self.current_accuracy = max(0, min(100, self.current_accuracy))
        
        # Store values for display
        self.confidence = confidence
        self.confidence_text = confidence_text
        
        # Determine color based on accuracy
        if self.current_accuracy >= 80:
            color = "#4CAF50"
            bg_color = "#1a3a1a"
            bar_color = "#4CAF50"
        elif self.current_accuracy >= 60:
            color = "#FFC107"
            bg_color = "#3a3a1a"
            bar_color = "#FFC107"
        elif self.current_accuracy >= 40:
            color = "#FF9800"
            bg_color = "#3a2a1a"
            bar_color = "#FF9800"
        else:
            color = "#f44336"
            bg_color = "#3a1a1a"
            bar_color = "#f44336"
        
        outlier_text = f"⚠️ {outliers} outlier{'s' if outliers != 1 else ''}" if outliers > 0 else ""
        
        html = f"""
        <div style="text-align: center;">
            <div style="color: {color}; font-weight: bold; font-size: 12px;">
                ACCURACY: {self.current_accuracy}%
            </div>
            <div style="background-color: #2b2b2b; border-radius: 4px; height: 8px; margin: 4px 0;">
                <div style="background-color: {bar_color}; width: {self.current_accuracy}%; height: 8px; border-radius: 4px;"></div>
            </div>
            <div style="color: #aaa; font-size: 9px;">
                {confidence_text} ({data_points_used} point{'s' if data_points_used != 1 else ''})
                {outlier_text}
            </div>
        </div>
        """
        
        self.setStyleSheet(f"""
            QLabel {{
                background-color: {bg_color};
                border-radius: 8px;
                padding: 8px;
                font-family: monospace;
                font-size: 11px;
            }}
        """)
        self.setText(html)
    
    def update_display(self):
        self.set_accuracy(self.confidence, self.data_points, None, None, self.outliers)


class ManualEditDialog(QDialog):
    """Dialog for manually editing a ratio in the AIW file"""
    
    def __init__(self, parent, ratio_name: str, current_ratio: float, aiw_path: Path = None):
        super().__init__(parent)
        self.ratio_name = ratio_name
        self.current_ratio = current_ratio
        self.aiw_path = aiw_path
        self.new_ratio = None
        self.setup_ui()
    
    def setup_ui(self):
        self.setWindowTitle(f"Manual Edit - {self.ratio_name}")
        self.setFixedSize(400, 250)
        self.setStyleSheet("""
            QDialog {
                background-color: #2b2b2b;
            }
            QLabel {
                color: white;
            }
            QDoubleSpinBox {
                background-color: #3c3c3c;
                color: white;
                border: 1px solid #4CAF50;
                border-radius: 4px;
                padding: 4px;
                font-size: 14px;
            }
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton#cancel {
                background-color: #555;
            }
            QPushButton#cancel:hover {
                background-color: #666;
            }
        """)
        
        layout = QVBoxLayout(self)
        
        # Title
        title = QLabel(f"Edit {self.ratio_name}")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #FFA500;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        layout.addSpacing(10)
        
        # Current value display
        current_label = QLabel(f"Current {self.ratio_name}:")
        current_label.setStyleSheet("color: #888;")
        layout.addWidget(current_label)
        
        current_value = QLabel(f"{self.current_ratio:.6f}")
        current_value.setStyleSheet("font-size: 14px; font-family: monospace; color: #4CAF50;")
        layout.addWidget(current_value)
        
        layout.addSpacing(15)
        
        # New value input
        new_label = QLabel(f"New {self.ratio_name}:")
        new_label.setStyleSheet("color: #888;")
        layout.addWidget(new_label)
        
        self.ratio_spin = QDoubleSpinBox()
        self.ratio_spin.setRange(0.3, 3.0)
        self.ratio_spin.setDecimals(6)
        self.ratio_spin.setSingleStep(0.01)
        self.ratio_spin.setValue(self.current_ratio)
        self.ratio_spin.setStyleSheet("font-size: 14px;")
        layout.addWidget(self.ratio_spin)
        
        layout.addSpacing(10)
        
        # Info about AIW path
        if self.aiw_path:
            info = QLabel(f"AIW: {self.aiw_path.name}")
            info.setStyleSheet("color: #666; font-size: 9px;")
            info.setWordWrap(True)
            layout.addWidget(info)
        
        layout.addSpacing(20)
        
        # Buttons
        btn_layout = QHBoxLayout()
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setObjectName("cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        
        apply_btn = QPushButton("Apply")
        apply_btn.clicked.connect(self.accept)
        btn_layout.addWidget(apply_btn)
        
        layout.addLayout(btn_layout)
    
    def accept(self):
        self.new_ratio = self.ratio_spin.value()
        super().accept()


class RatioPanel(QFrame):
    """Panel for displaying Qualifying or Race ratio information with accuracy indicator and edit button"""
    
    edit_complete = pyqtSignal(float)
    
    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.title = title
        self.current_ratio = None
        self.last_read_ratio = None  # Store the ratio read from AIW file
        self.setup_ui()
        
    def setup_ui(self):
        self.setFrameStyle(QFrame.NoFrame)
        self.setStyleSheet("""
            QFrame {
                background-color: #2b2b2b;
                border-radius: 10px;
            }
            QLabel {
                color: white;
            }
            QPushButton#edit_btn {
                background-color: #2196F3;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 6px 12px;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton#edit_btn:hover {
                background-color: #1976D2;
            }
            QPushButton#edit_btn:disabled {
                background-color: #555;
                color: #888;
            }
        """)
        
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMinimumHeight(420)  # Increased to accommodate last ratio read
        
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(25, 25, 25, 25)
        
        # Title row with edit button
        title_layout = QHBoxLayout()
        
        self.title_label = QLabel(self.title)
        self.title_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #aaa;")
        self.title_label.setAlignment(Qt.AlignCenter)
        title_layout.addWidget(self.title_label, stretch=1)
        
        # Edit button
        self.edit_btn = QPushButton("✎ Edit")
        self.edit_btn.setObjectName("edit_btn")
        self.edit_btn.setFixedSize(70, 28)
        self.edit_btn.clicked.connect(self.on_edit_clicked)
        title_layout.addWidget(self.edit_btn)
        
        layout.addLayout(title_layout)
        
        layout.addSpacing(10)
        
        # Current ratio value (calculated/active)
        ratio_label = QLabel("Current Ratio:")
        ratio_label.setStyleSheet("font-size: 11px; color: #888;")
        layout.addWidget(ratio_label)
        
        self.ratio_label = QLabel("-")
        self.ratio_label.setStyleSheet("font-size: 38px; font-weight: bold; font-family: monospace; color: #FFA500;")
        self.ratio_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.ratio_label)
        
        # Last read ratio (smaller, below)
        self.last_read_label = QLabel("last ratio read: --")
        self.last_read_label.setStyleSheet("font-size: 10px; color: #666; font-family: monospace; margin-top: -5px;")
        self.last_read_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.last_read_label)
        
        layout.addSpacing(15)
        
        # Expected Best Laptimes label
        expected_label = QLabel("Expected Best Laptimes:")
        expected_label.setStyleSheet("font-size: 12px; color: #888;")
        layout.addWidget(expected_label)
        
        # AI range
        self.ai_range_label = QLabel("AI: -- - --")
        self.ai_range_label.setStyleSheet("font-size: 15px; font-family: monospace; color: #FFA500;")
        layout.addWidget(self.ai_range_label)
        
        layout.addSpacing(10)
        
        # User time
        self.user_time_label = QLabel("User: --")
        self.user_time_label.setStyleSheet("font-size: 15px; font-family: monospace; color: #4CAF50; font-weight: bold;")
        layout.addWidget(self.user_time_label)
        
        layout.addStretch()
        
        # Formula - lighter color
        self.formula_label = QLabel("")
        self.formula_label.setStyleSheet("color: #888; font-size: 10px; font-family: monospace; margin-top: 10px;")
        self.formula_label.setWordWrap(True)
        self.formula_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.formula_label)
        
        # Accuracy indicator
        self.accuracy_indicator = AccuracyIndicator()
        layout.addWidget(self.accuracy_indicator)
    
    def update_ratio(self, ratio: Optional[float]):
        self.current_ratio = ratio
        if ratio is not None:
            self.ratio_label.setText(f"{ratio:.6f}")
        else:
            self.ratio_label.setText("-")
    
    def update_last_read_ratio(self, ratio: Optional[float]):
        """Update the 'last ratio read' display - shows what was read from AIW"""
        self.last_read_ratio = ratio
        if ratio is not None:
            self.last_read_label.setText(f"last ratio read: {ratio:.6f}")
            self.last_read_label.setStyleSheet("font-size: 10px; color: #FFA500; font-family: monospace; margin-top: -5px;")
        else:
            self.last_read_label.setText("last ratio read: --")
            self.last_read_label.setStyleSheet("font-size: 10px; color: #666; font-family: monospace; margin-top: -5px;")
    
    def update_ai_range(self, best: Optional[float], worst: Optional[float]):
        if best is not None and worst is not None:
            self.ai_range_label.setText(f"AI: {format_time(best)} - {format_time(worst)}")
        else:
            self.ai_range_label.setText("AI: -- - --")
    
    def update_user_time(self, time_sec: Optional[float]):
        if time_sec is not None and time_sec > 0:
            self.user_time_label.setText(f"User: {format_time(time_sec)}")
        else:
            self.user_time_label.setText("User: --")
    
    def update_formula(self, a: float, b: float):
        self.formula_label.setText(f"T = {a:.2f} / R + {b:.2f}")
    
    def update_accuracy(self, confidence: float, data_points_used: int, 
                        avg_error: float = None, max_error: float = None,
                        outliers: int = 0):
        self.accuracy_indicator.set_accuracy(confidence, data_points_used, 
                                             avg_error, max_error, outliers)
    
    def set_edit_enabled(self, enabled: bool):
        self.edit_btn.setEnabled(enabled)
    
    def on_edit_clicked(self):
        if self.current_ratio is None:
            return
        dialog = ManualEditDialog(self, self.title, self.current_ratio)
        if dialog.exec_() == QDialog.Accepted and dialog.new_ratio is not None:
            self.edit_complete.emit(dialog.new_ratio)


class GTR2Logo(QLabel):
    """Custom GTR² logo with gray GTR and red ²"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setText("GTR²")
        self.setStyleSheet("""
            QLabel {
                font-size: 40px;
                font-weight: bold;
            }
        """)
        self.setTextFormat(Qt.RichText)
        self.setText('<span style="color: #888888;">GTR</span><span style="color: #FF4444;">²</span>')


class RedesignedMainWindow(QMainWindow):
    """Redesigned main window matching the reference image layout exactly"""
    
    # Class-level signal for data refresh notifications
    data_refresh_signal = pyqtSignal()
    
    def __init__(self, db_path: str = "ai_data.db", config_file: str = "cfg.yml"):
        super().__init__()
        self.setWindowTitle("GTR2 Dynamic AI")
        self.setGeometry(100, 100, 950, 700)
        self.setMinimumWidth(850)
        self.setMinimumHeight(600)
        
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
        
        # Autopilot manager
        self.autopilot_manager = AutopilotManager(self.db)
        
        # State
        self.autosave_enabled = True
        self.autoratio_enabled = False
        self.autopilot_manager.set_enabled(self.autoratio_enabled)
        
        # AI Target settings
        self.ai_target_settings = {
            "mode": "percentage",
            "percentage": 50,
            "offset_seconds": 0.0,
            "error_margin": 0.0
        }
        
        # Current formulas - ALWAYS use fixed a=32, only b changes
        self.qual_a: float = DEFAULT_A_VALUE
        self.qual_b: float = 70.0
        self.race_a: float = DEFAULT_A_VALUE
        self.race_b: float = 70.0
        
        # Current data
        self.current_track: str = ""
        self.current_vehicle: str = ""
        self.current_vehicle_class: str = ""
        
        # AI lap times
        self.qual_best_ai = None
        self.qual_worst_ai = None
        self.race_best_ai = None
        self.race_worst_ai = None
        
        # User lap times
        self.user_qualifying_sec: float = 0.0
        self.user_best_lap_sec: float = 0.0
        self.last_qual_ratio: Optional[float] = None
        self.last_race_ratio: Optional[float] = None
        
        # Store the original ratios read from AIW (for display)
        self.qual_read_ratio: Optional[float] = None
        self.race_read_ratio: Optional[float] = None
        
        # Advanced settings window
        self.advanced_window = None
        
        # Daemon
        self.daemon = None
        
        self.setup_ui()
        
        # Check and set base path before loading data
        if not self.ensure_base_path():
            # User canceled or no path selected - exit?
            QMessageBox.critical(self, "No Path Selected",
                "GTR2 installation path is required for the application to work.\n\n"
                "Please run the application again and select the correct path.")
            self.close()
            return
        
        self.load_data()
        self.update_display()
        
        # Auto-start daemon
        base_path = get_base_path(config_file)
        if base_path:
            self.start_daemon()
    
    def ensure_base_path(self) -> bool:
        """Ensure that a valid base path is configured. Returns True if path is set."""
        config = get_config_with_defaults(self.config_file)
        base_path = config.get('base_path', '')
        
        # Check if base_path exists and is valid
        if not base_path or not Path(base_path).exists():
            # Check if the path contains GameData directory
            path = Path(base_path) if base_path else None
            if not path or not (path / "GameData").exists() or not (path / "UserData").exists():
                # Ask user for base path
                dialog = BasePathSelectionDialog(self)
                if dialog.exec_() == QDialog.Accepted and dialog.selected_path:
                    update_base_path(dialog.selected_path, self.config_file)
                    logger.info(f"Base path set to: {dialog.selected_path}")
                    return True
                else:
                    return False
        
        # Validate the existing path
        path = Path(base_path)
        if (path / "GameData").exists() and (path / "UserData").exists():
            return True
        else:
            # Path exists but doesn't contain required directories
            reply = QMessageBox.question(self, "Invalid Path",
                f"The configured path '{base_path}' does not appear to be a valid GTR2 installation.\n\n"
                "Would you like to select a different path?",
                QMessageBox.Yes | QMessageBox.No)
            
            if reply == QMessageBox.Yes:
                dialog = BasePathSelectionDialog(self)
                if dialog.exec_() == QDialog.Accepted and dialog.selected_path:
                    update_base_path(dialog.selected_path, self.config_file)
                    logger.info(f"Base path updated to: {dialog.selected_path}")
                    return True
            return False
    
    def setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setSpacing(25)
        main_layout.setContentsMargins(30, 30, 30, 30)
        
        # === Header section ===
        header_layout = QHBoxLayout()
        
        # GTR² logo
        logo_label = GTR2Logo()
        header_layout.addWidget(logo_label)
        
        header_layout.addStretch()
        
        # Track name
        self.track_label = QLabel("-")
        self.track_label.setStyleSheet("font-size: 28px; font-weight: bold; color: white;")
        header_layout.addWidget(self.track_label)
        
        header_layout.addStretch()
        
        # Empty spacer for balance
        header_layout.addSpacing(80)
        
        main_layout.addLayout(header_layout)
        
        # Car class (below track)
        self.car_class_label = QLabel("Car Class: -")
        self.car_class_label.setStyleSheet("font-size: 14px; color: #4CAF50; margin-bottom: 10px;")
        main_layout.addWidget(self.car_class_label)
        
        main_layout.addSpacing(20)
        
        # === Two-column layout for Quali and Race panels ===
        panels_layout = QHBoxLayout()
        panels_layout.setSpacing(30)
        
        # Qualifying panel
        self.qual_panel = RatioPanel("Quali-Ratio")
        self.qual_panel.edit_complete.connect(lambda ratio: self.on_manual_edit("qual", ratio))
        panels_layout.addWidget(self.qual_panel)
        
        # Race panel
        self.race_panel = RatioPanel("Race-Ratio")
        self.race_panel.edit_complete.connect(lambda ratio: self.on_manual_edit("race", ratio))
        panels_layout.addWidget(self.race_panel)
        
        main_layout.addLayout(panels_layout)
        
        main_layout.addSpacing(30)
        
        # === Control buttons row ===
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(20)
        
        # Auto-harvest Data toggle
        self.autosave_switch = ToggleSwitch("Auto-harvest Data (ON)", "Auto-harvest Data (OFF)")
        self.autosave_switch.set_checked(self.autosave_enabled)
        self.autosave_switch.clicked.connect(self.toggle_autosave)
        buttons_layout.addWidget(self.autosave_switch)
        
        # Auto-calculate Ratios toggle
        self.autoratio_switch = ToggleSwitch("Auto-calculate Ratios (ON)", "Auto-calculate Ratios (OFF)")
        self.autoratio_switch.set_checked(self.autoratio_enabled)
        self.autoratio_switch.clicked.connect(self.toggle_autoratio)
        buttons_layout.addWidget(self.autoratio_switch)
        
        buttons_layout.addStretch()
        
        # Advanced button
        self.advanced_btn = QPushButton("Advanced")
        self.advanced_btn.setMinimumHeight(36)
        self.advanced_btn.setMinimumWidth(100)
        self.advanced_btn.setStyleSheet("""
            QPushButton {
                background-color: #9C27B0;
                color: white;
                padding: 8px 24px;
                border: none;
                border-radius: 4px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #7B1FA2;
            }
        """)
        self.advanced_btn.clicked.connect(self.open_advanced_settings)
        buttons_layout.addWidget(self.advanced_btn)
        
        # Exit button
        self.exit_btn = QPushButton("Exit")
        self.exit_btn.setMinimumHeight(36)
        self.exit_btn.setMinimumWidth(100)
        self.exit_btn.setStyleSheet("""
            QPushButton {
                background-color: #555;
                color: white;
                padding: 8px 24px;
                border: none;
                border-radius: 4px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #666;
            }
        """)
        self.exit_btn.clicked.connect(self.close)
        buttons_layout.addWidget(self.exit_btn)
        
        main_layout.addLayout(buttons_layout)
        
        # Status bar
        self.statusBar().showMessage("Ready")
        self.statusBar().setStyleSheet("QStatusBar { color: #888; }")
        
        # Set dark background
        self.setStyleSheet("""
            QMainWindow {
                background-color: #1e1e1e;
            }
            QLabel {
                color: white;
            }
        """)
    
    def toggle_autosave(self):
        """Toggle autosave mode"""
        self.autosave_enabled = self.autosave_switch.is_checked()
        logger.info(self.simplified_logger.autosave_status(self.autosave_enabled))
        self.statusBar().showMessage(f"Auto-harvest Data {'ON' if self.autosave_enabled else 'OFF'}", 2000)
    
    def toggle_autoratio(self):
        """Toggle autoratio mode"""
        self.autoratio_enabled = self.autoratio_switch.is_checked()
        self.autopilot_manager.set_enabled(self.autoratio_enabled)
        
        # Enable/disable manual edit buttons
        self.qual_panel.set_edit_enabled(not self.autoratio_enabled)
        self.race_panel.set_edit_enabled(not self.autoratio_enabled)
        
        logger.info(self.simplified_logger.autoratio_status(self.autoratio_enabled))
        self.statusBar().showMessage(f"Auto-calculate Ratios {'ON' if self.autoratio_enabled else 'OFF'}", 2000)
        
        if self.autoratio_enabled:
            self.autopilot_manager.reload_formulas()
            self._update_formulas_from_autopilot()
            self.update_display()
            # Update accuracy after reload
            if self.current_track and self.current_vehicle_class:
                self.update_formula_accuracy("qual")
                self.update_formula_accuracy("race")
    
    def _get_ai_times_for_track(self, track: str, session_type: str) -> Tuple[Optional[float], Optional[float]]:
        """Get best and worst AI lap times for a track from the database"""
        conn = sqlite3.connect(self.db.db_path)
        cursor = conn.cursor()
        
        if session_type == "qual":
            cursor.execute("""
                SELECT qual_time_sec FROM ai_results ar
                JOIN race_sessions rs ON ar.race_id = rs.race_id
                WHERE rs.track_name = ? AND ar.qual_time_sec > 0
                ORDER BY ar.qual_time_sec
                LIMIT 1
            """, (track,))
            best_row = cursor.fetchone()
            
            cursor.execute("""
                SELECT qual_time_sec FROM ai_results ar
                JOIN race_sessions rs ON ar.race_id = rs.race_id
                WHERE rs.track_name = ? AND ar.qual_time_sec > 0
                ORDER BY ar.qual_time_sec DESC
                LIMIT 1
            """, (track,))
            worst_row = cursor.fetchone()
        else:
            cursor.execute("""
                SELECT best_lap_sec FROM ai_results ar
                JOIN race_sessions rs ON ar.race_id = rs.race_id
                WHERE rs.track_name = ? AND ar.best_lap_sec > 0
                ORDER BY ar.best_lap_sec
                LIMIT 1
            """, (track,))
            best_row = cursor.fetchone()
            
            cursor.execute("""
                SELECT best_lap_sec FROM ai_results ar
                JOIN race_sessions rs ON ar.race_id = rs.race_id
                WHERE rs.track_name = ? AND ar.best_lap_sec > 0
                ORDER BY ar.best_lap_sec DESC
                LIMIT 1
            """, (track,))
            worst_row = cursor.fetchone()
        
        conn.close()
        
        best = best_row[0] if best_row else None
        worst = worst_row[0] if worst_row else None
        return best, worst
    
    def update_formula_accuracy(self, session_type: str):
        """Update the accuracy indicator for a session type"""
        if not self.current_track or not self.current_vehicle_class:
            return
            
        formula = self.autopilot_manager.formula_manager.get_formula_by_class(
            self.current_track, self.current_vehicle_class, session_type
        )
        
        if formula and formula.is_valid():
            # Get data points for this track/class/session to calculate outliers
            data_points = self.autopilot_manager.engine._get_data_points(
                self.current_track, self.current_vehicle_class, session_type
            )
            
            # Calculate outliers (points where error > 0.5 seconds)
            outliers = 0
            avg_error = None
            if data_points and len(data_points) > 1:
                total_error = 0
                for ratio, lap_time in data_points:
                    predicted = formula.get_time_at_ratio(ratio)
                    error = abs(predicted - lap_time)
                    total_error += error
                    if error > 0.5:
                        outliers += 1
                avg_error = total_error / len(data_points)
            
            panel = self.qual_panel if session_type == "qual" else self.race_panel
            panel.update_accuracy(
                confidence=formula.confidence,
                data_points_used=formula.data_points_used,
                avg_error=avg_error,
                max_error=formula.max_error if formula.max_error > 0 else None,
                outliers=outliers
            )
        else:
            # No formula exists - show 0 accuracy
            panel = self.qual_panel if session_type == "qual" else self.race_panel
            panel.update_accuracy(0, 0, None, None, 0)
    
    def on_manual_edit(self, session_type: str, new_ratio: float):
        """Handle manual ratio edit from panel button"""
        if self.autoratio_enabled:
            show_warning_dialog(self, "Auto-Ratio Enabled", 
                "Manual editing is disabled while Auto-calculate Ratios is ON.\n"
                "Please turn off Auto-calculate Ratios to manually edit.")
            # Re-disable the button if it somehow got enabled
            if session_type == "qual":
                self.qual_panel.set_edit_enabled(False)
            else:
                self.race_panel.set_edit_enabled(False)
            return
        
        # Find the AIW path
        if not self.current_track:
            show_warning_dialog(self, "No Track", "No track data available.")
            return
        
        # Try to get AIW path
        aiw_path = None
        if hasattr(self, 'daemon') and self.daemon and self.daemon.base_path:
            locations_dir = self.daemon.base_path / "GameData" / "Locations"
            if locations_dir.exists():
                for track_dir in locations_dir.iterdir():
                    if track_dir.is_dir() and track_dir.name.lower() == self.current_track.lower():
                        for ext in ["*.AIW", "*.aiw"]:
                            aiw_files = list(track_dir.glob(ext))
                            if aiw_files:
                                aiw_path = aiw_files[0]
                                break
                        break
        
        if not aiw_path or not aiw_path.exists():
            # Ask user to locate AIW file
            aiw_path_str, _ = QFileDialog.getOpenFileName(
                self, f"Select AIW file for {self.current_track}",
                str(Path.cwd()), "AIW Files (*.AIW *.aiw)"
            )
            if aiw_path_str:
                aiw_path = Path(aiw_path_str)
            else:
                show_warning_dialog(self, "AIW Not Found", 
                    f"Could not find AIW file for {self.current_track}.\n"
                    f"Please locate the AIW file manually.")
                return
        
        # Update the AIW file
        ratio_name = "QualRatio" if session_type == "qual" else "RaceRatio"
        if self.autopilot_manager.engine._update_aiw_ratio(aiw_path, ratio_name, new_ratio):
            # Update stored ratio
            if session_type == "qual":
                self.last_qual_ratio = new_ratio
                self.qual_panel.update_ratio(new_ratio)
            else:
                self.last_race_ratio = new_ratio
                self.race_panel.update_ratio(new_ratio)
            
            logger.info(f"Manually updated {ratio_name} to {new_ratio:.6f}")
            self.statusBar().showMessage(f"{ratio_name} updated to {new_ratio:.6f}", 3000)
            
            # Ask if user wants to save this as a formula
            reply = QMessageBox.question(self, "Save Formula", 
                f"Do you want to save this {session_type.upper()} ratio as a formula?\n\n"
                f"This will create/update the formula for {self.current_track}/{self.current_vehicle_class}.",
                QMessageBox.Yes | QMessageBox.No)
            
            if reply == QMessageBox.Yes:
                # Create/update formula with new ratio at current user time
                target_time = None
                if session_type == "qual" and self.user_qualifying_sec > 0:
                    target_time = self.user_qualifying_sec
                elif session_type == "race" and self.user_best_lap_sec > 0:
                    target_time = self.user_best_lap_sec
                
                if target_time and target_time > 0:
                    new_formula = Formula.from_point(
                        self.current_track, self.current_vehicle_class, 
                        new_ratio, target_time, session_type, DEFAULT_A_VALUE
                    )
                    self.autopilot_manager.formula_manager.save_formula(new_formula)
                    self.autopilot_manager.reload_formulas()
                    self._update_formulas_from_autopilot()
                    self.update_display()
                    self.update_formula_accuracy(session_type)
                    logger.debug(f"Saved formula from manual edit: {new_formula.get_formula_string()}")
                else:
                    show_warning_dialog(self, "No Lap Time", 
                        f"No user {session_type} lap time available to create formula.")
        else:
            show_error_dialog(self, "Update Failed", f"Failed to update {ratio_name} in AIW file.")
    
    def _update_formulas_from_autopilot(self):
        """Update current formulas from autopilot - keeps a fixed, only b changes"""
        if not self.current_track or not self.current_vehicle_class:
            if self.current_vehicle:
                self.current_vehicle_class = get_vehicle_class(self.current_vehicle, self.class_mapping)
            if not self.current_vehicle_class:
                return
        
        # Get qualifying formula - a should always be DEFAULT_A_VALUE (32)
        qual_formula = self.autopilot_manager.formula_manager.get_formula_by_class(
            self.current_track, self.current_vehicle_class, "qual"
        )
        if qual_formula and qual_formula.is_valid():
            self.qual_a = DEFAULT_A_VALUE  # Force a to be default
            self.qual_b = qual_formula.b   # Only take b from stored formula
        else:
            self.qual_a = DEFAULT_A_VALUE
            self.qual_b = 70.0
        
        # Get race formula - a should always be DEFAULT_A_VALUE (32)
        race_formula = self.autopilot_manager.formula_manager.get_formula_by_class(
            self.current_track, self.current_vehicle_class, "race"
        )
        if race_formula and race_formula.is_valid():
            self.race_a = DEFAULT_A_VALUE  # Force a to be default
            self.race_b = race_formula.b   # Only take b from stored formula
        else:
            self.race_a = DEFAULT_A_VALUE
            self.race_b = 70.0
    
    def _fit_b_from_data_points(self, session_type: str, ratio: float, ai_times: List[float]) -> Optional[float]:
        """
        Calculate b value from AI data points.
        Using T = a/R + b, we solve for b: b = T - a/R
        For multiple points, use the average of the calculated b values.
        """
        if not ai_times:
            return None
        
        # Calculate b for each AI time at the given ratio
        b_values = []
        for ai_time in ai_times:
            b = ai_time - (DEFAULT_A_VALUE / ratio)
            b_values.append(b)
        
        # Use the average b value
        avg_b = sum(b_values) / len(b_values)
        # Clamp b to reasonable range
        avg_b = max(10.0, min(200.0, avg_b))
        
        logger.debug(f"  Fitted b from {len(ai_times)} points at ratio {ratio:.4f}: b={avg_b:.4f}")
        return avg_b
    
    def _update_formula_from_new_data(self, race_data: RaceData, session_type: str) -> bool:
        """
        Update formula based on new AI data.
        Keeps a fixed at DEFAULT_A_VALUE (32), only calculates a new b value.
        Returns True if formula was updated.
        """
        if not self.current_track or not self.current_vehicle_class:
            return False
        
        # Get the ratio and AI times for this session type
        if session_type == "qual":
            current_ratio = race_data.qual_ratio
            best_ai = race_data.qual_best_ai_lap_sec
            worst_ai = race_data.qual_worst_ai_lap_sec
        else:
            current_ratio = race_data.race_ratio
            best_ai = race_data.best_ai_lap_sec
            worst_ai = race_data.worst_ai_lap_sec
        
        if not current_ratio or current_ratio <= 0:
            logger.debug(f"  No ratio available for {session_type}")
            return False
        
        # Collect all AI times at this ratio
        ai_times = []
        
        # Add best and worst as the range
        if best_ai and best_ai > 0:
            ai_times.append(best_ai)
        if worst_ai and worst_ai > 0:
            ai_times.append(worst_ai)
        
        # Also get all AI results from the race data for more points
        for ai in race_data.ai_results:
            if session_type == "qual" and ai.get('qual_time_sec', 0) > 0:
                ai_times.append(ai['qual_time_sec'])
            elif session_type == "race" and ai.get('best_lap_sec', 0) > 0:
                ai_times.append(ai['best_lap_sec'])
        
        if not ai_times:
            logger.debug(f"  No AI times available for {session_type}")
            return False
        
        # Fit b from the AI data points
        new_b = self._fit_b_from_data_points(session_type, current_ratio, ai_times)
        
        if new_b is None:
            return False
        
        # Update the formula in the database (with fixed a=32, new b)
        formula = Formula(
            track=self.current_track,
            vehicle_class=self.current_vehicle_class,
            a=DEFAULT_A_VALUE,
            b=new_b,
            session_type=session_type,
            data_points_used=len(ai_times),
            confidence=0.7 if len(ai_times) >= 2 else 0.5
        )
        
        if formula.is_valid():
            self.autopilot_manager.formula_manager.save_formula(formula)
            
            # Update local variables
            if session_type == "qual":
                self.qual_b = new_b
            else:
                self.race_b = new_b
            
            logger.info(f"  Updated {session_type} formula: T = {DEFAULT_A_VALUE:.0f} / R + {new_b:.4f} (from {len(ai_times)} AI times at ratio {current_ratio:.4f})")
            return True
        
        return False
    
    def _calculate_ratio_for_user_time(self, user_time: float, session_type: str) -> Optional[float]:
        """
        Calculate the ratio that would give the user's lap time using the current formula.
        Formula: R = a / (T - b)
        """
        if session_type == "qual":
            a = DEFAULT_A_VALUE
            b = self.qual_b
        else:
            a = DEFAULT_A_VALUE
            b = self.race_b
        
        denominator = user_time - b
        if denominator <= 0:
            logger.debug(f"  Denominator <= 0: {user_time} - {b} = {denominator}")
            return None
        
        ratio = a / denominator
        
        if 0.3 < ratio < 3.0:
            return ratio
        else:
            logger.debug(f"  Calculated ratio {ratio:.6f} out of range (0.3-3.0)")
            return None
    
    def open_advanced_settings(self):
        """Open the advanced settings window"""
        if self.advanced_window is None:
            self.advanced_window = AdvancedSettingsDialog(self, self.db, self.log_window)
            self.advanced_window.data_updated.connect(self.on_data_updated)
            self.advanced_window.formula_updated.connect(self.on_formula_updated)
            # Connect the data refresh signal
            self.data_refresh_signal.connect(self.advanced_window.on_parent_data_refresh)
        
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
        """
        Handle formula updates from advanced settings.
        Note: We ignore the 'a' value from the dialog and keep DEFAULT_A_VALUE.
        """
        if session_type == "qual":
            self.qual_b = b  # Only take b, keep a fixed
        else:
            self.race_b = b  # Only take b, keep a fixed
        self.update_display()
        self.update_formula_accuracy(session_type)
    
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
        logger.debug(f"Monitoring: {file_path}")
    
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
        
        # Store the ORIGINAL ratios read from AIW (before any modification)
        if race_data.qual_ratio:
            self.qual_read_ratio = race_data.qual_ratio
            # Update the "last ratio read" display
            self.qual_panel.update_last_read_ratio(self.qual_read_ratio)
        if race_data.race_ratio:
            self.race_read_ratio = race_data.race_ratio
            # Update the "last ratio read" display
            self.race_panel.update_last_read_ratio(self.race_read_ratio)
        
        # Store the current active ratios (will be updated if modified)
        if race_data.qual_ratio:
            self.last_qual_ratio = race_data.qual_ratio
        if race_data.race_ratio:
            self.last_race_ratio = race_data.race_ratio
        
        # Store AI lap times from the race data
        if race_data.qual_best_ai_lap_sec:
            self.qual_best_ai = race_data.qual_best_ai_lap_sec
        if race_data.qual_worst_ai_lap_sec:
            self.qual_worst_ai = race_data.qual_worst_ai_lap_sec
        if race_data.best_ai_lap_sec:
            self.race_best_ai = race_data.best_ai_lap_sec
        if race_data.worst_ai_lap_sec:
            self.race_worst_ai = race_data.worst_ai_lap_sec
        
        # Update vehicle info
        if race_data.user_vehicle:
            self.current_vehicle = race_data.user_vehicle
            self.current_vehicle_class = get_vehicle_class(self.current_vehicle, self.class_mapping)
            self.car_class_label.setText(f"Car Class: {self.current_vehicle_class}")
        
        # Determine session type string for logging
        has_qual = race_data.qual_ratio and race_data.qual_best_ai_lap_sec > 0 and race_data.qual_worst_ai_lap_sec > 0
        has_race = race_data.race_ratio and race_data.best_ai_lap_sec > 0 and race_data.worst_ai_lap_sec > 0
        
        session_type_str = ""
        if has_qual and has_race:
            session_type_str = "both"
        elif has_qual:
            session_type_str = "qualifying"
        elif has_race:
            session_type_str = "race"
        
        if session_type_str:
            logger.info(self.simplified_logger.new_data_detected(
                race_data.track_name, self.current_vehicle_class, session_type_str,
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
                logger.debug(f"Saved {points_added} new data points")
        
        # Update formula from AI data ONLY (keep a fixed at 32, update b)
        if self.current_track and self.current_vehicle_class:
            # Update qualifying formula from AI data
            if has_qual:
                self._update_formula_from_new_data(race_data, "qual")
            # Update race formula from AI data
            if has_race:
                self._update_formula_from_new_data(race_data, "race")
        
        # Reload formulas from database
        self.autopilot_manager.reload_formulas()
        self._update_formulas_from_autopilot()
        self.update_display()
        
        # Update accuracy indicators
        if self.current_track and self.current_vehicle_class:
            self.update_formula_accuracy("qual")
            self.update_formula_accuracy("race")
        
        # Run autoratio if enabled - this calculates the new ratio for the AIW file
        if self.autoratio_enabled and race_data.aiw_path:
            logger.debug("Running Autoratio...")
            
            # Calculate the ratio that would give the user's time with the current formula
            # This is the NEW ratio to write to the AIW file
            if self.user_qualifying_sec > 0 and self.last_qual_ratio:
                new_qual_ratio = self._calculate_ratio_for_user_time(self.user_qualifying_sec, "qual")
                if new_qual_ratio and abs(new_qual_ratio - self.last_qual_ratio) > 0.000001:
                    logger.info(self.simplified_logger.new_ratio_calculation(
                        self.last_qual_ratio, new_qual_ratio, "qual", 
                        format_time(self.user_qualifying_sec), self.last_qual_ratio
                    ))
                    # Update the AIW file with the new ratio
                    if self.autopilot_manager.engine._update_aiw_ratio(race_data.aiw_path, "QualRatio", new_qual_ratio):
                        self.last_qual_ratio = new_qual_ratio
                        self.qual_panel.update_ratio(new_qual_ratio)
                        logger.info(f"  Updated QualRatio in AIW to {new_qual_ratio:.6f}")
            
            if self.user_best_lap_sec > 0 and self.last_race_ratio:
                new_race_ratio = self._calculate_ratio_for_user_time(self.user_best_lap_sec, "race")
                if new_race_ratio and abs(new_race_ratio - self.last_race_ratio) > 0.000001:
                    logger.info(self.simplified_logger.new_ratio_calculation(
                        self.last_race_ratio, new_race_ratio, "race",
                        format_time(self.user_best_lap_sec), self.last_race_ratio
                    ))
                    # Update the AIW file with the new ratio
                    if self.autopilot_manager.engine._update_aiw_ratio(race_data.aiw_path, "RaceRatio", new_race_ratio):
                        self.last_race_ratio = new_race_ratio
                        self.race_panel.update_ratio(new_race_ratio)
                        logger.info(f"  Updated RaceRatio in AIW to {new_race_ratio:.6f}")
        
        # Reload formulas after any changes
        self.autopilot_manager.reload_formulas()
        self._update_formulas_from_autopilot()
        self.update_display()
        
        # Update accuracy after all updates
        if self.current_track and self.current_vehicle_class:
            self.update_formula_accuracy("qual")
            self.update_formula_accuracy("race")
        
        # Emit signal to notify advanced dialog about data refresh
        self.data_refresh_signal.emit()
        
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
        """Load tracks from database"""
        if not self.db.database_exists():
            return
        
        self.all_tracks = self.db.get_all_tracks()
        
        if self.all_tracks and not self.current_track:
            self.current_track = self.all_tracks[0]
            self.track_label.setText(self.current_track)
            self.setWindowTitle(f"GTR2 Dynamic AI - {self.current_track}")
            
            # Load AI times for this track
            self.qual_best_ai, self.qual_worst_ai = self._get_ai_times_for_track(self.current_track, "qual")
            self.race_best_ai, self.race_worst_ai = self._get_ai_times_for_track(self.current_track, "race")
        
        if self.autopilot_manager:
            self._update_formulas_from_autopilot()
        
        # Update accuracy after loading data
        if self.current_track and self.current_vehicle_class:
            self.update_formula_accuracy("qual")
            self.update_formula_accuracy("race")
    
    def update_display(self):
        """Update all display elements"""
        # Update Qualifying panel
        self.qual_panel.update_ratio(self.last_qual_ratio)
        self.qual_panel.update_ai_range(self.qual_best_ai, self.qual_worst_ai)
        self.qual_panel.update_user_time(self.user_qualifying_sec if self.user_qualifying_sec > 0 else None)
        self.qual_panel.update_formula(self.qual_a, self.qual_b)
        # Ensure last read ratio is still shown if available
        if self.qual_read_ratio is not None:
            self.qual_panel.update_last_read_ratio(self.qual_read_ratio)
        
        # Update Race panel
        self.race_panel.update_ratio(self.last_race_ratio)
        self.race_panel.update_ai_range(self.race_best_ai, self.race_worst_ai)
        self.race_panel.update_user_time(self.user_best_lap_sec if self.user_best_lap_sec > 0 else None)
        self.race_panel.update_formula(self.race_a, self.race_b)
        # Ensure last read ratio is still shown if available
        if self.race_read_ratio is not None:
            self.race_panel.update_last_read_ratio(self.race_read_ratio)
    
    def closeEvent(self, event):
        """Handle close event"""
        self.stop_daemon()
        if self.advanced_window:
            self.advanced_window.close()
        event.accept()


class ToggleSwitch(QPushButton):
    """A toggle switch button that changes appearance based on state"""
    
    def __init__(self, text_on: str, text_off: str, parent=None):
        super().__init__(parent)
        self.text_on = text_on
        self.text_off = text_off
        self._checked = False
        self.setCheckable(True)
        self.clicked.connect(self._on_click)
        self._update_style()
        self.setMinimumHeight(36)
        self.setMinimumWidth(180)
    
    def _on_click(self):
        self._checked = not self._checked
        self._update_style()
    
    def _update_style(self):
        if self._checked:
            self.setText(self.text_on)
            self.setStyleSheet("""
                QPushButton {
                    background-color: #4CAF50;
                    color: white;
                    font-weight: bold;
                    padding: 8px 18px;
                    border: none;
                    border-radius: 4px;
                    font-size: 13px;
                }
                QPushButton:hover {
                    background-color: #45a049;
                }
            """)
        else:
            self.setText(self.text_off)
            self.setStyleSheet("""
                QPushButton {
                    background-color: #3c3c3c;
                    color: #aaa;
                    font-weight: bold;
                    padding: 8px 18px;
                    border: none;
                    border-radius: 4px;
                    font-size: 13px;
                }
                QPushButton:hover {
                    background-color: #4a4a4a;
                }
            """)
    
    def is_checked(self) -> bool:
        return self._checked
    
    def set_checked(self, checked: bool):
        self._checked = checked
        self.setChecked(checked)
        self._update_style()


def main():
    # Check if config file exists and base_path is set
    config = get_config_with_defaults()
    base_path = config.get('base_path', '')
    
    # If no config file or base_path is empty, we'll handle it in the main window
    # But we still need to create default config if missing
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
    
    window = RedesignedMainWindow(db_path)
    window.show()
    
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
