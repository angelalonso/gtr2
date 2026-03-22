#!/usr/bin/env python3
"""
AIW Ratio Editor - Scans for AIW files, allows editing of QualRatio and RaceRatio values
with backup/restore functionality.
"""

import sys
import re
import shutil
from pathlib import Path
from datetime import datetime
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *

# Import configuration management
from cfg_manage import get_or_prompt_base_path, save_last_filter, load_last_filter, get_formulas_dir
# Import ratio calculator dialog
from ratio_gui import RatioCalculatorDialog
# Import global curve builder
from global_curve_builder import GlobalCurveBuilderDialog


class RatioItemDelegate(QStyledItemDelegate):
    """Custom delegate for ratio cells to handle editing"""
    def createEditor(self, parent, option, index):
        editor = QDoubleSpinBox(parent)
        editor.setRange(0.0, 10.0)
        editor.setDecimals(6)
        editor.setSingleStep(0.001)
        editor.setAlignment(Qt.AlignRight)
        return editor
    
    def setEditorData(self, editor, index):
        value = index.model().data(index, Qt.EditRole)
        if value and value != "(not found)":
            try:
                editor.setValue(float(value))
            except ValueError:
                editor.setValue(0.0)
        else:
            editor.setValue(1.0)
    
    def setModelData(self, editor, model, index):
        value = editor.value()
        model.setData(index, f"{value:.6f}", Qt.EditRole)


class Worker(QThread):
    """Worker thread for background tasks"""
    finished = pyqtSignal(object)
    progress = pyqtSignal(str)
    error = pyqtSignal(str)
    
    def __init__(self, fn, *args, **kwargs):
        super().__init__()
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
    
    def run(self):
        try:
            result = self.fn(*self.args, **self.kwargs)
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))


class EditableTableWidget(QTableWidget):
    """Custom table widget with editable ratio cells and per-row action buttons"""
    
    value_changed = pyqtSignal(int, str, str)
    save_row = pyqtSignal(int)
    restore_row = pyqtSignal(int)
    restore_from_backup_row = pyqtSignal(int)
    calc_row = pyqtSignal(int)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.modified_rows = set()
        self.original_values = {}
        self.has_backup = set()
        self.row_data = {}  # row_id -> {file_path, track_name, visual_row}
        self.next_row_id = 0
        self.setup_ui()
        
    def setup_ui(self):
        self.setColumnCount(4)
        self.setHorizontalHeaderLabels(["Track Name", "QualRatio", "RaceRatio", "Actions"])
        
        # Set column widths
        self.setColumnWidth(0, 400)
        self.setColumnWidth(1, 120)
        self.setColumnWidth(2, 120)
        self.setColumnWidth(3, 320)
        
        # Row height for buttons
        self.verticalHeader().setDefaultSectionSize(50)
        
        # Disable sorting to maintain row_id mapping
        self.setSortingEnabled(False)
        self.horizontalHeader().setSectionsClickable(False)
        
        # Styling
        self.setAlternatingRowColors(True)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        
        # Custom delegate for ratio columns
        self.setItemDelegateForColumn(1, RatioItemDelegate(self))
        self.setItemDelegateForColumn(2, RatioItemDelegate(self))
        
        # Connect signals
        self.itemChanged.connect(self.on_item_changed)
    
    def get_row_id(self, visual_row):
        """Get row ID for visual row index"""
        for row_id, data in self.row_data.items():
            if data.get('visual_row') == visual_row:
                return row_id
        return None
    
    def on_item_changed(self, item):
        """Handle item changes"""
        if item.column() in [1, 2]:
            visual_row = item.row()
            row_id = self.get_row_id(visual_row)
            if row_id is None:
                return
                
            ratio_type = "QualRatio" if item.column() == 1 else "RaceRatio"
            new_value = item.text()
            
            # Store original value
            if (row_id, ratio_type) not in self.original_values:
                self.original_values[(row_id, ratio_type)] = new_value
            
            self.modified_rows.add(row_id)
            item.setForeground(QBrush(QColor("#FFA500")))
            self.value_changed.emit(row_id, ratio_type, new_value)
            self.update_row_buttons(row_id)
    
    def update_row_buttons(self, row_id):
        """Update action buttons for a row"""
        data = self.row_data.get(row_id)
        if not data or data['visual_row'] < 0:
            return
            
        visual_row = data['visual_row']
        
        # Remove existing widget
        current_widget = self.cellWidget(visual_row, 3)
        if current_widget:
            current_widget.deleteLater()
        
        # Create button widget
        button_widget = QWidget()
        layout = QHBoxLayout(button_widget)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(4)
        
        track_name = data.get('track_name', 'Unknown')
        
        # Data&Calc button
        calc_btn = QPushButton("Data&Calc")
        calc_btn.setToolTip(f"Open data calculator for {track_name}")
        calc_btn.setFixedHeight(32)
        calc_btn.setFixedWidth(75)
        calc_btn.setCursor(Qt.PointingHandCursor)
        calc_btn.setStyleSheet("""
            QPushButton {
                background-color: #9C27B0;
                color: white;
                border: none;
                border-radius: 4px;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #7B1FA2; }
            QPushButton:pressed { background-color: #6A1B9A; }
        """)
        calc_btn.clicked.connect(lambda: self.calc_row.emit(row_id))
        layout.addWidget(calc_btn)
        
        # Save button (modified rows only)
        if row_id in self.modified_rows:
            save_btn = QPushButton("Save")
            save_btn.setToolTip(f"Save changes to: {data.get('file_path', 'Unknown')}")
            save_btn.setFixedHeight(32)
            save_btn.setFixedWidth(45)
            save_btn.setCursor(Qt.PointingHandCursor)
            save_btn.setStyleSheet("""
                QPushButton {
                    background-color: #4CAF50;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    font-size: 11px;
                    font-weight: bold;
                }
                QPushButton:hover { background-color: #45a049; }
                QPushButton:pressed { background-color: #3d8b40; }
            """)
            save_btn.clicked.connect(lambda: self.save_row.emit(row_id))
            layout.addWidget(save_btn)
            
            # Restore button (modified rows only)
            restore_btn = QPushButton("Restore")
            restore_btn.setToolTip(f"Restore to original session values")
            restore_btn.setFixedHeight(32)
            restore_btn.setFixedWidth(45)
            restore_btn.setCursor(Qt.PointingHandCursor)
            restore_btn.setStyleSheet("""
                QPushButton {
                    background-color: #FFA500;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    font-size: 11px;
                    font-weight: bold;
                }
                QPushButton:hover { background-color: #f39c12; }
                QPushButton:pressed { background-color: #e67e22; }
            """)
            restore_btn.clicked.connect(lambda: self.restore_row.emit(row_id))
            layout.addWidget(restore_btn)
        
        # Orig button (if backup exists)
        if row_id in self.has_backup:
            orig_btn = QPushButton("Orig")
            orig_btn.setToolTip(f"Restore from backup")
            orig_btn.setFixedHeight(32)
            orig_btn.setFixedWidth(40)
            orig_btn.setCursor(Qt.PointingHandCursor)
            orig_btn.setStyleSheet("""
                QPushButton {
                    background-color: #2196F3;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    font-size: 11px;
                    font-weight: bold;
                }
                QPushButton:hover { background-color: #1976D2; }
                QPushButton:pressed { background-color: #0D47A1; }
            """)
            orig_btn.clicked.connect(lambda: self.restore_from_backup_row.emit(row_id))
            layout.addWidget(orig_btn)
        
        layout.addStretch()
        self.setCellWidget(visual_row, 3, button_widget)
    
    def restore_row_value(self, row_id, ratio_type):
        """Restore a single value from session"""
        key = (row_id, ratio_type)
        if key not in self.original_values:
            return
            
        data = self.row_data.get(row_id)
        if not data or data['visual_row'] < 0:
            return
            
        visual_row = data['visual_row']
        col = 1 if ratio_type == "QualRatio" else 2
        
        item = self.item(visual_row, col)
        if item:
            item.setText(self.original_values[key])
            item.setForeground(QBrush(QColor("#ffffff")))
        
        del self.original_values[key]
        
        # Check if row still has modifications
        if not any(k[0] == row_id for k in self.original_values):
            self.modified_rows.discard(row_id)
        
        self.update_row_buttons(row_id)
    
    def clear_row_modifications(self, row_id):
        """Clear all modifications for a row"""
        self.modified_rows.discard(row_id)
        keys = [k for k in self.original_values if k[0] == row_id]
        for key in keys:
            del self.original_values[key]
        
        data = self.row_data.get(row_id)
        if data and data['visual_row'] >= 0:
            for col in [1, 2]:
                item = self.item(data['visual_row'], col)
                if item:
                    item.setForeground(QBrush(QColor("#ffffff")))
        
        self.update_row_buttons(row_id)
    
    def update_values_from_backup(self, row_id, qual_value, race_value):
        """Update display with values from backup"""
        data = self.row_data.get(row_id)
        if not data or data['visual_row'] < 0:
            return
            
        visual_row = data['visual_row']
        
        # Update values
        for col, value in [(1, qual_value), (2, race_value)]:
            if value is not None:
                item = self.item(visual_row, col)
                if item:
                    item.setText(f"{value:.6f}")
                    item.setForeground(QBrush(QColor("#2196F3")))
        
        # Clear modifications
        self.clear_row_modifications(row_id)
    
    def update_ratios(self, row_id, qual_ratio, race_ratio):
        """Update both ratios (used by calculator)"""
        data = self.row_data.get(row_id)
        if not data or data['visual_row'] < 0:
            return
            
        visual_row = data['visual_row']
        any_change = False
        
        for col, ratio, ratio_type in [(1, qual_ratio, "QualRatio"), (2, race_ratio, "RaceRatio")]:
            if ratio is not None:
                item = self.item(visual_row, col)
                if item:
                    old_value = item.text()
                    new_value = f"{ratio:.6f}"
                    
                    if old_value != new_value:
                        if (row_id, ratio_type) not in self.original_values:
                            self.original_values[(row_id, ratio_type)] = old_value
                        
                        item.setText(new_value)
                        item.setForeground(QBrush(QColor("#9C27B0")))
                        any_change = True
        
        if any_change:
            self.modified_rows.add(row_id)
            self.value_changed.emit(row_id, "QualRatio", qual_ratio)
            self.value_changed.emit(row_id, "RaceRatio", race_ratio)
        
        self.update_row_buttons(row_id)
    
    def add_row(self, track_name, qual_value, race_value, has_backup, aiw_path):
        """Add a new row to the table"""
        row_id = self.next_row_id
        self.next_row_id += 1
        visual_row = self.rowCount()
        
        # Store row data
        self.row_data[row_id] = {
            'visual_row': visual_row,
            'file_path': str(aiw_path),
            'track_name': track_name
        }
        
        self.insertRow(visual_row)
        self.blockSignals(True)
        
        # Track Name
        name_item = QTableWidgetItem(track_name)
        name_item.setFlags(name_item.flags() & ~Qt.ItemIsEditable)
        name_item.setToolTip(f"AIW File: {aiw_path}")
        name_item.setForeground(QBrush(QColor("#4CAF50" if track_name != Path(aiw_path).stem else "#FFA500")))
        self.setItem(visual_row, 0, name_item)
        
        # QualRatio
        if qual_value is not None:
            qual_item = QTableWidgetItem(f"{qual_value:.6f}")
        else:
            qual_item = QTableWidgetItem("(not found)")
            qual_item.setFlags(qual_item.flags() & ~Qt.ItemIsEditable)
            qual_item.setForeground(QBrush(QColor("#f44336")))
        self.setItem(visual_row, 1, qual_item)
        
        # RaceRatio
        if race_value is not None:
            race_item = QTableWidgetItem(f"{race_value:.6f}")
        else:
            race_item = QTableWidgetItem("(not found)")
            race_item.setFlags(race_item.flags() & ~Qt.ItemIsEditable)
            race_item.setForeground(QBrush(QColor("#f44336")))
        self.setItem(visual_row, 2, race_item)
        
        self.blockSignals(False)
        
        # Set backup status
        if has_backup:
            self.has_backup.add(row_id)
        
        self.update_row_buttons(row_id)
        return row_id
    
    def clear_all(self):
        """Clear all rows and data"""
        self.setRowCount(0)
        self.modified_rows.clear()
        self.original_values.clear()
        self.has_backup.clear()
        self.row_data.clear()
        self.next_row_id = 0
    
    def filter_rows(self, filter_text):
        """Filter rows based on track name - returns count of visible rows"""
        filter_text = filter_text.lower()
        visible_count = 0
        
        for visual_row in range(self.rowCount()):
            item = self.item(visual_row, 0)
            if item:
                should_show = not filter_text or filter_text in item.text().lower()
                self.setRowHidden(visual_row, not should_show)
                if should_show:
                    visible_count += 1
        
        return visible_count


class AIWRatioEditor(QMainWindow):
    def __init__(self, base_path):
        super().__init__()
        self.base_path = Path(base_path)
        self.aiw_files = []  # List of (aiw_path, gdb_path, track_name, row_id)
        self.backup_dir = Path("./backup_originals")
        self.scan_worker = None
        self.formulas_dir = get_formulas_dir()
        self.setup_ui()
        
        # Load last filter and apply it
        last_filter = load_last_filter()
        if last_filter:
            self.filter_edit.setText(last_filter)
            self.apply_filter()
        
        self.scan_files()
        
    def setup_ui(self):
        self.setWindowTitle(f"AIW Ratio Editor - Scanning: {self.base_path}")
        self.setGeometry(100, 100, 1250, 850)
        
        self.apply_dark_theme()
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # Header
        header = QWidget()
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 10)
        
        header_layout.addWidget(QLabel("Scanning: "))
        self.path_value = QLabel(str(self.base_path))
        self.path_value.setStyleSheet("color: #4CAF50; font-weight: bold;")
        header_layout.addWidget(self.path_value)
        header_layout.addStretch()
        
        self.stats_label = QLabel("")
        self.stats_label.setStyleSheet("color: #FFA500;")
        header_layout.addWidget(self.stats_label)
        
        main_layout.addWidget(header)
        
        # Global Curve Builder Button
        global_curve_widget = QWidget()
        global_curve_layout = QHBoxLayout(global_curve_widget)
        global_curve_layout.setContentsMargins(0, 0, 0, 10)
        
        self.global_curve_btn = QPushButton("📊 BUILD GLOBAL CURVE")
        self.global_curve_btn.setToolTip("Build a global curve from all track data")
        self.global_curve_btn.setFixedHeight(45)
        self.global_curve_btn.setCursor(Qt.PointingHandCursor)
        self.global_curve_btn.setStyleSheet("""
            QPushButton {
                background-color: #9C27B0;
                color: white;
                font-size: 14px;
                font-weight: bold;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #7B1FA2;
            }
        """)
        global_curve_layout.addWidget(self.global_curve_btn)
        global_curve_layout.addStretch()
        
        main_layout.addWidget(global_curve_widget)
        
        # Filter section
        filter_widget = QWidget()
        filter_layout = QHBoxLayout(filter_widget)
        filter_layout.setContentsMargins(0, 0, 0, 10)
        
        filter_layout.addWidget(QLabel("Filter by Track Name:"))
        
        self.filter_edit = QLineEdit()
        self.filter_edit.setPlaceholderText("Enter track name to filter...")
        self.filter_edit.setFixedHeight(28)
        self.filter_edit.setStyleSheet("""
            QLineEdit {
                background-color: #3c3c3c;
                color: white;
                border: 1px solid #555;
                border-radius: 4px;
                padding: 4px 8px;
            }
            QLineEdit:focus { border: 1px solid #4CAF50; }
        """)
        self.filter_edit.returnPressed.connect(self.save_and_apply_filter)
        filter_layout.addWidget(self.filter_edit)
        
        self.apply_filter_btn = QPushButton("Apply Filter")
        self.apply_filter_btn.setFixedHeight(28)
        self.apply_filter_btn.setFixedWidth(100)
        self.apply_filter_btn.setCursor(Qt.PointingHandCursor)
        self.apply_filter_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 4px;
                font-weight: bold;
                font-size: 11px;
            }
            QPushButton:hover { background-color: #45a049; }
        """)
        self.apply_filter_btn.clicked.connect(self.save_and_apply_filter)
        filter_layout.addWidget(self.apply_filter_btn)
        
        self.clear_filter_btn = QPushButton("Clear")
        self.clear_filter_btn.setFixedHeight(28)
        self.clear_filter_btn.setFixedWidth(60)
        self.clear_filter_btn.setCursor(Qt.PointingHandCursor)
        self.clear_filter_btn.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                border: none;
                border-radius: 4px;
                font-weight: bold;
                font-size: 11px;
            }
            QPushButton:hover { background-color: #d32f2f; }
        """)
        self.clear_filter_btn.clicked.connect(self.clear_filter)
        filter_layout.addWidget(self.clear_filter_btn)
        
        filter_layout.addStretch()
        
        filter_hint = QLabel("(Press Enter or click Apply to filter)")
        filter_hint.setStyleSheet("color: #888; font-style: italic; font-size: 10px;")
        filter_layout.addWidget(filter_hint)
        
        main_layout.addWidget(filter_widget)
        
        # Table
        self.table = EditableTableWidget()
        self.table.value_changed.connect(self.on_value_changed)
        self.table.save_row.connect(self.save_row)
        self.table.restore_row.connect(self.restore_row)
        self.table.restore_from_backup_row.connect(self.restore_from_backup)
        self.table.calc_row.connect(self.open_calculator)
        main_layout.addWidget(self.table)
        
        # Progress bar for scanning
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #555;
                border-radius: 3px;
                text-align: center;
                color: white;
            }
            QProgressBar::chunk {
                background-color: #4CAF50;
                border-radius: 2px;
            }
        """)
        main_layout.addWidget(self.progress_bar)
        
        # Button bar
        button_bar = QWidget()
        button_layout = QHBoxLayout(button_bar)
        button_layout.setContentsMargins(0, 10, 0, 0)
        button_layout.setSpacing(8)
        
        self.rescan_btn = QPushButton("Rescan")
        self.rescan_btn.setToolTip("Rescan for AIW files")
        self.rescan_btn.setFixedHeight(32)
        self.rescan_btn.setFixedWidth(100)
        self.rescan_btn.setCursor(Qt.PointingHandCursor)
        self.rescan_btn.clicked.connect(self.scan_files)
        self.rescan_btn.setStyleSheet(self.button_style("#4CAF50"))
        button_layout.addWidget(self.rescan_btn)
        
        self.save_all_btn = QPushButton("Save All Modified")
        self.save_all_btn.setToolTip("Save all modified rows")
        self.save_all_btn.setFixedHeight(32)
        self.save_all_btn.setFixedWidth(150)
        self.save_all_btn.setCursor(Qt.PointingHandCursor)
        self.save_all_btn.clicked.connect(self.save_all)
        self.save_all_btn.setStyleSheet(self.button_style("#4CAF50"))
        button_layout.addWidget(self.save_all_btn)
        
        self.restore_all_btn = QPushButton("Restore All Modified")
        self.restore_all_btn.setToolTip("Restore all modified rows to session values")
        self.restore_all_btn.setFixedHeight(32)
        self.restore_all_btn.setFixedWidth(170)
        self.restore_all_btn.setCursor(Qt.PointingHandCursor)
        self.restore_all_btn.clicked.connect(self.restore_all)
        self.restore_all_btn.setStyleSheet(self.button_style("#FFA500"))
        button_layout.addWidget(self.restore_all_btn)
        
        self.restore_all_backup_btn = QPushButton("Restore All from Backup")
        self.restore_all_backup_btn.setToolTip("Restore all files from backup")
        self.restore_all_backup_btn.setFixedHeight(32)
        self.restore_all_backup_btn.setFixedWidth(200)
        self.restore_all_backup_btn.setCursor(Qt.PointingHandCursor)
        self.restore_all_backup_btn.clicked.connect(self.restore_all_from_backup)
        self.restore_all_backup_btn.setStyleSheet(self.button_style("#2196F3"))
        button_layout.addWidget(self.restore_all_backup_btn)
        
        button_layout.addStretch()
        
        self.status_label = QLabel("Ready")
        self.status_label.setFixedHeight(32)
        self.status_label.setMinimumWidth(200)
        self.status_label.setStyleSheet("""
            QLabel {
                color: #888;
                font-style: italic;
                padding: 5px 10px;
                background-color: #3c3c3c;
                border-radius: 4px;
            }
        """)
        button_layout.addWidget(self.status_label)
        
        main_layout.addWidget(button_bar)
        
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")
        
        # Connect button
        self.global_curve_btn.clicked.connect(self.open_global_curve_builder)
    
    def button_style(self, color):
        return f"""
            QPushButton {{
                background-color: {color};
                color: white;
                border: none;
                border-radius: 4px;
                font-size: 12px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {self.darken_color(color)};
            }}
        """
    
    def darken_color(self, color):
        if color == "#4CAF50":
            return "#45a049"
        elif color == "#FFA500":
            return "#f39c12"
        elif color == "#2196F3":
            return "#1976D2"
        return color
    
    def apply_dark_theme(self):
        self.setStyleSheet("""
            QMainWindow, QDialog {
                background-color: #2b2b2b;
            }
            QTableWidget {
                background-color: #1e1e1e;
                alternate-background-color: #2b2b2b;
                gridline-color: #444;
                color: #ffffff;
                font-size: 12px;
            }
            QTableWidget::item {
                padding: 8px 5px;
            }
            QTableWidget::item:selected {
                background-color: #4CAF50;
            }
            QHeaderView::section {
                background-color: #3c3c3c;
                color: #4CAF50;
                padding: 8px;
                border: 1px solid #555;
                font-weight: bold;
            }
            QLabel {
                color: #ffffff;
            }
            QStatusBar {
                color: #ffffff;
                background-color: #3c3c3c;
                border-top: 1px solid #555;
            }
        """)
    
    def save_and_apply_filter(self):
        filter_text = self.filter_edit.text()
        save_last_filter(filter_text)
        self.apply_filter()
        self.status_bar.showMessage(f"Filter applied and saved: '{filter_text}'", 3000)
    
    def apply_filter(self):
        filter_text = self.filter_edit.text()
        visible = self.table.filter_rows(filter_text)
        total = self.table.rowCount()
        self.status_bar.showMessage(f"Filter: showing {visible} of {total} tracks")
    
    def clear_filter(self):
        self.filter_edit.clear()
        save_last_filter("")
        self.apply_filter()
        self.status_bar.showMessage("Filter cleared", 2000)
    
    def open_global_curve_builder(self):
        """Open the global curve builder dialog"""
        dialog = GlobalCurveBuilderDialog(self, self.formulas_dir)
        dialog.exec_()
    
    def find_matching_gdb(self, aiw_path):
        stem = aiw_path.stem
        for ext in ['.gdb', '.GDB']:
            exact = aiw_path.with_suffix(ext)
            if exact.exists():
                return exact
            
            for file in aiw_path.parent.glob(f"*{ext}"):
                if file.stem.lower() == stem.lower():
                    return file
        return None
    
    def extract_track_name(self, gdb_path):
        if not gdb_path or not gdb_path.exists():
            return None
            
        try:
            with open(gdb_path, 'rb') as f:
                data = f.read()
            
            try:
                content = data.decode('utf-8', errors='ignore')
            except:
                content = data.decode('latin-1', errors='ignore')
            
            match = re.search(r'TrackName\s*=\s*"([^"]+)"', content)
            if not match:
                match = re.search(r'TrackName\s*=\s*([^\n\r]+)', content)
            
            return match.group(1).strip() if match else None
        except Exception:
            return None
    
    def extract_ratios(self, aiw_path):
        qual_ratio = race_ratio = None
        
        try:
            with open(aiw_path, 'rb') as f:
                data = f.read()
            
            try:
                content = data.decode('utf-8', errors='ignore')
            except:
                content = data.decode('latin-1', errors='ignore')
            
            waypoint = re.search(r'\[Waypoint\](.*?)(?=\[|$)', content, re.DOTALL)
            section = waypoint.group(1) if waypoint else content
            
            for pattern, attr in [(r'QualRatio\s*=\s*\(?\s*([0-9.eE+-]+)\s*\)?', 'qual'),
                                   (r'RaceRatio\s*=\s*\(?\s*([0-9.eE+-]+)\s*\)?', 'race')]:
                match = re.search(pattern, section)
                if match:
                    try:
                        value = float(match.group(1))
                        if attr == 'qual':
                            qual_ratio = value
                        else:
                            race_ratio = value
                    except ValueError:
                        pass
        except Exception:
            pass
        
        return qual_ratio, race_ratio
    
    def check_backup_exists(self, aiw_path):
        return (self.backup_dir / f"{aiw_path.name}.original").exists()
    
    def create_backup(self, aiw_path):
        if not self.backup_dir.exists():
            self.backup_dir.mkdir(parents=True)
        
        backup_path = self.backup_dir / f"{aiw_path.name}.original"
        if not backup_path.exists():
            try:
                shutil.copy2(aiw_path, backup_path)
            except Exception:
                return False
        return True
    
    def restore_from_backup_file(self, aiw_path):
        backup_path = self.backup_dir / f"{aiw_path.name}.original"
        if not backup_path.exists():
            return False, "Backup file not found"
        
        try:
            shutil.copy2(backup_path, aiw_path)
            return True, "Successfully restored"
        except Exception as e:
            return False, str(e)
    
    def update_ratio_in_file(self, aiw_path, ratio_type, new_value):
        try:
            with open(aiw_path, 'rb') as f:
                data = f.read()
            
            try:
                content = data.decode('utf-8', errors='ignore')
            except:
                content = data.decode('latin-1', errors='ignore')
            
            pattern = rf'({ratio_type}\s*=\s*\(?)\s*[0-9.eE+-]+\s*(\)?)'
            
            def replacer(m):
                return f"{m.group(1)}{new_value:.6f}{m.group(2)}"
            
            new_content = re.sub(pattern, replacer, content)
            
            if new_content != content:
                with open(aiw_path, 'wb') as f:
                    f.write(new_content.encode('utf-8', errors='ignore'))
                return True
        except Exception:
            pass
        return False
    
    def scan_files(self):
        self.rescan_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)
        self.status_bar.showMessage("Scanning files...")
        
        self.scan_worker = Worker(self._scan_files_impl)
        self.scan_worker.finished.connect(self.on_scan_complete)
        self.scan_worker.error.connect(self.on_scan_error)
        self.scan_worker.start()
    
    def _scan_files_impl(self):
        locations_path = self.base_path / "GameData" / "Locations"
        results = []
        
        if not locations_path.exists():
            return None
        
        aiw_files = []
        seen = set()
        for ext in ['*.aiw', '*.AIW']:
            for f in locations_path.rglob(ext):
                if str(f).lower() not in seen:
                    seen.add(str(f).lower())
                    aiw_files.append(f)
        
        for aiw_path in sorted(aiw_files, key=lambda p: p.stem.lower()):
            gdb_path = self.find_matching_gdb(aiw_path)
            track_name = self.extract_track_name(gdb_path) or aiw_path.stem
            qual, race = self.extract_ratios(aiw_path)
            has_backup = self.check_backup_exists(aiw_path)
            
            results.append((aiw_path, gdb_path, track_name, qual, race, has_backup))
        
        return results
    
    def on_scan_complete(self, results):
        self.rescan_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        
        if results is None:
            QMessageBox.warning(self, "Path Not Found", 
                               f"Directory not found:\n{self.base_path / 'GameData' / 'Locations'}")
            self.stats_label.setText("Directory not found!")
            self.status_bar.showMessage("Scan failed")
            return
        
        if not results:
            QMessageBox.information(self, "No Files Found", 
                                   "No .aiw or .AIW files found.")
            self.status_bar.showMessage("No AIW files found")
            self.stats_label.setText("No files found")
            return
        
        self.table.clear_all()
        self.aiw_files.clear()
        
        missing_qual = missing_race = 0
        
        for aiw_path, gdb_path, track_name, qual, race, has_backup in results:
            row_id = self.table.add_row(track_name, qual, race, has_backup, aiw_path)
            self.aiw_files.append((aiw_path, gdb_path, track_name, row_id))
            
            if qual is None:
                missing_qual += 1
            if race is None:
                missing_race += 1
        
        stats = f"Found {len(results)} AIW files"
        if missing_qual or missing_race:
            stats += f" | Missing: Qual:{missing_qual} Race:{missing_race}"
        if self.table.has_backup:
            stats += f" | Backups: {len(self.table.has_backup)}"
        
        self.stats_label.setText(stats)
        self.status_bar.showMessage(f"Scan complete - found {len(results)} AIW files")
        
        self.apply_filter()
    
    def on_scan_error(self, error_msg):
        self.rescan_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        QMessageBox.critical(self, "Scan Error", f"Error during scan:\n{error_msg}")
        self.status_bar.showMessage("Scan failed")
    
    def on_value_changed(self, row_id, ratio_type, new_value):
        self.status_bar.showMessage(f"Row {row_id} {ratio_type} changed - unsaved", 3000)
    
    def save_row(self, row_id):
        file_info = next((info for info in self.aiw_files if info[3] == row_id), None)
        if not file_info:
            return
        
        aiw_path = file_info[0]
        
        if not self.create_backup(aiw_path):
            QMessageBox.warning(self, "Backup Failed", f"Could not create backup")
            return
        
        data = self.table.row_data.get(row_id)
        if not data or data['visual_row'] < 0:
            return
        
        success = 0
        keys = [k for k in self.table.original_values if k[0] == row_id]
        
        for _, ratio_type in keys:
            col = 1 if ratio_type == "QualRatio" else 2
            item = self.table.item(data['visual_row'], col)
            if item and item.text() != "(not found)":
                try:
                    val = float(item.text())
                    if self.update_ratio_in_file(aiw_path, ratio_type, val):
                        success += 1
                except ValueError:
                    pass
        
        if success:
            self.table.clear_row_modifications(row_id)
            self.table.has_backup.add(row_id)
            self.status_bar.showMessage(f"Saved {success} changes", 3000)
    
    def restore_row(self, row_id):
        keys = [k for k in self.table.original_values if k[0] == row_id]
        for r, ratio_type in keys:
            self.table.restore_row_value(row_id, ratio_type)
        if keys:
            self.status_bar.showMessage(f"Restored original values", 3000)
    
    def restore_from_backup(self, row_id):
        file_info = next((info for info in self.aiw_files if info[3] == row_id), None)
        if not file_info:
            return
        
        aiw_path, _, track_name, _ = file_info
        
        reply = QMessageBox.question(self, "Confirm Restore",
                                    f"Restore '{track_name}' from backup?",
                                    QMessageBox.Yes | QMessageBox.No)
        
        if reply != QMessageBox.Yes:
            return
        
        success, msg = self.restore_from_backup_file(aiw_path)
        if success:
            qual, race = self.extract_ratios(aiw_path)
            self.table.update_values_from_backup(row_id, qual, race)
            self.status_bar.showMessage(f"Restored from backup", 3000)
        else:
            QMessageBox.critical(self, "Restore Failed", msg)
    
    def save_all(self):
        modified = list(self.table.modified_rows)
        if not modified:
            QMessageBox.information(self, "No Changes", "No modified rows to save.")
            return
        
        success = fail = 0
        for row_id in modified:
            file_info = next((info for info in self.aiw_files if info[3] == row_id), None)
            if not file_info:
                continue
            
            if self.create_backup(file_info[0]):
                self.save_row(row_id)
                success += 1
            else:
                fail += 1
        
        if success:
            msg = f"Saved {success} files"
            if fail:
                msg += f", {fail} failed"
                QMessageBox.warning(self, "Partial Success", msg)
            else:
                QMessageBox.information(self, "Success", msg)
            self.status_bar.showMessage(msg, 3000)
    
    def restore_all(self):
        modified = list(self.table.modified_rows)
        if not modified:
            QMessageBox.information(self, "No Changes", "No modified rows to restore.")
            return
        
        reply = QMessageBox.question(self, "Confirm Restore All",
                                    "Restore all modified rows?",
                                    QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            for row_id in modified:
                keys = [k for k in self.table.original_values if k[0] == row_id]
                for r, ratio_type in keys:
                    self.table.restore_row_value(row_id, ratio_type)
            self.status_bar.showMessage(f"Restored {len(modified)} rows", 3000)
    
    def restore_all_from_backup(self):
        rows = list(self.table.has_backup)
        if not rows:
            QMessageBox.information(self, "No Backups", "No backup files found.")
            return
        
        reply = QMessageBox.question(self, "Confirm Restore All",
                                    f"Restore {len(rows)} files from backup?",
                                    QMessageBox.Yes | QMessageBox.No)
        
        if reply != QMessageBox.Yes:
            return
        
        success = fail = 0
        for row_id in rows:
            file_info = next((info for info in self.aiw_files if info[3] == row_id), None)
            if not file_info:
                continue
            
            ok, _ = self.restore_from_backup_file(file_info[0])
            if ok:
                qual, race = self.extract_ratios(file_info[0])
                self.table.update_values_from_backup(row_id, qual, race)
                success += 1
            else:
                fail += 1
        
        msg = f"Restored {success} files"
        if fail:
            msg += f", {fail} failed"
            QMessageBox.warning(self, "Partial Success", msg)
        else:
            QMessageBox.information(self, "Success", msg)
        self.status_bar.showMessage(msg, 3000)
    
    def open_calculator(self, row_id):
        file_info = next((info for info in self.aiw_files if info[3] == row_id), None)
        if not file_info:
            return
        
        _, _, track_name, _ = file_info
        data = self.table.row_data.get(row_id)
        if not data or data['visual_row'] < 0:
            return
        
        qual_item = self.table.item(data['visual_row'], 1)
        race_item = self.table.item(data['visual_row'], 2)
        
        def get_float(item, default):
            if item and item.text() != "(not found)":
                try:
                    return float(item.text())
                except ValueError:
                    pass
            return default
        
        current_qual = get_float(qual_item, 1.0)
        current_race = get_float(race_item, 1.0)
        
        dialog = RatioCalculatorDialog(self, track_name, current_qual, current_race)
        if dialog.exec_() == QDialog.Accepted:
            new_qual, new_race = dialog.get_ratios()
            self.table.update_ratios(row_id, new_qual, new_race)
            self.status_bar.showMessage(f"Updated ratios from calculator", 3000)


def main():
    base_path = get_or_prompt_base_path()
    if base_path is None:
        print("No path selected. Exiting.")
        return 1
    
    try:
        app = QApplication(sys.argv)
        editor = AIWRatioEditor(base_path)
        editor.show()
        return app.exec_()
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
