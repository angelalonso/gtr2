#!/usr/bin/env python3
"""
SimHub-style Telemetry Overlay
Visualize throttle, brake, gear, speed, RPM, and steering from MoTeC .ld or .csv files
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
import math


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
            print(f"Time range: {self.time_data[0]:.3f} to {self.time_data[-1]:.3f} seconds")
            
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
        steering = np.zeros_like(t)
        
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
                steering[idx] = 0
            
            # Braking phase (30-40s)
            brake_mask = (lap_t >= 30) & (lap_t < 40)
            if np.any(brake_mask):
                idx = np.where(brake_mask)[0] + start
                brake[idx] = 100 * ((lap_t[brake_mask] - 30) / 10)
                speed[idx] = 200 * (1 - (lap_t[brake_mask] - 30) / 10)
                steering[idx] = 0
            
            # Cornering phase (40-60s)
            corner_mask = (lap_t >= 40) & (lap_t < 60)
            if np.any(corner_mask):
                idx = np.where(corner_mask)[0] + start
                speed[idx] = 80 + 20 * np.sin(2 * np.pi * (lap_t[corner_mask] - 40) / 20)
                throttle[idx] = 30 + 20 * np.sin(2 * np.pi * (lap_t[corner_mask] - 40) / 20 + 1)
                # Simulate steering through corners
                steering[idx] = 30 * np.sin(2 * np.pi * (lap_t[corner_mask] - 40) / 20)
            
            # Acceleration out of corner (60-80s)
            accel2_mask = (lap_t >= 60) & (lap_t < 80)
            if np.any(accel2_mask):
                idx = np.where(accel2_mask)[0] + start
                speed[idx] = 100 + 100 * ((lap_t[accel2_mask] - 60) / 20)
                throttle[idx] = 80 + 20 * (1 - (lap_t[accel2_mask] - 60) / 20)
                rpm[idx] = 6000 + 2000 * ((lap_t[accel2_mask] - 60) / 20)
                steering[idx] = 0
            
            # Braking for next corner (80-90s)
            brake2_mask = (lap_t >= 80) & (lap_t < 90)
            if np.any(brake2_mask):
                idx = np.where(brake2_mask)[0] + start
                brake[idx] = 100 * ((lap_t[brake2_mask] - 80) / 10)
                speed[idx] = 200 * (1 - (lap_t[brake2_mask] - 80) / 10)
                steering[idx] = 0
            
            # Rest of lap...
            other_mask = lap_t >= 90
            if np.any(other_mask):
                idx = np.where(other_mask)[0] + start
                speed[idx] = 180
                throttle[idx] = 60
                rpm[idx] = 7000
                steering[idx] = 0
        
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
        steering += np.random.normal(0, 0.5, self.sample_count)
        
        self.data = {
            'Throttle Position': throttle,
            'Brake Pedal Position': brake,
            'Ground Speed': speed,
            'Engine RPM': rpm,
            'Gear': gear.astype(float),
            'Steering Wheel Angle': steering
        }
        self.time_data = t


class SteeringWheel(QWidget):
    """Simple widget to display steering wheel angle (0° = straight up)"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.angle = 0
        self.setMinimumSize(120, 120)
        self.setMaximumSize(150, 150)
        
    def set_angle(self, angle):
        """Set the current steering angle in degrees (0° = straight up)"""
        self.angle = angle
        self.update()  # Trigger a repaint
    
    def paintEvent(self, event):
        # Create painter for this widget only
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Get widget dimensions (as integers)
        width = self.width()
        height = self.height()
        center_x = width // 2
        center_y = height // 2
        radius = min(width, height) // 3  # Use integer division
        
        # Draw background circle
        painter.setPen(QPen(QColor('#00ff00'), 2))
        painter.setBrush(QBrush(QColor(0, 0, 0, 200)))
        painter.drawEllipse(center_x - radius, center_y - radius, radius * 2, radius * 2)
        
        # Draw reference line (straight up) - dashed
        painter.setPen(QPen(QColor('#00ff00'), 1, Qt.DashLine))
        painter.drawLine(center_x, center_y - radius, center_x, center_y + radius)
        
        # Draw steering line (rotated, starting from straight up)
        painter.save()
        painter.translate(center_x, center_y)
        painter.rotate(self.angle)  # Apply steering angle directly
        
        painter.setPen(QPen(QColor('#ffffff'), 3))
        painter.drawLine(0, 0, 0, -(radius - 5))  # Draw upward line
        
        painter.restore()
        
        # Draw angle text
        painter.setPen(QPen(QColor('#00ff00')))
        painter.setFont(QFont("Arial", 10))
        angle_text = f"{self.angle:.0f}°"
        text_width = painter.fontMetrics().horizontalAdvance(angle_text)
        painter.drawText(center_x - text_width // 2, center_y + radius + 15, angle_text)
        
        # End painting
        painter.end()


class SimHubOverlay(QWidget):
    """SimHub-style telemetry overlay widget"""
    
    def __init__(self, reader, parent=None):
        super().__init__(parent)
        self.reader = reader
        self.current_index = 0  # Current sample index
        
        # Playback speed control - extended for slower speeds
        self.frame_delay = 100  # milliseconds between frames (default slower)
        self.frames_per_step = 1  # Number of frames to advance per timer tick
        self.frame_skip_counter = 0  # Counter for frame skipping
        self.frame_skip_mod = 1  # Skip frames (1 = no skip, 2 = show every 2nd frame, etc.)
        
        self.setup_ui()
        
        # Set window flags for overlay style
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        # Timer for playback
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)
        self.update_timer_interval()
        
        # Enable/disable buttons based on data availability
        self.update_button_states()
        
        # Initial display update
        self.update_display()
    
    def setup_ui(self):
        # Main layout
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Top row: Gear, Speed, RPM
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
        
        # Middle row: Steering wheel and bars
        middle_row = QWidget()
        middle_layout = QHBoxLayout(middle_row)
        middle_layout.setContentsMargins(0, 0, 0, 0)
        middle_layout.setSpacing(20)
        
        # Steering wheel
        self.steering_wheel = SteeringWheel()
        middle_layout.addWidget(self.steering_wheel)
        
        # Bars container
        bars_container = QWidget()
        bars_layout = QVBoxLayout(bars_container)
        bars_layout.setContentsMargins(0, 0, 0, 0)
        bars_layout.setSpacing(15)
        
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
        
        bars_layout.addWidget(throttle_widget)
        
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
        
        bars_layout.addWidget(brake_widget)
        
        middle_layout.addWidget(bars_container)
        middle_layout.setStretchFactor(bars_container, 1)
        
        layout.addWidget(middle_row)
        
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
        self.plot_widget.setLabel('bottom', 'Time (s)')
        
        # Throttle curve (green)
        self.throttle_curve = self.plot_widget.plot(pen=pg.mkPen('#00ff00', width=2))
        
        # Brake curve (red)
        self.brake_curve = self.plot_widget.plot(pen=pg.mkPen('#ff0000', width=2))
        
        graph_layout.addWidget(self.plot_widget)
        layout.addWidget(graph_widget)
        
        # Position slider (by time)
        slider_widget = QWidget()
        slider_layout = QHBoxLayout(slider_widget)
        slider_layout.setContentsMargins(0, 0, 0, 0)
        
        self.position_slider = QSlider(Qt.Horizontal)
        self.position_slider.setRange(0, 1000)
        self.position_slider.valueChanged.connect(self.on_slider_changed)
        slider_layout.addWidget(self.position_slider)
        
        # Time display (minutes:seconds)
        self.time_label = QLabel("00:00.0")
        self.time_label.setStyleSheet("color: white; background-color: rgba(0,0,0,0.7); padding: 5px; border-radius: 3px; min-width: 80px;")
        self.time_label.setAlignment(Qt.AlignCenter)
        slider_layout.addWidget(self.time_label)
        
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
        
        # Speed control panel
        speed_panel = QWidget()
        speed_layout = QHBoxLayout(speed_panel)
        speed_layout.setContentsMargins(0, 0, 0, 0)
        speed_layout.setSpacing(10)
        
        # Frame delay control (with wider range)
        delay_label = QLabel("Delay:")
        delay_label.setStyleSheet("color: white; background-color: rgba(0,0,0,0.7); padding: 8px; border-radius: 3px;")
        speed_layout.addWidget(delay_label)
        
        self.delay_spin = QSpinBox()
        self.delay_spin.setRange(1, 2000)  # Up to 2 seconds between frames
        self.delay_spin.setValue(self.frame_delay)
        self.delay_spin.setSuffix(" ms")
        self.delay_spin.valueChanged.connect(self.on_delay_changed)
        self.delay_spin.setStyleSheet("""
            QSpinBox {
                background-color: rgba(0, 0, 0, 0.7);
                color: white;
                border: 2px solid #00ff00;
                border-radius: 5px;
                padding: 5px;
                min-width: 80px;
            }
        """)
        speed_layout.addWidget(self.delay_spin)
        
        # Frames per step control
        step_label = QLabel("Step:")
        step_label.setStyleSheet("color: white; background-color: rgba(0,0,0,0.7); padding: 8px; border-radius: 3px;")
        speed_layout.addWidget(step_label)
        
        self.step_spin = QSpinBox()
        self.step_spin.setRange(1, 100)
        self.step_spin.setValue(self.frames_per_step)
        self.step_spin.valueChanged.connect(self.on_step_changed)
        self.step_spin.setStyleSheet("""
            QSpinBox {
                background-color: rgba(0, 0, 0, 0.7);
                color: white;
                border: 2px solid #00ff00;
                border-radius: 5px;
                padding: 5px;
                min-width: 60px;
            }
        """)
        speed_layout.addWidget(self.step_spin)
        
        # Frame skip control (for very slow playback)
        skip_label = QLabel("Skip:")
        skip_label.setStyleSheet("color: white; background-color: rgba(0,0,0,0.7); padding: 8px; border-radius: 3px;")
        speed_layout.addWidget(skip_label)
        
        self.skip_spin = QSpinBox()
        self.skip_spin.setRange(1, 100)
        self.skip_spin.setValue(self.frame_skip_mod)
        self.skip_spin.setToolTip("Show every Nth frame (1 = all frames, 2 = every other frame, etc.)")
        self.skip_spin.valueChanged.connect(self.on_skip_changed)
        self.skip_spin.setStyleSheet("""
            QSpinBox {
                background-color: rgba(0, 0, 0, 0.7);
                color: white;
                border: 2px solid #00ff00;
                border-radius: 5px;
                padding: 5px;
                min-width: 60px;
            }
        """)
        speed_layout.addWidget(self.skip_spin)
        
        # Estimated FPS display
        self.fps_label = QLabel("~10 FPS")
        self.fps_label.setStyleSheet("color: #00ff00; background-color: rgba(0,0,0,0.7); padding: 8px; border-radius: 3px; min-width: 80px;")
        self.fps_label.setAlignment(Qt.AlignCenter)
        speed_layout.addWidget(self.fps_label)
        
        controls_layout.addWidget(speed_panel)
        controls_layout.addStretch()
        layout.addWidget(controls_widget)
        
        self.setLayout(layout)
        self.setFixedSize(1000, 750)  # Wider for new controls
        
        # Update FPS display
        self.update_fps_display()
    
    def update_button_states(self):
        """Enable/disable buttons based on data availability"""
        has_data = self.reader.sample_count > 0
        self.play_btn.setEnabled(has_data)
        self.reset_btn.setEnabled(has_data)
        self.position_slider.setEnabled(has_data)
    
    def update_timer_interval(self):
        """Update timer interval based on frame delay"""
        self.timer.setInterval(self.frame_delay)
    
    def update_fps_display(self):
        """Update the estimated FPS display"""
        if self.frame_delay > 0:
            base_fps = 1000.0 / self.frame_delay
            # Effective FPS is base_fps divided by skip factor (since we skip frames)
            effective_fps = base_fps / self.frame_skip_mod
            self.fps_label.setText(f"~{effective_fps:.1f} FPS")
    
    def on_delay_changed(self, value):
        """Handle frame delay change"""
        self.frame_delay = value
        if self.play_btn.isChecked():
            self.timer.setInterval(self.frame_delay)
        self.update_fps_display()
    
    def on_step_changed(self, value):
        """Handle frames per step change"""
        self.frames_per_step = value
    
    def on_skip_changed(self, value):
        """Handle frame skip change"""
        self.frame_skip_mod = value
        self.frame_skip_counter = 0  # Reset counter
        self.update_fps_display()
    
    def format_time(self, seconds):
        """Format time as MM:SS.t"""
        minutes = int(seconds // 60)
        secs = seconds % 60
        return f"{minutes:02d}:{secs:04.1f}"
    
    def update_frame(self):
        """Update current frame for playback with frame skipping"""
        if not self.play_btn.isChecked() or self.reader.sample_count == 0:
            return
        
        # Frame skipping logic
        self.frame_skip_counter += 1
        if self.frame_skip_counter < self.frame_skip_mod:
            return  # Skip this frame
        
        self.frame_skip_counter = 0  # Reset counter
        
        # Advance by configured number of frames
        new_index = self.current_index + self.frames_per_step
        
        if new_index >= self.reader.sample_count:
            # Loop back to start
            self.current_index = 0
        else:
            self.current_index = new_index
        
        # Update slider
        if self.reader.sample_count > 1:
            current_time = self.reader.time_data[self.current_index]
            slider_value = int((current_time / self.reader.time_data[-1]) * 1000)
            self.position_slider.blockSignals(True)
            self.position_slider.setValue(slider_value)
            self.position_slider.blockSignals(False)
        
        self.update_display()
    
    def on_slider_changed(self, value):
        """Handle slider movement"""
        if self.reader.sample_count > 1:
            # Convert slider value to time
            target_time = (value / 1000.0) * self.reader.time_data[-1]
            # Find closest index to that time
            self.current_index = np.argmin(np.abs(self.reader.time_data - target_time))
            self.update_display()
    
    def update_display(self):
        """Update all display elements with current values"""
        if self.reader.sample_count == 0:
            return
        
        # Get current time
        if self.current_index < len(self.reader.time_data):
            current_time = self.reader.time_data[self.current_index]
            self.time_label.setText(self.format_time(current_time))
        
        # Get current values
        throttle = 0
        brake = 0
        speed = 0
        rpm = 0
        gear = 0
        steering = 0
        
        # Try different possible channel names
        throttle_keys = ['Throttle Position', 'Throttle Pos']
        brake_keys = ['Brake Pedal Position', 'Brake Pedal Pos']
        speed_keys = ['Ground Speed', 'Ground Speed']
        rpm_keys = ['Engine RPM', 'Engine RPM']
        gear_keys = ['Gear', 'Gear']
        steering_keys = ['Steering Wheel Angle', 'Steering Wheel Angle', 'Steering']
        
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
        
        for key in steering_keys:
            if key in self.reader.data and self.current_index < len(self.reader.data[key]):
                steering = self.reader.data[key][self.current_index]
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
        
        # Update steering wheel (0° = straight up)
        self.steering_wheel.set_angle(steering)
        
        # Update graph with last 10 seconds of data
        if self.current_index > 0 and len(self.reader.time_data) > 0:
            current_time = self.reader.time_data[self.current_index]
            start_time = max(0, current_time - 10)
            start_idx = np.searchsorted(self.reader.time_data, start_time)
            end_idx = self.current_index + 1
            
            if end_idx > start_idx:
                # X-axis is time relative to current
                time_range = self.reader.time_data[start_idx:end_idx] - current_time
                
                # Throttle data
                for key in throttle_keys:
                    if key in self.reader.data:
                        throttle_data = self.reader.data[key][start_idx:end_idx]
                        self.throttle_curve.setData(time_range, throttle_data)
                        break
                
                # Brake data
                for key in brake_keys:
                    if key in self.reader.data:
                        brake_data = self.reader.data[key][start_idx:end_idx]
                        self.brake_curve.setData(time_range, brake_data)
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
            
            # Reset frame skip counter
            self.frame_skip_counter = 0
            
            # Start the timer
            self.timer.start()
            print(f"Playback started: delay={self.frame_delay}ms, step={self.frames_per_step}, skip={self.frame_skip_mod}")
        else:
            self.play_btn.setText("▶")
            self.timer.stop()
            print("Playback stopped")
    
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
                # Move forward 1 second
                current_time = self.reader.time_data[self.current_index]
                target_time = min(current_time + 1.0, self.reader.time_data[-1])
                self.current_index = np.argmin(np.abs(self.reader.time_data - target_time))
                if self.reader.sample_count > 1:
                    slider_value = int((self.reader.time_data[self.current_index] / self.reader.time_data[-1]) * 1000)
                    self.position_slider.setValue(slider_value)
                self.update_display()
        elif event.key() == Qt.Key_Left:
            if self.reader.sample_count > 0:
                # Move backward 1 second
                current_time = self.reader.time_data[self.current_index]
                target_time = max(current_time - 1.0, 0)
                self.current_index = np.argmin(np.abs(self.reader.time_data - target_time))
                if self.reader.sample_count > 1:
                    slider_value = int((self.reader.time_data[self.current_index] / self.reader.time_data[-1]) * 1000)
                    self.position_slider.setValue(slider_value)
                self.update_display()
        elif event.key() == Qt.Key_PageUp:
            if self.reader.sample_count > 0:
                # Move forward 10 seconds
                current_time = self.reader.time_data[self.current_index]
                target_time = min(current_time + 10.0, self.reader.time_data[-1])
                self.current_index = np.argmin(np.abs(self.reader.time_data - target_time))
                if self.reader.sample_count > 1:
                    slider_value = int((self.reader.time_data[self.current_index] / self.reader.time_data[-1]) * 1000)
                    self.position_slider.setValue(slider_value)
                self.update_display()
        elif event.key() == Qt.Key_PageDown:
            if self.reader.sample_count > 0:
                # Move backward 10 seconds
                current_time = self.reader.time_data[self.current_index]
                target_time = max(current_time - 10.0, 0)
                self.current_index = np.argmin(np.abs(self.reader.time_data - target_time))
                if self.reader.sample_count > 1:
                    slider_value = int((self.reader.time_data[self.current_index] / self.reader.time_data[-1]) * 1000)
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
            print(f"Time range: {reader.time_data[0]:.3f} to {reader.time_data[-1]:.3f} seconds")
        
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
