#!/usr/bin/env python3
"""
Session Panel component for Live AI Tuner
Provides the qualifying and race session control panels
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGroupBox, QCheckBox, QDoubleSpinBox, QMessageBox, QDialog
)
from PyQt5.QtCore import Qt, pyqtSignal

from core_config import get_ratio_limits
from core_formula import DEFAULT_A_VALUE
from gui_common_dialogs import ManualLapTimeDialog


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
        self.median_time = None
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
            QLabel#median_label {
                color: #FFA500;
                font-family: monospace;
                font-size: 11px;
                font-weight: bold;
            }
        """)
        
        group = QGroupBox(self.title)
        group_layout = QVBoxLayout(group)
        group_layout.setSpacing(4)
        group_layout.setContentsMargins(8, 8, 8, 8)

        row1 = QHBoxLayout()
        self.show_checkbox = QCheckBox("Show on graph")
        self.show_checkbox.setChecked(True)
        self.show_checkbox.setStyleSheet("color: #4CAF50; font-weight: bold;")
        self.show_checkbox.toggled.connect(self.on_show_toggled)
        row1.addWidget(self.show_checkbox)

        row1.addSpacing(12)
        row1.addWidget(QLabel("Latest Time:"))
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
        
        row1.addSpacing(12)
        row1.addWidget(QLabel("Median:"))
        self.median_label = QLabel("--")
        self.median_label.setObjectName("median_label")
        row1.addWidget(self.median_label)
        
        row1.addStretch()
        group_layout.addLayout(row1)

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
    
    def update_median_time(self, median_time: float):
        """Update the displayed median time"""
        self.median_time = median_time
        if median_time is not None and median_time > 0:
            minutes = int(median_time) // 60
            seconds = median_time % 60
            self.median_label.setText(f"{minutes}:{seconds:06.3f}")
        else:
            self.median_label.setText("--")
    
    def on_edit_time_clicked(self):
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
    
    def on_calculate_ratio(self):
        if self.user_time and self.user_time > 0:
            denominator = self.user_time - self.b
            if denominator <= 0:
                QMessageBox.warning(self, "Invalid Calculation", 
                    f"Cannot calculate ratio: T - b = {self.user_time:.3f} - {self.b:.2f} = {denominator:.3f} (must be positive)")
                return
            
            ratio = self.a / denominator
            
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
            
            self.calculate_ratio.emit(self.session_type, self.user_time)
            self.set_calc_button_modified(False)
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
