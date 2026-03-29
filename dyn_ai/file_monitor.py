"""
File monitor for raceresults.txt using watchdog
"""

import os
import time
import logging
import threading
from pathlib import Path
from datetime import datetime
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from results_parser import parse_race_results, RaceResults

logger = logging.getLogger(__name__)


class ResultsFileHandler(FileSystemEventHandler):
    """Handles file system events for raceresults.txt"""
    
    def __init__(self, target_file: Path, base_path: Path, callback, console_mode=False):
        super().__init__()
        self.target_file = Path(target_file)
        self.base_path = Path(base_path) if base_path else None
        self.callback = callback
        self.console_mode = console_mode
        self.last_analysis_time = 0
        self.pending_analysis = False
        self.file_states = {}
    
    def is_target_file(self, file_path):
        """Check if the given file is our target file"""
        try:
            return Path(file_path).resolve() == self.target_file.resolve()
        except Exception:
            return str(file_path) == str(self.target_file)
    
    def analyze_results(self, file_path):
        """Analyze the race results file"""
        try:
            # Debounce: ignore if analyzed recently (within 2 seconds)
            current_time = time.time()
            if current_time - self.last_analysis_time < 2.0:
                logger.debug("Skipping analysis (too soon)")
                return
            
            logger.info(f"Analyzing race results: {file_path}")
            self.last_analysis_time = current_time
            self.pending_analysis = False
            
            # Parse the results
            results = parse_race_results(file_path, self.base_path)
            
            if results and results.has_data():
                if self.callback:
                    self.callback(results.to_dict())
                elif self.console_mode:
                    self._print_results(results)
            else:
                logger.info("No valid race data found in file")
                
        except Exception as e:
            logger.error(f"Error analyzing results: {e}", exc_info=True)
    
    def _print_results(self, results: RaceResults):
        """Print results to console"""
        print("\n" + "=" * 60)
        print("RACE RESULTS DETECTED!")
        print("=" * 60)
        print(f"Track: {results.track_name}")
        print(f"AIW File: {results.aiw_file}")
        print(f"QualRatio: {results.qual_ratio:.6f}" if results.qual_ratio else "QualRatio: Not found")
        print(f"RaceRatio: {results.race_ratio:.6f}" if results.race_ratio else "RaceRatio: Not found")
        print("-" * 40)
        print("LAP TIMES:")
        print(f"  Best AI Lap: {results.best_ai_lap or 'N/A'}")
        print(f"  Worst AI Lap: {results.worst_ai_lap or 'N/A'}")
        print(f"  Best User Lap: {results.user_best_lap or 'N/A'}")
        print(f"  User Qualifying: {results.user_qualifying or 'N/A'}")
        print("=" * 60 + "\n")
    
    def schedule_analysis(self, file_path):
        """Schedule analysis with a delay"""
        if self.pending_analysis:
            return
        
        self.pending_analysis = True
        
        def delayed_analysis():
            time.sleep(1.0)  # Wait for file to be fully written
            self.analyze_results(file_path)
        
        thread = threading.Thread(target=delayed_analysis, daemon=True)
        thread.start()
        logger.info(f"Scheduled analysis for {file_path}")
    
    def on_modified(self, event):
        """Called when a file is modified"""
        if not event.is_directory and self.is_target_file(event.src_path):
            logger.info(f"Target file modified: {event.src_path}")
            self._check_file_change(Path(event.src_path))
    
    def on_created(self, event):
        """Called when a file is created"""
        if not event.is_directory and self.is_target_file(event.src_path):
            logger.info(f"Target file created: {event.src_path}")
            self._track_file(Path(event.src_path))
            self.schedule_analysis(Path(event.src_path))
    
    def _track_file(self, file_path):
        """Track initial state of a file"""
        try:
            if file_path.exists() and file_path.is_file():
                stat_info = file_path.stat()
                self.file_states[str(file_path)] = {
                    'size': stat_info.st_size,
                    'mtime': stat_info.st_mtime
                }
        except Exception as e:
            logger.error(f"Error tracking file {file_path}: {e}")
    
    def _check_file_change(self, file_path):
        """Check if file content has actually changed"""
        try:
            if not file_path.exists():
                return
            
            current_state = {
                'size': file_path.stat().st_size,
                'mtime': file_path.stat().st_mtime
            }
            
            previous_state = self.file_states.get(str(file_path))
            
            if previous_state is None:
                self.file_states[str(file_path)] = current_state
                self.schedule_analysis(file_path)
                return
            
            if (current_state['size'] != previous_state['size'] or 
                current_state['mtime'] != previous_state['mtime']):
                
                logger.info(f"File content changed: {file_path}")
                self.file_states[str(file_path)] = current_state
                self.schedule_analysis(file_path)
                
        except Exception as e:
            logger.error(f"Error checking file {file_path}: {e}")


class FileMonitor:
    """Main file monitor class"""
    
    def __init__(self, watch_folder: Path, target_file: Path, base_path: Path, 
                 callback=None, console_mode=False):
        self.watch_folder = Path(watch_folder)
        self.target_file = Path(target_file)
        self.base_path = Path(base_path) if base_path else None
        self.console_mode = console_mode
        self.callback = callback
        self.observer = Observer()
        self.event_handler = ResultsFileHandler(
            self.target_file, 
            self.base_path, 
            self.callback,
            self.console_mode
        )
    
    def start(self) -> bool:
        """Start monitoring"""
        if not self.watch_folder.exists():
            logger.info(f"Creating watch folder: {self.watch_folder}")
            self.watch_folder.mkdir(parents=True, exist_ok=True)
        
        # Ensure target file directory exists
        self.target_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Schedule monitoring
        self.observer.schedule(
            self.event_handler,
            str(self.watch_folder),
            recursive=True
        )
        self.observer.start()
        
        # Track existing file
        if self.target_file.exists():
            self.event_handler._track_file(self.target_file)
        
        logger.info(f"Started monitoring: {self.watch_folder}")
        logger.info(f"Target file: {self.target_file}")
        
        return True
    
    def stop(self):
        """Stop monitoring"""
        self.observer.stop()
        self.observer.join()
        logger.info("Stopped monitoring")
