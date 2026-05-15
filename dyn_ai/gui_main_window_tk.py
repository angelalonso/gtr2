#!/usr/bin/env python3
"""
Main window for Live AI Tuner - Tkinter version
Lightweight main screen that uses tkinter and calls PyQt5 for advanced dialogs
"""

import sys
import threading
import logging
import sqlite3
import subprocess
import re
from pathlib import Path
from typing import List, Tuple, Optional, Dict, Any
from datetime import datetime

import tkinter as tk
from tkinter import ttk, messagebox

from core_database import CurveDatabase
from core_formula import DEFAULT_A_VALUE
from core_config import (
    get_config_with_defaults, get_results_file_path, get_poll_interval,
    get_db_path, create_default_config_if_missing, get_base_path,
    get_ratio_limits, update_base_path, get_nr_last_user_laptimes
)
from core_data_extraction import RaceData
from core_autopilot import AutopilotManager, get_vehicle_class, load_vehicle_classes
from core_user_laptimes import UserLapTimesManager

from core_common import SimpleLogHandler
from gui_base_path_dialog_tk import BasePathSelectionDialog
from gui_file_monitor import FileMonitorDaemon, SimplifiedLogger

# Configure logging to show debug messages
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class RatioPanel(tk.Frame):
    """Panel for displaying Qualifying or Race ratio information"""
    
    def __init__(self, parent, main_window, title: str, min_ratio: float, max_ratio: float):
        super().__init__(parent)
        self.title = title
        self.current_ratio = None
        self.last_read_ratio = None
        self.previous_ratio = None
        self.min_ratio = min_ratio
        self.max_ratio = max_ratio
        self.main_window = main_window
        self.setup_ui()
        logger.debug(f"RatioPanel created for {title} with main_window reference")
        
    def setup_ui(self):
        self.configure(bg='#2b2b2b')
        
        main_frame = tk.Frame(self, bg='#2b2b2b')
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Title and buttons row
        title_frame = tk.Frame(main_frame, bg='#2b2b2b')
        title_frame.pack(fill=tk.X, pady=(0, 15))
        
        title_label = tk.Label(title_frame, text=self.title, bg='#2b2b2b', fg='#aaa',
                                font=('Arial', 16, 'bold'))
        title_label.pack(side=tk.LEFT)
        
        button_frame = tk.Frame(title_frame, bg='#2b2b2b')
        button_frame.pack(side=tk.RIGHT)
        
        self.revert_btn = tk.Button(button_frame, text="Revert", bg='#FF9800', fg='black',
                                     font=('Arial', 10, 'bold'), relief=tk.FLAT, padx=12, pady=4,
                                     state=tk.DISABLED, command=self.on_revert)
        self.revert_btn.pack(side=tk.LEFT, padx=5)
        
        self.edit_btn = tk.Button(button_frame, text="Edit", bg='#555', fg='black',
                                   font=('Arial', 10, 'bold'), relief=tk.FLAT, padx=12, pady=4,
                                   command=self.on_edit, state=tk.DISABLED)
        self.edit_btn.pack(side=tk.LEFT, padx=5)
        
        # Ratio display
        ratio_label = tk.Label(main_frame, text="Current Ratio:", bg='#2b2b2b', fg='#888',
                                font=('Arial', 11))
        ratio_label.pack()
        
        self.ratio_value = tk.Label(main_frame, text="-", bg='#2b2b2b', fg='#FFA500',
                                     font=('Courier', 38, 'bold'))
        self.ratio_value.pack(pady=5)
        
        self.last_read_value = tk.Label(main_frame, text="last ratio read: --", bg='#2b2b2b',
                                         fg='#666', font=('Courier', 10))
        self.last_read_value.pack()
        
        # AI range
        ai_label = tk.Label(main_frame, text="Expected Best Laptimes:", bg='#2b2b2b', fg='#888',
                             font=('Arial', 11))
        ai_label.pack(pady=(20, 5))
        
        self.ai_range = tk.Label(main_frame, text="AI: -- - --", bg='#2b2b2b', fg='#FFA500',
                                  font=('Courier', 14))
        self.ai_range.pack()
        
        # User time
        self.user_time = tk.Label(main_frame, text="User: --", bg='#2b2b2b', fg='#4CAF50',
                                   font=('Courier', 14, 'bold'))
        self.user_time.pack(pady=10)
        
        # Formula
        self.formula = tk.Label(main_frame, text="", bg='#2b2b2b', fg='#888',
                                 font=('Courier', 10))
        self.formula.pack(pady=10)
        
        # Accuracy indicator frame
        self.accuracy_frame = tk.Frame(main_frame, bg='#3c3c3c', relief=tk.FLAT, bd=0)
        self.accuracy_frame.pack(fill=tk.X, pady=10)
        self.accuracy_frame.pack_forget()
        
        self.accuracy_label = tk.Label(self.accuracy_frame, text="", bg='#3c3c3c', fg='#4CAF50',
                                        font=('Arial', 10))
        self.accuracy_label.pack(pady=5)
        
        self.progress_bar = ttk.Progressbar(self.accuracy_frame, length=150, mode='determinate')
        self.progress_bar.pack(pady=5)
    
    def get_current_ratio_value(self) -> Optional[float]:
        """Get the current ratio value from the panel or main window"""
        if self.current_ratio is not None:
            return self.current_ratio
        if self.last_read_ratio is not None:
            return self.last_read_ratio
        if self.main_window:
            if self.title == "Quali-Ratio":
                return self.main_window.last_qual_ratio
            else:
                return self.main_window.last_race_ratio
        return None
    
    def update_ratio(self, ratio: float):
        logger.debug(f"[RatioPanel.{self.title}] update_ratio called with ratio={ratio}")
        
        if ratio is not None:
            # Store previous ratio before updating
            if self.current_ratio is not None and ratio != self.current_ratio:
                self.previous_ratio = self.current_ratio
                self.revert_btn.config(state=tk.NORMAL)
                logger.debug(f"[RatioPanel.{self.title}] Stored previous_ratio={self.previous_ratio}")
            self.current_ratio = ratio
            self.ratio_value.config(text=f"{ratio:.6f}")
        else:
            self.current_ratio = None
            self.ratio_value.config(text="-")
    
    def update_last_read_ratio(self, ratio: float):
        self.last_read_ratio = ratio
        if ratio is not None:
            self.last_read_value.config(text=f"last ratio read: {ratio:.6f}", fg='#FFA500')
        else:
            self.last_read_value.config(text="last ratio read: --", fg='#666')
    
    def update_ai_range(self, best: float, worst: float):
        if best is not None and worst is not None:
            minutes_best = int(best) // 60
            secs_best = best % 60
            minutes_worst = int(worst) // 60
            secs_worst = worst % 60
            self.ai_range.config(text=f"AI: {minutes_best}:{secs_best:06.3f} - {minutes_worst}:{secs_worst:06.3f}")
        else:
            self.ai_range.config(text="AI: -- - --")
    
    def update_user_time(self, time_sec: float):
        if time_sec is not None and time_sec > 0:
            minutes = int(time_sec) // 60
            seconds = time_sec % 60
            self.user_time.config(text=f"User: {minutes}:{seconds:06.3f}")
        else:
            self.user_time.config(text="User: --")
    
    def update_formula(self, a: float, b: float):
        self.formula.config(text=f"T = {a:.2f} / R + {b:.2f}")
    
    def update_accuracy(self, confidence: float, data_points_used: int,
                        avg_error: float = None, max_error: float = None,
                        outliers: int = 0):
        if data_points_used == 0:
            self.accuracy_frame.pack_forget()
            return
        
        self.accuracy_frame.pack(fill=tk.X, pady=10)
        
        if confidence >= 0.8:
            color = "#4CAF50"
        elif confidence >= 0.6:
            color = "#FFC107"
        elif confidence >= 0.4:
            color = "#FF9800"
        else:
            color = "#f44336"
        
        percent = int(confidence * 100)
        self.progress_bar['value'] = percent
        self.accuracy_label.config(text=f"Accuracy: {percent}% ({data_points_used} points)", fg=color)
        
        if avg_error is not None:
            self.accuracy_label.config(text=f"Accuracy: {percent}% ({data_points_used} points, err:{avg_error:.2f}s)", fg=color)
    
    def set_edit_enabled(self, enabled: bool):
        state = tk.NORMAL if enabled else tk.DISABLED
        self.edit_btn.config(state=state, bg=f"{'#84C7FC' if enabled else '#555'}")
    
    def on_edit(self):
        logger.debug(f"[RatioPanel.{self.title}] on_edit called")
        
        # Get the current ratio value to edit
        edit_value = self.get_current_ratio_value()
        
        ## if edit_value is None:
        ##     logger.warning(f"[RatioPanel.{self.title}] No ratio value available to edit")
        ##     messagebox.showwarning("No Ratio", f"No {self.title} value available to edit. Please select a track or run a race session first.")
        ##     return

        if edit_value is None:
            edit_value = 1.000
        
        logger.debug(f"[RatioPanel.{self.title}] Using edit_value={edit_value}")
        
        # Create edit dialog
        dialog = tk.Toplevel(self)
        dialog.title(f"Edit {self.title}")
        dialog.geometry("400x300")
        dialog.configure(bg='#2b2b2b')
        dialog.transient(self)
        dialog.grab_set()
        
        frame = tk.Frame(dialog, bg='#2b2b2b', padx=20, pady=20)
        frame.pack(fill=tk.BOTH, expand=True)
        
        tk.Label(frame, text=f"Current {self.title}:", bg='#2b2b2b', fg='#888').pack()
        current_value_label = tk.Label(frame, text=f"{edit_value:.6f}", bg='#2b2b2b', fg='#4CAF50',
                                        font=('Courier', 14))
        current_value_label.pack(pady=5)
        
        tk.Label(frame, text=f"New {self.title} (min: {self.min_ratio}, max: {self.max_ratio}):",
                 bg='#2b2b2b', fg='#888').pack(pady=(15, 5))
        
        # Use a StringVar so the spinbox always shows exactly what we set.
        # Reading the value back via spinbox.get() avoids the known DoubleVar
        # issue where manually typed text is not reflected by the variable.
        spinbox = tk.Spinbox(frame, from_=self.min_ratio, to=self.max_ratio, increment=0.01,
                              width=15, font=('Courier', 12),
                              bg='#3c3c3c', fg='white')
        spinbox.pack()
        
        # Explicitly set the initial value after creation so the spinbox
        # displays the real current ratio, not the from_ default (e.g. 0.5).
        spinbox.delete(0, tk.END)
        spinbox.insert(0, f"{edit_value:.6f}")
        
        # Preview label
        preview_var = tk.StringVar(value=f"Will write: {edit_value:.6f}")
        preview_label = tk.Label(frame, textvariable=preview_var, bg='#2b2b2b', fg='#888', font=('Arial', 9))
        preview_label.pack(pady=10)
        
        def on_spin_change(*args):
            try:
                val = float(spinbox.get())
                preview_var.set(f"Will write: {val:.6f}")
            except ValueError:
                pass
        
        spinbox.bind('<KeyRelease>', on_spin_change)
        spinbox.bind('<<Increment>>', on_spin_change)
        spinbox.bind('<<Decrement>>', on_spin_change)
        
        button_frame = tk.Frame(frame, bg='#2b2b2b')
        button_frame.pack(pady=20)
        
        def apply():
            # Read directly from the spinbox widget so that manually typed
            # values are captured correctly (DoubleVar.get() only tracks
            # arrow-button changes, not keyboard input).
            try:
                new_ratio = float(spinbox.get())
            except ValueError:
                messagebox.showwarning("Invalid Value",
                    "Please enter a valid number.")
                return
            logger.debug(f"[RatioPanel.{self.title}] Apply clicked, new_ratio={new_ratio}")
            dialog.destroy()
            if self.main_window and hasattr(self.main_window, 'on_manual_edit'):
                session = "qual" if self.title == "Quali-Ratio" else "race"
                self.main_window.on_manual_edit(session, new_ratio)
            else:
                logger.error(f"[RatioPanel.{self.title}] main_window or on_manual_edit not available")
        
        tk.Button(button_frame, text="Cancel", command=dialog.destroy,
                  bg='#555', fg='white', padx=15, pady=5).pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="Apply", command=apply,
                  bg='#4CAF50', fg='white', padx=15, pady=5).pack(side=tk.LEFT, padx=5)
        
        # Bind Enter key to apply
        spinbox.bind('<Return>', lambda e: apply())
        dialog.bind('<Return>', lambda e: apply())
    
    def on_revert(self):
        logger.debug(f"[RatioPanel.{self.title}] on_revert called, previous_ratio={self.previous_ratio}")
        
        if self.previous_ratio is not None:
            if self.main_window and hasattr(self.main_window, 'on_revert_ratio'):
                session = "qual" if self.title == "Quali-Ratio" else "race"
                self.main_window.on_revert_ratio(session)
        else:
            messagebox.showwarning("Cannot Revert", "No previous ratio value available to revert to.")
    
    def revert_success(self):
        self.previous_ratio = None
        self.revert_btn.config(state=tk.DISABLED)


class MainWindowTk:
    """Main application window using tkinter"""
    
    def __init__(self, config_file: str = "cfg.yml"):
        self.config_file = config_file
        self.config = get_config_with_defaults(config_file)
        self.db_path = get_db_path(config_file)
        self.db = CurveDatabase(self.db_path)
        
        self.min_ratio, self.max_ratio = get_ratio_limits(config_file)
        
        self.autosave_enabled = True
        self.autoratio_enabled = True
        
        self.qual_panel = None
        self.race_panel = None
        self.daemon = None
        self.advanced_window = None
        
        self.qual_a = DEFAULT_A_VALUE
        self.qual_b = 70.0
        self.race_a = DEFAULT_A_VALUE
        self.race_b = 70.0
        
        self.current_track = ""
        self.current_vehicle = ""
        self.current_vehicle_class = ""
        
        self.qual_best_ai = None
        self.qual_worst_ai = None
        self.race_best_ai = None
        self.race_worst_ai = None
        
        self.user_qualifying_sec = 0.0
        self.user_best_lap_sec = 0.0
        self.last_qual_ratio = None
        self.last_race_ratio = None
        self.qual_read_ratio = None
        self.race_read_ratio = None
        self.original_qual_ratio = None
        self.original_race_ratio = None
        
        self.qual_ab_modified = False
        self.race_ab_modified = False
        
        logger.info("MainWindowTk initialized")
        logger.debug(f"min_ratio={self.min_ratio}, max_ratio={self.max_ratio}")
        
        # Load vehicle classes
        from core_common import get_data_file_path
        vehicle_classes_path = get_data_file_path("vehicle_classes.json")
        self.class_mapping = load_vehicle_classes(vehicle_classes_path)
        
        self.autopilot_manager = AutopilotManager(self.db)
        
        # Initialize user laptimes manager
        max_laptimes = get_nr_last_user_laptimes(config_file)
        self.user_laptimes_manager = UserLapTimesManager(self.db_path, max_laptimes)
        self.autopilot_manager.set_user_laptimes_manager(self.user_laptimes_manager)
        
        self.autopilot_manager.set_enabled(self.autoratio_enabled)
        
        # Setup UI
        self.setup_ui()
        
        if not self.ensure_base_path():
            messagebox.showerror("No Path Selected",
                "GTR2 installation path is required for the application to work.\n\n"
                "Please run the application again and select the correct path.")
            return
        
        self.load_data()
        self.update_display()
        
        base_path = get_base_path(config_file)
        if base_path:
            self.start_daemon()
        
        self.track_label.config(text="- No Track Selected -")
    
    def setup_ui(self):
        self.root = tk.Tk()
        self.root.title("GTR2 Dynamic AI")
        self.root.geometry("950x700")
        self.root.minsize(850, 600)
        self.root.configure(bg='#1e1e1e')
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        
        # Main container
        main_frame = tk.Frame(self.root, bg='#1e1e1e')
        main_frame.pack(fill=tk.BOTH, expand=True, padx=30, pady=30)
        
        # Top section with header
        top_frame = tk.Frame(main_frame, bg='#1e1e1e')
        top_frame.pack(fill=tk.X, pady=(0, 20))
        
        # Header with track  and car class info
        header_frame = tk.Frame(top_frame, bg='#1e1e1e')
        header_frame.pack(fill=tk.X)
        
        title_label1 = tk.Label(header_frame, text="GTR", fg='#888', bg='#1e1e1e',
                                font=('Arial', 40, 'bold'))
        title_label1.pack(side=tk.LEFT)
        title_label2 = tk.Label(header_frame, text="2", fg='#d20a0a', bg='#1e1e1e',
                                font=('Arial', 26, 'bold'))
        title_label2.pack(side=tk.LEFT, pady=(8, 20))
        
        # Track container
        track_container = tk.Frame(header_frame, bg='#2b2b2b', relief=tk.FLAT, bd=0)
        track_container.pack(side=tk.TOP, fill=tk.BOTH, padx=5, pady=5)
        
        tk.Label(track_container, text="Track:", bg='#2b2b2b', fg='#888',
                 font=('Arial', 11)).pack(side=tk.LEFT, padx=(10, 5), pady=5)
        
        self.track_label = tk.Label(track_container, text="- No Track Selected -", bg='#2b2b2b',
                                     fg='#FFA500', font=('Arial', 14, 'bold'))
        self.track_label.pack(side=tk.LEFT, padx=5, pady=5)
        
        # Car class container
        class_container = tk.Frame(header_frame, bg='#2b2b2b', relief=tk.FLAT, bd=0)
        class_container.pack(side=tk.BOTTOM, fill=tk.BOTH, padx=5, pady=5)
        
        tk.Label(class_container, text="Car Class:", bg='#2b2b2b', fg='#888',
                 font=('Arial', 11)).pack(side=tk.LEFT, padx=(10, 5), pady=5)
        
        self.car_class_label = tk.Label(class_container, text="- No Car Selected -", bg='#2b2b2b',
                                         fg='#FFA500', font=('Arial', 14, 'bold'))
        self.car_class_label.pack(side=tk.LEFT, padx=5, pady=5)
        
        ## select_track_btn = tk.Button(track_container, text="Configure", bg='#9C27B0', fg='white',
        ##                               font=('Arial', 10, 'bold'), relief=tk.FLAT, padx=12, pady=4,
        ##                               command=self.open_advanced_to_data_management)
        ## select_track_btn.pack(side=tk.LEFT, padx=(10, 10), pady=5)
        
        # Panels container
        panels_frame = tk.Frame(main_frame, bg='#1e1e1e')
        panels_frame.pack(fill=tk.BOTH, expand=True, pady=20)
        
        # Left panel (Qualifying)
        left_panel = tk.Frame(panels_frame, bg='#1e1e1e')
        left_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 15))
        
        self.qual_panel = RatioPanel(left_panel, self, "Quali-Ratio", self.min_ratio, self.max_ratio)
        self.qual_panel.pack(fill=tk.BOTH, expand=True)
        
        # Right panel (Race)
        right_panel = tk.Frame(panels_frame, bg='#1e1e1e')
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(15, 0))
        
        self.race_panel = RatioPanel(right_panel, self, "Race-Ratio", self.min_ratio, self.max_ratio)
        self.race_panel.pack(fill=tk.BOTH, expand=True)
        
        # Bottom buttons
        bottom_frame = tk.Frame(main_frame, bg='#1e1e1e')
        bottom_frame.pack(fill=tk.X, pady=(20, 0))
        
        # Toggle switches
        self.autosave_btn = tk.Button(bottom_frame,
                                       text="Auto-harvest Data (ON)" if self.autosave_enabled else "Auto-harvest Data (OFF)",
                                       bg='#4CAF50' if self.autosave_enabled else '#3c3c3c',
                                       fg='white', font=('Arial', 11, 'bold'),
                                       relief=tk.FLAT, padx=18, pady=8,
                                       command=self.toggle_autosave)
        self.autosave_btn.pack(side=tk.LEFT, padx=5)
        
        self.autoratio_btn = tk.Button(bottom_frame,
                                        text="Auto-calculate Ratios (ON)" if self.autoratio_enabled else "Auto-calculate Ratios (OFF)",
                                        bg='#4CAF50' if self.autoratio_enabled else '#3c3c3c',
                                        fg='white', font=('Arial', 11, 'bold'),
                                        relief=tk.FLAT, padx=18, pady=8,
                                        command=self.toggle_autoratio)
        self.autoratio_btn.pack(side=tk.LEFT, padx=5)
        
        # Spacer
        tk.Frame(bottom_frame, bg='#1e1e1e', width=50).pack(side=tk.LEFT, expand=True)
        
        # Advanced and Exit buttons
        ## advanced_btn = tk.Button(bottom_frame, text="Advanced", bg='#9C27B0', fg='white',
        ##                           font=('Arial', 11, 'bold'), relief=tk.FLAT, padx=24, pady=8,
        ##                           command=self.open_advanced_settings)
        ## advanced_btn.pack(side=tk.RIGHT, padx=5)
        
        exit_btn = tk.Button(bottom_frame, text="Exit", bg='#d20a0a', fg='white',
                              font=('Arial', 11, 'bold'), relief=tk.FLAT, padx=24, pady=8,
                              command=self.on_close)
        exit_btn.pack(side=tk.RIGHT, padx=5)
        
        # Status bar
        self.status_bar = tk.Frame(self.root, bg='#2b2b2b', height=25)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        self.status_label = tk.Label(self.status_bar, text="Ready", bg='#2b2b2b', fg='#888',
                                      anchor=tk.W, padx=10)
        self.status_label.pack(fill=tk.X)
        
        # Style configurations
        style = ttk.Style()
        style.theme_use('clam')
        style.configure("TProgressbar", background='#4CAF50', troughcolor='#3c3c3c')
        
        logger.info("UI setup complete")
    
##    def open_advanced_to_data_management(self):
##        self.open_advanced_settings()
    
##    def open_advanced_settings(self):
##        if self.advanced_window is None or not self.advanced_window.winfo_exists():
##            self.launch_advanced_dialog()
##        else:
##            self.advanced_window.lift()
##            self.advanced_window.focus()
    
##    def launch_advanced_dialog(self):
##        # Hide the tkinter window temporarily
##        self.root.withdraw()
##        
##        try:
##            from PyQt5.QtWidgets import QApplication
##            from gui_advanced_settings import AdvancedSettingsDialog
##            
##            # Check if a QApplication instance exists, create one if not
##            qt_app = QApplication.instance()
##            if qt_app is None:
##                qt_app = QApplication(sys.argv)
##            
##            # Create and show the dialog - pass None as parent
##            self.advanced_window = AdvancedSettingsDialog(None, self.db, None)
##            
##            # Connect signals
##            self.advanced_window.data_updated.connect(self.on_data_updated)
##            self.advanced_window.formula_updated.connect(self.on_formula_updated)
##            self.advanced_window.ratio_saved.connect(self.on_ratio_saved_from_advanced)
##            self.advanced_window.lap_time_updated.connect(self.on_lap_time_updated_from_advanced)
##            self.advanced_window.track_selected.connect(self.on_track_selected_from_advanced)
##            
##            # Manually set the data in the dialog
##            if hasattr(self.advanced_window, 'curve_graph'):
##                self.advanced_window.curve_graph.current_track = self.current_track
##                self.advanced_window.curve_graph.current_vehicle = self.current_vehicle
##                self.advanced_window.curve_graph.user_qual_time = self.user_qualifying_sec if self.user_qualifying_sec > 0 else None
##                self.advanced_window.curve_graph.user_race_time = self.user_best_lap_sec if self.user_best_lap_sec > 0 else None
##                self.advanced_window.curve_graph.user_qual_ratio = self.last_qual_ratio
##                self.advanced_window.curve_graph.user_race_ratio = self.last_race_ratio
##                self.advanced_window.curve_graph.set_formulas(self.qual_a, self.qual_b, self.race_a, self.race_b)
##                self.advanced_window.curve_graph.load_data()
##                self.advanced_window.curve_graph.full_refresh()
##            
##            if hasattr(self.advanced_window, 'qual_panel'):
##                self.advanced_window.qual_panel.update_formula(self.qual_a, self.qual_b)
##                self.advanced_window.qual_panel.update_user_time(self.user_qualifying_sec)
##                self.advanced_window.qual_panel.update_ratio(self.last_qual_ratio)
##            
##            if hasattr(self.advanced_window, 'race_panel'):
##                self.advanced_window.race_panel.update_formula(self.race_a, self.race_b)
##                self.advanced_window.race_panel.update_user_time(self.user_best_lap_sec)
##                self.advanced_window.race_panel.update_ratio(self.last_race_ratio)
##            
##            self.advanced_window.show()
##            
##            # When dialog closes, show tkinter window again
##            def on_dialog_close():
##                self.advanced_window = None
##                self.root.deiconify()
##                self.root.lift()
##                self.root.focus()
##            
##            self.advanced_window.finished.connect(on_dialog_close)
##            
##        except Exception as e:
##            messagebox.showerror("Error", f"Failed to open Advanced Settings:\n{str(e)}")
##            self.root.deiconify()
    
    def on_track_selected_from_advanced(self, track_name: str):
        if track_name and track_name != self.current_track:
            self.current_track = track_name
            self.track_label.config(text=track_name)
            self.root.title(f"GTR2 Dynamic AI - {self.current_track}")
            
            self.qual_best_ai, self.qual_worst_ai = self.get_ai_times_for_track(track_name, "qual")
            self.race_best_ai, self.race_worst_ai = self.get_ai_times_for_track(track_name, "race")
            
            self.update_formulas_from_autopilot()
            self.update_display()
            self.load_aiw_ratios()
    
    def get_ai_times_for_track(self, track: str, session_type: str) -> Tuple[Optional[float], Optional[float]]:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if session_type == "qual":
            cursor.execute("""
                SELECT qual_time_sec FROM ai_results ar
                JOIN race_sessions rs ON ar.race_id = rs.race_id
                WHERE rs.track_name = ? AND ar.qual_time_sec > 0
                ORDER BY ar.qual_time_sec LIMIT 1
            """, (track,))
            best_row = cursor.fetchone()
            cursor.execute("""
                SELECT qual_time_sec FROM ai_results ar
                JOIN race_sessions rs ON ar.race_id = rs.race_id
                WHERE rs.track_name = ? AND ar.qual_time_sec > 0
                ORDER BY ar.qual_time_sec DESC LIMIT 1
            """, (track,))
            worst_row = cursor.fetchone()
        else:
            cursor.execute("""
                SELECT best_lap_sec FROM ai_results ar
                JOIN race_sessions rs ON ar.race_id = rs.race_id
                WHERE rs.track_name = ? AND ar.best_lap_sec > 0
                ORDER BY ar.best_lap_sec LIMIT 1
            """, (track,))
            best_row = cursor.fetchone()
            cursor.execute("""
                SELECT best_lap_sec FROM ai_results ar
                JOIN race_sessions rs ON ar.race_id = rs.race_id
                WHERE rs.track_name = ? AND ar.best_lap_sec > 0
                ORDER BY ar.best_lap_sec DESC LIMIT 1
            """, (track,))
            worst_row = cursor.fetchone()
        
        conn.close()
        best = best_row[0] if best_row else None
        worst = worst_row[0] if worst_row else None
        return best, worst
    
    def update_formulas_from_autopilot(self):
        if not self.current_track or not self.current_vehicle_class:
            if self.current_vehicle:
                self.current_vehicle_class = get_vehicle_class(self.current_vehicle, self.class_mapping)
            if not self.current_vehicle_class:
                return
        
        qual_formula = self.autopilot_manager.formula_manager.get_formula_by_class(
            self.current_track, self.current_vehicle_class, "qual")
        if qual_formula and qual_formula.is_valid():
            self.qual_b = qual_formula.b
        
        race_formula = self.autopilot_manager.formula_manager.get_formula_by_class(
            self.current_track, self.current_vehicle_class, "race")
        if race_formula and race_formula.is_valid():
            self.race_b = race_formula.b
    
    def on_data_updated(self):
        self.load_data()
        self.update_display()
    
    def on_formula_updated(self, session_type: str, a: float, b: float):
        if session_type == "qual":
            self.qual_b = b
            self.qual_ab_modified = True
        else:
            self.race_b = b
            self.race_ab_modified = True
        self.update_display()
    
    def on_ratio_saved_from_advanced(self, session_type: str, ratio: float):
        if session_type == "qual":
            self.last_qual_ratio = ratio
            self.qual_panel.update_ratio(ratio)
            self.qual_panel.previous_ratio = None
            self.qual_panel.revert_btn.config(state=tk.DISABLED)
        else:
            self.last_race_ratio = ratio
            self.race_panel.update_ratio(ratio)
            self.race_panel.previous_ratio = None
            self.race_panel.revert_btn.config(state=tk.DISABLED)
    
    def on_lap_time_updated_from_advanced(self, session_type: str, lap_time: float):
        if session_type == "qual":
            self.user_qualifying_sec = lap_time
            self.qual_panel.update_user_time(lap_time)
            if hasattr(self, 'current_track') and hasattr(self, 'current_vehicle_class'):
                self.user_laptimes_manager.add_laptime(
                    self.current_track, self.current_vehicle_class, "qual",
                    lap_time, self.last_qual_ratio
                )
        else:
            self.user_best_lap_sec = lap_time
            self.race_panel.update_user_time(lap_time)
            if hasattr(self, 'current_track') and hasattr(self, 'current_vehicle_class'):
                self.user_laptimes_manager.add_laptime(
                    self.current_track, self.current_vehicle_class, "race",
                    lap_time, self.last_race_ratio
                )
    
    def load_aiw_ratios(self):
        logger.debug(f"load_aiw_ratios called, current_track={self.current_track}")
        
        if not self.current_track:
            logger.warning("load_aiw_ratios: no current track")
            return
        
        aiw_path = self.find_aiw_file(self.current_track)
        logger.debug(f"load_aiw_ratios: aiw_path={aiw_path}")
        
        if not aiw_path or not aiw_path.exists():
            logger.warning(f"load_aiw_ratios: AIW file not found")
            return
        
        qual_ratio, race_ratio = self.read_aiw_ratios(aiw_path)
        logger.debug(f"load_aiw_ratios: qual_ratio={qual_ratio}, race_ratio={race_ratio}")
        
        if qual_ratio is not None:
            self.last_qual_ratio = qual_ratio
            self.qual_panel.update_ratio(qual_ratio)
            self.qual_panel.update_last_read_ratio(qual_ratio)
            if self.original_qual_ratio is None:
                self.original_qual_ratio = qual_ratio
        
        if race_ratio is not None:
            self.last_race_ratio = race_ratio
            self.race_panel.update_ratio(race_ratio)
            self.race_panel.update_last_read_ratio(race_ratio)
            if self.original_race_ratio is None:
                self.original_race_ratio = race_ratio
        
        self.qual_read_ratio = qual_ratio
        self.race_read_ratio = race_ratio
    
    def find_aiw_file(self, track_name: str) -> Optional[Path]:
        if track_name == '':
            logger.error(f"find_aiw_file: No Track Name provided!")
            return None

        base_path = get_base_path(self.config_file)
        if not base_path:
            logger.error("find_aiw_file: No base path configured")
            return None
        
        locations_dir = base_path / "GameData" / "Locations"
        if not locations_dir.exists():
            logger.error(f"find_aiw_file: Locations directory not found: {locations_dir}")
            return None
        

        track_lower = track_name.lower()
        for track_dir in locations_dir.iterdir():
            if track_dir.is_dir() and track_dir.name.lower() == track_lower:
                for ext in ["*.AIW", "*.aiw"]:
                    aiw_files = list(track_dir.glob(ext))
                    if aiw_files:
                        logger.info(f"find_aiw_file: Found AIW file at {aiw_files[0]}")
                        return aiw_files[0]
        
        for ext in ["*.AIW", "*.aiw"]:
            for aiw_file in locations_dir.rglob(ext):
                if aiw_file.stem.lower() == track_lower or track_lower in aiw_file.stem.lower():
                    logger.info(f"find_aiw_file: Found AIW file via stem match at {aiw_file}")
                    return aiw_file
        
        logger.error(f"find_aiw_file: No AIW file found for track {track_name}")
        return None
    
    def read_aiw_ratios(self, aiw_path: Path) -> tuple:
        qual_ratio = None
        race_ratio = None
        
        try:
            with open(aiw_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            waypoint_match = re.search(r'\[Waypoint\](.*?)(?=\[|$)', content, re.DOTALL | re.IGNORECASE)
            if waypoint_match:
                section = waypoint_match.group(1)
                
                qual_match = re.search(r'QualRatio\s*=\s*\(?([\d.eE+-]+)\)?', section, re.IGNORECASE)
                if qual_match:
                    qual_ratio = float(qual_match.group(1))
                
                race_match = re.search(r'RaceRatio\s*=\s*\(?([\d.eE+-]+)\)?', section, re.IGNORECASE)
                if race_match:
                    race_ratio = float(race_match.group(1))
            
            return qual_ratio, race_ratio
            
        except Exception as e:
            logger.error(f"Error reading AIW ratios: {e}")
            return None, None
    
    def ensure_base_path(self) -> bool:
        config = get_config_with_defaults(self.config_file)
        base_path = config.get('base_path', '')
        
        if not base_path or not Path(base_path).exists():
            dialog = BasePathSelectionDialog(self.root)
            if dialog.show() and dialog.selected_path:
                update_base_path(dialog.selected_path, self.config_file)
                return True
            else:
                return False
        
        path = Path(base_path)
        if (path / "GameData").exists() and (path / "UserData").exists():
            return True
        else:
            reply = messagebox.askyesno("Invalid Path",
                f"The configured path '{base_path}' does not appear to be a valid GTR2 installation.\n\n"
                "Would you like to select a different path?")
            if reply:
                dialog = BasePathSelectionDialog(self.root)
                if dialog.show() and dialog.selected_path:
                    update_base_path(dialog.selected_path, self.config_file)
                    return True
            return False
    
    def toggle_autosave(self):
        self.autosave_enabled = not self.autosave_enabled
        self.autosave_btn.config(
            text="Auto-harvest Data (ON)" if self.autosave_enabled else "Auto-harvest Data (OFF)",
            bg='#4CAF50' if self.autosave_enabled else '#3c3c3c'
        )
        self.status_label.config(text=f"Auto-harvest Data {'ON' if self.autosave_enabled else 'OFF'}")
        self.root.after(2000, lambda: self.status_label.config(text="Ready"))
    
    def toggle_autoratio(self):
        self.autoratio_enabled = not self.autoratio_enabled
        self.autopilot_manager.set_enabled(self.autoratio_enabled)
        self.autoratio_btn.config(
            text="Auto-calculate Ratios (ON)" if self.autoratio_enabled else "Auto-calculate Ratios (OFF)",
            bg='#4CAF50' if self.autoratio_enabled else '#3c3c3c'
        )
        self.qual_panel.set_edit_enabled(not self.autoratio_enabled)
        self.race_panel.set_edit_enabled(not self.autoratio_enabled)
        self.status_label.config(text=f"Auto-calculate Ratios {'ON' if self.autoratio_enabled else 'OFF'}")
        self.root.after(2000, lambda: self.status_label.config(text="Ready"))
        
        if self.autoratio_enabled:
            self.autopilot_manager.reload_formulas()
            self.update_formulas_from_autopilot()
            self.update_display()
    
    def on_manual_edit(self, session_type: str, new_ratio: float):
        logger.info(f"on_manual_edit called: session={session_type}, new_ratio={new_ratio}")
        
        if self.autoratio_enabled:
            messagebox.showwarning("Auto-Ratio Enabled", 
                "Manual editing is disabled while Auto-calculate Ratios is ON.")
            return
        
        ratio_name = "QualRatio" if session_type == "qual" else "RaceRatio"
        
        if self.current_track == '':
            logger.error(f"on_manual_edit: No Track name provided")
            messagebox.showerror("AIW Not Found", 
                f"Could not find AIW file because no track was provided\n\n"
                f"You may need to run a session on that Track before you can modify its Ratio!")
            return

        # Find the AIW file
        aiw_path = self.find_aiw_file(self.current_track)
        
        if not aiw_path:
            logger.error(f"on_manual_edit: AIW file not found for track {self.current_track}")
            messagebox.showerror("AIW Not Found", 
                f"Could not find AIW file for track: {self.current_track}\n\n"
                f"Please make sure the track folder exists in GameData/Locations/")
            return
        
        if not aiw_path.exists():
            logger.error(f"on_manual_edit: AIW file does not exist at {aiw_path}")
            messagebox.showerror("AIW Not Found", f"AIW file not found at:\n{aiw_path}")
            return
        
        # Validate ratio range
        clamped_ratio = new_ratio
        if new_ratio < self.min_ratio:
            clamped_ratio = self.min_ratio
            messagebox.showwarning(f"{ratio_name} Adjusted",
                f"WARNING: {ratio_name} = {new_ratio:.6f} fell below the minimum allowed value of {self.min_ratio:.3f}.\n\n"
                f"The ratio has been clamped to {clamped_ratio:.6f}.")
        elif new_ratio > self.max_ratio:
            clamped_ratio = self.max_ratio
            messagebox.showwarning(f"{ratio_name} Adjusted",
                f"WARNING: {ratio_name} = {new_ratio:.6f} exceeded the maximum allowed value of {self.max_ratio:.3f}.\n\n"
                f"The ratio has been clamped to {clamped_ratio:.6f}.")
        
        # Store previous ratio for revert
        if session_type == "qual":
            current_ratio = self.last_qual_ratio
            if current_ratio is not None and abs(clamped_ratio - current_ratio) > 0.000001:
                self.qual_panel.previous_ratio = current_ratio
                self.qual_panel.revert_btn.config(state=tk.NORMAL)
                logger.debug(f"Stored previous qual ratio: {current_ratio}")
        else:
            current_ratio = self.last_race_ratio
            if current_ratio is not None and abs(clamped_ratio - current_ratio) > 0.000001:
                self.race_panel.previous_ratio = current_ratio
                self.race_panel.revert_btn.config(state=tk.NORMAL)
                logger.debug(f"Stored previous race ratio: {current_ratio}")
        
        # Write to AIW file
        if self.update_aiw_ratio(aiw_path, ratio_name, clamped_ratio):
            logger.info(f"Successfully updated {ratio_name} to {clamped_ratio:.6f}")
            
            if session_type == "qual":
                self.last_qual_ratio = clamped_ratio
                self.qual_panel.update_ratio(clamped_ratio)
                self.qual_panel.update_last_read_ratio(clamped_ratio)
                self.qual_read_ratio = clamped_ratio
            else:
                self.last_race_ratio = clamped_ratio
                self.race_panel.update_ratio(clamped_ratio)
                self.race_panel.update_last_read_ratio(clamped_ratio)
                self.race_read_ratio = clamped_ratio
            
            self.status_label.config(text=f"{ratio_name} updated to {clamped_ratio:.6f}")
            self.root.after(3000, lambda: self.status_label.config(text="Ready"))
        else:
            logger.error(f"Failed to update {ratio_name} in AIW file")
            messagebox.showerror("Update Failed", f"Failed to update {ratio_name} in the AIW file.")
    
    def update_aiw_ratio(self, aiw_path: Path, ratio_name: str, new_ratio: float) -> bool:
        logger.info(f"update_aiw_ratio: path={aiw_path}, ratio_name={ratio_name}, new_ratio={new_ratio}")
        
        try:
            # Read the file
            with open(aiw_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            logger.debug(f"File content length: {len(content)} characters")
            
            # Look for the ratio in the Waypoint section first
            waypoint_match = re.search(r'(\[Waypoint\][^\[]*)', content, re.DOTALL | re.IGNORECASE)
            if waypoint_match:
                waypoint_section = waypoint_match.group(1)
                logger.debug(f"Found Waypoint section, length: {len(waypoint_section)}")
                
                # Pattern to match the specific ratio line
                pattern = rf'({re.escape(ratio_name)}\s*=\s*\(?)\s*([0-9.eE+-]+)\s*(\)?)'
                
                def replacer(match):
                    prefix = match.group(1)
                    suffix = match.group(3) if match.group(3) else ""
                    return f"{prefix}{new_ratio:.6f}{suffix}"
                
                new_content, count = re.subn(pattern, replacer, waypoint_section, flags=re.IGNORECASE)
                
                if count > 0:
                    # Replace the waypoint section in the full content
                    full_new_content = content.replace(waypoint_section, new_content)
                    
                    # Write back the file
                    with open(aiw_path, 'w', encoding='utf-8', errors='ignore') as f:
                        f.write(full_new_content)
                    
                    logger.info(f"Successfully updated {ratio_name} to {new_ratio:.6f} in {aiw_path.name} (found {count} match)")
                    return True
                else:
                    logger.warning(f"No {ratio_name} pattern found in Waypoint section")
            else:
                logger.warning("No Waypoint section found in AIW file")
            
            # Try searching the entire file
            pattern_full = rf'({re.escape(ratio_name)}\s*=\s*\(?)\s*([0-9.eE+-]+)\s*(\)?)'
            
            def replacer_full(match):
                prefix = match.group(1)
                suffix = match.group(3) if match.group(3) else ""
                return f"{prefix}{new_ratio:.6f}{suffix}"
            
            new_content, count = re.subn(pattern_full, replacer_full, content, flags=re.IGNORECASE)
            
            if count > 0:
                with open(aiw_path, 'w', encoding='utf-8', errors='ignore') as f:
                    f.write(new_content)
                logger.info(f"Successfully updated {ratio_name} to {new_ratio:.6f} (found {count} match in full file)")
                return True
            
            logger.error(f"Could not find {ratio_name} anywhere in the AIW file")
            return False
                
        except Exception as e:
            logger.error(f"Error updating AIW ratio: {e}", exc_info=True)
            return False
    
    def on_revert_ratio(self, session_type: str):
        logger.debug(f"on_revert_ratio called: session={session_type}")
        
        if session_type == "qual":
            old_ratio = self.qual_panel.previous_ratio
            if old_ratio is None:
                messagebox.showwarning("Cannot Revert", "No previous ratio value available to revert to.")
                return
            
            aiw_path = self.find_aiw_file(self.current_track)
            if not aiw_path or not aiw_path.exists():
                messagebox.showerror("AIW Not Found", "Could not find AIW file to revert.")
                return
            
            if self.update_aiw_ratio(aiw_path, "QualRatio", old_ratio):
                self.last_qual_ratio = old_ratio
                self.qual_panel.update_ratio(old_ratio)
                self.qual_panel.update_last_read_ratio(old_ratio)
                self.qual_read_ratio = old_ratio
                self.qual_panel.revert_success()
                self.status_label.config(text=f"QualRatio reverted to {old_ratio:.6f}")
                self.root.after(3000, lambda: self.status_label.config(text="Ready"))
                logger.info(f"QualRatio reverted to {old_ratio}")
            else:
                messagebox.showerror("Revert Failed", "Failed to update the AIW file.")
        else:
            old_ratio = self.race_panel.previous_ratio
            if old_ratio is None:
                messagebox.showwarning("Cannot Revert", "No previous ratio value available to revert to.")
                return
            
            aiw_path = self.find_aiw_file(self.current_track)
            if not aiw_path or not aiw_path.exists():
                messagebox.showerror("AIW Not Found", "Could not find AIW file to revert.")
                return
            
            if self.update_aiw_ratio(aiw_path, "RaceRatio", old_ratio):
                self.last_race_ratio = old_ratio
                self.race_panel.update_ratio(old_ratio)
                self.race_panel.update_last_read_ratio(old_ratio)
                self.race_read_ratio = old_ratio
                self.race_panel.revert_success()
                self.status_label.config(text=f"RaceRatio reverted to {old_ratio:.6f}")
                self.root.after(3000, lambda: self.status_label.config(text="Ready"))
                logger.info(f"RaceRatio reverted to {old_ratio}")
            else:
                messagebox.showerror("Revert Failed", "Failed to update the AIW file.")
    
    def calculate_ratio_from_user_time(self, session_type: str, user_time: float) -> Optional[float]:
        a = DEFAULT_A_VALUE
        b = self.qual_b if session_type == "qual" else self.race_b
        
        denominator = user_time - b
        if denominator <= 0:
            return None
        
        ratio = a / denominator
        return ratio
    
    def start_daemon(self):
        file_path = get_results_file_path(self.config_file)
        base_path = get_base_path(self.config_file)
        if not file_path or not base_path:
            logger.warning(f"[MAIN] Cannot start daemon: file_path={file_path}, base_path={base_path}")
            return
        poll_interval = get_poll_interval(self.config_file)
        logger.info(f"[MAIN] Starting daemon with callback, watching: {file_path}")
        self.daemon = FileMonitorDaemon(file_path, base_path, poll_interval, callback=self.on_file_changed)
        self.daemon.start()
    
    def stop_daemon(self):
        if self.daemon:
            self.daemon.stop()
            self.daemon = None
    
    def on_file_changed(self, race_data: RaceData):
        """Direct callback from the file monitor daemon"""
        logger.info(f"[MAIN] on_file_changed called with race_data: track={race_data.track_name if race_data else 'None'}")
        
        if not race_data:
            logger.warning("[MAIN] No race data received")
            return
        
        if race_data.track_name:
            self.current_track = race_data.track_name
            self.track_label.config(text=self.current_track)
            self.root.title(f"GTR2 Dynamic AI - {self.current_track}")
        
        if race_data.user_qualifying_sec:
            self.user_qualifying_sec = race_data.user_qualifying_sec
        if race_data.user_best_lap_sec:
            self.user_best_lap_sec = race_data.user_best_lap_sec
        
        if race_data.qual_ratio:
            self.qual_read_ratio = race_data.qual_ratio
            if self.qual_panel:
                self.qual_panel.update_last_read_ratio(self.qual_read_ratio)
        if race_data.race_ratio:
            self.race_read_ratio = race_data.race_ratio
            if self.race_panel:
                self.race_panel.update_last_read_ratio(self.race_read_ratio)
        
        if race_data.qual_ratio:
            self.last_qual_ratio = race_data.qual_ratio
        if race_data.race_ratio:
            self.last_race_ratio = race_data.race_ratio
        
        if race_data.qual_best_ai_lap_sec:
            self.qual_best_ai = race_data.qual_best_ai_lap_sec
        if race_data.qual_worst_ai_lap_sec:
            self.qual_worst_ai = race_data.qual_worst_ai_lap_sec
        if race_data.best_ai_lap_sec:
            self.race_best_ai = race_data.best_ai_lap_sec
        if race_data.worst_ai_lap_sec:
            self.race_worst_ai = race_data.worst_ai_lap_sec
        
        if race_data.user_vehicle:
            self.current_vehicle = race_data.user_vehicle
            self.current_vehicle_class = get_vehicle_class(self.current_vehicle, self.class_mapping)
            self.car_class_label.config(text=self.current_vehicle_class)
        
        # Save race session to database
        race_dict = race_data.to_dict()
        race_id = self.db.save_race_session(race_dict)
        
        # Save data points if autosave is enabled
        if race_id and self.autosave_enabled:
            points_added = 0
            for track, vehicle_name, ratio, lap_time, session_type in race_data.to_data_points_with_vehicles():
                try:
                    vehicle_class = get_vehicle_class(vehicle_name, self.class_mapping)
                    if self.db.add_data_point(track, vehicle_class, float(ratio), float(lap_time), session_type):
                        points_added += 1
                except (ValueError, TypeError) as e:
                    logger.error(f"[MAIN] Failed to add data point: {e}")
            if points_added > 0:
                logger.info(f"[MAIN] Saved {points_added} new data points")
        
        # Update formulas from new data
        if self.current_track and self.current_vehicle_class:
            if race_data.qual_ratio:
                self._update_formula_from_new_data(race_data, "qual")
            if race_data.race_ratio:
                self._update_formula_from_new_data(race_data, "race")
        
        self.autopilot_manager.reload_formulas()
        self.update_formulas_from_autopilot()
        self.update_display()
        
        # Auto-ratio update if enabled
        if self.autoratio_enabled and race_data.aiw_path:
            logger.info("[MAIN] Auto-ratio is enabled, calculating new ratios")

            if self.last_qual_ratio is not None:
                self.qual_panel.previous_ratio = self.last_qual_ratio
            
            if self.last_race_ratio is not None:
                self.race_panel.previous_ratio = self.last_race_ratio
            
            if self.user_qualifying_sec > 0:
                self.user_laptimes_manager.add_laptime(
                    self.current_track, self.current_vehicle_class, "qual",
                    self.user_qualifying_sec, self.last_qual_ratio
                )
                median_time = self.user_laptimes_manager.get_median_laptime_for_combo(
                    self.current_track, self.current_vehicle_class, "qual"
                )
                effective_time = median_time if median_time is not None else self.user_qualifying_sec
                
                new_qual_ratio = self.calculate_ratio_from_user_time("qual", effective_time)
                if new_qual_ratio and abs(new_qual_ratio - self.last_qual_ratio) > 0.000001:
                    clamped = max(self.min_ratio, min(self.max_ratio, new_qual_ratio))
                    if self.update_aiw_ratio(race_data.aiw_path, "QualRatio", clamped):
                        self.last_qual_ratio = clamped
                        self.qual_panel.update_ratio(clamped)
                        self.qual_panel.revert_btn.config(state=tk.NORMAL)
            
            if self.user_best_lap_sec > 0:
                self.user_laptimes_manager.add_laptime(
                    self.current_track, self.current_vehicle_class, "race",
                    self.user_best_lap_sec, self.last_race_ratio
                )
                median_time = self.user_laptimes_manager.get_median_laptime_for_combo(
                    self.current_track, self.current_vehicle_class, "race"
                )
                effective_time = median_time if median_time is not None else self.user_best_lap_sec
                
                new_race_ratio = self.calculate_ratio_from_user_time("race", effective_time)
                if new_race_ratio and abs(new_race_ratio - self.last_race_ratio) > 0.000001:
                    clamped = max(self.min_ratio, min(self.max_ratio, new_race_ratio))
                    if self.update_aiw_ratio(race_data.aiw_path, "RaceRatio", clamped):
                        self.last_race_ratio = clamped
                        self.race_panel.update_ratio(clamped)
                        self.race_panel.revert_btn.config(state=tk.NORMAL)
        
        self.autopilot_manager.reload_formulas()
        self.update_formulas_from_autopilot()
        self.update_display()
        
        qual_display = f"{self.last_qual_ratio:.6f}" if self.last_qual_ratio is not None else "N/A"
        race_display = f"{self.last_race_ratio:.6f}" if self.last_race_ratio is not None else "N/A"
        self.status_label.config(text=f"Data processed: {self.current_track} - Qual: {qual_display} / Race: {race_display}")
        self.root.after(5000, lambda: self.status_label.config(text="Ready"))
    
    def _update_formula_from_new_data(self, race_data: RaceData, session_type: str) -> bool:
        """Update formula from new race data"""
        from core_autopilot import Formula
        
        if not self.current_track or not self.current_vehicle_class:
            return False
        
        if session_type == "qual":
            current_ratio = race_data.qual_ratio
            best_ai = race_data.qual_best_ai_lap_sec
            worst_ai = race_data.qual_worst_ai_lap_sec
        else:
            current_ratio = race_data.race_ratio
            best_ai = race_data.best_ai_lap_sec
            worst_ai = race_data.worst_ai_lap_sec
        
        if not current_ratio or current_ratio <= 0:
            return False
        
        ai_times = []
        if best_ai and best_ai > 0:
            ai_times.append(best_ai)
        if worst_ai and worst_ai > 0:
            ai_times.append(worst_ai)
        
        for ai in race_data.ai_results:
            if session_type == "qual":
                qual_time = ai.get('qual_time_sec')
                if qual_time is not None and qual_time > 0:
                    ai_times.append(qual_time)
            else:
                best_lap = ai.get('best_lap_sec')
                if best_lap is not None and best_lap > 0:
                    ai_times.append(best_lap)
        
        if not ai_times:
            return False
        
        a = DEFAULT_A_VALUE
        b_values = []
        for ai_time in ai_times:
            if ai_time is not None and ai_time > 0:
                b = ai_time - (a / current_ratio)
                b_values.append(b)
        
        if not b_values:
            return False
        
        new_b = sum(b_values) / len(b_values)
        new_b = max(10.0, min(200.0, new_b))
        
        formula = Formula(
            track=self.current_track,
            vehicle_class=self.current_vehicle_class,
            a=a,
            b=new_b,
            session_type=session_type,
            data_points_used=len(ai_times),
            confidence=0.7 if len(ai_times) >= 2 else 0.5
        )
        
        if formula.is_valid():
            self.autopilot_manager.formula_manager.save_formula(formula)
            if session_type == "qual":
                self.qual_b = new_b
            else:
                self.race_b = new_b
            return True
        return False
    
    def load_data(self):
        if not self.db.database_exists():
            return
        self.all_tracks = self.db.get_all_tracks()
        
        if self.autopilot_manager:
            self.update_formulas_from_autopilot()
    
    def update_display(self):
        if self.qual_panel:
            self.qual_panel.update_ratio(self.last_qual_ratio)
            self.qual_panel.update_ai_range(self.qual_best_ai, self.qual_worst_ai)
            self.qual_panel.update_user_time(self.user_qualifying_sec if self.user_qualifying_sec > 0 else None)
            self.qual_panel.update_formula(self.qual_a, self.qual_b)
            if self.qual_read_ratio is not None:
                self.qual_panel.update_last_read_ratio(self.qual_read_ratio)
        
        if self.race_panel:
            self.race_panel.update_ratio(self.last_race_ratio)
            self.race_panel.update_ai_range(self.race_best_ai, self.race_worst_ai)
            self.race_panel.update_user_time(self.user_best_lap_sec if self.user_best_lap_sec > 0 else None)
            self.race_panel.update_formula(self.race_a, self.race_b)
            if self.race_read_ratio is not None:
                self.race_panel.update_last_read_ratio(self.race_read_ratio)
    
    def on_close(self):
        self.stop_daemon()
        if self.advanced_window:
            try:
                self.advanced_window.close()
            except:
                pass
        self.root.quit()
        self.root.destroy()
    
    def run(self):
        self.root.mainloop()
