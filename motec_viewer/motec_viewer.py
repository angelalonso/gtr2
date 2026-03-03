# pipenv install
#!/usr/bin/env python3
"""
SimHub-style Telemetry Overlay
Visualize throttle, brake, gear, speed, and RPM from MoTeC .ld or .csv files
"""

import sys
import struct
import numpy as np
import csv
from pathlib import Path
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
import pyqtgraph as pg


class MoTeCDataReader:
    """Read and parse MoTeC .ld or .csv data files"""
    
    def __init__(self, filename):
        self.filename = filename
        self.channels = []
        self.data = {}  # channel name -> numpy array of values
        self.time_data = None
        self.sample_count = 0
        self.file_info = {}
        self.file_extension = Path(filename).suffix.lower()
        
        if self.file_extension == '.csv':
            self.read_csv_file()
        else:
            self.read_ld_file()
    
    def read_csv_file(self):
        """Parse the MoTeC CSV file format (with metadata header)"""
        try:
            # Read the file to find data start
            with open(self.filename, 'r', encoding='latin-1') as f:
                lines = f.readlines()
            
            # Find the line with column headers (contains "Time","Distance"...)
            header_line_index = -1
            for i, line in enumerate(lines):
                if '"Time","Distance"' in line or line.startswith('"Time","Distance"'):
                    header_line_index = i
                    break
            
            if header_line_index == -1:
                raise ValueError("Could not find data header in CSV file")
            
            # Parse metadata from lines before header
            for i in range(header_line_index):
                line = lines[i].strip()
                if line and ',' in line:
                    parts = line.split(',')
                    if len(parts) >= 2:
                        key = parts[0].strip('"')
                        value = parts[1].strip('"')
                        self.file_info[key] = value
            
            # Parse header to get column names
            header_line = lines[header_line_index].strip()
            # Split CSV properly handling quotes
            import csv as csv_module
            reader = csv_module.reader([header_line])
            column_names = next(reader)
            
            # Clean up column names (remove quotes)
            column_names = [name.strip('"') for name in column_names]
            
            # Map our needed channels to column names
            channel_map = {
                'Throttle Position': 'Throttle Pos',
                'Brake Pedal Position': 'Brake Pedal Pos',
                'Ground Speed': 'Ground Speed',
                'Engine RPM': 'Engine RPM',
                'Gear': 'Gear',
                'Steering Wheel Angle': 'Steering Wheel Angle',
                'Time': 'Time'
            }
            
            # Find column indices for our channels
            column_indices = {}
            for our_name, csv_name in channel_map.items():
                if csv_name in column_names:
                    column_indices[our_name] = column_names.index(csv_name)
                else:
                    # Try to find alternative names
                    for i, col in enumerate(column_names):
                        if csv_name.lower() in col.lower() or our_name.lower() in col.lower():
                            column_indices[our_name] = i
                            print(f"Found alternative match: {col} for {our_name}")
                            break
            
            if 'Time' not in column_indices:
                print("Warning: Time column not found")
                return
            
            # Parse data
            data_arrays = {name: [] for name in column_indices.keys()}
            
            # Process data lines
            for line in lines[header_line_index + 1:]:
                line = line.strip()
                if not line:
                    continue
                
                try:
                    # Parse CSV line
                    reader = csv_module.reader([line])
                    values = next(reader)
                    
                    if len(values) >= len(column_names):
                        for our_name, idx in column_indices.items():
                            if idx < len(values):
                                val_str = values[idx].strip()
                                if val_str and val_str != '':
                                    try:
                                        # Convert comma decimal to float
                                        val_str = val_str.replace(',', '.')
                                        val = float(val_str)
                                        data_arrays[our_name].append(val)
                                    except ValueError:
                                        data_arrays[our_name].append(0.0)
                                else:
                                    data_arrays[our_name].append(0.0)
                except Exception as e:
                    print(f"Error parsing line: {e}")
                    continue
            
            # Convert to numpy arrays
            min_length = min(len(arr) for arr in data_arrays.values())
            for name in data_arrays:
                if len(data_arrays[name]) > min_length:
                    data_arrays[name] = data_arrays[name][:min_length]
                self.data[name] = np.array(data_arrays[name])
            
            # Create time axis (use Time column if available)
            if 'Time' in data_arrays and len(data_arrays['Time']) > 0:
                self.time_data = np.array(data_arrays['Time'])
            else:
                # Create sequential sample numbers as time
                self.sample_count = len(self.data[list(self.data.keys())[0]])
                self.time_data = np.arange(self.sample_count)
            
            self.sample_count = len(self.time_data)
            print(f"Loaded {self.sample_count} samples from CSV")
            print(f"Channels found: {list(self.data.keys())}")
            print(f"Time range: {self.time_data[0]:.3f} to {self.time_data[-1]:.3f}")
            
        except Exception as e:
            print(f"Error reading CSV: {e}")
            import traceback
            traceback.print_exc()
            self.generate_synthetic_data()
    
    def read_ld_file(self):
        """Parse the MoTeC LD file format"""
        try:
            with open(self.filename, 'rb') as f:
                content = f.read()
            
            # Try to decode as text to find channel information
            text_part = content[:50000].decode('latin-1', errors='ignore')
            lines = text_part.split('\n')
            
            # Parse channel information
            channel_patterns = [
                'Throttle Position', 'Brake Pedal Position', 'Ground Speed',
                'Engine RPM', 'Gear', 'Steering Wheel Angle'
            ]
            
            for i, line in enumerate(lines):
                for pattern in channel_patterns:
                    if pattern in line:
                        parts = line.split('\x00')
                        clean_parts = [p for p in parts if p.strip()]
                        
                        for part in clean_parts:
                            if pattern in part:
                                units = 'unknown'
                                if 'deg' in part:
                                    units = 'deg'
                                elif '%' in part:
                                    units = '%'
                                elif 'km/h' in part.lower():
                                    units = 'km/h'
                                elif 'rpm' in part.lower():
                                    units = 'rpm'
                                
                                self.channels.append({
                                    'name': pattern,
                                    'units': units,
                                    'index': i
                                })
                                break
            
            # Find the start of binary data
            data_start = 0
            for i in range(len(content) - 4):
                possible_count = struct.unpack('<I', content[i:i+4])[0]
                if 1000 < possible_count < 100000:
                    data_start = i
                    self.sample_count = possible_count
                    break
            
            if data_start == 0 or self.sample_count == 0:
                print("Warning: Could not parse file structure, generating synthetic data")
                self.generate_synthetic_data()
                return
            
            # Try to extract data for each channel
            bytes_per_sample = 4
            for channel in self.channels:
                channel_name = channel['name']
                data_array = []
                
                for sample in range(min(self.sample_count, 10000)):
                    offset = data_start + sample * bytes_per_sample
                    if offset + 4 <= len(content):
                        try:
                            value = struct.unpack('<f', content[offset:offset+4])[0]
                            if -1000 < value < 10000:
                                data_array.append(value)
                        except:
                            data_array.append(0.0)
                
                if len(data_array) > 10:
                    self.data[channel_name] = np.array(data_array)
            
            # Generate time axis
            if self.data:
                max_len = max(len(arr) for arr in self.data.values())
                self.sample_count = max_len
                self.time_data = np.arange(max_len) * 0.01  # Assume 100Hz sampling
            
            # If no data was extracted, generate synthetic data
            if not self.data:
                self.generate_synthetic_data()
                
        except Exception as e:
            print(f"Error reading LD file: {e}")
            self.generate_synthetic_data()
    
    def generate_synthetic_data(self):
        """Generate synthetic data for demonstration"""
        self.sample_count = 5000
        t = np.arange(self.sample_count) * 0.01
        
        # Generate realistic Formula BMW telemetry
        speed = np.zeros_like(t)
        throttle = np.zeros_like(t)
        brake = np.zeros_like(t)
        rpm = np.zeros_like(t)
        gear = np.zeros_like(t, dtype=int)
        
        # Simulate a lap
        lap_time = 100  # seconds
        samples_per_lap = int(lap_time / 0.01)
        
        for lap in range(int(self.sample_count / samples_per_lap) + 1):
            start = lap * samples_per_lap
            end = min((lap + 1) * samples_per_lap, self.sample_count)
            if start >= self.sample_count:
                break
            
            lap_t = t[start:end] - t[start]
            
            # Acceleration phase (0-30s)
            accel_mask = lap_t < 30
            if np.any(accel_mask):
                idx = np.where(accel_mask)[0] + start
                speed[idx] = 200 * (lap_t[accel_mask] / 30)
                throttle[idx] = 100 * (1 - lap_t[accel_mask] / 60)
                rpm[idx] = 5000 + 3000 * (lap_t[accel_mask] / 30)
            
            # Braking phase (30-40s)
            brake_mask = (lap_t >= 30) & (lap_t < 40)
            if np.any(brake_mask):
                idx = np.where(brake_mask)[0] + start
                brake[idx] = 100 * ((lap_t[brake_mask] - 30) / 10)
                speed[idx] = 200 * (1 - (lap_t[brake_mask] - 30) / 10)
            
            # Cornering phase (40-60s)
            corner_mask = (lap_t >= 40) & (lap_t < 60)
            if np.any(corner_mask):
                idx = np.where(corner_mask)[0] + start
                speed[idx] = 80 + 20 * np.sin(2 * np.pi * (lap_t[corner_mask] - 40) / 20)
                throttle[idx] = 30 + 20 * np.sin(2 * np.pi * (lap_t[corner_mask] - 40) / 20 + 1)
            
            # Acceleration out of corner (60-80s)
            accel2_mask = (lap_t >= 60) & (lap_t < 80)
            if np.any(accel2_mask):
                idx = np.where(accel2_mask)[0] + start
                speed[idx] = 100 + 100 * ((lap_t[accel2_mask] - 60) / 20)
                throttle[idx] = 80 + 20 * (1 - (lap_t[accel2_mask] - 60) / 20)
                rpm[idx] = 6000 + 2000 * ((lap_t[accel2_mask] - 60) / 20)
            
            # Braking for next corner (80-90s)
            brake2_mask = (lap_t >= 80) & (lap_t < 90)
            if np.any(brake2_mask):
                idx = np.where(brake2_mask)[0] + start
                brake[idx] = 100 * ((lap_t[brake2_mask] - 80) / 10)
                speed[idx] = 200 * (1 - (lap_t[brake2_mask] - 80) / 10)
            
            # Rest of lap...
            other_mask = lap_t >= 90
            if np.any(other_mask):
                idx = np.where(other_mask)[0] + start
                speed[idx] = 180
                throttle[idx] = 60
                rpm[idx] = 7000
        
        # Calculate gear based on RPM
        gear[:] = 1
        gear[rpm > 6000] = 2
        gear[rpm > 7000] = 3
        gear[rpm > 8000] = 4
        gear[rpm > 9000] = 5
        gear[rpm > 10000] = 6
        
        # Add noise
        speed += np.random.normal(0, 1, self.sample_count)
        rpm += np.random.normal(0, 50, self.sample_count)
        
        self.data = {
            'Throttle Position': throttle,
            'Brake Pedal Position': brake,
            'Ground Speed': speed,
            'Engine RPM': rpm,
            'Gear': gear.astype(float)
        }
        self.time_data = t


class SimHubOverlay(QWidget):
    """SimHub-style telemetry overlay widget"""
    
    def __init__(self, reader, parent=None):
        super().__init__(parent)
        self.reader = reader
        self.current_index = 0  # Use index instead of time
        self.setup_ui()
        
        # Set window flags for overlay style
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        # Timer for playback
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)
        self.timer.setInterval(16)  # ~60 fps for smooth playback
        
        # Enable/disable buttons based on data availability
        self.update_button_states()
        
        # Initial display update
        self.update_display()
    
    def setup_ui(self):
        # Main layout
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Top row: Gear and Speed
        top_row = QWidget()
        top_layout = QHBoxLayout(top_row)
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setSpacing(20)
        
        # Gear display (big)
        self.gear_label = QLabel("0")
        self.gear_label.setAlignment(Qt.AlignCenter)
        gear_font = QFont("Arial Black", 72)
        self.gear_label.setFont(gear_font)
        self.gear_label.setStyleSheet("""
            color: white;
            background-color: rgba(0, 0, 0, 0.7);
            border: 3px solid #00ff00;
            border-radius: 10px;
            padding: 10px 20px;
            min-width: 120px;
        """)
        top_layout.addWidget(self.gear_label)
        
        # Speed display (big)
        self.speed_label = QLabel("0")
        self.speed_label.setAlignment(Qt.AlignCenter)
        speed_font = QFont("Arial Black", 72)
        self.speed_label.setFont(speed_font)
        self.speed_label.setStyleSheet("""
            color: white;
            background-color: rgba(0, 0, 0, 0.7);
            border: 3px solid #00ff00;
            border-radius: 10px;
            padding: 10px 20px;
            min-width: 200px;
        """)
        top_layout.addWidget(self.speed_label)
        
        # RPM display (smaller)
        self.rpm_label = QLabel("0 RPM")
        self.rpm_label.setAlignment(Qt.AlignCenter)
        rpm_font = QFont("Arial", 36)
        self.rpm_label.setFont(rpm_font)
        self.rpm_label.setStyleSheet("""
            color: white;
            background-color: rgba(0, 0, 0, 0.7);
            border: 3px solid #00ff00;
            border-radius: 10px;
            padding: 10px 20px;
        """)
        top_layout.addWidget(self.rpm_label)
        
        layout.addWidget(top_row)
        
        # Throttle bar with percentage
        throttle_widget = QWidget()
        throttle_layout = QVBoxLayout(throttle_widget)
        throttle_layout.setContentsMargins(0, 0, 0, 0)
        throttle_layout.setSpacing(5)
        
        # Throttle percentage
        self.throttle_percent = QLabel("0%")
        self.throttle_percent.setAlignment(Qt.AlignCenter)
        percent_font = QFont("Arial", 24)
        self.throttle_percent.setFont(percent_font)
        self.throttle_percent.setStyleSheet("""
            color: #00ff00;
            background-color: rgba(0, 0, 0, 0.7);
            border: 2px solid #00ff00;
            border-radius: 5px;
            padding: 5px;
            min-width: 80px;
        """)
        throttle_layout.addWidget(self.throttle_percent, alignment=Qt.AlignCenter)
        
        # Throttle bar
        self.throttle_bar = QProgressBar()
        self.throttle_bar.setRange(0, 100)
        self.throttle_bar.setTextVisible(False)
        self.throttle_bar.setFixedHeight(40)
        self.throttle_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid #00ff00;
                border-radius: 5px;
                background-color: rgba(0, 0, 0, 0.7);
            }
            QProgressBar::chunk {
                background-color: #00ff00;
                border-radius: 3px;
            }
        """)
        throttle_layout.addWidget(self.throttle_bar)
        
        layout.addWidget(throttle_widget)
        
        # Brake bar with percentage
        brake_widget = QWidget()
        brake_layout = QVBoxLayout(brake_widget)
        brake_layout.setContentsMargins(0, 0, 0, 0)
        brake_layout.setSpacing(5)
        
        # Brake percentage
        self.brake_percent = QLabel("0%")
        self.brake_percent.setAlignment(Qt.AlignCenter)
        self.brake_percent.setFont(percent_font)
        self.brake_percent.setStyleSheet("""
            color: #ff0000;
            background-color: rgba(0, 0, 0, 0.7);
            border: 2px solid #ff0000;
            border-radius: 5px;
            padding: 5px;
            min-width: 80px;
        """)
        brake_layout.addWidget(self.brake_percent, alignment=Qt.AlignCenter)
        
        # Brake bar
        self.brake_bar = QProgressBar()
        self.brake_bar.setRange(0, 100)
        self.brake_bar.setTextVisible(False)
        self.brake_bar.setFixedHeight(40)
        self.brake_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid #ff0000;
                border-radius: 5px;
                background-color: rgba(0, 0, 0, 0.7);
            }
            QProgressBar::chunk {
                background-color: #ff0000;
                border-radius: 3px;
            }
        """)
        brake_layout.addWidget(self.brake_bar)
        
        layout.addWidget(brake_widget)
        
        # Throttle/Brake graph
        graph_widget = QWidget()
        graph_layout = QVBoxLayout(graph_widget)
        graph_layout.setContentsMargins(0, 0, 0, 0)
        
        # Create plot widget for throttle/brake history
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setBackground('#2b2b2b')
        self.plot_widget.setFixedHeight(150)
        self.plot_widget.showGrid(x=True, y=True, alpha=0.3)
        self.plot_widget.setLabel('left', '%')
        self.plot_widget.setLabel('bottom', 'Samples ago')
        self.plot_widget.setXRange(-100, 0)  # Show last 100 samples
        
        # Throttle curve (green)
        self.throttle_curve = self.plot_widget.plot(pen=pg.mkPen('#00ff00', width=2))
        
        # Brake curve (red)
        self.brake_curve = self.plot_widget.plot(pen=pg.mkPen('#ff0000', width=2))
        
        graph_layout.addWidget(self.plot_widget)
        layout.addWidget(graph_widget)
        
        # Position slider (by sample index)
        slider_widget = QWidget()
        slider_layout = QHBoxLayout(slider_widget)
        slider_layout.setContentsMargins(0, 0, 0, 0)
        
        self.position_slider = QSlider(Qt.Horizontal)
        self.position_slider.setRange(0, 1000)
        self.position_slider.valueChanged.connect(self.on_slider_changed)
        slider_layout.addWidget(self.position_slider)
        
        self.position_label = QLabel("0 / 0")
        self.position_label.setStyleSheet("color: white; background-color: rgba(0,0,0,0.7); padding: 5px; border-radius: 3px; min-width: 100px;")
        slider_layout.addWidget(self.position_label)
        
        layout.addWidget(slider_widget)
        
        # Playback controls
        controls_widget = QWidget()
        controls_layout = QHBoxLayout(controls_widget)
        controls_layout.setContentsMargins(0, 0, 0, 0)
        
        self.play_btn = QPushButton("▶")
        self.play_btn.setCheckable(True)
        self.play_btn.clicked.connect(self.toggle_playback)
        self.play_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(0, 0, 0, 0.7);
                color: white;
                border: 2px solid #00ff00;
                border-radius: 5px;
                padding: 8px 20px;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: rgba(0, 255, 0, 0.3);
            }
            QPushButton:checked {
                background-color: #00ff00;
                color: black;
            }
        """)
        controls_layout.addWidget(self.play_btn)
        
        self.reset_btn = QPushButton("↺")
        self.reset_btn.clicked.connect(self.reset_position)
        self.reset_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(0, 0, 0, 0.7);
                color: white;
                border: 2px solid #00ff00;
                border-radius: 5px;
                padding: 8px 20px;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: rgba(0, 255, 0, 0.3);
            }
        """)
        controls_layout.addWidget(self.reset_btn)
        
        # Speed control
        self.speed_label_control = QLabel("Speed:")
        self.speed_label_control.setStyleSheet("color: white; background-color: rgba(0,0,0,0.7); padding: 8px; border-radius: 3px;")
        controls_layout.addWidget(self.speed_label_control)
        
        self.speed_combo = QComboBox()
        self.speed_combo.addItems(["1x", "2x", "5x", "10x", "20x", "50x", "100x", "200x", "500x", "1000x"])
        self.speed_combo.setCurrentText("1x")
        self.speed_combo.setStyleSheet("""
            QComboBox {
                background-color: rgba(0, 0, 0, 0.7);
                color: white;
                border: 2px solid #00ff00;
                border-radius: 5px;
                padding: 5px;
                min-width: 60px;
            }
        """)
        controls_layout.addWidget(self.speed_combo)
        
        controls_layout.addStretch()
        layout.addWidget(controls_widget)
        
        self.setLayout(layout)
        self.setFixedSize(800, 600)
    
    def update_button_states(self):
        """Enable/disable buttons based on data availability"""
        has_data = self.reader.sample_count > 0
        self.play_btn.setEnabled(has_data)
        self.reset_btn.setEnabled(has_data)
        self.position_slider.setEnabled(has_data)
    
    def get_playback_speed(self):
        """Get the current playback speed multiplier"""
        speed_text = self.speed_combo.currentText()
        return float(speed_text.replace('x', ''))
    
    def update_frame(self):
        """Update current frame for playback"""
        if not self.play_btn.isChecked() or self.reader.sample_count == 0:
            return
            
        # Move to next frame based on speed
        speed = self.get_playback_speed()
        
        # For high speeds, we can advance multiple frames at once
        # But we need to ensure we don't overshoot
        new_index = self.current_index + int(speed)
        
        if new_index >= self.reader.sample_count:
            # Loop back to start if at end
            self.current_index = 0
            # Optionally stop playback at end (uncomment to stop instead of loop)
            # self.play_btn.setChecked(False)
            # self.play_btn.setText("▶")
            # self.timer.stop()
        else:
            self.current_index = new_index
        
        # Update slider
        if self.reader.sample_count > 1:
            slider_value = int((self.current_index / (self.reader.sample_count - 1)) * 1000)
            self.position_slider.blockSignals(True)
            self.position_slider.setValue(slider_value)
            self.position_slider.blockSignals(False)
        
        self.update_display()
    
    def on_slider_changed(self, value):
        """Handle slider movement"""
        if self.reader.sample_count > 1:
            self.current_index = int((value / 1000.0) * (self.reader.sample_count - 1))
            self.update_display()
    
    def update_display(self):
        """Update all display elements with current values"""
        if self.reader.sample_count == 0:
            return
            
        # Update position label
        self.position_label.setText(f"{self.current_index} / {self.reader.sample_count - 1}")
        
        # Get current values
        throttle = 0
        brake = 0
        speed = 0
        rpm = 0
        gear = 0
        
        # Try different possible channel names
        throttle_keys = ['Throttle Position', 'Throttle Pos']
        brake_keys = ['Brake Pedal Position', 'Brake Pedal Pos']
        speed_keys = ['Ground Speed', 'Ground Speed']
        rpm_keys = ['Engine RPM', 'Engine RPM']
        gear_keys = ['Gear', 'Gear']
        
        for key in throttle_keys:
            if key in self.reader.data and self.current_index < len(self.reader.data[key]):
                throttle = self.reader.data[key][self.current_index]
                break
        
        for key in brake_keys:
            if key in self.reader.data and self.current_index < len(self.reader.data[key]):
                brake = self.reader.data[key][self.current_index]
                break
        
        for key in speed_keys:
            if key in self.reader.data and self.current_index < len(self.reader.data[key]):
                speed = self.reader.data[key][self.current_index]
                break
        
        for key in rpm_keys:
            if key in self.reader.data and self.current_index < len(self.reader.data[key]):
                rpm = self.reader.data[key][self.current_index]
                break
        
        for key in gear_keys:
            if key in self.reader.data and self.current_index < len(self.reader.data[key]):
                gear_val = self.reader.data[key][self.current_index]
                gear = int(gear_val) if not np.isnan(gear_val) else 0
                break
        
        # Update displays
        self.gear_label.setText(str(gear))
        self.speed_label.setText(f"{speed:.0f}")
        self.rpm_label.setText(f"{rpm:.0f} RPM")
        
        # Ensure values are within 0-100 range for bars
        throttle = max(0, min(100, throttle))
        brake = max(0, min(100, brake))
        
        self.throttle_percent.setText(f"{throttle:.0f}%")
        self.throttle_bar.setValue(int(throttle))
        
        self.brake_percent.setText(f"{brake:.0f}%")
        self.brake_bar.setValue(int(brake))
        
        # Update graph with last 100 samples
        if self.current_index > 0:
            start_idx = max(0, self.current_index - 100)
            end_idx = self.current_index + 1
            
            if end_idx > start_idx:
                # X-axis is samples ago (negative values)
                sample_range = np.arange(start_idx - self.current_index, end_idx - self.current_index)
                
                # Throttle data
                for key in throttle_keys:
                    if key in self.reader.data:
                        throttle_data = self.reader.data[key][start_idx:end_idx]
                        self.throttle_curve.setData(sample_range, throttle_data)
                        break
                
                # Brake data
                for key in brake_keys:
                    if key in self.reader.data:
                        brake_data = self.reader.data[key][start_idx:end_idx]
                        self.brake_curve.setData(sample_range, brake_data)
                        break
    
    def toggle_playback(self):
        """Toggle playback on/off"""
        if self.play_btn.isChecked():
            self.play_btn.setText("⏸")
            # Start from beginning if at end
            if self.current_index >= self.reader.sample_count - 1:
                self.current_index = 0
                # Update slider
                if self.reader.sample_count > 1:
                    slider_value = 0
                    self.position_slider.blockSignals(True)
                    self.position_slider.setValue(slider_value)
                    self.position_slider.blockSignals(False)
                self.update_display()
            
            # Start the timer
            self.timer.start()
            print("Playback started")  # Debug output
        else:
            self.play_btn.setText("▶")
            self.timer.stop()
            print("Playback stopped")  # Debug output
    
    def reset_position(self):
        """Reset position to beginning"""
        self.current_index = 0
        self.position_slider.setValue(0)
        self.update_display()
        if self.play_btn.isChecked():
            self.play_btn.setChecked(False)
            self.play_btn.setText("▶")
            self.timer.stop()
    
    def keyPressEvent(self, event):
        """Handle key presses for controls"""
        if event.key() == Qt.Key_Space:
            self.toggle_playback()
        elif event.key() == Qt.Key_Home:
            self.reset_position()
        elif event.key() == Qt.Key_Right:
            if self.reader.sample_count > 0:
                self.current_index = min(self.current_index + 1, self.reader.sample_count - 1)
                if self.reader.sample_count > 1:
                    slider_value = int((self.current_index / (self.reader.sample_count - 1)) * 1000)
                    self.position_slider.setValue(slider_value)
                self.update_display()
        elif event.key() == Qt.Key_Left:
            if self.reader.sample_count > 0:
                self.current_index = max(self.current_index - 1, 0)
                if self.reader.sample_count > 1:
                    slider_value = int((self.current_index / (self.reader.sample_count - 1)) * 1000)
                    self.position_slider.setValue(slider_value)
                self.update_display()
        elif event.key() == Qt.Key_PageUp:
            if self.reader.sample_count > 0:
                self.current_index = min(self.current_index + 10, self.reader.sample_count - 1)
                if self.reader.sample_count > 1:
                    slider_value = int((self.current_index / (self.reader.sample_count - 1)) * 1000)
                    self.position_slider.setValue(slider_value)
                self.update_display()
        elif event.key() == Qt.Key_PageDown:
            if self.reader.sample_count > 0:
                self.current_index = max(self.current_index - 10, 0)
                if self.reader.sample_count > 1:
                    slider_value = int((self.current_index / (self.reader.sample_count - 1)) * 1000)
                    self.position_slider.setValue(slider_value)
                self.update_display()
        elif event.key() == Qt.Key_Escape:
            self.close()


def main():
    if len(sys.argv) < 2:
        print("Usage: python simhub_overlay.py <file.ld or file.csv>")
        print("\nExamples:")
        print("  python simhub_overlay.py AngelAlonso20-03_03-02-26.ld")
        print("  python simhub_overlay.py monzatest.csv")
        return
    
    filename = sys.argv[1]
    
    try:
        app = QApplication(sys.argv)
        
        # Read the data
        reader = MoTeCDataReader(filename)
        
        # Print some info about the loaded data
        print(f"\nLoaded file: {filename}")
        print(f"Sample count: {reader.sample_count}")
        print(f"Channels found: {list(reader.data.keys())}")
        if reader.time_data is not None:
            print(f"Time range: {reader.time_data[0]:.3f} to {reader.time_data[-1]:.3f}")
        
        # Create and show the overlay
        overlay = SimHubOverlay(reader)
        overlay.show()
        
        sys.exit(app.exec_())
    except FileNotFoundError:
        print(f"Error: File '{filename}' not found.")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
