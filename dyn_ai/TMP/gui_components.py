#!/usr/bin/env python3
"""
Reusable GUI Components for Live AI Tuner
Provides custom widgets used across multiple windows
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QGroupBox, QCheckBox, QDoubleSpinBox, QDialog,
    QMessageBox, QTextEdit, QComboBox, QSpinBox
)
from PyQt5.QtCore import Qt, pyqtSignal

from core_config import get_ratio_limits
from core_formula import DEFAULT_A_VALUE


class GTR2Logo(QLabel):
    """Custom GTR2 logo with gray GTR and red 2"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setText("GTR2")
        self.setStyleSheet("""
            QLabel {
                font-size: 40px;
                font-weight: bold;
                color: #888888;
            }
        """)
        self.setTextFormat(Qt.RichText)


class ToggleSwitch(QPushButton):
    """A toggle switch button that changes appearance based on state"""
    
    def __init__(self, text_on: str, text_off: str, parent=None):
        super().__init__(parent)
        self.text_on = text_on
        self.text_off = text_off
        self._checked = False
        self.setCheckable(True)
        self.clicked.connect(self._on_click)
        self._update_style()
        self.setMinimumHeight(36)
        self.setMinimumWidth(180)
    
    def _on_click(self):
        self._checked = not self._checked
        self._update_style()
    
    def _update_style(self):
        if self._checked:
            self.setText(self.text_on)
            self.setStyleSheet("""
                QPushButton {
                    background-color: #4CAF50;
                    color: white;
                    font-weight: bold;
                    padding: 8px 18px;
                    border: none;
                    border-radius: 4px;
                    font-size: 13px;
                }
                QPushButton:hover {
                    background-color: #45a049;
                }
            """)
        else:
            self.setText(self.text_off)
            self.setStyleSheet("""
                QPushButton {
                    background-color: #3c3c3c;
                    color: #aaa;
                    font-weight: bold;
                    padding: 8px 18px;
                    border: none;
                    border-radius: 4px;
                    font-size: 13px;
                }
                QPushButton:hover {
                    background-color: #4a4a4a;
                }
            """)
    
    def is_checked(self) -> bool:
        return self._checked
    
    def set_checked(self, checked: bool):
        self._checked = checked
        self.setChecked(checked)
        self._update_style()


class AccuracyIndicator(QLabel):
    """Visual indicator for formula accuracy with color coding"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignCenter)
        self.setMinimumWidth(150)
        self.setMinimumHeight(50)
        self.current_accuracy = 0
        self.confidence = 0
        self.data_points = 0
        self.outliers = 0
        self.setStyleSheet("""
            QLabel {
                background-color: #3c3c3c;
                border-radius: 8px;
                padding: 5px;
                font-family: monospace;
                font-size: 11px;
            }
        """)
        self.update_display()
    
    def set_accuracy(self, confidence: float, data_points_used: int, 
                     avg_error: float = None, max_error: float = None,
                     outliers: int = 0):
        self.data_points = data_points_used
        self.outliers = outliers
        
        if data_points_used == 0:
            base_accuracy = 0
            confidence_text = "No Data"
        elif data_points_used == 1:
            base_accuracy = 25
            confidence_text = "Single Point"
        elif data_points_used <= 3:
            base_accuracy = 50
            confidence_text = "Low Data"
        elif data_points_used <= 5:
            base_accuracy = 65
            confidence_text = "Fair"
        elif data_points_used <= 9:
            base_accuracy = 80
            confidence_text = "Good"
        else:
            base_accuracy = 90
            confidence_text = "High Data"
        
        if confidence > 0:
            confidence_bonus = min(10, int(confidence * 10))
        else:
            confidence_bonus = 0
        
        error_penalty = 0
        if avg_error is not None and avg_error > 0:
            error_penalty = min(10, int(avg_error * 10))
        
        outlier_penalty = min(20, outliers * 5)
        
        self.current_accuracy = base_accuracy + confidence_bonus - error_penalty - outlier_penalty
        self.current_accuracy = max(0, min(100, self.current_accuracy))
        
        self.confidence = confidence
        self.confidence_text = confidence_text
        
        if self.current_accuracy >= 80:
            color = "#4CAF50"
            bg_color = "#1a3a1a"
            bar_color = "#4CAF50"
        elif self.current_accuracy >= 60:
            color = "#FFC107"
            bg_color = "#3a3a1a"
            bar_color = "#FFC107"
        elif self.current_accuracy >= 40:
            color = "#FF9800"
            bg_color = "#3a2a1a"
            bar_color = "#FF9800"
        else:
            color = "#f44336"
            bg_color = "#3a1a1a"
            bar_color = "#f44336"
        
        outlier_text = f"! {outliers} outlier{'s' if outliers != 1 else ''}" if outliers > 0 else ""
        
        html = f"""
        <div style="text-align: center;">
            <div style="color: {color}; font-weight: bold; font-size: 12px;">
                ACCURACY: {self.current_accuracy}%
            </div>
            <div style="background-color: #2b2b2b; border-radius: 4px; height: 8px; margin: 4px 0;">
                <div style="background-color: {bar_color}; width: {self.current_accuracy}%; height: 8px; border-radius: 4px;"></div>
            </div>
            <div style="color: #aaa; font-size: 9px;">
                {confidence_text} ({data_points_used} point{'s' if data_points_used != 1 else ''})
                {outlier_text}
            </div>
        </div>
        """
        
        self.setStyleSheet(f"""
            QLabel {{
                background-color: {bg_color};
                border-radius: 8px;
                padding: 8px;
                font-family: monospace;
                font-size: 11px;
            }}
        """)
        self.setText(html)
    
    def update_display(self):
        self.set_accuracy(self.confidence, self.data_points, None, None, self.outliers)
