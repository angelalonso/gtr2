"""
Dedicated Graph Window for Global Curve Analysis
Shows points from all tracks and the global curve with track-specific scaling
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
import warnings
warnings.filterwarnings('ignore', category=RuntimeWarning)

from track_formula import GlobalFormulaManager


class GlobalCurveDialog(QDialog):
    """Dialog for showing global curve information and statistics"""
    
    def __init__(self, parent=None, manager=None):
        super().__init__(parent)
        self.manager = manager
        self.setWindowTitle("Global Curve Information")
        self.setMinimumWidth(500)
        self.setMinimumHeight(400)
        
        self.setStyleSheet("""
            QDialog {
                background-color: #2b2b2b;
            }
            QLabel {
                color: white;
                font-size: 12px;
            }
            QGroupBox {
                color: #4CAF50;
                font-weight: bold;
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
        """)
        
        layout = QVBoxLayout(self)
        
        stats = self.manager.get_stats() if self.manager else {}
        
        # Stats group
        stats_group = QGroupBox("Global Curve Statistics")
        stats_layout = QVBoxLayout(stats_group)
        
        formula = QLabel(f"Formula: T = {stats.get('global_A', 300):.4f} × e^(-{stats.get('global_k', 3):.4f} × R) + {stats.get('global_B', 100):.4f}")
        formula.setWordWrap(True)
        formula.setStyleSheet("color: #FFA500; font-family: monospace;")
        stats_layout.addWidget(formula)
        
        if stats.get('r_squared'):
            r2_label = QLabel(f"R² = {stats['r_squared']:.6f}")
            stats_layout.addWidget(r2_label)
        
        tracks_label = QLabel(f"Tracks with data: {stats.get('total_tracks', 0)}")
        stats_layout.addWidget(tracks_label)
        
        points_label = QLabel(f"Total data points: {stats.get('total_points', 0)}")
        stats_layout.addWidget(points_label)
        
        layout.addWidget(stats_group)
        
        # Track multipliers group
        multipliers_group = QGroupBox("Track Multipliers")
        multipliers_layout = QVBoxLayout(multipliers_group)
        
        multiplier_text = QTextEdit()
        multiplier_text.setReadOnly(True)
        multiplier_text.setMaximumHeight(200)
        
        multipliers = stats.get('track_multipliers', {})
        if multipliers:
            text = ""
            for track, mult in sorted(multipliers.items()):
                text += f"{track}: {mult:.6f}\n"
            multiplier_text.setText(text)
        else:
            multiplier_text.setText("No track multipliers calculated yet.\nAdd points and fit the curve.")
        
        multipliers_layout.addWidget(multiplier_text)
        layout.addWidget(multipliers_group)
        
        # Close button
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)


class RatioGraphWindow(QMainWindow):
    """Main window for global curve analysis"""
    
    def __init__(self, parent=None, manager=None):
        super().__init__(parent)
        self.manager = manager or GlobalFormulaManager()
        self.current_track = None
        self.hover_annotation = None
        self.hover_point = None
        
        self.setWindowTitle("Global Curve Analysis")
        self.setGeometry(100, 100, 1400, 900)
        
        self.setup_ui()
        self.setup_connections()
        self.update_graph()
    
    def setup_ui(self):
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
            QComboBox {
                background-color: #3c3c3c;
                color: white;
                border: 1px solid #4CAF50;
                border-radius: 3px;
                padding: 5px;
                min-width: 200px;
            }
            QSpinBox, QDoubleSpinBox {
                background-color: #3c3c3c;
                color: white;
                border: 1px solid #4CAF50;
                border-radius: 3px;
                padding: 5px;
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
        
        self.stats_label = QLabel("Loading...")
        self.stats_label.setStyleSheet("color: #4CAF50; font-size: 11px;")
        stats_layout.addWidget(self.stats_label)
        stats_layout.addStretch()
        
        main_layout.addWidget(stats_widget)
        
        # Track selection
        track_widget = QWidget()
        track_layout = QHBoxLayout(track_widget)
        track_layout.setContentsMargins(0, 0, 0, 10)
        
        track_layout.addWidget(QLabel("Select Track to Highlight:"))
        self.track_combo = QComboBox()
        self.track_combo.setMinimumWidth(250)
        self.track_combo.addItem("All Tracks")
        track_layout.addWidget(self.track_combo)
        
        track_layout.addStretch()
        
        # Add point section
        track_layout.addWidget(QLabel("Add Point:"))
        
        track_layout.addWidget(QLabel("Ratio:"))
        self.ratio_spin = QDoubleSpinBox()
        self.ratio_spin.setRange(0.1, 10.0)
        self.ratio_spin.setDecimals(6)
        self.ratio_spin.setValue(1.0)
        self.ratio_spin.setFixedWidth(100)
        track_layout.addWidget(self.ratio_spin)
        
        track_layout.addWidget(QLabel("Time (s):"))
        self.time_spin = QDoubleSpinBox()
        self.time_spin.setRange(30, 500)
        self.time_spin.setDecimals(3)
        self.time_spin.setValue(120.0)
        self.time_spin.setFixedWidth(100)
        track_layout.addWidget(self.time_spin)
        
        self.add_point_btn = QPushButton("Add Point")
        self.add_point_btn.setFixedHeight(30)
        self.add_point_btn.setFixedWidth(100)
        track_layout.addWidget(self.add_point_btn)
        
        main_layout.addWidget(track_widget)
        
        # Graph area
        graph_group = QGroupBox("Global Curve Analysis - Hover over points for details | Use mouse to zoom/pan")
        graph_layout = QVBoxLayout(graph_group)
        
        self.graph_widget = GraphWidget(self)
        graph_layout.addWidget(self.graph_widget)
        
        main_layout.addWidget(graph_group, 1)
        
        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")
        
        self.update_stats()
    
    def create_toolbar(self):
        toolbar_widget = QWidget()
        toolbar_layout = QHBoxLayout(toolbar_widget)
        toolbar_layout.setSpacing(10)
        
        self.fit_curve_btn = QPushButton("📈 Fit Global Curve")
        self.fit_curve_btn.setFixedHeight(35)
        self.fit_curve_btn.setFixedWidth(150)
        self.fit_curve_btn.clicked.connect(self.fit_curve)
        toolbar_layout.addWidget(self.fit_curve_btn)
        
        self.show_info_btn = QPushButton("📊 Show Statistics")
        self.show_info_btn.setFixedHeight(35)
        self.show_info_btn.setFixedWidth(150)
        self.show_info_btn.clicked.connect(self.show_info)
        toolbar_layout.addWidget(self.show_info_btn)
        
        sep = QFrame()
        sep.setFrameShape(QFrame.VLine)
        sep.setFrameShadow(QFrame.Sunken)
        sep.setStyleSheet("background-color: #555;")
        toolbar_layout.addWidget(sep)
        
        self.reset_view_btn = QPushButton("🔄 Reset View")
        self.reset_view_btn.setFixedHeight(35)
        self.reset_view_btn.setFixedWidth(100)
        self.reset_view_btn.clicked.connect(self.reset_view)
        toolbar_layout.addWidget(self.reset_view_btn)
        
        self.save_image_btn = QPushButton("💾 Save Image")
        self.save_image_btn.setFixedHeight(35)
        self.save_image_btn.setFixedWidth(100)
        self.save_image_btn.clicked.connect(self.save_graph_image)
        toolbar_layout.addWidget(self.save_image_btn)
        
        toolbar_layout.addStretch()
        
        # Help text
        help_label = QLabel("💡 Points from all tracks are used to fit a global curve. Each track has its own multiplier.")
        help_label.setStyleSheet("color: #888; font-size: 10px;")
        toolbar_layout.addWidget(help_label)
        
        return toolbar_widget
    
    def setup_connections(self):
        self.track_combo.currentTextChanged.connect(self.on_track_changed)
        self.add_point_btn.clicked.connect(self.add_point)
    
    def on_track_changed(self, track_name):
        self.current_track = track_name if track_name != "All Tracks" else None
        self.update_graph()
    
    def add_point(self):
        """Add a point for the selected track"""
        track_name = self.track_combo.currentText()
        if track_name == "All Tracks":
            QMessageBox.warning(self, "No Track Selected", "Please select a specific track to add points.")
            return
        
        ratio = self.ratio_spin.value()
        time = self.time_spin.value()
        
        self.manager.add_point(track_name, ratio, time)
        self.update_track_list()
        self.update_graph()
        self.update_stats()
        self.status_bar.showMessage(f"Added point: {track_name} - R={ratio:.4f}, T={time:.2f}s")
    
    def update_track_list(self):
        """Update the track selection combo box"""
        self.track_combo.blockSignals(True)
        current = self.track_combo.currentText()
        self.track_combo.clear()
        self.track_combo.addItem("All Tracks")
        for track in sorted(self.manager.get_all_tracks()):
            self.track_combo.addItem(track)
        
        # Restore selection if possible
        index = self.track_combo.findText(current)
        if index >= 0:
            self.track_combo.setCurrentIndex(index)
        self.track_combo.blockSignals(False)
    
    def fit_curve(self):
        """Fit the global curve"""
        stats = self.manager.get_stats()
        if stats['total_points'] < 3:
            QMessageBox.warning(self, "Insufficient Data", 
                               f"Need at least 3 points to fit a curve.\nCurrently have {stats['total_points']} points across {stats['total_tracks']} tracks.")
            return
        
        self.status_bar.showMessage("Fitting global curve...")
        QApplication.processEvents()
        
        success, message = self.manager.fit_curve()
        
        if success:
            self.status_bar.showMessage(message)
            self.update_graph()
            self.update_stats()
            QMessageBox.information(self, "Fit Successful", message)
        else:
            self.status_bar.showMessage("Fit failed")
            QMessageBox.warning(self, "Fit Failed", message)
    
    def show_info(self):
        """Show the global curve information dialog"""
        dialog = GlobalCurveDialog(self, self.manager)
        dialog.exec_()
    
    def update_stats(self):
        """Update the stats display"""
        stats = self.manager.get_stats()
        if stats['total_points'] > 0:
            if stats.get('r_squared'):
                self.stats_label.setText(f"📊 {stats['total_tracks']} tracks, {stats['total_points']} points | R² = {stats['r_squared']:.6f}")
            else:
                self.stats_label.setText(f"📊 {stats['total_tracks']} tracks, {stats['total_points']} points | Not fitted yet")
        else:
            self.stats_label.setText("📊 No data points. Add points from your tracks to build the global curve.")
    
    def update_graph(self):
        """Update the graph display"""
        self.graph_widget.set_data(self.manager, self.current_track)
    
    def reset_view(self):
        self.graph_widget.reset_view()
        self.status_bar.showMessage("View reset to default", 2000)
    
    def save_graph_image(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Graph Image",
            "global_curve.png",
            "PNG Images (*.png);;All Files (*)"
        )
        
        if file_path:
            self.graph_widget.figure.savefig(file_path, dpi=150, facecolor='#1e1e1e')
            self.status_bar.showMessage(f"Graph saved to {file_path}", 3000)


class GraphWidget(QWidget):
    """Widget containing matplotlib figure with interactive drawing"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.manager = None
        self.current_track = None
        self.hover_annotation = None
        self.hover_point = None
        
        self.figure = Figure(figsize=(12, 8), facecolor='#1e1e1e')
        self.canvas = FigureCanvas(self.figure)
        
        self.canvas.mpl_connect('motion_notify_event', self.on_motion)
        
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
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        layout.addWidget(self.toolbar)
        layout.addWidget(self.canvas)
        
        self.ax = self.figure.add_subplot(111)
        self.ax.set_facecolor('#2b2b2b')
        
        self.ax.grid(True, alpha=0.3, color='gray', linestyle='-', linewidth=0.5)
        self.ax.set_axisbelow(True)
        
        for spine in self.ax.spines.values():
            spine.set_color('#4CAF50')
            spine.set_linewidth(1.5)
        
        self.ax.tick_params(colors='white', labelsize=9)
        self.ax.xaxis.label.set_color('white')
        self.ax.yaxis.label.set_color('white')
        self.ax.title.set_color('#FFA500')
        
        self.setup_default_view()
    
    def setup_default_view(self):
        self.ax.set_xlabel('Ratio', fontsize=12, fontweight='bold')
        self.ax.set_ylabel('Lap Time (seconds)', fontsize=12, fontweight='bold')
        self.ax.set_title('Global Curve Analysis', fontsize=14, fontweight='bold')
        self.ax.set_xlim(0.3, 3.0)
        self.ax.set_ylim(50, 200)
        
        self.ax.grid(True, alpha=0.1, which='minor', linestyle=':', linewidth=0.5)
        self.ax.xaxis.set_minor_locator(AutoMinorLocator())
        self.ax.yaxis.set_minor_locator(AutoMinorLocator())
        
        self.canvas.draw()
    
    def on_motion(self, event):
        """Handle mouse motion for hover tooltips"""
        if event.inaxes != self.ax:
            if self.hover_annotation:
                self.hover_annotation.remove()
                self.hover_annotation = None
                self.hover_point = None
                self.canvas.draw_idle()
            return
        
        if not self.manager:
            return
        
        mouse_x = event.x
        mouse_y = event.y
        
        # Check all points from all tracks
        for track_name in self.manager.get_all_tracks():
            points = self.manager.get_track_points(track_name)
            for ratio, time in points:
                x_pixel = self.ax.transData.transform((ratio, time))[0]
                y_pixel = self.ax.transData.transform((ratio, time))[1]
                dist = np.sqrt((x_pixel - mouse_x)**2 + (y_pixel - mouse_y)**2)
                
                if dist < 15:
                    if self.hover_point != (track_name, ratio, time):
                        if self.hover_annotation:
                            self.hover_annotation.remove()
                        text = f"Track: {track_name}\nR = {ratio:.4f}\nT = {time:.2f}s"
                        self.hover_annotation = self.ax.annotate(
                            text, xy=(ratio, time), xytext=(10, -15),
                            textcoords='offset points',
                            bbox=dict(boxstyle='round', facecolor='#2b2b2b', 
                                     edgecolor='#4CAF50', alpha=0.9),
                            color='#4CAF50', fontsize=9, fontfamily='monospace',
                            arrowprops=dict(arrowstyle='->', color='#4CAF50')
                        )
                        self.hover_point = (track_name, ratio, time)
                        self.canvas.draw_idle()
                    return
        
        # No point under cursor
        if self.hover_annotation:
            self.hover_annotation.remove()
            self.hover_annotation = None
            self.hover_point = None
            self.canvas.draw_idle()
    
    def set_data(self, manager, current_track=None):
        """Set the data for plotting"""
        self.manager = manager
        self.current_track = current_track
        self.update_plot()
    
    def update_plot(self):
        """Update the plot with current data"""
        self.ax.clear()
        
        self.ax.set_facecolor('#2b2b2b')
        self.ax.set_xlabel('Ratio', fontsize=12, fontweight='bold', color='white')
        self.ax.set_ylabel('Lap Time (seconds)', fontsize=12, fontweight='bold', color='white')
        self.ax.set_title('Global Curve Analysis', fontsize=14, fontweight='bold', color='#FFA500')
        
        self.ax.grid(True, alpha=0.3, color='gray', linestyle='-', linewidth=0.5)
        self.ax.grid(True, alpha=0.1, which='minor', linestyle=':', linewidth=0.5)
        self.ax.set_axisbelow(True)
        
        for spine in self.ax.spines.values():
            spine.set_color('#4CAF50')
            spine.set_linewidth(1.5)
        
        self.ax.tick_params(colors='white', labelsize=9)
        self.ax.xaxis.set_minor_locator(AutoMinorLocator())
        self.ax.yaxis.set_minor_locator(AutoMinorLocator())
        
        if not self.manager:
            self.canvas.draw()
            return
        
        # Plot points from all tracks
        colors = plt.cm.tab10(np.linspace(0, 1, max(1, len(self.manager.get_all_tracks()))))
        track_colors = {}
        
        for i, track_name in enumerate(self.manager.get_all_tracks()):
            points = self.manager.get_track_points(track_name)
            if not points:
                continue
            
            ratios = [p[0] for p in points]
            times = [p[1] for p in points]
            
            color = colors[i % len(colors)]
            track_colors[track_name] = color
            
            # Determine marker style based on whether this is the current track
            if self.current_track == track_name:
                marker = 'o'
                size = 50
                edgecolor = 'white'
                linewidth = 2
                alpha = 1.0
            else:
                marker = 'o'
                size = 30
                edgecolor = None
                linewidth = 1
                alpha = 0.6
            
            self.ax.scatter(ratios, times, c=[color], s=size, marker=marker,
                          alpha=alpha, label=track_name, edgecolors=edgecolor,
                          linewidth=linewidth, zorder=3)
        
        # Plot global curve
        stats = self.manager.get_stats()
        if stats.get('r_squared'):
            # Plot scaled curves for tracks with multipliers
            if self.current_track and self.current_track in stats['track_multipliers']:
                # Show only the selected track's scaled curve
                ratios, times = self.manager.global_curve.get_curve_points(self.current_track)
                self.ax.plot(ratios, times, c='cyan', linewidth=2.5, 
                           linestyle='-', label=f'{self.current_track} (scaled)', zorder=4)
                
                # Also show global curve for reference
                global_ratios, global_times = self.manager.global_curve.get_global_curve_points()
                self.ax.plot(global_ratios, global_times, c='#FFA500', linewidth=2, 
                           linestyle='--', label='Global (unscaled)', alpha=0.7, zorder=3)
            else:
                # Show all scaled curves or just global
                if self.current_track is None:
                    # Show all scaled curves
                    for track_name, multiplier in stats['track_multipliers'].items():
                        ratios, times = self.manager.global_curve.get_curve_points(track_name)
                        color = track_colors.get(track_name, '#888')
                        self.ax.plot(ratios, times, c=color, linewidth=1.5, 
                                   linestyle=':', alpha=0.5, label=f'{track_name} scaled', zorder=2)
                
                # Always show global curve
                global_ratios, global_times = self.manager.global_curve.get_global_curve_points()
                self.ax.plot(global_ratios, global_times, c='cyan', linewidth=2.5, 
                           linestyle='-', label='Global fitted curve', zorder=4)
        
        # Add formula annotation
        if stats.get('r_squared'):
            formula = self.manager.global_curve.get_formula_string()
            r2 = stats.get('r_squared', 0)
            self.ax.text(0.02, 0.98, 
                        f"Global Curve: {formula}\nR² = {r2:.6f}",
                        transform=self.ax.transAxes,
                        fontsize=8,
                        verticalalignment='top',
                        bbox=dict(boxstyle='round', 
                                 facecolor='#2b2b2b', 
                                 edgecolor='#4CAF50',
                                 alpha=0.8),
                        color='#4CAF50',
                        family='monospace')
        
        # Legend
        handles, labels = self.ax.get_legend_handles_labels()
        if handles:
            # Remove duplicates
            unique = {}
            for h, l in zip(handles, labels):
                if l not in unique:
                    unique[l] = h
            self.ax.legend(handles=unique.values(), labels=unique.keys(),
                          loc='upper left', framealpha=0.8,
                          facecolor='#2b2b2b', edgecolor='#4CAF50', 
                          labelcolor='white', fontsize=8)
        
        self.figure.tight_layout()
        self.canvas.draw()
    
    def reset_view(self):
        self.ax.autoscale()
        self.canvas.draw()


# Import matplotlib for colors
import matplotlib.pyplot as plt
