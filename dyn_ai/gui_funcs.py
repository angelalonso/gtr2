#!/usr/bin/env python3
"""
GUI module for curve viewer
Provides reusable GUI components and dialogs using pyqtgraph for lightweight plotting
"""

import numpy as np
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QListWidget, 
    QDoubleSpinBox, QPushButton, QGroupBox, QSplitter, 
    QMessageBox, QAbstractItemView, QComboBox, QDialog,
    QDialogButtonBox
)
from PyQt5.QtCore import Qt
import pyqtgraph as pg


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
        
        # Instructions
        info_label = QLabel("Select tracks to display data from.\n"
                           "Ctrl+Click = multi-select | Shift+Click = range")
        info_label.setStyleSheet("color: #888; font-size: 10px;")
        info_label.setWordWrap(True)
        layout.addWidget(info_label)
        
        # Track list
        self.track_list = QListWidget()
        self.track_list.setSelectionMode(QAbstractItemView.ExtendedSelection)
        for track in self.all_tracks:
            item = self.track_list.addItem(track)
            if track == self.current_track:
                self.track_list.setCurrentItem(item)
                item.setSelected(True)
        layout.addWidget(self.track_list)
        
        # Buttons
        btn_layout = QHBoxLayout()
        select_all_btn = QPushButton("Select All")
        select_all_btn.clicked.connect(self.track_list.selectAll)
        btn_layout.addWidget(select_all_btn)
        
        clear_btn = QPushButton("Clear All")
        clear_btn.clicked.connect(self.track_list.clearSelection)
        btn_layout.addWidget(clear_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        
        # Dialog buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
    def get_selected_tracks(self):
        return [item.text() for item in self.track_list.selectedItems()]


def create_control_panel(parent=None):
    """Create the left control panel with all widgets"""
    panel = QWidget(parent)
    layout = QVBoxLayout(panel)
    layout.setSpacing(10)
    
    # Instructions
    info_label = QLabel("Select vehicles to display data points.\n"
                       "Ctrl+Click = multi-select | Click = single")
    info_label.setStyleSheet("color: #888; font-size: 10px;")
    info_label.setWordWrap(True)
    layout.addWidget(info_label)
    
    # Track selection - now single track with multi-select button
    track_group = QGroupBox("Track")
    track_layout = QVBoxLayout(track_group)
    
    # Current track display
    current_track_layout = QHBoxLayout()
    current_track_label = QLabel("Current:")
    current_track_label.setStyleSheet("color: #FFA500; font-weight: bold;")
    current_track_layout.addWidget(current_track_label)
    
    current_track_display = QLabel("-")
    current_track_display.setStyleSheet("color: #4CAF50; font-family: monospace; font-weight: bold;")
    current_track_display.setWordWrap(True)
    current_track_layout.addWidget(current_track_display, 1)
    track_layout.addLayout(current_track_layout)
    
    # Multi-select button
    multi_track_btn = QPushButton("📋 Select Multiple Tracks...")
    multi_track_btn.setStyleSheet("""
        QPushButton {
            background-color: #2196F3;
            color: white;
            padding: 6px;
            font-size: 11px;
        }
        QPushButton:hover {
            background-color: #1976D2;
        }
    """)
    multi_track_btn.setToolTip("Open dialog to select multiple tracks for data comparison")
    track_layout.addWidget(multi_track_btn)
    
    # Hidden track list for internal use (kept for compatibility but not shown)
    track_list = QListWidget()
    track_list.setVisible(False)
    
    layout.addWidget(track_group)
    
    # Vehicle selection
    vehicle_group = QGroupBox("Vehicles")
    vehicle_layout = QVBoxLayout(vehicle_group)
    vehicle_list = QListWidget()
    vehicle_list.setSelectionMode(QAbstractItemView.ExtendedSelection)
    vehicle_layout.addWidget(vehicle_list)
    
    vehicle_btn_layout = QHBoxLayout()
    select_all_vehicles = QPushButton("Select All")
    clear_vehicles = QPushButton("Clear")
    vehicle_btn_layout.addWidget(select_all_vehicles)
    vehicle_btn_layout.addWidget(clear_vehicles)
    vehicle_layout.addLayout(vehicle_btn_layout)
    layout.addWidget(vehicle_group)
    
    # Data type selector
    type_group = QGroupBox("Data Types")
    type_layout = QHBoxLayout(type_group)
    type_layout.setSpacing(8)
    
    qual_btn = QPushButton("Quali")
    qual_btn.setCheckable(True)
    qual_btn.setChecked(True)
    qual_btn.setStyleSheet("""
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
    type_layout.addWidget(qual_btn)
    
    race_btn = QPushButton("Race")
    race_btn.setCheckable(True)
    race_btn.setChecked(True)
    race_btn.setStyleSheet("""
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
    type_layout.addWidget(race_btn)
    
    unkn_btn = QPushButton("Unknw")
    unkn_btn.setCheckable(True)
    unkn_btn.setChecked(True)
    unkn_btn.setStyleSheet("""
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
    type_layout.addWidget(unkn_btn)
    
    type_layout.addStretch()
    layout.addWidget(type_group)
    
    # Formula parameters - now with curve selector
    param_group = QGroupBox("Manual Curve Parameters: T = a / R + b")
    param_layout = QVBoxLayout(param_group)
    
    # Curve selector (Quali or Race)
    curve_selector_layout = QHBoxLayout()
    curve_selector_label = QLabel("Edit curve:")
    curve_selector_label.setStyleSheet("color: #FFA500; font-weight: bold;")
    curve_selector_layout.addWidget(curve_selector_label)
    
    curve_selector = QComboBox()
    curve_selector.addItem("🏁 Qualifying (Yellow)", "qual")
    curve_selector.addItem("🏎️ Race (Orange)", "race")
    curve_selector.setStyleSheet("""
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
            border-left: 5px solid transparent;
            border-right: 5px solid transparent;
            border-top: 5px solid white;
            margin-right: 5px;
        }
    """)
    curve_selector_layout.addWidget(curve_selector)
    curve_selector_layout.addStretch()
    param_layout.addLayout(curve_selector_layout)
    
    # Current formula display
    current_formula_label = QLabel("Current formula: T = -- / R + --")
    current_formula_label.setStyleSheet("color: #4CAF50; font-family: monospace; font-size: 11px;")
    current_formula_label.setWordWrap(True)
    param_layout.addWidget(current_formula_label)
    
    param_layout.addSpacing(5)
    
    # a parameter
    a_layout = QHBoxLayout()
    a_label = QLabel("Height (a):")
    a_label.setToolTip("Controls how steep the curve is. Higher = more sensitive to ratio changes")
    a_layout.addWidget(a_label)
    a_spin = QDoubleSpinBox()
    a_spin.setRange(0.01, 500.0)
    a_spin.setDecimals(3)
    a_spin.setSingleStep(1.0)
    a_spin.setValue(30.0)
    a_layout.addWidget(a_spin)
    param_layout.addLayout(a_layout)
    
    # b parameter
    b_layout = QHBoxLayout()
    b_label = QLabel("Base (b):")
    b_label.setToolTip("Minimum lap time in seconds. The curve approaches this as ratio increases")
    b_layout.addWidget(b_label)
    b_spin = QDoubleSpinBox()
    b_spin.setRange(0.01, 200.0)
    b_spin.setDecimals(3)
    b_spin.setSingleStep(0.5)
    b_spin.setValue(70.0)
    b_layout.addWidget(b_spin)
    param_layout.addLayout(b_layout)
    
    # Apply button for manual edits
    apply_btn = QPushButton("Apply to Selected Curve")
    apply_btn.setStyleSheet("background-color: #2196F3;")
    param_layout.addWidget(apply_btn)
    
    # Derived values
    info_layout = QVBoxLayout()
    k_label = QLabel("Steepness k = a/(a+b) = ---")
    k_label.setToolTip("k close to 0 = shallow curve, k close to 1 = steep curve")
    k_label.setStyleSheet("color: #888;")
    info_layout.addWidget(k_label)
    
    m_label = QLabel("Time at R=1.0 = a+b = ---")
    m_label.setStyleSheet("color: #888;")
    info_layout.addWidget(m_label)
    
    param_layout.addLayout(info_layout)
    layout.addWidget(param_group)
    
    # Autopilot group
    autopilot_group = QGroupBox("[AUTO] Autopilot")
    autopilot_layout = QVBoxLayout(autopilot_group)
    
    # Autopilot enable/disable
    autopilot_enable_layout = QHBoxLayout()
    autopilot_enable_btn = QPushButton("Autopilot is OFF")
    autopilot_enable_btn.setCheckable(True)
    autopilot_enable_btn.setStyleSheet("""
        QPushButton {
            background-color: #555;
            color: white;
        }
        QPushButton:checked {
            background-color: #FF9800;
            color: white;
            font-weight: bold;
        }
    """)
    autopilot_enable_layout.addWidget(autopilot_enable_btn)
    
    autopilot_silent_btn = QPushButton("Silent Mode")
    autopilot_silent_btn.setCheckable(True)
    autopilot_silent_btn.setStyleSheet("""
        QPushButton {
            background-color: #555;
            color: white;
        }
        QPushButton:checked {
            background-color: #2196F3;
            color: white;
        }
    """)
    autopilot_enable_layout.addWidget(autopilot_silent_btn)
    autopilot_layout.addLayout(autopilot_enable_layout)
    
    # Autopilot info label
    autopilot_info = QLabel("When enabled, automatically adjusts AIW ratios\nbased on detected race data and stored formulas.\nThe graph will show the formula being used.")
    autopilot_info.setStyleSheet("color: #888; font-size: 9px;")
    autopilot_info.setWordWrap(True)
    autopilot_layout.addWidget(autopilot_info)
    
    autopilot_status = QLabel("Status: Disabled")
    autopilot_status.setStyleSheet("color: #FF9800; font-size: 10px;")
    autopilot_layout.addWidget(autopilot_status)
    
    layout.addWidget(autopilot_group)
    
    # Buttons
    btn_layout = QVBoxLayout()
    
    fit_btn = QPushButton("Auto-Fit to Selected Data")
    fit_btn.setStyleSheet("background-color: #4CAF50;")
    btn_layout.addWidget(fit_btn)
    
    reset_btn = QPushButton("Reset View")
    btn_layout.addWidget(reset_btn)
    
    exit_btn = QPushButton("Exit")
    exit_btn.setStyleSheet("background-color: #f44336;")
    btn_layout.addWidget(exit_btn)
    
    layout.addLayout(btn_layout)
    layout.addStretch()
    
    # Stats label
    stats_label = QLabel("")
    stats_label.setStyleSheet("color: #888; padding: 5px;")
    stats_label.setWordWrap(True)
    layout.addWidget(stats_label)
    
    return {
        'panel': panel,
        'track_list': track_list,  # Kept for compatibility but hidden
        'current_track_display': current_track_display,
        'multi_track_btn': multi_track_btn,
        'vehicle_list': vehicle_list,
        'qual_btn': qual_btn,
        'race_btn': race_btn,
        'unkn_btn': unkn_btn,
        'a_spin': a_spin,
        'b_spin': b_spin,
        'k_label': k_label,
        'm_label': m_label,
        'fit_btn': fit_btn,
        'reset_btn': reset_btn,
        'exit_btn': exit_btn,
        'stats_label': stats_label,
        'select_all_vehicles': select_all_vehicles,
        'clear_vehicles': clear_vehicles,
        'autopilot_enable_btn': autopilot_enable_btn,
        'autopilot_silent_btn': autopilot_silent_btn,
        'autopilot_status': autopilot_status,
        'curve_selector': curve_selector,
        'current_formula_label': current_formula_label,
        'apply_btn': apply_btn
    }


def create_plot_widget(parent=None):
    """Create the plot widget using pyqtgraph for lightweight rendering"""
    widget = QWidget(parent)
    layout = QVBoxLayout(widget)
    layout.setContentsMargins(0, 0, 0, 0)
    
    # Create GraphicsLayoutWidget for plotting
    plot_widget = pg.GraphicsLayoutWidget()
    plot_widget.setBackground('#2b2b2b')
    
    # Create plot item
    plot = plot_widget.addPlot()
    plot.setLabel('bottom', 'Ratio (R)', color='white', size='11pt')
    plot.setLabel('left', 'Lap Time (seconds)', color='white', size='11pt')
    plot.setTitle('Hyperbolic Curve: T = a / R + b', color='#FFA500', size='12pt')
    plot.showGrid(x=True, y=True, alpha=0.3)
    plot.setXRange(0.4, 2.0)
    plot.setYRange(50, 200)
    
    # Style the axes
    plot.getAxis('bottom').setPen('white')
    plot.getAxis('bottom').setTextPen('white')
    plot.getAxis('left').setPen('white')
    plot.getAxis('left').setTextPen('white')
    
    # Store plot reference and curve/point items for updating
    plot_data = {
        'widget': plot_widget,
        'plot': plot,
        'curve_line': None,
        'quali_scatter': None,
        'race_scatter': None,
        'unknown_scatter': None,
        'legend': None,
        'parent_widget': widget
    }
    
    layout.addWidget(plot_widget)
    
    return plot_data


def update_plot(plot_data, a: float, b: float, points_data: dict):
    """
    Update the plot with new curve and points
    This is kept for compatibility with existing code
    """
    plot = plot_data['plot']
    
    # Generate curve points
    ratios = np.linspace(0.4, 2.0, 200)
    times = a / ratios + b
    
    # Update or create curve line
    if plot_data['curve_line'] is None:
        plot_data['curve_line'] = plot.plot(ratios, times, pen=pg.mkPen(color='#00FFFF', width=2.5))
    else:
        plot_data['curve_line'].setData(ratios, times)
    
    # Get point data
    quali_points = points_data.get('quali', [])
    race_points = points_data.get('race', [])
    unknown_points = points_data.get('unknown', [])
    
    # Update quali points (yellow circles)
    if quali_points:
        r = [p[0] for p in quali_points]
        t = [p[1] for p in quali_points]
        if plot_data['quali_scatter'] is None:
            plot_data['quali_scatter'] = pg.ScatterPlotItem(
                r, t, brush=pg.mkBrush('#FFFF00'), size=6,
                symbol='o', pen=None
            )
            plot.addItem(plot_data['quali_scatter'])
        else:
            plot_data['quali_scatter'].setData(r, t)
    elif plot_data['quali_scatter'] is not None:
        plot.removeItem(plot_data['quali_scatter'])
        plot_data['quali_scatter'] = None
    
    # Update race points (orange squares)
    if race_points:
        r = [p[0] for p in race_points]
        t = [p[1] for p in race_points]
        if plot_data['race_scatter'] is None:
            plot_data['race_scatter'] = pg.ScatterPlotItem(
                r, t, brush=pg.mkBrush('#FF6600'), size=6,
                symbol='s', pen=None
            )
            plot.addItem(plot_data['race_scatter'])
        else:
            plot_data['race_scatter'].setData(r, t)
    elif plot_data['race_scatter'] is not None:
        plot.removeItem(plot_data['race_scatter'])
        plot_data['race_scatter'] = None
    
    # Update unknown points (magenta triangles)
    if unknown_points:
        r = [p[0] for p in unknown_points]
        t = [p[1] for p in unknown_points]
        if plot_data['unknown_scatter'] is None:
            plot_data['unknown_scatter'] = pg.ScatterPlotItem(
                r, t, brush=pg.mkBrush('#FF00FF'), size=6,
                symbol='t', pen=None
            )
            plot.addItem(plot_data['unknown_scatter'])
        else:
            plot_data['unknown_scatter'].setData(r, t)
    elif plot_data['unknown_scatter'] is not None:
        plot.removeItem(plot_data['unknown_scatter'])
        plot_data['unknown_scatter'] = None
    
    # Update legend - remove old and create new
    if plot_data['legend'] is not None:
        plot.scene().removeItem(plot_data['legend'])
        plot_data['legend'] = None
    
    # Create new legend
    plot_data['legend'] = plot.addLegend()
    
    # Add items to legend
    if plot_data['curve_line']:
        plot_data['legend'].addItem(plot_data['curve_line'], f'T = {a:.3f}/R + {b:.3f}')
    if quali_points:
        plot_data['legend'].addItem(plot_data['quali_scatter'], f'Qualifying ({len(quali_points)})')
    if race_points:
        plot_data['legend'].addItem(plot_data['race_scatter'], f'Race ({len(race_points)})')
    if unknown_points:
        plot_data['legend'].addItem(plot_data['unknown_scatter'], f'Unknown ({len(unknown_points)})')


def reset_plot_view(plot_data):
    """Reset the plot to default view"""
    plot = plot_data['plot']
    plot.setXRange(0.4, 2.0)
    plot.setYRange(50, 200)


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


def show_error_dialog(parent, title: str, message: str):
    """Show an error message dialog"""
    msg = QMessageBox(parent)
    msg.setWindowTitle(title)
    msg.setIcon(QMessageBox.Critical)
    msg.setText(message)
    msg.exec_()


def show_info_dialog(parent, title: str, message: str):
    """Show an information message dialog"""
    msg = QMessageBox(parent)
    msg.setWindowTitle(title)
    msg.setIcon(QMessageBox.Information)
    msg.setText(message)
    msg.exec_()


def show_warning_dialog(parent, title: str, message: str):
    """Show a warning message dialog"""
    msg = QMessageBox(parent)
    msg.setWindowTitle(title)
    msg.setIcon(QMessageBox.Warning)
    msg.setText(message)
    msg.exec_()
