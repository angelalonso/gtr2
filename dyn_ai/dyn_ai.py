#!/usr/bin/env python3
"""
Dyn AI - Main Entry Point
"""

import sys
import logging
from pathlib import Path
from tkinter import messagebox

from gui_pre_run_check import run_pre_run_check
from gui_main_window import MainWindowTk
from core_config import get_config_with_defaults, get_db_path, create_default_config_if_missing
from core_database import CurveDatabase
from core_log_manager import setup_rotating_logging


# Set up rotating logging before anything else
rotating_handler = setup_rotating_logging(log_level=logging.INFO)
logger = logging.getLogger(__name__)

logger.info("=" * 60)
logger.info("Dynamic AI Starting")
logger.info("=" * 60)


def main():
    config = get_config_with_defaults()
    create_default_config_if_missing()
    db_path = get_db_path()
    
    if not Path(db_path).exists():
        create_new_db = messagebox.askyesno("No DB found", f"Database '{db_path}' does not exist.\nCreate empty database?")
        if create_new_db:
            CurveDatabase(db_path)
            messagebox.showinfo("Success", f"Created empty database: {db_path}")
        else:
            messagebox.showerror("Error", "Failed to start without a DB")
            return

    # Log the current log file location
    current_log = rotating_handler.get_current_log_path()
    if current_log:
        logger.info(f"Log file: {current_log}")

    # Run lightweight pre-run check (returns True if checks passed)
    # Pass accept_enter=True to enable Enter key to continue
    if not run_pre_run_check("cfg.yml", accept_enter=True):
        logger.info("Pre-run checks failed or cancelled. Exiting.")
        sys.exit(1)
    
    # Create and run tkinter main window
    window = MainWindowTk("cfg.yml")
    window.run()


if __name__ == "__main__":
    main()
