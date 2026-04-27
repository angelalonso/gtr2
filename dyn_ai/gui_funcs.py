#!/usr/bin/env python3
"""
GUI module for curve viewer
Provides reusable GUI components and dialogs
"""

import logging
import numpy as np
import shutil
import sqlite3
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Tuple, Any
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QListWidget, 
    QDoubleSpinBox, QPushButton, QGroupBox, QSplitter, 
    QMessageBox, QAbstractItemView, QComboBox, QDialog,
    QDialogButtonBox, QListWidgetItem, QSlider, QSpinBox,
    QCheckBox, QTabWidget, QTableWidget, QTableWidgetItem,
    QHeaderView, QScrollArea, QFileDialog, QSizePolicy, QRadioButton,
    QTextEdit, QFrame, QLineEdit
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor, QFont
import pyqtgraph as pg

from formula_funcs import fit_curve, get_formula_string, hyperbolic, ratio_from_time
from autopilot import load_vehicle_classes, get_vehicle_class, DEFAULT_A_VALUE
from cfg_funcs import get_ratio_limits


# Set up logger for this module
logger = logging.getLogger(__name__)


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
        
        control_layout = QHBoxLayout()
        
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
        
        self.clear_btn = QPushButton("Clear")
        self.clear_btn.clicked.connect(self.clear_log)
        control_layout.addWidget(self.clear_btn)
        
        self.auto_scroll_cb = QCheckBox("Auto-scroll")
        self.auto_scroll_cb.setChecked(True)
        control_layout.addWidget(self.auto_scroll_cb)
        
        layout.addLayout(control_layout)
        
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
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        formatted = f"[{timestamp}] [{level:7}] {message}"
        
        self.log_buffer.append((level, formatted))
        
        if len(self.log_buffer) > self.max_lines:
            self.log_buffer = self.log_buffer[-self.max_lines:]
        
        self._update_display()
        
    def _update_display(self):
        level_map = {"ERROR": 40, "WARNING": 30, "INFO": 20, "DEBUG": 10, "ALL": 0}
        min_level = level_map.get(self.current_level, 20)
        
        level_values = {"ERROR": 40, "WARNING": 30, "INFO": 20, "DEBUG": 10}
        color_map = {"ERROR": "#f44336", "WARNING": "#ff9800", "INFO": "#4caf50", "DEBUG": "#9e9e9e"}
        
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
        self.current_level = level
        self._update_display()
        
    def on_max_lines_changed(self, value: int):
        self.max_lines = value
        if len(self.log_buffer) > self.max_lines:
            self.log_buffer = self.log_buffer[-self.max_lines:]
        self._update_display()
        
    def clear_log(self):
        self.log_buffer.clear()
        self.log_text.clear()


class SimpleLogHandler(logging.Handler):
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


class ManualLapTimeDialog(QDialog):
    """Dialog for manually editing user lap time"""
    
    def __init__(self, parent, session_type: str, current_time: float):
        super().__init__(parent)
        self.session_type = session_type
        self.current_time = current_time
        self.new_time = None
        self.setup_ui()
    
    def setup_ui(self):
        self.setWindowTitle(f"Edit {self.session_type.upper()} Lap Time")
        self.setFixedSize(350, 200)
        self.setStyleSheet("""
            QDialog {
                background-color: #2b2b2b;
            }
            QLabel {
                color: white;
            }
            QDoubleSpinBox {
                background-color: #3c3c3c;
                color: white;
                border: 1px solid #4CAF50;
                border-radius: 4px;
                padding: 4px;
                font-size: 14px;
            }
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton#cancel {
                background-color: #555;
            }
            QPushButton#cancel:hover {
                background-color: #666;
            }
        """)
        
        layout = QVBoxLayout(self)
        
        # Title
        title = QLabel(f"Edit {self.session_type.upper()} Lap Time")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #FFA500;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        layout.addSpacing(10)
        
        # Current value display
        current_label = QLabel(f"Current {self.session_type.upper()} Time:")
        current_label.setStyleSheet("color: #888;")
        layout.addWidget(current_label)
        
        minutes = int(self.current_time) // 60
        seconds = self.current_time % 60
        current_value = QLabel(f"{minutes}:{seconds:06.3f} ({self.current_time:.3f}s)")
        current_value.setStyleSheet("font-size: 14px; font-family: monospace; color: #4CAF50;")
        layout.addWidget(current_value)
        
        layout.addSpacing(15)
        
        # New time input
        new_label = QLabel(f"New {self.session_type.upper()} Time (seconds):")
        new_label.setStyleSheet("color: #888;")
        layout.addWidget(new_label)
        
        self.time_spin = QDoubleSpinBox()
        self.time_spin.setRange(10.0, 500.0)
        self.time_spin.setDecimals(3)
        self.time_spin.setSingleStep(0.5)
        self.time_spin.setValue(self.current_time)
        self.time_spin.setStyleSheet("font-size: 14px;")
        layout.addWidget(self.time_spin)
        
        layout.addSpacing(20)
        
        # Buttons
        btn_layout = QHBoxLayout()
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setObjectName("cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        
        apply_btn = QPushButton("Apply")
        apply_btn.clicked.connect(self.accept)
        btn_layout.addWidget(apply_btn)
        
        layout.addLayout(btn_layout)
    
    def accept(self):
        self.new_time = self.time_spin.value()
        super().accept()


class SessionPanel(QWidget):
    """Panel for a single session (Qualifying or Race) with controls"""
    
    formula_changed = pyqtSignal(str, float, float)  # session_type, a, b
    show_data_toggled = pyqtSignal(str, bool)  # session_type, show
    calculate_ratio = pyqtSignal(str, float)  # session_type, lap_time
    auto_fit_requested = pyqtSignal(str)  # session_type
    lap_time_edited = pyqtSignal(str, float)  # session_type, new_lap_time
    
    def __init__(self, session_type: str, title: str, db, parent=None):
        super().__init__(parent)
        self.session_type = session_type  # "qual" or "race"
        self.title = title
        self.db = db
        
        self.a = DEFAULT_A_VALUE
        self.b = 70.0
        self.user_time = None
        self.user_ratio = None
        self.current_ratio = None
        self.calc_button_modified = False  # Track if button should be orange
        
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(10, 10, 10, 10)
        
        self.setStyleSheet("""
            QGroupBox {
                background-color: #2b2b2b;
                border-radius: 8px;
                margin-top: 8px;
                padding-top: 8px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
            QPushButton#edit_time_btn {
                background-color: #2196F3;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 2px 8px;
                font-size: 10px;
            }
            QPushButton#edit_time_btn:hover {
                background-color: #1976D2;
            }
        """)
        
        # Main group box
        group = QGroupBox(self.title)
        group_layout = QVBoxLayout(group)
        
        # Header with show/hide button
        header_layout = QHBoxLayout()
        
        self.show_checkbox = QCheckBox("Show on graph")
        self.show_checkbox.setChecked(True)
        self.show_checkbox.setStyleSheet("color: #4CAF50; font-weight: bold;")
        self.show_checkbox.toggled.connect(self.on_show_toggled)
        header_layout.addWidget(self.show_checkbox)
        
        header_layout.addStretch()
        
        group_layout.addLayout(header_layout)
        
        # Formula display
        formula_layout = QHBoxLayout()
        formula_layout.addWidget(QLabel("Formula:"))
        self.formula_label = QLabel(f"T = {self.a:.2f} / R + {self.b:.2f}")
        self.formula_label.setStyleSheet("color: #FFA500; font-family: monospace;")
        formula_layout.addWidget(self.formula_label)
        formula_layout.addStretch()
        group_layout.addLayout(formula_layout)
        
        # User time display with edit button
        user_layout = QHBoxLayout()
        user_layout.addWidget(QLabel("Your Time:"))
        self.user_time_label = QLabel("--")
        self.user_time_label.setStyleSheet("color: #4CAF50; font-weight: bold; font-family: monospace; font-size: 12px;")
        user_layout.addWidget(self.user_time_label)
        
        self.edit_time_btn = QPushButton("✎ Edit")
        self.edit_time_btn.setObjectName("edit_time_btn")
        self.edit_time_btn.setFixedSize(50, 20)
        self.edit_time_btn.clicked.connect(self.on_edit_time_clicked)
        user_layout.addWidget(self.edit_time_btn)
        
        user_layout.addStretch()
        group_layout.addLayout(user_layout)
        
        # A and B controls
        params_layout = QHBoxLayout()
        
        params_layout.addWidget(QLabel("a:"))
        self.a_spin = QDoubleSpinBox()
        self.a_spin.setRange(0.01, 500.0)
        self.a_spin.setDecimals(3)
        self.a_spin.setValue(self.a)
        self.a_spin.valueChanged.connect(self.on_param_changed)
        params_layout.addWidget(self.a_spin)
        
        params_layout.addWidget(QLabel("b:"))
        self.b_spin = QDoubleSpinBox()
        self.b_spin.setRange(0.01, 200.0)
        self.b_spin.setDecimals(3)
        self.b_spin.setValue(self.b)
        self.b_spin.valueChanged.connect(self.on_param_changed)
        params_layout.addWidget(self.b_spin)
        
        params_layout.addStretch()
        group_layout.addLayout(params_layout)
        
        # Buttons row
        buttons_layout = QHBoxLayout()
        
        self.calc_btn = QPushButton("Calculate Ratio")
        self.calc_btn.clicked.connect(self.on_calculate_ratio)
        buttons_layout.addWidget(self.calc_btn)
        
        self.auto_fit_btn = QPushButton("Auto-Fit")
        self.auto_fit_btn.setStyleSheet("background-color: #2196F3;")
        self.auto_fit_btn.clicked.connect(lambda: self.auto_fit_requested.emit(self.session_type))
        buttons_layout.addWidget(self.auto_fit_btn)
        
        group_layout.addLayout(buttons_layout)
        
        layout.addWidget(group)
    
    def on_edit_time_clicked(self):
        """Open dialog to edit user lap time"""
        if self.user_time is None or self.user_time <= 0:
            QMessageBox.warning(self, "No Time", "No lap time available to edit.")
            return
        
        dialog = ManualLapTimeDialog(self, self.session_type, self.user_time)
        if dialog.exec_() == QDialog.Accepted and dialog.new_time is not None:
            self.user_time = dialog.new_time
            minutes = int(self.user_time) // 60
            seconds = self.user_time % 60
            self.user_time_label.setText(f"{minutes}:{seconds:06.3f}")
            self.lap_time_edited.emit(self.session_type, self.user_time)
    
    def on_show_toggled(self, checked):
        self.show_data_toggled.emit(self.session_type, checked)
        
    def on_param_changed(self):
        self.a = self.a_spin.value()
        self.b = self.b_spin.value()
        self.formula_label.setText(f"T = {self.a:.2f} / R + {self.b:.2f}")
        self.formula_changed.emit(self.session_type, self.a, self.b)
        # Mark button as needing calculation (turn orange)
        self.set_calc_button_modified(True)
    
    def set_calc_button_modified(self, modified: bool):
        """Set whether the calculate button should be orange"""
        self.calc_button_modified = modified
        if modified:
            self.calc_btn.setStyleSheet("background-color: #FF9800;")
        else:
            self.calc_btn.setStyleSheet("")  # Reset to default
    
    def _calculate_and_confirm_ratio(self, lap_time: float):
        """Calculate ratio and ask user to confirm saving to AIW"""
        denominator = lap_time - self.b
        if denominator <= 0:
            return
        
        ratio = self.a / denominator
        if 0.3 < ratio < 3.0:
            self.current_ratio = ratio
            
            # Check ratio limits
            min_ratio, max_ratio = get_ratio_limits()
            if ratio < min_ratio or ratio > max_ratio:
                reply = QMessageBox.question(
                    self, "Ratio Out of Range",
                    f"The calculated {self.session_type.upper()} Ratio = {ratio:.6f} is outside the allowed range "
                    f"({min_ratio} - {max_ratio}).\n\n"
                    f"Values outside this range can make AI behavior unpredictable.\n\n"
                    f"Do you still want to save this ratio?",
                    QMessageBox.Yes | QMessageBox.No
                )
                if reply != QMessageBox.Yes:
                    return
            
            # Ask user to confirm saving to AIW
            reply = QMessageBox.question(
                self, "Save Ratio to AIW?",
                f"Calculated {self.session_type.upper()} Ratio = {ratio:.6f}\n\n"
                f"Based on lap time: {lap_time:.3f}s\n"
                f"Using formula: T = {self.a:.3f} / R + {self.b:.3f}\n\n"
                f"Save this ratio to the AIW file?",
                QMessageBox.Yes | QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                # Emit signal to save ratio to AIW
                self.calculate_ratio.emit(self.session_type, lap_time)
                # Reset button color after saving
                self.set_calc_button_modified(False)
            else:
                QMessageBox.information(self, "Cancelled", "Ratio not saved to AIW.")
        
    def on_calculate_ratio(self):
        if self.user_time and self.user_time > 0:
            self._calculate_and_confirm_ratio(self.user_time)
        else:
            QMessageBox.warning(self, "No Time", "No user time available for this session.")
            
    def update_formula(self, a: float, b: float):
        self.a = a
        self.b = b
        self.a_spin.blockSignals(True)
        self.b_spin.blockSignals(True)
        self.a_spin.setValue(a)
        self.b_spin.setValue(b)
        self.a_spin.blockSignals(False)
        self.b_spin.blockSignals(False)
        self.formula_label.setText(f"T = {a:.2f} / R + {b:.2f}")
        # Reset the modified flag since formula was updated externally
        self.set_calc_button_modified(False)
        
    def update_user_time(self, time_sec: float):
        self.user_time = time_sec
        if time_sec and time_sec > 0:
            minutes = int(time_sec) // 60
            seconds = time_sec % 60
            self.user_time_label.setText(f"{minutes}:{seconds:06.3f}")
        else:
            self.user_time_label.setText("--")
            
    def update_ratio(self, ratio: float):
        self.current_ratio = ratio
        
    def set_show_data(self, show: bool):
        self.show_checkbox.blockSignals(True)
        self.show_checkbox.setChecked(show)
        self.show_checkbox.blockSignals(False)


class CurveGraphWidget(QWidget):
    """Widget containing the curve graph and data management"""
    
    point_selected = pyqtSignal(str, str, float, float)
    data_updated = pyqtSignal()
    formula_changed = pyqtSignal(str, float, float)  # session_type, a, b
    
    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self.class_mapping = load_vehicle_classes()
        
        # Current state
        self.qual_a = DEFAULT_A_VALUE
        self.qual_b = 70.0
        self.race_a = DEFAULT_A_VALUE
        self.race_b = 70.0
        self.show_qualifying = True
        self.show_race = True
        self.show_user_points = True
        
        # Data
        self.all_tracks = []
        self.all_classes = []
        self.current_track = ""
        self.current_vehicle = ""
        self.current_vehicle_class = ""
        self.selected_classes = []
        
        # Current user times and calculated ratios
        self.user_qual_time = None
        self.user_race_time = None
        self.user_qual_ratio = None
        self.user_race_ratio = None
        
        # Plot items
        self.qual_curve = None
        self.race_curve = None
        self.qual_scatter = None
        self.race_scatter = None
        self.unknown_scatter = None
        self.user_qual_point = None
        self.user_race_point = None
        self.legend = None
        self.selected_point_marker = None
        
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Top info bar with track/class selection
        top_frame = QFrame()
        top_frame.setStyleSheet("""
            QFrame {
                background-color: #2b2b2b;
                border-radius: 5px;
                padding: 8px;
            }
        """)
        top_layout = QHBoxLayout(top_frame)
        
        # Track selection
        track_group = QFrame()
        track_group.setStyleSheet("background-color: #1e1e1e; border-radius: 3px;")
        track_layout = QHBoxLayout(track_group)
        track_layout.setContentsMargins(8, 4, 8, 4)
        track_layout.addWidget(QLabel("🏁 Track:"))
        self.current_track_label = QLabel("-")
        self.current_track_label.setStyleSheet("color: #FFA500; font-weight: bold;")
        track_layout.addWidget(self.current_track_label)
        
        self.select_track_btn = QPushButton("Change")
        self.select_track_btn.setFixedWidth(70)
        self.select_track_btn.setStyleSheet("background-color: #2196F3; padding: 2px 8px;")
        self.select_track_btn.clicked.connect(self.select_track)
        track_layout.addWidget(self.select_track_btn)
        top_layout.addWidget(track_group)
        
        # Vehicle class selection
        class_group = QFrame()
        class_group.setStyleSheet("background-color: #1e1e1e; border-radius: 3px;")
        class_layout = QHBoxLayout(class_group)
        class_layout.setContentsMargins(8, 4, 8, 4)
        class_layout.addWidget(QLabel("📊 Class:"))
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
        
        # Refresh button
        self.refresh_btn = QPushButton("Refresh Data")
        self.refresh_btn.setStyleSheet("background-color: #4CAF50;")
        self.refresh_btn.clicked.connect(self.full_refresh)
        top_layout.addWidget(self.refresh_btn)
        
        layout.addWidget(top_frame)
        
        layout.addSpacing(5)
        
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
        
        self.plot.scene().sigMouseClicked.connect(self.on_plot_click)
        
        layout.addWidget(self.plot_widget)
        
        # Formula summary at bottom
        info_layout = QHBoxLayout()
        self.formula_label = QLabel("")
        self.formula_label.setStyleSheet("color: #888; font-size: 10px; font-family: monospace;")
        info_layout.addWidget(self.formula_label)
        info_layout.addStretch()
        layout.addLayout(info_layout)
        
    def _calculate_ratio_for_user_time(self, time_sec: float, session_type: str) -> Optional[float]:
        """Calculate the ratio that would produce the given lap time using the current formula"""
        if session_type == "qual":
            a, b = self.qual_a, self.qual_b
        else:
            a, b = self.race_a, self.race_b
        
        denominator = time_sec - b
        if denominator <= 0:
            return None
        
        ratio = a / denominator
        if 0.3 < ratio < 3.0:
            return ratio
        return None
    
    def select_track(self):
        """Open dialog to select a different track"""
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
        """Open dialog to select vehicle classes"""
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
    
    def get_user_qual_time(self) -> Optional[float]:
        return self.user_qual_time
    
    def get_user_race_time(self) -> Optional[float]:
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

    def _get_vehicles_for_classes(self, classes: List[str]) -> List[str]:
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
    
    def update_graph(self):
        ratios = np.linspace(0.4, 2.0, 200)
        points_data = self.get_selected_data()
        
        qual_times = self.qual_a / ratios + self.qual_b
        race_times = self.race_a / ratios + self.race_b
        
        if self.show_qualifying:
            if self.qual_curve is None:
                self.qual_curve = self.plot.plot(ratios, qual_times, 
                                                 pen=pg.mkPen(color='#FFFF00', width=2.5))
            else:
                self.qual_curve.setData(ratios, qual_times)
                self.qual_curve.setVisible(True)
        elif self.qual_curve is not None:
            self.qual_curve.setVisible(False)
        
        if self.show_race:
            if self.race_curve is None:
                self.race_curve = self.plot.plot(ratios, race_times,
                                                 pen=pg.mkPen(color='#FF6600', width=2.5))
            else:
                self.race_curve.setData(ratios, race_times)
                self.race_curve.setVisible(True)
        elif self.race_curve is not None:
            self.race_curve.setVisible(False)
        
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
        if unknown_points:
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
        
        # User points
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
                self.user_qual_point = pg.ScatterPlotItem(
                    r, t, brush=pg.mkBrush('#00FFFF'), size=14,
                    symbol='star', pen=pg.mkPen('white', width=2)
                )
                self.plot.addItem(self.user_qual_point)
                
                self.user_point_labels = []
                for i, (label, ratio_val, time_val) in enumerate(user_labels):
                    text_item = pg.TextItem(text=f"  {label}", color='#00FFFF', anchor=(0, 0.5))
                    text_item.setPos(ratio_val, time_val)
                    self.plot.addItem(text_item)
                    self.user_point_labels.append(text_item)
            else:
                self.user_qual_point.setData(r, t)
                self.user_qual_point.setVisible(True)
                
                for i, (label, ratio_val, time_val) in enumerate(user_labels):
                    if i < len(self.user_point_labels):
                        self.user_point_labels[i].setPos(ratio_val, time_val)
                        self.user_point_labels[i].setHtml(f'  <span style="color:#00FFFF;">{label}</span>')
                    else:
                        text_item = pg.TextItem(text=f"  {label}", color='#00FFFF', anchor=(0, 0.5))
                        text_item.setPos(ratio_val, time_val)
                        self.plot.addItem(text_item)
                        self.user_point_labels.append(text_item)
        elif self.user_qual_point is not None:
            self.user_qual_point.setVisible(False)
            if hasattr(self, 'user_point_labels'):
                for label in self.user_point_labels:
                    label.setVisible(False)
        
        # Draw dashed lines from user point to axes
        if user_points and self.show_user_points:
            if hasattr(self, 'user_v_lines'):
                for line in self.user_v_lines:
                    self.plot.removeItem(line)
            
            self.user_v_lines = []
            for ratio_val, time_val in user_points:
                v_line = pg.InfiniteLine(pos=ratio_val, angle=90, pen=pg.mkPen(color='#00FFFF', width=1, style=Qt.DashLine))
                self.plot.addItem(v_line)
                self.user_v_lines.append(v_line)
                
                h_line = pg.InfiniteLine(pos=time_val, angle=0, pen=pg.mkPen(color='#00FFFF', width=1, style=Qt.DashLine))
                self.plot.addItem(h_line)
                self.user_v_lines.append(h_line)
        
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
        if unknown_points:
            self.legend.addItem(self.unknown_scatter, f'Unknown ({len(unknown_points)})')
        if user_points:
            self.legend.addItem(self.user_qual_point, 'Your Lap Times')
        
        qual_info = ""
        race_info = ""
        if self.user_qual_time and self.user_qual_ratio:
            qual_info = f"Qual: T={self.user_qual_time:.2f}s → R={self.user_qual_ratio:.4f}"
        if self.user_race_time and self.user_race_ratio:
            race_info = f"Race: T={self.user_race_time:.2f}s → R={self.user_race_ratio:.4f}"
        
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
        
        if self.selected_point_marker:
            self.plot.removeItem(self.selected_point_marker)
        
        self.selected_point_marker = pg.ScatterPlotItem(
            [ratio], [lap_time], brush=pg.mkBrush('#FFFFFF'), size=12,
            symbol='o', pen=pg.mkPen('#FF0000', width=2)
        )
        self.plot.addItem(self.selected_point_marker)
        
        self.point_selected.emit(self.current_track, session, ratio, lap_time)
    
    def set_formulas(self, qual_a, qual_b, race_a, race_b):
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


def calculate_accuracy_rating(data_points: List[Tuple[float, float]], formula, max_allowed_error: float = 0.5) -> str:
    """
    Calculate accuracy rating based on data points and error rate.
    
    Returns: "very_low", "low", "medium", "high"
    
    Criteria:
    - less than 4 different ratios OR more than 4 different ratios, less than 4 datapoints per ratio -> very low
    - more than that, error rate too big -> low
    - more than that, error rate not too big -> medium
    - more than 10 ratios, error rate too big -> also medium
    - anything better than that -> high
    """
    if not data_points or len(data_points) < 2:
        return "very_low"
    
    # Count unique ratios
    unique_ratios = set()
    ratio_counts = {}
    for ratio, _ in data_points:
        unique_ratios.add(ratio)
        ratio_counts[ratio] = ratio_counts.get(ratio, 0) + 1
    
    unique_ratio_count = len(unique_ratios)
    
    # Check if less than 4 different ratios
    if unique_ratio_count < 4:
        return "very_low"
    
    # Check if any ratio has less than 4 data points
    min_points_per_ratio = min(ratio_counts.values()) if ratio_counts else 0
    if min_points_per_ratio < 4:
        return "very_low"
    
    # Calculate error rate
    total_error = 0
    for ratio, lap_time in data_points:
        predicted = formula.get_time_at_ratio(ratio) if hasattr(formula, 'get_time_at_ratio') else (formula.a / ratio + formula.b)
        error = abs(predicted - lap_time)
        total_error += error
    
    avg_error = total_error / len(data_points)
    error_too_big = avg_error > max_allowed_error
    
    # More than 10 ratios with error too big -> medium
    if unique_ratio_count > 10 and error_too_big:
        return "medium"
    
    # More than 4 different ratios with 4+ points per ratio
    if error_too_big:
        return "low"
    else:
        return "medium" if 4 <= unique_ratio_count <= 10 else "high"


class AdvancedSettingsDialog(QDialog):
    """Advanced settings window with unified tab layout"""
    
    data_updated = pyqtSignal()
    formula_updated = pyqtSignal(str, float, float)  # session_type, a, b
    ratio_saved = pyqtSignal(str, float)  # session_type, ratio
    lap_time_updated = pyqtSignal(str, float)  # session_type, lap_time
    
    def __init__(self, parent=None, db=None, log_window=None):
        super().__init__(parent)
        self.parent = parent
        self.db = db
        self.log_window = log_window
        self.setWindowTitle("Advanced Settings")
        self.setGeometry(100, 100, 1200, 800)
        self.setMinimumWidth(1000)
        self.setMinimumHeight(700)
        
        self.target_mode = "percentage"
        self.target_percentage = 50
        self.target_offset_seconds = 0.0
        self.ai_error_margin = 0.0
        
        self.qual_panel = None
        self.race_panel = None
        self.curve_graph = None
        self.data_table = None
        
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        self.tab_widget = QTabWidget()
        
        # TAB 1: DATA MANAGEMENT
        data_tab = QWidget()
        data_layout = QVBoxLayout(data_tab)
        data_layout.setContentsMargins(0, 0, 0, 0)
        
        # Curve graph at top
        self.curve_graph = CurveGraphWidget(self.db, self)
        self.curve_graph.point_selected.connect(self.on_point_selected)
        self.curve_graph.data_updated.connect(self.on_data_updated)
        self.curve_graph.formula_changed.connect(self.on_formula_changed)
        data_layout.addWidget(self.curve_graph)
        
        # Middle section: Qualifying and Race panels side by side
        middle_layout = QHBoxLayout()
        middle_layout.setSpacing(15)
        
        # Qualifying panel
        self.qual_panel = SessionPanel("qual", "Qualifying Session", self.db, self)
        self.qual_panel.formula_changed.connect(self.on_session_formula_changed)
        self.qual_panel.show_data_toggled.connect(self.on_show_data_toggled)
        self.qual_panel.calculate_ratio.connect(self.on_calculate_and_save_ratio)
        self.qual_panel.auto_fit_requested.connect(self.on_auto_fit_requested)
        self.qual_panel.lap_time_edited.connect(self.on_lap_time_edited)
        middle_layout.addWidget(self.qual_panel)
        
        # Race panel
        self.race_panel = SessionPanel("race", "Race Session", self.db, self)
        self.race_panel.formula_changed.connect(self.on_session_formula_changed)
        self.race_panel.show_data_toggled.connect(self.on_show_data_toggled)
        self.race_panel.calculate_ratio.connect(self.on_calculate_and_save_ratio)
        self.race_panel.auto_fit_requested.connect(self.on_auto_fit_requested)
        self.race_panel.lap_time_edited.connect(self.on_lap_time_edited)
        middle_layout.addWidget(self.race_panel)
        
        data_layout.addLayout(middle_layout)
        
        # Bottom: Data points table
        table_group = QGroupBox("Data Points")
        table_layout = QVBoxLayout(table_group)
        
        self.data_table = QTableWidget()
        self.data_table.setColumnCount(6)
        self.data_table.setHorizontalHeaderLabels(["Track", "Vehicle", "Class", "Ratio", "Lap Time", "Session"])
        self.data_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.data_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.data_table.setAlternatingRowColors(True)
        self.data_table.itemSelectionChanged.connect(self.on_table_selection_changed)
        table_layout.addWidget(self.data_table)
        
        table_btn_layout = QHBoxLayout()
        
        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self.refresh_all)
        table_btn_layout.addWidget(refresh_btn)
        
        delete_btn = QPushButton("Delete Selected")
        delete_btn.setStyleSheet("background-color: #f44336;")
        delete_btn.clicked.connect(self.delete_selected_points)
        table_btn_layout.addWidget(delete_btn)
        
        table_btn_layout.addStretch()
        table_layout.addLayout(table_btn_layout)
        
        data_layout.addWidget(table_group)
        
        self.tab_widget.addTab(data_tab, "Data Management")
        
        # TAB 2: AI TARGET
        target_tab = QWidget()
        target_layout = QVBoxLayout(target_tab)
        
        target_info = QLabel(
            "AI Target Positioning\n\n"
            "This controls where your lap time should fall within the AI's lap time range.\n\n"
            "The AI's best and worst lap times create a range. You choose where you want to be.\n\n"
            "⚡ These settings will be applied to BOTH Qualifying and Race sessions.\n\n"
            "How it works:\n"
            "1. The AI range is defined by the fastest and slowest AI lap times from your data\n"
            "2. Your target position determines what lap time the AI should aim for\n"
            "3. The program calculates a new AI Ratio that will make AI lap times match your target\n"
            "4. This ratio is written to the AIW file and used in your next session"
        )
        target_info.setStyleSheet("color: #FFA500; background-color: #2b2b2b; padding: 10px; border-radius: 5px;")
        target_info.setWordWrap(True)
        target_layout.addWidget(target_info)
        
        target_layout.addSpacing(10)
        
        mode_group = QGroupBox("Target Mode")
        mode_layout = QVBoxLayout(mode_group)
        
        self.percentage_radio = QRadioButton("Percentage within AI range (Recommended)")
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
        self.tab_widget.addTab(target_tab, "AI Target")
        
        # TAB 3: BACKUP RESTORE
        backup_tab = QWidget()
        backup_layout = QVBoxLayout(backup_tab)
        
        backup_info = QLabel(
            "AIW Backup Restore\n\n"
            "When Autoratio modifies an AIW file, it creates a backup first.\n"
            "Use this section to restore original AIW files.\n\n"
            "Note: Restoring will undo any Autoratio changes made to that track."
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
        self.tab_widget.addTab(backup_tab, "Backup Restore")
        
        # TAB 4: LOGS
        logs_tab = QWidget()
        logs_layout = QVBoxLayout(logs_tab)
        
        if self.log_window:
            logs_layout.addWidget(QLabel("Application Logs:"))
            
            self.log_display = QTextEdit()
            self.log_display.setReadOnly(True)
            self.log_display.setFontFamily("Courier New")
            self.log_display.setStyleSheet("""
                QTextEdit {
                    background-color: #1e1e1e;
                    color: #d4d4d4;
                    font-size: 10px;
                }
            """)
            logs_layout.addWidget(self.log_display)
            
            self.log_window.log_text.document().contentsChange.connect(self.sync_log_display)
            self.sync_log_display()
            
            log_btn_layout = QHBoxLayout()
            
            clear_log_btn = QPushButton("Clear Log")
            clear_log_btn.clicked.connect(self.clear_log_display)
            log_btn_layout.addWidget(clear_log_btn)
            
            log_btn_layout.addStretch()
            logs_layout.addLayout(log_btn_layout)
        
        self.tab_widget.addTab(logs_tab, "Logs")
        
        layout.addWidget(self.tab_widget)
        
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
    
    def on_lap_time_edited(self, session_type: str, new_time: float):
        """Handle lap time edit from panel"""
        self.lap_time_updated.emit(session_type, new_time)
        # Refresh the graph with new lap time
        if self.curve_graph:
            if session_type == "qual":
                self.curve_graph.user_qual_time = new_time
                self.curve_graph.user_qual_ratio = self.curve_graph._calculate_ratio_for_user_time(new_time, "qual")
            else:
                self.curve_graph.user_race_time = new_time
                self.curve_graph.user_race_ratio = self.curve_graph._calculate_ratio_for_user_time(new_time, "race")
            self.curve_graph.update_graph()
    
    def on_parent_data_refresh(self):
        logger.debug("AdvancedSettingsDialog: Received data refresh signal from parent")
        self.refresh_display()
    
    def sync_log_display(self):
        if hasattr(self, 'log_display') and self.log_window:
            self.log_display.setHtml(self.log_window.log_text.toHtml())
            
    def clear_log_display(self):
        if self.log_window:
            self.log_window.clear_log()
        if hasattr(self, 'log_display'):
            self.log_display.clear()
    
    def refresh_all(self):
        if self.curve_graph:
            self.curve_graph.full_refresh()
        self.load_data_table()
        self.refresh_display()
        
    def load_data_table(self):
        if not self.curve_graph or not self.curve_graph.current_track:
            self.data_table.setRowCount(0)
            return
        
        vehicle_classes = self.curve_graph.selected_classes
        if not vehicle_classes:
            self.data_table.setRowCount(0)
            return
        
        conn = sqlite3.connect(self.db.db_path)
        cursor = conn.cursor()
        
        placeholders = ','.join('?' * len(vehicle_classes))
        query = f"""
            SELECT track, vehicle_class, ratio, lap_time, session_type 
            FROM data_points 
            WHERE track = ? AND vehicle_class IN ({placeholders})
            ORDER BY session_type, ratio
        """
        cursor.execute(query, [self.curve_graph.current_track] + vehicle_classes)
        rows = cursor.fetchall()
        conn.close()
        
        self.data_table.setRowCount(len(rows))
        for i, row in enumerate(rows):
            track, vehicle_class, ratio, lap_time, session_type = row
            
            self.data_table.setItem(i, 0, QTableWidgetItem(str(track)))
            self.data_table.setItem(i, 1, QTableWidgetItem(str(vehicle_class)))
            self.data_table.setItem(i, 2, QTableWidgetItem(str(vehicle_class)))
            self.data_table.setItem(i, 3, QTableWidgetItem(f"{ratio:.6f}"))
            self.data_table.setItem(i, 4, QTableWidgetItem(f"{lap_time:.3f}"))
            self.data_table.setItem(i, 5, QTableWidgetItem(str(session_type)))
            
            if session_type == 'qual':
                color = QColor(58, 58, 0)
            elif session_type == 'race':
                color = QColor(58, 26, 0)
            else:
                color = QColor(42, 0, 58)
            
            for j in range(6):
                item = self.data_table.item(i, j)
                if item:
                    item.setBackground(color)
        
        self.data_table.resizeRowsToContents()
    
    def on_table_selection_changed(self):
        selected = self.data_table.selectedItems()
        if not selected:
            return
        
        row = selected[0].row()
        ratio = float(self.data_table.item(row, 3).text())
        lap_time = float(self.data_table.item(row, 4).text())
        
        if self.curve_graph:
            if hasattr(self.curve_graph, 'selected_point_marker') and self.curve_graph.selected_point_marker:
                self.curve_graph.plot.removeItem(self.curve_graph.selected_point_marker)
            
            self.curve_graph.selected_point_marker = pg.ScatterPlotItem(
                [ratio], [lap_time], brush=pg.mkBrush('#FFFFFF'), size=12,
                symbol='o', pen=pg.mkPen('#FF0000', width=2)
            )
            self.curve_graph.plot.addItem(self.curve_graph.selected_point_marker)
    
    def delete_selected_points(self):
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
            ratio = float(self.data_table.item(row_idx, 3).text())
            lap_time = float(self.data_table.item(row_idx, 4).text())
            session_type = self.data_table.item(row_idx, 5).text()
            
            cursor.execute("""
                DELETE FROM data_points 
                WHERE track = ? AND vehicle_class = ? AND ratio = ? 
                AND lap_time = ? AND session_type = ?
            """, (track, vehicle, ratio, lap_time, session_type))
            deleted += cursor.rowcount
        
        conn.commit()
        conn.close()
        
        self.refresh_all()
        QMessageBox.information(self, "Success", f"Deleted {deleted} data point(s).")
    
    def refresh_display(self):
        if not self.parent:
            return
        
        current_track = getattr(self.parent, 'current_track', None)
        current_vehicle = getattr(self.parent, 'current_vehicle', None)
        user_qual_time = getattr(self.parent, 'user_qualifying_sec', 0.0)
        user_race_time = getattr(self.parent, 'user_best_lap_sec', 0.0)
        qual_a = getattr(self.parent, 'qual_a', DEFAULT_A_VALUE)
        qual_b = getattr(self.parent, 'qual_b', 70.0)
        race_a = getattr(self.parent, 'race_a', DEFAULT_A_VALUE)
        race_b = getattr(self.parent, 'race_b', 70.0)
        last_qual_ratio = getattr(self.parent, 'last_qual_ratio', None)
        last_race_ratio = getattr(self.parent, 'last_race_ratio', None)
        
        if self.curve_graph:
            self.curve_graph.update_current_info(
                track=current_track,
                vehicle=current_vehicle,
                qual_time=user_qual_time if user_qual_time > 0 else None,
                race_time=user_race_time if user_race_time > 0 else None,
                qual_ratio=last_qual_ratio,
                race_ratio=last_race_ratio
            )
            self.curve_graph.set_formulas(qual_a, qual_b, race_a, race_b)
            self.curve_graph.update_graph()
        
        if self.qual_panel:
            self.qual_panel.update_formula(qual_a, qual_b)
            self.qual_panel.update_user_time(user_qual_time)
            self.qual_panel.update_ratio(last_qual_ratio)
        
        if self.race_panel:
            self.race_panel.update_formula(race_a, race_b)
            self.race_panel.update_user_time(user_race_time)
            self.race_panel.update_ratio(last_race_ratio)
        
        self.load_data_table()
    
    def showEvent(self, event):
        self.refresh_display()
        super().showEvent(event)
    
    def on_point_selected(self, track, session, ratio, lap_time):
        for row in range(self.data_table.rowCount()):
            if (abs(float(self.data_table.item(row, 3).text()) - ratio) < 0.001 and
                abs(float(self.data_table.item(row, 4).text()) - lap_time) < 0.01):
                self.data_table.selectRow(row)
                self.data_table.scrollToItem(self.data_table.item(row, 0))
                break
    
    def on_data_updated(self):
        self.load_data_table()
        self.data_updated.emit()
    
    def on_formula_changed(self, session_type: str, a: float, b: float):
        if session_type == "qual" and self.qual_panel:
            self.qual_panel.update_formula(a, b)
        elif session_type == "race" and self.race_panel:
            self.race_panel.update_formula(a, b)
        self.formula_updated.emit(session_type, a, b)
    
    def on_session_formula_changed(self, session_type: str, a: float, b: float):
        if self.curve_graph:
            if session_type == "qual":
                self.curve_graph.qual_a = a
                self.curve_graph.qual_b = b
            else:
                self.curve_graph.race_a = a
                self.curve_graph.race_b = b
            if self.curve_graph.user_qual_time and session_type == "qual":
                self.curve_graph.user_qual_ratio = self.curve_graph._calculate_ratio_for_user_time(
                    self.curve_graph.user_qual_time, "qual")
            if self.curve_graph.user_race_time and session_type == "race":
                self.curve_graph.user_race_ratio = self.curve_graph._calculate_ratio_for_user_time(
                    self.curve_graph.user_race_time, "race")
            self.curve_graph.update_graph()
        self.formula_updated.emit(session_type, a, b)
    
    def on_show_data_toggled(self, session_type: str, show: bool):
        if self.curve_graph:
            if session_type == "qual":
                self.curve_graph.set_show_qualifying(show)
            else:
                self.curve_graph.set_show_race(show)
    
    def on_calculate_and_save_ratio(self, session_type: str, lap_time: float):
        """Calculate ratio and save directly to AIW"""
        if session_type == "qual":
            a, b = self.qual_panel.a, self.qual_panel.b
        else:
            a, b = self.race_panel.a, self.race_panel.b
        
        denominator = lap_time - b
        if denominator <= 0:
            return
        
        ratio = a / denominator
        
        if 0.3 < ratio < 3.0:
            # Check ratio limits before saving
            min_ratio, max_ratio = get_ratio_limits()
            if ratio < min_ratio or ratio > max_ratio:
                reply = QMessageBox.question(self, "Ratio Out of Range",
                    f"The calculated {session_type.upper()} Ratio = {ratio:.6f} is outside the allowed range "
                    f"({min_ratio} - {max_ratio}).\n\n"
                    f"Values outside this range can make AI behavior unpredictable.\n\n"
                    f"Do you still want to save this ratio?",
                    QMessageBox.Yes | QMessageBox.No)
                if reply != QMessageBox.Yes:
                    return
            
            # Emit signal to parent to save to AIW
            self.ratio_saved.emit(session_type, ratio)
            
            # Update the graph to show the saved ratio
            if self.curve_graph:
                if session_type == "qual":
                    self.curve_graph.user_qual_ratio = ratio
                else:
                    self.curve_graph.user_race_ratio = ratio
                self.curve_graph.update_graph()
            
            # Also update the main window's display through the parent
            if self.parent:
                if session_type == "qual":
                    self.parent.last_qual_ratio = ratio
                    self.parent.qual_panel.update_ratio(ratio)
                else:
                    self.parent.last_race_ratio = ratio
                    self.parent.race_panel.update_ratio(ratio)
            
            QMessageBox.information(self, "Ratio Saved", 
                f"{session_type.upper()} Ratio = {ratio:.6f} has been saved to the AIW file.")
    
    def on_auto_fit_requested(self, session_type: str):
        if not self.curve_graph:
            return
        
        points_data = self.curve_graph.get_selected_data()
        
        if session_type == "qual":
            points = points_data.get('quali', [])
        else:
            points = points_data.get('race', [])
        
        if len(points) < 2:
            QMessageBox.warning(self, "Insufficient Data", 
                f"Need at least 2 data points to auto-fit {session_type} formula.\n"
                f"Found {len(points)} points.")
            return
        
        ratios = [p[0] for p in points]
        times = [p[1] for p in points]
        a, b, avg_err, max_err = fit_curve(ratios, times, verbose=False)
        
        if a and b and a > 0 and b > 0:
            b = b
            a = DEFAULT_A_VALUE
            
            # Check if the fitted b produces valid ratios within limits
            min_ratio, max_ratio = get_ratio_limits()
            
            # Test a typical user time to see what ratio would be produced
            test_time = None
            if session_type == "qual" and self.curve_graph.user_qual_time:
                test_time = self.curve_graph.user_qual_time
            elif session_type == "race" and self.curve_graph.user_race_time:
                test_time = self.curve_graph.user_race_time
            
            ratio_warning = None
            if test_time and test_time > 0:
                denominator = test_time - b
                if denominator > 0:
                    test_ratio = a / denominator
                    if test_ratio < min_ratio:
                        ratio_warning = f"WARNING: This formula would produce a ratio of {test_ratio:.6f}, which is BELOW the minimum allowed ({min_ratio})."
                    elif test_ratio > max_ratio:
                        ratio_warning = f"WARNING: This formula would produce a ratio of {test_ratio:.6f}, which is ABOVE the maximum allowed ({max_ratio})."
            
            if ratio_warning:
                reply = QMessageBox.question(self, "Ratio Limit Warning",
                    f"{ratio_warning}\n\n"
                    f"Formula: T = {a:.4f} / R + {b:.4f}\n"
                    f"Average error: {avg_err:.3f}s\n"
                    f"Max error: {max_err:.3f}s\n\n"
                    f"Do you still want to apply this formula?",
                    QMessageBox.Yes | QMessageBox.No)
                
                if reply != QMessageBox.Yes:
                    return
            
            if session_type == "qual":
                self.qual_panel.update_formula(a, b)
                if self.curve_graph:
                    self.curve_graph.qual_a = a
                    self.curve_graph.qual_b = b
            else:
                self.race_panel.update_formula(a, b)
                if self.curve_graph:
                    self.curve_graph.race_a = a
                    self.curve_graph.race_b = b
            
            if self.curve_graph:
                if self.curve_graph.user_qual_time:
                    self.curve_graph.user_qual_ratio = self.curve_graph._calculate_ratio_for_user_time(
                        self.curve_graph.user_qual_time, "qual")
                if self.curve_graph.user_race_time:
                    self.curve_graph.user_race_ratio = self.curve_graph._calculate_ratio_for_user_time(
                        self.curve_graph.user_race_time, "race")
                self.curve_graph.update_graph()
            
            self.formula_updated.emit(session_type, a, b)
            
            # Also update the main window's formulas
            if self.parent:
                if session_type == "qual":
                    self.parent.qual_b = b
                else:
                    self.parent.race_b = b
                self.parent.update_display()
            
            QMessageBox.information(self, "Auto-Fit Complete", 
                f"Formula fitted to {len(points)} data points:\n"
                f"T = {a:.4f} / R + {b:.4f}\n"
                f"Average error: {avg_err:.3f}s\n"
                f"Max error: {max_err:.3f}s\n\n"
                f"Note: The 'a' value has been kept at {DEFAULT_A_VALUE}.")
        else:
            QMessageBox.warning(self, "Fit Failed", "Could not fit curve to data.")
    
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
        """Apply AI Target settings - calculates new target lap time based on settings"""
        settings = {
            "mode": self.target_mode,
            "percentage": self.target_percentage,
            "offset_seconds": self.target_offset_seconds,
            "error_margin": self.ai_error_margin
        }
        
        if self.parent:
            self.parent.ai_target_settings = settings
            if hasattr(self.parent, 'statusBar'):
                self.parent.statusBar().showMessage(f"AI Target settings applied", 3000)
            
            # Update the target display on the main window
            if hasattr(self.parent, 'update_target_display'):
                self.parent.update_target_display()
            
            # Calculate and show the target position using the autopilot engine
            if hasattr(self.parent, 'autopilot_manager') and self.parent.autopilot_manager:
                engine = self.parent.autopilot_manager.engine
                if engine:
                    qual_best = getattr(self.parent, 'qual_best_ai', None)
                    qual_worst = getattr(self.parent, 'qual_worst_ai', None)
                    race_best = getattr(self.parent, 'race_best_ai', None)
                    race_worst = getattr(self.parent, 'race_worst_ai', None)
                    
                    target_text = ""
                    if qual_best and qual_worst:
                        target_time = engine.calculate_target_time_from_settings(
                            qual_best, qual_worst, settings
                        )
                        target_text += f"Qual: {target_time:.3f}s"
                    
                    if race_best and race_worst:
                        target_time = engine.calculate_target_time_from_settings(
                            race_best, race_worst, settings
                        )
                        if target_text:
                            target_text += f" | Race: {target_time:.3f}s"
                        else:
                            target_text = f"Race: {target_time:.3f}s"
                    
                    if target_text:
                        QMessageBox.information(self, "Target Applied",
                            f"AI Target settings applied!\n\n"
                            f"Your target lap times:\n{target_text}\n\n"
                            f"These settings will affect BOTH Qualifying and Race sessions.\n"
                            f"The AI will aim to produce lap times around your target position.")
                    else:
                        QMessageBox.information(self, "Target Applied",
                            f"AI Target settings have been applied.\n\n"
                            f"These settings will affect BOTH Qualifying and Race sessions.")
                else:
                    QMessageBox.information(self, "Target Applied",
                        f"AI Target settings have been applied.\n\n"
                        f"These settings will affect BOTH Qualifying and Race sessions.")
            else:
                QMessageBox.information(self, "Target Applied",
                    f"AI Target settings have been applied.\n\n"
                    f"These settings will affect BOTH Qualifying and Race sessions.")
    
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
            logger.error(f"Error restoring backup: {e}")
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
            f"Restore {len(selected_items)} AIW file(s)?\n\nThis will undo Autoratio changes.",
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
            QMessageBox.information(self, "Restore Complete", f"Successfully restored {restored} AIW file(s).")
            self.refresh_backup_list()
    
    def restore_all_backups(self):
        backups = self.scan_aiw_backups()
        if not backups:
            QMessageBox.information(self, "No Backups", "No backups found to restore.")
            return
        
        reply = QMessageBox.question(
            self, "Confirm Restore All",
            f"Restore ALL {len(backups)} AIW backup(s)?\n\nThis will undo ALL Autoratio changes.",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
        
        restored = 0
        for backup in backups:
            if self.restore_aiw_backup(backup):
                restored += 1
        
        if restored > 0:
            QMessageBox.information(self, "Restore Complete", f"Successfully restored {restored} AIW file(s).")
            self.refresh_backup_list()


def setup_dark_theme(app):
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
        QDoubleSpinBox, QSpinBox {
            background-color: #3c3c3c;
            color: white;
            border: 1px solid #4CAF50;
            border-radius: 3px;
            padding: 4px;
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
        QCheckBox {
            color: white;
        }
        QRadioButton {
            color: white;
        }
        QFrame {
            background-color: transparent;
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
