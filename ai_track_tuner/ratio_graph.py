"""
Dedicated Graph Window for Ratio vs Time Analysis
Supports interactive drawing, curve fitting with multiple formula types, and data visualization
"""

from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
import numpy as np
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.ticker import AutoMinorLocator
from matplotlib.lines import Line2D
from scipy.optimize import curve_fit
import warnings
warnings.filterwarnings('ignore', category=RuntimeWarning)


class CurveFitter:
    """Handles curve fitting to approximate points"""
    
    def __init__(self):
        self.points = []  # List of (ratio, time)
        self.fitted_params = None
        self.fit_error = None
        self.fit_type = None
        self.formula_string = ""
        self.available_fits = []  # List of (fit_type, params, error, formula)
    
    def add_point(self, ratio, time):
        """Add a point"""
        self.points.append((ratio, time))
        self.points.sort(key=lambda x: x[0])
        self.fitted_params = None  # Clear fit when points change
        self.available_fits = []
    
    def remove_point(self, index):
        """Remove a point by index"""
        if 0 <= index < len(self.points):
            del self.points[index]
            self.fitted_params = None
            self.available_fits = []
    
    def clear_points(self):
        """Clear all points"""
        self.points = []
        self.fitted_params = None
        self.fit_error = None
        self.fit_type = None
        self.available_fits = []
    
    # Formula types
    def linear_func(self, R, a, b):
        """Linear: T = a * R + b"""
        return a * R + b
    
    def power_func(self, R, a, b, c):
        """Power: T = a * R^b + c"""
        return a * (R ** b) + c
    
    def exponential_func(self, R, a, b, c):
        """Exponential: T = a * exp(-b * R) + c"""
        return a * np.exp(-b * R) + c
    
    def polynomial_2_func(self, R, a, b, c):
        """Quadratic: T = a * R^2 + b * R + c"""
        return a * R**2 + b * R + c
    
    def polynomial_3_func(self, R, a, b, c, d):
        """Cubic: T = a * R^3 + b * R^2 + c * R + d"""
        return a * R**3 + b * R**2 + c * R + d
    
    def fit_linear(self):
        """Fit linear: T = a * R + b"""
        if len(self.points) < 2:
            return None, None, "Need at least 2 points"
        
        ratios = np.array([p[0] for p in self.points])
        times = np.array([p[1] for p in self.points])
        
        try:
            # Use polyfit for linear (more stable)
            coeffs = np.polyfit(ratios, times, 1)
            a, b = coeffs[0], coeffs[1]
            
            # Calculate R-squared
            predictions = a * ratios + b
            residuals = times - predictions
            ss_res = np.sum(residuals**2)
            ss_tot = np.sum((times - np.mean(times))**2)
            r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
            
            formula = f"T = {a:.4f} × R + {b:.4f}"
            return [a, b], r_squared, formula
        except Exception as e:
            return None, None, str(e)
    
    def fit_power(self):
        """Fit power: T = a * R^b + c"""
        if len(self.points) < 3:
            return None, None, "Need at least 3 points"
        
        ratios = np.array([p[0] for p in self.points])
        times = np.array([p[1] for p in self.points])
        
        # Ensure all ratios > 0 and times > 0
        if np.any(ratios <= 0) or np.any(times <= 0):
            return None, None, "Power fit requires positive values"
        
        try:
            # Try to fit using polyfit on log-log for initial guess
            # For a*R^b + c, we can approximate with log(t-c) = log(a) + b*log(R)
            c_guess = np.min(times) * 0.95
            log_t = np.log(times - c_guess + 0.001)
            log_r = np.log(ratios)
            coeffs = np.polyfit(log_r, log_t, 1)
            a_guess = np.exp(coeffs[1])
            b_guess = coeffs[0]
            
            popt, pcov = curve_fit(self.power_func, ratios, times, 
                                   p0=[a_guess, b_guess, c_guess],
                                   maxfev=5000)
            
            predictions = self.power_func(ratios, *popt)
            residuals = times - predictions
            ss_res = np.sum(residuals**2)
            ss_tot = np.sum((times - np.mean(times))**2)
            r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
            
            formula = f"T = {popt[0]:.4f} × R^{popt[1]:.4f} + {popt[2]:.4f}"
            return popt.tolist(), r_squared, formula
        except Exception as e:
            return None, None, str(e)
    
    def fit_exponential(self):
        """Fit exponential: T = a * exp(-b * R) + c"""
        if len(self.points) < 3:
            return None, None, "Need at least 3 points"
        
        ratios = np.array([p[0] for p in self.points])
        times = np.array([p[1] for p in self.points])
        
        try:
            # Initial guess
            c_guess = np.min(times) * 0.9
            a_guess = np.max(times) - c_guess
            b_guess = 1.0
            
            # Try to fit with bounds
            bounds = ([0, 0.01, 0], [np.inf, 10, np.max(times)])
            popt, pcov = curve_fit(self.exponential_func, ratios, times, 
                                   p0=[a_guess, b_guess, c_guess],
                                   bounds=bounds, maxfev=5000)
            
            predictions = self.exponential_func(ratios, *popt)
            residuals = times - predictions
            ss_res = np.sum(residuals**2)
            ss_tot = np.sum((times - np.mean(times))**2)
            r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
            
            formula = f"T = {popt[0]:.4f} × e^(-{popt[1]:.4f} × R) + {popt[2]:.4f}"
            return popt.tolist(), r_squared, formula
        except Exception as e:
            return None, None, str(e)
    
    def fit_quadratic(self):
        """Fit quadratic: T = a * R^2 + b * R + c"""
        if len(self.points) < 3:
            return None, None, "Need at least 3 points"
        
        ratios = np.array([p[0] for p in self.points])
        times = np.array([p[1] for p in self.points])
        
        try:
            # Use polyfit for quadratic (more stable)
            coeffs = np.polyfit(ratios, times, 2)
            a, b, c = coeffs[0], coeffs[1], coeffs[2]
            
            # Calculate R-squared
            predictions = a * ratios**2 + b * ratios + c
            residuals = times - predictions
            ss_res = np.sum(residuals**2)
            ss_tot = np.sum((times - np.mean(times))**2)
            r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
            
            formula = f"T = {a:.4f}×R² + {b:.4f}×R + {c:.4f}"
            return [a, b, c], r_squared, formula
        except Exception as e:
            return None, None, str(e)
    
    def fit_cubic(self):
        """Fit cubic: T = a * R^3 + b * R^2 + c * R + d"""
        if len(self.points) < 4:
            return None, None, "Need at least 4 points"
        
        ratios = np.array([p[0] for p in self.points])
        times = np.array([p[1] for p in self.points])
        
        try:
            # Use polyfit for cubic (more stable)
            coeffs = np.polyfit(ratios, times, 3)
            a, b, c, d = coeffs[0], coeffs[1], coeffs[2], coeffs[3]
            
            # Calculate R-squared
            predictions = a * ratios**3 + b * ratios**2 + c * ratios + d
            residuals = times - predictions
            ss_res = np.sum(residuals**2)
            ss_tot = np.sum((times - np.mean(times))**2)
            r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
            
            formula = f"T = {a:.4f}×R³ + {b:.4f}×R² + {c:.4f}×R + {d:.4f}"
            return [a, b, c, d], r_squared, formula
        except Exception as e:
            return None, None, str(e)
    
    def fit_all_types(self):
        """Try all fit types and collect results"""
        self.available_fits = []
        
        # Always try linear (needs 2 points)
        if len(self.points) >= 2:
            params, r_squared, formula = self.fit_linear()
            if params is not None:
                self.available_fits.append({
                    'type': 'Linear',
                    'params': params,
                    'r_squared': r_squared,
                    'formula': formula,
                    'func': self.linear_func
                })
        
        # Quadratic (needs 3 points)
        if len(self.points) >= 3:
            params, r_squared, formula = self.fit_quadratic()
            if params is not None:
                self.available_fits.append({
                    'type': 'Quadratic',
                    'params': params,
                    'r_squared': r_squared,
                    'formula': formula,
                    'func': self.polynomial_2_func
                })
        
        # Power (needs 3 points)
        if len(self.points) >= 3:
            params, r_squared, formula = self.fit_power()
            if params is not None:
                self.available_fits.append({
                    'type': 'Power',
                    'params': params,
                    'r_squared': r_squared,
                    'formula': formula,
                    'func': self.power_func
                })
        
        # Exponential (needs 3 points)
        if len(self.points) >= 3:
            params, r_squared, formula = self.fit_exponential()
            if params is not None:
                self.available_fits.append({
                    'type': 'Exponential',
                    'params': params,
                    'r_squared': r_squared,
                    'formula': formula,
                    'func': self.exponential_func
                })
        
        # Cubic (needs 4 points)
        if len(self.points) >= 4:
            params, r_squared, formula = self.fit_cubic()
            if params is not None:
                self.available_fits.append({
                    'type': 'Cubic',
                    'params': params,
                    'r_squared': r_squared,
                    'formula': formula,
                    'func': self.polynomial_3_func
                })
        
        # Sort by R² (best first)
        self.available_fits.sort(key=lambda x: x['r_squared'], reverse=True)
        
        return self.available_fits
    
    def select_fit(self, index=0):
        """Select a fit by index"""
        if 0 <= index < len(self.available_fits):
            fit = self.available_fits[index]
            self.fit_type = fit['type']
            self.fitted_params = fit['params']
            self.fit_error = fit['r_squared']
            self.formula_string = fit['formula']
            return True
        return False
    
    def predict_time(self, ratio):
        """Predict time for a given ratio using selected fit"""
        if self.fitted_params is None or self.fit_type is None:
            return None
        
        try:
            if self.fit_type == 'Linear':
                a, b = self.fitted_params
                return a * ratio + b
            elif self.fit_type == 'Quadratic':
                a, b, c = self.fitted_params
                return a * ratio**2 + b * ratio + c
            elif self.fit_type == 'Cubic':
                a, b, c, d = self.fitted_params
                return a * ratio**3 + b * ratio**2 + c * ratio + d
            elif self.fit_type == 'Power':
                a, b, c = self.fitted_params
                return a * (ratio ** b) + c
            elif self.fit_type == 'Exponential':
                a, b, c = self.fitted_params
                return a * np.exp(-b * ratio) + c
        except:
            return None
        return None
    
    def predict_ratio(self, time, tolerance=0.001, max_iter=100):
        """Predict ratio for a given time using binary search"""
        if self.fitted_params is None or self.fit_type is None or len(self.points) < 2:
            return None
        
        # Get ratio range from points
        ratios = [p[0] for p in self.points]
        r_min = min(ratios)
        r_max = max(ratios)
        
        # Check if time is within range
        t_min = self.predict_time(r_min)
        t_max = self.predict_time(r_max)
        
        if t_min is None or t_max is None:
            return None
        
        if time < min(t_min, t_max) - tolerance or time > max(t_min, t_max) + tolerance:
            return None
        
        # Binary search
        left, right = r_min, r_max
        
        # Determine if function is decreasing
        if t_min > t_max:
            for _ in range(max_iter):
                mid = (left + right) / 2
                t_mid = self.predict_time(mid)
                if t_mid is None:
                    return None
                if abs(t_mid - time) < tolerance:
                    return mid
                if t_mid > time:
                    left = mid
                else:
                    right = mid
        else:
            for _ in range(max_iter):
                mid = (left + right) / 2
                t_mid = self.predict_time(mid)
                if t_mid is None:
                    return None
                if abs(t_mid - time) < tolerance:
                    return mid
                if t_mid < time:
                    left = mid
                else:
                    right = mid
        
        return (left + right) / 2
    
    def get_curve_points(self, ratio_min=None, ratio_max=None, num_points=200):
        """Get points for plotting the fitted curve"""
        if self.fitted_params is None or self.fit_type is None:
            return [], []
        
        if ratio_min is None and self.points:
            ratio_min = min([p[0] for p in self.points])
        if ratio_max is None and self.points:
            ratio_max = max([p[0] for p in self.points])
        
        if ratio_min is None or ratio_max is None:
            ratio_min, ratio_max = 0.5, 2.0
        
        # Extend range slightly
        ratio_min = max(0.1, ratio_min * 0.9)
        ratio_max = ratio_max * 1.1
        
        ratios = np.linspace(ratio_min, ratio_max, num_points)
        times = [self.predict_time(r) for r in ratios]
        
        valid = [(r, t) for r, t in zip(ratios, times) if t is not None]
        if valid:
            ratios, times = zip(*valid)
            return np.array(ratios), np.array(times)
        
        return [], []


class FormulaSelectionDialog(QDialog):
    """Dialog for selecting which formula to use"""
    
    def __init__(self, parent=None, fits=None):
        super().__init__(parent)
        self.parent_window = parent
        self.fits = fits or []
        self.selected_index = 0
        
        self.setWindowTitle("Select Curve Formula")
        self.setMinimumWidth(550)
        self.setMinimumHeight(450)
        
        self.setStyleSheet("""
            QDialog {
                background-color: #2b2b2b;
            }
            QLabel {
                color: white;
                font-size: 12px;
            }
            QListWidget {
                background-color: #3c3c3c;
                color: #4CAF50;
                border: 1px solid #4CAF50;
                border-radius: 3px;
                font-family: monospace;
                font-size: 11px;
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
            QGroupBox {
                color: #4CAF50;
                border: 2px solid #555;
                border-radius: 5px;
                margin-top: 8px;
                padding-top: 8px;
            }
        """)
        
        layout = QVBoxLayout(self)
        
        # Info label
        info_label = QLabel(f"Found {len(fits)} formula types that fit your points:")
        info_label.setStyleSheet("color: #FFA500; font-size: 12px;")
        layout.addWidget(info_label)
        
        # List of formulas
        self.list_widget = QListWidget()
        for i, fit in enumerate(fits):
            r2 = fit['r_squared']
            # Truncate formula if too long
            formula = fit['formula']
            if len(formula) > 70:
                formula = formula[:67] + "..."
            item_text = f"{fit['type']}: R² = {r2:.6f}\n  {formula}"
            self.list_widget.addItem(item_text)
        
        layout.addWidget(self.list_widget)
        
        # Buttons
        btn_layout = QHBoxLayout()
        
        select_btn = QPushButton("Select This Formula")
        select_btn.clicked.connect(self.select_formula)
        btn_layout.addWidget(select_btn)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        
        layout.addLayout(btn_layout)
        
        # Select first item by default
        if self.list_widget.count() > 0:
            self.list_widget.setCurrentRow(0)
    
    def select_formula(self):
        """Select the current formula"""
        self.selected_index = self.list_widget.currentRow()
        self.accept()
    
    def get_selected_index(self):
        return self.selected_index


class RatioGraphWindow(QMainWindow):
    """Main window for ratio vs time graph with interactive features"""
    
    def __init__(self, parent=None, track_name=""):
        super().__init__(parent)
        self.track_name = track_name
        self.qual_points = []
        self.race_points = []
        self.current_times = None
        self.current_ratio = None
        self.current_type = None
        self.drawing_mode = False
        self.curve_fitting_dialog = None
        self.formula_selection_dialog = None
        
        self.setWindowTitle(f"Ratio Graph Analysis - {track_name}")
        self.setGeometry(100, 100, 1400, 900)
        
        self.setup_ui()
        self.setup_connections()
    
    def setup_ui(self):
        """Setup the user interface"""
        self.setStyleSheet("""
            QMainWindow {
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
                padding: 8px 15px;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:checked {
                background-color: #f44336;
            }
            QGroupBox {
                color: #4CAF50;
                font-weight: bold;
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
        """)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        # Top toolbar
        toolbar = self.create_toolbar()
        main_layout.addWidget(toolbar)
        
        # Stats bar
        stats_widget = QWidget()
        stats_widget.setStyleSheet("background-color: #2b2b2b; border-radius: 3px; padding: 5px;")
        stats_layout = QHBoxLayout(stats_widget)
        stats_layout.setContentsMargins(10, 5, 10, 5)
        
        self.stats_label = QLabel("Loading data...")
        self.stats_label.setStyleSheet("color: #4CAF50; font-size: 11px;")
        stats_layout.addWidget(self.stats_label)
        stats_layout.addStretch()
        
        main_layout.addWidget(stats_widget)
        
        # Graph area
        graph_group = QGroupBox("Interactive Graph - Click points to add data | Use mouse to zoom/pan")
        graph_layout = QVBoxLayout(graph_group)
        
        self.graph_widget = GraphWidget(self)
        graph_layout.addWidget(self.graph_widget)
        
        main_layout.addWidget(graph_group, 1)
        
        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")
    
    def create_toolbar(self):
        """Create the toolbar with controls"""
        toolbar_widget = QWidget()
        toolbar_layout = QHBoxLayout(toolbar_widget)
        toolbar_layout.setSpacing(10)
        
        # Drawing mode toggle
        self.drawing_toggle = QPushButton("✏️ Draw Points Mode")
        self.drawing_toggle.setCheckable(True)
        self.drawing_toggle.setFixedHeight(35)
        self.drawing_toggle.setFixedWidth(150)
        toolbar_layout.addWidget(self.drawing_toggle)
        
        # Clear points button
        self.clear_points_btn = QPushButton("🗑️ Clear Points")
        self.clear_points_btn.setFixedHeight(35)
        self.clear_points_btn.setFixedWidth(120)
        toolbar_layout.addWidget(self.clear_points_btn)
        
        # Fit curve button
        self.fit_curve_btn = QPushButton("📈 Fit Curve")
        self.fit_curve_btn.setFixedHeight(35)
        self.fit_curve_btn.setFixedWidth(120)
        self.fit_curve_btn.setEnabled(False)
        self.fit_curve_btn.clicked.connect(self.fit_curve)
        toolbar_layout.addWidget(self.fit_curve_btn)
        
        # Select formula button
        self.select_formula_btn = QPushButton("🎯 Select Formula")
        self.select_formula_btn.setFixedHeight(35)
        self.select_formula_btn.setFixedWidth(120)
        self.select_formula_btn.setEnabled(False)
        self.select_formula_btn.clicked.connect(self.select_formula)
        toolbar_layout.addWidget(self.select_formula_btn)
        
        # Show info button
        self.show_info_btn = QPushButton("📊 Show Info")
        self.show_info_btn.setFixedHeight(35)
        self.show_info_btn.setFixedWidth(100)
        self.show_info_btn.setEnabled(False)
        self.show_info_btn.clicked.connect(self.show_curve_info)
        toolbar_layout.addWidget(self.show_info_btn)
        
        # Separator
        sep = QFrame()
        sep.setFrameShape(QFrame.VLine)
        sep.setFrameShadow(QFrame.Sunken)
        sep.setStyleSheet("background-color: #555;")
        toolbar_layout.addWidget(sep)
        
        # Reset view button
        self.reset_view_btn = QPushButton("🔄 Reset View")
        self.reset_view_btn.setFixedHeight(35)
        self.reset_view_btn.setFixedWidth(100)
        self.reset_view_btn.clicked.connect(self.reset_view)
        toolbar_layout.addWidget(self.reset_view_btn)
        
        # Save image button
        self.save_image_btn = QPushButton("💾 Save Image")
        self.save_image_btn.setFixedHeight(35)
        self.save_image_btn.setFixedWidth(100)
        self.save_image_btn.clicked.connect(self.save_graph_image)
        toolbar_layout.addWidget(self.save_image_btn)
        
        toolbar_layout.addStretch()
        
        # Track info
        track_info = QLabel(f"<b>Track:</b> {self.track_name}")
        track_info.setStyleSheet("color: #FFA500; font-size: 12px; padding: 5px;")
        toolbar_layout.addWidget(track_info)
        
        return toolbar_widget
    
    def setup_connections(self):
        """Setup signal connections"""
        self.drawing_toggle.toggled.connect(self.toggle_drawing_mode)
        self.clear_points_btn.clicked.connect(self.clear_drawn_points)
    
    def toggle_drawing_mode(self, enabled):
        """Toggle drawing mode on/off"""
        self.drawing_mode = enabled
        self.graph_widget.enable_drawing_mode(enabled)
        if enabled:
            self.status_bar.showMessage("Drawing mode ON - Click on graph to add points (Ratio, Time)")
        else:
            self.status_bar.showMessage("Drawing mode OFF")
    
    def on_point_added(self, ratio, time):
        """Handle point added to graph"""
        self.status_bar.showMessage(f"Point added: R={ratio:.4f}, T={time:.2f}s")
        self.fit_curve_btn.setEnabled(True)
        
        # Clear existing fit when new points are added
        self.graph_widget.clear_fit_curve()
        self.select_formula_btn.setEnabled(False)
        self.show_info_btn.setEnabled(False)
    
    def remove_point(self, index):
        """Remove a point by index"""
        self.graph_widget.curve_fitter.remove_point(index)
        self.graph_widget.update_drawing_points()
        
        # Clear fit when points change
        self.graph_widget.clear_fit_curve()
        
        if len(self.graph_widget.curve_fitter.points) < 2:
            self.fit_curve_btn.setEnabled(False)
            self.select_formula_btn.setEnabled(False)
            self.show_info_btn.setEnabled(False)
        
        self.status_bar.showMessage(f"Removed point {index+1}")
    
    def clear_drawn_points(self):
        """Clear all drawn points"""
        self.graph_widget.clear_drawn_points()
        self.graph_widget.clear_fit_curve()
        self.fit_curve_btn.setEnabled(False)
        self.select_formula_btn.setEnabled(False)
        self.show_info_btn.setEnabled(False)
        self.status_bar.showMessage("Cleared all drawn points")
    
    def fit_curve(self):
        """Fit curve to points"""
        if len(self.graph_widget.curve_fitter.points) < 2:
            self.status_bar.showMessage("Need at least 2 points to fit a curve")
            return
        
        self.status_bar.showMessage("Fitting curves...")
        QApplication.processEvents()
        
        # Try all fit types
        fits = self.graph_widget.curve_fitter.fit_all_types()
        
        if not fits:
            self.status_bar.showMessage("Could not fit any curve to these points")
            QMessageBox.warning(self, "Fit Failed", 
                               "Could not fit any curve to these points.\n\n"
                               "Try adding more points or using different values.")
            return
        
        # Automatically select the best fit
        self.graph_widget.curve_fitter.select_fit(0)
        self.graph_widget.update_fit_curve()
        
        self.select_formula_btn.setEnabled(len(fits) > 1)
        self.show_info_btn.setEnabled(True)
        
        self.status_bar.showMessage(f"Curve fitted! Best fit: {fits[0]['type']} (R² = {fits[0]['r_squared']:.6f})")
    
    def select_formula(self):
        """Open dialog to select formula"""
        if not self.graph_widget.curve_fitter.available_fits:
            QMessageBox.information(self, "No Fits", "Please fit a curve first.")
            return
        
        dialog = FormulaSelectionDialog(self, self.graph_widget.curve_fitter.available_fits)
        if dialog.exec_() == QDialog.Accepted:
            index = dialog.get_selected_index()
            self.graph_widget.curve_fitter.select_fit(index)
            self.graph_widget.update_fit_curve()
            fit = self.graph_widget.curve_fitter.available_fits[index]
            self.status_bar.showMessage(f"Selected: {fit['type']} (R² = {fit['r_squared']:.6f})")
    
    def show_curve_info(self):
        """Show curve information"""
        if self.graph_widget.curve_fitter.fitted_params is None:
            QMessageBox.information(self, "No Curve", "Please fit a curve first.")
            return
        
        fit = None
        for f in self.graph_widget.curve_fitter.available_fits:
            if f['type'] == self.graph_widget.curve_fitter.fit_type:
                fit = f
                break
        
        if not fit:
            return
        
        info = f"<b>Current Formula:</b><br><br>"
        info += f"<tt style='color: #4CAF50; font-size: 12px;'>{fit['formula']}</tt><br><br>"
        info += f"<b>R² = {fit['r_squared']:.6f}</b><br><br>"
        info += f"<b>Points used:</b> {len(self.graph_widget.curve_fitter.points)}<br>"
        
        # Show point deviations
        info += f"<br><b>Deviations:</b><br>"
        total_error = 0
        for i, (r, t) in enumerate(self.graph_widget.curve_fitter.points):
            predicted = self.graph_widget.curve_fitter.predict_time(r)
            if predicted:
                diff = t - predicted
                total_error += abs(diff)
                info += f"  Point {i+1}: {diff:+.4f}s (error: {abs(diff):.3f}s)<br>"
        
        avg_error = total_error / len(self.graph_widget.curve_fitter.points)
        info += f"<br><b>Average error:</b> {avg_error:.3f}s"
        
        msg = QMessageBox(self)
        msg.setWindowTitle("Curve Information")
        msg.setText(info)
        msg.setStandardButtons(QMessageBox.Ok)
        msg.setStyleSheet("""
            QMessageBox {
                background-color: #2b2b2b;
                color: white;
            }
            QPushButton {
                background-color: #4CAF50;
                color: white;
                padding: 8px 20px;
                border-radius: 3px;
            }
        """)
        msg.exec_()
    
    def get_ratio_from_time(self, time):
        """Get predicted ratio for a given time"""
        return self.graph_widget.curve_fitter.predict_ratio(time)
    
    def reset_view(self):
        """Reset the graph view"""
        self.graph_widget.reset_view()
        self.status_bar.showMessage("View reset to default", 2000)
    
    def save_graph_image(self):
        """Save the current graph as an image"""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Graph Image",
            f"{self.track_name}_ratio_graph.png",
            "PNG Images (*.png);;All Files (*)"
        )
        
        if file_path:
            self.graph_widget.figure.savefig(file_path, dpi=150, facecolor='#1e1e1e')
            self.status_bar.showMessage(f"Graph saved to {file_path}", 3000)
    
    def set_data(self, qual_points, race_points, current_times=None, current_ratio=None, current_type=None):
        """Set the data for the graph"""
        self.qual_points = qual_points or []
        self.race_points = race_points or []
        self.current_times = current_times
        self.current_ratio = current_ratio
        self.current_type = current_type
        
        qual_count = len(self.qual_points)
        race_count = len(self.race_points)
        total = qual_count + race_count
        
        if total > 0:
            self.stats_label.setText(f"📊 Historic Data: {total} total points (Qualifying: {qual_count}, Race: {race_count})")
        else:
            self.stats_label.setText("📊 No historic data available for this track")
        
        self.graph_widget.set_data(qual_points, race_points, current_times, current_ratio, current_type)


class GraphWidget(QWidget):
    """Widget containing matplotlib figure with interactive drawing"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.curve_fitter = CurveFitter()
        self.fit_curve_line = None
        self.user_points_scatter = None
        self.current_temp_point = None
        self.formula_annotation = None
        self.hover_annotation = None
        self.hover_point = None
        
        # Create figure and canvas
        self.figure = Figure(figsize=(12, 8), facecolor='#1e1e1e')
        self.canvas = FigureCanvas(self.figure)
        
        # Connect mouse events
        self.canvas.mpl_connect('button_press_event', self.on_click)
        self.canvas.mpl_connect('motion_notify_event', self.on_motion)
        
        # Create toolbar
        self.toolbar = NavigationToolbar(self.canvas, self)
        self.toolbar.setStyleSheet("""
            QToolBar {
                background-color: #2b2b2b;
                border: none;
                spacing: 3px;
            }
            QToolButton {
                background-color: #3c3c3c;
                border: 1px solid #4CAF50;
                border-radius: 3px;
                padding: 5px;
            }
            QToolButton:hover {
                background-color: #4CAF50;
            }
        """)
        
        # Layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        layout.addWidget(self.toolbar)
        layout.addWidget(self.canvas)
        
        # Create axes
        self.ax = self.figure.add_subplot(111)
        self.ax.set_facecolor('#2b2b2b')
        
        # Configure grid
        self.ax.grid(True, alpha=0.3, color='gray', linestyle='-', linewidth=0.5)
        self.ax.set_axisbelow(True)
        
        # Style spines
        for spine in self.ax.spines.values():
            spine.set_color('#4CAF50')
            spine.set_linewidth(1.5)
        
        # Style ticks
        self.ax.tick_params(colors='white', labelsize=9)
        self.ax.xaxis.label.set_color('white')
        self.ax.yaxis.label.set_color('white')
        self.ax.title.set_color('#FFA500')
        
        # Data storage
        self.qual_points = []
        self.race_points = []
        self.current_times = None
        self.current_ratio = None
        self.current_type = None
        self.drawing_mode = False
        
        self.setup_default_view()
    
    def setup_default_view(self):
        """Setup initial view limits"""
        self.ax.set_xlabel('Ratio', fontsize=12, fontweight='bold')
        self.ax.set_ylabel('Lap Time (seconds)', fontsize=12, fontweight='bold')
        self.ax.set_title('Ratio vs Lap Time Relationship', fontsize=14, fontweight='bold')
        self.ax.set_xlim(0.5, 2.0)
        self.ax.set_ylim(60, 180)
        
        self.ax.grid(True, alpha=0.1, which='minor', linestyle=':', linewidth=0.5)
        self.ax.xaxis.set_minor_locator(AutoMinorLocator())
        self.ax.yaxis.set_minor_locator(AutoMinorLocator())
        
        self.canvas.draw()
    
    def enable_drawing_mode(self, enabled):
        """Enable or disable drawing mode"""
        self.drawing_mode = enabled
        if enabled:
            self.ax.set_title('Drawing Mode ON - Click to add points (Ratio, Time)', 
                             fontsize=12, fontweight='bold', color='#FFA500')
        else:
            self.ax.set_title('Ratio vs Lap Time Relationship', fontsize=14, fontweight='bold', color='#FFA500')
        self.canvas.draw()
    
    def on_click(self, event):
        """Handle mouse clicks for drawing points"""
        if not self.drawing_mode:
            return
        
        if event.inaxes != self.ax:
            return
        
        ratio = event.xdata
        time = event.ydata
        
        if ratio and time:
            self.curve_fitter.add_point(ratio, time)
            parent_window = self.window()
            if hasattr(parent_window, 'on_point_added'):
                parent_window.on_point_added(ratio, time)
            self.update_drawing_points()
    
    def on_motion(self, event):
        """Handle mouse motion for hover tooltips"""
        if event.inaxes != self.ax:
            if self.hover_annotation:
                self.hover_annotation.remove()
                self.hover_annotation = None
                self.hover_point = None
                self.canvas.draw_idle()
            if self.current_temp_point and self.drawing_mode:
                self.current_temp_point.remove()
                self.current_temp_point = None
                self.canvas.draw_idle()
            return
        
        # Handle drawing mode preview
        if self.drawing_mode:
            ratio = event.xdata
            time = event.ydata
            if ratio and time:
                if self.current_temp_point:
                    self.current_temp_point.remove()
                self.current_temp_point = self.ax.scatter([ratio], [time], 
                                                          c='yellow', s=50, marker='x',
                                                          alpha=0.7, zorder=10)
                self.canvas.draw_idle()
            return
        
        # Handle hover tooltips for user-drawn points
        if self.user_points_scatter and self.curve_fitter.points:
            # Check if hovering over any user point
            for point in self.curve_fitter.points:
                x, y = point
                # Check distance in pixels
                x_pixel = self.ax.transData.transform((x, y))[0]
                mouse_x = event.x
                mouse_y = event.y
                y_pixel = self.ax.transData.transform((x, y))[1]
                dist = np.sqrt((x_pixel - mouse_x)**2 + (y_pixel - mouse_y)**2)
                
                if dist < 15:  # 15 pixel tolerance
                    if self.hover_point != point:
                        if self.hover_annotation:
                            self.hover_annotation.remove()
                        text = f"R = {x:.4f}\nT = {y:.2f}s"
                        self.hover_annotation = self.ax.annotate(
                            text, xy=(x, y), xytext=(10, -15),
                            textcoords='offset points',
                            bbox=dict(boxstyle='round', facecolor='#2b2b2b', 
                                     edgecolor='#FFA500', alpha=0.9),
                            color='#FFA500', fontsize=9, fontfamily='monospace',
                            arrowprops=dict(arrowstyle='->', color='#FFA500')
                        )
                        self.hover_point = point
                        self.canvas.draw_idle()
                    return
            
            # No point under cursor
            if self.hover_annotation:
                self.hover_annotation.remove()
                self.hover_annotation = None
                self.hover_point = None
                self.canvas.draw_idle()
    
    def update_drawing_points(self):
        """Update the display of user-drawn points (smaller markers)"""
        if self.user_points_scatter:
            self.user_points_scatter.remove()
        
        if self.curve_fitter.points:
            ratios = [p[0] for p in self.curve_fitter.points]
            times = [p[1] for p in self.curve_fitter.points]
            self.user_points_scatter = self.ax.scatter(ratios, times, c='yellow', s=35,
                                                       marker='D', edgecolors='orange',
                                                       linewidth=1.5, label='User Drawn',
                                                       zorder=6)
        
        self.update_legend()
        self.canvas.draw()
    
    def clear_fit_curve(self):
        """Clear the fitted curve"""
        if self.fit_curve_line:
            self.fit_curve_line.remove()
            self.fit_curve_line = None
        
        if self.formula_annotation:
            self.formula_annotation.remove()
            self.formula_annotation = None
        
        self.curve_fitter.fitted_params = None
        self.update_legend()
        self.canvas.draw()
    
    def update_fit_curve(self):
        """Update the fitted curve display"""
        # Remove existing
        if self.fit_curve_line:
            self.fit_curve_line.remove()
        
        if self.formula_annotation:
            self.formula_annotation.remove()
            self.formula_annotation = None
        
        # Plot new curve
        if self.curve_fitter.fitted_params is not None:
            curve_ratios, curve_times = self.curve_fitter.get_curve_points()
            if len(curve_ratios) > 0:
                self.fit_curve_line = self.ax.plot(curve_ratios, curve_times, 
                                                   c='cyan', linewidth=2.5, 
                                                   linestyle='-', label='Fitted Curve',
                                                   zorder=5)[0]
                
                # Add formula annotation
                formula = self.curve_fitter.formula_string
                r2 = self.curve_fitter.fit_error
                if len(formula) > 65:
                    formula = formula[:62] + "..."
                self.formula_annotation = self.ax.text(0.02, 0.98, 
                                                       f"{self.curve_fitter.fit_type}: R² = {r2:.6f}\n{formula}",
                                                       transform=self.ax.transAxes,
                                                       fontsize=8,
                                                       verticalalignment='top',
                                                       bbox=dict(boxstyle='round', 
                                                                facecolor='#2b2b2b', 
                                                                edgecolor='#4CAF50',
                                                                alpha=0.8),
                                                       color='#4CAF50',
                                                       family='monospace')
        
        self.update_legend()
        self.canvas.draw()
    
    def clear_drawn_points(self):
        """Clear all user-drawn points"""
        self.curve_fitter.clear_points()
        
        if self.user_points_scatter:
            self.user_points_scatter.remove()
            self.user_points_scatter = None
        
        self.clear_fit_curve()
        
        self.ax.set_title('Ratio vs Lap Time Relationship', fontsize=14, fontweight='bold', color='#FFA500')
        self.update_legend()
        self.canvas.draw()
    
    def update_legend(self):
        """Update the legend with current items"""
        legend_items = []
        
        for artist in self.ax.get_children():
            if isinstance(artist, (Line2D,)) and artist.get_label() and artist.get_label() != '_nolegend_':
                label = artist.get_label()
                if not (label.startswith('_child') or label.isdigit()):
                    legend_items.append(artist)
            elif isinstance(artist, (np.ndarray,)) and len(artist) > 0:
                for item in artist:
                    if hasattr(item, 'get_label'):
                        label = item.get_label()
                        if label and label != '_nolegend_' and not (label.startswith('_child') or label.isdigit()):
                            legend_items.append(item)
        
        if self.user_points_scatter:
            legend_items.append(self.user_points_scatter)
        
        if self.fit_curve_line:
            legend_items.append(self.fit_curve_line)
        
        seen = set()
        unique_items = []
        for item in legend_items:
            label = item.get_label()
            if label not in seen:
                seen.add(label)
                unique_items.append(item)
        
        if unique_items:
            self.ax.legend(handles=unique_items, loc='upper left', framealpha=0.8,
                          facecolor='#2b2b2b', edgecolor='#4CAF50', labelcolor='white', fontsize=9)
        else:
            if self.ax.get_legend():
                self.ax.get_legend().remove()
    
    def set_data(self, qual_points, race_points, current_times=None, current_ratio=None, current_type=None):
        """Set the data for plotting"""
        self.qual_points = qual_points or []
        self.race_points = race_points or []
        self.current_times = current_times
        self.current_ratio = current_ratio
        self.current_type = current_type
        
        self.update_plot()
    
    def update_plot(self):
        """Update the plot with current data"""
        self.ax.clear()
        
        self.ax.set_facecolor('#2b2b2b')
        self.ax.set_xlabel('Ratio', fontsize=12, fontweight='bold', color='white')
        self.ax.set_ylabel('Lap Time (seconds)', fontsize=12, fontweight='bold', color='white')
        self.ax.set_title('Ratio vs Lap Time Relationship', fontsize=14, fontweight='bold', color='#FFA500')
        
        self.ax.grid(True, alpha=0.3, color='gray', linestyle='-', linewidth=0.5)
        self.ax.grid(True, alpha=0.1, which='minor', linestyle=':', linewidth=0.5)
        self.ax.set_axisbelow(True)
        
        for spine in self.ax.spines.values():
            spine.set_color('#4CAF50')
            spine.set_linewidth(1.5)
        
        self.ax.tick_params(colors='white', labelsize=9)
        self.ax.xaxis.set_minor_locator(AutoMinorLocator())
        self.ax.yaxis.set_minor_locator(AutoMinorLocator())
        
        # Plot qualifying points (smaller markers)
        if self.qual_points:
            qual_ratios = [p[0] for p in self.qual_points]
            qual_best = [p[1] for p in self.qual_points]
            qual_worst = [p[2] for p in self.qual_points]
            
            self.ax.scatter(qual_ratios, qual_best, c='#4CAF50', s=30, 
                          alpha=0.7, marker='o', label='Qual Best AI', zorder=3)
            self.ax.scatter(qual_ratios, qual_worst, c='#4CAF50', s=30,
                          alpha=0.5, marker='s', label='Qual Worst AI', zorder=3)
            
            for i, (r, best, worst, _, _) in enumerate(self.qual_points):
                if best > 0 and worst > 0:
                    self.ax.plot([r, r], [best, worst], c='#4CAF50', 
                               alpha=0.4, linewidth=1, linestyle='--', zorder=2)
            
            qual_user = [(p[0], p[3]) for p in self.qual_points if p[3] > 0]
            if qual_user:
                user_ratios, user_times = zip(*qual_user)
                self.ax.scatter(user_ratios, user_times, c='#9C27B0', s=28,
                              alpha=0.8, marker='^', label='Qual User', zorder=4)
        
        # Plot race points (smaller markers)
        if self.race_points:
            race_ratios = [p[0] for p in self.race_points]
            race_best = [p[1] for p in self.race_points]
            race_worst = [p[2] for p in self.race_points]
            
            self.ax.scatter(race_ratios, race_best, c='#f44336', s=30,
                          alpha=0.7, marker='o', label='Race Best AI', zorder=3)
            self.ax.scatter(race_ratios, race_worst, c='#f44336', s=30,
                          alpha=0.5, marker='s', label='Race Worst AI', zorder=3)
            
            for i, (r, best, worst, _, _) in enumerate(self.race_points):
                if best > 0 and worst > 0:
                    self.ax.plot([r, r], [best, worst], c='#f44336',
                               alpha=0.4, linewidth=1, linestyle='--', zorder=2)
            
            race_user = [(p[0], p[3]) for p in self.race_points if p[3] > 0]
            if race_user:
                user_ratios, user_times = zip(*race_user)
                self.ax.scatter(user_ratios, user_times, c='#9C27B0', s=28,
                              alpha=0.8, marker='^', label='Race User', zorder=4)
        
        # Plot current data point if available
        if self.current_times and self.current_ratio:
            best_time = self.current_times.pole
            worst_time = self.current_times.last_ai
            user_time = self.current_times.player
            
            marker_style = 'o' if self.current_type == 'qual' else 's'
            color = '#4CAF50' if self.current_type == 'qual' else '#f44336'
            
            if best_time > 0:
                self.ax.scatter([self.current_ratio], [best_time],
                               c='white', s=80, marker=marker_style,
                               edgecolors=color, linewidth=2, label='Current Best', zorder=5)
            
            if worst_time > 0:
                self.ax.scatter([self.current_ratio], [worst_time],
                               c='white', s=80, marker=marker_style,
                               edgecolors=color, linewidth=2, label='Current Worst', zorder=5)
            
            if user_time > 0:
                self.ax.scatter([self.current_ratio], [user_time],
                               c='white', s=70, marker='^',
                               edgecolors='#9C27B0', linewidth=2, label='Current User', zorder=5)
            
            if best_time > 0 and worst_time > 0:
                self.ax.plot([self.current_ratio, self.current_ratio], 
                           [best_time, worst_time],
                           c=color, alpha=0.6, linewidth=2, linestyle='-', zorder=4)
        
        # Restore user-drawn points if they exist (smaller markers)
        if self.curve_fitter.points:
            ratios = [p[0] for p in self.curve_fitter.points]
            times = [p[1] for p in self.curve_fitter.points]
            self.user_points_scatter = self.ax.scatter(ratios, times, c='yellow', s=35,
                                                       marker='D', edgecolors='orange',
                                                       linewidth=1.5, label='User Drawn',
                                                       zorder=6)
        
        # Restore fitted curve if it exists
        if self.curve_fitter.fitted_params is not None:
            curve_ratios, curve_times = self.curve_fitter.get_curve_points()
            if len(curve_ratios) > 0:
                self.fit_curve_line = self.ax.plot(curve_ratios, curve_times, 
                                                   c='cyan', linewidth=2.5, 
                                                   linestyle='-', label='Fitted Curve',
                                                   zorder=5)[0]
                
                formula = self.curve_fitter.formula_string
                r2 = self.curve_fitter.fit_error
                if len(formula) > 65:
                    formula = formula[:62] + "..."
                self.formula_annotation = self.ax.text(0.02, 0.98, 
                                                       f"{self.curve_fitter.fit_type}: R² = {r2:.6f}\n{formula}",
                                                       transform=self.ax.transAxes,
                                                       fontsize=8,
                                                       verticalalignment='top',
                                                       bbox=dict(boxstyle='round', 
                                                                facecolor='#2b2b2b', 
                                                                edgecolor='#4CAF50',
                                                                alpha=0.8),
                                                       color='#4CAF50',
                                                       family='monospace')
        
        self.update_legend()
        self.figure.tight_layout()
        self.canvas.draw()
    
    def reset_view(self):
        """Reset to default view"""
        self.ax.autoscale()
        self.canvas.draw()
