#!/usr/bin/env python3
"""
Ratio Panel component for Live AI Tuner
Provides the ratio display panel for qualifying and race
"""

from PyQt5.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QMessageBox, QDialog
)
from PyQt5.QtCore import Qt, pyqtSignal

from core_config import get_ratio_limits
from core_data_extraction import format_time
from gui_common_dialogs import ManualEditDialog
from gui_components import AccuracyIndicator


class RatioPanel(QFrame):
    """Panel for displaying Qualifying or Race ratio information with accuracy indicator and edit button"""
    
    edit_complete = pyqtSignal(float)
    revert_requested = pyqtSignal()
    
    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.title = title
        self.current_ratio = None
        self.last_read_ratio = None
        self.previous_ratio = None
        self.calc_button_modified = False
        self.parent_window = parent
        self.setup_ui()
        
    def setup_ui(self):
        self.setFrameStyle(QFrame.NoFrame)
        self.setStyleSheet("""
            QFrame {
                background-color: #2b2b2b;
                border-radius: 10px;
            }
            QLabel {
                color: white;
            }
            QPushButton#edit_btn {
                background-color: #2196F3;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 6px 12px;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton#edit_btn:hover {
                background-color: #1976D2;
            }
            QPushButton#edit_btn:disabled {
                background-color: #555;
                color: #888;
            }
            QPushButton#revert_btn {
                background-color: #FF9800;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 6px 12px;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton#revert_btn:hover {
                background-color: #F57C00;
            }
            QPushButton#revert_btn:disabled {
                background-color: #555;
                color: #888;
            }
        """)
        
        self.setMinimumHeight(380)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(25, 25, 25, 25)
        
        self.title_layout = QHBoxLayout()
        
        self.title_label = QLabel(self.title)
        self.title_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #aaa;")
        self.title_label.setAlignment(Qt.AlignCenter)
        self.title_layout.addWidget(self.title_label, stretch=1)
        
        self.revert_btn = QPushButton("Revert")
        self.revert_btn.setObjectName("revert_btn")
        self.revert_btn.setFixedSize(70, 28)
        self.revert_btn.setEnabled(False)
        self.revert_btn.clicked.connect(self.on_revert_clicked)
        self.title_layout.addWidget(self.revert_btn)
        
        self.edit_btn = QPushButton("Edit")
        self.edit_btn.setObjectName("edit_btn")
        self.edit_btn.setFixedSize(70, 28)
        self.edit_btn.clicked.connect(self.on_edit_clicked)
        self.title_layout.addWidget(self.edit_btn)
        
        layout.addLayout(self.title_layout)
        
        layout.addSpacing(10)
        
        ratio_label = QLabel("Current Ratio:")
        ratio_label.setStyleSheet("font-size: 11px; color: #888;")
        layout.addWidget(ratio_label)
        
        self.ratio_label = QLabel("-")
        self.ratio_label.setStyleSheet("font-size: 38px; font-weight: bold; font-family: monospace; color: #FFA500;")
        self.ratio_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.ratio_label)
        
        self.last_read_label = QLabel("last ratio read: --")
        self.last_read_label.setStyleSheet("font-size: 10px; color: #666; font-family: monospace; margin-top: -5px;")
        self.last_read_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.last_read_label)
        
        layout.addSpacing(15)
        
        expected_label = QLabel("Expected Best Laptimes:")
        expected_label.setStyleSheet("font-size: 12px; color: #888;")
        layout.addWidget(expected_label)
        
        self.ai_range_label = QLabel("AI: -- - --")
        self.ai_range_label.setStyleSheet("font-size: 15px; font-family: monospace; color: #FFA500;")
        layout.addWidget(self.ai_range_label)
        
        layout.addSpacing(10)
        
        self.user_time_label = QLabel("User: --")
        self.user_time_label.setStyleSheet("font-size: 15px; font-family: monospace; color: #4CAF50; font-weight: bold;")
        layout.addWidget(self.user_time_label)
        
        layout.addStretch()
        
        self.formula_label = QLabel("")
        self.formula_label.setStyleSheet("color: #888; font-size: 10px; font-family: monospace; margin-top: 10px;")
        self.formula_label.setWordWrap(True)
        self.formula_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.formula_label)
        
        self.accuracy_indicator = AccuracyIndicator()
        layout.addWidget(self.accuracy_indicator)
    
    def update_ratio(self, ratio: float):
        if ratio is not None and self.current_ratio is not None and ratio != self.current_ratio:
            self.previous_ratio = self.current_ratio
            self.revert_btn.setEnabled(True)
        self.current_ratio = ratio
        if ratio is not None:
            self.ratio_label.setText(f"{ratio:.6f}")
        else:
            self.ratio_label.setText("-")
    
    def update_last_read_ratio(self, ratio: float):
        self.last_read_ratio = ratio
        if ratio is not None:
            self.last_read_label.setText(f"last ratio read: {ratio:.6f}")
            self.last_read_label.setStyleSheet("font-size: 10px; color: #FFA500; font-family: monospace; margin-top: -5px;")
        else:
            self.last_read_label.setText("last ratio read: --")
            self.last_read_label.setStyleSheet("font-size: 10px; color: #666; font-family: monospace; margin-top: -5px;")
    
    def update_ai_range(self, best: float, worst: float):
        if best is not None and worst is not None:
            self.ai_range_label.setText(f"AI: {format_time(best)} - {format_time(worst)}")
        else:
            self.ai_range_label.setText("AI: -- - --")
    
    def update_user_time(self, time_sec: float):
        if time_sec is not None and time_sec > 0:
            self.user_time_label.setText(f"User: {format_time(time_sec)}")
        else:
            self.user_time_label.setText("User: --")
    
    def update_formula(self, a: float, b: float):
        self.formula_label.setText(f"T = {a:.2f} / R + {b:.2f}")
    
    def update_accuracy(self, confidence: float, data_points_used: int, 
                        avg_error: float = None, max_error: float = None,
                        outliers: int = 0):
        self.accuracy_indicator.set_accuracy(confidence, data_points_used, 
                                             avg_error, max_error, outliers)
    
    def set_edit_enabled(self, enabled: bool):
        self.edit_btn.setEnabled(enabled)
    
    def on_edit_clicked(self):
        if self.current_ratio is None:
            if self.parent_window and hasattr(self.parent_window, 'load_aiw_ratios'):
                self.parent_window.load_aiw_ratios()
            if self.current_ratio is None:
                QMessageBox.warning(self, "No Ratio", f"No {self.title} value available to edit. Please select a track or run a race session first.")
                return
        min_ratio, max_ratio = get_ratio_limits()
        dialog = ManualEditDialog(self, self.title, self.current_ratio, None, min_ratio, max_ratio)
        if dialog.exec_() == QDialog.Accepted and dialog.new_ratio is not None:
            self.edit_complete.emit(dialog.new_ratio)
    
    def on_revert_clicked(self):
        if self.previous_ratio is not None:
            self.revert_requested.emit()
    
    def revert_success(self):
        self.previous_ratio = None
        self.revert_btn.setEnabled(False)
    
    def set_calc_button_orange(self, is_orange: bool):
        self.calc_button_modified = is_orange
