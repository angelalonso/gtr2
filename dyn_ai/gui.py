"""
GUI for Live AI Tuner - Main window and dialogs
UPDATED: UI layout improvements, compact design
"""

import sys
import logging
import csv
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List, Tuple
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *

from cfg_manage import get_formulas_dir, get_autopilot_enabled
from global_curve import GlobalCurveManager
from aiw_manager import AIWManager

logger = logging.getLogger(__name__)


class RaceResultsSignal(QObject):
    """Signal for thread-safe GUI updates"""
    results_detected = pyqtSignal(dict)


class AutopilotConfirmationDialog(QDialog):
    """Dialog to confirm autopilot action"""
    
    def __init__(self, track_name: str, car_class: str, formula: str, 
                 current_ratios: Dict[str, float], new_ratios: Dict[str, float], 
                 user_time: str, ai_time: str, parent=None):
        super().__init__(parent)
        self.track_name = track_name
        self.car_class = car_class
        self.formula = formula
        self.current_ratios = current_ratios
        self.new_ratios = new_ratios
        self.user_time = user_time
        self.ai_time = ai_time
        self.setup_ui()
    
    def setup_ui(self):
        self.setWindowTitle(f"Autopilot Confirmation - {self.track_name}")
        self.setModal(True)
        self.setMinimumWidth(600)
        
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
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
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
            QPushButton#cancel {
                background-color: #f44336;
            }
            QPushButton#cancel:hover {
                background-color: #d32f2f;
            }
        """)
        
        layout = QVBoxLayout(self)
        
        # Header with track name
        header = QLabel(f"🚗 Autopilot: {self.track_name}")
        header.setStyleSheet("font-size: 16px; font-weight: bold; color: #FFA500; padding: 10px;")
        header.setAlignment(Qt.AlignCenter)
        layout.addWidget(header)
        
        layout.addSpacing(10)
        
        # Vehicle info
        if self.car_class and self.car_class != "Unknown":
            vehicle_group = QGroupBox("Vehicle Information")
            vehicle_layout = QVBoxLayout(vehicle_group)
            
            vehicle_label = QLabel(f"Car Class: {self.car_class}")
            vehicle_label.setStyleSheet("font-size: 12px; font-weight: bold; color: #4CAF50;")
            vehicle_layout.addWidget(vehicle_label)
            
            layout.addWidget(vehicle_group)
            layout.addSpacing(10)
        
        # Formula info
        formula_group = QGroupBox("Curve Formula in Use")
        formula_layout = QVBoxLayout(formula_group)
        
        formula_label = QLabel(self.formula)
        formula_label.setStyleSheet("font-family: monospace; font-size: 11px; color: #9C27B0;")
        formula_label.setWordWrap(True)
        formula_layout.addWidget(formula_label)
        
        layout.addWidget(formula_group)
        layout.addSpacing(10)
        
        # Lap times
        times_group = QGroupBox("Lap Times")
        times_layout = QGridLayout(times_group)
        
        times_layout.addWidget(QLabel("Your Lap:"), 0, 0)
        times_layout.addWidget(QLabel(self.user_time), 0, 1)
        times_layout.addWidget(QLabel("AI Best:"), 1, 0)
        times_layout.addWidget(QLabel(self.ai_time), 1, 1)
        
        layout.addWidget(times_group)
        layout.addSpacing(10)
        
        # Ratio changes
        changes_group = QGroupBox("Ratio Changes")
        changes_layout = QVBoxLayout(changes_group)
        
        for ratio_type, new_value in self.new_ratios.items():
            current = self.current_ratios.get(ratio_type, 1.0)
            display_name = "Qualifying" if ratio_type == "QualRatio" else "Race"
            diff = new_value - current
            
            frame = QFrame()
            frame.setStyleSheet("""
                QFrame {
                    background-color: #3c3c3c;
                    border-radius: 4px;
                    padding: 8px;
                }
            """)
            frame_layout = QHBoxLayout(frame)
            
            name_label = QLabel(f"{display_name}:")
            name_label.setStyleSheet("font-weight: bold; min-width: 80px;")
            frame_layout.addWidget(name_label)
            
            current_label = QLabel(f"{current:.6f}")
            current_label.setStyleSheet("color: #f44336;")
            frame_layout.addWidget(current_label)
            
            arrow_label = QLabel("→")
            arrow_label.setStyleSheet("color: #888; font-weight: bold;")
            frame_layout.addWidget(arrow_label)
            
            new_label = QLabel(f"{new_value:.6f}")
            new_label.setStyleSheet("color: #4CAF50; font-weight: bold;")
            frame_layout.addWidget(new_label)
            
            if diff > 0:
                change_text = f"+{diff:.4f} (AI will be faster)"
                change_color = "#4CAF50"
            elif diff < 0:
                change_text = f"{diff:.4f} (AI will be slower)"
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
        
        apply_btn = QPushButton("✓ Apply Changes")
        apply_btn.setFixedHeight(45)
        apply_btn.setFixedWidth(150)
        apply_btn.clicked.connect(self.accept)
        
        cancel_btn = QPushButton("✗ Cancel")
        cancel_btn.setObjectName("cancel")
        cancel_btn.setFixedHeight(45)
        cancel_btn.setFixedWidth(150)
        cancel_btn.clicked.connect(self.reject)
        
        btn_layout.addStretch()
        btn_layout.addWidget(apply_btn)
        btn_layout.addWidget(cancel_btn)
        btn_layout.addStretch()
        
        layout.addLayout(btn_layout)
    
    def get_decision(self) -> bool:
        return self.exec_() == QDialog.Accepted


class SaveToHistoricDialog(QDialog):
    """Dialog for saving current data to historic.csv with car class"""
    
    def __init__(self, track_name: str, current_ratios: Dict[str, float], 
                 ai_times: Dict[str, float], user_times: Dict[str, float], 
                 vehicles: Dict[str, str], parent=None):
        super().__init__(parent)
        self.track_name = track_name
        self.current_ratios = current_ratios
        self.ai_times = ai_times
        self.user_times = user_times
        self.vehicles = vehicles
        self.car_class = ""
        self.setup_ui()
    
    def setup_ui(self):
        self.setWindowTitle(f"Save to Historic CSV - {self.track_name}")
        self.setModal(True)
        self.setMinimumWidth(650)
        
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
                border-radius: 3px;
                padding: 5px;
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
        """)
        
        layout = QVBoxLayout(self)
        
        title = QLabel("Save Current Session Data")
        title.setStyleSheet("font-size: 14px; font-weight: bold; color: #FFA500;")
        layout.addWidget(title)
        
        layout.addSpacing(10)
        
        track_label = QLabel(f"Track: {self.track_name}")
        track_label.setStyleSheet("font-size: 12px; font-weight: bold;")
        layout.addWidget(track_label)
        
        layout.addSpacing(10)
        
        # Car class input
        car_class_layout = QHBoxLayout()
        car_class_layout.addWidget(QLabel("Car Class (your vehicle):"))
        self.car_class_input = QLineEdit()
        self.car_class_input.setPlaceholderText("e.g., Formula Senior, GT1, GT2, etc.")
        self.car_class_input.setText(self.vehicles.get('user', ''))
        car_class_layout.addWidget(self.car_class_input)
        layout.addLayout(car_class_layout)
        
        layout.addSpacing(15)
        
        # Vehicles information
        vehicles_group = QGroupBox("Vehicle Information")
        vehicles_layout = QGridLayout(vehicles_group)
        
        vehicles_layout.addWidget(QLabel("Your Vehicle:"), 0, 0)
        user_vehicle = QLabel(self.vehicles.get('user', 'Unknown'))
        user_vehicle.setStyleSheet("color: #4CAF50; font-weight: bold;")
        vehicles_layout.addWidget(user_vehicle, 0, 1)
        
        vehicles_layout.addWidget(QLabel("Qualifying Best AI:"), 1, 0)
        qual_best_vehicle = QLabel(self.vehicles.get('qual_best', 'Unknown'))
        vehicles_layout.addWidget(qual_best_vehicle, 1, 1)
        
        vehicles_layout.addWidget(QLabel("Qualifying Worst AI:"), 2, 0)
        qual_worst_vehicle = QLabel(self.vehicles.get('qual_worst', 'Unknown'))
        vehicles_layout.addWidget(qual_worst_vehicle, 2, 1)
        
        vehicles_layout.addWidget(QLabel("Race Best AI:"), 3, 0)
        race_best_vehicle = QLabel(self.vehicles.get('race_best', 'Unknown'))
        vehicles_layout.addWidget(race_best_vehicle, 3, 1)
        
        vehicles_layout.addWidget(QLabel("Race Worst AI:"), 4, 0)
        race_worst_vehicle = QLabel(self.vehicles.get('race_worst', 'Unknown'))
        vehicles_layout.addWidget(race_worst_vehicle, 4, 1)
        
        layout.addWidget(vehicles_group)
        
        layout.addSpacing(15)
        
        # Data preview
        data_group = QGroupBox("Data to Save")
        data_layout = QGridLayout(data_group)
        
        row = 0
        data_layout.addWidget(QLabel("Qualifying Ratio:"), row, 0)
        data_layout.addWidget(QLabel(f"{self.current_ratios.get('QualRatio', 1.0):.6f}"), row, 1)
        
        row += 1
        data_layout.addWidget(QLabel("Qual AI Best (seconds):"), row, 0)
        data_layout.addWidget(QLabel(f"{self.ai_times.get('qual_best_sec', 0):.3f}"), row, 1)
        
        row += 1
        data_layout.addWidget(QLabel("Qual AI Worst (seconds):"), row, 0)
        data_layout.addWidget(QLabel(f"{self.ai_times.get('qual_worst_sec', 0):.3f}"), row, 1)
        
        row += 1
        data_layout.addWidget(QLabel("Qual User Time (seconds):"), row, 0)
        data_layout.addWidget(QLabel(f"{self.user_times.get('qual', 0):.3f}"), row, 1)
        
        row += 2
        data_layout.addWidget(QLabel("Race Ratio:"), row, 0)
        data_layout.addWidget(QLabel(f"{self.current_ratios.get('RaceRatio', 1.0):.6f}"), row, 1)
        
        row += 1
        data_layout.addWidget(QLabel("Race AI Best (seconds):"), row, 0)
        data_layout.addWidget(QLabel(f"{self.ai_times.get('race_best_sec', 0):.3f}"), row, 1)
        
        row += 1
        data_layout.addWidget(QLabel("Race AI Worst (seconds):"), row, 0)
        data_layout.addWidget(QLabel(f"{self.ai_times.get('race_worst_sec', 0):.3f}"), row, 1)
        
        row += 1
        data_layout.addWidget(QLabel("Race User Best (seconds):"), row, 0)
        data_layout.addWidget(QLabel(f"{self.user_times.get('race', 0):.3f}"), row, 1)
        
        layout.addWidget(data_group)
        
        layout.addSpacing(20)
        
        btn_layout = QHBoxLayout()
        
        save_btn = QPushButton("Save to CSV")
        save_btn.setFixedHeight(40)
        save_btn.clicked.connect(self.accept)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setFixedHeight(40)
        cancel_btn.setStyleSheet("background-color: #f44336;")
        cancel_btn.clicked.connect(self.reject)
        
        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)
    
    def get_data(self) -> Dict:
        """Get the data to save"""
        self.car_class = self.car_class_input.text().strip()
        return {
            'car_class': self.car_class if self.car_class else self.vehicles.get('user', 'Unknown'),
            'qual_ratio': self.current_ratios.get('QualRatio', 1.0),
            'qual_best': self.ai_times.get('qual_best_sec', 0.0),
            'qual_worst': self.ai_times.get('qual_worst_sec', 0.0),
            'qual_user': self.user_times.get('qual', 0.0),
            'race_ratio': self.current_ratios.get('RaceRatio', 1.0),
            'race_best': self.ai_times.get('race_best_sec', 0.0),
            'race_worst': self.ai_times.get('race_worst_sec', 0.0),
            'race_user': self.user_times.get('race', 0.0),
            'user_vehicle': self.car_class if self.car_class else self.vehicles.get('user', 'Unknown'),
            'qual_best_vehicle': self.vehicles.get('qual_best', 'Unknown'),
            'qual_worst_vehicle': self.vehicles.get('qual_worst', 'Unknown'),
            'race_best_vehicle': self.vehicles.get('race_best', 'Unknown'),
            'race_worst_vehicle': self.vehicles.get('race_worst', 'Unknown')
        }


class ConfirmApplyDialog(QDialog):
    """Dialog to confirm applying new ratio(s)"""
    
    def __init__(self, track_name: str, changes: Dict[str, Dict], parent=None):
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
        
        title = QLabel("Apply Ratio Changes?")
        title.setStyleSheet("font-size: 14px; font-weight: bold; color: #FFA500;")
        layout.addWidget(title)
        
        layout.addSpacing(10)
        
        track_label = QLabel(f"Track: {self.track_name}")
        track_label.setStyleSheet("font-size: 12px;")
        layout.addWidget(track_label)
        
        layout.addSpacing(15)
        
        changes_group = QGroupBox("Changes to Apply")
        changes_layout = QVBoxLayout(changes_group)
        
        for ratio_type, data in self.changes.items():
            display_name = "Qualifying" if ratio_type == "QualRatio" else "Race"
            current = data['current']
            new = data['new']
            diff = new - current
            
            frame = QFrame()
            frame.setStyleSheet("""
                QFrame {
                    background-color: #3c3c3c;
                    border-radius: 4px;
                    padding: 5px;
                }
            """)
            frame_layout = QHBoxLayout(frame)
            
            name_label = QLabel(f"{display_name}:")
            name_label.setStyleSheet("font-weight: bold; min-width: 80px;")
            frame_layout.addWidget(name_label)
            
            current_label = QLabel(f"{current:.6f}")
            current_label.setStyleSheet("color: #f44336;")
            frame_layout.addWidget(current_label)
            
            arrow_label = QLabel("->")
            arrow_label.setStyleSheet("color: #888;")
            frame_layout.addWidget(arrow_label)
            
            new_label = QLabel(f"{new:.6f}")
            new_label.setStyleSheet("color: #4CAF50; font-weight: bold;")
            frame_layout.addWidget(new_label)
            
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


class MainWindow(QMainWindow):
    """Main GUI window - UPDATED with compact layout"""
    
    def __init__(self, base_path: Path, monitor_folder: Path, target_file: Path):
        super().__init__()
        self.base_path = base_path
        self.monitor_folder = monitor_folder
        self.target_file = target_file
        
        self.signal = RaceResultsSignal()
        self.signal.results_detected.connect(self._update_race_results)
        
        formulas_dir = get_formulas_dir()
        self.curve_manager = GlobalCurveManager(formulas_dir)
        
        if self.curve_manager.load():
            stats = self.curve_manager.get_stats()
            logger.info(f"Loaded existing curve: {stats['total_points']} points, {stats['total_tracks']} tracks")
        
        self.load_historic_data_into_curve()
        
        self.aiw_manager = AIWManager(base_path / 'backups')
        
        self.last_results = None
        self.pending_changes = {}
        self.has_ai_data = False
        self.current_vehicles = {}
        
        self.setup_ui()
        self.update_status()
        self.update_backup_info()
        
        # Load autopilot setting from config
        self.autopilot_enabled = get_autopilot_enabled()
        self.update_autopilot_button()
        
        # Initially disable save button
        self.save_to_csv_btn.setEnabled(False)
    
    def check_curve_exists(self) -> bool:
        """Check if there's enough curve data for reliable predictions"""
        stats = self.curve_manager.get_stats()
        return stats['total_points'] >= 2 or len(stats['track_params']) > 0
    
    def time_to_seconds(self, time_str: str) -> float:
        """Convert time string to seconds"""
        if not time_str or time_str == 'N/A' or time_str == '0':
            return 0.0
        
        try:
            if ':' in str(time_str):
                parts = str(time_str).split(':')
                minutes = int(parts[0])
                seconds = float(parts[1])
                return minutes * 60 + seconds
            else:
                return float(time_str)
        except (ValueError, IndexError):
            return 0.0
    
    def load_historic_data_into_curve(self):
        """Load all historic data into the curve manager"""
        csv_path = Path("./historic.csv")
        if not csv_path.exists():
            return
        
        try:
            loaded_points = 0
            with open(csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f, delimiter=';')
                for row in reader:
                    track_name = row.get('Track Name', '')
                    car_class = row.get('Car', '')
                    
                    if not track_name:
                        continue
                    
                    # Add qualifying data point
                    try:
                        qual_ratio = float(row.get('Current QualRatio', '0'))
                        qual_best = float(row.get('Qual AI Best (s)', '0'))
                        qual_worst = float(row.get('Qual AI Worst (s)', '0'))
                        if qual_ratio > 0 and qual_best > 0 and qual_worst > 0:
                            midpoint = (qual_best + qual_worst) / 2
                            full_track_name = f"{track_name} [{car_class}]" if car_class and car_class != "Unknown" else track_name
                            self.curve_manager.add_point(full_track_name, qual_ratio, midpoint)
                            loaded_points += 1
                    except (ValueError, KeyError):
                        pass
                    
                    # Add race data point
                    try:
                        race_ratio = float(row.get('Current RaceRatio', '0'))
                        race_best = float(row.get('Race AI Best (s)', '0'))
                        race_worst = float(row.get('Race AI Worst (s)', '0'))
                        if race_ratio > 0 and race_best > 0 and race_worst > 0:
                            midpoint = (race_best + race_worst) / 2
                            full_track_name = f"{track_name} [{car_class}]" if car_class and car_class != "Unknown" else track_name
                            self.curve_manager.add_point(full_track_name, race_ratio, midpoint)
                            loaded_points += 1
                    except (ValueError, KeyError):
                        pass
            
            if loaded_points > 0:
                logger.info(f"Loaded {loaded_points} points from historic.csv")
                self.curve_manager.save()
                
        except Exception as e:
            logger.error(f"Error loading historic.csv: {e}")
    
    def setup_ui(self):
        """Setup the main UI with compact layout"""
        self.setWindowTitle("dyn_ai")
        self.setGeometry(100, 100, 950, 750)
        
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
                background-color: #555;
                color: #888;
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
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(15, 15, 15, 15)
        
        # Header with track display
        self.track_display = QLabel("No Track Selected")
        self.track_display.setAlignment(Qt.AlignCenter)
        self.track_display.setStyleSheet("""
            font-size: 22px;
            font-weight: bold;
            color: #FFA500;
            background-color: #2b2b2b;
            border-radius: 6px;
            padding: 10px;
            margin: 2px;
        """)
        main_layout.addWidget(self.track_display)
        
        # Status bar (compact)
        status_layout = QHBoxLayout()
        self.status_indicator = QLabel("● ACTIVE")
        self.status_indicator.setStyleSheet("color: #4CAF50; font-size: 10px; font-weight: bold;")
        status_layout.addWidget(self.status_indicator)
        
        self.monitor_path_label = QLabel(f"Monitoring: {self.target_file.name}")
        self.monitor_path_label.setStyleSheet("color: #888; font-size: 9px;")
        status_layout.addWidget(self.monitor_path_label)
        
        status_layout.addStretch()
        main_layout.addLayout(status_layout)
        
        # Current AIW Ratios - compact horizontal layout
        ratios_group = QGroupBox("Current AIW Ratios")
        ratios_layout = QHBoxLayout(ratios_group)
        ratios_layout.setSpacing(20)
        
        # Qualifying - horizontal
        quali_frame = QFrame()
        quali_frame.setStyleSheet("background-color: #2b2b2b; border-radius: 4px; padding: 5px;")
        quali_layout = QHBoxLayout(quali_frame)
        quali_layout.setContentsMargins(10, 5, 10, 5)
        quali_layout.addWidget(QLabel("Qualifying:"))
        self.current_qual_label = QLabel("---")
        self.current_qual_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #9C27B0;")
        quali_layout.addWidget(self.current_qual_label)
        ratios_layout.addWidget(quali_frame)
        
        # Race - horizontal
        race_frame = QFrame()
        race_frame.setStyleSheet("background-color: #2b2b2b; border-radius: 4px; padding: 5px;")
        race_layout = QHBoxLayout(race_frame)
        race_layout.setContentsMargins(10, 5, 10, 5)
        race_layout.addWidget(QLabel("Race:"))
        self.current_race_label = QLabel("---")
        self.current_race_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #9C27B0;")
        race_layout.addWidget(self.current_race_label)
        ratios_layout.addWidget(race_frame)
        
        ratios_layout.addStretch()
        main_layout.addWidget(ratios_group)
        
        # AI Lap Times Group
        ai_times_group = QGroupBox("AI Lap Times")
        ai_times_layout = QGridLayout(ai_times_group)
        ai_times_layout.setSpacing(8)
        
        # Qualifying section
        ai_times_layout.addWidget(QLabel("QUALIFYING:"), 0, 0, 1, 4)
        ai_times_layout.addWidget(QLabel("Best AI Lap:"), 1, 0)
        self.qual_best_ai_label = QLabel("---")
        self.qual_best_ai_label.setStyleSheet("color: #4CAF50; font-weight: bold;")
        ai_times_layout.addWidget(self.qual_best_ai_label, 1, 1)
        
        ai_times_layout.addWidget(QLabel("Vehicle:"), 1, 2)
        self.qual_best_vehicle_label = QLabel("---")
        self.qual_best_vehicle_label.setStyleSheet("color: #888; font-style: italic; font-size: 10px;")
        ai_times_layout.addWidget(self.qual_best_vehicle_label, 1, 3)
        
        ai_times_layout.addWidget(QLabel("Worst AI Lap:"), 2, 0)
        self.qual_worst_ai_label = QLabel("---")
        self.qual_worst_ai_label.setStyleSheet("color: #f44336; font-weight: bold;")
        ai_times_layout.addWidget(self.qual_worst_ai_label, 2, 1)
        
        ai_times_layout.addWidget(QLabel("Vehicle:"), 2, 2)
        self.qual_worst_vehicle_label = QLabel("---")
        self.qual_worst_vehicle_label.setStyleSheet("color: #888; font-style: italic; font-size: 10px;")
        ai_times_layout.addWidget(self.qual_worst_vehicle_label, 2, 3)
        
        # Separator line
        sep_line = QFrame()
        sep_line.setFrameShape(QFrame.HLine)
        sep_line.setStyleSheet("background-color: #555;")
        ai_times_layout.addWidget(sep_line, 3, 0, 1, 4)
        
        # Race section
        ai_times_layout.addWidget(QLabel("RACE:"), 4, 0, 1, 4)
        ai_times_layout.addWidget(QLabel("Best AI Lap:"), 5, 0)
        self.race_best_ai_label = QLabel("---")
        self.race_best_ai_label.setStyleSheet("color: #4CAF50; font-weight: bold;")
        ai_times_layout.addWidget(self.race_best_ai_label, 5, 1)
        
        ai_times_layout.addWidget(QLabel("Vehicle:"), 5, 2)
        self.race_best_vehicle_label = QLabel("---")
        self.race_best_vehicle_label.setStyleSheet("color: #888; font-style: italic; font-size: 10px;")
        ai_times_layout.addWidget(self.race_best_vehicle_label, 5, 3)
        
        ai_times_layout.addWidget(QLabel("Worst AI Lap:"), 6, 0)
        self.race_worst_ai_label = QLabel("---")
        self.race_worst_ai_label.setStyleSheet("color: #f44336; font-weight: bold;")
        ai_times_layout.addWidget(self.race_worst_ai_label, 6, 1)
        
        ai_times_layout.addWidget(QLabel("Vehicle:"), 6, 2)
        self.race_worst_vehicle_label = QLabel("---")
        self.race_worst_vehicle_label.setStyleSheet("color: #888; font-style: italic; font-size: 10px;")
        ai_times_layout.addWidget(self.race_worst_vehicle_label, 6, 3)
        
        main_layout.addWidget(ai_times_group)
        
        # User info group (compact)
        user_group = QGroupBox("Your Information")
        user_layout = QHBoxLayout(user_group)
        user_layout.setSpacing(20)
        
        user_layout.addWidget(QLabel("Name:"))
        self.user_name_label = QLabel("---")
        self.user_name_label.setStyleSheet("color: #4CAF50; font-weight: bold;")
        user_layout.addWidget(self.user_name_label)
        
        user_layout.addWidget(QLabel("Vehicle:"))
        self.user_vehicle_label = QLabel("---")
        self.user_vehicle_label.setStyleSheet("color: #4CAF50; font-weight: bold;")
        user_layout.addWidget(self.user_vehicle_label)
        
        user_layout.addStretch()
        main_layout.addWidget(user_group)
        
        # Your Lap Times input
        input_group = QGroupBox("Your Lap Times")
        input_layout = QGridLayout(input_group)
        input_layout.setSpacing(8)
        
        input_layout.addWidget(QLabel("Qualifying:"), 0, 0)
        self.qual_time_input = QLineEdit()
        self.qual_time_input.setPlaceholderText("e.g., 1:55.364")
        input_layout.addWidget(self.qual_time_input, 0, 1)
        
        self.qual_calc_btn = QPushButton("Calculate")
        self.qual_calc_btn.setFixedWidth(80)
        self.qual_calc_btn.clicked.connect(lambda: self.calculate_ratio("QualRatio"))
        input_layout.addWidget(self.qual_calc_btn, 0, 2)
        
        input_layout.addWidget(QLabel("→"), 0, 3)
        self.qual_result_label = QLabel("---")
        self.qual_result_label.setStyleSheet("color: #9C27B0; font-weight: bold;")
        input_layout.addWidget(self.qual_result_label, 0, 4)
        
        input_layout.addWidget(QLabel("Race:"), 1, 0)
        self.race_time_input = QLineEdit()
        self.race_time_input.setPlaceholderText("e.g., 1:55.364")
        input_layout.addWidget(self.race_time_input, 1, 1)
        
        self.race_calc_btn = QPushButton("Calculate")
        self.race_calc_btn.setFixedWidth(80)
        self.race_calc_btn.clicked.connect(lambda: self.calculate_ratio("RaceRatio"))
        input_layout.addWidget(self.race_calc_btn, 1, 2)
        
        input_layout.addWidget(QLabel("→"), 1, 3)
        self.race_result_label = QLabel("---")
        self.race_result_label.setStyleSheet("color: #9C27B0; font-weight: bold;")
        input_layout.addWidget(self.race_result_label, 1, 4)
        
        main_layout.addWidget(input_group)
        
        # Apply Changes group
        apply_group = QGroupBox("Apply Changes")
        apply_layout = QVBoxLayout(apply_group)
        
        selection_layout = QHBoxLayout()
        self.apply_qual_check = QCheckBox("Apply Qualifying Ratio")
        self.apply_qual_check.setChecked(False)
        selection_layout.addWidget(self.apply_qual_check)
        
        self.apply_race_check = QCheckBox("Apply Race Ratio")
        self.apply_race_check.setChecked(False)
        selection_layout.addWidget(self.apply_race_check)
        
        selection_layout.addStretch()
        apply_layout.addLayout(selection_layout)
        
        # Button row
        button_row = QHBoxLayout()
        
        self.apply_all_btn = QPushButton("Apply Selected Changes")
        self.apply_all_btn.setFixedHeight(40)
        self.apply_all_btn.setStyleSheet("background-color: #9C27B0;")
        self.apply_all_btn.setEnabled(False)
        self.apply_all_btn.clicked.connect(self.apply_selected_changes)
        button_row.addWidget(self.apply_all_btn)
        
        self.save_to_csv_btn = QPushButton("Save to CSV")
        self.save_to_csv_btn.setFixedHeight(40)
        self.save_to_csv_btn.setStyleSheet("background-color: #2196F3;")
        self.save_to_csv_btn.clicked.connect(self.save_to_historic_csv)
        button_row.addWidget(self.save_to_csv_btn)
        
        self.autopilot_btn = QPushButton("Autopilot: OFF")
        self.autopilot_btn.setFixedHeight(40)
        self.autopilot_btn.setStyleSheet("background-color: #f44336;")
        self.autopilot_btn.clicked.connect(self.toggle_autopilot)
        button_row.addWidget(self.autopilot_btn)
        
        apply_layout.addLayout(button_row)
        
        main_layout.addWidget(apply_group)
        
        # Action buttons row
        action_layout = QHBoxLayout()
        
        self.open_editor_btn = QPushButton("Open Curve Editor")
        self.open_editor_btn.setFixedHeight(32)
        self.open_editor_btn.setStyleSheet("background-color: #2196F3;")
        self.open_editor_btn.clicked.connect(self.open_curve_editor)
        action_layout.addWidget(self.open_editor_btn)
        
        self.reset_btn = QPushButton("Reset to Original")
        self.reset_btn.setFixedHeight(32)
        self.reset_btn.setStyleSheet("background-color: #f44336;")
        self.reset_btn.clicked.connect(self.reset_original)
        action_layout.addWidget(self.reset_btn)
        
        action_layout.addStretch()
        main_layout.addLayout(action_layout)
        
        # Compact info labels
        info_layout = QHBoxLayout()
        
        self.curve_info = QLabel("")
        self.curve_info.setStyleSheet("color: #888; font-size: 9px;")
        info_layout.addWidget(self.curve_info)
        
        self.backup_info_label = QLabel("")
        self.backup_info_label.setStyleSheet("color: #888; font-size: 9px;")
        info_layout.addWidget(self.backup_info_label)
        
        info_layout.addStretch()
        main_layout.addLayout(info_layout)
        
        # Log and results at the bottom (compact)
        bottom_tabs = QTabWidget()
        bottom_tabs.setMaximumHeight(180)
        
        # Results tab
        results_widget = QWidget()
        results_layout = QVBoxLayout(results_widget)
        results_layout.setContentsMargins(5, 5, 5, 5)
        self.results_text = QTextEdit()
        self.results_text.setReadOnly(True)
        self.results_text.setMaximumHeight(140)
        self.results_text.setStyleSheet("font-size: 10px;")
        results_layout.addWidget(self.results_text)
        bottom_tabs.addTab(results_widget, "Race Results")
        
        # Log tab
        log_widget = QWidget()
        log_layout = QVBoxLayout(log_widget)
        log_layout.setContentsMargins(5, 5, 5, 5)
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(140)
        self.log_text.setStyleSheet("font-size: 10px;")
        log_layout.addWidget(self.log_text)
        bottom_tabs.addTab(log_widget, "Activity Log")
        
        main_layout.addWidget(bottom_tabs)
    
    def update_autopilot_button(self):
        """Update autopilot button appearance"""
        if self.autopilot_enabled:
            self.autopilot_btn.setText("Autopilot: ON")
            self.autopilot_btn.setStyleSheet("background-color: #4CAF50;")
        else:
            self.autopilot_btn.setText("Autopilot: OFF")
            self.autopilot_btn.setStyleSheet("background-color: #f44336;")
    
    def toggle_autopilot(self):
        """Toggle autopilot mode"""
        if not self.autopilot_enabled:
            if not self.check_curve_exists():
                msg = QMessageBox(self)
                msg.setWindowTitle("Cannot Enable Autopilot")
                msg.setIcon(QMessageBox.Warning)
                msg.setText("No curve data available for predictions")
                msg.setInformativeText(
                    "Autopilot requires at least 2 data points or one fitted track to make reliable predictions.\n\n"
                    "Please complete at least 2 races (with different ratio settings) or use the Global Curve Editor to create a curve first."
                )
                msg.setStandardButtons(QMessageBox.Ok)
                msg.exec_()
                
                self.log_message("Cannot enable autopilot: No curve data available", "warning")
                return
        
        self.autopilot_enabled = not self.autopilot_enabled
        self.update_autopilot_button()
        
        if self.autopilot_enabled:
            self.log_message("Autopilot enabled for this session", "success")
        else:
            self.log_message("Autopilot disabled for this session", "info")
    
    def update_status(self):
        """Update curve info display"""
        stats = self.curve_manager.get_stats()
        
        formula_text = ""
        if self.last_results and self.last_results.get('track_name'):
            track_name = self.last_results.get('track_name')
            formula = self.curve_manager.get_formula_string(track_name)
            formula_text = f" | {formula}"
        
        if stats['total_points'] > 0:
            if stats.get('avg_error', 0) > 0:
                if stats['track_params']:
                    text = f"Hyperbolic | k={stats['global_k']:.3f} | {stats['total_points']}pts/{stats['total_tracks']}tracks | error={stats['avg_error']:.1f}s{formula_text}"
                    color = "#4CAF50"
                else:
                    text = f"Collecting: {stats['total_points']}pts/{stats['total_tracks']}tracks | need 2pts/track{formula_text}"
                    color = "#FFA500"
            else:
                text = f"Bootstrap: {stats['total_points']}pts/{stats['total_tracks']}tracks | add 2nd point{formula_text}"
                color = "#FFA500"
        else:
            text = "No data yet. Complete a race to start building the model."
            color = "#f44336"
        
        self.curve_info.setText(text)
        self.curve_info.setStyleSheet(f"color: {color}; font-size: 9px;")
        
        if hasattr(self, 'status_indicator'):
            if stats['total_points'] >= 2:
                self.status_indicator.setText(f"● ACTIVE ({stats['total_points']} pts)")
            else:
                self.status_indicator.setText(f"● WAITING ({stats['total_points']} pt)")
    
    def update_backup_info(self):
        if not self.last_results:
            return
        
        aiw_filename = self.last_results.get('aiw_file')
        track_folder = self.last_results.get('track_folder')
        track_name = self.last_results.get('track_name')
        
        if not aiw_filename or not track_name:
            return
        
        aiw_path = self.aiw_manager.find_aiw_file(aiw_filename, track_folder, self.base_path)
        
        if not aiw_path:
            return
        
        backup_info = self.aiw_manager.get_backup_info(aiw_path, track_name)
        
        if backup_info['original_exists']:
            backup_status = f"Backup: ✓"
            backup_color = "#4CAF50"
        else:
            backup_status = "Backup: ✗ (will be created on first change)"
            backup_color = "#FFA500"
        
        self.backup_info_label.setText(backup_status)
        self.backup_info_label.setStyleSheet(f"color: {backup_color}; font-size: 9px;")
    
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
        
        # Update big track display
        self.track_display.setText(f"🏁 {track} 🏁")
        
        # Get qualifying AI times
        qual_best_ai_sec = data.get('qual_best_ai_lap_sec', 0.0)
        qual_worst_ai_sec = data.get('qual_worst_ai_lap_sec', 0.0)
        
        # Get race AI times
        race_best_ai_sec = data.get('best_ai_lap_sec', 0.0)
        race_worst_ai_sec = data.get('worst_ai_lap_sec', 0.0)
        
        # Get vehicle information
        drivers = data.get('drivers', [])
        
        # Extract vehicles
        user_vehicle = "Unknown"
        qual_best_vehicle = "Unknown"
        qual_worst_vehicle = "Unknown"
        race_best_vehicle = "Unknown"
        race_worst_vehicle = "Unknown"
        
        # Find user vehicle (slot 0)
        user_name = data.get('user_name', 'Unknown')
        self.user_name_label.setText(user_name if user_name != 'Unknown' else '---')
        
        # Parse vehicles from driver data
        for driver in drivers:
            driver_name = driver.get('name', '')
            driver_team = driver.get('team', 'Unknown')
            slot = driver.get('slot', -1)
            
            if slot == 0:
                user_vehicle = driver_team if driver_team != 'Unknown' else 'Unknown'
                self.user_vehicle_label.setText(user_vehicle)
            
            # Match AI vehicles based on lap times
            if driver.get('best_lap') and driver['best_lap'] == data.get('best_ai_lap'):
                race_best_vehicle = driver_team if driver_team != 'Unknown' else 'Unknown'
            if driver.get('best_lap') and driver['best_lap'] == data.get('worst_ai_lap'):
                race_worst_vehicle = driver_team if driver_team != 'Unknown' else 'Unknown'
            if driver.get('qual_time') and driver['qual_time'] == data.get('qual_best_ai_lap'):
                qual_best_vehicle = driver_team if driver_team != 'Unknown' else 'Unknown'
            if driver.get('qual_time') and driver['qual_time'] == data.get('qual_worst_ai_lap'):
                qual_worst_vehicle = driver_team if driver_team != 'Unknown' else 'Unknown'
        
        # Store vehicles for later use
        self.current_vehicles = {
            'user': user_vehicle,
            'qual_best': qual_best_vehicle,
            'qual_worst': qual_worst_vehicle,
            'race_best': race_best_vehicle,
            'race_worst': race_worst_vehicle
        }
        
        # Format times for display
        qual_best_ai = self.format_time(qual_best_ai_sec) if qual_best_ai_sec > 0 else 'N/A'
        qual_worst_ai = self.format_time(qual_worst_ai_sec) if qual_worst_ai_sec > 0 else 'N/A'
        race_best_ai = self.format_time(race_best_ai_sec) if race_best_ai_sec > 0 else 'N/A'
        race_worst_ai = self.format_time(race_worst_ai_sec) if race_worst_ai_sec > 0 else 'N/A'
        
        user_best = data.get('user_best_lap', 'N/A')
        user_qual = data.get('user_qualifying', 'N/A')
        qual_ratio = data.get('qual_ratio')
        race_ratio = data.get('race_ratio')
        
        qual_str = f"{qual_ratio:.6f}" if qual_ratio is not None else 'Not found'
        race_str = f"{race_ratio:.6f}" if race_ratio is not None else 'Not found'
        self.current_qual_label.setText(qual_str)
        self.current_race_label.setText(race_str)
        
        # Update AI times display with vehicles
        self.qual_best_ai_label.setText(qual_best_ai)
        self.qual_worst_ai_label.setText(qual_worst_ai)
        self.race_best_ai_label.setText(race_best_ai)
        self.race_worst_ai_label.setText(race_worst_ai)
        
        self.qual_best_vehicle_label.setText(qual_best_vehicle)
        self.qual_worst_vehicle_label.setText(qual_worst_vehicle)
        self.race_best_vehicle_label.setText(race_best_vehicle)
        self.race_worst_vehicle_label.setText(race_worst_vehicle)
        
        # Check if we have AI data to enable save button
        has_ai_data = (qual_best_ai_sec > 0 or race_best_ai_sec > 0)
        self.has_ai_data = has_ai_data
        self.save_to_csv_btn.setEnabled(has_ai_data)
        
        if has_ai_data:
            self.log_message("AI lap times detected - Save button enabled", "success")
        
        if user_qual and user_qual != 'N/A':
            self.qual_time_input.setText(user_qual)
        if user_best and user_best != 'N/A':
            self.race_time_input.setText(user_best)
        
        # Compact results text
        text = f"""Track: {track}
AIW: {aiw}
Qual: {qual_str} | Race: {race_str}
AI Times: Q {qual_best_ai}/{qual_worst_ai} | R {race_best_ai}/{race_worst_ai}
User: Q {user_qual} | R {user_best}"""
        
        self.results_text.setText(text)
        
        if track:
            points = self.curve_manager.curve.points_by_track.get(track, [])
            if len(points) == 0:
                self.log_message(f"First data point for {track} - will use bootstrap estimation", "info")
            elif len(points) == 1:
                self.log_message(f"Second data point for {track} - next calculation will be exact", "info")
            elif len(points) >= 2:
                self.log_message(f"Track {track} now has {len(points)} points - using exact fit", "success")
        
        self.update_backup_info()
        self.log_message(f"Race results detected for {track}", "success")
        
        # Autopilot check
        if self.autopilot_enabled:
            if self.check_curve_exists():
                self.autopilot_process()
            else:
                self.log_message("Autopilot: Curve data no longer available, disabling autopilot", "error")
                self.autopilot_enabled = False
                self.update_autopilot_button()
    
    def format_time(self, seconds: float) -> str:
        """Format seconds as mm:ss.ms"""
        if seconds <= 0:
            return 'N/A'
        minutes = int(seconds) // 60
        secs = int(seconds) % 60
        ms = int((seconds - int(seconds)) * 1000)
        return f"{minutes}:{secs:02d}.{ms:03d}"
    
    def autopilot_process(self):
        """Process race results automatically in autopilot mode"""
        if not self.last_results:
            return
        
        track_name = self.last_results.get('track_name', 'Unknown')
        
        # Get times in seconds
        qual_best_ai_sec = self.last_results.get('qual_best_ai_lap_sec', 0.0)
        qual_worst_ai_sec = self.last_results.get('qual_worst_ai_lap_sec', 0.0)
        race_best_ai_sec = self.last_results.get('best_ai_lap_sec', 0.0)
        race_worst_ai_sec = self.last_results.get('worst_ai_lap_sec', 0.0)
        
        # Parse user times
        user_qual_str = self.last_results.get('user_qualifying', 'N/A')
        user_race_str = self.last_results.get('user_best_lap', 'N/A')
        
        user_qual_sec = self._parse_time(user_qual_str) if user_qual_str != 'N/A' else 0.0
        user_race_sec = self._parse_time(user_race_str) if user_race_str != 'N/A' else 0.0
        
        # Calculate new ratios
        new_ratios = {}
        current_ratios = {
            'QualRatio': self.last_results.get('qual_ratio', 1.0),
            'RaceRatio': self.last_results.get('race_ratio', 1.0)
        }
        
        if user_qual_sec > 0:
            qual_ratio = self.curve_manager.predict_ratio(user_qual_sec, track_name)
            if qual_ratio:
                new_ratios['QualRatio'] = qual_ratio
        
        if user_race_sec > 0:
            race_ratio = self.curve_manager.predict_ratio(user_race_sec, track_name)
            if race_ratio:
                new_ratios['RaceRatio'] = race_ratio
        
        if not new_ratios:
            self.log_message("Autopilot: No valid user times found to calculate ratios", "warning")
            return
        
        # Get user time string for display
        user_time_str = user_race_str if user_race_sec > 0 else user_qual_str
        ai_time_str = self.format_time(race_best_ai_sec) if race_best_ai_sec > 0 else self.format_time(qual_best_ai_sec)
        
        # Get car class
        car_class = self.current_vehicles.get('user', 'Unknown') if hasattr(self, 'current_vehicles') else 'Unknown'
        
        # Get formula string
        formula = self.curve_manager.get_formula_string(track_name)
        
        # Show confirmation dialog
        confirm_dialog = AutopilotConfirmationDialog(
            track_name=track_name,
            car_class=car_class,
            formula=formula,
            current_ratios=current_ratios,
            new_ratios=new_ratios,
            user_time=user_time_str,
            ai_time=ai_time_str,
            parent=self
        )
        
        if not confirm_dialog.get_decision():
            self.log_message("Autopilot cancelled by user", "warning")
            return
        
        # User confirmed - save to CSV first
        ai_times_sec = {
            'qual_best_sec': qual_best_ai_sec,
            'qual_worst_sec': qual_worst_ai_sec,
            'race_best_sec': race_best_ai_sec,
            'race_worst_sec': race_worst_ai_sec
        }
        
        user_times_sec = {
            'qual': user_qual_sec,
            'race': user_race_sec
        }
        
        # Save to CSV with vehicle data
        self._append_to_historic_csv({
            'car_class': car_class,
            'qual_ratio': current_ratios['QualRatio'],
            'qual_best': ai_times_sec['qual_best_sec'],
            'qual_worst': ai_times_sec['qual_worst_sec'],
            'qual_user': user_times_sec['qual'],
            'race_ratio': current_ratios['RaceRatio'],
            'race_best': ai_times_sec['race_best_sec'],
            'race_worst': ai_times_sec['race_worst_sec'],
            'race_user': user_times_sec['race'],
            'user_vehicle': car_class,
            'qual_best_vehicle': self.current_vehicles.get('qual_best', 'Unknown'),
            'qual_worst_vehicle': self.current_vehicles.get('qual_worst', 'Unknown'),
            'race_best_vehicle': self.current_vehicles.get('race_best', 'Unknown'),
            'race_worst_vehicle': self.current_vehicles.get('race_worst', 'Unknown')
        }, track_name)
        
        # Apply the changes
        self._apply_ratios_autopilot(new_ratios, user_qual_sec, user_race_sec)
    
    def _apply_ratios_autopilot(self, new_ratios: Dict[str, float], user_qual_sec: float, user_race_sec: float):
        """Apply ratios automatically in autopilot mode"""
        if not self.last_results:
            return
        
        track_name = self.last_results.get('track_name')
        track_folder = self.last_results.get('track_folder', track_name)
        aiw_filename = self.last_results.get('aiw_file')
        
        if not aiw_filename:
            self.log_message("Autopilot: Cannot find AIW file name in results", "error")
            return
        
        aiw_path = self.aiw_manager.find_aiw_file(aiw_filename, track_folder, self.base_path)
        
        if not aiw_path or not aiw_path.exists():
            self.log_message(f"Autopilot: AIW file not found: {aiw_filename}", "error")
            return
        
        # Apply each ratio
        success_count = 0
        for ratio_type, new_value in new_ratios.items():
            current_ratio = self.last_results.get(ratio_type.lower() if ratio_type == "QualRatio" else "race_ratio", 1.0)
            
            if self.aiw_manager.update_ratio(aiw_path, ratio_type, new_value, track_name, create_backup=True):
                success_count += 1
                self.log_message(f"Autopilot: Applied {ratio_type}: {current_ratio:.6f} -> {new_value:.6f}", "success")
                
                # Add to curve
                if ratio_type == "QualRatio" and user_qual_sec > 0:
                    self.curve_manager.add_point(track_name, new_value, user_qual_sec)
                    self.log_message(f"Autopilot: Added qualifying data point to global curve", "info")
                elif ratio_type == "RaceRatio" and user_race_sec > 0:
                    self.curve_manager.add_point(track_name, new_value, user_race_sec)
                    self.log_message(f"Autopilot: Added race data point to global curve", "info")
        
        if success_count > 0:
            self.log_message(f"Autopilot: Successfully applied {success_count} change(s)", "success")
            
            # Update displayed ratios
            qual, race = self.aiw_manager.read_ratios(aiw_path)
            if self.last_results:
                self.last_results['qual_ratio'] = qual
                self.last_results['race_ratio'] = race
                self._update_race_results(self.last_results)
            
            self.update_backup_info()
            self.update_status()
    
    def calculate_ratio(self, ratio_type: str):
        """Calculate ratio for a specific type"""
        if not self.last_results:
            self.log_message("No race results available. Waiting for race data...", "warning")
            return
        
        track_name = self.last_results.get('track_name')
        if not track_name:
            self.log_message("No track name found in results", "error")
            return
        
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
        
        user_time = self._parse_time(user_time_str)
        if user_time is None or user_time <= 0:
            self.log_message(f"Invalid time format: {user_time_str}. Use format like '1:55.364'", "error")
            return
        
        ratio = self.curve_manager.predict_ratio(user_time, track_name)
        
        if ratio is None:
            stats = self.curve_manager.get_stats()
            points_for_track = self.curve_manager.curve.points_by_track.get(track_name, [])
            
            if len(points_for_track) == 0:
                self.log_message(f"No data for {track_name} yet. Complete a race to get first data point.", "warning")
            elif len(points_for_track) == 1:
                self.log_message(f"Only 1 data point for {track_name}. Complete another race at a different ratio to get exact fit.", "warning")
                ratio = self.curve_manager.curve._bootstrap_one_point(user_time, track_name, points_for_track[0])
                if ratio:
                    self.log_message(f"Using bootstrap estimation (error may be +-2-5 seconds)", "info")
                else:
                    self.log_message(f"Could not calculate ratio. Time may be outside valid range.", "error")
                    result_label.setText("Error")
                    return
            else:
                self.log_message(f"Could not calculate ratio. Time may be outside valid range.", "error")
                result_label.setText("Out of range")
                return
        
        if ratio is None:
            return
        
        if ratio_type == "QualRatio":
            current_ratio = self.last_results.get('qual_ratio', 1.0)
        else:
            current_ratio = self.last_results.get('race_ratio', 1.0)
        
        self.pending_changes[ratio_type] = {
            'current': current_ratio,
            'new': ratio,
            'user_time': user_time
        }
        
        result_label.setText(f"{ratio:.6f}")
        
        if ratio_type == "QualRatio":
            self.apply_qual_check.setChecked(True)
        else:
            self.apply_race_check.setChecked(True)
        
        self.apply_all_btn.setEnabled(True)
        
        points_count = len(self.curve_manager.curve.points_by_track.get(track_name, []))
        if points_count == 1:
            self.log_message(f"Calculated {ratio_type}: {ratio:.6f} (bootstrap estimate, +-~2-5s error)", "success")
        elif points_count == 2:
            self.log_message(f"Calculated {ratio_type}: {ratio:.6f} (exact fit, <1s error)", "success")
        else:
            self.log_message(f"Calculated {ratio_type}: {ratio:.6f} (least squares fit, <0.3s error)", "success")
    
    def apply_selected_changes(self):
        """Apply only the selected ratio changes"""
        if not self.last_results:
            return
        
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
        
        confirm = ConfirmApplyDialog(track_name, changes_to_apply, self)
        if not confirm.get_decision():
            self.log_message("Changes cancelled by user", "warning")
            return
        
        aiw_filename = self.last_results.get('aiw_file')
        if not aiw_filename:
            self.log_message("Cannot find AIW file name in results", "error")
            return
        
        aiw_path = self.aiw_manager.find_aiw_file(aiw_filename, track_folder, self.base_path)
        
        if not aiw_path or not aiw_path.exists():
            self.log_message(f"AIW file not found: {aiw_filename}", "error")
            return
        
        success_count = 0
        for ratio_type, change in changes_to_apply.items():
            if self.aiw_manager.update_ratio(aiw_path, ratio_type, change['new'], track_name, create_backup=True):
                success_count += 1
                self.log_message(f"Applied {ratio_type}: {change['current']:.6f} -> {change['new']:.6f}", "success")
                
                if change.get('user_time'):
                    self.curve_manager.add_point(track_name, change['new'], change['user_time'])
                    self.log_message(f"Added data point to global curve", "info")
        
        if success_count > 0:
            self.log_message(f"Successfully applied {success_count} change(s)", "success")
            
            qual, race = self.aiw_manager.read_ratios(aiw_path)
            if self.last_results:
                self.last_results['qual_ratio'] = qual
                self.last_results['race_ratio'] = race
                self._update_race_results(self.last_results)
            
            self.update_backup_info()
            self.update_status()
            
            for ratio_type in changes_to_apply:
                if ratio_type in self.pending_changes:
                    del self.pending_changes[ratio_type]
            
            if not self.pending_changes:
                self.qual_result_label.setText("---")
                self.race_result_label.setText("---")
                self.apply_qual_check.setChecked(False)
                self.apply_race_check.setChecked(False)
                self.apply_all_btn.setEnabled(False)
        else:
            self.log_message("Failed to apply changes", "error")
    
    def save_to_historic_csv(self):
        """Save current data to historic.csv with car class and vehicle info"""
        if not self.last_results:
            self.log_message("No race results available to save", "warning")
            return
        
        # Check if we have AI data
        if not self.has_ai_data:
            self.log_message("No AI lap times available to save", "warning")
            return
        
        track_name = self.last_results.get('track_name', 'Unknown')
        
        # Prepare current ratios
        current_ratios = {
            'QualRatio': self.last_results.get('qual_ratio', 1.0),
            'RaceRatio': self.last_results.get('race_ratio', 1.0)
        }
        
        # Prepare AI times (in seconds)
        ai_times = {
            'qual_best_sec': self.last_results.get('qual_best_ai_lap_sec', 0.0),
            'qual_worst_sec': self.last_results.get('qual_worst_ai_lap_sec', 0.0),
            'race_best_sec': self.last_results.get('best_ai_lap_sec', 0.0),
            'race_worst_sec': self.last_results.get('worst_ai_lap_sec', 0.0)
        }
        
        # Prepare user times
        user_qual_sec = self._parse_time(self.last_results.get('user_qualifying', '0'))
        user_race_sec = self._parse_time(self.last_results.get('user_best_lap', '0'))
        
        user_times = {
            'qual': user_qual_sec if user_qual_sec else 0.0,
            'race': user_race_sec if user_race_sec else 0.0
        }
        
        # Get vehicles
        vehicles = getattr(self, 'current_vehicles', {
            'user': 'Unknown',
            'qual_best': 'Unknown',
            'qual_worst': 'Unknown',
            'race_best': 'Unknown',
            'race_worst': 'Unknown'
        })
        
        # Show dialog
        dialog = SaveToHistoricDialog(track_name, current_ratios, ai_times, user_times, vehicles, self)
        
        if dialog.exec_() == QDialog.Accepted:
            data = dialog.get_data()
            self._append_to_historic_csv(data, track_name)
    
    def _append_to_historic_csv(self, data: Dict, track_name: str):
        """Append data to historic.csv with vehicle information"""
        csv_path = Path("./historic.csv")
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        file_exists = csv_path.exists()
        
        try:
            with open(csv_path, 'a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f, delimiter=';')
                
                if not file_exists:
                    writer.writerow([
                        'Car', 'Timestamp', 'Track Name',
                        'Current QualRatio', 'Qual AI Best (s)', 'Qual AI Worst (s)', 'Qual User (s)',
                        'Current RaceRatio', 'Race AI Best (s)', 'Race AI Worst (s)', 'Race User (s)',
                        'User Vehicle', 'Qual Best AI Vehicle', 'Qual Worst AI Vehicle',
                        'Race Best AI Vehicle', 'Race Worst AI Vehicle'
                    ])
                
                writer.writerow([
                    data['car_class'],
                    timestamp,
                    track_name,
                    f"{data['qual_ratio']:.6f}",
                    f"{data['qual_best']:.3f}",
                    f"{data['qual_worst']:.3f}",
                    f"{data['qual_user']:.3f}",
                    f"{data['race_ratio']:.6f}",
                    f"{data['race_best']:.3f}",
                    f"{data['race_worst']:.3f}",
                    f"{data['race_user']:.3f}",
                    data.get('user_vehicle', data['car_class']),
                    data.get('qual_best_vehicle', 'Unknown'),
                    data.get('qual_worst_vehicle', 'Unknown'),
                    data.get('race_best_vehicle', 'Unknown'),
                    data.get('race_worst_vehicle', 'Unknown')
                ])
            
            self.log_message(f"Saved data to historic.csv (Car: {data['car_class']})", "success")
            self.load_historic_data_into_curve()
            
        except Exception as e:
            self.log_message(f"Error saving to historic.csv: {e}", "error")
    
    def _parse_time(self, time_str: str) -> float:
        """Parse time string to seconds"""
        if not time_str or time_str == 'N/A' or time_str == '0':
            return 0.0
        
        try:
            if ':' in str(time_str):
                parts = str(time_str).split(':')
                minutes = int(parts[0])
                seconds = float(parts[1])
                return minutes * 60 + seconds
            else:
                return float(time_str)
        except (ValueError, IndexError):
            return 0.0
    
    def reset_original(self):
        """Reset to original values from backup"""
        if not self.last_results:
            return
        
        track_name = self.last_results.get('track_name')
        track_folder = self.last_results.get('track_folder', track_name)
        aiw_filename = self.last_results.get('aiw_file')
        
        if not aiw_filename or not track_name:
            return
        
        aiw_path = self.aiw_manager.find_aiw_file(aiw_filename, track_folder, self.base_path)
        
        if not aiw_path:
            self.log_message("AIW file not found", "error")
            return
        
        if not self.aiw_manager.has_original_backup(aiw_path, track_name):
            self.log_message("No original backup found. Cannot restore.", "warning")
            return
        
        reply = QMessageBox.question(self, "Confirm Restore", 
                                    f"Restore original AIW file for {track_name}?\n\n"
                                    f"This will discard all changes made to this file.",
                                    QMessageBox.Yes | QMessageBox.No)
        
        if reply != QMessageBox.Yes:
            return
        
        if self.aiw_manager.restore_original(aiw_path, track_name):
            self.log_message(f"Restored original AIW file for {track_name}", "success")
            
            qual, race = self.aiw_manager.read_ratios(aiw_path)
            if self.last_results:
                self.last_results['qual_ratio'] = qual
                self.last_results['race_ratio'] = race
                self._update_race_results(self.last_results)
            
            self.update_backup_info()
            
            self.pending_changes.clear()
            self.qual_result_label.setText("---")
            self.race_result_label.setText("---")
            self.apply_qual_check.setChecked(False)
            self.apply_race_check.setChecked(False)
            self.apply_all_btn.setEnabled(False)
        else:
            self.log_message("Failed to restore original backup", "error")
    
    def open_curve_editor(self):
        """Open the global curve builder dialog"""
        try:
            from global_curve_builder import GlobalCurveBuilderDialog
            
            dialog = GlobalCurveBuilderDialog(
                parent=self,
                formulas_dir=get_formulas_dir(),
                curve_manager=self.curve_manager
            )
            
            result = dialog.exec_()
            
            if result == QDialog.Accepted:
                self.curve_manager.load()
                self.update_status()
                self.update_backup_info()
                
                if self.last_results:
                    self._update_race_results(self.last_results)
                
                self.log_message("Global curve updated from editor", "success")
                
        except ImportError as e:
            self.log_message(f"Could not open curve editor: {e}", "error")
        except Exception as e:
            self.log_message(f"Error opening curve editor: {e}", "error")
    
    def run(self):
        self.show()
    
    def quit(self):
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
