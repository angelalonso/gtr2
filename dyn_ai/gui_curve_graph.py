#!/usr/bin/env python3
"""
Curve Graph component for Live AI Tuner
Provides the hyperbolic curve visualization and data point display
"""

import sqlite3
import numpy as np
import pyqtgraph as pg
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QMessageBox, QListWidget, QListWidgetItem, QAbstractItemView,
    QDialog, QDialogButtonBox
)
from PyQt5.QtCore import Qt, pyqtSignal

from core_formula import DEFAULT_A_VALUE
from core_autopilot import get_vehicle_class, load_vehicle_classes


class CurveGraphWidget(QWidget):
    """Widget containing the curve graph and data management"""
    
    point_selected = pyqtSignal(str, str, float, float)
    data_updated = pyqtSignal()
    formula_changed = pyqtSignal(str, float, float)
    
    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self.class_mapping = load_vehicle_classes()
        
        self.qual_a = DEFAULT_A_VALUE
        self.qual_b = 70.0
        self.race_a = DEFAULT_A_VALUE
        self.race_b = 70.0
        self.show_qualifying = True
        self.show_race = True
        self.show_user_points = True
        
        self.all_tracks = []
        self.all_classes = []
        self.current_track = ""
        self.current_vehicle = ""
        self.current_vehicle_class = ""
        self.selected_classes = []
        
        self.user_qual_time = None
        self.user_race_time = None
        self.user_qual_ratio = None
        self.user_race_ratio = None
        
        self.qual_curve = None
        self.race_curve = None
        self.qual_scatter = None
        self.race_scatter = None
        self.unknown_scatter = None
        self.user_qual_point = None
        self.user_race_point = None
        self.legend = None
        self.selected_point_marker = None
        self.user_point_labels = []
        self.user_v_lines = []
        
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        top_frame = QFrame()
        top_frame.setStyleSheet("QFrame { background-color: #2b2b2b; border-radius: 5px; padding: 8px; }")
        top_layout = QHBoxLayout(top_frame)
        
        track_group = QFrame()
        track_group.setStyleSheet("background-color: #1e1e1e; border-radius: 3px;")
        track_layout = QHBoxLayout(track_group)
        track_layout.setContentsMargins(8, 4, 8, 4)
        track_layout.addWidget(QLabel("Track:"))
        self.current_track_label = QLabel("-")
        self.current_track_label.setStyleSheet("color: #FFA500; font-weight: bold;")
        track_layout.addWidget(self.current_track_label)
        
        self.select_track_btn = QPushButton("Change")
        self.select_track_btn.setFixedWidth(70)
        self.select_track_btn.setStyleSheet("background-color: #2196F3; padding: 2px 8px;")
        self.select_track_btn.clicked.connect(self.select_track)
        track_layout.addWidget(self.select_track_btn)
        top_layout.addWidget(track_group)
        
        class_group = QFrame()
        class_group.setStyleSheet("background-color: #1e1e1e; border-radius: 3px;")
        class_layout = QHBoxLayout(class_group)
        class_layout.setContentsMargins(8, 4, 8, 4)
        class_layout.addWidget(QLabel("Class:"))
        self.current_class_label = QLabel("-")
        self.current_class_label.setStyleSheet("color: #FF6600; font-weight: bold;")
        class_layout.addWidget(self.current_class_label)
        
        self.select_class_btn = QPushButton("Change")
        self.select_class_btn.setFixedWidth(70)
        self.select_class_btn.setStyleSheet("background-color: #2196F3; padding: 2px 8px;")
        self.select_class_btn.clicked.connect(self.select_classes)
        class_layout.addWidget(self.select_class_btn)
        top_layout.addWidget(class_group)
        
        top_layout.addStretch()
        
        self.refresh_btn = QPushButton("Refresh Data")
        self.refresh_btn.setStyleSheet("background-color: #4CAF50;")
        self.refresh_btn.clicked.connect(self.full_refresh)
        top_layout.addWidget(self.refresh_btn)
        
        layout.addWidget(top_frame)
        layout.addSpacing(5)
        
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
        self.plot.scene().sigMouseClicked.connect(self.on_plot_click)
        
        layout.addWidget(self.plot_widget)
        
        info_layout = QHBoxLayout()
        self.formula_label = QLabel("")
        self.formula_label.setStyleSheet("color: #888; font-size: 10px; font-family: monospace;")
        info_layout.addWidget(self.formula_label)
        info_layout.addStretch()
        layout.addLayout(info_layout)
        
    def _calculate_ratio_for_user_time(self, time_sec: float, session_type: str) -> float:
        if session_type == "qual":
            a, b = self.qual_a, self.qual_b
        else:
            a, b = self.race_a, self.race_b
        denominator = time_sec - b
        if denominator <= 0:
            return None
        ratio = a / denominator
        return ratio if 0.3 < ratio < 3.0 else None
    
    def select_track(self):
        if not self.all_tracks:
            QMessageBox.warning(self, "No Tracks", "No tracks available in database.")
            return
        dialog = QDialog(self)
        dialog.setWindowTitle("Select Track")
        dialog.setModal(True)
        layout = QVBoxLayout(dialog)
        list_widget = QListWidget()
        for track in self.all_tracks:
            list_widget.addItem(track)
        items = list_widget.findItems(self.current_track, Qt.MatchExactly)
        if items:
            list_widget.setCurrentItem(items[0])
        layout.addWidget(list_widget)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        if dialog.exec_() == QDialog.Accepted and list_widget.currentItem():
            selected = list_widget.currentItem().text()
            if selected != self.current_track:
                self.current_track = selected
                self.current_track_label.setText(selected)
                self.load_data()
                self.update_graph()
                self.data_updated.emit()
    
    def select_classes(self):
        if not self.all_classes:
            QMessageBox.warning(self, "No Classes", "No vehicle classes available in database.")
            return
        dialog = QDialog(self)
        dialog.setWindowTitle("Select Vehicle Classes")
        dialog.setModal(True)
        layout = QVBoxLayout(dialog)
        label = QLabel("Select vehicle classes to display:")
        layout.addWidget(label)
        list_widget = QListWidget()
        list_widget.setSelectionMode(QAbstractItemView.MultiSelection)
        for cls in self.all_classes:
            item = QListWidgetItem(cls)
            list_widget.addItem(item)
            if cls in self.selected_classes:
                item.setSelected(True)
        layout.addWidget(list_widget)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        if dialog.exec_() == QDialog.Accepted:
            self.selected_classes = [item.text() for item in list_widget.selectedItems()]
            if not self.selected_classes:
                self.selected_classes = self.all_classes.copy()
            self.current_class_label.setText(f"{len(self.selected_classes)} class(es)")
            self.load_data()
            self.update_graph()
            self.data_updated.emit()
    
    def full_refresh(self):
        self.load_data()
        self.update_graph()
    
    def update_current_info(self, track: str = None, vehicle: str = None, 
                            qual_time: float = None, race_time: float = None,
                            qual_ratio: float = None, race_ratio: float = None):
        if track is not None and track != self.current_track:
            self.current_track = track
            self.current_track_label.setText(track)
            self.load_data()
        if vehicle is not None and vehicle != self.current_vehicle:
            self.current_vehicle = vehicle
            self.current_vehicle_class = get_vehicle_class(vehicle, self.class_mapping)
            self.current_class_label.setText(self.current_vehicle_class)
            if self.current_vehicle_class not in self.selected_classes:
                self.selected_classes = [self.current_vehicle_class]
            self.load_data()
        if qual_time is not None and qual_time > 0:
            self.user_qual_time = qual_time
            self.user_qual_ratio = self._calculate_ratio_for_user_time(qual_time, "qual")
        if race_time is not None and race_time > 0:
            self.user_race_time = race_time
            self.user_race_ratio = self._calculate_ratio_for_user_time(race_time, "race")
        if qual_ratio is not None:
            self.user_qual_ratio = qual_ratio
        if race_ratio is not None:
            self.user_race_ratio = race_ratio
        self.update_graph()
    
    def get_user_qual_time(self) -> float:
        return self.user_qual_time
    
    def get_user_race_time(self) -> float:
        return self.user_race_time
    
    def load_data(self):
        if not self.db.database_exists():
            return
        conn = sqlite3.connect(self.db.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT track FROM data_points ORDER BY track")
        self.all_tracks = [row[0] for row in cursor.fetchall()]
        cursor.execute("SELECT DISTINCT vehicle_class FROM data_points")
        all_vehicles = [row[0] for row in cursor.fetchall()]
        class_set = set()
        for vehicle in all_vehicles:
            vehicle_class = get_vehicle_class(vehicle, self.class_mapping)
            class_set.add(vehicle_class)
        self.all_classes = sorted(class_set)
        if not self.current_track and self.all_tracks:
            self.current_track = self.all_tracks[0]
            self.current_track_label.setText(self.current_track)
        if not self.selected_classes and self.all_classes:
            self.selected_classes = self.all_classes.copy()
            self.current_class_label.setText(f"{len(self.selected_classes)} class(es)")
        conn.close()
        self.data_updated.emit()

    def _get_vehicles_for_classes(self, classes: list) -> list:
        if not classes:
            return []
        conn = sqlite3.connect(self.db.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT vehicle_class FROM data_points")
        all_classes = [row[0] for row in cursor.fetchall()]
        conn.close()
        return [cls for cls in all_classes if cls in classes]

    def get_selected_data(self) -> dict:
        if not self.current_track or not self.selected_classes:
            return {'quali': [], 'race': [], 'unknown': []}
        vehicle_classes = self._get_vehicles_for_classes(self.selected_classes)
        if not vehicle_classes:
            return {'quali': [], 'race': [], 'unknown': []}
        conn = sqlite3.connect(self.db.db_path)
        cursor = conn.cursor()
        placeholders = ','.join('?' * len(vehicle_classes))
        query = f"""
            SELECT ratio, lap_time, session_type 
            FROM data_points 
            WHERE track = ? AND vehicle_class IN ({placeholders})
        """
        cursor.execute(query, [self.current_track] + vehicle_classes)
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
    
    def _safe_remove_legend(self):
        """Safely remove the legend without scene errors"""
        if self.legend is not None:
            try:
                # Check if the legend is still in the scene
                if self.legend.scene() is not None:
                    self.plot.scene().removeItem(self.legend)
            except Exception:
                pass
            self.legend = None
    
    def _safe_remove_item(self, item):
        """Safely remove a graphics item"""
        if item is not None:
            try:
                if item.scene() is not None:
                    self.plot.scene().removeItem(item)
            except Exception:
                pass
    
    def update_graph(self):
        ratios = np.linspace(0.4, 2.0, 200)
        points_data = self.get_selected_data()
        qual_times = self.qual_a / ratios + self.qual_b
        race_times = self.race_a / ratios + self.race_b
        
        # Update or create qual curve
        if self.show_qualifying:
            if self.qual_curve is None:
                self.qual_curve = self.plot.plot(ratios, qual_times, pen=pg.mkPen(color='#FFFF00', width=2.5))
            else:
                # Check if curve is still in scene before updating
                if self.qual_curve.scene() is None:
                    self.qual_curve = self.plot.plot(ratios, qual_times, pen=pg.mkPen(color='#FFFF00', width=2.5))
                else:
                    self.qual_curve.setData(ratios, qual_times)
                    self.qual_curve.setVisible(True)
        elif self.qual_curve is not None:
            self.qual_curve.setVisible(False)
        
        # Update or create race curve
        if self.show_race:
            if self.race_curve is None:
                self.race_curve = self.plot.plot(ratios, race_times, pen=pg.mkPen(color='#FF6600', width=2.5))
            else:
                if self.race_curve.scene() is None:
                    self.race_curve = self.plot.plot(ratios, race_times, pen=pg.mkPen(color='#FF6600', width=2.5))
                else:
                    self.race_curve.setData(ratios, race_times)
                    self.race_curve.setVisible(True)
        elif self.race_curve is not None:
            self.race_curve.setVisible(False)
        
        # Update qual scatter
        quali_points = points_data.get('quali', [])
        if self.show_qualifying and quali_points:
            r = [p[0] for p in quali_points]
            t = [p[1] for p in quali_points]
            if self.qual_scatter is None:
                self.qual_scatter = pg.ScatterPlotItem(r, t, brush=pg.mkBrush('#FFFF00'), size=8, symbol='o', pen=pg.mkPen('white', width=1))
                self.plot.addItem(self.qual_scatter)
            else:
                if self.qual_scatter.scene() is None:
                    self.qual_scatter = pg.ScatterPlotItem(r, t, brush=pg.mkBrush('#FFFF00'), size=8, symbol='o', pen=pg.mkPen('white', width=1))
                    self.plot.addItem(self.qual_scatter)
                else:
                    self.qual_scatter.setData(r, t)
                    self.qual_scatter.setVisible(True)
        elif self.qual_scatter is not None:
            self.qual_scatter.setVisible(False)
        
        # Update race scatter
        race_points = points_data.get('race', [])
        if self.show_race and race_points:
            r = [p[0] for p in race_points]
            t = [p[1] for p in race_points]
            if self.race_scatter is None:
                self.race_scatter = pg.ScatterPlotItem(r, t, brush=pg.mkBrush('#FF6600'), size=8, symbol='s', pen=pg.mkPen('white', width=1))
                self.plot.addItem(self.race_scatter)
            else:
                if self.race_scatter.scene() is None:
                    self.race_scatter = pg.ScatterPlotItem(r, t, brush=pg.mkBrush('#FF6600'), size=8, symbol='s', pen=pg.mkPen('white', width=1))
                    self.plot.addItem(self.race_scatter)
                else:
                    self.race_scatter.setData(r, t)
                    self.race_scatter.setVisible(True)
        elif self.race_scatter is not None:
            self.race_scatter.setVisible(False)
        
        # Update unknown scatter
        unknown_points = points_data.get('unknown', [])
        if unknown_points:
            r = [p[0] for p in unknown_points]
            t = [p[1] for p in unknown_points]
            if self.unknown_scatter is None:
                self.unknown_scatter = pg.ScatterPlotItem(r, t, brush=pg.mkBrush('#FF00FF'), size=6, symbol='t', pen=pg.mkPen('white', width=1))
                self.plot.addItem(self.unknown_scatter)
            else:
                if self.unknown_scatter.scene() is None:
                    self.unknown_scatter = pg.ScatterPlotItem(r, t, brush=pg.mkBrush('#FF00FF'), size=6, symbol='t', pen=pg.mkPen('white', width=1))
                    self.plot.addItem(self.unknown_scatter)
                else:
                    self.unknown_scatter.setData(r, t)
                    self.unknown_scatter.setVisible(True)
        elif self.unknown_scatter is not None:
            self.unknown_scatter.setVisible(False)
        
        # Update user points
        user_points = []
        user_labels = []
        if self.user_qual_time and self.user_qual_time > 0 and self.user_qual_ratio:
            user_points.append((self.user_qual_ratio, self.user_qual_time))
            user_labels.append(("Qualifying", self.user_qual_ratio, self.user_qual_time))
        if self.user_race_time and self.user_race_time > 0 and self.user_race_ratio:
            user_points.append((self.user_race_ratio, self.user_race_time))
            user_labels.append(("Race", self.user_race_ratio, self.user_race_time))
        
        if user_points:
            r = [p[0] for p in user_points]
            t = [p[1] for p in user_points]
            if self.user_qual_point is None:
                self.user_qual_point = pg.ScatterPlotItem(r, t, brush=pg.mkBrush('#00FFFF'), size=14, symbol='star', pen=pg.mkPen('white', width=2))
                self.plot.addItem(self.user_qual_point)
                self.user_point_labels = []
                for i, (label, ratio_val, time_val) in enumerate(user_labels):
                    text_item = pg.TextItem(text=f"  {label}", color='#00FFFF', anchor=(0, 0.5))
                    text_item.setPos(ratio_val, time_val)
                    self.plot.addItem(text_item)
                    self.user_point_labels.append(text_item)
            else:
                if self.user_qual_point.scene() is None:
                    self.user_qual_point = pg.ScatterPlotItem(r, t, brush=pg.mkBrush('#00FFFF'), size=14, symbol='star', pen=pg.mkPen('white', width=2))
                    self.plot.addItem(self.user_qual_point)
                else:
                    self.user_qual_point.setData(r, t)
                    self.user_qual_point.setVisible(True)
                
                # Update or create labels
                for i, (label, ratio_val, time_val) in enumerate(user_labels):
                    if i < len(self.user_point_labels):
                        if self.user_point_labels[i].scene() is None:
                            text_item = pg.TextItem(text=f"  {label}", color='#00FFFF', anchor=(0, 0.5))
                            text_item.setPos(ratio_val, time_val)
                            self.plot.addItem(text_item)
                            self.user_point_labels[i] = text_item
                        else:
                            self.user_point_labels[i].setPos(ratio_val, time_val)
                            self.user_point_labels[i].setHtml(f'  <span style="color:#00FFFF;">{label}</span>')
                    else:
                        text_item = pg.TextItem(text=f"  {label}", color='#00FFFF', anchor=(0, 0.5))
                        text_item.setPos(ratio_val, time_val)
                        self.plot.addItem(text_item)
                        self.user_point_labels.append(text_item)
        elif self.user_qual_point is not None:
            self.user_qual_point.setVisible(False)
            for label in self.user_point_labels:
                if label.scene() is not None:
                    self.plot.scene().removeItem(label)
            self.user_point_labels = []
        
        # Update user vertical/horizontal lines
        if self.user_v_lines:
            for line in self.user_v_lines:
                self._safe_remove_item(line)
            self.user_v_lines = []
        
        if user_points and self.show_user_points:
            for ratio_val, time_val in user_points:
                v_line = pg.InfiniteLine(pos=ratio_val, angle=90, pen=pg.mkPen(color='#00FFFF', width=1, style=Qt.DashLine))
                self.plot.addItem(v_line)
                self.user_v_lines.append(v_line)
                h_line = pg.InfiniteLine(pos=time_val, angle=0, pen=pg.mkPen(color='#00FFFF', width=1, style=Qt.DashLine))
                self.plot.addItem(h_line)
                self.user_v_lines.append(h_line)
        
        # Update legend - safe removal
        self._safe_remove_legend()
        
        # Add new legend
        self.legend = self.plot.addLegend()
        if self.show_qualifying and self.qual_curve is not None and self.qual_curve.scene() is not None:
            self.legend.addItem(self.qual_curve, f'Qualifying: T={self.qual_a:.2f}/R+{self.qual_b:.2f}')
        if self.show_race and self.race_curve is not None and self.race_curve.scene() is not None:
            self.legend.addItem(self.race_curve, f'Race: T={self.race_a:.2f}/R+{self.race_b:.2f}')
        if self.show_qualifying and quali_points and self.qual_scatter is not None and self.qual_scatter.scene() is not None:
            self.legend.addItem(self.qual_scatter, f'Qual Data ({len(quali_points)})')
        if self.show_race and race_points and self.race_scatter is not None and self.race_scatter.scene() is not None:
            self.legend.addItem(self.race_scatter, f'Race Data ({len(race_points)})')
        if unknown_points and self.unknown_scatter is not None and self.unknown_scatter.scene() is not None:
            self.legend.addItem(self.unknown_scatter, f'Unknown ({len(unknown_points)})')
        if user_points and self.user_qual_point is not None and self.user_qual_point.scene() is not None:
            self.legend.addItem(self.user_qual_point, 'Your Lap Times')
        
        qual_info = ""
        race_info = ""
        if self.user_qual_time and self.user_qual_ratio:
            qual_info = f"Qual: T={self.user_qual_time:.2f}s -> R={self.user_qual_ratio:.4f}"
        if self.user_race_time and self.user_race_ratio:
            race_info = f"Race: T={self.user_race_time:.2f}s -> R={self.user_race_ratio:.4f}"
        separator = "  |  " if qual_info and race_info else ""
        self.formula_label.setText(f"{qual_info}{separator}{race_info}")
    
    def on_plot_click(self, event):
        if self.plot.scene().mouseGrabberItem() is not None:
            return
        pos = event.scenePos()
        mouse_point = self.plot.vb.mapSceneToView(pos)
        points_data = self.get_selected_data()
        all_points = []
        for session in [('quali', '#FFFF00'), ('race', '#FF6600'), ('unknown', '#FF00FF')]:
            for ratio, lap_time in points_data.get(session[0], []):
                all_points.append((ratio, lap_time, session[0]))
        if not all_points:
            return
        closest = min(all_points, key=lambda p: ((p[0] - mouse_point.x())**2 + (p[1] - mouse_point.y())**2))
        ratio, lap_time, session = closest
        
        # Remove old marker safely
        if self.selected_point_marker:
            self._safe_remove_item(self.selected_point_marker)
        
        self.selected_point_marker = pg.ScatterPlotItem([ratio], [lap_time], brush=pg.mkBrush('#FFFFFF'), size=12, symbol='o', pen=pg.mkPen('#FF0000', width=2))
        self.plot.addItem(self.selected_point_marker)
        self.point_selected.emit(self.current_track, session, ratio, lap_time)
    
    def set_formulas(self, qual_a: float, qual_b: float, race_a: float, race_b: float):
        self.qual_a = qual_a
        self.qual_b = qual_b
        self.race_a = race_a
        self.race_b = race_b
        if self.user_qual_time:
            self.user_qual_ratio = self._calculate_ratio_for_user_time(self.user_qual_time, "qual")
        if self.user_race_time:
            self.user_race_ratio = self._calculate_ratio_for_user_time(self.user_race_time, "race")
        self.update_graph()
    
    def set_show_qualifying(self, show: bool):
        self.show_qualifying = show
        self.update_graph()
        
    def set_show_race(self, show: bool):
        self.show_race = show
        self.update_graph()
