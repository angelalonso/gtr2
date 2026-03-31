"""
GUI for Live AI Tuner - Main window and dialogs
UPDATED: Enhanced autopilot with track change detection, better readiness assessment
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

from cfg_manage import get_formulas_dir, get_autopilot_enabled, update_autopilot_enabled
from global_curve import GlobalCurveManager
from aiw_manager import AIWManager

logger = logging.getLogger(__name__)


class RaceResultsSignal(QObject):
    """Signal for thread-safe GUI updates"""
    results_detected = pyqtSignal(dict)


class AutopilotConfirmationDialog(QDialog):
    """Dialog to confirm autopilot action - UPDATED with fit quality and outlier info"""

    def __init__(self, track_name: str, car_class: str, formula: str,
                 current_ratios: Dict[str, float], new_ratios: Dict[str, float],
                 user_time: str, ai_time: str,
                 fit_info: Dict = None, outliers: List[Dict] = None,
                 parent=None):
        super().__init__(parent)
        self.track_name = track_name
        self.car_class = car_class
        self.formula = formula
        self.current_ratios = current_ratios
        self.new_ratios = new_ratios
        self.user_time = user_time
        self.ai_time = ai_time
        self.fit_info = fit_info or {}
        self.outliers = outliers or []
        self.setup_ui()

    def setup_ui(self):
        self.setWindowTitle(f"Autopilot Confirmation - {self.track_name}")
        self.setModal(True)
        self.setMinimumWidth(650)

        self.setStyleSheet("""
            QDialog { background-color: #2b2b2b; }
            QLabel { color: white; }
            QGroupBox {
                color: #4CAF50; border: 2px solid #555; border-radius: 5px;
                margin-top: 8px; padding-top: 8px;
            }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px 0 5px; }
            QPushButton {
                background-color: #4CAF50; color: white; border: none;
                border-radius: 3px; padding: 8px; font-weight: bold;
            }
            QPushButton:hover { background-color: #45a049; }
            QPushButton#cancel { background-color: #f44336; }
            QPushButton#cancel:hover { background-color: #d32f2f; }
        """)

        layout = QVBoxLayout(self)

        # Header
        header = QLabel(f"🚗 Autopilot: {self.track_name}")
        header.setStyleSheet("font-size: 16px; font-weight: bold; color: #FFA500; padding: 10px;")
        header.setAlignment(Qt.AlignCenter)
        layout.addWidget(header)

        layout.addSpacing(6)

        # Vehicle info
        if self.car_class and self.car_class != "Unknown":
            vehicle_group = QGroupBox("Vehicle")
            vehicle_layout = QVBoxLayout(vehicle_group)
            vehicle_label = QLabel(f"Car Class: {self.car_class}")
            vehicle_label.setStyleSheet("font-size: 12px; font-weight: bold; color: #4CAF50;")
            vehicle_layout.addWidget(vehicle_label)
            layout.addWidget(vehicle_group)
            layout.addSpacing(6)

        # ── Curve quality ──────────────────────────────────────────────
        quality_group = QGroupBox("Curve Quality")
        quality_layout = QGridLayout(quality_group)

        mode_map = {
            'least_squares':    ("Least-squares fit",    "#4CAF50"),
            'exact_2pt':        ("Exact 2-point fit",    "#4CAF50"),
            'bootstrap_1pt':    ("1-point bootstrap",    "#FFA500"),
            'bootstrap_global': ("Global bootstrap",     "#FFA500"),
            'bootstrap_fallback':("Bootstrap (fallback)","#FFA500"),
            'existing_params':  ("Saved params (fallback)","#FFA500"),
            'loaded_fallback':  ("Loaded saved curve",   "#FFA500"),
        }
        mode_key = self.fit_info.get('mode', 'unknown')
        mode_label, mode_color = mode_map.get(mode_key, (mode_key, "#888"))
        n_pts = self.fit_info.get('n_points', '?')

        quality_layout.addWidget(QLabel("Fit mode:"), 0, 0)
        mode_lbl = QLabel(f"{mode_label}  ({n_pts} data point{'s' if str(n_pts) != '1' else ''})")
        mode_lbl.setStyleSheet(f"color: {mode_color}; font-weight: bold;")
        quality_layout.addWidget(mode_lbl, 0, 1)

        quality_layout.addWidget(QLabel("Formula:"), 1, 0)
        formula_lbl = QLabel(self.formula)
        formula_lbl.setStyleSheet("font-family: monospace; color: #9C27B0;")
        quality_layout.addWidget(formula_lbl, 1, 1)

        rmse = self.fit_info.get('rmse')
        if rmse is not None:
            quality_layout.addWidget(QLabel("RMSE:"), 2, 0)
            rmse_color = "#4CAF50" if rmse < 1.0 else "#FFA500" if rmse < 3.0 else "#f44336"
            rmse_lbl = QLabel(f"{rmse:.3f} s")
            rmse_lbl.setStyleSheet(f"color: {rmse_color}; font-weight: bold;")
            quality_layout.addWidget(rmse_lbl, 2, 1)
        
        # Add points needed info if applicable
        points_needed = self.fit_info.get('points_needed', 0)
        if points_needed > 0:
            quality_layout.addWidget(QLabel("Points needed:"), 3, 0)
            need_lbl = QLabel(f"{points_needed} more race(s) for better fit")
            need_lbl.setStyleSheet("color: #FFA500; font-style: italic;")
            quality_layout.addWidget(need_lbl, 3, 1)

        layout.addWidget(quality_group)
        layout.addSpacing(6)

        # ── Outlier warnings (only if present) ───────────────────────
        if self.outliers:
            outlier_group = QGroupBox(f"⚠ Outlier Warning  ({len(self.outliers)} point(s) deviate from curve)")
            outlier_group.setStyleSheet(
                "QGroupBox { color: #FFA500; border: 2px solid #FFA500; "
                "border-radius: 5px; margin-top: 8px; padding-top: 8px; }"
                "QGroupBox::title { left: 10px; padding: 0 5px 0 5px; }"
            )
            outlier_layout = QVBoxLayout(outlier_group)
            for o in self.outliers:
                lbl = QLabel(
                    f"  R={o['ratio']:.4f},  T={o['time']:.2f} s  "
                    f"(residual={o['residual']:.2f} s,  z={o['z_score']:.1f}σ)"
                )
                lbl.setStyleSheet("color: #FFA500; font-family: monospace; font-size: 10px;")
                outlier_layout.addWidget(lbl)
            note = QLabel("These points may represent different conditions (wet/dry, tyre compound, etc.).\n"
                          "Consider removing them in the Curve Editor if they shouldn't affect the fit.")
            note.setWordWrap(True)
            note.setStyleSheet("color: #888; font-size: 10px; padding: 4px 0 0 0;")
            outlier_layout.addWidget(note)
            layout.addWidget(outlier_group)
            layout.addSpacing(6)

        # ── Lap times ─────────────────────────────────────────────────
        times_group = QGroupBox("Lap Times")
        times_layout = QGridLayout(times_group)
        times_layout.addWidget(QLabel("Your Lap:"), 0, 0)
        times_layout.addWidget(QLabel(self.user_time), 0, 1)
        times_layout.addWidget(QLabel("AI Best:"), 1, 0)
        times_layout.addWidget(QLabel(self.ai_time), 1, 1)
        layout.addWidget(times_group)
        layout.addSpacing(6)

        # ── Ratio changes ─────────────────────────────────────────────
        changes_group = QGroupBox("Ratio Changes")
        changes_layout = QVBoxLayout(changes_group)

        for ratio_type, new_value in self.new_ratios.items():
            current = self.current_ratios.get(ratio_type, 1.0)
            display_name = "Qualifying" if ratio_type == "QualRatio" else "Race"
            diff = new_value - current

            frame = QFrame()
            frame.setStyleSheet("QFrame { background-color: #3c3c3c; border-radius: 4px; padding: 8px; }")
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
                change_text, change_color = f"+{diff:.4f} (AI faster)", "#4CAF50"
            elif diff < 0:
                change_text, change_color = f"{diff:.4f} (AI slower)", "#f44336"
            else:
                change_text, change_color = "no change", "#888"

            change_label = QLabel(change_text)
            change_label.setStyleSheet(f"color: {change_color};")
            frame_layout.addWidget(change_label)
            frame_layout.addStretch()
            changes_layout.addWidget(frame)

        layout.addWidget(changes_group)
        layout.addSpacing(16)

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
    """Dialog for saving current data to historic.csv with car class and vehicle info"""

    def __init__(self, track_name: str, current_ratios: Dict[str, float],
                 ai_times: Dict[str, float], user_times: Dict[str, float],
                 vehicles: Dict[str, str], parent=None):
        super().__init__(parent)
        self.track_name = track_name
        self.current_ratios = current_ratios
        self.ai_times = ai_times
        self.user_times = user_times
        self.vehicles = vehicles  # Now contains both vehicle and team info
        self.car_class = ""
        self.setup_ui()

    def setup_ui(self):
        self.setWindowTitle(f"Save to Historic CSV - {self.track_name}")
        self.setModal(True)
        self.setMinimumWidth(650)

        self.setStyleSheet("""
            QDialog { background-color: #2b2b2b; }
            QLabel { color: white; }
            QLineEdit {
                background-color: #3c3c3c; color: white;
                border: 1px solid #4CAF50; border-radius: 3px; padding: 5px;
            }
            QGroupBox {
                color: #4CAF50; border: 2px solid #555; border-radius: 5px;
                margin-top: 8px; padding-top: 8px;
            }
            QPushButton {
                background-color: #4CAF50; color: white; border: none;
                border-radius: 3px; padding: 8px; font-weight: bold;
            }
            QPushButton:hover { background-color: #45a049; }
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

        # Vehicles information - FIXED: Show both vehicle and team
        vehicles_group = QGroupBox("Vehicle Information")
        vehicles_layout = QGridLayout(vehicles_group)

        vehicles_layout.addWidget(QLabel("Your Vehicle:"), 0, 0)
        user_vehicle = QLabel(self.vehicles.get('user', 'Unknown'))
        user_vehicle.setStyleSheet("color: #4CAF50; font-weight: bold;")
        vehicles_layout.addWidget(user_vehicle, 0, 1)
        
        vehicles_layout.addWidget(QLabel("Your Team:"), 0, 2)
        user_team = QLabel(self.vehicles.get('user_team', 'Unknown'))
        user_team.setStyleSheet("color: #4CAF50;")
        vehicles_layout.addWidget(user_team, 0, 3)

        vehicles_layout.addWidget(QLabel("Qualifying Best AI:"), 1, 0)
        vehicles_layout.addWidget(QLabel(f"{self.vehicles.get('qual_best', 'Unknown')}"), 1, 1)
        vehicles_layout.addWidget(QLabel("Team:"), 1, 2)
        vehicles_layout.addWidget(QLabel(f"{self.vehicles.get('qual_best_team', 'Unknown')}"), 1, 3)

        vehicles_layout.addWidget(QLabel("Qualifying Worst AI:"), 2, 0)
        vehicles_layout.addWidget(QLabel(f"{self.vehicles.get('qual_worst', 'Unknown')}"), 2, 1)
        vehicles_layout.addWidget(QLabel("Team:"), 2, 2)
        vehicles_layout.addWidget(QLabel(f"{self.vehicles.get('qual_worst_team', 'Unknown')}"), 2, 3)

        vehicles_layout.addWidget(QLabel("Race Best AI:"), 3, 0)
        vehicles_layout.addWidget(QLabel(f"{self.vehicles.get('race_best', 'Unknown')}"), 3, 1)
        vehicles_layout.addWidget(QLabel("Team:"), 3, 2)
        vehicles_layout.addWidget(QLabel(f"{self.vehicles.get('race_best_team', 'Unknown')}"), 3, 3)

        vehicles_layout.addWidget(QLabel("Race Worst AI:"), 4, 0)
        vehicles_layout.addWidget(QLabel(f"{self.vehicles.get('race_worst', 'Unknown')}"), 4, 1)
        vehicles_layout.addWidget(QLabel("Team:"), 4, 2)
        vehicles_layout.addWidget(QLabel(f"{self.vehicles.get('race_worst_team', 'Unknown')}"), 4, 3)

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
        """Get the data to save with correct vehicle mapping"""
        self.car_class = self.car_class_input.text().strip()
        return {
            # User vehicle info - use the car class from input or detected vehicle
            'user_vehicle': self.car_class if self.car_class else self.vehicles.get('user', 'Unknown'),
            
            # Qualifying data
            'qual_ratio': self.current_ratios.get('QualRatio', 1.0),
            'qual_best': self.ai_times.get('qual_best_sec', 0.0),
            'qual_worst': self.ai_times.get('qual_worst_sec', 0.0),
            'qual_user': self.user_times.get('qual', 0.0),
            'qual_best_vehicle': self.vehicles.get('qual_best', 'Unknown'),
            'qual_worst_vehicle': self.vehicles.get('qual_worst', 'Unknown'),
            
            # Race data
            'race_ratio': self.current_ratios.get('RaceRatio', 1.0),
            'race_best': self.ai_times.get('race_best_sec', 0.0),
            'race_worst': self.ai_times.get('race_worst_sec', 0.0),
            'race_user': self.user_times.get('race', 0.0),
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
            QDialog { background-color: #2b2b2b; }
            QLabel { color: white; }
            QPushButton {
                background-color: #4CAF50; color: white; border: none;
                border-radius: 3px; padding: 8px; font-weight: bold;
            }
            QPushButton:hover { background-color: #45a049; }
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
            frame.setStyleSheet("QFrame { background-color: #3c3c3c; border-radius: 4px; padding: 5px; }")
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
                change_text, change_color = f"+{diff:.4f} (faster)", "#4CAF50"
            elif diff < 0:
                change_text, change_color = f"{diff:.4f} (slower)", "#f44336"
            else:
                change_text, change_color = "no change", "#888"

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
    """Main GUI window - UPDATED with enhanced autopilot"""

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
        
        # Track change tracking
        self._current_autopilot_track = None

        self.setup_ui()
        self.update_status()
        self.update_backup_info()

        # Load autopilot setting from config
        from cfg_manage import get_autopilot_enabled
        self.autopilot_enabled = get_autopilot_enabled()
        self.log_message(f"Initial autopilot state from config: {self.autopilot_enabled}", "info")
        self.update_autopilot_button()

        # Initially disable save button
        self.save_to_csv_btn.setEnabled(False)

    def check_track_change(self, new_track: str) -> bool:
        """Check if track has changed and handle autopilot accordingly"""
        if self._current_autopilot_track is None:
            # First race, store track
            self._current_autopilot_track = new_track
            return True
        
        if self._current_autopilot_track.lower() != new_track.lower():
            # Track changed while autopilot was active
            self.log_message(
                f"⚠️ Track changed from '{self._current_autopilot_track}' to '{new_track}'. "
                f"Autopilot paused. Review data for new track before re-enabling.",
                "warning"
            )
            
            # Show dialog asking user what to do
            msg = QMessageBox(self)
            msg.setWindowTitle("Track Change Detected")
            msg.setIcon(QMessageBox.Question)
            msg.setText(f"Track changed from '{self._current_autopilot_track}' to '{new_track}'")
            msg.setInformativeText(
                "Autopilot is currently paused. What would you like to do?\n\n"
                "• Continue with autopilot on new track (if enough data exists)\n"
                "• Keep autopilot disabled for now\n"
                "• Disable autopilot permanently"
            )
            
            continue_btn = msg.addButton("Continue on New Track", QMessageBox.AcceptRole)
            pause_btn = msg.addButton("Keep Disabled", QMessageBox.RejectRole)
            disable_btn = msg.addButton("Disable Autopilot", QMessageBox.DestructiveRole)
            
            msg.exec_()
            
            clicked = msg.clickedButton()
            
            if clicked == disable_btn:
                # Disable autopilot and save to config
                self.autopilot_enabled = False
                update_autopilot_enabled(False)
                self.update_autopilot_button()
                self.log_message("Autopilot disabled due to track change", "info")
                return False
            elif clicked == continue_btn:
                # Check if new track has enough data
                readiness = self.curve_manager.get_readiness(new_track)
                if readiness['can_autopilot']:
                    self._current_autopilot_track = new_track
                    self.log_message(f"Continuing autopilot on new track: {new_track}", "info")
                    if readiness.get('needs_warning'):
                        self.log_message(f"Note: {readiness['message']}", "warning")
                    return True
                else:
                    self.log_message(
                        f"Cannot continue autopilot: {readiness['message']}", 
                        "warning"
                    )
                    # Show detailed message
                    QMessageBox.warning(
                        self,
                        "Insufficient Data",
                        readiness.get('detailed_message', readiness['message'])
                    )
                    self.autopilot_enabled = False
                    update_autopilot_enabled(False)
                    self.update_autopilot_button()
                    return False
            else:
                # Pause autopilot
                self.autopilot_enabled = False
                update_autopilot_enabled(False)
                self.update_autopilot_button()
                self.log_message("Autopilot paused due to track change", "info")
                return False
        
        return True

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
        self.setWindowTitle("Live AI Tuner")
        self.setGeometry(100, 100, 950, 750)

        self.setStyleSheet("""
            QMainWindow { background-color: #1e1e1e; }
            QLabel { color: white; }
            QPushButton {
                background-color: #4CAF50; color: white; border: none;
                border-radius: 4px; padding: 8px; font-weight: bold;
            }
            QPushButton:hover { background-color: #45a049; }
            QPushButton:disabled { background-color: #555; color: #888; }
            QGroupBox {
                color: #4CAF50; border: 2px solid #555; border-radius: 5px;
                margin-top: 8px; padding-top: 8px;
            }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px 0 5px; }
            QTextEdit {
                background-color: #2b2b2b; color: #4CAF50;
                border: 1px solid #4CAF50; border-radius: 3px; font-family: monospace;
            }
            QLineEdit {
                background-color: #3c3c3c; color: white;
                border: 1px solid #4CAF50; border-radius: 3px; padding: 5px;
            }
            QCheckBox { color: white; spacing: 8px; }
            QCheckBox::indicator { width: 18px; height: 18px; }
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
            font-size: 22px; font-weight: bold; color: #FFA500;
            background-color: #2b2b2b; border-radius: 6px;
            padding: 10px; margin: 2px;
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

    def _do_enable_autopilot(self, track_name: str):
        """Actually enable autopilot after readiness check"""
        self.autopilot_enabled = True
        update_autopilot_enabled(True)
        self.update_autopilot_button()
        
        # Store current track if available
        if track_name:
            self._current_autopilot_track = track_name
            self.log_message(f"Autopilot enabled for track: {track_name}", "success")
        else:
            self.log_message("Autopilot enabled (waiting for track detection)", "success")
        
        # Show a quick confirmation
        QMessageBox.information(
            self,
            "Autopilot Enabled",
            f"Autopilot is now active.\n\n"
            f"It will automatically:\n"
            f"• Save race data to CSV\n"
            f"• Update the curve model\n"
            f"• Calculate and apply new ratios\n\n"
            f"Track: {track_name if track_name else 'Waiting for race...'}\n\n"
            f"You can disable autopilot anytime by clicking the button again."
        )

    def toggle_autopilot(self):
        """Toggle autopilot mode - Shows detailed readiness check before enabling"""
        from cfg_manage import update_autopilot_enabled, get_autopilot_enabled
        
        self.log_message("=" * 60, "info")
        self.log_message(f"Autopilot button clicked", "info")
        self.log_message(f"  Current self.autopilot_enabled: {self.autopilot_enabled}", "info")
        self.log_message(f"  Current config autopilot_enabled: {get_autopilot_enabled()}", "info")
        
        # If autopilot is currently ON, we're turning it OFF - simple toggle
        if self.autopilot_enabled:
            self.log_message("Turning autopilot OFF", "info")
            self.autopilot_enabled = False
            update_autopilot_enabled(False)
            self.update_autopilot_button()
            self._current_autopilot_track = None
            self.log_message("Autopilot disabled", "info")
            return
        
        # ── AUTOPILOT IS OFF, SHOW READINESS CHECK BEFORE ENABLING ─────────
        self.log_message("Showing readiness check dialog...", "info")
        
        # Get current track (if any)
        track_name = self.last_results.get('track_name') if self.last_results else None
        self.log_message(f"Current track: {track_name}", "info")
        
        # Create detailed readiness dialog
        dialog = QDialog(self)
        dialog.setWindowTitle("Autopilot Readiness Check")
        dialog.setModal(True)
        dialog.setMinimumWidth(550)
        dialog.setStyleSheet("""
            QDialog { background-color: #2b2b2b; }
            QLabel { color: white; }
            QGroupBox {
                color: #4CAF50; border: 2px solid #555; border-radius: 5px;
                margin-top: 8px; padding-top: 8px;
            }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px 0 5px; }
            QPushButton {
                background-color: #4CAF50; color: white; border: none;
                border-radius: 3px; padding: 8px; font-weight: bold;
            }
            QPushButton:hover { background-color: #45a049; }
            QPushButton#cancel { background-color: #f44336; }
            QPushButton#cancel:hover { background-color: #d32f2f; }
            QPushButton:disabled { background-color: #555; color: #888; }
        """)
        
        layout = QVBoxLayout(dialog)
        
        # Header
        header = QLabel("🔍 Autopilot Readiness Check")
        header.setStyleSheet("font-size: 16px; font-weight: bold; color: #FFA500; padding: 10px;")
        header.setAlignment(Qt.AlignCenter)
        layout.addWidget(header)
        
        layout.addSpacing(10)
        
        # ── Gather all readiness data ──────────────────────────────────────
        stats = self.curve_manager.get_stats()
        total_points = stats['total_points']
        total_tracks = stats['total_tracks']
        global_k = stats['global_k']
        has_curve = total_points >= 2 or len(stats['track_params']) > 0
        
        # Track-specific readiness
        track_readiness = None
        if track_name:
            track_readiness = self.curve_manager.get_readiness(track_name)
        
        # Check if track is known
        track_has_points = track_name and track_name in self.curve_manager.curve.points_by_track
        track_points_count = len(self.curve_manager.curve.points_by_track.get(track_name, [])) if track_has_points else 0
        
        # Check if we have any points at all
        has_any_data = total_points > 0
        
        # ── Status Overview Group ──────────────────────────────────────────
        status_group = QGroupBox("📊 Data Status Overview")
        status_layout = QGridLayout(status_group)
        
        row = 0
        status_layout.addWidget(QLabel("Current Track:"), row, 0)
        track_display = QLabel(track_name if track_name else "No track detected yet")
        track_display.setStyleSheet("color: #FFA500; font-weight: bold;" if track_name else "color: #888;")
        status_layout.addWidget(track_display, row, 1)
        
        row += 1
        status_layout.addWidget(QLabel("Total Data Points:"), row, 0)
        points_label = QLabel(f"{total_points} point{'s' if total_points != 1 else ''}")
        points_label.setStyleSheet("color: #4CAF50; font-weight: bold;" if total_points > 0 else "color: #f44336;")
        status_layout.addWidget(points_label, row, 1)
        
        row += 1
        status_layout.addWidget(QLabel("Total Tracks with Data:"), row, 0)
        tracks_label = QLabel(f"{total_tracks} track{'s' if total_tracks != 1 else ''}")
        tracks_label.setStyleSheet("color: #4CAF50; font-weight: bold;" if total_tracks > 0 else "color: #888;")
        status_layout.addWidget(tracks_label, row, 1)
        
        if track_name:
            row += 1
            status_layout.addWidget(QLabel(f"Points for '{track_name}':"), row, 0)
            track_points_label = QLabel(f"{track_points_count} point{'s' if track_points_count != 1 else ''}")
            if track_points_count == 0:
                track_points_label.setStyleSheet("color: #FFA500;")
            elif track_points_count == 1:
                track_points_label.setStyleSheet("color: #FFA500; font-weight: bold;")
            else:
                track_points_label.setStyleSheet("color: #4CAF50; font-weight: bold;")
            status_layout.addWidget(track_points_label, row, 1)
        
        if global_k and has_any_data:
            row += 1
            status_layout.addWidget(QLabel("Global k (prior):"), row, 0)
            k_label = QLabel(f"{global_k:.4f}")
            k_label.setStyleSheet("color: #9C27B0; font-family: monospace;")
            status_layout.addWidget(k_label, row, 1)
        
        layout.addWidget(status_group)
        layout.addSpacing(10)
        
        # ── Track-Specific Assessment (if track is known) ───────────────────
        if track_name and track_readiness:
            assessment_group = QGroupBox(f"🎯 Assessment for '{track_name}'")
            assessment_layout = QVBoxLayout(assessment_group)
            
            # Fit quality
            quality_map = {
                'none': ("❌ No data", "#f44336"),
                'bootstrap_global': ("⚠️ Global estimation (least reliable)", "#FFA500"),
                'bootstrap_1pt': ("⚠️ 1-point bootstrap (moderate accuracy)", "#FFA500"),
                'exact_2pt': ("✅ Exact 2-point fit (good accuracy)", "#4CAF50"),
                'least_squares': ("✅✅ Least-squares fit (high accuracy)", "#4CAF50"),
            }
            quality_text, quality_color = quality_map.get(
                track_readiness['fit_quality'], 
                (track_readiness['fit_quality'], "#888")
            )
            
            quality_label = QLabel(f"Fit Type: {quality_text}")
            quality_label.setStyleSheet(f"color: {quality_color}; font-weight: bold;")
            assessment_layout.addWidget(quality_label)
            
            # Message
            msg_label = QLabel(track_readiness['message'])
            msg_label.setWordWrap(True)
            msg_label.setStyleSheet("color: #AAA; padding: 5px;")
            assessment_layout.addWidget(msg_label)
            
            # Detailed message with points needed
            if track_readiness.get('points_needed', 0) > 0:
                need_label = QLabel(f"\n📈 {track_readiness['detailed_message']}")
                need_label.setWordWrap(True)
                need_label.setStyleSheet("color: #FFA500; padding: 5px; font-style: italic;")
                assessment_layout.addWidget(need_label)
            
            layout.addWidget(assessment_group)
            layout.addSpacing(10)
        
        # ── What Autopilot Will Do ─────────────────────────────────────────
        info_group = QGroupBox("🤖 What Autopilot Will Do")
        info_layout = QVBoxLayout(info_group)
        
        steps = [
            "1. 📝 Save current race data to historic.csv",
            "2. 📊 Add AI lap times as data points to the curve",
            "3. 🔄 Auto-fit the curve (same as 'Auto-Fit Current Track')",
            "4. 🎯 Calculate new QualRatio and/or RaceRatio from your lap time",
            "5. ✅ Show confirmation dialog with all changes",
            "6. ✍️ Apply new ratios to AIW file (if confirmed)",
            "7. 🔁 Listen for new races and repeat"
        ]
        
        for step in steps:
            step_label = QLabel(step)
            step_label.setStyleSheet("color: #AAA; font-size: 11px; padding: 2px;")
            info_layout.addWidget(step_label)
        
        layout.addWidget(info_group)
        layout.addSpacing(15)
        
        # ── Warning Section (if data is insufficient) ──────────────────────
        can_autopilot = False
        warning_text = ""
        warning_color = "#FFA500"
        
        # Determine if autopilot can be enabled
        if not track_name:
            can_autopilot = False
            warning_text = "⚠️ No track detected yet.\n\nComplete a race first so the program can identify which track you're racing on."
            warning_color = "#f44336"
        elif track_readiness:
            can_autopilot = track_readiness['can_autopilot']
            if not can_autopilot:
                warning_text = f"⚠️ {track_readiness['message']}\n\n{track_readiness.get('detailed_message', '')}"
                warning_color = "#f44336"
            elif track_readiness.get('needs_warning'):
                warning_text = f"⚠️ {track_readiness['message']}\n\n{track_readiness.get('detailed_message', '')}"
                warning_color = "#FFA500"
        elif not has_any_data:
            can_autopilot = False
            warning_text = "⚠️ No data available at all.\n\nYou need at least 2 races with different ratio settings to build a proper curve."
            warning_color = "#f44336"
        else:
            can_autopilot = has_any_data
        
        if warning_text:
            warning_group = QGroupBox("⚠️ Important Notice")
            warning_group.setStyleSheet("QGroupBox { color: #FFA500; border: 2px solid #FFA500; }")
            warning_layout = QVBoxLayout(warning_group)
            
            warning_label = QLabel(warning_text)
            warning_label.setWordWrap(True)
            warning_label.setStyleSheet(f"color: {warning_color}; padding: 5px;")
            warning_layout.addWidget(warning_label)
            
            layout.addWidget(warning_group)
            layout.addSpacing(10)
        
        # ── Buttons ────────────────────────────────────────────────────────
        button_layout = QHBoxLayout()
        
        if can_autopilot:
            enable_btn = QPushButton("✓ Enable Autopilot")
            enable_btn.setFixedHeight(45)
            enable_btn.setFixedWidth(150)
            enable_btn.clicked.connect(lambda: self._do_enable_autopilot(track_name, dialog))
            button_layout.addWidget(enable_btn)
        else:
            enable_btn = QPushButton("Enable Autopilot")
            enable_btn.setEnabled(False)
            enable_btn.setFixedHeight(45)
            enable_btn.setFixedWidth(150)
            enable_btn.setToolTip("Not enough data to enable autopilot")
            button_layout.addWidget(enable_btn)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setObjectName("cancel")
        cancel_btn.setFixedHeight(45)
        cancel_btn.setFixedWidth(150)
        cancel_btn.clicked.connect(dialog.reject)
        button_layout.addWidget(cancel_btn)
        
        button_layout.addStretch()
        layout.addLayout(button_layout)
        
        layout.addSpacing(10)
        
        # Show dialog
        dialog.exec_()

    def _do_enable_autopilot(self, track_name: str, dialog=None):
        """Actually enable autopilot after readiness check"""
        from cfg_manage import update_autopilot_enabled
        
        self.log_message("=" * 60, "info")
        self.log_message("ENABLING AUTOPILOT", "success")
        self.log_message(f"  Track: {track_name}", "info")
        self.log_message(f"  Before - self.autopilot_enabled: {self.autopilot_enabled}", "info")
        
        # Set the flag
        self.autopilot_enabled = True
        
        # Save to config
        update_autopilot_enabled(True)
        
        # Update button appearance
        self.update_autopilot_button()
        
        # Store current track if available
        if track_name:
            self._current_autopilot_track = track_name
            self.log_message(f"  Stored track: {self._current_autopilot_track}", "info")
        
        # Verify it was set
        from cfg_manage import get_autopilot_enabled
        self.log_message(f"  After - self.autopilot_enabled: {self.autopilot_enabled}", "info")
        self.log_message(f"  After - config autopilot_enabled: {get_autopilot_enabled()}", "info")
        
        # Close the dialog if provided
        if dialog:
            dialog.accept()
        
        self.log_message("✓ Autopilot enabled successfully", "success")
        
        # Show a quick confirmation
        QMessageBox.information(
            self,
            "Autopilot Enabled",
            f"Autopilot is now active.\n\n"
            f"It will automatically:\n"
            f"• Save race data to CSV\n"
            f"• Update the curve model\n"
            f"• Calculate and apply new ratios\n\n"
            f"Track: {track_name if track_name else 'Waiting for race...'}\n\n"
            f"You can disable autopilot anytime by clicking the button again.\n\n"
            f"NOTE: The next race result will trigger autopilot."
        )

    def _do_enable_autopilot(self, track_name: str, dialog=None):
        """Actually enable autopilot after readiness check"""
        from cfg_manage import update_autopilot_enabled
        
        self.log_message("=" * 60, "info")
        self.log_message("ENABLING AUTOPILOT", "success")
        self.log_message(f"  Track: {track_name}", "info")
        self.log_message(f"  Before - self.autopilot_enabled: {self.autopilot_enabled}", "info")
        
        # Set the flag
        self.autopilot_enabled = True
        
        # Save to config
        update_autopilot_enabled(True)
        
        # Update button appearance
        self.update_autopilot_button()
        
        # Store current track if available
        if track_name:
            self._current_autopilot_track = track_name
            self.log_message(f"  Stored track: {self._current_autopilot_track}", "info")
        
        # Verify it was set
        from cfg_manage import get_autopilot_enabled
        self.log_message(f"  After - self.autopilot_enabled: {self.autopilot_enabled}", "info")
        self.log_message(f"  After - config autopilot_enabled: {get_autopilot_enabled()}", "info")
        
        # Close the dialog if provided
        if dialog:
            dialog.accept()
        
        self.log_message("✓ Autopilot enabled successfully", "success")
        
        # Show a quick confirmation
        QMessageBox.information(
            self,
            "Autopilot Enabled",
            f"Autopilot is now active.\n\n"
            f"It will automatically:\n"
            f"• Save race data to CSV\n"
            f"• Update the curve model\n"
            f"• Calculate and apply new ratios\n\n"
            f"Track: {track_name if track_name else 'Waiting for race...'}\n\n"
            f"You can disable autopilot anytime by clicking the button again.\n\n"
            f"NOTE: The next race result will trigger autopilot."
        )

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
            backup_status = "Backup: ✓"
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

        # Get driver information
        drivers = data.get('drivers', [])

        # Extract vehicles - FIXED: Use vehicle field, not team
        user_vehicle = "Unknown"
        qual_best_vehicle = "Unknown"
        qual_worst_vehicle = "Unknown"
        race_best_vehicle = "Unknown"
        race_worst_vehicle = "Unknown"
        
        # Also keep team for reference
        user_team = "Unknown"
        qual_best_team = "Unknown"
        qual_worst_team = "Unknown"
        race_best_team = "Unknown"
        race_worst_team = "Unknown"

        # Find user vehicle (slot 0)
        user_name = data.get('user_name', 'Unknown')
        self.user_name_label.setText(user_name if user_name != 'Unknown' else '---')

# In _update_race_results method, ensure vehicle data is correctly captured:

        # Parse vehicles from driver data
        for driver in drivers:
            driver_name = driver.get('name', '')
            driver_vehicle = driver.get('vehicle', 'Unknown')
            driver_team = driver.get('team', 'Unknown')
            slot = driver.get('slot', -1)

            if slot == 0:
                user_vehicle = driver_vehicle if driver_vehicle != 'Unknown' else 'Unknown'
                user_team = driver_team if driver_team != 'Unknown' else 'Unknown'
                self.user_vehicle_label.setText(user_vehicle)

            # Match AI vehicles based on lap times
            # For qualifying best
            if driver.get('qual_time') and driver['qual_time'] == data.get('qual_best_ai_lap'):
                qual_best_vehicle = driver_vehicle if driver_vehicle != 'Unknown' else 'Unknown'
                qual_best_team = driver_team if driver_team != 'Unknown' else 'Unknown'
            
            # For qualifying worst
            if driver.get('qual_time') and driver['qual_time'] == data.get('qual_worst_ai_lap'):
                qual_worst_vehicle = driver_vehicle if driver_vehicle != 'Unknown' else 'Unknown'
                qual_worst_team = driver_team if driver_team != 'Unknown' else 'Unknown'
            
            # For race best
            if driver.get('best_lap') and driver['best_lap'] == data.get('best_ai_lap'):
                race_best_vehicle = driver_vehicle if driver_vehicle != 'Unknown' else 'Unknown'
                race_best_team = driver_team if driver_team != 'Unknown' else 'Unknown'
            
            # For race worst
            if driver.get('best_lap') and driver['best_lap'] == data.get('worst_ai_lap'):
                race_worst_vehicle = driver_vehicle if driver_vehicle != 'Unknown' else 'Unknown'
                race_worst_team = driver_team if driver_team != 'Unknown' else 'Unknown'

        # Store vehicles with correct mapping
        self.current_vehicles = {
            'user': user_vehicle,
            'user_team': user_team,
            'qual_best': qual_best_vehicle,
            'qual_best_team': qual_best_team,
            'qual_worst': qual_worst_vehicle,
            'qual_worst_team': qual_worst_team,
            'race_best': race_best_vehicle,
            'race_best_team': race_best_team,
            'race_worst': race_worst_vehicle,
            'race_worst_team': race_worst_team
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
        
        # DEBUG: Show autopilot state
        self.log_message(f"=== AUTOPILOT DEBUG ===", "info")
        self.log_message(f"self.autopilot_enabled = {self.autopilot_enabled}", "info")
        self.log_message(f"type(self.autopilot_enabled) = {type(self.autopilot_enabled)}", "info")
        
        # Autopilot check
        if self.autopilot_enabled:
            self.log_message("Autopilot is enabled, checking curve data...", "info")
            if self.check_curve_exists():
                self.log_message("Curve exists, starting autopilot process...", "info")
                self.autopilot_process()
            else:
                self.log_message("Autopilot: No curve data available", "warning")
        else:
            self.log_message("Autopilot is disabled - not processing", "info")

    def format_time(self, seconds: float) -> str:
        """Format seconds as mm:ss.ms"""
        if seconds <= 0:
            return 'N/A'
        minutes = int(seconds) // 60
        secs = int(seconds) % 60
        ms = int((seconds - int(seconds)) * 1000)
        return f"{minutes}:{secs:02d}.{ms:03d}"

    # ------------------------------------------------------------------
    # Autopilot - ENHANCED
    # ------------------------------------------------------------------

    def autopilot_process(self):
        """
        Enhanced autopilot with clear workflow steps.
        """
        self.log_message("=" * 60, "info")
        self.log_message("AUTOPILOT PROCESS STARTED", "success")
        self.log_message(f"Autopilot enabled: {self.autopilot_enabled}", "info")
        
        if not self.last_results:
            self.log_message("Autopilot: No race results available", "warning")
            return

        track_name = self.last_results.get('track_name', 'Unknown')
        self.log_message(f"Processing track: {track_name}", "info")

        if not self.last_results:
            self.log_message("Autopilot: No race results available", "warning")
            return

        track_name = self.last_results.get('track_name', 'Unknown')
        
        # STEP 1: Check for track change
        if not self.check_track_change(track_name):
            return
        
        # STEP 2: Gather race data
        qual_best_ai_sec  = self.last_results.get('qual_best_ai_lap_sec',  0.0)
        qual_worst_ai_sec = self.last_results.get('qual_worst_ai_lap_sec', 0.0)
        race_best_ai_sec  = self.last_results.get('best_ai_lap_sec',       0.0)
        race_worst_ai_sec = self.last_results.get('worst_ai_lap_sec',      0.0)
        
        user_qual_str = self.last_results.get('user_qualifying', 'N/A')
        user_race_str = self.last_results.get('user_best_lap', 'N/A')
        user_qual_sec = self._parse_time(user_qual_str) if user_qual_str != 'N/A' else 0.0
        user_race_sec = self._parse_time(user_race_str) if user_race_str != 'N/A' else 0.0
        
        # Validate we have user lap time
        if user_qual_sec <= 0 and user_race_sec <= 0:
            self.log_message("Autopilot: No user lap time found", "warning")
            QMessageBox.warning(self, "Autopilot Error", 
                               "No user lap time detected.\n\n"
                               "Autopilot needs your lap time to calculate new ratios.\n"
                               "Please complete a lap in qualifying or race.")
            return
        
        current_qual_ratio = self.last_results.get('qual_ratio') or 1.0
        current_race_ratio = self.last_results.get('race_ratio') or 1.0
        
        # STEP 3: Save to CSV
        vehicles = self.current_vehicles if hasattr(self, 'current_vehicles') else {}
        car_class = vehicles.get('user', 'Unknown')
        
        self._append_to_historic_csv({
            'car_class': car_class,
            'qual_ratio': current_qual_ratio,
            'qual_best': qual_best_ai_sec,
            'qual_worst': qual_worst_ai_sec,
            'qual_user': user_qual_sec,
            'race_ratio': current_race_ratio,
            'race_best': race_best_ai_sec,
            'race_worst': race_worst_ai_sec,
            'race_user': user_race_sec,
            'user_vehicle': car_class,
            'qual_best_vehicle': vehicles.get('qual_best', 'Unknown'),
            'qual_worst_vehicle': vehicles.get('qual_worst', 'Unknown'),
            'race_best_vehicle': vehicles.get('race_best', 'Unknown'),
            'race_worst_vehicle': vehicles.get('race_worst', 'Unknown'),
        }, track_name)
        
        # STEP 4: Add data points to curve
        added_any = False
        
        if current_qual_ratio > 0 and qual_best_ai_sec > 0 and qual_worst_ai_sec > 0:
            self.curve_manager.curve.add_point(track_name, current_qual_ratio,
                                               qual_best_ai_sec, qual_worst_ai_sec)
            self.log_message(f"Added qual point: R={current_qual_ratio:.4f}", "info")
            added_any = True
        
        if current_race_ratio > 0 and race_best_ai_sec > 0 and race_worst_ai_sec > 0:
            self.curve_manager.curve.add_point(track_name, current_race_ratio,
                                               race_best_ai_sec, race_worst_ai_sec)
            self.log_message(f"Added race point: R={current_race_ratio:.4f}", "info")
            added_any = True
        
        if not added_any:
            self.log_message("Autopilot: No valid AI lap times found", "warning")
            return
        
        # STEP 5: Fit the curve
        fit_info = self.curve_manager.fit_track(track_name)
        self.curve_manager.curve.fit_global_k()
        
        # Check if fit produced usable formula
        has_formula = track_name in self.curve_manager.curve.track_params
        n_points = len(self.curve_manager.curve.points_by_track.get(track_name, []))
        
        self.log_message(f"Fit result: {fit_info['mode']}, {n_points} points", "info")
        
        # STEP 6: Validate fit quality
        if not has_formula:
            # No formula available
            QMessageBox.warning(
                self,
                "Cannot Calculate Ratios",
                f"Cannot create formula for '{track_name}'.\n\n"
                f"Data points: {n_points}\n"
                f"Need at least 2 points with different ratios.\n\n"
                f"Current points:\n" + 
                "\n".join([f"  R={r:.4f} → T={t:.2f}s" for r, t in self.curve_manager.curve.points_by_track.get(track_name, [])])
            )
            return
        
        # Check if we have valid a and b parameters
        a = self.curve_manager.curve.track_params[track_name]['a']
        b = self.curve_manager.curve.track_params[track_name]['b']
        
        if a <= 0 or b <= 0:
            QMessageBox.warning(
                self,
                "Invalid Formula",
                f"Calculated formula is invalid.\n\n"
                f"a={a:.3f}, b={b:.3f}\n\n"
                f"This usually means the data points are too close or invalid.\n"
                f"Try using more varied ratio values."
            )
            return
        
        # Save curve if we have good data (≥2 points)
        if n_points >= 2:
            self.curve_manager.save()
            self.log_message(f"Curve saved: T = {a:.3f}/R + {b:.3f}", "success")
        
        # STEP 7: Predict new ratios
        new_ratios = {}
        
        if user_qual_sec > 0:
            predicted_ratio = self.curve_manager.predict_ratio(user_qual_sec, track_name)
            if predicted_ratio and predicted_ratio > 0:
                new_ratios['QualRatio'] = predicted_ratio
                self.log_message(f"Predicted QualRatio: {predicted_ratio:.6f}", "info")
            else:
                self.log_message(f"Failed to predict QualRatio from {user_qual_str}", "warning")
        
        if user_race_sec > 0:
            predicted_ratio = self.curve_manager.predict_ratio(user_race_sec, track_name)
            if predicted_ratio and predicted_ratio > 0:
                new_ratios['RaceRatio'] = predicted_ratio
                self.log_message(f"Predicted RaceRatio: {predicted_ratio:.6f}", "info")
            else:
                self.log_message(f"Failed to predict RaceRatio from {user_race_str}", "warning")
        
        if not new_ratios:
            QMessageBox.warning(
                self,
                "Prediction Failed",
                f"Could not predict ratios from your lap times.\n\n"
                f"User Qual: {user_qual_str} ({user_qual_sec:.3f}s)\n"
                f"User Race: {user_race_str} ({user_race_sec:.3f}s)\n\n"
                f"Formula: T = {a:.3f}/R + {b:.3f}\n\n"
                f"Your lap time may be outside the valid range of the curve.\n"
                f"Valid range: R=0.3 to 3.0 → T={a/0.3+b:.1f}s to {a/3.0+b:.1f}s"
            )
            return
        
        # STEP 8: Update GUI with predictions
        if 'QualRatio' in new_ratios:
            self.qual_result_label.setText(f"{new_ratios['QualRatio']:.6f}")
            self.apply_qual_check.setChecked(True)
        if 'RaceRatio' in new_ratios:
            self.race_result_label.setText(f"{new_ratios['RaceRatio']:.6f}")
            self.apply_race_check.setChecked(True)
        self.apply_all_btn.setEnabled(True)

        # STEP 9: Check for outliers
        outliers = self.curve_manager.get_outliers(track_name)

        # STEP 10: Show confirmation dialog
        current_ratios = {
            'QualRatio': current_qual_ratio,
            'RaceRatio': current_race_ratio,
        }

        user_time_str = user_race_str if user_race_sec > 0 else user_qual_str
        ai_time_str = (self.format_time(race_best_ai_sec) if race_best_ai_sec > 0
                       else self.format_time(qual_best_ai_sec))
        formula = self.curve_manager.get_formula_string(track_name)

        # Get vehicle info from current_vehicles
        car_class = self.current_vehicles.get('user', 'Unknown') if hasattr(self, 'current_vehicles') else 'Unknown'

        confirm_dialog = AutopilotConfirmationDialog(
            track_name=track_name,
            car_class=car_class,
            formula=formula,
            current_ratios=current_ratios,
            new_ratios=new_ratios,
            user_time=user_time_str,
            ai_time=ai_time_str,
            fit_info=fit_info,
            outliers=outliers,
            parent=self,
        )
        
        if not confirm_dialog.get_decision():
            self.log_message("Autopilot cancelled by user", "warning")
            return
        
        # STEP 11: Apply to AIW file
        self._apply_ratios_autopilot(new_ratios)
        
        self.log_message(f"Autopilot cycle complete for {track_name}", "success")

    def _apply_ratios_autopilot(self, new_ratios: Dict[str, float]):
        """
        Write new ratios to the AIW file with detailed debugging.
        """
        if not self.last_results:
            return

        track_name = self.last_results.get('track_name')
        track_folder = self.last_results.get('track_folder', track_name)
        aiw_filename = self.last_results.get('aiw_file')

        self.log_message("=" * 60, "info")
        self.log_message("AUTOPILOT: Applying ratios", "info")
        self.log_message(f"  Track: {track_name}", "info")
        self.log_message(f"  Track folder: {track_folder}", "info")
        self.log_message(f"  AIW filename from results: {aiw_filename}", "info")
        self.log_message(f"  Base path: {self.base_path}", "info")

        if not aiw_filename:
            self.log_message("ERROR: No AIW filename in results", "error")
            QMessageBox.critical(self, "Error", "No AIW filename found in race results.")
            return

        # Find AIW file
        aiw_path = self.aiw_manager.find_aiw_file(aiw_filename, track_folder, self.base_path)

        if not aiw_path:
            self.log_message("ERROR: AIW file NOT FOUND", "error")
            QMessageBox.critical(self, "Error", f"AIW file not found: {aiw_filename}")
            return

        self.log_message(f"✓ AIW found at: {aiw_path}", "success")
        
        # Get file modification time before
        try:
            mtime_before = aiw_path.stat().st_mtime
            self.log_message(f"  File mtime before: {datetime.fromtimestamp(mtime_before)}", "info")
        except Exception as e:
            self.log_message(f"  Could not get mtime: {e}", "warning")
            mtime_before = None
        
        # Read current ratios before change
        current_qual, current_race = self.aiw_manager.read_ratios(aiw_path)
        self.log_message(f"  Current ratios before:", "info")
        self.log_message(f"    Qual: {current_qual}", "info")
        self.log_message(f"    Race: {current_race}", "info")

        # Apply each ratio
        success_count = 0
        for ratio_type, new_value in new_ratios.items():
            self.log_message(f"  Attempting to update {ratio_type} to {new_value:.6f}", "info")
            
            if self.aiw_manager.update_ratio(aiw_path, ratio_type, new_value, track_name, create_backup=True):
                success_count += 1
                self.log_message(f"  ✓ Successfully updated {ratio_type}", "success")
            else:
                self.log_message(f"  ✗ Failed to update {ratio_type}", "error")

        # Get file modification time after
        try:
            mtime_after = aiw_path.stat().st_mtime
            self.log_message(f"  File mtime after: {datetime.fromtimestamp(mtime_after)}", "info")
            if mtime_before and mtime_after != mtime_before:
                self.log_message(f"  ✓ File was modified (mtime changed)", "success")
            elif mtime_before:
                self.log_message(f"  ✗ File was NOT modified (mtime unchanged)", "warning")
        except Exception as e:
            self.log_message(f"  Could not get mtime after: {e}", "warning")

        if success_count > 0:
            # Read back updated ratios
            new_qual, new_race = self.aiw_manager.read_ratios(aiw_path)
            self.log_message(f"  Ratios after update:", "info")
            self.log_message(f"    Qual: {new_qual} (was {current_qual})", "info")
            self.log_message(f"    Race: {new_race} (was {current_race})", "info")
            
            # Check if they actually changed
            qual_changed = new_qual != current_qual
            race_changed = new_race != current_race
            
            if qual_changed and 'QualRatio' in new_ratios:
                self.log_message(f"  ✓ QualRatio changed from {current_qual} to {new_qual}", "success")
            elif 'QualRatio' in new_ratios:
                self.log_message(f"  ✗ QualRatio did NOT change (expected {new_ratios['QualRatio']})", "error")
            
            if race_changed and 'RaceRatio' in new_ratios:
                self.log_message(f"  ✓ RaceRatio changed from {current_race} to {new_race}", "success")
            elif 'RaceRatio' in new_ratios:
                self.log_message(f"  ✗ RaceRatio did NOT change (expected {new_ratios['RaceRatio']})", "error")
            
            # Update display
            if new_qual is not None:
                self.current_qual_label.setText(f"{new_qual:.6f}")
            if new_race is not None:
                self.current_race_label.setText(f"{new_race:.6f}")
            
            # Update last_results
            if self.last_results:
                self.last_results['qual_ratio'] = new_qual
                self.last_results['race_ratio'] = new_race
            
            self.update_backup_info()
            self.update_status()
            
            QMessageBox.information(
                self,
                "Autopilot Applied",
                f"Successfully applied changes:\n\n"
                f"Qualifying: {new_qual:.6f}\n"
                f"Race: {new_race:.6f}\n\n"
                f"File: {aiw_path.name}\n"
                f"Modified: {'Yes' if (qual_changed or race_changed) else 'No'}"
            )
        else:
            QMessageBox.critical(
                self,
                "Failed to Apply",
                f"Could not apply any ratio changes.\n\n"
                f"AIW file: {aiw_path}\n"
                f"Check file permissions and that the ratio patterns exist."
            )
        
        self.log_message("=" * 60, "info")

    # ------------------------------------------------------------------
    # Manual ratio calculation
    # ------------------------------------------------------------------

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
                    self.log_message("Using bootstrap estimation (error may be +-2-5 seconds)", "info")
                else:
                    self.log_message("Could not calculate ratio. Time may be outside valid range.", "error")
                    result_label.setText("Error")
                    return
            else:
                self.log_message("Could not calculate ratio. Time may be outside valid range.", "error")
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
                    self.log_message("Added data point to global curve", "info")

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
        """Append data to historic.csv with correct column order"""
        csv_path = Path("./historic.csv")
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        file_exists = csv_path.exists()

        try:
            with open(csv_path, 'a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f, delimiter=';')

                if not file_exists:
                    # Write header with correct column order
                    writer.writerow([
                        'User Vehicle',           # Column 1
                        'Timestamp',              # Column 2
                        'Track Name',             # Column 3
                        'Current QualRatio',      # Column 4
                        'Qual AI Best (s)',       # Column 5
                        'Q AI Best Vehicle',      # Column 6
                        'Qual AI Worst (s)',      # Column 7
                        'Q AI Worst Vehicle',     # Column 8
                        'Qual User (s)',          # Column 9
                        'Current RaceRatio',      # Column 10
                        'Race AI Best (s)',       # Column 11
                        'R AI Best Vehicle',      # Column 12
                        'Race AI Worst (s)',      # Column 13
                        'R AI Worst Vehicle',     # Column 14
                        'Race User (s)'           # Column 15
                    ])

                # Write data in the exact same order as header
                writer.writerow([
                    data.get('user_vehicle', 'Unknown'),           # User Vehicle
                    timestamp,                                     # Timestamp
                    track_name,                                    # Track Name
                    f"{data.get('qual_ratio', 0.0):.6f}",         # Current QualRatio
                    f"{data.get('qual_best', 0.0):.3f}",          # Qual AI Best (s)
                    data.get('qual_best_vehicle', 'Unknown'),     # Q AI Best Vehicle
                    f"{data.get('qual_worst', 0.0):.3f}",         # Qual AI Worst (s)
                    data.get('qual_worst_vehicle', 'Unknown'),    # Q AI Worst Vehicle
                    f"{data.get('qual_user', 0.0):.3f}",          # Qual User (s)
                    f"{data.get('race_ratio', 0.0):.6f}",         # Current RaceRatio
                    f"{data.get('race_best', 0.0):.3f}",          # Race AI Best (s)
                    data.get('race_best_vehicle', 'Unknown'),     # R AI Best Vehicle
                    f"{data.get('race_worst', 0.0):.3f}",         # Race AI Worst (s)
                    data.get('race_worst_vehicle', 'Unknown'),    # R AI Worst Vehicle
                    f"{data.get('race_user', 0.0):.3f}"           # Race User (s)
                ])

            self.log_message(f"Saved data to historic.csv (Vehicle: {data.get('user_vehicle', 'Unknown')})", "success")
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
