#!/usr/bin/env python3
"""
Base path selection dialog for Live AI Tuner
"""

from pathlib import Path

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QMessageBox, QFileDialog
)
from PyQt5.QtCore import Qt


class BasePathSelectionDialog(QDialog):
    """Dialog to select GTR2 installation base path"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.selected_path = None
        self.setup_ui()
    
    def setup_ui(self):
        self.setWindowTitle("Select GTR2 Installation Path")
        self.setFixedSize(600, 300)
        self.setModal(True)
        
        self.setStyleSheet("""
            QDialog {
                background-color: #2b2b2b;
            }
            QLabel {
                color: white;
            }
            QLineEdit {
                background-color: #3c3c3c;
                color: white;
                border: 1px solid #4CAF50;
                border-radius: 4px;
                padding: 8px;
                font-size: 12px;
            }
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton#cancel {
                background-color: #f44336;
            }
            QPushButton#cancel:hover {
                background-color: #d32f2f;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(25, 25, 25, 25)
        
        title = QLabel("GTR2 Installation Path")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #FFA500;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        layout.addSpacing(10)
        
        desc = QLabel(
            "Please select the root folder of your GTR2 installation.\n\n"
            "This folder should contain the 'GameData' and 'UserData' directories.\n"
            "Example: C:\\GTR2 or /home/user/GTR2"
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #aaa; font-size: 12px;")
        desc.setAlignment(Qt.AlignCenter)
        layout.addWidget(desc)
        
        layout.addSpacing(10)
        
        path_layout = QHBoxLayout()
        path_layout.addWidget(QLabel("Path:"))
        
        self.path_edit = QLineEdit()
        self.path_edit.setPlaceholderText("Select or enter GTR2 installation path...")
        path_layout.addWidget(self.path_edit)
        
        self.browse_btn = QPushButton("Browse...")
        self.browse_btn.clicked.connect(self.browse_path)
        path_layout.addWidget(self.browse_btn)
        
        layout.addLayout(path_layout)
        
        self.validation_label = QLabel("")
        self.validation_label.setStyleSheet("color: #FFA500; font-size: 10px;")
        layout.addWidget(self.validation_label)
        
        layout.addSpacing(20)
        
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setObjectName("cancel")
        self.cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self.cancel_btn)
        
        self.ok_btn = QPushButton("OK")
        self.ok_btn.clicked.connect(self.accept_path)
        btn_layout.addWidget(self.ok_btn)
        
        layout.addLayout(btn_layout)
    
    def browse_path(self):
        directory = QFileDialog.getExistingDirectory(
            self, "Select GTR2 Installation Directory",
            str(Path.home()), QFileDialog.ShowDirsOnly
        )
        
        if directory:
            self.path_edit.setText(directory)
            self.validate_path(directory)
    
    def validate_path(self, path_str: str) -> bool:
        path = Path(path_str)
        
        if not path.exists():
            self.validation_label.setText("X Path does not exist")
            self.validation_label.setStyleSheet("color: #f44336; font-size: 10px;")
            return False
        
        game_data = path / "GameData"
        user_data = path / "UserData"
        
        if not game_data.exists():
            self.validation_label.setText("X GameData directory not found in this path")
            self.validation_label.setStyleSheet("color: #f44336; font-size: 10px;")
            return False
        
        if not user_data.exists():
            self.validation_label.setText("X UserData directory not found in this path")
            self.validation_label.setStyleSheet("color: #f44336; font-size: 10px;")
            return False
        
        log_results = user_data / "Log" / "Results"
        if not log_results.exists():
            self.validation_label.setText("! Log/Results directory not found (may be created later)")
            self.validation_label.setStyleSheet("color: #FFA500; font-size: 10px;")
        else:
            self.validation_label.setText("Valid GTR2 installation path")
            self.validation_label.setStyleSheet("color: #4CAF50; font-size: 10px;")
        
        return True
    
    def accept_path(self):
        path_str = self.path_edit.text().strip()
        
        if not path_str:
            self.validation_label.setText("X Please select a path")
            return
        
        if self.validate_path(path_str):
            self.selected_path = Path(path_str)
            self.accept()
        else:
            reply = QMessageBox.question(
                self, "Continue Anyway?",
                "The selected path does not appear to be a valid GTR2 installation.\n"
                "The application may not work correctly.\n\n"
                "Continue anyway?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                self.selected_path = Path(path_str)
                self.accept()
