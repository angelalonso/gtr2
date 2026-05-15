#!/usr/bin/env python3
"""
Shared GUI components and utilities for Dynamic AI
Provides common dialogs, styles, and reusable widgets
"""

import sys
import os
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, Callable

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QDialog, QPushButton,
    QMessageBox, QDialogButtonBox, QLineEdit, QGroupBox, QComboBox,
    QSpinBox, QCheckBox, QTextEdit
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

logger = logging.getLogger(__name__)


## def resource_path(relative_path: str) -> Path:
##     """Get absolute path to resource, works for dev and for PyInstaller"""
##     try:
##         # PyInstaller creates a temp folder and stores path in _MEIPASS
##         base_path = sys._MEIPASS
##     except Exception:
##         base_path = os.path.abspath(".")
##     
##     return Path(base_path) / relative_path


## def get_data_file_path(filename: str) -> Path:
##     """Get path to a data file (cfg.yml, vehicle_classes.json, etc.)"""
##     # First check the executable's directory (for user-editable files)
##     if getattr(sys, 'frozen', False):
##         exe_dir = Path(sys.executable).parent
##         exe_path = exe_dir / filename
##         if exe_path.exists():
##             return exe_path
##     
##     # Then check PyInstaller's _MEIPASS (for bundled files)
##     meipass_path = resource_path(filename)
##     if meipass_path.exists():
##         return meipass_path
##     
##     # Finally check current working directory (for development)
##     cwd_path = Path.cwd() / filename
##     if cwd_path.exists():
##         return cwd_path
##     
##     # Return the executable directory as default (will try to create there)
##     if getattr(sys, 'frozen', False):
##         return Path(sys.executable).parent / filename
##     return Path.cwd() / filename


class InfoMessageDialog(QDialog):
    """Information dialog about using the application"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
    
    def setup_ui(self):
        self.setWindowTitle("Dynamic AI - Getting Started")
        self.setFixedSize(600, 500)
        self.setModal(True)
        
        self.setStyleSheet("""
            QDialog {
                background-color: #1e1e1e;
            }
            QLabel {
                color: white;
            }
            QGroupBox {
                color: #4CAF50;
                border: 2px solid #555;
                border-radius: 5px;
                margin-top: 12px;
                padding-top: 12px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 12px 28px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(25, 25, 25, 25)
        
        title_label = QLabel("Dynamic AI - Ready to Go")
        title_label.setStyleSheet("font-size: 22px; font-weight: bold; color: #FFA500;")
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)
        
        layout.addSpacing(10)
        
        info_group = QGroupBox("What to do")
        info_layout = QVBoxLayout(info_group)
        
        info_text = QLabel(
            "1. LEAVE THIS APPLICATION RUNNING\n"
            "2. Launch GTR2 and start your race session\n\n"
            "TIPS:\n"
            " - Complete qualifying and the race normally\n"
            " - The application will detect your race results\n"
            " - AI ratios will be automatically calculated and applied\n"
            " - Each race makes the AI adapt to your pace."
        )
        info_text.setWordWrap(True)
        info_text.setStyleSheet("font-size: 13px; line-height: 1.8; font-weight: normal;")
        info_layout.addWidget(info_text)
        
        layout.addWidget(info_group)
        
        layout.addSpacing(20)
        
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        start_btn = QPushButton("Start Application")
        start_btn.clicked.connect(self.accept)
        button_layout.addWidget(start_btn)
        
        button_layout.addStretch()
        layout.addLayout(button_layout)
    
    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter:
            self.accept()
        else:
            super().keyPressEvent(event)


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


class LogWindow(QDialog):
    """Separate window for displaying logs on demand"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Dynamic AI - Log Viewer")
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
    def __init__(self, log_window):
        super().__init__()
        self.log_window = log_window
    
    def emit(self, record):
        try:
            level = record.levelname
            message = self.format(record)
            if self.log_window:
                self.log_window.add_log(level, message)
        except Exception:
            pass


def setup_dark_theme(app):
    """Apply dark theme styling to the application"""
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
        QTabWidget::pane { background-color: #2b2b2b; border: 1px solid #555; }
        QTabBar::tab { background-color: #3c3c3c; color: white; padding: 8px 12px; margin-right: 2px; }
        QTabBar::tab:selected { background-color: #4CAF50; }
        QTableWidget { background-color: #2b2b2b; color: white; alternate-background-color: #3c3c3c; gridline-color: #555; }
        QHeaderView::section { background-color: #3c3c3c; color: white; padding: 4px; }
        QTextEdit { background-color: #2b2b2b; color: white; border: 1px solid #555; border-radius: 4px; font-family: monospace; }
        QLineEdit { background-color: #3c3c3c; color: white; border: 1px solid #4CAF50; border-radius: 4px; padding: 6px; }
        QProgressBar { border: 1px solid #555; border-radius: 4px; text-align: center; color: white; }
        QProgressBar::chunk { background-color: #4CAF50; border-radius: 3px; }
        QSplitter::handle { background-color: #555; }
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
