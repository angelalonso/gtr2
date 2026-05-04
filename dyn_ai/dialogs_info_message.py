#!/usr/bin/env python3
"""
Info message dialog (currently not used - info is now in pre-run check screen)
Kept for compatibility but not called.
"""

from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QGroupBox
from PyQt5.QtCore import Qt


class InfoMessageDialog(QDialog):
    """Dialog showing information message about using the application"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
    
    def setup_ui(self):
        self.setWindowTitle("Live AI Tuner - Getting Started")
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
        
        title_label = QLabel("Live AI Tuner - Ready to Go")
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
