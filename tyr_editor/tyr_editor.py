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
        elif event.key() == Qt.Key_Right:
            self.select_next_point()
        elif event.key() == Qt.Key_Up:
            self.increase_value()
        elif event.key() == Qt.Key_Down:
            self.decrease_value()
        else:
            super().keyPressEvent(event)
        event.accept()
    
    def focusInEvent(self, event):
        super().focusInEvent(event)
        self.editor.highlight_point(self.current_point_index)

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
        self.show_btn.setStyleSheet("background-color: #4CAF50; color: white;")
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
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
        print(f"Setting comparison compound: {compound['name'] if compound else None}, axle: {axle}")
        self.comparison_compound = compound
        self.comparison_axle = axle
        self.update_table()
    
    def clear_comparison(self):
        print("Clearing comparison")
        self.comparison_compound = None
        self.update_table()
    
    def values_differ(self, val1, val2):
        if val1 is None and val2 is None: return False
        if val1 is None or val2 is None: return True
        
        str1, str2 = str(val1).strip(), str(val2).strip()
        print(f"Comparing: '{str1}' vs '{str2}'")
        
        if '(' in str1 and ')' in str1:
            try:
                nums1 = [float(x.strip()) for x in str1.strip('()').split(',')]
                nums2 = [float(x.strip()) for x in str2.strip('()').split(',')]
                if len(nums1) != len(nums2): 
                    print("  Different lengths -> DIFFERENT")
                    return True
                for i, (a, b) in enumerate(zip(nums1, nums2)):
                    if abs(a - b) > 1e-10:
                        print(f"  Values differ at position {i}: {a} vs {b} -> DIFFERENT")
                        return True
                print("  All values same -> SAME")
                return False
            except:
                result = str1 != str2
                print(f"  String comparison -> {'DIFFERENT' if result else 'SAME'}")
                return result
        
        try:
            diff = abs(float(str1) - float(str2))
            result = diff > 1e-10
            print(f"  Numeric: {diff:.2e} -> {'DIFFERENT' if result else 'SAME'}")
            return result
        except:
            result = str1 != str2
            print(f"  String comparison -> {'DIFFERENT' if result else 'SAME'}")
            return result
    
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
            print(f"\nRow '{name}':")
            is_diff = self.values_differ(curr_val, comp_val)
            color = "#fcad37" if is_diff else "#fcfcfc"
            print(f"  Setting color to {color}")
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
        print(f"\n--- Updating table for compound {self.current_compound_index}, axle {self.current_axle} ---")
        self.clearContents()
        self.setRowCount(0)
        
        if self.current_compound_index < 0:
            return
        
        # Get the compound data
        compound = self.parent().editor.compounds[self.current_compound_index].copy()
        print(f"Current compound: {compound['name']}")
        
        # Apply any modified parameters to the compound data
        if self.current_compound_index in self.parent().editor.modified_compounds:
            mod = self.parent().editor.modified_compounds[self.current_compound_index]
            if self.current_axle in mod.get('axles', {}):
                for key, val in mod['axles'][self.current_axle].items():
                    if self.current_axle in compound['axles']:
                        compound['axles'][self.current_axle][key] = val
                        print(f"Applied modified value: {key} = {val}")
        
        comp_name = self.comparison_compound['name'] if self.comparison_compound else None
        self.add_row("Name", compound['name'], comp_name, special=True)
        
        if compound.get('wet_weather') is not None:
            comp_wet = self.comparison_compound.get('wet_weather') if self.comparison_compound else None
            self.add_row("WetWeather", str(compound['wet_weather']), 
                        str(comp_wet) if comp_wet is not None else None)
        
        if self.current_axle in compound['axles']:
            axle_data = compound['axles'][self.current_axle]
            print(f"Axle data: {axle_data}")
            
            comp_axle_data = None
            if self.comparison_compound and self.comparison_axle in self.comparison_compound['axles']:
                comp_axle_data = self.comparison_compound['axles'][self.comparison_axle]
                print(f"Comparison axle data: {comp_axle_data}")
            
            self.add_row("Axle", self.current_axle, self.comparison_axle if comp_axle_data else None, special=True)
            
            for key, val in axle_data.items():
                comp_val = comp_axle_data.get(key) if comp_axle_data else None
                row = self.add_row(key, val, comp_val, editable=True)
                
                if key in ["LatCurve", "BrakingCurve", "TractiveCurve"]:
                    btn = QPushButton("✎")
                    btn.setMaximumWidth(30)
                    btn.setStyleSheet("QPushButton { background-color: #4CAF50; color: white; border-radius: 3px; }")
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
        print("--- Table update complete ---\n")
    
    def set_current_compound(self, index):
        print(f"Setting current compound to index {index}")
        self.current_compound_index = index
        self.update_table()
    
    def set_current_axle(self, axle):
        print(f"Setting current axle to {axle}")
        self.current_axle = axle
        self.update_table()
    
    def on_item_double_clicked(self, item):
        if item.column() == 1 and item.flags() & Qt.ItemIsEditable:
            key = self.item(item.row(), 0).text()
            if key not in ["Name", "WetWeather", "Axle"]:
                print(f"Double clicked on {key}, current value: {item.text()}")
                self.edit_parameter(key, item.text())
    
    def edit_parameter(self, key, curr_val):
        print(f"Editing parameter {key}, current value: {curr_val}")
        dlg = ParameterEditDialog(key, curr_val, self.window())
        if dlg.exec_() == QDialog.Accepted:
            new_val = dlg.get_value()
            print(f"Dialog accepted, new value: {new_val}")
            if new_val != curr_val:
                print(f"Value changed, emitting signal")
                self.parameter_edited.emit(self.current_axle, key, new_val)
                # Force immediate table update
                self.update_table()
            else:
                print("Value unchanged")

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
        ok_btn.setStyleSheet("background-color: #4CAF50; color: white;")
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(ok_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)
        self.setLayout(layout)
    
    def on_text_changed(self, text):
        self.new_val = text
        print(f"Edit dialog: value changed to '{text}'")
    
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
        
        # Top toolbar
        toolbar = QHBoxLayout()
        toolbar.addWidget(QLabel("Compound:"))
        self.compound_combo = QComboBox()
        self.compound_combo.currentIndexChanged.connect(self.on_compound_selected)
        toolbar.addWidget(self.compound_combo)
        
        toolbar.addWidget(QLabel("Axle:"))
        self.axle_combo = QComboBox()
        self.axle_combo.addItems(["FRONT", "REAR"])
        self.axle_combo.currentTextChanged.connect(self.on_axle_selected)
        toolbar.addWidget(self.axle_combo)
        toolbar.addStretch()
        
        self.load_btn = QPushButton("📊 Load Comparison")
        self.load_btn.clicked.connect(self.load_comparison)
        self.load_btn.setStyleSheet("background-color: #ff9800; color: white; padding: 5px;")
        toolbar.addWidget(self.load_btn)
        
        self.hide_btn = QPushButton("❌ Hide Comparison")
        self.hide_btn.clicked.connect(self.clear_comparison)
        self.hide_btn.setEnabled(False)
        self.hide_btn.setStyleSheet("background-color: #f44336; color: white; padding: 5px;")
        toolbar.addWidget(self.hide_btn)
        
        layout.addLayout(toolbar)
        
        # Simple comparison info display (no selection controls)
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
        
        # Parameter table
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
                
                # Show comparison info
                self.file_label.setText(Path(file).name)
                self.compound_label.setText(comp['name'])
                self.axle_label.setText(f"({axle})")
                self.info_widget.show()
                self.hide_btn.setEnabled(True)
                
                # Update the table with comparison data
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
        print(f"\n=== Parameter edited: {key} = {val} (axle: {axle}) ===")
        self.editor.update_compound_parameter(self.current_compound_index, axle, key, val)
        print("Forcing table update...")
        self.table.update_table()
        self.editor.status_bar.showMessage(f"Updated {key} = {val}", 2000)
        print("=== Update complete ===\n")
    
    def on_edit_curve(self, curve, comp_curve, axle):
        self.editor.open_curve_editor(curve, comp_curve, axle)

class SlipCurveEditWidget(QWidget):
    def __init__(self, editor, curve, comp_curve=None, axle=None, parent=None):
        super().__init__(parent)
        self.editor = editor
        self.curve_name = curve
        self.comparison_curve_name = comp_curve
        self.axle = axle
        self.current_curve_index = self.find_curve_index()
        self.setup_ui()
        
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
        layout.addWidget(QLabel(title))
        
        self.back_btn = QPushButton("← Back")
        self.back_btn.clicked.connect(self.editor.close_curve_editor)
        self.back_btn.setStyleSheet("background-color: #ff9800; color: white;")
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
        params.addWidget(QLabel("Step:"))
        self.step_spin = QDoubleSpinBox()
        self.step_spin.setRange(0.0001, 1.0)
        self.step_spin.setDecimals(6)
        self.step_spin.valueChanged.connect(self.on_step_changed)
        params.addWidget(self.step_spin)
        params.addWidget(QLabel("Points:"))
        self.points_label = QLabel("0")
        params.addWidget(self.points_label)
        params.addStretch()
        layout.addLayout(params)
        
        ops = QHBoxLayout()
        self.smooth_btn = QPushButton("Smooth")
        self.smooth_btn.clicked.connect(lambda: self.editor.show_preview_dialog("smooth"))
        ops.addWidget(self.smooth_btn)
        self.reset_btn = QPushButton("Reset")
        self.reset_btn.clicked.connect(self.editor.reset_curve)
        ops.addWidget(self.reset_btn)
        ops.addStretch()
        layout.addLayout(ops)
        
        self.setLayout(layout)
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
    
    def update_display(self):
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
        
        self.point_edit.set_values(vals)
        self.step_spin.blockSignals(True)
        self.step_spin.setValue(step)
        self.step_spin.blockSignals(False)
        self.points_label.setText(str(len(vals)))
        
        # Only call highlight_point if the editor has a curve_editor_widget
        if hasattr(self.editor, 'curve_editor_widget') and self.editor.curve_editor_widget:
            self.editor.highlight_point(0)
        
        self.plot.autoRange()
    
    def on_step_changed(self, val):
        self.editor.on_step_changed(val)
        self.update_display()

class PreviewDialog(QDialog):
    def __init__(self, title, vals, plot, parent=None):
        super().__init__(parent)
        self.vals = vals
        self.plot = plot
        self.sigma = 1.0
        self.setWindowTitle(title)
        self.setModal(True)
        
        layout = QVBoxLayout()
        layout.addWidget(QLabel("Gaussian Smoothing"))
        layout.addWidget(QLabel("Sigma:"))
        self.sigma_spin = QDoubleSpinBox()
        self.sigma_spin.setRange(0.1, 10.0)
        self.sigma_spin.setValue(1.0)
        self.sigma_spin.valueChanged.connect(self.update_preview)
        layout.addWidget(self.sigma_spin)
        
        btns = QHBoxLayout()
        apply_btn = QPushButton("Apply")
        apply_btn.clicked.connect(self.accept)
        apply_btn.setStyleSheet("background-color: #4CAF50; color: white;")
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btns.addWidget(apply_btn)
        btns.addWidget(cancel_btn)
        layout.addLayout(btns)
        self.setLayout(layout)
        self.update_preview()
    
    def update_preview(self):
        self.sigma = self.sigma_spin.value()
        self.preview_values = gaussian_filter1d(self.vals, sigma=self.sigma, mode='nearest')
        self.parent().editor.update_preview_curve(self.preview_values)
    
    def get_values(self): return self.preview_values

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
        self.window.setWindowTitle(f"Editor - {Path(self.filename).name}")
        self.window.setGeometry(100, 100, 1000, 1000)
        self.window.setStyleSheet("QMainWindow { background-color: #2b2b2b; }")
        
        central = QWidget()
        self.window.setCentralWidget(central)
        layout = QVBoxLayout(central)
        
        toolbar = QHBoxLayout()
        self.save_btn = QPushButton("💾 Save")
        self.save_btn.clicked.connect(self.save_changes)
        self.save_btn.setStyleSheet("background-color: #4CAF50; color: white;")
        toolbar.addWidget(self.save_btn)
        
        self.save_as_btn = QPushButton("📁 Save As")
        self.save_as_btn.clicked.connect(self.save_as)
        self.save_as_btn.setStyleSheet("background-color: #3c3c3c; color: white;")
        toolbar.addWidget(self.save_as_btn)
        
        self.revert_btn = QPushButton("↺ Revert")
        self.revert_btn.clicked.connect(self.revert_all)
        self.revert_btn.setStyleSheet("background-color: #3c3c3c; color: white;")
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
        self.curve_editor_window.setWindowTitle(f"Curve: {curve}")
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
        print(f"update_compound_parameter: compound {idx}, axle {axle}, {key} = {val}")
        if idx >= len(self.compounds):
            return
        if idx not in self.modified_compounds:
            self.modified_compounds[idx] = {'axles': {}}
        if axle not in self.modified_compounds[idx]['axles']:
            self.modified_compounds[idx]['axles'][axle] = {}
        self.modified_compounds[idx]['axles'][axle][key] = val
        print(f"Stored in modified_compounds[{idx}]['axles'][{axle}][{key}] = {val}")
        self.status_bar.showMessage("Unsaved changes", 2000)
    
    def update_point_value(self, idx, val):
        curve = self.slip_curves[self.current_curve_index]
        if self.current_curve_index not in self.modified_curves:
            self.modified_curves[self.current_curve_index] = {
                'values': curve['values'].copy(), 'step': curve['step']
            }
        self.modified_curves[self.current_curve_index]['values'][idx] = val
        self.load_curve(self.current_curve_index)
        self.status_bar.showMessage(f"Point {idx+1} updated", 1000)
    
    def highlight_point(self, idx):
        # Check if we're in curve editor mode and have the necessary attributes
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
    
    def show_preview_dialog(self, op):
        if not self.curve_editor_widget or op != "smooth":
            return
        curve = self.slip_curves[self.current_curve_index]
        curr = self.modified_curves[self.current_curve_index]['values'] if self.current_curve_index in self.modified_curves else curve['values'].copy()
        dlg = PreviewDialog("Smooth", curr, self.curve_editor_widget.plot, self.curve_editor_window)
        if dlg.exec_() == QDialog.Accepted:
            if self.current_curve_index not in self.modified_curves:
                self.modified_curves[self.current_curve_index] = {'values': curve['values'].copy(), 'step': curve['step']}
            self.modified_curves[self.current_curve_index]['values'] = dlg.get_values()
            self.load_curve(self.current_curve_index)
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
    
    def load_curve(self, idx):
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
                self.curve_editor_widget.point_edit.set_values(vals)
            if hasattr(self.curve_editor_widget, 'step_spin'):
                self.curve_editor_widget.step_spin.setValue(step)
            
            self.highlight_point(0)
            
            if hasattr(self.curve_editor_widget, 'plot'):
                self.curve_editor_widget.plot.autoRange()
    
    def on_step_changed(self, val):
        if not self.curve_editor_widget:
            return
        curve = self.slip_curves[self.current_curve_index]
        if self.current_curve_index not in self.modified_curves:
            self.modified_curves[self.current_curve_index] = {'values': curve['values'].copy(), 'step': curve['step']}
        self.modified_curves[self.current_curve_index]['step'] = val
        self.load_curve(self.current_curve_index)
    
    def reset_curve(self):
        if self.current_curve_index in self.modified_curves:
            del self.modified_curves[self.current_curve_index]
            self.load_curve(self.current_curve_index)
    
    def revert_all(self):
        if QMessageBox.question(self.window, "Confirm", "Revert all changes?") == QMessageBox.Yes:
            self.modified_curves.clear()
            self.modified_compounds.clear()
            if self.compound_edit_widget:
                self.compound_edit_widget.update_compounds(self.compounds)
            if self.curve_editor_widget:
                self.load_curve(self.current_curve_index)
    
    def save_changes(self):
        self.save_to_file(self.filename)
    
    def save_as(self):
        fname, _ = QFileDialog.getSaveFileName(
            self.window, "Save As", str(Path(self.filename).with_suffix('.tbc'))
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
            QMessageBox.information(self.window, "Success", f"Saved to {fname}")
        except Exception as e:
            QMessageBox.critical(self.window, "Error", str(e))
            import traceback
            traceback.print_exc()
    
    def run(self):
        return self.app.exec_()

def main():
    if len(sys.argv) < 2:
        print("Usage: python editor.py <file>")
        return
    try:
        app = TireCurveEditor(sys.argv[1])
        sys.exit(app.run())
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
