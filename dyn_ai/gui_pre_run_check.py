#!/usr/bin/env python3
"""
Pre-run check dialog for Dynamic AI
Uses tkinter for minimal dependencies and faster startup
"""

import sys
import json
import re
import threading
import subprocess
import time
import logging
import os
import traceback
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


def get_app_directory() -> Path:
    """
    Get the directory where the application is running.
    Works correctly for both Python scripts and compiled EXE files.
    """
    if getattr(sys, 'frozen', False):
        # Running as compiled executable
        return Path(sys.executable).parent
    else:
        # Running as Python script
        return Path(__file__).parent


def get_cache_file_path() -> Path:
    """Get the path for the vehicle scan cache file"""
    app_dir = get_app_directory()
    return app_dir / ".vehicle_scan_cache.json"


@dataclass
class CheckResult:
    """Result of a single check"""
    name: str
    passed: bool
    message: str = ""
    critical: bool = True
    warning: bool = False


def get_vehicle_classes_path() -> Path:
    """Get the path to vehicle_classes.json"""
    app_dir = get_app_directory()
    classes_path = app_dir / "vehicle_classes.json"
    
    if classes_path.exists():
        return classes_path
    
    # If not in app directory, try current directory
    cwd_path = Path.cwd() / "vehicle_classes.json"
    if cwd_path.exists():
        return cwd_path
    
    # Return app directory path as default
    return classes_path


def is_running_as_exe() -> bool:
    """Return True if the program is running as a compiled executable"""
    return getattr(sys, 'frozen', False)


def get_setup_launcher_path() -> Path:
    """Get the path to the setup program (dyn_ai_setup)"""
    app_dir = get_app_directory()
    
    if is_running_as_exe():
        # Running as exe - look for dyn_ai_setup.exe in same directory
        setup_path = app_dir / "dyn_ai_setup.exe"
        if setup_path.exists():
            return setup_path
        setup_path_upper = app_dir / "DYN_AI_SETUP.EXE"
        if setup_path_upper.exists():
            return setup_path_upper
    else:
        # Running as Python script
        setup_path = Path(__file__).parent / "dyn_ai_setup.py"
        if setup_path.exists():
            return setup_path
    
    return app_dir / "dyn_ai_setup.exe"


def launch_setup_manager():
    """Launch the setup manager (dyn_ai_setup)"""
    setup_path = get_setup_launcher_path()
    
    if not setup_path.exists():
        messagebox.showerror("Setup Not Found", 
            f"Setup manager not found at:\n{setup_path}\n\n"
            f"Please ensure dyn_ai_setup is in the same directory.")
        return False
    
    try:
        if is_running_as_exe():
            subprocess.Popen([str(setup_path)], shell=False)
        else:
            python_exe = sys.executable
            subprocess.Popen([python_exe, str(setup_path)], shell=False)
        return True
    except Exception as e:
        messagebox.showerror("Launch Error", f"Failed to launch setup manager:\n{str(e)}")
        return False


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
        self.vehicle_classes_path = get_vehicle_classes_path()
        self.result = False
        self.auto_continue_timer = None
        self.auto_continue_seconds = 3
        self.auto_continue_remaining = 3
        self.auto_continue_active = False
        
        # Create root window but hide it
        self.root = tk.Tk()
        self.root.withdraw()
        
        # Create dialog window
        self.dialog = tk.Toplevel(self.root)
        self.dialog.title("Dynamic AI - Pre-Run Checks")
        self.dialog.geometry("850x950")
        self.dialog.minsize(800, 750)
        self.dialog.configure(bg='#1e1e1e')
        self.dialog.protocol("WM_DELETE_WINDOW", self._on_close)
        
        # Center the window
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() // 2) - (850 // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (950 // 2)
        self.dialog.geometry(f"850x950+{x}+{y}")
        
        self._setup_ui()
        self._apply_styles()
        
        # Bind Enter key to continue button
        if self.accept_enter:
            self.dialog.bind('<Return>', lambda event: self._accept())
            self.dialog.bind('<KP_Enter>', lambda event: self._accept())
        
        # Bind Escape key to cancel auto-continue
        self.dialog.bind('<Escape>', lambda event: self._cancel_auto_continue())
        
        # Make dialog modal
        self.dialog.grab_set()
        self.dialog.focus_set()
        
        # Run checks
        self.dialog.after(100, self.run_checks)
    
    def _setup_ui(self):
        """Setup the dialog UI"""
        main_frame = tk.Frame(self.dialog, bg='#1e1e1e')
        main_frame.pack(fill=tk.BOTH, expand=True, padx=25, pady=25)
        
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
        
        # Auto-continue timer label
        self.timer_label = tk.Label(main_frame, text="", bg='#1e1e1e', 
                                     font=('Arial', 11), fg='#888')
        self.timer_label.pack(pady=(0, 10))
        
        # Button frame
        button_frame = tk.Frame(main_frame, bg='#1e1e1e')
        button_frame.pack(fill=tk.X, pady=(0, 15))
        
        # Center buttons
        button_container = tk.Frame(button_frame, bg='#1e1e1e')
        button_container.pack(anchor=tk.CENTER)
        
        self.fix_plr_btn = tk.Button(button_container, text="Fix PLR File (Set Extra Stats=0)",
                                      bg='#2196F3', fg='white', font=('Arial', 10, 'bold'),
                                      relief=tk.FLAT, padx=12, pady=8,
                                      command=self.fix_plr_file)
        self.fix_plr_btn.pack(side=tk.LEFT, padx=5)
        self.fix_plr_btn.pack_forget()
        
        self.open_setup_btn = tk.Button(button_container, text="Setup",
                                         bg='#9C27B0', fg='white', font=('Arial', 10, 'bold'),
                                         relief=tk.FLAT, padx=12, pady=8,
                                         command=self.open_setup_manager)
        self.open_setup_btn.pack(side=tk.LEFT, padx=5)
        self.open_setup_btn.pack_forget()
        
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
            "1. Click Continue and LEAVE THE APPLICATION RUNNING\n\n"
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
            "ERROR": "#f44336",
            "DETAIL": "#FFA500"
        }
        
        color = color_map.get(status, "#ffffff")
        
        self.status_text.insert(tk.END, "\n")
        
        if status == "CHECK":
            self.status_text.insert(tk.END, f"[CHECK] {message}...\n", f'color_{color}')
        elif status == "DETAIL":
            self.status_text.insert(tk.END, f"  -> {message}\n", f'color_{color}')
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
    
    def _cancel_auto_continue(self):
        """Cancel the auto-continue timer when user presses Escape"""
        if self.auto_continue_active:
            self._stop_auto_continue_timer()
            self.timer_label.config(text="Auto-start cancelled. Click Continue to proceed.")
            self.continue_btn.config(state=tk.NORMAL)
            self.continue_btn.focus_set()
            self._log("INFO", "Auto-start cancelled by user", "Press Continue to proceed manually")
    
    def _start_auto_continue_timer(self):
        """Start the auto-continue timer if all checks passed"""
        if self.auto_continue_timer is not None:
            self.auto_continue_timer.cancel()
        
        self.auto_continue_active = True
        self.auto_continue_remaining = self.auto_continue_seconds
        self._update_timer_display()
        
        def timer_tick():
            if not self.auto_continue_active:
                return
            self.auto_continue_remaining -= 1
            if self.auto_continue_remaining <= 0:
                self.auto_continue_active = False
                self.timer_label.config(text="")
                self._accept()
            else:
                self._update_timer_display()
                self.auto_continue_timer = threading.Timer(1.0, timer_tick)
                self.auto_continue_timer.daemon = True
                self.auto_continue_timer.start()
        
        self.auto_continue_timer = threading.Timer(1.0, timer_tick)
        self.auto_continue_timer.daemon = True
        self.auto_continue_timer.start()
    
    def _update_timer_display(self):
        """Update the timer label display"""
        if self.auto_continue_active:
            self.timer_label.config(text=f"Starting automatically in {self.auto_continue_remaining} second(s). Press Enter to start now, or Escape to cancel auto-start.")
        else:
            self.timer_label.config(text="")
    
    def _stop_auto_continue_timer(self):
        """Stop the auto-continue timer"""
        self.auto_continue_active = False
        if self.auto_continue_timer is not None:
            self.auto_continue_timer.cancel()
            self.auto_continue_timer = None
        self.timer_label.config(text="")
    
    def run_checks(self):
        """Run all pre-run checks"""
        # Clear previous results
        self.status_text.delete(1.0, tk.END)
        self.check_results.clear()
        self.continue_btn.config(state=tk.DISABLED)
        self.fix_plr_btn.pack_forget()
        self.open_setup_btn.pack_forget()
        self.info_frame.pack_forget()
        self.result_label.config(text="")
        self._stop_auto_continue_timer()
        
        self._log("CHECK", "Running pre-run checks", "")
        
        checks = [
            ("Vehicle Classes File", self._check_vehicle_classes_file, True, False),
            ("Vehicle Classes Data", self._check_vehicle_classes_data, True, False),
            ("GTR2 Base Path", self._check_base_path, True, False),
            ("GTR2 Executable", self._check_gtr2_executable, True, False),
            ("GTR2 PLR File", self._check_plr_file, True, False),
            ("Vehicle Cache", self._check_vehicle_cache, False, True),
        ]
        
        all_critical_passed = True
        has_any_warning = False
        
        for check_name, check_func, critical, is_warning in checks:
            try:
                passed, message = check_func()
                self._add_result(check_name, passed, message, critical, is_warning and not passed)
                
                if critical and not passed:
                    all_critical_passed = False
                if is_warning and not passed:
                    has_any_warning = True
                    
            except Exception as e:
                self._add_result(check_name, False, str(e), critical, False)
                if critical:
                    all_critical_passed = False
                has_any_warning = True
            
            self.dialog.update_idletasks()
        
        self.all_critical_passed = all_critical_passed
        
        plr_check_failed = any(r.name == "GTR2 PLR File" and not r.passed for r in self.check_results)
        cache_check_failed = any(r.name == "Vehicle Cache" and not r.passed for r in self.check_results)
        
        # Show Open Setup Manager button for cache warning
        if cache_check_failed:
            self.open_setup_btn.pack(side=tk.LEFT, padx=5)
        
        if plr_check_failed:
            self.fix_plr_btn.pack(side=tk.LEFT, padx=5)
        
        if all_critical_passed:
            if has_any_warning:
                self.result_label.config(text="Requirements are OK (with warnings)", fg="#FFCC00")
                self._log("WARN", "Summary", "All critical checks passed, but some warnings were found")
                self.retry_btn.config(bg="#FF9800", state=tk.NORMAL)
                self.continue_btn.config(state=tk.NORMAL)
                self.info_frame.pack(fill=tk.X, pady=(15, 0))
                self.continue_btn.focus_set()
            else:
                self.result_label.config(text="System ready - Starting automatically in 3 seconds", fg="#4CAF50")
                self._log("INFO", "Summary", "All checks passed. Starting application...")
                self.retry_btn.config(bg="#555", state=tk.DISABLED)
                self.continue_btn.config(state=tk.NORMAL)
                self.info_frame.pack(fill=tk.X, pady=(15, 0))
                self._start_auto_continue_timer()
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
                return True, f"Created default file at {self.vehicle_classes_path}"
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
            return False, "No base path in cfg.yml. Run SETUP"
        
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
            return False, f"Missing directories: {', '.join(missing)}. Check Path in SETUP"
        
        return True, "Valid GTR2 path"
    
    def _check_gtr2_executable(self) -> Tuple[bool, str]:
        """Check that GTR2.exe exists"""
        config = get_config_with_defaults(self.config_file)
        base_path = config.get('base_path', '')
        
        if not base_path:
            return False, "No base path in cfg.yml. Check Path in SETUP"
        
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
        
        return False, "GTR2.exe not found in the GTR2 Base Path. Check Path in SETUP"
    
    def _find_plr_file(self) -> Tuple[Optional[Path], str]:
        """Find the active PLR file in the UserData directory"""
        base_path = get_base_path(self.config_file)
        
        if not base_path:
            return None, "Base path not configured"
        
        userdata_dir = base_path / "UserData"
        if not userdata_dir.exists():
            return None, "UserData directory not found. Check with SETUP"
        
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
        
        return None, "No .PLR file found in UserData. Check with SETUP"
    
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
    
    def open_setup_manager(self):
        """Open the setup manager dialog"""
        self.dialog.withdraw()
        
        success = launch_setup_manager()
        
        # Show the dialog again after setup closes
        self.dialog.deiconify()
        self.dialog.lift()
        self.dialog.focus_set()
    
    def _check_vehicle_cache(self) -> Tuple[bool, str]:
        """Check if the vehicle cache file exists (no scanning!)"""
        cache_file = get_cache_file_path()
        
        if cache_file.exists():
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)
                
                # Verify it has the required data
                if 'all_vehicles' in cache_data and 'missing_vehicles' in cache_data:
                    missing_count = len(cache_data.get('missing_vehicles', []))
                    if missing_count == 0:
                        return True, f"Cache valid: {len(cache_data.get('all_vehicles', []))} vehicles defined"
                    else:
                        return False, f"Cache shows {missing_count} missing vehicles. Run SETUP > Vehicle Classes to assign them."
                else:
                    return False, "Cache file is incomplete. Run SETUP > Vehicle Classes > Import Cars to rebuild."
            except Exception as e:
                return False, f"Cache file corrupted: {str(e)}. Run SETUP > Vehicle Classes > Import Cars to rebuild."
        else:
            return False, "No vehicle cache found. Run SETUP > Vehicle Classes > Import Cars to scan and assign vehicles."
    
    def _accept(self):
        """Handle continue button click"""
        self._stop_auto_continue_timer()
        self.result = True
        self._on_close()
    
    def _on_close(self):
        """Handle window close"""
        self._stop_auto_continue_timer()
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
