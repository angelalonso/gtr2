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

class PointEditWidget(QWidget):
    """Widget for editing individual data points with arrow keys"""
    
    def __init__(self, editor, parent=None):
        super().__init__(parent)
        self.editor = editor  # Store reference to TireCurveEditor
        self.current_point_index = 0
        self.current_values = []
        self.setup_ui()
        
    def setup_ui(self):
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Current point indicator
        self.point_label = QLabel("Point: 0/0")
        self.point_label.setStyleSheet("color: #4CAF50; font-weight: bold;")
        layout.addWidget(self.point_label)
        
        # Value display/edit
        layout.addWidget(QLabel("Value:"))
        self.value_spin = QDoubleSpinBox()
        self.value_spin.setRange(-10.0, 10.0)
        self.value_spin.setDecimals(6)
        self.value_spin.setSingleStep(0.001)
        self.value_spin.valueChanged.connect(self.on_value_changed)
        
        # Install event filter to catch arrow keys before the spinbox does
        self.value_spin.installEventFilter(self)
        
        layout.addWidget(self.value_spin)
        
        # Instructions
        instr_label = QLabel("←/→: Select point, ↑/↓: Change value")
        instr_label.setStyleSheet("color: #888; font-style: italic;")
        layout.addWidget(instr_label)
        
        layout.addStretch()
        self.setLayout(layout)
        
        # Make sure the widget can receive focus
        self.setFocusPolicy(Qt.StrongFocus)
    
    def eventFilter(self, obj, event):
        """Filter events to catch arrow keys before they're processed by the spinbox"""
        if obj == self.value_spin and event.type() == QEvent.KeyPress:
            if event.key() == Qt.Key_Left:
                self.select_previous_point()
                return True  # Event handled, don't pass to spinbox
            elif event.key() == Qt.Key_Right:
                self.select_next_point()
                return True  # Event handled, don't pass to spinbox
            elif event.key() == Qt.Key_Up:
                self.increase_value()
                return True  # Event handled, don't pass to spinbox
            elif event.key() == Qt.Key_Down:
                self.decrease_value()
                return True  # Event handled, don't pass to spinbox
        return super().eventFilter(obj, event)
    
    def set_values(self, values):
        """Set the current values array"""
        self.current_values = values.copy() if values else []
        self.current_point_index = 0
        self.update_display()
    
    def update_display(self):
        """Update the display with current point"""
        if self.current_values:
            self.point_label.setText(f"Point: {self.current_point_index + 1}/{len(self.current_values)}")
            self.value_spin.blockSignals(True)
            self.value_spin.setValue(self.current_values[self.current_point_index])
            self.value_spin.blockSignals(False)
    
    def on_value_changed(self, value):
        """Handle value change from spinbox"""
        if self.current_values and self.current_point_index < len(self.current_values):
            self.current_values[self.current_point_index] = value
            self.editor.update_point_value(self.current_point_index, value)
    
    def select_previous_point(self):
        """Select the previous point"""
        if self.current_values and self.current_point_index > 0:
            self.current_point_index -= 1
            self.update_display()
            self.editor.highlight_point(self.current_point_index)
    
    def select_next_point(self):
        """Select the next point"""
        if self.current_values and self.current_point_index < len(self.current_values) - 1:
            self.current_point_index += 1
            self.update_display()
            self.editor.highlight_point(self.current_point_index)
    
    def increase_value(self):
        """Increase current point value"""
        if self.current_values:
            current_val = self.current_values[self.current_point_index]
            self.value_spin.setValue(current_val + 0.001)
    
    def decrease_value(self):
        """Decrease current point value"""
        if self.current_values:
            current_val = self.current_values[self.current_point_index]
            self.value_spin.setValue(current_val - 0.001)
    
    def keyPressEvent(self, event):
        """Handle key press events when the widget itself has focus"""
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
        """Handle focus in event"""
        super().focusInEvent(event)
        # Optionally highlight the current point when widget gets focus
        self.editor.highlight_point(self.current_point_index)

class PreviewDialog(QDialog):
    """Dialog for previewing operations with real-time updates"""
    
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
        
        # Preview label
        preview_label = QLabel("Preview - Changes will show in real-time")
        preview_label.setStyleSheet("color: #4CAF50; font-weight: bold;")
        layout.addWidget(preview_label)
        
        # Mini preview plot
        self.preview_plot = pg.PlotWidget(title="Preview")
        self.preview_plot.setLabel('left', 'Force')
        self.preview_plot.setLabel('bottom', 'Slip')
        self.preview_plot.showGrid(x=True, y=True, alpha=0.3)
        self.preview_plot.setFixedHeight(150)
        layout.addWidget(self.preview_plot)
        
        # Original curve (gray dashed)
        x_values = list(range(len(self.original_values)))
        self.preview_plot.plot(x_values, self.original_values, 
                               pen=pg.mkPen('gray', width=1, style=Qt.DashLine), 
                               name='Original')
        
        # Preview curve (yellow)
        self.preview_curve = self.preview_plot.plot(x_values, self.original_values,
                                                     pen=pg.mkPen('y', width=2),
                                                     name='Preview')
        
        # Operation-specific controls
        control_group = QGroupBox("Parameters")
        control_layout = QVBoxLayout()
        
        if self.operation_type == "multiply":
            control_layout.addWidget(QLabel("Multiplication Factor:"))
            self.param_input = QDoubleSpinBox()
            self.param_input.setRange(0.0, 10.0)
            self.param_input.setValue(1.0)
            self.param_input.setSingleStep(0.1)
            self.param_input.setDecimals(3)
            self.param_input.valueChanged.connect(self.update_preview)
            
        elif self.operation_type == "offset":
            control_layout.addWidget(QLabel("Offset Value:"))
            self.param_input = QDoubleSpinBox()
            self.param_input.setRange(-10.0, 10.0)
            self.param_input.setValue(0.0)
            self.param_input.setSingleStep(0.1)
            self.param_input.setDecimals(3)
            self.param_input.valueChanged.connect(self.update_preview)
            
        elif self.operation_type == "smooth":
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
        
        # Statistics comparison
        stats_group = QGroupBox("Statistics Comparison")
        stats_layout = QGridLayout()
        
        # Headers
        stats_layout.addWidget(QLabel("Metric"), 0, 0)
        stats_layout.addWidget(QLabel("Original"), 0, 1)
        stats_layout.addWidget(QLabel("Preview"), 0, 2)
        
        # Statistics rows
        metrics = ['Min:', 'Max:', 'Mean:', 'Peak:']
        self.stats_labels = {}
        for i, metric in enumerate(metrics):
            stats_layout.addWidget(QLabel(metric), i+1, 0)
            
            # Original value
            orig_label = QLabel("0.000")
            orig_label.setStyleSheet("color: #888;")
            stats_layout.addWidget(orig_label, i+1, 1)
            
            # Preview value
            preview_label = QLabel("0.000")
            preview_label.setStyleSheet("color: #4CAF50; font-weight: bold;")
            stats_layout.addWidget(preview_label, i+1, 2)
            
            self.stats_labels[metric] = {'original': orig_label, 'preview': preview_label}
        
        stats_group.setLayout(stats_layout)
        layout.addWidget(stats_group)
        
        # Buttons
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
        
        # Initial preview update
        self.update_preview()
    
    def update_preview(self):
        """Update preview based on current parameter"""
        param_value = self.param_input.value()
        
        if self.operation_type == "multiply":
            self.preview_values = [v * param_value for v in self.original_values]
        elif self.operation_type == "offset":
            self.preview_values = [v + param_value for v in self.original_values]
        elif self.operation_type == "smooth":
            values = np.array(self.original_values)
            self.preview_values = gaussian_filter1d(values, sigma=param_value).tolist()
        
        # Update preview plot
        x_values = list(range(len(self.preview_values)))
        self.preview_curve.setData(x_values, self.preview_values)
        
        # Update statistics
        self.update_statistics()
        
        # Update main plot preview if parent has the method
        if self.parent() and hasattr(self.parent(), 'update_preview_curve'):
            self.parent().update_preview_curve(self.preview_values)
    
    def update_statistics(self):
        """Update statistics comparison"""
        if self.preview_values:
            # Original stats
            orig_min = min(self.original_values)
            orig_max = max(self.original_values)
            orig_mean = np.mean(self.original_values)
            orig_peak_idx = np.argmax(self.original_values)
            orig_peak = self.original_values[orig_peak_idx]
            
            # Preview stats
            preview_min = min(self.preview_values)
            preview_max = max(self.preview_values)
            preview_mean = np.mean(self.preview_values)
            preview_peak_idx = np.argmax(self.preview_values)
            preview_peak = self.preview_values[preview_peak_idx]
            
            # Update labels
            self.stats_labels['Min:']['original'].setText(f"{orig_min:.3f}")
            self.stats_labels['Max:']['original'].setText(f"{orig_max:.3f}")
            self.stats_labels['Mean:']['original'].setText(f"{orig_mean:.3f}")
            self.stats_labels['Peak:']['original'].setText(f"{orig_peak:.3f}")
            
            self.stats_labels['Min:']['preview'].setText(f"{preview_min:.3f}")
            self.stats_labels['Max:']['preview'].setText(f"{preview_max:.3f}")
            self.stats_labels['Mean:']['preview'].setText(f"{preview_mean:.3f}")
            self.stats_labels['Peak:']['preview'].setText(f"{preview_peak:.3f}")
    
    def revert_to_original(self):
        """Revert to original values"""
        self.param_input.setValue(1.0 if self.operation_type == "multiply" else 
                                  0.0 if self.operation_type == "offset" else
                                  1.0)
        self.preview_values = self.original_values.copy()
        self.update_preview()
        if self.parent() and hasattr(self.parent(), 'clear_preview'):
            self.parent().clear_preview()
    
    def get_values(self):
        return self.preview_values
    
    def closeEvent(self, event):
        """Clean up when dialog closes"""
        if self.parent() and hasattr(self.parent(), 'clear_preview'):
            self.parent().clear_preview()
        event.accept()

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

class CompareFileDialog(QDialog):
    """Dialog for loading comparison curves from another file"""
    
    def __init__(self, parent=None, last_file=None):
        super().__init__(parent)
        self.selected_file = None
        self.selected_curve_index = 0
        self.comparison_curves = []
        self.last_file = last_file  # Store the last used file path
        self.setup_ui()
        
    def setup_ui(self):
        self.setWindowTitle("Load Comparison Curve")
        self.setModal(True)
        self.setMinimumWidth(500)
        
        layout = QVBoxLayout()
        
        # File selection
        file_group = QGroupBox("Select File")
        file_layout = QHBoxLayout()
        
        self.file_path_edit = QLineEdit()
        self.file_path_edit.setReadOnly(True)
        self.file_path_edit.setPlaceholderText("No file selected")
        
        # Add a "Change File" button
        self.browse_btn = QPushButton("Browse...")
        self.browse_btn.clicked.connect(self.browse_file)
        
        file_layout.addWidget(self.file_path_edit)
        file_layout.addWidget(self.browse_btn)
        file_group.setLayout(file_layout)
        layout.addWidget(file_group)
        
        # Curve selection
        curve_group = QGroupBox("Select Curve")
        curve_layout = QVBoxLayout()
        
        # Add radio buttons for "Use same file" vs "Load different file"
        self.file_selection_group = QButtonGroup()
        
        self.same_file_radio = QRadioButton("Use current comparison file")
        self.same_file_radio.setChecked(True)
        self.same_file_radio.toggled.connect(self.on_file_selection_changed)
        
        self.different_file_radio = QRadioButton("Load different file")
        self.different_file_radio.toggled.connect(self.on_file_selection_changed)
        
        curve_layout.addWidget(self.same_file_radio)
        curve_layout.addWidget(self.different_file_radio)
        
        # Curve combo box
        self.curve_combo = QComboBox()
        self.curve_combo.setEnabled(True)
        self.curve_combo.currentIndexChanged.connect(self.on_curve_selected)
        
        curve_layout.addWidget(QLabel("Select curve:"))
        curve_layout.addWidget(self.curve_combo)
        
        # Curve info
        self.info_label = QLabel("")
        self.info_label.setStyleSheet("color: #888; font-style: italic;")
        curve_layout.addWidget(self.info_label)
        
        curve_group.setLayout(curve_layout)
        layout.addWidget(curve_group)
        
        # Preview plot
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
        
        # Buttons
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
        
        # If we have a last file, load it automatically
        if self.last_file and Path(self.last_file).exists():
            self.load_file(self.last_file)
            self.same_file_radio.setChecked(True)
        else:
            # Disable same file radio if no last file
            self.same_file_radio.setEnabled(False)
            self.different_file_radio.setChecked(True)
    
    def on_file_selection_changed(self):
        """Handle file selection radio button changes"""
        if self.same_file_radio.isChecked():
            # Use the last file
            if self.last_file and Path(self.last_file).exists():
                self.load_file(self.last_file)
                self.browse_btn.setEnabled(False)
                self.file_path_edit.setEnabled(False)
            else:
                # Fall back to different file if last file doesn't exist
                self.different_file_radio.setChecked(True)
        else:
            # Allow browsing for a different file
            self.browse_btn.setEnabled(True)
            self.file_path_edit.setEnabled(True)
            # Clear current selection if no file is loaded
            if not self.file_path_edit.text():
                self.curve_combo.clear()
                self.curve_combo.setEnabled(False)
                self.show_btn.setEnabled(False)
                self.info_label.setText("No file selected")
                self.preview_plot.clear()
    
    def browse_file(self):
        """Browse for a tire file"""
        # Start from the last file's directory if available
        start_dir = str(Path.home())
        if self.last_file:
            start_dir = str(Path(self.last_file).parent)
        
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Select Tire File",
            start_dir,
            "Tire files (*.tbc *.tyr);;All files (*.*)"
        )
        
        if filename:
            self.load_file(filename)
            # Automatically switch to "different file" mode when browsing
            self.different_file_radio.setChecked(True)
    
    def load_file(self, filename):
        """Load curves from selected file"""
        try:
            self.comparison_curves = self.parse_tire_file(filename)
            
            if self.comparison_curves:
                self.file_path_edit.setText(filename)
                self.selected_file = filename
                
                # Update curve combo
                self.curve_combo.clear()
                self.curve_combo.addItems([c['name'] for c in self.comparison_curves])
                self.curve_combo.setEnabled(True)
                
                # Update info
                self.info_label.setText(f"Loaded {len(self.comparison_curves)} curves from {Path(filename).name}")
                self.info_label.setStyleSheet("color: #4CAF50;")
                
                # Enable show button
                self.show_btn.setEnabled(True)
                
                # Show first curve preview
                self.on_curve_selected(0)
            else:
                QMessageBox.warning(self, "No Curves", "No slip curves found in the selected file.")
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load file: {e}")
    
    def parse_tire_file(self, filename):
        """Parse tire file and extract slip curves"""
        curves = []
        
        with open(filename, 'r') as f:
            content = f.read()
        
        # Parse slip curves
        slip_curve_pattern = r'(\[SLIPCURVE\]\s*Name="([^"]+)"\s*Step=([0-9.e+-]+)[^\n]*\s*DropoffFunction=([0-9.e+-]+)[^\n]*\s*Data:\s*((?:\d+\.\d+\s*)+))'
        
        for match in re.finditer(slip_curve_pattern, content, re.MULTILINE | re.DOTALL):
            name = match.group(2)
            step = float(match.group(3))
            dropoff = float(match.group(4))
            
            # Parse the data values
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
        """Handle curve selection change"""
        if index >= 0 and index < len(self.comparison_curves):
            self.selected_curve_index = index
            curve = self.comparison_curves[index]
            
            # Update preview plot
            self.preview_plot.clear()
            self.preview_plot.plot(curve['x_values'], curve['values'], 
                                   pen=pg.mkPen('y', width=2))
            self.preview_plot.autoRange()
    
    def get_selected_curve(self):
        """Get the selected curve data"""
        if self.comparison_curves and self.selected_curve_index < len(self.comparison_curves):
            return self.comparison_curves[self.selected_curve_index]
        return None
    
    def get_selected_file(self):
        """Get the selected file path"""
        return self.selected_file

class TireCurveEditor:
    def __init__(self, filename):
        self.filename = filename
        self.original_content = ""
        self.slip_curves = []
        self.curve_matches = []
        self.modified_curves = {}
        self.current_curve_index = 0
        self.show_all_curves = False
        self.all_curves_plots = []  # Store all curve plot items
        self.comparison_curve = None  # Store comparison curve data
        self.comparison_plot = None  # Store comparison curve plot item
        self.preview_curve = None  # Store preview curve item
        self.preview_values = None  # Store current preview values
        self.point_highlight = None  # Store point highlight item
        self.point_edit_widget = None  # Store point edit widget
        self.legend = None  # Store legend widget
        self.last_comparison_file = None  # Store last used comparison file
        
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
        self.window.setGeometry(100, 100, 1600, 1000)  # Larger window
        
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
        
        # Curve selection - IMPROVED VISIBILITY
        control_layout.addWidget(QLabel("Curve:"))
        self.curve_combo = QComboBox()
        self.curve_combo.addItems([c['name'] for c in self.slip_curves])
        self.curve_combo.currentIndexChanged.connect(self.on_curve_selected)
        # Make the combo box more visible
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
        
        # Show all curves checkbox
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
        
        # Comparison controls
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
        
        # Operation buttons
        self.multiply_btn = QPushButton("✕ Multiply")
        self.multiply_btn.clicked.connect(lambda: self.show_preview_dialog("multiply"))
        control_layout.addWidget(self.multiply_btn)
        
        self.offset_btn = QPushButton("➕ Add Offset")
        self.offset_btn.clicked.connect(lambda: self.show_preview_dialog("offset"))
        control_layout.addWidget(self.offset_btn)
        
        self.smooth_btn = QPushButton("〰 Smooth")
        self.smooth_btn.clicked.connect(lambda: self.show_preview_dialog("smooth"))
        control_layout.addWidget(self.smooth_btn)
        
        self.reset_btn = QPushButton("↺ Reset")
        self.reset_btn.clicked.connect(self.reset_curve)
        control_layout.addWidget(self.reset_btn)
        
        left_layout.addWidget(control_bar)
        
        # Point edit widget - pass left_panel as parent (which is a QWidget)
        self.point_edit_widget = PointEditWidget(self, left_panel)
        self.point_edit_widget.setFocusPolicy(Qt.ClickFocus)  # Allow focus by clicking
        left_layout.addWidget(self.point_edit_widget)
        
        # Plot widget - made larger with stretch factor
        self.plot_widget = pg.PlotWidget(title="Slip Curve")
        self.plot_widget.setLabel('left', 'Normalized Force')
        self.plot_widget.setLabel('bottom', 'Slip')
        self.plot_widget.showGrid(x=True, y=True, alpha=0.3)
        self.plot_widget.setMouseEnabled(x=True, y=True)
        self.plot_widget.setMinimumHeight(500)  # Set minimum height
        self.plot_widget.setFocusPolicy(Qt.StrongFocus)  # Allow plot to receive focus
        
        # Add legend and store reference
        self.legend = self.plot_widget.addLegend()
        
        # Create curves
        self.curve_plot = self.plot_widget.plot(pen=pg.mkPen('b', width=2), name='Slip Curve')
        self.original_curve_plot = self.plot_widget.plot(pen=pg.mkPen('gray', width=1, style=Qt.DashLine), name='Original')
        
        # Create comparison plot with a name
        self.comparison_plot = self.plot_widget.plot(pen=pg.mkPen('orange', width=2, style=Qt.DashLine), 
                                                      name='Comparison')
        self.comparison_plot.hide()  # Hide initially
        
        self.preview_curve = self.plot_widget.plot(pen=pg.mkPen('y', width=2, style=Qt.DashLine), name='Preview')
        self.preview_curve.hide()  # Hide initially
        
        # Point highlight (red circle)
        self.point_highlight = pg.ScatterPlotItem(pen='r', brush=None, size=15, symbol='o', name='Selected Point')
        
        self.peak_marker = pg.ScatterPlotItem(pen='r', brush='r', size=15, symbol='star', name='Peak')
        
        self.plot_widget.addItem(self.peak_marker)
        self.plot_widget.addItem(self.point_highlight)
        
        left_layout.addWidget(self.plot_widget, 2)  # Give plot more stretch
        
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
        
        # Right panel - Parameters and Data
        right_panel = QWidget()
        right_panel.setMaximumWidth(450)
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
        self.param_list.setMaximumHeight(120)
        self.param_list.itemDoubleClicked.connect(self.edit_parameter)
        params_layout.addWidget(self.param_list)
        
        params_group.setLayout(params_layout)
        right_layout.addWidget(params_group)
        
        # Data display
        data_group = QGroupBox("Curve Data")
        data_layout = QVBoxLayout()
        
        # Data text edit with monospace font
        self.data_display = QTextEdit()
        self.data_display.setFont(QFont("Courier New", 9))
        self.data_display.setReadOnly(True)
        self.data_display.setLineWrapMode(QTextEdit.NoWrap)
        self.data_display.setMinimumHeight(300)
        data_layout.addWidget(self.data_display)
        
        # Copy data button
        copy_data_btn = QPushButton("📋 Copy Data to Clipboard")
        copy_data_btn.clicked.connect(self.copy_data_to_clipboard)
        data_layout.addWidget(copy_data_btn)
        
        data_group.setLayout(data_layout)
        right_layout.addWidget(data_group, 1)  # Give data display stretch
        
        # Status bar
        self.status_bar = QStatusBar()
        self.window.setStatusBar(self.status_bar)
        
        # Add panels to main layout
        main_layout.addWidget(left_panel, 3)  # Left panel gets more space
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
    
    def update_point_value(self, index, value):
        """Update a single point value (called from PointEditWidget)"""
        if self.show_all_curves:
            return
        
        # Store modified curve if not already modified
        curve = self.slip_curves[self.current_curve_index]
        if self.current_curve_index not in self.modified_curves:
            self.modified_curves[self.current_curve_index] = {
                'values': curve['values'].copy(),
                'step': curve['step']
            }
        
        # Update the value
        self.modified_curves[self.current_curve_index]['values'][index] = value
        
        # Reload the curve to update display
        self.load_curve(self.current_curve_index)
        
        # Keep the same point selected
        if self.point_edit_widget:
            self.point_edit_widget.current_point_index = index
            self.point_edit_widget.update_display()
            self.highlight_point(index)
        
        self.status_bar.showMessage(f"Point {index+1} updated", 1000)
    
    def highlight_point(self, index):
        """Highlight a specific point on the curve"""
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
        """Update the data display with current curve values"""
        curve = self.slip_curves[self.current_curve_index]
        
        # Get current values (modified or original)
        if self.current_curve_index in self.modified_curves:
            values = self.modified_curves[self.current_curve_index]['values']
        else:
            values = curve['values']
        
        # Format the data with 6 decimal places, 10 values per line
        data_lines = []
        for i in range(0, len(values), 10):
            line_values = values[i:i+10]
            formatted_line = ' '.join(f"{v:.6f}" for v in line_values)
            data_lines.append(formatted_line)
        
        data_text = '\n'.join(data_lines)
        self.data_display.setText(data_text)
    
    def copy_data_to_clipboard(self):
        """Copy the data display content to clipboard"""
        clipboard = QApplication.clipboard()
        clipboard.setText(self.data_display.toPlainText())
        self.status_bar.showMessage("Data copied to clipboard", 2000)
    
    def load_comparison_curve(self):
        """Load a comparison curve from another file"""
        # Pass the last used comparison file to the dialog
        dialog = CompareFileDialog(self.window, self.last_comparison_file)
        
        if dialog.exec_() == QDialog.Accepted:
            curve = dialog.get_selected_curve()
            selected_file = dialog.get_selected_file()
            
            if curve and selected_file:
                # Store the selected file for next time
                self.last_comparison_file = selected_file
                self.comparison_curve = curve
                self.show_comparison_curve()
                self.status_bar.showMessage(f"Loaded comparison curve: {curve['name']} from {Path(selected_file).name}", 3000)
    
    def show_comparison_curve(self):
        """Show the comparison curve on the plot"""
        if self.comparison_curve and not self.show_all_curves:
            # Plot the comparison curve
            self.comparison_plot.setData(
                self.comparison_curve['x_values'],
                self.comparison_curve['values']
            )
            self.comparison_plot.show()
            
            # Update legend using self.legend
            if hasattr(self, 'legend') and self.legend is not None:
                # Remove old item from legend if it exists
                try:
                    self.legend.removeItem(self.comparison_plot)
                except:
                    pass  # Item might not be in legend yet
                # Add back with new name
                self.legend.addItem(self.comparison_plot, f"Comparison: {self.comparison_curve['name']}")
            
            # Enable hide button
            self.hide_compare_btn.setEnabled(True)
            
            # Auto-range to include comparison curve
            self.plot_widget.autoRange()
    
    def hide_comparison_curve(self):
        """Hide the comparison curve"""
        if self.comparison_plot:
            self.comparison_plot.hide()
            self.hide_compare_btn.setEnabled(False)
            
            # Also remove from legend
            if hasattr(self, 'legend') and self.legend is not None:
                try:
                    self.legend.removeItem(self.comparison_plot)
                except:
                    pass
            
            self.status_bar.showMessage("Comparison curve hidden", 2000)
    
    def show_preview_dialog(self, operation_type):
        """Show preview dialog for operations"""
        if self.show_all_curves:
            QMessageBox.warning(self.window, "Editing Disabled", 
                               "Editing is disabled when showing all curves. Please uncheck 'Show All Curves' to edit.")
            return
        
        # Get current curve values
        curve = self.slip_curves[self.current_curve_index]
        if self.current_curve_index in self.modified_curves:
            current_values = self.modified_curves[self.current_curve_index]['values']
        else:
            current_values = curve['values'].copy()
        
        # Create and show preview dialog with self.window as parent
        dialog = PreviewDialog(
            f"{operation_type.capitalize()} Curve - Preview",
            operation_type,
            current_values,
            self.plot_widget,
            self.window  # Pass the main window as parent
        )
        
        if dialog.exec_() == QDialog.Accepted:
            # Apply the changes
            new_values = dialog.get_values()
            
            # Store modified curve
            if self.current_curve_index not in self.modified_curves:
                self.modified_curves[self.current_curve_index] = {
                    'values': curve['values'].copy(),
                    'step': curve['step']
                }
            
            self.modified_curves[self.current_curve_index]['values'] = new_values
            self.load_curve(self.current_curve_index)
            self.status_bar.showMessage(f"{operation_type.capitalize()} applied", 2000)
        
        # Clear preview
        self.clear_preview()
    
    def update_preview_curve(self, preview_values):
        """Update the preview curve with new values (called from dialog)"""
        if self.show_all_curves:
            return
        
        curve = self.slip_curves[self.current_curve_index]
        step = curve['step']
        if self.current_curve_index in self.modified_curves:
            step = self.modified_curves[self.current_curve_index]['step']
        
        x_values = [i * step for i in range(len(preview_values))]
        
        # Show preview curve
        self.preview_curve.setData(x_values, preview_values)
        self.preview_curve.show()
        
        # Dim the main curve slightly to highlight preview
        self.curve_plot.setPen(pg.mkPen('b', width=2, style=Qt.DashLine))
        
        # Store preview values
        self.preview_values = preview_values
    
    def clear_preview(self):
        """Clear the preview curve"""
        self.preview_curve.hide()
        self.curve_plot.setPen(pg.mkPen('b', width=2))
        self.preview_values = None
    
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
        if not self.show_all_curves:
            # Normal mode - show only selected curve
            self.curve_plot.setData(x_values, values)
            
            # Show original for comparison if modified
            if index in self.modified_curves:
                orig_x = [i * curve['step'] for i in range(len(curve['values']))]
                self.original_curve_plot.setData(orig_x, curve['values'])
                self.original_curve_plot.show()
            else:
                self.original_curve_plot.hide()
            
            # Hide all all-curves plots
            for plot in self.all_curves_plots:
                plot.hide()
            
            # Hide preview if showing
            self.preview_curve.hide()
            
            # Show comparison curve if available
            if self.comparison_curve:
                self.show_comparison_curve()
            else:
                self.comparison_plot.hide()
            
            # Mark peak
            peak_idx = np.argmax(values)
            peak_x = x_values[peak_idx]
            peak_y = values[peak_idx]
            self.peak_marker.setData([peak_x], [peak_y])
            
            # Update point edit widget
            if self.point_edit_widget:
                self.point_edit_widget.set_values(values)
            
            # Highlight first point
            self.highlight_point(0)
        else:
            # Show all curves mode
            self.update_all_curves_display()
        
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
        
        # Update data display
        self.update_data_display()
        
        # Update status
        if index in self.modified_curves:
            self.status_bar.showMessage(f"Curve modified (unsaved changes)", 3000)
        else:
            self.status_bar.showMessage(f"Original curve", 3000)
    
    def update_all_curves_display(self):
        """Update the display when showing all curves"""
        # Clear existing all-curves plots
        for plot in self.all_curves_plots:
            self.plot_widget.removeItem(plot)
        self.all_curves_plots.clear()
        
        # Hide individual curve plots
        self.curve_plot.hide()
        self.original_curve_plot.hide()
        self.preview_curve.hide()
        self.comparison_plot.hide()
        self.peak_marker.hide()
        self.point_highlight.hide()
        
        # Clear legend
        if hasattr(self, 'legend') and self.legend is not None:
            self.legend.clear()
        
        # Generate colors for curves
        colors = [
            (255, 0, 0),    # Red
            (0, 255, 0),    # Green
            (0, 0, 255),    # Blue
            (255, 255, 0),  # Yellow
            (255, 0, 255),  # Magenta
            (0, 255, 255),  # Cyan
            (255, 128, 0),  # Orange
            (128, 0, 255),  # Purple
            (255, 128, 128), # Light Red
            (128, 255, 128), # Light Green
        ]
        
        # Plot all curves
        for i, curve in enumerate(self.slip_curves):
            # Use modified values if available
            if i in self.modified_curves:
                values = self.modified_curves[i]['values']
                step = self.modified_curves[i]['step']
            else:
                values = curve['values']
                step = curve['step']
            
            x_values = [j * step for j in range(len(values))]
            
            # Select color (cycle through colors if more curves than colors)
            color = colors[i % len(colors)]
            
            # Determine line style: dashed for all except current curve
            if i == self.current_curve_index:
                # Current curve - solid line, thicker
                pen = pg.mkPen(color=color, width=3, style=Qt.SolidLine)
            else:
                # Other curves - dashed lines
                pen = pg.mkPen(color=color, width=1.5, style=Qt.DashLine)
            
            # Create plot with name
            plot = self.plot_widget.plot(
                x_values, values,
                pen=pen,
                name=curve['name']
            )
            self.all_curves_plots.append(plot)
            
            # Add to legend
            if hasattr(self, 'legend') and self.legend is not None:
                self.legend.addItem(plot, curve['name'])
    
    def toggle_show_all_curves(self, state):
        """Toggle between showing all curves or single curve"""
        self.show_all_curves = (state == Qt.Checked)
        
        if self.show_all_curves:
            # Show all curves
            self.update_all_curves_display()
            # Disable step spin and some operations when showing all curves
            self.step_spin.setEnabled(False)
            self.multiply_btn.setEnabled(False)
            self.offset_btn.setEnabled(False)
            self.smooth_btn.setEnabled(False)
            self.load_compare_btn.setEnabled(False)
            self.hide_compare_btn.setEnabled(False)
            if self.point_edit_widget:
                self.point_edit_widget.setEnabled(False)
            self.status_bar.showMessage("Showing all curves - editing disabled", 3000)
        else:
            # Back to single curve mode
            # Hide all all-curves plots
            for plot in self.all_curves_plots:
                self.plot_widget.removeItem(plot)
            self.all_curves_plots.clear()
            
            # Show individual curve plots
            self.curve_plot.show()
            self.peak_marker.show()
            self.point_highlight.show()
            
            # Re-enable controls
            self.step_spin.setEnabled(True)
            self.multiply_btn.setEnabled(True)
            self.offset_btn.setEnabled(True)
            self.smooth_btn.setEnabled(True)
            self.load_compare_btn.setEnabled(True)
            if self.point_edit_widget:
                self.point_edit_widget.setEnabled(True)
            
            # Show comparison curve if available
            if self.comparison_curve:
                self.show_comparison_curve()
            else:
                self.comparison_plot.hide()
                self.hide_compare_btn.setEnabled(False)
            
            # Reload current curve
            self.load_curve(self.current_curve_index)
    
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
    
    def on_curve_selected(self, index):
        """Handle curve selection change"""
        self.current_curve_index = index
        if self.show_all_curves:
            # Just highlight the selected curve in the all-curves view
            self.update_all_curves_display()
        else:
            self.load_curve(index)
    
    def on_step_changed(self, value):
        """Handle step size change"""
        if self.show_all_curves:
            return
            
        curve = self.slip_curves[self.current_curve_index]
        
        # Store modified curve
        if self.current_curve_index not in self.modified_curves:
            self.modified_curves[self.current_curve_index] = {
                'values': curve['values'].copy(),
                'step': curve['step']
            }
        
        self.modified_curves[self.current_curve_index]['step'] = value
        self.load_curve(self.current_curve_index)
    
    def reset_curve(self):
        """Reset current curve to original"""
        if self.show_all_curves:
            QMessageBox.warning(self.window, "Editing Disabled", 
                               "Editing is disabled when showing all curves. Please uncheck 'Show All Curves' to edit.")
            return
            
        if self.current_curve_index in self.modified_curves:
            del self.modified_curves[self.current_curve_index]
            self.load_curve(self.current_curve_index)
            self.status_bar.showMessage("Curve reset to original", 2000)
    
    def revert_all(self):
        """Revert all curves to original"""
        if self.show_all_curves:
            QMessageBox.warning(self.window, "Editing Disabled", 
                               "Editing is disabled when showing all curves. Please uncheck 'Show All Curves' to edit.")
            return
            
        reply = QMessageBox.question(self.window, "Confirm",
                                    "Revert all changes?",
                                    QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.modified_curves.clear()
            self.load_curve(self.current_curve_index)
            self.status_bar.showMessage("All curves reverted to original", 3000)
    
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
            # Start with original content
            new_content = self.original_content
            
            # Apply modifications - process in reverse order to maintain indices
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
                    formatted_line = ' '.join(f"{v:.6f}" for v in line_values)
                    data_lines.append(formatted_line)
                new_data_str = '\n'.join(data_lines)
                
                # Create new block with proper formatting - ensure it ends with newline
                new_block = f'[SLIPCURVE]\nName="{original_curve["name"]}"\nStep={step:.6f}            // Slip step\nDropoffFunction={original_curve["dropoff_function"]:.1f}      // see above            \nData:\n{new_data_str}\n'
                
                # Get the original block
                old_block = original_curve['full_match']
                
                # Find the position of this block in the content
                pos = new_content.find(old_block)
                if pos >= 0:
                    # Find where this block ends
                    end_pos = pos + len(old_block)
                    
                    # Look ahead to find the next section marker ([SLIPCURVE] or [COMPOUND])
                    next_section_pos = -1
                    
                    # Try to find next [SLIPCURVE]
                    next_curve_pos = new_content.find('[SLIPCURVE]', end_pos)
                    # Try to find next [COMPOUND]
                    next_compound_pos = new_content.find('[COMPOUND]', end_pos)
                    
                    # Find the closest next section
                    if next_curve_pos >= 0 and next_compound_pos >= 0:
                        next_section_pos = min(next_curve_pos, next_compound_pos)
                    elif next_curve_pos >= 0:
                        next_section_pos = next_curve_pos
                    elif next_compound_pos >= 0:
                        next_section_pos = next_compound_pos
                    
                    if next_section_pos >= 0:
                        # Capture everything between this block and the next section
                        between_content = new_content[end_pos:next_section_pos]
                        
                        # Ensure we have at least one newline between blocks
                        # But preserve the original formatting
                        if not between_content.startswith('\n'):
                            between_content = '\n' + between_content
                        
                        # Replace with new block + the preserved between content
                        new_content = new_content[:pos] + new_block + between_content + new_content[next_section_pos:]
                    else:
                        # This is the last block, replace it and keep everything after
                        trailing_content = new_content[end_pos:]
                        
                        # Ensure the file ends with a newline
                        if trailing_content and not trailing_content.endswith('\n'):
                            trailing_content += '\n'
                        
                        new_content = new_content[:pos] + new_block + trailing_content
                else:
                    # Fallback to simple replace if position not found
                    # Ensure we add a newline after the block
                    if not old_block.endswith('\n'):
                        old_block_with_newline = old_block + '\n'
                        new_block_with_newline = new_block + '\n' if not new_block.endswith('\n') else new_block
                        new_content = new_content.replace(old_block_with_newline, new_block_with_newline)
                    else:
                        new_content = new_content.replace(old_block, new_block)
            
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
            import traceback
            traceback.print_exc()
    
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
