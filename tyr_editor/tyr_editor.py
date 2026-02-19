# pipenv install; pipenv run pip install PyQt5 pyqtgraph numpy scipy
# pipenv run python3 tire_slip_editor.py <path to .tyr file>
import sys
import re
import numpy as np
from pathlib import Path
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
import pyqtgraph as pg
from scipy.ndimage import gaussian_filter1d

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
        self.setMinimumWidth(400)
        
        layout = QVBoxLayout()
        
        # Key display
        key_layout = QHBoxLayout()
        key_layout.addWidget(QLabel("Parameter:"))
        key_label = QLabel(self.key)
        key_label.setStyleSheet("font-weight: bold; color: #4CAF50;")
        key_layout.addWidget(key_label)
        key_layout.addStretch()
        layout.addLayout(key_layout)
        
        # Current value
        current_layout = QHBoxLayout()
        current_layout.addWidget(QLabel("Current:"))
        current_label = QLabel(self.original_value)
        current_label.setStyleSheet("color: #888;")
        current_layout.addWidget(current_label)
        current_layout.addStretch()
        layout.addLayout(current_layout)
        
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
                layout.addWidget(self.value_editor)
            except ValueError:
                # String editor
                self.value_editor = QLineEdit(self.original_value)
                self.value_editor.textChanged.connect(self.on_text_changed)
                layout.addWidget(self.value_editor)
        
        # Buttons
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
        """Update tuple value at index"""
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
    
    def get_value(self):
        return self.new_value

class TireCurveEditor:
    def __init__(self, filename):
        self.filename = filename
        self.original_content = ""
        self.slip_curves = []
        self.curve_matches = []
        self.modified_curves = {}
        self.current_curve_index = 0
        
        self.parse_tire_file(filename)
        self.setup_ui()
    
    def parse_tire_file(self, filename):
        """Parse the tire file and return structured data"""
        with open(filename, 'r') as f:
            self.original_content = f.read()
        
        # Parse slip curves
        slip_curve_pattern = r'(\[SLIPCURVE\]\s*Name="([^"]+)"\s*Step=([0-9.e+-]+)[^\n]*\s*DropoffFunction=([0-9.e+-]+)[^\n]*\s*Data:\s*((?:\d+\.\d+\s*)+))'
        
        for match in re.finditer(slip_curve_pattern, self.original_content, re.MULTILINE | re.DOTALL):
            full_match = match.group(1)
            name = match.group(2)
            step = float(match.group(3))
            dropoff = float(match.group(4))
            
            # Parse the data values
            data_str = match.group(5).strip()
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
    
    def setup_ui(self):
        self.app = QApplication.instance() or QApplication(sys.argv)
        self.window = QMainWindow()
        self.window.setWindowTitle(f"Tire Curve Editor - {Path(self.filename).name}")
        self.window.setGeometry(100, 100, 1400, 900)
        
        # Apply dark theme
        self.apply_dark_theme()
        
        # Central widget
        central_widget = QWidget()
        self.window.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        
        # Left panel - Plot and controls
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        
        # Control bar
        control_bar = QWidget()
        control_layout = QHBoxLayout(control_bar)
        control_layout.setContentsMargins(0, 0, 0, 0)
        
        # Curve selection
        control_layout.addWidget(QLabel("Curve:"))
        self.curve_combo = QComboBox()
        self.curve_combo.addItems([c['name'] for c in self.slip_curves])
        self.curve_combo.currentIndexChanged.connect(self.on_curve_selected)
        control_layout.addWidget(self.curve_combo)
        
        control_layout.addWidget(QLabel("Step:"))
        self.step_spin = QDoubleSpinBox()
        self.step_spin.setRange(0.0001, 1.0)
        self.step_spin.setDecimals(6)
        self.step_spin.setSingleStep(0.001)
        self.step_spin.valueChanged.connect(self.on_step_changed)
        control_layout.addWidget(self.step_spin)
        
        control_layout.addStretch()
        
        # Operation buttons
        self.multiply_btn = QPushButton("✕ Multiply")
        self.multiply_btn.clicked.connect(self.multiply_curve)
        control_layout.addWidget(self.multiply_btn)
        
        self.offset_btn = QPushButton("➕ Add Offset")
        self.offset_btn.clicked.connect(self.add_offset)
        control_layout.addWidget(self.offset_btn)
        
        self.smooth_btn = QPushButton("〰 Smooth")
        self.smooth_btn.clicked.connect(self.smooth_curve)
        control_layout.addWidget(self.smooth_btn)
        
        self.reset_btn = QPushButton("↺ Reset")
        self.reset_btn.clicked.connect(self.reset_curve)
        control_layout.addWidget(self.reset_btn)
        
        left_layout.addWidget(control_bar)
        
        # Plot widget
        self.plot_widget = pg.PlotWidget(title="Slip Curve")
        self.plot_widget.setLabel('left', 'Normalized Force')
        self.plot_widget.setLabel('bottom', 'Slip')
        self.plot_widget.showGrid(x=True, y=True, alpha=0.3)
        self.plot_widget.setMouseEnabled(x=True, y=True)
        
        # Create curves
        self.curve_plot = self.plot_widget.plot(pen=pg.mkPen('b', width=2), name='Slip Curve')
        self.original_curve_plot = self.plot_widget.plot(pen=pg.mkPen('gray', width=1, style=Qt.DashLine), name='Original')
        self.peak_marker = pg.ScatterPlotItem(pen='r', brush='r', size=15, symbol='star', name='Peak')
        
        self.plot_widget.addItem(self.peak_marker)
        self.plot_widget.addLegend()
        
        left_layout.addWidget(self.plot_widget, 1)
        
        # Statistics panel
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
        
        # Right panel - Parameters
        right_panel = QWidget()
        right_panel.setMaximumWidth(400)
        right_layout = QVBoxLayout(right_panel)
        
        # File operations
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
        
        # Parameters list
        params_group = QGroupBox("Curve Parameters")
        params_layout = QVBoxLayout()
        
        # Parameter list
        self.param_list = QListWidget()
        self.param_list.itemDoubleClicked.connect(self.edit_parameter)
        params_layout.addWidget(self.param_list)
        
        # Add new parameter button
        self.add_param_btn = QPushButton("➕ Add Parameter")
        self.add_param_btn.clicked.connect(self.add_parameter)
        params_layout.addWidget(self.add_param_btn)
        
        params_group.setLayout(params_layout)
        right_layout.addWidget(params_group)
        
        # Status bar
        self.status_bar = QStatusBar()
        self.window.setStatusBar(self.status_bar)
        
        # Add panels to main layout
        main_layout.addWidget(left_panel, 2)
        main_layout.addWidget(right_panel, 1)
        
        # Load first curve
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
            QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox, QListWidget {
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
            QListWidget::item:selected {
                background-color: #4CAF50;
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
    
    def load_curve(self, index):
        """Load and display a curve"""
        self.current_curve_index = index
        curve = self.slip_curves[index]
        
        # Use modified values if available
        if index in self.modified_curves:
            values = self.modified_curves[index]['values']
            step = self.modified_curves[index]['step']
        else:
            values = curve['values']
            step = curve['step']
        
        x_values = [i * step for i in range(len(values))]
        
        # Update plots
        self.curve_plot.setData(x_values, values)
        
        # Show original for comparison if modified
        if index in self.modified_curves:
            orig_x = [i * curve['step'] for i in range(len(curve['values']))]
            self.original_curve_plot.setData(orig_x, curve['values'])
            self.original_curve_plot.show()
        else:
            self.original_curve_plot.hide()
        
        # Mark peak
        peak_idx = np.argmax(values)
        peak_x = x_values[peak_idx]
        peak_y = values[peak_idx]
        self.peak_marker.setData([peak_x], [peak_y])
        
        # Auto-range
        self.plot_widget.autoRange()
        
        # Update step spin
        self.step_spin.blockSignals(True)
        self.step_spin.setValue(step)
        self.step_spin.blockSignals(False)
        
        # Update statistics
        self.update_statistics(values, x_values, step)
        
        # Update parameters list
        self.update_parameters_list()
        
        # Update status
        if index in self.modified_curves:
            self.status_bar.showMessage(f"Curve modified (unsaved changes)", 3000)
        else:
            self.status_bar.showMessage(f"Original curve", 3000)
    
    def update_statistics(self, values, x_values, step):
        """Update statistics display"""
        peak_idx = np.argmax(values)
        
        self.stats_labels['Points:'].setText(str(len(values)))
        self.stats_labels['Max Slip:'].setText(f"{x_values[-1]:.3f}")
        self.stats_labels['Peak Value:'].setText(f"{values[peak_idx]:.3f}")
        self.stats_labels['Peak at:'].setText(f"{x_values[peak_idx]:.3f}")
        self.stats_labels['Min Value:'].setText(f"{min(values):.3f}")
        self.stats_labels['Mean Value:'].setText(f"{np.mean(values):.3f}")
    
    def update_parameters_list(self):
        """Update the parameters list"""
        self.param_list.clear()
        
        # Add curve parameters
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
        """Edit a parameter when double-clicked"""
        text = item.text()
        if '=' not in text:
            return
        
        key, value = text.split('=', 1)
        key = key.strip()
        value = value.strip()
        
        # Create edit dialog
        dialog = ParameterEditDialog(key, value, self.window)
        if dialog.exec_() == QDialog.Accepted:
            new_value = dialog.get_value()
            
            if new_value != value:
                # Apply the change
                if key == 'Step':
                    try:
                        new_step = float(new_value)
                        self.on_step_changed(new_step)
                    except ValueError:
                        QMessageBox.warning(self.window, "Invalid Value", "Step must be a number")
                else:
                    # Store in modified curves if needed
                    if self.current_curve_index not in self.modified_curves:
                        curve = self.slip_curves[self.current_curve_index]
                        self.modified_curves[self.current_curve_index] = {
                            'values': curve['values'].copy(),
                            'step': curve['step']
                        }
                    
                    self.status_bar.showMessage("Parameter updated - Unsaved changes", 2000)
                    self.update_parameters_list()
    
    def add_parameter(self):
        """Add a new parameter"""
        # This could be expanded to add new parameters
        QMessageBox.information(self.window, "Info", "Adding new parameters is not supported yet.")
    
    def on_curve_selected(self, index):
        """Handle curve selection change"""
        self.load_curve(index)
    
    def on_step_changed(self, value):
        """Handle step size change"""
        curve = self.slip_curves[self.current_curve_index]
        
        # Store modified curve
        if self.current_curve_index not in self.modified_curves:
            self.modified_curves[self.current_curve_index] = {
                'values': curve['values'].copy(),
                'step': curve['step']
            }
        
        self.modified_curves[self.current_curve_index]['step'] = value
        self.load_curve(self.current_curve_index)
    
    def multiply_curve(self):
        """Multiply curve values by a factor"""
        factor, ok = QInputDialog.getDouble(self.window, "Multiply", 
                                           "Enter multiplication factor:",
                                           value=1.0, min=0.0, max=10.0, decimals=2)
        if ok:
            curve = self.slip_curves[self.current_curve_index]
            
            # Store modified curve
            if self.current_curve_index not in self.modified_curves:
                self.modified_curves[self.current_curve_index] = {
                    'values': curve['values'].copy(),
                    'step': curve['step']
                }
            
            # Apply multiplication
            self.modified_curves[self.current_curve_index]['values'] = [
                v * factor for v in self.modified_curves[self.current_curve_index]['values']
            ]
            
            self.load_curve(self.current_curve_index)
    
    def add_offset(self):
        """Add offset to curve values"""
        offset, ok = QInputDialog.getDouble(self.window, "Add Offset",
                                           "Enter offset value:",
                                           value=0.0, decimals=3)
        if ok:
            curve = self.slip_curves[self.current_curve_index]
            
            # Store modified curve
            if self.current_curve_index not in self.modified_curves:
                self.modified_curves[self.current_curve_index] = {
                    'values': curve['values'].copy(),
                    'step': curve['step']
                }
            
            # Apply offset
            self.modified_curves[self.current_curve_index]['values'] = [
                v + offset for v in self.modified_curves[self.current_curve_index]['values']
            ]
            
            self.load_curve(self.current_curve_index)
    
    def smooth_curve(self):
        """Apply smoothing to the curve"""
        sigma, ok = QInputDialog.getDouble(self.window, "Smooth",
                                          "Enter smoothing sigma:",
                                          value=1.0, min=0.1, max=5.0, decimals=1)
        if ok:
            curve = self.slip_curves[self.current_curve_index]
            
            # Store modified curve
            if self.current_curve_index not in self.modified_curves:
                self.modified_curves[self.current_curve_index] = {
                    'values': curve['values'].copy(),
                    'step': curve['step']
                }
            
            # Apply Gaussian smoothing
            values = np.array(self.modified_curves[self.current_curve_index]['values'])
            smoothed = gaussian_filter1d(values, sigma=sigma)
            
            self.modified_curves[self.current_curve_index]['values'] = smoothed.tolist()
            self.load_curve(self.current_curve_index)
    
    def reset_curve(self):
        """Reset current curve to original"""
        if self.current_curve_index in self.modified_curves:
            del self.modified_curves[self.current_curve_index]
            self.load_curve(self.current_curve_index)
    
    def revert_all(self):
        """Revert all curves to original"""
        reply = QMessageBox.question(self.window, "Confirm",
                                    "Revert all changes?",
                                    QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.modified_curves.clear()
            self.load_curve(self.current_curve_index)
    
    def save_changes(self):
        """Save changes to the current file"""
        self.save_to_file(self.filename)
    
    def save_as(self):
        """Save to a new file"""
        filename, _ = QFileDialog.getSaveFileName(
            self.window,
            "Save As",
            str(Path(self.filename).with_suffix('.tbc')),
            "Tire files (*.tbc);;Text files (*.txt);;All files (*.*)"
        )
        if filename:
            self.save_to_file(filename)
    
    def save_to_file(self, filename):
        """Save the modified curves to a file"""
        try:
            new_content = self.original_content
            
            # Apply modifications in reverse order to maintain string positions
            for idx in sorted(self.modified_curves.keys(), reverse=True):
                mod = self.modified_curves[idx]
                original_curve = self.slip_curves[idx]
                
                # Format new data string
                values = mod['values']
                step = mod['step']
                
                # Format values with 6 decimal places, 10 per line
                data_lines = []
                for i in range(0, len(values), 10):
                    line_values = values[i:i+10]
                    data_lines.append(' '.join(f"{v:.6f}" for v in line_values))
                new_data_str = '\n'.join(data_lines)
                
                # Create new block
                new_block = f'[SLIPCURVE]\nName="{original_curve["name"]}"\nStep={step:.6f}            // Slip step\nDropoffFunction={original_curve["dropoff_function"]:.1f}      // see above            \nData:\n{new_data_str}'
                
                # Replace in content
                new_content = new_content.replace(original_curve['full_match'], new_block)
            
            # Write to file
            with open(filename, 'w') as f:
                f.write(new_content)
            
            # Update original content and clear modifications
            self.original_content = new_content
            self.modified_curves.clear()
            
            # Reparse the file to update matches
            self.slip_curves.clear()
            self.curve_matches.clear()
            self.parse_tire_file(filename)
            
            QMessageBox.information(self.window, "Success", f"Changes saved to {filename}")
            self.status_bar.showMessage("Changes saved", 3000)
            
            # Reload current curve
            self.load_curve(self.current_curve_index)
            
        except Exception as e:
            QMessageBox.critical(self.window, "Error", f"Failed to save: {e}")
    
    def run(self):
        """Start the application"""
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
