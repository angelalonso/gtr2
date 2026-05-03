#!/usr/bin/env python3
"""
Dialog windows for lightweight GUI
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QLineEdit, QPushButton, QFileDialog, QTextEdit
)
from PyQt5.QtCore import Qt
from pathlib import Path


class BasePathDialog(QDialog):
    """Dialog for selecting GTR2 base path"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.selected_path = None
        self.setup_ui()
    
    def setup_ui(self):
        self.setWindowTitle("Select GTR2 Installation")
        self.setFixedSize(500, 250)
        self.setModal(True)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        
        title = QLabel("GTR2 Installation Path")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #FFA500;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        desc = QLabel(
            "Select the root folder of your GTR2 installation.\n"
            "It should contain GameData and UserData directories."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #aaa;")
        desc.setAlignment(Qt.AlignCenter)
        layout.addWidget(desc)
        
        path_layout = QHBoxLayout()
        self.path_edit = QLineEdit()
        self.path_edit.setPlaceholderText("Select folder...")
        path_layout.addWidget(self.path_edit)
        
        self.browse_btn = QPushButton("Browse...")
        self.browse_btn.clicked.connect(self.browse)
        path_layout.addWidget(self.browse_btn)
        layout.addLayout(path_layout)
        
        self.info_label = QLabel("")
        self.info_label.setStyleSheet("color: #FFA500; font-size: 10px;")
        layout.addWidget(self.info_label)
        
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        
        ok_btn = QPushButton("OK")
        ok_btn.clicked.connect(self.accept_path)
        btn_layout.addWidget(ok_btn)
        
        layout.addLayout(btn_layout)
    
    def browse(self):
        directory = QFileDialog.getExistingDirectory(self, "Select GTR2 Folder")
        if directory:
            self.path_edit.setText(directory)
            self._validate(directory)
    
    def _validate(self, path: str) -> bool:
        p = Path(path)
        if not p.exists():
            self.info_label.setText("Path does not exist")
            return False
        
        if not (p / "GameData").exists():
            self.info_label.setText("GameData directory not found")
            return False
        
        if not (p / "UserData").exists():
            self.info_label.setText("UserData directory not found")
            return False
        
        self.info_label.setText("✓ Valid GTR2 installation")
        self.info_label.setStyleSheet("color: #4CAF50;")
        return True
    
    def accept_path(self):
        path = self.path_edit.text().strip()
        if path and self._validate(path):
            self.selected_path = Path(path)
            self.accept()


class LogWindow(QDialog):
    """Simple log viewer window"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Log Viewer")
        self.setGeometry(200, 200, 800, 400)
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
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
        
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.close)
        layout.addWidget(close_btn)
    
    def add_log(self, level: str, message: str):
        from datetime import datetime
        timestamp = datetime.now().strftime("%H:%M:%S")
        color = {"ERROR": "#f44336", "WARNING": "#ff9800", "INFO": "#4caf50"}.get(level, "#ffffff")
        html = f'<span style="color: {color};">[{timestamp}] [{level}] {message}</span>'
        self.log_text.append(html)
