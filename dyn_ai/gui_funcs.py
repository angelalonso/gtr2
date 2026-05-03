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

from formula_funcs import fit_curve, get_formula_string, hyperbolic, ratio_from_time, DEFAULT_A_VALUE
from autopilot import load_vehicle_classes, get_vehicle_class
from cfg_funcs import get_ratio_limits, get_config_with_defaults, get_base_path


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
    
    def __init__(self, parent, session_type: str, current_time: float = None):
        super().__init__(parent)
        self.session_type = session_type
        self.current_time = current_time if current_time is not None and current_time > 0 else None
        self.new_time = None
        self.setup_ui()
    
    def setup_ui(self):
        self.setWindowTitle(f"Edit {self.session_type.upper()} Lap Time")
        self.setFixedSize(350, 220)
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
        
        title = QLabel(f"Edit {self.session_type.upper()} Lap Time")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #FFA500;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        layout.addSpacing(10)
        
        # Current value display (if exists)
        if self.current_time is not None:
            current_label = QLabel(f"Current {self.session_type.upper()} Time:")
            current_label.setStyleSheet("color: #888;")
            layout.addWidget(current_label)
            
            minutes = int(self.current_time) // 60
            seconds = self.current_time % 60
            current_value = QLabel(f"{minutes}:{seconds:06.3f} ({self.current_time:.3f}s)")
            current_value.setStyleSheet("font-size: 14px; font-family: monospace; color: #4CAF50;")
            layout.addWidget(current_value)
        else:
            no_time_label = QLabel(f"No {self.session_type.upper()} time recorded yet")
            no_time_label.setStyleSheet("color: #FFA500; font-style: italic;")
            layout.addWidget(no_time_label)
        
        layout.addSpacing(15)
        
        new_label = QLabel(f"New {self.session_type.upper()} Time (seconds):")
        new_label.setStyleSheet("color: #888;")
        layout.addWidget(new_label)
        
        self.time_spin = QDoubleSpinBox()
        self.time_spin.setRange(10.0, 500.0)
        self.time_spin.setDecimals(3)
        self.time_spin.setSingleStep(0.5)
        if self.current_time is not None:
            self.time_spin.setValue(self.current_time)
        else:
            self.time_spin.setValue(90.0)  # Default reasonable value
        self.time_spin.setStyleSheet("font-size: 14px;")
        layout.addWidget(self.time_spin)
        
        layout.addSpacing(20)
        
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
    
    formula_changed = pyqtSignal(str, float, float)
    show_data_toggled = pyqtSignal(str, bool)
    calculate_ratio = pyqtSignal(str, float)
    auto_fit_requested = pyqtSignal(str)
    lap_time_edited = pyqtSignal(str, float)
    
    def __init__(self, session_type: str, title: str, db, parent=None):
        super().__init__(parent)
        self.session_type = session_type
        self.title = title
        self.db = db
        
        self.a = DEFAULT_A_VALUE
        self.b = 70.0
        self.user_time = None
        self.user_ratio = None
        self.current_ratio = None
        self.calc_button_modified = False
        
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(4)
        layout.setContentsMargins(6, 6, 6, 6)
        
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
        
        group = QGroupBox(self.title)
        group_layout = QVBoxLayout(group)
        group_layout.setSpacing(4)
        group_layout.setContentsMargins(8, 8, 8, 8)

        # Row 1: Show checkbox | Your Time: value [Edit]
        row1 = QHBoxLayout()
        self.show_checkbox = QCheckBox("Show on graph")
        self.show_checkbox.setChecked(True)
        self.show_checkbox.setStyleSheet("color: #4CAF50; font-weight: bold;")
        self.show_checkbox.toggled.connect(self.on_show_toggled)
        row1.addWidget(self.show_checkbox)

        row1.addSpacing(12)
        row1.addWidget(QLabel("Your Time:"))
        self.user_time_label = QLabel("--")
        self.user_time_label.setStyleSheet(
            "color: #4CAF50; font-weight: bold; font-family: monospace; font-size: 12px;"
        )
        row1.addWidget(self.user_time_label)

        self.edit_time_btn = QPushButton("Edit")
        self.edit_time_btn.setObjectName("edit_time_btn")
        self.edit_time_btn.setFixedSize(50, 20)
        self.edit_time_btn.clicked.connect(self.on_edit_time_clicked)
        row1.addWidget(self.edit_time_btn)
        row1.addStretch()
        group_layout.addLayout(row1)

        # Row 2: Formula: label | a: spin | b: spin
        row2 = QHBoxLayout()
        row2.addWidget(QLabel("Formula:"))
        self.formula_label = QLabel(f"T = {self.a:.2f} / R + {self.b:.2f}")
        self.formula_label.setStyleSheet("color: #FFA500; font-family: monospace;")
        row2.addWidget(self.formula_label)

        row2.addSpacing(8)
        row2.addWidget(QLabel("a:"))
        self.a_spin = QDoubleSpinBox()
        self.a_spin.setRange(0.01, 500.0)
        self.a_spin.setDecimals(3)
        self.a_spin.setValue(self.a)
        self.a_spin.setFixedWidth(70)
        self.a_spin.valueChanged.connect(self.on_param_changed)
        row2.addWidget(self.a_spin)

        row2.addWidget(QLabel("b:"))
        self.b_spin = QDoubleSpinBox()
        self.b_spin.setRange(0.01, 200.0)
        self.b_spin.setDecimals(3)
        self.b_spin.setValue(self.b)
        self.b_spin.setFixedWidth(70)
        self.b_spin.valueChanged.connect(self.on_param_changed)
        row2.addWidget(self.b_spin)
        row2.addStretch()
        group_layout.addLayout(row2)

        # Row 3: action buttons
        row3 = QHBoxLayout()
        self.calc_btn = QPushButton("Calculate Ratio")
        self.calc_btn.clicked.connect(self.on_calculate_ratio)
        row3.addWidget(self.calc_btn)

        self.auto_fit_btn = QPushButton("Auto-Fit")
        self.auto_fit_btn.setStyleSheet("background-color: #2196F3;")
        self.auto_fit_btn.clicked.connect(lambda: self.auto_fit_requested.emit(self.session_type))
        row3.addWidget(self.auto_fit_btn)
        row3.addStretch()
        group_layout.addLayout(row3)

        layout.addWidget(group)
    
    def on_edit_time_clicked(self):
        """Allow editing lap time even if none exists yet"""
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
        self.set_calc_button_modified(True)
    
    def set_calc_button_modified(self, modified: bool):
        self.calc_button_modified = modified
        if modified:
            self.calc_btn.setStyleSheet("background-color: #FF9800;")
        else:
            self.calc_btn.setStyleSheet("")
    
    def _calculate_and_confirm_ratio(self, lap_time: float):
        denominator = lap_time - self.b
        if denominator <= 0:
            QMessageBox.warning(self, "Invalid Calculation", 
                f"Cannot calculate ratio: T - b = {lap_time:.3f} - {self.b:.2f} = {denominator:.3f} (must be positive)")
            return
        
        ratio = self.a / denominator
        
        # Check valid range
        if not (0.3 < ratio < 3.0):
            QMessageBox.warning(self, "Ratio Out of Range", 
                f"Calculated ratio {ratio:.6f} is outside valid range (0.3 - 3.0)")
            return
        
        self.current_ratio = ratio
        
        min_ratio, max_ratio = get_ratio_limits()
        if ratio < min_ratio or ratio > max_ratio:
            reply = QMessageBox.question(
                self, "Ratio Out of Range",
                f"The calculated {self.session_type.upper()} Ratio = {ratio:.6f} is outside the allowed range "
                f"({min_ratio} - {max_ratio}).\n\n"
                f"Do you still want to save this ratio?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply != QMessageBox.Yes:
                return
        
        # NOTE: Removed the confirmation dialog here because the save method
        # (_save_ratio_to_aiw) already has its own confirmation. This prevents double popups.
        self.calculate_ratio.emit(self.session_type, lap_time)
        self.set_calc_button_modified(False)
        
    def on_calculate_ratio(self):
        if self.user_time and self.user_time > 0:
            self._calculate_and_confirm_ratio(self.user_time)
        else:
            QMessageBox.warning(self, "No Time", "No user time available for this session.\n\nClick the 'Edit' button to set a lap time manually.")
            
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
        self.set_calc_button_modified(False)
        
    def update_user_time(self, time_sec: float):
        self.user_time = time_sec if time_sec > 0 else None
        if self.user_time:
            minutes = int(self.user_time) // 60
            seconds = self.user_time % 60
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
        
    def _calculate_ratio_for_user_time(self, time_sec: float, session_type: str) -> Optional[float]:
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
                self.qual_curve = self.plot.plot(ratios, qual_times, pen=pg.mkPen(color='#FFFF00', width=2.5))
            else:
                self.qual_curve.setData(ratios, qual_times)
                self.qual_curve.setVisible(True)
        elif self.qual_curve is not None:
            self.qual_curve.setVisible(False)
        
        if self.show_race:
            if self.race_curve is None:
                self.race_curve = self.plot.plot(ratios, race_times, pen=pg.mkPen(color='#FF6600', width=2.5))
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
                self.qual_scatter = pg.ScatterPlotItem(r, t, brush=pg.mkBrush('#FFFF00'), size=8, symbol='o', pen=pg.mkPen('white', width=1))
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
                self.race_scatter = pg.ScatterPlotItem(r, t, brush=pg.mkBrush('#FF6600'), size=8, symbol='s', pen=pg.mkPen('white', width=1))
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
                self.unknown_scatter = pg.ScatterPlotItem(r, t, brush=pg.mkBrush('#FF00FF'), size=6, symbol='t', pen=pg.mkPen('white', width=1))
                self.plot.addItem(self.unknown_scatter)
            else:
                self.unknown_scatter.setData(r, t)
                self.unknown_scatter.setVisible(True)
        elif self.unknown_scatter is not None:
            self.unknown_scatter.setVisible(False)
        
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
        if self.selected_point_marker:
            self.plot.removeItem(self.selected_point_marker)
        self.selected_point_marker = pg.ScatterPlotItem([ratio], [lap_time], brush=pg.mkBrush('#FFFFFF'), size=12, symbol='o', pen=pg.mkPen('#FF0000', width=2))
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
    if not data_points or len(data_points) < 2:
        return "very_low"
    unique_ratios = set()
    ratio_counts = {}
    for ratio, _ in data_points:
        unique_ratios.add(ratio)
        ratio_counts[ratio] = ratio_counts.get(ratio, 0) + 1
    unique_ratio_count = len(unique_ratios)
    if unique_ratio_count < 4:
        return "very_low"
    min_points_per_ratio = min(ratio_counts.values()) if ratio_counts else 0
    if min_points_per_ratio < 4:
        return "very_low"
    total_error = 0
    for ratio, lap_time in data_points:
        predicted = formula.get_time_at_ratio(ratio) if hasattr(formula, 'get_time_at_ratio') else (formula.a / ratio + formula.b)
        error = abs(predicted - lap_time)
        total_error += error
    avg_error = total_error / len(data_points)
    error_too_big = avg_error > max_allowed_error
    if unique_ratio_count > 10 and error_too_big:
        return "medium"
    if error_too_big:
        return "low"
    else:
        return "medium" if 4 <= unique_ratio_count <= 10 else "high"


class AdvancedSettingsDialog(QDialog):
    """Advanced settings window with unified tab layout"""
    
    data_updated = pyqtSignal()
    formula_updated = pyqtSignal(str, float, float)
    ratio_saved = pyqtSignal(str, float)
    lap_time_updated = pyqtSignal(str, float)
    track_selected = pyqtSignal(str)  # Signal to notify parent when track is selected
    
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

    def _find_aiw_path_from_config(self) -> Optional[Path]:
        """
        Find AIW file using the same method as the main application and autopilot.
        Ensures consistency across all AIW operations.
        """
        base_path = get_base_path()
        
        if not base_path:
            logger.error("No base path configured in cfg.yml")
            return None
        
        # Get current track from parent
        if self.parent and hasattr(self.parent, 'current_track'):
            track_name = self.parent.current_track
        else:
            track_name = getattr(self.parent, 'current_track', None)
        
        if not track_name:
            logger.error("No current track selected")
            return None
        
        locations_dir = base_path / "GameData" / "Locations"
        if not locations_dir.exists():
            logger.error(f"Locations directory not found: {locations_dir}")
            return None
        
        # Search case-insensitively for track folder
        track_lower = track_name.lower()
        for track_dir in locations_dir.iterdir():
            if track_dir.is_dir() and track_dir.name.lower() == track_lower:
                # Look for AIW file in found directory
                for ext in ["*.AIW", "*.aiw"]:
                    aiw_files = list(track_dir.glob(ext))
                    if aiw_files:
                        logger.debug(f"Found AIW file: {aiw_files[0]}")
                        return aiw_files[0]
                break
        
        # If not found, search all subdirectories for any AIW file matching track name
        for ext in ["*.AIW", "*.aiw"]:
            for aiw_file in locations_dir.rglob(ext):
                if aiw_file.stem.lower() == track_lower or track_lower in aiw_file.stem.lower():
                    logger.debug(f"Found AIW file via partial match: {aiw_file}")
                    return aiw_file
        
        logger.warning(f"AIW file not found for track: {track_name}")
        return None
    
    def _show_aiw_path_error(self):
        """Show detailed error message with paths checked"""
        config = get_config_with_defaults()
        base_path = get_base_path()
        
        if self.parent and hasattr(self.parent, 'current_track'):
            track_name = self.parent.current_track
        else:
            track_name = getattr(self.parent, 'current_track', 'Unknown')
        
        error_msg = f"AIW file not found for track: {track_name}\n\n"
        error_msg += f"Base path from cfg.yml: {base_path if base_path else 'NOT SET'}\n"
        
        if base_path:
            locations_dir = base_path / "GameData" / "Locations"
            error_msg += f"Looking in: {locations_dir}\n"
            
            if locations_dir.exists():
                error_msg += f"\nExisting track folders in {locations_dir}:\n"
                for folder in locations_dir.iterdir():
                    if folder.is_dir():
                        error_msg += f"  - {folder.name}\n"
                
                # Check for partial matches
                error_msg += f"\nSearching for folders matching '{track_name}':\n"
                track_lower = track_name.lower()
                found = False
                for folder in locations_dir.iterdir():
                    if folder.is_dir() and folder.name.lower() == track_lower:
                        error_msg += f"  - FOUND: {folder.name}\n"
                        found = True
                if not found:
                    error_msg += f"  - No folder named '{track_name}' found\n"
            else:
                error_msg += f"\nLocations directory does NOT exist: {locations_dir}\n"
                error_msg += f"Please verify your GTR2 installation path in cfg.yml\n"
        
        error_msg += f"\nPlease ensure:\n"
        error_msg += f"1. cfg.yml has correct 'base_path' pointing to your GTR2 installation\n"
        error_msg += f"2. The track folder exists in GameData/Locations/\n"
        error_msg += f"3. The AIW file exists in that folder\n"
        
        QMessageBox.critical(self, "AIW File Not Found", error_msg)
    
    def _update_aiw_ratio(self, aiw_path: Path, ratio_name: str, new_ratio: float) -> bool:
        """Update a ratio in the AIW file"""
        import re
        
        try:
            if not aiw_path.exists():
                logger.error(f"AIW file not found: {aiw_path}")
                return False
            
            # Create backup if enabled
            try:
                backup_dir = aiw_path.parent / "aiw_backups"
                backup_dir.mkdir(parents=True, exist_ok=True)
                backup_path = backup_dir / f"{aiw_path.stem}_BACKUP{aiw_path.suffix}"
                if not backup_path.exists():
                    shutil.copy2(aiw_path, backup_path)
                    logger.info(f"Created backup: {backup_path}")
            except Exception as e:
                logger.warning(f"Could not create backup: {e}")
            
            # Read and patch AIW file
            raw = aiw_path.read_bytes()
            content = raw.replace(b"\x00", b"").decode("utf-8", errors="ignore")
            
            pattern = rf'({re.escape(ratio_name)}\s*=\s*\(?)\s*[0-9.eE+-]+\s*(\)?)'
            new_content, count = re.subn(
                pattern, 
                lambda m: f"{m.group(1)}{new_ratio:.6f}{m.group(2)}", 
                content, 
                flags=re.IGNORECASE
            )
            
            if count > 0:
                aiw_path.write_bytes(new_content.encode("utf-8", errors="ignore"))
                logger.info(f"Updated {ratio_name} to {new_ratio:.6f} in {aiw_path.name}")
                return True
            else:
                logger.warning(f"Could not find {ratio_name} pattern in {aiw_path.name}")
                return False
                
        except Exception as e:
            logger.error(f"Error updating AIW ratio: {e}")
            return False
    
    def _save_ratio_to_aiw(self, session_type: str, ratio: float, lap_time: float) -> bool:
        """Save calculated ratio to AIW file - this shows ONE confirmation dialog"""
        aiw_path = self._find_aiw_path_from_config()
        
        if not aiw_path:
            self._show_aiw_path_error()
            return False
        
        ratio_name = "QualRatio" if session_type == "qual" else "RaceRatio"
        
        # ONE confirmation dialog only
        confirm_msg = f"Save {ratio_name} = {ratio:.6f}\n\n"
        confirm_msg += f"To AIW file:\n{aiw_path}\n\n"
        confirm_msg += f"Based on lap time: {lap_time:.3f}s\n"
        confirm_msg += f"Formula: T = {DEFAULT_A_VALUE:.2f}/R + {self.qual_panel.b if session_type == 'qual' else self.race_panel.b:.2f}\n\n"
        confirm_msg += f"Proceed?"
        
        reply = QMessageBox.question(self, "Confirm Save", confirm_msg, QMessageBox.Yes | QMessageBox.No)
        if reply != QMessageBox.Yes:
            return False
        
        # Update the AIW file
        if self._update_aiw_ratio(aiw_path, ratio_name, ratio):
            QMessageBox.information(self, "Success", 
                f"{ratio_name} successfully updated to {ratio:.6f}\n\n"
                f"AIW file: {aiw_path}")
            return True
        else:
            QMessageBox.critical(self, "Error", 
                f"Failed to update {ratio_name} in AIW file.\n\n"
                f"File: {aiw_path}\n\n"
                f"Please check file permissions and format.")
            return False

    def setup_ui(self):
        layout = QVBoxLayout(self)
        self.tab_widget = QTabWidget()
        
        # TAB 1: DATA MANAGEMENT
        data_tab = QWidget()
        data_layout = QVBoxLayout(data_tab)
        data_layout.setContentsMargins(0, 0, 0, 0)
        
        self.curve_graph = CurveGraphWidget(self.db, self)
        self.curve_graph.point_selected.connect(self.on_point_selected)
        self.curve_graph.data_updated.connect(self.on_data_updated)
        self.curve_graph.formula_changed.connect(self.on_formula_changed)
        data_layout.addWidget(self.curve_graph, stretch=4)
        
        middle_layout = QHBoxLayout()
        middle_layout.setSpacing(15)
        
        self.qual_panel = SessionPanel("qual", "Qualifying Session", self.db, self)
        self.qual_panel.formula_changed.connect(self.on_session_formula_changed)
        self.qual_panel.show_data_toggled.connect(self.on_show_data_toggled)
        self.qual_panel.calculate_ratio.connect(self.on_calculate_and_save_ratio)
        self.qual_panel.auto_fit_requested.connect(self.on_auto_fit_requested)
        self.qual_panel.lap_time_edited.connect(self.on_lap_time_edited)
        middle_layout.addWidget(self.qual_panel)
        
        self.race_panel = SessionPanel("race", "Race Session", self.db, self)
        self.race_panel.formula_changed.connect(self.on_session_formula_changed)
        self.race_panel.show_data_toggled.connect(self.on_show_data_toggled)
        self.race_panel.calculate_ratio.connect(self.on_calculate_and_save_ratio)
        self.race_panel.auto_fit_requested.connect(self.on_auto_fit_requested)
        self.race_panel.lap_time_edited.connect(self.on_lap_time_edited)
        middle_layout.addWidget(self.race_panel)

        middle_widget = QWidget()
        middle_widget.setLayout(middle_layout)
        data_layout.addWidget(middle_widget, stretch=1)
        
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
        
        # WARNING BANNER - Feature under construction
        warning_banner = QLabel("WARNING: AI TARGET FEATURE IS UNDER CONSTRUCTION")
        warning_banner.setStyleSheet("""
            QLabel {
                background-color: #f44336;
                color: white;
                font-weight: bold;
                font-size: 14px;
                padding: 8px;
                border-radius: 5px;
                text-align: center;
            }
        """)
        warning_banner.setAlignment(Qt.AlignCenter)
        target_layout.addWidget(warning_banner)
        target_layout.addSpacing(10)
        
        target_info = QLabel(
            "AI Target Positioning\n\n"
            "This controls where your lap time should fall within the AI's lap time range.\n\n"
            "The AI's best and worst lap times create a range. You choose where you want to be.\n\n"
            "These settings will be applied to BOTH Qualifying and Race sessions.\n\n"
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
        
        # Dump Analysis buttons
        dump_analysis_layout = QHBoxLayout()
        dump_analysis_layout.addStretch()
        
        self.dump_qual_btn = QPushButton("Dump Qual Analysis")
        self.dump_qual_btn.setStyleSheet("background-color: #9C27B0;")
        self.dump_qual_btn.clicked.connect(lambda: self.dump_analysis("qual"))
        dump_analysis_layout.addWidget(self.dump_qual_btn)
        
        self.dump_race_btn = QPushButton("Dump Race Analysis")
        self.dump_race_btn.setStyleSheet("background-color: #9C27B0;")
        self.dump_race_btn.clicked.connect(lambda: self.dump_analysis("race"))
        dump_analysis_layout.addWidget(self.dump_race_btn)
        
        target_layout.addLayout(dump_analysis_layout)
        
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
            self.log_display.setStyleSheet("QTextEdit { background-color: #1e1e1e; color: #d4d4d4; font-size: 10px; }")
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
        
        # Connect the curve graph's track selection to notify parent
        self.curve_graph.data_updated.connect(self.on_graph_data_updated)
        
        self.setStyleSheet("""
            QDialog { background-color: #1e1e1e; }
            QTabWidget::pane { background-color: #2b2b2b; border: 1px solid #555; }
            QTabBar::tab { background-color: #3c3c3c; color: white; padding: 8px 12px; margin-right: 2px; }
            QTabBar::tab:selected { background-color: #4CAF50; }
            QTableWidget { background-color: #2b2b2b; color: white; alternate-background-color: #3c3c3c; gridline-color: #555; }
            QHeaderView::section { background-color: #3c3c3c; color: white; padding: 4px; }
            QListWidget { background-color: #2b2b2b; color: white; }
            QGroupBox { color: #4CAF50; }
            QRadioButton { color: white; }
        """)
        self.update_mode_visibility()
        
        # Load backups automatically when tab is shown
        self.tab_widget.currentChanged.connect(self.on_tab_changed)
    
    def on_graph_data_updated(self):
        """When the graph updates its data, check if track changed and notify parent"""
        if self.curve_graph and self.curve_graph.current_track:
            # Get current track from the graph
            current_track = self.curve_graph.current_track
            # Notify parent about the track change
            self.track_selected.emit(current_track)
    
    def on_tab_changed(self, index):
        """Load backups when Backup Restore tab is selected"""
        if self.tab_widget.tabText(index) == "Backup Restore":
            self.refresh_backup_list()
    
    def dump_analysis(self, session_type: str):
        """Dump analysis data for the specified session type"""
        try:
            from ai_target_analyzer import AITargetAnalyzer
            
            # Get current data from parent - self.parent is the RedesignedMainWindow instance
            parent = self.parent() if callable(self.parent) else self.parent
            if not parent:
                QMessageBox.warning(self, "Error", "Cannot access parent window data.")
                return
            
            # Create analysis
            analyzer = AITargetAnalyzer()
            
            # Collect data from parent (RedesignedMainWindow)
            track = getattr(parent, 'current_track', 'Unknown')
            vehicle_class = getattr(parent, 'current_vehicle_class', 'Unknown')
            
            if session_type == "qual":
                best_ai = getattr(parent, 'qual_best_ai', None)
                worst_ai = getattr(parent, 'qual_worst_ai', None)
                user_time = getattr(parent, 'user_qualifying_sec', None)
                current_ratio = getattr(parent, 'last_qual_ratio', None)
                formula_b = getattr(parent, 'qual_b', 70.0)
            else:
                best_ai = getattr(parent, 'race_best_ai', None)
                worst_ai = getattr(parent, 'race_worst_ai', None)
                user_time = getattr(parent, 'user_best_lap_sec', None)
                current_ratio = getattr(parent, 'last_race_ratio', None)
                formula_b = getattr(parent, 'race_b', 70.0)
            
            target_settings = getattr(parent, 'ai_target_settings', {
                "mode": "percentage",
                "percentage": 50,
                "offset_seconds": 0.0,
                "error_margin": 0.0
            })
            
            # Start the analysis
            analyzer.start_analysis(session_type, track, vehicle_class)
            
            # Add input data
            analyzer.add_input_data(
                best_ai=best_ai,
                worst_ai=worst_ai,
                user_lap_time=user_time if user_time and user_time > 0 else None,
                current_ratio=current_ratio,
                formula_a=32.0,
                formula_b=formula_b
            )
            
            # Add target settings
            analyzer.add_target_settings(
                mode=target_settings.get("mode", "percentage"),
                settings=target_settings
            )
            
            # Calculate target time based on settings
            if best_ai and worst_ai and best_ai > 0 and worst_ai > 0:
                mode = target_settings.get("mode", "percentage")
                pct = target_settings.get("percentage", 50) / 100.0
                offset = target_settings.get("offset_seconds", 0.0)
                error_margin = target_settings.get("error_margin", 0.0)
                
                if mode == "percentage":
                    target_time = best_ai + (worst_ai - best_ai) * pct
                    analyzer.add_calculation_step(
                        f"Target mode: Percentage - {pct*100:.0f}% from fastest AI",
                        {"percentage": pct*100, "target_time": target_time}
                    )
                elif mode == "faster_than_best":
                    target_time = best_ai + offset
                    analyzer.add_calculation_step(
                        f"Target mode: Faster than best AI - offset={offset:+.2f}s",
                        {"offset": offset, "target_time": target_time}
                    )
                else:
                    target_time = worst_ai - offset
                    analyzer.add_calculation_step(
                        f"Target mode: Slower than worst AI - offset={offset:+.2f}s",
                        {"offset": offset, "target_time": target_time}
                    )
                
                # Apply error margin
                if error_margin > 0:
                    old_target = target_time
                    target_time = target_time + error_margin
                    analyzer.add_calculation_step(
                        f"Applied error margin: +{error_margin:.2f}s",
                        {"error_margin": error_margin, "old_target": old_target, "new_target": target_time}
                    )
                
                # Clamp to AI range
                target_time = max(best_ai, min(worst_ai + error_margin, target_time))
                analyzer.add_calculation_step(
                    f"Final target clamped to AI range: {target_time:.3f}s",
                    {"final_target": target_time}
                )
                
                # Calculate ratio from target time
                denominator = target_time - formula_b
                if denominator > 0:
                    calculated_ratio = 32.0 / denominator
                    analyzer.add_calculation_step(
                        f"Calculated ratio: R = a/(T-b) = 32.0/({target_time:.3f} - {formula_b:.2f}) = {calculated_ratio:.6f}",
                        {"a": 32.0, "b": formula_b, "target_time": target_time, "calculated_ratio": calculated_ratio}
                    )
                    
                    # Check ratio limits
                    min_ratio, max_ratio = get_ratio_limits()
                    if min_ratio <= calculated_ratio <= max_ratio:
                        analyzer.add_range_check(
                            f"Ratio {calculated_ratio:.6f} is within allowed range ({min_ratio} - {max_ratio})",
                            {"in_range": True}
                        )
                        success = True
                        message = "Analysis complete - ratio within limits"
                    else:
                        analyzer.add_range_check(
                            f"Ratio {calculated_ratio:.6f} is OUTSIDE allowed range ({min_ratio} - {max_ratio})",
                            {"in_range": False, "min_ratio": min_ratio, "max_ratio": max_ratio}
                        )
                        success = False
                        message = f"Ratio {calculated_ratio:.6f} is outside allowed range"
                    
                    analyzer.set_result(target_time, calculated_ratio, calculated_ratio, success, message)
                else:
                    analyzer.add_error(
                        f"Cannot calculate ratio: T-b = {target_time:.3f} - {formula_b:.2f} = {denominator:.3f} (must be positive)",
                        {}
                    )
                    analyzer.set_result(target_time, None, None, False, "Cannot calculate ratio: T-b must be positive")
            else:
                analyzer.add_error(
                    f"Insufficient AI data for {session_type}",
                    {"best_ai": best_ai, "worst_ai": worst_ai}
                )
                analyzer.set_result(None, None, None, False, "Insufficient AI data - complete at least one race session")
            
            # Finalize and dump
            dump_path = analyzer.finalize_and_dump()
            
            QMessageBox.information(
                self, "Data Dump Complete", 
                f"Analysis dumped to:\n{dump_path}\n\n"
                f"Also saved to:\n{analyzer.dump_dir}/ai_target_log.csv"
            )
            
        except ImportError as e:
            QMessageBox.warning(self, "Error", f"AI Target Analyzer module not available: {e}")
        except Exception as e:
            import traceback
            traceback.print_exc()
            QMessageBox.warning(self, "Error", f"Failed to dump analysis: {e}")
    
    def scan_aiw_backups(self):
        """Scan for AIW backups - returns unique backups without duplicates"""
        backups = []
        seen_tracks = set()  # Track to prevent duplicates
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
                
                # Create a unique key to prevent duplicates
                unique_key = f"{track_name}_{original_name}"
                
                if unique_key not in seen_tracks:
                    seen_tracks.add(unique_key)
                    backups.append({
                        "track": track_name,
                        "original_file": original_name,
                        "backup_path": backup_file,
                        "backup_time": backup_file.stat().st_mtime if backup_file.exists() else 0,
                        "backup_dir": str(backup_dir)
                    })
        
        return sorted(backups, key=lambda x: x.get("track", ""))
    
    def refresh_backup_list(self):
        """Refresh the backup list - loads all unique backups"""
        self.backup_list.clear()
        backups = self.scan_aiw_backups()
        
        if not backups:
            item = QListWidgetItem("No backups found")
            item.setFlags(Qt.NoItemFlags)  # Make it non-selectable
            self.backup_list.addItem(item)
            return
        
        for backup in backups:
            time_str = datetime.fromtimestamp(backup["backup_time"]).strftime("%Y-%m-%d %H:%M:%S")
            item = QListWidgetItem(f"{backup['track']} - {backup['original_file']} (backup: {time_str})")
            item.setData(Qt.UserRole, backup)
            self.backup_list.addItem(item)

    def restore_aiw_backup(self, backup_info):
        """Restore AIW backup using consistent path finding"""
        try:
            backup_path = backup_info["backup_path"]
            original_name = backup_info["original_file"]
            track_name = backup_info["track"]
            restore_path = None
            
            # Use the same path finding method as the main application
            base_path = get_base_path()
            
            if base_path:
                locations_dir = base_path / "GameData" / "Locations"
                if locations_dir.exists():
                    # Search case-insensitively for the track folder
                    track_lower = track_name.lower()
                    for track_dir in locations_dir.iterdir():
                        if track_dir.is_dir() and track_dir.name.lower() == track_lower:
                            aiw_path = track_dir / original_name
                            if aiw_path.exists():
                                restore_path = aiw_path
                                break
                    
                    # If not found, search by filename
                    if not restore_path:
                        for ext in ["*.AIW", "*.aiw"]:
                            for aiw_file in locations_dir.rglob(ext):
                                if aiw_file.name.lower() == original_name.lower():
                                    restore_path = aiw_file
                                    break
            
            # If still not found, ask user for location
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
            logger.info(f"Restored backup to {restore_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error restoring backup: {e}")
            return False
    
    def restore_selected_backups(self):
        selected_items = self.backup_list.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "No Selection", "Please select backups to restore.")
            return
        reply = QMessageBox.question(self, "Confirm Restore", f"Restore {len(selected_items)} AIW file(s)?", QMessageBox.Yes | QMessageBox.No)
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
        reply = QMessageBox.question(self, "Confirm Restore All", f"Restore ALL {len(backups)} AIW backup(s)?", QMessageBox.Yes | QMessageBox.No)
        if reply != QMessageBox.Yes:
            return
        restored = 0
        for backup in backups:
            if self.restore_aiw_backup(backup):
                restored += 1
        if restored > 0:
            QMessageBox.information(self, "Restore Complete", f"Successfully restored {restored} AIW file(s).")
            self.refresh_backup_list()
    
    def on_lap_time_edited(self, session_type: str, new_time: float):
        self.lap_time_updated.emit(session_type, new_time)
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
            self.curve_graph.selected_point_marker = pg.ScatterPlotItem([ratio], [lap_time], brush=pg.mkBrush('#FFFFFF'), size=12, symbol='o', pen=pg.mkPen('#FF0000', width=2))
            self.curve_graph.plot.addItem(self.curve_graph.selected_point_marker)
    
    def delete_selected_points(self):
        selected_rows = set()
        for item in self.data_table.selectedItems():
            selected_rows.add(item.row())
        if not selected_rows:
            QMessageBox.warning(self, "No Selection", "Please select data points to delete.")
            return
        reply = QMessageBox.question(self, "Confirm Delete", f"Delete {len(selected_rows)} data point(s)?", QMessageBox.Yes | QMessageBox.No)
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
            cursor.execute("DELETE FROM data_points WHERE track = ? AND vehicle_class = ? AND ratio = ? AND lap_time = ? AND session_type = ?", (track, vehicle, ratio, lap_time, session_type))
            deleted += cursor.rowcount
        conn.commit()
        conn.close()
        self.refresh_all()
        QMessageBox.information(self, "Success", f"Deleted {deleted} data point(s).")
    
    def refresh_display(self):
        if not self.parent:
            return
        parent = self.parent() if callable(self.parent) else self.parent
        current_track = getattr(parent, 'current_track', None)
        current_vehicle = getattr(parent, 'current_vehicle', None)
        user_qual_time = getattr(parent, 'user_qualifying_sec', 0.0)
        user_race_time = getattr(parent, 'user_best_lap_sec', 0.0)
        qual_a = getattr(parent, 'qual_a', DEFAULT_A_VALUE)
        qual_b = getattr(parent, 'qual_b', 70.0)
        race_a = getattr(parent, 'race_a', DEFAULT_A_VALUE)
        race_b = getattr(parent, 'race_b', 70.0)
        last_qual_ratio = getattr(parent, 'last_qual_ratio', None)
        last_race_ratio = getattr(parent, 'last_race_ratio', None)
        
        if self.curve_graph:
            self.curve_graph.update_current_info(
                track=current_track, vehicle=current_vehicle,
                qual_time=user_qual_time if user_qual_time > 0 else None,
                race_time=user_race_time if user_race_time > 0 else None,
                qual_ratio=last_qual_ratio, race_ratio=last_race_ratio
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
        # Also update the graph's track and notify parent
        if self.curve_graph and self.curve_graph.current_track:
            self.track_selected.emit(self.curve_graph.current_track)
    
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
                self.curve_graph.user_qual_ratio = self.curve_graph._calculate_ratio_for_user_time(self.curve_graph.user_qual_time, "qual")
            if self.curve_graph.user_race_time and session_type == "race":
                self.curve_graph.user_race_ratio = self.curve_graph._calculate_ratio_for_user_time(self.curve_graph.user_race_time, "race")
            self.curve_graph.update_graph()
        self.formula_updated.emit(session_type, a, b)
    
    def on_show_data_toggled(self, session_type: str, show: bool):
        if self.curve_graph:
            if session_type == "qual":
                self.curve_graph.set_show_qualifying(show)
            else:
                self.curve_graph.set_show_race(show)
    
    def on_calculate_and_save_ratio(self, session_type: str, lap_time: float):
        """Calculate and save ratio - the save method already shows confirmation"""
        if session_type == "qual":
            a, b = self.qual_panel.a, self.qual_panel.b
        else:
            a, b = self.race_panel.a, self.race_panel.b
        
        denominator = lap_time - b
        if denominator <= 0:
            QMessageBox.warning(self, "Invalid Calculation", 
                f"Cannot calculate ratio: T - b = {lap_time:.3f} - {b:.2f} = {denominator:.3f} (must be positive)")
            return
        
        ratio = a / denominator
        if not (0.3 < ratio < 3.0):
            QMessageBox.warning(self, "Ratio Out of Range", 
                f"Calculated ratio {ratio:.6f} is outside valid range (0.3 - 3.0)")
            return
        
        min_ratio, max_ratio = get_ratio_limits()
        if ratio < min_ratio or ratio > max_ratio:
            reply = QMessageBox.question(self, "Ratio Out of Range", 
                f"The calculated {session_type.upper()} Ratio = {ratio:.6f} is outside the allowed range "
                f"({min_ratio} - {max_ratio}).\n\nContinue anyway?",
                QMessageBox.Yes | QMessageBox.No)
            if reply != QMessageBox.Yes:
                return
        
        # Save to AIW file - this method already shows its own confirmation dialog
        if self._save_ratio_to_aiw(session_type, ratio, lap_time):
            self.ratio_saved.emit(session_type, ratio)
            if self.curve_graph:
                if session_type == "qual":
                    self.curve_graph.user_qual_ratio = ratio
                else:
                    self.curve_graph.user_race_ratio = ratio
                self.curve_graph.update_graph()
            if self.parent:
                parent = self.parent() if callable(self.parent) else self.parent
                if session_type == "qual":
                    parent.last_qual_ratio = ratio
                    parent.qual_panel.update_ratio(ratio)
                else:
                    parent.last_race_ratio = ratio
                    parent.race_panel.update_ratio(ratio)
    
    def on_auto_fit_requested(self, session_type: str):
        if not self.curve_graph:
            return
        points_data = self.curve_graph.get_selected_data()
        if session_type == "qual":
            points = points_data.get('quali', [])
        else:
            points = points_data.get('race', [])
        if len(points) < 2:
            QMessageBox.warning(self, "Insufficient Data", f"Need at least 2 data points to auto-fit {session_type} formula. Found {len(points)} points.")
            return
        ratios = [p[0] for p in points]
        times = [p[1] for p in points]
        a, b, avg_err, max_err = fit_curve(ratios, times, verbose=False)
        if a and b and a > 0 and b > 0:
            b = b
            a = DEFAULT_A_VALUE
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
                    self.curve_graph.user_qual_ratio = self.curve_graph._calculate_ratio_for_user_time(self.curve_graph.user_qual_time, "qual")
                if self.curve_graph.user_race_time:
                    self.curve_graph.user_race_ratio = self.curve_graph._calculate_ratio_for_user_time(self.curve_graph.user_race_time, "race")
                self.curve_graph.update_graph()
            self.formula_updated.emit(session_type, a, b)
            if self.parent:
                parent = self.parent() if callable(self.parent) else self.parent
                if session_type == "qual":
                    parent.qual_b = b
                else:
                    parent.race_b = b
                parent.update_display()
            QMessageBox.information(self, "Auto-Fit Complete", f"Formula fitted to {len(points)} data points:\nT = {a:.4f} / R + {b:.4f}\nAverage error: {avg_err:.3f}s\nMax error: {max_err:.3f}s")
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
    
    def calculate_target_lap_time(self, best_ai: float, worst_ai: float, settings: dict) -> float:
        logger.info(f"[AI TARGET] calculate_target_lap_time: best={best_ai:.3f}, worst={worst_ai:.3f}")
        mode = settings.get("mode", "percentage")
        error_margin = settings.get("error_margin", 0.0)
        if mode == "percentage":
            pct = settings.get("percentage", 50) / 100.0
            target = best_ai + (worst_ai - best_ai) * pct
            logger.info(f"[AI TARGET] Percentage mode: {pct*100:.0f}% -> target={target:.3f}s")
        elif mode == "faster_than_best":
            offset = settings.get("offset_seconds", 0.0)
            target = best_ai + offset
            logger.info(f"[AI TARGET] Faster than best: offset={offset:.2f} -> target={target:.3f}s")
        else:
            offset = settings.get("offset_seconds", 0.0)
            target = worst_ai - offset
            logger.info(f"[AI TARGET] Slower than worst: offset={offset:.2f} -> target={target:.3f}s")
        target = target + error_margin
        logger.info(f"[AI TARGET] After error margin (+{error_margin:.2f}): {target:.3f}s")
        target = max(best_ai, min(worst_ai + error_margin, target))
        return target
    
    def calculate_new_ratio_for_target(self, target_time: float, session_type: str) -> Optional[float]:
        logger.info(f"[AI TARGET] calculate_new_ratio_for_target: target={target_time:.3f}s, session={session_type}")
        if session_type == "qual":
            if self.qual_panel:
                a, b = self.qual_panel.a, self.qual_panel.b
            else:
                a, b = DEFAULT_A_VALUE, 70.0
        else:
            if self.race_panel:
                a, b = self.race_panel.a, self.race_panel.b
            else:
                a, b = DEFAULT_A_VALUE, 70.0
        logger.info(f"[AI TARGET] Using formula: T = {a:.2f}/R + {b:.2f}")
        denominator = target_time - b
        if denominator <= 0:
            logger.warning(f"[AI TARGET] Denominator <= 0: {target_time:.3f} - {b:.2f} = {denominator:.3f}")
            return None
        ratio = a / denominator
        logger.info(f"[AI TARGET] Calculated ratio: {ratio:.6f}")
        return ratio if 0.3 < ratio < 3.0 else None
    
    def apply_target_settings(self):
        logger.info("=" * 60)
        logger.info("[AI TARGET] ========== APPLY AI TARGET SETTINGS ==========")
        logger.info("=" * 60)
        
        settings = {"mode": self.target_mode, "percentage": self.target_percentage,
                    "offset_seconds": self.target_offset_seconds, "error_margin": self.ai_error_margin}
        logger.info(f"[AI TARGET] Settings: mode={self.target_mode}, percentage={self.target_percentage}, offset={self.target_offset_seconds}, error_margin={self.ai_error_margin}")
        
        parent = self.parent() if callable(self.parent) else self.parent
        if parent:
            qual_best = getattr(parent, 'qual_best_ai', None)
            qual_worst = getattr(parent, 'qual_worst_ai', None)
            race_best = getattr(parent, 'race_best_ai', None)
            race_worst = getattr(parent, 'race_worst_ai', None)
        else:
            qual_best = qual_worst = race_best = race_worst = None
        logger.info(f"[AI TARGET] AI ranges: Qual={qual_best}-{qual_worst}, Race={race_best}-{race_worst}")
        
        if qual_best is None or qual_worst is None or race_best is None or race_worst is None:
            error_msg = "No AI lap time data available. Please complete at least one race session first."
            logger.error(f"[AI TARGET] {error_msg}")
            QMessageBox.warning(self, "No AI Data", error_msg)
            return
        
        qual_target = self.calculate_target_lap_time(qual_best, qual_worst, settings)
        race_target = self.calculate_target_lap_time(race_best, race_worst, settings)
        logger.info(f"[AI TARGET] Target times: Qual={qual_target:.3f}s, Race={race_target:.3f}s")
        
        qual_new_ratio = self.calculate_new_ratio_for_target(qual_target, "qual")
        race_new_ratio = self.calculate_new_ratio_for_target(race_target, "race")
        logger.info(f"[AI TARGET] New ratios: Qual={qual_new_ratio}, Race={race_new_ratio}")
        
        if not qual_new_ratio or not race_new_ratio:
            error_msg = "Could not calculate new ratios. Target times may be too close to formula b value."
            logger.error(f"[AI TARGET] {error_msg}")
            QMessageBox.warning(self, "Calculation Failed", error_msg)
            return
        
        min_ratio, max_ratio = get_ratio_limits()
        qual_ok = min_ratio <= qual_new_ratio <= max_ratio
        race_ok = min_ratio <= race_new_ratio <= max_ratio
        logger.info(f"[AI TARGET] Ratio limits check: Qual OK={qual_ok}, Race OK={race_ok}")
        
        confirm_msg = f"AI Target Settings Summary:\n\nQualifying:\n  AI Range: {qual_best:.3f}s - {qual_worst:.3f}s\n  Target: {qual_target:.3f}s\n  New QualRatio: {qual_new_ratio:.6f}\n\nRace:\n  AI Range: {race_best:.3f}s - {race_worst:.3f}s\n  Target: {race_target:.3f}s\n  New RaceRatio: {race_new_ratio:.6f}\n\nContinue?"
        
        reply = QMessageBox.question(self, "Apply AI Target Settings", confirm_msg, QMessageBox.Yes | QMessageBox.No)
        if reply != QMessageBox.Yes:
            logger.info("[AI TARGET] User cancelled")
            return
        
        aiw_path = None
        # Use the config-based path finder
        aiw_path = self._find_aiw_path_from_config()
        
        if not aiw_path:
            self._show_aiw_path_error()
            return
        
        engine = parent.autopilot_manager.engine if parent and hasattr(parent, 'autopilot_manager') else None
        logger.info(f"[AI TARGET] Engine available: {engine is not None}")
        
        if engine:
            qual_updated = engine._update_aiw_ratio(aiw_path, "QualRatio", qual_new_ratio)
            race_updated = engine._update_aiw_ratio(aiw_path, "RaceRatio", race_new_ratio)
            logger.info(f"[AI TARGET] Updates: Qual={qual_updated}, Race={race_updated}")
            
            if qual_updated or race_updated:
                if qual_updated and parent:
                    parent.last_qual_ratio = qual_new_ratio
                    parent.qual_panel.update_ratio(qual_new_ratio)
                if race_updated and parent:
                    parent.last_race_ratio = race_new_ratio
                    parent.race_panel.update_ratio(race_new_ratio)
                if parent and hasattr(parent, 'ai_target_settings'):
                    parent.ai_target_settings = settings
                if parent and hasattr(parent, 'update_target_display'):
                    parent.update_target_display()
                QMessageBox.information(self, "Settings Applied", f"AI Target settings applied!\nQualRatio: {qual_new_ratio:.6f}\nRaceRatio: {race_new_ratio:.6f}")
            else:
                logger.error("[AI TARGET] Failed to update AIW file")
                QMessageBox.warning(self, "Update Failed", "Failed to update AIW file with new ratios.")
        else:
            logger.error("[AI TARGET] No engine available")
            QMessageBox.warning(self, "Error", "Could not access autopilot engine.")


def setup_dark_theme(app):
    app.setStyle('Fusion')
    app.setStyleSheet("""
        QMainWindow, QWidget { background-color: #1e1e1e; }
        QLabel { color: white; }
        QGroupBox { color: #4CAF50; border: 2px solid #555; border-radius: 5px; margin-top: 8px; padding-top: 8px; }
        QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px 0 5px; }
        QListWidget { background-color: #2b2b2b; color: white; border: 1px solid #4CAF50; border-radius: 3px; outline: none; }
        QListWidget::item:selected { background-color: #4CAF50; color: white; }
        QListWidget::item:hover { background-color: #3c3c3c; }
        QDoubleSpinBox, QSpinBox { background-color: #3c3c3c; color: white; border: 1px solid #4CAF50; border-radius: 3px; padding: 4px; }
        QPushButton { background-color: #4CAF50; color: white; border: none; border-radius: 4px; padding: 6px 12px; font-weight: bold; }
        QPushButton:hover { background-color: #45a049; }
        QStatusBar { color: #888; }
        QComboBox { background-color: #3c3c3c; color: white; border: 1px solid #4CAF50; border-radius: 3px; padding: 4px; }
        QCheckBox { color: white; }
        QRadioButton { color: white; }
        QFrame { background-color: transparent; }
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
