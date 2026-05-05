#!/usr/bin/env python3
"""
Advanced Settings Dialog for Live AI Tuner
Provides data management, AI target configuration, backup restore, and logs
"""

import logging
import sys
import re
import shutil
import sqlite3
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List, Tuple

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QWidget, QLabel, QPushButton,
    QGroupBox, QTabWidget, QListWidget, QListWidgetItem, QAbstractItemView, QMessageBox,
    QDialogButtonBox, QFileDialog, QSlider, QSpinBox, QDoubleSpinBox,
    QRadioButton, QTextEdit, QFrame, QCheckBox
)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer

from core_database import CurveDatabase
from core_formula import fit_curve, DEFAULT_A_VALUE
from core_config import get_base_path, get_ratio_limits, get_config_with_defaults
from core_autopilot import load_vehicle_classes

from gui_components import AccuracyIndicator
from gui_session_panel import SessionPanel
from gui_curve_graph import CurveGraphWidget
from gui_common_dialogs import ManualLapTimeDialog

logger = logging.getLogger(__name__)


class AdvancedSettingsDialog(QDialog):
    """Advanced settings window with unified tab layout"""
    
    data_updated = pyqtSignal()
    formula_updated = pyqtSignal(str, float, float)
    ratio_saved = pyqtSignal(str, float)
    lap_time_updated = pyqtSignal(str, float)
    track_selected = pyqtSignal(str)
    
    def __init__(self, parent=None, db=None, log_window=None):
        super().__init__(parent)
        self.parent = parent
        self.db = db
        self.log_window = log_window
        self.setWindowTitle("Advanced Settings")
        self.setGeometry(100, 100, 1200, 800)
        self.setMinimumWidth(1000)
        self.setMinimumHeight(700)
        
        self.target_mode = "percentage"
        self.target_percentage = 50
        self.target_offset_seconds = 0.0
        self.ai_error_margin = 0.0
        
        self.qual_panel = None
        self.race_panel = None
        self.curve_graph = None
        self.log_update_timer = None
        
        self.setup_ui()

    def _find_aiw_path_from_config(self) -> Optional[Path]:
        base_path = get_base_path()
        
        if not base_path:
            logger.error("No base path configured in cfg.yml")
            return None
        
        if self.parent and hasattr(self.parent, 'current_track'):
            track_name = self.parent.current_track
        else:
            track_name = getattr(self.parent, 'current_track', None)
        
        if not track_name:
            logger.error("No current track selected")
            return None
        
        locations_dir = base_path / "GameData" / "Locations"
        if not locations_dir.exists():
            logger.error(f"Locations directory not found: {locations_dir}")
            return None
        
        track_lower = track_name.lower()
        for track_dir in locations_dir.iterdir():
            if track_dir.is_dir() and track_dir.name.lower() == track_lower:
                for ext in ["*.AIW", "*.aiw"]:
                    aiw_files = list(track_dir.glob(ext))
                    if aiw_files:
                        return aiw_files[0]
                break
        
        for ext in ["*.AIW", "*.aiw"]:
            for aiw_file in locations_dir.rglob(ext):
                if aiw_file.stem.lower() == track_lower or track_lower in aiw_file.stem.lower():
                    return aiw_file
        
        logger.warning(f"AIW file not found for track: {track_name}")
        return None
    
    def _show_aiw_path_error(self):
        config = get_config_with_defaults()
        base_path = get_base_path()
        
        if self.parent and hasattr(self.parent, 'current_track'):
            track_name = self.parent.current_track
        else:
            track_name = getattr(self.parent, 'current_track', 'Unknown')
        
        error_msg = f"AIW file not found for track: {track_name}\n\n"
        error_msg += f"Base path from cfg.yml: {base_path if base_path else 'NOT SET'}\n"
        
        if base_path:
            locations_dir = base_path / "GameData" / "Locations"
            error_msg += f"Looking in: {locations_dir}\n"
            
            if locations_dir.exists():
                error_msg += f"\nExisting track folders in {locations_dir}:\n"
                for folder in locations_dir.iterdir():
                    if folder.is_dir():
                        error_msg += f"  - {folder.name}\n"
                
                error_msg += f"\nSearching for folders matching '{track_name}':\n"
                track_lower = track_name.lower()
                found = False
                for folder in locations_dir.iterdir():
                    if folder.is_dir() and folder.name.lower() == track_lower:
                        error_msg += f"  - FOUND: {folder.name}\n"
                        found = True
                if not found:
                    error_msg += f"  - No folder named '{track_name}' found\n"
            else:
                error_msg += f"\nLocations directory does NOT exist: {locations_dir}\n"
                error_msg += f"Please verify your GTR2 installation path in cfg.yml\n"
        
        error_msg += f"\nPlease ensure:\n"
        error_msg += f"1. cfg.yml has correct 'base_path' pointing to your GTR2 installation\n"
        error_msg += f"2. The track folder exists in GameData/Locations/\n"
        error_msg += f"3. The AIW file exists in that folder\n"
        
        QMessageBox.critical(self, "AIW File Not Found", error_msg)
    
    def _update_aiw_ratio(self, aiw_path: Path, ratio_name: str, new_ratio: float) -> bool:
        try:
            if not aiw_path.exists():
                logger.error(f"AIW file not found: {aiw_path}")
                return False
            
            try:
                backup_dir = aiw_path.parent / "aiw_backups"
                backup_dir.mkdir(parents=True, exist_ok=True)
                backup_path = backup_dir / f"{aiw_path.stem}_BACKUP{aiw_path.suffix}"
                if not backup_path.exists():
                    shutil.copy2(aiw_path, backup_path)
                    logger.info(f"Created backup: {backup_path}")
            except Exception as e:
                logger.warning(f"Could not create backup: {e}")
            
            raw = aiw_path.read_bytes()
            content = raw.replace(b"\x00", b"").decode("utf-8", errors="ignore")
            
            pattern = rf'({re.escape(ratio_name)}\s*=\s*\(?)\s*[0-9.eE+-]+\s*(\)?)'
            new_content, count = re.subn(
                pattern, 
                lambda m: f"{m.group(1)}{new_ratio:.6f}{m.group(2)}", 
                content, 
                flags=re.IGNORECASE
            )
            
            if count > 0:
                aiw_path.write_bytes(new_content.encode("utf-8", errors="ignore"))
                logger.info(f"Updated {ratio_name} to {new_ratio:.6f} in {aiw_path.name}")
                return True
            else:
                logger.warning(f"Could not find {ratio_name} pattern in {aiw_path.name}")
                return False
                
        except Exception as e:
            logger.error(f"Error updating AIW ratio: {e}")
            return False

    def setup_ui(self):
        layout = QVBoxLayout(self)
        self.tab_widget = QTabWidget()
        
        data_tab = self._create_data_tab()
        self.tab_widget.addTab(data_tab, "Data Management")
        
        target_tab = self._create_target_tab()
        self.tab_widget.addTab(target_tab, "AI Target")
        
        backup_tab = self._create_backup_tab()
        self.tab_widget.addTab(backup_tab, "Backup Restore")
        
        logs_tab = self._create_logs_tab()
        self.tab_widget.addTab(logs_tab, "Logs")
        
        layout.addWidget(self.tab_widget)
        button_box = QDialogButtonBox(QDialogButtonBox.Close)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
        if self.curve_graph:
            self.curve_graph.data_updated.connect(self.on_graph_data_updated)
        
        self.setStyleSheet("""
            QDialog { background-color: #1e1e1e; }
            QTabWidget::pane { background-color: #2b2b2b; border: 1px solid #555; }
            QTabBar::tab { background-color: #3c3c3c; color: white; padding: 8px 12px; margin-right: 2px; }
            QTabBar::tab:selected { background-color: #4CAF50; }
            QTableWidget { background-color: #2b2b2b; color: white; alternate-background-color: #3c3c3c; gridline-color: #555; }
            QHeaderView::section { background-color: #3c3c3c; color: white; padding: 4px; }
            QListWidget { background-color: #2b2b2b; color: white; }
            QGroupBox { color: #4CAF50; }
            QRadioButton { color: white; }
        """)
        self.update_mode_visibility()
        self.tab_widget.currentChanged.connect(self.on_tab_changed)
    
    def _create_data_tab(self) -> QWidget:
        tab = QWidget()
        data_layout = QVBoxLayout(tab)
        data_layout.setContentsMargins(0, 0, 0, 0)
        
        graph_group = QGroupBox("Curve Graph - Track Data")
        graph_layout = QVBoxLayout(graph_group)
        
        self.curve_graph = CurveGraphWidget(self.db, self)
        self.curve_graph.point_selected.connect(self.on_point_selected)
        self.curve_graph.data_updated.connect(self.on_data_updated)
        self.curve_graph.formula_changed.connect(self.on_formula_changed)
        graph_layout.addWidget(self.curve_graph)
        
        data_layout.addWidget(graph_group, stretch=3)
        
        middle_layout = QHBoxLayout()
        middle_layout.setSpacing(15)
        
        self.qual_panel = SessionPanel("qual", "Qualifying Session", self.db, self)
        self.qual_panel.formula_changed.connect(self.on_session_formula_changed)
        self.qual_panel.show_data_toggled.connect(self.on_show_data_toggled)
        self.qual_panel.calculate_ratio.connect(self.on_calculate_and_save_ratio)
        self.qual_panel.auto_fit_requested.connect(self.on_auto_fit_requested)
        self.qual_panel.lap_time_edited.connect(self.on_lap_time_edited)
        middle_layout.addWidget(self.qual_panel)
        
        self.race_panel = SessionPanel("race", "Race Session", self.db, self)
        self.race_panel.formula_changed.connect(self.on_session_formula_changed)
        self.race_panel.show_data_toggled.connect(self.on_show_data_toggled)
        self.race_panel.calculate_ratio.connect(self.on_calculate_and_save_ratio)
        self.race_panel.auto_fit_requested.connect(self.on_auto_fit_requested)
        self.race_panel.lap_time_edited.connect(self.on_lap_time_edited)
        middle_layout.addWidget(self.race_panel)

        middle_widget = QWidget()
        middle_widget.setLayout(middle_layout)
        data_layout.addWidget(middle_widget, stretch=1)
        
        datamgmt_layout = QHBoxLayout()
        datamgmt_layout.addStretch()
        
        self.datamgmt_btn = QPushButton("Open Dyn AI Data Manager")
        self.datamgmt_btn.setStyleSheet("""
            QPushButton {
                background-color: #9C27B0;
                color: white;
                padding: 10px 20px;
                font-size: 13px;
                font-weight: bold;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #7B1FA2;
            }
        """)
        self.datamgmt_btn.clicked.connect(self.open_datamgmt_dyn_ai)
        datamgmt_layout.addWidget(self.datamgmt_btn)
        
        datamgmt_layout.addStretch()
        data_layout.addLayout(datamgmt_layout)
        
        return tab
    
    def _create_target_tab(self) -> QWidget:
        tab = QWidget()
        target_layout = QVBoxLayout(tab)
        
        warning_banner = QLabel("WARNING: AI TARGET FEATURE IS UNDER CONSTRUCTION")
        warning_banner.setStyleSheet("""
            QLabel {
                background-color: #f44336;
                color: white;
                font-weight: bold;
                font-size: 14px;
                padding: 8px;
                border-radius: 5px;
                text-align: center;
            }
        """)
        warning_banner.setAlignment(Qt.AlignCenter)
        target_layout.addWidget(warning_banner)
        target_layout.addSpacing(10)
        
        target_info = QLabel(
            "AI Target Positioning\n\n"
            "This controls where your lap time should fall within the AI's lap time range.\n\n"
            "The AI's best and worst lap times create a range. You choose where you want to be.\n\n"
            "These settings will be applied to BOTH Qualifying and Race sessions."
        )
        target_info.setStyleSheet("color: #FFA500; background-color: #2b2b2b; padding: 10px; border-radius: 5px;")
        target_info.setWordWrap(True)
        target_layout.addWidget(target_info)
        target_layout.addSpacing(10)
        
        mode_group = QGroupBox("Target Mode")
        mode_layout = QVBoxLayout(mode_group)
        self.percentage_radio = QRadioButton("Percentage within AI range (Recommended)")
        self.percentage_radio.setChecked(True)
        self.percentage_radio.toggled.connect(self.on_target_mode_changed)
        mode_layout.addWidget(self.percentage_radio)
        pct_desc = QLabel("  0 percent = match fastest AI, 50 percent = middle, 100 percent = match slowest AI")
        pct_desc.setStyleSheet("color: #888; font-size: 10px; margin-left: 20px;")
        pct_desc.setWordWrap(True)
        mode_layout.addWidget(pct_desc)
        mode_layout.addSpacing(5)
        self.faster_radio = QRadioButton("Fixed seconds from fastest AI")
        self.faster_radio.toggled.connect(self.on_target_mode_changed)
        mode_layout.addWidget(self.faster_radio)
        self.slower_radio = QRadioButton("Fixed seconds from slowest AI")
        self.slower_radio.toggled.connect(self.on_target_mode_changed)
        mode_layout.addWidget(self.slower_radio)
        target_layout.addWidget(mode_group)
        target_layout.addSpacing(10)
        
        percent_group = QGroupBox("Percentage Setting")
        percent_layout = QVBoxLayout(percent_group)
        percent_slider_layout = QHBoxLayout()
        percent_slider_layout.addWidget(QLabel("Position in AI range:"))
        self.target_percent_slider = QSlider(Qt.Horizontal)
        self.target_percent_slider.setRange(0, 100)
        self.target_percent_slider.setValue(50)
        self.target_percent_slider.setTickPosition(QSlider.TicksBelow)
        self.target_percent_slider.setTickInterval(10)
        self.target_percent_slider.valueChanged.connect(self.on_percent_changed)
        percent_slider_layout.addWidget(self.target_percent_slider)
        self.target_percent_spin = QSpinBox()
        self.target_percent_spin.setRange(0, 100)
        self.target_percent_spin.setValue(50)
        self.target_percent_spin.setSuffix("%")
        self.target_percent_spin.valueChanged.connect(self.on_percent_spin_changed)
        percent_slider_layout.addWidget(self.target_percent_spin)
        percent_layout.addLayout(percent_slider_layout)
        self.percent_description = QLabel("You will be exactly in the MIDDLE of the AI range")
        self.percent_description.setStyleSheet("color: #4CAF50; font-weight: bold;")
        percent_layout.addWidget(self.percent_description)
        target_layout.addWidget(percent_group)
        
        absolute_group = QGroupBox("Fixed Offset Setting")
        absolute_layout = QVBoxLayout(absolute_group)
        offset_layout = QHBoxLayout()
        offset_layout.addWidget(QLabel("Offset:"))
        self.target_offset_spin = QDoubleSpinBox()
        self.target_offset_spin.setRange(-10.0, 10.0)
        self.target_offset_spin.setDecimals(2)
        self.target_offset_spin.setSingleStep(0.1)
        self.target_offset_spin.setValue(0.0)
        self.target_offset_spin.setSuffix(" seconds")
        self.target_offset_spin.valueChanged.connect(self.on_offset_changed)
        offset_layout.addWidget(self.target_offset_spin)
        offset_layout.addStretch()
        absolute_layout.addLayout(offset_layout)
        self.offset_description = QLabel("You will be 0.00 seconds from the reference AI time")
        self.offset_description.setStyleSheet("color: #4CAF50; font-weight: bold;")
        absolute_layout.addWidget(self.offset_description)
        target_layout.addWidget(absolute_group)
        target_layout.addSpacing(10)
        
        error_group = QGroupBox("AI Error Margin (Makes AI Slower)")
        error_layout = QVBoxLayout(error_group)
        error_slider_layout = QHBoxLayout()
        error_slider_layout.addWidget(QLabel("Extra time:"))
        self.error_margin_slider = QSlider(Qt.Horizontal)
        self.error_margin_slider.setRange(0, 500)
        self.error_margin_slider.setValue(0)
        self.error_margin_slider.setTickPosition(QSlider.TicksBelow)
        self.error_margin_slider.setTickInterval(50)
        self.error_margin_slider.valueChanged.connect(self.on_error_margin_changed)
        error_slider_layout.addWidget(self.error_margin_slider)
        self.error_margin_spin = QDoubleSpinBox()
        self.error_margin_spin.setRange(0, 5.0)
        self.error_margin_spin.setDecimals(2)
        self.error_margin_spin.setSingleStep(0.1)
        self.error_margin_spin.setValue(0.0)
        self.error_margin_spin.setSuffix(" seconds")
        self.error_margin_spin.valueChanged.connect(self.on_error_margin_spin_changed)
        error_slider_layout.addWidget(self.error_margin_spin)
        error_layout.addLayout(error_slider_layout)
        target_layout.addWidget(error_group)
        target_layout.addSpacing(10)
        
        apply_target_btn = QPushButton("Apply Target Settings")
        apply_target_btn.setStyleSheet("background-color: #FF9800;")
        apply_target_btn.clicked.connect(self.apply_target_settings)
        target_layout.addWidget(apply_target_btn)
        
        target_layout.addStretch()
        
        return tab
    
    def _create_backup_tab(self) -> QWidget:
        tab = QWidget()
        backup_layout = QVBoxLayout(tab)
        
        backup_info = QLabel(
            "AIW Backup Restore\n\n"
            "When Autoratio modifies an AIW file, it creates a backup first.\n"
            "Use this section to restore original AIW files.\n\n"
            "Note: Restoring will undo any Autoratio changes made to that track."
        )
        backup_info.setStyleSheet("color: #FFA500; background-color: #2b2b2b; padding: 10px; border-radius: 5px;")
        backup_info.setWordWrap(True)
        backup_layout.addWidget(backup_info)
        backup_layout.addSpacing(10)
        backup_layout.addWidget(QLabel("Available Backups:"))
        
        self.backup_list = QListWidget()
        self.backup_list.setSelectionMode(QAbstractItemView.ExtendedSelection)
        backup_layout.addWidget(self.backup_list)
        
        backup_btn_layout = QHBoxLayout()
        refresh_backups_btn = QPushButton("Refresh List")
        refresh_backups_btn.clicked.connect(self.refresh_backup_list)
        backup_btn_layout.addWidget(refresh_backups_btn)
        restore_selected_btn = QPushButton("Restore Selected")
        restore_selected_btn.setStyleSheet("background-color: #FF9800;")
        restore_selected_btn.clicked.connect(self.restore_selected_backups)
        backup_btn_layout.addWidget(restore_selected_btn)
        restore_all_btn = QPushButton("Restore All")
        restore_all_btn.setStyleSheet("background-color: #f44336;")
        restore_all_btn.clicked.connect(self.restore_all_backups)
        backup_btn_layout.addWidget(restore_all_btn)
        backup_btn_layout.addStretch()
        backup_layout.addLayout(backup_btn_layout)
        backup_layout.addStretch()
        
        return tab
    
    def _create_logs_tab(self) -> QWidget:
        tab = QWidget()
        logs_layout = QVBoxLayout(tab)
        
        if self.log_window:
            logs_layout.addWidget(QLabel("Application Logs:"))
            
            # Create a container widget for the log display to handle proper resizing
            log_container = QWidget()
            log_container_layout = QVBoxLayout(log_container)
            log_container_layout.setContentsMargins(0, 0, 0, 0)
            
            self.log_display = QTextEdit()
            self.log_display.setReadOnly(True)
            self.log_display.setFontFamily("Courier New")
            self.log_display.setStyleSheet("""
                QTextEdit { 
                    background-color: #1e1e1e; 
                    color: #d4d4d4; 
                    font-size: 10px;
                    font-family: monospace;
                }
            """)
            log_container_layout.addWidget(self.log_display)
            logs_layout.addWidget(log_container, stretch=1)
            
            # Connect to the log window's text change signal if available
            if hasattr(self.log_window, 'log_text'):
                self.log_window.log_text.document().contentsChange.connect(self.sync_log_display)
            
            # Start a timer to periodically update the log display
            self.log_update_timer = QTimer()
            self.log_update_timer.timeout.connect(self.sync_log_display)
            self.log_update_timer.start(500)  # Update every 500ms
            
            log_btn_layout = QHBoxLayout()
            clear_log_btn = QPushButton("Clear Log")
            clear_log_btn.clicked.connect(self.clear_log_display)
            log_btn_layout.addWidget(clear_log_btn)
            log_btn_layout.addStretch()
            logs_layout.addLayout(log_btn_layout)
        
        return tab
    
    def open_datamgmt_dyn_ai(self):
        script_dir = Path(__file__).parent
        exe_path = script_dir / "datamgmt_dyn_ai.exe"
        py_path = script_dir / "dyn_ai_data_manager.py"
        
        try:
            if exe_path.exists():
                subprocess.Popen([str(exe_path)], shell=False)
                logger.info(f"Started datamgmt_dyn_ai.exe")
            elif py_path.exists():
                python_exe = sys.executable
                subprocess.Popen([python_exe, str(py_path)], shell=False)
                logger.info(f"Started dyn_ai_data_manager.py with {python_exe}")
            else:
                QMessageBox.warning(self, "File Not Found", 
                    "Data Manager not found in the application directory.\n\n"
                    f"Expected locations:\n{exe_path}\n{py_path}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to start Dyn AI Data Manager:\n{str(e)}")
            logger.error(f"Failed to start datamgmt_dyn_ai: {e}")
    
    def on_parent_data_refresh(self):
        """Called when parent window signals that data has been refreshed"""
        logger.debug("AdvancedSettingsDialog: Received data refresh signal from parent")
        self.refresh_display()
    
    def on_graph_data_updated(self):
        if self.curve_graph and self.curve_graph.current_track:
            current_track = self.curve_graph.current_track
            self.track_selected.emit(current_track)
    
    def on_tab_changed(self, index):
        if self.tab_widget.tabText(index) == "Backup Restore":
            self.refresh_backup_list()
        elif self.tab_widget.tabText(index) == "Logs":
            # Force a refresh of the logs when switching to the logs tab
            self.sync_log_display()
    
    def scan_aiw_backups(self):
        backups = []
        seen_tracks = set()
        backup_dirs = []
        
        if self.db:
            backup_dirs.append(Path(self.db.db_path).parent / "aiw_backups")
        backup_dirs.append(Path.cwd() / "aiw_backups")
        
        for backup_dir in backup_dirs:
            if not backup_dir.exists():
                continue
            for backup_file in backup_dir.glob("*_ORIGINAL.AIW"):
                original_name = backup_file.name.replace("_ORIGINAL.AIW", ".AIW")
                track_name = original_name.replace(".AIW", "")
                
                unique_key = f"{track_name}_{original_name}"
                
                if unique_key not in seen_tracks:
                    seen_tracks.add(unique_key)
                    backups.append({
                        "track": track_name,
                        "original_file": original_name,
                        "backup_path": backup_file,
                        "backup_time": backup_file.stat().st_mtime if backup_file.exists() else 0,
                        "backup_dir": str(backup_dir)
                    })
        
        return sorted(backups, key=lambda x: x.get("track", ""))
    
    def refresh_backup_list(self):
        self.backup_list.clear()
        backups = self.scan_aiw_backups()
        
        if not backups:
            item = QListWidgetItem("No backups found")
            item.setFlags(Qt.NoItemFlags)
            self.backup_list.addItem(item)
            return
        
        for backup in backups:
            time_str = datetime.fromtimestamp(backup["backup_time"]).strftime("%Y-%m-%d %H:%M:%S")
            item = QListWidgetItem(f"{backup['track']} - {backup['original_file']} (backup: {time_str})")
            item.setData(Qt.UserRole, backup)
            self.backup_list.addItem(item)

    def restore_aiw_backup(self, backup_info):
        try:
            backup_path = backup_info["backup_path"]
            original_name = backup_info["original_file"]
            track_name = backup_info["track"]
            restore_path = None
            
            base_path = get_base_path()
            
            if base_path:
                locations_dir = base_path / "GameData" / "Locations"
                if locations_dir.exists():
                    track_lower = track_name.lower()
                    for track_dir in locations_dir.iterdir():
                        if track_dir.is_dir() and track_dir.name.lower() == track_lower:
                            aiw_path = track_dir / original_name
                            if aiw_path.exists():
                                restore_path = aiw_path
                                break
                    
                    if not restore_path:
                        for ext in ["*.AIW", "*.aiw"]:
                            for aiw_file in locations_dir.rglob(ext):
                                if aiw_file.name.lower() == original_name.lower():
                                    restore_path = aiw_file
                                    break
            
            if not restore_path:
                restore_path_str, _ = QFileDialog.getSaveFileName(
                    self, "Save Restored AIW As", 
                    str(backup_path.parent / original_name), 
                    "AIW Files (*.AIW)"
                )
                if restore_path_str:
                    restore_path = Path(restore_path_str)
                else:
                    return False
            
            shutil.copy2(backup_path, restore_path)
            logger.info(f"Restored backup to {restore_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error restoring backup: {e}")
            return False
    
    def restore_selected_backups(self):
        selected_items = self.backup_list.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "No Selection", "Please select backups to restore.")
            return
        reply = QMessageBox.question(self, "Confirm Restore", f"Restore {len(selected_items)} AIW file(s)?", QMessageBox.Yes | QMessageBox.No)
        if reply != QMessageBox.Yes:
            return
        restored = 0
        for item in selected_items:
            backup = item.data(Qt.UserRole)
            if backup and self.restore_aiw_backup(backup):
                restored += 1
        if restored > 0:
            QMessageBox.information(self, "Restore Complete", f"Successfully restored {restored} AIW file(s).")
            self.refresh_backup_list()
    
    def restore_all_backups(self):
        backups = self.scan_aiw_backups()
        if not backups:
            QMessageBox.information(self, "No Backups", "No backups found to restore.")
            return
        reply = QMessageBox.question(self, "Confirm Restore All", f"Restore ALL {len(backups)} AIW backup(s)?", QMessageBox.Yes | QMessageBox.No)
        if reply != QMessageBox.Yes:
            return
        restored = 0
        for backup in backups:
            if self.restore_aiw_backup(backup):
                restored += 1
        if restored > 0:
            QMessageBox.information(self, "Restore Complete", f"Successfully restored {restored} AIW file(s).")
            self.refresh_backup_list()
    
    def on_lap_time_edited(self, session_type: str, new_time: float):
        self.lap_time_updated.emit(session_type, new_time)
        if self.curve_graph:
            if session_type == "qual":
                self.curve_graph.user_qual_time = new_time
                self.curve_graph.user_qual_ratio = self.curve_graph._calculate_ratio_for_user_time(new_time, "qual")
            else:
                self.curve_graph.user_race_time = new_time
                self.curve_graph.user_race_ratio = self.curve_graph._calculate_ratio_for_user_time(new_time, "race")
            self.curve_graph.update_graph()
    
    def sync_log_display(self):
        """Sync the log display with the log window content"""
        if hasattr(self, 'log_display') and self.log_window:
            if hasattr(self.log_window, 'log_text'):
                # Copy the HTML content from the log window
                html_content = self.log_window.log_text.toHtml()
                if html_content != self.log_display.toHtml():
                    self.log_display.setHtml(html_content)
                    
                    # Auto-scroll to bottom
                    scrollbar = self.log_display.verticalScrollBar()
                    scrollbar.setValue(scrollbar.maximum())
    
    def clear_log_display(self):
        if self.log_window:
            self.log_window.clear_log()
        if hasattr(self, 'log_display'):
            self.log_display.clear()
    
    def refresh_all(self):
        if self.curve_graph:
            self.curve_graph.full_refresh()
        self.refresh_display()
    
    def on_point_selected(self, track, session, ratio, lap_time):
        pass
    
    def on_data_updated(self):
        self.data_updated.emit()
        if self.curve_graph and self.curve_graph.current_track:
            self.track_selected.emit(self.curve_graph.current_track)
    
    def on_formula_changed(self, session_type: str, a: float, b: float):
        if session_type == "qual" and self.qual_panel:
            self.qual_panel.update_formula(a, b)
        elif session_type == "race" and self.race_panel:
            self.race_panel.update_formula(a, b)
        self.formula_updated.emit(session_type, a, b)
    
    def on_session_formula_changed(self, session_type: str, a: float, b: float):
        if self.curve_graph:
            if session_type == "qual":
                self.curve_graph.qual_a = a
                self.curve_graph.qual_b = b
            else:
                self.curve_graph.race_a = a
                self.curve_graph.race_b = b
            if self.curve_graph.user_qual_time and session_type == "qual":
                self.curve_graph.user_qual_ratio = self.curve_graph._calculate_ratio_for_user_time(self.curve_graph.user_qual_time, "qual")
            if self.curve_graph.user_race_time and session_type == "race":
                self.curve_graph.user_race_ratio = self.curve_graph._calculate_ratio_for_user_time(self.curve_graph.user_race_time, "race")
            self.curve_graph.update_graph()
        self.formula_updated.emit(session_type, a, b)
    
    def on_show_data_toggled(self, session_type: str, show: bool):
        if self.curve_graph:
            if session_type == "qual":
                self.curve_graph.set_show_qualifying(show)
            else:
                self.curve_graph.set_show_race(show)
    
    def on_calculate_and_save_ratio(self, session_type: str, lap_time: float):
        if session_type == "qual":
            a, b = self.qual_panel.a, self.qual_panel.b
        else:
            a, b = self.race_panel.a, self.race_panel.b
        
        denominator = lap_time - b
        if denominator <= 0:
            QMessageBox.warning(self, "Invalid Calculation", 
                f"Cannot calculate ratio: T - b = {lap_time:.3f} - {b:.2f} = {denominator:.3f} (must be positive)")
            return
        
        ratio = a / denominator
        if not (0.3 < ratio < 3.0):
            QMessageBox.warning(self, "Ratio Out of Range", 
                f"Calculated ratio {ratio:.6f} is outside valid range (0.3 - 3.0)")
            return
        
        min_ratio, max_ratio = get_ratio_limits()
        if ratio < min_ratio or ratio > max_ratio:
            reply = QMessageBox.question(self, "Ratio Out of Range", 
                f"The calculated {session_type.upper()} Ratio = {ratio:.6f} is outside the allowed range "
                f"({min_ratio} - {max_ratio}).\n\nContinue anyway?",
                QMessageBox.Yes | QMessageBox.No)
            if reply != QMessageBox.Yes:
                return
        
        aiw_path = self._find_aiw_path_from_config()
        
        if not aiw_path:
            self._show_aiw_path_error()
            return
        
        if self._update_aiw_ratio(aiw_path, "QualRatio" if session_type == "qual" else "RaceRatio", ratio):
            self.ratio_saved.emit(session_type, ratio)
            if self.curve_graph:
                if session_type == "qual":
                    self.curve_graph.user_qual_ratio = ratio
                else:
                    self.curve_graph.user_race_ratio = ratio
                self.curve_graph.update_graph()
            if self.parent:
                parent = self.parent() if callable(self.parent) else self.parent
                if session_type == "qual":
                    parent.last_qual_ratio = ratio
                    parent.qual_panel.update_ratio(ratio)
                else:
                    parent.last_race_ratio = ratio
                    parent.race_panel.update_ratio(ratio)
    
    def on_auto_fit_requested(self, session_type: str):
        if not self.curve_graph:
            return
        points_data = self.curve_graph.get_selected_data()
        if session_type == "qual":
            points = points_data.get('quali', [])
        else:
            points = points_data.get('race', [])
        if len(points) < 2:
            QMessageBox.warning(self, "Insufficient Data", f"Need at least 2 data points to auto-fit {session_type} formula. Found {len(points)} points.")
            return
        ratios = [p[0] for p in points]
        times = [p[1] for p in points]
        a, b, avg_err, max_err = fit_curve(ratios, times, verbose=False)
        if a and b and a > 0 and b > 0:
            b = b
            a = DEFAULT_A_VALUE
            if session_type == "qual":
                self.qual_panel.update_formula(a, b)
                if self.curve_graph:
                    self.curve_graph.qual_a = a
                    self.curve_graph.qual_b = b
            else:
                self.race_panel.update_formula(a, b)
                if self.curve_graph:
                    self.curve_graph.race_a = a
                    self.curve_graph.race_b = b
            if self.curve_graph:
                if self.curve_graph.user_qual_time:
                    self.curve_graph.user_qual_ratio = self.curve_graph._calculate_ratio_for_user_time(self.curve_graph.user_qual_time, "qual")
                if self.curve_graph.user_race_time:
                    self.curve_graph.user_race_ratio = self.curve_graph._calculate_ratio_for_user_time(self.curve_graph.user_race_time, "race")
                self.curve_graph.update_graph()
            self.formula_updated.emit(session_type, a, b)
            if self.parent:
                parent = self.parent() if callable(self.parent) else self.parent
                if session_type == "qual":
                    parent.qual_b = b
                else:
                    parent.race_b = b
                parent.update_display()
            QMessageBox.information(self, "Auto-Fit Complete", f"Formula fitted to {len(points)} data points:\nT = {a:.4f} / R + {b:.4f}\nAverage error: {avg_err:.3f}s\nMax error: {max_err:.3f}s")
        else:
            QMessageBox.warning(self, "Fit Failed", "Could not fit curve to data.")
    
    def refresh_display(self):
        if not self.parent:
            return
        parent = self.parent() if callable(self.parent) else self.parent
        current_track = getattr(parent, 'current_track', None)
        current_vehicle = getattr(parent, 'current_vehicle', None)
        user_qual_time = getattr(parent, 'user_qualifying_sec', 0.0)
        user_race_time = getattr(parent, 'user_best_lap_sec', 0.0)
        qual_a = getattr(parent, 'qual_a', DEFAULT_A_VALUE)
        qual_b = getattr(parent, 'qual_b', 70.0)
        race_a = getattr(parent, 'race_a', DEFAULT_A_VALUE)
        race_b = getattr(parent, 'race_b', 70.0)
        last_qual_ratio = getattr(parent, 'last_qual_ratio', None)
        last_race_ratio = getattr(parent, 'last_race_ratio', None)
        
        if self.curve_graph:
            self.curve_graph.update_current_info(
                track=current_track, vehicle=current_vehicle,
                qual_time=user_qual_time if user_qual_time > 0 else None,
                race_time=user_race_time if user_race_time > 0 else None,
                qual_ratio=last_qual_ratio, race_ratio=last_race_ratio
            )
            self.curve_graph.set_formulas(qual_a, qual_b, race_a, race_b)
            self.curve_graph.update_graph()
        if self.qual_panel:
            self.qual_panel.update_formula(qual_a, qual_b)
            self.qual_panel.update_user_time(user_qual_time)
            self.qual_panel.update_ratio(last_qual_ratio)
        if self.race_panel:
            self.race_panel.update_formula(race_a, race_b)
            self.race_panel.update_user_time(user_race_time)
            self.race_panel.update_ratio(last_race_ratio)
    
    def showEvent(self, event):
        self.refresh_display()
        super().showEvent(event)
    
    def closeEvent(self, event):
        # Stop the log update timer when closing
        if self.log_update_timer:
            self.log_update_timer.stop()
        super().closeEvent(event)
    
    def on_target_mode_changed(self):
        if self.percentage_radio.isChecked():
            self.target_mode = "percentage"
        elif self.faster_radio.isChecked():
            self.target_mode = "faster_than_best"
        else:
            self.target_mode = "slower_than_worst"
        self.update_mode_visibility()
    
    def update_mode_visibility(self):
        for child in self.findChildren(QGroupBox):
            if "Percentage Setting" in child.title():
                child.setVisible(self.target_mode == "percentage")
            elif "Fixed Offset Setting" in child.title():
                child.setVisible(self.target_mode != "percentage")
        self.update_mode_description()
    
    def update_mode_description(self):
        if self.target_mode == "percentage":
            pct = self.target_percent_slider.value()
            if pct == 0:
                desc = "You will match the FASTEST AI lap time"
            elif pct == 100:
                desc = "You will match the SLOWEST AI lap time"
            elif pct == 50:
                desc = "You will be exactly in the MIDDLE of the AI range"
            else:
                desc = f"You will be {pct}% from fastest AI to slowest AI"
            self.percent_description.setText(desc)
        elif self.target_mode == "faster_than_best":
            offset = self.target_offset_spin.value()
            if offset == 0:
                desc = "You will match the fastest AI lap time"
            elif offset > 0:
                desc = f"You will be {offset:.2f} seconds SLOWER than the fastest AI"
            else:
                desc = f"You will be {abs(offset):.2f} seconds FASTER than the fastest AI"
            self.offset_description.setText(desc)
        else:
            offset = self.target_offset_spin.value()
            if offset == 0:
                desc = "You will match the slowest AI lap time"
            elif offset > 0:
                desc = f"You will be {offset:.2f} seconds FASTER than the slowest AI"
            else:
                desc = f"You will be {abs(offset):.2f} seconds SLOWER than the slowest AI"
            self.offset_description.setText(desc)
    
    def on_percent_changed(self, value):
        self.target_percent_spin.blockSignals(True)
        self.target_percent_spin.setValue(value)
        self.target_percent_spin.blockSignals(False)
        self.target_percentage = value
        self.update_mode_description()
    
    def on_percent_spin_changed(self, value):
        self.target_percent_slider.blockSignals(True)
        self.target_percent_slider.setValue(value)
        self.target_percent_slider.blockSignals(False)
        self.target_percentage = value
        self.update_mode_description()
    
    def on_offset_changed(self, value):
        self.target_offset_seconds = value
        self.update_mode_description()
    
    def on_error_margin_changed(self, value):
        seconds = value / 100.0
        self.error_margin_spin.blockSignals(True)
        self.error_margin_spin.setValue(seconds)
        self.error_margin_spin.blockSignals(False)
        self.ai_error_margin = seconds
    
    def on_error_margin_spin_changed(self, value):
        self.error_margin_slider.blockSignals(True)
        self.error_margin_slider.setValue(int(value * 100))
        self.error_margin_slider.blockSignals(False)
        self.ai_error_margin = value
    
    def calculate_target_lap_time(self, best_ai: float, worst_ai: float, settings: dict) -> float:
        mode = settings.get("mode", "percentage")
        error_margin = settings.get("error_margin", 0.0)
        if mode == "percentage":
            pct = settings.get("percentage", 50) / 100.0
            target = best_ai + (worst_ai - best_ai) * pct
        elif mode == "faster_than_best":
            offset = settings.get("offset_seconds", 0.0)
            target = best_ai + offset
        else:
            offset = settings.get("offset_seconds", 0.0)
            target = worst_ai - offset
        target = target + error_margin
        target = max(best_ai, min(worst_ai + error_margin, target))
        return target
    
    def calculate_new_ratio_for_target(self, target_time: float, session_type: str) -> float:
        if session_type == "qual":
            if self.qual_panel:
                a, b = self.qual_panel.a, self.qual_panel.b
            else:
                a, b = DEFAULT_A_VALUE, 70.0
        else:
            if self.race_panel:
                a, b = self.race_panel.a, self.race_panel.b
            else:
                a, b = DEFAULT_A_VALUE, 70.0
        denominator = target_time - b
        if denominator <= 0:
            return None
        ratio = a / denominator
        return ratio if 0.3 < ratio < 3.0 else None
    
    def apply_target_settings(self):
        settings = {
            "mode": self.target_mode,
            "percentage": self.target_percentage,
            "offset_seconds": self.target_offset_seconds,
            "error_margin": self.ai_error_margin
        }
        
        parent = self.parent() if callable(self.parent) else self.parent
        if parent:
            qual_best = getattr(parent, 'qual_best_ai', None)
            qual_worst = getattr(parent, 'qual_worst_ai', None)
            race_best = getattr(parent, 'race_best_ai', None)
            race_worst = getattr(parent, 'race_worst_ai', None)
        else:
            qual_best = qual_worst = race_best = race_worst = None
        
        if qual_best is None or qual_worst is None or race_best is None or race_worst is None:
            error_msg = "No AI lap time data available. Please complete at least one race session first."
            QMessageBox.warning(self, "No AI Data", error_msg)
            return
        
        qual_target = self.calculate_target_lap_time(qual_best, qual_worst, settings)
        race_target = self.calculate_target_lap_time(race_best, race_worst, settings)
        
        qual_new_ratio = self.calculate_new_ratio_for_target(qual_target, "qual")
        race_new_ratio = self.calculate_new_ratio_for_target(race_target, "race")
        
        if not qual_new_ratio or not race_new_ratio:
            error_msg = "Could not calculate new ratios. Target times may be too close to formula b value."
            QMessageBox.warning(self, "Calculation Failed", error_msg)
            return
        
        confirm_msg = f"AI Target Settings Summary:\n\nQualifying:\n  AI Range: {qual_best:.3f}s - {qual_worst:.3f}s\n  Target: {qual_target:.3f}s\n  New QualRatio: {qual_new_ratio:.6f}\n\nRace:\n  AI Range: {race_best:.3f}s - {race_worst:.3f}s\n  Target: {race_target:.3f}s\n  New RaceRatio: {race_new_ratio:.6f}\n\nContinue?"
        
        reply = QMessageBox.question(self, "Apply AI Target Settings", confirm_msg, QMessageBox.Yes | QMessageBox.No)
        if reply != QMessageBox.Yes:
            return
        
        aiw_path = self._find_aiw_path_from_config()
        
        if not aiw_path:
            self._show_aiw_path_error()
            return
        
        engine = parent.autopilot_manager.engine if parent and hasattr(parent, 'autopilot_manager') else None
        
        if engine:
            qual_updated = engine._update_aiw_ratio(aiw_path, "QualRatio", qual_new_ratio)
            race_updated = engine._update_aiw_ratio(aiw_path, "RaceRatio", race_new_ratio)
            
            if qual_updated or race_updated:
                if qual_updated and parent:
                    parent.last_qual_ratio = qual_new_ratio
                    parent.qual_panel.update_ratio(qual_new_ratio)
                if race_updated and parent:
                    parent.last_race_ratio = race_new_ratio
                    parent.race_panel.update_ratio(race_new_ratio)
                if parent and hasattr(parent, 'ai_target_settings'):
                    parent.ai_target_settings = settings
                if parent and hasattr(parent, 'update_target_display'):
                    parent.update_target_display()
                QMessageBox.information(self, "Settings Applied", f"AI Target settings applied!\nQualRatio: {qual_new_ratio:.6f}\nRaceRatio: {race_new_ratio:.6f}")
            else:
                QMessageBox.warning(self, "Update Failed", "Failed to update AIW file with new ratios.")
        else:
            QMessageBox.warning(self, "Error", "Could not access autopilot engine.")
