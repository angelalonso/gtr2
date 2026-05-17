#!/usr/bin/env python3
"""
Dynamic AI - Formula Visualizer (Standalone)
Shows curve graphs and formula management
Runs its own pre-run checks before starting
"""

import sys
import logging
import sqlite3
from pathlib import Path

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QMessageBox, QListWidget, QListWidgetItem,
    QAbstractItemView, QDialog, QDialogButtonBox, QLineEdit
)
from PyQt5.QtCore import Qt, QFileSystemWatcher, QTimer, pyqtSignal

from core_database import CurveDatabase
from core_config import get_db_path, get_config_with_defaults, create_default_config_if_missing, get_base_path, get_ratio_limits
from core_autopilot import get_vehicle_class, load_vehicle_classes, AutopilotManager
from core_formula import DEFAULT_A_VALUE, fit_curve
from core_aiw_utils import update_aiw_ratio, find_aiw_file_by_track
from core_user_laptimes import UserLapTimesManager
from gui_curve_graph import CurveGraphWidget
from gui_session_panel import SessionPanel
from gui_common import setup_dark_theme
from core_common import get_data_file_path


logger = logging.getLogger(__name__)


class TrackClassSelector(QWidget):
    """Widget for selecting track and vehicle class"""
    
    selection_changed = pyqtSignal(str, str)
    
    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self.all_tracks = []
        self.all_classes = []
        self.current_track = ""
        self.current_class = ""
        
        self.setup_ui()
        
    def setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(15)
        
        # Track selection group
        track_group = QFrame()
        track_group.setStyleSheet("background-color: #2b2b2b; border-radius: 5px; padding: 8px;")
        track_layout = QHBoxLayout(track_group)
        track_layout.setContentsMargins(10, 5, 10, 5)
        
        track_layout.addWidget(QLabel("TrackXX:"))
        self.track_label = QLabel("- Select Track -")
        self.track_label.setStyleSheet("color: #FFA500; font-weight: bold;")
        track_layout.addWidget(self.track_label)
        
        self.select_track_btn = QPushButton("Change")
        self.select_track_btn.setFixedWidth(70)
        self.select_track_btn.setStyleSheet("background-color: #2196F3;")
        self.select_track_btn.clicked.connect(self.select_track)
        track_layout.addWidget(self.select_track_btn)
        
        layout.addWidget(track_group)
        
        # Class selection group
        class_group = QFrame()
        class_group.setStyleSheet("background-color: #2b2b2b; border-radius: 5px; padding: 8px;")
        class_layout = QHBoxLayout(class_group)
        class_layout.setContentsMargins(10, 5, 10, 5)
        
        class_layout.addWidget(QLabel("Car Class:"))
        self.class_label = QLabel("- Select Class -")
        self.class_label.setStyleSheet("color: #FF6600; font-weight: bold;")
        class_layout.addWidget(self.class_label)
        
        self.select_class_btn = QPushButton("Change")
        self.select_class_btn.setFixedWidth(70)
        self.select_class_btn.setStyleSheet("background-color: #2196F3;")
        self.select_class_btn.clicked.connect(self.select_classes)
        class_layout.addWidget(self.select_class_btn)
        
        layout.addWidget(class_group)
        layout.addStretch()
        
        # Refresh button
        self.refresh_btn = QPushButton("Refresh Data")
        self.refresh_btn.setStyleSheet("background-color: #4CAF50;")
        self.refresh_btn.clicked.connect(self.refresh_data)
        layout.addWidget(self.refresh_btn)
    
    def load_data(self):
        """Load available tracks and classes from database"""
        if not self.db.database_exists():
            return
        
        conn = sqlite3.connect(self.db.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT DISTINCT track FROM data_points ORDER BY track")
        self.all_tracks = [row[0] for row in cursor.fetchall()]
        
        if not self.all_tracks:
            cursor.execute("SELECT DISTINCT track_name FROM race_sessions WHERE track_name IS NOT NULL ORDER BY track_name")
            self.all_tracks = [row[0] for row in cursor.fetchall()]
        
        cursor.execute("SELECT DISTINCT vehicle_class FROM data_points ORDER BY vehicle_class")
        all_vehicles = [row[0] for row in cursor.fetchall()]
        
        from core_autopilot import load_vehicle_classes
        class_mapping = load_vehicle_classes()
        class_set = set()
        for vehicle in all_vehicles:
            vehicle_class = get_vehicle_class(vehicle, class_mapping)
            class_set.add(vehicle_class)
        self.all_classes = sorted(class_set)
        
        conn.close()
        
        # Set defaults if available
        if self.all_tracks and not self.current_track:
            self.current_track = self.all_tracks[0]
            self.track_label.setText(self.current_track)
        
        if self.all_classes and not self.current_class:
            self.current_class = self.all_classes[0]
            self.class_label.setText(self.current_class)
    
    def select_track(self):
        """Open dialog to select a track"""
        if not self.all_tracks:
            QMessageBox.warning(self, "No Tracks", "No tracks available in database.")
            return
        
        dialog = QDialog(self)
        dialog.setWindowTitle("Select Track")
        dialog.setModal(True)
        dialog.setMinimumWidth(400)
        
        layout = QVBoxLayout(dialog)
        
        search_label = QLabel("Search:")
        layout.addWidget(search_label)
        
        search_edit = QLineEdit()
        search_edit.setPlaceholderText("Type to filter tracks...")
        layout.addWidget(search_edit)
        
        list_widget = QListWidget()
        for track in self.all_tracks:
            list_widget.addItem(track)
        
        items = list_widget.findItems(self.current_track, Qt.MatchExactly)
        if items:
            list_widget.setCurrentItem(items[0])
        
        layout.addWidget(list_widget)
        
        def filter_tracks():
            search_text = search_edit.text().lower()
            list_widget.clear()
            for track in self.all_tracks:
                if search_text in track.lower():
                    list_widget.addItem(track)
            if items and search_text in self.current_track.lower():
                found = list_widget.findItems(self.current_track, Qt.MatchExactly)
                if found:
                    list_widget.setCurrentItem(found[0])
        
        search_edit.textChanged.connect(filter_tracks)
        
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        
        if dialog.exec_() == QDialog.Accepted and list_widget.currentItem():
            selected = list_widget.currentItem().text()
            if selected != self.current_track:
                self.current_track = selected
                self.track_label.setText(selected)
                self.selection_changed.emit(self.current_track, self.current_class)
    
    def select_classes(self):
        """Open dialog to select vehicle classes"""
        if not self.all_classes:
            QMessageBox.warning(self, "No Classes", "No vehicle classes available in database.")
            return
        
        dialog = QDialog(self)
        dialog.setWindowTitle("Select Vehicle Class")
        dialog.setModal(True)
        dialog.setMinimumWidth(400)
        
        layout = QVBoxLayout(dialog)
        
        label = QLabel("Select a vehicle class to display:")
        layout.addWidget(label)
        
        list_widget = QListWidget()
        for cls in self.all_classes:
            list_widget.addItem(cls)
        
        items = list_widget.findItems(self.current_class, Qt.MatchExactly)
        if items:
            list_widget.setCurrentItem(items[0])
        
        layout.addWidget(list_widget)
        
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        
        if dialog.exec_() == QDialog.Accepted and list_widget.currentItem():
            selected = list_widget.currentItem().text()
            if selected != self.current_class:
                self.current_class = selected
                self.class_label.setText(selected)
                self.selection_changed.emit(self.current_track, self.current_class)
    
    def refresh_data(self):
        """Refresh the track and class lists"""
        self.load_data()
        self.selection_changed.emit(self.current_track, self.current_class)
    
    def get_current_track(self) -> str:
        return self.current_track
    
    def get_current_class(self) -> str:
        return self.current_class


class FormulaVisualizer(QMainWindow):
    """Standalone Formula Visualizer window with real-time data"""

    def __init__(self, config_file: str = "cfg.yml"):
        super().__init__()
        self.config_file = config_file
        self.config = get_config_with_defaults(config_file)
        self.db_path = get_db_path(config_file)
        self.db = CurveDatabase(self.db_path)
        self.base_path = get_base_path(config_file)
        
        # Load vehicle classes
        vehicle_classes_path = get_data_file_path("vehicle_classes.json")
        self.class_mapping = load_vehicle_classes(vehicle_classes_path)
        
        # Initialize autopilot manager
        self.autopilot_manager = AutopilotManager(self.db)
        
        # Initialize user laptimes manager
        from core_config import get_nr_last_user_laptimes
        max_laptimes = get_nr_last_user_laptimes(config_file)
        self.user_laptimes_manager = UserLapTimesManager(self.db_path, max_laptimes)
        self.autopilot_manager.set_user_laptimes_manager(self.user_laptimes_manager)
        
        # Current state - these will be set by the selector
        self.current_track = ""
        self.current_vehicle_class = ""
        
        # Formula values
        self.qual_a = DEFAULT_A_VALUE
        self.qual_b = 70.0
        self.race_a = DEFAULT_A_VALUE
        self.race_b = 70.0
        
        # User times
        self.user_qual_time = None
        self.user_race_time = None
        self.median_qual_time = None
        self.median_race_time = None
        self.last_qual_ratio = None
        self.last_race_ratio = None
        
        # AI times
        self.qual_best_ai = None
        self.qual_worst_ai = None
        self.race_best_ai = None
        self.race_worst_ai = None
        
        # User history
        self.user_qual_history = []
        self.user_race_history = []

        self.setWindowTitle("Dynamic AI - Formula Visualizer")
        self.setGeometry(100, 100, 1200, 800)
        self.setMinimumWidth(1000)
        self.setMinimumHeight(700)

        self.setup_ui()
        self.setup_db_watcher()
        self.setup_refresh_timer()
        
        # Load initial data after UI is ready
        self.selector.load_data()
        # The selector's selection_changed signal will trigger initial data load

    # ------------------------------------------------------------------
    # Database file watcher
    # ------------------------------------------------------------------

    def setup_db_watcher(self):
        """Watch the SQLite database file for changes made by other processes."""
        self._watcher = QFileSystemWatcher(self)
        self._watcher.addPath(self.db_path)
        
        wal_path = self.db_path + "-wal"
        if Path(wal_path).exists():
            self._watcher.addPath(wal_path)
            
        self._watcher.fileChanged.connect(self._on_db_file_changed)

        self._refresh_timer = QTimer(self)
        self._refresh_timer.setSingleShot(True)
        self._refresh_timer.setInterval(300)
        self._refresh_timer.timeout.connect(self._do_full_refresh)

    def _on_db_file_changed(self, path: str):
        if path not in self._watcher.files():
            self._watcher.addPath(path)
        
        wal_path = self.db_path + "-wal"
        if Path(wal_path).exists() and wal_path not in self._watcher.files():
            self._watcher.addPath(wal_path)
            
        self._refresh_timer.start()

    def setup_refresh_timer(self):
        """Periodic refresh as fallback (every 2 seconds)"""
        self._periodic_timer = QTimer(self)
        self._periodic_timer.setInterval(2000)
        self._periodic_timer.timeout.connect(self._check_and_update)
        self._periodic_timer.start()

    def _do_full_refresh(self):
        """Full refresh from database"""
        logger.debug("Database change detected - refreshing visualizer")
        if self.current_track and self.current_vehicle_class:
            self.load_current_data()
            self.update_all_display()
            if self.curve_graph:
                self.curve_graph.load_data()
                self.curve_graph.full_refresh()

    def _check_and_update(self):
        """Check for changes and update if needed"""
        if self.current_track and self.current_vehicle_class:
            self.load_current_data()
            self.update_all_display()

    # ------------------------------------------------------------------
    # Data loading
    # ------------------------------------------------------------------

    def load_current_data(self):
        """Load the current data from the database based on selected track/class"""
        if not self.current_track or not self.current_vehicle_class:
            return
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Load formulas for current track/class
        qual_formula = self.autopilot_manager.formula_manager.get_formula_by_class(
            self.current_track, self.current_vehicle_class, "qual")
        if qual_formula and qual_formula.is_valid():
            self.qual_a = qual_formula.a
            self.qual_b = qual_formula.b
        else:
            self.qual_a = DEFAULT_A_VALUE
            self.qual_b = 70.0
        
        race_formula = self.autopilot_manager.formula_manager.get_formula_by_class(
            self.current_track, self.current_vehicle_class, "race")
        if race_formula and race_formula.is_valid():
            self.race_a = race_formula.a
            self.race_b = race_formula.b
        else:
            self.race_a = DEFAULT_A_VALUE
            self.race_b = 70.0
        
        # Load user laptimes
        cursor.execute("""
            SELECT lap_time, ratio FROM user_laptimes 
            WHERE track = ? AND vehicle_class = ? AND session_type = 'qual'
            ORDER BY timestamp DESC LIMIT 1
        """, (self.current_track, self.current_vehicle_class))
        qual_row = cursor.fetchone()
        if qual_row:
            self.user_qual_time = qual_row[0]
            self.last_qual_ratio = qual_row[1]
        else:
            self.user_qual_time = None
            self.last_qual_ratio = None
        
        cursor.execute("""
            SELECT lap_time, ratio FROM user_laptimes 
            WHERE track = ? AND vehicle_class = ? AND session_type = 'race'
            ORDER BY timestamp DESC LIMIT 1
        """, (self.current_track, self.current_vehicle_class))
        race_row = cursor.fetchone()
        if race_row:
            self.user_race_time = race_row[0]
            self.last_race_ratio = race_row[1]
        else:
            self.user_race_time = None
            self.last_race_ratio = None
        
        # History for graph
        cursor.execute("""
            SELECT lap_time, ratio FROM user_laptimes 
            WHERE track = ? AND vehicle_class = ? AND session_type = 'qual'
            ORDER BY timestamp ASC
        """, (self.current_track, self.current_vehicle_class))
        self.user_qual_history = cursor.fetchall()
        
        cursor.execute("""
            SELECT lap_time, ratio FROM user_laptimes 
            WHERE track = ? AND vehicle_class = ? AND session_type = 'race'
            ORDER BY timestamp ASC
        """, (self.current_track, self.current_vehicle_class))
        self.user_race_history = cursor.fetchall()
        
        # Median times
        cursor.execute("""
            SELECT lap_time FROM user_laptimes 
            WHERE track = ? AND vehicle_class = ? AND session_type = 'qual'
        """, (self.current_track, self.current_vehicle_class))
        qual_times = [row[0] for row in cursor.fetchall()]
        self.median_qual_time = self._calculate_median(qual_times) if qual_times else None
        
        cursor.execute("""
            SELECT lap_time FROM user_laptimes 
            WHERE track = ? AND vehicle_class = ? AND session_type = 'race'
        """, (self.current_track, self.current_vehicle_class))
        race_times = [row[0] for row in cursor.fetchall()]
        self.median_race_time = self._calculate_median(race_times) if race_times else None
        
        # AI times for range
        self.qual_best_ai, self.qual_worst_ai = self._get_ai_times_for_track(self.current_track, "qual")
        self.race_best_ai, self.race_worst_ai = self._get_ai_times_for_track(self.current_track, "race")
        
        conn.close()
        
        logger.debug(f"Loaded data for track={self.current_track}, class={self.current_vehicle_class}")

    def _get_ai_times_for_track(self, track: str, session_type: str):
        """Get best and worst AI times for a track"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if session_type == "qual":
            cursor.execute("""
                SELECT MIN(qual_time_sec), MAX(qual_time_sec) FROM ai_results ar
                JOIN race_sessions rs ON ar.race_id = rs.race_id
                WHERE rs.track_name = ? AND ar.qual_time_sec > 0
            """, (track,))
        else:
            cursor.execute("""
                SELECT MIN(best_lap_sec), MAX(best_lap_sec) FROM ai_results ar
                JOIN race_sessions rs ON ar.race_id = rs.race_id
                WHERE rs.track_name = ? AND ar.best_lap_sec > 0
            """, (track,))
        
        row = cursor.fetchone()
        conn.close()
        return (row[0], row[1]) if row[0] is not None else (None, None)

    def _calculate_median(self, values):
        """Calculate median of a list"""
        if not values:
            return None
        values.sort()
        n = len(values)
        if n % 2 == 0:
            return (values[n//2 - 1] + values[n//2]) / 2
        return values[n//2]

    def update_all_display(self):
        """Update all display elements with current data"""
        if not self.current_track or not self.current_vehicle_class:
            return
        
        # Update session panels
        if hasattr(self, 'qual_panel'):
            self.qual_panel.update_formula(self.qual_a, self.qual_b)
            if self.user_qual_time:
                self.qual_panel.update_user_time(self.user_qual_time)
            if self.median_qual_time:
                self.qual_panel.update_median_time(self.median_qual_time)
            if self.last_qual_ratio:
                self.qual_panel.update_ratio(self.last_qual_ratio)
        
        if hasattr(self, 'race_panel'):
            self.race_panel.update_formula(self.race_a, self.race_b)
            if self.user_race_time:
                self.race_panel.update_user_time(self.user_race_time)
            if self.median_race_time:
                self.race_panel.update_median_time(self.median_race_time)
            if self.last_race_ratio:
                self.race_panel.update_ratio(self.last_race_ratio)
        
        # Update curve graph
        if hasattr(self, 'curve_graph') and self.curve_graph:
            self.curve_graph.set_formulas(self.qual_a, self.qual_b, self.race_a, self.race_b)
            self.curve_graph.update_current_info(
                track=self.current_track,
                vehicle=self.current_vehicle_class,
                qual_time=self.user_qual_time,
                race_time=self.user_race_time,
                qual_ratio=self.last_qual_ratio,
                race_ratio=self.last_race_ratio,
                qual_history=self.user_qual_history,
                race_history=self.user_race_history,
                median_qual_time=self.median_qual_time,
                median_race_time=self.median_race_time
            )
            self.curve_graph.update_graph()
        
        # Update window title
        self.setWindowTitle(f"Dynamic AI - Formula Visualizer - {self.current_track} - {self.current_vehicle_class}")

    # ------------------------------------------------------------------
    # UI setup
    # ------------------------------------------------------------------

    def setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # Track and class selector
        self.selector = TrackClassSelector(self.db, self)
        self.selector.selection_changed.connect(self.on_selection_changed)
        layout.addWidget(self.selector)

        # Curve graph
        self.curve_graph = CurveGraphWidget(self.db, self)
        layout.addWidget(self.curve_graph, stretch=3)

        # Session panels
        middle_layout = QHBoxLayout()
        middle_layout.setSpacing(15)

        self.qual_panel = SessionPanel("qual", "Qualifying Session", self.db, self)
        self.qual_panel.formula_changed.connect(self.on_qual_formula_changed)
        self.qual_panel.show_data_toggled.connect(self.on_show_data_toggled)
        self.qual_panel.calculate_ratio.connect(self.on_calculate_ratio)
        self.qual_panel.auto_fit_requested.connect(self.on_auto_fit)
        self.qual_panel.lap_time_edited.connect(self.on_lap_time_edited)
        middle_layout.addWidget(self.qual_panel)

        self.race_panel = SessionPanel("race", "Race Session", self.db, self)
        self.race_panel.formula_changed.connect(self.on_race_formula_changed)
        self.race_panel.show_data_toggled.connect(self.on_show_data_toggled)
        self.race_panel.calculate_ratio.connect(self.on_calculate_ratio)
        self.race_panel.auto_fit_requested.connect(self.on_auto_fit)
        self.race_panel.lap_time_edited.connect(self.on_lap_time_edited)
        middle_layout.addWidget(self.race_panel)

        layout.addLayout(middle_layout, stretch=1)

    # ------------------------------------------------------------------
    # Signal handlers
    # ------------------------------------------------------------------

    def on_selection_changed(self, track: str, vehicle_class: str):
        """Handle track/class selection change"""
        if not track or not vehicle_class:
            return
        
        logger.info(f"Selection changed: track={track}, class={vehicle_class}")
        
        self.current_track = track
        self.current_vehicle_class = vehicle_class
        
        # Update graph's selection
        if self.curve_graph:
            self.curve_graph.current_track = track
            self.curve_graph.selected_classes = [vehicle_class]
        
        # Load data for new selection
        self.load_current_data()
        self.update_all_display()
        
        # Refresh graph data
        if self.curve_graph:
            self.curve_graph.load_data()
            self.curve_graph.full_refresh()

    def on_qual_formula_changed(self, session_type: str, a: float, b: float):
        """Handle formula changes from qualifying panel"""
        self.qual_a = a
        self.qual_b = b
        if self.curve_graph:
            self.curve_graph.qual_a = a
            self.curve_graph.qual_b = b
            self.curve_graph.update_graph()
        
        # Save formula to database for the CURRENT selection
        if self.current_track and self.current_vehicle_class:
            from core_autopilot import Formula
            formula = Formula(
                track=self.current_track,
                vehicle_class=self.current_vehicle_class,
                a=a,
                b=b,
                session_type="qual",
                confidence=0.7
            )
            if formula.is_valid():
                self.autopilot_manager.formula_manager.save_formula(formula)
                logger.info(f"Saved qual formula for {self.current_track}/{self.current_vehicle_class}: T={a:.2f}/R+{b:.2f}")

    def on_race_formula_changed(self, session_type: str, a: float, b: float):
        """Handle formula changes from race panel"""
        self.race_a = a
        self.race_b = b
        if self.curve_graph:
            self.curve_graph.race_a = a
            self.curve_graph.race_b = b
            self.curve_graph.update_graph()
        
        # Save formula to database for the CURRENT selection
        if self.current_track and self.current_vehicle_class:
            from core_autopilot import Formula
            formula = Formula(
                track=self.current_track,
                vehicle_class=self.current_vehicle_class,
                a=a,
                b=b,
                session_type="race",
                confidence=0.7
            )
            if formula.is_valid():
                self.autopilot_manager.formula_manager.save_formula(formula)
                logger.info(f"Saved race formula for {self.current_track}/{self.current_vehicle_class}: T={a:.2f}/R+{b:.2f}")

    def on_show_data_toggled(self, session_type: str, show: bool):
        """Handle show/hide data toggles"""
        if self.curve_graph:
            if session_type == "qual":
                self.curve_graph.set_show_qualifying(show)
            else:
                self.curve_graph.set_show_race(show)

    def on_calculate_ratio(self, session_type: str, user_time: float):
        """Calculate ratio from user time and current formula, then update AIW file"""
        if not self.current_track:
            QMessageBox.warning(self, "No Track", "No track selected. Please select a track first.")
            return
        
        if not self.current_vehicle_class:
            QMessageBox.warning(self, "No Vehicle Class", "No vehicle class selected. Please select a class first.")
            return
        
        a = self.qual_a if session_type == "qual" else self.race_a
        b = self.qual_b if session_type == "qual" else self.race_b
        
        denominator = user_time - b
        if denominator <= 0:
            QMessageBox.warning(self, "Calculation Error", 
                f"Cannot calculate ratio: T - b = {user_time:.3f} - {b:.2f} = {denominator:.3f} (must be positive)")
            return
        
        new_ratio = a / denominator
        
        min_ratio, max_ratio = get_ratio_limits(self.config_file)
        
        if new_ratio < min_ratio or new_ratio > max_ratio:
            reply = QMessageBox.question(self, "Ratio Out of Range",
                f"The calculated ratio = {new_ratio:.6f} is outside the allowed range "
                f"({min_ratio} - {max_ratio}).\n\nDo you still want to save this ratio?",
                QMessageBox.Yes | QMessageBox.No)
            if reply != QMessageBox.Yes:
                return
        
        # Find the AIW file for the SELECTED track
        aiw_path = find_aiw_file_by_track(self.current_track, self.base_path)
        
        if not aiw_path or not aiw_path.exists():
            QMessageBox.warning(self, "AIW Not Found", 
                f"Could not find AIW file for track: {self.current_track}\n\n"
                f"Please ensure the track folder exists in GameData/Locations/")
            return
        
        ratio_name = "QualRatio" if session_type == "qual" else "RaceRatio"
        backup_dir = Path(self.db_path).parent / "aiw_backups"
        
        if update_aiw_ratio(aiw_path, ratio_name, new_ratio, backup_dir):
            if session_type == "qual":
                self.last_qual_ratio = new_ratio
                self.qual_panel.update_ratio(new_ratio)
            else:
                self.last_race_ratio = new_ratio
                self.race_panel.update_ratio(new_ratio)
            
            QMessageBox.information(self, "Success", 
                f"{ratio_name} updated to {new_ratio:.6f} in {aiw_path.name}")
            
            self.update_all_display()
        else:
            QMessageBox.critical(self, "Update Failed", 
                f"Failed to update {ratio_name} in the AIW file.")

    def on_auto_fit(self, session_type: str):
        """Auto-fit the curve to data points from the database for the selected track/class"""
        if not self.current_track or not self.current_vehicle_class:
            QMessageBox.warning(self, "No Data", 
                "No track or vehicle class selected. Please select a track and class first.")
            return
        
        logger.info(f"Auto-fit for {session_type} on {self.current_track}/{self.current_vehicle_class}")
        
        # Get data points from database for this track/class/session
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        session_filter = "qual" if session_type == "qual" else "race"
        cursor.execute("""
            SELECT ratio, lap_time FROM data_points 
            WHERE track = ? AND vehicle_class = ? AND session_type = ?
            ORDER BY ratio
        """, (self.current_track, self.current_vehicle_class, session_filter))
        
        rows = cursor.fetchall()
        conn.close()
        
        if len(rows) < 2:
            QMessageBox.warning(self, "Insufficient Data", 
                f"Need at least 2 data points to fit a curve.\n\n"
                f"Found {len(rows)} points for {self.current_track}/{self.current_vehicle_class}/{session_type}")
            return
        
        ratios = [row[0] for row in rows]
        times = [row[1] for row in rows]
        
        # Fit the curve
        a, b, avg_error, max_error, outlier_info = fit_curve(ratios, times, verbose=True)
        
        if a is not None and b is not None:
            if session_type == "qual":
                self.qual_a = a
                self.qual_b = b
                self.qual_panel.update_formula(a, b)
                self.qual_panel.set_calc_button_modified(False)
            else:
                self.race_a = a
                self.race_b = b
                self.race_panel.update_formula(a, b)
                self.race_panel.set_calc_button_modified(False)
            
            if self.curve_graph:
                self.curve_graph.set_formulas(self.qual_a, self.qual_b, self.race_a, self.race_b)
                self.curve_graph.update_graph()
            
            # Save formula to database for the SELECTED track/class
            from core_autopilot import Formula
            formula = Formula(
                track=self.current_track,
                vehicle_class=self.current_vehicle_class,
                a=a,
                b=b,
                session_type=session_filter,
                confidence=0.7,
                data_points_used=len(rows),
                avg_error=avg_error if avg_error else 0,
                max_error=max_error if max_error else 0
            )
            self.autopilot_manager.formula_manager.save_formula(formula)
            
            outlier_msg = ""
            if outlier_info and outlier_info.outliers_removed > 0:
                outlier_msg = f"\nRemoved {outlier_info.outliers_removed} outlier(s)."
            
            QMessageBox.information(self, "Auto-Fit Complete", 
                f"Fitted curve for {session_type.upper()} using {len(rows)} data points.\n\n"
                f"Formula: T = {a:.4f} / R + {b:.4f}\n"
                f"Average error: {avg_error:.3f}s\n"
                f"Max error: {max_error:.3f}s{outlier_msg}")
        else:
            QMessageBox.warning(self, "Fit Failed", 
                f"Could not fit a curve to the {len(rows)} data points.\n\n"
                f"Please ensure you have at least 2 valid data points.")

    def on_lap_time_edited(self, session_type: str, new_time: float):
        """Handle lap time editing from the session panel"""
        if self.current_track and self.current_vehicle_class:
            # Get the current ratio for this session
            current_ratio = self.last_qual_ratio if session_type == "qual" else self.last_race_ratio
            if current_ratio is None:
                current_ratio = 1.0
            
            self.user_laptimes_manager.add_laptime(
                self.current_track, self.current_vehicle_class, session_type,
                new_time, current_ratio
            )
            
            # Refresh the median time
            median_time = self.user_laptimes_manager.get_median_laptime_for_combo(
                self.current_track, self.current_vehicle_class, session_type
            )
            if median_time:
                if session_type == "qual":
                    self.median_qual_time = median_time
                    self.qual_panel.update_median_time(median_time)
                else:
                    self.median_race_time = median_time
                    self.race_panel.update_median_time(median_time)
            
            # Refresh user history for graph
            self.load_current_data()
            if self.curve_graph:
                self.curve_graph.update_current_info(
                    track=self.current_track,
                    vehicle=self.current_vehicle_class,
                    qual_time=self.user_qual_time,
                    race_time=self.user_race_time,
                    qual_ratio=self.last_qual_ratio,
                    race_ratio=self.last_race_ratio,
                    qual_history=self.user_qual_history,
                    race_history=self.user_race_history,
                    median_qual_time=self.median_qual_time,
                    median_race_time=self.median_race_time
                )
                self.curve_graph.update_graph()


def main():
    # Ensure config and database exist
    create_default_config_if_missing()
    db_path = get_db_path()
    if not Path(db_path).exists():
        CurveDatabase(db_path)

    setup_dark_theme(QApplication.instance() or QApplication(sys.argv))

    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)

    window = FormulaVisualizer()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
