#!/usr/bin/env python3
"""
UI setup for the main window
"""

from PyQt5.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton,
    QFrame, QStatusBar
)
from PyQt5.QtCore import Qt

from gui_common import GTR2Logo, ToggleSwitch
from gui_ratio_panel import RatioPanel


class MainWindowUI:
    """UI setup for the main window"""
    
    def __init__(self, main_window):
        self.main_window = main_window
    
    def setup_ui(self):
        central = QWidget()
        self.main_window.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setSpacing(25)
        main_layout.setContentsMargins(30, 30, 30, 30)
        
        top_section = QWidget()
        top_layout = QVBoxLayout(top_section)
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setSpacing(20)
        
        header_layout = QHBoxLayout()
        logo_label = GTR2Logo()
        header_layout.addWidget(logo_label)
        header_layout.addStretch()
        
        track_container = QWidget()
        track_container.setStyleSheet("""
            QWidget {
                background-color: #2b2b2b;
                border-radius: 8px;
                padding: 5px 10px;
            }
        """)
        track_container_layout = QHBoxLayout(track_container)
        track_container_layout.setContentsMargins(10, 5, 10, 5)
        
        track_label_title = QLabel("Track:")
        track_label_title.setStyleSheet("font-size: 14px; color: #888;")
        track_container_layout.addWidget(track_label_title)
        
        self.main_window.track_label = QLabel("- No Track Selected -")
        self.main_window.track_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #FFA500;")
        track_container_layout.addWidget(self.main_window.track_label)
        
        select_track_btn = QPushButton("Configure")
        select_track_btn.setStyleSheet("""
            QPushButton {
                background-color: #9C27B0;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 4px 12px;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #7B1FA2;
            }
        """)
        select_track_btn.clicked.connect(self.main_window.open_advanced_to_data_management)
        track_container_layout.addWidget(select_track_btn)
        
        header_layout.addWidget(track_container)
        header_layout.addStretch()
        header_layout.addSpacing(80)
        top_layout.addLayout(header_layout)
        
        car_class_container = QWidget()
        car_class_container.setStyleSheet("""
            QWidget {
                background-color: #2b2b2b;
                border-radius: 8px;
                padding: 5px 10px;
            }
        """)
        car_class_layout = QHBoxLayout(car_class_container)
        car_class_layout.setContentsMargins(10, 5, 10, 5)

        car_class_label_title = QLabel("Car Class:")
        car_class_label_title.setStyleSheet("font-size: 13px; color: #888;")
        car_class_layout.addWidget(car_class_label_title)

        self.main_window.car_class_label = QLabel("-")
        self.main_window.car_class_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #4CAF50;")
        car_class_layout.addWidget(self.main_window.car_class_label)
        car_class_layout.addStretch()

        top_layout.addWidget(car_class_container)
        
        panels_layout = QHBoxLayout()
        panels_layout.setSpacing(30)
        
        self.main_window.qual_panel = RatioPanel("Quali-Ratio", self.main_window)
        self.main_window.qual_panel.edit_complete.connect(lambda ratio: self.main_window.on_manual_edit("qual", ratio))
        panels_layout.addWidget(self.main_window.qual_panel)
        
        self.main_window.race_panel = RatioPanel("Race-Ratio", self.main_window)
        self.main_window.race_panel.edit_complete.connect(lambda ratio: self.main_window.on_manual_edit("race", ratio))
        panels_layout.addWidget(self.main_window.race_panel)
        
        top_layout.addLayout(panels_layout)
        
        main_layout.addWidget(top_section, stretch=1)
        
        bottom_section = QWidget()
        bottom_layout = QVBoxLayout(bottom_section)
        bottom_layout.setContentsMargins(0, 0, 0, 0)
        bottom_layout.setSpacing(20)
        
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(20)
        
        self.main_window.autosave_switch = ToggleSwitch("Auto-harvest Data (ON)", "Auto-harvest Data (OFF)")
        self.main_window.autosave_switch.set_checked(self.main_window.autosave_enabled)
        self.main_window.autosave_switch.clicked.connect(self.main_window.toggle_autosave)
        buttons_layout.addWidget(self.main_window.autosave_switch)
        
        self.main_window.autoratio_switch = ToggleSwitch("Auto-calculate Ratios (ON)", "Auto-calculate Ratios (OFF)")
        self.main_window.autoratio_switch.set_checked(self.main_window.autoratio_enabled)
        self.main_window.autoratio_switch.clicked.connect(self.main_window.toggle_autoratio)
        buttons_layout.addWidget(self.main_window.autoratio_switch)
        
        buttons_layout.addStretch()
        
        advanced_btn = QPushButton("Advanced")
        advanced_btn.setMinimumHeight(36)
        advanced_btn.setMinimumWidth(100)
        advanced_btn.setStyleSheet("""
            QPushButton {
                background-color: #9C27B0;
                color: white;
                padding: 8px 24px;
                border: none;
                border-radius: 4px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #7B1FA2;
            }
        """)
        advanced_btn.clicked.connect(self.main_window.open_advanced_settings)
        buttons_layout.addWidget(advanced_btn)
        
        exit_btn = QPushButton("Exit")
        exit_btn.setMinimumHeight(36)
        exit_btn.setMinimumWidth(100)
        exit_btn.setStyleSheet("""
            QPushButton {
                background-color: #555;
                color: white;
                padding: 8px 24px;
                border: none;
                border-radius: 4px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #666;
            }
        """)
        exit_btn.clicked.connect(self.main_window.close)
        buttons_layout.addWidget(exit_btn)
        
        bottom_layout.addLayout(buttons_layout)
        
        main_layout.addWidget(bottom_section, stretch=0)
        
        self.main_window.statusBar().showMessage("Ready")
        self.main_window.statusBar().setStyleSheet("QStatusBar { color: #888; }")
        
        self.main_window.setStyleSheet("""
            QMainWindow { background-color: #1e1e1e; }
            QLabel { color: white; }
        """)
