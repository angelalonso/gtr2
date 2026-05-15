#!/usr/bin/env python3
"""
Dyn AI - Main Entry Point
"""

import sys
import logging
from pathlib import Path

from gui_pre_run_check_light import run_pre_run_check
from gui_main_window_tk import MainWindowTk
from core_config import get_config_with_defaults, get_db_path, create_default_config_if_missing
from core_database import CurveDatabase


logger = logging.getLogger(__name__)


def main():
    config = get_config_with_defaults()
    create_default_config_if_missing()
    db_path = get_db_path()
    
    if not Path(db_path).exists():
        print(f"\nDatabase '{db_path}' does not exist.")
        response = input("Create empty database? (y/n): ").lower().strip()
        if response == 'y':
            CurveDatabase(db_path)
            print(f"Created empty database: {db_path}\n")
        else:
            print("\nExiting.\n")
            return
    
    # Run lightweight pre-run check (returns True if checks passed)
    # Pass accept_enter=True to enable Enter key to continue
    if not run_pre_run_check("cfg.yml", accept_enter=True):
        print("Pre-run checks failed or cancelled. Exiting.")
        sys.exit(1)
    
    # Create and run tkinter main window
    window = MainWindowTk("cfg.yml")
    window.run()


if __name__ == "__main__":
    main()
