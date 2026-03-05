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
    
    value_changed = pyqtSignal(int, str, str)  # row, ratio_type, new_value
    save_row = pyqtSignal(int)  # row
    restore_row = pyqtSignal(int)  # row - restore session changes
    restore_from_backup_row = pyqtSignal(int)  # row - restore from backup file
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.modified_rows = set()  # Track which rows have unsaved changes
        self.original_values = {}  # Store original values for each row: (row, type) -> value
        self.has_backup = set()  # Track which rows have backup files
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
        self.setColumnWidth(3, 200)  # Actions - wider for more buttons
        
        # Enable sorting
        self.setSortingEnabled(True)
        
        # Table styling
        self.setAlternatingRowColors(True)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        
        # Set custom delegate for ratio columns
        self.setItemDelegateForColumn(1, RatioItemDelegate(self))
        self.setItemDelegateForColumn(2, RatioItemDelegate(self))
        
        # Connect signals
        self.itemChanged.connect(self.on_item_changed)
    
    def on_item_changed(self, item):
        """Handle item changes"""
        if item.column() in [1, 2]:  # Only for ratio columns
            row = item.row()
            ratio_type = "QualRatio" if item.column() == 1 else "RaceRatio"
            new_value = item.text()
            
            # Store original value if not already stored
            if (row, ratio_type) not in self.original_values:
                self.original_values[(row, ratio_type)] = new_value
            
            # Mark row as modified
            self.modified_rows.add(row)
            
            # Change text color to yellow
            item.setForeground(QBrush(QColor("#FFA500")))
            
            # Emit signal
            self.value_changed.emit(row, ratio_type, new_value)
            
            # Update action buttons for this row
            self.update_row_buttons(row)
    
    def update_row_buttons(self, row):
        """Update the action buttons for a specific row"""
        # Check if we already have a widget in this cell
        cell_widget = self.cellWidget(row, 3)
        
        # Create button widget for this row
        button_widget = QWidget()
        button_layout = QHBoxLayout(button_widget)
        button_layout.setContentsMargins(2, 2, 2, 2)
        button_layout.setSpacing(4)
        
        # Save button (only for modified rows)
        if row in self.modified_rows:
            save_btn = QPushButton("💾")
            save_btn.setToolTip("Save this row")
            save_btn.setMaximumWidth(30)
            save_btn.setStyleSheet("background-color: #4CAF50; color: white;")
            save_btn.clicked.connect(lambda checked, r=row: self.save_row.emit(r))
            button_layout.addWidget(save_btn)
        
        # Restore session button (only for modified rows)
        if row in self.modified_rows:
            restore_btn = QPushButton("↺")
            restore_btn.setToolTip("Restore to original (session)")
            restore_btn.setMaximumWidth(30)
            restore_btn.setStyleSheet("background-color: #FFA500; color: white;")
            restore_btn.clicked.connect(lambda checked, r=row: self.restore_row.emit(r))
            button_layout.addWidget(restore_btn)
        
        # Restore from backup button (if backup exists)
        if row in self.has_backup:
            restore_backup_btn = QPushButton("📂")
            restore_backup_btn.setToolTip("Restore from backup file")
            restore_backup_btn.setMaximumWidth(30)
            restore_backup_btn.setStyleSheet("background-color: #2196F3; color: white;")
            restore_backup_btn.clicked.connect(lambda checked, r=row: self.restore_from_backup_row.emit(r))
            button_layout.addWidget(restore_backup_btn)
        
        button_layout.addStretch()
        
        self.setCellWidget(row, 3, button_widget)
    
    def restore_row_value(self, row, ratio_type):
        """Restore a single value for a row from session"""
        key = (row, ratio_type)
        if key in self.original_values:
            original = self.original_values[key]
            col = 1 if ratio_type == "QualRatio" else 2
            
            # Update the item
            item = self.item(row, col)
            if item:
                item.setText(original)
                item.setForeground(QBrush(QColor("#ffffff")))  # Back to white
            
            # Remove from original values
            del self.original_values[key]
            
            # Check if the row still has any modified values
            remaining = [k for k in self.original_values if k[0] == row]
            if not remaining:
                self.modified_rows.discard(row)
            
            self.update_row_buttons(row)
    
    def clear_row_modifications(self, row):
        """Clear all modifications for a row after save"""
        # Remove from modified rows
        self.modified_rows.discard(row)
        
        # Clear original values for this row
        keys_to_remove = [k for k in self.original_values if k[0] == row]
        for key in keys_to_remove:
            del self.original_values[key]
        
        # Reset text colors to white
        for col in [1, 2]:
            item = self.item(row, col)
            if item:
                item.setForeground(QBrush(QColor("#ffffff")))
        
        # Update action buttons
        self.update_row_buttons(row)
    
    def set_has_backup(self, row, has_backup):
        """Set whether a row has a backup file"""
        if has_backup:
            self.has_backup.add(row)
        else:
            self.has_backup.discard(row)
        self.update_row_buttons(row)
    
    def get_row_data(self, row):
        """Get all data for a row"""
        track_name = self.item(row, 0).text() if self.item(row, 0) else ""
        qual_ratio = self.item(row, 1).text() if self.item(row, 1) else "(not found)"
        race_ratio = self.item(row, 2).text() if self.item(row, 2) else "(not found)"
        return track_name, qual_ratio, race_ratio
    
    def update_values_from_backup(self, row, qual_value, race_value):
        """Update the display with values from backup"""
        # Update QualRatio
        qual_item = self.item(row, 1)
        if qual_item and qual_value is not None:
            qual_item.setText(f"{qual_value:.6f}")
            qual_item.setForeground(QBrush(QColor("#2196F3")))  # Blue to indicate from backup
        
        # Update RaceRatio
        race_item = self.item(row, 2)
        if race_item and race_value is not None:
            race_item.setText(f"{race_value:.6f}")
            race_item.setForeground(QBrush(QColor("#2196F3")))  # Blue to indicate from backup
        
        # Clear any session modifications for this row
        keys_to_remove = [k for k in self.original_values if k[0] == row]
        for key in keys_to_remove:
            del self.original_values[key]
        self.modified_rows.discard(row)
        
        # Update buttons
        self.update_row_buttons(row)


class AIWRatioEditor(QMainWindow):
    def __init__(self, base_path):
        super().__init__()
        self.base_path = Path(base_path)
        self.aiw_files = []  # List of (aiw_path, gdb_path, track_name)
        self.backup_dir = Path("./backup_originals")
        self.setup_ui()
        self.scan_files()
        
    def setup_ui(self):
        self.setWindowTitle(f"AIW Ratio Editor - Scanning: {self.base_path}")
        self.setGeometry(100, 100, 1100, 800)  # Slightly wider for more buttons
        
        self.apply_dark_theme()
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # Header with path info
        header_widget = QWidget()
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(0, 0, 0, 10)
        
        path_label = QLabel(f"Scanning: ")
        path_label.setStyleSheet("color: #888;")
        header_layout.addWidget(path_label)
        
        path_value = QLabel(str(self.base_path))
        path_value.setStyleSheet("color: #4CAF50; font-weight: bold;")
        header_layout.addWidget(path_value)
        
        header_layout.addStretch()
        
        self.stats_label = QLabel("")
        self.stats_label.setStyleSheet("color: #FFA500;")
        header_layout.addWidget(self.stats_label)
        
        main_layout.addWidget(header_widget)
        
        # Create table
        self.table = EditableTableWidget()
        self.table.value_changed.connect(self.on_value_changed)
        self.table.save_row.connect(self.save_row)
        self.table.restore_row.connect(self.restore_row)
        self.table.restore_from_backup_row.connect(self.restore_from_backup)
        
        main_layout.addWidget(self.table)
        
        # Bottom button bar
        button_bar = QWidget()
        button_layout = QHBoxLayout(button_bar)
        button_layout.setContentsMargins(0, 10, 0, 0)
        
        self.rescan_btn = QPushButton("🔄 Rescan")
        self.rescan_btn.clicked.connect(self.scan_files)
        self.rescan_btn.setStyleSheet("background-color: #4CAF50; color: white;")
        button_layout.addWidget(self.rescan_btn)
        
        self.save_all_btn = QPushButton("💾 Save All Modified")
        self.save_all_btn.clicked.connect(self.save_all)
        self.save_all_btn.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
        button_layout.addWidget(self.save_all_btn)
        
        self.restore_all_btn = QPushButton("↺ Restore All Modified")
        self.restore_all_btn.clicked.connect(self.restore_all)
        self.restore_all_btn.setStyleSheet("background-color: #FFA500; color: white; font-weight: bold;")
        button_layout.addWidget(self.restore_all_btn)
        
        self.restore_all_backup_btn = QPushButton("📂 Restore All from Backup")
        self.restore_all_backup_btn.clicked.connect(self.restore_all_from_backup)
        self.restore_all_backup_btn.setStyleSheet("background-color: #2196F3; color: white; font-weight: bold;")
        button_layout.addWidget(self.restore_all_backup_btn)
        
        button_layout.addStretch()
        
        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet("color: #888; font-style: italic;")
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
            }
            QTableWidget::item {
                padding: 5px;
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
            }
            QLabel {
                color: #ffffff;
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
            QDoubleSpinBox {
                background-color: #3c3c3c;
                color: #ffffff;
                border: 1px solid #4CAF50;
                border-radius: 3px;
                padding: 2px;
            }
        """)
    
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
        self.table.setSortingEnabled(False)
        self.table.setRowCount(0)
        
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
        for ext in ['*.aiw', '*.AIW']:
            aiw_files.extend(locations_path.rglob(ext))
        
        if not aiw_files:
            QMessageBox.information(
                self,
                "No Files Found",
                f"No .aiw or .AIW files found in:\n{locations_path}"
            )
            self.status_bar.showMessage("No AIW files found")
            self.stats_label.setText("No files found")
            return
        
        row = 0
        for aiw_path in sorted(aiw_files, key=lambda p: p.stem.lower()):
            # Find matching GDB file
            gdb_path = self.find_matching_gdb(aiw_path)
            
            # Extract track name
            track_name = self.extract_track_name(gdb_path)
            if track_name is None:
                track_name = aiw_path.stem
            
            # Extract ratios
            qual_ratio, race_ratio = self.extract_ratios(aiw_path)
            
            # Store file info
            self.aiw_files.append((aiw_path, gdb_path, track_name))
            
            # Check if backup exists
            has_backup = self.check_backup_exists(aiw_path)
            
            # Add to table
            self.table.insertRow(row)
            
            # Track Name (read-only)
            name_item = QTableWidgetItem(track_name)
            name_item.setFlags(name_item.flags() & ~Qt.ItemIsEditable)
            if track_name == aiw_path.stem:
                name_item.setForeground(QBrush(QColor("#FFA500")))  # Orange for fallback
            else:
                name_item.setForeground(QBrush(QColor("#4CAF50")))  # Green for real track name
            self.table.setItem(row, 0, name_item)
            
            # QualRatio (editable)
            if qual_ratio is not None:
                qual_item = QTableWidgetItem(f"{qual_ratio:.6f}")
            else:
                qual_item = QTableWidgetItem("(not found)")
                qual_item.setFlags(qual_item.flags() & ~Qt.ItemIsEditable)  # Make read-only if not found
                qual_item.setForeground(QBrush(QColor("#f44336")))
            self.table.setItem(row, 1, qual_item)
            
            # RaceRatio (editable)
            if race_ratio is not None:
                race_item = QTableWidgetItem(f"{race_ratio:.6f}")
            else:
                race_item = QTableWidgetItem("(not found)")
                race_item.setFlags(race_item.flags() & ~Qt.ItemIsEditable)  # Make read-only if not found
                race_item.setForeground(QBrush(QColor("#f44336")))
            self.table.setItem(row, 2, race_item)
            
            # Set backup status
            self.table.set_has_backup(row, has_backup)
            
            row += 1
        
        self.table.setSortingEnabled(True)
        
        # Update stats
        stats_text = f"Found {len(aiw_files)} AIW files"
        missing_qual = sum(1 for i in range(self.table.rowCount()) 
                          if self.table.item(i, 1).text() == "(not found)")
        missing_race = sum(1 for i in range(self.table.rowCount()) 
                          if self.table.item(i, 2).text() == "(not found)")
        
        backup_count = sum(1 for i in range(self.table.rowCount()) if self.table.has_backup.__contains__(i))
        
        if missing_qual > 0 or missing_race > 0:
            stats_text += f" | Missing ratios: Qual:{missing_qual} Race:{missing_race}"
        
        if backup_count > 0:
            stats_text += f" | Backups: {backup_count}"
        
        self.stats_label.setText(stats_text)
        self.status_bar.showMessage(f"Scan complete - found {len(aiw_files)} AIW files")
    
    def on_value_changed(self, row, ratio_type, new_value):
        """Handle value change in table"""
        self.status_bar.showMessage(f"Row {row+1} {ratio_type} changed to {new_value} - unsaved", 3000)
    
    def save_row(self, row):
        """Save changes for a specific row"""
        track_name, qual_ratio, race_ratio = self.table.get_row_data(row)
        
        if row >= len(self.aiw_files):
            self.status_bar.showMessage(f"Error: Invalid row index", 3000)
            return
        
        aiw_path, gdb_path, _ = self.aiw_files[row]
        
        # Create backup if needed
        if not self.create_backup(aiw_path):
            QMessageBox.warning(self, "Backup Failed", f"Could not create backup for {aiw_path.name}")
            return
        
        # Update values
        success_count = 0
        modified_keys = [k for k in self.table.original_values if k[0] == row]
        
        for (r, ratio_type) in modified_keys:
            new_value = self.table.item(row, 1 if ratio_type == "QualRatio" else 2).text()
            
            if new_value != "(not found)":
                try:
                    float_val = float(new_value)
                    if self.update_ratio_in_file(aiw_path, ratio_type, float_val):
                        success_count += 1
                except ValueError:
                    pass
        
        if success_count > 0:
            self.table.clear_row_modifications(row)
            # Update backup status
            self.table.set_has_backup(row, True)
            self.status_bar.showMessage(f"Saved {success_count} changes to {aiw_path.name}", 3000)
        else:
            self.status_bar.showMessage(f"No changes saved for {aiw_path.name}", 3000)
    
    def restore_row(self, row):
        """Restore original values for a specific row (from current session)"""
        modified_keys = [k for k in self.table.original_values if k[0] == row]
        
        for (r, ratio_type) in modified_keys:
            self.table.restore_row_value(row, ratio_type)
        
        if modified_keys:
            self.status_bar.showMessage(f"Restored original values for row {row+1}", 3000)
    
    def restore_from_backup(self, row):
        """Restore a specific row from its backup file"""
        if row >= len(self.aiw_files):
            self.status_bar.showMessage(f"Error: Invalid row index", 3000)
            return
        
        aiw_path, _, track_name = self.aiw_files[row]
        
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
            self.table.update_values_from_backup(row, qual_ratio, race_ratio)
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
        
        for row in modified_rows:
            aiw_path, _, _ = self.aiw_files[row]
            
            # Create backup if needed
            if not self.create_backup(aiw_path):
                fail_count += 1
                continue
            
            # Update values
            row_success = 0
            modified_keys = [k for k in self.table.original_values if k[0] == row]
            
            for (r, ratio_type) in modified_keys:
                new_value = self.table.item(row, 1 if ratio_type == "QualRatio" else 2).text()
                
                if new_value != "(not found)":
                    try:
                        float_val = float(new_value)
                        if self.update_ratio_in_file(aiw_path, ratio_type, float_val):
                            row_success += 1
                    except ValueError:
                        pass
            
            if row_success > 0:
                success_count += 1
                self.table.clear_row_modifications(row)
                self.table.set_has_backup(row, True)
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
            for row in modified_rows:
                modified_keys = [k for k in self.table.original_values if k[0] == row]
                for (r, ratio_type) in modified_keys:
                    self.table.restore_row_value(row, ratio_type)
            
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
        
        for row in rows_with_backup:
            aiw_path, _, track_name = self.aiw_files[row]
            
            # Restore from backup
            success, message = self.restore_from_backup_file(aiw_path)
            
            if success:
                # Reload the ratios
                qual_ratio, race_ratio = self.extract_ratios(aiw_path)
                self.table.update_values_from_backup(row, qual_ratio, race_ratio)
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


def main():
    if len(sys.argv) < 2:
        print("Usage: python aiw_editor.py <base_path>")
        print("\nExample:")
        print("  python aiw_editor.py C:/Games/MyGame")
        print("\nThe program will scan <base_path>/GameData/Locations/ for .aiw files")
        print("and allow editing of QualRatio and RaceRatio values.")
        return 1
    
    base_path = sys.argv[1]
    
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
