#!/usr/bin/env python3
"""
Log window for Live AI Tuner
Provides a separate window for displaying application logs
"""

from datetime import datetime
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QComboBox, QSpinBox, QCheckBox
)
from PyQt5.QtCore import Qt


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
