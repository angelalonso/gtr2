#!/usr/bin/env python3
"""
GUI module for curve viewer
Provides reusable GUI components and dialogs
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QListWidget, 
    QDoubleSpinBox, QPushButton, QGroupBox, QSplitter, 
    QMessageBox, QAbstractItemView
)
from PyQt5.QtCore import Qt

import matplotlib
matplotlib.use('Qt5Agg')
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar


def create_control_panel(parent=None):
    """Create the left control panel with all widgets"""
    panel = QWidget(parent)
    layout = QVBoxLayout(panel)
    layout.setSpacing(10)
    
    # Instructions
    info_label = QLabel("Select tracks and vehicles to display data points.\n"
                       "Ctrl+Click = multi-select | Click = single")
    info_label.setStyleSheet("color: #888; font-size: 10px;")
    info_label.setWordWrap(True)
    layout.addWidget(info_label)
    
    # Track selection
    track_group = QGroupBox("Tracks")
    track_layout = QVBoxLayout(track_group)
    track_list = QListWidget()
    track_list.setSelectionMode(QAbstractItemView.ExtendedSelection)
    track_layout.addWidget(track_list)
    
    track_btn_layout = QHBoxLayout()
    select_all_tracks = QPushButton("Select All")
    clear_tracks = QPushButton("Clear")
    track_btn_layout.addWidget(select_all_tracks)
    track_btn_layout.addWidget(clear_tracks)
    track_layout.addLayout(track_btn_layout)
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
    
    # Formula parameters
    param_group = QGroupBox("Curve Parameters: T = a / R + b")
    param_layout = QVBoxLayout(param_group)
    
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
        'track_list': track_list,
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
        'select_all_tracks': select_all_tracks,
        'clear_tracks': clear_tracks,
        'select_all_vehicles': select_all_vehicles,
        'clear_vehicles': clear_vehicles
    }


def create_plot_widget(parent=None):
    """Create the plot widget with matplotlib figure"""
    widget = QWidget(parent)
    layout = QVBoxLayout(widget)
    layout.setContentsMargins(0, 0, 0, 0)
    
    figure = Figure(figsize=(8, 6), facecolor='#1e1e1e')
    canvas = FigureCanvas(figure)
    toolbar = NavigationToolbar(canvas, widget)
    
    ax = figure.add_subplot(111)
    ax.set_facecolor('#2b2b2b')
    
    # Styling
    for spine in ax.spines.values():
        spine.set_color('#4CAF50')
    ax.tick_params(colors='white')
    ax.xaxis.label.set_color('white')
    ax.yaxis.label.set_color('white')
    ax.title.set_color('#FFA500')
    
    ax.set_xlabel('Ratio (R)', fontsize=11)
    ax.set_ylabel('Lap Time (seconds)', fontsize=11)
    ax.set_title('Hyperbolic Curve: T = a / R + b', fontsize=12)
    ax.grid(True, alpha=0.3)
    ax.set_xlim(0.4, 2.0)  # Changed to 0.4
    ax.set_ylim(50, 200)
    
    layout.addWidget(toolbar)
    layout.addWidget(canvas)
    
    return {
        'widget': widget,
        'figure': figure,
        'canvas': canvas,
        'ax': ax
    }


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
