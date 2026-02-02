#!/usr/bin/env python3
# debug_logger.py - Debug logging utilities

from config import DEBUG

class DebugLogger:
    """Handles debug output with various levels of detail"""
    
    def __init__(self, debug_mode=None):
        self.debug_mode = debug_mode if debug_mode is not None else DEBUG
    
    def log(self, message, level="INFO", details=None):
        """Log a message with optional details"""
        icon = self._get_icon(level)
        print(f"{icon} {message}")
        
        if self.debug_mode and details:
            if isinstance(details, list):
                for detail in details:
                    print(f"    {detail}")
            else:
                print(f"    {details}")
    
    def section(self, title, width=60):
        """Print a section header"""
        print(f"\n{'='*width}")
        print(f"📌 {title}")
        print(f"{'='*width}")
    
    def subsection(self, title):
        """Print a subsection header"""
        print(f"\n{'-'*40}")
        print(f"🔹 {title}")
        print(f"{'-'*40}")
    
    def progress(self, current, total, message):
        """Show progress information"""
        print(f"[{current}/{total}] {message}")
    
    def _get_icon(self, level):
        """Get icon for log level"""
        icons = {
            "INFO": "ℹ️",
            "SUCCESS": "✅",
            "WARNING": "⚠️",
            "ERROR": "❌",
            "DEBUG": "🐛",
            "SEARCH": "🔍",
            "FILE": "📄",
            "FOLDER": "📁",
            "DATA": "📊",
            "DRIVER": "👤",
        }
        return icons.get(level, "➡️")
    
    def debug(self, message, details=None):
        """Debug-level logging (only shown when debug_mode is True)"""
        if self.debug_mode:
            self.log(message, "DEBUG", details)
    
    def info(self, message, details=None):
        """Info-level logging"""
        self.log(message, "INFO", details)
    
    def success(self, message, details=None):
        """Success-level logging"""
        self.log(message, "SUCCESS", details)
    
    def warning(self, message, details=None):
        """Warning-level logging"""
        self.log(message, "WARNING", details)
    
    def error(self, message, details=None):
        """Error-level logging"""
        self.log(message, "ERROR", details)

# Global logger instance
logger = DebugLogger()
