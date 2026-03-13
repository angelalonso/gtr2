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
from cfg_manage import get_or_prompt_base_path
# Import ratio calculator dialog
from ratio_gui import RatioCalculatorDialog


class RatioItemDelegate(QStyledItemDelegate):
    """Custom delegate for ratio cells to handle editing"""
    def __init__(self, parent=None):
        super().__init__(parent)
    
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
            editor.setValue(1.0)  # Default value
    
    def setModelData(self, editor, model, index):
        value = editor.value()
        model.setData(index, f"{value:.6f}", Qt.EditRole)


class EditableTableWidget(QTableWidget):
    """Custom table widget with editable ratio cells and per-row action buttons"""
    
    value_changed = pyqtSignal(int, str, str)  # row_id, ratio_type, new_value
    save_row = pyqtSignal(int)  # row_id
    restore_row = pyqtSignal(int)  # row_id - restore session changes
    restore_from_backup_row = pyqtSignal(int)  # row_id - restore from backup file
    calc_row = pyqtSignal(int)  # row_id - open ratio calculator
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.modified_rows = set()  # Track which row_ids have unsaved changes
        self.original_values = {}  # Store original values for each row: (row_id, type) -> value
        self.has_backup = set()  # Track which row_ids have backup files
        self.row_id_to_file = {}  # Map row_id to file path
        self.row_id_to_track = {}  # Map row_id to track name
        self.row_id_to_index = {}  # Map row_id to current visual index
        self.index_to_row_id = {}  # Map visual index to row_id
        self.next_row_id = 0  # Counter for generating unique row IDs
        self.setup_ui()
        
    def setup_ui(self):
        self.setColumnCount(4)
        self.setHorizontalHeaderLabels([
            "Track Name", 
            "QualRatio", 
            "RaceRatio", 
            "Actions"
        ])
        
        # Set column widths
        self.setColumnWidth(0, 400)  # Track Name
        self.setColumnWidth(1, 120)  # QualRatio
        self.setColumnWidth(2, 120)  # RaceRatio
        self.setColumnWidth(3, 300)  # Actions - wider for four buttons
        
        # Set row height to be taller for buttons
        self.verticalHeader().setDefaultSectionSize(50)
        
        # DISABLE SORTING - THIS FIXES THE ISSUE
        self.setSortingEnabled(False)
        
        # Also disable clickable headers to prevent any sorting attempts
        self.horizontalHeader().setSectionsClickable(False)
        self.horizontalHeader().setHighlightSections(False)
        
        # Table styling
        self.setAlternatingRowColors(True)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        
        # Set custom delegate for ratio columns
        self.setItemDelegateForColumn(1, RatioItemDelegate(self))
        self.setItemDelegateForColumn(2, RatioItemDelegate(self))
        
        # Connect signals
        self.itemChanged.connect(self.on_item_changed)
    
    def get_row_id_from_visual(self, visual_row):
        """Get the row ID for a visual row index"""
        return self.index_to_row_id.get(visual_row)
    
    def get_visual_row_from_id(self, row_id):
        """Get the visual row index for a row ID"""
        return self.row_id_to_index.get(row_id, -1)
    
    def on_item_changed(self, item):
        """Handle item changes"""
        if item.column() in [1, 2]:  # Only for ratio columns
            visual_row = item.row()
            row_id = self.get_row_id_from_visual(visual_row)
            if row_id is None:
                return
                
            ratio_type = "QualRatio" if item.column() == 1 else "RaceRatio"
            new_value = item.text()
            
            # Store original value if not already stored
            if (row_id, ratio_type) not in self.original_values:
                self.original_values[(row_id, ratio_type)] = new_value
            
            # Mark row as modified
            self.modified_rows.add(row_id)
            
            # Change text color to yellow
            item.setForeground(QBrush(QColor("#FFA500")))
            
            # Emit signal
            self.value_changed.emit(row_id, ratio_type, new_value)
            
            # Update action buttons for this row
            self.update_row_buttons_by_id(row_id)
    
    def update_row_buttons_by_id(self, row_id):
        """Update the action buttons for a specific row ID"""
        visual_row = self.get_visual_row_from_id(row_id)
        if visual_row < 0:
            return
            
        # Remove existing widget if any
        current_widget = self.cellWidget(visual_row, 3)
        if current_widget:
            current_widget.deleteLater()
        
        # Create button widget for this row
        button_widget = QWidget()
        button_layout = QHBoxLayout(button_widget)
        button_layout.setContentsMargins(2, 2, 2, 2)
        button_layout.setSpacing(4)
        
        # Get file path and track name for tooltips
        file_path = self.row_id_to_file.get(row_id, "Unknown file")
        track_name = self.row_id_to_track.get(row_id, "Unknown track")
        
        # Calc button (always visible)
        calc_btn = QPushButton("Calc")
        calc_btn.setToolTip(f"Open ratio calculator for {track_name}")
        calc_btn.setFixedHeight(32)
        calc_btn.setFixedWidth(45)
        calc_btn.setCursor(Qt.PointingHandCursor)
        calc_btn.setStyleSheet("""
            QPushButton {
                background-color: #9C27B0;
                color: white;
                border: none;
                border-radius: 4px;
                font-family: 'Segoe UI', 'Arial', sans-serif;
                font-size: 11px;
                font-weight: bold;
                text-align: center;
                padding: 2px 0px;
                margin: 0px;
            }
            QPushButton:hover {
                background-color: #7B1FA2;
            }
            QPushButton:pressed {
                background-color: #6A1B9A;
            }
        """)
        calc_btn.clicked.connect(lambda checked, r=row_id: self.calc_row.emit(r))
        button_layout.addWidget(calc_btn)
        
        # Save button (only for modified rows)
        if row_id in self.modified_rows:
            save_btn = QPushButton("Save")
            save_btn.setToolTip(f"Save changes to: {file_path}")
            save_btn.setFixedHeight(32)
            save_btn.setFixedWidth(45)
            save_btn.setCursor(Qt.PointingHandCursor)
            save_btn.setStyleSheet("""
                QPushButton {
                    background-color: #4CAF50;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    font-family: 'Segoe UI', 'Arial', sans-serif;
                    font-size: 11px;
                    font-weight: bold;
                    text-align: center;
                    padding: 2px 0px;
                    margin: 0px;
                }
                QPushButton:hover {
                    background-color: #45a049;
                }
                QPushButton:pressed {
                    background-color: #3d8b40;
                }
                QPushButton:disabled {
                    background-color: #666666;
                    color: #999999;
                }
            """)
            save_btn.clicked.connect(lambda checked, r=row_id: self.save_row.emit(r))
            button_layout.addWidget(save_btn)
        
        # Restore session button (only for modified rows)
        if row_id in self.modified_rows:
            restore_btn = QPushButton("Restore")
            restore_btn.setToolTip(f"Restore {track_name} to original session values")
            restore_btn.setFixedHeight(32)
            restore_btn.setFixedWidth(45)
            restore_btn.setCursor(Qt.PointingHandCursor)
            restore_btn.setStyleSheet("""
                QPushButton {
                    background-color: #FFA500;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    font-family: 'Segoe UI', 'Arial', sans-serif;
                    font-size: 11px;
                    font-weight: bold;
                    text-align: center;
                    padding: 2px 0px;
                    margin: 0px;
                }
                QPushButton:hover {
                    background-color: #f39c12;
                }
                QPushButton:pressed {
                    background-color: #e67e22;
                }
                QPushButton:disabled {
                    background-color: #666666;
                    color: #999999;
                }
            """)
            restore_btn.clicked.connect(lambda checked, r=row_id: self.restore_row.emit(r))
            button_layout.addWidget(restore_btn)
        
        # Restore from backup button (if backup exists) - ALWAYS show this if backup exists
        if row_id in self.has_backup:
            restore_backup_btn = QPushButton("Orig")
            restore_backup_btn.setToolTip(f"Restore {track_name} from backup: {file_path}.original")
            restore_backup_btn.setFixedHeight(32)
            restore_backup_btn.setFixedWidth(40)
            restore_backup_btn.setCursor(Qt.PointingHandCursor)
            restore_backup_btn.setStyleSheet("""
                QPushButton {
                    background-color: #2196F3;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    font-family: 'Segoe UI', 'Arial', sans-serif;
                    font-size: 11px;
                    font-weight: bold;
                    text-align: center;
                    padding: 2px 0px;
                    margin: 0px;
                }
                QPushButton:hover {
                    background-color: #1976D2;
                }
                QPushButton:pressed {
                    background-color: #0D47A1;
                }
                QPushButton:disabled {
                    background-color: #666666;
                    color: #999999;
                }
            """)
            restore_backup_btn.clicked.connect(lambda checked, r=row_id: self.restore_from_backup_row.emit(r))
            button_layout.addWidget(restore_backup_btn)
        
        button_layout.addStretch()
        
        self.setCellWidget(visual_row, 3, button_widget)
    
    def restore_row_value(self, row_id, ratio_type):
        """Restore a single value for a row from session"""
        key = (row_id, ratio_type)
        if key in self.original_values:
            original = self.original_values[key]
            col = 1 if ratio_type == "QualRatio" else 2
            
            visual_row = self.get_visual_row_from_id(row_id)
            if visual_row < 0:
                return
            
            # Update the item
            item = self.item(visual_row, col)
            if item:
                item.setText(original)
                item.setForeground(QBrush(QColor("#ffffff")))  # Back to white
            
            # Remove from original values
            del self.original_values[key]
            
            # Check if the row still has any modified values
            remaining = [k for k in self.original_values if k[0] == row_id]
            if not remaining:
                self.modified_rows.discard(row_id)
            
            self.update_row_buttons_by_id(row_id)
    
    def clear_row_modifications(self, row_id):
        """Clear all modifications for a row after save"""
        # Remove from modified rows
        self.modified_rows.discard(row_id)
        
        # Clear original values for this row
        keys_to_remove = [k for k in self.original_values if k[0] == row_id]
        for key in keys_to_remove:
            del self.original_values[key]
        
        visual_row = self.get_visual_row_from_id(row_id)
        if visual_row >= 0:
            # Reset text colors to white
            for col in [1, 2]:
                item = self.item(visual_row, col)
                if item:
                    item.setForeground(QBrush(QColor("#ffffff")))
        
        # Update action buttons
        self.update_row_buttons_by_id(row_id)
    
    def set_has_backup(self, row_id, has_backup):
        """Set whether a row has a backup file"""
        if has_backup:
            self.has_backup.add(row_id)
        else:
            self.has_backup.discard(row_id)
    
    def get_row_data(self, row_id):
        """Get all data for a row"""
        visual_row = self.get_visual_row_from_id(row_id)
        if visual_row < 0:
            return "", "", ""
            
        track_name = self.item(visual_row, 0).text() if self.item(visual_row, 0) else ""
        qual_ratio = self.item(visual_row, 1).text() if self.item(visual_row, 1) else "(not found)"
        race_ratio = self.item(visual_row, 2).text() if self.item(visual_row, 2) else "(not found)"
        return track_name, qual_ratio, race_ratio
    
    def set_file_path(self, row_id, aiw_path):
        """Store the AIW file path for a row"""
        self.row_id_to_file[row_id] = str(aiw_path)
        visual_row = self.get_visual_row_from_id(row_id)
        if visual_row >= 0:
            # Set tooltip for the track name cell
            track_item = self.item(visual_row, 0)
            if track_item:
                track_item.setToolTip(f"AIW File: {aiw_path}")
    
    def update_values_from_backup(self, row_id, qual_value, race_value):
        """Update the display with values from backup"""
        visual_row = self.get_visual_row_from_id(row_id)
        if visual_row < 0:
            return
            
        # Update QualRatio
        qual_item = self.item(visual_row, 1)
        if qual_item and qual_value is not None:
            qual_item.setText(f"{qual_value:.6f}")
            qual_item.setForeground(QBrush(QColor("#2196F3")))  # Blue to indicate from backup
        
        # Update RaceRatio
        race_item = self.item(visual_row, 2)
        if race_item and race_value is not None:
            race_item.setText(f"{race_value:.6f}")
            race_item.setForeground(QBrush(QColor("#2196F3")))  # Blue to indicate from backup
        
        # Clear any session modifications for this row
        keys_to_remove = [k for k in self.original_values if k[0] == row_id]
        for key in keys_to_remove:
            del self.original_values[key]
        self.modified_rows.discard(row_id)
        
        # Update buttons
        self.update_row_buttons_by_id(row_id)
    
    def update_ratios(self, row_id, qual_ratio, race_ratio):
        """Update both ratios for a row (used by calculator)"""
        visual_row = self.get_visual_row_from_id(row_id)
        if visual_row < 0:
            return
            
        any_change = False
        
        # Update QualRatio
        qual_item = self.item(visual_row, 1)
        if qual_item and qual_ratio is not None:
            old_value = qual_item.text()
            new_value = f"{qual_ratio:.6f}"
            
            if old_value != new_value:
                # Store original value if not already stored
                if (row_id, "QualRatio") not in self.original_values:
                    self.original_values[(row_id, "QualRatio")] = old_value
                
                qual_item.setText(new_value)
                qual_item.setForeground(QBrush(QColor("#9C27B0")))  # Purple to indicate from calculator
                any_change = True
        
        # Update RaceRatio
        race_item = self.item(visual_row, 2)
        if race_item and race_ratio is not None:
            old_value = race_item.text()
            new_value = f"{race_ratio:.6f}"
            
            if old_value != new_value:
                # Store original value if not already stored
                if (row_id, "RaceRatio") not in self.original_values:
                    self.original_values[(row_id, "RaceRatio")] = old_value
                
                race_item.setText(new_value)
                race_item.setForeground(QBrush(QColor("#9C27B0")))  # Purple to indicate from calculator
                any_change = True
        
        # Mark as modified if any value changed
        if any_change:
            self.modified_rows.add(row_id)
            # Update action buttons for this row
            self.update_row_buttons_by_id(row_id)
            
            # Emit signals for any changed values
            if qual_ratio is not None and qual_item:
                self.value_changed.emit(row_id, "QualRatio", qual_item.text())
            if race_ratio is not None and race_item:
                self.value_changed.emit(row_id, "RaceRatio", race_item.text())
        else:
            # Even if no change, we should still update buttons to ensure they're correct
            self.update_row_buttons_by_id(row_id)
    
    def populate_row(self, row_id, track_name, qual_value, race_value, has_backup, aiw_path):
        """Populate a row with initial data - this should not trigger modified state"""
        visual_row = self.rowCount()  # New row at the end
        
        # Store mappings and data
        self.row_id_to_index[row_id] = visual_row
        self.index_to_row_id[visual_row] = row_id
        self.row_id_to_file[row_id] = str(aiw_path)
        self.row_id_to_track[row_id] = track_name
        
        # Insert the row
        self.insertRow(visual_row)
        
        # Block signals to prevent itemChanged from firing
        self.blockSignals(True)
        
        # Track Name (read-only)
        name_item = QTableWidgetItem(track_name)
        name_item.row_id = row_id  # Store row_id in the item
        name_item.setFlags(name_item.flags() & ~Qt.ItemIsEditable)
        if track_name == Path(aiw_path).stem:
            name_item.setForeground(QBrush(QColor("#FFA500")))  # Orange for fallback
        else:
            name_item.setForeground(QBrush(QColor("#4CAF50")))  # Green for real track name
        
        # Set tooltip with full AIW file path
        name_item.setToolTip(f"AIW File: {aiw_path}")
        self.setItem(visual_row, 0, name_item)
        
        # QualRatio (editable)
        if qual_value is not None:
            qual_item = QTableWidgetItem(f"{qual_value:.6f}")
        else:
            qual_item = QTableWidgetItem("(not found)")
            qual_item.setFlags(qual_item.flags() & ~Qt.ItemIsEditable)  # Make read-only if not found
            qual_item.setForeground(QBrush(QColor("#f44336")))
        self.setItem(visual_row, 1, qual_item)
        
        # RaceRatio (editable)
        if race_value is not None:
            race_item = QTableWidgetItem(f"{race_value:.6f}")
        else:
            race_item = QTableWidgetItem("(not found)")
            race_item.setFlags(race_item.flags() & ~Qt.ItemIsEditable)  # Make read-only if not found
            race_item.setForeground(QBrush(QColor("#f44336")))
        self.setItem(visual_row, 2, race_item)
        
        # Unblock signals
        self.blockSignals(False)
        
        # Set backup status (without triggering button update yet)
        if has_backup:
            self.has_backup.add(row_id)
        else:
            self.has_backup.discard(row_id)
        
        # Now create the initial buttons
        self.update_row_buttons_by_id(row_id)
    
    def clear_table(self):
        """Clear all rows and mappings"""
        self.setRowCount(0)
        self.modified_rows.clear()
        self.original_values.clear()
        self.has_backup.clear()
        self.row_id_to_file.clear()
        self.row_id_to_track.clear()
        self.row_id_to_index.clear()
        self.index_to_row_id.clear()
    
    def filter_rows(self, filter_text):
        """Filter rows based on track name"""
        filter_text = filter_text.lower()
        
        for visual_row in range(self.rowCount()):
            item = self.item(visual_row, 0)
            if item:
                track_name = item.text().lower()
                should_show = filter_text in track_name if filter_text else True
                self.setRowHidden(visual_row, not should_show)


class AIWRatioEditor(QMainWindow):
    def __init__(self, base_path):
        super().__init__()
        self.base_path = Path(base_path)
        self.aiw_files = []  # List of (aiw_path, gdb_path, track_name, row_id)
        self.backup_dir = Path("./backup_originals")
        self.setup_ui()
        self.scan_files()
        
    def setup_ui(self):
        self.setWindowTitle(f"AIW Ratio Editor - Scanning: {self.base_path}")
        self.setGeometry(100, 100, 1250, 850)  # Taller for filter box
        
        self.apply_dark_theme()
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # Header with path info
        header_widget = QWidget()
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(0, 0, 0, 10)
        
        path_label = QLabel(f"Scanning: ")
        path_label.setStyleSheet("color: #888; font-size: 12px;")
        header_layout.addWidget(path_label)
        
        self.path_value = QLabel(str(self.base_path))
        self.path_value.setStyleSheet("color: #4CAF50; font-weight: bold; font-size: 12px;")
        header_layout.addWidget(self.path_value)
        
        header_layout.addStretch()
        
        self.stats_label = QLabel("")
        self.stats_label.setStyleSheet("color: #FFA500; font-size: 12px;")
        header_layout.addWidget(self.stats_label)
        
        main_layout.addWidget(header_widget)
        
        # Filter section
        filter_widget = QWidget()
        filter_layout = QHBoxLayout(filter_widget)
        filter_layout.setContentsMargins(0, 0, 0, 10)
        
        filter_label = QLabel("Filter by Track Name:")
        filter_label.setStyleSheet("color: #888; font-size: 12px;")
        filter_layout.addWidget(filter_label)
        
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
                font-size: 12px;
            }
            QLineEdit:focus {
                border: 1px solid #4CAF50;
            }
        """)
        self.filter_edit.textChanged.connect(self.on_filter_changed)
        filter_layout.addWidget(self.filter_edit)
        
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
                font-size: 11px;
                font-weight: bold;
                padding: 4px 8px;
            }
            QPushButton:hover {
                background-color: #d32f2f;
            }
            QPushButton:pressed {
                background-color: #b71c1c;
            }
        """)
        self.clear_filter_btn.clicked.connect(self.clear_filter)
        filter_layout.addWidget(self.clear_filter_btn)
        
        filter_layout.addStretch()
        
        main_layout.addWidget(filter_widget)
        
        # Create table
        self.table = EditableTableWidget()
        self.table.value_changed.connect(self.on_value_changed)
        self.table.save_row.connect(self.save_row)
        self.table.restore_row.connect(self.restore_row)
        self.table.restore_from_backup_row.connect(self.restore_from_backup)
        self.table.calc_row.connect(self.open_calculator)
        
        main_layout.addWidget(self.table)
        
        # Bottom button bar
        button_bar = QWidget()
        button_layout = QHBoxLayout(button_bar)
        button_layout.setContentsMargins(0, 10, 0, 0)
        button_layout.setSpacing(8)  # Consistent spacing between buttons
        
        # Create buttons with explicit fixed sizes and text
        self.rescan_btn = QPushButton("Rescan")
        self.rescan_btn.setToolTip("Rescan for AIW files")
        self.rescan_btn.setFixedHeight(32)
        self.rescan_btn.setFixedWidth(100)
        self.rescan_btn.setCursor(Qt.PointingHandCursor)
        self.rescan_btn.clicked.connect(self.scan_files)
        self.rescan_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 4px;
                font-family: 'Segoe UI', 'Arial', sans-serif;
                font-size: 12px;
                font-weight: bold;
                text-align: center;
                padding: 5px 10px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
            }
        """)
        button_layout.addWidget(self.rescan_btn)
        
        self.save_all_btn = QPushButton("Save All Modified")
        self.save_all_btn.setToolTip("Save all modified rows")
        self.save_all_btn.setFixedHeight(32)
        self.save_all_btn.setFixedWidth(150)
        self.save_all_btn.setCursor(Qt.PointingHandCursor)
        self.save_all_btn.clicked.connect(self.save_all)
        self.save_all_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 4px;
                font-family: 'Segoe UI', 'Arial', sans-serif;
                font-size: 12px;
                font-weight: bold;
                text-align: center;
                padding: 5px 10px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
            }
        """)
        button_layout.addWidget(self.save_all_btn)
        
        self.restore_all_btn = QPushButton("Restore All Modified")
        self.restore_all_btn.setToolTip("Restore all modified rows to session values")
        self.restore_all_btn.setFixedHeight(32)
        self.restore_all_btn.setFixedWidth(170)
        self.restore_all_btn.setCursor(Qt.PointingHandCursor)
        self.restore_all_btn.clicked.connect(self.restore_all)
        self.restore_all_btn.setStyleSheet("""
            QPushButton {
                background-color: #FFA500;
                color: white;
                border: none;
                border-radius: 4px;
                font-family: 'Segoe UI', 'Arial', sans-serif;
                font-size: 12px;
                font-weight: bold;
                text-align: center;
                padding: 5px 10px;
            }
            QPushButton:hover {
                background-color: #f39c12;
            }
            QPushButton:pressed {
                background-color: #e67e22;
            }
        """)
        button_layout.addWidget(self.restore_all_btn)
        
        self.restore_all_backup_btn = QPushButton("Restore All from Backup")
        self.restore_all_backup_btn.setToolTip("Restore all files from backup")
        self.restore_all_backup_btn.setFixedHeight(32)
        self.restore_all_backup_btn.setFixedWidth(200)
        self.restore_all_backup_btn.setCursor(Qt.PointingHandCursor)
        self.restore_all_backup_btn.clicked.connect(self.restore_all_from_backup)
        self.restore_all_backup_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                border-radius: 4px;
                font-family: 'Segoe UI', 'Arial', sans-serif;
                font-size: 12px;
                font-weight: bold;
                text-align: center;
                padding: 5px 10px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
            QPushButton:pressed {
                background-color: #0D47A1;
            }
        """)
        button_layout.addWidget(self.restore_all_backup_btn)
        
        button_layout.addStretch()
        
        # Status label with explicit styling
        self.status_label = QLabel("Ready")
        self.status_label.setFixedHeight(32)
        self.status_label.setMinimumWidth(200)
        self.status_label.setStyleSheet("""
            QLabel {
                color: #888;
                font-style: italic;
                font-size: 12px;
                padding: 5px 10px;
                background-color: #3c3c3c;
                border-radius: 4px;
            }
        """)
        button_layout.addWidget(self.status_label)
        
        main_layout.addWidget(button_bar)
        
        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")
    
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
                font-family: 'Segoe UI', 'Arial', sans-serif;
                font-size: 12px;
            }
            QTableWidget::item {
                padding: 8px 5px;
            }
            QTableWidget::item:selected {
                background-color: #4CAF50;
                color: #ffffff;
            }
            QHeaderView::section {
                background-color: #3c3c3c;
                color: #4CAF50;
                padding: 8px;
                border: 1px solid #555;
                font-weight: bold;
                font-family: 'Segoe UI', 'Arial', sans-serif;
                font-size: 12px;
            }
            QLabel {
                color: #ffffff;
                font-family: 'Segoe UI', 'Arial', sans-serif;
                font-size: 12px;
            }
            QStatusBar {
                color: #ffffff;
                background-color: #3c3c3c;
                border-top: 1px solid #555;
                font-family: 'Segoe UI', 'Arial', sans-serif;
                font-size: 12px;
            }
            QDoubleSpinBox {
                background-color: #3c3c3c;
                color: #ffffff;
                border: 1px solid #4CAF50;
                border-radius: 3px;
                padding: 2px;
                font-family: 'Segoe UI', 'Arial', sans-serif;
                font-size: 12px;
            }
        """)
    
    def on_filter_changed(self, text):
        """Handle filter text changes"""
        self.table.filter_rows(text)
        
        # Update status to show filtered count
        total_rows = self.table.rowCount()
        visible_rows = sum(1 for i in range(total_rows) if not self.table.isRowHidden(i))
        if text:
            self.status_bar.showMessage(f"Filter: showing {visible_rows} of {total_rows} tracks")
        else:
            self.status_bar.showMessage(f"Showing all {total_rows} tracks")
    
    def clear_filter(self):
        """Clear the filter text"""
        self.filter_edit.clear()
    
    def find_matching_gdb(self, aiw_path):
        """Find matching GDB file regardless of case"""
        stem = aiw_path.stem
        
        for ext in ['.gdb', '.GDB']:
            exact_match = aiw_path.with_suffix(ext)
            if exact_match.exists():
                return exact_match
            
            directory = aiw_path.parent
            pattern = f"*{ext}"
            for file in directory.glob(pattern):
                if file.stem.lower() == stem.lower():
                    return file
        
        return None
    
    def extract_track_name(self, gdb_path):
        """Extract TrackName from GDB file"""
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
            
            if match:
                return match.group(1).strip()
        except Exception as e:
            print(f"Error reading GDB file {gdb_path}: {e}")
        
        return None
    
    def extract_ratios(self, aiw_path):
        """Extract QualRatio and RaceRatio from AIW file"""
        qual_ratio = None
        race_ratio = None
        
        try:
            with open(aiw_path, 'rb') as f:
                data = f.read()
            
            try:
                content = data.decode('utf-8', errors='ignore')
            except:
                content = data.decode('latin-1', errors='ignore')
            
            # Look for the [Waypoint] section
            waypoint_match = re.search(r'\[Waypoint\](.*?)(?=\[|$)', content, re.DOTALL)
            if waypoint_match:
                waypoint_section = waypoint_match.group(1)
                
                # Look for QualRatio
                qual_match = re.search(r'QualRatio\s*=\s*\(?\s*([0-9.eE+-]+)\s*\)?', waypoint_section)
                if qual_match:
                    try:
                        qual_ratio = float(qual_match.group(1))
                    except ValueError:
                        pass
                
                # Look for RaceRatio
                race_match = re.search(r'RaceRatio\s*=\s*\(?\s*([0-9.eE+-]+)\s*\)?', waypoint_section)
                if race_match:
                    try:
                        race_ratio = float(race_match.group(1))
                    except ValueError:
                        pass
            
            # Fallback to whole file search
            if qual_ratio is None:
                qual_match = re.search(r'QualRatio\s*=\s*\(?\s*([0-9.eE+-]+)\s*\)?', content)
                if qual_match:
                    try:
                        qual_ratio = float(qual_match.group(1))
                    except ValueError:
                        pass
            
            if race_ratio is None:
                race_match = re.search(r'RaceRatio\s*=\s*\(?\s*([0-9.eE+-]+)\s*\)?', content)
                if race_match:
                    try:
                        race_ratio = float(race_match.group(1))
                    except ValueError:
                        pass
                    
        except Exception as e:
            print(f"Error reading AIW file {aiw_path}: {e}")
        
        return qual_ratio, race_ratio
    
    def check_backup_exists(self, aiw_path):
        """Check if a backup file exists for the given AIW file"""
        backup_path = self.backup_dir / f"{aiw_path.name}.original"
        return backup_path.exists()
    
    def create_backup(self, aiw_path):
        """Create a backup of the original AIW file if it doesn't exist"""
        if not self.backup_dir.exists():
            self.backup_dir.mkdir(parents=True)
        
        backup_path = self.backup_dir / f"{aiw_path.name}.original"
        
        # Only create backup if it doesn't exist
        if not backup_path.exists():
            try:
                shutil.copy2(aiw_path, backup_path)
                return True
            except Exception as e:
                print(f"Failed to create backup for {aiw_path}: {e}")
                return False
        return True
    
    def restore_from_backup_file(self, aiw_path):
        """Restore an AIW file from its backup"""
        backup_path = self.backup_dir / f"{aiw_path.name}.original"
        
        if not backup_path.exists():
            return False, "Backup file not found"
        
        try:
            shutil.copy2(backup_path, aiw_path)
            return True, "Successfully restored from backup"
        except Exception as e:
            return False, f"Failed to restore: {e}"
    
    def update_ratio_in_file(self, aiw_path, ratio_type, new_value):
        """Update a ratio value in the AIW file"""
        try:
            with open(aiw_path, 'rb') as f:
                data = f.read()
            
            try:
                content = data.decode('utf-8', errors='ignore')
            except:
                content = data.decode('latin-1', errors='ignore')
            
            # Pattern to match the ratio line
            pattern = rf'({ratio_type}\s*=\s*\(?)\s*[0-9.eE+-]+\s*(\)?)'
            
            # Format the new value (with parentheses if they were present)
            def replacer(match):
                prefix = match.group(1)
                suffix = match.group(2) if len(match.groups()) > 1 else ''
                return f"{prefix}{new_value:.6f}{suffix}"
            
            new_content = re.sub(pattern, replacer, content, flags=re.MULTILINE)
            
            if new_content != content:
                # Write back the file (preserving original encoding)
                with open(aiw_path, 'wb') as f:
                    f.write(new_content.encode('utf-8', errors='ignore'))
                return True
            else:
                print(f"Pattern not found in {aiw_path}")
                return False
                
        except Exception as e:
            print(f"Error updating file {aiw_path}: {e}")
            return False
    
    def scan_files(self):
        """Scan for AIW files and extract data"""
        self.status_bar.showMessage("Scanning files...")
        self.table.clear_table()
        
        self.aiw_files = []
        locations_path = self.base_path / "GameData" / "Locations"
        
        if not locations_path.exists():
            QMessageBox.warning(
                self, 
                "Path Not Found", 
                f"Directory not found:\n{locations_path}\n\nPlease check the path and try again."
            )
            self.status_bar.showMessage("Scan failed - directory not found")
            self.stats_label.setText("Directory not found!")
            return
        
        # Find all AIW files recursively
        aiw_files = []
        seen_paths = set()
        for ext in ['*.aiw', '*.AIW']:
            for file_path in locations_path.rglob(ext):
                file_path_lower = str(file_path).lower()
                if file_path_lower not in seen_paths:
                    seen_paths.add(file_path_lower)
                    aiw_files.append(file_path)
        
        if not aiw_files:
            QMessageBox.information(
                self,
                "No Files Found",
                f"No .aiw or .AIW files found in:\n{locations_path}"
            )
            self.status_bar.showMessage("No AIW files found")
            self.stats_label.setText("No files found")
            return
        
        for aiw_path in sorted(aiw_files, key=lambda p: p.stem.lower()):
            # Find matching GDB file
            gdb_path = self.find_matching_gdb(aiw_path)
            
            # Extract track name
            track_name = self.extract_track_name(gdb_path)
            if track_name is None:
                track_name = aiw_path.stem
            
            # Extract ratios
            qual_ratio, race_ratio = self.extract_ratios(aiw_path)
            
            # Generate unique row ID
            row_id = self.table.next_row_id
            self.table.next_row_id += 1
            
            # Store file info with row_id
            self.aiw_files.append((aiw_path, gdb_path, track_name, row_id))
            
            # Check if backup exists
            has_backup = self.check_backup_exists(aiw_path)
            
            # Add to table using the new populate_row method
            self.table.populate_row(row_id, track_name, qual_ratio, race_ratio, has_backup, aiw_path)
        
        # Update stats
        stats_text = f"Found {len(aiw_files)} AIW files"
        missing_qual = 0
        missing_race = 0
        
        for visual_row in range(self.table.rowCount()):
            if self.table.item(visual_row, 1).text() == "(not found)":
                missing_qual += 1
            if self.table.item(visual_row, 2).text() == "(not found)":
                missing_race += 1
        
        backup_count = len(self.table.has_backup)
        
        if missing_qual > 0 or missing_race > 0:
            stats_text += f" | Missing ratios: Qual:{missing_qual} Race:{missing_race}"
        
        if backup_count > 0:
            stats_text += f" | Backups: {backup_count}"
        
        self.stats_label.setText(stats_text)
        self.status_bar.showMessage(f"Scan complete - found {len(aiw_files)} AIW files")
    
    def on_value_changed(self, row_id, ratio_type, new_value):
        """Handle value change in table"""
        self.status_bar.showMessage(f"Row {row_id} {ratio_type} changed to {new_value} - unsaved", 3000)
    
    def save_row(self, row_id):
        """Save changes for a specific row"""
        track_name, qual_ratio, race_ratio = self.table.get_row_data(row_id)
        
        # Find the file info with this row_id
        file_info = None
        for info in self.aiw_files:
            if info[3] == row_id:
                file_info = info
                break
        
        if file_info is None:
            self.status_bar.showMessage(f"Error: Invalid row ID", 3000)
            return
        
        aiw_path, gdb_path, _, _ = file_info
        
        # Create backup if needed
        if not self.create_backup(aiw_path):
            QMessageBox.warning(self, "Backup Failed", f"Could not create backup for {aiw_path.name}")
            return
        
        # Update values
        success_count = 0
        modified_keys = [k for k in self.table.original_values if k[0] == row_id]
        
        for (r, ratio_type) in modified_keys:
            visual_row = self.table.get_visual_row_from_id(row_id)
            if visual_row < 0:
                continue
                
            new_value = self.table.item(visual_row, 1 if ratio_type == "QualRatio" else 2).text()
            
            if new_value != "(not found)":
                try:
                    float_val = float(new_value)
                    if self.update_ratio_in_file(aiw_path, ratio_type, float_val):
                        success_count += 1
                except ValueError:
                    pass
        
        if success_count > 0:
            self.table.clear_row_modifications(row_id)
            # Update backup status
            self.table.set_has_backup(row_id, True)
            self.status_bar.showMessage(f"Saved {success_count} changes to {aiw_path.name}", 3000)
        else:
            self.status_bar.showMessage(f"No changes saved for {aiw_path.name}", 3000)
    
    def restore_row(self, row_id):
        """Restore original values for a specific row (from current session)"""
        modified_keys = [k for k in self.table.original_values if k[0] == row_id]
        
        for (r, ratio_type) in modified_keys:
            self.table.restore_row_value(row_id, ratio_type)
        
        if modified_keys:
            self.status_bar.showMessage(f"Restored original values for row {row_id}", 3000)
    
    def restore_from_backup(self, row_id):
        """Restore a specific row from its backup file"""
        # Find the file info with this row_id
        file_info = None
        for info in self.aiw_files:
            if info[3] == row_id:
                file_info = info
                break
        
        if file_info is None:
            self.status_bar.showMessage(f"Error: Invalid row ID", 3000)
            return
        
        aiw_path, _, track_name, _ = file_info
        
        # Confirm with user
        reply = QMessageBox.question(
            self, 
            "Confirm Restore from Backup",
            f"Restore '{track_name}' from its backup file?\n\n"
            f"This will overwrite any changes you've made.",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
        
        # Restore from backup
        success, message = self.restore_from_backup_file(aiw_path)
        
        if success:
            # Reload the ratios from the restored file
            qual_ratio, race_ratio = self.extract_ratios(aiw_path)
            self.table.update_values_from_backup(row_id, qual_ratio, race_ratio)
            self.status_bar.showMessage(f"Restored {aiw_path.name} from backup", 3000)
        else:
            QMessageBox.critical(self, "Restore Failed", f"Failed to restore from backup:\n{message}")
    
    def save_all(self):
        """Save all modified rows"""
        modified_rows = list(self.table.modified_rows)
        if not modified_rows:
            QMessageBox.information(self, "No Changes", "No modified rows to save.")
            return
        
        success_count = 0
        fail_count = 0
        
        for row_id in modified_rows:
            # Find the file info with this row_id
            file_info = None
            for info in self.aiw_files:
                if info[3] == row_id:
                    file_info = info
                    break
            
            if file_info is None:
                continue
                
            aiw_path, _, _, _ = file_info
            
            # Create backup if needed
            if not self.create_backup(aiw_path):
                fail_count += 1
                continue
            
            # Update values
            row_success = 0
            modified_keys = [k for k in self.table.original_values if k[0] == row_id]
            
            visual_row = self.table.get_visual_row_from_id(row_id)
            if visual_row < 0:
                continue
                
            for (r, ratio_type) in modified_keys:
                new_value = self.table.item(visual_row, 1 if ratio_type == "QualRatio" else 2).text()
                
                if new_value != "(not found)":
                    try:
                        float_val = float(new_value)
                        if self.update_ratio_in_file(aiw_path, ratio_type, float_val):
                            row_success += 1
                    except ValueError:
                        pass
            
            if row_success > 0:
                success_count += 1
                self.table.clear_row_modifications(row_id)
                self.table.set_has_backup(row_id, True)
            else:
                fail_count += 1
        
        if success_count > 0:
            self.status_bar.showMessage(f"Saved {success_count} files successfully", 3000)
            if fail_count > 0:
                QMessageBox.warning(self, "Partial Success", 
                                   f"Saved {success_count} files.\n{fail_count} files failed.")
        else:
            QMessageBox.critical(self, "Save Failed", "Failed to save any files.")
    
    def restore_all(self):
        """Restore all modified rows to their original values"""
        modified_rows = list(self.table.modified_rows)
        if not modified_rows:
            QMessageBox.information(self, "No Changes", "No modified rows to restore.")
            return
        
        reply = QMessageBox.question(self, "Confirm Restore All",
                                    "Restore all modified rows to their original (session) values?",
                                    QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            for row_id in modified_rows:
                modified_keys = [k for k in self.table.original_values if k[0] == row_id]
                for (r, ratio_type) in modified_keys:
                    self.table.restore_row_value(row_id, ratio_type)
            
            self.status_bar.showMessage(f"Restored {len(modified_rows)} rows", 3000)
    
    def restore_all_from_backup(self):
        """Restore all rows that have backups from their backup files"""
        rows_with_backup = list(self.table.has_backup)
        if not rows_with_backup:
            QMessageBox.information(self, "No Backups", "No backup files found to restore from.")
            return
        
        reply = QMessageBox.question(
            self, 
            "Confirm Restore All from Backup",
            f"Restore {len(rows_with_backup)} files from their backups?\n\n"
            f"This will overwrite any changes you've made.",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
        
        success_count = 0
        fail_count = 0
        
        for row_id in rows_with_backup:
            # Find the file info with this row_id
            file_info = None
            for info in self.aiw_files:
                if info[3] == row_id:
                    file_info = info
                    break
            
            if file_info is None:
                continue
                
            aiw_path, _, track_name, _ = file_info
            
            # Restore from backup
            success, message = self.restore_from_backup_file(aiw_path)
            
            if success:
                # Reload the ratios
                qual_ratio, race_ratio = self.extract_ratios(aiw_path)
                self.table.update_values_from_backup(row_id, qual_ratio, race_ratio)
                success_count += 1
            else:
                fail_count += 1
                print(f"Failed to restore {aiw_path.name}: {message}")
        
        if success_count > 0:
            self.status_bar.showMessage(f"Restored {success_count} files from backup", 3000)
            if fail_count > 0:
                QMessageBox.warning(self, "Partial Success", 
                                   f"Restored {success_count} files.\n{fail_count} files failed.")
        else:
            QMessageBox.critical(self, "Restore Failed", "Failed to restore any files from backup.")
    
    def open_calculator(self, row_id):
        """Open the ratio calculator dialog for a specific row"""
        # Find the file info with this row_id
        file_info = None
        for info in self.aiw_files:
            if info[3] == row_id:
                file_info = info
                break
        
        if file_info is None:
            self.status_bar.showMessage(f"Error: Invalid row ID", 3000)
            return
        
        aiw_path, _, track_name, _ = file_info
        
        # Get current ratios
        visual_row = self.table.get_visual_row_from_id(row_id)
        if visual_row < 0:
            return
            
        current_qual = self.table.item(visual_row, 1).text()
        current_race = self.table.item(visual_row, 2).text()
        
        # Convert to float if possible
        try:
            current_qual_float = float(current_qual) if current_qual != "(not found)" else 1.0
        except ValueError:
            current_qual_float = 1.0
            
        try:
            current_race_float = float(current_race) if current_race != "(not found)" else 1.0
        except ValueError:
            current_race_float = 1.0
        
        # Create and show calculator dialog
        dialog = RatioCalculatorDialog(
            self, 
            track_name, 
            current_qual_float, 
            current_race_float
        )
        
        if dialog.exec_() == QDialog.Accepted:
            new_qual, new_race = dialog.get_ratios()
            self.table.update_ratios(row_id, new_qual, new_race)
            self.status_bar.showMessage(f"Updated ratios for {track_name} from calculator", 3000)


def main():
    # Get base path from config or user selection using the cfg_manage module
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
