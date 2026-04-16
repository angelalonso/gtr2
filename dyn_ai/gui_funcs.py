# gui_funcs.py - Updated with graph and data management
#!/usr/bin/env python3
"""
GUI module for curve viewer
Provides reusable GUI components and dialogs using pyqtgraph for lightweight plotting
"""

import logging
import numpy as np
import shutil
import sqlite3
from pathlib import Path
from datetime import datetime
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QListWidget, 
    QDoubleSpinBox, QPushButton, QGroupBox, QSplitter, 
    QMessageBox, QAbstractItemView, QComboBox, QDialog,
    QDialogButtonBox, QListWidgetItem, QSlider, QSpinBox,
    QCheckBox, QTabWidget, QTableWidget, QTableWidgetItem,
    QHeaderView, QScrollArea, QFileDialog, QSizePolicy, QRadioButton,
    QTextEdit, QSplitter
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor
import pyqtgraph as pg

from formula_funcs import fit_curve, get_formula_string, hyperbolic
#from data_extraction import get_vehicle_class
from autopilot import load_vehicle_classes, get_vehicle_class


class MultiTrackSelectionDialog(QDialog):
    """Dialog for selecting multiple tracks"""
    
    def __init__(self, all_tracks, current_track, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select Multiple Tracks")
        self.setGeometry(300, 300, 400, 500)
        self.all_tracks = all_tracks
        self.current_track = current_track
        self.selected_tracks = [current_track] if current_track else []
        
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        info_label = QLabel("Select tracks to display data from.\n"
                           "Ctrl+Click = multi-select | Shift+Click = range")
        info_label.setStyleSheet("color: #888; font-size: 10px;")
        info_label.setWordWrap(True)
        layout.addWidget(info_label)
        
        self.track_list = QListWidget()
        self.track_list.setSelectionMode(QAbstractItemView.ExtendedSelection)
        
        for i, track in enumerate(self.all_tracks):
            item = QListWidgetItem(track)
            self.track_list.addItem(item)
            if track == self.current_track:
                item.setSelected(True)
                self.track_list.setCurrentItem(item)
        
        layout.addWidget(self.track_list)
        
        btn_layout = QHBoxLayout()
        select_all_btn = QPushButton("Select All")
        select_all_btn.clicked.connect(self.track_list.selectAll)
        btn_layout.addWidget(select_all_btn)
        
        clear_btn = QPushButton("Clear All")
        clear_btn.clicked.connect(self.track_list.clearSelection)
        btn_layout.addWidget(clear_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
    def get_selected_tracks(self):
        return [item.text() for item in self.track_list.selectedItems()]


class LogWindow(QDialog):
    """Separate window for displaying logs on demand"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Live AI Tuner - Log Viewer")
        self.setGeometry(200, 200, 800, 500)
        
        self.log_buffer = []
        self.max_lines = 1000
        self.current_level = "INFO"
        
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Controls at top
        control_layout = QHBoxLayout()
        
        # Log level filter
        control_layout.addWidget(QLabel("Show level:"))
        self.level_combo = QComboBox()
        self.level_combo.addItems(["ERROR", "WARNING", "INFO", "DEBUG", "ALL"])
        self.level_combo.setCurrentText("INFO")
        self.level_combo.currentTextChanged.connect(self.on_level_changed)
        control_layout.addWidget(self.level_combo)
        
        control_layout.addWidget(QLabel("Max lines:"))
        self.max_lines_spin = QSpinBox()
        self.max_lines_spin.setRange(100, 10000)
        self.max_lines_spin.setValue(1000)
        self.max_lines_spin.valueChanged.connect(self.on_max_lines_changed)
        control_layout.addWidget(self.max_lines_spin)
        
        control_layout.addStretch()
        
        # Clear button
        self.clear_btn = QPushButton("Clear")
        self.clear_btn.clicked.connect(self.clear_log)
        control_layout.addWidget(self.clear_btn)
        
        # Auto-scroll checkbox
        self.auto_scroll_cb = QCheckBox("Auto-scroll")
        self.auto_scroll_cb.setChecked(True)
        control_layout.addWidget(self.auto_scroll_cb)
        
        layout.addLayout(control_layout)
        
        # Log text area
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFontFamily("Courier New")
        self.log_text.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #d4d4d4;
                font-size: 10px;
            }
        """)
        layout.addWidget(self.log_text)
        
    def add_log(self, level: str, message: str):
        """Add a log message to the buffer and display"""
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        formatted = f"[{timestamp}] [{level:7}] {message}"
        
        self.log_buffer.append((level, formatted))
        
        # Trim buffer
        if len(self.log_buffer) > self.max_lines:
            self.log_buffer = self.log_buffer[-self.max_lines:]
        
        # Update display if level matches filter
        self._update_display()
        
    def _update_display(self):
        """Update the display based on current filter"""
        level_map = {
            "ERROR": 40,
            "WARNING": 30,
            "INFO": 20,
            "DEBUG": 10,
            "ALL": 0
        }
        min_level = level_map.get(self.current_level, 20)
        
        level_values = {
            "ERROR": 40,
            "WARNING": 30,
            "INFO": 20,
            "DEBUG": 10
        }
        
        # Color mapping
        color_map = {
            "ERROR": "#f44336",
            "WARNING": "#ff9800",
            "INFO": "#4caf50",
            "DEBUG": "#9e9e9e"
        }
        
        html_lines = []
        for level, formatted in self.log_buffer:
            if self.current_level == "ALL" or level_values.get(level, 0) >= min_level:
                color = color_map.get(level, "#ffffff")
                html_lines.append(f'<span style="color: {color};">{formatted}</span>')
        
        if self.auto_scroll_cb.isChecked():
            self.log_text.setHtml("<br>".join(html_lines))
            scrollbar = self.log_text.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())
        else:
            self.log_text.setHtml("<br>".join(html_lines))
        
    def on_level_changed(self, level: str):
        """Handle log level change"""
        self.current_level = level
        self._update_display()
        
    def on_max_lines_changed(self, value: int):
        """Handle max lines change"""
        self.max_lines = value
        if len(self.log_buffer) > self.max_lines:
            self.log_buffer = self.log_buffer[-self.max_lines:]
        self._update_display()
        
    def clear_log(self):
        """Clear the log buffer and display"""
        self.log_buffer.clear()
        self.log_text.clear()


class SimpleLogHandler(logging.Handler):
    """Custom logging handler that sends logs to the GUI window"""
    
    def __init__(self, log_window: LogWindow):
        super().__init__()
        self.log_window = log_window
        
    def emit(self, record):
        try:
            level = record.levelname
            message = self.format(record)
            self.log_window.add_log(level, message)
        except Exception:
            pass


class CurveGraphWidget(QWidget):
    """Widget containing the curve graph and data management"""
    
    point_selected = pyqtSignal(str, str, float, float)  # track, vehicle, ratio, lap_time
    
    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self.class_mapping = load_vehicle_classes()
        
        # Current state
        self.qual_a = 30.0
        self.qual_b = 70.0
        self.race_a = 30.0
        self.race_b = 70.0
        self.show_qualifying = True
        self.show_race = True
        self.show_unknown = True
        
        # Data
        self.all_tracks = []
        self.all_vehicles = []
        self.current_track = ""
        self.selected_vehicles = []
        self.multi_track_mode = False
        self.selected_tracks = []
        
        # Plot items
        self.qual_curve = None
        self.race_curve = None
        self.qual_scatter = None
        self.race_scatter = None
        self.unknown_scatter = None
        self.legend = None
        self.selected_point_marker = None
        
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Filter controls
        filter_layout = QHBoxLayout()
        
        filter_layout.addWidget(QLabel("Tracks:"))
        self.track_combo = QComboBox()
        self.track_combo.currentTextChanged.connect(self.on_track_changed)
        filter_layout.addWidget(self.track_combo)
        
        self.multi_track_btn = QPushButton("Multi")
        self.multi_track_btn.setFixedWidth(40)
        self.multi_track_btn.clicked.connect(self.open_multi_track)
        filter_layout.addWidget(self.multi_track_btn)
        
        filter_layout.addSpacing(20)
        
        filter_layout.addWidget(QLabel("Vehicles:"))
        self.vehicle_list = QListWidget()
        self.vehicle_list.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.vehicle_list.setMaximumHeight(80)
        self.vehicle_list.itemSelectionChanged.connect(self.on_vehicles_changed)
        filter_layout.addWidget(self.vehicle_list)
        
        filter_layout.addSpacing(20)
        
        self.qual_check = QCheckBox("Qualifying")
        self.qual_check.setChecked(True)
        self.qual_check.setStyleSheet("color: #FFFF00;")
        self.qual_check.stateChanged.connect(self.on_filter_changed)
        filter_layout.addWidget(self.qual_check)
        
        self.race_check = QCheckBox("Race")
        self.race_check.setChecked(True)
        self.race_check.setStyleSheet("color: #FF6600;")
        self.race_check.stateChanged.connect(self.on_filter_changed)
        filter_layout.addWidget(self.race_check)
        
        self.unknown_check = QCheckBox("Unknown")
        self.unknown_check.setChecked(True)
        self.unknown_check.setStyleSheet("color: #FF00FF;")
        self.unknown_check.stateChanged.connect(self.on_filter_changed)
        filter_layout.addWidget(self.unknown_check)
        
        filter_layout.addStretch()
        layout.addLayout(filter_layout)
        
        # Plot widget
        self.plot_widget = pg.GraphicsLayoutWidget()
        self.plot_widget.setBackground('#2b2b2b')
        self.plot = self.plot_widget.addPlot()
        self.plot.setLabel('bottom', 'Ratio (R)', color='white', size='11pt')
        self.plot.setLabel('left', 'Lap Time (seconds)', color='white', size='11pt')
        self.plot.setTitle('Hyperbolic Curves: T = a / R + b', color='#FFA500', size='12pt')
        self.plot.showGrid(x=True, y=True, alpha=0.3)
        self.plot.setXRange(0.4, 2.0)
        self.plot.setYRange(50, 200)
        
        self.plot.getAxis('bottom').setPen('white')
        self.plot.getAxis('bottom').setTextPen('white')
        self.plot.getAxis('left').setPen('white')
        self.plot.getAxis('left').setTextPen('white')
        
        # Enable point clicking
        self.plot.scene().sigMouseClicked.connect(self.on_plot_click)
        
        layout.addWidget(self.plot_widget)
        
        # Manual curve controls
        manual_group = QGroupBox("Manual Curve Adjustment")
        manual_layout = QHBoxLayout(manual_group)
        
        manual_layout.addWidget(QLabel("Curve:"))
        self.curve_selector = QComboBox()
        self.curve_selector.addItem("Qualifying (Yellow)", "qual")
        self.curve_selector.addItem("Race (Orange)", "race")
        self.curve_selector.currentIndexChanged.connect(self.on_curve_selected)
        manual_layout.addWidget(self.curve_selector)
        
        manual_layout.addWidget(QLabel("a:"))
        self.a_spin = QDoubleSpinBox()
        self.a_spin.setRange(0.01, 500.0)
        self.a_spin.setDecimals(3)
        self.a_spin.setValue(30.0)
        manual_layout.addWidget(self.a_spin)
        
        manual_layout.addWidget(QLabel("b:"))
        self.b_spin = QDoubleSpinBox()
        self.b_spin.setRange(0.01, 200.0)
        self.b_spin.setDecimals(3)
        self.b_spin.setValue(70.0)
        manual_layout.addWidget(self.b_spin)
        
        self.apply_btn = QPushButton("Apply")
        self.apply_btn.clicked.connect(self.apply_manual_curve)
        manual_layout.addWidget(self.apply_btn)
        
        self.auto_fit_btn = QPushButton("Auto-Fit")
        self.auto_fit_btn.clicked.connect(self.auto_fit)
        manual_layout.addWidget(self.auto_fit_btn)
        
        self.reset_view_btn = QPushButton("Reset View")
        self.reset_view_btn.clicked.connect(self.reset_view)
        manual_layout.addWidget(self.reset_view_btn)
        
        layout.addWidget(manual_group)
        
        # Data table
        table_group = QGroupBox("Data Points")
        table_layout = QVBoxLayout(table_group)
        
        self.data_table = QTableWidget()
        self.data_table.setColumnCount(5)
        self.data_table.setHorizontalHeaderLabels(["Track", "Vehicle", "Ratio", "Lap Time", "Session"])
        self.data_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.data_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.data_table.setAlternatingRowColors(True)
        self.data_table.itemSelectionChanged.connect(self.on_table_selection_changed)
        table_layout.addWidget(self.data_table)
        
        table_btn_layout = QHBoxLayout()
        
        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self.load_data)
        table_btn_layout.addWidget(refresh_btn)
        
        delete_btn = QPushButton("Delete Selected")
        delete_btn.setStyleSheet("background-color: #f44336;")
        delete_btn.clicked.connect(self.delete_selected_points)
        table_btn_layout.addWidget(delete_btn)
        
        table_btn_layout.addStretch()
        table_layout.addLayout(table_btn_layout)
        
        layout.addWidget(table_group)
        
        # Formula info
        info_layout = QHBoxLayout()
        self.formula_label = QLabel("")
        self.formula_label.setStyleSheet("color: #888; font-size: 10px; font-family: monospace;")
        info_layout.addWidget(self.formula_label)
        info_layout.addStretch()
        layout.addLayout(info_layout)
        
    def load_data(self):
        """Load tracks, vehicles, and data points"""
        if not self.db.database_exists():
            return
        
        conn = sqlite3.connect(self.db.db_path)
        cursor = conn.cursor()
        
        # Load tracks
        cursor.execute("SELECT DISTINCT track FROM data_points ORDER BY track")
        self.all_tracks = [row[0] for row in cursor.fetchall()]
        
        # Load vehicles
        cursor.execute("SELECT DISTINCT vehicle FROM data_points ORDER BY vehicle")
        self.all_vehicles = [row[0] for row in cursor.fetchall()]
        
        # Update track combo
        self.track_combo.clear()
        for track in self.all_tracks:
            self.track_combo.addItem(track)
        if self.current_track and self.current_track in self.all_tracks:
            self.track_combo.setCurrentText(self.current_track)
        elif self.all_tracks:
            self.current_track = self.all_tracks[0]
            self.track_combo.setCurrentIndex(0)
        
        # Update vehicle list
        self.vehicle_list.clear()
        for vehicle in self.all_vehicles:
            self.vehicle_list.addItem(vehicle)
        if not self.selected_vehicles:
            self.vehicle_list.selectAll()
            self.selected_vehicles = self.all_vehicles.copy()
        
        # Load data table
        self._load_data_table()
        
        conn.close()
        
        # Update graph
        self.update_graph()
        
    def _load_data_table(self):
        """Load data points into table"""
        if not self.current_track:
            return
        
        conn = sqlite3.connect(self.db.db_path)
        cursor = conn.cursor()
        
        # Build vehicle filter
        if self.selected_vehicles:
            placeholders = ','.join('?' * len(self.selected_vehicles))
            query = f"""
                SELECT track, vehicle, ratio, lap_time, session_type 
                FROM data_points 
                WHERE track = ? AND vehicle IN ({placeholders})
                ORDER BY session_type, ratio
            """
            cursor.execute(query, [self.current_track] + self.selected_vehicles)
        else:
            cursor.execute("""
                SELECT track, vehicle, ratio, lap_time, session_type 
                FROM data_points 
                WHERE track = ?
                ORDER BY session_type, ratio
            """, (self.current_track,))
        
        rows = cursor.fetchall()
        conn.close()
        
        self.data_table.setRowCount(len(rows))
        for i, row in enumerate(rows):
            for j, value in enumerate(row):
                item = QTableWidgetItem(str(value))
                self.data_table.setItem(i, j, item)
            
            # Color rows by session type
            session = row[4]
            if session == 'qual':
                color = QColor(58, 58, 0)
            elif session == 'race':
                color = QColor(58, 26, 0)
            else:
                color = QColor(42, 0, 58)
            
            for j in range(5):
                item = self.data_table.item(i, j)
                if item:
                    item.setBackground(color)
        
        self.data_table.resizeRowsToContents()
        
    def on_track_changed(self, track):
        """Handle track selection change"""
        self.current_track = track
        self._load_data_table()
        self.update_graph()
        
    def on_vehicles_changed(self):
        """Handle vehicle selection change"""
        self.selected_vehicles = [item.text() for item in self.vehicle_list.selectedItems()]
        if not self.selected_vehicles:
            self.selected_vehicles = self.all_vehicles.copy()
        self._load_data_table()
        self.update_graph()
        
    def on_filter_changed(self):
        """Handle filter checkbox changes"""
        self.show_qualifying = self.qual_check.isChecked()
        self.show_race = self.race_check.isChecked()
        self.show_unknown = self.unknown_check.isChecked()
        self.update_graph()
        
    def on_curve_selected(self):
        """Handle curve selection change"""
        curve = self.curve_selector.currentData()
        if curve == "qual":
            self.a_spin.setValue(self.qual_a)
            self.b_spin.setValue(self.qual_b)
        else:
            self.a_spin.setValue(self.race_a)
            self.b_spin.setValue(self.race_b)
            
    def apply_manual_curve(self):
        """Apply manually edited curve"""
        a = self.a_spin.value()
        b = self.b_spin.value()
        
        curve = self.curve_selector.currentData()
        if curve == "qual":
            self.qual_a = a
            self.qual_b = b
        else:
            self.race_a = a
            self.race_b = b
        
        self.update_graph()
        
    def auto_fit(self):
        """Auto-fit curves to data"""
        points_data = self.get_selected_data()
        
        # Fit qualifying
        if points_data['quali'] and len(points_data['quali']) >= 2:
            ratios = [p[0] for p in points_data['quali']]
            times = [p[1] for p in points_data['quali']]
            a, b, avg_err, max_err = fit_curve(ratios, times, verbose=False)
            if a and b and a > 0 and b > 0:
                self.qual_a = a
                self.qual_b = b
        
        # Fit race
        if points_data['race'] and len(points_data['race']) >= 2:
            ratios = [p[0] for p in points_data['race']]
            times = [p[1] for p in points_data['race']]
            a, b, avg_err, max_err = fit_curve(ratios, times, verbose=False)
            if a and b and a > 0 and b > 0:
                self.race_a = a
                self.race_b = b
        
        self.update_graph()
        
    def reset_view(self):
        """Reset plot view"""
        self.plot.setXRange(0.4, 2.0)
        self.plot.setYRange(50, 200)
        
    def get_selected_data(self) -> dict:
        """Get data points from selected track and vehicles"""
        if not self.current_track or not self.selected_vehicles:
            return {'quali': [], 'race': [], 'unknown': []}
        
        conn = sqlite3.connect(self.db.db_path)
        cursor = conn.cursor()
        
        placeholders = ','.join('?' * len(self.selected_vehicles))
        query = f"""
            SELECT ratio, lap_time, session_type 
            FROM data_points 
            WHERE track = ? AND vehicle IN ({placeholders})
        """
        cursor.execute(query, [self.current_track] + self.selected_vehicles)
        rows = cursor.fetchall()
        conn.close()
        
        result = {'quali': [], 'race': [], 'unknown': []}
        for ratio, lap_time, session_type in rows:
            if session_type == 'qual':
                result['quali'].append((ratio, lap_time))
            elif session_type == 'race':
                result['race'].append((ratio, lap_time))
            else:
                result['unknown'].append((ratio, lap_time))
        
        return result
        
    def update_graph(self):
        """Update the plot with curves and data points"""
        ratios = np.linspace(0.4, 2.0, 200)
        points_data = self.get_selected_data()
        
        # Calculate curve values
        qual_times = self.qual_a / ratios + self.qual_b
        race_times = self.race_a / ratios + self.race_b
        
        # Update qualifying curve
        if self.show_qualifying:
            if self.qual_curve is None:
                self.qual_curve = self.plot.plot(ratios, qual_times, 
                                                 pen=pg.mkPen(color='#FFFF00', width=2.5))
            else:
                self.qual_curve.setData(ratios, qual_times)
                self.qual_curve.setVisible(True)
        elif self.qual_curve is not None:
            self.qual_curve.setVisible(False)
        
        # Update race curve
        if self.show_race:
            if self.race_curve is None:
                self.race_curve = self.plot.plot(ratios, race_times,
                                                 pen=pg.mkPen(color='#FF6600', width=2.5))
            else:
                self.race_curve.setData(ratios, race_times)
                self.race_curve.setVisible(True)
        elif self.race_curve is not None:
            self.race_curve.setVisible(False)
        
        # Update scatter points
        quali_points = points_data.get('quali', [])
        if self.show_qualifying and quali_points:
            r = [p[0] for p in quali_points]
            t = [p[1] for p in quali_points]
            if self.qual_scatter is None:
                self.qual_scatter = pg.ScatterPlotItem(
                    r, t, brush=pg.mkBrush('#FFFF00'), size=8,
                    symbol='o', pen=pg.mkPen('white', width=1)
                )
                self.plot.addItem(self.qual_scatter)
            else:
                self.qual_scatter.setData(r, t)
                self.qual_scatter.setVisible(True)
        elif self.qual_scatter is not None:
            self.qual_scatter.setVisible(False)
        
        race_points = points_data.get('race', [])
        if self.show_race and race_points:
            r = [p[0] for p in race_points]
            t = [p[1] for p in race_points]
            if self.race_scatter is None:
                self.race_scatter = pg.ScatterPlotItem(
                    r, t, brush=pg.mkBrush('#FF6600'), size=8,
                    symbol='s', pen=pg.mkPen('white', width=1)
                )
                self.plot.addItem(self.race_scatter)
            else:
                self.race_scatter.setData(r, t)
                self.race_scatter.setVisible(True)
        elif self.race_scatter is not None:
            self.race_scatter.setVisible(False)
        
        unknown_points = points_data.get('unknown', [])
        if self.show_unknown and unknown_points:
            r = [p[0] for p in unknown_points]
            t = [p[1] for p in unknown_points]
            if self.unknown_scatter is None:
                self.unknown_scatter = pg.ScatterPlotItem(
                    r, t, brush=pg.mkBrush('#FF00FF'), size=6,
                    symbol='t', pen=pg.mkPen('white', width=1)
                )
                self.plot.addItem(self.unknown_scatter)
            else:
                self.unknown_scatter.setData(r, t)
                self.unknown_scatter.setVisible(True)
        elif self.unknown_scatter is not None:
            self.unknown_scatter.setVisible(False)
        
        # Update legend
        if self.legend is not None:
            self.plot.scene().removeItem(self.legend)
        
        self.legend = self.plot.addLegend()
        
        if self.show_qualifying and self.qual_curve is not None:
            self.legend.addItem(self.qual_curve, f'Qualifying: T={self.qual_a:.2f}/R+{self.qual_b:.2f}')
        if self.show_race and self.race_curve is not None:
            self.legend.addItem(self.race_curve, f'Race: T={self.race_a:.2f}/R+{self.race_b:.2f}')
        
        if self.show_qualifying and quali_points:
            self.legend.addItem(self.qual_scatter, f'Qual Data ({len(quali_points)})')
        if self.show_race and race_points:
            self.legend.addItem(self.race_scatter, f'Race Data ({len(race_points)})')
        if self.show_unknown and unknown_points:
            self.legend.addItem(self.unknown_scatter, f'Unknown ({len(unknown_points)})')
        
        # Update formula label
        self.formula_label.setText(f"Qual: T={self.qual_a:.3f}/R+{self.qual_b:.3f}  |  Race: T={self.race_a:.3f}/R+{self.race_b:.3f}")
        
    def on_plot_click(self, event):
        """Handle click on plot to select points"""
        if self.plot.scene().mouseGrabberItem() is not None:
            return
        
        # Get mouse position in plot coordinates
        pos = event.scenePos()
        mouse_point = self.plot.vb.mapSceneToView(pos)
        
        # Find closest data point
        points_data = self.get_selected_data()
        all_points = []
        for session, color in [('quali', '#FFFF00'), ('race', '#FF6600'), ('unknown', '#FF00FF')]:
            for ratio, lap_time in points_data.get(session, []):
                all_points.append((ratio, lap_time, session))
        
        if not all_points:
            return
        
        # Find closest point
        closest = min(all_points, key=lambda p: ((p[0] - mouse_point.x())**2 + (p[1] - mouse_point.y())**2))
        ratio, lap_time, session = closest
        
        # Highlight the point
        if self.selected_point_marker:
            self.plot.removeItem(self.selected_point_marker)
        
        self.selected_point_marker = pg.ScatterPlotItem(
            [ratio], [lap_time], brush=pg.mkBrush('#FFFFFF'), size=12,
            symbol='o', pen=pg.mkPen('#FF0000', width=2)
        )
        self.plot.addItem(self.selected_point_marker)
        
        # Find and select in table
        for row in range(self.data_table.rowCount()):
            if (abs(float(self.data_table.item(row, 2).text()) - ratio) < 0.001 and
                abs(float(self.data_table.item(row, 3).text()) - lap_time) < 0.01):
                self.data_table.selectRow(row)
                self.data_table.scrollToItem(self.data_table.item(row, 0))
                break
        
        # Emit signal
        self.point_selected.emit(self.current_track, session, ratio, lap_time)
        
    def on_table_selection_changed(self):
        """Handle table selection change - highlight point on graph"""
        selected = self.data_table.selectedItems()
        if not selected:
            if self.selected_point_marker:
                self.plot.removeItem(self.selected_point_marker)
                self.selected_point_marker = None
            return
        
        row = selected[0].row()
        ratio = float(self.data_table.item(row, 2).text())
        lap_time = float(self.data_table.item(row, 3).text())
        
        # Highlight the point
        if self.selected_point_marker:
            self.plot.removeItem(self.selected_point_marker)
        
        self.selected_point_marker = pg.ScatterPlotItem(
            [ratio], [lap_time], brush=pg.mkBrush('#FFFFFF'), size=12,
            symbol='o', pen=pg.mkPen('#FF0000', width=2)
        )
        self.plot.addItem(self.selected_point_marker)
        
    def delete_selected_points(self):
        """Delete selected data points"""
        selected_rows = set()
        for item in self.data_table.selectedItems():
            selected_rows.add(item.row())
        
        if not selected_rows:
            QMessageBox.warning(self, "No Selection", "Please select data points to delete.")
            return
        
        reply = QMessageBox.question(
            self, "Confirm Delete",
            f"Delete {len(selected_rows)} data point(s)?\nThis cannot be undone.",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
        
        conn = sqlite3.connect(self.db.db_path)
        cursor = conn.cursor()
        
        deleted = 0
        for row_idx in sorted(selected_rows, reverse=True):
            track = self.data_table.item(row_idx, 0).text()
            vehicle = self.data_table.item(row_idx, 1).text()
            ratio = float(self.data_table.item(row_idx, 2).text())
            lap_time = float(self.data_table.item(row_idx, 3).text())
            session_type = self.data_table.item(row_idx, 4).text()
            
            cursor.execute("""
                DELETE FROM data_points 
                WHERE track = ? AND vehicle = ? AND ratio = ? 
                AND lap_time = ? AND session_type = ?
            """, (track, vehicle, ratio, lap_time, session_type))
            deleted += cursor.rowcount
        
        conn.commit()
        conn.close()
        
        self.load_data()
        QMessageBox.information(self, "Success", f"Deleted {deleted} data point(s).")
        
    def open_multi_track(self):
        """Open multi-track selection dialog"""
        if not self.all_tracks:
            return
        
        dialog = MultiTrackSelectionDialog(self.all_tracks, self.current_track, self)
        if dialog.exec_() == QDialog.Accepted:
            selected = dialog.get_selected_tracks()
            if selected:
                self.selected_tracks = selected
                self.multi_track_mode = len(selected) > 1
                self.current_track = selected[0] if selected else ""
                self.load_data()
                
    def set_formulas(self, qual_a, qual_b, race_a, race_b):
        """Set formulas from external source"""
        self.qual_a = qual_a
        self.qual_b = qual_b
        self.race_a = race_a
        self.race_b = race_b
        self.update_graph()


class AdvancedSettingsDialog(QDialog):
    """Advanced settings window with graph and data management"""
    
    data_updated = pyqtSignal()
    
    def __init__(self, parent=None, db=None, log_window=None):
        super().__init__(parent)
        self.parent = parent
        self.db = db
        self.log_window = log_window
        self.setWindowTitle("Advanced Settings - Curve Editor & Data Management")
        self.setGeometry(100, 100, 1200, 800)
        self.setMinimumWidth(1000)
        self.setMinimumHeight(700)
        
        # AI Target settings
        self.target_mode = "percentage"
        self.target_percentage = 50
        self.target_offset_seconds = 0.0
        self.ai_error_margin = 0.0
        
        self.setup_ui()
        self.load_data()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Main splitter: left side graph, right side settings
        main_splitter = QSplitter(Qt.Horizontal)
        
        # Left side: Curve graph
        self.curve_graph = CurveGraphWidget(self.db, self)
        self.curve_graph.point_selected.connect(self.on_point_selected)
        main_splitter.addWidget(self.curve_graph)
        
        # Right side: Settings tabs
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        
        tabs = QTabWidget()
        
        # ========== TAB 1: AI TARGET SETTINGS ==========
        target_tab = QWidget()
        target_layout = QVBoxLayout(target_tab)
        
        target_info = QLabel(
            "AI Target Positioning\n\n"
            "This controls where your lap time should fall within the AI's lap time range.\n\n"
            "The AI's best and worst lap times create a range. You choose where you want to be."
        )
        target_info.setStyleSheet("color: #FFA500; background-color: #2b2b2b; padding: 10px; border-radius: 5px;")
        target_info.setWordWrap(True)
        target_layout.addWidget(target_info)
        
        target_layout.addSpacing(10)
        
        # Mode selection
        mode_group = QGroupBox("Target Mode")
        mode_layout = QVBoxLayout(mode_group)
        
        self.percentage_radio = QRadioButton("Percentage within AI range")
        self.percentage_radio.setChecked(True)
        self.percentage_radio.toggled.connect(self.on_target_mode_changed)
        mode_layout.addWidget(self.percentage_radio)
        
        pct_desc = QLabel("  0% = match fastest AI, 50% = middle, 100% = match slowest AI")
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
        
        # Percentage controls
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
        
        # Absolute offset controls
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
        
        # Error margin
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
        tabs.addTab(target_tab, "AI Target")
        
        # ========== TAB 2: BACKUP RESTORE ==========
        backup_tab = QWidget()
        backup_layout = QVBoxLayout(backup_tab)
        
        backup_info = QLabel(
            "AIW Backup Restore\n\n"
            "When Autopilot modifies an AIW file, it creates a backup first.\n"
            "Use this section to restore original AIW files.\n\n"
            "Note: Restoring will undo any Autopilot changes made to that track."
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
        tabs.addTab(backup_tab, "Backup Restore")
        
        # ========== TAB 3: SETTINGS ==========
        settings_tab = QWidget()
        settings_layout = QVBoxLayout(settings_tab)
        
        log_group = QGroupBox("Logging Options")
        log_layout = QVBoxLayout(log_group)
        
        self.silent_mode_checkbox = QCheckBox("Silent Mode (suppress popup notifications)")
        if self.parent and hasattr(self.parent, 'autopilot_silent'):
            self.silent_mode_checkbox.setChecked(self.parent.autopilot_silent)
        self.silent_mode_checkbox.toggled.connect(self.on_silent_mode_toggled)
        log_layout.addWidget(self.silent_mode_checkbox)
        
        settings_layout.addWidget(log_group)
        
        show_log_btn = QPushButton("Show Log Window")
        show_log_btn.setStyleSheet("background-color: #2196F3;")
        show_log_btn.clicked.connect(self.show_log_window)
        settings_layout.addWidget(show_log_btn)
        
        changes_group = QGroupBox("Session Changes History")
        changes_layout = QVBoxLayout(changes_group)
        
        self.changes_list = QListWidget()
        changes_layout.addWidget(self.changes_list)
        
        clear_changes_btn = QPushButton("Clear History")
        clear_changes_btn.clicked.connect(self.changes_list.clear)
        changes_layout.addWidget(clear_changes_btn)
        
        settings_layout.addWidget(changes_group)
        
        settings_layout.addStretch()
        tabs.addTab(settings_tab, "Settings")
        
        right_layout.addWidget(tabs)
        main_splitter.addWidget(right_panel)
        
        main_splitter.setSizes([700, 400])
        layout.addWidget(main_splitter)
        
        # Close button
        button_box = QDialogButtonBox(QDialogButtonBox.Close)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
        self.setStyleSheet("""
            QDialog {
                background-color: #1e1e1e;
            }
            QTabWidget::pane {
                background-color: #2b2b2b;
                border: 1px solid #555;
            }
            QTabBar::tab {
                background-color: #3c3c3c;
                color: white;
                padding: 8px 12px;
                margin-right: 2px;
            }
            QTabBar::tab:selected {
                background-color: #4CAF50;
            }
            QTableWidget {
                background-color: #2b2b2b;
                color: white;
                alternate-background-color: #3c3c3c;
                gridline-color: #555;
            }
            QHeaderView::section {
                background-color: #3c3c3c;
                color: white;
                padding: 4px;
            }
            QListWidget {
                background-color: #2b2b2b;
                color: white;
            }
            QGroupBox {
                color: #4CAF50;
            }
            QRadioButton {
                color: white;
            }
        """)
        
        self.update_mode_visibility()
        
    def load_data(self):
        """Load initial data"""
        if self.parent:
            # Copy formulas from parent
            self.curve_graph.set_formulas(
                self.parent.qual_a, self.parent.qual_b,
                self.parent.race_a, self.parent.race_b
            )
        self.curve_graph.load_data()
        self.refresh_backup_list()
        
    def on_point_selected(self, track, session, ratio, lap_time):
        """Handle point selection"""
        pass  # Already handled by graph
        
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
        
    def apply_target_settings(self):
        settings = {
            "mode": self.target_mode,
            "percentage": self.target_percentage,
            "offset_seconds": self.target_offset_seconds,
            "error_margin": self.ai_error_margin
        }
        
        if self.parent:
            self.parent.ai_target_settings = settings
            self.parent.statusBar().showMessage(f"AI Target settings applied", 3000)
        
        QMessageBox.information(self, "Settings Applied", 
            f"AI Target settings have been applied.\n\n"
            f"These settings will be used the next time Autopilot runs.")
            
    def on_silent_mode_toggled(self, checked):
        if self.parent:
            self.parent.autopilot_silent = checked
            if hasattr(self.parent, 'autopilot_manager'):
                self.parent.autopilot_manager.set_silent(checked)
            self.add_change_entry("Settings", f"Silent Mode {'ON' if checked else 'OFF'}")
            
    def show_log_window(self):
        if self.log_window:
            self.log_window.show()
            self.log_window.raise_()
            
    def add_change_entry(self, category, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.changes_list.addItem(f"[{timestamp}] [{category}] {message}")
        self.changes_list.scrollToBottom()
        
    def scan_aiw_backups(self):
        backups = []
        
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
                backups.append({
                    "track": track_name,
                    "original_file": original_name,
                    "backup_path": backup_file,
                    "backup_time": backup_file.stat().st_mtime if backup_file.exists() else 0
                })
        
        return sorted(backups, key=lambda x: x.get("track", ""))
        
    def restore_aiw_backup(self, backup_info):
        try:
            backup_path = backup_info["backup_path"]
            original_name = backup_info["original_file"]
            
            # Try to find the original location
            restore_path = None
            
            if self.parent and hasattr(self.parent, 'daemon') and self.parent.daemon:
                base_path = self.parent.daemon.base_path
                locations_dir = base_path / "GameData" / "Locations"
                
                if locations_dir.exists():
                    for track_dir in locations_dir.iterdir():
                        if track_dir.is_dir():
                            aiw_path = track_dir / original_name
                            if aiw_path.exists():
                                restore_path = aiw_path
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
            return True
            
        except Exception as e:
            print(f"Error restoring backup: {e}")
            return False
            
    def refresh_backup_list(self):
        self.backup_list.clear()
        backups = self.scan_aiw_backups()
        
        if not backups:
            self.backup_list.addItem("No backups found")
            return
        
        for backup in backups:
            time_str = datetime.fromtimestamp(backup["backup_time"]).strftime("%Y-%m-%d %H:%M:%S")
            item_text = f"{backup['track']} - {backup['original_file']} (backup: {time_str})"
            self.backup_list.addItem(item_text)
            self.backup_list.item(self.backup_list.count() - 1).setData(Qt.UserRole, backup)
            
    def restore_selected_backups(self):
        selected_items = self.backup_list.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "No Selection", "Please select backups to restore.")
            return
        
        reply = QMessageBox.question(
            self, "Confirm Restore",
            f"Restore {len(selected_items)} AIW file(s)?\n\nThis will undo Autopilot changes.",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
        
        restored = 0
        for item in selected_items:
            backup = item.data(Qt.UserRole)
            if backup and self.restore_aiw_backup(backup):
                restored += 1
        
        if restored > 0:
            self.add_change_entry("Backup", f"Restored {restored} AIW file(s)")
            QMessageBox.information(self, "Restore Complete", f"Successfully restored {restored} AIW file(s).")
            self.refresh_backup_list()
            
    def restore_all_backups(self):
        backups = self.scan_aiw_backups()
        if not backups:
            QMessageBox.information(self, "No Backups", "No backups found to restore.")
            return
        
        reply = QMessageBox.question(
            self, "Confirm Restore All",
            f"Restore ALL {len(backups)} AIW backup(s)?\n\nThis will undo ALL Autopilot changes.",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
        
        restored = 0
        for backup in backups:
            if self.restore_aiw_backup(backup):
                restored += 1
        
        if restored > 0:
            self.add_change_entry("Backup", f"Restored all {restored} AIW file(s)")
            QMessageBox.information(self, "Restore Complete", f"Successfully restored {restored} AIW file(s).")
            self.refresh_backup_list()


def setup_dark_theme(app):
    """Apply dark theme styling to the application"""
    app.setStyle('Fusion')
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
            padding: 6px 12px;
            font-weight: bold;
        }
        QPushButton:hover {
            background-color: #45a049;
        }
        QStatusBar {
            color: #888;
        }
        QComboBox {
            background-color: #3c3c3c;
            color: white;
            border: 1px solid #4CAF50;
            border-radius: 3px;
            padding: 4px;
        }
        QComboBox::drop-down {
            border: none;
        }
        QComboBox::down-arrow {
            image: none;
            border: none;
        }
        QCheckBox {
            color: white;
        }
    """)


def show_error_dialog(parent, title: str, message: str):
    msg = QMessageBox(parent)
    msg.setWindowTitle(title)
    msg.setIcon(QMessageBox.Critical)
    msg.setText(message)
    msg.exec_()


def show_info_dialog(parent, title: str, message: str):
    msg = QMessageBox(parent)
    msg.setWindowTitle(title)
    msg.setIcon(QMessageBox.Information)
    msg.setText(message)
    msg.exec_()


def show_warning_dialog(parent, title: str, message: str):
    msg = QMessageBox(parent)
    msg.setWindowTitle(title)
    msg.setIcon(QMessageBox.Warning)
    msg.setText(message)
    msg.exec_()
