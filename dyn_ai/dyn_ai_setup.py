#!/usr/bin/env python3
"""
Dynamic AI - Setup & Data Manager (Standalone)
Handles configuration, backup restore, logs, and data management
Runs its own pre-run checks before starting
"""

import sys
import logging
import sqlite3
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from pathlib import Path
from typing import List, Tuple

from core_config import get_config_with_defaults, get_db_path, create_default_config_if_missing
from core_database import CurveDatabase
from core_log_manager import setup_rotating_logging


# Set up rotating logging before anything else
rotating_handler = setup_rotating_logging(log_level=logging.INFO)
logger = logging.getLogger(__name__)

logger.info("=" * 60)
logger.info("Dynamic AI Setup Manager Starting")
logger.info("=" * 60)


class SetupManager(tk.Tk):
    """Setup and Data Management window using tkinter"""
    
    def __init__(self, config_file: str = "cfg.yml"):
        super().__init__()
        self.config_file = config_file
        self.config = get_config_with_defaults(config_file)
        self.db_path = get_db_path(config_file)
        self.db = CurveDatabase(self.db_path)
        
        self.config_tab = None
        self.vehicle_tab = None
        
        self.setup_ui()
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def on_closing(self):
        """Handle window close event"""
        logger.info("Setup Manager closing")
        self.destroy()
        self.quit()
    
    def on_config_changed(self):
        """Called when configuration is saved in the Config tab"""
        logger.info("Configuration changed, notifying other tabs")
        # Reload config from file
        self.config = get_config_with_defaults(self.config_file)
        # Notify vehicle tab if it exists and has the method
        if self.vehicle_tab and hasattr(self.vehicle_tab, 'on_config_changed'):
            self.vehicle_tab.on_config_changed()
    
    def setup_ui(self):
        self.title("Dynamic AI - Setup & Data Manager")
        self.geometry("1200x850")
        self.minsize(1200, 600)
        self.configure(bg='#1e1e1e')
        
        # Notebook (tabbed interface)
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Configuration tab
        self.config_tab = self.create_config_tab()
        self.notebook.add(self.config_tab, text="Configuration")
        
        # Laptimes and Ratios tab (from data manager)
        self.laptimes_tab = self.create_laptimes_tab()
        self.notebook.add(self.laptimes_tab, text="Laptimes and Ratios")
        
        # Vehicle Classes tab (from data manager)
        self.vehicle_tab = self.create_vehicle_tab()
        self.notebook.add(self.vehicle_tab, text="Vehicle Classes")
        
        # Race Data Import tab (from data manager)
        self.import_tab = self.create_import_tab()
        self.notebook.add(self.import_tab, text="Race Data Import")
        
        # Backup Restore tab
        self.backup_tab = self.create_backup_tab()
        self.notebook.add(self.backup_tab, text="Backup Restore")
        
        # Logs tab
        self.logs_tab = self.create_logs_tab()
        self.notebook.add(self.logs_tab, text="Logs")
        
        # Exit button
        exit_btn = tk.Button(self, text="Exit", bg='#d20a0a', fg='white',
                              font=('Arial', 11, 'bold'), relief=tk.FLAT, padx=24, pady=8,
                              command=self.on_closing)
        exit_btn.pack(side=tk.RIGHT, padx=5)
    
    def create_laptimes_tab(self) -> tk.Frame:
        """Create the Laptimes and Ratios tab (from Data Manager)"""
        from gui_datamgmt_laptimes import LaptimesTab
        return LaptimesTab(self, self.db_path)
    
    def create_vehicle_tab(self) -> tk.Frame:
        """Create the Vehicle Classes tab (from Data Manager)"""
        from gui_datamgmt_vehicle import VehicleTab
        return VehicleTab(self)
    
    def create_import_tab(self) -> tk.Frame:
        """Create the Race Data Import tab (from Data Manager)"""
        from gui_datamgmt_import import ImportTab
        return ImportTab(self, self.db_path)
    
    def create_config_tab(self) -> tk.Frame:
        """Create the configuration tab"""
        from gui_setup_cfg import ConfigTab
        # Pass self as parent so ConfigTab can call back to us
        return ConfigTab(self, self.config_file, self.db)
    
    def create_backup_tab(self) -> tk.Frame:
        """Create the backup restore tab"""
        from gui_setup_backup import BackupTab
        return BackupTab(self, self.db)
    
    def create_logs_tab(self) -> tk.Frame:
        """Create the logs tab"""
        from gui_setup_logs import LogsTab
        return LogsTab(self)
    
    def run(self):
        logger.info("Setup Manager UI started")
        self.mainloop()


def main():
    # Ensure config and database exist
    create_default_config_if_missing()
    db_path = get_db_path()
    if not Path(db_path).exists():
        CurveDatabase(db_path)
    
    # Log the current log file location
    current_log = rotating_handler.get_current_log_path()
    if current_log:
        logger.info(f"Log file: {current_log}")
    
    app = SetupManager()
    app.run()
    # Ensure the application exits completely after the window is closed
    sys.exit(0)


if __name__ == "__main__":
    main()
