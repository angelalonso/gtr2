#!/usr/bin/env python3
"""
Pre-run check dialog for Dynamic AI
Uses tkinter for minimal dependencies and faster startup
Optimized for efficiency with proper threading
"""

import sys
import json
import re
import threading
import subprocess
import time
import logging
from pathlib import Path
from typing import Tuple, Set, Optional, List
from dataclasses import dataclass

import tkinter as tk
from tkinter import ttk, messagebox

from core_config import (
    get_config_with_defaults, create_default_config_if_missing,
    load_config, get_base_path
)


# Set up logging for debugging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


@dataclass
class CheckResult:
    """Result of a single check"""
    name: str
    passed: bool
    message: str = ""
    critical: bool = True
    warning: bool = False


class VehicleScanWorker(threading.Thread):
    """Worker thread for scanning vehicles without blocking UI"""
    
    def __init__(self, gtr2_path: Path, classes_path: Path, callback, progress_callback=None):
        super().__init__()
        self.gtr2_path = gtr2_path
        self.classes_path = classes_path
        self.callback = callback
        self.progress_callback = progress_callback
        self._is_running = True
        self.daemon = True
    
    def stop(self):
        self._is_running = False
    
    def run(self):
        try:
            logger.info(f"Starting vehicle scan - GTR2 path: {self.gtr2_path}")
            result = self._scan_vehicles_efficient()
            if result:
                all_vehicles, defined_vehicles, missing_vehicles = result
                logger.info(f"Scan complete: {len(all_vehicles)} vehicles found, {len(missing_vehicles)} missing")
                self.callback(all_vehicles, defined_vehicles, missing_vehicles, None)
            else:
                logger.error("Scan returned no results")
                self.callback(None, None, None, "Scan returned no results")
        except Exception as e:
            logger.exception(f"Scan error: {e}")
            self.callback(None, None, None, str(e))
    
    def _scan_vehicles_efficient(self):
        """Efficient vehicle scanning using optimized file reading"""
        try:
            from core_vehicle_scanner import scan_vehicles_from_gtr2, load_vehicle_classes, get_all_defined_vehicles
            
            if not self.gtr2_path or not self.gtr2_path.exists():
                logger.error(f"GTR2 path invalid: {self.gtr2_path}")
                return None
            
            teams_dir = self.gtr2_path / "GameData" / "Teams"
            if not teams_dir.exists():
                logger.error(f"Teams directory not found: {teams_dir}")
                return None
            
            logger.info(f"Teams directory exists: {teams_dir}")
            
            # Scan vehicles from GTR2
            all_vehicles = scan_vehicles_from_gtr2(
                self.gtr2_path,
                lambda c, t, m: self.progress_callback(c, t, m) if self.progress_callback and self._is_running else None
            )
            
            if not all_vehicles:
                logger.warning("No vehicles found in GTR2 installation")
                return None
            
            logger.info(f"Found {len(all_vehicles)} vehicles in GTR2")
            
            # Load defined vehicles from classes file
            classes_data = load_vehicle_classes(self.classes_path)
            defined_vehicles = get_all_defined_vehicles(classes_data)
            
            logger.info(f"Found {len(defined_vehicles)} defined vehicles in classes file")
            
            missing_vehicles = all_vehicles - defined_vehicles
            
            logger.info(f"Missing vehicles: {len(missing_vehicles)}")
            if missing_vehicles:
                logger.debug(f"Sample missing: {list(missing_vehicles)[:5]}")
            
            return all_vehicles, defined_vehicles, missing_vehicles
            
        except ImportError as e:
            logger.exception(f"Import error: {e}")
            return None
        except Exception as e:
            logger.exception(f"Scan error: {e}")
            return None


def get_vehicle_classes_path() -> Path:
    """Get the path to vehicle_classes.json"""
    # For frozen executable, look in the same directory as the executable
    if getattr(sys, 'frozen', False):
        # Running as compiled executable - look in executable directory
        exe_dir = Path(sys.executable).parent
        classes_path = exe_dir / "vehicle_classes.json"
        if classes_path.exists():
            return classes_path
        # Fall back to current working directory
        return Path.cwd() / "vehicle_classes.json"
    else:
        # Development mode
        try:
            from core_common import get_data_file_path
            return get_data_file_path("vehicle_classes.json")
        except ImportError:
            return Path.cwd() / "vehicle_classes.json"


class PreRunCheckDialog:
    """
    Pre-run check dialog using tkinter.
    Returns True if checks passed and user wants to continue.
    """
    
    def __init__(self, config_file: str = "cfg.yml", accept_enter: bool = False):
        self.config_file = config_file
        self.accept_enter = accept_enter
        self.check_results: List[CheckResult] = []
        self.all_critical_passed = False
        self.vehicle_scan_worker = None
        self.vehicle_classes_path = get_vehicle_classes_path()
        self.result = False
        
        # Create root window but hide it (we use our own window)
        self.root = tk.Tk()
        self.root.withdraw()
        
        # Create dialog window
        self.dialog = tk.Toplevel(self.root)
        self.dialog.title("Dynamic AI - Pre-Run Checks")
        self.dialog.geometry("850x900")
        self.dialog.minsize(800, 700)
        self.dialog.configure(bg='#1e1e1e')
        self.dialog.protocol("WM_DELETE_WINDOW", self._on_close)
        
        # Center the window
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() // 2) - (850 // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (900 // 2)
        self.dialog.geometry(f"850x900+{x}+{y}")
        
        self._setup_ui()
        self._apply_styles()
        
        # Bind Enter key to continue button
        if self.accept_enter:
            self.dialog.bind('<Return>', lambda event: self._accept())
            self.dialog.bind('<KP_Enter>', lambda event: self._accept())
        
        # Make dialog modal
        self.dialog.grab_set()
        self.dialog.focus_set()
        
        # Run checks
        self.dialog.after(100, self.run_checks)
    
    def _setup_ui(self):
        """Setup the dialog UI"""
        # Main frame
        main_frame = tk.Frame(self.dialog, bg='#1e1e1e')
        main_frame.pack(fill=tk.BOTH, expand=True, padx=25, pady=25)
        
        # Progress bar (hidden initially)
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(main_frame, variable=self.progress_var, mode='determinate')
        self.progress_bar.pack(fill=tk.X, pady=(0, 15))
        self.progress_bar.pack_forget()
        
        # Progress label for text display
        self.progress_label = tk.Label(main_frame, text="", bg='#1e1e1e', fg='#4CAF50', font=('Arial', 10))
        self.progress_label.pack(fill=tk.X, pady=(0, 15))
        self.progress_label.pack_forget()
        
        # Status group
        status_frame = tk.LabelFrame(main_frame, text="Check Status", bg='#1e1e1e', fg='#FFA500',
                                      font=('Arial', 12, 'bold'))
        status_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 15))
        
        # Status text widget with scrollbar
        text_frame = tk.Frame(status_frame, bg='#1e1e1e')
        text_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.status_text = tk.Text(text_frame, bg='#2b2b2b', fg='#4CAF50', 
                                    font=('Courier', 10), wrap=tk.WORD,
                                    relief=tk.FLAT, borderwidth=0)
        self.status_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        scrollbar = tk.Scrollbar(text_frame, command=self.status_text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.status_text.config(yscrollcommand=scrollbar.set)
        
        # Result label
        self.result_label = tk.Label(main_frame, text="", bg='#1e1e1e', 
                                      font=('Arial', 14, 'bold'))
        self.result_label.pack(pady=(0, 15))
        
        # Button frame
        button_frame = tk.Frame(main_frame, bg='#1e1e1e')
        button_frame.pack(fill=tk.X, pady=(0, 15))
        
        # Center buttons
        button_container = tk.Frame(button_frame, bg='#1e1e1e')
        button_container.pack(anchor=tk.CENTER)
        
        ## self.fix_vehicles_btn = tk.Button(button_container, text="Open Vehicle Manager to Fix Missing Vehicles",
        ##                                    bg='#9C27B0', fg='white', font=('Arial', 10, 'bold'),
        ##                                    relief=tk.FLAT, padx=12, pady=8,
        ##                                    command=self.open_vehicle_manager)
        ## self.fix_vehicles_btn.pack(side=tk.LEFT, padx=5)
        ## self.fix_vehicles_btn.pack_forget()
        
        self.fix_plr_btn = tk.Button(button_container, text="Fix PLR File (Set Extra Stats=0)",
                                      bg='#2196F3', fg='white', font=('Arial', 10, 'bold'),
                                      relief=tk.FLAT, padx=12, pady=8,
                                      command=self.fix_plr_file)
        self.fix_plr_btn.pack(side=tk.LEFT, padx=5)
        self.fix_plr_btn.pack_forget()
        
        self.retry_btn = tk.Button(button_container, text="Retry Checks",
                                    bg='#555', fg='white', font=('Arial', 10, 'bold'),
                                    relief=tk.FLAT, padx=12, pady=8, state=tk.DISABLED,
                                    command=self.run_checks)
        self.retry_btn.pack(side=tk.LEFT, padx=5)
        
        self.continue_btn = tk.Button(button_container, text="Continue to Application",
                                       bg='#4CAF50', fg='white', font=('Arial', 10, 'bold'),
                                       relief=tk.FLAT, padx=12, pady=8,
                                       command=self._accept)
        self.continue_btn.pack(side=tk.LEFT, padx=5)
        self.continue_btn.config(state=tk.DISABLED)
        
        # Info group
        info_frame = tk.LabelFrame(main_frame, text="How to Use", bg='#1e1e1e', fg='#FFA500',
                                    font=('Arial', 12, 'bold'))
        info_frame.pack(fill=tk.X, pady=(0, 0))
        
        info_text = (
            "1. Click <Continue> and LEAVE THE APPLICATION RUNNING\n\n"
            "2. Launch GTR2 and start your race session\n\n"
            "TIPS:\n"
            " - Complete qualifying and the race normally\n"
            " - The application will detect your race results\n"
            " - AI ratios will be automatically calculated and applied\n"
            " - Each race makes the AI adapt to your pace."
        )
        
        info_label = tk.Label(info_frame, text=info_text, bg='#1e1e1e', fg='white',
                               font=('Arial', 11), justify=tk.LEFT, anchor=tk.W)
        info_label.pack(fill=tk.X, padx=15, pady=15)
        
        self.info_frame = info_frame
        self.info_frame.pack_forget()
    
    def _apply_styles(self):
        """Apply custom styling to ttk widgets"""
        style = ttk.Style()
        style.theme_use('clam')
        
        style.configure("TProgressbar", 
                        background='#4CAF50',
                        troughcolor='#3c3c3c',
                        borderwidth=0,
                        thickness=20)
        
        style.configure("TLabelFrame", 
                        background='#1e1e1e',
                        foreground='#FFA500',
                        borderwidth=2,
                        relief=tk.GROOVE)
        
        style.map("TLabelFrame.Label",
                  foreground=[('active', '#FFA500')])
    
    def _log(self, status: str, message: str, details: str = ""):
        """Log a message to the status display"""
        color_map = {
            "PASS": "#4CAF50",
            "FAIL": "#f44336",
            "WARN": "#FFCC00",
            "CHECK": "#C0C0C0",
            "INFO": "#888",
            "ERROR": "#f44336"
        }
        
        color = color_map.get(status, "#ffffff")
        
        self.status_text.insert(tk.END, "\n")
        
        if status == "CHECK":
            self.status_text.insert(tk.END, f"[CHECK] {message}...\n", f'color_{color}')
        elif status in ("PASS", "FAIL", "WARN", "INFO", "ERROR"):
            self.status_text.insert(tk.END, f"[{status}] ", f'color_{color}_bold')
            self.status_text.insert(tk.END, f"{message}", f'color_{color}')
            if details:
                self.status_text.insert(tk.END, f": {details}", 'color_gray')
            self.status_text.insert(tk.END, "\n")
        else:
            self.status_text.insert(tk.END, f"{message}\n", f'color_{color}')
        
        # Configure text tags
        self.status_text.tag_config(f'color_{color}', foreground=color)
        self.status_text.tag_config(f'color_{color}_bold', foreground=color, font=('Courier', 10, 'bold'))
        self.status_text.tag_config('color_gray', foreground='#aaaaaa')
        
        self.status_text.see(tk.END)
        self.dialog.update_idletasks()
    
    def _add_result(self, check_name: str, passed: bool, message: str = "", 
                    critical: bool = True, warning: bool = False):
        """Add a check result"""
        result = CheckResult(check_name, passed, message, critical, warning)
        self.check_results.append(result)
        
        if warning:
            self._log("WARN", check_name, message)
        elif passed:
            self._log("PASS", check_name, message)
        else:
            self._log("FAIL", check_name, message)
    
    def run_checks(self):
        """Run all pre-run checks"""
        # Clear previous results
        self.status_text.delete(1.0, tk.END)
        self.check_results.clear()
        self.continue_btn.config(state=tk.DISABLED)
        ## self.fix_vehicles_btn.pack_forget()
        self.fix_plr_btn.pack_forget()
        self.info_frame.pack_forget()
        self.result_label.config(text="")
        self.progress_bar.pack_forget()
        self.progress_label.pack_forget()
        
        self._log("CHECK", "Running pre-run checks", "")
        
        checks = [
            ("Configuration File", self._check_config_file, True, False),
            ("Vehicle Classes File", self._check_vehicle_classes_file, True, False),
            ("Vehicle Classes Data", self._check_vehicle_classes_data, True, False),
            ("GTR2 Base Path", self._check_base_path, True, False),
            ("GTR2 Executable", self._check_gtr2_executable, True, False),
            ("GTR2 PLR File", self._check_plr_file, True, False),
            ("Vehicle Definitions", self._check_vehicle_definitions, False, True),
        ]
        
        all_critical_passed = True
        vehicle_warning = False
        
        for check_name, check_func, critical, is_warning in checks:
            try:
                passed, message = check_func()
                self._add_result(check_name, passed, message, critical, is_warning and not passed)
                
                if critical and not passed:
                    all_critical_passed = False
                if is_warning and not passed:
                    vehicle_warning = True
                    
            except Exception as e:
                self._add_result(check_name, False, str(e), critical, False)
                if critical:
                    all_critical_passed = False
            
            self.dialog.update_idletasks()
        
        self.all_critical_passed = all_critical_passed
        
        vehicle_check_failed = any(r.name == "Vehicle Definitions" and not r.passed for r in self.check_results)
        plr_check_failed = any(r.name == "GTR2 PLR File" and not r.passed for r in self.check_results)
        
        ## if vehicle_check_failed:
        ##     self.fix_vehicles_btn.pack(side=tk.LEFT, padx=5)
        if plr_check_failed:
            self.fix_plr_btn.pack(side=tk.LEFT, padx=5)
        
        if all_critical_passed:
            if vehicle_warning:
                self.result_label.config(text="Requirements are OK (with vehicle warnings)", fg="#FFCC00")
                self._log("WARN", "Summary", "All checks passed, but some vehicles are not defined")
                self.retry_btn.config(bg="#FF9800", state=tk.NORMAL)
            else:
                self.result_label.config(text="System ready, Click <Continue> to continue", fg="#4CAF50")
                self._log("INFO", "Summary", "All checks passed. Click <Continue> to open the application.")
                self.retry_btn.config(bg="#555", state=tk.DISABLED)
            
            self.continue_btn.config(state=tk.NORMAL)
            self.info_frame.pack(fill=tk.X, pady=(15, 0))
            self.continue_btn.focus_set()
        else:
            self.result_label.config(text="SOME REQUIREMENTS NOT READY - Please fix issues and retry", fg="#f44336")
            self._log("FAIL", "Summary", "Some requirements are not ready. Please fix the issues and retry.")
            self.retry_btn.config(bg="#FF9800", state=tk.NORMAL)
            
            guidance = self._get_guidance()
            if guidance:
                self._log("INFO", "Guidance", guidance)
    
    def _get_guidance(self) -> str:
        """Get guidance message for failed checks"""
        failed_critical = [r.name for r in self.check_results if r.critical and not r.passed]
        if not failed_critical:
            return ""
        
        guidance = []
        if "Configuration File" in failed_critical:
            guidance.append("cfg.yml exists and has valid YAML syntax")
        if "Vehicle Classes File" in failed_critical:
            guidance.append("vehicle_classes.json exists and is not corrupted")
        if "Vehicle Classes Data" in failed_critical:
            guidance.append("vehicle_classes.json has the correct structure with 'vehicles' arrays")
        if "GTR2 Base Path" in failed_critical:
            guidance.append("GTR2 base path is correctly set in cfg.yml")
        if "GTR2 Executable" in failed_critical:
            guidance.append("GTR2.exe exists in the base path")
        if "GTR2 PLR File" in failed_critical:
            guidance.append("PLR file has Extra Stats=0 (not 1)")
        
        return "Make sure: " + ", ".join(guidance)
    
    def _check_config_file(self) -> Tuple[bool, str]:
        """Check that cfg.yml exists and is valid"""
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
            
            return True, "Valid config file"
        except Exception as e:
            return False, f"Error reading config: {str(e)}"
    
    def _check_vehicle_classes_file(self) -> Tuple[bool, str]:
        """Check that vehicle_classes.json exists"""
        if not self.vehicle_classes_path.exists():
            try:
                self.vehicle_classes_path.parent.mkdir(parents=True, exist_ok=True)
                default_classes = {
                    "GT Cars": {"vehicles": []},
                    "Formula Cars": {"vehicles": []},
                    "Prototype Cars": {"vehicles": []}
                }
                with open(self.vehicle_classes_path, 'w', encoding='utf-8') as f:
                    json.dump(default_classes, f, indent=2)
                return True, f"Created default file"
            except Exception as e:
                return False, f"File not found and could not create: {str(e)}"
        
        try:
            with open(self.vehicle_classes_path, 'r', encoding='utf-8') as f:
                json.load(f)
            return True, "Found valid file"
        except json.JSONDecodeError as e:
            return False, f"Invalid JSON: {str(e)}"
        except Exception as e:
            return False, f"Error reading file: {str(e)}"
    
    def _check_vehicle_classes_data(self) -> Tuple[bool, str]:
        """Check that vehicle_classes.json has valid structure"""
        if not self.vehicle_classes_path.exists():
            return False, "vehicle_classes.json not found"
        
        try:
            with open(self.vehicle_classes_path, 'r', encoding='utf-8') as f:
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
                
                vehicles = class_data.get('vehicles', [])
                if not isinstance(vehicles, list):
                    return False, f"'vehicles' in '{class_name}' must be a list"
                
                class_count += 1
                vehicle_count += len(vehicles)
            
            return True, f"{class_count} classes, {vehicle_count} vehicles"
            
        except Exception as e:
            return False, f"Error validating: {str(e)}"
    
    def _check_base_path(self) -> Tuple[bool, str]:
        """Check that GTR2 base path is configured and valid"""
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
            return False, f"Missing directories: {', '.join(missing)}"
        
        return True, "Valid GTR2 path"
    
    def _check_gtr2_executable(self) -> Tuple[bool, str]:
        """Check that GTR2.exe exists"""
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
        
        for exe_candidate in base_path_obj.glob("*.exe"):
            if exe_candidate.name.lower() == "gtr2.exe":
                return True, f"Found at: {exe_candidate.name}"
        
        return False, "GTR2.exe not found in the GTR2 installation path"
    
    def _find_plr_file(self) -> Tuple[Optional[Path], str]:
        """Find the active PLR file in the UserData directory"""
        base_path = get_base_path(self.config_file)
        
        if not base_path:
            return None, "Base path not configured"
        
        userdata_dir = base_path / "UserData"
        if not userdata_dir.exists():
            return None, "UserData directory not found"
        
        for ext in ["*.PLR", "*.plr"]:
            plr_files = list(userdata_dir.glob(ext))
            if plr_files:
                return plr_files[0], f"Found: {plr_files[0].name}"
        
        for item in userdata_dir.iterdir():
            if item.is_dir():
                for ext in ["*.PLR", "*.plr"]:
                    plr_files = list(item.glob(ext))
                    if plr_files:
                        return plr_files[0], f"Found: {plr_files[0].name} (in {item.name})"
        
        return None, "No .PLR file found in UserData"
    
    def _check_plr_file(self) -> Tuple[bool, str]:
        """Check that the PLR file has Extra Stats set to 0"""
        plr_path, status_msg = self._find_plr_file()
        
        if not plr_path:
            return False, status_msg
        
        if not plr_path.exists():
            return False, "PLR file not found"
        
        try:
            content = plr_path.read_text(encoding='utf-8', errors='ignore')
            
            pattern = r'Extra\s+Stats\s*=\s*"([^"]*)"'
            match = re.search(pattern, content, re.IGNORECASE)
            
            if not match:
                return False, "Extra Stats setting not found"
            
            value = match.group(1).strip()
            
            try:
                float_val = float(value)
                if float_val == 0.0:
                    return True, "Extra Stats is properly set to 0"
                else:
                    return False, f"Extra Stats is set to {value} (must be 0)"
            except ValueError:
                if value == "0":
                    return True, "Extra Stats is properly set to 0"
                else:
                    return False, f"Extra Stats is set to '{value}' (must be 0)"
                
        except Exception as e:
            return False, f"Error reading PLR file: {str(e)}"
    
    def fix_plr_file(self):
        """Fix the PLR file by setting Extra Stats to 0"""
        plr_path, status_msg = self._find_plr_file()
        
        if not plr_path or not plr_path.exists():
            messagebox.showwarning("PLR File Not Found", 
                f"Cannot fix PLR file.\n{status_msg}\n\n"
                "Please ensure you have run GTR2 at least once to create a player profile.")
            return
        
        try:
            backup_path = plr_path.with_suffix(plr_path.suffix + ".backup")
            backup_content = plr_path.read_text(encoding='utf-8', errors='ignore')
            backup_path.write_text(backup_content, encoding='utf-8')
            
            content = backup_content
            
            pattern = r'(Extra\s+Stats\s*=\s*)"[^"]*"'
            replacement = r'\1"0"'
            
            new_content = re.sub(pattern, replacement, content, flags=re.IGNORECASE)
            
            pattern_no_quotes = r'(Extra\s+Stats\s*=\s*)([0-9.eE+-]+)'
            new_content = re.sub(pattern_no_quotes, r'\g<1>"0"', new_content, flags=re.IGNORECASE)
            
            if new_content == content:
                messagebox.showwarning("Fix Failed", "Could not find Extra Stats setting to modify")
                return
            
            plr_path.write_text(new_content, encoding='utf-8')
            
            messagebox.showinfo("PLR File Fixed", 
                "PLR file has been fixed.\n"
                f"Extra Stats has been set to 0.\n"
                f"A backup was saved to: {backup_path.name}")
            
            reply = messagebox.askyesno("Retry Checks", 
                "PLR file has been fixed.\n\nClick Yes to retry the checks, or No to continue without retrying.")
            
            if reply:
                self.run_checks()
                
        except Exception as e:
            messagebox.showerror("Error Fixing PLR File", f"Failed to fix PLR file:\n{str(e)}")
    
##     def open_vehicle_manager(self):
##         """Open the vehicle manager dialog - direct dialog launch"""
##         config = get_config_with_defaults(self.config_file)
##         base_path = config.get('base_path', '')
##         gtr2_path = Path(base_path) if base_path and Path(base_path).exists() else None
##         
##         # Hide the tkinter dialog temporarily
##         self.dialog.withdraw()
##         
##         try:
##             from PyQt5.QtWidgets import QApplication, QDialog
##             from gui_vehicle_manager import VehicleManagerDialog
##             
##             # Check if a QApplication instance exists, create one if not
##             qt_app = QApplication.instance()
##             if qt_app is None:
##                 qt_app = QApplication(sys.argv)
##             
##             # Create and show the dialog
##             dialog = VehicleManagerDialog(None, gtr2_path)
##             dialog.exec_()
##             
##         except ImportError as e:
##             messagebox.showerror("Import Error", f"Failed to import VehicleManagerDialog:\n{str(e)}\n\nPlease ensure the application is properly installed.")
##             self.dialog.deiconify()
##             return
##         except Exception as e:
##             messagebox.showerror("Error", f"Failed to open Vehicle Manager:\n{str(e)}")
##             self.dialog.deiconify()
##             return
##         
##         # Show the tkinter dialog again
##         self.dialog.deiconify()
##         self.dialog.lift()
##         self.dialog.focus_set()
##         
##         self.run_checks()
    
    def _check_vehicle_definitions(self) -> Tuple[bool, str]:
        """Check that all vehicles from GTR2 are defined in vehicle_classes.json"""
        config = get_config_with_defaults(self.config_file)
        base_path = config.get('base_path', '')
        
        if not base_path:
            return False, "No base path configured - cannot scan vehicles"
        
        gtr2_path = Path(base_path)
        
        if not self.vehicle_classes_path.exists():
            return False, "vehicle_classes.json not found"
        
        teams_dir = gtr2_path / "GameData" / "Teams"
        if not teams_dir.exists():
            return False, f"Teams directory not found: {teams_dir}"
        
        # Count car files to see if there are any
        car_files = list(teams_dir.rglob("*.car")) + list(teams_dir.rglob("*.CAR"))
        if not car_files:
            return False, f"No .car files found in {teams_dir}"
        
        self._log("INFO", "Vehicle Scan", f"Found {len(car_files)} car files to scan")
        
        # Show progress bar
        self.progress_var.set(0)
        self.progress_bar.pack(fill=tk.X, pady=(0, 5))
        self.progress_label.pack(fill=tk.X, pady=(0, 15))
        self.progress_bar.config(mode='determinate')
        self.dialog.update_idletasks()
        
        self.scan_complete = False
        self.scan_result = None
        self.scan_error = None
        
        def on_progress(current, total, message):
            if self.progress_bar.winfo_exists():
                if total > 0:
                    percent = (current / total) * 100
                    self.progress_var.set(percent)
                self.progress_label.config(text=f"{message} ({current}/{total})")
                self.dialog.update_idletasks()
        
        def on_finished(all_vehicles, defined_vehicles, missing_vehicles, error=None):
            self.scan_error = error
            if error:
                self.scan_result = None
            elif all_vehicles is None:
                self.scan_result = None
            else:
                self.scan_result = (all_vehicles, defined_vehicles, missing_vehicles)
            self.scan_complete = True
        
        self.vehicle_scan_worker = VehicleScanWorker(gtr2_path, self.vehicle_classes_path, on_finished, on_progress)
        self.vehicle_scan_worker.start()
        
        # Wait for completion with timeout
        timeout = 120  # 120 seconds timeout for large installations
        start_time = time.time()
        while not self.scan_complete and (time.time() - start_time) < timeout:
            self.dialog.update()
            self.dialog.after(100)
        
        # Hide progress bar
        self.progress_bar.pack_forget()
        self.progress_label.pack_forget()
        
        if not self.scan_complete:
            if self.vehicle_scan_worker:
                self.vehicle_scan_worker.stop()
            return False, "Vehicle scan timed out after 120 seconds. Your GTR2 installation may have many car files."
        
        if self.scan_error:
            return False, f"Scan error: {self.scan_error}"
        
        if self.scan_result:
            all_vehicles, defined_vehicles, missing_vehicles = self.scan_result
            
            if not all_vehicles:
                return False, "No vehicles found in GTR2 installation. Check that .car files exist in GameData/Teams/"
            
            missing_count = len(missing_vehicles)
            
            if missing_count > 0:
                missing_list = list(missing_vehicles)[:10]
                missing_display = ", ".join(missing_list)
                if missing_count > 10:
                    missing_display += f" and {missing_count - 10} more..."
                
                return False, f"{missing_count} vehicle(s) missing from classes: {missing_display}"
            
            return True, f"All {len(all_vehicles)} vehicles are defined"
        else:
            return False, "Failed to scan vehicles from GTR2 installation"
    
    def _accept(self):
        """Handle continue button click"""
        self.result = True
        self._on_close()
    
    def _on_close(self):
        """Handle window close"""
        if self.vehicle_scan_worker and self.vehicle_scan_worker.is_alive():
            self.vehicle_scan_worker.stop()
            self.vehicle_scan_worker.join(timeout=1.0)
        self.dialog.destroy()
        self.root.quit()
    
    def show(self) -> bool:
        """Show the dialog and return True if user wants to continue"""
        self.dialog.deiconify()
        self.root.mainloop()
        return self.result


def run_pre_run_check(config_file: str = "cfg.yml", accept_enter: bool = False) -> bool:
    """
    Run the pre-run check dialog.
    
    Args:
        config_file: Path to the configuration file
        accept_enter: If True, the Enter key will trigger the Continue button
    
    Returns:
        True if checks passed and user wants to continue
    """
    dialog = PreRunCheckDialog(config_file, accept_enter)
    return dialog.show()
