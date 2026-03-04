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
        self.setup_ui()
        
    def setup_ui(self):
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.point_label = QLabel("Point: 0/0")
        self.point_label.setStyleSheet("color: #4CAF50; font-weight: bold;")
        layout.addWidget(self.point_label)
        
        layout.addWidget(QLabel("Value:"))
        self.value_spin = QDoubleSpinBox()
        self.value_spin.setRange(-10.0, 10.0)
        self.value_spin.setDecimals(6)
        self.value_spin.setSingleStep(0.001)
        self.value_spin.valueChanged.connect(self.on_value_changed)
        
        self.value_spin.installEventFilter(self)
        
        layout.addWidget(self.value_spin)
        
        instr_label = QLabel("←/→: Select point, ↑/↓: Change value")
        instr_label.setStyleSheet("color: #888; font-style: italic;")
        layout.addWidget(instr_label)
        
        layout.addStretch()
        self.setLayout(layout)
        
        self.setFocusPolicy(Qt.StrongFocus)
    
    def eventFilter(self, obj, event):
        if obj == self.value_spin and event.type() == QEvent.KeyPress:
            if event.key() == Qt.Key_Left:
                self.select_previous_point()
                return True
            elif event.key() == Qt.Key_Right:
                self.select_next_point()
                return True
            elif event.key() == Qt.Key_Up:
                self.increase_value()
                return True
            elif event.key() == Qt.Key_Down:
                self.decrease_value()
                return True
        return super().eventFilter(obj, event)
    
    def set_values(self, values):
        self.current_values = values.copy() if values else []
        self.current_point_index = 0
        self.update_display()
    
    def update_display(self):
        if self.current_values:
            self.point_label.setText(f"Point: {self.current_point_index + 1}/{len(self.current_values)}")
            self.value_spin.blockSignals(True)
            self.value_spin.setValue(self.current_values[self.current_point_index])
            self.value_spin.blockSignals(False)
    
    def on_value_changed(self, value):
        if self.current_values and self.current_point_index < len(self.current_values):
            self.current_values[self.current_point_index] = value
            self.editor.update_point_value(self.current_point_index, value)
    
    def select_previous_point(self):
        if self.current_values and self.current_point_index > 0:
            self.current_point_index -= 1
            self.update_display()
            self.editor.highlight_point(self.current_point_index)
    
    def select_next_point(self):
        if self.current_values and self.current_point_index < len(self.current_values) - 1:
            self.current_point_index += 1
            self.update_display()
            self.editor.highlight_point(self.current_point_index)
    
    def increase_value(self):
        if self.current_values:
            current_val = self.current_values[self.current_point_index]
            self.value_spin.setValue(current_val + 0.001)
    
    def decrease_value(self):
        if self.current_values:
            current_val = self.current_values[self.current_point_index]
            self.value_spin.setValue(current_val - 0.001)
    
    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Left:
            self.select_previous_point()
            event.accept()
        elif event.key() == Qt.Key_Right:
            self.select_next_point()
            event.accept()
        elif event.key() == Qt.Key_Up:
            self.increase_value()
            event.accept()
        elif event.key() == Qt.Key_Down:
            self.decrease_value()
            event.accept()
        else:
            super().keyPressEvent(event)
    
    def focusInEvent(self, event):
        super().focusInEvent(event)
        self.editor.highlight_point(self.current_point_index)

class PreviewDialog(QDialog):
    def __init__(self, title, operation_type, current_values, plot_widget, parent=None):
        super().__init__(parent)
        self.operation_type = operation_type
        self.original_values = current_values.copy()
        self.current_values = current_values.copy()
        self.preview_values = current_values.copy()
        self.plot_widget = plot_widget
        self.preview_curve = None
        self.setup_ui(title)
        
    def setup_ui(self, title):
        self.setWindowTitle(title)
        self.setModal(True)
        self.setMinimumWidth(450)
        
        layout = QVBoxLayout()
        
        preview_label = QLabel("Preview - Changes will show in real-time")
        preview_label.setStyleSheet("color: #4CAF50; font-weight: bold;")
        layout.addWidget(preview_label)
        
        self.preview_plot = pg.PlotWidget(title="Preview")
        self.preview_plot.setLabel('left', 'Force')
        self.preview_plot.setLabel('bottom', 'Slip')
        self.preview_plot.showGrid(x=True, y=True, alpha=0.3)
        self.preview_plot.setFixedHeight(150)
        layout.addWidget(self.preview_plot)
        
        x_values = list(range(len(self.original_values)))
        self.preview_plot.plot(x_values, self.original_values, 
                               pen=pg.mkPen('gray', width=1, style=Qt.DashLine), 
                               name='Original')
        
        self.preview_curve = self.preview_plot.plot(x_values, self.original_values,
                                                     pen=pg.mkPen('y', width=2),
                                                     name='Preview')
        
        control_group = QGroupBox("Parameters")
        control_layout = QVBoxLayout()
        
        if self.operation_type == "smooth":
            control_layout.addWidget(QLabel("Smoothing Sigma:"))
            self.param_input = QDoubleSpinBox()
            self.param_input.setRange(0.1, 5.0)
            self.param_input.setValue(1.0)
            self.param_input.setSingleStep(0.1)
            self.param_input.setDecimals(1)
            self.param_input.valueChanged.connect(self.update_preview)
        
        control_layout.addWidget(self.param_input)
        control_group.setLayout(control_layout)
        layout.addWidget(control_group)
        
        stats_group = QGroupBox("Statistics Comparison")
        stats_layout = QGridLayout()
        
        stats_layout.addWidget(QLabel("Metric"), 0, 0)
        stats_layout.addWidget(QLabel("Original"), 0, 1)
        stats_layout.addWidget(QLabel("Preview"), 0, 2)
        
        metrics = ['Min:', 'Max:', 'Mean:', 'Peak:']
        self.stats_labels = {}
        for i, metric in enumerate(metrics):
            stats_layout.addWidget(QLabel(metric), i+1, 0)
            
            orig_label = QLabel("0.000")
            orig_label.setStyleSheet("color: #888;")
            stats_layout.addWidget(orig_label, i+1, 1)
            
            preview_label = QLabel("0.000")
            preview_label.setStyleSheet("color: #4CAF50; font-weight: bold;")
            stats_layout.addWidget(preview_label, i+1, 2)
            
            self.stats_labels[metric] = {'original': orig_label, 'preview': preview_label}
        
        stats_group.setLayout(stats_layout)
        layout.addWidget(stats_group)
        
        button_layout = QHBoxLayout()
        
        self.apply_btn = QPushButton("✅ Apply Changes")
        self.apply_btn.clicked.connect(self.accept)
        self.apply_btn.setStyleSheet("background-color: #4CAF50; color: white;")
        
        self.revert_btn = QPushButton("↺ Revert to Original")
        self.revert_btn.clicked.connect(self.revert_to_original)
        
        self.cancel_btn = QPushButton("✖ Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        
        button_layout.addWidget(self.apply_btn)
        button_layout.addWidget(self.revert_btn)
        button_layout.addWidget(self.cancel_btn)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
        
        self.update_preview()
    
    def update_preview(self):
        param_value = self.param_input.value()
        
        if self.operation_type == "smooth":
            values = np.array(self.original_values)
            self.preview_values = gaussian_filter1d(values, sigma=param_value).tolist()
        
        x_values = list(range(len(self.preview_values)))
        self.preview_curve.setData(x_values, self.preview_values)
        
        self.update_statistics()
        
        if self.parent() and hasattr(self.parent(), 'update_preview_curve'):
            self.parent().update_preview_curve(self.preview_values)
    
    def update_statistics(self):
        if self.preview_values:
            orig_min = min(self.original_values)
            orig_max = max(self.original_values)
            orig_mean = np.mean(self.original_values)
            orig_peak_idx = np.argmax(self.original_values)
            orig_peak = self.original_values[orig_peak_idx]
            
            preview_min = min(self.preview_values)
            preview_max = max(self.preview_values)
            preview_mean = np.mean(self.preview_values)
            preview_peak_idx = np.argmax(self.preview_values)
            preview_peak = self.preview_values[preview_peak_idx]
            
            self.stats_labels['Min:']['original'].setText(f"{orig_min:.3f}")
            self.stats_labels['Max:']['original'].setText(f"{orig_max:.3f}")
            self.stats_labels['Mean:']['original'].setText(f"{orig_mean:.3f}")
            self.stats_labels['Peak:']['original'].setText(f"{orig_peak:.3f}")
            
            self.stats_labels['Min:']['preview'].setText(f"{preview_min:.3f}")
            self.stats_labels['Max:']['preview'].setText(f"{preview_max:.3f}")
            self.stats_labels['Mean:']['preview'].setText(f"{preview_mean:.3f}")
            self.stats_labels['Peak:']['preview'].setText(f"{preview_peak:.3f}")
    
    def revert_to_original(self):
        self.param_input.setValue(1.0)
        self.preview_values = self.original_values.copy()
        self.update_preview()
        if self.parent() and hasattr(self.parent(), 'clear_preview'):
            self.parent().clear_preview()
    
    def get_values(self):
        return self.preview_values
    
    def closeEvent(self, event):
        if self.parent() and hasattr(self.parent(), 'clear_preview'):
            self.parent().clear_preview()
        event.accept()

class ParameterEditDialog(QDialog):
    def __init__(self, key, value, parent=None):
        super().__init__(parent)
        self.key = key
        self.original_value = value
        self.new_value = value
        self.setup_ui()
        
    def setup_ui(self):
        self.setWindowTitle(f"Edit Parameter: {self.key}")
        self.setModal(True)
        self.setMinimumWidth(400)
        
        layout = QVBoxLayout()
        
        key_layout = QHBoxLayout()
        key_layout.addWidget(QLabel("Parameter:"))
        key_label = QLabel(self.key)
        key_label.setStyleSheet("font-weight: bold; color: #4CAF50;")
        key_layout.addWidget(key_label)
        key_layout.addStretch()
        layout.addLayout(key_layout)
        
        current_layout = QHBoxLayout()
        current_layout.addWidget(QLabel("Current:"))
        current_label = QLabel(self.original_value)
        current_label.setStyleSheet("color: #888;")
        current_layout.addWidget(current_label)
        current_layout.addStretch()
        layout.addLayout(current_layout)
        
        layout.addWidget(QLabel("New Value:"))
        
        if self.original_value.startswith('(') and self.original_value.endswith(')'):
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
                tuple_layout.addWidget(editor)
                self.tuple_editors.append(editor)
            
            layout.addWidget(tuple_widget)
            self.value_editor = None
            
        else:
            try:
                float(self.original_value)
                self.value_editor = QDoubleSpinBox()
                self.value_editor.setRange(-1e12, 1e12)
                self.value_editor.setDecimals(6)
                self.value_editor.setValue(float(self.original_value))
                self.value_editor.valueChanged.connect(self.on_value_changed)
                layout.addWidget(self.value_editor)
            except ValueError:
                self.value_editor = QLineEdit(self.original_value)
                self.value_editor.textChanged.connect(self.on_text_changed)
                layout.addWidget(self.value_editor)
        
        button_layout = QHBoxLayout()
        
        self.save_btn = QPushButton("💾 Save")
        self.save_btn.clicked.connect(self.accept)
        self.save_btn.setStyleSheet("background-color: #4CAF50; color: white;")
        
        self.revert_btn = QPushButton("↺ Revert to Original")
        self.revert_btn.clicked.connect(self.revert_to_original)
        
        self.cancel_btn = QPushButton("✖ Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        
        button_layout.addWidget(self.save_btn)
        button_layout.addWidget(self.revert_btn)
        button_layout.addWidget(self.cancel_btn)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
    
    def update_tuple_value(self, index, text):
        values = []
        for i, editor in enumerate(self.tuple_editors):
            val = editor.text()
            if i == index:
                val = text
            values.append(val)
        
        self.new_value = f"({', '.join(values)})"
    
    def on_value_changed(self, value):
        self.new_value = str(value)
    
    def on_text_changed(self, text):
        self.new_value = text
    
    def revert_to_original(self):
        if self.value_editor:
            if isinstance(self.value_editor, QDoubleSpinBox):
                self.value_editor.setValue(float(self.original_value))
            else:
                self.value_editor.setText(self.original_value)
        else:
            inner = self.original_value[1:-1]
            values = [v.strip() for v in inner.split(',')]
            for i, val in enumerate(values):
                self.tuple_editors[i].setText(val)
        
        self.new_value = self.original_value
    
    def get_value(self):
        return self.new_value

class CompareFileDialog(QDialog):
    def __init__(self, parent=None, last_file=None, start_dir=None):
        super().__init__(parent)
        self.selected_file = None
        self.selected_curve_index = 0
        self.comparison_curves = []
        self.last_file = last_file
        self.start_dir = start_dir
        self.setup_ui()
        
    def setup_ui(self):
        self.setWindowTitle("Load Comparison Curve")
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
        
        curve_group = QGroupBox("Select Curve")
        curve_layout = QVBoxLayout()
        
        self.file_selection_group = QButtonGroup()
        
        self.same_file_radio = QRadioButton("Use current comparison file")
        self.same_file_radio.setChecked(True)
        self.same_file_radio.toggled.connect(self.on_file_selection_changed)
        
        self.different_file_radio = QRadioButton("Load different file")
        self.different_file_radio.toggled.connect(self.on_file_selection_changed)
        
        curve_layout.addWidget(self.same_file_radio)
        curve_layout.addWidget(self.different_file_radio)
        
        self.curve_combo = QComboBox()
        self.curve_combo.setEnabled(True)
        self.curve_combo.currentIndexChanged.connect(self.on_curve_selected)
        
        curve_layout.addWidget(QLabel("Select curve:"))
        curve_layout.addWidget(self.curve_combo)
        
        self.info_label = QLabel("")
        self.info_label.setStyleSheet("color: #888; font-style: italic;")
        curve_layout.addWidget(self.info_label)
        
        curve_group.setLayout(curve_layout)
        layout.addWidget(curve_group)
        
        preview_group = QGroupBox("Preview")
        preview_layout = QVBoxLayout()
        
        self.preview_plot = pg.PlotWidget()
        self.preview_plot.setLabel('left', 'Force')
        self.preview_plot.setLabel('bottom', 'Slip')
        self.preview_plot.showGrid(x=True, y=True, alpha=0.3)
        self.preview_plot.setFixedHeight(150)
        preview_layout.addWidget(self.preview_plot)
        
        preview_group.setLayout(preview_layout)
        layout.addWidget(preview_group)
        
        button_layout = QHBoxLayout()
        
        self.show_btn = QPushButton("Show Curve")
        self.show_btn.clicked.connect(self.accept)
        self.show_btn.setEnabled(False)
        self.show_btn.setStyleSheet("background-color: #4CAF50; color: white;")
        
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        
        button_layout.addWidget(self.show_btn)
        button_layout.addWidget(self.cancel_btn)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
        
        if self.last_file and Path(self.last_file).exists():
            self.load_file(self.last_file)
            self.same_file_radio.setChecked(True)
        else:
            self.same_file_radio.setEnabled(False)
            self.different_file_radio.setChecked(True)
    
    def on_file_selection_changed(self):
        if self.same_file_radio.isChecked():
            if self.last_file and Path(self.last_file).exists():
                self.load_file(self.last_file)
                self.browse_btn.setEnabled(False)
                self.file_path_edit.setEnabled(False)
            else:
                self.different_file_radio.setChecked(True)
        else:
            self.browse_btn.setEnabled(True)
            self.file_path_edit.setEnabled(True)
            if not self.file_path_edit.text():
                self.curve_combo.clear()
                self.curve_combo.setEnabled(False)
                self.show_btn.setEnabled(False)
                self.info_label.setText("No file selected")
                self.preview_plot.clear()
    
    def browse_file(self):
        start_dir = self.start_dir if self.start_dir else str(Path.home())
        if self.last_file and not start_dir:
            start_dir = str(Path(self.last_file).parent)
        
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Select Tire File",
            start_dir,
            "Tire files (*.tbc *.tyr);;All files (*.*)"
        )
        
        if filename:
            self.load_file(filename)
            self.different_file_radio.setChecked(True)
    
    def load_file(self, filename):
        try:
            self.comparison_curves = self.parse_tire_file(filename)
            
            if self.comparison_curves:
                self.file_path_edit.setText(filename)
                self.selected_file = filename
                
                self.curve_combo.clear()
                self.curve_combo.addItems([c['name'] for c in self.comparison_curves])
                self.curve_combo.setEnabled(True)
                
                self.info_label.setText(f"Loaded {len(self.comparison_curves)} curves from {Path(filename).name}")
                self.info_label.setStyleSheet("color: #4CAF50;")
                
                self.show_btn.setEnabled(True)
                
                self.on_curve_selected(0)
            else:
                QMessageBox.warning(self, "No Curves", "No slip curves found in the selected file.")
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load file: {e}")
    
    def parse_tire_file(self, filename):
        curves = []
        
        with open(filename, 'r') as f:
            content = f.read()
        
        slip_curve_pattern = r'(\[SLIPCURVE\]\s*Name="([^"]+)"\s*Step=([0-9.e+-]+)[^\n]*\s*DropoffFunction=([0-9.e+-]+)[^\n]*\s*Data:\s*((?:\d+\.\d+\s*)+))'
        
        for match in re.finditer(slip_curve_pattern, content, re.MULTILINE | re.DOTALL):
            name = match.group(2)
            step = float(match.group(3))
            dropoff = float(match.group(4))
            
            data_str = match.group(5).strip()
            values = [float(x) for x in data_str.split()]
            
            curves.append({
                'name': name,
                'step': step,
                'dropoff_function': dropoff,
                'values': values,
                'x_values': [i * step for i in range(len(values))]
            })
        
        return curves
    
    def on_curve_selected(self, index):
        if index >= 0 and index < len(self.comparison_curves):
            self.selected_curve_index = index
            curve = self.comparison_curves[index]
            
            self.preview_plot.clear()
            self.preview_plot.plot(curve['x_values'], curve['values'], 
                                   pen=pg.mkPen('y', width=2))
            self.preview_plot.autoRange()
    
    def get_selected_curve(self):
        if self.comparison_curves and self.selected_curve_index < len(self.comparison_curves):
            return self.comparison_curves[self.selected_curve_index]
        return None
    
    def get_selected_file(self):
        return self.selected_file

class CompoundEditWidget(QWidget):
    def __init__(self, editor, parent=None):
        super().__init__(parent)
        self.editor = editor
        self.current_compound_index = 0
        self.current_axle = "FRONT"
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        
        select_layout = QHBoxLayout()
        select_layout.addWidget(QLabel("Compound:"))
        self.compound_combo = QComboBox()
        self.compound_combo.currentIndexChanged.connect(self.on_compound_selected)
        select_layout.addWidget(self.compound_combo)
        
        select_layout.addWidget(QLabel("Axle:"))
        self.axle_combo = QComboBox()
        self.axle_combo.addItems(["FRONT", "REAR"])
        self.axle_combo.currentTextChanged.connect(self.on_axle_selected)
        select_layout.addWidget(self.axle_combo)
        
        select_layout.addStretch()
        layout.addLayout(select_layout)
        
        self.param_list = QListWidget()
        self.param_list.setMaximumHeight(200)
        self.param_list.itemDoubleClicked.connect(self.edit_parameter)
        layout.addWidget(self.param_list)
        
        self.setLayout(layout)
    
    def update_compounds(self, compounds):
        self.compound_combo.blockSignals(True)
        self.compound_combo.clear()
        if compounds:
            self.compound_combo.addItems([c['name'] for c in compounds])
        self.compound_combo.blockSignals(False)
        
        if compounds:
            self.current_compound_index = 0
            self.load_compound(0)
        else:
            self.param_list.clear()
            self.param_list.addItem("No compounds found in file")
    
    def load_compound(self, index):
        if index >= 0 and index < len(self.editor.compounds):
            self.current_compound_index = index
            compound = self.editor.compounds[index]
            self.update_parameters_list()
            return True
        return False
    
    def update_parameters_list(self):
        self.param_list.clear()
        
        if self.current_compound_index < len(self.editor.compounds):
            compound = self.editor.compounds[self.current_compound_index]
            
            items = [f"Name = {compound['name']}"]
            
            if 'wet_weather' in compound and compound['wet_weather'] is not None:
                items.append(f"WetWeather = {compound['wet_weather']}")
            
            if self.current_axle in compound['axles']:
                axle_data = compound['axles'][self.current_axle]
                for key, value in axle_data.items():
                    items.append(f"{key} = {value}")
            else:
                items.append(f"No {self.current_axle} section found")
            
            for item in items:
                self.param_list.addItem(item)
        else:
            self.param_list.addItem("No compound selected")
    
    def on_compound_selected(self, index):
        if index >= 0 and self.load_compound(index):
            self.editor.status_bar.showMessage(
                f"Editing compound: {self.editor.compounds[index]['name']} - {self.current_axle}", 
                2000
            )
    
    def on_axle_selected(self, axle):
        self.current_axle = axle
        self.update_parameters_list()
        if self.current_compound_index < len(self.editor.compounds):
            self.editor.status_bar.showMessage(
                f"Editing compound: {self.editor.compounds[self.current_compound_index]['name']} - {axle}", 
                2000
            )
    
    def edit_parameter(self, item):
        text = item.text()
        if '=' not in text:
            return
        
        key, value = text.split('=', 1)
        key = key.strip()
        value = value.strip()
        
        if key == 'Name':
            QMessageBox.information(self, "Info", "Compound name cannot be edited here")
            return
        
        dialog = ParameterEditDialog(key, value, self.window())
        if dialog.exec_() == QDialog.Accepted:
            new_value = dialog.get_value()
            
            if new_value != value:
                self.editor.update_compound_parameter(
                    self.current_compound_index,
                    self.current_axle,
                    key,
                    new_value
                )
                self.update_parameters_list()

class TireCurveEditor:
    def __init__(self, filename):
        self.filename = filename
        self.file_dir = str(Path(filename).parent)
        self.original_content = ""
        self.slip_curves = []
        self.compounds = []
        self.curve_matches = []
        self.modified_curves = {}
        self.modified_compounds = {}
        self.current_curve_index = 0
        self.show_all_curves = False
        self.all_curves_plots = []
        self.comparison_curve = None
        self.comparison_plot = None
        self.preview_curve = None
        self.preview_values = None
        self.point_highlight = None
        self.point_edit_widget = None
        self.compound_edit_widget = None
        self.legend = None
        self.last_comparison_file = None
        
        self.parse_tire_file(filename)
        self.setup_ui()
    
    def parse_tire_file(self, filename):
        with open(filename, 'r') as f:
            self.original_content = f.read()
        
        content_without_comments = re.sub(r'//.*$', '', self.original_content, flags=re.MULTILINE)
        
        slip_curve_pattern = r'\[SLIPCURVE\]\s*Name="([^"]+)"\s*Step=([0-9.e+-]+)[^\n]*\s*DropoffFunction=([0-9.e+-]+)[^\n]*\s*Data:\s*((?:\d+\.\d+\s*)+)'
        
        for match in re.finditer(slip_curve_pattern, self.original_content, re.MULTILINE | re.DOTALL):
            full_match = match.group(0)
            name = match.group(1)
            step = float(match.group(2))
            dropoff = float(match.group(3))
            
            data_str = match.group(4).strip()
            values = [float(x) for x in data_str.split()]
            
            self.slip_curves.append({
                'name': name,
                'step': step,
                'dropoff_function': dropoff,
                'values': values,
                'x_values': [i * step for i in range(len(values))],
                'full_match': full_match,
                'data_str': data_str
            })
            self.curve_matches.append(match)
        
        parts = self.original_content.split('[COMPOUND]')
        
        for i in range(1, len(parts)):
            compound_content = '[COMPOUND]' + parts[i]
            
            end_pos = len(compound_content)
            
            full_pos = self.original_content.find(compound_content.strip())
            if full_pos >= 0:
                next_compound = self.original_content.find('[COMPOUND]', full_pos + 1)
                next_slipcurve = self.original_content.find('[SLIPCURVE]', full_pos + 1)
                
                if next_compound >= 0 and next_slipcurve >= 0:
                    end_pos = min(next_compound, next_slipcurve) - full_pos
                elif next_compound >= 0:
                    end_pos = next_compound - full_pos
                elif next_slipcurve >= 0:
                    end_pos = next_slipcurve - full_pos
            
            full_match = compound_content[:end_pos].strip()
            
            name_match = re.search(r'Name="([^"]+)"', full_match)
            if not name_match:
                continue
            name = name_match.group(1)
            
            wet_weather = None
            wet_match = re.search(r'WetWeather\s*=\s*(\d+)', full_match)
            if wet_match:
                wet_weather = int(wet_match.group(1))
            
            axles = {}
            
            lines = full_match.split('\n')
            current_axle = None
            current_axle_lines = []
            
            for line in lines:
                clean_line = line.split('//')[0].strip()
                if not clean_line:
                    continue
                
                if clean_line.startswith('FRONT:'):
                    if current_axle and current_axle_lines:
                        axles[current_axle] = self._parse_axle_params('\n'.join(current_axle_lines))
                    current_axle = 'FRONT'
                    current_axle_lines = []
                elif clean_line.startswith('REAR:'):
                    if current_axle and current_axle_lines:
                        axles[current_axle] = self._parse_axle_params('\n'.join(current_axle_lines))
                    current_axle = 'REAR'
                    current_axle_lines = []
                elif current_axle and '=' in clean_line:
                    current_axle_lines.append(line)
            
            if current_axle and current_axle_lines:
                axles[current_axle] = self._parse_axle_params('\n'.join(current_axle_lines))
            
            self.compounds.append({
                'name': name,
                'wet_weather': wet_weather,
                'axles': axles,
                'full_match': full_match
            })
    
    def _parse_axle_params(self, axle_content):
        params = {}
        
        for line in axle_content.split('\n'):
            clean_line = line.split('//')[0].strip()
            if not clean_line or '=' not in clean_line:
                continue
            
            parts = clean_line.split('=', 1)
            if len(parts) == 2:
                key = parts[0].strip()
                value = parts[1].strip()
                params[key] = value
        
        return params
    
    def setup_ui(self):
        self.app = QApplication.instance() or QApplication(sys.argv)
        self.window = QMainWindow()
        self.window.setWindowTitle(f"Tire Curve Editor - {Path(self.filename).name}")
        self.window.setGeometry(100, 100, 1600, 1000)
        
        self.apply_dark_theme()
        
        central_widget = QWidget()
        self.window.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        
        control_bar = QWidget()
        control_layout = QHBoxLayout(control_bar)
        control_layout.setContentsMargins(0, 0, 0, 0)
        
        control_layout.addWidget(QLabel("Curve:"))
        self.curve_combo = QComboBox()
        self.curve_combo.addItems([c['name'] for c in self.slip_curves])
        self.curve_combo.currentIndexChanged.connect(self.on_curve_selected)
        self.curve_combo.setStyleSheet("""
            QComboBox {
                background-color: #3c3c3c;
                color: #ffffff;
                border: 2px solid #4CAF50;
                border-radius: 3px;
                padding: 4px;
                min-width: 150px;
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
            QComboBox QAbstractItemView {
                background-color: #2b2b2b;
                color: #ffffff;
                selection-background-color: #4CAF50;
                border: 1px solid #4CAF50;
            }
        """)
        control_layout.addWidget(self.curve_combo)
        
        self.show_all_checkbox = QCheckBox("Show All Curves")
        self.show_all_checkbox.setStyleSheet("""
            QCheckBox {
                color: #ffffff;
                spacing: 5px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
            }
            QCheckBox::indicator:unchecked {
                border: 2px solid #888;
                background-color: #3c3c3c;
            }
            QCheckBox::indicator:checked {
                border: 2px solid #4CAF50;
                background-color: #4CAF50;
            }
        """)
        self.show_all_checkbox.stateChanged.connect(self.toggle_show_all_curves)
        control_layout.addWidget(self.show_all_checkbox)
        
        compare_separator = QFrame()
        compare_separator.setFrameShape(QFrame.VLine)
        compare_separator.setFrameShadow(QFrame.Sunken)
        compare_separator.setStyleSheet("color: #555;")
        control_layout.addWidget(compare_separator)
        
        self.load_compare_btn = QPushButton("📊 Load Comparison")
        self.load_compare_btn.clicked.connect(self.load_comparison_curve)
        self.load_compare_btn.setStyleSheet("background-color: #ff9800;")
        control_layout.addWidget(self.load_compare_btn)
        
        self.hide_compare_btn = QPushButton("❌ Hide Comparison")
        self.hide_compare_btn.clicked.connect(self.hide_comparison_curve)
        self.hide_compare_btn.setEnabled(False)
        self.hide_compare_btn.setStyleSheet("background-color: #f44336;")
        control_layout.addWidget(self.hide_compare_btn)
        
        control_layout.addWidget(QLabel("Step:"))
        self.step_spin = QDoubleSpinBox()
        self.step_spin.setRange(0.0001, 1.0)
        self.step_spin.setDecimals(6)
        self.step_spin.setSingleStep(0.001)
        self.step_spin.valueChanged.connect(self.on_step_changed)
        control_layout.addWidget(self.step_spin)
        
        control_layout.addStretch()
        
        self.smooth_btn = QPushButton("〰 Smooth")
        self.smooth_btn.clicked.connect(lambda: self.show_preview_dialog("smooth"))
        control_layout.addWidget(self.smooth_btn)
        
        self.reset_btn = QPushButton("↺ Reset")
        self.reset_btn.clicked.connect(self.reset_curve)
        control_layout.addWidget(self.reset_btn)
        
        left_layout.addWidget(control_bar)
        
        self.point_edit_widget = PointEditWidget(self, left_panel)
        self.point_edit_widget.setFocusPolicy(Qt.ClickFocus)
        left_layout.addWidget(self.point_edit_widget)
        
        self.plot_widget = pg.PlotWidget(title="Slip Curve")
        self.plot_widget.setLabel('left', 'Normalized Force')
        self.plot_widget.setLabel('bottom', 'Slip')
        self.plot_widget.showGrid(x=True, y=True, alpha=0.3)
        self.plot_widget.setMouseEnabled(x=True, y=True)
        self.plot_widget.setMinimumHeight(500)
        self.plot_widget.setFocusPolicy(Qt.StrongFocus)
        
        self.legend = self.plot_widget.addLegend()
        
        self.curve_plot = self.plot_widget.plot(pen=pg.mkPen('b', width=2), name='Slip Curve')
        self.original_curve_plot = self.plot_widget.plot(pen=pg.mkPen('gray', width=1, style=Qt.DashLine), name='Original')
        
        self.comparison_plot = self.plot_widget.plot(pen=pg.mkPen('orange', width=2, style=Qt.DashLine), 
                                                      name='Comparison')
        self.comparison_plot.hide()
        
        self.preview_curve = self.plot_widget.plot(pen=pg.mkPen('y', width=2, style=Qt.DashLine), name='Preview')
        self.preview_curve.hide()
        
        self.point_highlight = pg.ScatterPlotItem(pen='r', brush=None, size=15, symbol='o', name='Selected Point')
        
        self.peak_marker = pg.ScatterPlotItem(pen='r', brush='r', size=15, symbol='star', name='Peak')
        
        self.plot_widget.addItem(self.peak_marker)
        self.plot_widget.addItem(self.point_highlight)
        
        left_layout.addWidget(self.plot_widget, 2)
        
        stats_group = QGroupBox("Curve Statistics")
        stats_layout = QGridLayout()
        
        self.stats_labels = {}
        stat_names = ['Points:', 'Max Slip:', 'Peak Value:', 'Peak at:', 'Min Value:', 'Mean Value:']
        for i, name in enumerate(stat_names):
            stats_layout.addWidget(QLabel(name), i // 2, (i % 2) * 2)
            self.stats_labels[name] = QLabel("0")
            self.stats_labels[name].setStyleSheet("font-weight: bold; color: #4CAF50;")
            stats_layout.addWidget(self.stats_labels[name], i // 2, (i % 2) * 2 + 1)
        
        stats_group.setLayout(stats_layout)
        left_layout.addWidget(stats_group)
        
        data_group = QGroupBox("Curve Data")
        data_layout = QVBoxLayout()
        
        self.data_display = QTextEdit()
        self.data_display.setFont(QFont("Courier New", 9))
        self.data_display.setReadOnly(True)
        self.data_display.setLineWrapMode(QTextEdit.NoWrap)
        self.data_display.setMinimumHeight(250)
        data_layout.addWidget(self.data_display)
        
        copy_data_btn = QPushButton("📋 Copy Data to Clipboard")
        copy_data_btn.clicked.connect(self.copy_data_to_clipboard)
        data_layout.addWidget(copy_data_btn)
        
        data_group.setLayout(data_layout)
        left_layout.addWidget(data_group, 1)
        
        params_group = QGroupBox("Curve Parameters")
        params_layout = QVBoxLayout()
        
        self.param_list = QListWidget()
        self.param_list.setMaximumHeight(120)
        self.param_list.itemDoubleClicked.connect(self.edit_parameter)
        params_layout.addWidget(self.param_list)
        
        params_group.setLayout(params_layout)
        left_layout.addWidget(params_group)
        
        right_panel = QWidget()
        right_panel.setMaximumWidth(450)
        right_layout = QVBoxLayout(right_panel)
        
        file_group = QGroupBox("File Operations")
        file_layout = QVBoxLayout()
        
        self.save_btn = QPushButton("💾 Save Changes")
        self.save_btn.clicked.connect(self.save_changes)
        self.save_btn.setStyleSheet("background-color: #4CAF50; color: white;")
        
        self.save_as_btn = QPushButton("📁 Save As...")
        self.save_as_btn.clicked.connect(self.save_as)
        
        self.revert_all_btn = QPushButton("↺ Revert All")
        self.revert_all_btn.clicked.connect(self.revert_all)
        
        file_layout.addWidget(self.save_btn)
        file_layout.addWidget(self.save_as_btn)
        file_layout.addWidget(self.revert_all_btn)
        file_group.setLayout(file_layout)
        right_layout.addWidget(file_group)
        
        compound_group = QGroupBox("Compound Editor")
        compound_layout = QVBoxLayout()
        
        self.compound_edit_widget = CompoundEditWidget(self, right_panel)
        self.compound_edit_widget.update_compounds(self.compounds)
        compound_layout.addWidget(self.compound_edit_widget)
        
        compound_group.setLayout(compound_layout)
        right_layout.addWidget(compound_group, 1)
        
        self.status_bar = QStatusBar()
        self.window.setStatusBar(self.status_bar)
        
        main_layout.addWidget(left_panel, 3)
        main_layout.addWidget(right_panel, 1)
        
        self.load_curve(0)
        
        self.window.show()
    
    def apply_dark_theme(self):
        self.window.setStyleSheet("""
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
            QLineEdit, QSpinBox, QDoubleSpinBox, QListWidget, QTextEdit {
                background-color: #3c3c3c;
                color: #ffffff;
                border: 1px solid #555;
                border-radius: 3px;
                padding: 4px;
                selection-background-color: #4CAF50;
            }
            QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus {
                border: 1px solid #4CAF50;
            }
            QListWidget::item:selected {
                background-color: #4CAF50;
            }
            QTextEdit {
                background-color: #1e1e1e;
                color: #d4d4d4;
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
            QStatusBar {
                color: #ffffff;
                background-color: #3c3c3c;
                border-top: 1px solid #555;
            }
        """)
    
    def update_compound_parameter(self, compound_index, axle, key, new_value):
        if compound_index >= len(self.compounds):
            return
            
        if compound_index not in self.modified_compounds:
            self.modified_compounds[compound_index] = {
                'axles': {}
            }
        
        if axle not in self.modified_compounds[compound_index]['axles']:
            self.modified_compounds[compound_index]['axles'][axle] = {}
        
        self.modified_compounds[compound_index]['axles'][axle][key] = new_value
        self.status_bar.showMessage(f"Compound parameter updated - Unsaved changes", 2000)
    
    def update_point_value(self, index, value):
        if self.show_all_curves:
            return
        
        curve = self.slip_curves[self.current_curve_index]
        if self.current_curve_index not in self.modified_curves:
            self.modified_curves[self.current_curve_index] = {
                'values': curve['values'].copy(),
                'step': curve['step']
            }
        
        self.modified_curves[self.current_curve_index]['values'][index] = value
        
        self.load_curve(self.current_curve_index)
        
        if self.point_edit_widget:
            self.point_edit_widget.current_point_index = index
            self.point_edit_widget.update_display()
            self.highlight_point(index)
        
        self.status_bar.showMessage(f"Point {index+1} updated", 1000)
    
    def highlight_point(self, index):
        if self.show_all_curves:
            return
        
        curve = self.slip_curves[self.current_curve_index]
        if self.current_curve_index in self.modified_curves:
            values = self.modified_curves[self.current_curve_index]['values']
            step = self.modified_curves[self.current_curve_index]['step']
        else:
            values = curve['values']
            step = curve['step']
        
        x = index * step
        y = values[index]
        
        self.point_highlight.setData([x], [y])
    
    def update_data_display(self):
        curve = self.slip_curves[self.current_curve_index]
        
        if self.current_curve_index in self.modified_curves:
            values = self.modified_curves[self.current_curve_index]['values']
        else:
            values = curve['values']
        
        data_lines = []
        for i in range(0, len(values), 10):
            line_values = values[i:i+10]
            formatted_line = ' '.join(f"{v:.6f}" for v in line_values)
            data_lines.append(formatted_line)
        
        data_text = '\n'.join(data_lines)
        self.data_display.setText(data_text)
    
    def copy_data_to_clipboard(self):
        clipboard = QApplication.clipboard()
        clipboard.setText(self.data_display.toPlainText())
        self.status_bar.showMessage("Data copied to clipboard", 2000)
    
    def load_comparison_curve(self):
        dialog = CompareFileDialog(
            self.window, 
            self.last_comparison_file,
            self.file_dir
        )
        
        if dialog.exec_() == QDialog.Accepted:
            curve = dialog.get_selected_curve()
            selected_file = dialog.get_selected_file()
            
            if curve and selected_file:
                self.last_comparison_file = selected_file
                self.comparison_curve = curve
                self.show_comparison_curve()
                self.status_bar.showMessage(f"Loaded comparison curve: {curve['name']} from {Path(selected_file).name}", 3000)
    
    def show_comparison_curve(self):
        if self.comparison_curve and not self.show_all_curves:
            self.comparison_plot.setData(
                self.comparison_curve['x_values'],
                self.comparison_curve['values']
            )
            self.comparison_plot.show()
            
            if hasattr(self, 'legend') and self.legend is not None:
                try:
                    self.legend.removeItem(self.comparison_plot)
                except:
                    pass
                self.legend.addItem(self.comparison_plot, f"Comparison: {self.comparison_curve['name']}")
            
            self.hide_compare_btn.setEnabled(True)
            
            self.plot_widget.autoRange()
    
    def hide_comparison_curve(self):
        if self.comparison_plot:
            self.comparison_plot.hide()
            self.hide_compare_btn.setEnabled(False)
            
            if hasattr(self, 'legend') and self.legend is not None:
                try:
                    self.legend.removeItem(self.comparison_plot)
                except:
                    pass
            
            self.status_bar.showMessage("Comparison curve hidden", 2000)
    
    def show_preview_dialog(self, operation_type):
        if self.show_all_curves:
            QMessageBox.warning(self.window, "Editing Disabled", 
                               "Editing is disabled when showing all curves. Please uncheck 'Show All Curves' to edit.")
            return
        
        if operation_type != "smooth":
            return
        
        curve = self.slip_curves[self.current_curve_index]
        if self.current_curve_index in self.modified_curves:
            current_values = self.modified_curves[self.current_curve_index]['values']
        else:
            current_values = curve['values'].copy()
        
        dialog = PreviewDialog(
            f"Smooth Curve - Preview",
            "smooth",
            current_values,
            self.plot_widget,
            self.window
        )
        
        if dialog.exec_() == QDialog.Accepted:
            new_values = dialog.get_values()
            
            if self.current_curve_index not in self.modified_curves:
                self.modified_curves[self.current_curve_index] = {
                    'values': curve['values'].copy(),
                    'step': curve['step']
                }
            
            self.modified_curves[self.current_curve_index]['values'] = new_values
            self.load_curve(self.current_curve_index)
            self.status_bar.showMessage(f"Smoothing applied", 2000)
        
        self.clear_preview()
    
    def update_preview_curve(self, preview_values):
        if self.show_all_curves:
            return
        
        curve = self.slip_curves[self.current_curve_index]
        step = curve['step']
        if self.current_curve_index in self.modified_curves:
            step = self.modified_curves[self.current_curve_index]['step']
        
        x_values = [i * step for i in range(len(preview_values))]
        
        self.preview_curve.setData(x_values, preview_values)
        self.preview_curve.show()
        
        self.curve_plot.setPen(pg.mkPen('b', width=2, style=Qt.DashLine))
        
        self.preview_values = preview_values
    
    def clear_preview(self):
        self.preview_curve.hide()
        self.curve_plot.setPen(pg.mkPen('b', width=2))
        self.preview_values = None
    
    def load_curve(self, index):
        self.current_curve_index = index
        curve = self.slip_curves[index]
        
        if index in self.modified_curves:
            values = self.modified_curves[index]['values']
            step = self.modified_curves[index]['step']
        else:
            values = curve['values']
            step = curve['step']
        
        x_values = [i * step for i in range(len(values))]
        
        if not self.show_all_curves:
            self.curve_plot.setData(x_values, values)
            
            if index in self.modified_curves:
                orig_x = [i * curve['step'] for i in range(len(curve['values']))]
                self.original_curve_plot.setData(orig_x, curve['values'])
                self.original_curve_plot.show()
            else:
                self.original_curve_plot.hide()
            
            for plot in self.all_curves_plots:
                plot.hide()
            
            self.preview_curve.hide()
            
            if self.comparison_curve:
                self.show_comparison_curve()
            else:
                self.comparison_plot.hide()
            
            peak_idx = np.argmax(values)
            peak_x = x_values[peak_idx]
            peak_y = values[peak_idx]
            self.peak_marker.setData([peak_x], [peak_y])
            
            if self.point_edit_widget:
                self.point_edit_widget.set_values(values)
            
            self.highlight_point(0)
        else:
            self.update_all_curves_display()
        
        self.plot_widget.autoRange()
        
        self.step_spin.blockSignals(True)
        self.step_spin.setValue(step)
        self.step_spin.blockSignals(False)
        
        self.update_statistics(values, x_values, step)
        
        self.update_parameters_list()
        
        self.update_data_display()
        
        if index in self.modified_curves:
            self.status_bar.showMessage(f"Curve modified (unsaved changes)", 3000)
        else:
            self.status_bar.showMessage(f"Original curve", 3000)
    
    def update_all_curves_display(self):
        for plot in self.all_curves_plots:
            self.plot_widget.removeItem(plot)
        self.all_curves_plots.clear()
        
        self.curve_plot.hide()
        self.original_curve_plot.hide()
        self.preview_curve.hide()
        self.comparison_plot.hide()
        self.peak_marker.hide()
        self.point_highlight.hide()
        
        if hasattr(self, 'legend') and self.legend is not None:
            self.legend.clear()
        
        colors = [
            (255, 0, 0),
            (0, 255, 0),
            (0, 0, 255),
            (255, 255, 0),
            (255, 0, 255),
            (0, 255, 255),
            (255, 128, 0),
            (128, 0, 255),
            (255, 128, 128),
            (128, 255, 128),
        ]
        
        for i, curve in enumerate(self.slip_curves):
            if i in self.modified_curves:
                values = self.modified_curves[i]['values']
                step = self.modified_curves[i]['step']
            else:
                values = curve['values']
                step = curve['step']
            
            x_values = [j * step for j in range(len(values))]
            
            color = colors[i % len(colors)]
            
            if i == self.current_curve_index:
                pen = pg.mkPen(color=color, width=3, style=Qt.SolidLine)
            else:
                pen = pg.mkPen(color=color, width=1.5, style=Qt.DashLine)
            
            plot = self.plot_widget.plot(
                x_values, values,
                pen=pen,
                name=curve['name']
            )
            self.all_curves_plots.append(plot)
            
            if hasattr(self, 'legend') and self.legend is not None:
                self.legend.addItem(plot, curve['name'])
    
    def toggle_show_all_curves(self, state):
        self.show_all_curves = (state == Qt.Checked)
        
        if self.show_all_curves:
            self.update_all_curves_display()
            self.step_spin.setEnabled(False)
            self.smooth_btn.setEnabled(False)
            self.load_compare_btn.setEnabled(False)
            self.hide_compare_btn.setEnabled(False)
            if self.point_edit_widget:
                self.point_edit_widget.setEnabled(False)
            self.status_bar.showMessage("Showing all curves - editing disabled", 3000)
        else:
            for plot in self.all_curves_plots:
                self.plot_widget.removeItem(plot)
            self.all_curves_plots.clear()
            
            self.curve_plot.show()
            self.peak_marker.show()
            self.point_highlight.show()
            
            self.step_spin.setEnabled(True)
            self.smooth_btn.setEnabled(True)
            self.load_compare_btn.setEnabled(True)
            if self.point_edit_widget:
                self.point_edit_widget.setEnabled(True)
            
            if self.comparison_curve:
                self.show_comparison_curve()
            else:
                self.comparison_plot.hide()
                self.hide_compare_btn.setEnabled(False)
            
            self.load_curve(self.current_curve_index)
    
    def update_statistics(self, values, x_values, step):
        peak_idx = np.argmax(values)
        
        self.stats_labels['Points:'].setText(str(len(values)))
        self.stats_labels['Max Slip:'].setText(f"{x_values[-1]:.3f}")
        self.stats_labels['Peak Value:'].setText(f"{values[peak_idx]:.3f}")
        self.stats_labels['Peak at:'].setText(f"{x_values[peak_idx]:.3f}")
        self.stats_labels['Min Value:'].setText(f"{min(values):.3f}")
        self.stats_labels['Mean Value:'].setText(f"{np.mean(values):.3f}")
    
    def update_parameters_list(self):
        self.param_list.clear()
        
        curve = self.slip_curves[self.current_curve_index]
        
        if self.current_curve_index in self.modified_curves:
            mod = self.modified_curves[self.current_curve_index]
            items = [
                f"Name = {curve['name']}",
                f"Step = {mod['step']:.6f}",
                f"DropoffFunction = {curve['dropoff_function']}",
                f"Points = {len(mod['values'])}"
            ]
        else:
            items = [
                f"Name = {curve['name']}",
                f"Step = {curve['step']:.6f}",
                f"DropoffFunction = {curve['dropoff_function']}",
                f"Points = {len(curve['values'])}"
            ]
        
        for item in items:
            self.param_list.addItem(item)
    
    def edit_parameter(self, item):
        if self.show_all_curves:
            QMessageBox.warning(self.window, "Editing Disabled", 
                               "Editing is disabled when showing all curves. Please uncheck 'Show All Curves' to edit.")
            return
            
        text = item.text()
        if '=' not in text:
            return
        
        key, value = text.split('=', 1)
        key = key.strip()
        value = value.strip()
        
        dialog = ParameterEditDialog(key, value, self.window)
        if dialog.exec_() == QDialog.Accepted:
            new_value = dialog.get_value()
            
            if new_value != value:
                if key == 'Step':
                    try:
                        new_step = float(new_value)
                        self.on_step_changed(new_step)
                    except ValueError:
                        QMessageBox.warning(self.window, "Invalid Value", "Step must be a number")
                else:
                    if self.current_curve_index not in self.modified_curves:
                        curve = self.slip_curves[self.current_curve_index]
                        self.modified_curves[self.current_curve_index] = {
                            'values': curve['values'].copy(),
                            'step': curve['step']
                        }
                    
                    self.status_bar.showMessage("Parameter updated - Unsaved changes", 2000)
                    self.update_parameters_list()
    
    def on_curve_selected(self, index):
        self.current_curve_index = index
        if self.show_all_curves:
            self.update_all_curves_display()
        else:
            self.load_curve(index)
    
    def on_step_changed(self, value):
        if self.show_all_curves:
            return
            
        curve = self.slip_curves[self.current_curve_index]
        
        if self.current_curve_index not in self.modified_curves:
            self.modified_curves[self.current_curve_index] = {
                'values': curve['values'].copy(),
                'step': curve['step']
            }
        
        self.modified_curves[self.current_curve_index]['step'] = value
        self.load_curve(self.current_curve_index)
    
    def reset_curve(self):
        if self.show_all_curves:
            QMessageBox.warning(self.window, "Editing Disabled", 
                               "Editing is disabled when showing all curves. Please uncheck 'Show All Curves' to edit.")
            return
            
        if self.current_curve_index in self.modified_curves:
            del self.modified_curves[self.current_curve_index]
            self.load_curve(self.current_curve_index)
            self.status_bar.showMessage("Curve reset to original", 2000)
    
    def revert_all(self):
        if self.show_all_curves:
            QMessageBox.warning(self.window, "Editing Disabled", 
                               "Editing is disabled when showing all curves. Please uncheck 'Show All Curves' to edit.")
            return
            
        reply = QMessageBox.question(self.window, "Confirm",
                                    "Revert all changes? (This will revert both curves and compounds)",
                                    QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.modified_curves.clear()
            self.modified_compounds.clear()
            self.load_curve(self.current_curve_index)
            if self.compound_edit_widget:
                self.compound_edit_widget.update_parameters_list()
            self.status_bar.showMessage("All curves and compounds reverted to original", 3000)
    
    def save_changes(self):
        self.save_to_file(self.filename)
    
    def save_as(self):
        filename, _ = QFileDialog.getSaveFileName(
            self.window,
            "Save As",
            str(Path(self.filename).with_suffix('.tbc')),
            "Tire files (*.tbc);;Text files (*.txt);;All files (*.*)"
        )
        if filename:
            self.save_to_file(filename)
    
    def save_to_file(self, filename):
        try:
            new_content = self.original_content
            
            for idx in sorted(self.modified_curves.keys(), reverse=True):
                mod = self.modified_curves[idx]
                original_curve = self.slip_curves[idx]
                
                values = mod['values']
                step = mod['step']
                
                data_lines = []
                for i in range(0, len(values), 10):
                    line_values = values[i:i+10]
                    formatted_line = ' '.join(f"{v:.6f}" for v in line_values)
                    data_lines.append(formatted_line)
                new_data_str = '\n'.join(data_lines)
                
                new_block = f'[SLIPCURVE]\nName="{original_curve["name"]}"\nStep={step:.6f}            // Slip step\nDropoffFunction={original_curve["dropoff_function"]:.1f}      // see above            \nData:\n{new_data_str}\n'
                
                old_block = original_curve['full_match']
                
                pos = new_content.find(old_block)
                if pos >= 0:
                    end_pos = pos + len(old_block)
                    
                    next_section_pos = -1
                    
                    next_curve_pos = new_content.find('[SLIPCURVE]', end_pos)
                    next_compound_pos = new_content.find('[COMPOUND]', end_pos)
                    
                    if next_curve_pos >= 0 and next_compound_pos >= 0:
                        next_section_pos = min(next_curve_pos, next_compound_pos)
                    elif next_curve_pos >= 0:
                        next_section_pos = next_curve_pos
                    elif next_compound_pos >= 0:
                        next_section_pos = next_compound_pos
                    
                    if next_section_pos >= 0:
                        between_content = new_content[end_pos:next_section_pos]
                        
                        if not between_content.startswith('\n'):
                            between_content = '\n' + between_content
                        
                        new_content = new_content[:pos] + new_block + between_content + new_content[next_section_pos:]
                    else:
                        trailing_content = new_content[end_pos:]
                        
                        if trailing_content and not trailing_content.endswith('\n'):
                            trailing_content += '\n'
                        
                        new_content = new_content[:pos] + new_block + trailing_content
                else:
                    if not old_block.endswith('\n'):
                        old_block_with_newline = old_block + '\n'
                        new_block_with_newline = new_block + '\n' if not new_block.endswith('\n') else new_block
                        new_content = new_content.replace(old_block_with_newline, new_block_with_newline)
                    else:
                        new_content = new_content.replace(old_block, new_block)
            
            for idx in sorted(self.modified_compounds.keys(), reverse=True):
                mod = self.modified_compounds[idx]
                original_compound = self.compounds[idx]
                old_block = original_compound['full_match']
                
                new_compound_content = old_block
                
                for axle, params in mod['axles'].items():
                    for key, new_value in params.items():
                        axle_pattern = rf'({axle}:.*?)(?=\n\s*//\s*\n|\Z|REAR:|FRONT:)'
                        axle_match = re.search(axle_pattern, new_compound_content, re.DOTALL)
                        if axle_match:
                            axle_section = axle_match.group(1)
                            
                            lines = axle_section.split('\n')
                            new_lines = []
                            for line in lines:
                                clean_line = line.split('//')[0].strip()
                                if clean_line.startswith(key + '=') or clean_line.startswith(key + ' ='):
                                    comment_part = ''
                                    if '//' in line:
                                        comment_part = ' //' + line.split('//', 1)[1]
                                    new_lines.append(f'{key}={new_value}{comment_part}')
                                else:
                                    new_lines.append(line)
                            
                            new_axle_section = '\n'.join(new_lines)
                            new_compound_content = new_compound_content.replace(axle_section, new_axle_section)
                
                pos = new_content.find(old_block)
                if pos >= 0:
                    new_content = new_content[:pos] + new_compound_content + new_content[pos + len(old_block):]
            
            with open(filename, 'w') as f:
                f.write(new_content)
            
            self.original_content = new_content
            self.modified_curves.clear()
            self.modified_compounds.clear()
            
            self.slip_curves.clear()
            self.curve_matches.clear()
            self.compounds.clear()
            self.parse_tire_file(filename)
            
            if self.compound_edit_widget:
                self.compound_edit_widget.update_compounds(self.compounds)
            
            QMessageBox.information(self.window, "Success", f"Changes saved to {filename}")
            self.status_bar.showMessage("Changes saved", 3000)
            
            self.load_curve(self.current_curve_index)
            
        except Exception as e:
            QMessageBox.critical(self.window, "Error", f"Failed to save: {e}")
            import traceback
            traceback.print_exc()
    
    def run(self):
        return self.app.exec_()

def main():
    if len(sys.argv) < 2:
        print("Usage: python tire_editor.py <tire_file>")
        print("\nExample:")
        print("  python tire_editor.py tire.tbc")
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
