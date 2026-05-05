#!/usr/bin/env python3
"""
Main window for Live AI Tuner
Redesigned GUI matching the reference image layout
"""

import sys
import threading
import logging
import sqlite3
import re
import shutil
import subprocess
from pathlib import Path
from typing import List, Tuple, Optional, Dict, Any
from datetime import datetime

from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QLabel, QPushButton, QFrame, QMessageBox, QSizePolicy, QDialog,
    QDoubleSpinBox, QFileDialog, QLineEdit, QListWidget, QListWidgetItem,
    QDialogButtonBox, QProgressBar, QTextEdit, QGroupBox
)
from PyQt5.QtCore import Qt, pyqtSignal, QObject, QTimer
from PyQt5.QtGui import QFont, QColor

from core_database import CurveDatabase
from core_formula import get_formula_string, hyperbolic, fit_curve, DEFAULT_A_VALUE
from core_config import (
    get_config_with_defaults, get_results_file_path, get_poll_interval,
    get_db_path, create_default_config_if_missing, get_base_path,
    get_autopilot_enabled, get_autopilot_silent, get_ratio_limits,
    update_autopilot_enabled, update_autopilot_silent, update_base_path,
    load_config, save_config
)
from core_data_extraction import DataExtractor, RaceData, format_time
from core_autopilot import AutopilotManager, Formula, get_vehicle_class, load_vehicle_classes, DEFAULT_A_VALUE

from gui_common import setup_dark_theme, show_error_dialog, show_info_dialog, show_warning_dialog, GTR2Logo, ToggleSwitch, LogWindow, SimpleLogHandler
from gui_advanced_settings import AdvancedSettingsDialog
from gui_pre_run_check import PreRunCheckDialog
from gui_base_path_dialog import BasePathSelectionDialog
from gui_components import AccuracyIndicator
from gui_ratio_panel import RatioPanel
from gui_common_dialogs import ManualEditDialog, ManualLapTimeDialog
from gui_file_monitor import FileMonitorDaemon, SimplifiedLogger

logger = logging.getLogger(__name__)


class RedesignedMainWindow(QMainWindow):
    """Redesigned main window matching the reference image layout exactly"""
    
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
        
        self.min_ratio, self.max_ratio = get_ratio_limits(config_file)
        
        self.log_window = LogWindow(self)
        log_handler = SimpleLogHandler(self.log_window)
        log_handler.setFormatter(logging.Formatter('%(message)s'))
        logging.getLogger().addHandler(log_handler)
        logging.getLogger().setLevel(logging.INFO)
        
        self.simplified_logger = SimplifiedLogger()
        self.class_mapping = load_vehicle_classes()
        
        self.autopilot_manager = AutopilotManager(self.db)
        
        self.autosave_enabled = True
        self.autoratio_enabled = True
        self.autopilot_manager.set_enabled(self.autoratio_enabled)
        
        self.ai_target_settings = {
            "mode": "percentage",
            "percentage": 50,
            "offset_seconds": 0.0,
            "error_margin": 0.0
        }
        
        self.qual_a: float = DEFAULT_A_VALUE
        self.qual_b: float = 70.0
        self.race_a: float = DEFAULT_A_VALUE
        self.race_b: float = 70.0
        
        self.current_track: str = ""
        self.current_vehicle: str = ""
        self.current_vehicle_class: str = ""
        
        self.qual_best_ai = None
        self.qual_worst_ai = None
        self.race_best_ai = None
        self.race_worst_ai = None
        
        self.user_qualifying_sec: float = 0.0
        self.user_best_lap_sec: float = 0.0
        self.last_qual_ratio: Optional[float] = None
        self.last_race_ratio: Optional[float] = None
        
        self.qual_read_ratio: Optional[float] = None
        self.race_read_ratio: Optional[float] = None
        self.original_qual_ratio: Optional[float] = None
        self.original_race_ratio: Optional[float] = None
        
        self.qual_ab_modified = False
        self.race_ab_modified = False
        
        self.advanced_window = None
        
        self.daemon = None
        
        self.aiw_accessible = True
        self.last_aiw_error = None
        
        self.setup_ui()
        
        self.qual_panel.revert_requested.connect(lambda: self.on_revert_ratio("qual"))
        self.race_panel.revert_requested.connect(lambda: self.on_revert_ratio("race"))
        
        if not self.ensure_base_path():
            QMessageBox.critical(self, "No Path Selected",
                "GTR2 installation path is required for the application to work.\n\n"
                "Please run the application again and select the correct path.")
            self.close()
            return
        
        self.load_data()
        self.update_display()
        
        base_path = get_base_path(config_file)
        if base_path:
            self.start_daemon()
        
        self.add_target_indicator()
        
        self.track_label.setText("- No Track Selected -")
        self.qual_panel.update_ratio(None)
        self.race_panel.update_ratio(None)
        self.qual_panel.update_last_read_ratio(None)
        self.race_panel.update_last_read_ratio(None)
    
    def open_advanced_to_data_management(self):
        self.open_advanced_settings()
        if self.advanced_window:
            self.advanced_window.tab_widget.setCurrentIndex(0)
    
    def _find_aiw_file(self, track_name: str = None) -> Optional[Path]:
        import re
        base_path = get_base_path(self.config_file)
        if not base_path:
            logger.error("No base path configured")
            return None
        
        track_name = track_name or self.current_track
        if not track_name:
            logger.error("No track selected")
            return None
        
        locations_candidates = [
            base_path / "GameData" / "Locations",
            base_path / "GAMEDATA" / "Locations",
            base_path / "gamedata" / "locations",
        ]
        
        locations_dir = None
        for candidate in locations_candidates:
            if candidate.exists():
                locations_dir = candidate
                break
        
        if not locations_dir:
            logger.error(f"Locations directory not found. Tried: {locations_candidates}")
            return None
        
        track_lower = track_name.lower()
        for track_dir in locations_dir.iterdir():
            if track_dir.is_dir() and track_dir.name.lower() == track_lower:
                for ext in ["*.AIW", "*.aiw"]:
                    aiw_files = list(track_dir.glob(ext))
                    if aiw_files:
                        logger.debug(f"Found AIW file via folder match: {aiw_files[0]}")
                        return aiw_files[0]
        
        for ext in ["*.AIW", "*.aiw"]:
            for aiw_file in locations_dir.rglob(ext):
                aiw_stem = re.sub(r'^\d+', '', aiw_file.stem.lower())
                if aiw_stem == track_lower:
                    logger.debug(f"Found AIW file via stem match: {aiw_file}")
                    return aiw_file
        
        import re
        for track_dir in locations_dir.iterdir():
            if track_dir.is_dir():
                dir_lower = track_dir.name.lower()
                if re.search(r'\b' + re.escape(track_lower) + r'\b', dir_lower):
                    for ext in ["*.AIW", "*.aiw"]:
                        aiw_files = list(track_dir.glob(ext))
                        if aiw_files:
                            logger.debug(f"Found AIW file via folder word match: {aiw_files[0]}")
                            return aiw_files[0]
        
        logger.warning(f"AIW file not found for track: {track_name}")
        return None

    def _read_aiw_ratios(self, aiw_path: Path) -> tuple:
        qual_ratio = None
        race_ratio = None
        
        try:
            raw = aiw_path.read_bytes()
            content = raw.replace(b"\x00", b"").decode("utf-8", errors="ignore")
            
            waypoint_match = re.search(r'\[Waypoint\](.*?)(?=\[|$)', content, re.DOTALL | re.IGNORECASE)
            if waypoint_match:
                section = waypoint_match.group(1)
                
                qual_match = re.search(r'QualRatio\s*=\s*\(?([\d.eE+-]+)\)?', section, re.IGNORECASE)
                if qual_match:
                    qual_ratio = float(qual_match.group(1))
                    logger.debug(f"Read QualRatio: {qual_ratio}")
                
                race_match = re.search(r'RaceRatio\s*=\s*\(?([\d.eE+-]+)\)?', section, re.IGNORECASE)
                if race_match:
                    race_ratio = float(race_match.group(1))
                    logger.debug(f"Read RaceRatio: {race_ratio}")
            
            return qual_ratio, race_ratio
            
        except Exception as e:
            logger.error(f"Error reading AIW ratios: {e}")
            return None, None
    
    def _ensure_aiw_has_ratios(self, aiw_path: Path) -> bool:
        try:
            raw = aiw_path.read_bytes()
            content = raw.replace(b"\x00", b"").decode("utf-8", errors="ignore")
            
            has_qual = re.search(r'QualRatio\s*=', content, re.IGNORECASE) is not None
            has_race = re.search(r'RaceRatio\s*=', content, re.IGNORECASE) is not None
            
            if has_qual and has_race:
                return True
            
            backup_dir = Path(self.db.db_path).parent / "aiw_backups"
            backup_dir.mkdir(parents=True, exist_ok=True)
            backup_path = backup_dir / f"{aiw_path.stem}_ORIGINAL{aiw_path.suffix}"
            if not backup_path.exists():
                shutil.copy2(aiw_path, backup_path)
                logger.info(f"Created backup before adding ratios: {backup_path}")
            
            waypoint_pattern = re.compile(r'(\[Waypoint\](.*?)(?=\[|$))', re.DOTALL | re.IGNORECASE)
            waypoint_match = waypoint_pattern.search(content)
            
            if not waypoint_match:
                logger.warning(f"Cannot find Waypoint section in {aiw_path.name}")
                return False
            
            waypoint_section = waypoint_match.group(1)
            waypoint_start = waypoint_match.start()
            
            insert_pos = waypoint_start + len("[Waypoint]")
            
            best_adjust_match = re.search(r'BestAdjust\s*=', waypoint_section, re.IGNORECASE)
            if best_adjust_match:
                line_end = waypoint_section.find('\n', best_adjust_match.end())
                if line_end != -1:
                    insert_pos = waypoint_start + line_end + 1
            
            lines_to_insert = []
            if not has_qual:
                lines_to_insert.append("QualRatio = 1.000000")
            if not has_race:
                lines_to_insert.append("RaceRatio = 1.000000")
            
            if lines_to_insert:
                insert_text = "\n" + "\n".join(lines_to_insert)
                new_content = content[:insert_pos] + insert_text + content[insert_pos:]
                aiw_path.write_bytes(new_content.encode("utf-8", errors="ignore"))
                logger.info(f"Added missing ratios to {aiw_path.name}: {lines_to_insert}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error ensuring AIW has ratios: {e}")
            return False
    
    def load_aiw_ratios(self):
        if not self.current_track:
            logger.debug("No track selected, skipping AIW ratio load")
            self.qual_panel.update_ratio(None)
            self.race_panel.update_ratio(None)
            return
        
        aiw_path = self._find_aiw_file()
        
        if not aiw_path or not aiw_path.exists():
            logger.warning(f"Cannot load AIW ratios: AIW file not found for track '{self.current_track}'")
            self.qual_panel.update_ratio(None)
            self.race_panel.update_ratio(None)
            return
        
        self._ensure_aiw_has_ratios(aiw_path)
        
        qual_ratio, race_ratio = self._read_aiw_ratios(aiw_path)
        
        if qual_ratio is not None:
            self.last_qual_ratio = qual_ratio
            self.qual_panel.update_ratio(qual_ratio)
            if self.original_qual_ratio is None:
                self.original_qual_ratio = qual_ratio
        else:
            self.qual_panel.update_ratio(None)
        
        if race_ratio is not None:
            self.last_race_ratio = race_ratio
            self.race_panel.update_ratio(race_ratio)
            if self.original_race_ratio is None:
                self.original_race_ratio = race_ratio
        else:
            self.race_panel.update_ratio(None)
        
        self.qual_read_ratio = qual_ratio
        self.race_read_ratio = race_ratio
        self.qual_panel.update_last_read_ratio(qual_ratio)
        self.race_panel.update_last_read_ratio(race_ratio)
        
        logger.info(f"Loaded AIW ratios: Qual={self.last_qual_ratio}, Race={self.last_race_ratio}")
    
    def add_target_indicator(self):
        target_widget = QWidget()
        target_layout = QHBoxLayout(target_widget)
        target_layout.setContentsMargins(5, 0, 10, 0)
        target_layout.setSpacing(8)
        
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
        self.open_advanced_settings()
        if self.advanced_window:
            self.advanced_window.tab_widget.setCurrentIndex(1)
    
    def update_target_display(self):
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
    
    def calculate_ratio_from_user_time(self, session_type: str, user_time: float) -> Optional[float]:
        if session_type == "qual":
            b = self.qual_b
        else:
            b = self.race_b
        
        a = DEFAULT_A_VALUE
        denominator = user_time - b
        
        if denominator <= 0:
            return None
        
        ratio = a / denominator
        return ratio

    def ensure_base_path(self) -> bool:
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
        
        top_section = QWidget()
        top_layout = QVBoxLayout(top_section)
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setSpacing(20)
        
        header_layout = QHBoxLayout()
        logo_label = GTR2Logo()
        header_layout.addWidget(logo_label)
        header_layout.addStretch()
        
        track_container = QWidget()
        track_container.setStyleSheet("""
            QWidget {
                background-color: #2b2b2b;
                border-radius: 8px;
                padding: 5px 10px;
            }
        """)
        track_container_layout = QHBoxLayout(track_container)
        track_container_layout.setContentsMargins(10, 5, 10, 5)
        
        track_label_title = QLabel("Track:")
        track_label_title.setStyleSheet("font-size: 14px; color: #888;")
        track_container_layout.addWidget(track_label_title)
        
        self.track_label = QLabel("- No Track Selected -")
        self.track_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #FFA500;")
        track_container_layout.addWidget(self.track_label)
        
        self.select_track_btn = QPushButton("Configure")
        self.select_track_btn.setStyleSheet("""
            QPushButton {
                background-color: #9C27B0;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 4px 12px;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #7B1FA2;
            }
        """)
        self.select_track_btn.clicked.connect(self.open_advanced_to_data_management)
        track_container_layout.addWidget(self.select_track_btn)
        
        header_layout.addWidget(track_container)
        header_layout.addStretch()
        header_layout.addSpacing(80)
        top_layout.addLayout(header_layout)
        
        car_class_container = QWidget()
        car_class_container.setStyleSheet("""
            QWidget {
                background-color: #2b2b2b;
                border-radius: 8px;
                padding: 5px 10px;
            }
        """)
        car_class_layout = QHBoxLayout(car_class_container)
        car_class_layout.setContentsMargins(10, 5, 10, 5)

        car_class_label_title = QLabel("Car Class:")
        car_class_label_title.setStyleSheet("font-size: 13px; color: #888;")
        car_class_layout.addWidget(car_class_label_title)

        self.car_class_label = QLabel("-")
        self.car_class_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #4CAF50;")
        car_class_layout.addWidget(self.car_class_label)
        car_class_layout.addStretch()

        top_layout.addWidget(car_class_container)
        
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
        
        bottom_section = QWidget()
        bottom_layout = QVBoxLayout(bottom_section)
        bottom_layout.setContentsMargins(0, 0, 0, 0)
        bottom_layout.setSpacing(20)
        
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
        return self._find_aiw_file()
    
    def check_aiw_accessible(self, session_type: str) -> bool:
        aiw_path = self._get_aiw_path()
        if not aiw_path or not aiw_path.exists():
            self.aiw_accessible = False
            self.show_aiw_error_and_accessible(f"update {session_type.upper()} ratio", 
                f"AIW file for track '{self.current_track}' not found in GameData/Locations/")
            return False
        self.aiw_accessible = True
        return True
    
    def show_aiw_error_and_accessible(self, operation: str, error_detail: str = None):
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
            self._ensure_aiw_has_ratios(aiw_path)
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
            self._ensure_aiw_has_ratios(aiw_path)
            if self.autopilot_manager.engine._update_aiw_ratio(aiw_path, "RaceRatio", old_ratio):
                self.last_race_ratio = old_ratio
                self.race_panel.update_ratio(old_ratio)
                self.race_panel.revert_success()
                self.statusBar().showMessage(f"RaceRatio reverted to {old_ratio:.6f}", 3000)
                logger.info(f"Reverted RaceRatio to {old_ratio:.6f}")
            else:
                show_error_dialog(self, "Revert Failed", "Failed to revert RaceRatio in AIW file.")
    
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
        
        self._ensure_aiw_has_ratios(aiw_path)
        
        final_ratio = new_ratio
        if self.ai_target_settings.get("mode") != "percentage" or self.ai_target_settings.get("percentage") != 50:
            if self.qual_best_ai and self.qual_worst_ai:
                target_time = self.calculate_target_lap_time(self.qual_best_ai, self.qual_worst_ai)
                if session_type == "qual":
                    target_ratio = self.calculate_ratio_from_user_time(session_type, target_time)
                else:
                    target_ratio = self.calculate_ratio_from_user_time(session_type, target_time)
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
    
    def open_advanced_settings(self):
        if self.advanced_window is None:
            self.advanced_window = AdvancedSettingsDialog(self, self.db, self.log_window)
            self.advanced_window.data_updated.connect(self.on_data_updated)
            self.advanced_window.formula_updated.connect(self.on_formula_updated)
            self.advanced_window.ratio_saved.connect(self.on_ratio_saved_from_advanced)
            self.advanced_window.lap_time_updated.connect(self.on_lap_time_updated_from_advanced)
            self.advanced_window.track_selected.connect(self.on_track_selected_from_advanced)
            self.data_refresh_signal.connect(self.advanced_window.on_parent_data_refresh)
        
        if hasattr(self.advanced_window, 'curve_graph'):
            self.advanced_window.curve_graph.update_current_info(
                track=self.current_track, vehicle=self.current_vehicle,
                qual_time=self.user_qualifying_sec if self.user_qualifying_sec > 0 else None,
                race_time=self.user_best_lap_sec if self.user_best_lap_sec > 0 else None,
                qual_ratio=self.last_qual_ratio, race_ratio=self.last_race_ratio)
            self.advanced_window.curve_graph.full_refresh()
        
        self.advanced_window.show()
        self.advanced_window.raise_()
        self.advanced_window.activateWindow()
    
    def on_track_selected_from_advanced(self, track_name: str):
        if track_name and track_name != self.current_track:
            self.current_track = track_name
            self.track_label.setText(track_name)
            self.setWindowTitle(f"GTR2 Dynamic AI - {track_name}")
            
            self.qual_best_ai, self.qual_worst_ai = self._get_ai_times_for_track(track_name, "qual")
            self.race_best_ai, self.race_worst_ai = self._get_ai_times_for_track(track_name, "race")
            
            self._update_formulas_from_autopilot()
            
            self.update_display()
            
            if self.current_track and self.current_vehicle_class:
                self.update_formula_accuracy("qual")
                self.update_formula_accuracy("race")
            
            self.load_aiw_ratios()
            
            if self.advanced_window and self.advanced_window.isVisible():
                self.advanced_window.refresh_display()
            
            self.data_refresh_signal.emit()
            
            logger.info(f"Track changed to: {track_name}")
    
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
    
    def on_ratio_saved_from_advanced(self, session_type: str, ratio: float):
        if not self.check_aiw_accessible(session_type):
            return
        
        aiw_path = self._get_aiw_path()
        if not aiw_path:
            if self.show_aiw_error_and_accessible("save ratio"):
                return
            show_warning_dialog(self, "AIW Not Found", "Could not find AIW file to save ratio.")
            return
        
        self._ensure_aiw_has_ratios(aiw_path)
        
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
            self.car_class_label.setText(self.current_vehicle_class)
        
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
        
        if self.autoratio_enabled and race_data.aiw_path:
            logger.info("[AUTORATIO] Running Autoratio with direct user lap time calculation")
            
            self._ensure_aiw_has_ratios(race_data.aiw_path)
            
            if self.user_qualifying_sec > 0:
                new_qual_ratio = self.calculate_ratio_from_user_time("qual", self.user_qualifying_sec)
                if new_qual_ratio and abs(new_qual_ratio - self.last_qual_ratio) > 0.000001:
                    if self._validate_ratio(new_qual_ratio, "QualRatio"):
                        if self.autopilot_manager.engine._update_aiw_ratio(race_data.aiw_path, "QualRatio", new_qual_ratio):
                            self.last_qual_ratio = new_qual_ratio
                            self.qual_panel.update_ratio(new_qual_ratio)
                            logger.info(f"[AUTORATIO] Updated QualRatio to {new_qual_ratio:.6f} based on user time {self.user_qualifying_sec:.3f}s")
            
            if self.user_best_lap_sec > 0:
                new_race_ratio = self.calculate_ratio_from_user_time("race", self.user_best_lap_sec)
                if new_race_ratio and abs(new_race_ratio - self.last_race_ratio) > 0.000001:
                    if self._validate_ratio(new_race_ratio, "RaceRatio"):
                        if self.autopilot_manager.engine._update_aiw_ratio(race_data.aiw_path, "RaceRatio", new_race_ratio):
                            self.last_race_ratio = new_race_ratio
                            self.race_panel.update_ratio(new_race_ratio)
                            logger.info(f"[AUTORATIO] Updated RaceRatio to {new_race_ratio:.6f} based on user time {self.user_best_lap_sec:.3f}s")
        
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
            pass
        elif self.current_track and self.current_track not in self.all_tracks:
            self.current_track = ""
            self.track_label.setText("- No Track Selected -")
            self.setWindowTitle("GTR2 Dynamic AI")
            
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
