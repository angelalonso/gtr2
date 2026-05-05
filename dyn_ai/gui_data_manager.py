#!/usr/bin/env python3
"""
Dyn AI Data Management Tool
Manages vehicle classes and imports race data into the Live AI Tuner SQLite database
"""

import sys
import csv
import sqlite3
import json
import logging
import subprocess
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Tuple, Optional, Set
from dataclasses import dataclass, field

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFileDialog, QTableWidget, QTableWidgetItem,
    QProgressBar, QGroupBox, QCheckBox, QMessageBox, QSplitter,
    QTextEdit, QHeaderView, QFrame, QSpinBox, QComboBox, QTabWidget,
    QLineEdit, QDialog, QDialogButtonBox, QListWidget, QListWidgetItem,
    QScrollArea, QGridLayout, QTreeWidget, QTreeWidgetItem, QInputDialog,
    QMenu, QProgressDialog
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer, QSettings
from PyQt5.QtGui import QFont, QColor, QTextCursor, QIcon

from gui_vehicle_manager import launch_vehicle_manager
from core_database import CurveDatabase
from core_config import get_base_path

logger = logging.getLogger(__name__)


class SimpleCurveDatabase:
    """Simplified database handler that matches the expected interface"""
    
    def __init__(self, db_path: str = "ai_data.db"):
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS data_points (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                track TEXT NOT NULL,
                vehicle_class TEXT NOT NULL,
                ratio REAL NOT NULL,
                lap_time REAL NOT NULL,
                session_type TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_track ON data_points(track)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_vehicle_class ON data_points(vehicle_class)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_session ON data_points(session_type)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_track_class ON data_points(track, vehicle_class)")
        
        conn.commit()
        conn.close()
    
    def data_point_exists(self, track: str, vehicle_class: str, ratio: float, lap_time: float, session_type: str) -> bool:
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                SELECT COUNT(*) FROM data_points 
                WHERE track = ? AND vehicle_class = ? AND ratio = ? AND lap_time = ? AND session_type = ?
            """, (track, vehicle_class, ratio, lap_time, session_type))
            count = cursor.fetchone()[0]
            conn.close()
            return count > 0
        except Exception as e:
            logger.error(f"Error checking existence: {e}")
            return False
    
    def add_data_point(self, track: str, vehicle_class: str, ratio: float, lap_time: float, session_type: str) -> bool:
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO data_points (track, vehicle_class, ratio, lap_time, session_type)
                VALUES (?, ?, ?, ?, ?)
            """, (track, vehicle_class, ratio, lap_time, session_type))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"Error adding data point: {e}")
            return False
    
    def get_stats(self) -> dict:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM data_points")
        total_points = cursor.fetchone()[0]
        
        cursor.execute("SELECT session_type, COUNT(*) FROM data_points GROUP BY session_type")
        by_type = dict(cursor.fetchall())
        
        cursor.execute("SELECT COUNT(DISTINCT track) FROM data_points")
        total_tracks = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(DISTINCT vehicle_class) FROM data_points")
        total_vehicle_classes = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            'total_points': total_points,
            'by_type': by_type,
            'total_tracks': total_tracks,
            'total_vehicle_classes': total_vehicle_classes
        }
    
    def database_exists(self) -> bool:
        return Path(self.db_path).exists()
    
    def get_all_tracks(self) -> List[str]:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT track FROM data_points ORDER BY track")
        tracks = [row[0] for row in cursor.fetchall()]
        conn.close()
        return tracks
    
    def get_all_vehicle_classes(self) -> List[str]:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT vehicle_class FROM data_points ORDER BY vehicle_class")
        vehicles = [row[0] for row in cursor.fetchall()]
        conn.close()
        return vehicles


class DataImportWorker(QThread):
    """Worker thread for importing race data"""
    
    progress = pyqtSignal(int, int, str)
    record_processed = pyqtSignal(int, int, int)
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)
    
    def __init__(self, db_path: str, data_file_path: str, 
                 import_qual: bool = True, import_race: bool = True,
                 skip_duplicates: bool = True):
        super().__init__()
        self.db_path = db_path
        self.data_file_path = data_file_path
        self.import_qual = import_qual
        self.import_race = import_race
        self.skip_duplicates = skip_duplicates
        self._is_running = True
    
    def stop(self):
        self._is_running = False
    
    def run(self):
        try:
            records = self._read_data_file()
            
            if not records:
                self.error.emit("No valid records found in data file")
                return
            
            total_records = len(records)
            self.progress.emit(0, total_records, f"Loading database...")
            
            db = SimpleCurveDatabase(self.db_path)
            
            qual_added = 0
            race_added = 0
            qual_skipped = 0
            race_skipped = 0
            tracks_seen = set()
            vehicles_seen = set()
            
            for i, record in enumerate(records):
                if not self._is_running:
                    self.progress.emit(i, total_records, "Import cancelled")
                    break
                
                tracks_seen.add(record.track)
                vehicles_seen.add(record.vehicle)
                
                if self.import_qual and record.has_valid_qual_data():
                    for vehicle_class, ratio, lap_time in record.get_qual_data_points():
                        exists = db.data_point_exists(
                            record.track, vehicle_class, ratio, lap_time, "qual"
                        )
                        
                        if exists and self.skip_duplicates:
                            qual_skipped += 1
                        else:
                            if db.add_data_point(record.track, vehicle_class, ratio, lap_time, "qual"):
                                qual_added += 1
                
                if self.import_race and record.has_valid_race_data():
                    for vehicle_class, ratio, lap_time in record.get_race_data_points():
                        exists = db.data_point_exists(
                            record.track, vehicle_class, ratio, lap_time, "race"
                        )
                        
                        if exists and self.skip_duplicates:
                            race_skipped += 1
                        else:
                            if db.add_data_point(record.track, vehicle_class, ratio, lap_time, "race"):
                                race_added += 1
                
                self.record_processed.emit(qual_added, race_added, i + 1)
                self.progress.emit(i + 1, total_records, f"Processing: {record.track}")
            
            stats = db.get_stats()
            
            summary = {
                'total_records': total_records,
                'qual_added': qual_added,
                'race_added': race_added,
                'qual_skipped': qual_skipped,
                'race_skipped': race_skipped,
                'total_points': stats.get('total_points', qual_added + race_added),
                'total_tracks': len(tracks_seen),
                'total_vehicles': len(vehicles_seen),
                'tracks': sorted(tracks_seen),
                'vehicles': sorted(vehicles_seen)
            }
            
            self.finished.emit(summary)
            
        except Exception as e:
            self.error.emit(f"Import failed: {str(e)}")
            logger.exception("Import error")
    
    def _read_data_file(self) -> List['RaceDataRecord']:
        records = []
        
        with open(self.data_file_path, 'r', encoding='utf-8-sig') as f:
            sample = f.read(1024)
            f.seek(0)
            
            if ';' in sample:
                delimiter = ';'
            elif ',' in sample:
                delimiter = ','
            else:
                delimiter = ';'
            
            reader = csv.DictReader(f, delimiter=delimiter)
            
            for row_num, row in enumerate(reader, 2):
                if not self._is_running:
                    break
                
                record = self._create_record_from_row(row)
                if record and (record.has_valid_qual_data() or record.has_valid_race_data()):
                    records.append(record)
        
        return records
    
    def _create_record_from_row(self, row: Dict[str, str]):
        def parse_float(val: str) -> float:
            if not val or val.strip() == '' or val.strip() == '0':
                return 0.0
            try:
                val = val.replace(',', '.')
                return float(val)
            except ValueError:
                return 0.0
        
        def parse_str(val: str) -> str:
            if not val or val.strip() == '':
                return "Unknown"
            return val.strip()
        
        try:
            return RaceDataRecord(
                vehicle=parse_str(row.get('User Vehicle', 'Unknown')),
                timestamp=parse_str(row.get('Timestamp', '')),
                track=parse_str(row.get('Track Name', 'Unknown')),
                qual_ratio=parse_float(row.get('Current QualRatio', '0')),
                qual_best_ai=parse_float(row.get('Qual AI Best (s)', '0')),
                qual_best_vehicle=parse_str(row.get('Q AI Best Vehicle', 'Unknown')),
                qual_worst_ai=parse_float(row.get('Qual AI Worst (s)', '0')),
                qual_worst_vehicle=parse_str(row.get('Q AI Worst Vehicle', 'Unknown')),
                qual_user=parse_float(row.get('Qual User (s)', '0')),
                race_ratio=parse_float(row.get('Current RaceRatio', '0')),
                race_best_ai=parse_float(row.get('Race AI Best (s)', '0')),
                race_best_vehicle=parse_str(row.get('R AI Best Vehicle', 'Unknown')),
                race_worst_ai=parse_float(row.get('Race AI Worst (s)', '0')),
                race_worst_vehicle=parse_str(row.get('R AI Worst Vehicle', 'Unknown')),
                race_user=parse_float(row.get('Race User (s)', '0'))
            )
        except Exception as e:
            logger.error(f"Error parsing race data row: {e}")
            return None


@dataclass
class RaceDataRecord:
    vehicle: str
    timestamp: str
    track: str
    qual_ratio: float
    qual_best_ai: float
    qual_best_vehicle: str
    qual_worst_ai: float
    qual_worst_vehicle: str
    qual_user: float
    race_ratio: float
    race_best_ai: float
    race_best_vehicle: str
    race_worst_ai: float
    race_worst_vehicle: str
    race_user: float
    
    def get_qual_data_points(self) -> List[Tuple[str, float, float]]:
        points = []
        if self.qual_best_ai > 0 and self.qual_worst_ai > 0:
            midpoint = (self.qual_best_ai + self.qual_worst_ai) / 2
            points.append((self.qual_best_vehicle, self.qual_ratio, midpoint))
        return points
    
    def get_race_data_points(self) -> List[Tuple[str, float, float]]:
        points = []
        if self.race_best_ai > 0 and self.race_worst_ai > 0:
            midpoint = (self.race_best_ai + self.race_worst_ai) / 2
            points.append((self.race_best_vehicle, self.race_ratio, midpoint))
        return points
    
    def has_valid_qual_data(self) -> bool:
        return (self.qual_ratio > 0 and 
                self.qual_best_ai > 0 and 
                self.qual_worst_ai > 0 and
                0.3 < self.qual_ratio < 3.0)
    
    def has_valid_race_data(self) -> bool:
        return (self.race_ratio > 0 and 
                self.race_best_ai > 0 and 
                self.race_worst_ai > 0 and
                0.3 < self.race_ratio < 3.0)


class DynAIDataManager(QMainWindow):
    """Main GUI window for Dyn AI Data Management"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Dyn AI Data Manager - Live AI Tuner")
        self.setGeometry(100, 100, 1200, 800)
        
        self.db_path = "ai_data.db"
        self.data_file_path = None
        self.worker = None
        
        self.setup_ui()
        self.apply_styles()
        self.refresh_db_info()
    
    def setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        title = QLabel("Dyn AI Data Manager")
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: #4CAF50;")
        title.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title)
        
        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget)
        
        import_tab = self.create_import_tab()
        self.tab_widget.addTab(import_tab, "Race Data Import")
        
        vehicle_tab = self.create_vehicle_tab()
        self.tab_widget.addTab(vehicle_tab, "Vehicle Classes")
        
        info_tab = self.create_info_tab()
        self.tab_widget.addTab(info_tab, "Database Info")
        
        about_tab = self.create_about_tab()
        self.tab_widget.addTab(about_tab, "About")
        
        self.statusBar().showMessage("Ready")
    
    def create_import_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        file_group = QGroupBox("Race Data File")
        file_layout = QVBoxLayout(file_group)
        
        data_file_layout = QHBoxLayout()
        data_file_layout.addWidget(QLabel("Data File (CSV):"))
        self.data_file_label = QLabel("No file selected")
        self.data_file_label.setStyleSheet("color: #888; font-family: monospace;")
        self.data_file_label.setWordWrap(True)
        data_file_layout.addWidget(self.data_file_label, 1)
        
        self.browse_data_btn = QPushButton("Browse...")
        self.browse_data_btn.clicked.connect(self.browse_data_file)
        data_file_layout.addWidget(self.browse_data_btn)
        file_layout.addLayout(data_file_layout)
        
        db_layout = QHBoxLayout()
        db_layout.addWidget(QLabel("Database:"))
        self.db_path_label = QLabel(self.db_path)
        self.db_path_label.setStyleSheet("color: #4CAF50; font-family: monospace;")
        db_layout.addWidget(self.db_path_label, 1)
        
        self.browse_db_btn = QPushButton("Change...")
        self.browse_db_btn.clicked.connect(self.browse_db_file)
        db_layout.addWidget(self.browse_db_btn)
        file_layout.addLayout(db_layout)
        
        layout.addWidget(file_group)
        
        options_group = QGroupBox("Import Options")
        options_layout = QHBoxLayout(options_group)
        
        self.import_qual_cb = QCheckBox("Import Qualifying Data")
        self.import_qual_cb.setChecked(True)
        self.import_qual_cb.setToolTip("Import qualifying session data points")
        options_layout.addWidget(self.import_qual_cb)
        
        self.import_race_cb = QCheckBox("Import Race Data")
        self.import_race_cb.setChecked(True)
        self.import_race_cb.setToolTip("Import race session data points")
        options_layout.addWidget(self.import_race_cb)
        
        self.skip_duplicates_cb = QCheckBox("Skip Duplicates")
        self.skip_duplicates_cb.setChecked(True)
        self.skip_duplicates_cb.setToolTip("Don't import data points that already exist")
        options_layout.addWidget(self.skip_duplicates_cb)
        
        options_layout.addStretch()
        layout.addWidget(options_group)
        
        preview_group = QGroupBox("Data Preview")
        preview_layout = QVBoxLayout(preview_group)
        
        self.preview_table = QTableWidget()
        self.preview_table.setAlternatingRowColors(True)
        self.preview_table.setMinimumHeight(200)
        preview_layout.addWidget(self.preview_table)
        
        self.refresh_preview_btn = QPushButton("Refresh Preview")
        self.refresh_preview_btn.clicked.connect(self.refresh_preview)
        preview_layout.addWidget(self.refresh_preview_btn)
        
        layout.addWidget(preview_group)
        
        progress_group = QGroupBox("Import Progress")
        progress_layout = QVBoxLayout(progress_group)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        progress_layout.addWidget(self.progress_bar)
        
        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet("color: #888;")
        progress_layout.addWidget(self.status_label)
        
        self.stats_label = QLabel("")
        self.stats_label.setStyleSheet("color: #4CAF50; font-family: monospace;")
        progress_layout.addWidget(self.stats_label)
        
        layout.addWidget(progress_group)
        
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.import_btn = QPushButton("Start Import")
        self.import_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                padding: 12px 30px;
                font-size: 14px;
                font-weight: bold;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        self.import_btn.clicked.connect(self.start_import)
        button_layout.addWidget(self.import_btn)
        
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setVisible(False)
        self.cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                padding: 12px 30px;
                font-size: 14px;
                font-weight: bold;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #d32f2f;
            }
        """)
        self.cancel_btn.clicked.connect(self.cancel_import)
        button_layout.addWidget(self.cancel_btn)
        
        button_layout.addStretch()
        layout.addLayout(button_layout)
        
        return tab
    
    def create_vehicle_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        info_label = QLabel(
            "Vehicle Classes Management\n\n"
            "This defines which vehicles belong to which class for AI tuning.\n"
            "Click the button below to open the Vehicle Manager dialog."
        )
        info_label.setStyleSheet("color: #FFA500; background-color: #2b2b2b; padding: 15px; border-radius: 5px;")
        info_label.setWordWrap(True)
        info_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(info_label)
        
        layout.addSpacing(30)
        
        open_manager_btn = QPushButton("Open Vehicle Manager")
        open_manager_btn.setStyleSheet("""
            QPushButton {
                background-color: #9C27B0;
                color: white;
                padding: 15px 30px;
                font-size: 16px;
                font-weight: bold;
                border-radius: 8px;
            }
            QPushButton:hover {
                background-color: #7B1FA2;
            }
        """)
        open_manager_btn.clicked.connect(self.open_vehicle_manager)
        
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_layout.addWidget(open_manager_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        
        layout.addStretch()
        
        return tab
    
    def create_info_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        stats_group = QGroupBox("Database Statistics")
        stats_layout = QVBoxLayout(stats_group)
        self.db_stats_label = QLabel("Click 'Refresh' to load database statistics")
        self.db_stats_label.setStyleSheet("font-family: monospace;")
        stats_layout.addWidget(self.db_stats_label)
        layout.addWidget(stats_group)
        
        tracks_group = QGroupBox("Tracks in Database")
        tracks_layout = QVBoxLayout(tracks_group)
        self.tracks_list = QTextEdit()
        self.tracks_list.setReadOnly(True)
        self.tracks_list.setMaximumHeight(200)
        self.tracks_list.setFont(QFont("Courier New", 10))
        tracks_layout.addWidget(self.tracks_list)
        layout.addWidget(tracks_group)
        
        vehicles_group = QGroupBox("Vehicle Classes in Database")
        vehicles_layout = QVBoxLayout(vehicles_group)
        self.vehicles_list = QTextEdit()
        self.vehicles_list.setReadOnly(True)
        self.vehicles_list.setMaximumHeight(150)
        self.vehicles_list.setFont(QFont("Courier New", 10))
        vehicles_layout.addWidget(self.vehicles_list)
        layout.addWidget(vehicles_group)
        
        refresh_layout = QHBoxLayout()
        refresh_layout.addStretch()
        self.refresh_db_btn = QPushButton("Refresh Database Info")
        self.refresh_db_btn.clicked.connect(self.refresh_db_info)
        refresh_layout.addWidget(self.refresh_db_btn)
        layout.addLayout(refresh_layout)
        
        return tab
    
    def create_about_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        about_text = QTextEdit()
        about_text.setReadOnly(True)
        about_text.setHtml("""
        <h2>Dyn AI Data Manager</h2>
        <p>Comprehensive data management tool for the Live AI Tuner system.</p>
        
        <h3>Race Data Import:</h3>
        <ul>
            <li>Import race data from CSV files (compatible with historic.csv format)</li>
            <li>Automatically calculates midpoint = (AI Best + AI Worst) / 2</li>
            <li>Separates qualifying and race session data</li>
            <li>Duplicate detection prevents redundant entries</li>
        </ul>
        
        <h3>Vehicle Classes Management:</h3>
        <ul>
            <li>Launch the standalone Vehicle Manager dialog</li>
            <li>Add, rename, or delete vehicle classes</li>
            <li>Add, edit, or remove vehicles from classes</li>
            <li>Import vehicles from GTR2 installation</li>
            <li>Batch assign unassigned vehicles to classes</li>
            <li>Changes are saved to vehicle_classes.json</li>
        </ul>
        
        <h3>Database Management:</h3>
        <ul>
            <li>View database statistics</li>
            <li>See all tracks and vehicle classes in the database</li>
            <li>Monitor data accumulation</li>
        </ul>
        """)
        layout.addWidget(about_text)
        
        return tab
    
    def apply_styles(self):
        self.setStyleSheet("""
            QMainWindow {
                background-color: #1e1e1e;
            }
            QWidget {
                background-color: #1e1e1e;
                color: #ffffff;
            }
            QGroupBox {
                color: #4CAF50;
                border: 2px solid #555;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
                font-weight: bold;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
            QTableWidget {
                background-color: #2b2b2b;
                alternate-background-color: #3c3c3c;
                gridline-color: #555;
                selection-background-color: #4CAF50;
            }
            QTableWidget::item {
                padding: 4px;
            }
            QHeaderView::section {
                background-color: #3c3c3c;
                color: white;
                padding: 6px;
                border: none;
            }
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
            QProgressBar {
                border: 1px solid #555;
                border-radius: 4px;
                text-align: center;
                color: white;
            }
            QProgressBar::chunk {
                background-color: #4CAF50;
                border-radius: 3px;
            }
            QCheckBox {
                spacing: 8px;
            }
            QTabWidget::pane {
                border: 1px solid #555;
                background-color: #2b2b2b;
            }
            QTabBar::tab {
                background-color: #3c3c3c;
                padding: 8px 16px;
                margin-right: 2px;
            }
            QTabBar::tab:selected {
                background-color: #4CAF50;
            }
            QTextEdit {
                background-color: #2b2b2b;
                border: 1px solid #555;
                border-radius: 4px;
                font-family: monospace;
            }
            QListWidget {
                background-color: #2b2b2b;
                color: white;
                border: 1px solid #555;
                border-radius: 4px;
                outline: none;
            }
            QListWidget::item:selected {
                background-color: #4CAF50;
            }
            QLineEdit {
                background-color: #3c3c3c;
                color: white;
                border: 1px solid #555;
                border-radius: 4px;
                padding: 6px;
            }
            QSplitter::handle {
                background-color: #555;
            }
        """)
    
    def open_vehicle_manager(self):
        from cfg_funcs import get_base_path
        base_path = get_base_path()
        gtr2_path = base_path if base_path and base_path.exists() else None
        launch_vehicle_manager(gtr2_path, self)
    
    def browse_data_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Race Data File", 
            str(Path.cwd()),
            "CSV Files (*.csv);;All Files (*)"
        )
        if file_path:
            self.data_file_path = file_path
            self.data_file_label.setText(file_path)
            self.data_file_label.setStyleSheet("color: #4CAF50; font-family: monospace;")
            self.refresh_preview()
            self.statusBar().showMessage(f"Loaded: {Path(file_path).name}")
    
    def browse_db_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select SQLite Database", 
            str(Path.cwd()),
            "SQLite DB (*.db);;All Files (*)"
        )
        if file_path:
            self.db_path = file_path
            self.db_path_label.setText(file_path)
            self.refresh_db_info()
            self.statusBar().showMessage(f"Database: {Path(file_path).name}")
    
    def refresh_preview(self):
        if not self.data_file_path or not Path(self.data_file_path).exists():
            self.preview_table.setRowCount(0)
            self.preview_table.setColumnCount(0)
            return
        
        try:
            with open(self.data_file_path, 'r', encoding='utf-8-sig') as f:
                sample = f.read(4096)
                f.seek(0)
                
                if ';' in sample:
                    delimiter = ';'
                else:
                    delimiter = ','
                
                reader = csv.DictReader(f, delimiter=delimiter)
                
                if reader.fieldnames:
                    display_cols = ['User Vehicle', 'Track Name', 'Current QualRatio', 
                                   'Current RaceRatio', 'Qual AI Best (s)', 'Race AI Best (s)']
                    cols = [c for c in display_cols if c in reader.fieldnames]
                    
                    self.preview_table.setColumnCount(len(cols))
                    self.preview_table.setHorizontalHeaderLabels(cols)
                    
                    rows = []
                    for i, row in enumerate(reader):
                        if i >= 20:
                            break
                        rows.append(row)
                    
                    self.preview_table.setRowCount(len(rows))
                    
                    for row_idx, row in enumerate(rows):
                        for col_idx, col_name in enumerate(cols):
                            value = row.get(col_name, '')
                            item = QTableWidgetItem(str(value))
                            self.preview_table.setItem(row_idx, col_idx, item)
                    
                    self.preview_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
                    self.status_label.setText(f"Preview: {len(rows)} rows shown")
                else:
                    self.preview_table.setRowCount(0)
                    self.preview_table.setColumnCount(0)
                    
        except Exception as e:
            self.status_label.setText(f"Error loading preview: {str(e)}")
            logger.error(f"Preview error: {e}")
    
    def refresh_db_info(self):
        try:
            if not Path(self.db_path).exists():
                self.db_stats_label.setText("Database file does not exist yet.")
                self.tracks_list.clear()
                self.vehicles_list.clear()
                return
            
            db = SimpleCurveDatabase(self.db_path)
            stats = db.get_stats()
            
            stats_text = f"""
            <b>Total Data Points:</b> {stats.get('total_points', 0)}<br>
            <b>Unique Tracks:</b> {stats.get('total_tracks', 0)}<br>
            <b>Unique Vehicle Classes:</b> {stats.get('total_vehicle_classes', 0)}<br>
            <b>By Session Type:</b><br>
            """
            
            if 'by_type' in stats:
                for session_type, count in stats['by_type'].items():
                    stats_text += f"&nbsp;&nbsp;&nbsp;{session_type}: {count}<br>"
            
            self.db_stats_label.setText(stats_text)
            
            tracks = db.get_all_tracks()
            tracks_text = ""
            for track in tracks:
                tracks_text += f"• {track}\n"
            if tracks_text:
                self.tracks_list.setText(tracks_text)
            else:
                self.tracks_list.setText("No tracks found in database.")
            
            vehicles = db.get_all_vehicle_classes()
            vehicles_text = ""
            for vehicle in vehicles:
                vehicles_text += f"• {vehicle}\n"
            if vehicles_text:
                self.vehicles_list.setText(vehicles_text)
            else:
                self.vehicles_list.setText("No vehicle classes found in database.")
            
        except Exception as e:
            self.db_stats_label.setText(f"Error loading database info: {str(e)}")
            logger.error(f"DB info error: {e}")
    
    def start_import(self):
        if not self.data_file_path:
            QMessageBox.warning(self, "No Data File", "Please select a race data file to import.")
            return
        
        if not Path(self.data_file_path).exists():
            QMessageBox.warning(self, "File Not Found", f"Data file not found: {self.data_file_path}")
            return
        
        reply = QMessageBox.question(
            self, "Confirm Import",
            f"This will import race data from:\n{self.data_file_path}\n\n"
            f"Into database:\n{self.db_path}\n\n"
            f"Qualifying: {'ON' if self.import_qual_cb.isChecked() else 'OFF'}\n"
            f"Race: {'ON' if self.import_race_cb.isChecked() else 'OFF'}\n"
            f"Skip duplicates: {'ON' if self.skip_duplicates_cb.isChecked() else 'OFF'}\n\n"
            f"Continue?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
        
        self.import_btn.setEnabled(False)
        self.import_btn.setVisible(False)
        self.cancel_btn.setVisible(True)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.status_label.setText("Starting import...")
        self.stats_label.setText("")
        
        self.worker = DataImportWorker(
            self.db_path, self.data_file_path,
            self.import_qual_cb.isChecked(),
            self.import_race_cb.isChecked(),
            self.skip_duplicates_cb.isChecked()
        )
        self.worker.progress.connect(self.update_progress)
        self.worker.record_processed.connect(self.update_stats)
        self.worker.finished.connect(self.import_finished)
        self.worker.error.connect(self.import_error)
        self.worker.start()
    
    def cancel_import(self):
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.status_label.setText("Cancelling import...")
            self.cancel_btn.setEnabled(False)
    
    def update_progress(self, current: int, total: int, message: str):
        if total > 0:
            percent = int((current / total) * 100)
            self.progress_bar.setValue(percent)
        self.status_label.setText(message)
    
    def update_stats(self, qual_added: int, race_added: int, processed: int):
        self.stats_label.setText(f"Processed: {processed} | Qual added: {qual_added} | Race added: {race_added}")
    
    def import_finished(self, summary: dict):
        self.import_btn.setEnabled(True)
        self.import_btn.setVisible(True)
        self.cancel_btn.setVisible(False)
        self.progress_bar.setVisible(False)
        
        message = (
            f"<b>Import Complete!</b><br><br>"
            f"Records processed: {summary['total_records']}<br>"
            f"Qualifying points added: {summary['qual_added']}<br>"
            f"Race points added: {summary['race_added']}<br>"
            f"Qualifying skipped (duplicates): {summary['qual_skipped']}<br>"
            f"Race skipped (duplicates): {summary['race_skipped']}<br><br>"
            f"Total data points in database: {summary['total_points']}<br>"
            f"Unique tracks: {summary['total_tracks']}<br>"
            f"Unique vehicles: {summary['total_vehicles']}"
        )
        
        QMessageBox.information(self, "Import Complete", message)
        self.status_label.setText(f"Import complete: {summary['qual_added'] + summary['race_added']} points added")
        self.refresh_db_info()
        self.worker = None
    
    def import_error(self, error_msg: str):
        self.import_btn.setEnabled(True)
        self.import_btn.setVisible(True)
        self.cancel_btn.setVisible(False)
        self.progress_bar.setVisible(False)
        QMessageBox.critical(self, "Import Error", error_msg)
        self.status_label.setText(f"Error: {error_msg}")
        self.worker = None


def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    window = DynAIDataManager()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
