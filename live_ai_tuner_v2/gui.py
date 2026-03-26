"""
GUI for Live AI Tuner - Main window and dialogs
"""

import sys
import logging
from pathlib import Path
from typing import Optional, Dict
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
    """Dialog to confirm applying new ratio(s)"""
    
    def __init__(self, track_name: str, changes: Dict[str, Dict], parent=None):
        """
        changes: {
            'QualRatio': {'current': float, 'new': float},
            'RaceRatio': {'current': float, 'new': float}
        }
        """
        super().__init__(parent)
        self.track_name = track_name
        self.changes = changes
        self.setup_ui()
    
    def setup_ui(self):
        self.setWindowTitle(f"Confirm Ratio Changes - {self.track_name}")
        self.setModal(True)
        self.setMinimumWidth(550)
        
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
        title = QLabel("Apply Ratio Changes?")
        title.setStyleSheet("font-size: 14px; font-weight: bold; color: #FFA500;")
        layout.addWidget(title)
        
        layout.addSpacing(10)
        
        # Track info
        track_label = QLabel(f"Track: {self.track_name}")
        track_label.setStyleSheet("font-size: 12px;")
        layout.addWidget(track_label)
        
        layout.addSpacing(15)
        
        # Changes summary
        changes_group = QGroupBox("Changes to Apply")
        changes_layout = QVBoxLayout(changes_group)
        
        for ratio_type, data in self.changes.items():
            display_name = "Qualifying" if ratio_type == "QualRatio" else "Race"
            current = data['current']
            new = data['new']
            diff = new - current
            
            # Create frame for each change
            frame = QFrame()
            frame.setStyleSheet("""
                QFrame {
                    background-color: #3c3c3c;
                    border-radius: 4px;
                    padding: 5px;
                }
            """)
            frame_layout = QHBoxLayout(frame)
            
            # Ratio name
            name_label = QLabel(f"{display_name}:")
            name_label.setStyleSheet("font-weight: bold; min-width: 80px;")
            frame_layout.addWidget(name_label)
            
            # Current value
            current_label = QLabel(f"{current:.6f}")
            current_label.setStyleSheet("color: #f44336;")
            frame_layout.addWidget(current_label)
            
            # Arrow
            arrow_label = QLabel("→")
            arrow_label.setStyleSheet("color: #888;")
            frame_layout.addWidget(arrow_label)
            
            # New value
            new_label = QLabel(f"{new:.6f}")
            new_label.setStyleSheet("color: #4CAF50; font-weight: bold;")
            frame_layout.addWidget(new_label)
            
            # Change indicator
            if diff > 0:
                change_text = f"+{diff:.4f} (faster)"
                change_color = "#4CAF50"
            elif diff < 0:
                change_text = f"{diff:.4f} (slower)"
                change_color = "#f44336"
            else:
                change_text = "no change"
                change_color = "#888"
            
            change_label = QLabel(change_text)
            change_label.setStyleSheet(f"color: {change_color};")
            frame_layout.addWidget(change_label)
            
            frame_layout.addStretch()
            changes_layout.addWidget(frame)
        
        layout.addWidget(changes_group)
        
        layout.addSpacing(20)
        
        # Buttons
        btn_layout = QHBoxLayout()
        
        apply_btn = QPushButton("Apply All Changes")
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
    
    def __init__(self, track_name: str, current_ratios: Dict[str, float],
                 curve_manager: GlobalCurveManager, parent=None):
        super().__init__(parent)
        self.track_name = track_name
        self.current_ratios = current_ratios
        self.curve_manager = curve_manager
        self.calculated_ratios = {}  # ratio_type -> new_ratio
        self.setup_ui()
    
    def setup_ui(self):
        self.setWindowTitle(f"Manual Entry - {self.track_name}")
        self.setModal(True)
        self.setMinimumWidth(550)
        
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
            QCheckBox {
                color: white;
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
            }
        """)
        
        layout = QVBoxLayout(self)
        
        # Track info
        track_label = QLabel(f"Track: {self.track_name}")
        track_label.setStyleSheet("font-size: 12px; color: #FFA500;")
        layout.addWidget(track_label)
        
        layout.addSpacing(10)
        
        # Qualifying section
        quali_group = QGroupBox("Qualifying")
        quali_layout = QVBoxLayout(quali_group)
        
        # Checkbox to enable
        self.quali_enabled = QCheckBox("Adjust Qualifying Ratio")
        self.quali_enabled.setChecked(True)
        quali_layout.addWidget(self.quali_enabled)
        
        # Current ratio
        quali_current = QLabel(f"Current: {self.current_ratios.get('QualRatio', 1.0):.6f}")
        quali_current.setStyleSheet("color: #888; margin-left: 20px;")
        quali_layout.addWidget(quali_current)
        
        # Time input
        time_layout = QHBoxLayout()
        time_layout.addWidget(QLabel("Lap Time:"))
        self.quali_minutes = QSpinBox()
        self.quali_minutes.setRange(0, 99)
        self.quali_minutes.setFixedWidth(70)
        time_layout.addWidget(self.quali_minutes)
        time_layout.addWidget(QLabel(":"))
        self.quali_seconds = QSpinBox()
        self.quali_seconds.setRange(0, 59)
        self.quali_seconds.setFixedWidth(70)
        time_layout.addWidget(self.quali_seconds)
        time_layout.addWidget(QLabel("."))
        self.quali_ms = QSpinBox()
        self.quali_ms.setRange(0, 999)
        self.quali_ms.setSingleStep(10)
        self.quali_ms.setFixedWidth(90)
        time_layout.addWidget(self.quali_ms)
        time_layout.addWidget(QLabel("ms"))
        time_layout.addStretch()
        quali_layout.addLayout(time_layout)
        
        # Result
        self.quali_result = QLabel("---")
        self.quali_result.setAlignment(Qt.AlignRight)
        self.quali_result.setStyleSheet("color: #9C27B0; font-weight: bold; font-size: 14px;")
        quali_layout.addWidget(self.quali_result)
        
        layout.addWidget(quali_group)
        
        # Race section
        race_group = QGroupBox("Race")
        race_layout = QVBoxLayout(race_group)
        
        # Checkbox to enable
        self.race_enabled = QCheckBox("Adjust Race Ratio")
        self.race_enabled.setChecked(True)
        race_layout.addWidget(self.race_enabled)
        
        # Current ratio
        race_current = QLabel(f"Current: {self.current_ratios.get('RaceRatio', 1.0):.6f}")
        race_current.setStyleSheet("color: #888; margin-left: 20px;")
        race_layout.addWidget(race_current)
        
        # Time input
        race_time_layout = QHBoxLayout()
        race_time_layout.addWidget(QLabel("Lap Time:"))
        self.race_minutes = QSpinBox()
        self.race_minutes.setRange(0, 99)
        self.race_minutes.setFixedWidth(70)
        race_time_layout.addWidget(self.race_minutes)
        race_time_layout.addWidget(QLabel(":"))
        self.race_seconds = QSpinBox()
        self.race_seconds.setRange(0, 59)
        self.race_seconds.setFixedWidth(70)
        race_time_layout.addWidget(self.race_seconds)
        race_time_layout.addWidget(QLabel("."))
        self.race_ms = QSpinBox()
        self.race_ms.setRange(0, 999)
        self.race_ms.setSingleStep(10)
        self.race_ms.setFixedWidth(90)
        race_time_layout.addWidget(self.race_ms)
        race_time_layout.addWidget(QLabel("ms"))
        race_time_layout.addStretch()
        race_layout.addLayout(race_time_layout)
        
        # Result
        self.race_result = QLabel("---")
        self.race_result.setAlignment(Qt.AlignRight)
        self.race_result.setStyleSheet("color: #9C27B0; font-weight: bold; font-size: 14px;")
        race_layout.addWidget(self.race_result)
        
        layout.addWidget(race_group)
        
        # Calculate button
        self.calc_btn = QPushButton("Calculate Both")
        self.calc_btn.setFixedHeight(40)
        self.calc_btn.clicked.connect(self.calculate_both)
        layout.addWidget(self.calc_btn)
        
        # Status
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #888; font-size: 10px;")
        layout.addWidget(self.status_label)
        
        layout.addSpacing(10)
        
        # Buttons
        btn_layout = QHBoxLayout()
        
        self.apply_btn = QPushButton("Apply Selected Changes")
        self.apply_btn.setEnabled(False)
        self.apply_btn.setFixedHeight(40)
        self.apply_btn.clicked.connect(self.accept)
        btn_layout.addWidget(self.apply_btn)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setFixedHeight(40)
        cancel_btn.setStyleSheet("background-color: #f44336;")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        
        layout.addLayout(btn_layout)
        
        # Curve info
        stats = self.curve_manager.get_stats()
        if stats['total_points'] > 0:
            if stats['r_squared']:
                info = f"Curve: {stats['total_points']} points | R² = {stats['r_squared']:.4f}"
            else:
                info = f"Curve: {stats['total_points']} points (click Fit Curve first)"
            info_label = QLabel(info)
            info_label.setStyleSheet("color: #888; font-size: 9px;")
            layout.addWidget(info_label)
    
    def get_lap_time(self, minutes, seconds, ms) -> float:
        return minutes.value() * 60 + seconds.value() + ms.value() / 1000.0
    
    def calculate_both(self):
        """Calculate both ratios"""
        self.calculated_ratios.clear()
        any_calculated = False
        
        # Calculate Qualifying
        if self.quali_enabled.isChecked():
            lap_time = self.get_lap_time(self.quali_minutes, self.quali_seconds, self.quali_ms)
            if lap_time > 0:
                ratio = self.curve_manager.predict_ratio(lap_time, self.track_name)
                if ratio is not None:
                    self.calculated_ratios['QualRatio'] = ratio
                    self.quali_result.setText(f"{ratio:.6f}")
                    any_calculated = True
                else:
                    self.quali_result.setText("Outside range")
                    self.status_label.setText("Time outside valid range for this track")
            else:
                self.quali_result.setText("Enter time")
        
        # Calculate Race
        if self.race_enabled.isChecked():
            lap_time = self.get_lap_time(self.race_minutes, self.race_seconds, self.race_ms)
            if lap_time > 0:
                ratio = self.curve_manager.predict_ratio(lap_time, self.track_name)
                if ratio is not None:
                    self.calculated_ratios['RaceRatio'] = ratio
                    self.race_result.setText(f"{ratio:.6f}")
                    any_calculated = True
                else:
                    self.race_result.setText("Outside range")
                    self.status_label.setText("Time outside valid range for this track")
            else:
                self.race_result.setText("Enter time")
        
        if any_calculated:
            self.apply_btn.setEnabled(True)
            self.status_label.setText("✓ Ready to apply selected changes")
    
    def get_changes(self) -> Dict[str, float]:
        """Get the calculated changes"""
        return self.calculated_ratios


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
        self.pending_changes = {}  # ratio_type -> {'current': float, 'new': float}
        
        self.setup_ui()
        self.update_status()
        self.update_backup_info()
    
    def setup_ui(self):
        self.setWindowTitle("Live AI Tuner")
        self.setGeometry(100, 100, 900, 700)
        
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
            QCheckBox {
                color: white;
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
            }
        """)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        # Header
        header = self.create_header()
        main_layout.addWidget(header)
        
        # Status section
        status_group = QGroupBox("Monitoring Status")
        status_layout = QVBoxLayout(status_group)
        
        self.status_indicator = QLabel("● ACTIVE")
        self.status_indicator.setStyleSheet("color: #4CAF50; font-size: 12px; font-weight: bold;")
        status_layout.addWidget(self.status_indicator)
        
        self.monitor_path_label = QLabel(f"Monitoring: {self.target_file}")
        self.monitor_path_label.setStyleSheet("color: #888; font-size: 10px;")
        status_layout.addWidget(self.monitor_path_label)
        
        main_layout.addWidget(status_group)
        
        # Race Results section
        results_group = QGroupBox("Latest Race Results")
        results_layout = QVBoxLayout(results_group)
        
        self.results_text = QTextEdit()
        self.results_text.setReadOnly(True)
        self.results_text.setMaximumHeight(150)
        results_layout.addWidget(self.results_text)
        
        main_layout.addWidget(results_group)
        
        # Current Ratios Display
        ratios_group = QGroupBox("Current AIW Ratios")
        ratios_layout = QHBoxLayout(ratios_group)
        
        quali_ratio_frame = QFrame()
        quali_ratio_frame.setStyleSheet("background-color: #2b2b2b; border-radius: 4px; padding: 8px;")
        quali_ratio_layout = QVBoxLayout(quali_ratio_frame)
        quali_ratio_layout.addWidget(QLabel("🏁 Qualifying:"))
        self.current_qual_label = QLabel("---")
        self.current_qual_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #9C27B0;")
        quali_ratio_layout.addWidget(self.current_qual_label)
        ratios_layout.addWidget(quali_ratio_frame)
        
        race_ratio_frame = QFrame()
        race_ratio_frame.setStyleSheet("background-color: #2b2b2b; border-radius: 4px; padding: 8px;")
        race_ratio_layout = QVBoxLayout(race_ratio_frame)
        race_ratio_layout.addWidget(QLabel("🏎️ Race:"))
        self.current_race_label = QLabel("---")
        self.current_race_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #9C27B0;")
        race_ratio_layout.addWidget(self.current_race_label)
        ratios_layout.addWidget(race_ratio_frame)
        
        ratios_layout.addStretch()
        main_layout.addWidget(ratios_group)
        
        # AI Times Display
        ai_times_group = QGroupBox("AI Lap Times")
        ai_times_layout = QGridLayout(ai_times_group)
        
        ai_times_layout.addWidget(QLabel("Best AI Lap:"), 0, 0)
        self.best_ai_label = QLabel("---")
        self.best_ai_label.setStyleSheet("color: #4CAF50; font-weight: bold;")
        ai_times_layout.addWidget(self.best_ai_label, 0, 1)
        
        ai_times_layout.addWidget(QLabel("Worst AI Lap:"), 0, 2)
        self.worst_ai_label = QLabel("---")
        self.worst_ai_label.setStyleSheet("color: #f44336; font-weight: bold;")
        ai_times_layout.addWidget(self.worst_ai_label, 0, 3)
        
        main_layout.addWidget(ai_times_group)
        
        # User Times Input Section
        input_group = QGroupBox("Your Lap Times")
        input_layout = QGridLayout(input_group)
        
        # Qualifying row
        input_layout.addWidget(QLabel("Qualifying:"), 0, 0)
        self.qual_time_input = QLineEdit()
        self.qual_time_input.setPlaceholderText("e.g., 1:55.364 or leave blank for auto")
        input_layout.addWidget(self.qual_time_input, 0, 1)
        
        self.qual_calc_btn = QPushButton("Calculate")
        self.qual_calc_btn.setFixedWidth(80)
        self.qual_calc_btn.clicked.connect(lambda: self.calculate_ratio("QualRatio"))
        input_layout.addWidget(self.qual_calc_btn, 0, 2)
        
        # Qualifying result
        input_layout.addWidget(QLabel("→"), 0, 3)
        self.qual_result_label = QLabel("---")
        self.qual_result_label.setStyleSheet("color: #9C27B0; font-weight: bold;")
        input_layout.addWidget(self.qual_result_label, 0, 4)
        
        # Race row
        input_layout.addWidget(QLabel("Race:"), 1, 0)
        self.race_time_input = QLineEdit()
        self.race_time_input.setPlaceholderText("e.g., 1:55.364 or leave blank for auto")
        input_layout.addWidget(self.race_time_input, 1, 1)
        
        self.race_calc_btn = QPushButton("Calculate")
        self.race_calc_btn.setFixedWidth(80)
        self.race_calc_btn.clicked.connect(lambda: self.calculate_ratio("RaceRatio"))
        input_layout.addWidget(self.race_calc_btn, 1, 2)
        
        # Race result
        input_layout.addWidget(QLabel("→"), 1, 3)
        self.race_result_label = QLabel("---")
        self.race_result_label.setStyleSheet("color: #9C27B0; font-weight: bold;")
        input_layout.addWidget(self.race_result_label, 1, 4)
        
        main_layout.addWidget(input_group)
        
        # Selection and Apply Section
        apply_group = QGroupBox("Apply Changes")
        apply_layout = QVBoxLayout(apply_group)
        
        # Selection checkboxes
        selection_layout = QHBoxLayout()
        self.apply_qual_check = QCheckBox("Apply Qualifying Ratio")
        self.apply_qual_check.setChecked(False)
        self.apply_qual_check.setStyleSheet("font-weight: bold;")
        selection_layout.addWidget(self.apply_qual_check)
        
        self.apply_race_check = QCheckBox("Apply Race Ratio")
        self.apply_race_check.setChecked(False)
        self.apply_race_check.setStyleSheet("font-weight: bold;")
        selection_layout.addWidget(self.apply_race_check)
        
        selection_layout.addStretch()
        apply_layout.addLayout(selection_layout)
        
        # Apply button
        self.apply_all_btn = QPushButton("Apply Selected Changes")
        self.apply_all_btn.setFixedHeight(45)
        self.apply_all_btn.setStyleSheet("background-color: #9C27B0; font-size: 14px;")
        self.apply_all_btn.setEnabled(False)
        self.apply_all_btn.clicked.connect(self.apply_selected_changes)
        apply_layout.addWidget(self.apply_all_btn)
        
        main_layout.addWidget(apply_group)
        
        # Manual Entry button
        self.manual_btn = QPushButton("✏️ Manual Entry (Advanced)")
        self.manual_btn.setFixedHeight(35)
        self.manual_btn.setStyleSheet("background-color: #FFA500;")
        self.manual_btn.clicked.connect(self.manual_entry)
        main_layout.addWidget(self.manual_btn)
        
        # Action buttons row
        action_layout = QHBoxLayout()
        
        self.open_editor_btn = QPushButton("📊 Open Global Curve Editor")
        self.open_editor_btn.setFixedHeight(35)
        self.open_editor_btn.setStyleSheet("background-color: #2196F3;")
        self.open_editor_btn.clicked.connect(self.open_curve_editor)
        action_layout.addWidget(self.open_editor_btn)
        
        self.reset_btn = QPushButton("↺ Reset to Original")
        self.reset_btn.setFixedHeight(35)
        self.reset_btn.setStyleSheet("background-color: #f44336;")
        self.reset_btn.clicked.connect(self.reset_original)
        action_layout.addWidget(self.reset_btn)
        
        action_layout.addStretch()
        main_layout.addLayout(action_layout)
        
        # Info section
        info_layout = QVBoxLayout()
        
        self.curve_info = QLabel("")
        self.curve_info.setStyleSheet("color: #888; font-size: 10px;")
        info_layout.addWidget(self.curve_info)
        
        self.backup_info_label = QLabel("")
        self.backup_info_label.setStyleSheet("color: #888; font-size: 10px;")
        info_layout.addWidget(self.backup_info_label)
        
        main_layout.addLayout(info_layout)
        
        # Log
        log_group = QGroupBox("Activity Log")
        log_layout = QVBoxLayout(log_group)
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(100)
        log_layout.addWidget(self.log_text)
        
        main_layout.addWidget(log_group)
    
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
                text = f"✓ Global Curve: {stats['total_points']} points | R² = {stats['r_squared']:.4f}"
                color = "#4CAF50"
            else:
                text = f"⚠ Global Curve: {stats['total_points']} points (not fitted - click 'Fit Curve' in editor)"
                color = "#FFA500"
        else:
            text = "⚠ No curve data. Add lap times from races to enable predictions."
            color = "#f44336"
        
        self.curve_info.setText(text)
        self.curve_info.setStyleSheet(f"color: {color}; font-size: 10px;")
    
    def update_backup_info(self):
        if not self.last_results:
            return
        
        aiw_filename = self.last_results.get('aiw_file')
        track_folder = self.last_results.get('track_folder')
        
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
        
        # Update current ratio displays
        qual_str = f"{qual_ratio:.6f}" if qual_ratio is not None else 'Not found'
        race_str = f"{race_ratio:.6f}" if race_ratio is not None else 'Not found'
        self.current_qual_label.setText(qual_str)
        self.current_race_label.setText(race_str)
        
        # Update AI times
        self.best_ai_label.setText(best_ai)
        self.worst_ai_label.setText(worst_ai)
        
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
    
    def calculate_ratio(self, ratio_type: str):
        """Calculate ratio for a specific type"""
        if not self.last_results:
            self.log_message("No race results available. Waiting for race data...", "warning")
            return
        
        track_name = self.last_results.get('track_name')
        if not track_name:
            self.log_message("No track name found in results", "error")
            return
        
        # Get user time
        if ratio_type == "QualRatio":
            user_time_str = self.qual_time_input.text().strip()
            if not user_time_str:
                user_time_str = self.last_results.get('user_qualifying')
            result_label = self.qual_result_label
        else:
            user_time_str = self.race_time_input.text().strip()
            if not user_time_str:
                user_time_str = self.last_results.get('user_best_lap')
            result_label = self.race_result_label
        
        if not user_time_str or user_time_str == 'N/A':
            self.log_message(f"No user lap time available for {ratio_type}. Please enter a lap time.", "warning")
            return
        
        # Parse time
        user_time = self._parse_time(user_time_str)
        if user_time is None:
            self.log_message(f"Invalid time format: {user_time_str}. Use format like '1:55.364'", "error")
            return
        
        # Calculate ratio
        ratio = self.curve_manager.predict_ratio(user_time, track_name)
        
        if ratio is None:
            self.log_message(f"Could not calculate ratio for time {user_time_str}. The global curve may not be fitted yet.", "error")
            self.log_message("Go to 'Open Global Curve Editor' and click 'Fit Curve' to fit the curve to your data.", "info")
            result_label.setText("Need curve fit")
            return
        
        # Get current ratio
        if ratio_type == "QualRatio":
            current_ratio = self.last_results.get('qual_ratio', 1.0)
        else:
            current_ratio = self.last_results.get('race_ratio', 1.0)
        
        # Store pending change
        self.pending_changes[ratio_type] = {
            'current': current_ratio,
            'new': ratio,
            'user_time': user_time
        }
        
        # Update display
        result_label.setText(f"{ratio:.6f}")
        
        # Enable the corresponding checkbox and the apply button
        if ratio_type == "QualRatio":
            self.apply_qual_check.setChecked(True)
        else:
            self.apply_race_check.setChecked(True)
        
        self.apply_all_btn.setEnabled(True)
        self.log_message(f"Calculated {ratio_type}: {ratio:.6f} (current: {current_ratio:.6f})", "success")
    
    def apply_selected_changes(self):
        """Apply only the selected ratio changes"""
        if not self.last_results:
            return
        
        # Build changes to apply
        changes_to_apply = {}
        for ratio_type, change in self.pending_changes.items():
            if ratio_type == "QualRatio" and self.apply_qual_check.isChecked():
                changes_to_apply[ratio_type] = change
            elif ratio_type == "RaceRatio" and self.apply_race_check.isChecked():
                changes_to_apply[ratio_type] = change
        
        if not changes_to_apply:
            self.log_message("No changes selected to apply", "warning")
            return
        
        track_name = self.last_results.get('track_name')
        track_folder = self.last_results.get('track_folder', track_name)
        
        # Confirm with user
        confirm = ConfirmApplyDialog(track_name, changes_to_apply, self)
        if not confirm.get_decision():
            self.log_message("Changes cancelled by user", "warning")
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
        
        # Apply each change
        success_count = 0
        for ratio_type, change in changes_to_apply.items():
            if self.aiw_manager.update_ratio(aiw_path, ratio_type, change['new'], create_backup=True):
                success_count += 1
                self.log_message(f"Applied {ratio_type}: {change['current']:.6f} → {change['new']:.6f}", "success")
                
                # Add point to global curve if we have user time
                if change.get('user_time'):
                    self.curve_manager.add_point(track_name, change['new'], change['user_time'])
                    self.log_message(f"Added data point to global curve", "info")
        
        if success_count > 0:
            self.log_message(f"Successfully applied {success_count} change(s)", "success")
            
            # Refresh ratios in results
            qual, race = self.aiw_manager.read_ratios(aiw_path)
            if self.last_results:
                self.last_results['qual_ratio'] = qual
                self.last_results['race_ratio'] = race
                self._update_race_results(self.last_results)
            
            self.update_backup_info()
            self.update_status()
            
            # Clear pending changes for applied ones
            for ratio_type in changes_to_apply:
                if ratio_type in self.pending_changes:
                    del self.pending_changes[ratio_type]
            
            # Clear results if both were applied
            if not self.pending_changes:
                self.qual_result_label.setText("---")
                self.race_result_label.setText("---")
                self.apply_qual_check.setChecked(False)
                self.apply_race_check.setChecked(False)
                self.apply_all_btn.setEnabled(False)
        else:
            self.log_message("Failed to apply changes", "error")
    
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
    
    def manual_entry(self):
        """Open manual entry dialog for both ratios"""
        if not self.last_results:
            self.log_message("No race results available. Please wait for race data first.", "warning")
            return
        
        track_name = self.last_results.get('track_name')
        if not track_name:
            self.log_message("No track name available", "error")
            return
        
        current_ratios = {
            'QualRatio': self.last_results.get('qual_ratio', 1.0),
            'RaceRatio': self.last_results.get('race_ratio', 1.0)
        }
        
        dialog = ManualEntryDialog(track_name, current_ratios, self.curve_manager, self)
        
        if dialog.exec_() == QDialog.Accepted:
            new_ratios = dialog.get_changes()
            if new_ratios:
                # Store pending changes
                self.pending_changes = {}
                for ratio_type, new_ratio in new_ratios.items():
                    current_ratio = current_ratios.get(ratio_type, 1.0)
                    self.pending_changes[ratio_type] = {
                        'current': current_ratio,
                        'new': new_ratio,
                        'user_time': None
                    }
                    
                    # Update display
                    if ratio_type == "QualRatio":
                        self.qual_result_label.setText(f"{new_ratio:.6f}")
                        self.apply_qual_check.setChecked(True)
                    else:
                        self.race_result_label.setText(f"{new_ratio:.6f}")
                        self.apply_race_check.setChecked(True)
                
                self.apply_all_btn.setEnabled(True)
                self.log_message(f"Manual entry: calculated {len(new_ratios)} ratio(s)", "success")
    
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
            self.pending_changes.clear()
            self.qual_result_label.setText("---")
            self.race_result_label.setText("---")
            self.apply_qual_check.setChecked(False)
            self.apply_race_check.setChecked(False)
            self.apply_all_btn.setEnabled(False)
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
