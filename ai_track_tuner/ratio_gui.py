"""
Ratio Calculator GUI for AIW Ratio Editor - Data Collection Focus
Now opens graph in a separate window
"""

from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
import cfg_manage
import os
from ratio_calc import LapTimes, TimeConverter, HistoricDataStore
from ratio_graph import RatioGraphWindow


class ConfigWindow(QDialog):
    """Pop-up window showing configuration and CSV settings"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Configuration & CSV Settings")
        self.setMinimumWidth(600)
        self.setMinimumHeight(200)
        
        self.setStyleSheet("""
            QDialog {
                background-color: #2b2b2b;
            }
            QLabel {
                color: white;
                font-size: 12px;
            }
            QGroupBox {
                color: #4CAF50;
                font-weight: bold;
                border: 2px solid #555;
                border-radius: 5px;
                margin-top: 8px;
                padding-top: 8px;
                font-size: 13px;
            }
            QLineEdit {
                background-color: #3c3c3c;
                color: white;
                border: 1px solid #4CAF50;
                border-radius: 3px;
                padding: 5px;
                font-size: 12px;
                min-height: 25px;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(20, 20, 20, 20)
        
        csv_group = QGroupBox("Historic Data CSV")
        csv_layout = QVBoxLayout(csv_group)
        
        csv_path_layout = QHBoxLayout()
        csv_path_layout.addWidget(QLabel("File path:"))
        self.csv_path = QLineEdit()
        self.csv_path.setReadOnly(True)
        csv_path_layout.addWidget(self.csv_path)
        
        self.csv_browse = QPushButton("Browse")
        self.csv_browse.setFixedWidth(100)
        self.csv_browse.setFixedHeight(30)
        csv_path_layout.addWidget(self.csv_browse)
        
        csv_layout.addLayout(csv_path_layout)
        layout.addWidget(csv_group)
        
        actions_group = QGroupBox("Actions")
        actions_layout = QHBoxLayout(actions_group)
        
        self.save_btn = QPushButton("Save Configuration to cfg.yml")
        self.save_btn.setFixedHeight(40)
        self.save_btn.setStyleSheet("background-color: #4CAF50; font-weight: bold;")
        actions_layout.addWidget(self.save_btn)
        
        layout.addWidget(actions_group)
        
        close_btn = QPushButton("Close")
        close_btn.setFixedHeight(40)
        close_btn.setFixedWidth(200)
        close_btn.clicked.connect(self.accept)
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 3px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_layout.addWidget(close_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
    
    def update_from_config(self, csv_path):
        self.csv_path.setText(csv_path)


class RatioCalculatorDialog(QDialog):
    """Main dialog for data collection - opens graph in separate window"""
    
    def __init__(self, parent=None, track_name="", current_qual=1.0, current_race=1.0):
        super().__init__(parent)
        self.track_name = track_name
        self.current_qual = current_qual
        self.current_race = current_race
        self.new_qual = current_qual
        self.new_race = current_race
        
        # Store current lap times
        self.qual_times = LapTimes()
        self.race_times = LapTimes()
        
        # Load configuration
        self.config_csv = cfg_manage.get_historic_csv()
        self.data_store = HistoricDataStore(self.config_csv)
        
        # Cache for historic points
        self.qual_points_cache = []
        self.race_points_cache = []
        
        self.config_window = None
        self.graph_window = None
        
        self.setup_ui()
        self.setup_connections()
        self.load_historic_data()
        
    def setup_ui(self):
        self.setWindowTitle(f"Data Collection - {self.track_name}")
        self.setModal(True)
        self.setMinimumWidth(1000)
        self.setMinimumHeight(700)
        
        self.setStyleSheet("""
            QDialog {
                background-color: #2b2b2b;
            }
            QLabel {
                color: white;
                font-size: 11px;
            }
            QGroupBox {
                color: #4CAF50;
                font-weight: bold;
                border: 2px solid #555;
                border-radius: 5px;
                margin-top: 8px;
                padding-top: 8px;
                font-size: 12px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 3px;
                padding: 6px;
                font-weight: bold;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QSpinBox, QDoubleSpinBox {
                background-color: #3c3c3c;
                color: white;
                border: 1px solid #4CAF50;
                border-radius: 3px;
                padding: 2px;
                font-size: 11px;
                min-height: 20px;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(15, 15, 15, 15)
        
        # Top info bar
        info_bar = QWidget()
        info_bar.setStyleSheet("background-color: #3c3c3c; border-radius: 3px; padding: 5px;")
        info_layout = QHBoxLayout(info_bar)
        info_layout.setContentsMargins(10, 5, 10, 5)
        
        track_label = QLabel(f"<b>Track:</b> {self.track_name}")
        track_label.setStyleSheet("color: #FFA500; font-size: 12px;")
        info_layout.addWidget(track_label)
        
        info_layout.addSpacing(20)
        
        info_layout.addWidget(QLabel("<b>Current Ratios:</b>"))
        
        qual_info = QLabel(f"Qual: {self.current_qual:.6f}")
        qual_info.setStyleSheet("color: #9C27B0;")
        info_layout.addWidget(qual_info)
        
        race_info = QLabel(f"Race: {self.current_race:.6f}")
        race_info.setStyleSheet("color: #9C27B0;")
        info_layout.addWidget(race_info)
        
        # Stats label for historic points
        self.historic_stats = QLabel("")
        self.historic_stats.setStyleSheet("color: #4CAF50; font-size: 11px;")
        info_layout.addWidget(self.historic_stats)
        
        info_layout.addStretch()
        
        layout.addWidget(info_bar)
        
        # Button to open graph window
        graph_btn_widget = QWidget()
        graph_btn_layout = QHBoxLayout(graph_btn_widget)
        graph_btn_layout.setContentsMargins(0, 5, 0, 10)
        
        self.open_graph_btn = QPushButton("📊 OPEN GRAPH ANALYSIS WINDOW")
        self.open_graph_btn.setToolTip("Open a separate window for graph analysis and curve fitting")
        self.open_graph_btn.setFixedHeight(50)
        self.open_graph_btn.setCursor(Qt.PointingHandCursor)
        self.open_graph_btn.setStyleSheet("""
            QPushButton {
                background-color: #9C27B0;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #7B1FA2;
            }
        """)
        graph_btn_layout.addWidget(self.open_graph_btn)
        graph_btn_layout.addStretch()
        
        layout.addWidget(graph_btn_widget)
        
        # Input section
        input_group = QGroupBox("Enter New Lap Times")
        input_group.setStyleSheet("""
            QGroupBox {
                color: #FFA500;
                font-size: 14px;
                border: 2px solid #FFA500;
            }
        """)
        input_layout = QGridLayout(input_group)
        input_layout.setVerticalSpacing(8)
        input_layout.setHorizontalSpacing(12)
        
        input_layout.addWidget(QLabel(""), 0, 0)
        input_layout.addWidget(QLabel("Minutes"), 0, 1)
        input_layout.addWidget(QLabel("Seconds"), 0, 2)
        input_layout.addWidget(QLabel("Milliseconds"), 0, 3)
        input_layout.addWidget(QLabel("Total"), 0, 4)
        
        row = 1
        
        # Qualifying Ratio
        input_layout.addWidget(QLabel("<b>Qual Ratio:</b>"), row, 0)
        self.qual_ratio_spin = QDoubleSpinBox()
        self.qual_ratio_spin.setRange(0.1, 10.0)
        self.qual_ratio_spin.setDecimals(6)
        self.qual_ratio_spin.setSingleStep(0.1)
        self.qual_ratio_spin.setValue(self.current_qual)
        self.qual_ratio_spin.setFixedHeight(24)
        self.qual_ratio_spin.setFixedWidth(100)
        input_layout.addWidget(self.qual_ratio_spin, row, 1, 1, 3)
        input_layout.addWidget(QLabel("(current ratio)"), row, 4)
        row += 1
        
        # Qualifying Best AI
        input_layout.addWidget(QLabel("Qual Best AI:"), row, 0)
        self.qual_best_min = self.create_spinbox(0, 99, 70)
        input_layout.addWidget(self.qual_best_min, row, 1)
        self.qual_best_sec = self.create_spinbox(0, 59, 70)
        input_layout.addWidget(self.qual_best_sec, row, 2)
        self.qual_best_ms = self.create_spinbox(0, 999, 70)
        self.qual_best_ms.setSingleStep(10)
        input_layout.addWidget(self.qual_best_ms, row, 3)
        self.qual_best_total = QLabel("0.000s")
        self.qual_best_total.setStyleSheet("color: #4CAF50; font-weight: bold;")
        input_layout.addWidget(self.qual_best_total, row, 4)
        row += 1
        
        # Qualifying Worst AI
        input_layout.addWidget(QLabel("Qual Worst AI:"), row, 0)
        self.qual_worst_min = self.create_spinbox(0, 99, 70)
        input_layout.addWidget(self.qual_worst_min, row, 1)
        self.qual_worst_sec = self.create_spinbox(0, 59, 70)
        input_layout.addWidget(self.qual_worst_sec, row, 2)
        self.qual_worst_ms = self.create_spinbox(0, 999, 70)
        self.qual_worst_ms.setSingleStep(10)
        input_layout.addWidget(self.qual_worst_ms, row, 3)
        self.qual_worst_total = QLabel("0.000s")
        self.qual_worst_total.setStyleSheet("color: #f44336; font-weight: bold;")
        input_layout.addWidget(self.qual_worst_total, row, 4)
        row += 1
        
        # Qualifying User
        user_label = QLabel("Qual User:")
        user_label.setStyleSheet("color: #888;")
        input_layout.addWidget(user_label, row, 0)
        self.qual_user_min = self.create_spinbox(0, 99, 70)
        input_layout.addWidget(self.qual_user_min, row, 1)
        self.qual_user_sec = self.create_spinbox(0, 59, 70)
        input_layout.addWidget(self.qual_user_sec, row, 2)
        self.qual_user_ms = self.create_spinbox(0, 999, 70)
        self.qual_user_ms.setSingleStep(10)
        input_layout.addWidget(self.qual_user_ms, row, 3)
        self.qual_user_total = QLabel("0.000s")
        self.qual_user_total.setStyleSheet("color: #888;")
        input_layout.addWidget(self.qual_user_total, row, 4)
        row += 1
        
        # Separator
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        line.setStyleSheet("background-color: #555;")
        input_layout.addWidget(line, row, 0, 1, 5)
        row += 1
        
        # Race Ratio
        input_layout.addWidget(QLabel("<b>Race Ratio:</b>"), row, 0)
        self.race_ratio_spin = QDoubleSpinBox()
        self.race_ratio_spin.setRange(0.1, 10.0)
        self.race_ratio_spin.setDecimals(6)
        self.race_ratio_spin.setSingleStep(0.1)
        self.race_ratio_spin.setValue(self.current_race)
        self.race_ratio_spin.setFixedHeight(24)
        self.race_ratio_spin.setFixedWidth(100)
        input_layout.addWidget(self.race_ratio_spin, row, 1, 1, 3)
        input_layout.addWidget(QLabel("(current ratio)"), row, 4)
        row += 1
        
        # Race Best AI
        race_best_label = QLabel("Race Best AI:")
        race_best_label.setStyleSheet("color: #888;")
        input_layout.addWidget(race_best_label, row, 0)
        self.race_best_min = self.create_spinbox(0, 99, 70)
        input_layout.addWidget(self.race_best_min, row, 1)
        self.race_best_sec = self.create_spinbox(0, 59, 70)
        input_layout.addWidget(self.race_best_sec, row, 2)
        self.race_best_ms = self.create_spinbox(0, 999, 70)
        self.race_best_ms.setSingleStep(10)
        input_layout.addWidget(self.race_best_ms, row, 3)
        self.race_best_total = QLabel("0.000s")
        self.race_best_total.setStyleSheet("color: #888;")
        input_layout.addWidget(self.race_best_total, row, 4)
        row += 1
        
        # Race Worst AI
        race_worst_label = QLabel("Race Worst AI:")
        race_worst_label.setStyleSheet("color: #888;")
        input_layout.addWidget(race_worst_label, row, 0)
        self.race_worst_min = self.create_spinbox(0, 99, 70)
        input_layout.addWidget(self.race_worst_min, row, 1)
        self.race_worst_sec = self.create_spinbox(0, 59, 70)
        input_layout.addWidget(self.race_worst_sec, row, 2)
        self.race_worst_ms = self.create_spinbox(0, 999, 70)
        self.race_worst_ms.setSingleStep(10)
        input_layout.addWidget(self.race_worst_ms, row, 3)
        self.race_worst_total = QLabel("0.000s")
        self.race_worst_total.setStyleSheet("color: #888;")
        input_layout.addWidget(self.race_worst_total, row, 4)
        row += 1
        
        # Race User
        race_user_label = QLabel("Race User:")
        race_user_label.setStyleSheet("color: #888;")
        input_layout.addWidget(race_user_label, row, 0)
        self.race_user_min = self.create_spinbox(0, 99, 70)
        input_layout.addWidget(self.race_user_min, row, 1)
        self.race_user_sec = self.create_spinbox(0, 59, 70)
        input_layout.addWidget(self.race_user_sec, row, 2)
        self.race_user_ms = self.create_spinbox(0, 999, 70)
        self.race_user_ms.setSingleStep(10)
        input_layout.addWidget(self.race_user_ms, row, 3)
        self.race_user_total = QLabel("0.000s")
        self.race_user_total.setStyleSheet("color: #888;")
        input_layout.addWidget(self.race_user_total, row, 4)
        
        layout.addWidget(input_group)
        
        # Button bar
        button_bar = QWidget()
        button_layout = QHBoxLayout(button_bar)
        button_layout.setSpacing(10)
        
        self.calc_btn = QPushButton("CALCULATE & SAVE")
        self.calc_btn.setToolTip("Save data to CSV and keep current ratios")
        self.calc_btn.setFixedHeight(50)
        self.calc_btn.setFixedWidth(200)
        self.calc_btn.setCursor(Qt.PointingHandCursor)
        self.calc_btn.setStyleSheet("background-color: #9C27B0; font-size: 14px;")
        button_layout.addWidget(self.calc_btn)
        
        self.save_only_btn = QPushButton("SAVE ONLY")
        self.save_only_btn.setToolTip("Save lap times to CSV without changing ratios")
        self.save_only_btn.setFixedHeight(50)
        self.save_only_btn.setFixedWidth(150)
        self.save_only_btn.setCursor(Qt.PointingHandCursor)
        self.save_only_btn.setStyleSheet("background-color: #2196F3; font-size: 14px;")
        button_layout.addWidget(self.save_only_btn)
        
        button_layout.addStretch()
        
        self.config_btn = QPushButton("Configuration & CSV")
        self.config_btn.setFixedHeight(35)
        self.config_btn.setFixedWidth(150)
        self.config_btn.setCursor(Qt.PointingHandCursor)
        self.config_btn.setStyleSheet("background-color: #9C27B0; font-size: 11px;")
        button_layout.addWidget(self.config_btn)
        
        self.apply_btn = QPushButton("APPLY RATIOS")
        self.apply_btn.setFixedHeight(50)
        self.apply_btn.setFixedWidth(200)
        self.apply_btn.setCursor(Qt.PointingHandCursor)
        self.apply_btn.setStyleSheet("background-color: #4CAF50; font-size: 14px;")
        button_layout.addWidget(self.apply_btn)
        
        self.cancel_btn = QPushButton("CANCEL")
        self.cancel_btn.setFixedHeight(50)
        self.cancel_btn.setFixedWidth(200)
        self.cancel_btn.setCursor(Qt.PointingHandCursor)
        self.cancel_btn.setStyleSheet("background-color: #f44336; font-size: 14px;")
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)
        
        layout.addWidget(button_bar)
        
        # Status label
        self.status_label = QLabel("")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("color: #888; font-style: italic;")
        layout.addWidget(self.status_label)
        
        # Initially disable calculate buttons until we have data
        self.calc_btn.setEnabled(False)
        self.save_only_btn.setEnabled(False)
        self.apply_btn.setEnabled(False)
    
    def create_spinbox(self, min_val, max_val, width):
        spin = QSpinBox()
        spin.setRange(min_val, max_val)
        spin.setValue(0)
        spin.setFixedHeight(24)
        spin.setFixedWidth(width)
        spin.setAlignment(Qt.AlignRight)
        return spin
    
    def get_time_value(self, min_spin, sec_spin, ms_spin):
        return min_spin.value() * 60 + sec_spin.value() + ms_spin.value() / 1000.0
    
    def update_qual_totals(self):
        best = self.get_time_value(self.qual_best_min, self.qual_best_sec, self.qual_best_ms)
        worst = self.get_time_value(self.qual_worst_min, self.qual_worst_sec, self.qual_worst_ms)
        user = self.get_time_value(self.qual_user_min, self.qual_user_sec, self.qual_user_ms)
        
        self.qual_best_total.setText(f"{best:.3f}s")
        self.qual_worst_total.setText(f"{worst:.3f}s")
        self.qual_user_total.setText(f"{user:.3f}s")
        
        self.check_data_available()
        self.update_graph_data()
    
    def update_race_totals(self):
        best = self.get_time_value(self.race_best_min, self.race_best_sec, self.race_best_ms)
        worst = self.get_time_value(self.race_worst_min, self.race_worst_sec, self.race_worst_ms)
        user = self.get_time_value(self.race_user_min, self.race_user_sec, self.race_user_ms)
        
        self.race_best_total.setText(f"{best:.3f}s")
        self.race_worst_total.setText(f"{worst:.3f}s")
        self.race_user_total.setText(f"{user:.3f}s")
        
        self.check_data_available()
        self.update_graph_data()
    
    def check_data_available(self):
        qual_has_data = (self.get_time_value(self.qual_best_min, self.qual_best_sec, self.qual_best_ms) > 0 and
                         self.get_time_value(self.qual_worst_min, self.qual_worst_sec, self.qual_worst_ms) > 0)
        
        race_has_data = (self.get_time_value(self.race_best_min, self.race_best_sec, self.race_best_ms) > 0 and
                         self.get_time_value(self.race_worst_min, self.race_worst_sec, self.race_worst_ms) > 0)
        
        has_data = qual_has_data or race_has_data
        self.calc_btn.setEnabled(has_data)
        self.save_only_btn.setEnabled(has_data)
    
    def setup_connections(self):
        # Qualifying connections
        self.qual_ratio_spin.valueChanged.connect(self.update_graph_data)
        self.qual_best_min.valueChanged.connect(self.update_qual_totals)
        self.qual_best_sec.valueChanged.connect(self.update_qual_totals)
        self.qual_best_ms.valueChanged.connect(self.update_qual_totals)
        self.qual_worst_min.valueChanged.connect(self.update_qual_totals)
        self.qual_worst_sec.valueChanged.connect(self.update_qual_totals)
        self.qual_worst_ms.valueChanged.connect(self.update_qual_totals)
        self.qual_user_min.valueChanged.connect(self.update_qual_totals)
        self.qual_user_sec.valueChanged.connect(self.update_qual_totals)
        self.qual_user_ms.valueChanged.connect(self.update_qual_totals)
        
        # Race connections
        self.race_ratio_spin.valueChanged.connect(self.update_graph_data)
        self.race_best_min.valueChanged.connect(self.update_race_totals)
        self.race_best_sec.valueChanged.connect(self.update_race_totals)
        self.race_best_ms.valueChanged.connect(self.update_race_totals)
        self.race_worst_min.valueChanged.connect(self.update_race_totals)
        self.race_worst_sec.valueChanged.connect(self.update_race_totals)
        self.race_worst_ms.valueChanged.connect(self.update_race_totals)
        self.race_user_min.valueChanged.connect(self.update_race_totals)
        self.race_user_sec.valueChanged.connect(self.update_race_totals)
        self.race_user_ms.valueChanged.connect(self.update_race_totals)
        
        # Button connections
        self.open_graph_btn.clicked.connect(self.open_graph_window)
        self.calc_btn.clicked.connect(self.calculate_and_save)
        self.save_only_btn.clicked.connect(self.save_only)
        self.config_btn.clicked.connect(self.show_config_window)
        self.apply_btn.clicked.connect(self.accept)
    
    def update_graph_data(self):
        """Update the graph window with current data"""
        if not self.graph_window or not self.graph_window.isVisible():
            return
        
        # Get current qualifying data
        qual_ratio = self.qual_ratio_spin.value()
        qual_best = self.get_time_value(self.qual_best_min, self.qual_best_sec, self.qual_best_ms)
        qual_worst = self.get_time_value(self.qual_worst_min, self.qual_worst_sec, self.qual_worst_ms)
        qual_user = self.get_time_value(self.qual_user_min, self.qual_user_sec, self.qual_user_ms)
        
        # Get current race data
        race_ratio = self.race_ratio_spin.value()
        race_best = self.get_time_value(self.race_best_min, self.race_best_sec, self.race_best_ms)
        race_worst = self.get_time_value(self.race_worst_min, self.race_worst_sec, self.race_worst_ms)
        race_user = self.get_time_value(self.race_user_min, self.race_user_sec, self.race_user_ms)
        
        # Determine which times to show
        if qual_best > 0 and qual_worst > 0:
            current_times = LapTimes(qual_best, qual_worst, qual_user, qual_ratio)
            self.graph_window.set_data(
                self.qual_points_cache,
                self.race_points_cache,
                current_times,
                qual_ratio,
                'qual'
            )
        elif race_best > 0 and race_worst > 0:
            current_times = LapTimes(race_best, race_worst, race_user, race_ratio)
            self.graph_window.set_data(
                self.qual_points_cache,
                self.race_points_cache,
                current_times,
                race_ratio,
                'race'
            )
        else:
            self.graph_window.set_data(
                self.qual_points_cache,
                self.race_points_cache
            )
    
    def open_graph_window(self):
        """Open the dedicated graph window"""
        if not self.graph_window:
            self.graph_window = RatioGraphWindow(self, self.track_name)
            # Connect signals
            self.graph_window.destroyed.connect(self.on_graph_window_closed)
        
        # Set the historic data in the graph window
        self.graph_window.set_data(
            self.qual_points_cache,
            self.race_points_cache
        )
        
        self.graph_window.show()
        self.graph_window.raise_()
    
    def on_graph_window_closed(self):
        """Handle graph window closing"""
        self.graph_window = None
    
    def load_historic_data(self):
        """Load historic data for this track"""
        self.qual_points_cache = self.data_store.get_qualifying_points(self.track_name)
        self.race_points_cache = self.data_store.get_race_points(self.track_name)
        
        # Update stats display
        qual_count = len(self.qual_points_cache)
        race_count = len(self.race_points_cache)
        total = qual_count + race_count
        
        if total > 0:
            self.historic_stats.setText(f"📊 {total} historic points (Q:{qual_count} R:{race_count})")
            self.status_label.setText(f"Loaded {total} historic data points for this track")
        else:
            self.historic_stats.setText("📊 No historic data")
            self.status_label.setText("No historic data found for this track")
        
        # Update graph window if open
        if self.graph_window and self.graph_window.isVisible():
            self.graph_window.set_data(self.qual_points_cache, self.race_points_cache)
    
    def get_qual_times(self):
        best = self.get_time_value(self.qual_best_min, self.qual_best_sec, self.qual_best_ms)
        worst = self.get_time_value(self.qual_worst_min, self.qual_worst_sec, self.qual_worst_ms)
        user = self.get_time_value(self.qual_user_min, self.qual_user_sec, self.qual_user_ms)
        ratio = self.qual_ratio_spin.value()
        return LapTimes(best, worst, user, ratio)
    
    def get_race_times(self):
        best = self.get_time_value(self.race_best_min, self.race_best_sec, self.race_best_ms)
        worst = self.get_time_value(self.race_worst_min, self.race_worst_sec, self.race_worst_ms)
        user = self.get_time_value(self.race_user_min, self.race_user_sec, self.race_user_ms)
        ratio = self.race_ratio_spin.value()
        return LapTimes(best, worst, user, ratio)
    
    def save_to_csv(self, times, is_qualifying):
        """Save lap times to CSV"""
        success = self.data_store.save_to_csv(self.track_name, times, is_qualifying)
        if success:
            self.status_label.setText(f"✓ Saved {('Qualifying' if is_qualifying else 'Race')} data to CSV")
            return True
        else:
            self.status_label.setText("✗ Failed to save to CSV")
            return False
    
    def calculate_and_save(self):
        """Save data and keep current ratios"""
        self._save_current_data()
        
        # Keep current ratios
        self.new_qual = self.current_qual
        self.new_race = self.current_race
        self.apply_btn.setEnabled(True)
        
        QMessageBox.information(self, "Data Saved", 
                               "Lap times have been saved to the CSV file.\n\n"
                               "Click APPLY RATIOS to keep the current values.")
    
    def save_only(self):
        """Save only - no calculation"""
        self._save_current_data()
        
        QMessageBox.information(self, "Data Saved", 
                               "Lap times have been saved to the CSV file.\n\n"
                               "Click APPLY RATIOS to keep the current values.")
    
    def _save_current_data(self):
        """Internal method to save all valid data"""
        qual_times = self.get_qual_times()
        race_times = self.get_race_times()
        
        saved_qual = False
        saved_race = False
        
        if qual_times.pole > 0 and qual_times.last_ai > 0:
            saved_qual = self.save_to_csv(qual_times, True)
        
        if race_times.pole > 0 and race_times.last_ai > 0:
            saved_race = self.save_to_csv(race_times, False)
        
        # Reload data to update graph
        self.load_historic_data()
        
        # Clear input fields after save
        if saved_qual:
            self.qual_best_min.setValue(0)
            self.qual_best_sec.setValue(0)
            self.qual_best_ms.setValue(0)
            self.qual_worst_min.setValue(0)
            self.qual_worst_sec.setValue(0)
            self.qual_worst_ms.setValue(0)
            self.qual_user_min.setValue(0)
            self.qual_user_sec.setValue(0)
            self.qual_user_ms.setValue(0)
        
        if saved_race:
            self.race_best_min.setValue(0)
            self.race_best_sec.setValue(0)
            self.race_best_ms.setValue(0)
            self.race_worst_min.setValue(0)
            self.race_worst_sec.setValue(0)
            self.race_worst_ms.setValue(0)
            self.race_user_min.setValue(0)
            self.race_user_sec.setValue(0)
            self.race_user_ms.setValue(0)
        
        if not saved_qual and not saved_race:
            QMessageBox.warning(self, "No Data", 
                               "No valid lap times entered.\n\n"
                               "Please enter at least Best and Worst AI times for qualifying or race.")
    
    def show_config_window(self):
        if not self.config_window:
            self.config_window = ConfigWindow(self)
            self.config_window.csv_browse.clicked.connect(self.browse_csv)
            self.config_window.save_btn.clicked.connect(self.save_configuration)
        
        self.config_window.update_from_config(self.config_csv)
        self.config_window.show()
        self.config_window.raise_()
    
    def browse_csv(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Historic CSV File",
            self.config_csv,
            "CSV Files (*.csv);;All Files (*)"
        )
        
        if file_path:
            self.config_csv = file_path
            self.data_store = HistoricDataStore(self.config_csv)
            self.load_historic_data()
            
            if self.config_window and self.config_window.isVisible():
                self.config_window.update_from_config(self.config_csv)
    
    def save_configuration(self):
        cfg_manage.update_historic_csv(self.config_csv)
        QMessageBox.information(self, "Saved", "Configuration saved to cfg.yml")
    
    def get_ratios(self):
        return self.new_qual, self.new_race
