"""
Global Curve Builder Dialog
Allows manual adjustment of hyperbolic curve parameters, auto-fitting, and data visualization
"""

import sys
import logging
import numpy as np
from pathlib import Path
from typing import Optional, List, Tuple, Dict
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *

# Import matplotlib for plotting
import matplotlib
matplotlib.use('Qt5Agg')
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.ticker import AutoMinorLocator

logger = logging.getLogger(__name__)


class ParameterEditor(QGroupBox):
    """Widget for editing curve parameters"""
    
    param_changed = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__("Curve Parameters", parent)
        self.setup_ui()
        
    def setup_ui(self):
        layout = QGridLayout(self)
        
        # Track selection
        layout.addWidget(QLabel("Track:"), 0, 0)
        self.track_combo = QComboBox()
        self.track_combo.currentTextChanged.connect(self.on_track_changed)
        layout.addWidget(self.track_combo, 0, 1)
        
        # Parameter display
        layout.addWidget(QLabel("Formula: T = a / R + b"), 1, 0, 1, 2)
        
        # a parameter
        layout.addWidget(QLabel("a (sensitivity):"), 2, 0)
        self.a_spin = QDoubleSpinBox()
        self.a_spin.setRange(0.01, 500)
        self.a_spin.setDecimals(3)
        self.a_spin.setSingleStep(1.0)
        self.a_spin.setFixedWidth(120)
        self.a_spin.valueChanged.connect(self.param_changed.emit)
        layout.addWidget(self.a_spin, 2, 1)
        
        # b parameter
        layout.addWidget(QLabel("b (floor, seconds):"), 3, 0)
        self.b_spin = QDoubleSpinBox()
        self.b_spin.setRange(0.01, 200)
        self.b_spin.setDecimals(3)
        self.b_spin.setSingleStep(0.5)
        self.b_spin.setFixedWidth(120)
        self.b_spin.valueChanged.connect(self.param_changed.emit)
        layout.addWidget(self.b_spin, 3, 1)
        
        # Global k parameter
        k_label = QLabel("k = a/(a+b):")
        k_label.setStyleSheet("color: #888;")
        layout.addWidget(k_label, 4, 0)
        self.k_value = QLabel("---")
        self.k_value.setStyleSheet("color: #4CAF50; font-weight: bold;")
        layout.addWidget(self.k_value, 4, 1)
        
        # M parameter
        m_label = QLabel("M = a+b (time at R=1.0):")
        m_label.setStyleSheet("color: #888;")
        layout.addWidget(m_label, 5, 0)
        self.m_value = QLabel("---")
        self.m_value.setStyleSheet("color: #4CAF50; font-weight: bold;")
        layout.addWidget(self.m_value, 5, 1)
        
        # Global k editor
        layout.addWidget(QLabel("Global k (prior):"), 6, 0)
        self.global_k_spin = QDoubleSpinBox()
        self.global_k_spin.setRange(0.1, 0.6)
        self.global_k_spin.setDecimals(4)
        self.global_k_spin.setSingleStep(0.01)
        self.global_k_spin.setFixedWidth(120)
        self.global_k_spin.valueChanged.connect(self.on_global_k_changed)
        layout.addWidget(self.global_k_spin, 6, 1)
        
        layout.setRowStretch(7, 1)
    
    def on_track_changed(self, track_name: str):
        self.param_changed.emit()
    
    def on_global_k_changed(self, value):
        self.param_changed.emit()
    
    def set_tracks(self, tracks: List[str], current_track: str = None):
        """Update track list"""
        self.track_combo.blockSignals(True)
        self.track_combo.clear()
        # Add "-- Select Track --" as first option
        self.track_combo.addItem("-- Select Track --")
        for track in sorted(tracks):
            self.track_combo.addItem(track)
        if current_track and current_track in tracks:
            self.track_combo.setCurrentText(current_track)
        self.track_combo.blockSignals(False)
    
    def set_params(self, a: float, b: float, global_k: float = None):
        """Set parameter values"""
        self.a_spin.blockSignals(True)
        self.b_spin.blockSignals(True)
        
        self.a_spin.setValue(a)
        self.b_spin.setValue(b)
        
        M = a + b
        self.m_value.setText(f"{M:.3f} s")
        
        if M > 0:
            k = a / M
            self.k_value.setText(f"{k:.4f}")
        
        if global_k is not None:
            self.global_k_spin.setValue(global_k)
        
        self.a_spin.blockSignals(False)
        self.b_spin.blockSignals(False)
    
    def get_params(self) -> Tuple[float, float]:
        """Get current a and b parameters"""
        return self.a_spin.value(), self.b_spin.value()
    
    def get_global_k(self) -> float:
        """Get global k value"""
        return self.global_k_spin.value()
    
    def get_selected_track(self) -> Optional[str]:
        """Get currently selected track"""
        text = self.track_combo.currentText()
        if text == "-- Select Track --":
            return None
        return text


class DataPointsTable(QTableWidget):
    """Table for displaying data points for the selected track"""
    
    point_deleted = pyqtSignal(int)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self.current_track = None
        self.all_points = {}  # track_name -> list of (ratio, time)
        
    def setup_ui(self):
        self.setColumnCount(3)
        self.setHorizontalHeaderLabels(["Ratio", "Lap Time (s)", ""])
        
        self.setColumnWidth(0, 100)
        self.setColumnWidth(1, 100)
        self.setColumnWidth(2, 60)
        
        self.setAlternatingRowColors(True)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        
        self.horizontalHeader().setStretchLastSection(False)
    
    def set_track_points(self, track_name: str, points: List[Tuple[float, float]]):
        """Update table to show points for the selected track"""
        self.current_track = track_name
        self.clear_all()
        
        if not track_name or track_name not in self.all_points:
            return
        
        points = self.all_points[track_name]
        for ratio, time in points:
            self.add_point(ratio, time)
    
    def add_point(self, ratio: float, time: float, row_index: int = None):
        """Add a data point to the table"""
        if row_index is None:
            row_index = self.rowCount()
            self.insertRow(row_index)
        
        # Ratio
        ratio_item = QTableWidgetItem(f"{ratio:.4f}")
        ratio_item.setFlags(ratio_item.flags() & ~Qt.ItemIsEditable)
        self.setItem(row_index, 0, ratio_item)
        
        # Time
        time_item = QTableWidgetItem(f"{time:.3f}")
        time_item.setFlags(time_item.flags() & ~Qt.ItemIsEditable)
        self.setItem(row_index, 1, time_item)
        
        # Delete button
        delete_btn = QPushButton("x")
        delete_btn.setFixedSize(30, 25)
        delete_btn.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                border: none;
                border-radius: 3px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #d32f2f;
            }
        """)
        delete_btn.clicked.connect(lambda: self.point_deleted.emit(row_index))
        self.setCellWidget(row_index, 2, delete_btn)
        
        return row_index
    
    def clear_all(self):
        """Clear all rows"""
        self.setRowCount(0)
    
    def get_point(self, row: int) -> Tuple[float, float]:
        """Get point data from row"""
        ratio = float(self.item(row, 0).text())
        time = float(self.item(row, 1).text())
        return ratio, time
    
    def update_all_points(self, all_points: Dict[str, List[Tuple[float, float]]]):
        """Update the internal storage of all points"""
        self.all_points = all_points.copy()
        # Refresh current track display
        if self.current_track:
            self.set_track_points(self.current_track, self.all_points.get(self.current_track, []))
        else:
            self.clear_all()


class CurveGraphWidget(QWidget):
    """Widget for displaying the curve and data points for selected track only"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        
        self.current_points = []  # points for current track [(ratio, time)]
        self.current_track = None
        self.curve_params = None  # (a, b) for current curve
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Create figure
        self.figure = Figure(figsize=(8, 6), facecolor='#1e1e1e')
        self.canvas = FigureCanvas(self.figure)
        self.toolbar = NavigationToolbar(self.canvas, self)
        
        layout.addWidget(self.toolbar)
        layout.addWidget(self.canvas)
        
        self.ax = self.figure.add_subplot(111)
        self.ax.set_facecolor('#2b2b2b')
        
        # Style
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
        self.ax.set_xlim(0.3, 3.0)
        self.ax.set_ylim(50, 200)
        
        self.ax.xaxis.set_minor_locator(AutoMinorLocator())
        self.ax.yaxis.set_minor_locator(AutoMinorLocator())
        
        # Disable legend by default
        self.ax.get_legend().remove() if self.ax.get_legend() else None
    
    def update_data(self, track_points: Dict[str, List[Tuple[float, float]]], 
                    current_track: str = None, curve_params: Tuple[float, float] = None):
        """Update the graph with data for the selected track only"""
        self.current_track = current_track
        self.curve_params = curve_params
        
        # Get points only for the selected track
        if current_track and current_track in track_points:
            self.current_points = track_points[current_track]
        else:
            self.current_points = []
        
        self.redraw()
    
    def redraw(self):
        """Redraw the graph - only shows selected track points"""
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
        self.ax.set_xlim(0.3, 3.0)
        self.ax.set_ylim(50, 200)
        
        # Plot data points for selected track only
        if self.current_points:
            ratios = [p[0] for p in self.current_points]
            times = [p[1] for p in self.current_points]
            
            # Use a single color for all points
            self.ax.scatter(ratios, times, c='#FFA500', s=60, alpha=0.9,
                           edgecolors='white', linewidth=1, zorder=3)
            
            # Add labels to show point coordinates
            for r, t in self.current_points:
                self.ax.annotate(f'({r:.2f}, {t:.1f})', 
                               xy=(r, t), xytext=(5, 5),
                               textcoords='offset points',
                               fontsize=8, color='#AAAAAA',
                               alpha=0.7)
        
        # Plot curve if parameters available
        if self.curve_params:
            a, b = self.curve_params
            ratios_curve = np.linspace(0.3, 3.0, 200)
            times_curve = [a / r + b for r in ratios_curve]
            
            # Curve label
            if self.current_track:
                label = f"T = {a:.3f}/R + {b:.3f}"
            else:
                label = f"Global: T = {a:.3f}/R + {b:.3f}"
            
            self.ax.plot(ratios_curve, times_curve, c='cyan', linewidth=2.5,
                        label=label, zorder=4)
            
            # Add legend only for the curve (not for points)
            self.ax.legend(loc='upper left', framealpha=0.8,
                          facecolor='#2b2b2b', edgecolor='#4CAF50',
                          labelcolor='white', fontsize=9)
        
        self.canvas.draw()
    
    def reset_view(self):
        """Reset to default view"""
        self.ax.set_xlim(0.3, 3.0)
        self.ax.set_ylim(50, 200)
        self.canvas.draw()


class GlobalCurveBuilderDialog(QDialog):
    """Main dialog for building and editing the global curve"""
    
    def __init__(self, parent=None, formulas_dir: str = None, curve_manager=None,
                 default_track: str = None):
        super().__init__(parent)
        self.formulas_dir = Path(formulas_dir) if formulas_dir else Path("./track_formulas")
        self.curve_manager = curve_manager
        self.default_track = default_track  # pre-select on open; None = start blank

        # Data storage
        self.track_points = {}
        self.track_params = {}
        self.global_k = 0.297

        self.setup_ui()
        self.load_data()
        
    def setup_ui(self):
        self.setWindowTitle("Global Curve Builder")
        self.setGeometry(100, 100, 1400, 850)
        self.setModal(False)
        
        self.setStyleSheet("""
            QDialog {
                background-color: #1e1e1e;
            }
            QLabel {
                color: white;
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
            QTableWidget {
                background-color: #2b2b2b;
                alternate-background-color: #3c3c3c;
                color: white;
                gridline-color: #555;
            }
            QTableWidget::item:selected {
                background-color: #4CAF50;
            }
            QHeaderView::section {
                background-color: #3c3c3c;
                color: #4CAF50;
                padding: 5px;
                border: 1px solid #555;
            }
            QTabWidget::pane {
                border: 1px solid #4CAF50;
            }
            QTabBar::tab {
                color: white;
                padding: 8px;
            }
            QTabBar::tab:selected {
                color: #4CAF50;
            }
        """)
        
        main_layout = QVBoxLayout(self)
        
        # Toolbar
        toolbar = self.create_toolbar()
        main_layout.addWidget(toolbar)
        
        # Main splitter
        splitter = QSplitter(Qt.Horizontal)
        
        # Left panel - Controls and data
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 5, 0)
        
        # Parameter editor
        self.param_editor = ParameterEditor()
        self.param_editor.param_changed.connect(self.on_param_changed)
        left_layout.addWidget(self.param_editor)
        
        # Data points table
        data_group = QGroupBox("Data Points (Selected Track Only)")
        data_layout = QVBoxLayout(data_group)
        
        self.points_table = DataPointsTable()
        self.points_table.point_deleted.connect(self.on_point_deleted)
        data_layout.addWidget(self.points_table)
        
        # Add point controls
        add_layout = QHBoxLayout()
        add_layout.addWidget(QLabel("Add point:"))
        
        self.new_track = QLineEdit()
        self.new_track.setPlaceholderText("Track name")
        add_layout.addWidget(self.new_track)
        
        self.new_ratio = QDoubleSpinBox()
        self.new_ratio.setRange(0.1, 5.0)
        self.new_ratio.setDecimals(4)
        self.new_ratio.setValue(1.0)
        add_layout.addWidget(self.new_ratio)
        
        self.new_time = QDoubleSpinBox()
        self.new_time.setRange(30, 300)
        self.new_time.setDecimals(3)
        self.new_time.setValue(100.0)
        add_layout.addWidget(self.new_time)
        
        add_btn = QPushButton("Add")
        add_btn.setFixedWidth(60)
        add_btn.clicked.connect(self.add_point)
        add_layout.addWidget(add_btn)
        
        data_layout.addLayout(add_layout)
        
        left_layout.addWidget(data_group)
        
        # Right panel - Graph
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(5, 0, 0, 0)
        
        self.graph = CurveGraphWidget()
        right_layout.addWidget(self.graph)
        
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setSizes([500, 900])
        
        main_layout.addWidget(splitter)
        
        # Status bar
        self.status_bar = QStatusBar()
        self.status_bar.setStyleSheet("QStatusBar { color: #888; }")
        main_layout.addWidget(self.status_bar)
    
    def create_toolbar(self):
        """Create toolbar widget"""
        toolbar = QWidget()
        layout = QHBoxLayout(toolbar)
        layout.setContentsMargins(0, 0, 0, 10)
        
        # Auto-fit button
        self.fit_btn = QPushButton("Auto-Fit Current Track")
        self.fit_btn.setFixedHeight(35)
        self.fit_btn.clicked.connect(self.auto_fit)
        layout.addWidget(self.fit_btn)
        
        # Fit all button
        self.fit_all_btn = QPushButton("Fit Global k")
        self.fit_all_btn.setFixedHeight(35)
        self.fit_all_btn.clicked.connect(self.fit_global_k)
        layout.addWidget(self.fit_all_btn)
        
        # Apply to manager button
        self.apply_btn = QPushButton("Apply to AI Tuner")
        self.apply_btn.setFixedHeight(35)
        self.apply_btn.setStyleSheet("background-color: #9C27B0;")
        self.apply_btn.clicked.connect(self.apply_to_manager)
        layout.addWidget(self.apply_btn)
        
        # Separator
        sep = QFrame()
        sep.setFrameShape(QFrame.VLine)
        sep.setStyleSheet("background-color: #555;")
        layout.addWidget(sep)
        
        # Reset view
        reset_btn = QPushButton("Reset Graph View")
        reset_btn.setFixedHeight(35)
        reset_btn.clicked.connect(self.reset_graph_view)
        layout.addWidget(reset_btn)
        
        # Import CSV
        import_btn = QPushButton("Import CSV Data")
        import_btn.setFixedHeight(35)
        import_btn.clicked.connect(self.import_csv)
        layout.addWidget(import_btn)
        
        layout.addStretch()
        
        # Stats display
        self.stats_label = QLabel("")
        self.stats_label.setStyleSheet("color: #888;")
        layout.addWidget(self.stats_label)
        
        return toolbar
    
    def load_data(self):
        """Load data from curve manager and historic CSV, then apply default_track."""
        # Load from curve manager if available
        if self.curve_manager:
            self.track_points = self.curve_manager.curve.points_by_track.copy()
            self.track_params = self.curve_manager.curve.track_params.copy()
            self.global_k    = self.curve_manager.curve.global_k

        # Merge any extra points from historic.csv
        historic_csv = Path("./historic.csv")
        if historic_csv.exists():
            self.load_historic_csv(historic_csv)

        # Populate track combo — always starts on "-- Select Track --"
        tracks = sorted(set(self.track_points.keys()))
        self.param_editor.set_tracks(tracks)          # combo index 0 = "-- Select Track --"

        # Update points table (no track selected yet → shows nothing)
        self.points_table.update_all_points(self.track_points)

        # Set default spinbox values regardless of selection
        self.param_editor.set_params(30.0, 70.0, self.global_k)

        # Pre-select a specific track if one was requested
        if self.default_track and self.default_track in self.track_points:
            self.param_editor.track_combo.setCurrentText(self.default_track)
            # set_params to the track's fitted values if available
            params = self.track_params.get(self.default_track)
            if params:
                self.param_editor.set_params(params['a'], params['b'], self.global_k)
            # show its points in the table
            self.points_table.set_track_points(
                self.default_track, self.track_points[self.default_track]
            )
        elif self.default_track:
            # Track name provided but no data yet — still select it so the user
            # can see it's the active track even though the graph is empty.
            self.param_editor.track_combo.setCurrentText(self.default_track)

        # Draw graph (blank if no track selected, or pre-filled if default_track set)
        self.update_graph()
        self.update_stats()
    
    def load_historic_csv(self, csv_path: Path):
        """Load data from historic.csv"""
        try:
            import csv
            loaded = 0
            with open(csv_path, 'r') as f:
                reader = csv.DictReader(f, delimiter=';')
                for row in reader:
                    track = row.get('Track Name', '')
                    if not track:
                        continue
                    
                    # Qualifying data
                    try:
                        ratio = float(row.get('Current QualRatio', '0'))
                        best = float(row.get('Qual AI Best (s)', '0'))
                        worst = float(row.get('Qual AI Worst (s)', '0'))
                        if ratio > 0 and best > 0 and worst > 0:
                            midpoint = (best + worst) / 2
                            if track not in self.track_points:
                                self.track_points[track] = []
                            # Check for duplicate ratio
                            exists = any(abs(r - ratio) < 0.001 for r, _ in self.track_points[track])
                            if not exists:
                                self.track_points[track].append((ratio, midpoint))
                                loaded += 1
                    except:
                        pass
                    
                    # Race data
                    try:
                        ratio = float(row.get('Current RaceRatio', '0'))
                        best = float(row.get('Race AI Best (s)', '0'))
                        worst = float(row.get('Race AI Worst (s)', '0'))
                        if ratio > 0 and best > 0 and worst > 0:
                            midpoint = (best + worst) / 2
                            if track not in self.track_points:
                                self.track_points[track] = []
                            exists = any(abs(r - ratio) < 0.001 for r, _ in self.track_points[track])
                            if not exists:
                                self.track_points[track].append((ratio, midpoint))
                                loaded += 1
                    except:
                        pass
            
            if loaded > 0:
                # Sort points by ratio
                for track in self.track_points:
                    self.track_points[track].sort(key=lambda x: x[0])
                
                self.log_message(f"Loaded {loaded} points from {csv_path.name}")
                
        except Exception as e:
            self.log_message(f"Error loading historic.csv: {e}", "error")
    
    def add_point(self):
        """Add a manual data point"""
        track = self.new_track.text().strip()
        if not track:
            self.log_message("Please enter a track name", "warning")
            return
        
        ratio = self.new_ratio.value()
        time = self.new_time.value()
        
        if track not in self.track_points:
            self.track_points[track] = []
        
        # Check for duplicate ratio
        for existing_ratio, _ in self.track_points[track]:
            if abs(existing_ratio - ratio) < 0.001:
                self.log_message(f"Point with ratio {ratio} already exists for {track}", "warning")
                return
        
        self.track_points[track].append((ratio, time))
        self.track_points[track].sort(key=lambda x: x[0])
        
        # Update points table
        self.points_table.update_all_points(self.track_points)
        
        # Update track list
        tracks = list(set(self.track_points.keys()))
        self.param_editor.set_tracks(tracks)
        
        # If this is the currently selected track, refresh the table display
        selected_track = self.param_editor.get_selected_track()
        if selected_track == track:
            self.points_table.set_track_points(track, self.track_points[track])
        
        self.log_message(f"Added point: {track} - R={ratio:.4f}, T={time:.3f}s", "success")
        self.update_graph()
        self.update_stats()
    
    def on_point_deleted(self, row: int):
        """Handle point deletion"""
        ratio, time = self.points_table.get_point(row)
        selected_track = self.param_editor.get_selected_track()
        
        if not selected_track:
            return
        
        if selected_track in self.track_points:
            # Find and remove the point
            for i, (r, t) in enumerate(self.track_points[selected_track]):
                if abs(r - ratio) < 0.001 and abs(t - time) < 0.01:
                    del self.track_points[selected_track][i]
                    break
            
            # Remove track if no points left
            if not self.track_points[selected_track]:
                del self.track_points[selected_track]
                # Also remove parameters if they exist
                if selected_track in self.track_params:
                    del self.track_params[selected_track]
        
        # Update points table
        self.points_table.update_all_points(self.track_points)
        
        # Update track list
        tracks = list(set(self.track_points.keys()))
        self.param_editor.set_tracks(tracks)
        
        # If track still exists, refresh display
        if selected_track in self.track_points:
            self.points_table.set_track_points(selected_track, self.track_points[selected_track])
        
        self.log_message(f"Deleted point: {selected_track} - R={ratio:.4f}", "info")
        self.update_graph()
        self.update_stats()
    
    def auto_fit(self):
        """Auto-fit curve for selected track"""
        selected_track = self.param_editor.get_selected_track()
        
        if not selected_track:
            self.log_message("Please select a track to fit", "warning")
            return
        
        points = self.track_points.get(selected_track, [])
        if len(points) < 2:
            self.log_message(f"Need at least 2 points for {selected_track} to fit (have {len(points)})", "warning")
            return
        
        # Perform fit
        ratios = np.array([p[0] for p in points])
        times = np.array([p[1] for p in points])
        
        def hyperbolic_func(R, a, b):
            return a / R + b
        
        try:
            # Use first two points for initial guess
            r1, m1 = points[0]
            r2, m2 = points[1]
            inv_r1 = 1.0 / r1
            inv_r2 = 1.0 / r2
            a_guess = (m1 - m2) / (inv_r1 - inv_r2)
            b_guess = m1 - a_guess * inv_r1
            
            from scipy.optimize import curve_fit
            popt, _ = curve_fit(hyperbolic_func, ratios, times, p0=[a_guess, b_guess])
            a, b = popt
            
            # Store parameters
            self.track_params[selected_track] = {'a': a, 'b': b}
            
            # Update display
            self.param_editor.set_params(a, b, self.global_k)
            
            # Calculate error
            predictions = hyperbolic_func(ratios, a, b)
            errors = np.abs(times - predictions)
            avg_error = np.mean(errors)
            
            self.log_message(f"Fitted {selected_track}: a={a:.3f}, b={b:.3f}, avg error={avg_error:.3f}s", "success")
            self.update_graph()
            
        except Exception as e:
            self.log_message(f"Fit failed: {e}", "error")
    
    def fit_global_k(self):
        """Fit global k from all tracks' parameters"""
        k_values = []
        for track_name, params in self.track_params.items():
            M = params['a'] + params['b']
            if M > 0:
                k = params['a'] / M
                k_values.append(k)
        
        if len(k_values) >= 2:
            self.global_k = np.mean(k_values)
            k_std = np.std(k_values)
            self.param_editor.global_k_spin.setValue(self.global_k)
            self.log_message(f"Global k = {self.global_k:.4f} +- {k_std:.4f} from {len(k_values)} tracks", "success")
        else:
            self.log_message(f"Need at least 2 tracks with fitted parameters to fit global k (have {len(k_values)})", "warning")
    
    def on_param_changed(self):
        """Handle parameter changes from editor"""
        selected_track = self.param_editor.get_selected_track()
        a, b = self.param_editor.get_params()
        self.global_k = self.param_editor.get_global_k()
        
        # Store parameters if track selected
        if selected_track:
            self.track_params[selected_track] = {'a': a, 'b': b}
        
        self.update_graph()
    
    def update_graph(self):
        """Update the graph display.

        When no track is selected the graph is intentionally left blank —
        no data points and no curve line.  A curve is only drawn once the
        user picks a track from the combo.
        """
        selected_track = self.param_editor.get_selected_track()

        if selected_track:
            # Use fitted params for this track if available, else editor values
            if selected_track in self.track_params:
                params = self.track_params[selected_track]
                curve_params = (params['a'], params['b'])
            else:
                a, b = self.param_editor.get_params()
                curve_params = (a, b)
        else:
            # No track selected → blank graph (no curve, no points)
            curve_params = None

        self.graph.update_data(self.track_points, selected_track, curve_params)

        # Sync points table with selection
        if selected_track and selected_track in self.track_points:
            self.points_table.set_track_points(selected_track, self.track_points[selected_track])
        else:
            self.points_table.clear_all()
    
    def update_stats(self):
        """Update statistics display"""
        total_points = sum(len(p) for p in self.track_points.values())
        total_tracks = len(self.track_points)
        fitted_tracks = len(self.track_params)
        
        self.stats_label.setText(f"Stats: {total_points} points | {total_tracks} tracks | {fitted_tracks} fitted")
        self.status_bar.showMessage(f"Ready - {total_points} data points loaded")
    
    def reset_graph_view(self):
        """Reset graph to default view"""
        self.graph.reset_view()
    
    def import_csv(self):
        """Import data from CSV file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Import CSV Data", "", "CSV Files (*.csv);;All Files (*)"
        )
        
        if file_path:
            self.load_historic_csv(Path(file_path))
            self.update_graph()
            self.update_stats()
            
            # Update track list
            tracks = list(set(self.track_points.keys()))
            self.param_editor.set_tracks(tracks)
            
            # Update points table
            self.points_table.update_all_points(self.track_points)
    
    def apply_to_manager(self):
        """Apply current parameters to the AI Tuner's curve manager"""
        if not self.curve_manager:
            self.log_message("No curve manager connected", "error")
            return
        
        # Update points in curve manager
        self.curve_manager.curve.points_by_track = self.track_points.copy()
        self.curve_manager.curve.track_params = self.track_params.copy()
        self.curve_manager.curve.global_k = self.global_k
        
        # Re-fit each track
        for track_name in self.track_points:
            try:
                self.curve_manager.curve._update_track_params(track_name)
            except Exception as e:
                self.log_message(f"Error updating track {track_name}: {e}", "warning")
        
        # Save
        self.curve_manager.save()
        
        # Force a refresh of the curve manager stats
        self.curve_manager.fit_global_k()
        
        self.log_message("Applied changes to AI Tuner", "success")
        
        # Show success message
        QMessageBox.information(self, "Success", 
                               f"Curve parameters applied to AI Tuner\n\n"
                               f"Total points: {len(self.track_points)}\n"
                               f"Total tracks: {len(self.track_params)}\n"
                               f"Global k: {self.global_k:.4f}")
        
        # Close the dialog
        self.accept()  # This closes the dialog
    
    def log_message(self, msg: str, level: str = "info"):
        """Log message to status bar and console"""
        self.status_bar.showMessage(msg, 3000)
        logger.info(f"[CurveBuilder] {msg}")
