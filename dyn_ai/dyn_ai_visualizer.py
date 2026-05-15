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
    QPushButton, QFrame
)
from PyQt5.QtCore import Qt, QFileSystemWatcher, QTimer

from core_database import CurveDatabase
from core_config import get_db_path, get_config_with_defaults, create_default_config_if_missing
from core_autopilot import get_vehicle_class, load_vehicle_classes, AutopilotManager
from core_formula import DEFAULT_A_VALUE
from gui_curve_graph import CurveGraphWidget
from gui_session_panel import SessionPanel
from gui_common import setup_dark_theme
from core_common import get_data_file_path


logger = logging.getLogger(__name__)


class FormulaVisualizer(QMainWindow):
    """Standalone Formula Visualizer window with real-time data"""

    def __init__(self, config_file: str = "cfg.yml"):
        super().__init__()
        self.config_file = config_file
        self.config = get_config_with_defaults(config_file)
        self.db_path = get_db_path(config_file)
        self.db = CurveDatabase(self.db_path)
        
        # Load vehicle classes
        vehicle_classes_path = get_data_file_path("vehicle_classes.json")
        self.class_mapping = load_vehicle_classes(vehicle_classes_path)
        
        # Initialize autopilot manager
        self.autopilot_manager = AutopilotManager(self.db)
        
        # Current state (mirrors main window)
        self.current_track = ""
        self.current_vehicle_class = ""
        self.current_vehicle = ""
        
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
        self.load_initial_data()
        self.setup_db_watcher()
        self.setup_refresh_timer()

    # ------------------------------------------------------------------
    # Database file watcher
    # ------------------------------------------------------------------

    def setup_db_watcher(self):
        """
        Watch the SQLite database file for changes made by other processes.
        """
        self._watcher = QFileSystemWatcher(self)
        self._watcher.addPath(self.db_path)
        
        # Also watch the WAL file for real-time updates
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
        self.load_current_data()
        self.update_all_display()
        if self.curve_graph:
            self.curve_graph.load_data()
            self.curve_graph.full_refresh()

    def _check_and_update(self):
        """Check for changes and update if needed"""
        old_track = self.current_track
        old_class = self.current_vehicle_class
        old_qual_time = self.user_qual_time
        old_race_time = self.user_race_time
        
        self.load_current_data()
        
        # Only update display if something changed
        if (old_track != self.current_track or 
            old_class != self.current_vehicle_class or
            old_qual_time != self.user_qual_time or
            old_race_time != self.user_race_time):
            self.update_all_display()

    # ------------------------------------------------------------------
    # Data loading
    # ------------------------------------------------------------------

    def load_current_data(self):
        """Load the current data from the database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get the most recent track from race_sessions
        cursor.execute("""
            SELECT track_name FROM race_sessions 
            WHERE track_name IS NOT NULL AND track_name != ''
            ORDER BY timestamp DESC LIMIT 1
        """)
        track_row = cursor.fetchone()
        
        if track_row:
            self.current_track = track_row[0]
            self.update_window_title()
        
        # Get the most recent vehicle class from user_laptimes
        if self.current_track:
            cursor.execute("""
                SELECT DISTINCT vehicle_class FROM user_laptimes 
                WHERE track = ?
                ORDER BY timestamp DESC LIMIT 1
            """, (self.current_track,))
            class_row = cursor.fetchone()
            
            if not class_row:
                cursor.execute("""
                    SELECT DISTINCT vehicle_class FROM data_points 
                    WHERE track = ?
                    ORDER BY created_at DESC LIMIT 1
                """, (self.current_track,))
                class_row = cursor.fetchone()
            
            if class_row:
                self.current_vehicle_class = class_row[0]
        
        # Load formulas for current track/class
        if self.current_track and self.current_vehicle_class:
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
        if self.current_track and self.current_vehicle_class:
            # Latest qualifying time
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
            
            # Latest race time
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
                ORDER BY lap_time
            """, (self.current_track, self.current_vehicle_class))
            qual_times = [row[0] for row in cursor.fetchall()]
            self.median_qual_time = self._calculate_median(qual_times) if qual_times else None
            
            cursor.execute("""
                SELECT lap_time FROM user_laptimes 
                WHERE track = ? AND vehicle_class = ? AND session_type = 'race'
                ORDER BY lap_time
            """, (self.current_track, self.current_vehicle_class))
            race_times = [row[0] for row in cursor.fetchall()]
            self.median_race_time = self._calculate_median(race_times) if race_times else None
            
            # AI times for range
            self.qual_best_ai, self.qual_worst_ai = self._get_ai_times_for_track(self.current_track, "qual")
            self.race_best_ai, self.race_worst_ai = self._get_ai_times_for_track(self.current_track, "race")
        
        conn.close()

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

    def update_window_title(self):
        """Update window title with current track"""
        if self.current_track:
            self.setWindowTitle(f"Dynamic AI - Formula Visualizer - {self.current_track}")
        else:
            self.setWindowTitle("Dynamic AI - Formula Visualizer")

    def update_all_display(self):
        """Update all display elements with current data"""
        # Update info bar
        if hasattr(self, 'track_label'):
            self.track_label.setText(self.current_track if self.current_track else "- No Track Selected -")
        if hasattr(self, 'class_label'):
            self.class_label.setText(self.current_vehicle_class if self.current_vehicle_class else "- No Car Selected -")
        
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

    # ------------------------------------------------------------------
    # UI setup
    # ------------------------------------------------------------------

    def setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # Info bar (shows track and car class)
        info_bar = self.create_info_bar()
        layout.addWidget(info_bar)

        # Curve graph
        self.curve_graph = CurveGraphWidget(self.db, self)
        layout.addWidget(self.curve_graph, stretch=3)

        # Session panels
        middle_layout = QHBoxLayout()
        middle_layout.setSpacing(15)

        self.qual_panel = SessionPanel("qual", "Qualifying Session", self.db, self)
        self.qual_panel.formula_changed.connect(self.on_qual_formula_changed)
        self.qual_panel.show_data_toggled.connect(self.on_show_data_toggled)
        middle_layout.addWidget(self.qual_panel)

        self.race_panel = SessionPanel("race", "Race Session", self.db, self)
        self.race_panel.formula_changed.connect(self.on_race_formula_changed)
        self.race_panel.show_data_toggled.connect(self.on_show_data_toggled)
        middle_layout.addWidget(self.race_panel)

        layout.addLayout(middle_layout, stretch=1)

    def create_info_bar(self):
        """Create the info bar showing track and car class"""
        info_bar = QFrame()
        info_bar.setStyleSheet("""
            QFrame {
                background-color: #2b2b2b;
                border-radius: 8px;
            }
            QLabel {
                color: white;
            }
        """)
        info_layout = QHBoxLayout(info_bar)
        info_layout.setContentsMargins(15, 10, 15, 10)

        # Track info
        track_container = QFrame()
        track_container.setStyleSheet("background-color: #1e1e1e; border-radius: 4px;")
        track_layout = QHBoxLayout(track_container)
        track_layout.setContentsMargins(10, 5, 10, 5)
        track_layout.addWidget(QLabel("Track:"))
        self.track_label = QLabel("- No Track Selected -")
        self.track_label.setStyleSheet("color: #FFA500; font-weight: bold;")
        track_layout.addWidget(self.track_label)
        info_layout.addWidget(track_container)

        info_layout.addSpacing(20)

        # Car class info
        class_container = QFrame()
        class_container.setStyleSheet("background-color: #1e1e1e; border-radius: 4px;")
        class_layout = QHBoxLayout(class_container)
        class_layout.setContentsMargins(10, 5, 10, 5)
        class_layout.addWidget(QLabel("Car Class:"))
        self.class_label = QLabel("- No Car Selected -")
        self.class_label.setStyleSheet("color: #4CAF50; font-weight: bold;")
        class_layout.addWidget(self.class_label)
        info_layout.addWidget(class_container)

        info_layout.addStretch()

        # Refresh button
        refresh_btn = QPushButton("Refresh")
        refresh_btn.setFixedWidth(80)
        refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 6px 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        refresh_btn.clicked.connect(self._do_full_refresh)
        info_layout.addWidget(refresh_btn)

        return info_bar

    # ------------------------------------------------------------------
    # Data loading
    # ------------------------------------------------------------------

    def load_initial_data(self):
        """Load initial data into the visualizer"""
        self.load_current_data()
        self.update_all_display()
        if self.curve_graph:
            self.curve_graph.load_data()
            self.curve_graph.full_refresh()

    # ------------------------------------------------------------------
    # Signal handlers
    # ------------------------------------------------------------------

    def on_qual_formula_changed(self, session_type: str, a: float, b: float):
        """Handle formula changes from qualifying panel"""
        self.qual_a = a
        self.qual_b = b
        if self.curve_graph:
            self.curve_graph.qual_a = a
            self.curve_graph.qual_b = b
            self.curve_graph.update_graph()

    def on_race_formula_changed(self, session_type: str, a: float, b: float):
        """Handle formula changes from race panel"""
        self.race_a = a
        self.race_b = b
        if self.curve_graph:
            self.curve_graph.race_a = a
            self.curve_graph.race_b = b
            self.curve_graph.update_graph()

    def on_show_data_toggled(self, session_type: str, show: bool):
        """Handle show/hide data toggles"""
        if self.curve_graph:
            if session_type == "qual":
                self.curve_graph.set_show_qualifying(show)
            else:
                self.curve_graph.set_show_race(show)


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
