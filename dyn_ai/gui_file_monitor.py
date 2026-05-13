#!/usr/bin/env python3
"""
File monitoring daemon for raceresults.txt
Checks for changes every N seconds and processes race data
"""

import threading
import logging
from pathlib import Path
from typing import Optional, Callable

from core_config import get_results_file_path, get_poll_interval, get_config_with_defaults
from core_data_extraction import DataExtractor, RaceData

logger = logging.getLogger(__name__)


class SimplifiedLogger:
    """Helper class to generate simplified, human-readable log messages"""
    
    @staticmethod
    def new_data_detected(track, vehicle_class, session_type, ratio, lap_time):
        return f"New data received for Track {track}, {session_type} session, car class {vehicle_class}"
    
    @staticmethod
    def new_ratio_calculation(old_ratio, new_ratio, ratio_name, user_lap_time, ratio_value):
        return f"New Ratio calculated for {ratio_name} session: {new_ratio:.6f} because user laptime was {user_lap_time} at Ratio {ratio_value:.6f}"
    
    @staticmethod
    def autosave_status(enabled):
        return f"Auto-harvest Data {'ON' if enabled else 'OFF'}"
    
    @staticmethod
    def autoratio_status(enabled):
        return f"Auto-calculate Ratios {'ON' if enabled else 'OFF'}"


class FileMonitorDaemon:
    """Daemon that monitors a file for changes - works with both PyQt and tkinter"""
    
    def __init__(self, file_path: Path, base_path: Path, poll_interval: float = 5.0, callback: Optional[Callable] = None):
        self.file_path = file_path
        self.base_path = base_path
        self.poll_interval = poll_interval
        self.running = False
        self.last_mtime = None
        self.last_size = None
        self.timer = None
        self.callback = callback
        self.extractor = DataExtractor(base_path)
        logger.info(f"[MONITOR] Initialized: watching {file_path}")
        
    def start(self):
        if not self.file_path.exists():
            logger.warning(f"[MONITOR] File does not exist yet: {self.file_path}")
            self.file_path.parent.mkdir(parents=True, exist_ok=True)
        
        self._update_file_state()
        self.running = True
        self._schedule_check()
        logger.info(f"[MONITOR] Started monitoring: {self.file_path}")
        
    def stop(self):
        self.running = False
        if self.timer:
            self.timer.cancel()
        logger.info("[MONITOR] Stopped monitoring")
    
    def _schedule_check(self):
        if self.running:
            self.timer = threading.Timer(self.poll_interval, self._check_file)
            self.timer.daemon = True
            self.timer.start()
    
    def _update_file_state(self):
        try:
            if self.file_path.exists():
                stat = self.file_path.stat()
                self.last_mtime = stat.st_mtime
                self.last_size = stat.st_size
                logger.debug(f"[MONITOR] Initial state: mtime={self.last_mtime}, size={self.last_size}")
        except Exception:
            pass
    
    def _check_file(self):
        try:
            if not self.running:
                return
            
            if not self.file_path.exists():
                logger.debug(f"[MONITOR] File not found: {self.file_path}")
                self._schedule_check()
                return
            
            try:
                stat = self.file_path.stat()
                current_mtime = stat.st_mtime
                current_size = stat.st_size
            except OSError as e:
                logger.error(f"[MONITOR] OSError reading file stats: {e}")
                self._schedule_check()
                return
            
            changed = (
                self.last_mtime is None
                or current_mtime != self.last_mtime
                or current_size != self.last_size
            )
            
            if changed:
                logger.info(f"[MONITOR] FILE CHANGE DETECTED! mtime: {self.last_mtime} -> {current_mtime}, size: {self.last_size} -> {current_size}")
                
                race_data = self.extractor.parse_race_results(self.file_path)
                if race_data and race_data.has_data():
                    logger.info(f"[MONITOR] Race data parsed successfully: track={race_data.track_name}")
                    if self.callback:
                        logger.info(f"[MONITOR] Calling callback with race data")
                        self.callback(race_data)
                else:
                    logger.warning(f"[MONITOR] No valid race data extracted from file")
                
                self.last_mtime = current_mtime
                self.last_size = current_size
            else:
                logger.debug(f"[MONITOR] No change detected")
            
        except Exception as e:
            logger.error(f"[MONITOR] Error checking file: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self._schedule_check()
