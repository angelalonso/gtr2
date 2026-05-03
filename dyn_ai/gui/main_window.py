#!/usr/bin/env python3
"""
Main window for Live AI Tuner - Lightweight version
"""

import sys
import logging
import threading
import time
import re
import shutil
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any

from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFrame, QMessageBox, QApplication,
    QStatusBar
)
from PyQt5.QtCore import Qt, pyqtSignal, QObject, QTimer

# Import core modules
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.database import DatabaseManager
from core.config import ConfigManager
from core.parser import RaceDataParser, RaceData
from core.formula import DEFAULT_A, ratio_from_time, hyperbolic
from core.autopilot import AutopilotManager, get_vehicle_class, load_vehicle_classes

from .dialogs import BasePathDialog, LogWindow
from .widgets import ToggleSwitch, RatioDisplay
from .styles import apply_dark_theme

logger = logging.getLogger(__name__)


class FileMonitorSignals(QObject):
    """Signals for file monitor thread"""
    file_changed = pyqtSignal(object)


class FileMonitorThread(threading.Thread):
    """Lightweight file monitor thread"""
    
    def __init__(self, file_path: Path, poll_interval: float = 10.0):
        super().__init__(daemon=True)
        self.file_path = file_path
        self.poll_interval = poll_interval
        self.running = False
        self.signals = FileMonitorSignals()
        self._last_mtime = None
        self._last_size = None
    
    def run(self):
        self.running = True
        self._update_state()
        
        while self.running:
            time.sleep(self.poll_interval)
            if not self.running:
                break
            self._check()
    
    def stop(self):
        self.running = False
    
    def _update_state(self):
        try:
            if self.file_path.exists():
                stat = self.file_path.stat()
                self._last_mtime = stat.st_mtime
                self._last_size = stat.st_size
        except Exception:
            pass
    
    def _check(self):
        try:
            if not self.file_path.exists():
                return
            
            stat = self.file_path.stat()
            changed = (self._last_mtime is None or 
                      stat.st_mtime != self._last_mtime or
                      stat.st_size != self._last_size)
            
            if changed:
                self._last_mtime = stat.st_mtime
                self._last_size = stat.st_size
                self.signals.file_changed.emit(self.file_path)
                
        except Exception as e:
            logger.debug(f"File check error: {e}")


class MainWindow(QMainWindow):
    """Main application window - lightweight version"""
    
    def __init__(self, config_file: str = "cfg.yml"):
        super().__init__()
        
        self.config_manager = ConfigManager()
        self.config = self.config_manager.load(config_file)
        
        # Set up logging
        log_level = self.config.get('logging_level', 'WARNING')
        logging.basicConfig(level=getattr(logging, log_level))
        
        self.db = DatabaseManager(self.config.get('db_path', 'ai_data.db'))
        self.parser = RaceDataParser()
        self.autopilot = AutopilotManager(self.db)
        
        # State variables
        self.current_track = ""
        self.current_vehicle = ""
        self.current_vehicle_class = ""
        
        self.qual_ratio = None
        self.race_ratio = None
        self.qual_read_ratio = None
        self.race_read_ratio = None
        
        self.qual_best_ai = None
        self.qual_worst_ai = None
        self.race_best_ai = None
        self.race_worst_ai = None
        
        self.user_qual_time = 0.0
        self.user_race_time = 0.0
        
        self.qual_b = 70.0
        self.race_b = 70.0
        
        self.autosave_enabled = self.config.get('auto_apply', False)
        self.autoratio_enabled = self.config.get('autopilot_enabled', False)
        self.autopilot.set_enabled(self.autoratio_enabled)
        
        self.monitor_thread = None
        self.class_mapping = load_vehicle_classes()
        self.log_window = None
        self._tracks = []  # Initialize tracks list
        
        self.setup_ui()
        
        # Start monitoring if base path configured
        self._start_monitoring()
        
        # Load initial data
        self._load_track_data()
    
    def setup_ui(self):
        """Setup main UI"""
        self.setWindowTitle("GTR2 Dynamic AI")
        self.setGeometry(100, 100, 800, 550)
        self.setMinimumWidth(700)
        
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setSpacing(20)
        layout.setContentsMargins(25, 25, 25, 25)
        
        # Header with logo and track
        header = QHBoxLayout()
        
        logo = QLabel("GTR2")
        logo.setStyleSheet("font-size: 28px; font-weight: bold; color: #888;")
        header.addWidget(logo)
        
        header.addStretch()
        
        track_frame = QFrame()
        track_frame.setStyleSheet("background-color: #2b2b2b; border-radius: 6px; padding: 5px 10px;")
        track_layout = QHBoxLayout(track_frame)
        track_layout.setContentsMargins(10, 5, 10, 5)
        
        track_layout.addWidget(QLabel("Track:"))
        self.track_label = QLabel("-")
        self.track_label.setStyleSheet("font-weight: bold; color: #FFA500;")
        track_layout.addWidget(self.track_label)
        
        self.select_track_btn = QPushButton("Select")
        self.select_track_btn.setFixedWidth(60)
        self.select_track_btn.clicked.connect(self._select_track)
        track_layout.addWidget(self.select_track_btn)
        
        header.addWidget(track_frame)
        
        layout.addLayout(header)
        
        # Car class
        class_frame = QFrame()
        class_frame.setStyleSheet("background-color: #2b2b2b; border-radius: 6px; padding: 5px 10px;")
        class_layout = QHBoxLayout(class_frame)
        
        class_layout.addWidget(QLabel("Car Class:"))
        self.class_label = QLabel("-")
        self.class_label.setStyleSheet("color: #4CAF50; font-weight: bold;")
        class_layout.addWidget(self.class_label)
        class_layout.addStretch()
        
        layout.addWidget(class_frame)
        
        # Ratio panels (Qualifying and Race)
        panels = QHBoxLayout()
        panels.setSpacing(20)
        
        # Qualifying panel
        self.qual_panel = self._create_ratio_panel("Qualifying")
        panels.addWidget(self.qual_panel)
        
        # Race panel
        self.race_panel = self._create_ratio_panel("Race")
        panels.addWidget(self.race_panel)
        
        layout.addLayout(panels)
        
        layout.addStretch()
        
        # Bottom buttons
        buttons = QHBoxLayout()
        buttons.setSpacing(15)
        
        self.autosave_switch = ToggleSwitch("Auto-save ON", "Auto-save OFF")
        self.autosave_switch.set_checked(self.autosave_enabled)
        self.autosave_switch.clicked.connect(self._toggle_autosave)
        buttons.addWidget(self.autosave_switch)
        
        self.autoratio_switch = ToggleSwitch("Auto-ratio ON", "Auto-ratio OFF")
        self.autoratio_switch.set_checked(self.autoratio_enabled)
        self.autoratio_switch.clicked.connect(self._toggle_autoratio)
        buttons.addWidget(self.autoratio_switch)
        
        buttons.addStretch()
        
        self.log_btn = QPushButton("Logs")
        self.log_btn.clicked.connect(self._show_logs)
        buttons.addWidget(self.log_btn)
        
        self.exit_btn = QPushButton("Exit")
        self.exit_btn.clicked.connect(self.close)
        buttons.addWidget(self.exit_btn)
        
        layout.addLayout(buttons)
        
        # Status bar
        self.statusBar().showMessage("Ready")
    
    def _create_ratio_panel(self, title: str) -> QFrame:
        """Create a ratio display panel"""
        panel = QFrame()
        panel.setStyleSheet("""
            QFrame {
                background-color: #2b2b2b;
                border-radius: 10px;
                padding: 15px;
            }
        """)
        
        layout = QVBoxLayout(panel)
        
        # Title
        title_label = QLabel(title)
        title_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #aaa;")
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)
        
        # Ratio display
        ratio_display = RatioDisplay()
        layout.addWidget(ratio_display)
        
        # Store reference
        if title == "Qualifying":
            self.qual_display = ratio_display
        else:
            self.race_display = ratio_display
        
        # AI range
        range_label = QLabel("AI Range: -- - --")
        range_label.setStyleSheet("color: #888; font-size: 10px;")
        range_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(range_label)
        
        if title == "Qualifying":
            self.qual_range = range_label
        else:
            self.race_range = range_label
        
        # User time
        time_label = QLabel("User: --")
        time_label.setStyleSheet("color: #4CAF50; font-size: 11px;")
        time_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(time_label)
        
        if title == "Qualifying":
            self.qual_user_time = time_label
        else:
            self.race_user_time = time_label
        
        # Formula
        formula_label = QLabel("T = 32/R + 70")
        formula_label.setStyleSheet("color: #666; font-size: 9px;")
        formula_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(formula_label)
        
        if title == "Qualifying":
            self.qual_formula = formula_label
        else:
            self.race_formula = formula_label
        
        return panel
    
    def _start_monitoring(self):
        """Start file monitoring thread"""
        results_path = self.config_manager.get_results_file_path()
        
        if not results_path:
            logger.debug("No results file path configured")
            return
        
        poll_interval = self.config_manager.get_poll_interval()
        
        self.monitor_thread = FileMonitorThread(results_path, poll_interval)
        self.monitor_thread.signals.file_changed.connect(self._on_file_changed)
        self.monitor_thread.start()
        
        logger.info(f"Monitoring {results_path} every {poll_interval}s")
    
    def _load_track_data(self):
        """Load track data from database"""
        self._tracks = self.db.get_all_tracks()
    
    def _select_track(self):
        """Open track selection dialog"""
        self._tracks = self.db.get_all_tracks()
        
        if not self._tracks:
            QMessageBox.information(self, "No Tracks", 
                "No tracks found in database. Run a race session or import data first.")
            return
        
        from PyQt5.QtWidgets import QListWidget, QDialog, QDialogButtonBox, QVBoxLayout
        
        dialog = QDialog(self)
        dialog.setWindowTitle("Select Track")
        dialog.setModal(True)
        
        layout = QVBoxLayout(dialog)
        list_widget = QListWidget()
        
        for track in self._tracks:
            list_widget.addItem(track)
        
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        
        layout.addWidget(list_widget)
        layout.addWidget(buttons)
        
        if dialog.exec_() == QDialog.Accepted and list_widget.currentItem():
            track = list_widget.currentItem().text()
            self._set_track(track)
    
    def _set_track(self, track: str):
        """Set current track and update display"""
        self.current_track = track
        self.track_label.setText(track)
        self.setWindowTitle(f"GTR2 Dynamic AI - {track}")
        
        # Load AI times for track
        self.qual_best_ai, self.qual_worst_ai = self.db.get_ai_times_for_track(track, "qual")
        self.race_best_ai, self.race_worst_ai = self.db.get_ai_times_for_track(track, "race")
        
        # Load formulas
        self._load_formulas()
        
        # Load AIW ratios
        self._load_aiw_ratios()
        
        # Update display
        self._update_display()
    
    def _load_formulas(self):
        """Load formulas from database"""
        if not self.current_track or not self.current_vehicle_class:
            return
        
        qual_formula = self.autopilot.formula_manager.get_formula_by_class(
            self.current_track, self.current_vehicle_class, "qual")
        if qual_formula:
            self.qual_b = qual_formula.b
            self.qual_formula.setText(f"T = {DEFAULT_A:.0f}/R + {self.qual_b:.1f}")
        
        race_formula = self.autopilot.formula_manager.get_formula_by_class(
            self.current_track, self.current_vehicle_class, "race")
        if race_formula:
            self.race_b = race_formula.b
            self.race_formula.setText(f"T = {DEFAULT_A:.0f}/R + {self.race_b:.1f}")
    
    def _load_aiw_ratios(self):
        """Load ratios from AIW file"""
        aiw_path = self._find_aiw_file()
        
        if not aiw_path or not aiw_path.exists():
            return
        
        try:
            raw = aiw_path.read_bytes()
            content = raw.replace(b"\x00", b"").decode("utf-8", errors="ignore")
            
            waypoint_match = re.search(r'\[Waypoint\](.*?)(?=\[|$)', content, re.DOTALL | re.IGNORECASE)
            if waypoint_match:
                section = waypoint_match.group(1)
                
                qual_match = re.search(r'QualRatio\s*=\s*\(?([\d.eE+-]+)\)?', section, re.IGNORECASE)
                if qual_match:
                    self.qual_ratio = float(qual_match.group(1))
                
                race_match = re.search(r'RaceRatio\s*=\s*\(?([\d.eE+-]+)\)?', section, re.IGNORECASE)
                if race_match:
                    self.race_ratio = float(race_match.group(1))
                    
        except Exception as e:
            logger.debug(f"Error reading AIW: {e}")
    
    def _find_aiw_file(self) -> Optional[Path]:
        """Find AIW file for current track"""
        base_path = self.config_manager.get_base_path()
        
        if not base_path or not self.current_track:
            return None
        
        locations = base_path / "GameData" / "Locations"
        if not locations.exists():
            return None
        
        track_lower = self.current_track.lower()
        
        for track_dir in locations.iterdir():
            if track_dir.is_dir() and track_dir.name.lower() == track_lower:
                for ext in ["*.AIW", "*.aiw"]:
                    aiw_files = list(track_dir.glob(ext))
                    if aiw_files:
                        return aiw_files[0]
        
        return None
    
    def _update_display(self):
        """Update all display elements"""
        # Update ratio displays
        if self.qual_ratio:
            self.qual_display.update_ratio(self.qual_ratio)
        if self.race_ratio:
            self.race_display.update_ratio(self.race_ratio)
        
        # Update AI ranges
        if self.qual_best_ai and self.qual_worst_ai:
            self.qual_range.setText(f"AI Range: {self.qual_best_ai:.2f}s - {self.qual_worst_ai:.2f}s")
        else:
            self.qual_range.setText("AI Range: -- - --")
        
        if self.race_best_ai and self.race_worst_ai:
            self.race_range.setText(f"AI Range: {self.race_best_ai:.2f}s - {self.race_worst_ai:.2f}s")
        else:
            self.race_range.setText("AI Range: -- - --")
        
        # Update user times
        if self.user_qual_time > 0:
            self.qual_user_time.setText(f"User: {self._format_time(self.user_qual_time)}")
        else:
            self.qual_user_time.setText("User: --")
        
        if self.user_race_time > 0:
            self.race_user_time.setText(f"User: {self._format_time(self.user_race_time)}")
        else:
            self.race_user_time.setText("User: --")
    
    def _format_time(self, seconds: float) -> str:
        """Format seconds as mm:ss.ms"""
        if seconds <= 0:
            return "--"
        minutes = int(seconds) // 60
        secs = seconds % 60
        return f"{minutes}:{secs:05.2f}"
    
    def _on_file_changed(self, file_path: Path):
        """Handle file change event"""
        logger.info("Race results file changed, parsing...")
        
        race_data = self.parser.parse(file_path)
        
        if not race_data or not race_data.has_data():
            logger.debug("No valid race data found")
            return
        
        # Update state from parsed data
        if race_data.track_name:
            self._set_track(race_data.track_name)
        
        if race_data.user_vehicle:
            self.current_vehicle = race_data.user_vehicle
            self.current_vehicle_class = get_vehicle_class(
                self.current_vehicle, self.class_mapping)
            self.class_label.setText(self.current_vehicle_class)
        
        if race_data.user_qualifying_sec > 0:
            self.user_qual_time = race_data.user_qualifying_sec
        if race_data.user_best_lap_sec > 0:
            self.user_race_time = race_data.user_best_lap_sec
        
        if race_data.qual_ratio:
            self.qual_read_ratio = race_data.qual_ratio
        if race_data.race_ratio:
            self.race_read_ratio = race_data.race_ratio
        
        if race_data.qual_best_ai_lap_sec:
            self.qual_best_ai = race_data.qual_best_ai_lap_sec
        if race_data.qual_worst_ai_lap_sec:
            self.qual_worst_ai = race_data.qual_worst_ai_lap_sec
        if race_data.best_ai_lap_sec:
            self.race_best_ai = race_data.best_ai_lap_sec
        if race_data.worst_ai_lap_sec:
            self.race_worst_ai = race_data.worst_ai_lap_sec
        
        # Save to database if auto-save enabled
        if self.autosave_enabled:
            race_dict = race_data.to_dict()
            self.db.save_race_session(race_dict)
            
            # Save data points
            points = race_data.to_data_points_with_vehicles()
            for track, vehicle, ratio, time, session in points:
                vehicle_class = get_vehicle_class(vehicle, self.class_mapping)
                self.db.add_data_point(track, vehicle_class, ratio, time, session)
        
        # Update formulas
        self._load_formulas()
        
        # Process autopilot
        if self.autoratio_enabled:
            self._run_autopilot(race_data)
        
        # Update display
        self._update_display()
        
        # Show notification
        self.statusBar().showMessage(f"Race data processed for {race_data.track_name}", 3000)
    
    def _run_autopilot(self, race_data: RaceData):
        """Run autopilot calculations"""
        aiw_path = self._find_aiw_file()
        
        if not aiw_path:
            logger.warning("Cannot run autopilot: AIW file not found")
            return
        
        # Get formula
        formula = self.autopilot.formula_manager.get_formula(
            race_data.track_name, self.current_vehicle, "race")
        
        if not formula or not formula.is_valid():
            logger.debug("No valid formula for auto-calculation")
            return
        
        # Calculate new ratio from user time
        if self.user_race_time > 0:
            new_ratio = formula.get_ratio(self.user_race_time)
            
            if new_ratio and abs(new_ratio - self.race_ratio) > 0.00001:
                # Validate ratio range
                min_r, max_r = self.config_manager.get_ratio_limits()
                if min_r <= new_ratio <= max_r:
                    if self._update_aiw_ratio(aiw_path, "RaceRatio", new_ratio):
                        self.race_ratio = new_ratio
                        logger.info(f"Autopilot updated RaceRatio to {new_ratio:.6f}")
                        self.statusBar().showMessage(f"Auto-ratio updated to {new_ratio:.6f}", 2000)
    
    def _update_aiw_ratio(self, aiw_path: Path, ratio_name: str, new_ratio: float) -> bool:
        """Update ratio in AIW file"""
        try:
            if not aiw_path.exists():
                return False
            
            # Backup
            backup_dir = Path(self.db.db_path).parent / "aiw_backups"
            backup_dir.mkdir(exist_ok=True)
            backup_path = backup_dir / f"{aiw_path.stem}_ORIGINAL{aiw_path.suffix}"
            if not backup_path.exists():
                shutil.copy2(aiw_path, backup_path)
            
            raw = aiw_path.read_bytes()
            content = raw.replace(b"\x00", b"").decode("utf-8", errors="ignore")
            
            pattern = rf'({re.escape(ratio_name)}\s*=\s*\(?)\s*[0-9.eE+-]+\s*(\)?)'
            new_content, count = re.subn(pattern, 
                lambda m: f"{m.group(1)}{new_ratio:.6f}{m.group(2)}", 
                content, flags=re.IGNORECASE)
            
            if count > 0:
                aiw_path.write_bytes(new_content.encode("utf-8", errors="ignore"))
                return True
            
            return False
        except Exception as e:
            logger.error(f"Error updating AIW: {e}")
            return False
    
    def _toggle_autosave(self):
        """Toggle auto-save setting"""
        self.autosave_enabled = self.autosave_switch.is_checked()
        self.config_manager.set('auto_apply', self.autosave_enabled)
        self.statusBar().showMessage(f"Auto-save {'ON' if self.autosave_enabled else 'OFF'}", 2000)
    
    def _toggle_autoratio(self):
        """Toggle auto-ratio setting"""
        self.autoratio_enabled = self.autoratio_switch.is_checked()
        self.autopilot.set_enabled(self.autoratio_enabled)
        self.config_manager.set('autopilot_enabled', self.autoratio_enabled)
        self.statusBar().showMessage(f"Auto-ratio {'ON' if self.autoratio_enabled else 'OFF'}", 2000)
    
    def _show_logs(self):
        """Show log window"""
        if not self.log_window:
            self.log_window = LogWindow(self)
        self.log_window.show()
        self.log_window.raise_()
    
    def closeEvent(self, event):
        """Handle clean shutdown"""
        if self.monitor_thread:
            self.monitor_thread.stop()
            self.monitor_thread.join(timeout=2)
        
        event.accept()
