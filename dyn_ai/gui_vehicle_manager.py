#!/usr/bin/env python3
"""
Vehicle Management Module for Live AI Tuner
Provides standalone vehicle management dialog that can be called from any part of the application
"""

import sys
import json
import logging
import re
from pathlib import Path
from typing import List, Dict, Optional, Set, Tuple

from PyQt5.QtWidgets import (
    QApplication, QDialog, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFileDialog, QListWidget, QListWidgetItem,
    QGroupBox, QMessageBox, QSplitter, QLineEdit, QInputDialog,
    QDialogButtonBox, QAbstractItemView, QProgressBar
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal

from core_vehicle_scanner import scan_vehicles_from_gtr2
from gui_common import get_data_file_path

logger = logging.getLogger(__name__)

DEFAULT_VEHICLE_CLASSES_PATH = get_data_file_path("vehicle_classes.json")

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
            "BMW M3",
            "BMW M3 GTR",
            "BMW Z3 M",
            "Chevrolet Corvette C5-R",
            "Gillet Vertigo Streiff",
            "Lotus Elise",
            "Morgan Aero 8",
            "Mosler MT900R",
            "Porsche 911 Biturbo",
            "Porsche 911 GT3 Cup",
            "Seat Toledo GT",
            "Viper Competition Coupe"
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
    },
    "OTHER": {
        "classes": ["OTHER"],
        "vehicles": [
            "2003 SafetyCar"
        ]
    }
}


class CarImporter(QThread):
    """Thread for importing cars from GTR2 installation"""
    
    progress = pyqtSignal(int, int, str)
    finished = pyqtSignal(set)
    error = pyqtSignal(str)
    
    def __init__(self, gtr2_path: Path):
        super().__init__()
        self.gtr2_path = Path(gtr2_path)
        self._is_running = True
    
    def stop(self):
        self._is_running = False
    
    def run(self):
        try:
            vehicles = scan_vehicles_from_gtr2(
                self.gtr2_path,
                lambda c, t, m: self.progress.emit(c, t, m) if self._is_running else None
            )
            self.finished.emit(vehicles)
        except Exception as e:
            self.error.emit(f"Import failed: {str(e)}")
            logger.exception("Car import error")


class VehicleClassesManager:
    """Manages the vehicle_classes.json file"""
    
    def __init__(self, file_path: Path = DEFAULT_VEHICLE_CLASSES_PATH):
        self.file_path = file_path
        self.data = {}
        self.load()
    
    def load(self) -> bool:
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
        try:
            self.file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.file_path, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            logger.error(f"Error saving vehicle classes: {e}")
            return False
    
    def get_all_classes(self) -> List[str]:
        return list(self.data.keys())
    
    def get_vehicles_for_class(self, class_name: str) -> List[str]:
        if class_name in self.data:
            return self.data[class_name].get("vehicles", [])
        return []
    
    def get_all_vehicles(self) -> Set[str]:
        all_vehicles = set()
        for class_data in self.data.values():
            all_vehicles.update(class_data.get("vehicles", []))
        return all_vehicles
    
    def get_class_info(self, class_name: str) -> Optional[Dict]:
        return self.data.get(class_name)
    
    def get_vehicle_class(self, vehicle_name: str) -> Optional[str]:
        vehicle_lower = vehicle_name.lower().strip()
        for class_name, class_data in self.data.items():
            for vehicle in class_data.get("vehicles", []):
                if vehicle.lower() == vehicle_lower:
                    return class_name
        for class_name, class_data in self.data.items():
            for vehicle in class_data.get("vehicles", []):
                if vehicle.lower() in vehicle_lower or vehicle_lower in vehicle.lower():
                    return class_name
        return None
    
    def add_class(self, class_name: str, classes_list: List[str] = None, vehicles: List[str] = None) -> bool:
        if class_name in self.data:
            return False
        self.data[class_name] = {
            "classes": classes_list or [class_name],
            "vehicles": vehicles or []
        }
        return self.save()
    
    def delete_class(self, class_name: str) -> bool:
        if class_name not in self.data:
            return False
        del self.data[class_name]
        return self.save()
    
    def rename_class(self, old_name: str, new_name: str) -> bool:
        if old_name not in self.data or new_name in self.data:
            return False
        self.data[new_name] = self.data.pop(old_name)
        if new_name not in self.data[new_name]["classes"]:
            self.data[new_name]["classes"] = [new_name]
        return self.save()
    
    def add_vehicle(self, class_name: str, vehicle_name: str) -> bool:
        if class_name not in self.data:
            return False
        if vehicle_name not in self.data[class_name]["vehicles"]:
            self.data[class_name]["vehicles"].append(vehicle_name)
            self.data[class_name]["vehicles"].sort()
            return self.save()
        return False
    
    def add_vehicles_batch(self, class_name: str, vehicle_names: List[str]) -> int:
        if class_name not in self.data:
            return 0
        added = 0
        for vehicle_name in vehicle_names:
            if vehicle_name not in self.data[class_name]["vehicles"]:
                self.data[class_name]["vehicles"].append(vehicle_name)
                added += 1
        if added > 0:
            self.data[class_name]["vehicles"].sort()
            self.save()
        return added
    
    def remove_vehicle(self, class_name: str, vehicle_name: str) -> bool:
        if class_name not in self.data:
            return False
        if vehicle_name in self.data[class_name]["vehicles"]:
            self.data[class_name]["vehicles"].remove(vehicle_name)
            return self.save()
        return False
    
    def remove_vehicles_batch(self, class_name: str, vehicle_names: List[str]) -> int:
        if class_name not in self.data:
            return 0
        removed = 0
        for vehicle_name in vehicle_names:
            if vehicle_name in self.data[class_name]["vehicles"]:
                self.data[class_name]["vehicles"].remove(vehicle_name)
                removed += 1
        if removed > 0:
            self.data[class_name]["vehicles"].sort()
            self.save()
        return removed
    
    def update_vehicle(self, class_name: str, old_name: str, new_name: str) -> bool:
        if class_name not in self.data:
            return False
        vehicles = self.data[class_name]["vehicles"]
        if old_name in vehicles:
            idx = vehicles.index(old_name)
            vehicles[idx] = new_name
            vehicles.sort()
            return self.save()
        return False
    
    def get_unassigned_vehicles(self, all_vehicles: Set[str]) -> List[str]:
        assigned = self.get_all_vehicles()
        unassigned = all_vehicles - assigned
        return sorted(unassigned)


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
            self.class_name_edit.setEnabled(False)
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
        
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("Class Name:"))
        self.class_name_edit = QLineEdit()
        self.class_name_edit.setPlaceholderText("e.g., GT_2012, Formula_4")
        name_layout.addWidget(self.class_name_edit)
        layout.addLayout(name_layout)
        
        layout.addWidget(QLabel("Vehicles in this class:"))
        
        self.vehicles_list = QListWidget()
        self.vehicles_list.setSelectionMode(QAbstractItemView.ExtendedSelection)
        layout.addWidget(self.vehicles_list)
        
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
        
        new_vehicle_layout = QHBoxLayout()
        self.new_vehicle_edit = QLineEdit()
        self.new_vehicle_edit.setPlaceholderText("New vehicle name...")
        new_vehicle_layout.addWidget(self.new_vehicle_edit)
        
        self.add_new_btn = QPushButton("Add")
        self.add_new_btn.clicked.connect(self.add_new_vehicle)
        new_vehicle_layout.addWidget(self.add_new_btn)
        
        layout.addLayout(new_vehicle_layout)
        
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
    
    def load_vehicles(self):
        self.vehicles_list.clear()
        for vehicle in sorted(self.vehicles):
            self.vehicles_list.addItem(vehicle)
    
    def add_vehicle(self):
        vehicle_name, ok = QInputDialog.getText(self, "Add Vehicle", "Vehicle name:")
        if ok and vehicle_name.strip():
            if vehicle_name.strip() not in self.vehicles:
                self.vehicles.append(vehicle_name.strip())
                self.vehicles.sort()
                self.load_vehicles()
    
    def edit_vehicle(self):
        current = self.vehicles_list.currentItem()
        if not current:
            return
        old_name = current.text()
        new_name, ok = QInputDialog.getText(self, "Edit Vehicle", "New vehicle name:", text=old_name)
        if ok and new_name.strip() and new_name.strip() != old_name:
            idx = self.vehicles.index(old_name)
            self.vehicles[idx] = new_name.strip()
            self.vehicles.sort()
            self.load_vehicles()
    
    def add_new_vehicle(self):
        vehicle_name = self.new_vehicle_edit.text().strip()
        if vehicle_name and vehicle_name not in self.vehicles:
            self.vehicles.append(vehicle_name)
            self.vehicles.sort()
            self.load_vehicles()
            self.new_vehicle_edit.clear()
    
    def remove_vehicles(self):
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


class VehicleManagerDialog(QDialog):
    """Standalone dialog for managing vehicle classes"""
    
    classes_updated = pyqtSignal()
    
    def __init__(self, parent=None, gtr2_path: Path = None):
        super().__init__(parent)
        self.manager = VehicleClassesManager()
        self.gtr2_path = gtr2_path
        self.imported_vehicles = set()
        self.car_importer = None
        self.mode = "standalone"
        
        self.setup_ui()
        self.load_data()
        
        if self.gtr2_path and self.gtr2_path.exists():
            self.import_cars()
    
    def setup_ui(self):
        self.setWindowTitle("Vehicle Classes Manager")
        self.setGeometry(100, 100, 1300, 800)
        
        self.setStyleSheet("""
            QDialog {
                background-color: #1e1e1e;
            }
            QLabel {
                color: white;
            }
            QGroupBox {
                color: #FFA500;
                border: 2px solid #555;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
                font-size: 14px;
                font-weight: bold;
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
                border-radius: 4px;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton#delete {
                background-color: #f44336;
            }
            QPushButton#delete:hover {
                background-color: #d32f2f;
            }
            QPushButton#import {
                background-color: #FF9800;
            }
            QPushButton#import:hover {
                background-color: #F57C00;
            }
            QListWidget {
                background-color: #2b2b2b;
                color: white;
                border: 1px solid #4CAF50;
                border-radius: 4px;
                outline: none;
            }
            QListWidget::item:selected {
                background-color: #4CAF50;
            }
            QListWidget::item:hover {
                background-color: #3c3c3c;
            }
            QLineEdit {
                background-color: #3c3c3c;
                color: white;
                border: 1px solid #4CAF50;
                border-radius: 4px;
                padding: 6px;
            }
            QSplitter::handle {
                background-color: #555;
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
        """)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        title = QLabel("Vehicle Classes Manager")
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: #4CAF50;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        layout.addSpacing(10)
        
        self.import_progress = QProgressBar()
        self.import_progress.setVisible(False)
        layout.addWidget(self.import_progress)
        
        if self.mode == "standalone" or not self.gtr2_path:
            import_group = QGroupBox("Import Vehicles from GTR2 Installation")
            import_layout = QHBoxLayout(import_group)
            
            self.gtr2_path_label = QLabel("No GTR2 folder selected")
            self.gtr2_path_label.setStyleSheet("color: #888; font-family: monospace;")
            self.gtr2_path_label.setWordWrap(True)
            import_layout.addWidget(self.gtr2_path_label, 1)
            
            self.select_gtr2_btn = QPushButton("Select GTR2 Folder")
            self.select_gtr2_btn.clicked.connect(self.select_gtr2_folder)
            import_layout.addWidget(self.select_gtr2_btn)
            
            self.import_cars_btn = QPushButton("Import Cars")
            self.import_cars_btn.setObjectName("import")
            self.import_cars_btn.setEnabled(False)
            self.import_cars_btn.clicked.connect(self.import_cars)
            import_layout.addWidget(self.import_cars_btn)
            
            layout.addWidget(import_group)
            layout.addSpacing(10)
        
        main_splitter = QSplitter(Qt.Horizontal)
        
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.addWidget(QLabel("Vehicle Classes:"))
        
        self.class_list = QListWidget()
        self.class_list.setSelectionMode(QAbstractItemView.SingleSelection)
        self.class_list.itemSelectionChanged.connect(self.on_class_selected)
        left_layout.addWidget(self.class_list)
        
        class_btn_layout = QHBoxLayout()
        self.add_class_btn = QPushButton("Add Class")
        self.add_class_btn.clicked.connect(self.add_class)
        class_btn_layout.addWidget(self.add_class_btn)
        self.rename_class_btn = QPushButton("Rename")
        self.rename_class_btn.clicked.connect(self.rename_class)
        class_btn_layout.addWidget(self.rename_class_btn)
        self.delete_class_btn = QPushButton("Delete")
        self.delete_class_btn.setObjectName("delete")
        self.delete_class_btn.clicked.connect(self.delete_class)
        class_btn_layout.addWidget(self.delete_class_btn)
        left_layout.addLayout(class_btn_layout)
        main_splitter.addWidget(left_panel)
        
        middle_panel = QWidget()
        middle_layout = QVBoxLayout(middle_panel)
        middle_layout.setContentsMargins(0, 0, 0, 0)
        
        self.selected_class_label = QLabel("No class selected")
        self.selected_class_label.setStyleSheet("color: #4CAF50; font-weight: bold; font-size: 14px;")
        middle_layout.addWidget(self.selected_class_label)
        middle_layout.addSpacing(5)
        middle_layout.addWidget(QLabel("Vehicles in this class:"))
        
        self.vehicles_list = QListWidget()
        self.vehicles_list.setSelectionMode(QAbstractItemView.ExtendedSelection)
        middle_layout.addWidget(self.vehicles_list)
        
        vehicle_btn_layout = QHBoxLayout()
        self.add_vehicle_btn = QPushButton("Add Vehicle")
        self.add_vehicle_btn.clicked.connect(self.add_vehicle)
        vehicle_btn_layout.addWidget(self.add_vehicle_btn)
        self.edit_vehicle_btn = QPushButton("Edit Vehicle")
        self.edit_vehicle_btn.clicked.connect(self.edit_vehicle)
        vehicle_btn_layout.addWidget(self.edit_vehicle_btn)
        self.remove_vehicle_btn = QPushButton("Remove Vehicle(s)")
        self.remove_vehicle_btn.setObjectName("delete")
        self.remove_vehicle_btn.clicked.connect(self.remove_vehicles)
        vehicle_btn_layout.addWidget(self.remove_vehicle_btn)
        middle_layout.addLayout(vehicle_btn_layout)
        
        quick_layout = QHBoxLayout()
        quick_layout.addWidget(QLabel("Quick Add:"))
        self.new_vehicle_edit = QLineEdit()
        self.new_vehicle_edit.setPlaceholderText("Vehicle name...")
        self.new_vehicle_edit.returnPressed.connect(self.quick_add_vehicle)
        quick_layout.addWidget(self.new_vehicle_edit)
        self.quick_add_btn = QPushButton("Add")
        self.quick_add_btn.clicked.connect(self.quick_add_vehicle)
        quick_layout.addWidget(self.quick_add_btn)
        middle_layout.addLayout(quick_layout)
        
        main_splitter.addWidget(middle_panel)
        
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.addWidget(QLabel("Unassigned Vehicles (from GTR2):"))
        right_layout.addWidget(QLabel("Select vehicles and click 'Add to Class' to assign"))
        
        self.unassigned_list = QListWidget()
        self.unassigned_list.setSelectionMode(QAbstractItemView.ExtendedSelection)
        right_layout.addWidget(self.unassigned_list)
        
        transfer_layout = QHBoxLayout()
        self.add_to_class_btn = QPushButton("Add to Class")
        self.add_to_class_btn.setEnabled(False)
        self.add_to_class_btn.clicked.connect(self.add_selected_to_class)
        transfer_layout.addWidget(self.add_to_class_btn)
        self.refresh_unassigned_btn = QPushButton("Refresh List")
        self.refresh_unassigned_btn.clicked.connect(self.refresh_unassigned_list)
        transfer_layout.addWidget(self.refresh_unassigned_btn)
        right_layout.addLayout(transfer_layout)
        
        self.import_status = QLabel("")
        self.import_status.setStyleSheet("color: #888; font-size: 10px;")
        right_layout.addWidget(self.import_status)
        
        main_splitter.addWidget(right_panel)
        main_splitter.setSizes([250, 350, 400])
        layout.addWidget(main_splitter)
        
        bottom_layout = QHBoxLayout()
        bottom_layout.addStretch()
        self.save_btn = QPushButton("Save Changes")
        self.save_btn.setStyleSheet("background-color: #4CAF50; font-size: 14px; padding: 10px 24px;")
        self.save_btn.clicked.connect(self.save_changes)
        bottom_layout.addWidget(self.save_btn)
        self.close_btn = QPushButton("Close")
        self.close_btn.clicked.connect(self.accept)
        bottom_layout.addWidget(self.close_btn)
        layout.addLayout(bottom_layout)
    
    def load_data(self):
        self.class_list.clear()
        for class_name in self.manager.get_all_classes():
            self.class_list.addItem(class_name)
    
    def on_class_selected(self):
        current = self.class_list.currentItem()
        if not current:
            self.selected_class_label.setText("No class selected")
            self.vehicles_list.clear()
            self.add_to_class_btn.setEnabled(False)
            return
        class_name = current.text()
        self.selected_class_label.setText(f"Class: {class_name}")
        self.add_to_class_btn.setEnabled(True)
        self.vehicles_list.clear()
        for vehicle in self.manager.get_vehicles_for_class(class_name):
            self.vehicles_list.addItem(vehicle)
    
    def select_gtr2_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select GTR2 Installation Folder", str(Path.home()))
        if folder:
            self.gtr2_path = Path(folder)
            self.gtr2_path_label.setText(str(self.gtr2_path))
            self.gtr2_path_label.setStyleSheet("color: #4CAF50; font-family: monospace;")
            self.import_cars_btn.setEnabled(True)
            self.import_status.setText("Ready to import. Click 'Import Cars'")
    
    def import_cars(self):
        if not self.gtr2_path:
            QMessageBox.warning(self, "No Folder", "Please select GTR2 installation folder first.")
            return
        
        reply = QMessageBox.question(self, "Confirm Import",
            f"This will scan all .car files in:\n{self.gtr2_path / 'GameData' / 'Teams'}\n\n"
            f"This may take a few minutes for large installations.\n\nContinue?",
            QMessageBox.Yes | QMessageBox.No)
        
        if reply != QMessageBox.Yes:
            return
        
        if hasattr(self, 'import_cars_btn'):
            self.import_cars_btn.setEnabled(False)
        if hasattr(self, 'select_gtr2_btn'):
            self.select_gtr2_btn.setEnabled(False)
        
        self.import_progress.setVisible(True)
        self.import_status.setText("Importing vehicles... Please wait.")
        
        self.car_importer = CarImporter(self.gtr2_path)
        self.car_importer.progress.connect(self.on_import_progress)
        self.car_importer.finished.connect(self.on_import_finished)
        self.car_importer.error.connect(self.on_import_error)
        self.car_importer.start()
    
    def on_import_progress(self, current: int, total: int, message: str):
        if total > 0:
            self.import_progress.setMaximum(total)
            self.import_progress.setValue(current)
        self.import_progress.setFormat(f"{message} ({current}/{total})")
        self.import_status.setText(f"Progress: {current}/{total} - {message}")
    
    def on_import_finished(self, vehicles: set):
        self.imported_vehicles = vehicles
        self.refresh_unassigned_list()
        
        if hasattr(self, 'import_cars_btn'):
            self.import_cars_btn.setEnabled(True)
        if hasattr(self, 'select_gtr2_btn'):
            self.select_gtr2_btn.setEnabled(True)
        
        self.import_progress.setVisible(False)
        
        QMessageBox.information(self, "Import Complete",
            f"Found {len(vehicles)} unique vehicles in GTR2 installation.\n\n"
            f"Unassigned vehicles are shown in the right panel.\n"
            f"Select a class on the left, then select vehicles and click 'Add to Class' to assign them.")
        
        self.import_status.setText(f"Import complete: {len(vehicles)} vehicles found")
    
    def on_import_error(self, error_msg: str):
        if hasattr(self, 'import_cars_btn'):
            self.import_cars_btn.setEnabled(True)
        if hasattr(self, 'select_gtr2_btn'):
            self.select_gtr2_btn.setEnabled(True)
        self.import_progress.setVisible(False)
        self.import_status.setText(f"Error: {error_msg}")
        QMessageBox.critical(self, "Import Error", error_msg)
    
    def refresh_unassigned_list(self):
        if not self.imported_vehicles:
            self.unassigned_list.clear()
            self.unassigned_list.addItem("No vehicles imported yet. Click 'Import Cars' first.")
            return
        
        unassigned = self.manager.get_unassigned_vehicles(self.imported_vehicles)
        self.unassigned_list.clear()
        if unassigned:
            for vehicle in unassigned:
                self.unassigned_list.addItem(vehicle)
        else:
            self.unassigned_list.addItem("All vehicles are assigned to classes!")
    
    def add_selected_to_class(self):
        current_class = self.class_list.currentItem()
        if not current_class:
            QMessageBox.warning(self, "No Class", "Please select a class first.")
            return
        
        selected = self.unassigned_list.selectedItems()
        if not selected:
            QMessageBox.warning(self, "No Selection", "Please select vehicles to add.")
            return
        
        class_name = current_class.text()
        vehicle_names = [item.text() for item in selected]
        
        reply = QMessageBox.question(self, "Confirm Assignment",
            f"Add {len(vehicle_names)} vehicle(s) to class '{class_name}'?",
            QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            added = self.manager.add_vehicles_batch(class_name, vehicle_names)
            if added > 0:
                self.refresh_unassigned_list()
                self.on_class_selected()
                self.classes_updated.emit()
                QMessageBox.information(self, "Success", f"Added {added} vehicle(s) to '{class_name}'")
            else:
                QMessageBox.warning(self, "Error", "Failed to add vehicles.")
    
    def add_class(self):
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
        current = self.class_list.currentItem()
        if not current:
            QMessageBox.warning(self, "No Selection", "Please select a class to rename.")
            return
        old_name = current.text()
        new_name, ok = QInputDialog.getText(self, "Rename Class", "New class name:", text=old_name)
        if ok and new_name.strip() and new_name.strip() != old_name:
            if self.manager.rename_class(old_name, new_name.strip()):
                self.load_data()
                self.classes_updated.emit()
                QMessageBox.information(self, "Success", f"Renamed '{old_name}' to '{new_name}'")
            else:
                QMessageBox.warning(self, "Error", f"Could not rename. Name '{new_name}' may already exist.")
    
    def delete_class(self):
        current = self.class_list.currentItem()
        if not current:
            QMessageBox.warning(self, "No Selection", "Please select a class to delete.")
            return
        class_name = current.text()
        reply = QMessageBox.question(self, "Confirm Delete",
            f"Delete class '{class_name}' and all its vehicles?\nThis cannot be undone.",
            QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            if self.manager.delete_class(class_name):
                self.load_data()
                self.refresh_unassigned_list()
                self.classes_updated.emit()
                QMessageBox.information(self, "Success", f"Deleted class: {class_name}")
            else:
                QMessageBox.warning(self, "Error", "Failed to delete class.")
    
    def add_vehicle(self):
        current = self.class_list.currentItem()
        if not current:
            QMessageBox.warning(self, "No Selection", "Please select a class first.")
            return
        class_name = current.text()
        vehicle_name, ok = QInputDialog.getText(self, "Add Vehicle", f"Vehicle name for class '{class_name}':")
        if ok and vehicle_name.strip():
            if self.manager.add_vehicle(class_name, vehicle_name.strip()):
                self.on_class_selected()
                self.refresh_unassigned_list()
                self.classes_updated.emit()
                QMessageBox.information(self, "Success", f"Added '{vehicle_name}' to '{class_name}'")
            else:
                QMessageBox.warning(self, "Error", "Failed to add vehicle.")
    
    def edit_vehicle(self):
        current_class = self.class_list.currentItem()
        current_vehicle = self.vehicles_list.currentItem()
        if not current_class or not current_vehicle:
            QMessageBox.warning(self, "No Selection", "Please select a class and a vehicle.")
            return
        class_name = current_class.text()
        old_name = current_vehicle.text()
        new_name, ok = QInputDialog.getText(self, "Edit Vehicle", "New vehicle name:", text=old_name)
        if ok and new_name.strip() and new_name.strip() != old_name:
            if self.manager.update_vehicle(class_name, old_name, new_name.strip()):
                self.on_class_selected()
                self.refresh_unassigned_list()
                self.classes_updated.emit()
                QMessageBox.information(self, "Success", f"Updated vehicle name")
            else:
                QMessageBox.warning(self, "Error", "Failed to update vehicle.")
    
    def remove_vehicles(self):
        current_class = self.class_list.currentItem()
        selected = self.vehicles_list.selectedItems()
        if not current_class or not selected:
            QMessageBox.warning(self, "No Selection", "Please select vehicles to remove.")
            return
        class_name = current_class.text()
        vehicle_names = [item.text() for item in selected]
        reply = QMessageBox.question(self, "Confirm Remove",
            f"Remove {len(vehicle_names)} vehicle(s) from '{class_name}'?\nThey will become unassigned.",
            QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            removed = self.manager.remove_vehicles_batch(class_name, vehicle_names)
            self.on_class_selected()
            self.refresh_unassigned_list()
            self.classes_updated.emit()
            QMessageBox.information(self, "Success", f"Removed {removed} vehicle(s).")
    
    def quick_add_vehicle(self):
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
            self.refresh_unassigned_list()
            self.classes_updated.emit()
            self.new_vehicle_edit.clear()
        else:
            QMessageBox.warning(self, "Error", f"Could not add '{vehicle_name}'. It may already exist.")
    
    def save_changes(self):
        if self.manager.save():
            QMessageBox.information(self, "Success", "Vehicle classes saved successfully!")
            self.classes_updated.emit()
        else:
            QMessageBox.critical(self, "Error", "Failed to save vehicle classes.")


def launch_vehicle_manager(gtr2_path: Path = None, parent=None):
    """
    Launch the vehicle manager dialog.
    
    Args:
        gtr2_path: Optional GTR2 installation path for auto-import
        parent: Optional parent widget
    
    Returns:
        True if changes were saved, False otherwise
    """
    dialog = VehicleManagerDialog(parent, gtr2_path)
    result = dialog.exec_()
    return result == QDialog.Accepted


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    dialog = VehicleManagerDialog()
    dialog.show()
    sys.exit(app.exec_())
