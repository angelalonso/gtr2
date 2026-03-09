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

class CompareCompoundDialog(QDialog):
    """Dialog for loading a comparison file for compound comparison"""
    def __init__(self, parent=None, last_file=None, start_dir=None):
        super().__init__(parent)
        self.selected_file = None
        self.selected_compound_index = 0
        self.selected_axle = "FRONT"
        self.comparison_compounds = []
        self.comparison_curves = []  # Store curves too
        self.last_file = last_file
        self.start_dir = start_dir
        self.setup_ui()
        
    def setup_ui(self):
        self.setWindowTitle("Load Comparison File for Compound")
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
        
        # Compound selection group
        compound_group = QGroupBox("Select Compound for Comparison")
        compound_layout = QVBoxLayout()
        
        compound_select_layout = QHBoxLayout()
        compound_select_layout.addWidget(QLabel("Compound:"))
        self.compound_combo = QComboBox()
        self.compound_combo.setEnabled(False)
        self.compound_combo.currentIndexChanged.connect(self.on_compound_selected)
        compound_select_layout.addWidget(self.compound_combo)
        
        compound_select_layout.addWidget(QLabel("Axle:"))
        self.axle_combo = QComboBox()
        self.axle_combo.addItems(["FRONT", "REAR"])
        self.axle_combo.setEnabled(False)
        self.axle_combo.currentTextChanged.connect(self.on_axle_selected)
        compound_select_layout.addWidget(self.axle_combo)
        
        compound_select_layout.addStretch()
        compound_layout.addLayout(compound_select_layout)
        
        self.compound_info_label = QLabel("")
        self.compound_info_label.setStyleSheet("color: #888; font-style: italic;")
        compound_layout.addWidget(self.compound_info_label)
        
        compound_group.setLayout(compound_layout)
        layout.addWidget(compound_group)
        
        button_layout = QHBoxLayout()
        
        self.show_btn = QPushButton("Compare Compounds")
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
    
    def load_file(self, filename):
        try:
            self.comparison_curves, self.comparison_compounds = self.parse_tire_file(filename)
            
            if self.comparison_compounds:
                self.file_path_edit.setText(filename)
                self.selected_file = filename
                
                # Update compound combo
                self.compound_combo.clear()
                self.compound_combo.addItems([c['name'] for c in self.comparison_compounds])
                self.compound_combo.setEnabled(True)
                self.axle_combo.setEnabled(True)
                
                info_text = f"Loaded {len(self.comparison_compounds)} compounds from {Path(filename).name}"
                self.compound_info_label.setText(info_text)
                self.compound_info_label.setStyleSheet("color: #4CAF50;")
                
                self.show_btn.setEnabled(True)
                
                if self.comparison_compounds:
                    self.on_compound_selected(0)
            else:
                QMessageBox.warning(self, "No Data", "No compounds found in the selected file.")
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load file: {e}")
    
    def parse_tire_file(self, filename):
        curves = []
        compounds = []
        
        with open(filename, 'r') as f:
            content = f.read()
        
        # Parse slip curves - improved pattern to handle various formats
        slip_curve_pattern = r'\[SLIPCURVE\]\s*Name="([^"]+)"\s*Step=([0-9.e+-]+)[^\n]*\s*DropoffFunction=([0-9.e+-]+)[^\n]*\s*Data:\s*((?:\d+\.\d+\s*)+)'
        
        for match in re.finditer(slip_curve_pattern, content, re.MULTILINE | re.DOTALL):
            name = match.group(1).strip()  # Remove any whitespace
            step = float(match.group(2))
            dropoff = float(match.group(3))
            
            data_str = match.group(4).strip()
            values = [float(x) for x in data_str.split()]
            
            curve = {
                'name': name,
                'step': step,
                'dropoff_function': dropoff,
                'values': values,
                'x_values': [i * step for i in range(len(values))]
            }
            curves.append(curve)
            print(f"Found curve: '{name}' with {len(values)} points")  # Debug print
        
        # Parse compounds
        parts = content.split('[COMPOUND]')
        
        for i in range(1, len(parts)):
            compound_content = '[COMPOUND]' + parts[i]
            
            end_pos = len(compound_content)
            
            full_pos = content.find(compound_content.strip())
            if full_pos >= 0:
                next_compound = content.find('[COMPOUND]', full_pos + 1)
                next_slipcurve = content.find('[SLIPCURVE]', full_pos + 1)
                
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
            
            compounds.append({
                'name': name,
                'wet_weather': wet_weather,
                'axles': axles
            })
        
        return curves, compounds
    
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
                # Remove quotes if present
                if value.startswith('"') and value.endswith('"'):
                    value = value[1:-1]
                params[key] = value
        
        return params
    
    def on_compound_selected(self, index):
        if index >= 0 and index < len(self.comparison_compounds):
            self.selected_compound_index = index
    
    def on_axle_selected(self, axle):
        self.selected_axle = axle
    
    def get_selected_compound(self):
        if self.comparison_compounds and self.selected_compound_index < len(self.comparison_compounds):
            return self.comparison_compounds[self.selected_compound_index]
        return None
    
    def get_selected_axle(self):
        return self.selected_axle
    
    def get_selected_file(self):
        return self.selected_file
    
    def get_curves(self):
        """Return all curves from the loaded file"""
        return self.comparison_curves

class CompoundParameterTableWidget(QTableWidget):
    """Custom table widget for displaying compound parameters in two columns"""
    
    parameter_edited = pyqtSignal(str, str, str)  # axle, key, new_value
    edit_curve_requested = pyqtSignal(str, str, str)  # curve_name, comparison_curve_name, current_axle
    
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
        
        # Set column resize modes - IMPORTANT for maintaining stretch
        header = self.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setStretchLastSection(False)
        
        self.verticalHeader().setVisible(False)
        self.setAlternatingRowColors(True)
        self.setEditTriggers(QAbstractItemView.DoubleClicked)
        
        # Create a default font for all cells
        self.default_font = QFont()
        
        # Style the table with two shades of grey for alternating rows
        self.setStyleSheet("""
            QTableWidget {
                background-color: #2b2b2b;
                alternate-background-color: #3a3a3a;
                gridline-color: #444;
            }
            QTableWidget::item {
                padding: 4px;
                color: #ffffff;
                border: none;
            }
            QTableWidget::item:selected {
                background-color: #4CAF50;
                color: #ffffff;
            }
            QTableWidget::item:selected:!active {
                background-color: #4CAF50;
            }
            QHeaderView::section {
                background-color: #1e1e1e;
                color: #4CAF50;
                padding: 6px;
                border: 1px solid #444;
                font-weight: bold;
            }
        """)
        
        self.itemDoubleClicked.connect(self.on_item_double_clicked)
    
    def set_comparison_compound(self, compound, axle):
        self.comparison_compound = compound
        self.comparison_axle = axle
        self.update_table()
        
        # Force the table to maintain its stretch after update
        QTimer.singleShot(10, self.force_stretch)
    
    def clear_comparison(self):
        self.comparison_compound = None
        self.update_table()
        
        # Force the table to maintain its stretch after update
        QTimer.singleShot(10, self.force_stretch)
    
    def force_stretch(self):
        """Force the table to maintain stretch after updates"""
        header = self.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.updateGeometry()
    
    def are_values_different(self, val1, val2):
        """Check if two values are different (handles numeric and string comparison)"""
        try:
            # Try numeric comparison
            return abs(float(val1) - float(val2)) > 1e-10
        except (ValueError, TypeError):
            # String comparison
            return val1 != val2
    
    def get_comparison_color(self, is_different):
        """Get the appropriate color for comparison values"""
        if is_different:
            return QColor("#FFD700")  # Gold for different
        else:
            return QColor("#FFA500")  # Orange for same
    
    def update_table(self):
        self.clearContents()
        self.setRowCount(0)
        
        if self.current_compound_index < 0:
            return
            
        # Get the compound data
        compound = self.parent().editor.compounds[self.current_compound_index]
        
        # Add name row (not editable)
        row = self.rowCount()
        self.insertRow(row)
        
        name_item = QTableWidgetItem("Name")
        name_item.setFlags(name_item.flags() & ~Qt.ItemIsEditable)
        name_item.setForeground(QBrush(QColor("#888")))
        name_item.setFont(self.default_font)
        self.setItem(row, 0, name_item)
        
        value_item = QTableWidgetItem(compound['name'])
        value_item.setFlags(value_item.flags() & ~Qt.ItemIsEditable)
        value_item.setForeground(QBrush(QColor("#4CAF50")))
        value_item.setFont(self.default_font)
        self.setItem(row, 1, value_item)
        
        # Add comparison value if available
        if self.comparison_compound:
            comp_value = self.comparison_compound['name']
            comp_item = QTableWidgetItem(comp_value)
            comp_item.setFlags(comp_item.flags() & ~Qt.ItemIsEditable)
            
            # Color code based on difference, use YELLOW for different values
            is_different = self.are_values_different(compound['name'], comp_value)
            if is_different:
                comp_item.setForeground(QBrush(QColor("#FFD700")))  # Yellow for different
            else:
                comp_item.setForeground(QBrush(QColor("#FFA500")))  # Orange for same
            comp_item.setFont(self.default_font)
            self.setItem(row, 2, comp_item)
        else:
            empty_item = QTableWidgetItem("")
            empty_item.setFlags(empty_item.flags() & ~Qt.ItemIsEditable)
            empty_item.setFont(self.default_font)
            self.setItem(row, 2, empty_item)
        
        # Empty cell for the button column
        button_cell = QTableWidgetItem("")
        button_cell.setFlags(button_cell.flags() & ~Qt.ItemIsEditable)
        button_cell.setFont(self.default_font)
        self.setItem(row, 3, button_cell)
        
        # Add wet weather if exists
        if compound.get('wet_weather') is not None:
            row = self.rowCount()
            self.insertRow(row)
            
            wet_item = QTableWidgetItem("WetWeather")
            wet_item.setFlags(wet_item.flags() & ~Qt.ItemIsEditable)
            wet_item.setForeground(QBrush(QColor("#888")))
            wet_item.setFont(self.default_font)
            self.setItem(row, 0, wet_item)
            
            value_item = QTableWidgetItem(str(compound['wet_weather']))
            value_item.setFlags(value_item.flags() & ~Qt.ItemIsEditable)
            value_item.setFont(self.default_font)
            self.setItem(row, 1, value_item)
            
            if self.comparison_compound and self.comparison_compound.get('wet_weather') is not None:
                comp_value = str(self.comparison_compound['wet_weather'])
                comp_item = QTableWidgetItem(comp_value)
                comp_item.setFlags(comp_item.flags() & ~Qt.ItemIsEditable)
                
                # Color code based on difference, use YELLOW for different values
                is_different = self.are_values_different(str(compound['wet_weather']), comp_value)
                if is_different:
                    comp_item.setForeground(QBrush(QColor("#FFD700")))  # Yellow for different
                else:
                    comp_item.setForeground(QBrush(QColor("#FFA500")))  # Orange for same
                comp_item.setFont(self.default_font)
                self.setItem(row, 2, comp_item)
            else:
                empty_item = QTableWidgetItem("")
                empty_item.setFlags(empty_item.flags() & ~Qt.ItemIsEditable)
                empty_item.setFont(self.default_font)
                self.setItem(row, 2, empty_item)
            
            button_cell = QTableWidgetItem("")
            button_cell.setFlags(button_cell.flags() & ~Qt.ItemIsEditable)
            button_cell.setFont(self.default_font)
            self.setItem(row, 3, button_cell)
        
        # Add axle data
        if self.current_axle in compound['axles']:
            axle_data = compound['axles'][self.current_axle]
            
            # Check if comparison axle exists and has different values
            has_comparison = (self.comparison_compound and 
                             self.comparison_axle in self.comparison_compound['axles'])
            
            comparison_axle_data = None
            has_differences = False
            
            if has_comparison:
                comparison_axle_data = self.comparison_compound['axles'][self.comparison_axle]
                # Check if any values are different
                for key, value in axle_data.items():
                    if key in comparison_axle_data:
                        if self.are_values_different(value, comparison_axle_data[key]):
                            has_differences = True
                            break
            
            # Add axle separator row
            row = self.rowCount()
            self.insertRow(row)
            
            # Parameter column shows "Axle"
            axle_param_item = QTableWidgetItem("Axle")
            axle_param_item.setFlags(axle_param_item.flags() & ~Qt.ItemIsEditable)
            axle_param_item.setForeground(QBrush(QColor("#4CAF50")))
            axle_param_item.setFont(self.default_font)
            self.setItem(row, 0, axle_param_item)
            
            # Value column shows the current axle
            axle_value_item = QTableWidgetItem(self.current_axle)
            axle_value_item.setFlags(axle_value_item.flags() & ~Qt.ItemIsEditable)
            axle_value_item.setForeground(QBrush(QColor("#4CAF50")))
            axle_value_item.setFont(self.default_font)
            self.setItem(row, 1, axle_value_item)
            
            # Comparison column shows comparison axle if available
            if has_comparison:
                comp_axle_item = QTableWidgetItem(self.comparison_axle)
                comp_axle_item.setFlags(comp_axle_item.flags() & ~Qt.ItemIsEditable)
                # Color based on whether there are any differences in parameters
                if has_differences:
                    comp_axle_item.setForeground(QBrush(QColor("#FFD700")))  # Yellow for different
                else:
                    comp_axle_item.setForeground(QBrush(QColor("#FFA500")))  # Orange for same
                comp_axle_item.setFont(self.default_font)
                self.setItem(row, 2, comp_axle_item)
            else:
                empty_item = QTableWidgetItem("")
                empty_item.setFlags(empty_item.flags() & ~Qt.ItemIsEditable)
                empty_item.setFont(self.default_font)
                self.setItem(row, 2, empty_item)
            
            # Empty cell for button column
            button_cell = QTableWidgetItem("")
            button_cell.setFlags(button_cell.flags() & ~Qt.ItemIsEditable)
            button_cell.setFont(self.default_font)
            self.setItem(row, 3, button_cell)
            
            # Add parameters
            for key, value in axle_data.items():
                row = self.rowCount()
                self.insertRow(row)
                
                key_item = QTableWidgetItem(key)
                key_item.setFlags(key_item.flags() & ~Qt.ItemIsEditable)
                key_item.setForeground(QBrush(QColor("#aaa")))
                key_item.setFont(self.default_font)
                self.setItem(row, 0, key_item)
                
                value_item = QTableWidgetItem(value)
                value_item.setFlags(value_item.flags() | Qt.ItemIsEditable)
                value_item.setForeground(QBrush(QColor("#ffffff")))
                value_item.setFont(self.default_font)
                self.setItem(row, 1, value_item)
                
                # Add comparison value if available
                comparison_curve_name = None
                if (self.comparison_compound and 
                    self.comparison_axle in self.comparison_compound['axles'] and
                    key in self.comparison_compound['axles'][self.comparison_axle]):
                    
                    comp_value = self.comparison_compound['axles'][self.comparison_axle][key]
                    comparison_curve_name = comp_value
                    comp_item = QTableWidgetItem(comp_value)
                    comp_item.setFlags(comp_item.flags() & ~Qt.ItemIsEditable)
                    
                    # Color code based on difference, use YELLOW for different values
                    is_different = self.are_values_different(value, comp_value)
                    if is_different:
                        comp_item.setForeground(QBrush(QColor("#FFD700")))  # Yellow for different
                    else:
                        comp_item.setForeground(QBrush(QColor("#FFA500")))  # Orange for same
                    comp_item.setFont(self.default_font)
                    
                    self.setItem(row, 2, comp_item)
                else:
                    empty_item = QTableWidgetItem("")
                    empty_item.setFlags(empty_item.flags() & ~Qt.ItemIsEditable)
                    empty_item.setFont(self.default_font)
                    self.setItem(row, 2, empty_item)
                
                # Add edit button for curve parameters
                if key in ["LatCurve", "BrakingCurve", "TractiveCurve"]:
                    btn = QPushButton("✎")
                    btn.setMaximumWidth(30)
                    btn.setToolTip(f"Edit {key} curve")
                    btn.setStyleSheet("""
                        QPushButton {
                            background-color: #4CAF50;
                            color: white;
                            border-radius: 3px;
                            padding: 2px;
                        }
                        QPushButton:hover {
                            background-color: #45a049;
                        }
                    """)
                    # Capture the current values for the lambda
                    current_value = value
                    current_comparison = comparison_curve_name
                    current_axle = self.current_axle
                    btn.clicked.connect(lambda checked, k=current_value, comp=current_comparison, ax=current_axle: 
                                      self.edit_curve_requested.emit(k, comp, ax))
                    self.setCellWidget(row, 3, btn)
                else:
                    button_cell = QTableWidgetItem("")
                    button_cell.setFlags(button_cell.flags() & ~Qt.ItemIsEditable)
                    button_cell.setFont(self.default_font)
                    self.setItem(row, 3, button_cell)
        
        # Force the table to update its geometry and maintain stretch
        self.resizeColumnsToContents()
        
        # Re-apply stretch modes after resize
        header = self.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        
        self.updateGeometry()
    
    def set_current_compound(self, index):
        self.current_compound_index = index
        self.update_table()
    
    def set_current_axle(self, axle):
        self.current_axle = axle
        self.update_table()
    
    def on_item_double_clicked(self, item):
        if item.column() == 1 and item.flags() & Qt.ItemIsEditable:
            key = self.item(item.row(), 0).text()
            if key and not key.startswith('---') and key != "Name" and key != "WetWeather" and key != "Axle":
                current_value = item.text()
                self.edit_parameter(key, current_value)
    
    def edit_parameter(self, key, current_value):
        dialog = ParameterEditDialog(key, current_value, self.window())
        if dialog.exec_() == QDialog.Accepted:
            new_value = dialog.get_value()
            if new_value != current_value:
                self.parameter_edited.emit(self.current_axle, key, new_value)
                self.update_table()

class CompoundEditWidget(QWidget):
    def __init__(self, editor, parent=None):
        super().__init__(parent)
        self.editor = editor
        self.current_compound_index = 0
        self.current_axle = "FRONT"
        self.comparison_compound = None
        self.comparison_axle = "FRONT"
        self.comparison_compounds_list = []
        self.comparison_curves_list = []  # Store curves from comparison file
        self.last_comparison_file = None
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Top toolbar
        toolbar_layout = QHBoxLayout()
        
        # Selection controls
        toolbar_layout.addWidget(QLabel("Compound:"))
        self.compound_combo = QComboBox()
        self.compound_combo.currentIndexChanged.connect(self.on_compound_selected)
        toolbar_layout.addWidget(self.compound_combo)
        
        toolbar_layout.addWidget(QLabel("Axle:"))
        self.axle_combo = QComboBox()
        self.axle_combo.addItems(["FRONT", "REAR"])
        self.axle_combo.currentTextChanged.connect(self.on_axle_selected)
        toolbar_layout.addWidget(self.axle_combo)
        
        toolbar_layout.addStretch()
        
        # Comparison button
        self.load_compare_btn = QPushButton("📊 Load Comparison")
        self.load_compare_btn.clicked.connect(self.load_comparison)
        self.load_compare_btn.setStyleSheet("background-color: #ff9800;")
        toolbar_layout.addWidget(self.load_compare_btn)
        
        self.hide_compare_btn = QPushButton("❌ Hide Comparison")
        self.hide_compare_btn.clicked.connect(self.clear_comparison)
        self.hide_compare_btn.setEnabled(False)
        self.hide_compare_btn.setStyleSheet("background-color: #f44336;")
        toolbar_layout.addWidget(self.hide_compare_btn)
        
        layout.addLayout(toolbar_layout)
        
        # Comparison controls (shown when comparison is active)
        self.comparison_info_widget = QWidget()
        comparison_info_layout = QHBoxLayout(self.comparison_info_widget)
        comparison_info_layout.setContentsMargins(0, 0, 0, 0)
        
        comparison_label = QLabel("Comparing with:")
        comparison_label.setStyleSheet("color: #FFA500; font-weight: bold;")
        comparison_info_layout.addWidget(comparison_label)
        
        self.comparison_file_label = QLabel("")
        self.comparison_file_label.setStyleSheet("color: #FFA500;")
        comparison_info_layout.addWidget(self.comparison_file_label)
        
        self.comparison_compound_combo = QComboBox()
        self.comparison_compound_combo.setEnabled(False)
        self.comparison_compound_combo.currentIndexChanged.connect(self.on_comparison_compound_selected)
        comparison_info_layout.addWidget(self.comparison_compound_combo)
        
        self.comparison_axle_combo = QComboBox()
        self.comparison_axle_combo.addItems(["FRONT", "REAR"])
        self.comparison_axle_combo.setEnabled(False)
        self.comparison_axle_combo.currentTextChanged.connect(self.on_comparison_axle_selected)
        comparison_info_layout.addWidget(self.comparison_axle_combo)
        
        comparison_info_layout.addStretch()
        
        self.comparison_info_widget.hide()
        layout.addWidget(self.comparison_info_widget)
        
        # Parameter table
        self.param_table = CompoundParameterTableWidget(self)
        self.param_table.setMinimumHeight(500)
        self.param_table.parameter_edited.connect(self.on_parameter_edited)
        self.param_table.edit_curve_requested.connect(self.on_edit_curve_requested)
        layout.addWidget(self.param_table)
        
        self.setLayout(layout)
    
    def update_compounds(self, compounds):
        self.compound_combo.blockSignals(True)
        self.compound_combo.clear()
        if compounds:
            self.compound_combo.addItems([c['name'] for c in compounds])
        self.compound_combo.blockSignals(False)
        
        if compounds:
            self.current_compound_index = 0
            self.param_table.set_current_compound(0)
        else:
            self.param_table.clearContents()
            self.param_table.setRowCount(1)
            self.param_table.setItem(0, 0, QTableWidgetItem("No compounds found in file"))
    
    def load_comparison(self):
        dialog = CompareCompoundDialog(
            self.window(), 
            self.last_comparison_file,
            self.editor.file_dir
        )
        
        if dialog.exec_() == QDialog.Accepted:
            compound = dialog.get_selected_compound()
            axle = dialog.get_selected_axle()
            selected_file = dialog.get_selected_file()
            
            if selected_file:
                self.last_comparison_file = selected_file
                self.editor.last_comparison_file = selected_file  # Store in editor for curve comparison
                self.comparison_curves_list = dialog.get_curves()  # Store curves
                
                if compound:
                    # Get all compounds from the comparison file for the dropdown
                    _, compounds = dialog.parse_tire_file(selected_file)
                    self.comparison_compounds_list = compounds
                    
                    self.set_comparison_data(compounds, compound, axle)
                    self.editor.status_bar.showMessage(f"Loaded comparison from {Path(selected_file).name}", 3000)
    
    def set_comparison_data(self, compounds, selected_compound, selected_axle):
        """Set the list of available comparison compounds and select the specified one"""
        self.comparison_compounds_list = compounds
        self.comparison_compound = selected_compound
        self.comparison_axle = selected_axle
        
        self.comparison_compound_combo.blockSignals(True)
        self.comparison_compound_combo.clear()
        
        if compounds:
            self.comparison_compound_combo.addItems([c['name'] for c in compounds])
            
            # Find and select the specified compound
            for i, c in enumerate(compounds):
                if c['name'] == selected_compound['name']:
                    self.comparison_compound_combo.setCurrentIndex(i)
                    break
            
            self.comparison_axle_combo.setCurrentText(selected_axle)
            
            self.comparison_compound_combo.setEnabled(True)
            self.comparison_axle_combo.setEnabled(True)
            
            # Show file info
            self.comparison_file_label.setText(f"{Path(self.last_comparison_file).name}")
            self.comparison_info_widget.show()
            self.hide_compare_btn.setEnabled(True)
            
            # Update the table with comparison data
            self.param_table.set_comparison_compound(self.comparison_compound, self.comparison_axle)
    
    def on_comparison_compound_selected(self, index):
        if index >= 0 and index < len(self.comparison_compounds_list):
            self.comparison_compound = self.comparison_compounds_list[index]
            self.param_table.set_comparison_compound(self.comparison_compound, self.comparison_axle)
            self.editor.status_bar.showMessage(
                f"Comparing with compound: {self.comparison_compound['name']} - {self.comparison_axle}", 
                2000
            )
    
    def on_comparison_axle_selected(self, axle):
        self.comparison_axle = axle
        if self.comparison_compound:
            self.param_table.set_comparison_compound(self.comparison_compound, axle)
            self.editor.status_bar.showMessage(
                f"Comparing with compound: {self.comparison_compound['name']} - {axle}", 
                2000
            )
    
    def clear_comparison(self):
        self.comparison_compound = None
        self.comparison_compounds_list = []
        self.comparison_curves_list = []
        self.comparison_compound_combo.clear()
        self.comparison_compound_combo.setEnabled(False)
        self.comparison_axle_combo.setEnabled(False)
        self.comparison_info_widget.hide()
        self.hide_compare_btn.setEnabled(False)
        self.param_table.clear_comparison()
        self.editor.status_bar.showMessage("Comparison cleared", 2000)
        self.editor.last_comparison_file = None  # Clear from editor too
    
    def on_compound_selected(self, index):
        if index >= 0:
            self.current_compound_index = index
            self.param_table.set_current_compound(index)
            self.editor.status_bar.showMessage(
                f"Editing compound: {self.editor.compounds[index]['name']} - {self.current_axle}", 
                2000
            )
    
    def on_axle_selected(self, axle):
        self.current_axle = axle
        self.param_table.set_current_axle(axle)
        if self.current_compound_index < len(self.editor.compounds):
            self.editor.status_bar.showMessage(
                f"Editing compound: {self.editor.compounds[self.current_compound_index]['name']} - {axle}", 
                2000
            )
    
    def on_parameter_edited(self, axle, key, new_value):
        self.editor.update_compound_parameter(self.current_compound_index, axle, key, new_value)
    
    def on_edit_curve_requested(self, curve_name, comparison_curve_name, axle):
        print(f"Edit curve requested: {curve_name}, comparison: {comparison_curve_name}, axle: {axle}")
        self.editor.open_curve_editor(curve_name, comparison_curve_name, axle)

class SlipCurveEditWidget(QWidget):
    """Widget for editing slip curves in a separate window"""
    def __init__(self, editor, curve_name, comparison_curve_name=None, axle=None, parent=None):
        super().__init__(parent)
        self.editor = editor
        self.curve_name = curve_name
        self.comparison_curve_name = comparison_curve_name
        self.axle = axle
        self.current_curve_index = self.find_curve_index()
        self.setup_ui()
        
    def find_curve_index(self):
        """Find the index of the curve we're editing"""
        print(f"Looking for curve: '{self.curve_name}'")
        for i, curve in enumerate(self.editor.slip_curves):
            print(f"  Curve {i}: '{curve['name']}'")
            if curve['name'] == self.curve_name:
                print(f"Found curve {self.curve_name} at index {i}")
                return i
        print(f"Warning: Curve {self.curve_name} not found, using index 0")
        return 0
    
    def setup_ui(self):
        layout = QVBoxLayout()
        
        # Title with both curve names
        title_text = f"Editing: {self.curve_name}"
        if self.comparison_curve_name:
            title_text += f"  |  Comparing with: {self.comparison_curve_name}"
        if self.axle:
            title_text += f"  |  Axle: {self.axle}"
        title_label = QLabel(title_text)
        title_label.setStyleSheet("font-size: 14pt; font-weight: bold; color: #4CAF50;")
        layout.addWidget(title_label)
        
        # Back button
        self.back_btn = QPushButton("← Back to Compound Editor")
        self.back_btn.clicked.connect(self.editor.close_curve_editor)
        self.back_btn.setStyleSheet("""
            QPushButton {
                background-color: #ff9800;
                color: white;
                font-weight: bold;
                padding: 8px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #f57c00;
            }
        """)
        layout.addWidget(self.back_btn)
        
        # Point edit widget
        self.point_edit_widget = PointEditWidget(self.editor)
        layout.addWidget(self.point_edit_widget)
        
        # Plot widget
        self.plot_widget = pg.PlotWidget(title=f"Slip Curve: {self.curve_name}")
        self.plot_widget.setLabel('left', 'Normalized Force')
        self.plot_widget.setLabel('bottom', 'Slip')
        self.plot_widget.showGrid(x=True, y=True, alpha=0.3)
        self.plot_widget.setMinimumHeight(400)
        
        # Add legend
        self.legend = self.plot_widget.addLegend()
        
        # Store references to plot items in the editor for access from other methods
        self.editor.curve_plot = self.plot_widget.plot(pen=pg.mkPen('b', width=2), name=f'Current: {self.curve_name}')
        self.editor.original_curve_plot = self.plot_widget.plot(pen=pg.mkPen('gray', width=1, style=Qt.DashLine), name='Original')
        self.editor.comparison_plot = self.plot_widget.plot(pen=pg.mkPen('orange', width=2, style=Qt.DashLine), name='Comparison')
        self.editor.preview_curve = self.plot_widget.plot(pen=pg.mkPen('y', width=2, style=Qt.DashLine), name='Preview')
        
        # Initially hide comparison and preview
        self.editor.comparison_plot.hide()
        self.editor.preview_curve.hide()
        
        # Point highlight and peak marker
        self.editor.point_highlight = pg.ScatterPlotItem(pen='r', brush=None, size=15, symbol='o', name='Selected Point')
        self.editor.peak_marker = pg.ScatterPlotItem(pen='r', brush='r', size=15, symbol='star', name='Peak')
        
        self.plot_widget.addItem(self.editor.peak_marker)
        self.plot_widget.addItem(self.editor.point_highlight)
        
        layout.addWidget(self.plot_widget, 2)
        
        # Parameters group
        params_group = QGroupBox("Curve Parameters")
        params_layout = QHBoxLayout()
        
        params_layout.addWidget(QLabel("Step:"))
        self.step_spin = QDoubleSpinBox()
        self.step_spin.setRange(0.0001, 1.0)
        self.step_spin.setDecimals(6)
        self.step_spin.setSingleStep(0.001)
        self.step_spin.valueChanged.connect(self.on_step_changed)
        params_layout.addWidget(self.step_spin)
        
        params_layout.addWidget(QLabel("Dropoff:"))
        self.dropoff_label = QLabel("0")
        self.dropoff_label.setStyleSheet("color: #4CAF50; font-weight: bold;")
        params_layout.addWidget(self.dropoff_label)
        
        params_layout.addWidget(QLabel("Points:"))
        self.points_label = QLabel("0")
        self.points_label.setStyleSheet("color: #4CAF50; font-weight: bold;")
        params_layout.addWidget(self.points_label)
        
        params_layout.addStretch()
        params_group.setLayout(params_layout)
        layout.addWidget(params_group)
        
        # Statistics group
        stats_group = QGroupBox("Statistics")
        stats_layout = QGridLayout()
        
        self.stats_labels = {}
        stat_names = ['Peak:', 'Peak at:', 'Min:', 'Mean:']
        for i, name in enumerate(stat_names):
            stats_layout.addWidget(QLabel(name), i // 2, (i % 2) * 2)
            self.stats_labels[name] = QLabel("0")
            self.stats_labels[name].setStyleSheet("font-weight: bold; color: #4CAF50;")
            stats_layout.addWidget(self.stats_labels[name], i // 2, (i % 2) * 2 + 1)
        
        stats_group.setLayout(stats_layout)
        layout.addWidget(stats_group)
        
        # Operations group
        ops_group = QGroupBox("Operations")
        ops_layout = QHBoxLayout()
        
        self.smooth_btn = QPushButton("〰 Smooth")
        self.smooth_btn.clicked.connect(lambda: self.editor.show_preview_dialog("smooth"))
        ops_layout.addWidget(self.smooth_btn)
        
        self.reset_btn = QPushButton("↺ Reset")
        self.reset_btn.clicked.connect(self.editor.reset_curve)
        ops_layout.addWidget(self.reset_btn)
        
        ops_layout.addStretch()
        ops_group.setLayout(ops_layout)
        layout.addWidget(ops_group)
        
        # Comparison info
        if self.comparison_curve_name:
            comparison_group = QGroupBox("Comparison")
            comparison_layout = QHBoxLayout()
            
            comparison_label = QLabel(f"Comparing {self.curve_name} with {self.comparison_curve_name}")
            comparison_label.setStyleSheet("color: #FFA500; font-weight: bold;")
            comparison_layout.addWidget(comparison_label)
            
            comparison_layout.addStretch()
            comparison_group.setLayout(comparison_layout)
            layout.addWidget(comparison_group)
        
        # Data display
        data_group = QGroupBox("Curve Data")
        data_layout = QVBoxLayout()
        
        self.data_display = QTextEdit()
        self.data_display.setFont(QFont("Courier New", 9))
        self.data_display.setReadOnly(True)
        self.data_display.setLineWrapMode(QTextEdit.NoWrap)
        self.data_display.setMinimumHeight(150)
        data_layout.addWidget(self.data_display)
        
        copy_data_btn = QPushButton("📋 Copy Data")
        copy_data_btn.clicked.connect(self.copy_data_to_clipboard)
        data_layout.addWidget(copy_data_btn)
        
        data_group.setLayout(data_layout)
        layout.addWidget(data_group, 1)
        
        self.setLayout(layout)
        
        # Load the curve data
        self.update_display()
        
        # Load comparison curve if available
        if self.comparison_curve_name and self.editor.last_comparison_file:
            print(f"Will load comparison curve: {self.comparison_curve_name}")
            QTimer.singleShot(100, self.load_comparison_curve)  # Small delay to ensure plot is ready
    
    def load_comparison_curve(self):
        """Load the comparison curve from the comparison file"""
        try:
            from pathlib import Path
            print(f"Loading comparison curve: '{self.comparison_curve_name}' from {self.editor.last_comparison_file}")
            
            # Parse the comparison file to get all curves
            with open(self.editor.last_comparison_file, 'r') as f:
                content = f.read()
            
            # Parse slip curves from the comparison file - improved pattern
            slip_curve_pattern = r'\[SLIPCURVE\]\s*Name="([^"]+)"\s*Step=([0-9.e+-]+)[^\n]*\s*DropoffFunction=([0-9.e+-]+)[^\n]*\s*Data:\s*((?:\d+\.\d+\s*)+)'
            
            found = False
            for match in re.finditer(slip_curve_pattern, content, re.MULTILINE | re.DOTALL):
                name = match.group(1).strip()
                print(f"  Found curve in file: '{name}'")
                if name == self.comparison_curve_name:  # Found matching curve name
                    step = float(match.group(2))
                    dropoff = float(match.group(3))
                    data_str = match.group(4).strip()
                    values = [float(x) for x in data_str.split()]
                    
                    print(f"Found comparison curve '{name}' with {len(values)} points")
                    
                    comparison_curve = {
                        'name': name,
                        'step': step,
                        'dropoff_function': dropoff,
                        'values': values,
                        'x_values': [i * step for i in range(len(values))]
                    }
                    
                    # Store in editor for later use
                    self.editor.comparison_curve = comparison_curve
                    
                    # Display the comparison curve
                    self.editor.comparison_plot.setData(
                        comparison_curve['x_values'],
                        comparison_curve['values']
                    )
                    self.editor.comparison_plot.show()
                    
                    # Update legend
                    if hasattr(self, 'legend') and self.legend is not None:
                        try:
                            self.legend.removeItem(self.editor.comparison_plot)
                        except:
                            pass
                        self.legend.addItem(self.editor.comparison_plot, f"Comparison: {self.comparison_curve_name}")
                    
                    # Auto-range the plot to show both curves
                    self.plot_widget.autoRange()
                    found = True
                    break
            
            if not found:
                print(f"Warning: Comparison curve '{self.comparison_curve_name}' not found in file")
                # Print all available curves for debugging
                print("Available curves in file:")
                for match in re.finditer(slip_curve_pattern, content, re.MULTILINE | re.DOTALL):
                    name = match.group(1).strip()
                    print(f"  - '{name}'")
        except Exception as e:
            print(f"Error loading comparison curve: {e}")
            import traceback
            traceback.print_exc()
    
    def update_display(self):
        """Update the display with the current curve data"""
        if self.current_curve_index < len(self.editor.slip_curves):
            curve = self.editor.slip_curves[self.current_curve_index]
            print(f"Updating display for curve: '{curve['name']}' at index {self.current_curve_index}")
            
            if self.current_curve_index in self.editor.modified_curves:
                mod = self.editor.modified_curves[self.current_curve_index]
                values = mod['values']
                step = mod['step']
            else:
                values = curve['values']
                step = curve['step']
            
            # Update plot
            x_values = [i * step for i in range(len(values))]
            self.editor.curve_plot.setData(x_values, values)
            
            if self.current_curve_index in self.editor.modified_curves:
                orig_x = [i * curve['step'] for i in range(len(curve['values']))]
                self.editor.original_curve_plot.setData(orig_x, curve['values'])
                self.editor.original_curve_plot.show()
            else:
                self.editor.original_curve_plot.hide()
            
            # Update peak marker
            peak_idx = np.argmax(values)
            peak_x = x_values[peak_idx]
            peak_y = values[peak_idx]
            self.editor.peak_marker.setData([peak_x], [peak_y])
            
            # Update point edit widget
            self.point_edit_widget.set_values(values)
            self.point_edit_widget.current_point_index = 0
            self.point_edit_widget.update_display()
            
            # Update parameters
            self.step_spin.blockSignals(True)
            self.step_spin.setValue(step)
            self.step_spin.blockSignals(False)
            
            self.dropoff_label.setText(str(curve['dropoff_function']))
            self.points_label.setText(str(len(values)))
            
            # Update statistics
            self.stats_labels['Peak:'].setText(f"{values[peak_idx]:.3f}")
            self.stats_labels['Peak at:'].setText(f"{x_values[peak_idx]:.3f}")
            self.stats_labels['Min:'].setText(f"{min(values):.3f}")
            self.stats_labels['Mean:'].setText(f"{np.mean(values):.3f}")
            
            # Update data display
            data_lines = []
            for i in range(0, len(values), 10):
                line_values = values[i:i+10]
                formatted_line = ' '.join(f"{v:.6f}" for v in line_values)
                data_lines.append(formatted_line)
            self.data_display.setText('\n'.join(data_lines))
            
            # Highlight the first point
            self.editor.highlight_point(0)
            
            self.plot_widget.autoRange()
    
    def on_step_changed(self, value):
        self.editor.on_step_changed(value)
        self.update_display()
    
    def copy_data_to_clipboard(self):
        clipboard = QApplication.clipboard()
        clipboard.setText(self.data_display.toPlainText())
        self.editor.status_bar.showMessage("Data copied to clipboard", 2000)

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
        self.current_compound_index = 0
        self.show_all_curves = False
        self.all_curves_plots = []
        self.comparison_curve = None
        self.comparison_compound = None
        self.comparison_axle = "FRONT"
        self.comparison_compounds_list = []
        self.comparison_plot = None
        self.preview_curve = None
        self.preview_values = None
        self.point_highlight = None
        self.peak_marker = None
        self.point_edit_widget = None
        self.compound_edit_widget = None
        self.curve_editor_window = None
        self.curve_editor_widget = None
        self.legend = None
        self.last_comparison_file = None
        self.curve_plot = None
        self.original_curve_plot = None
        
        self.parse_tire_file(filename)
        self.setup_ui()
    
    def parse_tire_file(self, filename):
        with open(filename, 'r') as f:
            self.original_content = f.read()
        
        content_without_comments = re.sub(r'//.*$', '', self.original_content, flags=re.MULTILINE)
        
        slip_curve_pattern = r'\[SLIPCURVE\]\s*Name="([^"]+)"\s*Step=([0-9.e+-]+)[^\n]*\s*DropoffFunction=([0-9.e+-]+)[^\n]*\s*Data:\s*((?:\d+\.\d+\s*)+)'
        
        print("Parsing slip curves from main file:")
        for match in re.finditer(slip_curve_pattern, self.original_content, re.MULTILINE | re.DOTALL):
            full_match = match.group(0)
            name = match.group(1).strip()
            step = float(match.group(2))
            dropoff = float(match.group(3))
            
            data_str = match.group(4).strip()
            values = [float(x) for x in data_str.split()]
            
            print(f"  Found curve: '{name}' with {len(values)} points")
            
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
                # Remove quotes if present
                if value.startswith('"') and value.endswith('"'):
                    value = value[1:-1]
                params[key] = value
        
        return params
    
    def setup_ui(self):
        self.app = QApplication.instance() or QApplication(sys.argv)
        self.window = QMainWindow()
        self.window.setWindowTitle(f"Tire Compound Editor - {Path(self.filename).name}")
        self.window.setGeometry(100, 100, 1000, 1000)
        
        self.apply_dark_theme()
        
        central_widget = QWidget()
        self.window.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # File operations
        file_group = QGroupBox("File Operations")
        file_layout = QHBoxLayout()
        
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
        file_layout.addStretch()
        file_group.setLayout(file_layout)
        main_layout.addWidget(file_group)
        
        # Compound editor (takes full space)
        self.compound_edit_widget = CompoundEditWidget(self)
        self.compound_edit_widget.update_compounds(self.compounds)
        main_layout.addWidget(self.compound_edit_widget, 1)
        
        self.status_bar = QStatusBar()
        self.window.setStatusBar(self.status_bar)
        
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
    
    def open_curve_editor(self, curve_name, comparison_curve_name=None, axle=None):
        """Open a new window for editing a slip curve"""
        print(f"Opening curve editor for '{curve_name}', comparison: '{comparison_curve_name}', axle: {axle}")
        
        self.curve_editor_window = QMainWindow(self.window)
        title = f"Slip Curve Editor - {curve_name}"
        if comparison_curve_name:
            title += f" (comparing with {comparison_curve_name})"
        self.curve_editor_window.setWindowTitle(title)
        self.curve_editor_window.setGeometry(150, 150, 1200, 800)
        self.curve_editor_window.setStyleSheet(self.window.styleSheet())
        
        self.curve_editor_widget = SlipCurveEditWidget(self, curve_name, comparison_curve_name, axle)
        self.curve_editor_window.setCentralWidget(self.curve_editor_widget)
        
        # Find the curve index
        found = False
        for i, curve in enumerate(self.slip_curves):
            print(f"  Checking curve: '{curve['name']}'")
            if curve['name'] == curve_name:
                self.current_curve_index = i
                print(f"Set current curve index to {i} for '{curve_name}'")
                found = True
                break
        
        if not found:
            print(f"Warning: Could not find curve '{curve_name}' in slip_curves")
            self.current_curve_index = 0
        
        self.curve_editor_window.show()
    
    def close_curve_editor(self):
        """Close the curve editor window"""
        if self.curve_editor_window:
            self.curve_editor_window.close()
            self.curve_editor_window = None
            self.curve_editor_widget = None
    
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
        
        if self.curve_editor_widget and self.curve_editor_widget.point_edit_widget:
            self.curve_editor_widget.point_edit_widget.current_point_index = index
            self.curve_editor_widget.point_edit_widget.update_display()
            self.highlight_point(index)
        
        self.status_bar.showMessage(f"Point {index+1} updated", 1000)
    
    def highlight_point(self, index):
        if self.show_all_curves or not self.curve_editor_widget:
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
        
        if hasattr(self, 'point_highlight') and self.point_highlight is not None:
            self.point_highlight.setData([x], [y])
    
    def show_preview_dialog(self, operation_type):
        if self.show_all_curves or not self.curve_editor_widget:
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
            self.curve_editor_widget.plot_widget,
            self.curve_editor_window
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
            
            if self.curve_editor_widget:
                self.curve_editor_widget.update_display()
            
            self.status_bar.showMessage(f"Smoothing applied", 2000)
        
        self.clear_preview()
    
    def update_preview_curve(self, preview_values):
        if self.show_all_curves or not self.curve_editor_widget:
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
        if self.preview_curve:
            self.preview_curve.hide()
        if self.curve_plot:
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
        
        if not self.show_all_curves and self.curve_editor_widget:
            # Update plot in curve editor window
            if self.curve_plot:
                self.curve_plot.setData(x_values, values)
            
            if index in self.modified_curves and self.original_curve_plot:
                orig_x = [i * curve['step'] for i in range(len(curve['values']))]
                self.original_curve_plot.setData(orig_x, curve['values'])
                self.original_curve_plot.show()
            elif self.original_curve_plot:
                self.original_curve_plot.hide()
            
            if self.preview_curve:
                self.preview_curve.hide()
            
            if self.comparison_curve and self.comparison_plot:
                self.comparison_plot.setData(
                    self.comparison_curve['x_values'],
                    self.comparison_curve['values']
                )
                self.comparison_plot.show()
            elif self.comparison_plot:
                self.comparison_plot.hide()
            
            if self.peak_marker:
                peak_idx = np.argmax(values)
                peak_x = x_values[peak_idx]
                peak_y = values[peak_idx]
                self.peak_marker.setData([peak_x], [peak_y])
            
            if self.curve_editor_widget and self.curve_editor_widget.point_edit_widget:
                self.curve_editor_widget.point_edit_widget.set_values(values)
                self.curve_editor_widget.point_edit_widget.current_point_index = 0
                self.curve_editor_widget.point_edit_widget.update_display()
            
            self.highlight_point(0)
            
            if self.curve_editor_widget:
                self.curve_editor_widget.plot_widget.autoRange()
        
        if self.curve_editor_widget:
            self.curve_editor_widget.update_display()
        
        if index in self.modified_curves:
            self.status_bar.showMessage(f"Curve modified (unsaved changes)", 3000)
        else:
            self.status_bar.showMessage(f"Original curve", 3000)
    
    def on_curve_selected(self, index):
        self.current_curve_index = index
        if not self.show_all_curves and self.curve_editor_widget:
            self.load_curve(index)
    
    def on_step_changed(self, value):
        if self.show_all_curves or not self.curve_editor_widget:
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
        if self.show_all_curves or not self.curve_editor_widget:
            return
            
        if self.current_curve_index in self.modified_curves:
            del self.modified_curves[self.current_curve_index]
            self.load_curve(self.current_curve_index)
            
            if self.curve_editor_widget:
                self.curve_editor_widget.update_display()
            
            self.status_bar.showMessage("Curve reset to original", 2000)
    
    def revert_all(self):
        reply = QMessageBox.question(self.window, "Confirm",
                                    "Revert all changes? (This will revert both curves and compounds)",
                                    QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.modified_curves.clear()
            self.modified_compounds.clear()
            if self.compound_edit_widget:
                self.compound_edit_widget.update_compounds(self.compounds)
                self.compound_edit_widget.set_current_compound(self.current_compound_index)
            
            if self.curve_editor_widget:
                self.load_curve(self.current_curve_index)
            
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
            
            if self.curve_editor_widget:
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
