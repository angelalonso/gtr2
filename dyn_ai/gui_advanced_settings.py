#!/usr/bin/env python3
"""
Advanced Settings Dialog for Dynamic AI
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
        self.tab_widget.addTab(data_tab, "Formula Management")
        
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
        
        warning_banner = QLabel("COMING (HOPEFULLY) SOON!")
        warning_banner.setStyleSheet("""
            QLabel {
                background-color: #f44336;
                color: white;
                font-weight: bold;
                font-size: 24px;
                padding: 30px;
                border-radius: 10px;
                text-align: center;
            }
        """)
        warning_banner.setAlignment(Qt.AlignCenter)
        target_layout.addWidget(warning_banner)
        
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
        
        # Get outlier settings from config
        from core_config import get_outlier_settings
        outlier_settings = get_outlier_settings()
        
        # Fit curve with outlier filtering
        a, b, avg_err, max_err, outlier_info = fit_curve(
            ratios, times, 
            verbose=False,
            outlier_method=outlier_settings['method'],
            outlier_threshold=outlier_settings['threshold'],
            min_points_after_filtering=2
        )
        
        if a and b and a > 0 and b > 0:
            b = b
            a = DEFAULT_A_VALUE
            
            # Show outlier information to user
            if outlier_info and outlier_info.outliers_removed > 0:
                outlier_msg = f"\n\nOutlier detection ({outlier_info.method_used}, threshold={outlier_info.threshold_used}):\n"
                outlier_msg += f"Removed {outlier_info.outliers_removed} outlier(s) from {outlier_info.total_points} total points."
                QMessageBox.information(self, "Outliers Removed", outlier_msg)
            
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
            
            summary_msg = f"Formula fitted to {len(points)} data points"
            if outlier_info and outlier_info.outliers_removed > 0:
                summary_msg += f" (after removing {outlier_info.outliers_removed} outliers)"
            summary_msg += f":\nT = {a:.4f} / R + {b:.4f}\nAverage error: {avg_err:.3f}s\nMax error: {max_err:.3f}s"
            
            QMessageBox.information(self, "Auto-Fit Complete", summary_msg)
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
