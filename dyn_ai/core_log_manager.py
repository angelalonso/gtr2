#!/usr/bin/env python3
"""
Log manager for Dynamic AI
Handles rotating log files and provides access for log viewers
"""

import os
import logging
import threading
import time
from pathlib import Path
from typing import Optional, List
from datetime import datetime


class RotatingLogHandler(logging.Handler):
    """
    Logging handler that writes to a rotating log file.
    Keeps only the current and previous log files.
    """
    
    def __init__(self, log_dir: Path = None, max_log_files: int = 2):
        """
        Initialize the rotating log handler.
        
        Args:
            log_dir: Directory to store log files (default: ./logs)
            max_log_files: Maximum number of log files to keep (default: 2)
        """
        super().__init__()
        
        self.max_log_files = max_log_files
        
        if log_dir is None:
            log_dir = Path.cwd() / "logs"
        self.log_dir = Path(log_dir)
        
        # Create log directory if it doesn't exist
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Current log file path
        self.current_log_path: Optional[Path] = None
        self._lock = threading.Lock()
        
        # Clean up old logs immediately
        self._cleanup_old_logs()
        
        # Then start a new log session
        self.start_new_session()
    
    def _cleanup_old_logs(self):
        """
        Clean up old log files, keeping only the most recent max_log_files.
        This runs on startup and can be called at any time.
        """
        try:
            # Get all log files sorted by modification time (newest first)
            log_files = sorted(
                self.log_dir.glob("dyn_ai_*.log"),
                key=lambda p: p.stat().st_mtime,
                reverse=True
            )
            
            # Remove files beyond max_log_files
            removed_count = 0
            for i, log_file in enumerate(log_files):
                if i >= self.max_log_files:
                    try:
                        log_file.unlink()
                        removed_count += 1
                        # Also remove watch file if exists
                        watch_file = log_file.with_suffix(".watch")
                        if watch_file.exists():
                            watch_file.unlink()
                    except Exception as e:
                        pass
            
            if removed_count > 0:
                print(f"[LOG] Cleaned up {removed_count} old log file(s)")
                    
        except Exception as e:
            print(f"[LOG] Error during log cleanup: {e}")
    
    def start_new_session(self):
        """Start a new log session with a timestamped filename"""
        with self._lock:
            # Generate timestamp for this session
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
            self.current_log_path = self.log_dir / f"dyn_ai_{timestamp}.log"
            
            # Write the initial header
            self._write_header()
    
    def _write_header(self):
        """Write session header to the log file"""
        if self.current_log_path:
            with open(self.current_log_path, 'w', encoding='utf-8') as f:
                f.write("=" * 80 + "\n")
                f.write(f"Dynamic AI Log Session\n")
                f.write(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}\n")
                f.write("=" * 80 + "\n\n")
    
    def emit(self, record):
        """Emit a log record to the current log file"""
        try:
            msg = self.format(record)
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
            level = record.levelname
            formatted = f"[{timestamp}] [{level:7}] {msg}"
            
            with self._lock:
                if self.current_log_path:
                    with open(self.current_log_path, 'a', encoding='utf-8') as f:
                        f.write(formatted + "\n")
        except Exception:
            self.handleError(record)
    
    def get_current_log_path(self) -> Optional[Path]:
        """Get the path to the current log file"""
        return self.current_log_path
    
    def get_log_files(self) -> List[Path]:
        """Get all log files sorted by modification time (newest first)"""
        log_files = list(self.log_dir.glob("dyn_ai_*.log"))
        return sorted(log_files, key=lambda p: p.stat().st_mtime, reverse=True)


class LogReader:
    """
    Reader for rotating log files that can be used by the log viewer.
    Supports real-time reading of the current log file.
    """
    
    def __init__(self, log_dir: Path = None):
        """
        Initialize the log reader.
        
        Args:
            log_dir: Directory where log files are stored (default: ./logs)
        """
        if log_dir is None:
            log_dir = Path.cwd() / "logs"
        self.log_dir = Path(log_dir)
        self._current_position = 0
        self._current_log_path: Optional[Path] = None
        self._last_cleanup_time = 0
        self._cleanup_interval = 30  # Clean up every 30 seconds
    
    def _cleanup_if_needed(self):
        """Clean up old log files periodically"""
        current_time = time.time()
        if current_time - self._last_cleanup_time > self._cleanup_interval:
            self._last_cleanup_time = current_time
            self._cleanup_old_logs()
    
    def _cleanup_old_logs(self):
        """Clean up old log files, keeping only the 2 most recent"""
        if not self.log_dir.exists():
            return
        
        try:
            # Get all log files sorted by modification time (newest first)
            log_files = sorted(
                self.log_dir.glob("dyn_ai_*.log"),
                key=lambda p: p.stat().st_mtime,
                reverse=True
            )
            
            # Keep only the 2 most recent
            removed_count = 0
            for i, log_file in enumerate(log_files):
                if i >= 2:
                    try:
                        log_file.unlink()
                        removed_count += 1
                    except Exception:
                        pass
            
            if removed_count > 0:
                pass  # Silent cleanup
        except Exception:
            pass
    
    def get_current_log_file(self) -> Optional[Path]:
        """
        Get the most recent log file (the one currently being written to).
        
        Returns:
            Path to the current log file, or None if no log files exist
        """
        self._cleanup_if_needed()
        
        if not self.log_dir.exists():
            return None
        
        log_files = list(self.log_dir.glob("dyn_ai_*.log"))
        if not log_files:
            return None
        
        # Return the most recently modified log file
        return max(log_files, key=lambda p: p.stat().st_mtime)
    
    def get_all_log_files(self) -> List[Path]:
        """Get all log files sorted by modification time (newest first)"""
        self._cleanup_if_needed()
        
        if not self.log_dir.exists():
            return []
        
        log_files = list(self.log_dir.glob("dyn_ai_*.log"))
        return sorted(log_files, key=lambda p: p.stat().st_mtime, reverse=True)
    
    def get_current_log_content(self) -> str:
        """
        Read the content of the current log file.
        
        Returns:
            The content of the log file as a string
        """
        current_log = self.get_current_log_file()
        if not current_log or not current_log.exists():
            return "No log file available yet."
        
        try:
            with open(current_log, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            return f"Error reading log file: {e}"
    
    def read_new_lines(self) -> List[str]:
        """
        Read only new lines from the current log file since the last read.
        
        Returns:
            List of new lines
        """
        current_log = self.get_current_log_file()
        
        # If the log file has changed (new session started), reset position
        if current_log != self._current_log_path:
            self._current_log_path = current_log
            self._current_position = 0
        
        if not current_log or not current_log.exists():
            return []
        
        try:
            with open(current_log, 'r', encoding='utf-8') as f:
                f.seek(self._current_position)
                new_lines = f.readlines()
                self._current_position = f.tell()
                return [line.rstrip('\n') for line in new_lines]
        except Exception:
            return []
    
    def reset_position(self):
        """Reset the read position to the beginning of the file"""
        self._current_position = 0


# Global handler instance for access
_global_handler: Optional[RotatingLogHandler] = None


def setup_rotating_logging(log_dir: Path = None, max_log_files: int = 2, 
                           log_level: int = logging.INFO) -> RotatingLogHandler:
    """
    Set up rotating logging for the application.
    
    Args:
        log_dir: Directory to store log files (default: ./logs)
        max_log_files: Maximum number of log files to keep (default: 2)
        log_level: Logging level (default: logging.INFO)
    
    Returns:
        The RotatingLogHandler instance
    """
    global _global_handler
    
    # Remove any existing file handlers to avoid duplicates
    root_logger = logging.getLogger()
    handlers_to_remove = []
    for handler in root_logger.handlers:
        if isinstance(handler, RotatingLogHandler):
            handlers_to_remove.append(handler)
        elif isinstance(handler, logging.FileHandler):
            handlers_to_remove.append(handler)
    
    for handler in handlers_to_remove:
        root_logger.removeHandler(handler)
    
    # Set root logger level
    root_logger.setLevel(log_level)
    
    # Create the rotating log handler
    _global_handler = RotatingLogHandler(log_dir, max_log_files)
    _global_handler.setLevel(log_level)
    _global_handler.setFormatter(logging.Formatter('%(message)s'))
    
    # Add the rotating handler
    root_logger.addHandler(_global_handler)
    
    # Always add console handler for visibility
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    root_logger.addHandler(console_handler)
    
    # Log a test message
    logger = logging.getLogger(__name__)
    logger.info("=" * 60)
    logger.info("Logging system initialized")
    logger.info(f"Log directory: {_global_handler.log_dir}")
    logger.info(f"Current log file: {_global_handler.current_log_path}")
    logger.info("=" * 60)
    
    return _global_handler


def get_log_reader() -> LogReader:
    """Get a LogReader instance for the default log directory"""
    return LogReader()


def cleanup_old_logs():
    """Public function to manually clean up old logs"""
    if _global_handler:
        _global_handler._cleanup_old_logs()
    else:
        log_dir = Path.cwd() / "logs"
        if log_dir.exists():
            log_files = sorted(
                log_dir.glob("dyn_ai_*.log"),
                key=lambda p: p.stat().st_mtime,
                reverse=True
            )
            for i, log_file in enumerate(log_files):
                if i >= 2:
                    try:
                        log_file.unlink()
                    except Exception:
                        pass
