"""
Ratio Calculator GUI for AIW Ratio Editor - SIMPLIFIED VERSION with New Calculations
"""

from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
import cfg_manage
from ratio_calc import (
    LapTimes, RatioConfig, RatioCalculator, 
    HistoricCSVHandler, CalculatedRatios, TimeConverter
)


class RatioCalculatorDialog(QDialog):
    """Main dialog for ratio calculator"""
    
    def __init__(self, parent=None, track_name="", current_qual=1.0, current_race=1.0):
        super().__init__(parent)
        self.track_name = track_name
        self.current_qual = current_qual
        self.current_race = current_race
        self.new_qual = current_qual
        self.new_race = current_race
        
        # Load configuration
        self.config = RatioConfig(
            historic_csv=cfg_manage.get_historic_csv() or "",
            goal_percent=cfg_manage.get_goal_percent(),
            goal_offset=cfg_manage.get_goal_offset(),
            percent_ratio=cfg_manage.get_percent_ratio()
        )
        
        # Initialize CSV handler
        self.csv_handler = HistoricCSVHandler(self.config.historic_csv)
        
        self.setup_ui()
        self.setup_connections()
        
    def setup_ui(self):
        self.setWindowTitle(f"Ratio Calculator - {self.track_name}")
        self.setModal(True)
        self.setMinimumWidth(1000)
        self.setMinimumHeight(1100)
        
        # Set dark background
        self.setStyleSheet("""
            QDialog {
                background-color: #2b2b2b;
            }
            QLabel {
                color: white;
                font-size: 12px;
            }
            QGroupBox {
                color: #4CAF50;
                font-weight: bold;
                border: 2px solid #555;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
                font-size: 13px;
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
                border-radius: 3px;
                padding: 8px;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:disabled {
                background-color: #666;
            }
            QSpinBox, QDoubleSpinBox {
                background-color: #3c3c3c;
                color: white;
                border: 1px solid #4CAF50;
                border-radius: 3px;
                padding: 5px;
                font-size: 13px;
                min-height: 25px;
            }
            QLineEdit {
                background-color: #3c3c3c;
                color: white;
                border: 1px solid #4CAF50;
                border-radius: 3px;
                padding: 5px;
                font-size: 12px;
                min-height: 25px;
            }
        """)
        
        # Main layout - vertical stack
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Title
        title = QLabel(f"<h2>Ratio Calculator - {self.track_name}</h2>")
        title.setTextFormat(Qt.RichText)
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # ===== CONFIGURATION SECTION =====
        config_group = QGroupBox("Configuration")
        config_layout = QVBoxLayout(config_group)
        config_layout.setSpacing(10)
        
        # Track info
        track_info = QLabel(f"Track: {self.track_name}")
        track_info.setStyleSheet("color: #4CAF50; font-size: 13px; font-weight: bold;")
        config_layout.addWidget(track_info)
        
        # Current ratios
        ratios_layout = QHBoxLayout()
        ratios_layout.addWidget(QLabel(f"Current QualRatio: "))
        self.qual_display = QLabel(f"{self.current_qual:.6f}")
        self.qual_display.setStyleSheet("color: #9C27B0; font-weight: bold; font-size: 13px;")
        ratios_layout.addWidget(self.qual_display)
        
        ratios_layout.addSpacing(30)
        
        ratios_layout.addWidget(QLabel(f"Current RaceRatio: "))
        self.race_display = QLabel(f"{self.current_race:.6f}")
        self.race_display.setStyleSheet("color: #9C27B0; font-weight: bold; font-size: 13px;")
        ratios_layout.addWidget(self.race_display)
        
        ratios_layout.addStretch()
        config_layout.addLayout(ratios_layout)
        
        # CSV path
        csv_layout = QHBoxLayout()
        csv_layout.addWidget(QLabel("Historic CSV:"))
        self.csv_path = QLineEdit(self.config.historic_csv)
        self.csv_path.setReadOnly(True)
        self.csv_path.setMinimumWidth(350)
        self.csv_path.setFixedHeight(35)
        csv_layout.addWidget(self.csv_path)
        
        self.csv_browse = QPushButton("Browse")
        self.csv_browse.setFixedHeight(35)
        self.csv_browse.setFixedWidth(100)
        self.csv_browse.clicked.connect(self.browse_csv)
        csv_layout.addWidget(self.csv_browse)
        csv_layout.addStretch()
        config_layout.addLayout(csv_layout)
        
        layout.addWidget(config_group)
        
        # ===== CURRENT VALUES SECTION =====
        values_group = QGroupBox("Current Values (editable)")
        values_layout = QGridLayout(values_group)
        values_layout.setVerticalSpacing(15)
        values_layout.setHorizontalSpacing(20)
        
        # Goal Percent
        values_layout.addWidget(QLabel("Goal Percent (%):"), 0, 0)
        self.goal_percent = QDoubleSpinBox()
        self.goal_percent.setRange(0, 100)
        self.goal_percent.setDecimals(1)
        self.goal_percent.setSingleStep(1)
        self.goal_percent.setValue(self.config.goal_percent)
        self.goal_percent.setSuffix("%")
        self.goal_percent.setFixedHeight(35)
        self.goal_percent.setMinimumWidth(150)
        self.goal_percent.valueChanged.connect(self.on_config_changed)
        values_layout.addWidget(self.goal_percent, 0, 1)
        
        # Goal Offset
        values_layout.addWidget(QLabel("Goal Offset:"), 0, 2)
        self.goal_offset = QDoubleSpinBox()
        self.goal_offset.setRange(-100, 100)
        self.goal_offset.setDecimals(2)
        self.goal_offset.setSingleStep(0.1)
        self.goal_offset.setValue(self.config.goal_offset)
        self.goal_offset.setFixedHeight(35)
        self.goal_offset.setMinimumWidth(150)
        self.goal_offset.valueChanged.connect(self.on_config_changed)
        values_layout.addWidget(self.goal_offset, 0, 3)
        
        # Percent Ratio
        values_layout.addWidget(QLabel("Percent Ratio:"), 1, 0)
        self.percent_ratio = QDoubleSpinBox()
        self.percent_ratio.setRange(0.001, 1.0)
        self.percent_ratio.setDecimals(3)
        self.percent_ratio.setSingleStep(0.01)
        self.percent_ratio.setValue(self.config.percent_ratio)
        self.percent_ratio.setToolTip("Ratio change per 1% shift (default: 0.01)")
        self.percent_ratio.setFixedHeight(35)
        self.percent_ratio.setMinimumWidth(150)
        self.percent_ratio.valueChanged.connect(self.on_config_changed)
        values_layout.addWidget(self.percent_ratio, 1, 1)
        
        # Save button
        self.save_btn = QPushButton("Save to cfg.yml")
        self.save_btn.setFixedHeight(40)
        self.save_btn.setFixedWidth(150)
        self.save_btn.setCursor(Qt.PointingHandCursor)
        self.save_btn.clicked.connect(self.save_configuration)
        self.save_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 4px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        values_layout.addWidget(self.save_btn, 1, 3, Qt.AlignRight)
        
        layout.addWidget(values_group)
        
        # ===== QUALIFYING SECTION =====
        qual_group = QGroupBox("Qualifying")
        qual_layout = QVBoxLayout(qual_group)
        qual_layout.setSpacing(10)
        
        # Best AI time
        best_layout = QHBoxLayout()
        best_layout.addWidget(QLabel("Best AI:"))
        self.qual_best_min = self.create_time_spinbox(0, 99)
        best_layout.addWidget(self.qual_best_min)
        best_layout.addWidget(QLabel("min"))
        self.qual_best_sec = self.create_time_spinbox(0, 59)
        best_layout.addWidget(self.qual_best_sec)
        best_layout.addWidget(QLabel("sec"))
        self.qual_best_ms = self.create_time_spinbox(0, 999)
        self.qual_best_ms.setSingleStep(10)
        best_layout.addWidget(self.qual_best_ms)
        best_layout.addWidget(QLabel("ms"))
        best_layout.addStretch()
        qual_layout.addLayout(best_layout)
        
        # Worst AI time
        worst_layout = QHBoxLayout()
        worst_layout.addWidget(QLabel("Worst AI:"))
        self.qual_worst_min = self.create_time_spinbox(0, 99)
        worst_layout.addWidget(self.qual_worst_min)
        worst_layout.addWidget(QLabel("min"))
        self.qual_worst_sec = self.create_time_spinbox(0, 59)
        worst_layout.addWidget(self.qual_worst_sec)
        worst_layout.addWidget(QLabel("sec"))
        self.qual_worst_ms = self.create_time_spinbox(0, 999)
        self.qual_worst_ms.setSingleStep(10)
        worst_layout.addWidget(self.qual_worst_ms)
        worst_layout.addWidget(QLabel("ms"))
        worst_layout.addStretch()
        qual_layout.addLayout(worst_layout)
        
        # User time
        user_layout = QHBoxLayout()
        user_layout.addWidget(QLabel("User:"))
        self.qual_user_min = self.create_time_spinbox(0, 99)
        user_layout.addWidget(self.qual_user_min)
        user_layout.addWidget(QLabel("min"))
        self.qual_user_sec = self.create_time_spinbox(0, 59)
        user_layout.addWidget(self.qual_user_sec)
        user_layout.addWidget(QLabel("sec"))
        self.qual_user_ms = self.create_time_spinbox(0, 999)
        self.qual_user_ms.setSingleStep(10)
        user_layout.addWidget(self.qual_user_ms)
        user_layout.addWidget(QLabel("ms"))
        user_layout.addStretch()
        qual_layout.addLayout(user_layout)
        
        # Qualifying totals display
        qual_totals_layout = QHBoxLayout()
        qual_totals_layout.addWidget(QLabel("Best AI:"))
        self.qual_best_total = QLabel("0.000s")
        self.qual_best_total.setStyleSheet("color: #4CAF50; font-weight: bold; font-size: 13px;")
        qual_totals_layout.addWidget(self.qual_best_total)
        
        qual_totals_layout.addSpacing(20)
        
        qual_totals_layout.addWidget(QLabel("Worst AI:"))
        self.qual_worst_total = QLabel("0.000s")
        self.qual_worst_total.setStyleSheet("color: #f44336; font-weight: bold; font-size: 13px;")
        qual_totals_layout.addWidget(self.qual_worst_total)
        
        qual_totals_layout.addSpacing(20)
        
        qual_totals_layout.addWidget(QLabel("User:"))
        self.qual_user_total = QLabel("0.000s")
        self.qual_user_total.setStyleSheet("color: #9C27B0; font-weight: bold; font-size: 13px;")
        qual_totals_layout.addWidget(self.qual_user_total)
        
        qual_totals_layout.addStretch()
        qual_layout.addLayout(qual_totals_layout)
        
        layout.addWidget(qual_group)
        
        # ===== RACE SECTION =====
        race_group = QGroupBox("Race")
        race_layout = QVBoxLayout(race_group)
        race_layout.setSpacing(10)
        
        # Best AI time
        best_layout = QHBoxLayout()
        best_layout.addWidget(QLabel("Best AI:"))
        self.race_best_min = self.create_time_spinbox(0, 99)
        best_layout.addWidget(self.race_best_min)
        best_layout.addWidget(QLabel("min"))
        self.race_best_sec = self.create_time_spinbox(0, 59)
        best_layout.addWidget(self.race_best_sec)
        best_layout.addWidget(QLabel("sec"))
        self.race_best_ms = self.create_time_spinbox(0, 999)
        self.race_best_ms.setSingleStep(10)
        best_layout.addWidget(self.race_best_ms)
        best_layout.addWidget(QLabel("ms"))
        best_layout.addStretch()
        race_layout.addLayout(best_layout)
        
        # Worst AI time
        worst_layout = QHBoxLayout()
        worst_layout.addWidget(QLabel("Worst AI:"))
        self.race_worst_min = self.create_time_spinbox(0, 99)
        worst_layout.addWidget(self.race_worst_min)
        worst_layout.addWidget(QLabel("min"))
        self.race_worst_sec = self.create_time_spinbox(0, 59)
        worst_layout.addWidget(self.race_worst_sec)
        worst_layout.addWidget(QLabel("sec"))
        self.race_worst_ms = self.create_time_spinbox(0, 999)
        self.race_worst_ms.setSingleStep(10)
        worst_layout.addWidget(self.race_worst_ms)
        worst_layout.addWidget(QLabel("ms"))
        worst_layout.addStretch()
        race_layout.addLayout(worst_layout)
        
        # User time
        user_layout = QHBoxLayout()
        user_layout.addWidget(QLabel("User:"))
        self.race_user_min = self.create_time_spinbox(0, 99)
        user_layout.addWidget(self.race_user_min)
        user_layout.addWidget(QLabel("min"))
        self.race_user_sec = self.create_time_spinbox(0, 59)
        user_layout.addWidget(self.race_user_sec)
        user_layout.addWidget(QLabel("sec"))
        self.race_user_ms = self.create_time_spinbox(0, 999)
        self.race_user_ms.setSingleStep(10)
        user_layout.addWidget(self.race_user_ms)
        user_layout.addWidget(QLabel("ms"))
        user_layout.addStretch()
        race_layout.addLayout(user_layout)
        
        # Race totals display
        race_totals_layout = QHBoxLayout()
        race_totals_layout.addWidget(QLabel("Best AI:"))
        self.race_best_total = QLabel("0.000s")
        self.race_best_total.setStyleSheet("color: #4CAF50; font-weight: bold; font-size: 13px;")
        race_totals_layout.addWidget(self.race_best_total)
        
        race_totals_layout.addSpacing(20)
        
        race_totals_layout.addWidget(QLabel("Worst AI:"))
        self.race_worst_total = QLabel("0.000s")
        self.race_worst_total.setStyleSheet("color: #f44336; font-weight: bold; font-size: 13px;")
        race_totals_layout.addWidget(self.race_worst_total)
        
        race_totals_layout.addSpacing(20)
        
        race_totals_layout.addWidget(QLabel("User:"))
        self.race_user_total = QLabel("0.000s")
        self.race_user_total.setStyleSheet("color: #9C27B0; font-weight: bold; font-size: 13px;")
        race_totals_layout.addWidget(self.race_user_total)
        
        race_totals_layout.addStretch()
        race_layout.addLayout(race_totals_layout)
        
        layout.addWidget(race_group)
        
        # ===== POSITION CALCULATIONS DISPLAY =====
        pos_group = QGroupBox("Position Calculations")
        pos_layout = QGridLayout(pos_group)
        pos_layout.setVerticalSpacing(15)
        pos_layout.setHorizontalSpacing(20)
        
        # Headers
        pos_layout.addWidget(QLabel(""), 0, 0)
        pos_layout.addWidget(QLabel("Current"), 0, 1)
        pos_layout.addWidget(QLabel("Target"), 0, 2)
        pos_layout.addWidget(QLabel("Shift"), 0, 3)
        pos_layout.addWidget(QLabel("Ratio Change"), 0, 4)
        
        # Qualifying row
        pos_layout.addWidget(QLabel("Qualifying:"), 1, 0)
        
        self.qual_current_pos = QLabel("0.0%")
        self.qual_current_pos.setStyleSheet("color: #888; font-weight: bold; font-size: 13px;")
        pos_layout.addWidget(self.qual_current_pos, 1, 1)
        
        self.qual_target_pos = QLabel(f"{self.config.goal_percent + self.config.goal_offset:.1f}%")
        self.qual_target_pos.setStyleSheet("color: #4CAF50; font-weight: bold; font-size: 13px;")
        pos_layout.addWidget(self.qual_target_pos, 1, 2)
        
        self.qual_pos_shift = QLabel("0.0%")
        self.qual_pos_shift.setStyleSheet("color: #FFA500; font-weight: bold; font-size: 13px;")
        pos_layout.addWidget(self.qual_pos_shift, 1, 3)
        
        self.qual_ratio_change = QLabel("0.000000")
        self.qual_ratio_change.setStyleSheet("color: #9C27B0; font-weight: bold; font-size: 13px;")
        pos_layout.addWidget(self.qual_ratio_change, 1, 4)
        
        # Race row
        pos_layout.addWidget(QLabel("Race:"), 2, 0)
        
        self.race_current_pos = QLabel("0.0%")
        self.race_current_pos.setStyleSheet("color: #888; font-weight: bold; font-size: 13px;")
        pos_layout.addWidget(self.race_current_pos, 2, 1)
        
        self.race_target_pos = QLabel(f"{self.config.goal_percent + self.config.goal_offset:.1f}%")
        self.race_target_pos.setStyleSheet("color: #4CAF50; font-weight: bold; font-size: 13px;")
        pos_layout.addWidget(self.race_target_pos, 2, 2)
        
        self.race_pos_shift = QLabel("0.0%")
        self.race_pos_shift.setStyleSheet("color: #FFA500; font-weight: bold; font-size: 13px;")
        pos_layout.addWidget(self.race_pos_shift, 2, 3)
        
        self.race_ratio_change = QLabel("0.000000")
        self.race_ratio_change.setStyleSheet("color: #9C27B0; font-weight: bold; font-size: 13px;")
        pos_layout.addWidget(self.race_ratio_change, 2, 4)
        
        layout.addWidget(pos_group)
        
        # ===== RESULTS DISPLAY =====
        results_group = QGroupBox("Results")
        results_layout = QHBoxLayout(results_group)
        results_layout.setSpacing(30)
        
        results_layout.addWidget(QLabel("New QualRatio:"))
        self.new_qual_label = QLabel(f"{self.current_qual:.6f}")
        self.new_qual_label.setStyleSheet("color: #9C27B0; font-size: 14px; font-weight: bold;")
        results_layout.addWidget(self.new_qual_label)
        
        results_layout.addSpacing(50)
        
        results_layout.addWidget(QLabel("New RaceRatio:"))
        self.new_race_label = QLabel(f"{self.current_race:.6f}")
        self.new_race_label.setStyleSheet("color: #9C27B0; font-size: 14px; font-weight: bold;")
        results_layout.addWidget(self.new_race_label)
        
        results_layout.addStretch()
        
        layout.addWidget(results_group)
        
        # ===== FORMULA DISPLAY =====
        formula_frame = QFrame()
        formula_frame.setFrameStyle(QFrame.Box)
        formula_frame.setStyleSheet("background-color: #1e1e1e; padding: 10px;")
        formula_layout = QVBoxLayout(formula_frame)
        
        formula_layout.addWidget(QLabel("Current Position = ((User - Best) / (Worst - Best)) × 100%"))
        formula_layout.addWidget(QLabel("Target Position = Goal Percent + Goal Offset"))
        formula_layout.addWidget(QLabel("Position Shift = Target - Current"))
        formula_layout.addWidget(QLabel("Ratio Change = Position Shift × Percent Ratio"))
        formula_layout.addWidget(QLabel("New Ratio = Current Ratio + Ratio Change"))
        
        layout.addWidget(formula_frame)
        
        # ===== BUTTONS =====
        button_layout = QHBoxLayout()
        
        self.calc_btn = QPushButton("Calculate & Save to CSV")
        self.calc_btn.setFixedHeight(45)
        self.calc_btn.setFixedWidth(220)
        self.calc_btn.setCursor(Qt.PointingHandCursor)
        self.calc_btn.clicked.connect(self.calculate_ratios)
        self.calc_btn.setEnabled(False)
        self.calc_btn.setStyleSheet("""
            QPushButton {
                background-color: #9C27B0;
                color: white;
                border: none;
                border-radius: 5px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #7B1FA2;
            }
            QPushButton:disabled {
                background-color: #666;
                color: #999;
            }
        """)
        button_layout.addWidget(self.calc_btn)
        
        button_layout.addStretch()
        
        self.apply_btn = QPushButton("Apply Ratios")
        self.apply_btn.setFixedHeight(45)
        self.apply_btn.setFixedWidth(150)
        self.apply_btn.setCursor(Qt.PointingHandCursor)
        self.apply_btn.clicked.connect(self.accept)
        self.apply_btn.setEnabled(False)
        self.apply_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 5px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:disabled {
                background-color: #666;
                color: #999;
            }
        """)
        button_layout.addWidget(self.apply_btn)
        
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setFixedHeight(45)
        self.cancel_btn.setFixedWidth(150)
        self.cancel_btn.setCursor(Qt.PointingHandCursor)
        self.cancel_btn.clicked.connect(self.reject)
        self.cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                border: none;
                border-radius: 5px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #d32f2f;
            }
        """)
        button_layout.addWidget(self.cancel_btn)
        
        layout.addLayout(button_layout)
        
        # Status label
        self.status_label = QLabel("")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("color: #888; font-style: italic; font-size: 12px;")
        layout.addWidget(self.status_label)
    
    def setup_connections(self):
        """Setup signal connections for live updates"""
        # Qualifying connections
        self.qual_best_min.valueChanged.connect(self.update_qual_calculations)
        self.qual_best_sec.valueChanged.connect(self.update_qual_calculations)
        self.qual_best_ms.valueChanged.connect(self.update_qual_calculations)
        self.qual_worst_min.valueChanged.connect(self.update_qual_calculations)
        self.qual_worst_sec.valueChanged.connect(self.update_qual_calculations)
        self.qual_worst_ms.valueChanged.connect(self.update_qual_calculations)
        self.qual_user_min.valueChanged.connect(self.update_qual_calculations)
        self.qual_user_sec.valueChanged.connect(self.update_qual_calculations)
        self.qual_user_ms.valueChanged.connect(self.update_qual_calculations)
        
        # Race connections
        self.race_best_min.valueChanged.connect(self.update_race_calculations)
        self.race_best_sec.valueChanged.connect(self.update_race_calculations)
        self.race_best_ms.valueChanged.connect(self.update_race_calculations)
        self.race_worst_min.valueChanged.connect(self.update_race_calculations)
        self.race_worst_sec.valueChanged.connect(self.update_race_calculations)
        self.race_worst_ms.valueChanged.connect(self.update_race_calculations)
        self.race_user_min.valueChanged.connect(self.update_race_calculations)
        self.race_user_sec.valueChanged.connect(self.update_race_calculations)
        self.race_user_ms.valueChanged.connect(self.update_race_calculations)
        
        # Config connections for target update
        self.goal_percent.valueChanged.connect(self.update_target_positions)
        self.goal_offset.valueChanged.connect(self.update_target_positions)
        self.percent_ratio.valueChanged.connect(self.update_qual_calculations)
        self.percent_ratio.valueChanged.connect(self.update_race_calculations)
        
        # Also update button state
        self.qual_best_min.valueChanged.connect(self.check_calc_button)
        self.qual_best_sec.valueChanged.connect(self.check_calc_button)
        self.qual_best_ms.valueChanged.connect(self.check_calc_button)
        self.qual_worst_min.valueChanged.connect(self.check_calc_button)
        self.qual_worst_sec.valueChanged.connect(self.check_calc_button)
        self.qual_worst_ms.valueChanged.connect(self.check_calc_button)
        self.qual_user_min.valueChanged.connect(self.check_calc_button)
        self.qual_user_sec.valueChanged.connect(self.check_calc_button)
        self.qual_user_ms.valueChanged.connect(self.check_calc_button)
        
        self.race_best_min.valueChanged.connect(self.check_calc_button)
        self.race_best_sec.valueChanged.connect(self.check_calc_button)
        self.race_best_ms.valueChanged.connect(self.check_calc_button)
        self.race_worst_min.valueChanged.connect(self.check_calc_button)
        self.race_worst_sec.valueChanged.connect(self.check_calc_button)
        self.race_worst_ms.valueChanged.connect(self.check_calc_button)
        self.race_user_min.valueChanged.connect(self.check_calc_button)
        self.race_user_sec.valueChanged.connect(self.check_calc_button)
        self.race_user_ms.valueChanged.connect(self.check_calc_button)
    
    def update_target_positions(self):
        """Update target position displays"""
        target = self.goal_percent.value() + self.goal_offset.value()
        self.qual_target_pos.setText(f"{target:.1f}%")
        self.race_target_pos.setText(f"{target:.1f}%")
        
        # Recalculate positions with new target
        self.update_qual_calculations()
        self.update_race_calculations()
    
    def create_time_spinbox(self, min_val, max_val):
        """Create a spinbox for time input"""
        spin = QSpinBox()
        spin.setRange(min_val, max_val)
        spin.setValue(0)
        spin.setFixedHeight(35)
        spin.setFixedWidth(80)
        spin.setAlignment(Qt.AlignRight)
        return spin
    
    def browse_csv(self):
        """Browse for CSV file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Historic CSV File",
            self.csv_path.text(),
            "CSV Files (*.csv);;All Files (*)"
        )
        
        if file_path:
            self.csv_path.setText(file_path)
            self.config.historic_csv = file_path
    
    def on_config_changed(self):
        """Handle configuration changes"""
        self.config.goal_percent = self.goal_percent.value()
        self.config.goal_offset = self.goal_offset.value()
        self.config.percent_ratio = self.percent_ratio.value()
        self.update_target_positions()
    
    def refresh_from_config(self):
        """Refresh values from config file"""
        # Reload configuration
        self.config.historic_csv = cfg_manage.get_historic_csv() or ""
        self.config.goal_percent = cfg_manage.get_goal_percent()
        self.config.goal_offset = cfg_manage.get_goal_offset()
        self.config.percent_ratio = cfg_manage.get_percent_ratio()
        
        # Update UI
        self.csv_path.setText(self.config.historic_csv)
        self.goal_percent.setValue(self.config.goal_percent)
        self.goal_offset.setValue(self.config.goal_offset)
        self.percent_ratio.setValue(self.config.percent_ratio)
        
        # Update CSV handler
        self.csv_handler = HistoricCSVHandler(self.config.historic_csv)
    
    def save_configuration(self):
        """Save configuration to file"""
        if self.config.historic_csv:
            cfg_manage.update_historic_csv(self.config.historic_csv)
        
        cfg_manage.update_goal_percent(self.config.goal_percent)
        cfg_manage.update_goal_offset(self.config.goal_offset)
        cfg_manage.update_percent_ratio(self.config.percent_ratio)
        
        QMessageBox.information(self, "Saved", "Configuration saved to cfg.yml")
        
        # Refresh from config to ensure everything is in sync
        self.refresh_from_config()
    
    def get_qual_times(self):
        """Get qualifying lap times"""
        best = TimeConverter.mmssms_to_seconds(
            self.qual_best_min.value(),
            self.qual_best_sec.value(),
            self.qual_best_ms.value()
        )
        worst = TimeConverter.mmssms_to_seconds(
            self.qual_worst_min.value(),
            self.qual_worst_sec.value(),
            self.qual_worst_ms.value()
        )
        user = TimeConverter.mmssms_to_seconds(
            self.qual_user_min.value(),
            self.qual_user_sec.value(),
            self.qual_user_ms.value()
        )
        return LapTimes(best, worst, user)
    
    def get_race_times(self):
        """Get race lap times"""
        best = TimeConverter.mmssms_to_seconds(
            self.race_best_min.value(),
            self.race_best_sec.value(),
            self.race_best_ms.value()
        )
        worst = TimeConverter.mmssms_to_seconds(
            self.race_worst_min.value(),
            self.race_worst_sec.value(),
            self.race_worst_ms.value()
        )
        user = TimeConverter.mmssms_to_seconds(
            self.race_user_min.value(),
            self.race_user_sec.value(),
            self.race_user_ms.value()
        )
        return LapTimes(best, worst, user)
    
    def update_qual_calculations(self):
        """Update qualifying calculation displays"""
        times = self.get_qual_times()
        
        # Update total displays
        self.qual_best_total.setText(f"{times.pole:.3f}s")
        self.qual_worst_total.setText(f"{times.last_ai:.3f}s")
        self.qual_user_total.setText(f"{times.player:.3f}s")
        
        if times.are_valid() and times.ai_spread > 0.001:
            # Calculate current position percentage
            current_pos = ((times.player - times.pole) / times.ai_spread) * 100
            target_pos = self.goal_percent.value() + self.goal_offset.value()
            pos_shift = target_pos - current_pos
            ratio_change = pos_shift * self.percent_ratio.value()
            
            # Update displays
            self.qual_current_pos.setText(f"{current_pos:.1f}%")
            self.qual_pos_shift.setText(f"{pos_shift:+.1f}%")
            self.qual_ratio_change.setText(f"{ratio_change:+.6f}")
            
            # Color code the position based on where user falls
            if current_pos < 33:
                self.qual_current_pos.setStyleSheet("color: #4CAF50; font-weight: bold; font-size: 13px;")
            elif current_pos < 66:
                self.qual_current_pos.setStyleSheet("color: #FFA500; font-weight: bold; font-size: 13px;")
            else:
                self.qual_current_pos.setStyleSheet("color: #f44336; font-weight: bold; font-size: 13px;")
        else:
            self.qual_current_pos.setText("0.0%")
            self.qual_pos_shift.setText("0.0%")
            self.qual_ratio_change.setText("0.000000")
            self.qual_current_pos.setStyleSheet("color: #888; font-weight: bold; font-size: 13px;")
    
    def update_race_calculations(self):
        """Update race calculation displays"""
        times = self.get_race_times()
        
        # Update total displays
        self.race_best_total.setText(f"{times.pole:.3f}s")
        self.race_worst_total.setText(f"{times.last_ai:.3f}s")
        self.race_user_total.setText(f"{times.player:.3f}s")
        
        if times.are_valid() and times.ai_spread > 0.001:
            # Calculate current position percentage
            current_pos = ((times.player - times.pole) / times.ai_spread) * 100
            target_pos = self.goal_percent.value() + self.goal_offset.value()
            pos_shift = target_pos - current_pos
            ratio_change = pos_shift * self.percent_ratio.value()
            
            # Update displays
            self.race_current_pos.setText(f"{current_pos:.1f}%")
            self.race_pos_shift.setText(f"{pos_shift:+.1f}%")
            self.race_ratio_change.setText(f"{ratio_change:+.6f}")
            
            # Color code the position based on where user falls
            if current_pos < 33:
                self.race_current_pos.setStyleSheet("color: #4CAF50; font-weight: bold; font-size: 13px;")
            elif current_pos < 66:
                self.race_current_pos.setStyleSheet("color: #FFA500; font-weight: bold; font-size: 13px;")
            else:
                self.race_current_pos.setStyleSheet("color: #f44336; font-weight: bold; font-size: 13px;")
        else:
            self.race_current_pos.setText("0.0%")
            self.race_pos_shift.setText("0.0%")
            self.race_ratio_change.setText("0.000000")
            self.race_current_pos.setStyleSheet("color: #888; font-weight: bold; font-size: 13px;")
    
    def check_calc_button(self):
        """Enable calculate button if all required fields have values"""
        qual_filled = (self.qual_best_min.value() > 0 or self.qual_best_sec.value() > 0 or self.qual_best_ms.value() > 0) and \
                      (self.qual_worst_min.value() > 0 or self.qual_worst_sec.value() > 0 or self.qual_worst_ms.value() > 0) and \
                      (self.qual_user_min.value() > 0 or self.qual_user_sec.value() > 0 or self.qual_user_ms.value() > 0)
        
        race_filled = (self.race_best_min.value() > 0 or self.race_best_sec.value() > 0 or self.race_best_ms.value() > 0) and \
                      (self.race_worst_min.value() > 0 or self.race_worst_sec.value() > 0 or self.race_worst_ms.value() > 0) and \
                      (self.race_user_min.value() > 0 or self.race_user_sec.value() > 0 or self.race_user_ms.value() > 0)
        
        self.calc_btn.setEnabled(qual_filled or race_filled)
    
    def calculate_ratios(self):
        """Calculate ratios and save to CSV"""
        qual_times = self.get_qual_times()
        race_times = self.get_race_times()
        
        results = RatioCalculator.calculate_all(
            qual_times, race_times, self.config, 
            self.current_qual, self.current_race
        )
        
        # Update displays
        if results.has_qual_ratio():
            self.new_qual = results.qual_ratio
            self.new_qual_label.setText(f"{self.new_qual:.6f}")
            self.new_qual_label.setStyleSheet("color: #9C27B0; font-size: 14px; font-weight: bold;")
        
        if results.has_race_ratio():
            self.new_race = results.race_ratio
            self.new_race_label.setText(f"{self.new_race:.6f}")
            self.new_race_label.setStyleSheet("color: #9C27B0; font-size: 14px; font-weight: bold;")
        
        # Show results message
        if results.any_ratio_calculated():
            self.apply_btn.setEnabled(True)
            
            msg = ""
            if results.qual_details:
                msg += f"Qualifying:\n"
                msg += f"  Current position: {results.qual_details.current_position:.1f}%\n"
                msg += f"  Target position: {results.qual_details.target_position:.1f}%\n"
                msg += f"  Ratio change: {results.qual_details.ratio_change:+.6f}\n"
                msg += f"  New QualRatio: {results.qual_ratio:.6f}\n\n"
            
            if results.race_details:
                msg += f"Race:\n"
                msg += f"  Current position: {results.race_details.current_position:.1f}%\n"
                msg += f"  Target position: {results.race_details.target_position:.1f}%\n"
                msg += f"  Ratio change: {results.race_details.ratio_change:+.6f}\n"
                msg += f"  New RaceRatio: {results.race_ratio:.6f}\n"
            
            QMessageBox.information(self, "Calculated Ratios", msg)
            
            # Save to CSV
            if self.csv_handler.is_valid():
                self.csv_handler.save_calculation(
                    self.track_name, qual_times, race_times, results, self.config,
                    self.current_qual, self.current_race
                )
                self.status_label.setText(f"✓ Saved to {self.config.historic_csv}")
        else:
            error_msg = ""
            if results.qual_error:
                error_msg += f"Qualifying: {results.qual_error}\n"
            if results.race_error:
                error_msg += f"Race: {results.race_error}"
            QMessageBox.warning(self, "Calculation Error", error_msg)
    
    def get_ratios(self):
        """Return the calculated ratios"""
        return self.new_qual, self.new_race
