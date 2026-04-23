#!/usr/bin/env python3
"""
CSV to SQLite Database Importer with Vehicle Classes Manager
Imports historic.csv data into the Live AI Tuner SQLite database
Manages vehicle_classes.json configuration

Features:
- Preview CSV data before import
- Select database file
- Handle duplicate detection
- Import qualifying and race data points
- Progress tracking
- Import summary with statistics
- Manage vehicle classes (add/edit/delete classes and vehicles)
"""

import sys
import csv
import sqlite3
import json
import logging
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
    QMenu
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QFont, QColor, QTextCursor, QIcon

# Import database module from the existing codebase
try:
    from db_funcs import CurveDatabase
    HAS_DB_FUNCS = True
except ImportError:
    HAS_DB_FUNCS = False
    print("Warning: db_funcs not found, using built-in database functions")


# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Default path for vehicle classes
DEFAULT_VEHICLE_CLASSES_PATH = Path(__file__).parent / "vehicle_classes.json"

# Default vehicle classes structure
DEFAULT_VEHICLE_CLASSES = {
    "GT_0304": {
        "classes": ["GT_0304"],
        "vehicles": [
            "Chrysler Viper GTS-R",
            "Ferrari 550 Maranello",
            "Ferrari 550",
            "Ferrari 575 GTC",
            "Lamborghini Murcielago R-GT",
            "Lister Storm",
            "Porsche 911 GT2",
            "Saleen S7-R",
            "Porsche 996"
        ]
    },
    "NGT_0304": {
        "classes": ["NGT_0304"],
        "vehicles": [
            "Ferrari 360 GTC",
            "Ferrari 360 Modena",
            "Porsche GT3-RS",
            "Porsche GT3-RSR",
            "TVR T400R",
            "Nissan 350Z"
        ]
    },
    "Spa_0304": {
        "classes": ["Spa_0304"],
        "vehicles": [
            "BMW M3"
        ]
    },
    "GT_2012": {
        "classes": ["GT_2012"],
        "vehicles": [
            "Aston Martin",
            "Audi R8 LMS Ultra",
            "Audi R8 LMS",
            "BMW Alpina B6",
            "BMW Z4 E89",
            "Chevrolet Camaro GT",
            "Chevrolet Corvette Z06.R",
            "Dodge Viper Competition Coupe",
            "Ferrari 458",
            "Ferrari F458 Italia",
            "Ford Mustang FR500",
            "Gallardo",
            "Lambda Performance Ford GT",
            "Lamborghini Gallardo LP600+",
            "Maserati MC12",
            "McLaren GT MP4-12C",
            "Mclaren",
            "Mercedes GT",
            "Mercedes-Benz SLS AMG",
            "Nissan Nismo GT-R",
            "Porsche 997 GT3 R",
            "GT Cars"
        ]
    },
    "Formula_4": {
        "classes": ["Formula_4"],
        "vehicles": [
            "Formula 4",
            "Formula BMW",
            "Formula F4",
            "Formula Senior",
            "f4",
            "F4"
        ]
    }
}


class VehicleClassesManager:
    """Manages the vehicle_classes.json file"""
    
    def __init__(self, file_path: Path = DEFAULT_VEHICLE_CLASSES_PATH):
        self.file_path = file_path
        self.data = {}
        self.load()
    
    def load(self) -> bool:
        """Load vehicle classes from JSON file"""
        if not self.file_path.exists():
            self.data = DEFAULT_VEHICLE_CLASSES.copy()
            self.save()
            return True
        
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                self.data = json.load(f)
            return True
        except Exception as e:
            logger.error(f"Error loading vehicle classes: {e}")
            self.data = DEFAULT_VEHICLE_CLASSES.copy()
            return False
    
    def save(self) -> bool:
        """Save vehicle classes to JSON file"""
        try:
            # Ensure parent directory exists
            self.file_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.file_path, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            logger.error(f"Error saving vehicle classes: {e}")
            return False
    
    def get_all_classes(self) -> List[str]:
        """Get all class names"""
        return list(self.data.keys())
    
    def get_vehicles_for_class(self, class_name: str) -> List[str]:
        """Get vehicles for a specific class"""
        if class_name in self.data:
            return self.data[class_name].get("vehicles", [])
        return []
    
    def get_class_info(self, class_name: str) -> Optional[Dict]:
        """Get full info for a class"""
        return self.data.get(class_name)
    
    def add_class(self, class_name: str, classes_list: List[str] = None, vehicles: List[str] = None) -> bool:
        """Add a new vehicle class"""
        if class_name in self.data:
            return False
        
        self.data[class_name] = {
            "classes": classes_list or [class_name],
            "vehicles": vehicles or []
        }
        return self.save()
    
    def delete_class(self, class_name: str) -> bool:
        """Delete a vehicle class"""
        if class_name not in self.data:
            return False
        
        del self.data[class_name]
        return self.save()
    
    def rename_class(self, old_name: str, new_name: str) -> bool:
        """Rename a vehicle class"""
        if old_name not in self.data or new_name in self.data:
            return False
        
        self.data[new_name] = self.data.pop(old_name)
        # Update the classes list to include the new name
        if new_name not in self.data[new_name]["classes"]:
            self.data[new_name]["classes"] = [new_name]
        return self.save()
    
    def add_vehicle(self, class_name: str, vehicle_name: str) -> bool:
        """Add a vehicle to a class"""
        if class_name not in self.data:
            return False
        
        if vehicle_name not in self.data[class_name]["vehicles"]:
            self.data[class_name]["vehicles"].append(vehicle_name)
            self.data[class_name]["vehicles"].sort()
            return self.save()
        return False
    
    def remove_vehicle(self, class_name: str, vehicle_name: str) -> bool:
        """Remove a vehicle from a class"""
        if class_name not in self.data:
            return False
        
        if vehicle_name in self.data[class_name]["vehicles"]:
            self.data[class_name]["vehicles"].remove(vehicle_name)
            return self.save()
        return False
    
    def update_vehicle(self, class_name: str, old_name: str, new_name: str) -> bool:
        """Update a vehicle name"""
        if class_name not in self.data:
            return False
        
        vehicles = self.data[class_name]["vehicles"]
        if old_name in vehicles:
            idx = vehicles.index(old_name)
            vehicles[idx] = new_name
            vehicles.sort()
            return self.save()
        return False
    
    def get_vehicle_class(self, vehicle_name: str) -> Optional[str]:
        """Find which class a vehicle belongs to"""
        vehicle_lower = vehicle_name.lower().strip()
        
        for class_name, class_data in self.data.items():
            for vehicle in class_data.get("vehicles", []):
                if vehicle.lower() == vehicle_lower:
                    return class_name
        
        # Try partial matching
        for class_name, class_data in self.data.items():
            for vehicle in class_data.get("vehicles", []):
                if vehicle.lower() in vehicle_lower or vehicle_lower in vehicle.lower():
                    return class_name
        
        return None


class AddEditClassDialog(QDialog):
    """Dialog for adding or editing a vehicle class"""
    
    def __init__(self, parent=None, class_name: str = None, vehicles: List[str] = None):
        super().__init__(parent)
        self.class_name = class_name
        self.vehicles = vehicles or []
        self.setup_ui()
        
        if class_name:
            self.setWindowTitle(f"Edit Class: {class_name}")
            self.class_name_edit.setText(class_name)
            self.class_name_edit.setEnabled(False)  # Can't change name in edit mode
            self.load_vehicles()
    
    def setup_ui(self):
        self.setWindowTitle("Add New Class")
        self.setMinimumSize(500, 400)
        self.setStyleSheet("""
            QDialog {
                background-color: #2b2b2b;
            }
            QLabel {
                color: white;
            }
            QLineEdit {
                background-color: #3c3c3c;
                color: white;
                border: 1px solid #4CAF50;
                border-radius: 4px;
                padding: 6px;
            }
            QListWidget {
                background-color: #3c3c3c;
                color: white;
                border: 1px solid #4CAF50;
                border-radius: 4px;
            }
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 6px 12px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        
        layout = QVBoxLayout(self)
        
        # Class name
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("Class Name:"))
        self.class_name_edit = QLineEdit()
        self.class_name_edit.setPlaceholderText("e.g., GT_2012, Formula_4")
        name_layout.addWidget(self.class_name_edit)
        layout.addLayout(name_layout)
        
        # Vehicles list
        layout.addWidget(QLabel("Vehicles in this class:"))
        
        self.vehicles_list = QListWidget()
        self.vehicles_list.setSelectionMode(QListWidget.ExtendedSelection)
        layout.addWidget(self.vehicles_list)
        
        # Vehicle management buttons
        vehicle_btn_layout = QHBoxLayout()
        
        self.add_vehicle_btn = QPushButton("Add Vehicle")
        self.add_vehicle_btn.clicked.connect(self.add_vehicle)
        vehicle_btn_layout.addWidget(self.add_vehicle_btn)
        
        self.edit_vehicle_btn = QPushButton("Edit Vehicle")
        self.edit_vehicle_btn.clicked.connect(self.edit_vehicle)
        vehicle_btn_layout.addWidget(self.edit_vehicle_btn)
        
        self.remove_vehicle_btn = QPushButton("Remove Vehicle(s)")
        self.remove_vehicle_btn.clicked.connect(self.remove_vehicles)
        vehicle_btn_layout.addWidget(self.remove_vehicle_btn)
        
        layout.addLayout(vehicle_btn_layout)
        
        # New vehicle input
        new_vehicle_layout = QHBoxLayout()
        self.new_vehicle_edit = QLineEdit()
        self.new_vehicle_edit.setPlaceholderText("New vehicle name...")
        new_vehicle_layout.addWidget(self.new_vehicle_edit)
        
        self.add_new_btn = QPushButton("Add")
        self.add_new_btn.clicked.connect(self.add_new_vehicle)
        new_vehicle_layout.addWidget(self.add_new_btn)
        
        layout.addLayout(new_vehicle_layout)
        
        # Dialog buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
    
    def load_vehicles(self):
        """Load vehicles into the list"""
        self.vehicles_list.clear()
        for vehicle in sorted(self.vehicles):
            self.vehicles_list.addItem(vehicle)
    
    def add_vehicle(self):
        """Show dialog to add a vehicle"""
        vehicle_name, ok = QInputDialog.getText(
            self, "Add Vehicle", "Vehicle name:"
        )
        if ok and vehicle_name.strip():
            if vehicle_name.strip() not in self.vehicles:
                self.vehicles.append(vehicle_name.strip())
                self.vehicles.sort()
                self.load_vehicles()
    
    def edit_vehicle(self):
        """Edit selected vehicle"""
        current = self.vehicles_list.currentItem()
        if not current:
            return
        
        old_name = current.text()
        new_name, ok = QInputDialog.getText(
            self, "Edit Vehicle", "New vehicle name:", text=old_name
        )
        if ok and new_name.strip() and new_name.strip() != old_name:
            idx = self.vehicles.index(old_name)
            self.vehicles[idx] = new_name.strip()
            self.vehicles.sort()
            self.load_vehicles()
    
    def add_new_vehicle(self):
        """Add vehicle from the quick input field"""
        vehicle_name = self.new_vehicle_edit.text().strip()
        if vehicle_name and vehicle_name not in self.vehicles:
            self.vehicles.append(vehicle_name)
            self.vehicles.sort()
            self.load_vehicles()
            self.new_vehicle_edit.clear()
    
    def remove_vehicles(self):
        """Remove selected vehicles"""
        selected = self.vehicles_list.selectedItems()
        if not selected:
            return
        
        for item in selected:
            if item.text() in self.vehicles:
                self.vehicles.remove(item.text())
        
        self.load_vehicles()
    
    def get_class_name(self) -> str:
        return self.class_name_edit.text().strip()
    
    def get_vehicles(self) -> List[str]:
        return self.vehicles


class VehicleClassesWidget(QWidget):
    """Widget for managing vehicle classes"""
    
    classes_updated = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.manager = VehicleClassesManager()
        self.setup_ui()
        self.load_data()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Info label
        info_label = QLabel(
            "Vehicle Classes Management\n\n"
            "This defines which vehicles belong to which class for AI tuning.\n"
            "Each class can have multiple vehicles, and vehicles can only belong to one class."
        )
        info_label.setStyleSheet("color: #FFA500; background-color: #2b2b2b; padding: 10px; border-radius: 5px;")
        info_label.setWordWrap(True)
        layout.addWidget(info_label)
        
        layout.addSpacing(10)
        
        # Main content splitter
        splitter = QSplitter(Qt.Horizontal)
        
        # Left panel - class list
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        left_layout.addWidget(QLabel("Vehicle Classes:"))
        
        self.class_list = QListWidget()
        self.class_list.setSelectionMode(QListWidget.SingleSelection)
        self.class_list.itemSelectionChanged.connect(self.on_class_selected)
        left_layout.addWidget(self.class_list)
        
        # Class management buttons
        class_btn_layout = QHBoxLayout()
        
        self.add_class_btn = QPushButton("Add Class")
        self.add_class_btn.clicked.connect(self.add_class)
        class_btn_layout.addWidget(self.add_class_btn)
        
        self.rename_class_btn = QPushButton("Rename")
        self.rename_class_btn.clicked.connect(self.rename_class)
        class_btn_layout.addWidget(self.rename_class_btn)
        
        self.delete_class_btn = QPushButton("Delete")
        self.delete_class_btn.setStyleSheet("background-color: #f44336;")
        self.delete_class_btn.clicked.connect(self.delete_class)
        class_btn_layout.addWidget(self.delete_class_btn)
        
        left_layout.addLayout(class_btn_layout)
        
        splitter.addWidget(left_panel)
        
        # Right panel - vehicle list for selected class
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        
        self.selected_class_label = QLabel("No class selected")
        self.selected_class_label.setStyleSheet("color: #4CAF50; font-weight: bold;")
        right_layout.addWidget(self.selected_class_label)
        
        right_layout.addSpacing(5)
        
        right_layout.addWidget(QLabel("Vehicles in this class:"))
        
        self.vehicles_list = QListWidget()
        self.vehicles_list.setSelectionMode(QListWidget.ExtendedSelection)
        right_layout.addWidget(self.vehicles_list)
        
        # Vehicle management buttons
        vehicle_btn_layout = QHBoxLayout()
        
        self.add_vehicle_btn = QPushButton("Add Vehicle")
        self.add_vehicle_btn.clicked.connect(self.add_vehicle)
        vehicle_btn_layout.addWidget(self.add_vehicle_btn)
        
        self.edit_vehicle_btn = QPushButton("Edit Vehicle")
        self.edit_vehicle_btn.clicked.connect(self.edit_vehicle)
        vehicle_btn_layout.addWidget(self.edit_vehicle_btn)
        
        self.remove_vehicle_btn = QPushButton("Remove Vehicle(s)")
        self.remove_vehicle_btn.setStyleSheet("background-color: #f44336;")
        self.remove_vehicle_btn.clicked.connect(self.remove_vehicles)
        vehicle_btn_layout.addWidget(self.remove_vehicle_btn)
        
        right_layout.addLayout(vehicle_btn_layout)
        
        # Quick add vehicle
        quick_layout = QHBoxLayout()
        quick_layout.addWidget(QLabel("Quick Add:"))
        self.new_vehicle_edit = QLineEdit()
        self.new_vehicle_edit.setPlaceholderText("Vehicle name...")
        self.new_vehicle_edit.returnPressed.connect(self.quick_add_vehicle)
        quick_layout.addWidget(self.new_vehicle_edit)
        
        self.quick_add_btn = QPushButton("Add")
        self.quick_add_btn.clicked.connect(self.quick_add_vehicle)
        quick_layout.addWidget(self.quick_add_btn)
        
        right_layout.addLayout(quick_layout)
        
        splitter.addWidget(right_panel)
        
        # Set splitter proportions
        splitter.setSizes([300, 500])
        
        layout.addWidget(splitter)
        
        # Bottom buttons
        bottom_layout = QHBoxLayout()
        bottom_layout.addStretch()
        
        self.save_btn = QPushButton("Save Changes")
        self.save_btn.setStyleSheet("background-color: #4CAF50; font-size: 14px; padding: 8px 20px;")
        self.save_btn.clicked.connect(self.save_changes)
        bottom_layout.addWidget(self.save_btn)
        
        self.reload_btn = QPushButton("Reload from File")
        self.reload_btn.clicked.connect(self.reload_from_file)
        bottom_layout.addWidget(self.reload_btn)
        
        layout.addLayout(bottom_layout)
    
    def load_data(self):
        """Load data from manager"""
        self.class_list.clear()
        for class_name in self.manager.get_all_classes():
            self.class_list.addItem(class_name)
    
    def on_class_selected(self):
        """Handle class selection"""
        current = self.class_list.currentItem()
        if not current:
            self.selected_class_label.setText("No class selected")
            self.vehicles_list.clear()
            return
        
        class_name = current.text()
        self.selected_class_label.setText(f"Class: {class_name}")
        
        # Load vehicles
        self.vehicles_list.clear()
        for vehicle in self.manager.get_vehicles_for_class(class_name):
            self.vehicles_list.addItem(vehicle)
    
    def add_class(self):
        """Add a new vehicle class"""
        dialog = AddEditClassDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            class_name = dialog.get_class_name()
            vehicles = dialog.get_vehicles()
            
            if not class_name:
                QMessageBox.warning(self, "Invalid", "Class name cannot be empty.")
                return
            
            if self.manager.add_class(class_name, [class_name], vehicles):
                self.load_data()
                self.classes_updated.emit()
                QMessageBox.information(self, "Success", f"Added class: {class_name}")
            else:
                QMessageBox.warning(self, "Error", f"Class '{class_name}' already exists.")
    
    def rename_class(self):
        """Rename the selected class"""
        current = self.class_list.currentItem()
        if not current:
            QMessageBox.warning(self, "No Selection", "Please select a class to rename.")
            return
        
        old_name = current.text()
        new_name, ok = QInputDialog.getText(
            self, "Rename Class", "New class name:", text=old_name
        )
        
        if ok and new_name.strip() and new_name.strip() != old_name:
            if self.manager.rename_class(old_name, new_name.strip()):
                self.load_data()
                self.classes_updated.emit()
                QMessageBox.information(self, "Success", f"Renamed '{old_name}' to '{new_name}'")
            else:
                QMessageBox.warning(self, "Error", f"Could not rename. Name '{new_name}' may already exist.")
    
    def delete_class(self):
        """Delete the selected class"""
        current = self.class_list.currentItem()
        if not current:
            QMessageBox.warning(self, "No Selection", "Please select a class to delete.")
            return
        
        class_name = current.text()
        
        reply = QMessageBox.question(
            self, "Confirm Delete",
            f"Delete class '{class_name}' and all its vehicles?\nThis cannot be undone.",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            if self.manager.delete_class(class_name):
                self.load_data()
                self.classes_updated.emit()
                QMessageBox.information(self, "Success", f"Deleted class: {class_name}")
            else:
                QMessageBox.warning(self, "Error", "Failed to delete class.")
    
    def add_vehicle(self):
        """Add a vehicle to the selected class"""
        current = self.class_list.currentItem()
        if not current:
            QMessageBox.warning(self, "No Selection", "Please select a class first.")
            return
        
        class_name = current.text()
        vehicle_name, ok = QInputDialog.getText(
            self, "Add Vehicle", f"Vehicle name for class '{class_name}':"
        )
        
        if ok and vehicle_name.strip():
            if self.manager.add_vehicle(class_name, vehicle_name.strip()):
                self.on_class_selected()  # Refresh the list
                self.classes_updated.emit()
                QMessageBox.information(self, "Success", f"Added '{vehicle_name}' to '{class_name}'")
            else:
                QMessageBox.warning(self, "Error", "Failed to add vehicle.")
    
    def edit_vehicle(self):
        """Edit the selected vehicle"""
        current_class = self.class_list.currentItem()
        current_vehicle = self.vehicles_list.currentItem()
        
        if not current_class or not current_vehicle:
            QMessageBox.warning(self, "No Selection", "Please select a class and a vehicle.")
            return
        
        class_name = current_class.text()
        old_name = current_vehicle.text()
        new_name, ok = QInputDialog.getText(
            self, "Edit Vehicle", "New vehicle name:", text=old_name
        )
        
        if ok and new_name.strip() and new_name.strip() != old_name:
            if self.manager.update_vehicle(class_name, old_name, new_name.strip()):
                self.on_class_selected()
                self.classes_updated.emit()
                QMessageBox.information(self, "Success", f"Updated vehicle name")
            else:
                QMessageBox.warning(self, "Error", "Failed to update vehicle.")
    
    def remove_vehicles(self):
        """Remove selected vehicles"""
        current_class = self.class_list.currentItem()
        selected = self.vehicles_list.selectedItems()
        
        if not current_class or not selected:
            QMessageBox.warning(self, "No Selection", "Please select vehicles to remove.")
            return
        
        class_name = current_class.text()
        vehicle_names = [item.text() for item in selected]
        
        reply = QMessageBox.question(
            self, "Confirm Remove",
            f"Remove {len(vehicle_names)} vehicle(s) from '{class_name}'?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            removed = 0
            for vehicle_name in vehicle_names:
                if self.manager.remove_vehicle(class_name, vehicle_name):
                    removed += 1
            
            self.on_class_selected()
            self.classes_updated.emit()
            QMessageBox.information(self, "Success", f"Removed {removed} vehicle(s).")
    
    def quick_add_vehicle(self):
        """Quick add a vehicle using the input field"""
        current_class = self.class_list.currentItem()
        if not current_class:
            QMessageBox.warning(self, "No Selection", "Please select a class first.")
            return
        
        vehicle_name = self.new_vehicle_edit.text().strip()
        if not vehicle_name:
            return
        
        class_name = current_class.text()
        if self.manager.add_vehicle(class_name, vehicle_name):
            self.on_class_selected()
            self.classes_updated.emit()
            self.new_vehicle_edit.clear()
        else:
            QMessageBox.warning(self, "Error", f"Could not add '{vehicle_name}'. It may already exist.")
    
    def save_changes(self):
        """Save changes to file"""
        if self.manager.save():
            QMessageBox.information(self, "Success", "Vehicle classes saved successfully!")
            self.classes_updated.emit()
        else:
            QMessageBox.critical(self, "Error", "Failed to save vehicle classes.")
    
    def reload_from_file(self):
        """Reload from file, discarding unsaved changes"""
        reply = QMessageBox.question(
            self, "Confirm Reload",
            "Reload from file? Any unsaved changes will be lost.",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.manager.load()
            self.load_data()
            self.classes_updated.emit()
            QMessageBox.information(self, "Success", "Reloaded from file.")


class SimpleCurveDatabase:
    """Simplified database handler that matches the expected interface"""
    
    def __init__(self, db_path: str = "ai_data.db"):
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        """Initialize database schema if it doesn't exist"""
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
        """Check if a data point already exists in the database"""
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
        """Add a new data point to the database"""
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
        """Get database statistics"""
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
        """Check if database file exists"""
        return Path(self.db_path).exists()
    
    def get_all_tracks(self) -> List[str]:
        """Get all unique track names"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT track FROM data_points ORDER BY track")
        tracks = [row[0] for row in cursor.fetchall()]
        conn.close()
        return tracks
    
    def get_all_vehicle_classes(self) -> List[str]:
        """Get all unique vehicle class names"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT vehicle_class FROM data_points ORDER BY vehicle_class")
        vehicles = [row[0] for row in cursor.fetchall()]
        conn.close()
        return vehicles


# Use the appropriate database class
if HAS_DB_FUNCS:
    class DatabaseWrapper:
        def __init__(self, db_path: str):
            self.db = CurveDatabase(db_path)
            self.db_path = db_path
        
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
            return self.db.add_data_point(track, vehicle_class, ratio, lap_time, session_type)
        
        def get_stats(self) -> dict:
            return self.db.get_stats()
        
        def database_exists(self) -> bool:
            return self.db.database_exists()
        
        def get_all_tracks(self) -> List[str]:
            return self.db.get_all_tracks()
        
        def get_all_vehicle_classes(self) -> List[str]:
            return self.db.get_all_vehicle_classes()
    
    CurveDatabaseClass = DatabaseWrapper
else:
    CurveDatabaseClass = SimpleCurveDatabase


@dataclass
class CSVRecord:
    """Represents a single record from historic.csv"""
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
    
    @classmethod
    def from_csv_row(cls, row: Dict[str, str]) -> Optional['CSVRecord']:
        """Create a CSVRecord from a CSV row dictionary"""
        try:
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
            
            return cls(
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
            logger.error(f"Error parsing CSV row: {e}")
            return None
    
    def get_qual_data_points(self) -> List[Tuple[str, float, float]]:
        """Get qualifying data points: (vehicle_class, ratio, lap_time)"""
        points = []
        
        if self.qual_best_ai > 0 and self.qual_worst_ai > 0:
            midpoint = (self.qual_best_ai + self.qual_worst_ai) / 2
            points.append((self.qual_best_vehicle, self.qual_ratio, midpoint))
        
        return points
    
    def get_race_data_points(self) -> List[Tuple[str, float, float]]:
        """Get race data points: (vehicle_class, ratio, lap_time)"""
        points = []
        
        if self.race_best_ai > 0 and self.race_worst_ai > 0:
            midpoint = (self.race_best_ai + self.race_worst_ai) / 2
            points.append((self.race_best_vehicle, self.race_ratio, midpoint))
        
        return points
    
    def has_valid_qual_data(self) -> bool:
        """Check if qualifying data is valid for import"""
        return (self.qual_ratio > 0 and 
                self.qual_best_ai > 0 and 
                self.qual_worst_ai > 0 and
                0.3 < self.qual_ratio < 3.0)
    
    def has_valid_race_data(self) -> bool:
        """Check if race data is valid for import"""
        return (self.race_ratio > 0 and 
                self.race_best_ai > 0 and 
                self.race_worst_ai > 0 and
                0.3 < self.race_ratio < 3.0)


class ImportWorker(QThread):
    """Worker thread for importing data"""
    
    progress = pyqtSignal(int, int, str)
    record_processed = pyqtSignal(int, int, int)
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)
    
    def __init__(self, db_path: str, csv_path: str, 
                 import_qual: bool = True, import_race: bool = True,
                 skip_duplicates: bool = True):
        super().__init__()
        self.db_path = db_path
        self.csv_path = csv_path
        self.import_qual = import_qual
        self.import_race = import_race
        self.skip_duplicates = skip_duplicates
        self._is_running = True
    
    def stop(self):
        self._is_running = False
    
    def run(self):
        try:
            records = self._read_csv_file()
            
            if not records:
                self.error.emit("No valid records found in CSV file")
                return
            
            total_records = len(records)
            self.progress.emit(0, total_records, f"Loading database...")
            
            db = CurveDatabaseClass(self.db_path)
            
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
    
    def _read_csv_file(self) -> List[CSVRecord]:
        """Read and parse CSV file"""
        records = []
        
        with open(self.csv_path, 'r', encoding='utf-8-sig') as f:
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
                
                record = CSVRecord.from_csv_row(row)
                if record and (record.has_valid_qual_data() or record.has_valid_race_data()):
                    records.append(record)
        
        return records


class CSVImporterGUI(QMainWindow):
    """Main GUI window for CSV importer"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("CSV to SQLite Importer - Live AI Tuner")
        self.setGeometry(100, 100, 1200, 800)
        
        self.db_path = "ai_data.db"
        self.csv_path = None
        self.worker = None
        
        self.setup_ui()
        self.apply_styles()
        
        self.refresh_db_info()
    
    def setup_ui(self):
        """Setup the user interface"""
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        # Title
        title = QLabel("CSV to SQLite Database Importer")
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: #4CAF50;")
        title.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title)
        
        # Tab widget
        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget)
        
        # === Import Tab ===
        import_tab = self.create_import_tab()
        self.tab_widget.addTab(import_tab, "Import")
        
        # === Vehicle Classes Tab ===
        self.vehicle_classes_widget = VehicleClassesWidget()
        self.vehicle_classes_widget.classes_updated.connect(self.on_classes_updated)
        self.tab_widget.addTab(self.vehicle_classes_widget, "Vehicle Classes")
        
        # === Database Info Tab ===
        info_tab = self.create_info_tab()
        self.tab_widget.addTab(info_tab, "Database Info")
        
        # === About Tab ===
        about_tab = self.create_about_tab()
        self.tab_widget.addTab(about_tab, "About")
        
        # Status bar
        self.statusBar().showMessage("Ready")
    
    def create_import_tab(self) -> QWidget:
        """Create the import tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # File selection group
        file_group = QGroupBox("File Selection")
        file_layout = QVBoxLayout(file_group)
        
        csv_layout = QHBoxLayout()
        csv_layout.addWidget(QLabel("CSV File:"))
        self.csv_path_label = QLabel("No file selected")
        self.csv_path_label.setStyleSheet("color: #888; font-family: monospace;")
        self.csv_path_label.setWordWrap(True)
        csv_layout.addWidget(self.csv_path_label, 1)
        
        self.browse_csv_btn = QPushButton("Browse...")
        self.browse_csv_btn.clicked.connect(self.browse_csv_file)
        csv_layout.addWidget(self.browse_csv_btn)
        file_layout.addLayout(csv_layout)
        
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
        
        # Import options group
        options_group = QGroupBox("Import Options")
        options_layout = QHBoxLayout(options_group)
        
        self.import_qual_cb = QCheckBox("Import Qualifying Data")
        self.import_qual_cb.setChecked(True)
        options_layout.addWidget(self.import_qual_cb)
        
        self.import_race_cb = QCheckBox("Import Race Data")
        self.import_race_cb.setChecked(True)
        options_layout.addWidget(self.import_race_cb)
        
        self.skip_duplicates_cb = QCheckBox("Skip Duplicates")
        self.skip_duplicates_cb.setChecked(True)
        options_layout.addWidget(self.skip_duplicates_cb)
        
        options_layout.addStretch()
        layout.addWidget(options_group)
        
        # Preview group
        preview_group = QGroupBox("CSV Preview")
        preview_layout = QVBoxLayout(preview_group)
        
        self.preview_table = QTableWidget()
        self.preview_table.setAlternatingRowColors(True)
        self.preview_table.setMinimumHeight(200)
        preview_layout.addWidget(self.preview_table)
        
        self.refresh_preview_btn = QPushButton("Refresh Preview")
        self.refresh_preview_btn.clicked.connect(self.refresh_preview)
        preview_layout.addWidget(self.refresh_preview_btn)
        
        layout.addWidget(preview_group)
        
        # Progress area
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
        
        # Import button
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
    
    def create_info_tab(self) -> QWidget:
        """Create the database info tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Database stats
        stats_group = QGroupBox("Database Statistics")
        stats_layout = QVBoxLayout(stats_group)
        
        self.db_stats_label = QLabel("Click 'Refresh' to load database statistics")
        self.db_stats_label.setStyleSheet("font-family: monospace;")
        stats_layout.addWidget(self.db_stats_label)
        
        layout.addWidget(stats_group)
        
        # Tracks list
        tracks_group = QGroupBox("Tracks in Database")
        tracks_layout = QVBoxLayout(tracks_group)
        
        self.tracks_list = QTextEdit()
        self.tracks_list.setReadOnly(True)
        self.tracks_list.setMaximumHeight(200)
        self.tracks_list.setFont(QFont("Courier New", 10))
        tracks_layout.addWidget(self.tracks_list)
        
        layout.addWidget(tracks_group)
        
        # Vehicle classes list
        vehicles_group = QGroupBox("Vehicle Classes in Database")
        vehicles_layout = QVBoxLayout(vehicles_group)
        
        self.vehicles_list = QTextEdit()
        self.vehicles_list.setReadOnly(True)
        self.vehicles_list.setMaximumHeight(150)
        self.vehicles_list.setFont(QFont("Courier New", 10))
        vehicles_layout.addWidget(self.vehicles_list)
        
        layout.addWidget(vehicles_group)
        
        # Refresh button
        refresh_layout = QHBoxLayout()
        refresh_layout.addStretch()
        
        self.refresh_db_btn = QPushButton("Refresh Database Info")
        self.refresh_db_btn.clicked.connect(self.refresh_db_info)
        refresh_layout.addWidget(self.refresh_db_btn)
        
        layout.addLayout(refresh_layout)
        
        return tab
    
    def create_about_tab(self) -> QWidget:
        """Create the about tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        about_text = QTextEdit()
        about_text.setReadOnly(True)
        about_text.setHtml("""
        <h2>CSV to SQLite Importer</h2>
        <p>This tool imports data from <b>historic.csv</b> into the Live AI Tuner SQLite database.</p>
        
        <h3>CSV Format Expected:</h3>
        <ul>
            <li>Delimiter: Semicolon (;) or comma (,)</li>
            <li>Columns: User Vehicle, Timestamp, Track Name, Current QualRatio, 
                Qual AI Best (s), Q AI Best Vehicle, Qual AI Worst (s), Q AI Worst Vehicle,
                Qual User (s), Current RaceRatio, Race AI Best (s), R AI Best Vehicle,
                Race AI Worst (s), R AI Worst Vehicle, Race User (s)</li>
        </ul>
        
        <h3>What gets imported:</h3>
        <ul>
            <li>For each qualifying session with valid data: 
                <b>midpoint = (AI Best + AI Worst) / 2</b> is imported as a data point</li>
            <li>For each race session with valid data: 
                <b>midpoint = (AI Best + AI Worst) / 2</b> is imported as a data point</li>
        </ul>
        
        <h3>Vehicle Classes Management:</h3>
        <ul>
            <li>Add, rename, or delete vehicle classes</li>
            <li>Add, edit, or remove vehicles from classes</li>
            <li>Changes are saved to vehicle_classes.json</li>
            <li>Used by the main application to map vehicles to classes</li>
        </ul>
        """)
        layout.addWidget(about_text)
        
        return tab
    
    def apply_styles(self):
        """Apply dark theme styling"""
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
        """)
    
    def browse_csv_file(self):
        """Open file dialog to select CSV file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select CSV File", 
            str(Path.cwd()),
            "CSV Files (*.csv);;All Files (*)"
        )
        
        if file_path:
            self.csv_path = file_path
            self.csv_path_label.setText(file_path)
            self.csv_path_label.setStyleSheet("color: #4CAF50; font-family: monospace;")
            self.refresh_preview()
            self.statusBar().showMessage(f"Loaded: {Path(file_path).name}")
    
    def browse_db_file(self):
        """Open file dialog to select database file"""
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
        """Refresh the CSV preview table"""
        if not self.csv_path or not Path(self.csv_path).exists():
            self.preview_table.setRowCount(0)
            self.preview_table.setColumnCount(0)
            return
        
        try:
            with open(self.csv_path, 'r', encoding='utf-8-sig') as f:
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
        """Refresh database information display"""
        try:
            if not Path(self.db_path).exists():
                self.db_stats_label.setText("Database file does not exist yet.")
                self.tracks_list.clear()
                self.vehicles_list.clear()
                return
            
            db = CurveDatabaseClass(self.db_path)
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
    
    def on_classes_updated(self):
        """Called when vehicle classes are updated"""
        self.statusBar().showMessage("Vehicle classes updated. Refresh database info to see changes.", 3000)
        # Optionally refresh the database info tab to show updated classes
        self.refresh_db_info()
    
    def start_import(self):
        """Start the import process"""
        if not self.csv_path:
            QMessageBox.warning(self, "No CSV File", "Please select a CSV file to import.")
            return
        
        if not Path(self.csv_path).exists():
            QMessageBox.warning(self, "File Not Found", f"CSV file not found: {self.csv_path}")
            return
        
        reply = QMessageBox.question(
            self, "Confirm Import",
            f"This will import data from:\n{self.csv_path}\n\n"
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
        
        self.worker = ImportWorker(
            self.db_path, self.csv_path,
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
        """Cancel the ongoing import"""
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.status_label.setText("Cancelling import...")
            self.cancel_btn.setEnabled(False)
    
    def update_progress(self, current: int, total: int, message: str):
        """Update progress bar"""
        if total > 0:
            percent = int((current / total) * 100)
            self.progress_bar.setValue(percent)
        self.status_label.setText(message)
    
    def update_stats(self, qual_added: int, race_added: int, processed: int):
        """Update statistics display during import"""
        self.stats_label.setText(f"Processed: {processed} | Qual added: {qual_added} | Race added: {race_added}")
    
    def import_finished(self, summary: dict):
        """Handle import completion"""
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
        """Handle import error"""
        self.import_btn.setEnabled(True)
        self.import_btn.setVisible(True)
        self.cancel_btn.setVisible(False)
        self.progress_bar.setVisible(False)
        
        QMessageBox.critical(self, "Import Error", error_msg)
        self.status_label.setText(f"Error: {error_msg}")
        
        self.worker = None


def main():
    """Main entry point"""
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    window = CSVImporterGUI()
    window.show()
    
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
