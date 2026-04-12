#!/usr/bin/env python3
"""
Simple Curve Viewer - Uses minimal SQLite database
Database schema: data_points(track, vehicle, ratio, lap_time, session_type)
"""

import sys
import sqlite3
from pathlib import Path
from typing import List, Tuple

import numpy as np
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QListWidget, QDoubleSpinBox, QPushButton, QGroupBox,
    QSplitter, QMessageBox, QAbstractItemView
)
from PyQt5.QtCore import Qt

import matplotlib
matplotlib.use('Qt5Agg')
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar


DB_PATH = "ai_data.db"


class SimpleCurveViewer(QMainWindow):
    """Lightweight GUI for viewing hyperbolic curves with simple SQLite storage"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Curve Viewer - T = a/R + b")
        self.setGeometry(100, 100, 1200, 700)
        
        # Current state
        self.current_a: float = 30.0
        self.current_b: float = 70.0
        
        # Filter state
        self.show_qualifying: bool = True
        self.show_race: bool = True
        self.show_unknown: bool = True
        
        # Cache for tracks and vehicles
        self.all_tracks: List[str] = []
        self.all_vehicles: List[str] = []
        
        self.setup_ui()
        self.load_data()
        self.update_display()
    
    def setup_ui(self):
        """Setup the user interface"""
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(5, 5, 5, 5)
        
        # Left panel - controls
        left_panel = QWidget()
        left_panel.setFixedWidth(340)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setSpacing(10)
        
        # Instructions
        info_label = QLabel("Select tracks and vehicles to display data points.\n"
                           "Ctrl+Click = multi-select | Click = single")
        info_label.setStyleSheet("color: #888; font-size: 10px;")
        info_label.setWordWrap(True)
        left_layout.addWidget(info_label)
        
        # Track selection
        track_group = QGroupBox("Tracks")
        track_layout = QVBoxLayout(track_group)
        
        self.track_list = QListWidget()
        self.track_list.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.track_list.itemSelectionChanged.connect(self.on_selection_changed)
        track_layout.addWidget(self.track_list)
        
        track_btn_layout = QHBoxLayout()
        select_all_tracks = QPushButton("Select All")
        select_all_tracks.clicked.connect(lambda: self.track_list.selectAll())
        clear_tracks = QPushButton("Clear")
        clear_tracks.clicked.connect(lambda: self.track_list.clearSelection())
        track_btn_layout.addWidget(select_all_tracks)
        track_btn_layout.addWidget(clear_tracks)
        track_layout.addLayout(track_btn_layout)
        
        left_layout.addWidget(track_group)
        
        # Vehicle selection
        vehicle_group = QGroupBox("Vehicles")
        vehicle_layout = QVBoxLayout(vehicle_group)
        
        self.vehicle_list = QListWidget()
        self.vehicle_list.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.vehicle_list.itemSelectionChanged.connect(self.on_selection_changed)
        vehicle_layout.addWidget(self.vehicle_list)
        
        vehicle_btn_layout = QHBoxLayout()
        select_all_vehicles = QPushButton("Select All")
        select_all_vehicles.clicked.connect(lambda: self.vehicle_list.selectAll())
        clear_vehicles = QPushButton("Clear")
        clear_vehicles.clicked.connect(lambda: self.vehicle_list.clearSelection())
        vehicle_btn_layout.addWidget(select_all_vehicles)
        vehicle_btn_layout.addWidget(clear_vehicles)
        vehicle_layout.addLayout(vehicle_btn_layout)
        
        left_layout.addWidget(vehicle_group)
        
        # Data type selector - compact buttons side by side
        type_group = QGroupBox("Data Types")
        type_layout = QHBoxLayout(type_group)
        type_layout.setSpacing(8)
        
        self.qual_btn = QPushButton("Quali")
        self.qual_btn.setCheckable(True)
        self.qual_btn.setChecked(True)
        self.qual_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                padding: 4px 8px;
                font-size: 11px;
            }
            QPushButton:checked {
                background-color: #FFFF00;
                color: black;
                font-weight: bold;
            }
        """)
        self.qual_btn.clicked.connect(self.on_filter_buttons)
        type_layout.addWidget(self.qual_btn)
        
        self.race_btn = QPushButton("Race")
        self.race_btn.setCheckable(True)
        self.race_btn.setChecked(True)
        self.race_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                padding: 4px 8px;
                font-size: 11px;
            }
            QPushButton:checked {
                background-color: #FF6600;
                color: white;
                font-weight: bold;
            }
        """)
        self.race_btn.clicked.connect(self.on_filter_buttons)
        type_layout.addWidget(self.race_btn)
        
        self.unkn_btn = QPushButton("Unknw")
        self.unkn_btn.setCheckable(True)
        self.unkn_btn.setChecked(True)
        self.unkn_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                padding: 4px 8px;
                font-size: 11px;
            }
            QPushButton:checked {
                background-color: #FF00FF;
                color: white;
                font-weight: bold;
            }
        """)
        self.unkn_btn.clicked.connect(self.on_filter_buttons)
        type_layout.addWidget(self.unkn_btn)
        
        type_layout.addStretch()
        left_layout.addWidget(type_group)
        
        # Formula parameters - with visual descriptions
        param_group = QGroupBox("Curve Parameters: T = a / R + b")
        param_layout = QVBoxLayout(param_group)
        
        # a parameter (height/sensitivity)
        a_layout = QHBoxLayout()
        a_label = QLabel("Height (a):")
        a_label.setToolTip("Controls how steep the curve is. Higher = more sensitive to ratio changes")
        a_layout.addWidget(a_label)
        self.a_spin = QDoubleSpinBox()
        self.a_spin.setRange(0.01, 500.0)
        self.a_spin.setDecimals(3)
        self.a_spin.setSingleStep(1.0)
        self.a_spin.setValue(30.0)
        self.a_spin.valueChanged.connect(self.on_param_changed)
        a_layout.addWidget(self.a_spin)
        param_layout.addLayout(a_layout)
        
        # b parameter (floor/base time)
        b_layout = QHBoxLayout()
        b_label = QLabel("Base (b):")
        b_label.setToolTip("Minimum lap time in seconds. The curve approaches this as ratio increases")
        b_layout.addWidget(b_label)
        self.b_spin = QDoubleSpinBox()
        self.b_spin.setRange(0.01, 200.0)
        self.b_spin.setDecimals(3)
        self.b_spin.setSingleStep(0.5)
        self.b_spin.setValue(70.0)
        self.b_spin.valueChanged.connect(self.on_param_changed)
        b_layout.addWidget(self.b_spin)
        param_layout.addLayout(b_layout)
        
        # Derived values
        info_layout = QVBoxLayout()
        self.k_label = QLabel("Steepness k = a/(a+b) = ---")
        self.k_label.setToolTip("k close to 0 = shallow curve, k close to 1 = steep curve")
        self.k_label.setStyleSheet("color: #888;")
        info_layout.addWidget(self.k_label)
        
        self.m_label = QLabel("Time at R=1.0 = a+b = ---")
        self.m_label.setStyleSheet("color: #888;")
        info_layout.addWidget(self.m_label)
        
        param_layout.addLayout(info_layout)
        left_layout.addWidget(param_group)
        
        # Buttons
        btn_layout = QVBoxLayout()
        
        self.fit_btn = QPushButton("Auto-Fit to Selected Data")
        self.fit_btn.setStyleSheet("background-color: #4CAF50;")
        self.fit_btn.clicked.connect(self.auto_fit)
        btn_layout.addWidget(self.fit_btn)
        
        reset_btn = QPushButton("Reset View")
        reset_btn.clicked.connect(self.reset_view)
        btn_layout.addWidget(reset_btn)
        
        # Exit button (red)
        exit_btn = QPushButton("Exit")
        exit_btn.setStyleSheet("background-color: #f44336;")
        exit_btn.clicked.connect(self.close)
        btn_layout.addWidget(exit_btn)
        
        left_layout.addLayout(btn_layout)
        left_layout.addStretch()
        
        # Stats label at bottom
        self.stats_label = QLabel("")
        self.stats_label.setStyleSheet("color: #888; padding: 5px;")
        self.stats_label.setWordWrap(True)
        left_layout.addWidget(self.stats_label)
        
        # Right panel - plot
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        
        # Matplotlib figure
        self.figure = Figure(figsize=(8, 6), facecolor='#1e1e1e')
        self.canvas = FigureCanvas(self.figure)
        self.toolbar = NavigationToolbar(self.canvas, self)
        
        self.ax = self.figure.add_subplot(111)
        self.ax.set_facecolor('#2b2b2b')
        
        # Styling
        for spine in self.ax.spines.values():
            spine.set_color('#4CAF50')
        self.ax.tick_params(colors='white')
        self.ax.xaxis.label.set_color('white')
        self.ax.yaxis.label.set_color('white')
        self.ax.title.set_color('#FFA500')
        
        self.ax.set_xlabel('Ratio (R)', fontsize=11)
        self.ax.set_ylabel('Lap Time (seconds)', fontsize=11)
        self.ax.set_title('Hyperbolic Curve: T = a / R + b', fontsize=12)
        self.ax.grid(True, alpha=0.3)
        self.ax.set_xlim(0.5, 2.0)
        self.ax.set_ylim(50, 200)
        
        right_layout.addWidget(self.toolbar)
        right_layout.addWidget(self.canvas)
        
        # Splitter
        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setSizes([340, 860])
        main_layout.addWidget(splitter)
        
        # Update labels
        self._update_labels()
    
    def on_filter_buttons(self):
        """Handle filter button toggles"""
        self.show_qualifying = self.qual_btn.isChecked()
        self.show_race = self.race_btn.isChecked()
        self.show_unknown = self.unkn_btn.isChecked()
        self.update_display()
    
    def load_data(self):
        """Load tracks and vehicles from database"""
        if not Path(DB_PATH).exists():
            print(f"Database not found: {DB_PATH}")
            print("Run import_to_simple_db.py first to import your data")
            return
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Get all tracks
        cursor.execute("SELECT DISTINCT track FROM data_points ORDER BY track")
        self.all_tracks = [row[0] for row in cursor.fetchall()]
        
        # Get all vehicles
        cursor.execute("SELECT DISTINCT vehicle FROM data_points ORDER BY vehicle")
        self.all_vehicles = [row[0] for row in cursor.fetchall()]
        
        # Get total points
        cursor.execute("SELECT COUNT(*) FROM data_points")
        total_points = cursor.fetchone()[0]
        
        # Get points by type
        cursor.execute("SELECT session_type, COUNT(*) FROM data_points GROUP BY session_type")
        by_type = cursor.fetchall()
        
        conn.close()
        
        # Populate lists
        self.track_list.clear()
        for track in self.all_tracks:
            self.track_list.addItem(track)
        
        self.vehicle_list.clear()
        for vehicle in self.all_vehicles:
            self.vehicle_list.addItem(vehicle)
        
        # Auto-select first items if available
        if self.all_tracks:
            self.track_list.setCurrentRow(0)
        if self.all_vehicles:
            self.vehicle_list.setCurrentRow(0)
        
        # Update stats label
        type_str = ", ".join([f"{t}: {c}" for t, c in by_type])
        self.stats_label.setText(f"Total points: {total_points}\n{type_str}")
        
        print(f"Loaded {total_points} points from database")
        print(f"  Tracks: {len(self.all_tracks)}")
        print(f"  Vehicles: {len(self.all_vehicles)}")
    
    def get_selected_data(self) -> List[Tuple[float, float, str]]:
        """Get all data points from selected tracks and vehicles, filtered by type"""
        selected_tracks = [item.text() for item in self.track_list.selectedItems()]
        selected_vehicles = [item.text() for item in self.vehicle_list.selectedItems()]
        
        if not selected_tracks or not selected_vehicles:
            return []
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Build query with placeholders
        track_placeholders = ','.join(['?' for _ in selected_tracks])
        vehicle_placeholders = ','.join(['?' for _ in selected_vehicles])
        
        # Build session type filter
        session_filters = []
        
        if self.show_qualifying:
            session_filters.append("session_type = 'qual'")
        if self.show_race:
            session_filters.append("session_type = 'race'")
        if self.show_unknown:
            session_filters.append("session_type = 'unknown'")
        
        session_clause = ""
        if session_filters:
            session_clause = f"AND ({' OR '.join(session_filters)})"
        
        query = f"""
            SELECT ratio, lap_time, session_type 
            FROM data_points 
            WHERE track IN ({track_placeholders}) 
            AND vehicle IN ({vehicle_placeholders})
            {session_clause}
            ORDER BY ratio
        """
        
        params = selected_tracks + selected_vehicles
        cursor.execute(query, params)
        
        points = [(row[0], row[1], row[2]) for row in cursor.fetchall()]
        conn.close()
        
        return points
    
    def on_selection_changed(self):
        """Handle selection changes"""
        self.update_display()
    
    def on_param_changed(self):
        """Handle parameter changes"""
        self.current_a = self.a_spin.value()
        self.current_b = self.b_spin.value()
        self._update_labels()
        self.update_display()
    
    def _update_labels(self):
        """Update derived value labels"""
        M = self.current_a + self.current_b
        k = self.current_a / M if M > 0 else 0
        self.k_label.setText(f"Steepness k = a/(a+b) = {k:.4f}")
        self.m_label.setText(f"Time at R=1.0 = {M:.3f} s")
    
    def auto_fit(self):
        """Fit hyperbolic curve to selected data points"""
        points = self.get_selected_data()
        
        if len(points) < 2:
            QMessageBox.warning(self, "Insufficient Data", 
                               f"Need at least 2 data points to fit.\nCurrently have {len(points)} selected.\n\n"
                               f"Select more tracks/vehicles or add more data points.")
            return
        
        ratios = np.array([p[0] for p in points])
        times = np.array([p[1] for p in points])
        
        def hyperbolic(R, a, b):
            return a / R + b
        
        try:
            # Use first two points for initial guess
            r1, t1 = points[0][0], points[0][1]
            r2, t2 = points[1][0], points[1][1]
            inv_r1 = 1.0 / r1
            inv_r2 = 1.0 / r2
            
            if abs(inv_r1 - inv_r2) > 1e-9:
                a_guess = (t1 - t2) / (inv_r1 - inv_r2)
                b_guess = t1 - a_guess * inv_r1
            else:
                a_guess = 30.0
                b_guess = 70.0
            
            from scipy.optimize import curve_fit
            popt, _ = curve_fit(hyperbolic, ratios, times, p0=[a_guess, b_guess])
            a, b = popt
            
            self.a_spin.setValue(a)
            self.b_spin.setValue(b)
            
            # Calculate error
            predictions = hyperbolic(ratios, a, b)
            errors = np.abs(times - predictions)
            avg_error = np.mean(errors)
            max_error = np.max(errors)
            
            QMessageBox.information(self, "Fit Complete",
                                   f"Fitted curve: a = {a:.3f}, b = {b:.3f}\n"
                                   f"Data points used: {len(points)}\n"
                                   f"Average error: {avg_error:.3f} seconds\n"
                                   f"Max error: {max_error:.3f} seconds")
            
        except Exception as e:
            QMessageBox.critical(self, "Fit Failed", f"Could not fit curve:\n{str(e)}")
    
    def update_display(self):
        """Update the plot"""
        self.ax.clear()
        
        # Restyle
        self.ax.set_facecolor('#2b2b2b')
        for spine in self.ax.spines.values():
            spine.set_color('#4CAF50')
        self.ax.tick_params(colors='white')
        self.ax.xaxis.label.set_color('white')
        self.ax.yaxis.label.set_color('white')
        self.ax.title.set_color('#FFA500')
        self.ax.set_xlabel('Ratio (R)', fontsize=11)
        self.ax.set_ylabel('Lap Time (seconds)', fontsize=11)
        self.ax.set_title('Hyperbolic Curve: T = a / R + b', fontsize=12)
        self.ax.grid(True, alpha=0.3)
        self.ax.set_xlim(0.5, 2.0)
        self.ax.set_ylim(50, 200)
        
        # Plot curve
        ratios = np.linspace(0.5, 2.0, 200)
        times = self.current_a / ratios + self.current_b
        self.ax.plot(ratios, times, '#00FFFF', linewidth=2.5, 
                    label=f'T = {self.current_a:.3f}/R + {self.current_b:.3f}')
        
        # Get selected data
        points = self.get_selected_data()
        
        if points:
            quali_points = [(r, t) for r, t, st in points if st == 'qual']
            race_points = [(r, t) for r, t, st in points if st == 'race']
            unknown_points = [(r, t) for r, t, st in points if st == 'unknown']
            
            # Point size: 9 = 3 pixels diameter (3^2)
            point_size = 9
            
            # Plot quali points (circles) - Bright Yellow
            if quali_points:
                r = [p[0] for p in quali_points]
                t = [p[1] for p in quali_points]
                self.ax.scatter(r, t, c='#FFFF00', s=point_size, alpha=0.9,
                              edgecolors='none', zorder=3,
                              marker='o', label=f'Qualifying ({len(quali_points)})')
            
            # Plot race points (squares) - Bright Orange
            if race_points:
                r = [p[0] for p in race_points]
                t = [p[1] for p in race_points]
                self.ax.scatter(r, t, c='#FF6600', s=point_size, alpha=0.9,
                              edgecolors='none', zorder=3,
                              marker='s', label=f'Race ({len(race_points)})')
            
            # Plot unknown points (triangles) - Magenta
            if unknown_points:
                r = [p[0] for p in unknown_points]
                t = [p[1] for p in unknown_points]
                self.ax.scatter(r, t, c='#FF00FF', s=point_size, alpha=0.9,
                              edgecolors='none', zorder=3,
                              marker='^', label=f'Unknown ({len(unknown_points)})')
            
            # Legend with larger markers for visibility
            self.ax.legend(loc='upper right', framealpha=0.8,
                          facecolor='#2b2b2b', edgecolor='#4CAF50',
                          labelcolor='white', fontsize=9, markerscale=2)
        else:
            # Show only curve in legend
            self.ax.legend(loc='upper right', framealpha=0.8,
                          facecolor='#2b2b2b', edgecolor='#4CAF50',
                          labelcolor='white', fontsize=9)
        
        self.canvas.draw()
        
        # Update status bar
        selected_tracks = len(self.track_list.selectedItems())
        selected_vehicles = len(self.vehicle_list.selectedItems())
        self.statusBar().showMessage(
            f"Tracks: {selected_tracks} | Vehicles: {selected_vehicles} | Data points: {len(points)}"
        )
    
    def reset_view(self):
        """Reset the plot to default view"""
        self.ax.set_xlim(0.5, 2.0)
        self.ax.set_ylim(50, 200)
        self.canvas.draw()


def main():
    # Check if database exists
    if not Path(DB_PATH).exists():
        print(f"\n{'='*60}")
        print("DATABASE NOT FOUND")
        print(f"{'='*60}")
        print(f"\nDatabase '{DB_PATH}' does not exist.")
        print("\nPlease run the importer first to migrate your existing data.")
        print("Update the importer to use 'ai_data.db' as the database name.")
        print(f"\n{'='*60}\n")
        
        # Ask if user wants to create empty database
        reply = input("Create an empty database and continue? (y/n): ").lower().strip()
        if reply == 'y':
            # Initialize empty database
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS data_points (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    track TEXT NOT NULL,
                    vehicle TEXT NOT NULL,
                    ratio REAL NOT NULL,
                    lap_time REAL NOT NULL,
                    session_type TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_track ON data_points(track)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_vehicle ON data_points(vehicle)")
            conn.commit()
            conn.close()
            print(f"\nCreated empty database: {DB_PATH}\n")
        else:
            print("\nExiting. Run importer first.\n")
            return
    
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    # Dark theme styling
    app.setStyleSheet("""
        QMainWindow, QWidget {
            background-color: #1e1e1e;
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
        QListWidget {
            background-color: #2b2b2b;
            color: white;
            border: 1px solid #4CAF50;
            border-radius: 3px;
            outline: none;
        }
        QListWidget::item:selected {
            background-color: #4CAF50;
            color: white;
        }
        QListWidget::item:hover {
            background-color: #3c3c3c;
        }
        QDoubleSpinBox {
            background-color: #3c3c3c;
            color: white;
            border: 1px solid #4CAF50;
            border-radius: 3px;
            padding: 4px;
        }
        QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {
            background-color: #4CAF50;
            width: 16px;
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
        QStatusBar {
            color: #888;
        }
    """)
    
    window = SimpleCurveViewer()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
