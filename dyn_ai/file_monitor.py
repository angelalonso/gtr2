"""
File monitor for raceresults.txt - OPTIMIZED with timer-based polling
UPDATED: Saves parsed race results to SQLite via db_manager
UPDATED: Removed user data from database storage
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
                 callback=None, console_mode=False, db=None):
        """
        Parameters
        ----------
        db : db_manager.Database | None
            Optional Database instance.  When provided every detected race
            result is persisted automatically before the callback fires.
        """
        self.watch_folder = Path(watch_folder)
        self.target_file = Path(target_file)
        self.base_path = Path(base_path) if base_path else None
        self.console_mode = console_mode
        self.callback = callback
        self.db = db                        # ← SQLite handle (may be None)
        self.running = False
        self.timer = None
        self.poll_interval = 5.0
        self.last_mtime = None
        self.last_size = None
        self.lock = threading.Lock()
        self.last_analysis_time = 0
        
    def start(self) -> bool:
        """Start monitoring with timer-based polling"""
        if not self.watch_folder.exists():
            logger.info(f"Creating watch folder: {self.watch_folder}")
            self.watch_folder.mkdir(parents=True, exist_ok=True)
        
        self.target_file.parent.mkdir(parents=True, exist_ok=True)
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
        if self.running:
            self.timer = threading.Timer(self.poll_interval, self._check_file)
            self.timer.daemon = True
            self.timer.start()
    
    def _check_file(self):
        try:
            if not self.running:
                return
            
            if not self.target_file.exists():
                self._schedule_check()
                return
            
            try:
                stat = self.target_file.stat()
                current_mtime = stat.st_mtime
                current_size = stat.st_size
            except OSError:
                self._schedule_check()
                return
            
            changed = (
                self.last_mtime is None
                or current_mtime != self.last_mtime
                or current_size != self.last_size
            )
            
            self.last_mtime = current_mtime
            self.last_size = current_size
            
            if changed:
                self._analyze_file()
                
        except Exception as e:
            logger.error(f"Error checking file: {e}")
        finally:
            self._schedule_check()
    
    def _analyze_file(self):
        """Parse the results file and optionally persist to SQLite."""
        with self.lock:
            current_time = time.time()
            if current_time - self.last_analysis_time < 2.0:
                logger.debug("Skipping analysis (too soon)")
                return
            
            logger.info(f"File changed, analyzing: {self.target_file}")
            self.last_analysis_time = current_time
            
            try:
                results = parse_race_results(self.target_file, self.base_path)
                
                if results and results.has_data():
                    data = results.to_dict()

                    # ── Persist to SQLite (NO USER DATA) ─────────────────────────
                    if self.db is not None:
                        try:
                            # Create a copy without user data for DB storage
                            db_data = {
                                "track_name": data.get("track_name"),
                                "track_folder": data.get("track_folder"),
                                "aiw_file": data.get("aiw_file"),
                                "qual_ratio": data.get("qual_ratio"),
                                "race_ratio": data.get("race_ratio"),
                                "ai_results": data.get("ai_results", []),
                            }
                            session_id = self.db.save_race_session(db_data)
                            if session_id:
                                data['session_id'] = session_id
                                logger.info(f"Race session saved to DB (id={session_id})")
                        except Exception as db_err:
                            logger.error(f"DB save failed (non-fatal): {db_err}")
                    # ─────────────────────────────────────────────────────────────

                    if self.callback:
                        self.callback(data)
                    elif self.console_mode:
                        self._print_results(results)
                else:
                    logger.info("No valid race data found in file")
                    
            except Exception as e:
                logger.error(f"Error analyzing results: {e}", exc_info=True)
    
    def _update_file_state(self):
        try:
            if self.target_file.exists():
                stat = self.target_file.stat()
                self.last_mtime = stat.st_mtime
                self.last_size = stat.st_size
        except Exception:
            pass
    
    def _print_results(self, results):
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
