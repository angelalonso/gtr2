#!/usr/bin/env python3
"""
Pre-run check dialog for Live AI Tuner
"""

import sys
import subprocess
from pathlib import Path
from typing import Tuple

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGroupBox, QTextEdit, QProgressBar, QApplication, QMessageBox
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont

from core_config import (
    get_config_with_defaults, create_default_config_if_missing,
    load_config, get_base_path
)
from core_vehicle_scanner import find_missing_vehicles, load_vehicle_classes, scan_vehicles_from_gtr2
from gui_vehicle_manager import launch_vehicle_manager


class VehicleScanWorker(QThread):
    """Worker thread for scanning vehicles without blocking UI"""
    
    progress = pyqtSignal(int, int, str)
    finished = pyqtSignal(set, set, set)
    error = pyqtSignal(str)
    
    def __init__(self, gtr2_path: Path, classes_path: Path):
        super().__init__()
        self.gtr2_path = gtr2_path
        self.classes_path = classes_path
    
    def run(self):
        try:
            all_vehicles, defined_vehicles, missing_vehicles = find_missing_vehicles(
                self.gtr2_path, 
                self.classes_path,
                lambda c, t, m: self.progress.emit(c, t, m)
            )
            self.finished.emit(all_vehicles, defined_vehicles, missing_vehicles)
        except Exception as e:
            self.error.emit(str(e))


class PreRunCheckDialog(QDialog):
    """Dialog that performs pre-run checks before the main application starts"""
    
    def __init__(self, config_file: str = "cfg.yml", parent=None):
        super().__init__(parent)
        self.config_file = config_file
        self.check_results = {}
        self.all_checks_passed = False
        self.vehicle_scan_worker = None
        self.datamgmt_process = None
        self.setup_ui()
        self.run_checks()
    
    def setup_ui(self):
        self.setWindowTitle("Live AI Tuner - Pre-Run Checks")
        self.setFixedSize(850, 850)
        self.setModal(True)
        
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
                padding: 12px 24px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton#retry {
                background-color: #FF9800;
            }
            QPushButton#retry:hover {
                background-color: #F57C00;
            }
            QPushButton#fix_vehicles {
                background-color: #9C27B0;
            }
            QPushButton#fix_vehicles:hover {
                background-color: #7B1FA2;
            }
            QPushButton#continue:disabled {
                background-color: #555;
                color: #888;
            }
            QTextEdit {
                background-color: #2b2b2b;
                color: #4CAF50;
                border: 2px solid #4CAF50;
                border-radius: 6px;
                font-family: monospace;
                font-size: 12px;
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
        layout.setContentsMargins(25, 25, 25, 25)
        
        self.scan_progress = QProgressBar()
        self.scan_progress.setVisible(False)
        layout.addWidget(self.scan_progress)
        
        self.status_group = QGroupBox("Check Status")
        status_layout = QVBoxLayout(self.status_group)
        
        self.status_text = QTextEdit()
        self.status_text.setReadOnly(True)
        self.status_text.setMinimumHeight(400)
        self.status_text.setFont(QFont("Monospace", 11))
        status_layout.addWidget(self.status_text)
        
        layout.addWidget(self.status_group)
        
        layout.addSpacing(10)
        
        self.result_label = QLabel("")
        self.result_label.setAlignment(Qt.AlignCenter)
        self.result_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(self.result_label)
        
        layout.addSpacing(15)
        
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.fix_vehicles_btn = QPushButton("Open Vehicle Manager to Fix Missing Vehicles")
        self.fix_vehicles_btn.setObjectName("fix_vehicles")
        self.fix_vehicles_btn.setVisible(False)
        self.fix_vehicles_btn.clicked.connect(self.open_vehicle_manager)
        button_layout.addWidget(self.fix_vehicles_btn)
        
        self.retry_btn = QPushButton("Retry Checks")
        self.retry_btn.setObjectName("retry")
        self.retry_btn.clicked.connect(self.run_checks)
        button_layout.addWidget(self.retry_btn)
        
        self.continue_btn = QPushButton("Continue to Application")
        self.continue_btn.setObjectName("continue")
        self.continue_btn.setEnabled(False)
        self.continue_btn.clicked.connect(self.accept)
        button_layout.addWidget(self.continue_btn)
        
        button_layout.addStretch()
        layout.addLayout(button_layout)
        
        layout.addSpacing(15)
        
        self.info_group = QGroupBox("How to Use")
        info_layout = QVBoxLayout(self.info_group)
        
        colored_text = (
            '<span style="color: white;">1. LEAVE THIS APPLICATION RUNNING</span><br>'
            '<span style="color: white;">2. Launch GTR2 and start your race session</span><br><br>'
            '<span style="color: #FFA500;">TIPS:</span><br>'
            '<span style="color: white;"> - Complete qualifying and the race normally</span><br>'
            '<span style="color: white;"> - The application will detect your race results</span><br>'
            '<span style="color: white;"> - AI ratios will be automatically calculated and applied</span><br>'
            '<span style="color: white;"> - Each race makes the AI adapt to your pace.</span>'
        )
        self.info_text = QLabel(colored_text)
        self.info_text.setWordWrap(True)
        self.info_text.setTextFormat(Qt.RichText)
        self.info_text.setStyleSheet("font-size: 14px; line-height: 1.8; font-weight: normal; background-color: transparent;")
        self.info_text.setAlignment(Qt.AlignLeft)
        info_layout.addWidget(self.info_text)
        
        layout.addWidget(self.info_group)
        self.info_group.setVisible(False)
    
    def log_check(self, check_name: str, status: str, message: str = ""):
        color = ""
        if status == "PASS":
            color = "#4CAF50"
        elif status == "WARN":
            color = "#FF9800"
        elif status == "FAIL":
            color = "#f44336"
        elif status == "CHECK":
            color = "#FFA500"
        elif status == "INFO":
            color = "#888"
        
        if color:
            if status == "PASS":
                formatted = f'<span style="color: {color}; font-weight: bold; font-size: 14px;">[PASS]</span> <span style="font-size: 13px;">{check_name}</span>'
            elif status == "FAIL":
                formatted = f'<span style="color: {color}; font-weight: bold; font-size: 14px;">[FAIL]</span> <span style="font-size: 13px;">{check_name}</span>'
            elif status == "WARN":
                formatted = f'<span style="color: {color}; font-weight: bold; font-size: 14px;">[WARN]</span> <span style="font-size: 13px;">{check_name}</span>'
            elif status == "CHECK":
                formatted = f'<span style="color: {color}; font-size: 13px;">[CHECK]</span> <span style="font-size: 13px;">{check_name}</span>'
            else:
                formatted = f'<span style="color: {color}; font-weight: bold;">[{status}]</span> {check_name}'
        else:
            formatted = f"[{status}] {check_name}"
        
        if message:
            if len(message) > 200:
                message = message[:197] + "..."
            formatted += f': <span style="color: #aaa;">{message}</span>'
        
        self.status_text.append(formatted)
        QApplication.processEvents()
    
    def run_checks(self):
        self.status_text.clear()
        self.check_results = {}
        self.continue_btn.setEnabled(False)
        self.fix_vehicles_btn.setVisible(False)
        self.info_group.setVisible(False)
        self.result_label.setText("")
        self.scan_progress.setVisible(False)
        
        checks = [
            ("Configuration File", self.check_config_file),
            ("Vehicle Classes File", self.check_vehicle_classes_file),
            ("Vehicle Classes Data", self.check_vehicle_classes_data),
            ("GTR2 Base Path", self.check_base_path),
            ("GTR2 Executable", self.check_gtr2_executable),
            ("Vehicle Definitions Complete", self.check_vehicle_definitions),
        ]
        
        all_passed = True
        
        for check_name, check_func in checks:
            self.log_check(check_name, "CHECK", "Running...")
            QApplication.processEvents()
            
            try:
                passed, message = check_func()
                status = "PASS" if passed else "FAIL"
                if not passed:
                    all_passed = False
                self.check_results[check_name] = passed
                self.log_check(check_name, status, message)
            except Exception as e:
                all_passed = False
                self.log_check(check_name, "FAIL", str(e))
            
            QApplication.processEvents()
        
        self.all_checks_passed = all_passed
        
        vehicle_check_failed = not self.check_results.get("Vehicle Definitions Complete", False)
        if vehicle_check_failed:
            self.fix_vehicles_btn.setVisible(True)
        
        if all_passed:
            self.result_label.setText("ALL CHECKS PASSED - System is ready")
            self.result_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #4CAF50;")
            self.log_check("SUMMARY", "INFO", "All checks passed. You can continue to the application.")
            self.continue_btn.setEnabled(True)
            self.continue_btn.setFocus()
            self.info_group.setVisible(True)
        else:
            self.result_label.setText("SOME CHECKS FAILED - Please fix issues and retry")
            self.result_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #f44336;")
            self.log_check("SUMMARY", "FAIL", "Some checks failed. Please fix the issues and retry.")
            
            guidance_msg = "Make sure:\n"
            guidance_msg += "1. cfg.yml exists in the application directory\n"
            guidance_msg += "2. vehicle_classes.json exists and is valid\n"
            guidance_msg += "3. GTR2 base path is correctly set in cfg.yml\n"
            guidance_msg += "4. GTR2.exe exists in the base path\n"
            
            if vehicle_check_failed:
                guidance_msg += "5. All vehicles in GTR2 are defined in vehicle_classes.json\n"
                guidance_msg += "   Click 'Open Vehicle Manager' to add missing vehicles to classes"
            else:
                guidance_msg += "5. All vehicles in GTR2 are defined in vehicle_classes.json"
            
            self.log_check("GUIDANCE", "INFO", guidance_msg)
    
    def open_vehicle_manager(self):
        config = get_config_with_defaults(self.config_file)
        base_path = config.get('base_path', '')
        gtr2_path = Path(base_path) if base_path and Path(base_path).exists() else None
        
        launch_vehicle_manager(gtr2_path, self)
        
        reply = QMessageBox.question(
            self, "Retry Checks?",
            "Have you finished adding vehicles to classes?\n\n"
            "Click Yes to retry the checks, or No to continue without retrying.",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.run_checks()
    
    def check_config_file(self) -> Tuple[bool, str]:
        config_path = Path(self.config_file)
        
        if not config_path.exists():
            if create_default_config_if_missing(self.config_file):
                return True, "Created default cfg.yml"
            return False, f"File not found: {self.config_file}"
        
        try:
            config = load_config(self.config_file)
            if config is None:
                return False, "Failed to load config (invalid YAML)"
            
            required_keys = ['base_path', 'db_path']
            for key in required_keys:
                if key not in config:
                    return False, f"Missing required key: {key}"
            
            return True, f"Valid config file (base_path: {config.get('base_path', 'not set')})"
        except Exception as e:
            return False, f"Error reading config: {str(e)}"
    
    def check_vehicle_classes_file(self) -> Tuple[bool, str]:
        classes_path = Path(__file__).parent / "vehicle_classes.json"
        
        if not classes_path.exists():
            return False, f"File not found: {classes_path}"
        
        try:
            import json
            with open(classes_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if not isinstance(data, dict):
                return False, "File does not contain a JSON object"
            
            return True, f"Valid JSON file with {len(data)} classes"
        except json.JSONDecodeError as e:
            return False, f"Invalid JSON: {str(e)}"
        except Exception as e:
            return False, f"Error reading file: {str(e)}"
    
    def check_vehicle_classes_data(self) -> Tuple[bool, str]:
        classes_path = Path(__file__).parent / "vehicle_classes.json"
        
        if not classes_path.exists():
            return False, "vehicle_classes.json not found"
        
        try:
            import json
            with open(classes_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if not isinstance(data, dict):
                return False, "Root must be a dictionary"
            
            if len(data) == 0:
                return False, "No classes defined"
            
            class_count = 0
            vehicle_count = 0
            
            for class_name, class_data in data.items():
                if not isinstance(class_name, str):
                    return False, f"Class name must be string: {class_name}"
                
                if not isinstance(class_data, dict):
                    return False, f"Class data for '{class_name}' must be a dictionary"
                
                if 'vehicles' not in class_data:
                    return False, f"Missing 'vehicles' key in class '{class_name}'"
                
                vehicles = class_data['vehicles']
                if not isinstance(vehicles, list):
                    return False, f"'vehicles' in '{class_name}' must be a list"
                
                class_count += 1
                vehicle_count += len(vehicles)
                
                for vehicle in vehicles:
                    if not isinstance(vehicle, str):
                        return False, f"Vehicle name in '{class_name}' must be string"
            
            return True, f"{class_count} classes, {vehicle_count} vehicles (valid structure)"
            
        except json.JSONDecodeError as e:
            return False, f"Invalid JSON: {str(e)}"
        except Exception as e:
            return False, f"Error validating: {str(e)}"
    
    def check_base_path(self) -> Tuple[bool, str]:
        config = get_config_with_defaults(self.config_file)
        base_path = config.get('base_path', '')
        
        if not base_path:
            return False, "No base path configured in cfg.yml"
        
        path = Path(base_path)
        
        if not path.exists():
            return False, f"Path does not exist: {base_path}"
        
        if not path.is_dir():
            return False, f"Not a directory: {base_path}"
        
        game_data = path / "GameData"
        user_data = path / "UserData"
        
        missing = []
        if not game_data.exists():
            missing.append("GameData")
        if not user_data.exists():
            missing.append("UserData")
        
        if missing:
            return False, f"Missing required directories: {', '.join(missing)}"
        
        return True, f"Valid GTR2 path: {base_path}"
    
    def check_gtr2_executable(self) -> Tuple[bool, str]:
        config = get_config_with_defaults(self.config_file)
        base_path = config.get('base_path', '')
        
        if not base_path:
            return False, "No base path configured"
        
        base_path_obj = Path(base_path)
        
        gtr2_exe = base_path_obj / "GTR2.exe"
        if gtr2_exe.exists():
            return True, "Found GTR2.exe"
        
        gtr2_exe_lower = base_path_obj / "gtr2.exe"
        if gtr2_exe_lower.exists():
            return True, "Found gtr2.exe"
        
        for exe_candidate in base_path_obj.rglob("*.exe"):
            if exe_candidate.name.lower() == "gtr2.exe":
                return True, f"Found GTR2.exe at: {exe_candidate}"
        
        return False, "GTR2.exe not found in the GTR2 installation path"
    
    def check_vehicle_definitions(self) -> Tuple[bool, str]:
        config = get_config_with_defaults(self.config_file)
        base_path = config.get('base_path', '')
        
        if not base_path:
            return False, "No base path configured - cannot scan vehicles"
        
        gtr2_path = Path(base_path)
        classes_path = Path(__file__).parent / "vehicle_classes.json"
        
        if not classes_path.exists():
            return False, f"vehicle_classes.json not found at {classes_path}"
        
        self.scan_progress.setVisible(True)
        self.scan_progress.setValue(0)
        
        self.vehicle_scan_worker = VehicleScanWorker(gtr2_path, classes_path)
        self.vehicle_scan_worker.progress.connect(self.on_scan_progress)
        self.vehicle_scan_worker.finished.connect(self.on_scan_finished)
        self.vehicle_scan_worker.error.connect(self.on_scan_error)
        
        self.scan_complete = False
        self.scan_result = None
        self.vehicle_scan_worker.start()
        
        while not hasattr(self, 'scan_complete') or not self.scan_complete:
            QApplication.processEvents()
            if hasattr(self, 'scan_result') and self.scan_result is not None:
                break
            self.msleep(100)
        
        self.scan_progress.setVisible(False)
        
        if hasattr(self, 'scan_result') and self.scan_result:
            all_vehicles, defined_vehicles, missing_vehicles = self.scan_result
            
            if not all_vehicles:
                return False, "No vehicles found in GTR2 installation (check GameData/Teams directory)"
            
            missing_count = len(missing_vehicles)
            
            if missing_count > 0:
                self.missing_vehicles_list = list(missing_vehicles)
                missing_list = list(missing_vehicles)[:10]
                missing_display = ", ".join(missing_list)
                if missing_count > 10:
                    missing_display += f" and {missing_count - 10} more..."
                
                return False, f"{missing_count} vehicle(s) missing from vehicle_classes.json: {missing_display}"
            
            return True, f"All {len(all_vehicles)} vehicles from GTR2 are defined in vehicle_classes.json"
        else:
            return False, "Failed to scan vehicles from GTR2 installation"
    
    def on_scan_progress(self, current: int, total: int, message: str):
        if total > 0:
            self.scan_progress.setMaximum(total)
            self.scan_progress.setValue(current)
        self.scan_progress.setFormat(f"{message} ({current}/{total})")
        QApplication.processEvents()
    
    def on_scan_finished(self, all_vehicles: set, defined_vehicles: set, missing_vehicles: set):
        self.scan_result = (all_vehicles, defined_vehicles, missing_vehicles)
        self.scan_complete = True
    
    def on_scan_error(self, error_msg: str):
        self.scan_result = None
        self.scan_complete = True
        self.log_check("Vehicle Scan", "ERROR", error_msg)
    
    def msleep(self, ms: int):
        from PyQt5.QtCore import QEventLoop, QTimer
        loop = QEventLoop()
        QTimer.singleShot(ms, loop.quit)
        loop.exec_()
    
    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter:
            if self.continue_btn.isEnabled():
                self.accept()
        else:
            super().keyPressEvent(event)
    
    def closeEvent(self, event):
        if self.datamgmt_process and self.datamgmt_process.poll() is None:
            self.datamgmt_process.terminate()
            try:
                self.datamgmt_process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self.datamgmt_process.kill()
        event.accept()
