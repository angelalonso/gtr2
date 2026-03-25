"""
GUI for Live AI Tuner - Main window and dialogs
"""

import sys
import logging
from pathlib import Path
from typing import Optional
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *

from cfg_manage import get_formulas_dir, get_auto_apply, get_backup_enabled
from global_curve import GlobalCurveManager
from aiw_manager import AIWManager
from ratio_calculator import RatioCalculator

logger = logging.getLogger(__name__)


class ConfirmApplyDialog(QDialog):
    """Dialog to confirm applying new ratio"""
    
    def __init__(self, track_name: str, current_ratio: float, new_ratio: float, 
                 ratio_type: str, parent=None):
        super().__init__(parent)
        self.track_name = track_name
        self.current_ratio = current_ratio
        self.new_ratio = new_ratio
        self.ratio_type = ratio_type
        self.setup_ui()
    
    def setup_ui(self):
        self.setWindowTitle("Confirm Ratio Change")
        self.setModal(True)
        self.setMinimumWidth(500)
        
        self.setStyleSheet("""
            QDialog {
                background-color: #2b2b2b;
            }
            QLabel {
                color: white;
            }
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 3px;
                padding: 8px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        
        layout = QVBoxLayout(self)
        
        # Title
        title = QLabel("Apply New AI Ratio?")
        title.setStyleSheet("font-size: 14px; font-weight: bold; color: #FFA500;")
        layout.addWidget(title)
        
        layout.addSpacing(10)
        
        # Track info
        track_label = QLabel(f"Track: {self.track_name}")
        track_label.setStyleSheet("font-size: 12px;")
        layout.addWidget(track_label)
        
        layout.addSpacing(5)
        
        # Ratio comparison
        current_label = QLabel(f"Current {self.ratio_type}: {self.current_ratio:.6f}")
        current_label.setStyleSheet("color: #f44336;")
        layout.addWidget(current_label)
        
        new_label = QLabel(f"New {self.ratio_type}: {self.new_ratio:.6f}")
        new_label.setStyleSheet("color: #4CAF50; font-weight: bold;")
        layout.addWidget(new_label)
        
        # Change direction
        diff = self.new_ratio - self.current_ratio
        if diff > 0:
            change = f"AI will be FASTER by {diff:.4f}"
            change_color = "#4CAF50"
        elif diff < 0:
            change = f"AI will be SLOWER by {abs(diff):.4f}"
            change_color = "#f44336"
        else:
            change = "No change"
            change_color = "#888"
        
        change_label = QLabel(change)
        change_label.setStyleSheet(f"color: {change_color}; font-weight: bold;")
        layout.addWidget(change_label)
        
        layout.addSpacing(20)
        
        # Buttons
        btn_layout = QHBoxLayout()
        
        apply_btn = QPushButton("Apply Change")
        apply_btn.setFixedHeight(40)
        apply_btn.setStyleSheet("background-color: #4CAF50; font-size: 12px;")
        apply_btn.clicked.connect(self.accept)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setFixedHeight(40)
        cancel_btn.setStyleSheet("background-color: #f44336; font-size: 12px;")
        cancel_btn.clicked.connect(self.reject)
        
        btn_layout.addWidget(apply_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)
    
    def get_decision(self) -> bool:
        return self.exec_() == QDialog.Accepted


class ManualEntryDialog(QDialog):
    """Dialog for manual entry of lap times and ratio calculation"""
    
    def __init__(self, track_name: str, current_ratio: float, ratio_type: str,
                 curve_manager: GlobalCurveManager, parent=None):
        super().__init__(parent)
        self.track_name = track_name
        self.current_ratio = current_ratio
        self.ratio_type = ratio_type
        self.curve_manager = curve_manager
        self.calculated_ratio = None
        self.setup_ui()
    
    def setup_ui(self):
        self.setWindowTitle(f"Manual Entry - {self.track_name}")
        self.setModal(True)
        self.setMinimumWidth(450)
        
        self.setStyleSheet("""
            QDialog {
                background-color: #2b2b2b;
            }
            QLabel {
                color: white;
            }
            QGroupBox {
                color: #4CAF50;
                border: 2px solid #555;
                border-radius: 5px;
                margin-top: 8px;
                padding-top: 8px;
            }
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 3px;
                padding: 8px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QSpinBox, QDoubleSpinBox {
                background-color: #3c3c3c;
                color: white;
                border: 1px solid #4CAF50;
                border-radius: 3px;
                padding: 4px;
            }
        """)
        
        layout = QVBoxLayout(self)
        
        # Track info
        track_label = QLabel(f"Track: {self.track_name}")
        track_label.setStyleSheet("font-size: 12px; color: #FFA500;")
        layout.addWidget(track_label)
        
        layout.addSpacing(10)
        
        # Current ratio
        current_label = QLabel(f"Current {self.ratio_type}: {self.current_ratio:.6f}")
        current_label.setStyleSheet("color: #888;")
        layout.addWidget(current_label)
        
        layout.addSpacing(15)
        
        # Lap time input group
        time_group = QGroupBox("Enter Your Lap Time")
        time_layout = QGridLayout(time_group)
        
        # Minutes
        time_layout.addWidget(QLabel("Minutes:"), 0, 0)
        self.minutes_spin = QSpinBox()
        self.minutes_spin.setRange(0, 99)
        self.minutes_spin.setFixedWidth(80)
        time_layout.addWidget(self.minutes_spin, 0, 1)
        
        # Seconds
        time_layout.addWidget(QLabel("Seconds:"), 0, 2)
        self.seconds_spin = QSpinBox()
        self.seconds_spin.setRange(0, 59)
        self.seconds_spin.setFixedWidth(80)
        time_layout.addWidget(self.seconds_spin, 0, 3)
        
        # Milliseconds
        time_layout.addWidget(QLabel("ms:"), 0, 4)
        self.ms_spin = QSpinBox()
        self.ms_spin.setRange(0, 999)
        self.ms_spin.setSingleStep(10)
        self.ms_spin.setFixedWidth(100)
        time_layout.addWidget(self.ms_spin, 0, 5)
        
        layout.addWidget(time_group)
        
        # Result
        result_group = QGroupBox("Calculated Ratio")
        result_layout = QVBoxLayout(result_group)
        
        self.result_label = QLabel("---")
        self.result_label.setAlignment(Qt.AlignCenter)
        self.result_label.setStyleSheet("color: #9C27B0; font-size: 18px; font-weight: bold;")
        result_layout.addWidget(self.result_label)
        
        layout.addWidget(result_group)
        
        # Status
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #888; font-size: 10px;")
        layout.addWidget(self.status_label)
        
        layout.addSpacing(10)
        
        # Buttons
        btn_layout = QHBoxLayout()
        
        self.calc_btn = QPushButton("Calculate")
        self.calc_btn.clicked.connect(self.calculate)
        btn_layout.addWidget(self.calc_btn)
        
        self.apply_btn = QPushButton("Apply Ratio")
        self.apply_btn.setEnabled(False)
        self.apply_btn.clicked.connect(self.accept)
        btn_layout.addWidget(self.apply_btn)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        
        layout.addLayout(btn_layout)
        
        # Show curve stats if available
        stats = self.curve_manager.get_stats()
        if stats['total_points'] > 0:
            if stats['r_squared']:
                info = f"Curve active: {stats['total_points']} points | R² = {stats['r_squared']:.4f}"
            else:
                info = f"Curve has {stats['total_points']} points (not fitted)"
            info_label = QLabel(info)
            info_label.setStyleSheet("color: #888; font-size: 9px;")
            layout.addWidget(info_label)
    
    def get_lap_time(self) -> float:
        """Get lap time in seconds"""
        return (self.minutes_spin.value() * 60 + 
                self.seconds_spin.value() + 
                self.ms_spin.value() / 1000.0)
    
    def calculate(self):
        """Calculate ratio from lap time"""
        lap_time = self.get_lap_time()
        
        if lap_time <= 0:
            self.status_label.setText("Please enter a valid lap time")
            return
        
        ratio = self.curve_manager.predict_ratio(lap_time, self.track_name)
        
        if ratio is not None:
            self.calculated_ratio = ratio
            self.result_label.setText(f"{ratio:.6f}")
            self.apply_btn.setEnabled(True)
            self.status_label.setText("✓ Ratio calculated successfully")
        else:
            self.result_label.setText("Outside range")
            self.apply_btn.setEnabled(False)
            self.status_label.setText("Lap time outside the valid range for this track")
    
    def get_ratio(self) -> float:
        return self.calculated_ratio


class MainWindow(QMainWindow):
    """Main GUI window"""
    
    def __init__(self, base_path: Path, monitor_folder: Path, target_file: Path):
        super().__init__()
        self.base_path = base_path
        self.monitor_folder = monitor_folder
        self.target_file = target_file
        
        # Initialize managers
        formulas_dir = get_formulas_dir()
        self.curve_manager = GlobalCurveManager(formulas_dir)
        self.aiw_manager = AIWManager(base_path / 'backups')
        
        self.last_results = None
        self.pending_change = None
        
        self.setup_ui()
        self.update_status()
    
    def setup_ui(self):
        self.setWindowTitle("Live AI Tuner")
        self.setGeometry(100, 100, 800, 600)
        
        # Apply dark theme
        self.setStyleSheet("""
            QMainWindow {
                background-color: #1e1e1e;
            }
            QLabel {
                color: white;
            }
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:disabled {
                background-color: #666;
            }
            QGroupBox {
                color: #4CAF50;
                border: 2px solid #555;
                border-radius: 5px;
                margin-top: 8px;
                padding-top: 8px;
            }
            QTextEdit {
                background-color: #2b2b2b;
                color: #4CAF50;
                border: 1px solid #4CAF50;
                border-radius: 3px;
                font-family: monospace;
            }
            QProgressBar {
                border: 1px solid #555;
                border-radius: 3px;
                text-align: center;
                color: white;
            }
            QProgressBar::chunk {
                background-color: #4CAF50;
                border-radius: 2px;
            }
        """)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Header
        header = self.create_header()
        layout.addWidget(header)
        
        # Status section
        status_group = QGroupBox("Monitoring Status")
        status_layout = QVBoxLayout(status_group)
        
        self.status_indicator = QLabel("● ACTIVE")
        self.status_indicator.setStyleSheet("color: #4CAF50; font-size: 12px; font-weight: bold;")
        status_layout.addWidget(self.status_indicator)
        
        self.monitor_path_label = QLabel(f"Monitoring: {self.target_file}")
        self.monitor_path_label.setStyleSheet("color: #888; font-size: 10px;")
        status_layout.addWidget(self.monitor_path_label)
        
        layout.addWidget(status_group)
        
        # Race Results section
        results_group = QGroupBox("Latest Race Results")
        results_layout = QVBoxLayout(results_group)
        
        self.results_text = QTextEdit()
        self.results_text.setReadOnly(True)
        self.results_text.setMaximumHeight(150)
        results_layout.addWidget(self.results_text)
        
        layout.addWidget(results_group)
        
        # Calculation section
        calc_group = QGroupBox("Ratio Calculation")
        calc_layout = QGridLayout(calc_group)
        
        # AI times
        calc_layout.addWidget(QLabel("Best AI Lap:"), 0, 0)
        self.best_ai_label = QLabel("---")
        self.best_ai_label.setStyleSheet("color: #4CAF50; font-weight: bold;")
        calc_layout.addWidget(self.best_ai_label, 0, 1)
        
        calc_layout.addWidget(QLabel("Worst AI Lap:"), 0, 2)
        self.worst_ai_label = QLabel("---")
        self.worst_ai_label.setStyleSheet("color: #f44336; font-weight: bold;")
        calc_layout.addWidget(self.worst_ai_label, 0, 3)
        
        # User time
        calc_layout.addWidget(QLabel("Your Lap Time:"), 1, 0)
        self.user_time_input = QLineEdit()
        self.user_time_input.setPlaceholderText("Enter lap time (e.g., 1:55.364) or leave blank to use detected")
        self.user_time_input.setStyleSheet("""
            QLineEdit {
                background-color: #3c3c3c;
                color: white;
                border: 1px solid #4CAF50;
                border-radius: 3px;
                padding: 5px;
            }
        """)
        calc_layout.addWidget(self.user_time_input, 1, 1, 1, 3)
        
        # Buttons
        btn_layout = QHBoxLayout()
        
        self.calc_btn = QPushButton("Calculate Optimal Ratio")
        self.calc_btn.setFixedHeight(35)
        self.calc_btn.clicked.connect(self.calculate_ratio)
        btn_layout.addWidget(self.calc_btn)
        
        self.manual_btn = QPushButton("Manual Entry")
        self.manual_btn.setFixedHeight(35)
        self.manual_btn.clicked.connect(self.manual_entry)
        btn_layout.addWidget(self.manual_btn)
        
        calc_layout.addLayout(btn_layout, 2, 0, 1, 4)
        
        # Result
        calc_layout.addWidget(QLabel("Recommended Ratio:"), 3, 0)
        self.recommended_label = QLabel("---")
        self.recommended_label.setStyleSheet("color: #9C27B0; font-size: 14px; font-weight: bold;")
        calc_layout.addWidget(self.recommended_label, 3, 1, 1, 3)
        
        layout.addWidget(calc_group)
        
        # Action buttons
        action_layout = QHBoxLayout()
        
        self.apply_btn = QPushButton("Apply Change")
        self.apply_btn.setFixedHeight(40)
        self.apply_btn.setEnabled(False)
        self.apply_btn.clicked.connect(self.apply_change)
        action_layout.addWidget(self.apply_btn)
        
        self.reset_btn = QPushButton("Reset to Original")
        self.reset_btn.setFixedHeight(40)
        self.reset_btn.setEnabled(False)
        self.reset_btn.clicked.connect(self.reset_original)
        action_layout.addWidget(self.reset_btn)
        
        self.open_editor_btn = QPushButton("Open Global Curve Editor")
        self.open_editor_btn.setFixedHeight(40)
        self.open_editor_btn.setStyleSheet("background-color: #9C27B0;")
        self.open_editor_btn.clicked.connect(self.open_curve_editor)
        action_layout.addWidget(self.open_editor_btn)
        
        layout.addLayout(action_layout)
        
        # Curve info
        info_layout = QHBoxLayout()
        self.curve_info = QLabel("")
        self.curve_info.setStyleSheet("color: #888; font-size: 10px;")
        info_layout.addWidget(self.curve_info)
        info_layout.addStretch()
        layout.addLayout(info_layout)
        
        # Log
        log_group = QGroupBox("Activity Log")
        log_layout = QVBoxLayout(log_group)
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(120)
        log_layout.addWidget(self.log_text)
        
        layout.addWidget(log_group)
    
    def create_header(self):
        """Create header widget"""
        header = QWidget()
        layout = QHBoxLayout(header)
        layout.setContentsMargins(0, 0, 0, 10)
        
        title = QLabel("Live AI Tuner")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #FFA500;")
        layout.addWidget(title)
        
        layout.addStretch()
        
        # Settings button (placeholder for future)
        settings_btn = QPushButton("⚙ Settings")
        settings_btn.setFixedHeight(30)
        settings_btn.setFixedWidth(80)
        settings_btn.setStyleSheet("background-color: #555;")
        settings_btn.clicked.connect(self.open_settings)
        layout.addWidget(settings_btn)
        
        return header
    
    def update_status(self):
        """Update curve info display"""
        stats = self.curve_manager.get_stats()
        if stats['total_points'] > 0:
            if stats['r_squared']:
                text = f"Global Curve: {stats['total_points']} points, R² = {stats['r_squared']:.4f}"
            else:
                text = f"Global Curve: {stats['total_points']} points (not fitted)"
        else:
            text = "Global Curve: No data points. Add data from races."
        
        self.curve_info.setText(text)
    
    def log_message(self, msg: str, level: str = "info"):
        """Add message to log display"""
        from datetime import datetime
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        colors = {
            "info": "#888",
            "success": "#4CAF50",
            "warning": "#FFA500",
            "error": "#f44336"
        }
        
        color = colors.get(level, "#888")
        self.log_text.append(f'<span style="color: {color};">[{timestamp}] {msg}</span>')
        self.log_text.ensureCursorVisible()
        
        # Also log to console
        logger.info(msg)
    
    def on_race_results_detected(self, data: dict):
        """Called when new race results are detected"""
        self.last_results = data
        
        # Update results text
        track = data.get('track_name', 'Unknown')
        aiw = data.get('aiw_file', 'Unknown')
        best_ai = data.get('best_ai_lap', 'N/A')
        worst_ai = data.get('worst_ai_lap', 'N/A')
        user_best = data.get('user_best_lap', 'N/A')
        user_qual = data.get('user_qualifying', 'N/A')
        qual_ratio = data.get('qual_ratio')
        race_ratio = data.get('race_ratio')
        
        text = f"""
Track: {track}
AIW File: {aiw}
Current Ratios: Qual={qual_ratio:.6f if qual_ratio else 'N/A'}, Race={race_ratio:.6f if race_ratio else 'N/A'}

AI Lap Times:
  Best: {best_ai}
  Worst: {worst_ai}

User Times:
  Best Lap: {user_best}
  Qualifying: {user_qual}
"""
        self.results_text.setText(text)
        
        # Update AI lap labels
        self.best_ai_label.setText(best_ai)
        self.worst_ai_label.setText(worst_ai)
        
        # Auto-populate user time if available
        if user_best and user_best != 'N/A':
            self.user_time_input.setText(user_best)
            self.log_message(f"Detected user best lap: {user_best}", "success")
        elif user_qual and user_qual != 'N/A':
            self.user_time_input.setText(user_qual)
            self.log_message(f"Detected user qualifying: {user_qual}", "success")
        
        self.log_message(f"Race results detected for {track}", "success")
    
    def calculate_ratio(self):
        """Calculate optimal ratio based on user time"""
        if not self.last_results:
            self.log_message("No race results available. Waiting for race data...", "warning")
            return
        
        # Get user time
        user_time_str = self.user_time_input.text().strip()
        if not user_time_str:
            user_time_str = self.last_results.get('user_best_lap') or self.last_results.get('user_qualifying')
        
        if not user_time_str or user_time_str == 'N/A':
            self.log_message("No user lap time available. Please enter a lap time or wait for race results.", "warning")
            return
        
        # Parse time string
        user_time = self._parse_time(user_time_str)
        if user_time is None:
            self.log_message(f"Invalid time format: {user_time_str}. Use format like '1:55.364'", "error")
            return
        
        track_name = self.last_results.get('track_name')
        if not track_name:
            self.log_message("No track name found in results", "error")
            return
        
        # Calculate ratio
        ratio = self.curve_manager.predict_ratio(user_time, track_name)
        
        if ratio is None:
            self.log_message(f"Could not calculate ratio for time {user_time_str} on {track_name}. Time may be outside valid range.", "error")
            return
        
        # Get current ratio
        current_ratio = self.last_results.get('race_ratio') or self.last_results.get('qual_ratio')
        if current_ratio is None:
            current_ratio = 1.0
        
        self.recommended_label.setText(f"{ratio:.6f}")
        self.pending_change = {
            'track_name': track_name,
            'current_ratio': current_ratio,
            'new_ratio': ratio,
            'user_time': user_time,
            'ratio_type': 'RaceRatio'  # Default to RaceRatio
        }
        
        self.apply_btn.setEnabled(True)
        self.log_message(f"Calculated optimal ratio: {ratio:.6f} (current: {current_ratio:.6f})", "success")
    
    def _parse_time(self, time_str: str) -> Optional[float]:
        """Parse time string to seconds"""
        try:
            time_str = time_str.strip()
            
            # Format: mm:ss.sss or mm:ss.ms
            if ':' in time_str:
                parts = time_str.split(':')
                minutes = int(parts[0])
                seconds = float(parts[1])
                return minutes * 60 + seconds
            else:
                # Just seconds as float
                return float(time_str)
        except (ValueError, IndexError):
            return None
    
    def manual_entry(self):
        """Open manual entry dialog"""
        if not self.last_results:
            self.log_message("No race results available. Please wait for race data first.", "warning")
            return
        
        track_name = self.last_results.get('track_name')
        if not track_name:
            self.log_message("No track name available", "error")
            return
        
        current_ratio = self.last_results.get('race_ratio') or self.last_results.get('qual_ratio') or 1.0
        
        dialog = ManualEntryDialog(
            track_name, 
            current_ratio,
            'RaceRatio',
            self.curve_manager,
            self
        )
        
        if dialog.exec_() == QDialog.Accepted:
            new_ratio = dialog.get_ratio()
            if new_ratio:
                self.recommended_label.setText(f"{new_ratio:.6f}")
                self.pending_change = {
                    'track_name': track_name,
                    'current_ratio': current_ratio,
                    'new_ratio': new_ratio,
                    'user_time': None,
                    'ratio_type': 'RaceRatio'
                }
                self.apply_btn.setEnabled(True)
                self.log_message(f"Manual entry: calculated ratio {new_ratio:.6f}", "success")
    
    def apply_change(self):
        """Apply the pending ratio change"""
        if not self.pending_change:
            return
        
        track_name = self.pending_change['track_name']
        current_ratio = self.pending_change['current_ratio']
        new_ratio = self.pending_change['new_ratio']
        ratio_type = self.pending_change['ratio_type']
        
        # Confirm with user
        confirm = ConfirmApplyDialog(track_name, current_ratio, new_ratio, ratio_type, self)
        if not confirm.get_decision():
            self.log_message("Change cancelled by user", "warning")
            return
        
        # Find AIW file
        aiw_filename = self.last_results.get('aiw_file')
        if not aiw_filename:
            self.log_message("Cannot find AIW file name in results", "error")
            return
        
        aiw_path = self.aiw_manager.find_aiw_file(aiw_filename, track_name, self.base_path)
        
        if not aiw_path or not aiw_path.exists():
            self.log_message(f"AIW file not found: {aiw_filename}", "error")
            return
        
        # Create backup
        backup_path = self.aiw_manager.create_backup(aiw_path)
        if not backup_path:
            self.log_message("Failed to create backup", "error")
            return
        
        # Update ratio
        if self.aiw_manager.update_ratio(aiw_path, ratio_type, new_ratio):
            self.log_message(f"Applied {ratio_type} change: {current_ratio:.6f} -> {new_ratio:.6f}", "success")
            self.log_message(f"Backup saved: {backup_path}", "info")
            self.apply_btn.setEnabled(False)
            
            # Add point to global curve
            if self.pending_change.get('user_time'):
                self.curve_manager.add_point(track_name, new_ratio, self.pending_change['user_time'])
                self.log_message(f"Added data point to global curve", "info")
                self.update_status()
            
            self.pending_change = None
        else:
            self.log_message(f"Failed to update {ratio_type}", "error")
    
    def reset_original(self):
        """Reset to original values from backup"""
        if not self.last_results:
            return
        
        track_name = self.last_results.get('track_name')
        aiw_filename = self.last_results.get('aiw_file')
        
        if not aiw_filename:
            return
        
        aiw_path = self.aiw_manager.find_aiw_file(aiw_filename, track_name, self.base_path)
        
        if not aiw_path:
            self.log_message("AIW file not found", "error")
            return
        
        backup_path = self.aiw_manager.get_latest_backup(aiw_path)
        
        if not backup_path:
            self.log_message("No backup found for this file", "warning")
            return
        
        if self.aiw_manager.restore_from_backup(aiw_path, backup_path):
            self.log_message(f"Restored from backup: {backup_path.name}", "success")
            self.apply_btn.setEnabled(False)
        else:
            self.log_message("Failed to restore from backup", "error")
    
    def open_curve_editor(self):
        """Open the global curve editor window"""
        try:
            # Import here to avoid circular imports
            from global_curve_builder import GlobalCurveBuilderDialog
            dialog = GlobalCurveBuilderDialog(self, get_formulas_dir())
            dialog.exec_()
            self.update_status()
        except ImportError as e:
            self.log_message(f"Could not open curve editor: {e}", "error")
            self.log_message("Make sure global_curve_builder.py is in the same directory", "error")
    
    def open_settings(self):
        """Open settings dialog (placeholder)"""
        QMessageBox.information(self, "Settings", 
            "Settings will be available in a future update.\n\n"
            "Currently, you can edit cfg.yml manually to adjust:\n"
            "- formulas_dir: Path to global curve data\n"
            "- auto_apply: Auto-apply calculated ratios\n"
            "- backup_enabled: Enable/disable backups")
    
    def run(self):
        """Run the GUI"""
        self.show()
    
    def quit(self):
        """Quit the application"""
        self.close()


def run_gui(base_path: Path):
    """Run the GUI application"""
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    monitor_folder = base_path / 'UserData'
    target_file = monitor_folder / 'Log' / 'Results' / 'raceresults.txt'
    
    window = MainWindow(base_path, monitor_folder, target_file)
    window.run()
    
    return app.exec_()
