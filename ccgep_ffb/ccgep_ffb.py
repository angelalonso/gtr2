# pipenv install; pipenv run pip install PyQt5 pyqtgraph numpy
# pipenv run python ffb_simulator.py

import sys
import numpy as np
from dataclasses import dataclass
from typing import List
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
import pyqtgraph as pg

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

class FFBSimulator:
    """Simulates Force Feedback based on tire model"""
    
    # Predefined GTR2 slip curve from VBA
    TIRE_CURVE = [
        0.0, 0.0998647816612757, 0.198850437271588, 0.295873493665782,
        0.389644451141353, 0.478747424649196, 0.56178359192142, 0.637554401460092,
        0.705248331276834, 0.764547986620691, 0.815509139440791, 0.858530337038116,
        0.894236140716461, 0.923360033673105, 0.946656989027165, 0.96485363271285,
        0.978639812934221, 0.988654033276242, 0.99528134397826, 0.998528480165178,
        1.0, 0.999541463061979, 0.998237083578454, 0.996193708545235,
        0.99351818495813, 0.990317359812947, 0.986698080105495, 0.982767192831583,
        0.978631544987019, 0.974397983567612, 0.970173355569171, 0.966064507987504,
        0.962178287818419, 0.958558064482702, 0.954720318327627, 0.950615762783142,
        0.946336323007018, 0.94197392415703, 0.937620491390951, 0.933367949866554,
        0.929308224741612, 0.925533241173899, 0.922134924321188, 0.919185333516923,
        0.916416541442141, 0.913716717485577, 0.911085861647233, 0.908523973927107,
        0.906031054325201, 0.903607102841513, 0.901252119476043, 0.898966104228793,
        0.896749057099761, 0.894600978088949, 0.892521867196355, 0.890511724421979,
        0.888570549765823, 0.886698343227885, 0.884895104808166, 0.883160834506666,
        0.881495532323385, 0.87989909911099, 0.878344786015002, 0.876811700347376,
        0.87529984210811, 0.873809211297205, 0.872339807914662, 0.870891631960479,
        0.869464683434658, 0.868058962337197, 0.866674468668097, 0.865311202427359,
        0.863969163614981, 0.862648352230965, 0.861348768275309, 0.860070411748015,
        0.858813282649081, 0.857577380978508, 0.856362706736297, 0.855169259922446,
        0.853997040536956, 0.852846048579828, 0.85171628405106, 0.850607746950653,
        0.849520437278608, 0.848454355034923, 0.8474095002196, 0.846385872832637,
        0.845383472874035, 0.844402300343795, 0.843442355241915, 0.842503637568396,
        0.841586147323239, 0.840689884506442, 0.839814513818727, 0.8389502198343,
        0.838092459357331, 0.837241232387822, 0.836396538925772, 0.835558378971181,
        0.834726752524049, 0.833901659584376, 0.833083100152162, 0.832271074227408,
        0.831465581810112, 0.830666622900276, 0.829874197497898, 0.82908830560298,
        0.828308947215521, 0.82753612233552, 0.826769830962979, 0.826010073097897,
        0.825256848740274, 0.82451015789011, 0.823770000547405, 0.82303637671216,
        0.822309286384373, 0.821588729564045, 0.820874706251177, 0.820167216445768,
        0.819466260147817, 0.818771837357326, 0.818083948074294, 0.817402592298721,
        0.816727770030607, 0.816059481269952, 0.815397726016756, 0.814742504271019,
        0.814093816032741, 0.813451661301923, 0.812816040078563, 0.812186952362663,
        0.811564398154221, 0.810948377453239, 0.810338890259716, 0.809735936573652,
        0.809139516395047, 0.808549629723901, 0.807966276560214, 0.807389456903986,
        0.806819170755217, 0.806255418113908, 0.805698198980057, 0.805147513353666,
        0.804603361234733, 0.80406574262326, 0.803534657519245, 0.80301010592269,
        0.802492087833594, 0.801980603251957, 0.8
    ]
    
    def __init__(self):
        self.params = FFBParameters()
        self.curve_size = len(self.TIRE_CURVE) - 1  # 150
        
        # Calculate grip fraction curve
        self.grip_fract = self._calculate_grip_fraction()
        
        # Define load cases (inside/outside tire loads in N)
        self.load_cases = [
            (1000, 4000),  # Low load
            (2000, 6000),  # Medium load
            (3000, 8000)   # High load
        ]
        
        # Calculate mu (friction coefficient) for each load
        self.mu_values = []
        for loads in self.load_cases:
            inside_mu = 2.01 - loads[0] * 0.00012
            outside_mu = 2.01 - loads[1] * 0.00012
            self.mu_values.append((inside_mu, outside_mu))
        
        # Results storage
        self.ffb_results = []  # Will hold 3 arrays of FFB values
        self.slip_values = np.array([i * 0.6 for i in range(self.curve_size + 1)])
        
    def _calculate_grip_fraction(self):
        """Calculate mGripFract from tire curve"""
        grip_fract = np.ones(len(self.TIRE_CURVE))
        for i in range(2, len(self.TIRE_CURVE)):
            if i > 0 and self.TIRE_CURVE[1] != 0:
                grip_fract[i] = (self.TIRE_CURVE[i] / i) / self.TIRE_CURVE[1]
            else:
                grip_fract[i] = 1.0
        return grip_fract
    
    def ffb_4(self, tire_load0, tire_load1, grip_fract0, grip_fract1,
              lat_force0, lat_force1, long_force0=0, long_force1=0):
        """
        FFB_4 function from VBA including caster and KPI effects
        """
        # Pneumatic trail depends on tire load and slip
        pneu_trail0 = self.params.pneumatic_trail_nm * tire_load0 * (grip_fract0 ** self.params.grip_fract_power)
        pneu_trail1 = self.params.pneumatic_trail_nm * tire_load1 * (grip_fract1 ** self.params.grip_fract_power)
        
        # Total torque from lateral forces
        lat_torque0 = pneu_trail0 * lat_force0 + self.params.suspension_trail_m * lat_force0
        lat_torque1 = pneu_trail1 * lat_force1 + self.params.suspension_trail_m * lat_force1
        
        # Longitudinal forces add torque from scrub radius
        long_torque0 = long_force0 * self.params.suspension_scrub_m
        long_torque1 = long_force1 * -self.params.suspension_scrub_m
        
        # Sum torques
        torque0 = lat_torque0 + long_torque0
        torque1 = lat_torque1 + long_torque1
        
        # Convert torque to force at steering arm
        arm_length = self.params.steering_arm_length_m if self.params.steering_arm_length_m != 0 else 0.1
        force0 = torque0 / arm_length
        force1 = torque1 / arm_length
        
        # KPI and caster geometry effects
        kpi_moment0 = np.sin(self.params.kpi_angle_rad) * self.params.suspension_trail_m * tire_load0
        caster_moment0 = np.sin(self.params.caster_angle_rad) * self.params.suspension_scrub_m * tire_load0
        kpi_caster_force0 = (kpi_moment0 + caster_moment0) / arm_length
        
        kpi_moment1 = np.sin(self.params.kpi_angle_rad) * self.params.suspension_trail_m * tire_load1
        caster_moment1 = np.sin(self.params.caster_angle_rad) * self.params.suspension_scrub_m * tire_load1
        kpi_caster_force1 = -((kpi_moment1 + caster_moment1) / arm_length)
        
        # Total force
        total_force0 = force0 + kpi_caster_force0
        total_force1 = force1 + kpi_caster_force1
        
        # Scale and sum
        ffb = (total_force0 + total_force1) * self.params.gain
        
        # Gamma shaping
        x = ffb / 10000.0
        ffb = np.sign(x) * (np.abs(x) ** self.params.gamma) * 10000.0
        
        return ffb
    
    def calculate_all(self):
        """Calculate FFB for all load cases"""
        self.ffb_results = []
        
        for case_idx, ((inside_load, outside_load), (inside_mu, outside_mu)) in enumerate(zip(self.load_cases, self.mu_values)):
            ffb_case = np.zeros(self.curve_size + 1)
            
            for j in range(self.curve_size + 1):
                tire_curve = self.TIRE_CURVE[j]
                grip_fract = self.grip_fract[j]
                
                # Estimate lateral forces
                in_lat_force = inside_load * inside_mu * tire_curve * -1
                out_lat_force = outside_load * outside_mu * tire_curve * -1
                
                # Longitudinal forces set to 0 for this simulation
                in_long_force = 0
                out_long_force = 0
                
                ffb = self.ffb_4(inside_load, outside_load,
                                 grip_fract, grip_fract,
                                 in_lat_force, out_lat_force,
                                 in_long_force, out_long_force)
                
                ffb_case[j] = ffb
            
            self.ffb_results.append(ffb_case)
        
        # Auto gain if enabled
        if self.params.auto_gain:
            self._apply_auto_gain()
    
    def _apply_auto_gain(self):
        """Scale gain to hit 10000 maximum"""
        if not self.ffb_results:
            return
        
        # Find maximum FFB value across all cases
        max_ffb = 0.01
        for ffb_case in self.ffb_results:
            case_max = np.max(np.abs(ffb_case))
            if case_max > max_ffb:
                max_ffb = case_max
        
        # Calculate gain multiplier and apply
        gain_mult = 10000.0 / max_ffb
        self.params.gain *= gain_mult
        
        # Recalculate with new gain
        self.ffb_results = []
        for case_idx, ((inside_load, outside_load), (inside_mu, outside_mu)) in enumerate(zip(self.load_cases, self.mu_values)):
            ffb_case = np.zeros(self.curve_size + 1)
            
            for j in range(self.curve_size + 1):
                tire_curve = self.TIRE_CURVE[j]
                grip_fract = self.grip_fract[j]
                
                in_lat_force = inside_load * inside_mu * tire_curve * -1
                out_lat_force = outside_load * outside_mu * tire_curve * -1
                
                ffb = self.ffb_4(inside_load, outside_load,
                                 grip_fract, grip_fract,
                                 in_lat_force, out_lat_force,
                                 0, 0)
                
                ffb_case[j] = ffb
            
            self.ffb_results.append(ffb_case)

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

def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    # Dark theme
    app.setStyleSheet("""
        QMainWindow, QDialog {
            background-color: #2b2b2b;
        }
        QGroupBox {
            color: #ffffff;
            border: 1px solid #555;
            border-radius: 5px;
            margin-top: 1ex;
            font-weight: bold;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 5px 0 5px;
            color: #4CAF50;
        }
        QLabel {
            color: #ffffff;
        }
        QCheckBox {
            color: #ffffff;
            font-size: 12px;
        }
        QStatusBar {
            color: #ffffff;
            background-color: #3c3c3c;
        }
    """)
    
    window = FFBSimulatorWidget()
    window.show()
    
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
