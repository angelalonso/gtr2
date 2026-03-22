"""
Global Curve Builder - Build a global curve from all track data
Shows best and worst AI times for each track, allows curve fitting and manual adjustment
"""

from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
import numpy as np
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.ticker import AutoMinorLocator
import json
from pathlib import Path
from scipy.optimize import minimize
import warnings
warnings.filterwarnings('ignore')


class GlobalCurveData:
    """Stores all track data and manages curve calculations"""
    
    def __init__(self):
        self.tracks = {}  # track_name -> {'ratios': [], 'best_times': [], 'worst_times': [], 'user_times': []}
        self.A = 300.0
        self.k = 3.0
        self.B = 100.0
        self.track_multipliers = {}
        self.r_squared = None
    
    def add_point(self, track_name, ratio, best_time, worst_time, user_time=0):
        """Add a data point for a track - best and worst are separate"""
        if track_name not in self.tracks:
            self.tracks[track_name] = {
                'ratios': [],
                'best_times': [],
                'worst_times': [],
                'user_times': []
            }
        
        # Add the point
        self.tracks[track_name]['ratios'].append(ratio)
        self.tracks[track_name]['best_times'].append(best_time)
        self.tracks[track_name]['worst_times'].append(worst_time)
        if user_time > 0:
            self.tracks[track_name]['user_times'].append((ratio, user_time))
        
        # Sort by ratio to keep everything aligned
        indices = np.argsort(self.tracks[track_name]['ratios'])
        self.tracks[track_name]['ratios'] = [self.tracks[track_name]['ratios'][i] for i in indices]
        self.tracks[track_name]['best_times'] = [self.tracks[track_name]['best_times'][i] for i in indices]
        self.tracks[track_name]['worst_times'] = [self.tracks[track_name]['worst_times'][i] for i in indices]
    
    def global_func(self, R, A, k, B):
        """Global exponential function"""
        return A * np.exp(-k * R) + B
    
    def predict_time(self, ratio, track_name):
        """Predict time for a specific track"""
        multiplier = self.track_multipliers.get(track_name, 1.0)
        return (self.A * np.exp(-self.k * ratio) + self.B) * multiplier
    
    def fit_curve(self):
        """Fit the global curve using all best times"""
        # Collect all best times
        all_ratios = []
        all_times = []
        track_indices = []
        track_names = list(self.tracks.keys())
        
        for idx, track_name in enumerate(track_names):
            for ratio, time in zip(self.tracks[track_name]['ratios'], self.tracks[track_name]['best_times']):
                all_ratios.append(ratio)
                all_times.append(time)
                track_indices.append(idx)
        
        if len(all_ratios) < 3:
            return False, f"Need at least 3 points across all tracks. Currently have {len(all_ratios)} points."
        
        def objective(params):
            A, k, B = params[:3]
            multipliers = params[3:]
            total_error = 0
            for i, (R, T) in enumerate(zip(all_ratios, all_times)):
                track_idx = track_indices[i]
                multiplier = multipliers[track_idx]
                predicted = (A * np.exp(-k * R) + B) * multiplier
                total_error += (predicted - T) ** 2
            return total_error
        
        times = np.array(all_times)
        B_guess = np.min(times) * 0.95
        A_guess = np.max(times) - B_guess
        k_guess = 2.0
        
        initial_params = [A_guess, k_guess, B_guess]
        for _ in track_names:
            initial_params.append(1.0)
        
        bounds = [(10, 1000), (0.1, 10), (30, 200)]
        for _ in track_names:
            bounds.append((0.1, 10))
        
        try:
            result = minimize(objective, initial_params, bounds=bounds, method='L-BFGS-B')
            if result.success:
                self.A, self.k, self.B = result.x[:3]
                for i, name in enumerate(track_names):
                    self.track_multipliers[name] = result.x[3 + i]
                
                # Calculate R²
                predictions = []
                for i, (R, T) in enumerate(zip(all_ratios, all_times)):
                    track_idx = track_indices[i]
                    multiplier = self.track_multipliers[track_names[track_idx]]
                    predicted = (self.A * np.exp(-self.k * R) + self.B) * multiplier
                    predictions.append(predicted)
                
                ss_res = np.sum((np.array(all_times) - np.array(predictions)) ** 2)
                ss_tot = np.sum((np.array(all_times) - np.mean(all_times)) ** 2)
                self.r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
                
                return True, f"Fit successful! R² = {self.r_squared:.6f}"
            else:
                return False, f"Optimization failed"
        except Exception as e:
            return False, f"Error: {str(e)}"
    
    def get_curve_points(self, track_name, r_min=0.3, r_max=3.0, num=200):
        """Get points for plotting the curve for a specific track"""
        multiplier = self.track_multipliers.get(track_name, 1.0)
        ratios = np.linspace(r_min, r_max, num)
        times = [(self.A * np.exp(-self.k * r) + self.B) * multiplier for r in ratios]
        return ratios, times
    
    def get_global_curve_points(self, r_min=0.3, r_max=3.0, num=200):
        """Get points for plotting the unscaled global curve"""
        ratios = np.linspace(r_min, r_max, num)
        times = [self.global_func(r, self.A, self.k, self.B) for r in ratios]
        return ratios, times
    
    def get_formula(self, track_name=None):
        """Get formula string"""
        if track_name and track_name in self.track_multipliers:
            mult = self.track_multipliers[track_name]
            return f"T = ({self.A:.2f} × e^(-{self.k:.4f} × R) + {self.B:.2f}) × {mult:.4f}"
        return f"T = {self.A:.2f} × e^(-{self.k:.4f} × R) + {self.B:.2f}"
    
    def get_stats(self):
        """Get statistics"""
        total_best = sum(len(t['best_times']) for t in self.tracks.values())
        total_worst = sum(len(t['worst_times']) for t in self.tracks.values())
        return {
            'tracks': len(self.tracks),
            'best_points': total_best,
            'worst_points': total_worst,
            'A': self.A,
            'k': self.k,
            'B': self.B,
            'r_squared': self.r_squared
        }
    
    def to_dict(self):
        """Convert to dictionary for saving"""
        return {
            'A': self.A,
            'k': self.k,
            'B': self.B,
            'track_multipliers': self.track_multipliers,
            'tracks': self.tracks,
            'r_squared': self.r_squared
        }
    
    @classmethod
    def from_dict(cls, data):
        """Create from dictionary - handles both old and new formats"""
        curve = cls()
        
        # New format with 'tracks'
        if 'tracks' in data:
            curve.A = data.get('A', 300.0)
            curve.k = data.get('k', 3.0)
            curve.B = data.get('B', 100.0)
            curve.track_multipliers = data.get('track_multipliers', {})
            curve.tracks = data.get('tracks', {})
            curve.r_squared = data.get('r_squared')
            return curve
        
        # Old format with 'points_by_track' (single point per ratio)
        if 'points_by_track' in data:
            curve.A = data.get('A', 300.0)
            curve.k = data.get('k', 3.0)
            curve.B = data.get('B', 100.0)
            curve.track_multipliers = data.get('track_multipliers', {})
            curve.r_squared = data.get('fit_error')
            
            points_by_track = data.get('points_by_track', {})
            for track_name, points in points_by_track.items():
                for ratio, time in points:
                    # Use same time for best and worst (no spread)
                    curve.add_point(track_name, ratio, time, time)
            return curve
        
        # Format with separate best/worst
        if 'best_points_by_track' in data:
            curve.A = data.get('A', 300.0)
            curve.k = data.get('k', 3.0)
            curve.B = data.get('B', 100.0)
            curve.track_multipliers = data.get('track_multipliers', {})
            curve.r_squared = data.get('fit_error')
            
            best_points = data.get('best_points_by_track', {})
            worst_points = data.get('worst_points_by_track', {})
            
            for track_name in best_points:
                best_list = best_points[track_name]
                worst_list = worst_points.get(track_name, [])
                for i, (ratio, best) in enumerate(best_list):
                    worst = worst_list[i][1] if i < len(worst_list) else best
                    curve.add_point(track_name, ratio, best, worst)
            return curve
        
        return curve


class ParameterDialog(QDialog):
    """Dialog for manual parameter adjustment"""
    
    def __init__(self, parent, A, k, B):
        super().__init__(parent)
        self.setWindowTitle("Adjust Curve Parameters")
        self.setModal(True)
        self.setMinimumWidth(400)
        
        self.A_val = A
        self.k_val = k
        self.B_val = B
        
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Formula display
        formula = QLabel(f"T = A × e^(-k × R) + B")
        formula.setStyleSheet("color: #FFA500; font-size: 14px; font-weight: bold;")
        layout.addWidget(formula)
        
        # Parameters
        grid = QGridLayout()
        
        grid.addWidget(QLabel("A (Amplitude):"), 0, 0)
        self.A_spin = QDoubleSpinBox()
        self.A_spin.setRange(10, 1000)
        self.A_spin.setDecimals(2)
        self.A_spin.setValue(self.A_val)
        self.A_spin.valueChanged.connect(self.update_formula)
        grid.addWidget(self.A_spin, 0, 1)
        
        grid.addWidget(QLabel("k (Decay Rate):"), 1, 0)
        self.k_spin = QDoubleSpinBox()
        self.k_spin.setRange(0.1, 10)
        self.k_spin.setDecimals(4)
        self.k_spin.setValue(self.k_val)
        self.k_spin.valueChanged.connect(self.update_formula)
        grid.addWidget(self.k_spin, 1, 1)
        
        grid.addWidget(QLabel("B (Asymptote):"), 2, 0)
        self.B_spin = QDoubleSpinBox()
        self.B_spin.setRange(30, 200)
        self.B_spin.setDecimals(2)
        self.B_spin.setValue(self.B_val)
        self.B_spin.valueChanged.connect(self.update_formula)
        grid.addWidget(self.B_spin, 2, 1)
        
        layout.addLayout(grid)
        
        # Live formula preview
        self.preview = QLabel()
        self.preview.setStyleSheet("color: #4CAF50; font-family: monospace;")
        layout.addWidget(self.preview)
        
        # Buttons
        btn_layout = QHBoxLayout()
        ok_btn = QPushButton("Apply")
        ok_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(ok_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)
        
        self.update_formula()
    
    def update_formula(self):
        A = self.A_spin.value()
        k = self.k_spin.value()
        B = self.B_spin.value()
        self.preview.setText(f"T = {A:.2f} × e^(-{k:.4f} × R) + {B:.2f}")
    
    def get_params(self):
        return self.A_spin.value(), self.k_spin.value(), self.B_spin.value()


class GlobalCurveBuilderDialog(QDialog):
    """Main dialog for building the global curve"""
    
    def __init__(self, parent=None, formulas_dir=None):
        super().__init__(parent)
        self.formulas_dir = Path(formulas_dir) if formulas_dir else Path("./track_formulas")
        self.formulas_dir.mkdir(parents=True, exist_ok=True)
        self.data = GlobalCurveData()
        self.current_track = None
        
        self.setWindowTitle("Global Curve Builder")
        self.setGeometry(100, 100, 1300, 800)
        self.setModal(True)
        
        self.setup_ui()
        self.load_data()
        self.update_track_list()
        self.update_graph()
        self.update_stats()
        self.update_formula()
    
    def setup_ui(self):
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
                border-radius: 3px;
                padding: 8px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QComboBox {
                background-color: #3c3c3c;
                color: white;
                border: 1px solid #4CAF50;
                border-radius: 3px;
                padding: 5px;
                min-width: 200px;
            }
            QGroupBox {
                color: #4CAF50;
                border: 2px solid #555;
                border-radius: 5px;
                margin-top: 8px;
                padding-top: 8px;
            }
            QTextEdit {
                background-color: #3c3c3c;
                color: #4CAF50;
                border: 1px solid #4CAF50;
                border-radius: 3px;
                font-family: monospace;
            }
        """)
        
        layout = QVBoxLayout(self)
        
        # Toolbar
        toolbar = self.create_toolbar()
        layout.addWidget(toolbar)
        
        # Stats
        stats_widget = QWidget()
        stats_layout = QHBoxLayout(stats_widget)
        self.stats_label = QLabel("Loading...")
        self.stats_label.setStyleSheet("color: #4CAF50;")
        stats_layout.addWidget(self.stats_label)
        stats_layout.addStretch()
        layout.addWidget(stats_widget)
        
        # Track selection
        track_widget = QWidget()
        track_layout = QHBoxLayout(track_widget)
        track_layout.addWidget(QLabel("Track:"))
        self.track_combo = QComboBox()
        self.track_combo.setMinimumWidth(250)
        track_layout.addWidget(self.track_combo)
        
        self.show_all_btn = QPushButton("Show All Tracks")
        self.show_all_btn.setFixedWidth(120)
        self.show_all_btn.clicked.connect(self.show_all_tracks)
        track_layout.addWidget(self.show_all_btn)
        
        track_layout.addStretch()
        layout.addWidget(track_widget)
        
        # Graph
        graph_group = QGroupBox("Curve Analysis - Hover over points for details (Circles = Best AI, Squares = Worst AI)")
        graph_layout = QVBoxLayout(graph_group)
        self.graph = GraphWidget(self)
        graph_layout.addWidget(self.graph)
        layout.addWidget(graph_group, 1)
        
        # Formula
        formula_group = QGroupBox("Current Formula")
        formula_layout = QVBoxLayout(formula_group)
        self.formula_text = QTextEdit()
        self.formula_text.setReadOnly(True)
        self.formula_text.setMaximumHeight(80)
        formula_layout.addWidget(self.formula_text)
        layout.addWidget(formula_group)
        
        # Status
        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet("color: #888; padding: 5px;")
        layout.addWidget(self.status_label)
    
    def create_toolbar(self):
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setSpacing(10)
        
        self.fit_btn = QPushButton("Fit Curve")
        self.fit_btn.setFixedHeight(35)
        self.fit_btn.setFixedWidth(120)
        self.fit_btn.clicked.connect(self.fit_curve)
        layout.addWidget(self.fit_btn)
        
        self.edit_btn = QPushButton("Edit Parameters")
        self.edit_btn.setFixedHeight(35)
        self.edit_btn.setFixedWidth(120)
        self.edit_btn.clicked.connect(self.edit_parameters)
        layout.addWidget(self.edit_btn)
        
        self.save_btn = QPushButton("Save Formula")
        self.save_btn.setFixedHeight(35)
        self.save_btn.setFixedWidth(120)
        self.save_btn.clicked.connect(self.save_formula)
        layout.addWidget(self.save_btn)
        
        sep = QFrame()
        sep.setFrameShape(QFrame.VLine)
        sep.setStyleSheet("background-color: #555;")
        layout.addWidget(sep)
        
        self.reset_btn = QPushButton("Reset View")
        self.reset_btn.setFixedHeight(35)
        self.reset_btn.setFixedWidth(100)
        self.reset_btn.clicked.connect(self.reset_view)
        layout.addWidget(self.reset_btn)
        
        self.save_img_btn = QPushButton("Save Image")
        self.save_img_btn.setFixedHeight(35)
        self.save_img_btn.setFixedWidth(100)
        self.save_img_btn.clicked.connect(self.save_image)
        layout.addWidget(self.save_img_btn)
        
        layout.addStretch()
        
        help_label = QLabel("💡 Circles = Best AI | Squares = Worst AI | Dashed lines connect best/worst at same ratio")
        help_label.setStyleSheet("color: #888; font-size: 10px;")
        layout.addWidget(help_label)
        
        return widget
    
    def load_data(self):
        """Load existing data from CSV files and saved curve"""
        # First, load from CSV files in the formulas directory
        csv_files = list(self.formulas_dir.glob("*.csv"))
        if csv_files:
            print(f"Found {len(csv_files)} CSV files to import")
            for csv_file in csv_files:
                self.import_csv(csv_file)
        
        # Then try to load saved curve (which may override some parameters)
        curve_path = self.formulas_dir / "global_curve.json"
        if curve_path.exists():
            try:
                with open(curve_path, 'r') as f:
                    data = json.load(f)
                saved_curve = GlobalCurveData.from_dict(data)
                
                # Merge the saved data with imported CSV data
                if saved_curve.tracks and not self.data.tracks:
                    # No CSV data, use saved curve data
                    self.data = saved_curve
                elif saved_curve.tracks:
                    # We have both, add saved points to existing data
                    for track_name, track_data in saved_curve.tracks.items():
                        for i, ratio in enumerate(track_data['ratios']):
                            best = track_data['best_times'][i]
                            worst = track_data['worst_times'][i]
                            self.data.add_point(track_name, ratio, best, worst)
                    
                    # Use saved curve parameters
                    self.data.A = saved_curve.A
                    self.data.k = saved_curve.k
                    self.data.B = saved_curve.B
                    self.data.track_multipliers = saved_curve.track_multipliers
                    self.data.r_squared = saved_curve.r_squared
                
                print(f"Loaded saved curve with {self.data.get_stats()['best_points']} best points")
            except Exception as e:
                print(f"Error loading saved curve: {e}")
        
        stats = self.data.get_stats()
        print(f"Total data loaded: {stats['best_points']} best points, {stats['worst_points']} worst points from {stats['tracks']} tracks")
    
    def import_csv(self, csv_path):
        """Import data from CSV file - stores both best and worst times"""
        try:
            import csv
            imported = 0
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
                        user = float(row.get('Qual User (s)', '0'))
                        if ratio > 0 and best > 0 and worst > 0:
                            self.data.add_point(track, ratio, best, worst, user)
                            imported += 1
                            print(f"  Added {track}: R={ratio:.3f}, Best={best:.2f}, Worst={worst:.2f}")
                    except Exception as e:
                        pass
                    
                    # Race data
                    try:
                        ratio = float(row.get('Current RaceRatio', '0'))
                        best = float(row.get('Race AI Best (s)', '0'))
                        worst = float(row.get('Race AI Worst (s)', '0'))
                        user = float(row.get('Race User (s)', '0'))
                        if ratio > 0 and best > 0 and worst > 0:
                            self.data.add_point(track, ratio, best, worst, user)
                            imported += 1
                            print(f"  Added {track}: R={ratio:.3f}, Best={best:.2f}, Worst={worst:.2f}")
                    except Exception as e:
                        pass
            
            if imported > 0:
                print(f"Imported {imported} points from {csv_path.name}")
        except Exception as e:
            print(f"Error importing {csv_path}: {e}")
    
    def update_track_list(self):
        """Update the track combo box"""
        self.track_combo.blockSignals(True)
        current = self.track_combo.currentText()
        self.track_combo.clear()
        
        tracks = list(self.data.tracks.keys())
        if tracks:
            self.track_combo.addItem("All Tracks")
            for track in sorted(tracks):
                self.track_combo.addItem(track)
            
            if current in tracks or current == "All Tracks":
                self.track_combo.setCurrentText(current)
        else:
            self.track_combo.addItem("No data")
        
        self.track_combo.blockSignals(False)
        self.track_combo.currentTextChanged.connect(self.on_track_changed)
    
    def on_track_changed(self, track_name):
        """Handle track selection change"""
        if track_name == "All Tracks" or track_name == "No data":
            self.current_track = None
        else:
            self.current_track = track_name
        self.update_graph()
        self.update_formula()
    
    def show_all_tracks(self):
        """Show all tracks"""
        if self.track_combo.count() > 0:
            self.track_combo.setCurrentText("All Tracks")
    
    def update_graph(self):
        """Update the graph display"""
        self.graph.set_data(self.data, self.current_track)
    
    def update_formula(self):
        """Update the formula display"""
        if self.current_track and self.current_track in self.data.track_multipliers:
            formula = self.data.get_formula(self.current_track)
            mult = self.data.track_multipliers.get(self.current_track, 1.0)
            text = f"Formula for {self.current_track}:\n{formula}\n\nMultiplier: {mult:.6f}"
        else:
            text = f"Global Curve:\n{self.data.get_formula()}"
        
        if self.data.r_squared:
            text += f"\n\nR² = {self.data.r_squared:.6f}"
        
        self.formula_text.setText(text)
    
    def update_stats(self):
        """Update stats display"""
        stats = self.data.get_stats()
        if stats['best_points'] > 0:
            self.stats_label.setText(f"📊 {stats['tracks']} tracks, {stats['best_points']} best points, {stats['worst_points']} worst points")
            if stats['r_squared']:
                self.stats_label.setText(self.stats_label.text() + f" | R² = {stats['r_squared']:.6f}")
        else:
            self.stats_label.setText("📊 No data points. Import CSV files to get started.")
    
    def fit_curve(self):
        """Fit the curve"""
        stats = self.data.get_stats()
        if stats['best_points'] < 3:
            QMessageBox.warning(self, "Insufficient Data", 
                               f"Need at least 3 best times to fit a curve.\nCurrently have {stats['best_points']} best points.")
            return
        
        self.status_label.setText("Fitting curve...")
        QApplication.processEvents()
        
        success, msg = self.data.fit_curve()
        
        if success:
            self.status_label.setText(msg)
            self.update_graph()
            self.update_formula()
            self.update_stats()
            QMessageBox.information(self, "Success", msg)
        else:
            self.status_label.setText("Fit failed")
            QMessageBox.warning(self, "Failed", msg)
    
    def edit_parameters(self):
        """Edit curve parameters manually"""
        dialog = ParameterDialog(self, self.data.A, self.data.k, self.data.B)
        if dialog.exec_() == QDialog.Accepted:
            A, k, B = dialog.get_params()
            self.data.A = A
            self.data.k = k
            self.data.B = B
            self.update_graph()
            self.update_formula()
            self.status_label.setText(f"Parameters updated: A={A:.2f}, k={k:.4f}, B={B:.2f}")
    
    def save_formula(self):
        """Save the curve"""
        try:
            path = self.formulas_dir / "global_curve.json"
            with open(path, 'w') as f:
                json.dump(self.data.to_dict(), f, indent=2)
            
            QMessageBox.information(self, "Saved", f"Formula saved to:\n{path}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save: {e}")
    
    def reset_view(self):
        """Reset graph view"""
        self.graph.reset_view()
        self.status_label.setText("View reset")
    
    def save_image(self):
        """Save graph image"""
        path, _ = QFileDialog.getSaveFileName(self, "Save Image", "global_curve.png", "PNG (*.png)")
        if path:
            self.graph.figure.savefig(path, dpi=150, facecolor='#1e1e1e')
            self.status_label.setText(f"Saved to {path}")


class GraphWidget(QWidget):
    """Matplotlib graph widget with hover tooltips"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.data = None
        self.current_track = None
        self.hover_annotation = None
        
        self.figure = Figure(figsize=(12, 8), facecolor='#1e1e1e')
        self.canvas = FigureCanvas(self.figure)
        
        self.canvas.mpl_connect('motion_notify_event', self.on_hover)
        
        self.toolbar = NavigationToolbar(self.canvas, self)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.toolbar)
        layout.addWidget(self.canvas)
        
        self.ax = self.figure.add_subplot(111)
        self.ax.set_facecolor('#2b2b2b')
        self.ax.grid(True, alpha=0.3)
        self.ax.set_axisbelow(True)
        
        for spine in self.ax.spines.values():
            spine.set_color('#4CAF50')
        
        self.ax.tick_params(colors='white')
        self.ax.xaxis.label.set_color('white')
        self.ax.yaxis.label.set_color('white')
        self.ax.title.set_color('#FFA500')
        
        self.setup_view()
    
    def setup_view(self):
        self.ax.set_xlabel('Ratio', fontsize=12)
        self.ax.set_ylabel('Lap Time (seconds)', fontsize=12)
        self.ax.set_title('Global Curve Builder', fontsize=14)
        self.ax.set_xlim(0.3, 3.0)
        self.ax.set_ylim(50, 200)
        self.ax.grid(True, alpha=0.1, which='minor')
        self.ax.xaxis.set_minor_locator(AutoMinorLocator())
        self.ax.yaxis.set_minor_locator(AutoMinorLocator())
        self.canvas.draw()
    
    def on_hover(self, event):
        """Handle hover for tooltips"""
        if event.inaxes != self.ax:
            if self.hover_annotation:
                self.hover_annotation.remove()
                self.hover_annotation = None
                self.canvas.draw_idle()
            return
        
        if not self.data:
            return
        
        mouse_x, mouse_y = event.x, event.y
        
        # Determine which tracks to check
        if self.current_track:
            tracks = [self.current_track]
        else:
            tracks = list(self.data.tracks.keys())
        
        for track in tracks:
            if track not in self.data.tracks:
                continue
            
            tdata = self.data.tracks[track]
            
            # Check best points (circles)
            for ratio, time in zip(tdata['ratios'], tdata['best_times']):
                x_px = self.ax.transData.transform((ratio, time))[0]
                y_px = self.ax.transData.transform((ratio, time))[1]
                dist = np.sqrt((x_px - mouse_x)**2 + (y_px - mouse_y)**2)
                
                if dist < 15:
                    if self.hover_annotation:
                        self.hover_annotation.remove()
                    text = f"{track}\nBEST AI\nR = {ratio:.4f}\nT = {time:.2f}s"
                    self.hover_annotation = self.ax.annotate(
                        text, xy=(ratio, time), xytext=(10, -15),
                        textcoords='offset points',
                        bbox=dict(boxstyle='round', facecolor='#2b2b2b', edgecolor='#4CAF50'),
                        color='#4CAF50', fontsize=9
                    )
                    self.canvas.draw_idle()
                    return
            
            # Check worst points (squares)
            for ratio, time in zip(tdata['ratios'], tdata['worst_times']):
                x_px = self.ax.transData.transform((ratio, time))[0]
                y_px = self.ax.transData.transform((ratio, time))[1]
                dist = np.sqrt((x_px - mouse_x)**2 + (y_px - mouse_y)**2)
                
                if dist < 15:
                    if self.hover_annotation:
                        self.hover_annotation.remove()
                    text = f"{track}\nWORST AI\nR = {ratio:.4f}\nT = {time:.2f}s"
                    self.hover_annotation = self.ax.annotate(
                        text, xy=(ratio, time), xytext=(10, -15),
                        textcoords='offset points',
                        bbox=dict(boxstyle='round', facecolor='#2b2b2b', edgecolor='#f44336'),
                        color='#f44336', fontsize=9
                    )
                    self.canvas.draw_idle()
                    return
        
        if self.hover_annotation:
            self.hover_annotation.remove()
            self.hover_annotation = None
            self.canvas.draw_idle()
    
    def set_data(self, data, current_track=None):
        """Update the graph with new data"""
        self.data = data
        self.current_track = current_track
        self.update_plot()
    
    def update_plot(self):
        """Redraw the plot"""
        self.ax.clear()
        self.setup_view()
        
        if not self.data or not self.data.tracks:
            # Show message if no data
            self.ax.text(0.5, 0.5, "No data loaded.\nImport CSV files to get started.",
                        transform=self.ax.transAxes, ha='center', va='center',
                        color='#888', fontsize=12)
            self.canvas.draw()
            return
        
        # Determine which tracks to show
        if self.current_track and self.current_track in self.data.tracks:
            tracks = [self.current_track]
        else:
            tracks = list(self.data.tracks.keys())
        
        # Colors for multiple tracks
        import matplotlib.pyplot as plt
        colors = plt.cm.tab10(np.linspace(0, 1, max(1, len(tracks))))
        
        # Track if we've shown any points
        shown_any = False
        
        for i, track in enumerate(tracks):
            if track not in self.data.tracks:
                continue
            
            tdata = self.data.tracks[track]
            ratios = tdata['ratios']
            best = tdata['best_times']
            worst = tdata['worst_times']
            
            if not ratios:
                continue
            
            shown_any = True
            
            # Determine color and size
            if track == self.current_track:
                color = '#4CAF50'
                best_size = 80
                worst_size = 80
                alpha = 1.0
                edge = 'white'
                linewidth = 2
                label_best = track
                label_worst = None
            else:
                color = colors[i % len(colors)]
                best_size = 50
                worst_size = 50
                alpha = 0.7
                edge = None
                linewidth = 1
                label_best = f"{track} (best)"
                label_worst = f"{track} (worst)"
            
            # Plot best times (circles)
            self.ax.scatter(ratios, best, c=color, s=best_size, marker='o',
                          alpha=alpha, label=label_best,
                          edgecolors=edge, linewidth=linewidth, zorder=3)
            
            # Plot worst times (squares) - always show them
            self.ax.scatter(ratios, worst, c=color, s=worst_size, marker='s',
                          alpha=alpha * 0.8, label=label_worst,
                          edgecolors=edge, linewidth=linewidth, zorder=3)
            
            # Connect best to worst at same ratio (dashed lines)
            for r, b, w in zip(ratios, best, worst):
                self.ax.plot([r, r], [b, w], c=color, alpha=0.4, linewidth=1, linestyle='--', zorder=2)
        
        if not shown_any:
            self.ax.text(0.5, 0.5, f"No points for {self.current_track if self.current_track else 'selected tracks'}",
                        transform=self.ax.transAxes, ha='center', va='center',
                        color='#888', fontsize=12)
            self.canvas.draw()
            return
        
        # Plot the curve
        if self.current_track and self.current_track in self.data.track_multipliers:
            ratios, times = self.data.get_curve_points(self.current_track)
            self.ax.plot(ratios, times, c='cyan', linewidth=2.5, linestyle='-', 
                        label=f'Curve for {self.current_track}', zorder=4)
            
            # Also show global curve for reference
            g_ratios, g_times = self.data.get_global_curve_points()
            self.ax.plot(g_ratios, g_times, c='#FFA500', linewidth=1.5, linestyle='--',
                        label='Global (unscaled)', alpha=0.6, zorder=3)
        elif self.data.A != 300 or self.data.k != 3 or self.data.B != 100 or self.data.r_squared:
            # Show global curve
            ratios, times = self.data.get_global_curve_points()
            self.ax.plot(ratios, times, c='cyan', linewidth=2.5, linestyle='-', 
                        label='Global Curve', zorder=4)
        
        # Legend
        handles, labels = self.ax.get_legend_handles_labels()
        if handles:
            unique = {}
            for h, l in zip(handles, labels):
                if l and l not in unique:
                    unique[l] = h
            self.ax.legend(handles=unique.values(), labels=unique.keys(),
                          loc='upper left', framealpha=0.8,
                          facecolor='#2b2b2b', edgecolor='#4CAF50',
                          labelcolor='white', fontsize=8)
        
        self.canvas.draw()
    
    def reset_view(self):
        """Reset to default view"""
        self.ax.autoscale()
        self.canvas.draw()


import matplotlib.pyplot as plt
