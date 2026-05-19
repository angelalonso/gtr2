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

import tkinter as tk
from tkinter import ttk, messagebox

from gui_pre_run_check import launch_setup_manager
from gui_track_selector import TrackSelectorDialog
from gui_ratio_panel import RatioPanel
from core_database import CurveDatabase
from core_math import DEFAULT_A_VALUE, ratio_from_time, clamp_ratio, calculate_b_from_point, get_formula_string
from core_aiw_utils import update_aiw_ratio
from core_config import (
    get_config_with_defaults, get_results_file_path, get_poll_interval,
    get_db_path, create_default_config_if_missing, get_base_path,
    get_ratio_limits, update_base_path, get_nr_last_user_laptimes
)
from core_data_extraction import RaceData
from core_autopilot import AutopilotManager, get_vehicle_class, load_vehicle_classes
from core_user_laptimes import UserLapTimesManager
from gui_base_path_dialog import BasePathSelectionDialog
from gui_file_monitor import FileMonitorDaemon

# Configure logging to show debug messages
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class MainWindowTk:
    """Main application window using tkinter"""
    
    def __init__(self, config_file: str = "cfg.yml"):
        self.config_file = config_file
        self.config = get_config_with_defaults(config_file)
        self.db_path = get_db_path(config_file)
        self.db = CurveDatabase(self.db_path)
        self.backup_dir = "aiw_backups"
        
        self.min_ratio, self.max_ratio = get_ratio_limits(config_file)
        
        self.autosave_enabled = True
        self.autoratio_enabled = True
        
        self.qual_panel = None
        self.race_panel = None
        self.daemon = None
        self.advanced_window = None
        self.setup_launch_in_progress = False
        self.graph_launch_in_progress = False
        
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
        
        # Formula accuracy tracking
        self.qual_formula_confidence = 0.0
        self.qual_formula_points = 0
        self.qual_formula_avg_error = 0.0
        self.race_formula_confidence = 0.0
        self.race_formula_points = 0
        self.race_formula_avg_error = 0.0
        
        # Queue for thread-safe GUI updates
        self._gui_queue = []
        self._queue_lock = threading.Lock()
        
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
        
        # Start the GUI queue processor
        self._process_gui_queue()
        
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
    
    def _process_gui_queue(self):
        """Process pending GUI updates from background threads"""
        with self._queue_lock:
            if self._gui_queue:
                item = self._gui_queue.pop(0)
                func = item.get('func')
                args = item.get('args', ())
                kwargs = item.get('kwargs', {})
                try:
                    func(*args, **kwargs)
                except Exception as e:
                    logger.error(f"Error processing GUI queue item: {e}")
        
        # Schedule next check
        self.root.after(100, self._process_gui_queue)
    
    def _show_warning_safe(self, title, message):
        """Thread-safe method to show a warning dialog"""
        with self._queue_lock:
            self._gui_queue.append({
                'func': messagebox.showwarning,
                'args': (title, message),
                'kwargs': {}
            })
    
    def _show_info_safe(self, title, message):
        """Thread-safe method to show an info dialog"""
        with self._queue_lock:
            self._gui_queue.append({
                'func': messagebox.showinfo,
                'args': (title, message),
                'kwargs': {}
            })
    
    def _update_status_safe(self, text):
        """Thread-safe method to update status label"""
        with self._queue_lock:
            self._gui_queue.append({
                'func': self._update_status_label,
                'args': (text,),
                'kwargs': {}
            })
    
    def _update_status_label(self, text):
        """Update status label (must be called from main thread)"""
        if hasattr(self, 'status_label'):
            self.status_label.config(text=text)
            # Auto-clear after 5 seconds
            self.root.after(5000, lambda: self.status_label.config(text="Ready") if self.status_label else None)
    
    def setup_ui(self):
        self.root = tk.Tk()
        self.root.title("GTR2 Dynamic AI")
        
        # Get screen size and set appropriate window size
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        
        if screen_width >= 1920 and screen_height >= 1080:
            window_width = 1100
            window_height = 800
        elif screen_width >= 1366:
            window_width = 1000
            window_height = 700
        else:
            window_width = 900
            window_height = 600
        
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        self.root.geometry(f"{window_width}x{window_height}+{x}+{y}")
        self.root.minsize(850, 600)
        self.root.configure(bg='#1e1e1e')
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        
        # Main container
        main_frame = tk.Frame(self.root, bg='#1e1e1e')
        main_frame.pack(fill=tk.BOTH, expand=True, padx=30, pady=30)
        
        # Top section with header
        top_frame = tk.Frame(main_frame, bg='#1e1e1e')
        top_frame.pack(fill=tk.X, pady=(0, 20))
        
        # Header with track and car class info
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
        
        # Manual track selection button (to the right of track name)
        select_track_btn = tk.Button(track_container, text="Select Track", bg='#2196F3', fg='white',
                                      font=('Arial', 10, 'bold'), relief=tk.FLAT, padx=12, pady=4,
                                      command=self.manual_track_selection)
        select_track_btn.pack(side=tk.LEFT, padx=(10, 0), pady=5)
        
        # Car class container
        class_container = tk.Frame(header_frame, bg='#2b2b2b', relief=tk.FLAT, bd=0)
        class_container.pack(side=tk.BOTTOM, fill=tk.BOTH, padx=5, pady=5)
        
        tk.Label(class_container, text="Car Class:", bg='#2b2b2b', fg='#888',
                 font=('Arial', 11)).pack(side=tk.LEFT, padx=(10, 5), pady=5)
        
        self.car_class_label = tk.Label(class_container, text="- No Car Selected -", bg='#2b2b2b',
                                         fg='#FFA500', font=('Arial', 14, 'bold'))
        self.car_class_label.pack(side=tk.LEFT, padx=5, pady=5)
        
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
        
        # Exit button
        exit_btn = tk.Button(bottom_frame, text="Exit", bg='#d20a0a', fg='white',
                              font=('Arial', 11, 'bold'), relief=tk.FLAT, padx=24, pady=8,
                              command=self.on_close)
        exit_btn.pack(side=tk.RIGHT, padx=5)

        # Setup Button
        self.setup_btn = tk.Button(bottom_frame, text="Setup", bg='#9C27B0', fg='white',
                                    font=('Arial', 10, 'bold'),
                                    relief=tk.FLAT, padx=12, pady=8,
                                    command=self.on_setup_open)
        self.setup_btn.pack(side=tk.RIGHT, padx=5)

        # Graph Button
        self.graph_btn = tk.Button(bottom_frame, text="Graph", bg='#FF9800', fg='white',
                                    font=('Arial', 10, 'bold'),
                                    relief=tk.FLAT, padx=12, pady=8,
                                    command=self.on_graph_open)
        self.graph_btn.pack(side=tk.RIGHT, padx=5)
        
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
    
    def manual_track_selection(self):
        """Open dialog for manual track selection"""
        base_path = get_base_path(self.config_file)
        
        if not base_path or not base_path.exists():
            messagebox.showerror("Base Path Error", 
                "GTR2 base path is not configured or does not exist.\n\n"
                "Please configure the correct GTR2 installation path in the setup manager.")
            
            # Ask if user wants to open setup manager
            reply = messagebox.askyesno("Open Setup Manager", 
                "Would you like to open the Setup Manager to configure the GTR2 path?")
            if reply:
                self.on_setup_open()
            return
        
        dialog = TrackSelectorDialog(self.root, base_path, self.db_path)
        selected_track = dialog.show()
        
        if selected_track:
            logger.info(f"Manually selected track: {selected_track}")
            self.current_track = selected_track
            self.track_label.config(text=selected_track)
            self.root.title(f"GTR2 Dynamic AI - {self.current_track}")
            
            # Verify AIW file exists
            from core_track_scanner import find_aiw_file_for_track
            aiw_path = find_aiw_file_for_track(selected_track, base_path)
            if aiw_path:
                logger.info(f"Found AIW file: {aiw_path}")
            else:
                logger.warning(f"No AIW file found for track: {selected_track}")
            
            # Load AI times for this track
            self.qual_best_ai, self.qual_worst_ai = self.get_ai_times_for_track(selected_track, "qual")
            self.race_best_ai, self.race_worst_ai = self.get_ai_times_for_track(selected_track, "race")
            
            # Update formulas from autopilot
            self.update_formulas_from_autopilot()
            self.update_display()
            self.load_aiw_ratios()
            
            self._update_status_safe(f"Track selected: {selected_track}")
    
    def get_ai_times_for_track(self, track: str, session_type: str) -> Tuple[Optional[float], Optional[float]]:
        """Get best and worst AI times for a track"""
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
            self.qual_formula_confidence = qual_formula.confidence
            self.qual_formula_points = qual_formula.data_points_used
            self.qual_formula_avg_error = qual_formula.avg_error
            if self.qual_panel:
                self.qual_panel.update_accuracy(
                    self.qual_formula_confidence,
                    self.qual_formula_points,
                    self.qual_formula_avg_error
                )
        
        race_formula = self.autopilot_manager.formula_manager.get_formula_by_class(
            self.current_track, self.current_vehicle_class, "race")
        if race_formula and race_formula.is_valid():
            self.race_b = race_formula.b
            self.race_formula_confidence = race_formula.confidence
            self.race_formula_points = race_formula.data_points_used
            self.race_formula_avg_error = race_formula.avg_error
            if self.race_panel:
                self.race_panel.update_accuracy(
                    self.race_formula_confidence,
                    self.race_formula_points,
                    self.race_formula_avg_error
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
        """Find AIW file for a track using the shared utility"""
        from core_track_scanner import find_aiw_file_for_track
        
        if track_name == '':
            logger.error(f"find_aiw_file: No Track Name provided!")
            return None

        base_path = get_base_path(self.config_file)
        if not base_path:
            logger.error("find_aiw_file: No base path configured")
            return None
        
        return find_aiw_file_for_track(track_name, base_path)

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
        self._update_status_safe(f"Auto-harvest Data {'ON' if self.autosave_enabled else 'OFF'}")
    
    def toggle_autoratio(self):
        self.autoratio_enabled = not self.autoratio_enabled
        self.autopilot_manager.set_enabled(self.autoratio_enabled)
        self.autoratio_btn.config(
            text="Auto-calculate Ratios (ON)" if self.autoratio_enabled else "Auto-calculate Ratios (OFF)",
            bg='#4CAF50' if self.autoratio_enabled else '#3c3c3c'
        )
        self.qual_panel.set_edit_enabled(not self.autoratio_enabled)
        self.race_panel.set_edit_enabled(not self.autoratio_enabled)
        self._update_status_safe(f"Auto-calculate Ratios {'ON' if self.autoratio_enabled else 'OFF'}")
        
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
        
        # Validate ratio range and show popup if clamped
        clamped_ratio = clamp_ratio(new_ratio, self.min_ratio, self.max_ratio)
        ratio_adjusted = False
        if clamped_ratio != new_ratio:
            ratio_adjusted = True
            messagebox.showwarning(f"{ratio_name} Adjusted",
                f"WARNING: {ratio_name} = {new_ratio:.6f} fell outside the allowed range ({self.min_ratio:.3f} - {self.max_ratio:.3f}).\n\n"
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
        if update_aiw_ratio(aiw_path, ratio_name, clamped_ratio, self.backup_dir):
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
            
            if ratio_adjusted:
                self._update_status_safe(f"{ratio_name} adjusted to {clamped_ratio:.6f} (within limits)")
            else:
                self._update_status_safe(f"{ratio_name} updated to {clamped_ratio:.6f}")
        else:
            logger.error(f"Failed to update {ratio_name} in AIW file")
            messagebox.showerror("Update Failed", f"Failed to update {ratio_name} in the AIW file.")
    
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
            
            if update_aiw_ratio(aiw_path, "QualRatio", old_ratio, self.backup_dir):
                self.last_qual_ratio = old_ratio
                self.qual_panel.update_ratio(old_ratio)
                self.qual_panel.update_last_read_ratio(old_ratio)
                self.qual_read_ratio = old_ratio
                self.qual_panel.revert_success()
                self._update_status_safe(f"QualRatio reverted to {old_ratio:.6f}")
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
            
            if update_aiw_ratio(aiw_path, "RaceRatio", old_ratio, self.backup_dir):
                self.last_race_ratio = old_ratio
                self.race_panel.update_ratio(old_ratio)
                self.race_panel.update_last_read_ratio(old_ratio)
                self.race_read_ratio = old_ratio
                self.race_panel.revert_success()
                self._update_status_safe(f"RaceRatio reverted to {old_ratio:.6f}")
                logger.info(f"RaceRatio reverted to {old_ratio}")
            else:
                messagebox.showerror("Revert Failed", "Failed to update the AIW file.")
    
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
        """Direct callback from the file monitor daemon - called from background thread"""
        logger.info(f"[MAIN] on_file_changed called with race_data: track={race_data.track_name if race_data else 'None'}")
        
        if not race_data:
            logger.warning("[MAIN] No race data received")
            return
        
        # Capture all data locally to avoid threading issues
        track_name = race_data.track_name
        user_qualifying_sec = race_data.user_qualifying_sec
        user_best_lap_sec = race_data.user_best_lap_sec
        qual_ratio = race_data.qual_ratio
        race_ratio = race_data.race_ratio
        qual_best_ai = race_data.qual_best_ai_lap_sec
        qual_worst_ai = race_data.qual_worst_ai_lap_sec
        best_ai = race_data.best_ai_lap_sec
        worst_ai = race_data.worst_ai_lap_sec
        user_vehicle = race_data.user_vehicle
        aiw_path = race_data.aiw_path
        ai_results = race_data.ai_results
        current_track_ref = self.current_track
        current_vehicle_class_ref = self.current_vehicle_class
        
        # Schedule UI updates on the main thread
        if track_name:
            self.root.after(0, lambda: self._update_track(track_name))
        
        if user_qualifying_sec:
            self.root.after(0, lambda: self._update_user_qualifying(user_qualifying_sec))
        if user_best_lap_sec:
            self.root.after(0, lambda: self._update_user_best_lap(user_best_lap_sec))
        
        if qual_ratio:
            self.root.after(0, lambda: self._update_qual_read_ratio(qual_ratio))
        if race_ratio:
            self.root.after(0, lambda: self._update_race_read_ratio(race_ratio))
        
        if qual_ratio:
            self.root.after(0, lambda: self._update_qual_ratio(qual_ratio))
        if race_ratio:
            self.root.after(0, lambda: self._update_race_ratio(race_ratio))
        
        if qual_best_ai:
            self.root.after(0, lambda: self._update_qual_best_ai(qual_best_ai))
        if qual_worst_ai:
            self.root.after(0, lambda: self._update_qual_worst_ai(qual_worst_ai))
        if best_ai:
            self.root.after(0, lambda: self._update_race_best_ai(best_ai))
        if worst_ai:
            self.root.after(0, lambda: self._update_race_worst_ai(worst_ai))
        
        if user_vehicle:
            self.root.after(0, lambda: self._update_user_vehicle(user_vehicle))
        
        # Save race session to database (database operations are thread-safe)
        race_dict = race_data.to_dict()
        race_id = self.db.save_race_session(race_dict)
        
        # Save data points if autosave is enabled
        if race_id and self.autosave_enabled:
            points_added = 0
            for t_name, vehicle_name, ratio_val, lap_time, s_type in race_data.to_data_points_with_vehicles():
                try:
                    vehicle_class = get_vehicle_class(vehicle_name, self.class_mapping)
                    if self.db.add_data_point(t_name, vehicle_class, float(ratio_val), float(lap_time), s_type):
                        points_added += 1
                except (ValueError, TypeError) as e:
                    logger.error(f"[MAIN] Failed to add data point: {e}")
            if points_added > 0:
                logger.info(f"[MAIN] Saved {points_added} new data points")
        
        # Update formulas from new data (database operations are thread-safe)
        if current_track_ref and current_vehicle_class_ref:
            if qual_ratio:
                self._update_formula_from_new_data(race_data, "qual")
            if race_ratio:
                self._update_formula_from_new_data(race_data, "race")
        
        self.root.after(0, lambda: self._reload_and_update())
        
        # Auto-ratio update if enabled - use thread-safe GUI updates
        if self.autoratio_enabled and aiw_path:
            logger.info("[MAIN] Auto-ratio is enabled, calculating new ratios")
            
            # Capture current values for use in closure
            last_qual = self.last_qual_ratio
            last_race = self.last_race_ratio
            
            if last_qual is not None:
                self.root.after(0, lambda: self._set_qual_previous_ratio(last_qual))
            
            if last_race is not None:
                self.root.after(0, lambda: self._set_race_previous_ratio(last_race))
            
            if user_qualifying_sec > 0:
                self.user_laptimes_manager.add_laptime(
                    current_track_ref, current_vehicle_class_ref, "qual",
                    user_qualifying_sec, last_qual
                )
                median_time = self.user_laptimes_manager.get_median_laptime_for_combo(
                    current_track_ref, current_vehicle_class_ref, "qual"
                )
                effective_time = median_time if median_time is not None else user_qualifying_sec
                
                new_qual_ratio_val = ratio_from_time(effective_time, DEFAULT_A_VALUE, self.qual_b)
                if new_qual_ratio_val and abs(new_qual_ratio_val - last_qual) > 0.000001:
                    clamped = clamp_ratio(new_qual_ratio_val, self.min_ratio, self.max_ratio)
                    ratio_adjusted = (clamped != new_qual_ratio_val)
                    
                    if update_aiw_ratio(aiw_path, "QualRatio", clamped, self.backup_dir):
                        self.root.after(0, lambda: self._update_qual_ratio(clamped))
                        self.root.after(0, lambda: self._enable_qual_revert())
                        
                        if ratio_adjusted:
                            self._show_warning_safe("QualRatio Adjusted",
                                f"The calculated QualRatio = {new_qual_ratio_val:.6f} was outside the allowed range "
                                f"({self.min_ratio:.3f} - {self.max_ratio:.3f}).\n\n"
                                f"The ratio has been clamped to {clamped:.6f}.")
            
            if user_best_lap_sec > 0:
                self.user_laptimes_manager.add_laptime(
                    current_track_ref, current_vehicle_class_ref, "race",
                    user_best_lap_sec, last_race
                )
                median_time = self.user_laptimes_manager.get_median_laptime_for_combo(
                    current_track_ref, current_vehicle_class_ref, "race"
                )
                effective_time = median_time if median_time is not None else user_best_lap_sec
                
                new_race_ratio_val = ratio_from_time(effective_time, DEFAULT_A_VALUE, self.race_b)
                if new_race_ratio_val and abs(new_race_ratio_val - last_race) > 0.000001:
                    clamped = clamp_ratio(new_race_ratio_val, self.min_ratio, self.max_ratio)
                    ratio_adjusted = (clamped != new_race_ratio_val)
                    
                    if update_aiw_ratio(aiw_path, "RaceRatio", clamped, self.backup_dir):
                        self.root.after(0, lambda: self._update_race_ratio(clamped))
                        self.root.after(0, lambda: self._enable_race_revert())
                        
                        if ratio_adjusted:
                            self._show_warning_safe("RaceRatio Adjusted",
                                f"The calculated RaceRatio = {new_race_ratio_val:.6f} was outside the allowed range "
                                f"({self.min_ratio:.3f} - {self.max_ratio:.3f}).\n\n"
                                f"The ratio has been clamped to {clamped:.6f}.")
        
        self.root.after(0, lambda: self._reload_and_update())
        
        qual_display = f"{self.last_qual_ratio:.6f}" if self.last_qual_ratio is not None else "N/A"
        race_display = f"{self.last_race_ratio:.6f}" if self.last_race_ratio is not None else "N/A"
        self._update_status_safe(f"Data processed: {track_name} - Qual: {qual_display} / Race: {race_display}")
    
    # Helper methods for thread-safe UI updates
    def _update_track(self, track_name):
        self.current_track = track_name
        self.track_label.config(text=track_name)
        self.root.title(f"GTR2 Dynamic AI - {track_name}")
    
    def _update_user_qualifying(self, time_sec):
        self.user_qualifying_sec = time_sec
    
    def _update_user_best_lap(self, time_sec):
        self.user_best_lap_sec = time_sec
    
    def _update_qual_read_ratio(self, ratio):
        self.qual_read_ratio = ratio
        if self.qual_panel:
            self.qual_panel.update_last_read_ratio(ratio)
    
    def _update_race_read_ratio(self, ratio):
        self.race_read_ratio = ratio
        if self.race_panel:
            self.race_panel.update_last_read_ratio(ratio)
    
    def _update_qual_ratio(self, ratio):
        self.last_qual_ratio = ratio
        if self.qual_panel:
            self.qual_panel.update_ratio(ratio)
    
    def _update_race_ratio(self, ratio):
        self.last_race_ratio = ratio
        if self.race_panel:
            self.race_panel.update_ratio(ratio)
    
    def _update_qual_best_ai(self, best):
        self.qual_best_ai = best
    
    def _update_qual_worst_ai(self, worst):
        self.qual_worst_ai = worst
    
    def _update_race_best_ai(self, best):
        self.race_best_ai = best
    
    def _update_race_worst_ai(self, worst):
        self.race_worst_ai = worst
    
    def _update_user_vehicle(self, vehicle):
        self.current_vehicle = vehicle
        self.current_vehicle_class = get_vehicle_class(vehicle, self.class_mapping)
        self.car_class_label.config(text=self.current_vehicle_class)
    
    def _set_qual_previous_ratio(self, ratio):
        if self.qual_panel:
            self.qual_panel.previous_ratio = ratio
    
    def _set_race_previous_ratio(self, ratio):
        if self.race_panel:
            self.race_panel.previous_ratio = ratio
    
    def _enable_qual_revert(self):
        if self.qual_panel:
            self.qual_panel.revert_btn.config(state=tk.NORMAL)
    
    def _enable_race_revert(self):
        if self.race_panel:
            self.race_panel.revert_btn.config(state=tk.NORMAL)
    
    def _reload_and_update(self):
        self.autopilot_manager.reload_formulas()
        self.update_formulas_from_autopilot()
        self.update_display()
    
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
                b = calculate_b_from_point(current_ratio, ai_time, a)
                b_values.append(b)
        
        if not b_values:
            return False
        
        new_b = sum(b_values) / len(b_values)
        from core_math import clamp_b
        new_b = clamp_b(new_b)
        
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
                self.qual_formula_points = len(ai_times)
                self.qual_formula_confidence = 0.7 if len(ai_times) >= 2 else 0.5
            else:
                self.race_b = new_b
                self.race_formula_points = len(ai_times)
                self.race_formula_confidence = 0.7 if len(ai_times) >= 2 else 0.5
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
            self.qual_panel.update_accuracy(
                self.qual_formula_confidence,
                self.qual_formula_points,
                self.qual_formula_avg_error
            )
        
        if self.race_panel:
            self.race_panel.update_ratio(self.last_race_ratio)
            self.race_panel.update_ai_range(self.race_best_ai, self.race_worst_ai)
            self.race_panel.update_user_time(self.user_best_lap_sec if self.user_best_lap_sec > 0 else None)
            self.race_panel.update_formula(self.race_a, self.race_b)
            if self.race_read_ratio is not None:
                self.race_panel.update_last_read_ratio(self.race_read_ratio)
            self.race_panel.update_accuracy(
                self.race_formula_confidence,
                self.race_formula_points,
                self.race_formula_avg_error
            )
    
    def _disable_buttons(self):
        """Disable both Setup and Graph buttons when one is open"""
        if hasattr(self, 'setup_btn'):
            self.setup_btn.config(state=tk.DISABLED, text="Loading...")
        if hasattr(self, 'graph_btn'):
            self.graph_btn.config(state=tk.DISABLED, text="Loading...")
        self.root.update_idletasks()
    
    def _enable_buttons(self):
        """Re-enable Setup and Graph buttons after closing"""
        if hasattr(self, 'setup_btn'):
            self.setup_btn.config(state=tk.NORMAL, text="Setup")
        if hasattr(self, 'graph_btn'):
            self.graph_btn.config(state=tk.NORMAL, text="Graph")
        self.root.update_idletasks()
    
    def on_setup_open(self):
        """Open the setup manager dialog"""
        if self.setup_launch_in_progress:
            return
        
        self.setup_launch_in_progress = True
        self._disable_buttons()
        
        def launch_thread():
            try:
                success = launch_setup_manager()
            except Exception as e:
                logger.error(f"Failed to launch setup manager: {e}")
            finally:
                self.root.after(0, self._on_setup_closed)
        
        threading.Thread(target=launch_thread, daemon=True).start()
    
    def _on_setup_closed(self):
        """Called when setup manager has closed"""
        self.setup_launch_in_progress = False
        self._enable_buttons()
    
    def on_graph_open(self):
        """Open the graph/visualizer window"""
        if self.graph_launch_in_progress:
            return
        
        self.graph_launch_in_progress = True
        self._disable_buttons()
        
        def launch_thread():
            try:
                if getattr(sys, 'frozen', False):
                    visualizer_path = Path(sys.executable).parent / "dyn_ai_visualizer.exe"
                    if not visualizer_path.exists():
                        visualizer_path = Path(sys.executable).parent / "DYN_AI_VISUALIZER.EXE"
                else:
                    visualizer_path = Path(__file__).parent / "dyn_ai_visualizer.py"
                
                if visualizer_path.exists():
                    if getattr(sys, 'frozen', False):
                        subprocess.Popen([str(visualizer_path)], shell=False)
                    else:
                        python_exe = sys.executable
                        subprocess.Popen([python_exe, str(visualizer_path)], shell=False)
                else:
                    self._show_warning_safe("Visualizer Not Found", 
                        f"Visualizer not found at:\n{visualizer_path}")
            except Exception as e:
                logger.error(f"Failed to launch visualizer: {e}")
                self._show_warning_safe("Launch Error", f"Failed to launch visualizer:\n{str(e)}")
            finally:
                self.root.after(0, self._on_graph_closed)
        
        threading.Thread(target=launch_thread, daemon=True).start()
    
    def _on_graph_closed(self):
        """Called when graph window has closed"""
        self.graph_launch_in_progress = False
        self._enable_buttons()

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
