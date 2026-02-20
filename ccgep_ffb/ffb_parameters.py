"""FFB Parameters data class and parameter spinbox widget"""

from dataclasses import dataclass
import numpy as np
from PyQt5.QtWidgets import QDoubleSpinBox
from PyQt5.QtCore import Qt


@dataclass
class FFBParameters:
    """Parameters for FFB calculation"""
    gain: float = -1.499866
    pneumatic_trail_nm: float = 0.00001
    suspension_trail_m: float = 0.05
    suspension_scrub_m: float = 0.03
    grip_fract_power: float = 3.0
    gamma: float = 1.0
    caster_angle_deg: float = 10.0
    kpi_angle_deg: float = 15.0
    steering_arm_length_m: float = 0.15
    auto_gain: bool = True
    
    def __post_init__(self):
        # Convert angles to radians
        self.caster_angle_rad = np.radians(self.caster_angle_deg)
        self.kpi_angle_rad = np.radians(self.kpi_angle_deg)
        
        # Ensure gain is negative
        if self.gain > 0:
            self.gain = -self.gain
        
        # Clamp gamma to [0.5, 1.0]
        self.gamma = np.clip(self.gamma, 0.5, 1.0)


class ParameterSpinBox(QDoubleSpinBox):
    """Custom spin box with double-click edit"""
    def __init__(self, param_name, value, min_val=-1e6, max_val=1e6, decimals=6, step=0.1):
        super().__init__()
        self.param_name = param_name
        self.setRange(min_val, max_val)
        self.setDecimals(decimals)
        self.setSingleStep(step)
        self.setValue(value)
        self.setButtonSymbols(QDoubleSpinBox.UpDownArrows)
        self.setMinimumWidth(150)
        self.setStyleSheet("""
            QDoubleSpinBox {
                background-color: #3c3c3c;
                color: #ffffff;
                border: 1px solid #555;
                border-radius: 3px;
                padding: 6px;
                font-weight: bold;
                font-size: 12px;
            }
            QDoubleSpinBox:focus {
                border: 1px solid #4CAF50;
            }
            QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {
                width: 20px;
                background-color: #4CAF50;
                border-radius: 2px;
            }
            QDoubleSpinBox::up-button:hover, QDoubleSpinBox::down-button:hover {
                background-color: #45a049;
            }
        """)
