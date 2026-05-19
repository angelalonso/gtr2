#!/usr/bin/env python3
"""
Race Data Import tab for Dyn AI Data Manager
"""

import sys
import csv
import logging
from pathlib import Path
from typing import List, Dict, Tuple, Set
from dataclasses import dataclass, field

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGroupBox, QCheckBox, QMessageBox, QFileDialog, QTableWidget,
    QTableWidgetItem, QProgressBar, QHeaderView
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal

from gui_data_manager_common import SimpleCurveDatabase

logger = logging.getLogger(__name__)


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
            self.progress.emit(0, total_records, "Loading database...")
            
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


class ImportTab(QWidget):
    """Race Data Import tab"""
    
    def __init__(self, db_path: str, parent=None):
        super().__init__(parent)
        self.db_path = db_path
        self.data_file_path = None
        self.worker = None
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
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
    
    def browse_db_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select SQLite Database", 
            str(Path.cwd()),
            "SQLite DB (*.db);;All Files (*)"
        )
        if file_path:
            self.db_path = file_path
            self.db_path_label.setText(file_path)
            self.refresh_preview()
    
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
        self.worker = None
        
        # Emit signal to refresh other tabs
        if self.parent():
            if hasattr(self.parent(), 'refresh_db_info'):
                self.parent().refresh_db_info()
            if hasattr(self.parent(), 'refresh_db_manager_tab'):
                self.parent().refresh_db_manager_tab()
    
    def import_error(self, error_msg: str):
        self.import_btn.setEnabled(True)
        self.import_btn.setVisible(True)
        self.cancel_btn.setVisible(False)
        self.progress_bar.setVisible(False)
        QMessageBox.critical(self, "Import Error", error_msg)
        self.status_label.setText(f"Error: {error_msg}")
        self.worker = None
