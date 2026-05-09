#!/usr/bin/env python3
"""
Common Dialogs for Live AI Tuner
Provides reusable dialog components
"""

from pathlib import Path

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QDoubleSpinBox, QMessageBox, QFileDialog, QListWidget,
    QLineEdit, QInputDialog, QAbstractItemView, QDialogButtonBox
)
from PyQt5.QtCore import Qt

from core_config import get_ratio_limits


class ManualLapTimeDialog(QDialog):
    """Dialog for manually editing user lap time"""
    
    def __init__(self, parent, session_type: str, current_time: float = None):
        super().__init__(parent)
        self.session_type = session_type
        self.current_time = current_time if current_time is not None and current_time > 0 else None
        self.new_time = None
        self.setup_ui()
    
    def setup_ui(self):
        self.setWindowTitle(f"Edit {self.session_type.upper()} Lap Time")
        self.setFixedSize(350, 220)
        self.setStyleSheet("""
            QDialog {
                background-color: #2b2b2b;
            }
            QLabel {
                color: white;
            }
            QDoubleSpinBox {
                background-color: #3c3c3c;
                color: white;
                border: 1px solid #4CAF50;
                border-radius: 4px;
                padding: 4px;
                font-size: 14px;
            }
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton#cancel {
                background-color: #555;
            }
            QPushButton#cancel:hover {
                background-color: #666;
            }
        """)
        
        layout = QVBoxLayout(self)
        
        title = QLabel(f"Edit {self.session_type.upper()} Lap Time")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #FFA500;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        layout.addSpacing(10)
        
        if self.current_time is not None:
            current_label = QLabel(f"Current {self.session_type.upper()} Time:")
            current_label.setStyleSheet("color: #888;")
            layout.addWidget(current_label)
            
            minutes = int(self.current_time) // 60
            seconds = self.current_time % 60
            current_value = QLabel(f"{minutes}:{seconds:06.3f} ({self.current_time:.3f}s)")
            current_value.setStyleSheet("font-size: 14px; font-family: monospace; color: #4CAF50;")
            layout.addWidget(current_value)
        else:
            no_time_label = QLabel(f"No {self.session_type.upper()} time recorded yet")
            no_time_label.setStyleSheet("color: #FFA500; font-style: italic;")
            layout.addWidget(no_time_label)
        
        layout.addSpacing(15)
        
        new_label = QLabel(f"New {self.session_type.upper()} Time (seconds):")
        new_label.setStyleSheet("color: #888;")
        layout.addWidget(new_label)
        
        self.time_spin = QDoubleSpinBox()
        self.time_spin.setRange(10.0, 500.0)
        self.time_spin.setDecimals(3)
        self.time_spin.setSingleStep(0.5)
        if self.current_time is not None:
            self.time_spin.setValue(self.current_time)
        else:
            self.time_spin.setValue(90.0)
        self.time_spin.setStyleSheet("font-size: 14px;")
        layout.addWidget(self.time_spin)
        
        layout.addSpacing(20)
        
        btn_layout = QHBoxLayout()
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setObjectName("cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        
        apply_btn = QPushButton("Apply")
        apply_btn.setDefault(True)
        apply_btn.clicked.connect(self.accept)
        btn_layout.addWidget(apply_btn)
        
        layout.addLayout(btn_layout)
    
    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter:
            self.accept()
        else:
            super().keyPressEvent(event)
    
    def accept(self):
        self.new_time = self.time_spin.value()
        super().accept()


class ManualEditDialog(QDialog):
    """Dialog for manually editing a ratio in the AIW file"""
    
    def __init__(self, parent, ratio_name: str, current_ratio: float, aiw_path: Path = None, min_ratio: float = 0.5, max_ratio: float = 1.5):
        super().__init__(parent)
        self.ratio_name = ratio_name
        self.current_ratio = current_ratio
        self.aiw_path = aiw_path
        self.min_ratio = min_ratio
        self.max_ratio = max_ratio
        self.new_ratio = None
        self.setup_ui()
    
    def setup_ui(self):
        self.setWindowTitle(f"Manual Edit - {self.ratio_name}")
        self.setFixedSize(400, 250)
        
        self.setStyleSheet("""
            QDialog {
                background-color: #2b2b2b;
            }
            QLabel {
                color: white;
            }
            QDoubleSpinBox {
                background-color: #3c3c3c;
                color: white;
                border: 1px solid #4CAF50;
                border-radius: 4px;
                padding: 4px;
                font-size: 14px;
            }
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton#cancel {
                background-color: #555;
            }
            QPushButton#cancel:hover {
                background-color: #666;
            }
        """)
        
        layout = QVBoxLayout(self)
        
        title = QLabel(f"Edit {self.ratio_name}")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #FFA500;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        layout.addSpacing(10)
        
        current_label = QLabel(f"Current {self.ratio_name}:")
        current_label.setStyleSheet("color: #888;")
        layout.addWidget(current_label)
        
        current_value = QLabel(f"{self.current_ratio:.6f}")
        current_value.setStyleSheet("font-size: 14px; font-family: monospace; color: #4CAF50;")
        layout.addWidget(current_value)
        
        layout.addSpacing(15)
        
        new_label = QLabel(f"New {self.ratio_name} (min: {self.min_ratio}, max: {self.max_ratio}):")
        new_label.setStyleSheet("color: #888;")
        layout.addWidget(new_label)
        
        self.ratio_spin = QDoubleSpinBox()
        self.ratio_spin.setRange(self.min_ratio, self.max_ratio)
        self.ratio_spin.setDecimals(6)
        self.ratio_spin.setSingleStep(0.01)
        self.ratio_spin.setValue(self.current_ratio)
        self.ratio_spin.setStyleSheet("font-size: 14px;")
        layout.addWidget(self.ratio_spin)
        
        layout.addSpacing(10)
        
        if self.aiw_path:
            info = QLabel(f"AIW: {self.aiw_path.name}")
            info.setStyleSheet("color: #666; font-size: 9px;")
            info.setWordWrap(True)
            layout.addWidget(info)
        
        layout.addSpacing(20)
        
        btn_layout = QHBoxLayout()
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setObjectName("cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        
        apply_btn = QPushButton("Apply")
        apply_btn.setDefault(True)
        apply_btn.clicked.connect(self.accept)
        btn_layout.addWidget(apply_btn)
        
        layout.addLayout(btn_layout)
    
    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter:
            self.accept()
        else:
            super().keyPressEvent(event)
    
    def accept(self):
        self.new_ratio = self.ratio_spin.value()
        super().accept()


class AddEditClassDialog(QDialog):
    """Dialog for adding or editing a vehicle class"""
    
    def __init__(self, parent=None, class_name: str = None, vehicles: list = None):
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
    
    def get_vehicles(self) -> list:
        return self.vehicles
