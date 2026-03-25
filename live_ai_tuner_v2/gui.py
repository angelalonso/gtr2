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

from cfg_manage import get_formulas_dir
from global_curve import GlobalCurveManager
from aiw_manager import AIWManager

logger = logging.getLogger(__name__)


class RaceResultsSignal(QObject):
    """Signal for thread-safe GUI updates"""
    results_detected = pyqtSignal(dict)


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
        ratio_display = "Qualifying" if self.ratio_type == "QualRatio" else "Race"
        self.setWindowTitle(f"Confirm {ratio_display} Ratio Change")
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
        
        title = QLabel(f"Apply New {ratio_display} Ratio?")
        title.setStyleSheet("font-size: 14px; font-weight: bold; color: #FFA500;")
        layout.addWidget(title)
        
        layout.addSpacing(10)
        
        track_label = QLabel(f"Track: {self.track_name}")
        track_label.setStyleSheet("font-size: 12px;")
        layout.addWidget(track_label)
        
        layout.addSpacing(5)
        
        current_label = QLabel(f"Current {ratio_display} Ratio: {self.current_ratio:.6f}")
        current_label.setStyleSheet("color: #f44336;")
        layout.addWidget(current_label)
        
        new_label = QLabel(f"New {ratio_display} Ratio: {self.new_ratio:.6f}")
        new_label.setStyleSheet("color: #4CAF50; font-weight: bold;")
        layout.addWidget(new_label)
        
        diff = self.new_ratio - self.current_ratio
        if diff > 0:
            change = f"AI will be FASTER in {ratio_display.lower()} by {abs(diff):.4f}"
            change_color = "#4CAF50"
        elif diff < 0:
            change = f"AI will be SLOWER in {ratio_display.lower()} by {abs(diff):.4f}"
            change_color = "#f44336"
        else:
            change = "No change"
            change_color = "#888"
        
        change_label = QLabel(change)
        change_label.setStyleSheet(f"color: {change_color}; font-weight: bold;")
        layout.addWidget(change_label)
        
        layout.addSpacing(20)
        
        btn_layout = QHBoxLayout()
        
        apply_btn = QPushButton("Apply Change")
        apply_btn.setFixedHeight(40)
        apply_btn.clicked.connect(self.accept)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setFixedHeight(40)
        cancel_btn.setStyleSheet("background-color: #f44336;")
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
        ratio_display = "Qualifying" if self.ratio_type == "QualRatio" else "Race"
        self.setWindowTitle(f"Manual Entry - {self.track_name} ({ratio_display})")
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
        
        track_label = QLabel(f"Track: {self.track_name}")
        track_label.setStyleSheet("font-size: 12px; color: #FFA500;")
        layout.addWidget(track_label)
        
        layout.addSpacing(10)
        
        current_label = QLabel(f"Current {ratio_display} Ratio: {self.current_ratio:.6f}")
        current_label.setStyleSheet("color: #888;")
        layout.addWidget(current_label)
        
        layout.addSpacing(15)
        
        time_group = QGroupBox(f"Enter Your {ratio_display} Lap Time")
        time_layout = QGridLayout(time_group)
        
        time_layout.addWidget(QLabel("Minutes:"), 0, 0)
        self.minutes_spin = QSpinBox()
        self.minutes_spin.setRange(0, 99)
        self.minutes_spin.setFixedWidth(80)
        time_layout.addWidget(self.minutes_spin, 0, 1)
        
        time_layout.addWidget(QLabel("Seconds:"), 0, 2)
        self.seconds_spin = QSpinBox()
        self.seconds_spin.setRange(0, 59)
        self.seconds_spin.setFixedWidth(80)
        time_layout.addWidget(self.seconds_spin, 0, 3)
        
        time_layout.addWidget(QLabel("ms:"), 0, 4)
        self.ms_spin = QSpinBox()
        self.ms_spin.setRange(0, 999)
        self.ms_spin.setSingleStep(10)
        self.ms_spin.setFixedWidth(100)
        time_layout.addWidget(self.ms_spin, 0, 5)
        
        layout.addWidget(time_group)
        
        result_group = QGroupBox(f"Calculated {ratio_display} Ratio")
        result_layout = QVBoxLayout(result_group)
        
        self.result_label = QLabel("---")
        self.result_label.setAlignment(Qt.AlignCenter)
        self.result_label.setStyleSheet("color: #9C27B0; font-size: 18px; font-weight: bold;")
        result_layout.addWidget(self.result_label)
        
        layout.addWidget(result_group)
        
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #888; font-size: 10px;")
        layout.addWidget(self.status_label)
        
        layout.addSpacing(10)
        
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
        
        stats = self.curve_manager.get_stats()
        if stats['total_points'] > 0:
            if stats['r_squared']:
                info = f"Curve active: {stats['total_points']} points | R² = {stats['r_squared']:.4f}"
            else:
                info = f"Curve has {stats['total_points']} points (click 'Fit Curve' in editor)"
            info_label = QLabel(info)
            info_label.setStyleSheet("color: #888; font-size: 9px;")
            layout.addWidget(info_label)
    
    def get_lap_time(self) -> float:
        return (self.minutes_spin.value() * 60 + 
                self.seconds_spin.value() + 
                self.ms_spin.value() / 1000.0)
    
    def calculate(self):
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
        
        self.signal = RaceResultsSignal()
        self.signal.results_detected.connect(self._update_race_results)
        
        formulas_dir = get_formulas_dir()
        self.curve_manager = GlobalCurveManager(formulas_dir)
        self.aiw_manager = AIWManager(base_path / 'backups')
        
        self.last_results = None
        self.pending_change = None
        
        self.setup_ui()
        self.update_status()
        self.update_backup_info()
    
    def setup_ui(self):
        self.setWindowTitle("Live AI Tuner")
        self.setGeometry(100, 100, 900, 750)
        
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
            QGroupBox {
                color: #4CAF50;
                border: 2px solid #555;
                border-radius: 5px;
                margin-top: 8px;
                padding-top: 8px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
            QTextEdit {
                background-color: #2b2b2b;
                color: #4CAF50;
                border: 1px solid #4CAF50;
                border-radius: 3px;
                font-family: monospace;
            }
            QLineEdit {
                background-color: #3c3c3c;
                color: white;
                border: 1px solid #4CAF50;
                border-radius: 3px;
                padding: 5px;
            }
            QSpinBox, QDoubleSpinBox {
                background-color: #3c3c3c;
                color: white;
                border: 1px solid #4CAF50;
                border-radius: 3px;
                padding: 4px;
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
        
        # Separate sections for Qualifying and Race
        ratio_tabs = QTabWidget()
        ratio_tabs.setStyleSheet("QTabWidget::pane { border: 2px solid #4CAF50; } QTabBar::tab { color: white; padding: 8px; } QTabBar::tab:selected { color: #4CAF50; }")
        
        # Qualifying Tab
        quali_tab = QWidget()
        quali_layout = QVBoxLayout(quali_tab)
        self._create_ratio_section(quali_layout, "Qualifying", "QualRatio")
        ratio_tabs.addTab(quali_tab, "🏁 Qualifying")
        
        # Race Tab
        race_tab = QWidget()
        race_layout = QVBoxLayout(race_tab)
        self._create_ratio_section(race_layout, "Race", "RaceRatio")
        ratio_tabs.addTab(race_tab, "🏎️ Race")
        
        layout.addWidget(ratio_tabs, 1)
        
        # Action buttons
        action_layout = QHBoxLayout()
        
        self.open_editor_btn = QPushButton("📊 Open Global Curve Editor")
        self.open_editor_btn.setFixedHeight(40)
        self.open_editor_btn.setStyleSheet("background-color: #9C27B0;")
        self.open_editor_btn.clicked.connect(self.open_curve_editor)
        action_layout.addWidget(self.open_editor_btn)
        
        self.reset_btn = QPushButton("↺ Reset to Original")
        self.reset_btn.setFixedHeight(40)
        self.reset_btn.setStyleSheet("background-color: #f44336;")
        self.reset_btn.clicked.connect(self.reset_original)
        action_layout.addWidget(self.reset_btn)
        
        layout.addLayout(action_layout)
        
        # Info section
        info_layout = QVBoxLayout()
        
        self.curve_info = QLabel("")
        self.curve_info.setStyleSheet("color: #888; font-size: 10px;")
        info_layout.addWidget(self.curve_info)
        
        self.backup_info_label = QLabel("")
        self.backup_info_label.setStyleSheet("color: #888; font-size: 10px;")
        info_layout.addWidget(self.backup_info_label)
        
        layout.addLayout(info_layout)
        
        # Log
        log_group = QGroupBox("Activity Log")
        log_layout = QVBoxLayout(log_group)
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(120)
        log_layout.addWidget(self.log_text)
        
        layout.addWidget(log_group)
    
    def _create_ratio_section(self, parent_layout, session_name: str, ratio_type: str):
        """Create a section for either Qualifying or Race ratio"""
        # Current ratio display
        current_layout = QHBoxLayout()
        current_layout.addWidget(QLabel(f"Current {session_name} Ratio:"))
        ratio_label = QLabel("---")
        ratio_label.setStyleSheet("color: #4CAF50; font-weight: bold; font-size: 14px;")
        ratio_label.setMinimumWidth(150)
        current_layout.addWidget(ratio_label)
        current_layout.addStretch()
        parent_layout.addLayout(current_layout)
        
        # Store reference to the label
        if ratio_type == "QualRatio":
            self.qual_ratio_label = ratio_label
        else:
            self.race_ratio_label = ratio_label
        
        # AI times display
        ai_layout = QGridLayout()
        ai_layout.addWidget(QLabel("Best AI Lap:"), 0, 0)
        best_ai_label = QLabel("---")
        best_ai_label.setStyleSheet("color: #4CAF50;")
        ai_layout.addWidget(best_ai_label, 0, 1)
        
        ai_layout.addWidget(QLabel("Worst AI Lap:"), 0, 2)
        worst_ai_label = QLabel("---")
        worst_ai_label.setStyleSheet("color: #f44336;")
        ai_layout.addWidget(worst_ai_label, 0, 3)
        
        parent_layout.addLayout(ai_layout)
        
        # Store references
        if ratio_type == "QualRatio":
            self.qual_best_ai = best_ai_label
            self.qual_worst_ai = worst_ai_label
        else:
            self.race_best_ai = best_ai_label
            self.race_worst_ai = worst_ai_label
        
        # User time input
        time_layout = QHBoxLayout()
        time_layout.addWidget(QLabel(f"Your {session_name} Lap Time:"))
        time_input = QLineEdit()
        time_input.setPlaceholderText("e.g., 1:55.364 or leave blank to use detected")
        time_layout.addWidget(time_input, 1)
        parent_layout.addLayout(time_layout)
        
        # Buttons
        btn_layout = QHBoxLayout()
        
        calc_btn = QPushButton(f"Calculate {session_name} Ratio")
        calc_btn.clicked.connect(lambda: self.calculate_ratio_for_type(ratio_type, time_input.text()))
        btn_layout.addWidget(calc_btn)
        
        manual_btn = QPushButton("Manual Entry")
        manual_btn.clicked.connect(lambda: self.manual_entry_for_type(ratio_type))
        btn_layout.addWidget(manual_btn)
        
        parent_layout.addLayout(btn_layout)
        
        # Result display
        result_layout = QHBoxLayout()
        result_layout.addWidget(QLabel(f"Recommended {session_name} Ratio:"))
        result_label = QLabel("---")
        result_label.setStyleSheet("color: #9C27B0; font-size: 14px; font-weight: bold;")
        result_layout.addWidget(result_label)
        result_layout.addStretch()
        parent_layout.addLayout(result_layout)
        
        # Apply button
        apply_btn = QPushButton(f"Apply {session_name} Change")
        apply_btn.setFixedHeight(35)
        apply_btn.clicked.connect(lambda: self.apply_change_for_type(ratio_type))
        parent_layout.addWidget(apply_btn)
        
        # Store references
        if ratio_type == "QualRatio":
            self.qual_time_input = time_input
            self.qual_result_label = result_label
            self.qual_apply_btn = apply_btn
            self.qual_pending = None
        else:
            self.race_time_input = time_input
            self.race_result_label = result_label
            self.race_apply_btn = apply_btn
            self.race_pending = None
    
    def create_header(self):
        header = QWidget()
        layout = QHBoxLayout(header)
        layout.setContentsMargins(0, 0, 0, 10)
        
        title = QLabel("Live AI Tuner")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #FFA500;")
        layout.addWidget(title)
        
        layout.addStretch()
        
        backup_path_label = QLabel(f"Backups: {self.aiw_manager.backup_dir}")
        backup_path_label.setStyleSheet("color: #888; font-size: 9px;")
        layout.addWidget(backup_path_label)
        
        return header
    
    def update_status(self):
        stats = self.curve_manager.get_stats()
        if stats['total_points'] > 0:
            if stats['r_squared']:
                text = f"Global Curve: {stats['total_points']} points, R² = {stats['r_squared']:.4f}"
            else:
                text = f"Global Curve: {stats['total_points']} points (not fitted - click 'Open Global Curve Editor' and click 'Fit Curve')"
        else:
            text = "Global Curve: No data points. Add data from races to enable predictions."
        
        self.curve_info.setText(text)
    
    def update_backup_info(self):
        if not self.last_results:
            return
        
        aiw_filename = self.last_results.get('aiw_file')
        track_name = self.last_results.get('track_name')
        track_folder = self.last_results.get('track_folder', track_name)
        
        if not aiw_filename:
            return
        
        aiw_path = self.aiw_manager.find_aiw_file(aiw_filename, track_folder, self.base_path)
        
        if not aiw_path:
            return
        
        backup_info = self.aiw_manager.get_backup_info(aiw_path)
        
        if backup_info['original_exists']:
            backup_status = f"✓ Original backup: {backup_info['original_path']}"
            backup_color = "#4CAF50"
        else:
            backup_status = "⚠ No original backup yet (will be created on first change)"
            backup_color = "#FFA500"
        
        backup_text = f"{backup_status} | {backup_info['backup_count']} timestamp backups"
        self.backup_info_label.setText(backup_text)
        self.backup_info_label.setStyleSheet(f"color: {backup_color}; font-size: 10px;")
    
    def log_message(self, msg: str, level: str = "info"):
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
        
        logger.info(msg)
    
    def on_race_results_detected(self, data: dict):
        self.signal.results_detected.emit(data)
    
    def _update_race_results(self, data: dict):
        self.last_results = data
        
        track = data.get('track_name', 'Unknown')
        track_folder = data.get('track_folder', track)
        aiw = data.get('aiw_file', 'Unknown')
        best_ai = data.get('best_ai_lap', 'N/A')
        worst_ai = data.get('worst_ai_lap', 'N/A')
        user_best = data.get('user_best_lap', 'N/A')
        user_qual = data.get('user_qualifying', 'N/A')
        qual_ratio = data.get('qual_ratio')
        race_ratio = data.get('race_ratio')
        
        # Update ratio labels
        qual_str = f"{qual_ratio:.6f}" if qual_ratio is not None else 'Not found'
        race_str = f"{race_ratio:.6f}" if race_ratio is not None else 'Not found'
        
        if hasattr(self, 'qual_ratio_label'):
            self.qual_ratio_label.setText(qual_str)
            self.race_ratio_label.setText(race_str)
        
        # Update AI lap displays
        if hasattr(self, 'qual_best_ai'):
            self.qual_best_ai.setText(best_ai)
            self.qual_worst_ai.setText(worst_ai)
            self.race_best_ai.setText(best_ai)
            self.race_worst_ai.setText(worst_ai)
        
        # Auto-populate time inputs
        if user_qual and user_qual != 'N/A':
            self.qual_time_input.setText(user_qual)
        if user_best and user_best != 'N/A':
            self.race_time_input.setText(user_best)
        
        # Update results text
        text = f"""
Track: {track}
Track Folder: {track_folder}
AIW File: {aiw}

Current Ratios:
  Qualifying: {qual_str}
  Race: {race_str}

AI Lap Times:
  Best: {best_ai}
  Worst: {worst_ai}

User Times:
  Qualifying: {user_qual}
  Best Race Lap: {user_best}
"""
        self.results_text.setText(text)
        
        self.update_backup_info()
        self.log_message(f"Race results detected for {track}", "success")
    
    def calculate_ratio_for_type(self, ratio_type: str, user_time_str: str = None):
        """Calculate ratio for a specific type (Qualifying or Race)"""
        if not self.last_results:
            self.log_message("No race results available. Waiting for race data...", "warning")
            return
        
        track_name = self.last_results.get('track_name')
        if not track_name:
            self.log_message("No track name found in results", "error")
            return
        
        # Get user time
        if not user_time_str or not user_time_str.strip():
            if ratio_type == "QualRatio":
                user_time_str = self.last_results.get('user_qualifying')
            else:
                user_time_str = self.last_results.get('user_best_lap')
        
        if not user_time_str or user_time_str == 'N/A':
            self.log_message(f"No user lap time available for {ratio_type}. Please enter a lap time.", "warning")
            return
        
        # Parse time
        user_time = self._parse_time(user_time_str)
        if user_time is None:
            self.log_message(f"Invalid time format: {user_time_str}. Use format like '1:55.364'", "error")
            return
        
        # Calculate ratio using global curve
        ratio = self.curve_manager.predict_ratio(user_time, track_name)
        
        if ratio is None:
            self.log_message(f"Could not calculate ratio for time {user_time_str}. The global curve may not be fitted yet or the time is outside range.", "error")
            self.log_message("Go to 'Open Global Curve Editor' and click 'Fit Curve' to fit the curve to your data.", "info")
            return
        
        # Get current ratio
        if ratio_type == "QualRatio":
            current_ratio = self.last_results.get('qual_ratio', 1.0)
            self.qual_result_label.setText(f"{ratio:.6f}")
            self.qual_pending = {'ratio_type': ratio_type, 'new_ratio': ratio, 'current_ratio': current_ratio, 'user_time': user_time}
            self.qual_apply_btn.setEnabled(True)
            self.log_message(f"Calculated {ratio_type}: {ratio:.6f} (current: {current_ratio:.6f})", "success")
        else:
            current_ratio = self.last_results.get('race_ratio', 1.0)
            self.race_result_label.setText(f"{ratio:.6f}")
            self.race_pending = {'ratio_type': ratio_type, 'new_ratio': ratio, 'current_ratio': current_ratio, 'user_time': user_time}
            self.race_apply_btn.setEnabled(True)
            self.log_message(f"Calculated {ratio_type}: {ratio:.6f} (current: {current_ratio:.6f})", "success")
    
    def manual_entry_for_type(self, ratio_type: str):
        """Open manual entry dialog for a specific ratio type"""
        if not self.last_results:
            self.log_message("No race results available. Please wait for race data first.", "warning")
            return
        
        track_name = self.last_results.get('track_name')
        if not track_name:
            self.log_message("No track name available", "error")
            return
        
        if ratio_type == "QualRatio":
            current_ratio = self.last_results.get('qual_ratio', 1.0)
        else:
            current_ratio = self.last_results.get('race_ratio', 1.0)
        
        dialog = ManualEntryDialog(track_name, current_ratio, ratio_type, self.curve_manager, self)
        
        if dialog.exec_() == QDialog.Accepted:
            new_ratio = dialog.get_ratio()
            if new_ratio:
                if ratio_type == "QualRatio":
                    self.qual_result_label.setText(f"{new_ratio:.6f}")
                    self.qual_pending = {'ratio_type': ratio_type, 'new_ratio': new_ratio, 'current_ratio': current_ratio, 'user_time': None}
                    self.qual_apply_btn.setEnabled(True)
                else:
                    self.race_result_label.setText(f"{new_ratio:.6f}")
                    self.race_pending = {'ratio_type': ratio_type, 'new_ratio': new_ratio, 'current_ratio': current_ratio, 'user_time': None}
                    self.race_apply_btn.setEnabled(True)
                self.log_message(f"Manual entry: calculated {ratio_type} {new_ratio:.6f}", "success")
    
    def apply_change_for_type(self, ratio_type: str):
        """Apply pending change for a specific ratio type"""
        if ratio_type == "QualRatio":
            pending = self.qual_pending
            if not pending:
                return
        else:
            pending = self.race_pending
            if not pending:
                return
        
        track_name = self.last_results.get('track_name')
        track_folder = self.last_results.get('track_folder', track_name)
        current_ratio = pending['current_ratio']
        new_ratio = pending['new_ratio']
        ratio_type_name = pending['ratio_type']
        
        # Confirm
        confirm = ConfirmApplyDialog(track_name, current_ratio, new_ratio, ratio_type_name, self)
        if not confirm.get_decision():
            self.log_message("Change cancelled by user", "warning")
            return
        
        # Find AIW file
        aiw_filename = self.last_results.get('aiw_file')
        if not aiw_filename:
            self.log_message("Cannot find AIW file name in results", "error")
            return
        
        aiw_path = self.aiw_manager.find_aiw_file(aiw_filename, track_folder, self.base_path)
        
        if not aiw_path or not aiw_path.exists():
            self.log_message(f"AIW file not found: {aiw_filename}", "error")
            return
        
        # Apply change
        if self.aiw_manager.update_ratio(aiw_path, ratio_type_name, new_ratio, create_backup=True):
            self.log_message(f"Applied {ratio_type_name} change: {current_ratio:.6f} -> {new_ratio:.6f}", "success")
            
            backup_info = self.aiw_manager.get_backup_info(aiw_path)
            self.log_message(f"Original backup: {backup_info['original_path']}", "info")
            
            # Clear pending
            if ratio_type == "QualRatio":
                self.qual_apply_btn.setEnabled(False)
                self.qual_pending = None
            else:
                self.race_apply_btn.setEnabled(False)
                self.race_pending = None
            
            # Add point to global curve if we have user time
            if pending.get('user_time'):
                self.curve_manager.add_point(track_name, new_ratio, pending['user_time'])
                self.log_message(f"Added data point to global curve", "info")
                self.update_status()
            
            # Update backup info
            self.update_backup_info()
        else:
            self.log_message(f"Failed to update {ratio_type_name}", "error")
    
    def _parse_time(self, time_str: str) -> Optional[float]:
        try:
            time_str = time_str.strip()
            if ':' in time_str:
                parts = time_str.split(':')
                minutes = int(parts[0])
                seconds = float(parts[1])
                return minutes * 60 + seconds
            else:
                return float(time_str)
        except (ValueError, IndexError):
            return None
    
    def reset_original(self):
        """Reset to original values from backup"""
        if not self.last_results:
            return
        
        track_name = self.last_results.get('track_name')
        track_folder = self.last_results.get('track_folder', track_name)
        aiw_filename = self.last_results.get('aiw_file')
        
        if not aiw_filename:
            return
        
        aiw_path = self.aiw_manager.find_aiw_file(aiw_filename, track_folder, self.base_path)
        
        if not aiw_path:
            self.log_message("AIW file not found", "error")
            return
        
        if not self.aiw_manager.has_original_backup(aiw_path):
            self.log_message("No original backup found. Cannot restore.", "warning")
            return
        
        reply = QMessageBox.question(self, "Confirm Restore", 
                                    f"Restore original AIW file for {track_name}?\n\n"
                                    f"This will discard all changes made to this file.",
                                    QMessageBox.Yes | QMessageBox.No)
        
        if reply != QMessageBox.Yes:
            return
        
        if self.aiw_manager.restore_original(aiw_path):
            self.log_message(f"Restored original AIW file for {track_name}", "success")
            
            # Refresh ratios
            qual, race = self.aiw_manager.read_ratios(aiw_path)
            if self.last_results:
                self.last_results['qual_ratio'] = qual
                self.last_results['race_ratio'] = race
                self._update_race_results(self.last_results)
            
            self.update_backup_info()
            
            # Clear pending changes
            if hasattr(self, 'qual_pending'):
                self.qual_pending = None
                self.qual_apply_btn.setEnabled(False)
            if hasattr(self, 'race_pending'):
                self.race_pending = None
                self.race_apply_btn.setEnabled(False)
        else:
            self.log_message("Failed to restore original backup", "error")
    
    def open_curve_editor(self):
        try:
            from global_curve_builder import GlobalCurveBuilderDialog
            dialog = GlobalCurveBuilderDialog(self, get_formulas_dir())
            dialog.exec_()
            self.update_status()
        except ImportError as e:
            self.log_message(f"Could not open curve editor: {e}", "error")
    
    def run(self):
        self.show()
    
    def quit(self):
        self.close()
