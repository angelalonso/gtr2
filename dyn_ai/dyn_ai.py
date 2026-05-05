#!/usr/bin/env python3
"""
Dynamic AI - Main Entry Point
Redesigned GUI matching the reference image layout
"""

import sys
import logging
from pathlib import Path

from PyQt5.QtWidgets import QDialog, QApplication

from gui_pre_run_check import PreRunCheckDialog
from gui_common import setup_dark_theme
from core_config import get_config_with_defaults, get_db_path, create_default_config_if_missing
from core_database import CurveDatabase
from gui_main_window import RedesignedMainWindow


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
    
    app = QApplication(sys.argv)
    setup_dark_theme(app)
    
    check_dialog = PreRunCheckDialog("cfg.yml")
    if check_dialog.exec_() != QDialog.Accepted:
        print("Pre-run checks failed or cancelled. Exiting.")
        sys.exit(1)
    
    window = RedesignedMainWindow(db_path)
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
