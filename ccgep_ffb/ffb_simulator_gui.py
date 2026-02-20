"""FFB Simulator GUI Widget"""

import sys
import numpy as np
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
import pyqtgraph as pg

from ffb_parameters import ParameterSpinBox
from ffb_simulator_core import FFBSimulator


class FFBSimulatorWidget(QMainWindow):
    def __init__(self):
        super().__init__()
        self.simulator = FFBSimulator()
        self.simulator.calculate_all()
        self.setup_ui()
        
    def setup_ui(self):
        self.setWindowTitle("FFB Simulator - Stiff Parking FFB Visualization")
        self.setGeometry(100, 100, 1600, 900)
        
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        
        # Left side - Plot
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        
        self.plot_widget = pg.PlotWidget(title="Force Feedback at Different Tire Loads")
        self.plot_widget.setLabel('left', 'Load (kN)')
        self.plot_widget.setLabel('bottom', 'Tire Slip')
        self.plot_widget.showGrid(x=True, y=True, alpha=0.3)
        self.plot_widget.addLegend()
        self.plot_widget.setBackground('#2b2b2b')
        
        # Create curves with distinct colors
        colors = [
            (100, 149, 237),  # Cornflower blue - Low Load
            (255, 165, 0),     # Orange - Medium Load
            (255, 69, 0)       # Red-Orange - High Load
        ]
        labels = ["Low Load FFB", "Medium Load FFB", "High Load FFB"]
        self.ffb_curves = []
        
        for i, (color, label) in enumerate(zip(colors, labels)):
            curve = self.plot_widget.plot(
                pen=pg.mkPen(color=color, width=2),
                name=label
            )
            self.ffb_curves.append(curve)
        
        # Gripping line (tire curve)
        self.grip_curve = self.plot_widget.plot(
            pen=pg.mkPen(color=(255, 255, 255), width=2),
            name="Gripping line"
        )
        
        # Clipping line at 10000
        clip_x = [0, 100]
        clip_y = [10000, 10000]
        self.clip_curve = self.plot_widget.plot(
            clip_x, clip_y, 
            pen=pg.mkPen(color=(255, 0, 0), width=2, style=Qt.DashLine),
            name="Clipping line"
        )
        
        left_layout.addWidget(self.plot_widget)
        
        # Right side - Parameters
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(10, 10, 10, 10)
        right_layout.setSpacing(15)
        
        # Plugin Parameters group
        param_group = QGroupBox("Plugin Parameters")
        param_group.setStyleSheet("""
            QGroupBox {
                color: #4CAF50;
                font-size: 14px;
                font-weight: bold;
                border: 2px solid #555;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
        """)
        param_layout = QGridLayout()
        param_layout.setVerticalSpacing(10)
        param_layout.setHorizontalSpacing(15)
        
        # Create parameter spinboxes
        self.param_spinboxes = {}
        params = [
            ("gain", "Gain", -1.499866, -1e6, 1e6, 6, 0.1),
            ("pneumatic_trail_nm", "Pneumatic Trail (Nm/N)", 0.00001, 0, 1, 6, 0.000001),
            ("suspension_trail_m", "Suspension Trail (m)", 0.05, 0, 1, 6, 0.001),
            ("suspension_scrub_m", "Suspension Scrub (m)", 0.03, 0, 1, 6, 0.001),
            ("grip_fract_power", "Grip Fract Power", 3.0, 0, 10, 6, 0.1),
            ("gamma", "Gamma", 1.0, 0.5, 1.0, 6, 0.01),
            ("caster_angle_deg", "Caster Angle (deg)", 10.0, -45, 45, 6, 0.5),
            ("kpi_angle_deg", "KPI Angle (deg)", 15.0, -45, 45, 6, 0.5),
            ("steering_arm_length_m", "Steering Arm Length (m)", 0.15, 0.01, 1, 6, 0.01)
        ]
        
        for i, (attr, display, default, min_val, max_val, decimals, step) in enumerate(params):
            row = i // 2
            col = (i % 2) * 2
            
            # Label
            label = QLabel(display)
            label.setStyleSheet("color: #ffffff; font-weight: bold; font-size: 12px;")
            label.setMinimumWidth(150)
            param_layout.addWidget(label, row, col)
            
            # Spinbox
            spinbox = ParameterSpinBox(attr, default, min_val, max_val, decimals, step)
            spinbox.valueChanged.connect(lambda value, a=attr: self.on_parameter_changed(a, value))
            param_layout.addWidget(spinbox, row, col + 1)
            self.param_spinboxes[attr] = spinbox
        
        param_group.setLayout(param_layout)
        right_layout.addWidget(param_group)
        
        # Auto Gain checkbox
        self.auto_gain_cb = QCheckBox("Auto Adjust Gain")
        self.auto_gain_cb.setChecked(self.simulator.params.auto_gain)
        self.auto_gain_cb.setStyleSheet("color: #ffffff; font-size: 12px;")
        self.auto_gain_cb.stateChanged.connect(self.on_auto_gain_changed)
        right_layout.addWidget(self.auto_gain_cb)
        
        # Spreadsheet Params group
        sheet_group = QGroupBox("Spreadsheet Params")
        sheet_group.setStyleSheet("QGroupBox { color: #4CAF50; font-size: 14px; font-weight: bold; }")
        sheet_layout = QVBoxLayout()
        
        # Copy/paste section
        copy_label = QLabel("Copy/paste to CCGEP.in")
        copy_label.setStyleSheet("color: #ffffff; font-weight: bold;")
        sheet_layout.addWidget(copy_label)
        
        self.copy_text = QTextEdit()
        self.copy_text.setMaximumHeight(150)
        self.copy_text.setFont(QFont("Courier New", 10))
        self.copy_text.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #4CAF50;
                border: 1px solid #555;
                border-radius: 3px;
                font-family: 'Courier New';
            }
        """)
        self.update_copy_text()
        sheet_layout.addWidget(self.copy_text)
        
        # Suggested LeoFFB
        leo_label = QLabel("Suggested LeoFFB for 'stiff parking FFB'")
        leo_label.setStyleSheet("color: #ffffff; font-weight: bold; margin-top: 10px;")
        sheet_layout.addWidget(leo_label)
        
        leo_grid = QGridLayout()
        leo_params = [
            ("ffbCCGEPLeoKf", -11500.0),
            ("ffbCCGEPLeoKs", 7.0),
            ("ffbCCGEPLeoA", 1.5),
            ("ffbCCGEPLeoKr", 1.5)
        ]
        
        for i, (param, value) in enumerate(leo_params):
            leo_grid.addWidget(QLabel(param), i, 0)
            val_label = QLabel(f"{value:.6f}")
            val_label.setStyleSheet("background-color: #3c3c3c; padding: 4px; border-radius: 3px;")
            val_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
            leo_grid.addWidget(val_label, i, 1)
        
        sheet_layout.addLayout(leo_grid)
        sheet_group.setLayout(sheet_layout)
        right_layout.addWidget(sheet_group)
        
        # Add to main layout
        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)
        splitter.setSizes([900, 700])
        
        main_layout.addWidget(splitter)
        
        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready - Edit parameters to update graph automatically")
        
        # Initial plot update
        self.update_plot()
    
    def on_parameter_changed(self, param_name, value):
        """Handle parameter changes and auto-update graph"""
        setattr(self.simulator.params, param_name, value)
        
        # Update angles in radians
        if param_name == "caster_angle_deg":
            self.simulator.params.caster_angle_rad = np.radians(value)
        elif param_name == "kpi_angle_deg":
            self.simulator.params.kpi_angle_rad = np.radians(value)
        
        # Auto-update graph
        self.update_graph()
    
    def on_auto_gain_changed(self, state):
        self.simulator.params.auto_gain = (state == Qt.Checked)
        self.update_copy_text()
        self.status_bar.showMessage(f"Auto Gain {'enabled' if state == Qt.Checked else 'disabled'}", 2000)
        # Auto-update graph
        self.update_graph()
    
    def update_copy_text(self):
        """Update the CCGEP.in copy text"""
        p = self.simulator.params
        text = f"""ffbCCGEPGain={p.gain:.15f}
ffbCCGEPPneumaticTrailNM={p.pneumatic_trail_nm}
ffbCCGEPSuspensionTrailM={p.suspension_trail_m}
ffbCCGEPSuspensionScrubM={p.suspension_scrub_m}
ffbCCGEPGripFractPower={p.grip_fract_power}
ffbCCGEPCasterDegrees={p.caster_angle_deg}
ffbCCGEPKPIDegrees={p.kpi_angle_deg}
ffbCCGEPSteeringArmLengthM={p.steering_arm_length_m}
ffbCCGEPTireSpeenInertiaKGM2=
ffbCCGEPRampUpKMH=10.000000
ffbCCGEPGamma={p.gamma}"""
        self.copy_text.setText(text)
    
    def update_graph(self):
        """Recalculate and update the graph"""
        self.status_bar.showMessage("Calculating...")
        QApplication.processEvents()
        
        self.simulator.calculate_all()
        self.update_plot()
        
        # Update parameter spinboxes with new gain if auto gain changed it
        self.param_spinboxes["gain"].setValue(self.simulator.params.gain)
        self.update_copy_text()
        
        self.status_bar.showMessage("Graph updated", 2000)
    
    def update_plot(self):
        """Update the plot with current FFB results"""
        if not self.simulator.ffb_results:
            return
        
        # Update FFB curves (convert to kN for display)
        for i, curve in enumerate(self.ffb_curves):
            if i < len(self.simulator.ffb_results):
                # Convert to kN for display
                ffb_kN = self.simulator.ffb_results[i] / 1000.0
                curve.setData(self.simulator.slip_values, ffb_kN)
        
        # Update gripping line (tire curve)
        # Scale tire curve to reasonable range for display
        tire_scaled = np.array(self.simulator.TIRE_CURVE) * 10000 / 1000.0  # Convert to kN
        self.grip_curve.setData(self.simulator.slip_values, tire_scaled)
        
        # Update clipping line (convert to kN)
        self.clip_curve.setData([0, 100], [10, 10])  # 10 kN = 10000 N
        
        # Auto-range with some padding
        self.plot_widget.autoRange()
        self.plot_widget.setLimits(xMin=0, xMax=100)
