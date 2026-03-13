import sys
import re
import numpy as np
from pathlib import Path
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
import pyqtgraph as pg
from scipy.ndimage import gaussian_filter1d

class PointEditWidget(QWidget):
    def __init__(self, editor, parent=None):
        super().__init__(parent)
        self.editor = editor
        self.current_point_index = 0
        self.current_values = []
        self.text_editing_enabled = False
        self.setup_ui()
        print(f"[PointEditWidget] Initialized with current_point_index={self.current_point_index}")
        
    def setup_ui(self):
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.point_label = QLabel("Point: 0/0")
        self.point_label.setStyleSheet("color: #4CAF50; font-weight: bold;")
        layout.addWidget(self.point_label)
        
        value_label = QLabel("Value:")
        value_label.setStyleSheet("color: #f0f0f0;")
        layout.addWidget(value_label)
        
        self.value_spin = QDoubleSpinBox()
        self.value_spin.setRange(-10.0, 10.0)
        self.value_spin.setDecimals(6)
        self.value_spin.setSingleStep(0.0001)
        self.value_spin.valueChanged.connect(self.on_value_changed)
        self.value_spin.setReadOnly(True)
        self.value_spin.setStyleSheet("""
            QDoubleSpinBox {
                background-color: #3a3a3a;
                color: #888;
                border: 1px solid #555;
                border-radius: 3px;
                padding: 2px;
            }
            QDoubleSpinBox:read-only {
                background-color: #2a2a2a;
                color: #666;
            }
        """)
        layout.addWidget(self.value_spin)
        
        self.edit_btn = QPushButton("Edit Text")
        self.edit_btn.setCheckable(True)
        self.edit_btn.setChecked(False)
        self.edit_btn.clicked.connect(self.toggle_text_editing)
        self.edit_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 4px 8px;
                border-radius: 3px;
                font-weight: bold;
                min-width: 60px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:checked {
                background-color: #f44336;
            }
            QPushButton:checked:hover {
                background-color: #d32f2f;
            }
        """)
        layout.addWidget(self.edit_btn)
        
        instr_label = QLabel("←/→: Select point, ↑/↓: Change value (Shift: x100, Alt: x0.01)")
        instr_label.setStyleSheet("color: #888; font-style: italic;")
        layout.addWidget(instr_label)
        layout.addStretch()
        self.setLayout(layout)
        self.setFocusPolicy(Qt.StrongFocus)
    
    def toggle_text_editing(self, checked):
        print(f"\n[PointEditWidget] toggle_text_editing: checked={checked}")
        self.text_editing_enabled = checked
        self.value_spin.setReadOnly(not checked)
        if checked:
            self.value_spin.setFocus()
            self.edit_btn.setText("Lock Text")
            self.value_spin.setStyleSheet("""
                QDoubleSpinBox {
                    background-color: #4CAF50;
                    color: white;
                    border: 1px solid #4CAF50;
                    border-radius: 3px;
                    padding: 2px;
                }
                QDoubleSpinBox:focus {
                    border: 2px solid #ff9800;
                }
            """)
        else:
            self.edit_btn.setText("Edit Text")
            self.value_spin.setStyleSheet("""
                QDoubleSpinBox {
                    background-color: #2a2a2a;
                    color: #666;
                    border: 1px solid #555;
                    border-radius: 3px;
                    padding: 2px;
                }
            """)
    
    def set_values(self, values, preserve_index=False):
        print(f"\n[PointEditWidget] set_values: preserve_index={preserve_index}, current_index={self.current_point_index}")
        self.current_values = values.copy() if values else []
        if not preserve_index:
            self.current_point_index = 0
            print(f"  Resetting index to 0")
        self.update_display()
    
    def update_display(self):
        print(f"\n[PointEditWidget] update_display: current_point_index={self.current_point_index}")
        if self.current_values:
            print(f"  current value = {self.current_values[self.current_point_index]}")
            self.point_label.setText(f"Point: {self.current_point_index + 1}/{len(self.current_values)}")
            self.value_spin.blockSignals(True)
            self.value_spin.setValue(self.current_values[self.current_point_index])
            self.value_spin.blockSignals(False)
            if hasattr(self.editor, 'curve_editor_widget') and self.editor.curve_editor_widget:
                self.editor.curve_editor_widget.update_points_display()
    
    def on_value_changed(self, value):
        print(f"\n[PointEditWidget] on_value_changed: value={value}, current_point_index={self.current_point_index}")
        if self.current_values and self.current_point_index < len(self.current_values):
            old_value = self.current_values[self.current_point_index]
            self.current_values[self.current_point_index] = value
            print(f"  Updated point {self.current_point_index} from {old_value} to {value}")
            self.editor.update_point_value(self.current_point_index, value, preserve_index=True)
    
    def select_previous_point(self):
        print(f"\n[PointEditWidget] select_previous_point: current_index={self.current_point_index}")
        if self.current_values and self.current_point_index > 0:
            self.current_point_index -= 1
            print(f"  New index={self.current_point_index}, value={self.current_values[self.current_point_index]}")
            self.update_display()
            self.editor.highlight_point(self.current_point_index)
        else:
            print(f"  Cannot select previous - at first point")
    
    def select_next_point(self):
        print(f"\n[PointEditWidget] select_next_point: current_index={self.current_point_index}")
        if self.current_values and self.current_point_index < len(self.current_values) - 1:
            self.current_point_index += 1
            print(f"  New index={self.current_point_index}, value={self.current_values[self.current_point_index]}")
            self.update_display()
            self.editor.highlight_point(self.current_point_index)
        else:
            print(f"  Cannot select next - at last point")
    
    def increase_value(self, modifiers):
        print(f"\n[PointEditWidget] increase_value: current_index={self.current_point_index}, modifiers={modifiers}")
        if self.current_values:
            current_val = self.value_spin.value()
            
            # Determine step size based on modifiers
            if modifiers & Qt.AltModifier:
                step = 0.000001  # Alt: fine adjustment
                print(f"  Alt modifier detected - using fine step: {step}")
            elif modifiers & Qt.ShiftModifier:
                step = 0.01       # Shift: coarse adjustment
                print(f"  Shift modifier detected - using coarse step: {step}")
            else:
                step = 0.0001      # Default: normal adjustment
                print(f"  No modifier - using normal step: {step}")
            
            new_val = current_val + step
            print(f"  Increasing from {current_val} to {new_val}")
            self.value_spin.setValue(new_val)
        else:
            print(f"  No values to increase")
    
    def decrease_value(self, modifiers):
        print(f"\n[PointEditWidget] decrease_value: current_index={self.current_point_index}, modifiers={modifiers}")
        if self.current_values:
            current_val = self.value_spin.value()
            
            # Determine step size based on modifiers
            if modifiers & Qt.AltModifier:
                step = 0.000001  # Alt: fine adjustment
                print(f"  Alt modifier detected - using fine step: {step}")
            elif modifiers & Qt.ShiftModifier:
                step = 0.01       # Shift: coarse adjustment
                print(f"  Shift modifier detected - using coarse step: {step}")
            else:
                step = 0.0001      # Default: normal adjustment
                print(f"  No modifier - using normal step: {step}")
            
            new_val = current_val - step
            print(f"  Decreasing from {current_val} to {new_val}")
            self.value_spin.setValue(new_val)
        else:
            print(f"  No values to decrease")
    
    def keyPressEvent(self, event):
        print(f"\n[PointEditWidget] keyPressEvent: key={event.key()}, current_index={self.current_point_index}")
        print(f"  Ignoring event to let parent handle it")
        event.ignore()
    
    def focusInEvent(self, event):
        print(f"\n[PointEditWidget] focusInEvent: current_index={self.current_point_index}")
        super().focusInEvent(event)
        self.editor.highlight_point(self.current_point_index)
    
    def focusOutEvent(self, event):
        print(f"\n[PointEditWidget] focusOutEvent")
        if self.text_editing_enabled:
            print(f"  Disabling text editing mode due to focus loss")
            self.text_editing_enabled = False
            self.value_spin.setReadOnly(True)
            self.edit_btn.setChecked(False)
            self.edit_btn.setText("Edit Text")
            self.value_spin.setStyleSheet("""
                QDoubleSpinBox {
                    background-color: #2a2a2a;
                    color: #666;
                    border: 1px solid #555;
                    border-radius: 3px;
                    padding: 2px;
                }
            """)
        super().focusOutEvent(event)

class SlipCurveEditWidget(QWidget):
    def __init__(self, editor, curve, comp_curve=None, axle=None, parent=None):
        super().__init__(parent)
        self.editor = editor
        self.curve_name = curve
        self.comparison_curve_name = comp_curve
        self.axle = axle
        self.current_curve_index = self.find_curve_index()
        self.setup_ui()
        print(f"[SlipCurveEditWidget] Initialized for curve: {curve}")
        
    def keyPressEvent(self, event):
        print(f"\n[SlipCurveEditWidget] keyPressEvent: key={event.key()}, modifiers={event.modifiers()}")
        # Handle all arrow keys here
        if event.key() == Qt.Key_Left:
            print("  Left arrow detected in keyPressEvent")
            self.point_edit.select_previous_point()
            event.accept()
        elif event.key() == Qt.Key_Right:
            print("  Right arrow detected in keyPressEvent")
            self.point_edit.select_next_point()
            event.accept()
        elif event.key() == Qt.Key_Up:
            print("  Up arrow detected in keyPressEvent")
            self.point_edit.increase_value(event.modifiers())
            event.accept()
        elif event.key() == Qt.Key_Down:
            print("  Down arrow detected in keyPressEvent")
            self.point_edit.decrease_value(event.modifiers())
            event.accept()
        else:
            print(f"  Other key {event.key()} - passing to parent")
            super().keyPressEvent(event)
    
    def eventFilter(self, obj, event):
        if event.type() == QEvent.KeyPress:
            print(f"\n[SlipCurveEditWidget] eventFilter: obj={obj.__class__.__name__}, key={event.key()}, modifiers={event.modifiers()}")
            # Handle all arrow keys
            if event.key() == Qt.Key_Left:
                print(f"  Left arrow detected in eventFilter from {obj.__class__.__name__}")
                self.point_edit.select_previous_point()
                return True
            elif event.key() == Qt.Key_Right:
                print(f"  Right arrow detected in eventFilter from {obj.__class__.__name__}")
                self.point_edit.select_next_point()
                return True
            elif event.key() == Qt.Key_Up:
                print(f"  Up arrow detected in eventFilter from {obj.__class__.__name__}")
                self.point_edit.increase_value(event.modifiers())
                return True
            elif event.key() == Qt.Key_Down:
                print(f"  Down arrow detected in eventFilter from {obj.__class__.__name__}")
                self.point_edit.decrease_value(event.modifiers())
                return True
        
        return super().eventFilter(obj, event)
        
    def find_curve_index(self):
        for i, c in enumerate(self.editor.slip_curves):
            if c['name'] == self.curve_name:
                return i
        return 0
    
    def setup_ui(self):
        layout = QVBoxLayout()
        
        title = f"Editing: {self.curve_name}"
        if self.comparison_curve_name:
            title += f" | Comparing: {self.comparison_curve_name}"
        if self.axle:
            title += f" | Axle: {self.axle}"
        title_label = QLabel(title)
        title_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #4CAF50; padding: 5px;")
        layout.addWidget(title_label)
        
        self.back_btn = QPushButton("← Back to Compound Editor")
        self.back_btn.clicked.connect(self.editor.close_curve_editor)
        self.back_btn.setStyleSheet("""
            QPushButton {
                background-color: #ff9800;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 3px;
                font-weight: bold;
                min-height: 20px;
                max-height: 30px;
            }
            QPushButton:hover {
                background-color: #f57c00;
            }
            QPushButton:pressed {
                background-color: #e65100;
            }
        """)
        layout.addWidget(self.back_btn)
        
        self.point_edit = PointEditWidget(self.editor)
        layout.addWidget(self.point_edit)
        
        self.plot = pg.PlotWidget()
        self.plot.setLabel('left', 'Force')
        self.plot.setLabel('bottom', 'Slip')
        self.plot.showGrid(x=True, y=True)
        self.plot.setMinimumHeight(400)
        
        self.legend = self.plot.addLegend()
        
        self.editor.curve_plot = self.plot.plot(pen=pg.mkPen('b', width=2), name='Current')
        self.editor.original_curve_plot = self.plot.plot(pen=pg.mkPen('gray', width=1, style=Qt.DashLine), name='Original')
        self.editor.comparison_plot = self.plot.plot(pen=pg.mkPen('orange', width=2, style=Qt.DashLine), name='Comparison')
        self.editor.preview_curve = self.plot.plot(pen=pg.mkPen('y', width=2, style=Qt.DashLine), name='Preview')
        
        self.editor.comparison_plot.hide()
        self.editor.preview_curve.hide()
        
        self.editor.point_highlight = pg.ScatterPlotItem(pen='r', size=15, symbol='o')
        self.editor.peak_marker = pg.ScatterPlotItem(pen='r', brush='r', size=15, symbol='star')
        self.plot.addItem(self.editor.peak_marker)
        self.plot.addItem(self.editor.point_highlight)
        
        layout.addWidget(self.plot)
        
        params = QHBoxLayout()
        
        step_label = QLabel("Step:")
        step_label.setStyleSheet("color: #f0f0f0;")
        params.addWidget(step_label)
        
        self.step_spin = QDoubleSpinBox()
        self.step_spin.setRange(0.0001, 1.0)
        self.step_spin.setDecimals(6)
        self.step_spin.valueChanged.connect(self.on_step_changed)
        params.addWidget(self.step_spin)
        
        points_label = QLabel("Points:")
        points_label.setStyleSheet("color: #f0f0f0;")
        params.addWidget(points_label)
        
        self.points_label = QLabel("0")
        self.points_label.setStyleSheet("font-weight: bold; color: #4CAF50;")
        params.addWidget(self.points_label)
        params.addStretch()
        layout.addLayout(params)
        
        ops = QHBoxLayout()
        self.smooth_btn = QPushButton("Smooth")
        self.smooth_btn.clicked.connect(lambda: self.editor.show_preview_dialog("smooth", self))
        self.smooth_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                padding: 5px 10px;
                border-radius: 3px;
                font-weight: bold;
                min-height: 20px;
                max-height: 30px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)
        ops.addWidget(self.smooth_btn)
        
        self.reset_btn = QPushButton("Reset")
        self.reset_btn.clicked.connect(self.editor.reset_curve)
        self.reset_btn.setStyleSheet("""
            QPushButton {
                background-color: #9C27B0;
                color: white;
                border: none;
                padding: 5px 10px;
                border-radius: 3px;
                font-weight: bold;
                min-height: 20px;
                max-height: 30px;
            }
            QPushButton:hover {
                background-color: #7B1FA2;
            }
        """)
        ops.addWidget(self.reset_btn)
        ops.addStretch()
        layout.addLayout(ops)
        
        points_display_label = QLabel("Point Values:")
        points_display_label.setStyleSheet("color: #f0f0f0; font-weight: bold; margin-top: 10px;")
        layout.addWidget(points_display_label)
        
        self.points_display = QTextEdit()
        self.points_display.setReadOnly(True)
        self.points_display.setMaximumHeight(100)
        self.points_display.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #f0f0f0;
                border: 1px solid #444;
                border-radius: 3px;
                padding: 5px;
                font-family: monospace;
                font-size: 11px;
            }
        """)
        layout.addWidget(self.points_display)
        
        self.setLayout(layout)
        
        self.setFocusPolicy(Qt.StrongFocus)
        
        print(f"\n[SlipCurveEditWidget] Installing event filters on child widgets...")
        children = self.findChildren(QWidget)
        print(f"  Found {len(children)} child widgets")
        for child in children:
            child.installEventFilter(self)
            print(f"  - Installed on {child.__class__.__name__}")
        
        self.update_display()
        
        if self.comparison_curve_name and self.editor.last_comparison_file:
            QTimer.singleShot(100, self.load_comparison)
    
    def load_comparison(self):
        try:
            with open(self.editor.last_comparison_file, 'r') as f:
                content = f.read()
            
            pattern = r'\[SLIPCURVE\]\s*Name="([^"]+)"\s*Step=([0-9.e+-]+)[^\n]*\s*DropoffFunction=([0-9.e+-]+)[^\n]*\s*Data:\s*((?:\d+\.\d+\s*)+)'
            for match in re.finditer(pattern, content, re.MULTILINE | re.DOTALL):
                if match.group(1).strip() == self.comparison_curve_name:
                    step = float(match.group(2))
                    values = [float(x) for x in match.group(4).strip().split()]
                    x_vals = [i * step for i in range(len(values))]
                    self.editor.comparison_plot.setData(x_vals, values)
                    self.editor.comparison_plot.show()
                    self.plot.autoRange()
                    break
        except Exception as e:
            print(f"Error loading comparison: {e}")
    
    def update_points_display(self):
        if not hasattr(self, 'points_display'):
            return
            
        if not self.point_edit.current_values:
            self.points_display.setText("")
            return
        
        points_text = []
        for i, val in enumerate(self.point_edit.current_values):
            if i == self.point_edit.current_point_index:
                points_text.append(f'<span style="color: #4CAF50; font-weight: bold;">[{val:.6f}]</span>')
            else:
                points_text.append(f'<span style="color: #f0f0f0;">{val:.6f}</span>')
        
        html_text = " ".join(points_text)
        self.points_display.setHtml(html_text)
    
    def update_display(self):
        print(f"\n[SlipCurveEditWidget] update_display")
        if self.current_curve_index >= len(self.editor.slip_curves):
            return
        
        curve = self.editor.slip_curves[self.current_curve_index]
        if self.current_curve_index in self.editor.modified_curves:
            mod = self.editor.modified_curves[self.current_curve_index]
            vals, step = mod['values'], mod['step']
        else:
            vals, step = curve['values'], curve['step']
        
        x = [i * step for i in range(len(vals))]
        self.editor.curve_plot.setData(x, vals)
        
        if self.current_curve_index in self.editor.modified_curves:
            orig_x = [i * curve['step'] for i in range(len(curve['values']))]
            self.editor.original_curve_plot.setData(orig_x, curve['values'])
            self.editor.original_curve_plot.show()
        else:
            self.editor.original_curve_plot.hide()
        
        peak_idx = np.argmax(vals)
        self.editor.peak_marker.setData([x[peak_idx]], [vals[peak_idx]])
        
        # Preserve current point index when updating values
        current_idx = self.point_edit.current_point_index if hasattr(self, 'point_edit') else 0
        self.point_edit.set_values(vals, preserve_index=True)
        
        self.step_spin.blockSignals(True)
        self.step_spin.setValue(step)
        self.step_spin.blockSignals(False)
        self.points_label.setText(str(len(vals)))
        
        self.update_points_display()
        
        if hasattr(self.editor, 'curve_editor_widget') and self.editor.curve_editor_widget:
            self.editor.highlight_point(self.point_edit.current_point_index)
        
        self.plot.autoRange()
    
    def on_step_changed(self, val):
        self.editor.on_step_changed(val)
        self.update_display()

class CompareCompoundDialog(QDialog):
    def __init__(self, parent=None, last_file=None, start_dir=None):
        super().__init__(parent)
        self.selected_file = None
        self.selected_compound_index = 0
        self.selected_axle = "FRONT"
        self.comparison_compounds = []
        self.comparison_curves = []
        self.last_file = last_file
        self.start_dir = start_dir
        self.setup_ui()
        
    def setup_ui(self):
        self.setWindowTitle("Load Comparison File")
        self.setModal(True)
        self.setMinimumWidth(500)
        
        layout = QVBoxLayout()
        
        file_group = QGroupBox("Select File")
        file_layout = QHBoxLayout()
        self.file_path_edit = QLineEdit()
        self.file_path_edit.setReadOnly(True)
        self.file_path_edit.setPlaceholderText("No file selected")
        self.browse_btn = QPushButton("Browse...")
        self.browse_btn.clicked.connect(self.browse_file)
        file_layout.addWidget(self.file_path_edit)
        file_layout.addWidget(self.browse_btn)
        file_group.setLayout(file_layout)
        layout.addWidget(file_group)
        
        compound_group = QGroupBox("Select Compound")
        compound_layout = QVBoxLayout()
        select_layout = QHBoxLayout()
        select_layout.addWidget(QLabel("Compound:"))
        self.compound_combo = QComboBox()
        self.compound_combo.setEnabled(False)
        self.compound_combo.currentIndexChanged.connect(self.on_compound_selected)
        select_layout.addWidget(self.compound_combo)
        select_layout.addWidget(QLabel("Axle:"))
        self.axle_combo = QComboBox()
        self.axle_combo.addItems(["FRONT", "REAR"])
        self.axle_combo.setEnabled(False)
        self.axle_combo.currentTextChanged.connect(self.on_axle_selected)
        select_layout.addWidget(self.axle_combo)
        select_layout.addStretch()
        compound_layout.addLayout(select_layout)
        compound_group.setLayout(compound_layout)
        layout.addWidget(compound_group)
        
        btn_layout = QHBoxLayout()
        self.show_btn = QPushButton("Compare")
        self.show_btn.clicked.connect(self.accept)
        self.show_btn.setEnabled(False)
        self.show_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 8px 16px;
                min-height: 20px;
                max-height: 30px;
                border-radius: 3px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
            }
            QPushButton:disabled {
                background-color: #666;
                color: #aaa;
            }
        """)
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        self.cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #666;
                color: white;
                border: none;
                padding: 8px 16px;
                min-height: 20px;
                max-height: 30px;
                border-radius: 3px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #777;
            }
            QPushButton:pressed {
                background-color: #888;
            }
        """)
        btn_layout.addWidget(self.show_btn)
        btn_layout.addWidget(self.cancel_btn)
        layout.addLayout(btn_layout)
        
        self.setLayout(layout)
        
        if self.last_file and Path(self.last_file).exists():
            self.load_file(self.last_file)
    
    def browse_file(self):
        start_dir = self.start_dir or str(Path.home())
        if self.last_file:
            start_dir = str(Path(self.last_file).parent)
        
        filename, _ = QFileDialog.getOpenFileName(
            self, "Select Tire File", start_dir, "Tire files (*.tbc *.tyr);;All files (*.*)"
        )
        if filename:
            self.load_file(filename)
    
    def load_file(self, filename):
        try:
            self.comparison_curves, self.comparison_compounds = self.parse_tire_file(filename)
            if self.comparison_compounds:
                self.file_path_edit.setText(filename)
                self.selected_file = filename
                self.compound_combo.clear()
                self.compound_combo.addItems([c['name'] for c in self.comparison_compounds])
                self.compound_combo.setEnabled(True)
                self.axle_combo.setEnabled(True)
                self.show_btn.setEnabled(True)
                self.on_compound_selected(0)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load file: {e}")
    
    def parse_tire_file(self, filename):
        curves = []
        compounds = []
        with open(filename, 'r') as f:
            content = f.read()
        
        pattern = r'\[SLIPCURVE\]\s*Name="([^"]+)"\s*Step=([0-9.e+-]+)[^\n]*\s*DropoffFunction=([0-9.e+-]+)[^\n]*\s*Data:\s*((?:\d+\.\d+\s*)+)'
        for match in re.finditer(pattern, content, re.MULTILINE | re.DOTALL):
            name = match.group(1).strip()
            step = float(match.group(2))
            dropoff = float(match.group(3))
            values = [float(x) for x in match.group(4).strip().split()]
            curves.append({
                'name': name, 'step': step, 'dropoff_function': dropoff,
                'values': values, 'x_values': [i * step for i in range(len(values))]
            })
        
        parts = content.split('[COMPOUND]')
        for i in range(1, len(parts)):
            compound_content = '[COMPOUND]' + parts[i]
            name_match = re.search(r'Name="([^"]+)"', compound_content)
            if not name_match:
                continue
            name = name_match.group(1)
            
            wet_match = re.search(r'WetWeather\s*=\s*(\d+)', compound_content)
            wet_weather = int(wet_match.group(1)) if wet_match else None
            
            axles = {}
            lines = compound_content.split('\n')
            current_axle = None
            axle_lines = []
            
            for line in lines:
                clean = line.split('//')[0].strip()
                if not clean:
                    continue
                if clean.startswith('FRONT:'):
                    if current_axle and axle_lines:
                        axles[current_axle] = self._parse_axle_params('\n'.join(axle_lines))
                    current_axle = 'FRONT'
                    axle_lines = []
                elif clean.startswith('REAR:'):
                    if current_axle and axle_lines:
                        axles[current_axle] = self._parse_axle_params('\n'.join(axle_lines))
                    current_axle = 'REAR'
                    axle_lines = []
                elif current_axle and '=' in clean:
                    axle_lines.append(line)
            
            if current_axle and axle_lines:
                axles[current_axle] = self._parse_axle_params('\n'.join(axle_lines))
            
            compounds.append({'name': name, 'wet_weather': wet_weather, 'axles': axles})
        
        return curves, compounds
    
    def _parse_axle_params(self, content):
        params = {}
        for line in content.split('\n'):
            clean = line.split('//')[0].strip()
            if '=' not in clean:
                continue
            key, val = [x.strip() for x in clean.split('=', 1)]
            if val.startswith('"') and val.endswith('"'):
                val = val[1:-1]
            params[key] = val
        return params
    
    def on_compound_selected(self, index):
        if 0 <= index < len(self.comparison_compounds):
            self.selected_compound_index = index
    
    def on_axle_selected(self, axle):
        self.selected_axle = axle
    
    def get_selected_compound(self):
        if self.comparison_compounds and self.selected_compound_index < len(self.comparison_compounds):
            return self.comparison_compounds[self.selected_compound_index]
        return None
    
    def get_selected_axle(self): return self.selected_axle
    def get_selected_file(self): return self.selected_file
    def get_curves(self): return self.comparison_curves

class CompoundParameterTableWidget(QTableWidget):
    parameter_edited = pyqtSignal(str, str, str)
    edit_curve_requested = pyqtSignal(str, str, str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_axle = "FRONT"
        self.current_compound_index = -1
        self.comparison_compound = None
        self.comparison_axle = "FRONT"
        self.setup_ui()
        
    def setup_ui(self):
        self.setColumnCount(4)
        self.setHorizontalHeaderLabels(["Parameter", "Value", "Comparison", ""])
        
        header = self.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        
        self.verticalHeader().setVisible(False)
        self.setAlternatingRowColors(True)
        self.setEditTriggers(QAbstractItemView.DoubleClicked)
        
        self.setStyleSheet("""
            QTableWidget { background-color: #2b2b2b; alternate-background-color: #3a3a3a; gridline-color: #444; }
            QTableWidget::item { padding: 4px; border: none; }
            QTableWidget::item:selected { background-color: #4CAF50; }
            QHeaderView::section { background-color: #1e1e1e; color: #4CAF50; padding: 6px; border: 1px solid #444; font-weight: bold; }
        """)
        
        self.itemDoubleClicked.connect(self.on_item_double_clicked)
    
    def set_comparison_compound(self, compound, axle):
        self.comparison_compound = compound
        self.comparison_axle = axle
        self.update_table()
    
    def clear_comparison(self):
        self.comparison_compound = None
        self.update_table()
    
    def values_differ(self, val1, val2):
        if val1 is None and val2 is None: return False
        if val1 is None or val2 is None: return True
        
        str1, str2 = str(val1).strip(), str(val2).strip()
        
        if '(' in str1 and ')' in str1:
            try:
                nums1 = [float(x.strip()) for x in str1.strip('()').split(',')]
                nums2 = [float(x.strip()) for x in str2.strip('()').split(',')]
                if len(nums1) != len(nums2): 
                    return True
                for i, (a, b) in enumerate(zip(nums1, nums2)):
                    if abs(a - b) > 1e-10:
                        return True
                return False
            except:
                return str1 != str2
        
        try:
            diff = abs(float(str1) - float(str2))
            return diff > 1e-10
        except:
            return str1 != str2
    
    def add_row(self, name, curr_val, comp_val=None, editable=False, special=False):
        row = self.rowCount()
        self.insertRow(row)
        
        p_item = QTableWidgetItem(name)
        p_item.setForeground(QBrush(QColor("#4CAF50" if special else "#888")))
        p_item.setFlags(p_item.flags() & ~Qt.ItemIsEditable)
        self.setItem(row, 0, p_item)
        
        v_item = QTableWidgetItem(str(curr_val) if curr_val is not None else "")
        if editable:
            v_item.setFlags(v_item.flags() | Qt.ItemIsEditable)
            v_item.setForeground(QBrush(QColor("#ffffff")))
        else:
            v_item.setFlags(v_item.flags() & ~Qt.ItemIsEditable)
            v_item.setForeground(QBrush(QColor("#4CAF50" if special else "#fcfcfc")))
        self.setItem(row, 1, v_item)
        
        if comp_val is not None and self.comparison_compound:
            c_item = QTableWidgetItem(str(comp_val))
            c_item.setFlags(c_item.flags() & ~Qt.ItemIsEditable)
            is_diff = self.values_differ(curr_val, comp_val)
            color = "#fcad37" if is_diff else "#fcfcfc"
            c_item.setForeground(QBrush(QColor(color)))
            self.setItem(row, 2, c_item)
        else:
            empty = QTableWidgetItem("")
            empty.setFlags(empty.flags() & ~Qt.ItemIsEditable)
            empty.setForeground(QBrush(QColor("#fcfcfc")))
            self.setItem(row, 2, empty)
        
        btn_item = QTableWidgetItem("")
        btn_item.setFlags(btn_item.flags() & ~Qt.ItemIsEditable)
        self.setItem(row, 3, btn_item)
        
        return row
    
    def update_table(self):
        self.clearContents()
        self.setRowCount(0)
        
        if self.current_compound_index < 0:
            return
        
        compound = self.parent().editor.compounds[self.current_compound_index].copy()
        
        if self.current_compound_index in self.parent().editor.modified_compounds:
            mod = self.parent().editor.modified_compounds[self.current_compound_index]
            if self.current_axle in mod.get('axles', {}):
                for key, val in mod['axles'][self.current_axle].items():
                    if self.current_axle in compound['axles']:
                        compound['axles'][self.current_axle][key] = val
        
        comp_name = self.comparison_compound['name'] if self.comparison_compound else None
        self.add_row("Name", compound['name'], comp_name, special=True)
        
        if compound.get('wet_weather') is not None:
            comp_wet = self.comparison_compound.get('wet_weather') if self.comparison_compound else None
            self.add_row("WetWeather", str(compound['wet_weather']), 
                        str(comp_wet) if comp_wet is not None else None)
        
        if self.current_axle in compound['axles']:
            axle_data = compound['axles'][self.current_axle]
            
            comp_axle_data = None
            if self.comparison_compound and self.comparison_axle in self.comparison_compound['axles']:
                comp_axle_data = self.comparison_compound['axles'][self.comparison_axle]
            
            self.add_row("Axle", self.current_axle, self.comparison_axle if comp_axle_data else None, special=True)
            
            for key, val in axle_data.items():
                comp_val = comp_axle_data.get(key) if comp_axle_data else None
                row = self.add_row(key, val, comp_val, editable=True)
                
                if key in ["LatCurve", "BrakingCurve", "TractiveCurve"]:
                    btn = QPushButton("Edit")
                    btn.setMaximumWidth(50)
                    btn.setStyleSheet("""
                        QPushButton {
                            background-color: #4CAF50;
                            color: white;
                            border: none;
                            padding: 2px 6px;
                            border-radius: 3px;
                            font-size: 10px;
                        }
                        QPushButton:hover {
                            background-color: #45a049;
                        }
                    """)
                    btn.clicked.connect(
                        lambda checked, k=val, c=comp_val, a=self.current_axle: 
                        self.edit_curve_requested.emit(k, c, a)
                    )
                    self.setCellWidget(row, 3, btn)
        
        self.resizeColumnsToContents()
        header = self.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
    
    def set_current_compound(self, index):
        self.current_compound_index = index
        self.update_table()
    
    def set_current_axle(self, axle):
        self.current_axle = axle
        self.update_table()
    
    def on_item_double_clicked(self, item):
        if item.column() == 1 and item.flags() & Qt.ItemIsEditable:
            key = self.item(item.row(), 0).text()
            if key not in ["Name", "WetWeather", "Axle"]:
                self.edit_parameter(key, item.text())
    
    def edit_parameter(self, key, curr_val):
        dlg = ParameterEditDialog(key, curr_val, self.window())
        if dlg.exec_() == QDialog.Accepted:
            new_val = dlg.get_value()
            if new_val != curr_val:
                self.parameter_edited.emit(self.current_axle, key, new_val)
                self.update_table()

class ParameterEditDialog(QDialog):
    def __init__(self, key, curr_val, parent=None):
        super().__init__(parent)
        self.key = key
        self.curr_val = curr_val
        self.new_val = curr_val
        self.setWindowTitle(f"Edit {key}")
        self.setModal(True)
        
        layout = QVBoxLayout()
        layout.addWidget(QLabel(f"Parameter: {key}"))
        layout.addWidget(QLabel("Value:"))
        self.edit = QLineEdit(curr_val)
        self.edit.textChanged.connect(self.on_text_changed)
        layout.addWidget(self.edit)
        
        btn_layout = QHBoxLayout()
        ok_btn = QPushButton("OK")
        ok_btn.clicked.connect(self.accept)
        ok_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 6px 12px;
                border-radius: 3px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #666;
                color: white;
                border: none;
                padding: 6px 12px;
                border-radius: 3px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #777;
            }
        """)
        btn_layout.addWidget(ok_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)
        self.setLayout(layout)
    
    def on_text_changed(self, text):
        self.new_val = text
    
    def get_value(self): 
        return self.new_val

class CompoundEditWidget(QWidget):
    def __init__(self, editor, parent=None):
        super().__init__(parent)
        self.editor = editor
        self.current_compound_index = 0
        self.current_axle = "FRONT"
        self.comparison_compound = None
        self.comparison_axle = "FRONT"
        self.comparison_compounds = []
        self.comparison_curves = []
        self.last_file = None
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        
        toolbar = QHBoxLayout()
        
        compound_label = QLabel("Compound:")
        compound_label.setStyleSheet("color: #f0f0f0;")
        toolbar.addWidget(compound_label)
        
        self.compound_combo = QComboBox()
        self.compound_combo.currentIndexChanged.connect(self.on_compound_selected)
        toolbar.addWidget(self.compound_combo)
        
        axle_label = QLabel("Axle:")
        axle_label.setStyleSheet("color: #f0f0f0;")
        toolbar.addWidget(axle_label)
        
        self.axle_combo = QComboBox()
        self.axle_combo.addItems(["FRONT", "REAR"])
        self.axle_combo.currentTextChanged.connect(self.on_axle_selected)
        toolbar.addWidget(self.axle_combo)
        toolbar.addStretch()
        
        self.load_btn = QPushButton("Load Comparison")
        self.load_btn.clicked.connect(self.load_comparison)
        self.load_btn.setStyleSheet("""
            QPushButton {
                background-color: #ff9800;
                color: white;
                border: none;
                padding: 5px 10px;
                min-height: 20px;
                max-height: 30px;
                border-radius: 3px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #f57c00;
            }
            QPushButton:pressed {
                background-color: #e65100;
            }
        """)
        toolbar.addWidget(self.load_btn)
        
        self.hide_btn = QPushButton("Hide Comparison")
        self.hide_btn.clicked.connect(self.clear_comparison)
        self.hide_btn.setEnabled(False)
        self.hide_btn.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                border: none;
                padding: 5px 10px;
                min-height: 20px;
                max-height: 30px;
                border-radius: 3px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #d32f2f;
            }
            QPushButton:pressed {
                background-color: #b71c1c;
            }
            QPushButton:disabled {
                background-color: #666;
                color: #aaa;
            }
        """)
        toolbar.addWidget(self.hide_btn)
        
        layout.addLayout(toolbar)
        
        self.info_widget = QWidget()
        info_layout = QHBoxLayout(self.info_widget)
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.addWidget(QLabel("Comparing with:"))
        self.file_label = QLabel("")
        self.file_label.setStyleSheet("color: #FFA500; font-weight: bold;")
        info_layout.addWidget(self.file_label)
        self.compound_label = QLabel("")
        self.compound_label.setStyleSheet("color: #FFA500;")
        info_layout.addWidget(self.compound_label)
        self.axle_label = QLabel("")
        self.axle_label.setStyleSheet("color: #FFA500;")
        info_layout.addWidget(self.axle_label)
        info_layout.addStretch()
        self.info_widget.hide()
        layout.addWidget(self.info_widget)
        
        self.table = CompoundParameterTableWidget(self)
        self.table.setMinimumHeight(500)
        self.table.parameter_edited.connect(self.on_parameter_edited)
        self.table.edit_curve_requested.connect(self.on_edit_curve)
        layout.addWidget(self.table)
        
        self.setLayout(layout)
    
    def update_compounds(self, compounds):
        self.compound_combo.blockSignals(True)
        self.compound_combo.clear()
        if compounds:
            self.compound_combo.addItems([c['name'] for c in compounds])
        self.compound_combo.blockSignals(False)
        
        if compounds:
            self.current_compound_index = 0
            self.table.set_current_compound(0)
    
    def load_comparison(self):
        dlg = CompareCompoundDialog(self.window(), self.last_file, self.editor.file_dir)
        if dlg.exec_() == QDialog.Accepted:
            comp = dlg.get_selected_compound()
            axle = dlg.get_selected_axle()
            file = dlg.get_selected_file()
            
            if file and comp:
                self.last_file = file
                self.editor.last_comparison_file = file
                self.comparison_curves = dlg.get_curves()
                self.comparison_compound = comp
                self.comparison_axle = axle
                
                self.file_label.setText(Path(file).name)
                self.compound_label.setText(comp['name'])
                self.axle_label.setText(f"({axle})")
                self.info_widget.show()
                self.hide_btn.setEnabled(True)
                
                self.table.set_comparison_compound(self.comparison_compound, self.comparison_axle)
                self.editor.status_bar.showMessage(f"Loaded comparison from {Path(file).name}", 3000)
    
    def clear_comparison(self):
        self.comparison_compound = None
        self.comparison_curves = []
        self.info_widget.hide()
        self.hide_btn.setEnabled(False)
        self.table.clear_comparison()
        self.editor.last_comparison_file = None
        self.editor.status_bar.showMessage("Comparison cleared", 2000)
    
    def on_compound_selected(self, idx):
        if idx >= 0:
            self.current_compound_index = idx
            self.table.set_current_compound(idx)
            self.editor.status_bar.showMessage(
                f"Editing compound: {self.editor.compounds[idx]['name']} - {self.current_axle}", 2000
            )
    
    def on_axle_selected(self, axle):
        self.current_axle = axle
        self.table.set_current_axle(axle)
        if self.current_compound_index < len(self.editor.compounds):
            self.editor.status_bar.showMessage(
                f"Editing compound: {self.editor.compounds[self.current_compound_index]['name']} - {axle}", 2000
            )
    
    def on_parameter_edited(self, axle, key, val):
        self.editor.update_compound_parameter(self.current_compound_index, axle, key, val)
        self.table.update_table()
        self.editor.status_bar.showMessage(f"Updated {key} = {val}", 2000)
    
    def on_edit_curve(self, curve, comp_curve, axle):
        self.editor.open_curve_editor(curve, comp_curve, axle)

class PreviewDialog(QDialog):
    def __init__(self, title, vals, plot, curve_editor_widget, parent=None):
        super().__init__(parent)
        self.vals = vals
        self.plot = plot
        self.curve_editor_widget = curve_editor_widget
        self.sigma = 1.0
        self.setWindowTitle(title)
        self.setModal(True)
        
        layout = QVBoxLayout()
        layout.addWidget(QLabel("Gaussian Smoothing"))
        layout.addWidget(QLabel("Sigma:"))
        self.sigma_spin = QDoubleSpinBox()
        self.sigma_spin.setRange(0.1, 10.0)
        self.sigma_spin.setValue(1.0)
        self.sigma_spin.setSingleStep(0.1)
        self.sigma_spin.valueChanged.connect(self.update_preview)
        layout.addWidget(self.sigma_spin)
        
        btns = QHBoxLayout()
        apply_btn = QPushButton("Apply")
        apply_btn.clicked.connect(self.accept)
        apply_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 6px 12px;
                border-radius: 3px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #666;
                color: white;
                border: none;
                padding: 6px 12px;
                border-radius: 3px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #777;
            }
        """)
        btns.addWidget(apply_btn)
        btns.addWidget(cancel_btn)
        layout.addLayout(btns)
        self.setLayout(layout)
        self.update_preview()
    
    def update_preview(self):
        self.sigma = self.sigma_spin.value()
        self.preview_values = gaussian_filter1d(self.vals, sigma=self.sigma, mode='nearest')
        self.curve_editor_widget.editor.update_preview_curve(self.preview_values)
    
    def get_values(self): 
        return self.preview_values

class TireCurveEditor:
    def __init__(self, filename):
        self.filename = filename
        self.file_dir = str(Path(filename).parent)
        self.original_content = ""
        self.slip_curves = []
        self.compounds = []
        self.modified_curves = {}
        self.modified_compounds = {}
        self.current_curve_index = 0
        self.current_compound_index = 0
        self.show_all_curves = False
        self.all_curves_plots = []
        self.comparison_curve = None
        self.comparison_plot = None
        self.preview_curve = None
        self.preview_values = None
        self.point_highlight = None
        self.peak_marker = None
        self.original_curve_plot = None
        self.curve_plot = None
        self.curve_editor_widget = None
        self.curve_editor_window = None
        self.last_comparison_file = None
        self.status_bar = None
        self.compound_edit_widget = None
        
        self.parse_tire_file(filename)
        self.setup_ui()
    
    def parse_tire_file(self, filename):
        with open(filename, 'r') as f:
            self.original_content = f.read()
        
        pattern = r'\[SLIPCURVE\]\s*Name="([^"]+)"\s*Step=([0-9.e+-]+)[^\n]*\s*DropoffFunction=([0-9.e+-]+)[^\n]*\s*Data:\s*((?:\d+\.\d+\s*)+)'
        
        for match in re.finditer(pattern, self.original_content, re.MULTILINE | re.DOTALL):
            name = match.group(1).strip()
            step = float(match.group(2))
            dropoff = float(match.group(3))
            values = [float(x) for x in match.group(4).strip().split()]
            
            self.slip_curves.append({
                'name': name, 'step': step, 'dropoff_function': dropoff,
                'values': values, 'x_values': [i * step for i in range(len(values))],
                'full_match': match.group(0)
            })
        
        parts = self.original_content.split('[COMPOUND]')
        for i in range(1, len(parts)):
            content = '[COMPOUND]' + parts[i]
            
            name_match = re.search(r'Name="([^"]+)"', content)
            if not name_match:
                continue
            name = name_match.group(1)
            
            wet_match = re.search(r'WetWeather\s*=\s*(\d+)', content)
            wet_weather = int(wet_match.group(1)) if wet_match else None
            
            axles = {}
            lines = content.split('\n')
            current_axle = None
            axle_lines = []
            
            for line in lines:
                clean = line.split('//')[0].strip()
                if not clean:
                    continue
                if clean.startswith('FRONT:'):
                    if current_axle and axle_lines:
                        axles[current_axle] = self._parse_axle_params('\n'.join(axle_lines))
                    current_axle = 'FRONT'
                    axle_lines = []
                elif clean.startswith('REAR:'):
                    if current_axle and axle_lines:
                        axles[current_axle] = self._parse_axle_params('\n'.join(axle_lines))
                    current_axle = 'REAR'
                    axle_lines = []
                elif current_axle and '=' in clean:
                    axle_lines.append(line)
            
            if current_axle and axle_lines:
                axles[current_axle] = self._parse_axle_params('\n'.join(axle_lines))
            
            self.compounds.append({
                'name': name, 'wet_weather': wet_weather, 'axles': axles, 'full_match': content
            })
    
    def _parse_axle_params(self, content):
        params = {}
        for line in content.split('\n'):
            clean = line.split('//')[0].strip()
            if '=' not in clean:
                continue
            key, val = [x.strip() for x in clean.split('=', 1)]
            if val.startswith('"') and val.endswith('"'):
                val = val[1:-1]
            params[key] = val
        return params
    
    def setup_ui(self):
        self.app = QApplication.instance() or QApplication(sys.argv)
        self.window = QMainWindow()
        self.window.setWindowTitle(f"Tire Compound Editor - {Path(self.filename).name}")
        self.window.setGeometry(100, 100, 1000, 1000)
        self.window.setStyleSheet("QMainWindow { background-color: #2b2b2b; }")
        
        central = QWidget()
        self.window.setCentralWidget(central)
        layout = QVBoxLayout(central)
        
        toolbar = QHBoxLayout()
        
        self.save_btn = QPushButton("Save Changes")
        self.save_btn.clicked.connect(self.save_changes)
        self.save_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 5px 10px;
                min-height: 20px;
                max-height: 30px;
                border-radius: 3px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
            }
        """)
        toolbar.addWidget(self.save_btn)
        
        self.save_as_btn = QPushButton("Save As...")
        self.save_as_btn.clicked.connect(self.save_as)
        self.save_as_btn.setStyleSheet("""
            QPushButton {
                background-color: #666;
                color: white;
                border: none;
                padding: 5px 10px;
                min-height: 20px;
                max-height: 30px;
                border-radius: 3px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #777;
            }
            QPushButton:pressed {
                background-color: #888;
            }
        """)
        toolbar.addWidget(self.save_as_btn)
        
        self.revert_btn = QPushButton("Revert All")
        self.revert_btn.clicked.connect(self.revert_all)
        self.revert_btn.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                border: none;
                padding: 5px 10px;
                min-height: 20px;
                max-height: 30px;
                border-radius: 3px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #d32f2f;
            }
            QPushButton:pressed {
                background-color: #b71c1c;
            }
        """)
        toolbar.addWidget(self.revert_btn)
        toolbar.addStretch()
        
        layout.addLayout(toolbar)
        
        self.compound_edit_widget = CompoundEditWidget(self)
        self.compound_edit_widget.update_compounds(self.compounds)
        layout.addWidget(self.compound_edit_widget)
        
        self.status_bar = QStatusBar()
        self.window.setStatusBar(self.status_bar)
        self.window.show()
    
    def open_curve_editor(self, curve, comp=None, axle=None):
        self.curve_editor_window = QMainWindow(self.window)
        self.curve_editor_window.setWindowTitle(f"Curve Editor - {curve}")
        self.curve_editor_window.setGeometry(150, 150, 1200, 800)
        self.curve_editor_widget = SlipCurveEditWidget(self, curve, comp, axle)
        self.curve_editor_window.setCentralWidget(self.curve_editor_widget)
        self.curve_editor_window.show()
    
    def close_curve_editor(self):
        if self.curve_editor_window:
            self.curve_editor_window.close()
            self.curve_editor_window = None
            self.curve_editor_widget = None
    
    def update_compound_parameter(self, idx, axle, key, val):
        if idx >= len(self.compounds):
            return
        if idx not in self.modified_compounds:
            self.modified_compounds[idx] = {'axles': {}}
        if axle not in self.modified_compounds[idx]['axles']:
            self.modified_compounds[idx]['axles'][axle] = {}
        self.modified_compounds[idx]['axles'][axle][key] = val
        self.status_bar.showMessage("Unsaved changes", 2000)
    
    def update_point_value(self, idx, val, preserve_index=False):
        print(f"\n[TireCurveEditor] update_point_value: idx={idx}, val={val}, preserve_index={preserve_index}")
        curve = self.slip_curves[self.current_curve_index]
        if self.current_curve_index not in self.modified_curves:
            self.modified_curves[self.current_curve_index] = {
                'values': curve['values'].copy(), 'step': curve['step']
            }
        self.modified_curves[self.current_curve_index]['values'][idx] = val
        # Pass preserve_index to load_curve
        self.load_curve(self.current_curve_index, preserve_index=preserve_index)
        self.status_bar.showMessage(f"Point {idx+1} updated", 1000)
    
    def highlight_point(self, idx):
        if not hasattr(self, 'curve_editor_widget') or not self.curve_editor_widget:
            return
        if not hasattr(self, 'point_highlight') or self.point_highlight is None:
            return
            
        curve = self.slip_curves[self.current_curve_index]
        if self.current_curve_index in self.modified_curves:
            vals = self.modified_curves[self.current_curve_index]['values']
            step = self.modified_curves[self.current_curve_index]['step']
        else:
            vals, step = curve['values'], curve['step']
        x, y = idx * step, vals[idx]
        self.point_highlight.setData([x], [y])
    
    def show_preview_dialog(self, op, curve_editor_widget):
        if not self.curve_editor_widget or op != "smooth":
            return
        curve = self.slip_curves[self.current_curve_index]
        curr = self.modified_curves[self.current_curve_index]['values'] if self.current_curve_index in self.modified_curves else curve['values'].copy()
        dlg = PreviewDialog("Smooth", curr, self.curve_editor_widget.plot, curve_editor_widget, self.curve_editor_window)
        if dlg.exec_() == QDialog.Accepted:
            if self.current_curve_index not in self.modified_curves:
                self.modified_curves[self.current_curve_index] = {'values': curve['values'].copy(), 'step': curve['step']}
            self.modified_curves[self.current_curve_index]['values'] = dlg.get_values()
            self.load_curve(self.current_curve_index, preserve_index=True)
        self.clear_preview()
    
    def update_preview_curve(self, vals):
        if not self.curve_editor_widget:
            return
        curve = self.slip_curves[self.current_curve_index]
        step = self.modified_curves[self.current_curve_index]['step'] if self.current_curve_index in self.modified_curves else curve['step']
        x = [i * step for i in range(len(vals))]
        if self.preview_curve:
            self.preview_curve.setData(x, vals)
            self.preview_curve.show()
        if self.curve_plot:
            self.curve_plot.setPen(pg.mkPen('b', width=2, style=Qt.DashLine))
    
    def clear_preview(self):
        if self.preview_curve:
            self.preview_curve.hide()
        if self.curve_plot:
            self.curve_plot.setPen(pg.mkPen('b', width=2))
    
    def load_curve(self, idx, preserve_index=False):
        print(f"\n[TireCurveEditor] load_curve: idx={idx}, preserve_index={preserve_index}")
        self.current_curve_index = idx
        curve = self.slip_curves[idx]
        if idx in self.modified_curves:
            vals, step = self.modified_curves[idx]['values'], self.modified_curves[idx]['step']
        else:
            vals, step = curve['values'], curve['step']
        
        if self.curve_editor_widget:
            x = [i * step for i in range(len(vals))]
            if self.curve_plot:
                self.curve_plot.setData(x, vals)
            
            if idx in self.modified_curves and self.original_curve_plot:
                orig_x = [i * curve['step'] for i in range(len(curve['values']))]
                self.original_curve_plot.setData(orig_x, curve['values'])
                self.original_curve_plot.show()
            elif self.original_curve_plot:
                self.original_curve_plot.hide()
            
            peak_idx = np.argmax(vals)
            if self.peak_marker:
                self.peak_marker.setData([x[peak_idx]], [vals[peak_idx]])
            
            if hasattr(self.curve_editor_widget, 'point_edit'):
                # Pass preserve_index to set_values
                self.curve_editor_widget.point_edit.set_values(vals, preserve_index=preserve_index)
            if hasattr(self.curve_editor_widget, 'step_spin'):
                self.curve_editor_widget.step_spin.setValue(step)
            
            # Get the current index from point_edit after setting values
            current_idx = self.curve_editor_widget.point_edit.current_point_index
            self.highlight_point(current_idx)
            
            if hasattr(self.curve_editor_widget, 'plot'):
                self.curve_editor_widget.plot.autoRange()
    
    def on_step_changed(self, val):
        if not self.curve_editor_widget:
            return
        curve = self.slip_curves[self.current_curve_index]
        if self.current_curve_index not in self.modified_curves:
            self.modified_curves[self.current_curve_index] = {'values': curve['values'].copy(), 'step': curve['step']}
        self.modified_curves[self.current_curve_index]['step'] = val
        self.load_curve(self.current_curve_index, preserve_index=True)
    
    def reset_curve(self):
        if self.current_curve_index in self.modified_curves:
            del self.modified_curves[self.current_curve_index]
            self.load_curve(self.current_curve_index, preserve_index=True)
    
    def revert_all(self):
        reply = QMessageBox.question(self.window, "Confirm", 
                                    "Revert all changes? This will undo all modifications to curves and compounds.",
                                    QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.modified_curves.clear()
            self.modified_compounds.clear()
            if self.compound_edit_widget:
                self.compound_edit_widget.update_compounds(self.compounds)
            if self.curve_editor_widget:
                self.load_curve(self.current_curve_index, preserve_index=True)
            self.status_bar.showMessage("All changes reverted", 3000)
    
    def save_changes(self):
        self.save_to_file(self.filename)
    
    def save_as(self):
        fname, _ = QFileDialog.getSaveFileName(
            self.window, "Save As", str(Path(self.filename).with_suffix('.tbc')),
            "Tire files (*.tbc);;All files (*.*)"
        )
        if fname:
            self.save_to_file(fname)
    
    def save_to_file(self, fname):
        try:
            new = self.original_content
            
            for idx in sorted(self.modified_curves.keys(), reverse=True):
                mod = self.modified_curves[idx]
                orig = self.slip_curves[idx]
                lines = []
                for i in range(0, len(mod['values']), 10):
                    lines.append(' '.join(f"{v:.6f}" for v in mod['values'][i:i+10]))
                new_block = f'[SLIPCURVE]\nName="{orig["name"]}"\nStep={mod["step"]:.6f}\nDropoffFunction={orig["dropoff_function"]:.1f}\nData:\n' + '\n'.join(lines) + '\n'
                new = new.replace(orig['full_match'], new_block)
            
            for idx in sorted(self.modified_compounds.keys(), reverse=True):
                mod = self.modified_compounds[idx]
                orig = self.compounds[idx]
                content = orig['full_match']
                for axle, params in mod['axles'].items():
                    for key, val in params.items():
                        pattern = rf'({axle}:.*?{key}\s*=\s*)[^\n]*'
                        import re
                        content = re.sub(pattern, f'\\1{val}', content, flags=re.DOTALL)
                new = new.replace(orig['full_match'], content)
            
            with open(fname, 'w') as f:
                f.write(new)
            
            self.original_content = new
            self.modified_curves.clear()
            self.modified_compounds.clear()
            self.slip_curves.clear()
            self.compounds.clear()
            self.parse_tire_file(fname)
            if self.compound_edit_widget:
                self.compound_edit_widget.update_compounds(self.compounds)
            QMessageBox.information(self.window, "Success", f"Changes saved to {fname}")
            self.status_bar.showMessage("Changes saved", 3000)
        except Exception as e:
            QMessageBox.critical(self.window, "Error", str(e))
            import traceback
            traceback.print_exc()
    
    def run(self):
        return self.app.exec_()

def main():
    if len(sys.argv) < 2:
        print("Usage: python editor.py <file>")
        print("\nExample:")
        print("  python editor.py tire.tbc")
        return
    
    filename = sys.argv[1]
    
    try:
        app = TireCurveEditor(filename)
        sys.exit(app.run())
    except FileNotFoundError:
        print(f"Error: File '{filename}' not found.")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
