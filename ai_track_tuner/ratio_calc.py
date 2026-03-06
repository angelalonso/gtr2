#!/usr/bin/env python3
"""
Ratio Calculator Dialog for AIW Ratio Editor
Allows calculating QualRatio and RaceRatio based on lap times
"""

from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
import re


class TimeSpinBox(QWidget):
    """Custom widget for time input in mm:ss.xxx format with separate fields"""
    
    timeChanged = pyqtSignal(float)  # Emits total seconds as float
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.total_seconds = 0.0
        self.setup_ui()
        
    def setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        
        # Minutes
        self.minutes_spin = QSpinBox()
        self.minutes_spin.setRange(0, 99)
        self.minutes_spin.setValue(0)
        self.minutes_spin.setFixedHeight(40)
        self.minutes_spin.setFixedWidth(70)
        self.minutes_spin.setAlignment(Qt.AlignRight)
        self.minutes_spin.setStyleSheet("""
            QSpinBox {
                background-color: #3c3c3c;
                color: #ffffff;
                border: 2px solid #4CAF50;
                border-radius: 4px;
                padding: 8px 4px;
                font-family: 'Segoe UI', 'Arial', sans-serif;
                font-size: 16px;
                font-weight: bold;
            }
            QSpinBox:hover {
                border-color: #45a049;
            }
            QSpinBox:focus {
                border-color: #9C27B0;
            }
            QSpinBox::up-button, QSpinBox::down-button {
                width: 20px;
                height: 15px;
            }
        """)
        self.minutes_spin.valueChanged.connect(self.update_total_seconds)
        layout.addWidget(self.minutes_spin)
        
        # Minutes label
        min_label = QLabel("min")
        min_label.setStyleSheet("color: #888; font-size: 12px;")
        min_label.setFixedWidth(30)
        layout.addWidget(min_label)
        
        # First separator
        colon_label = QLabel(":")
        colon_label.setStyleSheet("color: #4CAF50; font-size: 20px; font-weight: bold;")
        colon_label.setFixedWidth(15)
        colon_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(colon_label)
        
        # Seconds
        self.seconds_spin = QSpinBox()
        self.seconds_spin.setRange(0, 59)
        self.seconds_spin.setValue(0)
        self.seconds_spin.setFixedHeight(40)
        self.seconds_spin.setFixedWidth(60)
        self.seconds_spin.setAlignment(Qt.AlignRight)
        self.seconds_spin.setStyleSheet("""
            QSpinBox {
                background-color: #3c3c3c;
                color: #ffffff;
                border: 2px solid #4CAF50;
                border-radius: 4px;
                padding: 8px 4px;
                font-family: 'Segoe UI', 'Arial', sans-serif;
                font-size: 16px;
                font-weight: bold;
            }
            QSpinBox:hover {
                border-color: #45a049;
            }
            QSpinBox:focus {
                border-color: #9C27B0;
            }
            QSpinBox::up-button, QSpinBox::down-button {
                width: 20px;
                height: 15px;
            }
        """)
        self.seconds_spin.valueChanged.connect(self.update_total_seconds)
        layout.addWidget(self.seconds_spin)
        
        # Seconds label
        sec_label = QLabel("sec")
        sec_label.setStyleSheet("color: #888; font-size: 12px;")
        sec_label.setFixedWidth(30)
        layout.addWidget(sec_label)
        
        # Decimal separator
        dot_label = QLabel(".")
        dot_label.setStyleSheet("color: #4CAF50; font-size: 20px; font-weight: bold;")
        dot_label.setFixedWidth(15)
        dot_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(dot_label)
        
        # Milliseconds
        self.milliseconds_spin = QSpinBox()
        self.milliseconds_spin.setRange(0, 999)
        self.milliseconds_spin.setValue(0)
        self.milliseconds_spin.setFixedHeight(40)
        self.milliseconds_spin.setFixedWidth(70)
        self.milliseconds_spin.setAlignment(Qt.AlignRight)
        self.milliseconds_spin.setStyleSheet("""
            QSpinBox {
                background-color: #3c3c3c;
                color: #ffffff;
                border: 2px solid #4CAF50;
                border-radius: 4px;
                padding: 8px 4px;
                font-family: 'Segoe UI', 'Arial', sans-serif;
                font-size: 16px;
                font-weight: bold;
            }
            QSpinBox:hover {
                border-color: #45a049;
            }
            QSpinBox:focus {
                border-color: #9C27B0;
            }
            QSpinBox::up-button, QSpinBox::down-button {
                width: 20px;
                height: 15px;
            }
        """)
        self.milliseconds_spin.setSingleStep(10)  # Step by 10ms for quicker entry
        self.milliseconds_spin.valueChanged.connect(self.update_total_seconds)
        layout.addWidget(self.milliseconds_spin)
        
        # Milliseconds label
        ms_label = QLabel("ms")
        ms_label.setStyleSheet("color: #888; font-size: 12px;")
        ms_label.setFixedWidth(30)
        layout.addWidget(ms_label)
        
        layout.addStretch()
    
    def update_total_seconds(self):
        """Update total seconds and emit signal"""
        self.total_seconds = (self.minutes_spin.value() * 60 + 
                              self.seconds_spin.value() + 
                              self.milliseconds_spin.value() / 1000.0)
        self.timeChanged.emit(self.total_seconds)
    
    def set_time_from_seconds(self, seconds):
        """Set the time from total seconds"""
        total_seconds = max(0, seconds)
        minutes = int(total_seconds) // 60
        secs = int(total_seconds) % 60
        ms = int((total_seconds - int(total_seconds)) * 1000)
        
        # Block signals to avoid recursion
        self.minutes_spin.blockSignals(True)
        self.seconds_spin.blockSignals(True)
        self.milliseconds_spin.blockSignals(True)
        
        self.minutes_spin.setValue(minutes)
        self.seconds_spin.setValue(secs)
        self.milliseconds_spin.setValue(ms)
        
        self.minutes_spin.blockSignals(False)
        self.seconds_spin.blockSignals(False)
        self.milliseconds_spin.blockSignals(False)
        
        self.total_seconds = total_seconds
        self.timeChanged.emit(total_seconds)
    
    def get_seconds(self):
        """Get total seconds as float"""
        return self.total_seconds
    
    def setValue(self, seconds):
        """Set value from total seconds (compatibility method)"""
        self.set_time_from_seconds(seconds)
    
    def value(self):
        """Get value in total seconds (compatibility method)"""
        return self.get_seconds()
    
    def focusNextPrevChild(self, next):
        """Handle tab navigation between fields"""
        if self.minutes_spin.hasFocus():
            self.seconds_spin.setFocus()
            return True
        elif self.seconds_spin.hasFocus():
            self.milliseconds_spin.setFocus()
            return True
        elif self.milliseconds_spin.hasFocus():
            # Move to next widget in the parent
            return super().focusNextPrevChild(next)
        return super().focusNextPrevChild(next)


class RatioCalculatorDialog(QDialog):
    """Dialog for calculating QualRatio and RaceRatio from lap times"""
    
    def __init__(self, parent=None, track_name="", current_qual=1.0, current_race=1.0):
        super().__init__(parent)
        self.track_name = track_name
        self.current_qual = current_qual
        self.current_race = current_race
        self.new_qual = current_qual
        self.new_race = current_race
        self.setup_ui()
        
    def setup_ui(self):
        self.setWindowTitle(f"UNDER DEVELOPMENT - Ratio Calculator - {self.track_name}")
        self.setModal(True)
        self.setMinimumWidth(850)
        self.setMinimumHeight(750)
        
        self.apply_dark_theme()
        
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Title
        title_label = QLabel(f"<h2>UNDER DEVELOPMENT! Ratio Calculator</h2><h3>{self.track_name}</h3>")
        title_label.setTextFormat(Qt.RichText)
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)
        
        # Current values section (editable)
        current_group = QGroupBox("Current Values (editable)")
        current_group.setMinimumHeight(120)
        current_layout = QGridLayout(current_group)
        current_layout.setVerticalSpacing(15)
        current_layout.setHorizontalSpacing(20)
        
        current_layout.addWidget(QLabel("QualRatio:"), 0, 0)
        self.current_qual_edit = QDoubleSpinBox()
        self.current_qual_edit.setRange(0.1, 10.0)
        self.current_qual_edit.setDecimals(6)
        self.current_qual_edit.setSingleStep(0.1)
        self.current_qual_edit.setValue(self.current_qual)
        self.current_qual_edit.setAlignment(Qt.AlignRight)
        self.current_qual_edit.setFixedHeight(40)
        self.current_qual_edit.setMinimumWidth(250)
        self.current_qual_edit.valueChanged.connect(self.on_current_qual_changed)
        self.current_qual_edit.setStyleSheet("""
            QDoubleSpinBox {
                background-color: #3c3c3c;
                color: #ffffff;
                border: 2px solid #4CAF50;
                border-radius: 4px;
                padding: 8px;
                font-family: 'Segoe UI', 'Arial', sans-serif;
                font-size: 14px;
                font-weight: bold;
            }
        """)
        current_layout.addWidget(self.current_qual_edit, 0, 1)
        
        current_layout.addWidget(QLabel("RaceRatio:"), 1, 0)
        self.current_race_edit = QDoubleSpinBox()
        self.current_race_edit.setRange(0.1, 10.0)
        self.current_race_edit.setDecimals(6)
        self.current_race_edit.setSingleStep(0.1)
        self.current_race_edit.setValue(self.current_race)
        self.current_race_edit.setAlignment(Qt.AlignRight)
        self.current_race_edit.setFixedHeight(40)
        self.current_race_edit.setMinimumWidth(250)
        self.current_race_edit.valueChanged.connect(self.on_current_race_changed)
        self.current_race_edit.setStyleSheet("""
            QDoubleSpinBox {
                background-color: #3c3c3c;
                color: #ffffff;
                border: 2px solid #4CAF50;
                border-radius: 4px;
                padding: 8px;
                font-family: 'Segoe UI', 'Arial', sans-serif;
                font-size: 14px;
                font-weight: bold;
            }
        """)
        current_layout.addWidget(self.current_race_edit, 1, 1)
        
        layout.addWidget(current_group)
        
        # Qualifying section
        qual_group = QGroupBox("Qualifying Lap Times (mm:ss.ms)")
        qual_group.setMinimumHeight(200)
        qual_layout = QGridLayout(qual_group)
        qual_layout.setVerticalSpacing(15)
        qual_layout.setHorizontalSpacing(20)
        
        # Labels with bold font
        pole_label = QLabel("Pole position:")
        pole_label.setStyleSheet("font-weight: bold; font-size: 13px;")
        qual_layout.addWidget(pole_label, 0, 0)
        
        self.qual_pole = TimeSpinBox()
        self.qual_pole.timeChanged.connect(self.check_calc_button)
        qual_layout.addWidget(self.qual_pole, 0, 1)
        
        last_ai_label = QLabel("Last AI:")
        last_ai_label.setStyleSheet("font-weight: bold; font-size: 13px;")
        qual_layout.addWidget(last_ai_label, 1, 0)
        
        self.qual_last_ai = TimeSpinBox()
        self.qual_last_ai.timeChanged.connect(self.check_calc_button)
        qual_layout.addWidget(self.qual_last_ai, 1, 1)
        
        player_label = QLabel("Your best:")
        player_label.setStyleSheet("font-weight: bold; font-size: 13px;")
        qual_layout.addWidget(player_label, 2, 0)
        
        self.qual_player = TimeSpinBox()
        self.qual_player.timeChanged.connect(self.check_calc_button)
        qual_layout.addWidget(self.qual_player, 2, 1)
        
        # Quick tips
        tip_label = QLabel("Tip: Use Tab key to navigate between min, sec, ms fields")
        tip_label.setStyleSheet("color: #888; font-style: italic; font-size: 11px;")
        qual_layout.addWidget(tip_label, 3, 0, 1, 2)
        
        layout.addWidget(qual_group)
        
        # Race section
        race_group = QGroupBox("Race Lap Times (mm:ss.ms)")
        race_group.setMinimumHeight(200)
        race_layout = QGridLayout(race_group)
        race_layout.setVerticalSpacing(15)
        race_layout.setHorizontalSpacing(20)
        
        pole_label = QLabel("Pole position:")
        pole_label.setStyleSheet("font-weight: bold; font-size: 13px;")
        race_layout.addWidget(pole_label, 0, 0)
        
        self.race_pole = TimeSpinBox()
        self.race_pole.timeChanged.connect(self.check_calc_button)
        race_layout.addWidget(self.race_pole, 0, 1)
        
        last_ai_label = QLabel("Last AI:")
        last_ai_label.setStyleSheet("font-weight: bold; font-size: 13px;")
        race_layout.addWidget(last_ai_label, 1, 0)
        
        self.race_last_ai = TimeSpinBox()
        self.race_last_ai.timeChanged.connect(self.check_calc_button)
        race_layout.addWidget(self.race_last_ai, 1, 1)
        
        player_label = QLabel("Your best:")
        player_label.setStyleSheet("font-weight: bold; font-size: 13px;")
        race_layout.addWidget(player_label, 2, 0)
        
        self.race_player = TimeSpinBox()
        self.race_player.timeChanged.connect(self.check_calc_button)
        race_layout.addWidget(self.race_player, 2, 1)
        
        # Quick tips
        tip_label = QLabel("Tip: Arrow keys work independently for each field")
        tip_label.setStyleSheet("color: #888; font-style: italic; font-size: 11px;")
        race_layout.addWidget(tip_label, 3, 0, 1, 2)
        
        layout.addWidget(race_group)
        
        # Results section
        result_frame = QFrame()
        result_frame.setFrameStyle(QFrame.Box)
        result_frame.setLineWidth(2)
        result_frame.setMinimumHeight(100)
        result_layout = QVBoxLayout(result_frame)
        result_layout.setSpacing(15)
        
        # Calculated ratios
        ratios_layout = QHBoxLayout()
        ratios_layout.addWidget(QLabel("Calculated Ratios:"))
        ratios_layout.addStretch()
        
        self.qual_result_label = QLabel("QualRatio: <b>---</b>")
        self.qual_result_label.setTextFormat(Qt.RichText)
        self.qual_result_label.setMinimumWidth(250)
        self.qual_result_label.setAlignment(Qt.AlignRight)
        ratios_layout.addWidget(self.qual_result_label)
        
        self.race_result_label = QLabel("RaceRatio: <b>---</b>")
        self.race_result_label.setTextFormat(Qt.RichText)
        self.race_result_label.setMinimumWidth(250)
        self.race_result_label.setAlignment(Qt.AlignRight)
        ratios_layout.addWidget(self.race_result_label)
        
        result_layout.addLayout(ratios_layout)
        
        # Formula note
        note_label = QLabel("Formula: Ratio = (Pole - Player) / (Pole - LastAI) + 1.0")
        note_label.setStyleSheet("color: #888; font-style: italic; font-size: 11px;")
        note_label.setAlignment(Qt.AlignCenter)
        result_layout.addWidget(note_label)
        
        layout.addWidget(result_frame)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(15)
        
        self.calc_btn = QPushButton("Calculate")
        self.calc_btn.setFixedHeight(45)
        self.calc_btn.setFixedWidth(140)
        self.calc_btn.clicked.connect(self.calculate_ratios)
        self.calc_btn.setStyleSheet("""
            QPushButton {
                background-color: #9C27B0;
                color: white;
                border: none;
                border-radius: 4px;
                font-family: 'Segoe UI', 'Arial', sans-serif;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #7B1FA2;
            }
            QPushButton:disabled {
                background-color: #666666;
                color: #999999;
            }
        """)
        button_layout.addWidget(self.calc_btn)
        
        button_layout.addStretch()
        
        self.apply_btn = QPushButton("Apply")
        self.apply_btn.setFixedHeight(45)
        self.apply_btn.setFixedWidth(140)
        self.apply_btn.clicked.connect(self.accept)
        self.apply_btn.setEnabled(False)
        self.apply_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 4px;
                font-family: 'Segoe UI', 'Arial', sans-serif;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:disabled {
                background-color: #666666;
                color: #999999;
            }
        """)
        button_layout.addWidget(self.apply_btn)
        
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setFixedHeight(45)
        self.cancel_btn.setFixedWidth(140)
        self.cancel_btn.clicked.connect(self.reject)
        self.cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                border: none;
                border-radius: 4px;
                font-family: 'Segoe UI', 'Arial', sans-serif;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #d32f2f;
            }
        """)
        button_layout.addWidget(self.cancel_btn)
        
        layout.addLayout(button_layout)
        
        self.check_calc_button()
    
    def apply_dark_theme(self):
        self.setStyleSheet("""
            QDialog {
                background-color: #2b2b2b;
            }
            QGroupBox {
                color: #4CAF50;
                font-weight: bold;
                border: 2px solid #555;
                border-radius: 6px;
                margin-top: 15px;
                padding-top: 15px;
                font-size: 14px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 8px 0 8px;
            }
            QFrame {
                background-color: #1e1e1e;
                border: 2px solid #555;
                border-radius: 6px;
            }
            QLabel {
                color: #ffffff;
                font-family: 'Segoe UI', 'Arial', sans-serif;
                font-size: 13px;
            }
        """)
    
    def on_current_qual_changed(self, value):
        """Handle changes to current QualRatio"""
        self.current_qual = value
        self.new_qual = value
        # Update the result label if it was previously calculated
        if hasattr(self, 'qual_result_label') and self.qual_result_label.text() != "QualRatio: <b>---</b>":
            self.qual_result_label.setText(f"QualRatio: <b style='color:#9C27B0;'>{value:.6f}</b>")
    
    def on_current_race_changed(self, value):
        """Handle changes to current RaceRatio"""
        self.current_race = value
        self.new_race = value
        # Update the result label if it was previously calculated
        if hasattr(self, 'race_result_label') and self.race_result_label.text() != "RaceRatio: <b>---</b>":
            self.race_result_label.setText(f"RaceRatio: <b style='color:#9C27B0;'>{value:.6f}</b>")
    
    def check_calc_button(self):
        """Enable calculate button only if all required fields have values"""
        qual_valid = (self.qual_pole.value() > 0 and 
                     self.qual_last_ai.value() > 0 and 
                     self.qual_player.value() > 0)
        
        race_valid = (self.race_pole.value() > 0 and 
                     self.race_last_ai.value() > 0 and 
                     self.race_player.value() > 0)
        
        self.calc_btn.setEnabled(qual_valid or race_valid)
    
    def calculate_ratios(self):
        """Calculate ratios based on input lap times"""
        # Calculate QualRatio if all qualifying values are provided
        if (self.qual_pole.value() > 0 and 
            self.qual_last_ai.value() > 0 and 
            self.qual_player.value() > 0):
            
            pole = self.qual_pole.value()
            last_ai = self.qual_last_ai.value()
            player = self.qual_player.value()
            
            # Formula: ratio = (pole - player) / (pole - last_ai) + 1.0
            # Clamp between 0.1 and 10.0
            if abs(pole - last_ai) > 0.001:  # Avoid division by zero with small tolerance
                ratio = (pole - player) / (pole - last_ai) + 1.0
                self.new_qual = max(0.1, min(10.0, ratio))
                # Update both the result label and the current value edit
                self.qual_result_label.setText(f"QualRatio: <b style='color:#9C27B0;'>{self.new_qual:.6f}</b>")
                self.current_qual_edit.setValue(self.new_qual)  # Update the editable field
            else:
                self.qual_result_label.setText("QualRatio: <b style='color:#f44336;'>Error (pole ≈ last AI)</b>")
        
        # Calculate RaceRatio if all race values are provided
        if (self.race_pole.value() > 0 and 
            self.race_last_ai.value() > 0 and 
            self.race_player.value() > 0):
            
            pole = self.race_pole.value()
            last_ai = self.race_last_ai.value()
            player = self.race_player.value()
            
            # Formula: ratio = (pole - player) / (pole - last_ai) + 1.0
            # Clamp between 0.1 and 10.0
            if abs(pole - last_ai) > 0.001:  # Avoid division by zero with small tolerance
                ratio = (pole - player) / (pole - last_ai) + 1.0
                self.new_race = max(0.1, min(10.0, ratio))
                # Update both the result label and the current value edit
                self.race_result_label.setText(f"RaceRatio: <b style='color:#9C27B0;'>{self.new_race:.6f}</b>")
                self.current_race_edit.setValue(self.new_race)  # Update the editable field
            else:
                self.race_result_label.setText("RaceRatio: <b style='color:#f44336;'>Error (pole ≈ last AI)</b>")
        
        # Enable apply button if at least one ratio was calculated
        self.apply_btn.setEnabled(True)
    
    def get_ratios(self):
        """Return the calculated ratios (from the editable fields)"""
        return self.current_qual_edit.value(), self.current_race_edit.value()
