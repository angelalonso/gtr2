#!/usr/bin/env python3
"""
Vehicle Classes tab for Dyn AI Data Manager
"""

from pathlib import Path

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QMessageBox
)
from PyQt5.QtCore import Qt

from gui_vehicle_manager import launch_vehicle_manager
from core_config import get_base_path


class VehicleTab(QWidget):
    """Vehicle Classes tab"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        info_label = QLabel(
            "Vehicle Classes Management\n\n"
            "This defines which vehicles belong to which class for AI tuning.\n"
            "Click the button below to open the Vehicle Manager dialog."
        )
        info_label.setStyleSheet("color: #FFA500; background-color: #2b2b2b; padding: 15px; border-radius: 5px;")
        info_label.setWordWrap(True)
        info_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(info_label)
        
        layout.addSpacing(30)
        
        open_manager_btn = QPushButton("Open Vehicle Manager")
        open_manager_btn.setStyleSheet("""
            QPushButton {
                background-color: #9C27B0;
                color: white;
                padding: 15px 30px;
                font-size: 16px;
                font-weight: bold;
                border-radius: 8px;
            }
            QPushButton:hover {
                background-color: #7B1FA2;
            }
        """)
        open_manager_btn.clicked.connect(self.open_vehicle_manager)
        
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_layout.addWidget(open_manager_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        
        layout.addStretch()
    
    def open_vehicle_manager(self):
        base_path = get_base_path()
        gtr2_path = base_path if base_path and base_path.exists() else None
        launch_vehicle_manager(gtr2_path, self)
