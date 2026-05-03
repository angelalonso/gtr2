#!/usr/bin/env python3
"""
Live AI Tuner - Lightweight entry point
"""

import sys
import argparse
from pathlib import Path
from PyQt5.QtWidgets import QApplication

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from gui import MainWindow, apply_dark_theme
from core.database import DatabaseManager


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Live AI Tuner - Lightweight')
    parser.add_argument('--config', default='cfg.yml', help='Config file path')
    parser.add_argument('--no-gui', action='store_true', help='Run in console mode')
    args = parser.parse_args()
    
    # Check database
    from core.config import ConfigManager
    config = ConfigManager()
    config.load(args.config)
    db_path = config.get_db_path()
    
    if not Path(db_path).exists():
        print(f"Database '{db_path}' does not exist.")
        response = input("Create empty database? (y/n): ").lower().strip()
        if response == 'y':
            DatabaseManager(db_path)
            print(f"Created empty database: {db_path}")
        else:
            print("Exiting.")
            return
    
    if args.no_gui:
        print("Console mode not yet implemented")
        return
    
    app = QApplication(sys.argv)
    apply_dark_theme(app)
    
    window = MainWindow(args.config)
    window.show()
    
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
