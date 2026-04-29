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
    get_autopilot_enabled, get_autopilot_silent, get_ratio_limits,
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
    
    def __init__(self, parent, ratio_name: str, current_ratio: float, aiw_path: Path = None, min_ratio: float = 0.5, max_ratio: float = 1.5):
        super().__init__(parent)
        self.ratio_name = ratio_name
        self.current_ratio = current_ratio
        self.aiw_path = aiw_path
        self.min_ratio = min_ratio
        self.max_ratio = max_ratio
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
        new_label = QLabel(f"New {self.ratio_name} (min: {self.min_ratio}, max: {self.max_ratio}):")
        new_label.setStyleSheet("color: #888;")
        layout.addWidget(new_label)
        
        self.ratio_spin = QDoubleSpinBox()
        self.ratio_spin.setRange(self.min_ratio, self.max_ratio)
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
    revert_requested = pyqtSignal()
    
    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.title = title
        self.current_ratio = None
        self.last_read_ratio = None
        self.previous_ratio = None
        self.calc_button_modified = False
        self.parent_window = parent
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
            QPushButton#revert_btn {
                background-color: #FF9800;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 6px 12px;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton#revert_btn:hover {
                background-color: #F57C00;
            }
            QPushButton#revert_btn:disabled {
                background-color: #555;
                color: #888;
            }
        """)
        
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMinimumHeight(380)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(25, 25, 25, 25)
        
        # Title row with edit and revert buttons
        self.title_layout = QHBoxLayout()
        
        self.title_label = QLabel(self.title)
        self.title_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #aaa;")
        self.title_label.setAlignment(Qt.AlignCenter)
        self.title_layout.addWidget(self.title_label, stretch=1)
        
        # Revert button
        self.revert_btn = QPushButton("↺ Revert")
        self.revert_btn.setObjectName("revert_btn")
        self.revert_btn.setFixedSize(70, 28)
        self.revert_btn.setEnabled(False)
        self.revert_btn.clicked.connect(self.on_revert_clicked)
        self.title_layout.addWidget(self.revert_btn)
        
        # Edit button
        self.edit_btn = QPushButton("✎ Edit")
        self.edit_btn.setObjectName("edit_btn")
        self.edit_btn.setFixedSize(70, 28)
        self.edit_btn.clicked.connect(self.on_edit_clicked)
        self.title_layout.addWidget(self.edit_btn)
        
        layout.addLayout(self.title_layout)
        
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
        """Update the current ratio and store previous for revert"""
        if ratio is not None and self.current_ratio is not None and ratio != self.current_ratio:
            # Store previous ratio before updating
            self.previous_ratio = self.current_ratio
            self.revert_btn.setEnabled(True)
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
        min_ratio, max_ratio = get_ratio_limits()
        dialog = ManualEditDialog(self, self.title, self.current_ratio, None, min_ratio, max_ratio)
        if dialog.exec_() == QDialog.Accepted and dialog.new_ratio is not None:
            self.edit_complete.emit(dialog.new_ratio)
    
    def on_revert_clicked(self):
        """Revert to previous ratio"""
        if self.previous_ratio is not None:
            self.revert_requested.emit()
    
    def revert_success(self):
        """Called after successful revert to clear previous ratio"""
        self.previous_ratio = None
        self.revert_btn.setEnabled(False)
    
    def set_calc_button_orange(self, is_orange: bool):
        """Set the calculate button color (called from parent)"""
        self.calc_button_modified = is_orange


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
        
        # Get ratio limits from config
        self.min_ratio, self.max_ratio = get_ratio_limits(config_file)
        
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
        
        # AI Target settings - will be applied to ALL ratio calculations
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
        
        # Track if a/b have been modified (for button color)
        self.qual_ab_modified = False
        self.race_ab_modified = False
        
        # Advanced settings window
        self.advanced_window = None
        
        # Daemon
        self.daemon = None
        
        # Flag to track if AIW is accessible
        self.aiw_accessible = True
        self.last_aiw_error = None
        
        self.setup_ui()
        
        # Connect revert signals
        self.qual_panel.revert_requested.connect(lambda: self.on_revert_ratio("qual"))
        self.race_panel.revert_requested.connect(lambda: self.on_revert_ratio("race"))
        
        # Check and set base path before loading data
        if not self.ensure_base_path():
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
        
        # Add target indicator to status bar
        self.add_target_indicator()
    
    def add_target_indicator(self):
        """Add target indicator to status bar instead of main layout"""
        target_widget = QWidget()
        target_layout = QHBoxLayout(target_widget)
        target_layout.setContentsMargins(5, 0, 10, 0)
        target_layout.setSpacing(8)
        
        target_icon = QLabel("🎯")
        target_icon.setStyleSheet("font-size: 12px;")
        target_layout.addWidget(target_icon)
        
        target_label = QLabel("AI Target:")
        target_label.setStyleSheet("color: #FFA500; font-weight: bold; font-size: 11px;")
        target_layout.addWidget(target_label)
        
        self.target_display = QLabel("Not set")
        self.target_display.setStyleSheet("color: #4CAF50; font-family: monospace; font-size: 11px;")
        target_layout.addWidget(self.target_display)
        
        sep = QFrame()
        sep.setFrameShape(QFrame.VLine)
        sep.setStyleSheet("color: #555;")
        target_layout.addWidget(sep)
        
        target_btn = QPushButton("Configure")
        target_btn.setStyleSheet("""
            QPushButton {
                background-color: #FF9800;
                color: white;
                padding: 2px 8px;
                font-size: 10px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #F57C00;
            }
        """)
        target_btn.clicked.connect(self.open_advanced_settings_to_target)
        target_btn.setFixedWidth(70)
        target_layout.addWidget(target_btn)
        
        target_layout.addStretch()
        self.statusBar().addPermanentWidget(target_widget)
        self.update_target_display()
    
    def open_advanced_settings_to_target(self):
        """Open advanced settings and switch to AI Target tab"""
        self.open_advanced_settings()
        if self.advanced_window:
            self.advanced_window.tab_widget.setCurrentIndex(1)
    
    def update_target_display(self):
        """Update the target display on status bar"""
        if hasattr(self, 'target_display'):
            mode = self.ai_target_settings.get("mode", "percentage")
            error_margin = self.ai_target_settings.get("error_margin", 0)
            if mode == "percentage":
                pct = self.ai_target_settings.get("percentage", 50)
                if error_margin > 0:
                    self.target_display.setText(f"{pct}% (+{error_margin:.2f}s)")
                else:
                    self.target_display.setText(f"{pct}%")
            elif mode == "faster_than_best":
                offset = self.ai_target_settings.get("offset_seconds", 0)
                if error_margin > 0:
                    self.target_display.setText(f"{offset:+.2f}s (+{error_margin:.2f}s)")
                else:
                    self.target_display.setText(f"{offset:+.2f}s")
            else:
                offset = self.ai_target_settings.get("offset_seconds", 0)
                if error_margin > 0:
                    self.target_display.setText(f"{offset:+.2f}s (+{error_margin:.2f}s)")
                else:
                    self.target_display.setText(f"{offset:+.2f}s")
    
    def calculate_target_lap_time(self, best_ai: float, worst_ai: float) -> float:
        """Calculate target lap time based on current AI Target settings"""
        mode = self.ai_target_settings.get("mode", "percentage")
        error_margin = self.ai_target_settings.get("error_margin", 0.0)
        
        if mode == "percentage":
            pct = self.ai_target_settings.get("percentage", 50) / 100.0
            target = best_ai + (worst_ai - best_ai) * pct
        elif mode == "faster_than_best":
            offset = self.ai_target_settings.get("offset_seconds", 0.0)
            target = best_ai + offset
        else:
            offset = self.ai_target_settings.get("offset_seconds", 0.0)
            target = worst_ai - offset
        
        if error_margin > 0:
            target = target + error_margin
        
        target = max(best_ai, min(worst_ai + error_margin, target))
        
        return target
    
    def calculate_ratio_from_target(self, session_type: str) -> Optional[float]:
        """
        Calculate what ratio would achieve the AI Target lap time.
        This should be called when we want to apply AI Target settings.
        """
        logger.info(f"[AI TARGET] calculate_ratio_from_target called for {session_type}")
        
        # Start analysis if not already started
        if hasattr(self, 'analyzer') and not self.analyzer.current_analysis:
            self.analyzer.start_analysis(session_type, self.current_track, self.current_vehicle_class)
        
        # Get AI range
        if session_type == "qual":
            best_ai = self.qual_best_ai
            worst_ai = self.qual_worst_ai
            b = self.qual_b
            current_ratio = self.last_qual_ratio
            user_time = self.user_qualifying_sec
        else:
            best_ai = self.race_best_ai
            worst_ai = self.race_worst_ai
            b = self.race_b
            current_ratio = self.last_race_ratio
            user_time = self.user_best_lap_sec
        
        if hasattr(self, 'analyzer') and self.analyzer.current_analysis:
            self.analyzer.add_input_data(
                best_ai=best_ai,
                worst_ai=worst_ai,
                user_lap_time=user_time if user_time > 0 else None,
                current_ratio=current_ratio,
                formula_a=32.0,
                formula_b=b
            )
            self.analyzer.add_target_settings(
                mode=self.ai_target_settings.get("mode", "percentage"),
                settings=self.ai_target_settings
            )
        
        if best_ai is None or worst_ai is None or best_ai <= 0 or worst_ai <= 0:
            logger.warning(f"[AI TARGET] No AI range data for {session_type}")
            if hasattr(self, 'analyzer') and self.analyzer.current_analysis:
                self.analyzer.add_error(
                    f"No AI range data for {session_type}: best={best_ai}, worst={worst_ai}",
                    {}
                )
                self.analyzer.set_result(None, None, None, False, "No AI range data")
                self.analyzer.finalize_and_dump()
            return None
        
        # Calculate target lap time from settings
        target_time = self.calculate_target_lap_time(best_ai, worst_ai)
        logger.info(f"[AI TARGET] Target lap time: {target_time:.3f}s")
        
        # Calculate ratio from target time using formula T = a/R + b -> R = a/(T-b)
        a = DEFAULT_A_VALUE
        denominator = target_time - b
        
        if denominator <= 0:
            logger.warning(f"[AI TARGET] Denominator <= 0: {target_time:.3f} - {b:.2f} = {denominator:.3f}")
            if hasattr(self, 'analyzer') and self.analyzer.current_analysis:
                self.analyzer.add_error(
                    f"Denominator <= 0: T-b = {target_time:.3f} - {b:.2f} = {denominator:.3f}",
                    {}
                )
                self.analyzer.set_result(target_time, None, None, False, "Cannot calculate ratio: T-b must be positive")
                self.analyzer.finalize_and_dump()
            return None
        
        ratio = a / denominator
        logger.info(f"[AI TARGET] Calculated ratio from target: {ratio:.6f}")
        
        if hasattr(self, 'analyzer') and self.analyzer.current_analysis:
            self.analyzer.add_calculation_step(
                f"Calculated ratio: R = a/(T-b) = {a:.2f}/({target_time:.3f} - {b:.2f}) = {ratio:.6f}",
                {"a": a, "b": b, "target_time": target_time, "calculated_ratio": ratio}
            )
        
        # Check ratio limits
        if ratio < self.min_ratio or ratio > self.max_ratio:
            logger.warning(f"[AI TARGET] Ratio {ratio:.6f} outside limits ({self.min_ratio}-{self.max_ratio})")
            
            if hasattr(self, 'analyzer') and self.analyzer.current_analysis:
                self.analyzer.add_range_check(
                    f"Ratio {ratio:.6f} is OUTSIDE allowed range ({self.min_ratio} - {self.max_ratio})",
                    {"min_ratio": self.min_ratio, "max_ratio": self.max_ratio, "calculated_ratio": ratio}
                )
            
            # Ask user if they want to proceed
            reply = QMessageBox.question(self, "Ratio Out of Range",
                f"The calculated {session_type.upper()} Ratio = {ratio:.6f} is outside the allowed range "
                f"({self.min_ratio} - {self.max_ratio}).\n\n"
                f"Values outside this range can make AI behavior unpredictable.\n\n"
                f"Do you still want to apply this ratio?",
                QMessageBox.Yes | QMessageBox.No)
            
            if hasattr(self, 'analyzer') and self.analyzer.current_analysis:
                self.analyzer.add_decision(
                    f"User chose to {'apply' if reply == QMessageBox.Yes else 'reject'} ratio outside limits",
                    {"user_choice": "apply" if reply == QMessageBox.Yes else "reject"}
                )
            
            if reply != QMessageBox.Yes:
                if hasattr(self, 'analyzer') and self.analyzer.current_analysis:
                    self.analyzer.set_result(target_time, ratio, None, False, "User rejected ratio outside limits")
                    self.analyzer.finalize_and_dump()
                return None
        else:
            if hasattr(self, 'analyzer') and self.analyzer.current_analysis:
                self.analyzer.add_range_check(
                    f"Ratio {ratio:.6f} is within allowed range ({self.min_ratio} - {self.max_ratio})",
                    {"in_range": True, "min_ratio": self.min_ratio, "max_ratio": self.max_ratio}
                )
        
        if hasattr(self, 'analyzer') and self.analyzer.current_analysis:
            self.analyzer.set_result(target_time, ratio, ratio, True, "Ratio calculated successfully")
            self.analyzer.finalize_and_dump()
        
        return ratio

    def ensure_base_path(self) -> bool:
        """Ensure that a valid base path is configured. Returns True if path is set."""
        config = get_config_with_defaults(self.config_file)
        base_path = config.get('base_path', '')
        
        if not base_path or not Path(base_path).exists():
            path = Path(base_path) if base_path else None
            if not path or not (path / "GameData").exists() or not (path / "UserData").exists():
                dialog = BasePathSelectionDialog(self)
                if dialog.exec_() == QDialog.Accepted and dialog.selected_path:
                    update_base_path(dialog.selected_path, self.config_file)
                    logger.info(f"Base path set to: {dialog.selected_path}")
                    self.aiw_accessible = True
                    return True
                else:
                    return False
        
        path = Path(base_path)
        if (path / "GameData").exists() and (path / "UserData").exists():
            self.aiw_accessible = True
            return True
        else:
            reply = QMessageBox.question(self, "Invalid Path",
                f"The configured path '{base_path}' does not appear to be a valid GTR2 installation.\n\n"
                "Would you like to select a different path?",
                QMessageBox.Yes | QMessageBox.No)
            if reply == QMessageBox.Yes:
                dialog = BasePathSelectionDialog(self)
                if dialog.exec_() == QDialog.Accepted and dialog.selected_path:
                    update_base_path(dialog.selected_path, self.config_file)
                    logger.info(f"Base path updated to: {dialog.selected_path}")
                    self.aiw_accessible = True
                    return True
            return False
    
    def setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setSpacing(25)
        main_layout.setContentsMargins(30, 30, 30, 30)
        
        # Top section (stretches to take available space)
        top_section = QWidget()
        top_layout = QVBoxLayout(top_section)
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setSpacing(20)
        
        # Header section
        header_layout = QHBoxLayout()
        logo_label = GTR2Logo()
        header_layout.addWidget(logo_label)
        header_layout.addStretch()
        self.track_label = QLabel("-")
        self.track_label.setStyleSheet("font-size: 28px; font-weight: bold; color: white;")
        header_layout.addWidget(self.track_label)
        header_layout.addStretch()
        header_layout.addSpacing(80)
        top_layout.addLayout(header_layout)
        
        # Car class
        self.car_class_label = QLabel("Car Class: -")
        self.car_class_label.setStyleSheet("font-size: 14px; color: #4CAF50; margin-bottom: 10px;")
        top_layout.addWidget(self.car_class_label)
        
        # Two-column layout for Quali and Race panels
        panels_layout = QHBoxLayout()
        panels_layout.setSpacing(30)
        
        self.qual_panel = RatioPanel("Quali-Ratio", self)
        self.qual_panel.edit_complete.connect(lambda ratio: self.on_manual_edit("qual", ratio))
        panels_layout.addWidget(self.qual_panel)
        
        self.race_panel = RatioPanel("Race-Ratio", self)
        self.race_panel.edit_complete.connect(lambda ratio: self.on_manual_edit("race", ratio))
        panels_layout.addWidget(self.race_panel)
        
        top_layout.addLayout(panels_layout)
        
        main_layout.addWidget(top_section, stretch=1)
        
        # Bottom section (fixed height for buttons)
        bottom_section = QWidget()
        bottom_layout = QVBoxLayout(bottom_section)
        bottom_layout.setContentsMargins(0, 0, 0, 0)
        bottom_layout.setSpacing(20)
        
        # Control buttons row
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(20)
        
        self.autosave_switch = ToggleSwitch("Auto-harvest Data (ON)", "Auto-harvest Data (OFF)")
        self.autosave_switch.set_checked(self.autosave_enabled)
        self.autosave_switch.clicked.connect(self.toggle_autosave)
        buttons_layout.addWidget(self.autosave_switch)
        
        self.autoratio_switch = ToggleSwitch("Auto-calculate Ratios (ON)", "Auto-calculate Ratios (OFF)")
        self.autoratio_switch.set_checked(self.autoratio_enabled)
        self.autoratio_switch.clicked.connect(self.toggle_autoratio)
        buttons_layout.addWidget(self.autoratio_switch)
        
        buttons_layout.addStretch()
        
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
        
        bottom_layout.addLayout(buttons_layout)
        
        main_layout.addWidget(bottom_section, stretch=0)
        
        self.statusBar().showMessage("Ready")
        self.statusBar().setStyleSheet("QStatusBar { color: #888; }")
        
        self.setStyleSheet("""
            QMainWindow { background-color: #1e1e1e; }
            QLabel { color: white; }
        """)
    
    def toggle_autosave(self):
        self.autosave_enabled = self.autosave_switch.is_checked()
        logger.info(self.simplified_logger.autosave_status(self.autosave_enabled))
        self.statusBar().showMessage(f"Auto-harvest Data {'ON' if self.autosave_enabled else 'OFF'}", 2000)
    
    def toggle_autoratio(self):
        self.autoratio_enabled = self.autoratio_switch.is_checked()
        self.autopilot_manager.set_enabled(self.autoratio_enabled)
        self.qual_panel.set_edit_enabled(not self.autoratio_enabled)
        self.race_panel.set_edit_enabled(not self.autoratio_enabled)
        logger.info(self.simplified_logger.autoratio_status(self.autoratio_enabled))
        self.statusBar().showMessage(f"Auto-calculate Ratios {'ON' if self.autoratio_enabled else 'OFF'}", 2000)
        
        if self.autoratio_enabled:
            self.autopilot_manager.reload_formulas()
            self._update_formulas_from_autopilot()
            self.update_display()
            if self.current_track and self.current_vehicle_class:
                self.update_formula_accuracy("qual")
                self.update_formula_accuracy("race")
    
    def _get_ai_times_for_track(self, track: str, session_type: str) -> Tuple[Optional[float], Optional[float]]:
        conn = sqlite3.connect(self.db.db_path)
        cursor = conn.cursor()
        
        if session_type == "qual":
            cursor.execute("""
                SELECT qual_time_sec FROM ai_results ar
                JOIN race_sessions rs ON ar.race_id = rs.race_id
                WHERE rs.track_name = ? AND ar.qual_time_sec > 0
                ORDER BY ar.qual_time_sec LIMIT 1
            """, (track,))
            best_row = cursor.fetchone()
            cursor.execute("""
                SELECT qual_time_sec FROM ai_results ar
                JOIN race_sessions rs ON ar.race_id = rs.race_id
                WHERE rs.track_name = ? AND ar.qual_time_sec > 0
                ORDER BY ar.qual_time_sec DESC LIMIT 1
            """, (track,))
            worst_row = cursor.fetchone()
        else:
            cursor.execute("""
                SELECT best_lap_sec FROM ai_results ar
                JOIN race_sessions rs ON ar.race_id = rs.race_id
                WHERE rs.track_name = ? AND ar.best_lap_sec > 0
                ORDER BY ar.best_lap_sec LIMIT 1
            """, (track,))
            best_row = cursor.fetchone()
            cursor.execute("""
                SELECT best_lap_sec FROM ai_results ar
                JOIN race_sessions rs ON ar.race_id = rs.race_id
                WHERE rs.track_name = ? AND ar.best_lap_sec > 0
                ORDER BY ar.best_lap_sec DESC LIMIT 1
            """, (track,))
            worst_row = cursor.fetchone()
        
        conn.close()
        best = best_row[0] if best_row else None
        worst = worst_row[0] if worst_row else None
        return best, worst
    
    def update_formula_accuracy(self, session_type: str):
        if not self.current_track or not self.current_vehicle_class:
            return
        formula = self.autopilot_manager.formula_manager.get_formula_by_class(
            self.current_track, self.current_vehicle_class, session_type)
        
        if formula and formula.is_valid():
            data_points = self.autopilot_manager.engine._get_data_points(
                self.current_track, self.current_vehicle_class, session_type)
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
            panel.update_accuracy(formula.confidence, formula.data_points_used, avg_error, formula.max_error if formula.max_error > 0 else None, outliers)
        else:
            panel = self.qual_panel if session_type == "qual" else self.race_panel
            panel.update_accuracy(0, 0, None, None, 0)
    
    def _validate_ratio(self, ratio: float, ratio_name: str) -> bool:
        if ratio < self.min_ratio:
            show_warning_dialog(self, f"{ratio_name} Below Minimum",
                f"The calculated {ratio_name} = {ratio:.6f} is below the minimum allowed value ({self.min_ratio}).\n\n"
                f"The ratio will NOT be changed.\n\n"
                f"To allow lower values, adjust 'min_ratio' in cfg.yml.")
            return False
        elif ratio > self.max_ratio:
            show_warning_dialog(self, f"{ratio_name} Above Maximum",
                f"The calculated {ratio_name} = {ratio:.6f} is above the maximum allowed value ({self.max_ratio}).\n\n"
                f"The ratio will NOT be changed.\n\n"
                f"To allow higher values, adjust 'max_ratio' in cfg.yml.")
            return False
        return True
    
    def _get_aiw_path(self) -> Optional[Path]:
        if not self.current_track:
            return None
        if hasattr(self, 'daemon') and self.daemon and self.daemon.base_path:
            locations_dir = self.daemon.base_path / "GameData" / "Locations"
            if locations_dir.exists():
                for track_dir in locations_dir.iterdir():
                    if track_dir.is_dir() and track_dir.name.lower() == self.current_track.lower():
                        for ext in ["*.AIW", "*.aiw"]:
                            aiw_files = list(track_dir.glob(ext))
                            if aiw_files:
                                return aiw_files[0]
                        break
        return None
    
    def show_aiw_error_and_configure(self, operation: str, error_detail: str = None):
        """Show AIW error with option to reconfigure base path"""
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("AIW File Not Found")
        msg_box.setIcon(QMessageBox.Critical)
        
        error_text = (
            f"Cannot {operation} because the AIW file could not be found.\n\n"
            f"This usually means the GTR2 base path is not configured correctly.\n\n"
        )
        
        if error_detail:
            error_text += f"Details: {error_detail}\n\n"
        
        error_text += (
            f"Please configure the correct GTR2 installation folder "
            f"(the one containing GameData and UserData directories)."
        )
        
        msg_box.setText(error_text)
        msg_box.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)
        msg_box.button(QMessageBox.Ok).setText("Configure GTR2 Path")
        
        result = msg_box.exec_()
        
        if result == QMessageBox.Ok:
            # Open base path selection dialog
            dialog = BasePathSelectionDialog(self)
            if dialog.exec_() == QDialog.Accepted and dialog.selected_path:
                update_base_path(dialog.selected_path, self.config_file)
                self.aiw_accessible = True
                # Restart daemon with new path
                self.stop_daemon()
                self.start_daemon()
                QMessageBox.information(self, "Path Updated", 
                    f"GTR2 path updated to:\n{dialog.selected_path}\n\n"
                    f"Please try the operation again.")
            return True
        return False
    
    def check_aiw_accessible(self, session_type: str) -> bool:
        """Check if AIW file is accessible and show error if not"""
        aiw_path = self._get_aiw_path()
        if not aiw_path or not aiw_path.exists():
            self.aiw_accessible = False
            self.show_aiw_error_and_accessible(f"update {session_type.upper()} ratio", 
                f"AIW file for track '{self.current_track}' not found in GameData/Locations/")
            return False
        self.aiw_accessible = True
        return True
    
    def show_aiw_error_and_accessible(self, operation: str, error_detail: str = None):
        """Show AIW error and mark as inaccessible"""
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("AIW File Not Found")
        msg_box.setIcon(QMessageBox.Critical)
        
        error_text = (
            f"Cannot {operation} because the AIW file could not be found.\n\n"
            f"This usually means the GTR2 base path is not configured correctly.\n\n"
        )
        
        if error_detail:
            error_text += f"Details: {error_detail}\n\n"
        
        error_text += (
            f"Please configure the correct GTR2 installation folder "
            f"(the one containing GameData and UserData directories)."
        )
        
        msg_box.setText(error_text)
        msg_box.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)
        msg_box.button(QMessageBox.Ok).setText("Configure GTR2 Path")
        
        result = msg_box.exec_()
        
        if result == QMessageBox.Ok:
            dialog = BasePathSelectionDialog(self)
            if dialog.exec_() == QDialog.Accepted and dialog.selected_path:
                update_base_path(dialog.selected_path, self.config_file)
                self.aiw_accessible = True
                self.stop_daemon()
                self.start_daemon()
                QMessageBox.information(self, "Path Updated", 
                    f"GTR2 path updated to:\n{dialog.selected_path}\n\n"
                    f"Please try the operation again.")
            return True
        return False
    
    def on_revert_ratio(self, session_type: str):
        if not self.check_aiw_accessible(session_type):
            return
        
        if session_type == "qual":
            old_ratio = self.qual_panel.previous_ratio
            if old_ratio is None:
                return
            aiw_path = self._get_aiw_path()
            if not aiw_path:
                if self.show_aiw_error_and_accessible("revert QualRatio"):
                    return
                show_warning_dialog(self, "AIW Not Found", "Could not find AIW file to revert.")
                return
            if self.autopilot_manager.engine._update_aiw_ratio(aiw_path, "QualRatio", old_ratio):
                self.last_qual_ratio = old_ratio
                self.qual_panel.update_ratio(old_ratio)
                self.qual_panel.revert_success()
                self.statusBar().showMessage(f"QualRatio reverted to {old_ratio:.6f}", 3000)
                logger.info(f"Reverted QualRatio to {old_ratio:.6f}")
            else:
                show_error_dialog(self, "Revert Failed", "Failed to revert QualRatio in AIW file.")
        else:
            old_ratio = self.race_panel.previous_ratio
            if old_ratio is None:
                return
            aiw_path = self._get_aiw_path()
            if not aiw_path:
                if self.show_aiw_error_and_accessible("revert RaceRatio"):
                    return
                show_warning_dialog(self, "AIW Not Found", "Could not find AIW file to revert.")
                return
            if self.autopilot_manager.engine._update_aiw_ratio(aiw_path, "RaceRatio", old_ratio):
                self.last_race_ratio = old_ratio
                self.race_panel.update_ratio(old_ratio)
                self.race_panel.revert_success()
                self.statusBar().showMessage(f"RaceRatio reverted to {old_ratio:.6f}", 3000)
                logger.info(f"Reverted RaceRatio to {old_ratio:.6f}")
            else:
                show_error_dialog(self, "Revert Failed", "Failed to revert RaceRatio in AIW file.")
    
    def apply_ai_target_to_ratio(self, session_type: str, aiw_path: Path) -> Optional[float]:
        """
        Apply current AI Target settings to calculate and write a new ratio.
        Returns the new ratio if successful, None otherwise.
        """
        logger.info(f"[AI TARGET] apply_ai_target_to_ratio called for {session_type}")
        
        new_ratio = self.calculate_ratio_from_target(session_type)
        
        if new_ratio is None:
            logger.warning(f"[AI TARGET] Could not calculate ratio from target for {session_type}")
            return None
        
        ratio_name = "QualRatio" if session_type == "qual" else "RaceRatio"
        
        if self.autopilot_manager.engine._update_aiw_ratio(aiw_path, ratio_name, new_ratio):
            if session_type == "qual":
                self.last_qual_ratio = new_ratio
                self.qual_panel.update_ratio(new_ratio)
            else:
                self.last_race_ratio = new_ratio
                self.race_panel.update_ratio(new_ratio)
            logger.info(f"[AI TARGET] Successfully applied AI Target: {ratio_name} = {new_ratio:.6f}")
            self.statusBar().showMessage(f"AI Target applied: {ratio_name} = {new_ratio:.6f}", 3000)
            return new_ratio
        else:
            logger.error(f"[AI TARGET] Failed to update AIW with {ratio_name}={new_ratio:.6f}")
            return None
    
    def on_ratio_saved_from_advanced(self, session_type: str, ratio: float):
        """Handle ratio saved from advanced dialog - apply AI Target if needed"""
        if not self.check_aiw_accessible(session_type):
            return
        
        aiw_path = self._get_aiw_path()
        if not aiw_path:
            if self.show_aiw_error_and_accessible("save ratio"):
                return
            show_warning_dialog(self, "AIW Not Found", "Could not find AIW file to save ratio.")
            return
        
        # Check if we should apply AI Target adjustment
        if self.ai_target_settings.get("mode") != "percentage" or self.ai_target_settings.get("percentage") != 50:
            # User has non-default AI Target, recalculate based on target
            logger.info(f"[AI TARGET] Applying AI Target to manually saved ratio for {session_type}")
            new_ratio = self.calculate_ratio_from_target(session_type)
            if new_ratio and new_ratio != ratio:
                reply = QMessageBox.question(self, "Apply AI Target?",
                    f"You have AI Target settings active.\n\n"
                    f"Manual ratio: {ratio:.6f}\n"
                    f"AI Target ratio: {new_ratio:.6f}\n\n"
                    f"Which ratio would you like to use?",
                    QMessageBox.Yes | QMessageBox.No)
                if reply == QMessageBox.Yes:
                    ratio = new_ratio
        
        ratio_name = "QualRatio" if session_type == "qual" else "RaceRatio"
        if self._validate_ratio(ratio, ratio_name):
            if self.autopilot_manager.engine._update_aiw_ratio(aiw_path, ratio_name, ratio):
                if session_type == "qual":
                    self.last_qual_ratio = ratio
                    self.qual_panel.update_ratio(ratio)
                else:
                    self.last_race_ratio = ratio
                    self.race_panel.update_ratio(ratio)
                logger.info(f"Saved ratio from Advanced dialog: {ratio_name}={ratio:.6f}")
    
    def on_lap_time_updated_from_advanced(self, session_type: str, lap_time: float):
        if session_type == "qual":
            self.user_qualifying_sec = lap_time
            self.qual_panel.update_user_time(lap_time)
        else:
            self.user_best_lap_sec = lap_time
            self.race_panel.update_user_time(lap_time)
    
    def on_manual_edit(self, session_type: str, new_ratio: float):
        if self.autoratio_enabled:
            show_warning_dialog(self, "Auto-Ratio Enabled", 
                "Manual editing is disabled while Auto-calculate Ratios is ON.")
            if session_type == "qual":
                self.qual_panel.set_edit_enabled(False)
            else:
                self.race_panel.set_edit_enabled(False)
            return
        
        ratio_name = "QualRatio" if session_type == "qual" else "RaceRatio"
        if not self._validate_ratio(new_ratio, ratio_name):
            return
        
        if not self.check_aiw_accessible(session_type):
            return
        
        aiw_path = self._get_aiw_path()
        if not aiw_path or not aiw_path.exists():
            if self.show_aiw_error_and_accessible(f"update {ratio_name}"):
                return
            aiw_path_str, _ = QFileDialog.getOpenFileName(
                self, f"Select AIW file for {self.current_track}",
                str(Path.cwd()), "AIW Files (*.AIW *.aiw)")
            if aiw_path_str:
                aiw_path = Path(aiw_path_str)
            else:
                show_warning_dialog(self, "AIW Not Found", f"Could not find AIW file.")
                return
        
        # Apply AI Target if non-default settings
        final_ratio = new_ratio
        if self.ai_target_settings.get("mode") != "percentage" or self.ai_target_settings.get("percentage") != 50:
            target_ratio = self.calculate_ratio_from_target(session_type)
            if target_ratio and abs(target_ratio - new_ratio) > 0.0001:
                reply = QMessageBox.question(self, "Apply AI Target?",
                    f"You have AI Target settings active.\n\n"
                    f"Manual ratio: {new_ratio:.6f}\n"
                    f"AI Target ratio: {target_ratio:.6f}\n\n"
                    f"Which ratio would you like to use?",
                    QMessageBox.Yes | QMessageBox.No)
                if reply == QMessageBox.Yes:
                    final_ratio = target_ratio
        
        if self.autopilot_manager.engine._update_aiw_ratio(aiw_path, ratio_name, final_ratio):
            if session_type == "qual":
                self.last_qual_ratio = final_ratio
                self.qual_panel.update_ratio(final_ratio)
            else:
                self.last_race_ratio = final_ratio
                self.race_panel.update_ratio(final_ratio)
            logger.info(f"Manually updated {ratio_name} to {final_ratio:.6f}")
            self.statusBar().showMessage(f"{ratio_name} updated to {final_ratio:.6f}", 3000)
        else:
            show_error_dialog(self, "Update Failed", f"Failed to update {ratio_name} in AIW file.")
    
    def _update_formulas_from_autopilot(self):
        if not self.current_track or not self.current_vehicle_class:
            if self.current_vehicle:
                self.current_vehicle_class = get_vehicle_class(self.current_vehicle, self.class_mapping)
            if not self.current_vehicle_class:
                return
        
        qual_formula = self.autopilot_manager.formula_manager.get_formula_by_class(
            self.current_track, self.current_vehicle_class, "qual")
        if qual_formula and qual_formula.is_valid():
            self.qual_a = DEFAULT_A_VALUE
            self.qual_b = qual_formula.b
        else:
            self.qual_a = DEFAULT_A_VALUE
            self.qual_b = 70.0
        
        race_formula = self.autopilot_manager.formula_manager.get_formula_by_class(
            self.current_track, self.current_vehicle_class, "race")
        if race_formula and race_formula.is_valid():
            self.race_a = DEFAULT_A_VALUE
            self.race_b = race_formula.b
        else:
            self.race_a = DEFAULT_A_VALUE
            self.race_b = 70.0
    
    def _fit_b_from_data_points(self, session_type: str, ratio: float, ai_times: List[float]) -> Optional[float]:
        if not ai_times:
            return None
        b_values = []
        for ai_time in ai_times:
            if ai_time is not None and ai_time > 0:
                b = ai_time - (DEFAULT_A_VALUE / ratio)
                b_values.append(b)
        if not b_values:
            return None
        avg_b = sum(b_values) / len(b_values)
        avg_b = max(10.0, min(200.0, avg_b))
        return avg_b
    
    def _update_formula_from_new_data(self, race_data: RaceData, session_type: str) -> bool:
        if not self.current_track or not self.current_vehicle_class:
            return False
        
        if session_type == "qual":
            current_ratio = race_data.qual_ratio
            best_ai = race_data.qual_best_ai_lap_sec
            worst_ai = race_data.qual_worst_ai_lap_sec
        else:
            current_ratio = race_data.race_ratio
            best_ai = race_data.best_ai_lap_sec
            worst_ai = race_data.worst_ai_lap_sec
        
        if not current_ratio or current_ratio <= 0:
            return False
        
        ai_times = []
        if best_ai and best_ai > 0:
            ai_times.append(best_ai)
        if worst_ai and worst_ai > 0:
            ai_times.append(worst_ai)
        
        for ai in race_data.ai_results:
            if session_type == "qual":
                qual_time = ai.get('qual_time_sec')
                if qual_time is not None and qual_time > 0:
                    ai_times.append(qual_time)
            else:
                best_lap = ai.get('best_lap_sec')
                if best_lap is not None and best_lap > 0:
                    ai_times.append(best_lap)
        
        if not ai_times:
            return False
        
        new_b = self._fit_b_from_data_points(session_type, current_ratio, ai_times)
        if new_b is None:
            return False
        
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
            if session_type == "qual":
                self.qual_b = new_b
            else:
                self.race_b = new_b
            return True
        return False
    
    def _calculate_ratio_for_user_time(self, user_time: float, session_type: str) -> Optional[float]:
        if session_type == "qual":
            a = DEFAULT_A_VALUE
            b = self.qual_b
        else:
            a = DEFAULT_A_VALUE
            b = self.race_b
        
        denominator = user_time - b
        if denominator <= 0:
            return None
        ratio = a / denominator
        return ratio if 0.3 < ratio < 3.0 else None
    
    def open_advanced_settings(self):
        if self.advanced_window is None:
            self.advanced_window = AdvancedSettingsDialog(self, self.db, self.log_window)
            self.advanced_window.data_updated.connect(self.on_data_updated)
            self.advanced_window.formula_updated.connect(self.on_formula_updated)
            self.advanced_window.ratio_saved.connect(self.on_ratio_saved_from_advanced)
            self.advanced_window.lap_time_updated.connect(self.on_lap_time_updated_from_advanced)
            self.data_refresh_signal.connect(self.advanced_window.on_parent_data_refresh)
        
        if hasattr(self.advanced_window, 'curve_graph'):
            self.advanced_window.curve_graph.update_current_info(
                track=self.current_track, vehicle=self.current_vehicle,
                qual_time=self.user_qualifying_sec if self.user_qualifying_sec > 0 else None,
                race_time=self.user_best_lap_sec if self.user_best_lap_sec > 0 else None,
                qual_ratio=self.last_qual_ratio, race_ratio=self.last_race_ratio)
            self.advanced_window.curve_graph.set_formulas(self.qual_a, self.qual_b, self.race_a, self.race_b)
            self.advanced_window.curve_graph.full_refresh()
        
        self.advanced_window.show()
        self.advanced_window.raise_()
        self.advanced_window.activateWindow()
    
    def on_data_updated(self):
        self.load_data()
        self.update_display()
    
    def on_formula_updated(self, session_type: str, a: float, b: float):
        if session_type == "qual":
            self.qual_b = b
            self.qual_ab_modified = True
        else:
            self.race_b = b
            self.race_ab_modified = True
        self.update_display()
        self.update_formula_accuracy(session_type)
    
    def start_daemon(self):
        file_path = get_results_file_path(self.config_file)
        base_path = get_base_path(self.config_file)
        if not file_path or not base_path:
            logger.warning("Base path not configured - daemon not started")
            return
        poll_interval = get_poll_interval(self.config_file)
        self.daemon = FileMonitorDaemon(file_path, base_path, poll_interval)
        self.daemon.signal.file_changed.connect(self.on_file_changed)
        self.daemon.start()
    
    def stop_daemon(self):
        if self.daemon:
            self.daemon.stop()
            self.daemon = None
    
    def on_file_changed(self, race_data: RaceData):
        if not race_data:
            return
        
        if hasattr(race_data, 'aiw_error') and race_data.aiw_error:
            self.show_aiw_error_and_accessible("process race data", race_data.aiw_error)
            return
        
        if race_data.track_name:
            self.current_track = race_data.track_name
            self.track_label.setText(self.current_track)
            self.setWindowTitle(f"GTR2 Dynamic AI - {self.current_track}")
        
        if race_data.user_qualifying_sec:
            self.user_qualifying_sec = race_data.user_qualifying_sec
        if race_data.user_best_lap_sec:
            self.user_best_lap_sec = race_data.user_best_lap_sec
        
        if race_data.qual_ratio:
            self.qual_read_ratio = race_data.qual_ratio
            self.qual_panel.update_last_read_ratio(self.qual_read_ratio)
        if race_data.race_ratio:
            self.race_read_ratio = race_data.race_ratio
            self.race_panel.update_last_read_ratio(self.race_read_ratio)
        
        if race_data.qual_ratio:
            self.last_qual_ratio = race_data.qual_ratio
        if race_data.race_ratio:
            self.last_race_ratio = race_data.race_ratio
        
        if race_data.qual_best_ai_lap_sec:
            self.qual_best_ai = race_data.qual_best_ai_lap_sec
        if race_data.qual_worst_ai_lap_sec:
            self.qual_worst_ai = race_data.qual_worst_ai_lap_sec
        if race_data.best_ai_lap_sec:
            self.race_best_ai = race_data.best_ai_lap_sec
        if race_data.worst_ai_lap_sec:
            self.race_worst_ai = race_data.worst_ai_lap_sec
        
        if race_data.user_vehicle:
            self.current_vehicle = race_data.user_vehicle
            self.current_vehicle_class = get_vehicle_class(self.current_vehicle, self.class_mapping)
            self.car_class_label.setText(f"Car Class: {self.current_vehicle_class}")
        
        has_qual = race_data.qual_ratio and race_data.qual_best_ai_lap_sec > 0 and race_data.qual_worst_ai_lap_sec > 0
        has_race = race_data.race_ratio and race_data.best_ai_lap_sec > 0 and race_data.worst_ai_lap_sec > 0
        
        race_dict = race_data.to_dict()
        race_id = self.db.save_race_session(race_dict)
        
        if race_id and self.autosave_enabled:
            points_added = 0
            for track, vehicle_name, ratio, lap_time, session_type in race_data.to_data_points_with_vehicles():
                try:
                    vehicle_class = get_vehicle_class(vehicle_name, self.class_mapping)
                    if self.db.add_data_point(track, vehicle_class, float(ratio), float(lap_time), session_type):
                        points_added += 1
                except (ValueError, TypeError) as e:
                    logger.error(f"Failed to add data point: {e}")
            if points_added > 0:
                logger.debug(f"Saved {points_added} new data points")
        
        if self.current_track and self.current_vehicle_class:
            if has_qual:
                self._update_formula_from_new_data(race_data, "qual")
            if has_race:
                self._update_formula_from_new_data(race_data, "race")
        
        self.autopilot_manager.reload_formulas()
        self._update_formulas_from_autopilot()
        self.update_display()
        
        if self.current_track and self.current_vehicle_class:
            self.update_formula_accuracy("qual")
            self.update_formula_accuracy("race")
        
        # Apply AI Target to autoratio if enabled
        if self.autoratio_enabled and race_data.aiw_path:
            logger.info("[AI TARGET] Running Autoratio with AI Target settings")
            
            # Apply AI Target for qualifying if we have user time
            if self.user_qualifying_sec > 0 and self.qual_best_ai and self.qual_worst_ai:
                new_qual_ratio = self.calculate_ratio_from_target("qual")
                if new_qual_ratio and abs(new_qual_ratio - self.last_qual_ratio) > 0.000001:
                    if self._validate_ratio(new_qual_ratio, "QualRatio"):
                        if self.autopilot_manager.engine._update_aiw_ratio(race_data.aiw_path, "QualRatio", new_qual_ratio):
                            self.last_qual_ratio = new_qual_ratio
                            self.qual_panel.update_ratio(new_qual_ratio)
                            logger.info(f"[AI TARGET] Updated QualRatio to {new_qual_ratio:.6f}")
            
            # Apply AI Target for race if we have user time
            if self.user_best_lap_sec > 0 and self.race_best_ai and self.race_worst_ai:
                new_race_ratio = self.calculate_ratio_from_target("race")
                if new_race_ratio and abs(new_race_ratio - self.last_race_ratio) > 0.000001:
                    if self._validate_ratio(new_race_ratio, "RaceRatio"):
                        if self.autopilot_manager.engine._update_aiw_ratio(race_data.aiw_path, "RaceRatio", new_race_ratio):
                            self.last_race_ratio = new_race_ratio
                            self.race_panel.update_ratio(new_race_ratio)
                            logger.info(f"[AI TARGET] Updated RaceRatio to {new_race_ratio:.6f}")
        
        self.autopilot_manager.reload_formulas()
        self._update_formulas_from_autopilot()
        self.update_display()
        
        if self.current_track and self.current_vehicle_class:
            self.update_formula_accuracy("qual")
            self.update_formula_accuracy("race")
        
        self.data_refresh_signal.emit()
        
        if self.advanced_window and self.advanced_window.isVisible() and hasattr(self.advanced_window, 'curve_graph'):
            self.advanced_window.curve_graph.update_current_info(
                track=self.current_track, vehicle=self.current_vehicle,
                qual_time=self.user_qualifying_sec if self.user_qualifying_sec > 0 else None,
                race_time=self.user_best_lap_sec if self.user_best_lap_sec > 0 else None,
                qual_ratio=self.last_qual_ratio, race_ratio=self.last_race_ratio)
            self.advanced_window.curve_graph.full_refresh()
    
    def load_data(self):
        if not self.db.database_exists():
            return
        self.all_tracks = self.db.get_all_tracks()
        if self.all_tracks and not self.current_track:
            self.current_track = self.all_tracks[0]
            self.track_label.setText(self.current_track)
            self.setWindowTitle(f"GTR2 Dynamic AI - {self.current_track}")
            self.qual_best_ai, self.qual_worst_ai = self._get_ai_times_for_track(self.current_track, "qual")
            self.race_best_ai, self.race_worst_ai = self._get_ai_times_for_track(self.current_track, "race")
        if self.autopilot_manager:
            self._update_formulas_from_autopilot()
        if self.current_track and self.current_vehicle_class:
            self.update_formula_accuracy("qual")
            self.update_formula_accuracy("race")
    
    def update_display(self):
        self.qual_panel.update_ratio(self.last_qual_ratio)
        self.qual_panel.update_ai_range(self.qual_best_ai, self.qual_worst_ai)
        self.qual_panel.update_user_time(self.user_qualifying_sec if self.user_qualifying_sec > 0 else None)
        self.qual_panel.update_formula(self.qual_a, self.qual_b)
        if self.qual_read_ratio is not None:
            self.qual_panel.update_last_read_ratio(self.qual_read_ratio)
        
        self.race_panel.update_ratio(self.last_race_ratio)
        self.race_panel.update_ai_range(self.race_best_ai, self.race_worst_ai)
        self.race_panel.update_user_time(self.user_best_lap_sec if self.user_best_lap_sec > 0 else None)
        self.race_panel.update_formula(self.race_a, self.race_b)
        if self.race_read_ratio is not None:
            self.race_panel.update_last_read_ratio(self.race_read_ratio)
        
        self.update_target_display()
    
    def closeEvent(self, event):
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
    config = get_config_with_defaults()
    base_path = config.get('base_path', '')
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
