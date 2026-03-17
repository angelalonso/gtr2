"""
Ratio Calculator GUI for AIW Ratio Editor - COMPACT LAYOUT with Exponential Formula Support
"""

from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
import cfg_manage
import os
from ratio_calc import (
    LapTimes, RatioConfig, RatioCalculator, 
    HistoricCSVHandler, CalculatedRatios, TimeConverter,
    AdjustableExponentialModel, PredictedTimes
)


class ExponentialParamsDialog(QDialog):
    """Dialog for editing exponential model parameters"""
    
    def __init__(self, parent=None, current_params=None):
        super().__init__(parent)
        self.current_params = current_params or {}
        self.setup_ui()
        
    def setup_ui(self):
        self.setWindowTitle("Exponential Model Parameters")
        self.setModal(True)
        self.setMinimumWidth(500)
        self.setMinimumHeight(400)
        
        layout = QVBoxLayout(self)
        
        # Formula display
        formula_group = QGroupBox("Current Formula")
        formula_layout = QVBoxLayout(formula_group)
        
        self.formula_label = QLabel()
        self.formula_label.setWordWrap(True)
        self.formula_label.setStyleSheet("""
            color: #4CAF50; 
            font-size: 13px; 
            font-weight: bold; 
            font-family: 'Courier New', monospace;
            background-color: #1e1e1e;
            padding: 10px;
            border: 1px solid #333;
            border-radius: 3px;
        """)
        self.formula_label.setAlignment(Qt.AlignCenter)
        formula_layout.addWidget(self.formula_label)
        
        layout.addWidget(formula_group)
        
        # Parameters group
        params_group = QGroupBox("Model Parameters")
        params_layout = QGridLayout(params_group)
        params_layout.setVerticalSpacing(10)
        params_layout.setHorizontalSpacing(15)
        
        # Default A (time range)
        params_layout.addWidget(QLabel("A (Time Range):"), 0, 0)
        self.a_spin = QDoubleSpinBox()
        self.a_spin.setRange(10, 1000)
        self.a_spin.setDecimals(1)
        self.a_spin.setSingleStep(10)
        self.a_spin.setValue(self.current_params.get('default_A', 300.0))
        self.a_spin.setSuffix(" s")
        self.a_spin.setToolTip("Time range above minimum (higher = slower at low ratios)")
        self.a_spin.valueChanged.connect(self.update_formula)
        params_layout.addWidget(self.a_spin, 0, 1)
        
        # Default k (decay constant)
        params_layout.addWidget(QLabel("k (Decay Rate):"), 0, 2)
        self.k_spin = QDoubleSpinBox()
        self.k_spin.setRange(0.1, 10)
        self.k_spin.setDecimals(3)
        self.k_spin.setSingleStep(0.1)
        self.k_spin.setValue(self.current_params.get('default_k', 3.0))
        self.k_spin.setToolTip("How quickly times improve with ratio (higher = steeper curve)")
        self.k_spin.valueChanged.connect(self.update_formula)
        params_layout.addWidget(self.k_spin, 0, 3)
        
        # Default B (fastest time)
        params_layout.addWidget(QLabel("B (Fastest Time):"), 1, 0)
        self.b_spin = QDoubleSpinBox()
        self.b_spin.setRange(30, 500)
        self.b_spin.setDecimals(1)
        self.b_spin.setSingleStep(5)
        self.b_spin.setValue(self.current_params.get('default_B', 100.0))
        self.b_spin.setSuffix(" s")
        self.b_spin.setToolTip("Theoretical fastest possible AI time (asymptote)")
        self.b_spin.valueChanged.connect(self.update_formula)
        params_layout.addWidget(self.b_spin, 1, 1)
        
        # Power factor (p)
        params_layout.addWidget(QLabel("p (Power Factor):"), 1, 2)
        self.p_spin = QDoubleSpinBox()
        self.p_spin.setRange(0.1, 5)
        self.p_spin.setDecimals(2)
        self.p_spin.setSingleStep(0.1)
        self.p_spin.setValue(self.current_params.get('power_factor', 1.0))
        self.p_spin.setToolTip("Curve shape modifier (<1 = faster initial drop, >1 = gentler initial drop)")
        self.p_spin.valueChanged.connect(self.update_formula)
        params_layout.addWidget(self.p_spin, 1, 3)
        
        # Ratio offset (R0)
        params_layout.addWidget(QLabel("R₀ (Ratio Offset):"), 2, 0)
        self.r0_spin = QDoubleSpinBox()
        self.r0_spin.setRange(-5, 5)
        self.r0_spin.setDecimals(2)
        self.r0_spin.setSingleStep(0.1)
        self.r0_spin.setValue(self.current_params.get('ratio_offset', 0.0))
        self.r0_spin.setToolTip("Horizontal shift (positive = need higher ratio for same time)")
        self.r0_spin.valueChanged.connect(self.update_formula)
        params_layout.addWidget(self.r0_spin, 2, 1)
        
        # Min ratio
        params_layout.addWidget(QLabel("Min Ratio:"), 2, 2)
        self.min_spin = QDoubleSpinBox()
        self.min_spin.setRange(0.01, 1)
        self.min_spin.setDecimals(2)
        self.min_spin.setSingleStep(0.05)
        self.min_spin.setValue(self.current_params.get('min_ratio', 0.1))
        self.min_spin.setToolTip("Minimum allowed ratio")
        params_layout.addWidget(self.min_spin, 2, 3)
        
        # Max ratio
        params_layout.addWidget(QLabel("Max Ratio:"), 3, 0)
        self.max_spin = QDoubleSpinBox()
        self.max_spin.setRange(1, 20)
        self.max_spin.setDecimals(2)
        self.max_spin.setSingleStep(0.5)
        self.max_spin.setValue(self.current_params.get('max_ratio', 10.0))
        self.max_spin.setToolTip("Maximum allowed ratio")
        params_layout.addWidget(self.max_spin, 3, 1)
        
        layout.addWidget(params_group)
        
        # Description group
        desc_group = QGroupBox("Parameter Descriptions")
        desc_layout = QVBoxLayout(desc_group)
        
        desc_text = QLabel(
            "• <b>A</b>: Time range above minimum - higher values make AI slower at low ratios<br>"
            "• <b>k</b>: Decay rate - higher values make times improve faster as ratio increases<br>"
            "• <b>B</b>: Fastest possible time - AI cannot go faster than this<br>"
            "• <b>p</b>: Power factor - changes curve shape (<1 steeper start, >1 gentler start)<br>"
            "• <b>R₀</b>: Ratio offset - shifts the curve horizontally"
        )
        desc_text.setWordWrap(True)
        desc_text.setTextFormat(Qt.RichText)
        desc_text.setStyleSheet("color: #888; font-size: 11px; padding: 5px;")
        desc_layout.addWidget(desc_text)
        
        layout.addWidget(desc_group)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.defaults_btn = QPushButton("Restore Defaults")
        self.defaults_btn.setFixedHeight(30)
        self.defaults_btn.clicked.connect(self.restore_defaults)
        button_layout.addWidget(self.defaults_btn)
        
        button_layout.addStretch()
        
        self.ok_btn = QPushButton("OK")
        self.ok_btn.setFixedHeight(30)
        self.ok_btn.setFixedWidth(100)
        self.ok_btn.clicked.connect(self.accept)
        button_layout.addWidget(self.ok_btn)
        
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setFixedHeight(30)
        self.cancel_btn.setFixedWidth(100)
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)
        
        layout.addLayout(button_layout)
        
        # Initial formula update
        self.update_formula()
    
    def update_formula(self):
        """Update the formula display with current parameters"""
        A = self.a_spin.value()
        k = self.k_spin.value()
        B = self.b_spin.value()
        p = self.p_spin.value()
        R0 = self.r0_spin.value()
        
        # Format R0 with sign
        if R0 >= 0:
            R0_str = f"+{R0:.2f}"
        else:
            R0_str = f"{R0:.2f}"
        
        if p == 1.0:
            formula = f"R = {R0_str} + (-(1/{k:.3f}) × ln((T - {B:.1f})/{A:.1f}))"
        else:
            formula = f"R = {R0_str} + (-(1/{k:.3f}) × ln((T - {B:.1f})/{A:.1f}))^(1/{p:.2f})"
        
        self.formula_label.setText(formula)
    
    def restore_defaults(self):
        """Restore default parameter values"""
        self.a_spin.setValue(300.0)
        self.k_spin.setValue(3.0)
        self.b_spin.setValue(100.0)
        self.p_spin.setValue(1.0)
        self.r0_spin.setValue(0.0)
        self.min_spin.setValue(0.1)
        self.max_spin.setValue(10.0)
    
    def get_params(self):
        """Get the current parameter values"""
        return {
            'default_A': self.a_spin.value(),
            'default_k': self.k_spin.value(),
            'default_B': self.b_spin.value(),
            'power_factor': self.p_spin.value(),
            'ratio_offset': self.r0_spin.value(),
            'min_ratio': self.min_spin.value(),
            'max_ratio': self.max_spin.value()
        }


class RatioCalculatorDialog(QDialog):
    """Main dialog for ratio calculator"""
    
    def __init__(self, parent=None, track_name="", current_qual=1.0, current_race=1.0):
        super().__init__(parent)
        self.track_name = track_name
        self.current_qual = current_qual
        self.current_race = current_race
        self.new_qual = current_qual
        self.new_race = current_race
        self.calculator = RatioCalculator()  # Create calculator instance
        
        # Load configuration
        self.config = RatioConfig(
            historic_csv=cfg_manage.get_historic_csv() or "",
            goal_percent=cfg_manage.get_goal_percent(),
            goal_offset=cfg_manage.get_goal_offset(),
            percent_ratio=cfg_manage.get_percent_ratio(),
            use_exponential_model=cfg_manage.get_use_exponential_model(),
            exponential_default_A=cfg_manage.get_exponential_param('default_A', 300.0),
            exponential_default_k=cfg_manage.get_exponential_param('default_k', 3.0),
            exponential_default_B=cfg_manage.get_exponential_param('default_B', 100.0),
            exponential_power_factor=cfg_manage.get_exponential_param('power_factor', 1.0),
            exponential_ratio_offset=cfg_manage.get_exponential_param('ratio_offset', 0.0),
            exponential_min_ratio=cfg_manage.get_exponential_param('min_ratio', 0.1),
            exponential_max_ratio=cfg_manage.get_exponential_param('max_ratio', 10.0)
        )
        
        # Initialize CSV handler
        self.csv_handler = HistoricCSVHandler(self.config.historic_csv)
        
        # Load historic data for exponential models if available
        if self.config.historic_csv and os.path.exists(self.config.historic_csv):
            self.calculator.load_historic_data(self.config.historic_csv)
        
        self.setup_ui()
        self.setup_connections()
        
    def setup_ui(self):
        self.setWindowTitle(f"Ratio Calculator - {self.track_name}")
        self.setModal(True)
        self.setMinimumWidth(1300)  # Wider for new displays
        self.setMinimumHeight(1200)  # Taller for new displays
        
        # Set dark background
        self.setStyleSheet("""
            QDialog {
                background-color: #2b2b2b;
            }
            QLabel {
                color: white;
                font-size: 11px;
            }
            QGroupBox {
                color: #4CAF50;
                font-weight: bold;
                border: 2px solid #555;
                border-radius: 5px;
                margin-top: 8px;
                padding-top: 8px;
                font-size: 12px;
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
                padding: 6px;
                font-weight: bold;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:disabled {
                background-color: #666;
            }
            QSpinBox, QDoubleSpinBox, QComboBox {
                background-color: #3c3c3c;
                color: white;
                border: 1px solid #4CAF50;
                border-radius: 3px;
                padding: 2px;
                font-size: 11px;
                min-height: 20px;
                max-height: 22px;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid #4CAF50;
                margin-right: 5px;
            }
            QLineEdit {
                background-color: #3c3c3c;
                color: white;
                border: 1px solid #4CAF50;
                border-radius: 3px;
                padding: 3px;
                font-size: 11px;
                min-height: 20px;
                max-height: 22px;
            }
        """)
        
        # Main layout - vertical stack
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(15, 15, 15, 15)
        
        # Title
        title = QLabel(f"<h2>Ratio Calculator - {self.track_name}</h2>")
        title.setTextFormat(Qt.RichText)
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # ===== CONFIGURATION SECTION =====
        config_group = QGroupBox("Configuration")
        config_layout = QVBoxLayout(config_group)
        config_layout.setSpacing(8)
        
        # Track info and current ratios
        info_layout = QHBoxLayout()
        info_layout.addWidget(QLabel(f"Track: {self.track_name}"))
        info_layout.addStretch()
        info_layout.addWidget(QLabel(f"Current QualRatio:"))
        self.qual_display = QLabel(f"{self.current_qual:.6f}")
        self.qual_display.setStyleSheet("color: #9C27B0; font-weight: bold;")
        info_layout.addWidget(self.qual_display)
        info_layout.addSpacing(20)
        info_layout.addWidget(QLabel(f"Current RaceRatio:"))
        self.race_display = QLabel(f"{self.current_race:.6f}")
        self.race_display.setStyleSheet("color: #9C27B0; font-weight: bold;")
        info_layout.addWidget(self.race_display)
        config_layout.addLayout(info_layout)
        
        # CSV path
        csv_layout = QHBoxLayout()
        csv_layout.addWidget(QLabel("Historic CSV:"))
        self.csv_path = QLineEdit(self.config.historic_csv)
        self.csv_path.setReadOnly(True)
        self.csv_path.setMinimumWidth(300)
        self.csv_path.setFixedHeight(24)
        csv_layout.addWidget(self.csv_path)
        
        self.csv_browse = QPushButton("Browse")
        self.csv_browse.setFixedHeight(24)
        self.csv_browse.setFixedWidth(80)
        self.csv_browse.clicked.connect(self.browse_csv)
        csv_layout.addWidget(self.csv_browse)
        csv_layout.addStretch()
        config_layout.addLayout(csv_layout)
        
        layout.addWidget(config_group)
        
        # ===== CURRENT VALUES SECTION =====
        values_group = QGroupBox("Current Values (editable)")
        values_layout = QGridLayout(values_group)
        values_layout.setVerticalSpacing(8)
        values_layout.setHorizontalSpacing(15)
        
        # Goal Percent
        values_layout.addWidget(QLabel("Goal Percent (%):"), 0, 0)
        self.goal_percent = QDoubleSpinBox()
        self.goal_percent.setRange(0, 100)
        self.goal_percent.setDecimals(1)
        self.goal_percent.setSingleStep(1)
        self.goal_percent.setValue(self.config.goal_percent)
        self.goal_percent.setSuffix("%")
        self.goal_percent.setFixedHeight(24)
        self.goal_percent.setMinimumWidth(120)
        self.goal_percent.valueChanged.connect(self.on_config_changed)
        values_layout.addWidget(self.goal_percent, 0, 1)
        
        # Goal Offset
        values_layout.addWidget(QLabel("Goal Offset:"), 0, 2)
        self.goal_offset = QDoubleSpinBox()
        self.goal_offset.setRange(-100, 100)
        self.goal_offset.setDecimals(2)
        self.goal_offset.setSingleStep(0.1)
        self.goal_offset.setValue(self.config.goal_offset)
        self.goal_offset.setFixedHeight(24)
        self.goal_offset.setMinimumWidth(120)
        self.goal_offset.valueChanged.connect(self.on_config_changed)
        values_layout.addWidget(self.goal_offset, 0, 3)
        
        # Percent Ratio
        values_layout.addWidget(QLabel("Percent Ratio:"), 1, 0)
        self.percent_ratio = QDoubleSpinBox()
        self.percent_ratio.setRange(0.001, 1.0)
        self.percent_ratio.setDecimals(3)
        self.percent_ratio.setSingleStep(0.01)
        self.percent_ratio.setValue(self.config.percent_ratio)
        self.percent_ratio.setToolTip("Ratio change per 1% shift (default: 0.01) - Only used for linear method")
        self.percent_ratio.setFixedHeight(24)
        self.percent_ratio.setMinimumWidth(120)
        self.percent_ratio.valueChanged.connect(self.on_config_changed)
        values_layout.addWidget(self.percent_ratio, 1, 1)
        
        # Calculation Method
        values_layout.addWidget(QLabel("Method:"), 1, 2)
        self.method_combo = QComboBox()
        self.method_combo.addItem("Linear (% ratio based)", False)
        self.method_combo.addItem("Exponential (track history based)", True)
        self.method_combo.setCurrentIndex(1 if self.config.use_exponential_model else 0)
        self.method_combo.setFixedHeight(24)
        self.method_combo.setMinimumWidth(200)
        self.method_combo.currentIndexChanged.connect(self.on_method_changed)
        values_layout.addWidget(self.method_combo, 1, 3)
        
        # Exponential Parameters button
        self.params_btn = QPushButton("Edit Exponential Parameters")
        self.params_btn.setFixedHeight(28)
        self.params_btn.setFixedWidth(180)
        self.params_btn.setCursor(Qt.PointingHandCursor)
        self.params_btn.clicked.connect(self.edit_exponential_params)
        self.params_btn.setStyleSheet("""
            QPushButton {
                background-color: #FFA500;
                color: black;
                border: none;
                border-radius: 3px;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #FFB52E;
            }
        """)
        values_layout.addWidget(self.params_btn, 2, 0, 1, 2)
        
        # Save button
        self.save_btn = QPushButton("Save to cfg.yml")
        self.save_btn.setFixedHeight(28)
        self.save_btn.setFixedWidth(130)
        self.save_btn.setCursor(Qt.PointingHandCursor)
        self.save_btn.clicked.connect(self.save_configuration)
        self.save_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 3px;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        values_layout.addWidget(self.save_btn, 2, 3, Qt.AlignRight)
        
        # Track model status
        self.model_status = QLabel("")
        self.model_status.setStyleSheet("color: #FFA500; font-size: 10px;")
        values_layout.addWidget(self.model_status, 3, 0, 1, 4)
        
        layout.addWidget(values_group)
        
        # ===== FORMULA DISPLAY SECTION (PROMINENT) =====
        formula_group = QGroupBox("Active Formula")
        formula_group.setStyleSheet("""
            QGroupBox {
                color: #FFA500;
                font-weight: bold;
                border: 2px solid #FFA500;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
                font-size: 13px;
            }
        """)
        
        formula_layout = QVBoxLayout(formula_group)
        formula_layout.setSpacing(8)
        
        # Formula title with method
        self.formula_title = QLabel("Linear Method")
        self.formula_title.setStyleSheet("color: #FFA500; font-size: 14px; font-weight: bold;")
        formula_layout.addWidget(self.formula_title)
        
        # Main formula display (bigger font, prominent)
        self.formula_display = QLabel()
        self.formula_display.setWordWrap(True)
        self.formula_display.setStyleSheet("""
            color: #4CAF50; 
            font-size: 16px; 
            font-weight: bold; 
            font-family: 'Courier New', monospace;
            background-color: #1e1e1e;
            padding: 12px;
            border: 2px solid #FFA500;
            border-radius: 5px;
        """)
        self.formula_display.setAlignment(Qt.AlignCenter)
        formula_layout.addWidget(self.formula_display)
        
        # Parameter display
        self.param_display = QLabel()
        self.param_display.setWordWrap(True)
        self.param_display.setStyleSheet("color: #888; font-size: 12px; font-family: 'Courier New', monospace;")
        self.param_display.setAlignment(Qt.AlignCenter)
        formula_layout.addWidget(self.param_display)
        
        # Source info
        self.source_display = QLabel()
        self.source_display.setStyleSheet("color: #FFA500; font-size: 11px; font-style: italic;")
        self.source_display.setAlignment(Qt.AlignCenter)
        formula_layout.addWidget(self.source_display)
        
        layout.addWidget(formula_group)
        
        # ===== PREDICTED TIMES SECTION =====
        predict_group = QGroupBox("Predicted AI Times at New Ratio")
        predict_layout = QGridLayout(predict_group)
        predict_layout.setVerticalSpacing(8)
        predict_layout.setHorizontalSpacing(15)
        
        # Headers
        predict_layout.addWidget(QLabel(""), 0, 0)
        predict_layout.addWidget(QLabel("Best AI"), 0, 1)
        predict_layout.addWidget(QLabel("Worst AI"), 0, 2)
        predict_layout.addWidget(QLabel("Median AI"), 0, 3)
        predict_layout.addWidget(QLabel("Spread"), 0, 4)
        
        # Qualifying predictions
        predict_layout.addWidget(QLabel("Qualifying:"), 1, 0)
        
        self.qual_pred_best = QLabel("---")
        self.qual_pred_best.setStyleSheet("color: #4CAF50; font-weight: bold;")
        predict_layout.addWidget(self.qual_pred_best, 1, 1)
        
        self.qual_pred_worst = QLabel("---")
        self.qual_pred_worst.setStyleSheet("color: #f44336; font-weight: bold;")
        predict_layout.addWidget(self.qual_pred_worst, 1, 2)
        
        self.qual_pred_median = QLabel("---")
        self.qual_pred_median.setStyleSheet("color: #FFA500; font-weight: bold;")
        predict_layout.addWidget(self.qual_pred_median, 1, 3)
        
        self.qual_pred_spread = QLabel("---")
        self.qual_pred_spread.setStyleSheet("color: #888; font-weight: bold;")
        predict_layout.addWidget(self.qual_pred_spread, 1, 4)
        
        # Race predictions
        predict_layout.addWidget(QLabel("Race:"), 2, 0)
        
        self.race_pred_best = QLabel("---")
        self.race_pred_best.setStyleSheet("color: #4CAF50; font-weight: bold;")
        predict_layout.addWidget(self.race_pred_best, 2, 1)
        
        self.race_pred_worst = QLabel("---")
        self.race_pred_worst.setStyleSheet("color: #f44336; font-weight: bold;")
        predict_layout.addWidget(self.race_pred_worst, 2, 2)
        
        self.race_pred_median = QLabel("---")
        self.race_pred_median.setStyleSheet("color: #FFA500; font-weight: bold;")
        predict_layout.addWidget(self.race_pred_median, 2, 3)
        
        self.race_pred_spread = QLabel("---")
        self.race_pred_spread.setStyleSheet("color: #888; font-weight: bold;")
        predict_layout.addWidget(self.race_pred_spread, 2, 4)
        
        layout.addWidget(predict_group)
        
        # ===== QUALIFYING SECTION =====
        qual_group = QGroupBox("Qualifying")
        qual_layout = QGridLayout(qual_group)
        qual_layout.setVerticalSpacing(8)
        qual_layout.setHorizontalSpacing(15)
        
        # Column headers
        qual_layout.addWidget(QLabel(""), 0, 0)
        qual_layout.addWidget(QLabel("Minutes"), 0, 1)
        qual_layout.addWidget(QLabel("Seconds"), 0, 2)
        qual_layout.addWidget(QLabel("Milliseconds"), 0, 3)
        qual_layout.addWidget(QLabel("Total"), 0, 4)
        
        # Best AI
        qual_layout.addWidget(QLabel("Best AI:"), 1, 0)
        self.qual_best_min = self.create_time_spinbox(0, 99)
        qual_layout.addWidget(self.qual_best_min, 1, 1)
        self.qual_best_sec = self.create_time_spinbox(0, 59)
        qual_layout.addWidget(self.qual_best_sec, 1, 2)
        self.qual_best_ms = self.create_time_spinbox(0, 999)
        self.qual_best_ms.setSingleStep(10)
        qual_layout.addWidget(self.qual_best_ms, 1, 3)
        self.qual_best_total = QLabel("0.000s")
        self.qual_best_total.setStyleSheet("color: #4CAF50; font-weight: bold;")
        qual_layout.addWidget(self.qual_best_total, 1, 4)
        
        # Worst AI
        qual_layout.addWidget(QLabel("Worst AI:"), 2, 0)
        self.qual_worst_min = self.create_time_spinbox(0, 99)
        qual_layout.addWidget(self.qual_worst_min, 2, 1)
        self.qual_worst_sec = self.create_time_spinbox(0, 59)
        qual_layout.addWidget(self.qual_worst_sec, 2, 2)
        self.qual_worst_ms = self.create_time_spinbox(0, 999)
        self.qual_worst_ms.setSingleStep(10)
        qual_layout.addWidget(self.qual_worst_ms, 2, 3)
        self.qual_worst_total = QLabel("0.000s")
        self.qual_worst_total.setStyleSheet("color: #f44336; font-weight: bold;")
        qual_layout.addWidget(self.qual_worst_total, 2, 4)
        
        # User
        qual_layout.addWidget(QLabel("User:"), 3, 0)
        self.qual_user_min = self.create_time_spinbox(0, 99)
        qual_layout.addWidget(self.qual_user_min, 3, 1)
        self.qual_user_sec = self.create_time_spinbox(0, 59)
        qual_layout.addWidget(self.qual_user_sec, 3, 2)
        self.qual_user_ms = self.create_time_spinbox(0, 999)
        self.qual_user_ms.setSingleStep(10)
        qual_layout.addWidget(self.qual_user_ms, 3, 3)
        self.qual_user_total = QLabel("0.000s")
        self.qual_user_total.setStyleSheet("color: #9C27B0; font-weight: bold;")
        qual_layout.addWidget(self.qual_user_total, 3, 4)
        
        layout.addWidget(qual_group)
        
        # ===== RACE SECTION =====
        race_group = QGroupBox("Race")
        race_layout = QGridLayout(race_group)
        race_layout.setVerticalSpacing(8)
        race_layout.setHorizontalSpacing(15)
        
        # Column headers
        race_layout.addWidget(QLabel(""), 0, 0)
        race_layout.addWidget(QLabel("Minutes"), 0, 1)
        race_layout.addWidget(QLabel("Seconds"), 0, 2)
        race_layout.addWidget(QLabel("Milliseconds"), 0, 3)
        race_layout.addWidget(QLabel("Total"), 0, 4)
        
        # Best AI
        race_layout.addWidget(QLabel("Best AI:"), 1, 0)
        self.race_best_min = self.create_time_spinbox(0, 99)
        race_layout.addWidget(self.race_best_min, 1, 1)
        self.race_best_sec = self.create_time_spinbox(0, 59)
        race_layout.addWidget(self.race_best_sec, 1, 2)
        self.race_best_ms = self.create_time_spinbox(0, 999)
        self.race_best_ms.setSingleStep(10)
        race_layout.addWidget(self.race_best_ms, 1, 3)
        self.race_best_total = QLabel("0.000s")
        self.race_best_total.setStyleSheet("color: #4CAF50; font-weight: bold;")
        race_layout.addWidget(self.race_best_total, 1, 4)
        
        # Worst AI
        race_layout.addWidget(QLabel("Worst AI:"), 2, 0)
        self.race_worst_min = self.create_time_spinbox(0, 99)
        race_layout.addWidget(self.race_worst_min, 2, 1)
        self.race_worst_sec = self.create_time_spinbox(0, 59)
        race_layout.addWidget(self.race_worst_sec, 2, 2)
        self.race_worst_ms = self.create_time_spinbox(0, 999)
        self.race_worst_ms.setSingleStep(10)
        race_layout.addWidget(self.race_worst_ms, 2, 3)
        self.race_worst_total = QLabel("0.000s")
        self.race_worst_total.setStyleSheet("color: #f44336; font-weight: bold;")
        race_layout.addWidget(self.race_worst_total, 2, 4)
        
        # User
        race_layout.addWidget(QLabel("User:"), 3, 0)
        self.race_user_min = self.create_time_spinbox(0, 99)
        race_layout.addWidget(self.race_user_min, 3, 1)
        self.race_user_sec = self.create_time_spinbox(0, 59)
        race_layout.addWidget(self.race_user_sec, 3, 2)
        self.race_user_ms = self.create_time_spinbox(0, 999)
        self.race_user_ms.setSingleStep(10)
        race_layout.addWidget(self.race_user_ms, 3, 3)
        self.race_user_total = QLabel("0.000s")
        self.race_user_total.setStyleSheet("color: #9C27B0; font-weight: bold;")
        race_layout.addWidget(self.race_user_total, 3, 4)
        
        layout.addWidget(race_group)
        
        # ===== POSITION CALCULATIONS DISPLAY =====
        pos_group = QGroupBox("Position Calculations")
        pos_layout = QGridLayout(pos_group)
        pos_layout.setVerticalSpacing(8)
        pos_layout.setHorizontalSpacing(15)
        
        # Headers
        pos_layout.addWidget(QLabel(""), 0, 0)
        pos_layout.addWidget(QLabel("Current"), 0, 1)
        pos_layout.addWidget(QLabel("Target"), 0, 2)
        pos_layout.addWidget(QLabel("Shift"), 0, 3)
        pos_layout.addWidget(QLabel("Ratio Change"), 0, 4)
        
        # Qualifying row
        pos_layout.addWidget(QLabel("Qualifying:"), 1, 0)
        
        self.qual_current_pos = QLabel("0.0%")
        self.qual_current_pos.setStyleSheet("color: #888; font-weight: bold;")
        pos_layout.addWidget(self.qual_current_pos, 1, 1)
        
        self.qual_target_pos = QLabel(f"{self.config.goal_percent + self.config.goal_offset:.1f}%")
        self.qual_target_pos.setStyleSheet("color: #4CAF50; font-weight: bold;")
        pos_layout.addWidget(self.qual_target_pos, 1, 2)
        
        self.qual_pos_shift = QLabel("0.0%")
        self.qual_pos_shift.setStyleSheet("color: #FFA500; font-weight: bold;")
        pos_layout.addWidget(self.qual_pos_shift, 1, 3)
        
        self.qual_ratio_change = QLabel("0.000000")
        self.qual_ratio_change.setStyleSheet("color: #9C27B0; font-weight: bold;")
        pos_layout.addWidget(self.qual_ratio_change, 1, 4)
        
        # Race row
        pos_layout.addWidget(QLabel("Race:"), 2, 0)
        
        self.race_current_pos = QLabel("0.0%")
        self.race_current_pos.setStyleSheet("color: #888; font-weight: bold;")
        pos_layout.addWidget(self.race_current_pos, 2, 1)
        
        self.race_target_pos = QLabel(f"{self.config.goal_percent + self.config.goal_offset:.1f}%")
        self.race_target_pos.setStyleSheet("color: #4CAF50; font-weight: bold;")
        pos_layout.addWidget(self.race_target_pos, 2, 2)
        
        self.race_pos_shift = QLabel("0.0%")
        self.race_pos_shift.setStyleSheet("color: #FFA500; font-weight: bold;")
        pos_layout.addWidget(self.race_pos_shift, 2, 3)
        
        self.race_ratio_change = QLabel("0.000000")
        self.race_ratio_change.setStyleSheet("color: #9C27B0; font-weight: bold;")
        pos_layout.addWidget(self.race_ratio_change, 2, 4)
        
        layout.addWidget(pos_group)
        
        # ===== RESULTS DISPLAY =====
        results_group = QGroupBox("Results")
        results_layout = QHBoxLayout(results_group)
        results_layout.setSpacing(20)
        
        results_layout.addWidget(QLabel("Method:"))
        self.method_display = QLabel("Linear")
        self.method_display.setStyleSheet("color: #FFA500; font-size: 12px; font-weight: bold;")
        results_layout.addWidget(self.method_display)
        
        results_layout.addSpacing(20)
        
        results_layout.addWidget(QLabel("New QualRatio:"))
        self.new_qual_label = QLabel(f"{self.current_qual:.6f}")
        self.new_qual_label.setStyleSheet("color: #9C27B0; font-size: 12px; font-weight: bold;")
        results_layout.addWidget(self.new_qual_label)
        
        results_layout.addSpacing(30)
        
        results_layout.addWidget(QLabel("New RaceRatio:"))
        self.new_race_label = QLabel(f"{self.current_race:.6f}")
        self.new_race_label.setStyleSheet("color: #9C27B0; font-size: 12px; font-weight: bold;")
        results_layout.addWidget(self.new_race_label)
        
        results_layout.addStretch()
        
        layout.addWidget(results_group)
        
        # ===== BUTTONS =====
        button_layout = QHBoxLayout()
        
        self.calc_btn = QPushButton("Calculate")
        self.calc_btn.setToolTip("This will also add the current times and ratios to historic data")
        self.calc_btn.setFixedHeight(40)
        self.calc_btn.setFixedWidth(200)
        self.calc_btn.setCursor(Qt.PointingHandCursor)
        self.calc_btn.clicked.connect(self.calculate_ratios)
        self.calc_btn.setEnabled(False)
        self.calc_btn.setStyleSheet("""
            QPushButton {
                background-color: #9C27B0;
                color: white;
                border: none;
                border-radius: 4px;
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
        self.apply_btn.setFixedHeight(40)
        self.apply_btn.setFixedWidth(150)
        self.apply_btn.setCursor(Qt.PointingHandCursor)
        self.apply_btn.clicked.connect(self.accept)
        self.apply_btn.setEnabled(False)
        self.apply_btn.setStyleSheet("""
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
            QPushButton:disabled {
                background-color: #666;
                color: #999;
            }
        """)
        button_layout.addWidget(self.apply_btn)
        
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setFixedHeight(40)
        self.cancel_btn.setFixedWidth(150)
        self.cancel_btn.setCursor(Qt.PointingHandCursor)
        self.cancel_btn.clicked.connect(self.reject)
        self.cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                border: none;
                border-radius: 4px;
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
        self.status_label.setStyleSheet("color: #888; font-style: italic; font-size: 11px;")
        layout.addWidget(self.status_label)
        
        # Update model status
        self.update_model_status()
        self.update_formula_display()
    
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
    
    def on_method_changed(self, index):
        """Handle calculation method change"""
        self.config.use_exponential_model = (index == 1)
        self.update_formula_display()  # Update formula display immediately
        self.update_model_status()
        
        # Update method display
        self.method_display.setText("Exponential" if self.config.use_exponential_model else "Linear")
        
        # Enable/disable percent ratio based on method
        self.percent_ratio.setEnabled(not self.config.use_exponential_model)
        if self.config.use_exponential_model:
            self.percent_ratio.setToolTip("Not used in exponential mode")
        else:
            self.percent_ratio.setToolTip("Ratio change per 1% shift (default: 0.01)")
    
    def edit_exponential_params(self):
        """Open dialog to edit exponential parameters"""
        # Get current params
        current_params = {
            'default_A': self.config.exponential_default_A,
            'default_k': self.config.exponential_default_k,
            'default_B': self.config.exponential_default_B,
            'power_factor': self.config.exponential_power_factor,
            'ratio_offset': self.config.exponential_ratio_offset,
            'min_ratio': self.config.exponential_min_ratio,
            'max_ratio': self.config.exponential_max_ratio
        }
        
        dialog = ExponentialParamsDialog(self, current_params)
        if dialog.exec_() == QDialog.Accepted:
            new_params = dialog.get_params()
            
            # Update config
            self.config.exponential_default_A = new_params['default_A']
            self.config.exponential_default_k = new_params['default_k']
            self.config.exponential_default_B = new_params['default_B']
            self.config.exponential_power_factor = new_params['power_factor']
            self.config.exponential_ratio_offset = new_params['ratio_offset']
            self.config.exponential_min_ratio = new_params['min_ratio']
            self.config.exponential_max_ratio = new_params['max_ratio']
            
            # Update calculator
            self.calculator.configure_exponential_model(self.config)
            
            # Update displays
            self.update_formula_display()
            self.update_model_status()
            
            # Save to cfg.yml
            self.save_configuration()
    
    def update_model_status(self):
        """Update the status of exponential model for current track"""
        if self.config.use_exponential_model:
            params = self.calculator.track_db.get_parameters(self.track_name)
            if params:
                self.model_status.setText(f"✓ Exponential model available for {self.track_name} (A={params.A:.1f}, k={params.k:.3f}, B={params.B:.1f}s)")
                self.model_status.setStyleSheet("color: #4CAF50; font-size: 10px;")
            else:
                self.model_status.setText("⚠ No exponential model available for this track - using default parameters")
                self.model_status.setStyleSheet("color: #FFA500; font-size: 10px;")
        else:
            self.model_status.setText("")
    
    def update_formula_display(self, results=None):
        """Update the formula display based on current method and results"""
        if self.config.use_exponential_model:
            # Exponential method
            self.formula_title.setText("Exponential Model")
            
            if results and results.qual_details and results.qual_details.curve_info:
                # Show the actual formula used
                curve_info = results.qual_details.curve_info
                self.formula_display.setText(curve_info.get('formula_inverse', ''))
                
                # Show current parameters
                params = curve_info.get('params', {})
                param_text = f"A={params.get('A', 0):.1f}, k={params.get('k', 0):.3f}, B={params.get('B', 0):.1f}, p={params.get('p', 1.0):.2f}, R₀={params.get('R0', 0):+.2f}"
                self.param_display.setText(param_text)
                
                # Show source
                source = curve_info.get('source', 'default')
                if source == 'track-specific':
                    self.source_display.setText("✓ Using track-specific parameters from historic data")
                    self.source_display.setStyleSheet("color: #4CAF50; font-size: 11px; font-style: italic;")
                else:
                    self.source_display.setText("⚠ Using default parameters (edit with button above)")
                    self.source_display.setStyleSheet("color: #FFA500; font-size: 11px; font-style: italic;")
            else:
                # Show default formula
                A = self.config.exponential_default_A
                k = self.config.exponential_default_k
                B = self.config.exponential_default_B
                p = self.config.exponential_power_factor
                R0 = self.config.exponential_ratio_offset
                
                # Format R0 with sign
                if R0 >= 0:
                    R0_str = f"+{R0:.2f}"
                else:
                    R0_str = f"{R0:.2f}"
                
                if p == 1.0:
                    formula = f"R = {R0_str} + (-(1/{k:.3f}) × ln((T - {B:.1f})/{A:.1f}))"
                else:
                    formula = f"R = {R0_str} + (-(1/{k:.3f}) × ln((T - {B:.1f})/{A:.1f}))^(1/{p:.2f})"
                
                self.formula_display.setText(formula)
                self.param_display.setText(f"A={A:.1f}, k={k:.3f}, B={B:.1f}, p={p:.2f}, R₀={R0:+.2f}")
                self.source_display.setText("Enter times and click Calculate to use formula")
        else:
            # Linear method
            self.formula_title.setText("Linear Method")
            self.formula_display.setText("R = Current_Ratio + (Target_Position - Current_Position) × Percent_Ratio")
            
            target = self.goal_percent.value() + self.goal_offset.value()
            params_text = f"Goal: {target:.1f}%, Percent Ratio: {self.percent_ratio.value():.3f}"
            self.param_display.setText(params_text)
            self.source_display.setText("Linear interpolation between AI best and worst times")
    
    def update_predicted_times(self, results):
        """Update the predicted times display"""
        if results and results.qual_details and results.qual_details.predicted_times:
            pred = results.qual_details.predicted_times
            self.qual_pred_best.setText(f"{pred.best:.3f}s")
            self.qual_pred_worst.setText(f"{pred.worst:.3f}s")
            self.qual_pred_median.setText(f"{pred.median:.3f}s")
            self.qual_pred_spread.setText(f"{pred.spread:.3f}s")
        else:
            self.qual_pred_best.setText("---")
            self.qual_pred_worst.setText("---")
            self.qual_pred_median.setText("---")
            self.qual_pred_spread.setText("---")
        
        if results and results.race_details and results.race_details.predicted_times:
            pred = results.race_details.predicted_times
            self.race_pred_best.setText(f"{pred.best:.3f}s")
            self.race_pred_worst.setText(f"{pred.worst:.3f}s")
            self.race_pred_median.setText(f"{pred.median:.3f}s")
            self.race_pred_spread.setText(f"{pred.spread:.3f}s")
        else:
            self.race_pred_best.setText("---")
            self.race_pred_worst.setText("---")
            self.race_pred_median.setText("---")
            self.race_pred_spread.setText("---")
    
    def update_target_positions(self):
        """Update target position displays"""
        target = self.goal_percent.value() + self.goal_offset.value()
        self.qual_target_pos.setText(f"{target:.1f}%")
        self.race_target_pos.setText(f"{target:.1f}%")
        
        # Recalculate positions with new target
        self.update_qual_calculations()
        self.update_race_calculations()
        self.update_formula_display()
    
    def create_time_spinbox(self, min_val, max_val):
        """Create a compact spinbox for time input"""
        spin = QSpinBox()
        spin.setRange(min_val, max_val)
        spin.setValue(0)
        spin.setFixedHeight(24)
        spin.setFixedWidth(70)
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
            # Update CSV handler and reload models
            self.csv_handler = HistoricCSVHandler(self.config.historic_csv)
            if os.path.exists(file_path):
                self.calculator.load_historic_data(file_path)
            self.update_model_status()
    
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
        self.config.use_exponential_model = cfg_manage.get_use_exponential_model()
        self.config.exponential_default_A = cfg_manage.get_exponential_param('default_A', 300.0)
        self.config.exponential_default_k = cfg_manage.get_exponential_param('default_k', 3.0)
        self.config.exponential_default_B = cfg_manage.get_exponential_param('default_B', 100.0)
        self.config.exponential_power_factor = cfg_manage.get_exponential_param('power_factor', 1.0)
        self.config.exponential_ratio_offset = cfg_manage.get_exponential_param('ratio_offset', 0.0)
        self.config.exponential_min_ratio = cfg_manage.get_exponential_param('min_ratio', 0.1)
        self.config.exponential_max_ratio = cfg_manage.get_exponential_param('max_ratio', 10.0)
        
        # Update UI
        self.csv_path.setText(self.config.historic_csv)
        self.goal_percent.setValue(self.config.goal_percent)
        self.goal_offset.setValue(self.config.goal_offset)
        self.percent_ratio.setValue(self.config.percent_ratio)
        self.method_combo.setCurrentIndex(1 if self.config.use_exponential_model else 0)
        
        # Update CSV handler and reload models
        self.csv_handler = HistoricCSVHandler(self.config.historic_csv)
        if self.config.historic_csv and os.path.exists(self.config.historic_csv):
            self.calculator.load_historic_data(self.config.historic_csv)
        
        # Update calculator with new params
        self.calculator.configure_exponential_model(self.config)
        
        self.update_model_status()
        self.update_formula_display()
    
    def save_configuration(self):
        """Save configuration to file"""
        if self.config.historic_csv:
            cfg_manage.update_historic_csv(self.config.historic_csv)
        
        cfg_manage.update_goal_percent(self.config.goal_percent)
        cfg_manage.update_goal_offset(self.config.goal_offset)
        cfg_manage.update_percent_ratio(self.config.percent_ratio)
        cfg_manage.update_use_exponential_model(self.config.use_exponential_model)
        
        # Save exponential parameters
        cfg_manage.update_exponential_param('default_A', self.config.exponential_default_A)
        cfg_manage.update_exponential_param('default_k', self.config.exponential_default_k)
        cfg_manage.update_exponential_param('default_B', self.config.exponential_default_B)
        cfg_manage.update_exponential_param('power_factor', self.config.exponential_power_factor)
        cfg_manage.update_exponential_param('ratio_offset', self.config.exponential_ratio_offset)
        cfg_manage.update_exponential_param('min_ratio', self.config.exponential_min_ratio)
        cfg_manage.update_exponential_param('max_ratio', self.config.exponential_max_ratio)
        
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
                self.qual_current_pos.setStyleSheet("color: #4CAF50; font-weight: bold;")
            elif current_pos < 66:
                self.qual_current_pos.setStyleSheet("color: #FFA500; font-weight: bold;")
            else:
                self.qual_current_pos.setStyleSheet("color: #f44336; font-weight: bold;")
        else:
            self.qual_current_pos.setText("0.0%")
            self.qual_pos_shift.setText("0.0%")
            self.qual_ratio_change.setText("0.000000")
            self.qual_current_pos.setStyleSheet("color: #888; font-weight: bold;")
    
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
                self.race_current_pos.setStyleSheet("color: #4CAF50; font-weight: bold;")
            elif current_pos < 66:
                self.race_current_pos.setStyleSheet("color: #FFA500; font-weight: bold;")
            else:
                self.race_current_pos.setStyleSheet("color: #f44336; font-weight: bold;")
        else:
            self.race_current_pos.setText("0.0%")
            self.race_pos_shift.setText("0.0%")
            self.race_ratio_change.setText("0.000000")
            self.race_current_pos.setStyleSheet("color: #888; font-weight: bold;")
    
    def check_calc_button(self):
        """Enable calculate button if all required fields have values (User value optional)"""
        qual_filled = (self.qual_best_min.value() > 0 or self.qual_best_sec.value() > 0 or self.qual_best_ms.value() > 0) and \
                      (self.qual_worst_min.value() > 0 or self.qual_worst_sec.value() > 0 or self.qual_worst_ms.value() > 0)
        
        race_filled = (self.race_best_min.value() > 0 or self.race_best_sec.value() > 0 or self.race_best_ms.value() > 0) and \
                      (self.race_worst_min.value() > 0 or self.race_worst_sec.value() > 0 or self.race_worst_ms.value() > 0)
        
        # Check if at least one section has Best and Worst values
        has_valid_section = qual_filled or race_filled
        
        self.calc_btn.setEnabled(has_valid_section)
    
    def calculate_ratios(self):
        """Calculate ratios and save to CSV"""
        qual_times = self.get_qual_times()
        race_times = self.get_race_times()
        
        # DEBUG: Print the actual values
        print("=" * 50)
        print("DEBUG - Time Values:")
        print(f"Qualifying - Best: {qual_times.pole:.3f}, Worst: {qual_times.last_ai:.3f}, User: {qual_times.player:.3f}")
        print(f"Race - Best: {race_times.pole:.3f}, Worst: {race_times.last_ai:.3f}, User: {race_times.player:.3f}")
        print(f"Qual AI Spread: {qual_times.ai_spread:.3f}")
        print(f"Race AI Spread: {race_times.ai_spread:.3f}")
        print(f"Qual are_valid(): {qual_times.are_valid()}")
        print(f"Race are_valid(): {race_times.are_valid()}")
        print("=" * 50)
        
        # Save to CSV first (always try to save)
        csv_saved = False
        if self.csv_handler.is_valid():
            # Check what data we have to save
            qual_has_data = qual_times.pole > 0 or qual_times.last_ai > 0 or qual_times.player > 0
            race_has_data = race_times.pole > 0 or race_times.last_ai > 0 or race_times.player > 0
            
            if qual_has_data or race_has_data:
                self.save_to_csv(qual_times, race_times)
                csv_saved = True
                self.status_label.setText(f"✓ Saved to {os.path.basename(self.config.historic_csv)}")
        
        # Update config with current method
        self.config.use_exponential_model = self.method_combo.currentData()
        
        # Configure exponential model if needed
        if self.config.use_exponential_model:
            self.calculator.configure_exponential_model(self.config)
        
        # Calculate ratios using the calculator instance
        results = self.calculator.calculate_all(
            qual_times, race_times, self.config, self.track_name,
            self.current_qual, self.current_race
        )
        
        # DEBUG: Print results
        print("DEBUG - Results:")
        print(f"Qual ratio: {results.qual_ratio}, Qual error: {results.qual_error}")
        print(f"Race ratio: {results.race_ratio}, Race error: {results.race_error}")
        print("=" * 50)
        
        # Update formula display with results
        self.update_formula_display(results)
        
        # Update predicted times
        self.update_predicted_times(results)
        
        # Update displays if we have results
        if results.has_qual_ratio():
            self.new_qual = results.qual_ratio
            self.new_qual_label.setText(f"{self.new_qual:.6f}")
            self.new_qual_label.setStyleSheet("color: #9C27B0; font-size: 12px; font-weight: bold;")
            
            # Update method display based on what was actually used
            if results.qual_details:
                self.method_display.setText(results.qual_details.calculation_method.capitalize())
        
        if results.has_race_ratio():
            self.new_race = results.race_ratio
            self.new_race_label.setText(f"{self.new_race:.6f}")
            self.new_race_label.setStyleSheet("color: #9C27B0; font-size: 12px; font-weight: bold;")
        
        # Build appropriate message based on what succeeded/failed
        if results.any_ratio_calculated():
            self.apply_btn.setEnabled(True)
            
            msg = ""
            if results.qual_details:
                msg += f"Qualifying ({results.qual_details.calculation_method}):\n"
                msg += f"  Current position: {results.qual_details.current_position:.1f}%\n"
                msg += f"  Target position: {results.qual_details.target_position:.1f}%\n"
                msg += f"  Ratio change: {results.qual_details.ratio_change:+.6f}\n"
                msg += f"  New QualRatio: {results.qual_ratio:.6f}\n\n"
                
                # Add predicted times to message
                if results.qual_details.predicted_times:
                    pred = results.qual_details.predicted_times
                    msg += f"  Predicted AI at new ratio:\n"
                    msg += f"    Best: {pred.best:.3f}s\n"
                    msg += f"    Worst: {pred.worst:.3f}s\n"
                    msg += f"    Median: {pred.median:.3f}s\n\n"
            
            if results.race_details:
                msg += f"Race ({results.race_details.calculation_method}):\n"
                msg += f"  Current position: {results.race_details.current_position:.1f}%\n"
                msg += f"  Target position: {results.race_details.target_position:.1f}%\n"
                msg += f"  Ratio change: {results.race_details.ratio_change:+.6f}\n"
                msg += f"  New RaceRatio: {results.race_ratio:.6f}\n"
            
            QMessageBox.information(self, "Calculated Ratios", msg)
        else:
            # Build error message based on what's missing
            error_parts = []
            
            if results.qual_error:
                error_parts.append(f"qualifying ({results.qual_error})")
            if results.race_error:
                error_parts.append(f"race ({results.race_error})")
            
            if error_parts:
                missing_text = " and ".join(error_parts)
                message = f"Values saved to {os.path.basename(self.config.historic_csv) if self.config.historic_csv else 'historic.csv'}.\n"
                message += f"Could not calculate a new ratio because: {missing_text}"
            else:
                message = f"Values saved to {os.path.basename(self.config.historic_csv) if self.config.historic_csv else 'historic.csv'}.\n"
                message += "Could not calculate a new ratio due to invalid time values."
            
            QMessageBox.warning(self, "Calculation Note", message)

    
    def save_to_csv(self, qual_times, race_times):
        """Save data to CSV with semicolon separator"""
        import csv
        from datetime import datetime
        
        file_path = self.config.historic_csv
        if not file_path:
            return
        
        # Prepare the data row
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        row = [
            timestamp,                                   # Timestamp
            self.track_name,                             # Track Name
            f"{self.current_qual:.6f}",                  # Current QualRatio
            f"{qual_times.pole:.3f}" if qual_times.pole > 0 else "0",  # Qual AI Best laptime
            f"{qual_times.last_ai:.3f}" if qual_times.last_ai > 0 else "0",  # Qual AI Worst laptime
            f"{qual_times.player:.3f}" if qual_times.player > 0 else "0",  # Qual User laptime
            f"{self.current_race:.6f}",                  # Current RaceRatio
            f"{race_times.pole:.3f}" if race_times.pole > 0 else "0",  # Race AI Best laptime
            f"{race_times.last_ai:.3f}" if race_times.last_ai > 0 else "0",  # Race AI Worst laptime
            f"{race_times.player:.3f}" if race_times.player > 0 else "0"   # Race User laptime
        ]
        
        # Write to CSV
        file_exists = os.path.isfile(file_path)
        
        try:
            with open(file_path, 'a', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile, delimiter=';')
                
                # Write header if file is new
                if not file_exists or os.path.getsize(file_path) == 0:
                    header = [
                        'Timestamp',
                        'Track Name',
                        'Current QualRatio',
                        'Qual AI Best (s)',
                        'Qual AI Worst (s)',
                        'Qual User (s)',
                        'Current RaceRatio',
                        'Race AI Best (s)',
                        'Race AI Worst (s)',
                        'Race User (s)'
                    ]
                    writer.writerow(header)
                
                writer.writerow(row)
                
                # Reload models after saving new data
                self.calculator.load_historic_data(file_path)
                self.update_model_status()
                
        except Exception as e:
            print(f"Error saving to CSV: {e}")
    
    def get_ratios(self):
        """Return the calculated ratios"""
        return self.new_qual, self.new_race
