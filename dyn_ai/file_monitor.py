"""
File monitor for raceresults.txt - OPTIMIZED with timer-based polling
"""

import time
import logging
import threading
from pathlib import Path
from datetime import datetime

from results_parser import parse_race_results

logger = logging.getLogger(__name__)


class FileMonitor:
    """Main file monitor class - uses timer-based polling instead of watchdog"""
    
    def __init__(self, watch_folder: Path, target_file: Path, base_path: Path, 
                 callback=None, console_mode=False):
        self.watch_folder = Path(watch_folder)
        self.target_file = Path(target_file)
        self.base_path = Path(base_path) if base_path else None
        self.console_mode = console_mode
        self.callback = callback
        self.running = False
        self.timer = None
        self.poll_interval = 5.0  # Check every 5 seconds
        self.last_mtime = None
        self.last_size = None
        self.lock = threading.Lock()
        self.last_analysis_time = 0
        
    def start(self) -> bool:
        """Start monitoring with timer-based polling"""
        if not self.watch_folder.exists():
            logger.info(f"Creating watch folder: {self.watch_folder}")
            self.watch_folder.mkdir(parents=True, exist_ok=True)
        
        # Ensure target file directory exists
        self.target_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Record initial file state
        self._update_file_state()
        
        self.running = True
        self._schedule_check()
        
        logger.info(f"Started monitoring (polling every {self.poll_interval}s): {self.target_file}")
        
        return True
    
    def stop(self):
        """Stop monitoring"""
        self.running = False
        if self.timer:
            self.timer.cancel()
        logger.info("Stopped monitoring")
    
    def _schedule_check(self):
        """Schedule the next file check"""
        if self.running:
            self.timer = threading.Timer(self.poll_interval, self._check_file)
            self.timer.daemon = True
            self.timer.start()
    
    def _check_file(self):
        """Check if the target file has changed"""
        try:
            if not self.running:
                return
            
            # Check if file exists
            if not self.target_file.exists():
                # File doesn't exist, just reschedule
                self._schedule_check()
                return
            
            # Get current file stats
            try:
                stat = self.target_file.stat()
                current_mtime = stat.st_mtime
                current_size = stat.st_size
            except OSError:
                # File might be locked or inaccessible, skip this check
                self._schedule_check()
                return
            
            # Check if file has changed
            changed = False
            if self.last_mtime is None:
                # First check
                changed = True
            elif current_mtime != self.last_mtime or current_size != self.last_size:
                changed = True
            
            # Update stored state
            self.last_mtime = current_mtime
            self.last_size = current_size
            
            # Analyze if changed
            if changed:
                self._analyze_file()
            
        except Exception as e:
            logger.error(f"Error checking file: {e}")
        finally:
            # Always schedule next check
            self._schedule_check()
    
    def _analyze_file(self):
        """Analyze the race results file with debouncing"""
        with self.lock:
            current_time = time.time()
            # Debounce: wait at least 2 seconds between analyses
            if current_time - self.last_analysis_time < 2.0:
                logger.debug("Skipping analysis (too soon)")
                return
            
            logger.info(f"File changed, analyzing: {self.target_file}")
            self.last_analysis_time = current_time
            
            try:
                # Parse the results
                results = parse_race_results(self.target_file, self.base_path)
                
                if results and results.has_data():
                    if self.callback:
                        self.callback(results.to_dict())
                    elif self.console_mode:
                        self._print_results(results)
                else:
                    logger.info("No valid race data found in file")
                    
            except Exception as e:
                logger.error(f"Error analyzing results: {e}", exc_info=True)
    
    def _update_file_state(self):
        """Update the stored file state"""
        try:
            if self.target_file.exists():
                stat = self.target_file.stat()
                self.last_mtime = stat.st_mtime
                self.last_size = stat.st_size
        except Exception:
            pass
    
    def _print_results(self, results):
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
