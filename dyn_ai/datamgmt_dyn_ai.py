#!/usr/bin/env python3
"""
Dyn AI Data Management Tool - Lightweight version
"""

import sys
import csv
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Set
from dataclasses import dataclass

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFileDialog, QTableWidget, QTableWidgetItem,
    QProgressBar, QGroupBox, QCheckBox, QMessageBox, QTabWidget,
    QHeaderView, QDialog, QListWidget, QListWidgetItem
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent))

from core.database import DatabaseManager
from core.parser import RaceDataParser, RaceData
from core.autopilot import get_vehicle_class, load_vehicle_classes


class ImportWorker(QThread):
    progress = pyqtSignal(int, int, str)
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)
    
    def __init__(self, db_path: str, csv_path: str, import_qual: bool = True, import_race: bool = True):
        super().__init__()
        self.db_path = db_path
        self.csv_path = csv_path
        self.import_qual = import_qual
        self.import_race = import_race
        self._running = True
    
    def stop(self):
        self._running = False
    
    def run(self):
        try:
            db = DatabaseManager(self.db_path)
            class_mapping = load_vehicle_classes()
            
            added = 0
            total = 0
            
            with open(self.csv_path, 'r', encoding='utf-8-sig') as f:
                sample = f.read(1024)
                f.seek(0)
                delimiter = ';' if ';' in sample else ','
                reader = csv.DictReader(f, delimiter=delimiter)
                
                rows = list(reader)
                total = len(rows)
                
                for i, row in enumerate(rows):
                    if not self._running:
                        break
                    
                    track = row.get('Track Name', '')
                    if not track:
                        continue
                    
                    user_vehicle = row.get('User Vehicle', 'Unknown')
                    vehicle_class = get_vehicle_class(user_vehicle, class_mapping)
                    
                    # Qualifying
                    if self.import_qual:
                        try:
                            qual_ratio = float(row.get('Current QualRatio', '0'))
                            qual_best = float(row.get('Qual AI Best (s)', '0'))
                            qual_worst = float(row.get('Qual AI Worst (s)', '0'))
                            
                            if qual_ratio > 0 and qual_best > 0 and qual_worst > 0:
                                midpoint = (qual_best + qual_worst) / 2
                                if db.add_data_point(track, vehicle_class, qual_ratio, midpoint, 'qual'):
                                    added += 1
                        except (ValueError, KeyError):
                            pass
                    
                    # Race
                    if self.import_race:
                        try:
                            race_ratio = float(row.get('Current RaceRatio', '0'))
                            race_best = float(row.get('Race AI Best (s)', '0'))
                            race_worst = float(row.get('Race AI Worst (s)', '0'))
                            
                            if race_ratio > 0 and race_best > 0 and race_worst > 0:
                                midpoint = (race_best + race_worst) / 2
                                if db.add_data_point(track, vehicle_class, race_ratio, midpoint, 'race'):
                                    added += 1
                        except (ValueError, KeyError):
                            pass
                    
                    self.progress.emit(i + 1, total, f"Processing: {track}")
            
            self.finished.emit({'added': added, 'total': total})
            
        except Exception as e:
            self.error.emit(str(e))


class DataManagerWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Dyn AI Data Manager")
        self.setGeometry(100, 100, 800, 600)
        
        self.db_path = "ai_data.db"
        self.csv_path = None
        self.worker = None
        
        self.setup_ui()
        self.apply_styles()
    
    def setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        
        title = QLabel("Dyn AI Data Manager")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #4CAF50;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # File selection
        file_group = QGroupBox("Import File")
        file_layout = QVBoxLayout(file_group)
        
        file_row = QHBoxLayout()
        file_row.addWidget(QLabel("CSV File:"))
        self.file_label = QLabel("No file selected")
        self.file_label.setStyleSheet("color: #888;")
        file_row.addWidget(self.file_label, 1)
        
        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self._browse_file)
        file_row.addWidget(browse_btn)
        file_layout.addLayout(file_row)
        
        layout.addWidget(file_group)
        
        # Options
        options_group = QGroupBox("Import Options")
        options_layout = QHBoxLayout(options_group)
        
        self.import_qual_cb = QCheckBox("Import Qualifying")
        self.import_qual_cb.setChecked(True)
        options_layout.addWidget(self.import_qual_cb)
        
        self.import_race_cb = QCheckBox("Import Race")
        self.import_race_cb.setChecked(True)
        options_layout.addWidget(self.import_race_cb)
        
        options_layout.addStretch()
        layout.addWidget(options_group)
        
        # Preview
        preview_group = QGroupBox("Preview")
        preview_layout = QVBoxLayout(preview_group)
        
        self.preview_table = QTableWidget()
        self.preview_table.setAlternatingRowColors(True)
        preview_layout.addWidget(self.preview_table)
        
        refresh_btn = QPushButton("Refresh Preview")
        refresh_btn.clicked.connect(self._refresh_preview)
        preview_layout.addWidget(refresh_btn)
        
        layout.addWidget(preview_group)
        
        # Progress
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        self.status_label = QLabel("Ready")
        layout.addWidget(self.status_label)
        
        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        self.import_btn = QPushButton("Start Import")
        self.import_btn.setStyleSheet("background-color: #4CAF50; padding: 10px 20px;")
        self.import_btn.clicked.connect(self._start_import)
        btn_layout.addWidget(self.import_btn)
        
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setVisible(False)
        self.cancel_btn.clicked.connect(self._cancel_import)
        btn_layout.addWidget(self.cancel_btn)
        
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
    
    def apply_styles(self):
        self.setStyleSheet("""
            QMainWindow { background-color: #1e1e1e; }
            QWidget { background-color: #1e1e1e; color: white; }
            QGroupBox { color: #4CAF50; border: 1px solid #555; border-radius: 5px; margin-top: 8px; padding-top: 8px; }
            QGroupBox::title { left: 10px; padding: 0 5px; }
            QTableWidget { background-color: #2b2b2b; alternate-background-color: #3c3c3c; gridline-color: #555; }
            QHeaderView::section { background-color: #3c3c3c; color: white; padding: 4px; }
            QPushButton { background-color: #2196F3; color: white; border: none; border-radius: 3px; padding: 6px 12px; }
            QPushButton:hover { background-color: #1976D2; }
            QProgressBar { border: 1px solid #555; border-radius: 3px; text-align: center; }
            QProgressBar::chunk { background-color: #4CAF50; border-radius: 2px; }
            QCheckBox { color: white; }
        """)
    
    def _browse_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select CSV File", "", "CSV Files (*.csv)")
        if path:
            self.csv_path = path
            self.file_label.setText(path)
            self.file_label.setStyleSheet("color: #4CAF50;")
            self._refresh_preview()
    
    def _refresh_preview(self):
        if not self.csv_path or not Path(self.csv_path).exists():
            self.preview_table.setRowCount(0)
            return
        
        try:
            with open(self.csv_path, 'r', encoding='utf-8-sig') as f:
                sample = f.read(4096)
                f.seek(0)
                delimiter = ';' if ';' in sample else ','
                reader = csv.DictReader(f, delimiter=delimiter)
                
                cols = ['User Vehicle', 'Track Name', 'Current QualRatio', 'Current RaceRatio']
                display_cols = [c for c in cols if c in reader.fieldnames]
                
                self.preview_table.setColumnCount(len(display_cols))
                self.preview_table.setHorizontalHeaderLabels(display_cols)
                
                rows = []
                for i, row in enumerate(reader):
                    if i >= 10:
                        break
                    rows.append(row)
                
                self.preview_table.setRowCount(len(rows))
                for i, row in enumerate(rows):
                    for j, col in enumerate(display_cols):
                        self.preview_table.setItem(i, j, QTableWidgetItem(str(row.get(col, ''))))
                
                self.preview_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
                
        except Exception as e:
            self.status_label.setText(f"Preview error: {e}")
    
    def _start_import(self):
        if not self.csv_path:
            QMessageBox.warning(self, "No File", "Please select a CSV file to import.")
            return
        
        self.import_btn.setVisible(False)
        self.cancel_btn.setVisible(True)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        
        self.worker = ImportWorker(
            self.db_path, self.csv_path,
            self.import_qual_cb.isChecked(),
            self.import_race_cb.isChecked()
        )
        self.worker.progress.connect(self._update_progress)
        self.worker.finished.connect(self._import_finished)
        self.worker.error.connect(self._import_error)
        self.worker.start()
    
    def _cancel_import(self):
        if self.worker:
            self.worker.stop()
            self.status_label.setText("Cancelling...")
    
    def _update_progress(self, current, total, message):
        if total > 0:
            percent = int((current / total) * 100)
            self.progress_bar.setValue(percent)
        self.status_label.setText(message)
    
    def _import_finished(self, result):
        self.import_btn.setVisible(True)
        self.cancel_btn.setVisible(False)
        self.progress_bar.setVisible(False)
        
        QMessageBox.information(self, "Import Complete", 
            f"Added {result['added']} data points from {result['total']} records.")
        self.status_label.setText(f"Import complete: {result['added']} points added")
        self.worker = None
    
    def _import_error(self, error_msg):
        self.import_btn.setVisible(True)
        self.cancel_btn.setVisible(False)
        self.progress_bar.setVisible(False)
        QMessageBox.critical(self, "Import Error", error_msg)
        self.worker = None


def main():
    app = QApplication(sys.argv)
    window = DataManagerWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
