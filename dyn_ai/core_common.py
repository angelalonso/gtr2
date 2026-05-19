#!/usr/bin/env python3
"""
Shared functional components and utilities for Dynamic AI
Provides common functions
"""

import sys
import os
import logging
from pathlib import Path


def resource_path(relative_path: str) -> Path:
    """Get absolute path to resource, works for dev and for PyInstaller"""
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    
    return Path(base_path) / relative_path

def get_data_file_path(filename: str) -> Path:
    """Get path to a data file (cfg.yml, vehicle_classes.json, etc.)"""
    # First check the executable's directory (for user-editable files)
    if getattr(sys, 'frozen', False):
        exe_dir = Path(sys.executable).parent
        exe_path = exe_dir / filename
        if exe_path.exists():
            return exe_path
    
    # Then check PyInstaller's _MEIPASS (for bundled files)
    meipass_path = resource_path(filename)
    if meipass_path.exists():
        return meipass_path
    
    # Finally check current working directory (for development)
    cwd_path = Path.cwd() / filename
    if cwd_path.exists():
        return cwd_path
    
    # Return the executable directory as default (will try to create there)
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).parent / filename
    return Path.cwd() / filename


class SimpleLogHandler(logging.Handler):
    def __init__(self, log_window):
        super().__init__()
        self.log_window = log_window
    
    def emit(self, record):
        try:
            level = record.levelname
            message = self.format(record)
            if self.log_window:
                self.log_window.add_log(level, message)
        except Exception:
            pass



