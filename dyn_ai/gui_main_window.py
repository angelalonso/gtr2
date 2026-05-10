#!/usr/bin/env python3
"""
Main window for Live AI Tuner
Redesigned GUI matching the reference image layout
"""

import sys
import threading
import logging
import sqlite3
import subprocess
from pathlib import Path
from typing import List, Tuple, Optional, Dict, Any
from datetime import datetime

from PyQt5.QtWidgets import (
    QMainWindow, QMessageBox, QDialog, QFileDialog
)
from PyQt5.QtCore import Qt, pyqtSignal

from core_database import CurveDatabase
from core_formula import DEFAULT_A_VALUE
from core_config import (
    get_config_with_defaults, get_results_file_path, get_poll_interval,
    get_db_path, create_default_config_if_missing, get_base_path,
    get_ratio_limits, update_base_path, get_nr_last_user_laptimes
)
from core_data_extraction import RaceData
from core_autopilot import AutopilotManager, get_vehicle_class, load_vehicle_classes
from core_user_laptimes import UserLapTimesManager

from gui_common import setup_dark_theme, show_error_dialog, show_warning_dialog, LogWindow, SimpleLogHandler
from gui_advanced_settings import AdvancedSettingsDialog
from gui_pre_run_check import PreRunCheckDialog
from gui_base_path_dialog import BasePathSelectionDialog
from gui_file_monitor import FileMonitorDaemon, SimplifiedLogger
from gui_main_window_components import clamp_ratio, show_clamp_warning, AIWFileManager, TargetIndicator
from gui_ai_time_manager import AITimeManager
from gui_main_window_ui import MainWindowUI
from gui_target_manager import TargetManager, RatioCalculator

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
        self.db_path = db_path
        
        self.min_ratio, self.max_ratio = get_ratio_limits(config_file)
        
        self.log_window = LogWindow(self)
        log_handler = SimpleLogHandler(self.log_window)
        log_handler.setFormatter(logging.Formatter('%(message)s'))
        logging.getLogger().addHandler(log_handler)
        logging.getLogger().setLevel(logging.INFO)
        
        self.simplified_logger = SimplifiedLogger()
        
        # Load vehicle classes
        from gui_common import get_data_file_path
        vehicle_classes_path = get_data_file_path("vehicle_classes.json")
        self.class_mapping = load_vehicle_classes(vehicle_classes_path)
        
        self.autopilot_manager = AutopilotManager(self.db)
        
        # Initialize user laptimes manager
        max_laptimes = get_nr_last_user_laptimes(config_file)
        self.user_laptimes_manager = UserLapTimesManager(db_path, max_laptimes)
        self.autopilot_manager.set_user_laptimes_manager(self.user_laptimes_manager)
        
        # Initialize managers
        self.aiw_manager = AIWFileManager(config_file, db_path)
        self.ai_time_manager = AITimeManager(self.db, self.autopilot_manager)
        
        self.autosave_enabled = True
        self.autoratio_enabled = True
        self.autopilot_manager.set_enabled(self.autoratio_enabled)
        
        self.ai_target_settings = {
            "mode": "percentage",
            "percentage": 50,
            "offset_seconds": 0.0,
            "error_margin": 0.0
        }
        self.target_manager = TargetManager(self.ai_target_settings)
        
        self.qual_a: float = DEFAULT_A_VALUE
        self.qual_b: float = 70.0
        self.race_a: float = DEFAULT_A_VALUE
        self.race_b: float = 70.0
        
        self.ratio_calculator = RatioCalculator(self.qual_b, self.race_b)
        
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
        
        # Setup UI
        self.ui = MainWindowUI(self)
        self.ui.setup_ui()
        
        # Connect signals
        self.qual_panel.revert_requested.connect(lambda: self.on_revert_ratio("qual"))
        self.race_panel.revert_requested.connect(lambda: self.on_revert_ratio("race"))
        
        # Add target indicator
        self.target_indicator = TargetIndicator(self, lambda: self.ai_target_settings)
        self.statusBar().addPermanentWidget(self.target_indicator)
        self.update_target_display()
        
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
        
        self.track_label.setText("- No Track Selected -")
        self.qual_panel.update_ratio(None)
        self.race_panel.update_ratio(None)
        self.qual_panel.update_last_read_ratio(None)
        self.race_panel.update_last_read_ratio(None)
    
    def open_advanced_to_data_management(self):
        self.open_advanced_settings()
        if self.advanced_window:
            self.advanced_window.tab_widget.setCurrentIndex(0)
    
    def load_aiw_ratios(self):
        if not self.current_track:
            logger.debug("No track selected, skipping AIW ratio load")
            self.qual_panel.update_ratio(None)
            self.race_panel.update_ratio(None)
            return
        
        aiw_path = self.aiw_manager.find_aiw_file(self.current_track)
        
        if not aiw_path or not aiw_path.exists():
            logger.warning(f"Cannot load AIW ratios: AIW file not found for track '{self.current_track}'")
            self.qual_panel.update_ratio(None)
            self.race_panel.update_ratio(None)
            return
        
        self.aiw_manager.ensure_aiw_has_ratios(aiw_path)
        
        qual_ratio, race_ratio = self.aiw_manager.read_aiw_ratios(aiw_path)
        
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
    
    def update_target_display(self):
        if hasattr(self, 'target_indicator'):
            self.target_indicator.update_display()
    
    def calculate_target_lap_time(self, best_ai: float, worst_ai: float) -> float:
        return self.target_manager.calculate_target_lap_time(best_ai, worst_ai)
    
    def calculate_ratio_from_user_time(self, session_type: str, user_time: float) -> Optional[float]:
        self.ratio_calculator.update_formula_b(session_type, self.qual_b if session_type == "qual" else self.race_b)
        return self.ratio_calculator.calculate_ratio_from_user_time(session_type, user_time)

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
                    return True
                else:
                    return False
        
        path = Path(base_path)
        if (path / "GameData").exists() and (path / "UserData").exists():
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
                    return True
            return False
    
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
    
    def _clamp_ratio(self, ratio: float) -> float:
        return clamp_ratio(ratio, self.min_ratio, self.max_ratio)
    
    def _validate_and_clamp_ratio(self, ratio: float, ratio_name: str) -> tuple:
        if ratio < self.min_ratio:
            clamped = self.min_ratio
            show_clamp_warning(self, ratio_name, ratio, clamped, self.min_ratio, self.max_ratio)
            return clamped, True, f"{ratio_name} was below minimum ({self.min_ratio}). Clamped to {clamped}."
        elif ratio > self.max_ratio:
            clamped = self.max_ratio
            show_clamp_warning(self, ratio_name, ratio, clamped, self.min_ratio, self.max_ratio)
            return clamped, True, f"{ratio_name} was above maximum ({self.max_ratio}). Clamped to {clamped}."
        return ratio, False, None
    
    def _get_aiw_path(self) -> Optional[Path]:
        return self.aiw_manager.find_aiw_file(self.current_track)
    
    def check_aiw_accessible(self, session_type: str) -> bool:
        return self.aiw_manager.check_aiw_accessible(self, self.current_track, session_type)
    
    def on_revert_ratio(self, session_type: str):
        if not self.check_aiw_accessible(session_type):
            return
        
        if session_type == "qual":
            old_ratio = self.qual_panel.previous_ratio
            if old_ratio is None:
                return
            aiw_path = self._get_aiw_path()
            if not aiw_path:
                show_warning_dialog(self, "AIW Not Found", "Could not find AIW file to revert.")
                return
            self.aiw_manager.ensure_aiw_has_ratios(aiw_path)
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
                show_warning_dialog(self, "AIW Not Found", "Could not find AIW file to revert.")
                return
            self.aiw_manager.ensure_aiw_has_ratios(aiw_path)
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
        clamped_ratio, was_clamped, warning_msg = self._validate_and_clamp_ratio(new_ratio, ratio_name)
        
        if not self.check_aiw_accessible(session_type):
            return
        
        aiw_path = self._get_aiw_path()
        if not aiw_path or not aiw_path.exists():
            aiw_path_str, _ = QFileDialog.getOpenFileName(
                self, f"Select AIW file for {self.current_track}",
                str(Path.cwd()), "AIW Files (*.AIW *.aiw)")
            if aiw_path_str:
                aiw_path = Path(aiw_path_str)
            else:
                show_warning_dialog(self, "AIW Not Found", f"Could not find AIW file.")
                return
        
        self.aiw_manager.ensure_aiw_has_ratios(aiw_path)
        
        final_ratio = clamped_ratio
        if self.ai_target_settings.get("mode") != "percentage" or self.ai_target_settings.get("percentage") != 50:
            if self.qual_best_ai and self.qual_worst_ai:
                target_time = self.calculate_target_lap_time(self.qual_best_ai, self.qual_worst_ai)
                target_ratio = self.calculate_ratio_from_user_time(session_type, target_time)
                if target_ratio and abs(target_ratio - new_ratio) > 0.0001:
                    reply = QMessageBox.question(self, "Apply AI Target?",
                        f"You have AI Target settings active.\n\n"
                        f"Manual ratio: {new_ratio:.6f}\n"
                        f"AI Target ratio: {target_ratio:.6f}\n\n"
                        f"Which ratio would you like to use?",
                        QMessageBox.Yes | QMessageBox.No)
                    if reply == QMessageBox.Yes:
                        target_clamped, target_was_clamped, target_warning = self._validate_and_clamp_ratio(target_ratio, ratio_name)
                        final_ratio = target_clamped
        
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
        
        qual_b_list = [self.qual_b]
        race_b_list = [self.race_b]
        new_qual_b, new_race_b = self.ai_time_manager.update_formulas_from_autopilot(
            self.current_track, self.current_vehicle_class, qual_b_list, race_b_list)
        self.qual_b = new_qual_b
        self.race_b = new_race_b
    
    def _update_formula_from_new_data(self, race_data: RaceData, session_type: str) -> bool:
        new_b = self.ai_time_manager.update_formula_from_new_data(
            self.current_track, self.current_vehicle_class, race_data, session_type)
        if new_b:
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
            median_qual = self.user_laptimes_manager.get_median_laptime_for_combo(
                self.current_track, self.current_vehicle_class, "qual"
            ) if hasattr(self, 'user_laptimes_manager') else None
            median_race = self.user_laptimes_manager.get_median_laptime_for_combo(
                self.current_track, self.current_vehicle_class, "race"
            ) if hasattr(self, 'user_laptimes_manager') else None
            
            self.advanced_window.curve_graph.update_current_info(
                track=self.current_track, vehicle=self.current_vehicle,
                qual_time=self.user_qualifying_sec if self.user_qualifying_sec > 0 else None,
                race_time=self.user_best_lap_sec if self.user_best_lap_sec > 0 else None,
                qual_ratio=self.last_qual_ratio, race_ratio=self.last_race_ratio,
                median_qual_time=median_qual, median_race_time=median_race)
            self.advanced_window.curve_graph.full_refresh()
        
        self.advanced_window.show()
        self.advanced_window.raise_()
        self.advanced_window.activateWindow()
    
    def on_track_selected_from_advanced(self, track_name: str):
        if track_name and track_name != self.current_track:
            self.current_track = track_name
            self.track_label.setText(track_name)
            self.setWindowTitle(f"GTR2 Dynamic AI - {track_name}")
            
            self.qual_best_ai, self.qual_worst_ai = self.ai_time_manager.get_ai_times_for_track(track_name, "qual")
            self.race_best_ai, self.race_worst_ai = self.ai_time_manager.get_ai_times_for_track(track_name, "race")
            
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
            show_warning_dialog(self, "AIW Not Found", "Could not find AIW file to save ratio.")
            return
        
        self.aiw_manager.ensure_aiw_has_ratios(aiw_path)
        
        ratio_name = "QualRatio" if session_type == "qual" else "RaceRatio"
        clamped_ratio, was_clamped, warning_msg = self._validate_and_clamp_ratio(ratio, ratio_name)
        
        if self.autopilot_manager.engine._update_aiw_ratio(aiw_path, ratio_name, clamped_ratio):
            if session_type == "qual":
                self.last_qual_ratio = clamped_ratio
                self.qual_panel.update_ratio(clamped_ratio)
            else:
                self.last_race_ratio = clamped_ratio
                self.race_panel.update_ratio(clamped_ratio)
            logger.info(f"Saved ratio from Advanced dialog: {ratio_name}={clamped_ratio:.6f}")
    
    def on_lap_time_updated_from_advanced(self, session_type: str, lap_time: float):
        if session_type == "qual":
            self.user_qualifying_sec = lap_time
            self.qual_panel.update_user_time(lap_time)
            if hasattr(self, 'current_track') and hasattr(self, 'current_vehicle_class'):
                self.user_laptimes_manager.add_laptime(
                    self.current_track, self.current_vehicle_class, "qual",
                    lap_time, self.last_qual_ratio
                )
                median_qual = self.user_laptimes_manager.get_median_laptime_for_combo(
                    self.current_track, self.current_vehicle_class, "qual"
                )
                if median_qual and self.advanced_window and hasattr(self.advanced_window, 'qual_panel'):
                    self.advanced_window.qual_panel.update_median_time(median_qual)
        else:
            self.user_best_lap_sec = lap_time
            self.race_panel.update_user_time(lap_time)
            if hasattr(self, 'current_track') and hasattr(self, 'current_vehicle_class'):
                self.user_laptimes_manager.add_laptime(
                    self.current_track, self.current_vehicle_class, "race",
                    lap_time, self.last_race_ratio
                )
                median_race = self.user_laptimes_manager.get_median_laptime_for_combo(
                    self.current_track, self.current_vehicle_class, "race"
                )
                if median_race and self.advanced_window and hasattr(self.advanced_window, 'race_panel'):
                    self.advanced_window.race_panel.update_median_time(median_race)
    
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
            self.aiw_manager.show_aiw_error_and_accessible(self, "process race data", race_data.aiw_error)
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
            logger.info("[AUTORATIO] Running Autoratio with user lap time history")
            
            self.aiw_manager.ensure_aiw_has_ratios(race_data.aiw_path)
            
            if self.user_qualifying_sec > 0:
                self.user_laptimes_manager.add_laptime(
                    self.current_track, self.current_vehicle_class, "qual",
                    self.user_qualifying_sec, self.last_qual_ratio
                )
                median_time = self.user_laptimes_manager.get_median_laptime_for_combo(
                    self.current_track, self.current_vehicle_class, "qual"
                )
                effective_time = median_time if median_time is not None else self.user_qualifying_sec
                if effective_time != self.user_qualifying_sec:
                    logger.info(f"[AUTORATIO] Using median qualifying time {effective_time:.3f}s (from history)")
                
                new_qual_ratio = self.calculate_ratio_from_user_time("qual", effective_time)
                if new_qual_ratio and abs(new_qual_ratio - self.last_qual_ratio) > 0.000001:
                    clamped_ratio = self._clamp_ratio(new_qual_ratio)
                    if clamped_ratio != new_qual_ratio:
                        show_clamp_warning(self, "QualRatio", new_qual_ratio, clamped_ratio, self.min_ratio, self.max_ratio)
                    if self.autopilot_manager.engine._update_aiw_ratio(race_data.aiw_path, "QualRatio", clamped_ratio):
                        self.last_qual_ratio = clamped_ratio
                        self.qual_panel.update_ratio(clamped_ratio)
                        logger.info(f"[AUTORATIO] Updated QualRatio to {clamped_ratio:.6f} based on effective time {effective_time:.3f}s (current={self.user_qualifying_sec:.3f}s)")
            
            if self.user_best_lap_sec > 0:
                self.user_laptimes_manager.add_laptime(
                    self.current_track, self.current_vehicle_class, "race",
                    self.user_best_lap_sec, self.last_race_ratio
                )
                median_time = self.user_laptimes_manager.get_median_laptime_for_combo(
                    self.current_track, self.current_vehicle_class, "race"
                )
                effective_time = median_time if median_time is not None else self.user_best_lap_sec
                if effective_time != self.user_best_lap_sec:
                    logger.info(f"[AUTORATIO] Using median race time {effective_time:.3f}s (from history)")
                
                new_race_ratio = self.calculate_ratio_from_user_time("race", effective_time)
                if new_race_ratio and abs(new_race_ratio - self.last_race_ratio) > 0.000001:
                    clamped_ratio = self._clamp_ratio(new_race_ratio)
                    if clamped_ratio != new_race_ratio:
                        show_clamp_warning(self, "RaceRatio", new_race_ratio, clamped_ratio, self.min_ratio, self.max_ratio)
                    if self.autopilot_manager.engine._update_aiw_ratio(race_data.aiw_path, "RaceRatio", clamped_ratio):
                        self.last_race_ratio = clamped_ratio
                        self.race_panel.update_ratio(clamped_ratio)
                        logger.info(f"[AUTORATIO] Updated RaceRatio to {clamped_ratio:.6f} based on effective time {effective_time:.3f}s (current={self.user_best_lap_sec:.3f}s)")
        
        self.autopilot_manager.reload_formulas()
        self._update_formulas_from_autopilot()
        self.update_display()
        
        if self.current_track and self.current_vehicle_class:
            self.update_formula_accuracy("qual")
            self.update_formula_accuracy("race")
        
        self.data_refresh_signal.emit()
        
        if self.advanced_window and self.advanced_window.isVisible() and hasattr(self.advanced_window, 'curve_graph'):
            qual_history = self.user_laptimes_manager.get_laptimes_for_combo(
                self.current_track, self.current_vehicle_class, "qual"
            ) if hasattr(self, 'user_laptimes_manager') else []
            race_history = self.user_laptimes_manager.get_laptimes_for_combo(
                self.current_track, self.current_vehicle_class, "race"
            ) if hasattr(self, 'user_laptimes_manager') else []
            median_qual = self.user_laptimes_manager.get_median_laptime_for_combo(
                self.current_track, self.current_vehicle_class, "qual"
            ) if hasattr(self, 'user_laptimes_manager') else None
            median_race = self.user_laptimes_manager.get_median_laptime_for_combo(
                self.current_track, self.current_vehicle_class, "race"
            ) if hasattr(self, 'user_laptimes_manager') else None
            
            if median_qual and hasattr(self.advanced_window, 'qual_panel'):
                self.advanced_window.qual_panel.update_median_time(median_qual)
            if median_race and hasattr(self.advanced_window, 'race_panel'):
                self.advanced_window.race_panel.update_median_time(median_race)
            
            self.advanced_window.curve_graph.update_current_info(
                track=self.current_track, vehicle=self.current_vehicle,
                qual_time=self.user_qualifying_sec if self.user_qualifying_sec > 0 else None,
                race_time=self.user_best_lap_sec if self.user_best_lap_sec > 0 else None,
                qual_ratio=self.last_qual_ratio, race_ratio=self.last_race_ratio,
                qual_history=qual_history, race_history=race_history,
                median_qual_time=median_qual, median_race_time=median_race)
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
