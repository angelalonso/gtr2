#!/usr/bin/env python3
"""
Reusable widgets for lightweight GUI
"""

from PyQt5.QtWidgets import QPushButton, QLabel, QFrame, QVBoxLayout
from PyQt5.QtCore import Qt


class ToggleSwitch(QPushButton):
    """Simple toggle switch button"""
    
    def __init__(self, text_on: str, text_off: str, parent=None):
        super().__init__(parent)
        self.text_on = text_on
        self.text_off = text_off
        self._checked = False
        self.setCheckable(True)
        self.clicked.connect(self._toggle)
        self._update_style()
        self.setMinimumHeight(32)
        self.setMinimumWidth(160)
    
    def _toggle(self):
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
                    padding: 6px 12px;
                    border: none;
                    border-radius: 3px;
                }
            """)
        else:
            self.setText(self.text_off)
            self.setStyleSheet("""
                QPushButton {
                    background-color: #3c3c3c;
                    color: #aaa;
                    font-weight: bold;
                    padding: 6px 12px;
                    border: none;
                    border-radius: 3px;
                }
            """)
    
    def is_checked(self) -> bool:
        return self._checked
    
    def set_checked(self, checked: bool):
        self._checked = checked
        self._update_style()


class RatioDisplay(QLabel):
    """Styled ratio display widget"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignCenter)
        self.setStyleSheet("""
            QLabel {
                font-size: 32px;
                font-weight: bold;
                font-family: monospace;
                color: #FFA500;
                background-color: #2b2b2b;
                border-radius: 8px;
                padding: 10px;
            }
        """)
        self.setText("-")
    
    def update_ratio(self, ratio: float = None):
        if ratio is not None:
            self.setText(f"{ratio:.6f}")
        else:
            self.setText("-")


class InfoCard(QFrame):
    """Card-style info panel"""
    
    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.setFrameStyle(QFrame.NoFrame)
        self.setStyleSheet("""
            QFrame {
                background-color: #2b2b2b;
                border-radius: 8px;
                padding: 10px;
            }
        """)
        
        layout = QVBoxLayout(self)
        
        self.title_label = QLabel(title)
        self.title_label.setStyleSheet("color: #888; font-size: 11px;")
        layout.addWidget(self.title_label)
        
        self.value_label = QLabel("-")
        self.value_label.setStyleSheet("color: #4CAF50; font-size: 14px; font-family: monospace;")
        layout.addWidget(self.value_label)
    
    def set_value(self, value):
        self.value_label.setText(str(value))
