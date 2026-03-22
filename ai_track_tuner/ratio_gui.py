"""
Ratio Calculator GUI for AIW Ratio Editor - Data Collection Focus
Now uses global curve for predictions
"""

from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
import cfg_manage
import os
from ratio_calc import LapTimes, TimeConverter, HistoricDataStore
from track_formula import GlobalFormulaManager
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
    """Main dialog for data collection - uses global curve for predictions"""
    
    def __init__(self, parent=None, track_name="", current_qual=1.0, current_race=1.0):
        super().__init__(parent)
        self.parent_window = parent
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
        self.formulas_dir = cfg_manage.get_formulas_dir()
        self.data_store = HistoricDataStore(self.config_csv)
        self.global_manager = GlobalFormulaManager(self.formulas_dir)
        
        # Cache for historic points
        self.qual_points_cache = []
        self.race_points_cache = []
        
        self.config_window = None
        self.graph_window = None
        
        self.setup_ui()
        self.setup_connections()
        self.load_historic_data()
        self.import_csv_data_to_global_curve()
        
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
        
        info_layout.addStretch()
        
        layout.addWidget(info_bar)
        
        # Global curve status
        stats = self.global_manager.get_stats()
        if stats['total_points'] > 0:
            if stats.get('r_squared'):
                status_text = f"✓ Global curve active: {stats['total_tracks']} tracks, {stats['total_points']} points | R² = {stats['r_squared']:.4f}"
            else:
                status_text = f"⚠ Global curve: {stats['total_tracks']} tracks, {stats['total_points']} points | Not fitted yet"
        else:
            status_text = "⚠ No global curve data. Add points from tracks to build the curve."
        
        self.status_label_global = QLabel(status_text)
        self.status_label_global.setWordWrap(True)
        self.status_label_global.setStyleSheet("color: #FFA500; font-size: 11px; padding: 5px; background-color: #3c3c3c; border-radius: 3px;")
        layout.addWidget(self.status_label_global)
        
        # Buttons row
        buttons_widget = QWidget()
        buttons_layout = QHBoxLayout(buttons_widget)
        buttons_layout.setContentsMargins(0, 5, 0, 10)
        buttons_layout.setSpacing(10)
        
        self.open_graph_btn = QPushButton("📊 OPEN GLOBAL CURVE EDITOR")
        self.open_graph_btn.setToolTip("Open window to view/manage the global curve and add points")
        self.open_graph_btn.setFixedHeight(45)
        self.open_graph_btn.setCursor(Qt.PointingHandCursor)
        self.open_graph_btn.setStyleSheet("""
            QPushButton {
                background-color: #9C27B0;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #7B1FA2;
            }
        """)
        buttons_layout.addWidget(self.open_graph_btn)
        
        self.quick_calc_btn = QPushButton("🔢 CALCULATE RATIO FROM LAP TIME")
        self.quick_calc_btn.setToolTip("Calculate ratio using the global curve")
        self.quick_calc_btn.setFixedHeight(45)
        self.quick_calc_btn.setCursor(Qt.PointingHandCursor)
        self.quick_calc_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)
        buttons_layout.addWidget(self.quick_calc_btn)
        
        buttons_layout.addStretch()
        
        layout.addWidget(buttons_widget)
        
        # Input section
        input_group = QGroupBox("Enter New Lap Times (will be added to global curve)")
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
        
        self.save_btn = QPushButton("SAVE & ADD TO GLOBAL CURVE")
        self.save_btn.setToolTip("Save lap times and add them to the global curve database")
        self.save_btn.setFixedHeight(50)
        self.save_btn.setFixedWidth(220)
        self.save_btn.setCursor(Qt.PointingHandCursor)
        self.save_btn.setStyleSheet("background-color: #9C27B0; font-size: 14px;")
        button_layout.addWidget(self.save_btn)
        
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
        
        # Initially disable save button until we have data
        self.save_btn.setEnabled(False)
        self.apply_btn.setEnabled(False)
        self.quick_calc_btn.setEnabled(stats['total_points'] >= 2 and stats.get('r_squared') is not None)
    
    def import_csv_data_to_global_curve(self):
        """Import all historic data from CSV to global curve"""
        # Load all qualifying data
        all_qual_points = self.data_store.qualifying_data
        for track_name, points in all_qual_points.items():
            for ratio, best, worst, user, timestamp in points:
                # Use median of best and worst
                median_time = (best + worst) / 2
                if median_time > 0 and ratio > 0:
                    self.global_manager.add_point(track_name, ratio, median_time)
        
        # Load all race data
        all_race_points = self.data_store.race_data
        for track_name, points in all_race_points.items():
            for ratio, best, worst, user, timestamp in points:
                median_time = (best + worst) / 2
                if median_time > 0 and ratio > 0:
                    self.global_manager.add_point(track_name, ratio, median_time)
        
        stats = self.global_manager.get_stats()
        if stats['total_points'] > 0:
            print(f"Imported {stats['total_points']} points from {stats['total_tracks']} tracks to global curve")
    
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
    
    def update_race_totals(self):
        best = self.get_time_value(self.race_best_min, self.race_best_sec, self.race_best_ms)
        worst = self.get_time_value(self.race_worst_min, self.race_worst_sec, self.race_worst_ms)
        user = self.get_time_value(self.race_user_min, self.race_user_sec, self.race_user_ms)
        
        self.race_best_total.setText(f"{best:.3f}s")
        self.race_worst_total.setText(f"{worst:.3f}s")
        self.race_user_total.setText(f"{user:.3f}s")
        
        self.check_data_available()
    
    def check_data_available(self):
        qual_has_data = (self.get_time_value(self.qual_best_min, self.qual_best_sec, self.qual_best_ms) > 0 and
                         self.get_time_value(self.qual_worst_min, self.qual_worst_sec, self.qual_worst_ms) > 0)
        
        race_has_data = (self.get_time_value(self.race_best_min, self.race_best_sec, self.race_best_ms) > 0 and
                         self.get_time_value(self.race_worst_min, self.race_worst_sec, self.race_worst_ms) > 0)
        
        has_data = qual_has_data or race_has_data
        self.save_btn.setEnabled(has_data)
    
    def setup_connections(self):
        # Qualifying connections
        self.qual_ratio_spin.valueChanged.connect(self.check_data_available)
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
        self.race_ratio_spin.valueChanged.connect(self.check_data_available)
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
        self.quick_calc_btn.clicked.connect(self.open_quick_calculator)
        self.save_btn.clicked.connect(self.save_data)
        self.config_btn.clicked.connect(self.show_config_window)
        self.apply_btn.clicked.connect(self.accept)
    
    def open_quick_calculator(self):
        """Open the standalone ratio calculator using global curve"""
        stats = self.global_manager.get_stats()
        if stats['total_points'] < 2:
            QMessageBox.warning(self, "Insufficient Data", 
                               "Not enough data points to make reliable predictions.\n\n"
                               "Please add at least 2 data points from different tracks to build the global curve.")
            return
        
        if not stats.get('r_squared'):
            QMessageBox.information(self, "Curve Not Fitted", 
                                   "The global curve has not been fitted yet.\n\n"
                                   "Please go to the Global Curve Editor and click 'Fit Global Curve' first.")
            return
        
        # Create a temporary calculator dialog using the global curve
        class QuickCalcDialog(QDialog):
            def __init__(self, parent, track_name, manager):
                super().__init__(parent)
                self.track_name = track_name
                self.manager = manager
                self.calculated_ratio = None
                self.setup_ui()
            
            def setup_ui(self):
                self.setWindowTitle(f"Calculate Ratio - {self.track_name}")
                self.setModal(True)
                self.setMinimumWidth(450)
                
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
                    }
                    QPushButton {
                        background-color: #4CAF50;
                        color: white;
                        border: none;
                        border-radius: 3px;
                        padding: 8px;
                        font-weight: bold;
                    }
                    QSpinBox, QDoubleSpinBox {
                        background-color: #3c3c3c;
                        color: white;
                        border: 1px solid #4CAF50;
                        border-radius: 3px;
                        padding: 5px;
                    }
                """)
                
                layout = QVBoxLayout(self)
                
                # Track info
                info_label = QLabel(f"Track: {self.track_name}")
                info_label.setStyleSheet("color: #FFA500; font-size: 14px; font-weight: bold;")
                layout.addWidget(info_label)
                
                # Formula info
                stats = self.manager.get_stats()
                formula = self.manager.global_curve.get_formula_string()
                formula_label = QLabel(f"Global Curve:\n{formula}")
                formula_label.setWordWrap(True)
                formula_label.setStyleSheet("color: #4CAF50; font-family: monospace; font-size: 11px;")
                layout.addWidget(formula_label)
                
                multiplier = self.manager.global_curve.get_track_multiplier(self.track_name)
                multiplier_label = QLabel(f"Track multiplier: {multiplier:.6f}")
                multiplier_label.setStyleSheet("color: #FFA500;")
                layout.addWidget(multiplier_label)
                
                # Input
                input_group = QGroupBox("Enter Your Lap Time")
                input_layout = QGridLayout(input_group)
                
                input_layout.addWidget(QLabel("Minutes:"), 0, 0)
                self.minutes_spin = QSpinBox()
                self.minutes_spin.setRange(0, 99)
                self.minutes_spin.setFixedWidth(80)
                input_layout.addWidget(self.minutes_spin, 0, 1)
                
                input_layout.addWidget(QLabel("Seconds:"), 0, 2)
                self.seconds_spin = QSpinBox()
                self.seconds_spin.setRange(0, 59)
                self.seconds_spin.setFixedWidth(80)
                input_layout.addWidget(self.seconds_spin, 0, 3)
                
                input_layout.addWidget(QLabel("Milliseconds:"), 0, 4)
                self.ms_spin = QSpinBox()
                self.ms_spin.setRange(0, 999)
                self.ms_spin.setSingleStep(10)
                self.ms_spin.setFixedWidth(100)
                input_layout.addWidget(self.ms_spin, 0, 5)
                
                layout.addWidget(input_group)
                
                # Result
                result_group = QGroupBox("Calculated Ratio")
                result_layout = QVBoxLayout(result_group)
                
                self.result_label = QLabel("---")
                self.result_label.setAlignment(Qt.AlignCenter)
                self.result_label.setStyleSheet("color: #9C27B0; font-size: 18px; font-weight: bold;")
                result_layout.addWidget(self.result_label)
                
                layout.addWidget(result_group)
                
                # Buttons
                btn_layout = QHBoxLayout()
                
                self.calc_btn = QPushButton("Calculate")
                self.calc_btn.clicked.connect(self.calculate)
                btn_layout.addWidget(self.calc_btn)
                
                self.apply_btn = QPushButton("Apply Ratio")
                self.apply_btn.clicked.connect(self.accept)
                self.apply_btn.setEnabled(False)
                btn_layout.addWidget(self.apply_btn)
                
                cancel_btn = QPushButton("Cancel")
                cancel_btn.clicked.connect(self.reject)
                btn_layout.addWidget(cancel_btn)
                
                layout.addLayout(btn_layout)
                
                # Status
                self.status_label = QLabel("")
                self.status_label.setStyleSheet("color: #888;")
                layout.addWidget(self.status_label)
            
            def get_user_time(self):
                return self.minutes_spin.value() * 60 + self.seconds_spin.value() + self.ms_spin.value() / 1000.0
            
            def calculate(self):
                user_time = self.get_user_time()
                ratio = self.manager.global_curve.predict_ratio(user_time, self.track_name)
                
                if ratio is not None:
                    self.calculated_ratio = ratio
                    self.result_label.setText(f"{ratio:.6f}")
                    self.apply_btn.setEnabled(True)
                    self.status_label.setText("✓ Ratio calculated successfully")
                else:
                    self.result_label.setText("Outside range")
                    self.apply_btn.setEnabled(False)
                    self.status_label.setText("Time outside the valid range for this track")
            
            def get_ratio(self):
                return self.calculated_ratio
        
        dialog = QuickCalcDialog(self, self.track_name, self.global_manager)
        if dialog.exec_() == QDialog.Accepted:
            ratio = dialog.get_ratio()
            if ratio:
                self.new_qual = ratio
                self.new_race = ratio
                self.apply_btn.setEnabled(True)
                self.status_label.setText(f"Calculated ratio: {ratio:.6f}")
    
    def open_graph_window(self):
        """Open the global curve editor window"""
        if not self.graph_window:
            self.graph_window = RatioGraphWindow(self, self.global_manager)
            self.graph_window.destroyed.connect(self.on_graph_window_closed)
        
        self.graph_window.show()
        self.graph_window.raise_()
    
    def on_graph_window_closed(self):
        """Handle graph window closing"""
        self.graph_window = None
        # Update quick calculate button state
        stats = self.global_manager.get_stats()
        self.quick_calc_btn.setEnabled(stats['total_points'] >= 2 and stats.get('r_squared') is not None)
        # Update status label
        if stats['total_points'] > 0:
            if stats.get('r_squared'):
                status_text = f"✓ Global curve active: {stats['total_tracks']} tracks, {stats['total_points']} points | R² = {stats['r_squared']:.4f}"
            else:
                status_text = f"⚠ Global curve: {stats['total_tracks']} tracks, {stats['total_points']} points | Not fitted yet"
        else:
            status_text = "⚠ No global curve data. Add points from tracks to build the curve."
        
        self.status_label_global.setText(status_text)
    
    def save_data(self):
        """Save lap times and add to global curve"""
        qual_times = self.get_qual_times()
        race_times = self.get_race_times()
        
        saved = 0
        
        # Save qualifying data
        if qual_times.pole > 0 and qual_times.last_ai > 0:
            # Use median time
            median_time = (qual_times.pole + qual_times.last_ai) / 2
            self.global_manager.add_point(self.track_name, qual_times.ratio, median_time)
            saved += 1
            self.status_label.setText(f"✓ Added qualifying point: R={qual_times.ratio:.4f}, T={median_time:.2f}s")
        
        # Save race data
        if race_times.pole > 0 and race_times.last_ai > 0:
            median_time = (race_times.pole + race_times.last_ai) / 2
            self.global_manager.add_point(self.track_name, race_times.ratio, median_time)
            saved += 1
            if saved == 1:
                self.status_label.setText(f"✓ Added race point: R={race_times.ratio:.4f}, T={median_time:.2f}s")
            else:
                self.status_label.setText(f"✓ Added both points to global curve")
        
        if saved == 0:
            QMessageBox.warning(self, "No Data", "Please enter at least Best and Worst AI times.")
            return
        
        # Clear input fields
        self.qual_best_min.setValue(0)
        self.qual_best_sec.setValue(0)
        self.qual_best_ms.setValue(0)
        self.qual_worst_min.setValue(0)
        self.qual_worst_sec.setValue(0)
        self.qual_worst_ms.setValue(0)
        self.qual_user_min.setValue(0)
        self.qual_user_sec.setValue(0)
        self.qual_user_ms.setValue(0)
        
        self.race_best_min.setValue(0)
        self.race_best_sec.setValue(0)
        self.race_best_ms.setValue(0)
        self.race_worst_min.setValue(0)
        self.race_worst_sec.setValue(0)
        self.race_worst_ms.setValue(0)
        self.race_user_min.setValue(0)
        self.race_user_sec.setValue(0)
        self.race_user_ms.setValue(0)
        
        # Update quick calculate button state
        stats = self.global_manager.get_stats()
        self.quick_calc_btn.setEnabled(stats['total_points'] >= 2 and stats.get('r_squared') is not None)
        
        # Update status label
        if stats['total_points'] > 0:
            if stats.get('r_squared'):
                status_text = f"✓ Global curve active: {stats['total_tracks']} tracks, {stats['total_points']} points | R² = {stats['r_squared']:.4f}"
            else:
                status_text = f"⚠ Global curve: {stats['total_tracks']} tracks, {stats['total_points']} points | Not fitted yet"
        else:
            status_text = "⚠ No global curve data. Add points from tracks to build the curve."
        
        self.status_label_global.setText(status_text)
        
        QMessageBox.information(self, "Data Saved", 
                               f"Data added to global curve.\n\n"
                               f"Total points: {stats['total_points']} across {stats['total_tracks']} tracks.\n\n"
                               f"Click 'Fit Global Curve' in the editor to build the model.")
    
    def load_historic_data(self):
        """Load historic data from CSV for display"""
        self.qual_points_cache = self.data_store.get_qualifying_points(self.track_name)
        self.race_points_cache = self.data_store.get_race_points(self.track_name)
        
        count = len(self.qual_points_cache) + len(self.race_points_cache)
        if count > 0:
            print(f"Loaded {count} historic data points for {self.track_name}")
    
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
            self.import_csv_data_to_global_curve()
            
            if self.config_window and self.config_window.isVisible():
                self.config_window.update_from_config(self.config_csv)
    
    def save_configuration(self):
        cfg_manage.update_historic_csv(self.config_csv)
        QMessageBox.information(self, "Saved", "Configuration saved to cfg.yml")
    
    def get_ratios(self):
        return self.new_qual, self.new_race
