# pipenv install; pipenv run pip install matplotlib numpy scipy
# pipenv run python3 eng_editor <path to .eng file>
import sys
import re
import numpy as np
from dataclasses import dataclass
from typing import List, Dict, Optional
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
import pyqtgraph as pg
from scipy import interpolate

@dataclass
class TorquePoint:
    rpm: float
    drive_torque: float
    braking_torque: float
    power: float = None
    
    def __post_init__(self):
        if self.power is None:
            self.calculate_power()
    
    def calculate_power(self):
        if self.rpm > 0:
            self.power = self.drive_torque * self.rpm / 7127
        else:
            self.power = 0.0
    
    def update_from_drive_torque(self, new_torque):
        self.drive_torque = new_torque
        self.calculate_power()
    
    def update_from_power(self, new_power):
        self.power = new_power
        if self.rpm > 0:
            self.drive_torque = new_power * 7127 / self.rpm

class ParameterEditDialog(QDialog):
    """Dialog for editing parameter values"""
    
    def __init__(self, key, value, parent=None):
        super().__init__(parent)
        self.key = key
        self.original_value = value
        self.new_value = value
        self.setup_ui()
        
    def setup_ui(self):
        self.setWindowTitle(f"Edit Parameter: {self.key}")
        self.setModal(True)
        self.setMinimumWidth(500)
        
        layout = QVBoxLayout()
        
        # Key display
        key_layout = QHBoxLayout()
        key_layout.addWidget(QLabel("Parameter:"))
        key_label = QLabel(self.key)
        key_label.setStyleSheet("font-weight: bold; color: #4CAF50; font-size: 12px;")
        key_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        key_layout.addWidget(key_label)
        key_layout.addStretch()
        layout.addLayout(key_layout)
        
        # Current value
        current_layout = QHBoxLayout()
        current_layout.addWidget(QLabel("Current:"))
        current_label = QLabel(self.original_value)
        current_label.setStyleSheet("color: #888; font-family: monospace;")
        current_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        current_layout.addWidget(current_label)
        current_layout.addStretch()
        layout.addLayout(current_layout)
        
        # Separator
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        layout.addWidget(line)
        
        # New value input
        layout.addWidget(QLabel("New Value:"))
        
        # Check if it's a tuple
        if self.original_value.startswith('(') and self.original_value.endswith(')'):
            # Tuple editor
            inner = self.original_value[1:-1]
            values = [v.strip() for v in inner.split(',')]
            
            self.tuple_editors = []
            tuple_widget = QWidget()
            tuple_layout = QHBoxLayout(tuple_widget)
            tuple_layout.setContentsMargins(0, 0, 0, 0)
            
            for i, val in enumerate(values):
                editor = QLineEdit(val)
                editor.setPlaceholderText(f"Value {i+1}")
                editor.textChanged.connect(lambda text, idx=i: self.update_tuple_value(idx, text))
                editor.setMinimumWidth(100)
                tuple_layout.addWidget(editor)
                self.tuple_editors.append(editor)
            
            layout.addWidget(tuple_widget)
            self.value_editor = None
            
        else:
            # Try to determine if it's a number
            try:
                float(self.original_value)
                # Number editor
                self.value_editor = QDoubleSpinBox()
                self.value_editor.setRange(-1e12, 1e12)
                self.value_editor.setDecimals(6)
                self.value_editor.setValue(float(self.original_value))
                self.value_editor.valueChanged.connect(self.on_value_changed)
                self.value_editor.setMinimumWidth(200)
                layout.addWidget(self.value_editor)
            except ValueError:
                # String editor
                self.value_editor = QLineEdit(self.original_value)
                self.value_editor.textChanged.connect(self.on_text_changed)
                self.value_editor.setMinimumWidth(300)
                layout.addWidget(self.value_editor)
        
        # Preview of new value (for complex edits)
        self.preview_label = QLabel()
        self.preview_label.setStyleSheet("color: #4CAF50; font-family: monospace; padding: 5px;")
        layout.addWidget(self.preview_label)
        self.update_preview()
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.save_btn = QPushButton("💾 Save")
        self.save_btn.clicked.connect(self.accept)
        self.save_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                padding: 8px 15px;
                font-weight: bold;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        
        self.revert_btn = QPushButton("↺ Revert to Original")
        self.revert_btn.clicked.connect(self.revert_to_original)
        self.revert_btn.setStyleSheet("""
            QPushButton {
                background-color: #ff9800;
                color: white;
                padding: 8px 15px;
                font-weight: bold;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #f57c00;
            }
        """)
        
        self.cancel_btn = QPushButton("✖ Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        self.cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                padding: 8px 15px;
                font-weight: bold;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #da190b;
            }
        """)
        
        button_layout.addWidget(self.save_btn)
        button_layout.addWidget(self.revert_btn)
        button_layout.addWidget(self.cancel_btn)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
    
    def update_tuple_value(self, index, text):
        """Update tuple value at index"""
        values = []
        for i, editor in enumerate(self.tuple_editors):
            val = editor.text()
            if i == index:
                val = text
            values.append(val)
        
        self.new_value = f"({', '.join(values)})"
        self.update_preview()
    
    def on_value_changed(self, value):
        self.new_value = str(value)
        self.update_preview()
    
    def on_text_changed(self, text):
        self.new_value = text
        self.update_preview()
    
    def update_preview(self):
        """Update the preview label"""
        if self.new_value != self.original_value:
            self.preview_label.setText(f"Preview: {self.new_value}")
            self.preview_label.show()
        else:
            self.preview_label.hide()
    
    def revert_to_original(self):
        """Revert to original value"""
        if self.value_editor:
            if isinstance(self.value_editor, QDoubleSpinBox):
                self.value_editor.setValue(float(self.original_value))
            else:
                self.value_editor.setText(self.original_value)
        else:
            # Tuple editor
            inner = self.original_value[1:-1]
            values = [v.strip() for v in inner.split(',')]
            for i, val in enumerate(values):
                self.tuple_editors[i].setText(val)
        
        self.new_value = self.original_value
        self.update_preview()
    
    def get_value(self):
        return self.new_value

class TorqueCurveEditor:
    def __init__(self, filename):
        self.filename = filename
        self.points: List[TorquePoint] = []
        self.header_lines = []
        self.other_params = {}
        self.comments = {}
        self.selected_point_idx = 0
        self.load_file()
    
    def load_file(self):
        with open(self.filename, 'r') as f:
            lines = f.readlines()
        
        for line in lines:
            line = line.rstrip()
            rpm_match = re.search(r'RPMTORQUE=\(\s*(\d+)\s*,\s*(-?\d+\.?\d*)\s*,\s*(-?\d+\.?\d*)\s*\)', line, re.IGNORECASE)
            if rpm_match:
                rpm = float(rpm_match.group(1))
                braking_torque = float(rpm_match.group(2))
                drive_torque = float(rpm_match.group(3))
                self.points.append(TorquePoint(rpm, drive_torque, braking_torque))
            elif '=' in line and not line.startswith('//'):
                comment = ''
                if '//' in line:
                    line_part, comment = line.split('//', 1)
                    comment = '//' + comment
                else:
                    line_part = line
                
                parts = line_part.strip().split('=', 1)
                if len(parts) == 2:
                    key, value = parts
                    self.other_params[key.strip()] = value.strip()
                    if comment:
                        self.comments[key.strip()] = comment.strip()
            else:
                self.header_lines.append(line)
        
        self.points.sort(key=lambda p: p.rpm)
    
    def save_file(self):
        with open(self.filename, 'w') as f:
            for line in self.header_lines:
                f.write(line + '\n')
            
            for point in self.points:
                f.write(f"RPMTORQUE=(\t{int(point.rpm)}\t,\t{point.braking_torque:.1f}\t,\t{point.drive_torque:.1f}\t)\n")
            
            for key, value in self.other_params.items():
                line = f"{key}={value}"
                if key in self.comments:
                    line += f"  {self.comments[key]}"
                f.write(line + '\n')

class ParameterModel(QAbstractListModel):
    def __init__(self, editor):
        super().__init__()
        self.editor = editor
        self.filtered_keys = []
        self.filter_text = ""
        self.category = "All"
        self.update_filter()
    
    def rowCount(self, parent=QModelIndex()):
        return len(self.filtered_keys)
    
    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid() or index.row() >= len(self.filtered_keys):
            return QVariant()
        
        key = self.filtered_keys[index.row()]
        value = self.editor.other_params[key]
        
        if role == Qt.DisplayRole:
            # Truncate long values for display
            if len(value) > 30:
                display_value = value[:27] + "..."
            else:
                display_value = value
            return f"{key} = {display_value}"
        elif role == Qt.UserRole:
            return key
        elif role == Qt.EditRole:
            return value
        elif role == Qt.ToolTipRole:
            # Full value in tooltip
            return f"Key: {key}\nValue: {value}"
        return QVariant()
    
    def setData(self, index, value, role=Qt.EditRole):
        if role == Qt.EditRole and index.isValid():
            key = self.filtered_keys[index.row()]
            self.editor.other_params[key] = value
            self.dataChanged.emit(index, index)
            return True
        return False
    
    def flags(self, index):
        if not index.isValid():
            return Qt.NoItemFlags
        return Qt.ItemIsEnabled | Qt.ItemIsSelectable
    
    def filter(self, text="", category="All"):
        self.filter_text = text.lower()
        self.category = category
        self.update_filter()
    
    def update_filter(self):
        self.filtered_keys = []
        for key in sorted(self.editor.other_params.keys()):
            # Apply category filter
            if self.category != "All":
                cat = self.categorize(key)
                if cat != self.category:
                    continue
            
            # Apply text filter
            if self.filter_text and self.filter_text not in key.lower():
                continue
            
            self.filtered_keys.append(key)
        
        self.layoutChanged.emit()
    
    def categorize(self, key):
        key_lower = key.lower()
        if any(x in key_lower for x in ['fuel', 'consumption', 'estimate']):
            return 'Fuel'
        elif any(x in key_lower for x in ['inertia', 'idle', 'launch', 'revlimit', 'map']):
            return 'Engine'
        elif any(x in key_lower for x in ['oil', 'water', 'radiator', 'cooling', 'heat']):
            return 'Cooling'
        elif any(x in key_lower for x in ['lifetime', 'avg', 'var']):
            return 'Lifetime'
        else:
            return 'Other'

class TorqueCurveWidget(QWidget):
    pointSelected = pyqtSignal(int)
    
    def __init__(self, editor):
        super().__init__()
        self.editor = editor
        self.show_braking = False
        self.selected_point = None
        self.setup_ui()
        self.update_plot()
    
    def setup_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Create plot widget
        self.plot_widget = pg.PlotWidget(title="Torque & Power Curves")
        self.plot_widget.setLabel('left', 'Torque (Nm) / Power (HP)')
        self.plot_widget.setLabel('bottom', 'RPM')
        self.plot_widget.showGrid(x=True, y=True, alpha=0.3)
        self.plot_widget.setMouseEnabled(x=True, y=False)
        self.plot_widget.setMenuEnabled(False)
        
        # Create curves
        self.torque_curve = self.plot_widget.plot(pen=pg.mkPen('b', width=2), name='Drive Torque')
        self.power_curve = self.plot_widget.plot(pen=pg.mkPen('r', width=2), name='Power')
        self.braking_curve = self.plot_widget.plot(pen=pg.mkPen('g', width=1, style=Qt.DashLine), name='Braking Torque')
        
        # Create scatter plot items for points
        self.torque_points = pg.ScatterPlotItem(pen='b', brush='b', size=8, name='Torque Points')
        self.power_points = pg.ScatterPlotItem(pen='r', brush='r', size=8, name='Power Points')
        self.braking_points = pg.ScatterPlotItem(pen='g', brush='g', size=6, name='Braking Points')
        self.selected_point_marker = pg.ScatterPlotItem(pen='y', brush='y', size=15, symbol='star')
        
        self.plot_widget.addItem(self.torque_points)
        self.plot_widget.addItem(self.power_points)
        self.plot_widget.addItem(self.braking_points)
        self.plot_widget.addItem(self.selected_point_marker)
        
        # Add legend
        self.plot_widget.addLegend()
        
        # Connect mouse click
        self.plot_widget.scene().sigMouseClicked.connect(self.on_mouse_click)
        
        # Add toggle button
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self.toggle_braking_btn = QPushButton("Show Braking Torque")
        self.toggle_braking_btn.setCheckable(True)
        self.toggle_braking_btn.toggled.connect(self.toggle_braking)
        btn_layout.addWidget(self.toggle_braking_btn)
        btn_layout.addStretch()
        
        layout.addWidget(self.plot_widget)
        layout.addLayout(btn_layout)
        self.setLayout(layout)
    
    def toggle_braking(self, checked):
        self.show_braking = checked
        self.update_plot()
    
    def update_plot(self):
        if not self.editor.points:
            return
        
        rpms = [p.rpm for p in self.editor.points]
        torques = [p.drive_torque for p in self.editor.points]
        powers = [p.power for p in self.editor.points]
        brakings = [p.braking_torque for p in self.editor.points]
        
        # Update curves
        self.torque_curve.setData(rpms, torques)
        self.power_curve.setData(rpms, powers)
        
        # Update points
        self.torque_points.setData(rpms, torques)
        self.power_points.setData(rpms, powers)
        
        # Update braking curve
        if self.show_braking:
            self.braking_curve.setData(rpms, brakings)
            self.braking_points.setData(rpms, brakings)
            self.braking_curve.show()
            self.braking_points.show()
        else:
            self.braking_curve.hide()
            self.braking_points.hide()
        
        # Update selected point marker
        if self.editor.points and self.editor.selected_point_idx < len(self.editor.points):
            selected = self.editor.points[self.editor.selected_point_idx]
            self.selected_point_marker.setData([selected.rpm], [selected.drive_torque])
        
        # Auto-range
        self.plot_widget.autoRange()
    
    def on_mouse_click(self, event):
        if event.button() == Qt.LeftButton:
            # Get mouse position in plot coordinates
            pos = event.scenePos()
            mouse_point = self.plot_widget.plotItem.vb.mapSceneToView(pos)
            
            # Find closest point
            rpms = [p.rpm for p in self.editor.points]
            if rpms:
                closest_idx = min(range(len(rpms)), key=lambda i: abs(rpms[i] - mouse_point.x()))
                self.pointSelected.emit(closest_idx)

class PointEditorWidget(QWidget):
    valueChanged = pyqtSignal()
    
    def __init__(self, editor):
        super().__init__()
        self.editor = editor
        self.setup_ui()
    
    def setup_ui(self):
        layout = QGridLayout()
        layout.setVerticalSpacing(10)
        
        # Point navigation
        layout.addWidget(QLabel("Point:"), 0, 0)
        self.point_spin = QSpinBox()
        self.point_spin.setMinimum(1)
        self.point_spin.setMaximum(max(1, len(self.editor.points)))
        self.point_spin.valueChanged.connect(self.on_point_changed)
        layout.addWidget(self.point_spin, 0, 1)
        
        # Point count
        self.point_count_label = QLabel(f"of {len(self.editor.points)}")
        layout.addWidget(self.point_count_label, 0, 2)
        
        # RPM (read-only display)
        layout.addWidget(QLabel("RPM:"), 1, 0)
        self.rpm_label = QLabel("0")
        self.rpm_label.setStyleSheet("font-weight: bold; color: #4CAF50;")
        layout.addWidget(self.rpm_label, 1, 1, 1, 2)
        
        # Drive Torque
        layout.addWidget(QLabel("Drive Torque:"), 2, 0)
        self.torque_spin = QDoubleSpinBox()
        self.torque_spin.setRange(0, 2000)
        self.torque_spin.setSingleStep(5)
        self.torque_spin.setDecimals(1)
        self.torque_spin.valueChanged.connect(self.on_torque_changed)
        layout.addWidget(self.torque_spin, 2, 1, 1, 2)
        
        # Power
        layout.addWidget(QLabel("Power:"), 3, 0)
        self.power_spin = QDoubleSpinBox()
        self.power_spin.setRange(0, 2000)
        self.power_spin.setSingleStep(5)
        self.power_spin.setDecimals(1)
        self.power_spin.valueChanged.connect(self.on_power_changed)
        layout.addWidget(self.power_spin, 3, 1, 1, 2)
        
        # Braking Torque
        layout.addWidget(QLabel("Braking Torque:"), 4, 0)
        self.braking_spin = QDoubleSpinBox()
        self.braking_spin.setRange(-1000, 0)
        self.braking_spin.setSingleStep(5)
        self.braking_spin.setDecimals(1)
        self.braking_spin.valueChanged.connect(self.on_braking_changed)
        layout.addWidget(self.braking_spin, 4, 1, 1, 2)
        
        # Add/Delete buttons
        btn_layout = QHBoxLayout()
        self.add_btn = QPushButton("+ Add Point")
        self.add_btn.clicked.connect(self.add_point)
        self.delete_btn = QPushButton("- Delete Point")
        self.delete_btn.clicked.connect(self.delete_point)
        btn_layout.addWidget(self.add_btn)
        btn_layout.addWidget(self.delete_btn)
        layout.addLayout(btn_layout, 5, 0, 1, 3)
        
        # Navigation hint
        hint = QLabel("←/→: Select point\n↑/↓: Adjust drive torque\nShift+↑/↓: Adjust braking\nDouble-click parameters to edit")
        hint.setStyleSheet("color: #888; font-size: 10px; padding: 5px; background-color: #3c3c3c; border-radius: 3px;")
        layout.addWidget(hint, 6, 0, 1, 3)
        
        self.setLayout(layout)
        self.update_from_selected()
    
    def update_from_selected(self):
        if not self.editor.points:
            return
        
        if self.editor.selected_point_idx >= len(self.editor.points):
            self.editor.selected_point_idx = 0
        
        selected = self.editor.points[self.editor.selected_point_idx]
        
        # Block signals to prevent recursion
        self.torque_spin.blockSignals(True)
        self.power_spin.blockSignals(True)
        self.braking_spin.blockSignals(True)
        self.point_spin.blockSignals(True)
        
        self.point_spin.setValue(self.editor.selected_point_idx + 1)
        self.point_count_label.setText(f"of {len(self.editor.points)}")
        self.rpm_label.setText(f"{selected.rpm:.0f}")
        self.torque_spin.setValue(selected.drive_torque)
        self.power_spin.setValue(selected.power)
        self.braking_spin.setValue(selected.braking_torque)
        
        self.torque_spin.blockSignals(False)
        self.power_spin.blockSignals(False)
        self.braking_spin.blockSignals(False)
        self.point_spin.blockSignals(False)
    
    def on_point_changed(self, value):
        self.editor.selected_point_idx = value - 1
        self.update_from_selected()
        self.valueChanged.emit()
    
    def on_torque_changed(self, value):
        selected = self.editor.points[self.editor.selected_point_idx]
        selected.update_from_drive_torque(value)
        self.power_spin.blockSignals(True)
        self.power_spin.setValue(selected.power)
        self.power_spin.blockSignals(False)
        self.valueChanged.emit()
    
    def on_power_changed(self, value):
        selected = self.editor.points[self.editor.selected_point_idx]
        selected.update_from_power(value)
        self.torque_spin.blockSignals(True)
        self.torque_spin.setValue(selected.drive_torque)
        self.torque_spin.blockSignals(False)
        self.valueChanged.emit()
    
    def on_braking_changed(self, value):
        selected = self.editor.points[self.editor.selected_point_idx]
        selected.braking_torque = value
        self.valueChanged.emit()
    
    def add_point(self):
        if len(self.editor.points) < 2:
            QMessageBox.information(self, "Cannot Add Point", "Need at least 2 points to interpolate.")
            return
        
        # Find largest gap
        rpms = [p.rpm for p in self.editor.points]
        max_gap = 0
        insert_rpm = 0
        for i in range(len(rpms) - 1):
            gap = rpms[i+1] - rpms[i]
            if gap > max_gap:
                max_gap = gap
                insert_rpm = (rpms[i] + rpms[i+1]) / 2
        
        # Interpolate
        drive_torques = [p.drive_torque for p in self.editor.points]
        braking_torques = [p.braking_torque for p in self.editor.points]
        
        f_drive = interpolate.interp1d(rpms, drive_torques, kind='linear', fill_value='extrapolate')
        f_brake = interpolate.interp1d(rpms, braking_torques, kind='linear', fill_value='extrapolate')
        
        new_point = TorquePoint(insert_rpm, float(f_drive(insert_rpm)), float(f_brake(insert_rpm)))
        self.editor.points.append(new_point)
        self.editor.points.sort(key=lambda p: p.rpm)
        self.editor.selected_point_idx = self.editor.points.index(new_point)
        self.point_spin.setMaximum(len(self.editor.points))
        self.update_from_selected()
        self.valueChanged.emit()
    
    def delete_point(self):
        if len(self.editor.points) <= 2:
            QMessageBox.information(self, "Cannot Delete", "Need at least 2 points in the curve.")
            return
        
        del self.editor.points[self.editor.selected_point_idx]
        self.editor.selected_point_idx = min(self.editor.selected_point_idx, len(self.editor.points) - 1)
        self.point_spin.setMaximum(len(self.editor.points))
        self.update_from_selected()
        self.valueChanged.emit()

class MainWindow(QMainWindow):
    def __init__(self, filename):
        super().__init__()
        self.editor = TorqueCurveEditor(filename)
        self.setup_ui()
    
    def setup_ui(self):
        self.setWindowTitle(f"Torque Curve Editor - {self.editor.filename}")
        self.setGeometry(100, 100, 1600, 900)
        
        # Create central widget with splitter
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(5, 5, 5, 5)
        
        # Left side - Plot and point editor
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(5)
        
        self.plot_widget = TorqueCurveWidget(self.editor)
        self.plot_widget.pointSelected.connect(self.on_point_selected)
        left_layout.addWidget(self.plot_widget, 3)  # Give plot more space
        
        self.point_editor = PointEditorWidget(self.editor)
        self.point_editor.valueChanged.connect(self.on_data_changed)
        left_layout.addWidget(self.point_editor, 1)
        
        # Right side - Parameters with filtering
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(5, 5, 5, 5)
        right_layout.setSpacing(5)
        
        # Filter controls
        filter_group = QGroupBox("Parameter Filter")
        filter_group.setStyleSheet("QGroupBox { font-weight: bold; }")
        filter_layout = QVBoxLayout()
        
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("🔍"))
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Type to filter parameters...")
        self.search_box.textChanged.connect(self.filter_params)
        search_layout.addWidget(self.search_box)
        filter_layout.addLayout(search_layout)
        
        category_layout = QHBoxLayout()
        category_layout.addWidget(QLabel("Category:"))
        self.category_combo = QComboBox()
        self.category_combo.addItems(['All', 'Fuel', 'Engine', 'Cooling', 'Lifetime', 'Other'])
        self.category_combo.currentTextChanged.connect(self.filter_params)
        category_layout.addWidget(self.category_combo)
        filter_layout.addLayout(category_layout)
        
        # Parameter count label
        self.param_count_label = QLabel("")
        filter_layout.addWidget(self.param_count_label)
        
        filter_group.setLayout(filter_layout)
        right_layout.addWidget(filter_group)
        
        # Parameter list with model/view
        self.param_model = ParameterModel(self.editor)
        
        self.param_view = QListView()
        self.param_view.setModel(self.param_model)
        self.param_view.setEditTriggers(QAbstractItemView.NoEditTriggers)  # Disable inline editing
        self.param_view.setAlternatingRowColors(True)
        self.param_view.setSelectionMode(QListView.SingleSelection)
        self.param_view.doubleClicked.connect(self.edit_parameter)
        
        # Enable tooltips
        self.param_view.setToolTip("Double-click to edit parameter")
        
        right_layout.addWidget(self.param_view, 1)
        
        # Save button
        self.save_btn = QPushButton("💾 Save File")
        self.save_btn.clicked.connect(self.save_file)
        self.save_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                padding: 10px;
                font-weight: bold;
                border-radius: 4px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        right_layout.addWidget(self.save_btn)
        
        # Add widgets to splitter
        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)
        splitter.setSizes([1000, 600])
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 1)
        
        main_layout.addWidget(splitter)
        
        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.update_status()
    
    def update_status(self):
        self.status_bar.showMessage(
            f"Points: {len(self.editor.points)} | Parameters: {len(self.editor.other_params)} | File: {self.editor.filename}"
        )
    
    def keyPressEvent(self, event):
        if not self.editor.points:
            return
        
        key = event.key()
        modifiers = event.modifiers()
        
        if key == Qt.Key_Left:
            # Previous point
            self.editor.selected_point_idx = (self.editor.selected_point_idx - 1) % len(self.editor.points)
            self.point_editor.update_from_selected()
            self.plot_widget.update_plot()
            self.status_bar.showMessage(f"Selected point {self.editor.selected_point_idx + 1}/{len(self.editor.points)}", 1000)
            
        elif key == Qt.Key_Right:
            # Next point
            self.editor.selected_point_idx = (self.editor.selected_point_idx + 1) % len(self.editor.points)
            self.point_editor.update_from_selected()
            self.plot_widget.update_plot()
            self.status_bar.showMessage(f"Selected point {self.editor.selected_point_idx + 1}/{len(self.editor.points)}", 1000)
            
        elif key == Qt.Key_Up and modifiers == Qt.NoModifier:
            # Increase drive torque
            selected = self.editor.points[self.editor.selected_point_idx]
            selected.update_from_drive_torque(selected.drive_torque + 5)
            self.point_editor.update_from_selected()
            self.plot_widget.update_plot()
            self.status_bar.showMessage(f"Drive torque: {selected.drive_torque:.1f} Nm", 1000)
            
        elif key == Qt.Key_Down and modifiers == Qt.NoModifier:
            # Decrease drive torque
            selected = self.editor.points[self.editor.selected_point_idx]
            selected.update_from_drive_torque(max(0, selected.drive_torque - 5))
            self.point_editor.update_from_selected()
            self.plot_widget.update_plot()
            self.status_bar.showMessage(f"Drive torque: {selected.drive_torque:.1f} Nm", 1000)
            
        elif key == Qt.Key_Up and modifiers == Qt.ShiftModifier:
            # Increase braking torque (more negative)
            selected = self.editor.points[self.editor.selected_point_idx]
            selected.braking_torque -= 5
            self.point_editor.update_from_selected()
            self.plot_widget.update_plot()
            self.status_bar.showMessage(f"Braking torque: {selected.braking_torque:.1f} Nm", 1000)
            
        elif key == Qt.Key_Down and modifiers == Qt.ShiftModifier:
            # Decrease braking torque (less negative)
            selected = self.editor.points[self.editor.selected_point_idx]
            selected.braking_torque += 5
            self.point_editor.update_from_selected()
            self.plot_widget.update_plot()
            self.status_bar.showMessage(f"Braking torque: {selected.braking_torque:.1f} Nm", 1000)
        
        else:
            super().keyPressEvent(event)
    
    def filter_params(self):
        self.param_model.filter(
            self.search_box.text(),
            self.category_combo.currentText()
        )
        self.param_count_label.setText(f"Showing {len(self.param_model.filtered_keys)} parameters")
    
    def on_point_selected(self, idx):
        self.editor.selected_point_idx = idx
        self.point_editor.update_from_selected()
        self.plot_widget.update_plot()
        self.status_bar.showMessage(f"Selected point {idx + 1}/{len(self.editor.points)}", 1000)
    
    def on_data_changed(self):
        self.plot_widget.update_plot()
        self.update_status()
        self.status_bar.showMessage("Unsaved changes", 2000)
    
    def edit_parameter(self, index):
        """Open dialog to edit parameter"""
        key = self.param_model.filtered_keys[index.row()]
        value = self.editor.other_params[key]
        
        dialog = ParameterEditDialog(key, value, self)
        if dialog.exec_() == QDialog.Accepted:
            new_value = dialog.get_value()
            if new_value != value:
                self.editor.other_params[key] = new_value
                self.param_model.dataChanged.emit(index, index)
                self.on_parameter_changed()
    
    def on_parameter_changed(self):
        """Called when a parameter is edited"""
        self.update_status()
        self.status_bar.showMessage("Parameter updated - Unsaved changes", 2000)
    
    def save_file(self):
        try:
            self.editor.save_file()
            self.update_status()
            self.status_bar.showMessage(f"✅ File saved: {self.editor.filename}", 3000)
            QMessageBox.information(self, "Success", "File saved successfully!")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save file: {str(e)}")
            self.status_bar.showMessage(f"❌ Error saving file", 3000)

def main():
    if len(sys.argv) != 2:
        print("Usage: python torque_editor.py <filename>")
        sys.exit(1)
    
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    # Set dark theme
    app.setStyleSheet("""
        QMainWindow, QDialog {
            background-color: #2b2b2b;
        }
        QGroupBox {
            color: #ffffff;
            border: 1px solid #555;
            border-radius: 5px;
            margin-top: 1ex;
            font-weight: normal;
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
        QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {
            background-color: #3c3c3c;
            color: #ffffff;
            border: 1px solid #555;
            border-radius: 3px;
            padding: 4px;
            selection-background-color: #4CAF50;
        }
        QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {
            border: 1px solid #4CAF50;
        }
        QListView {
            background-color: #2b2b2b;
            color: #ffffff;
            border: 1px solid #555;
            border-radius: 3px;
            outline: none;
        }
        QListView::item {
            padding: 6px;
            border-bottom: 1px solid #3c3c3c;
        }
        QListView::item:selected {
            background-color: #4CAF50;
            color: white;
        }
        QListView::item:alternate {
            background-color: #333333;
        }
        QListView::item:hover {
            background-color: #3c3c3c;
        }
        QPushButton {
            background-color: #3c3c3c;
            color: white;
            border: 1px solid #555;
            border-radius: 3px;
            padding: 5px 10px;
        }
        QPushButton:hover {
            background-color: #4c4c4c;
            border: 1px solid #4CAF50;
        }
        QPushButton:pressed {
            background-color: #2c2c2c;
        }
        QStatusBar {
            color: #ffffff;
            background-color: #3c3c3c;
            border-top: 1px solid #555;
        }
        QScrollBar:vertical {
            background-color: #2b2b2b;
            width: 12px;
            border-radius: 6px;
        }
        QScrollBar::handle:vertical {
            background-color: #555;
            border-radius: 6px;
            min-height: 20px;
        }
        QScrollBar::handle:vertical:hover {
            background-color: #4CAF50;
        }
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
            border: none;
            background: none;
        }
    """)
    
    window = MainWindow(sys.argv[1])
    window.show()
    
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
