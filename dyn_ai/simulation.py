#!/usr/bin/env python3
"""
Test Harness for Dyn AI
Launches the application with test configuration and simulates game behavior
UPDATED: Works with test_mocks/ directory and restores ALL modified files

WORKFLOW (per mock result file):
  1. Parse ratios from filename (qr / rr values)
  2. Parse track name + AIW filename from the mock result content
  3. Find the actual AIW file under test_mocks/GameData/Locations
  4. Backup the AIW (once per unique AIW path)
  5. Backup raceresults.txt (once, at the start)
  6. Backup the real cfg.yml and database before starting
  7. Patch the AIW with the ratios from the filename
  8. Copy the mock result content to the live raceresults.txt
  9. Let the main program detect and process the change
  10. On finish / interrupt / error → restore everything (AIWs, raceresults.txt, cfg.yml, database)
"""

import os
import sys
import time
import yaml
import subprocess
import logging
import shutil
import threading
import queue
import re
import hashlib
import sqlite3
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List, Tuple

# Configure logging with TEST_HARNESS tag
logging.basicConfig(
    level=logging.INFO,
    format='[TEST_HARNESS] %(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class LiveAITunerTestHarness:
    """Test harness for Live AI Tuner using real race results files"""

    def __init__(self, test_dir: str = "./test_mocks"):
        self.test_dir = Path(test_dir).absolute()
        self.project_dir = Path(__file__).parent.absolute()
        
        # Paths in the project directory (real files that will be modified)
        self.real_cfg_path = self.project_dir / "cfg.yml"
        self.real_db_path = self.project_dir / "ai_data.db"
        
        # Paths in test_mocks directory (mock files)
        self.user_data_dir = self.test_dir / "UserData"
        self.log_results_dir = self.user_data_dir / "Log" / "Results"
        self.target_results_file = self.log_results_dir / "raceresults.txt"
        self.test_config_path = self.test_dir / "cfg_test.yml"
        
        # Directory containing generated race results
        self.mock_results_dir = self.test_dir / "mock_raceresults"
        
        # Backup directory for ALL modified files
        self.harness_backup_dir = self.test_dir / "harness_backups"
        self.harness_backup_dir.mkdir(parents=True, exist_ok=True)
        
        # Track backup paths
        self.backup_results_file = self.harness_backup_dir / "original_raceresults_backup.txt"
        self.backup_cfg_file = self.harness_backup_dir / "original_cfg_backup.yml"
        self.backup_db_file = self.harness_backup_dir / "original_ai_data_backup.db"
        
        # AIW backup tracking: maps str(aiw_path) -> Path of backup copy
        self._aiw_backups: Dict[str, Path] = {}
        
        # Track which AIW files we've modified
        self._modified_aiw_files: set = set()
        
        # Create necessary directories
        self.log_results_dir.mkdir(parents=True, exist_ok=True)
        
        # Track information from existing data
        self.tracks = self._discover_tracks()
        
        # Process tracking
        self.app_process = None
        self.log_queue = queue.Queue()
        self.app_log_file = None

    # ------------------------------------------------------------------
    # Backup and restore for ALL modified files
    # ------------------------------------------------------------------

    def backup_real_files(self) -> bool:
        """Backup the real cfg.yml and database before starting"""
        logger.info("\n" + "=" * 60)
        logger.info("BACKING UP REAL FILES")
        logger.info("=" * 60)
        
        # Backup cfg.yml
        if self.real_cfg_path.exists():
            try:
                shutil.copy2(self.real_cfg_path, self.backup_cfg_file)
                logger.info(f"✓ Backed up cfg.yml → {self.backup_cfg_file.name}")
            except Exception as e:
                logger.error(f"✗ Failed to backup cfg.yml: {e}")
                return False
        else:
            logger.warning(f"cfg.yml not found at {self.real_cfg_path}, will create default")
        
        # Backup database
        if self.real_db_path.exists():
            try:
                shutil.copy2(self.real_db_path, self.backup_db_file)
                logger.info(f"✓ Backed up database → {self.backup_db_file.name}")
            except Exception as e:
                logger.error(f"✗ Failed to backup database: {e}")
                return False
        else:
            logger.info("Database doesn't exist yet, will be created by application")
        
        logger.info("=" * 60 + "\n")
        return True

    def restore_real_files(self) -> bool:
        """Restore the real cfg.yml and database from backups"""
        logger.info("\n" + "=" * 60)
        logger.info("RESTORING REAL FILES")
        logger.info("=" * 60)
        
        # Restore cfg.yml
        if self.backup_cfg_file.exists():
            try:
                shutil.copy2(self.backup_cfg_file, self.real_cfg_path)
                logger.info(f"✓ Restored cfg.yml from backup")
            except Exception as e:
                logger.error(f"✗ Failed to restore cfg.yml: {e}")
        elif self.real_cfg_path.exists():
            # If no backup but file exists, keep it (might be user's original)
            logger.info("No cfg.yml backup found, keeping existing file")
        
        # Restore database
        if self.backup_db_file.exists():
            try:
                shutil.copy2(self.backup_db_file, self.real_db_path)
                logger.info(f"✓ Restored database from backup")
            except Exception as e:
                logger.error(f"✗ Failed to restore database: {e}")
        elif self.real_db_path.exists():
            # Delete the test database if no backup exists
            try:
                self.real_db_path.unlink()
                logger.info("✓ Removed test database (no original backup)")
            except Exception as e:
                logger.warning(f"Could not remove test database: {e}")
        
        logger.info("=" * 60 + "\n")
        return True

    # ------------------------------------------------------------------
    # Database cleanup methods (for test entries only)
    # ------------------------------------------------------------------

    def _cleanup_database_entries(self, track_name_pattern: str = "TestTrack") -> int:
        """
        Delete all database entries (data_points, race_sessions, formulas) 
        that reference tracks matching the pattern (case-insensitive).
        
        Returns number of rows deleted.
        """
        if not self.real_db_path.exists():
            logger.info(f"Database {self.real_db_path} does not exist, skipping cleanup")
            return 0
        
        total_deleted = 0
        
        try:
            conn = sqlite3.connect(self.real_db_path)
            cursor = conn.cursor()
            
            # First, find all track names that match the pattern (case-insensitive)
            cursor.execute("""
                SELECT DISTINCT track FROM data_points 
                WHERE LOWER(track) LIKE LOWER(?)
            """, (f'%{track_name_pattern}%',))
            matching_tracks = [row[0] for row in cursor.fetchall()]
            
            if matching_tracks:
                logger.info(f"Found {len(matching_tracks)} track(s) matching '{track_name_pattern}': {matching_tracks}")
                
                # Build placeholders for IN clause
                placeholders = ','.join('?' * len(matching_tracks))
                
                # Delete from data_points
                cursor.execute(f"""
                    DELETE FROM data_points 
                    WHERE track IN ({placeholders})
                """, matching_tracks)
                data_points_deleted = cursor.rowcount
                total_deleted += data_points_deleted
                if data_points_deleted > 0:
                    logger.info(f"  Deleted {data_points_deleted} entries from data_points")
                
                # Delete from race_sessions
                cursor.execute(f"""
                    DELETE FROM race_sessions 
                    WHERE track_name IN ({placeholders})
                """, matching_tracks)
                race_sessions_deleted = cursor.rowcount
                total_deleted += race_sessions_deleted
                if race_sessions_deleted > 0:
                    logger.info(f"  Deleted {race_sessions_deleted} entries from race_sessions")
                
                # Delete from formulas
                cursor.execute(f"""
                    DELETE FROM formulas 
                    WHERE track IN ({placeholders})
                """, matching_tracks)
                formulas_deleted = cursor.rowcount
                total_deleted += formulas_deleted
                if formulas_deleted > 0:
                    logger.info(f"  Deleted {formulas_deleted} entries from formulas")
            
            conn.commit()
            conn.close()
            
            if total_deleted > 0:
                logger.info(f"✓ Database cleanup complete: {total_deleted} total entries deleted")
            else:
                logger.info("No test data found in database")
            
            return total_deleted
            
        except sqlite3.Error as e:
            logger.error(f"Database error during cleanup: {e}")
            if conn:
                conn.close()
            return 0
        except Exception as e:
            logger.error(f"Unexpected error during cleanup: {e}")
            if conn:
                conn.close()
            return 0

    def _cleanup_test_data(self):
        """Clean up test data from database before and after test runs"""
        logger.info("\n" + "=" * 60)
        logger.info("DATABASE CLEANUP")
        logger.info("=" * 60)
        
        # Delete entries for TestTrack (case-insensitive)
        self._cleanup_database_entries("TestTrack")
        
        logger.info("=" * 60 + "\n")

    # ------------------------------------------------------------------
    # Modify cfg.yml to point to test_mocks
    # ------------------------------------------------------------------

    def modify_cfg_for_test(self) -> bool:
        """
        Modify the real cfg.yml to point to test_mocks directory.
        Also backup the original first.
        """
        logger.info("\n" + "=" * 60)
        logger.info("MODIFYING cfg.yml FOR TEST")
        logger.info("=" * 60)
        
        # Load existing config or create default
        config = {}
        if self.real_cfg_path.exists():
            try:
                with open(self.real_cfg_path, 'r') as f:
                    config = yaml.safe_load(f) or {}
                logger.info(f"Loaded existing cfg.yml")
            except Exception as e:
                logger.warning(f"Could not load cfg.yml: {e}")
        
        # Modify base_path to point to test_mocks
        config['base_path'] = str(self.test_dir)
        
        # Ensure other required settings exist
        if 'db_path' not in config:
            config['db_path'] = 'ai_data.db'
        if 'poll_interval' not in config:
            config['poll_interval'] = 1.0  # Faster polling for tests
        ## if 'autopilot_enabled' not in config:
        ##     config['autopilot_enabled'] = False
        ## if 'backup_enabled' not in config:
        ##     config['backup_enabled'] = True
        ## if 'logging_enabled' not in config:
        ##     config['logging_enabled'] = True
        
        # Write modified config
        try:
            with open(self.real_cfg_path, 'w') as f:
                yaml.dump(config, f, default_flow_style=False, indent=2)
            logger.info(f"✓ Modified cfg.yml - base_path set to: {self.test_dir}")
            logger.info("=" * 60 + "\n")
            return True
        except Exception as e:
            logger.error(f"✗ Failed to write cfg.yml: {e}")
            return False

    # ------------------------------------------------------------------
    # Track / AIW discovery
    # ------------------------------------------------------------------

    def _discover_tracks(self) -> List[Dict]:
        """Discover existing tracks from test_mocks/GameData/Locations"""
        tracks = []
        locations_dir = self.test_dir / "GameData" / "Locations"

        if not locations_dir.exists():
            logger.warning(f"Locations directory not found: {locations_dir}")
            return []

        for track_dir in locations_dir.iterdir():
            if track_dir.is_dir():
                aiw_files = list(track_dir.glob("*.AIW")) + list(track_dir.glob("*.aiw"))
                for aiw_file in aiw_files:
                    tracks.append({
                        "name": track_dir.name,
                        "folder": track_dir.name,
                        "aiw_file": aiw_file.name,
                        "aiw_path": aiw_file,
                    })
                    logger.info(f"Discovered track: {track_dir.name}")
                    break

        return tracks

    # ------------------------------------------------------------------
    # Filename / content parsing helpers
    # ------------------------------------------------------------------

    def _parse_filename_for_ratios(self, filename: str) -> Optional[Dict]:
        """
        Parse qualratio and raceratio from filename like raceresult_1_qr0_98_rr0_97.txt
        Handles both underscore and dot as decimal separators.
        """
        # Method 1: Simple string splitting approach
        if 'qr' in filename and 'rr' in filename:
            try:
                qr_part = filename.split('qr')[1].split('_rr')[0]
                rr_part = filename.split('rr')[1].split('.txt')[0]
                
                qr_part = qr_part.rstrip('_.')
                rr_part = rr_part.rstrip('_.')
                
                qr_part = qr_part.replace('_', '.')
                rr_part = rr_part.replace('_', '.')
                
                qual_ratio = float(qr_part)
                race_ratio = float(rr_part)
                
                logger.info(f"  ✓ Parsed ratios: QR={qual_ratio}, RR={race_ratio}")
                return {
                    "qual_ratio": qual_ratio,
                    "race_ratio": race_ratio
                }
            except (IndexError, ValueError) as e:
                logger.debug(f"  String splitting failed: {e}")
        
        # Method 2: Regex approach
        pattern = r'qr([\d_]+?)_rr([\d_]+?)\.txt'
        match = re.search(pattern, filename)
        if match:
            try:
                qual_str = match.group(1).replace('_', '.')
                race_str = match.group(2).replace('_', '.')
                
                qual_str = qual_str.rstrip('.')
                race_str = race_str.rstrip('.')
                
                qual_ratio = float(qual_str)
                race_ratio = float(race_str)
                logger.info(f"  ✓ Parsed ratios (regex): QR={qual_ratio}, RR={race_ratio}")
                return {
                    "qual_ratio": qual_ratio,
                    "race_ratio": race_ratio
                }
            except ValueError as e:
                logger.debug(f"  Regex parsing failed: {e}")
        
        logger.warning(f"  ✗ Could not parse ratios from filename: {filename}")
        return None

    def _parse_track_from_result_file(self, filepath: Path) -> Dict:
        """
        Read a mock result file and extract track folder name and AIW filename.
        Returns a dict with keys 'track_folder' and 'aiw_file' (may be None if not found).
        """
        info = {"track_folder": None, "aiw_file": None}
        try:
            content = filepath.read_text(encoding="utf-8", errors="ignore")

            # Scene=<path>  → derive track folder
            scene_match = re.search(r'Scene\s*=\s*(.+)', content, re.IGNORECASE)
            if scene_match:
                scene = scene_match.group(1).strip().replace("\\", "/")
                scene_path = Path(scene)
                info["track_folder"] = scene_path.parent.name

            # AIDB=<path>  → derive AIW filename
            aidb_match = re.search(r'AIDB\s*=\s*(.+)', content, re.IGNORECASE)
            if aidb_match:
                aiw_path_str = aidb_match.group(1).strip().replace("\\", "/")
                info["aiw_file"] = Path(aiw_path_str).name

        except Exception as e:
            logger.warning(f"Could not parse track info from {filepath.name}: {e}")

        return info

    def _find_aiw_path(self, track_folder: Optional[str], aiw_file: Optional[str]) -> Optional[Path]:
        """
        Locate the AIW file under test_mocks/GameData/Locations.
        Uses case-insensitive matching on both folder and filename.
        """
        locations_dir = self.test_dir / "GameData" / "Locations"
        if not locations_dir.exists():
            return None

        tf_lower = track_folder.lower() if track_folder else None
        af_lower = aiw_file.lower() if aiw_file else None

        try:
            for folder in locations_dir.iterdir():
                if not folder.is_dir():
                    continue

                folder_matches = (tf_lower is None) or (folder.name.lower() == tf_lower)
                if not folder_matches:
                    continue

                if af_lower:
                    for f in folder.iterdir():
                        if f.is_file() and f.name.lower() == af_lower:
                            return f

                for ext_glob in ("*.AIW", "*.aiw"):
                    candidates = list(folder.glob(ext_glob))
                    if candidates:
                        return candidates[0]

        except OSError as e:
            logger.warning(f"Error searching for AIW: {e}")

        if af_lower:
            try:
                for root, _dirs, files in os.walk(locations_dir):
                    for f in files:
                        if f.lower() == af_lower:
                            return Path(root) / f
            except OSError:
                pass

        return None

    # ------------------------------------------------------------------
    # AIW backup / patch / restore
    # ------------------------------------------------------------------

    def _backup_aiw_file(self, aiw_path: Path) -> Optional[Path]:
        """Back up an AIW file before the first time we touch it."""
        key = str(aiw_path)
        if key in self._aiw_backups:
            logger.debug(f"AIW already backed up: {aiw_path.name}")
            return self._aiw_backups[key]

        backup_name = f"{aiw_path.stem}_HARNESS_ORIGINAL{aiw_path.suffix}"
        backup_path = self.harness_backup_dir / backup_name

        try:
            shutil.copy2(aiw_path, backup_path)
            self._aiw_backups[key] = backup_path
            logger.info(f"  ✓ AIW backed up → {backup_path.name}")
            return backup_path
        except Exception as e:
            logger.error(f"  ✗ Failed to back up AIW {aiw_path.name}: {e}")
            return None

    def _update_aiw_ratios(self, aiw_path: Path, qual_ratio: float, race_ratio: float) -> bool:
        """Patch QualRatio and RaceRatio values inside the AIW file in-place."""
        try:
            raw = aiw_path.read_bytes()
            content = raw.replace(b"\x00", b"").decode("utf-8", errors="ignore")

            original = content

            def _replace_ratio(text: str, key: str, value: float) -> Tuple[str, bool]:
                pattern = rf'({re.escape(key)}\s*=\s*\(?)\s*[0-9.eE+-]+\s*(\)?)'
                new_text, n = re.subn(
                    pattern,
                    lambda m: f"{m.group(1)}{value:.6f}{m.group(2)}",
                    text,
                    flags=re.IGNORECASE
                )
                return new_text, n > 0

            content, qual_ok = _replace_ratio(content, "QualRatio", qual_ratio)
            content, race_ok = _replace_ratio(content, "RaceRatio", race_ratio)

            if not qual_ok:
                logger.warning(f"  ⚠ QualRatio pattern not found in {aiw_path.name}")
            if not race_ok:
                logger.warning(f"  ⚠ RaceRatio pattern not found in {aiw_path.name}")

            if content != original:
                aiw_path.write_bytes(content.encode("utf-8", errors="ignore"))
                logger.info(f"  ✓ AIW patched: QualRatio={qual_ratio:.6f}  RaceRatio={race_ratio:.6f}")
                self._modified_aiw_files.add(str(aiw_path))
                return True
            else:
                logger.warning(f"  ⚠ AIW content unchanged after patch attempt ({aiw_path.name})")
                return False

        except Exception as e:
            logger.error(f"  ✗ Failed to update AIW ratios in {aiw_path.name}: {e}")
            return False

    def _restore_aiw_file(self, aiw_path: Path) -> bool:
        """Restore a single AIW file from its harness backup."""
        key = str(aiw_path)
        backup_path = self._aiw_backups.get(key)
        if not backup_path or not backup_path.exists():
            logger.debug(f"  No harness backup found for {aiw_path.name}")
            return False
        try:
            shutil.copy2(backup_path, aiw_path)
            logger.info(f"  ✓ AIW restored: {aiw_path.name}")
            return True
        except Exception as e:
            logger.error(f"  ✗ Failed to restore AIW {aiw_path.name}: {e}")
            return False

    def _restore_all_aiw_backups(self):
        """Restore every AIW file that was backed up during this test run."""
        if not self._aiw_backups:
            logger.info("No AIW backups to restore.")
            return

        logger.info(f"Restoring {len(self._aiw_backups)} AIW file(s)...")
        for aiw_path_str, backup_path in self._aiw_backups.items():
            self._restore_aiw_file(Path(aiw_path_str))

    # ------------------------------------------------------------------
    # raceresults.txt backup / restore
    # ------------------------------------------------------------------

    def backup_original_results(self) -> bool:
        """Backup the original test raceresults.txt if it exists"""
        if self.target_results_file.exists():
            try:
                shutil.copy2(self.target_results_file, self.backup_results_file)
                logger.info(f"✓ Backed up original test results to: {self.backup_results_file}")
                return True
            except Exception as e:
                logger.error(f"Failed to backup results: {e}")
                return False
        else:
            logger.info("No existing test results file to backup")
            return True

    def restore_original_results(self) -> bool:
        """Restore the original test raceresults.txt"""
        if self.backup_results_file.exists():
            try:
                shutil.copy2(self.backup_results_file, self.target_results_file)
                logger.info("✓ Restored original test results from backup")
                return True
            except Exception as e:
                logger.error(f"Failed to restore results: {e}")
                return False
        else:
            if self.target_results_file.exists():
                self.target_results_file.unlink()
                logger.info("✓ Removed test results file (didn't exist originally)")
            return True

    # ------------------------------------------------------------------
    # Core simulation step
    # ------------------------------------------------------------------

    def simulate_race_with_file(self, result_file: Path, wait_before: float = 0) -> bool:
        """
        Full per-file simulation workflow:
          1. Extract ratios from the filename
          2. Parse track / AIW info from the file content
          3. Find + backup the AIW (once per AIW path)
          4. Patch the AIW with the filename ratios
          5. Copy mock result → live raceresults.txt
          6. Force mtime update
        """
        logger.info(f"\n  Simulating race with: {result_file.name}")

        if wait_before > 0:
            time.sleep(wait_before)

        # Step 1: ratios from filename
        ratios = self._parse_filename_for_ratios(result_file.name)
        if ratios:
            logger.info(f"  Ratios from filename → QualRatio={ratios['qual_ratio']}  RaceRatio={ratios['race_ratio']}")
        else:
            logger.warning(f"  Could not parse ratios from filename: {result_file.name} (will skip AIW patch)")

        # Step 2: track / AIW info from file content
        track_info = self._parse_track_from_result_file(result_file)
        logger.info(f"  Track folder: {track_info['track_folder'] or '(unknown)'}  AIW file: {track_info['aiw_file'] or '(unknown)'}")

        # Step 3 + 4: locate AIW, backup, patch
        if ratios and (track_info["track_folder"] or track_info["aiw_file"]):
            aiw_path = self._find_aiw_path(track_info["track_folder"], track_info["aiw_file"])
            if aiw_path:
                logger.info(f"  Found AIW: {aiw_path}")
                self._backup_aiw_file(aiw_path)
                self._update_aiw_ratios(aiw_path, ratios["qual_ratio"], ratios["race_ratio"])
            else:
                logger.warning(f"  ⚠ AIW file not found for track '{track_info['track_folder']}' / '{track_info['aiw_file']}' — skipping AIW patch")
        else:
            logger.warning("  ⚠ Insufficient info to locate AIW — skipping AIW patch")

        # Step 5 + 6: copy mock result → live raceresults.txt
        success = self._copy_result_to_target(result_file)

        if success:
            logger.info(f"  ✓ Race results written to: {self.target_results_file}")
            time.sleep(1)
        else:
            logger.error("  ✗ Failed to write race results")

        return success

    def _copy_result_to_target(self, source_file: Path) -> bool:
        """Copy a mock result file to the monitored raceresults.txt location."""
        try:
            self.target_results_file.parent.mkdir(parents=True, exist_ok=True)

            content = source_file.read_text(encoding="utf-8", errors="ignore")
            self.target_results_file.write_text(content, encoding="utf-8")

            # Force mtime update so file-monitor always sees a change
            now = time.time()
            os.utime(self.target_results_file, (now, now))

            logger.info(f"  ✓ Copied to: {self.target_results_file}")
            self._log_result_file_info(source_file)
            return True
        except Exception as e:
            logger.error(f"  Failed to copy result file: {e}")
            return False

    # ------------------------------------------------------------------
    # Misc helpers
    # ------------------------------------------------------------------

    def _get_sorted_result_files(self) -> List[Path]:
        """Get all race result files from mock_raceresults directory, sorted by number"""
        if not self.mock_results_dir.exists():
            logger.error(f"Mock results directory not found: {self.mock_results_dir}")
            return []

        result_files = list(self.mock_results_dir.glob("raceresult_*.txt"))

        def get_file_number(filepath):
            match = re.search(r'raceresult_(\d+)', filepath.name)
            return int(match.group(1)) if match else 0

        result_files.sort(key=get_file_number)

        logger.info(f"Found {len(result_files)} result files in {self.mock_results_dir}")
        for f in result_files:
            ratios = self._parse_filename_for_ratios(f.name)
            if ratios:
                logger.info(f"  - {f.name}: QR={ratios['qual_ratio']}, RR={ratios['race_ratio']}")

        return result_files

    def _log_result_file_info(self, filepath: Path):
        """Log information from a result file"""
        try:
            content = filepath.read_text(encoding="utf-8", errors="ignore")

            driver_pattern = r'Driver=(\w+)'
            best_lap_pattern = r'BestLap=(\d+:\d+\.\d+)'
            qual_time_pattern = r'QualTime=(\d+:\d+\.\d+)'

            drivers = re.findall(driver_pattern, content)
            best_laps = re.findall(best_lap_pattern, content)
            qual_times = re.findall(qual_time_pattern, content)

            if drivers:
                logger.info(f"  Driver: {drivers[0]}")
            if best_laps:
                logger.info(f"  User BestLap: {best_laps[0]}")
            if qual_times:
                logger.info(f"  User QualTime: {qual_times[0]}")
            if len(best_laps) > 1:
                logger.info(f"  AI Best: {best_laps[1]}")
            if len(best_laps) > 6:
                logger.info(f"  AI Worst: {best_laps[6]}")

        except Exception as e:
            logger.debug(f"  Could not parse result file info: {e}")

    # ------------------------------------------------------------------
    # Application lifecycle
    # ------------------------------------------------------------------

    def _log_reader_thread(self, pipe, log_file, source_name):
        """Thread to read from a pipe and log to file and queue"""
        try:
            for line in iter(pipe.readline, ''):
                if line:
                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
                    formatted_line = f"[{timestamp}] [{source_name}] {line.rstrip()}"

                    self.log_queue.put(formatted_line)
                    log_file.write(formatted_line + '\n')
                    log_file.flush()

                    if "ERROR" in line or "CRITICAL" in line:
                        print(f"\033[91m{formatted_line}\033[0m")
                    elif "WARNING" in line:
                        print(f"\033[93m{formatted_line}\033[0m")
                    elif "INFO" in line:
                        print(f"\033[92m{formatted_line}\033[0m")
                    else:
                        print(formatted_line)
        except Exception as e:
            logger.error(f"Log reader thread error for {source_name}: {e}")

    def launch_application(self, no_gui: bool = False) -> bool:
        """Launch the Live AI Tuner application and capture logs"""
        logger.info("Launching Live AI Tuner...")

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        app_logs_dir = self.project_dir / "app_logs"
        app_logs_dir.mkdir(parents=True, exist_ok=True)
        self.app_log_file = app_logs_dir / f"app_log_{timestamp}.txt"

        script_dir = self.project_dir
        app_script = script_dir / "dyn_ai.py"

        if not app_script.exists():
            logger.error(f"Application script not found: {app_script}")
            return False

        # Use the real cfg.yml - we already modified it to point to test_mocks
        cmd = [sys.executable, "-u", str(app_script)]

        if no_gui:
            cmd.append("--no-gui")
            logger.info("  Running in console mode")

        try:
            self.app_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                universal_newlines=True,
                env=os.environ.copy()
            )

            log_file = open(self.app_log_file, 'w', encoding='utf-8')
            log_file.write(f"=== Live AI Tuner Log - {datetime.now().isoformat()} ===\n")
            log_file.write(f"Command: {' '.join(cmd)}\n")
            log_file.write(f"PID: {self.app_process.pid}\n")
            log_file.write("=" * 80 + "\n\n")

            stdout_thread = threading.Thread(
                target=self._log_reader_thread,
                args=(self.app_process.stdout, log_file, "STDOUT"),
                daemon=True
            )
            stderr_thread = threading.Thread(
                target=self._log_reader_thread,
                args=(self.app_process.stderr, log_file, "STDERR"),
                daemon=True
            )

            stdout_thread.start()
            stderr_thread.start()

            self.log_file_handle = log_file
            self.log_threads = (stdout_thread, stderr_thread)

            logger.info("  Waiting for application to initialize...")
            time.sleep(5)

            if self.app_process.poll() is not None:
                time.sleep(1)
                logger.error(f"  ❌ Application exited immediately with code {self.app_process.returncode}")
                logger.error(f"  Check log file for details: {self.app_log_file}")
                self._display_recent_logs()
                return False

            logger.info(f"  ✓ Application launched with PID: {self.app_process.pid}")
            logger.info(f"  ✓ Log file: {self.app_log_file}")
            return True

        except Exception as e:
            logger.error(f"  Failed to launch application: {e}")
            return False

    def _display_recent_logs(self, lines: int = 20):
        """Display recent lines from the log file"""
        if not self.app_log_file or not self.app_log_file.exists():
            return

        logger.error(f"\n  Recent logs from {self.app_log_file}:")
        logger.error("  " + "-" * 50)

        try:
            with open(self.app_log_file, 'r') as f:
                all_lines = f.readlines()
                recent = all_lines[-lines:] if len(all_lines) > lines else all_lines
                for line in recent:
                    line = line.strip()
                    if line:
                        logger.error(f"    {line}")
        except Exception as e:
            logger.error(f"    Could not read log file: {e}")

    def stop_application(self):
        """Stop the application gracefully"""
        if self.app_process:
            logger.info("Stopping application...")
            self.app_process.terminate()
            try:
                self.app_process.wait(timeout=5)
                logger.info("  Application stopped gracefully")
            except subprocess.TimeoutExpired:
                logger.warning("  Application didn't terminate, killing...")
                self.app_process.kill()
                self.app_process.wait()
                logger.info("  Application killed")

            time.sleep(1)

            if hasattr(self, 'log_file_handle'):
                self.log_file_handle.write("\n" + "=" * 80 + "\n")
                self.log_file_handle.write(f"=== Application stopped at {datetime.now().isoformat()} ===\n")
                self.log_file_handle.close()

            self.app_process = None


    def _full_cleanup(self):
        """Restore ALL modified files: AIWs, raceresults.txt, cfg.yml, database"""
        logger.info("\n" + "=" * 60)
        logger.info("FULL CLEANUP - RESTORING ALL FILES")
        logger.info("=" * 60)
        
        self._restore_all_aiw_backups()
        self.restore_original_results()
        self.restore_real_files()
        self._cleanup_test_data()
        
        logger.info("=" * 60 + "\n")


    def run_full_test_with_files(self):
        """Run full test reading all result files in order"""
        logger.info("\n" + "=" * 60)
        logger.info("Full Test Mode - Reading Race Result Files in Order")
        logger.info("=" * 60)

        # Step 1: Backup real files first
        if not self.backup_real_files():
            logger.error("Failed to backup real files")
            return False

        # Step 2: Modify cfg.yml to point to test_mocks
        if not self.modify_cfg_for_test():
            logger.error("Failed to modify cfg.yml for test")
            self.restore_real_files()
            return False

        # Step 3: Clean up any existing test data
        self._cleanup_test_data()

        # Step 4: Get result files
        result_files = self._get_sorted_result_files()
        if not result_files:
            logger.error("No result files found to process!")
            self._full_cleanup()
            return False

        logger.info(f"\nWill process {len(result_files)} result files:")
        for i, f in enumerate(result_files, 1):
            ratios = self._parse_filename_for_ratios(f.name)
            ratio_str = f"QR={ratios['qual_ratio']}, RR={ratios['race_ratio']}" if ratios else "unknown ratios"
            logger.info(f"  {i}. {f.name} ({ratio_str})")

        # Step 5: Backup original test results file
        self.backup_original_results()

        # Step 6: Launch application
        if not self.launch_application(no_gui=False):
            logger.error("Failed to launch application")
            self._full_cleanup()
            return False

        try:
            logger.info("\nWaiting 3 seconds for application to fully initialize...")
            time.sleep(3)

            for i, result_file in enumerate(result_files, 1):
                if i > 1:
                    logger.info(f"\nWaiting 5 seconds before next file...")
                    time.sleep(5)

                logger.info(f"\n{'=' * 50}")
                logger.info(f"[File {i}/{len(result_files)}] Processing: {result_file.name}")

                ratios = self._parse_filename_for_ratios(result_file.name)
                if ratios:
                    logger.info(f"  Expected QualRatio: {ratios['qual_ratio']}")
                    logger.info(f"  Expected RaceRatio: {ratios['race_ratio']}")

                self.simulate_race_with_file(result_file, wait_before=0)

                logger.info("  Waiting 5 seconds for processing...")
                time.sleep(5)

            logger.info("\n" + "=" * 60)
            logger.info("✓ Full test complete!")
            logger.info(f"Processed {len(result_files)} result files")
            logger.info(f"Log file: {self.app_log_file}")
            logger.info("Application is still running. Press Enter to stop and restore all files...")
            logger.info("=" * 60)

            input()

        except KeyboardInterrupt:
            logger.info("\nTest interrupted by user")
        finally:
            self.stop_application()
            self._full_cleanup()

        return True

    def run_user_interactive_test(self):
        """Run user-interactive test - single change after delay"""
        logger.info("\n" + "=" * 60)
        logger.info("User-Interactive Test Mode")
        logger.info("=" * 60)
        logger.info("This will:")
        logger.info("  1. Backup real files and modify cfg.yml for test")
        logger.info("  2. Launch the application")
        logger.info("  3. Wait 2 seconds")
        logger.info("  4. Make ONE change to raceresults.txt (with AIW patched)")
        logger.info("  5. Keep application running for you to observe")
        logger.info("  6. Restore all files when you press Enter")
        logger.info("=" * 60)

        # Step 1: Backup real files
        if not self.backup_real_files():
            logger.error("Failed to backup real files")
            return False

        # Step 2: Modify cfg.yml to point to test_mocks
        if not self.modify_cfg_for_test():
            logger.error("Failed to modify cfg.yml for test")
            self.restore_real_files()
            return False

        # Step 3: Clean up test data
        self._cleanup_test_data()

        # Step 4: Get result files
        result_files = self._get_sorted_result_files()
        if not result_files:
            logger.error("No result files found!")
            self._full_cleanup()
            return False

        test_file = result_files[0]
        logger.info(f"Using test file: {test_file.name}")

        # Step 5: Backup original test results
        self.backup_original_results()

        # Step 6: Run integration tests
        if not self.run_integration_tests():
            logger.warning("Integration tests had issues, but continuing...")

        # Step 7: Launch application
        if not self.launch_application(no_gui=False):
            logger.error("Failed to launch application")
            self._full_cleanup()
            return False

        try:
            logger.info("\nWaiting 3 seconds for application to fully initialize...")
            time.sleep(3)

            logger.info("\nMaking ONE change to raceresults.txt (with AIW patched)...")
            self.simulate_race_with_file(test_file, wait_before=0)

            logger.info("\n" + "=" * 60)
            logger.info("✓ Test change complete!")
            logger.info("Application is now running and monitoring.")
            logger.info(f"Log file: {self.app_log_file}")
            logger.info("Press Enter to stop the application and restore all files...")
            logger.info("=" * 60)

            input()

        except KeyboardInterrupt:
            logger.info("\nTest interrupted by user")
        finally:
            self.stop_application()
            self._full_cleanup()

        return True


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    """Main entry point"""
    print("\n" + "=" * 60)
    print("[TEST_HARNESS] Live AI Tuner Test Harness")
    print("=" * 60)
    print("\nSelect test mode:")
    print("  1. User-interactive test - one change after delay")
    print("  2. Full test - read all race result files in order (DEFAULT)")
    print("\nDefault option (2) will be selected in 3 seconds...")
    print("=" * 60)

    user_input = [None]
    timeout = 3

    print("\nEnter choice (1-2) or press Enter for default: ", end="", flush=True)

    def get_input():
        try:
            user_input[0] = sys.stdin.readline().strip()
        except Exception:
            pass

    input_thread = threading.Thread(target=get_input)
    input_thread.daemon = True
    input_thread.start()

    for i in range(timeout, 0, -1):
        if user_input[0] is not None:
            break
        print(f"\rEnter choice (1-2) or press Enter for default: (waiting {i}s) ", end="", flush=True)
        time.sleep(1)

    choice = user_input[0] if user_input[0] is not None else "2"
    if not choice:
        choice = "2"

    if choice not in ("1", "2"):
        print(f"\nInvalid choice: {choice!r} — using default (2)")
        choice = "2"

    print()
    harness = LiveAITunerTestHarness()

    if choice == "1":
        print("\nRunning user-interactive test...")
        success = harness.run_user_interactive_test()
    else:
        print("\nRunning full test with result files...")
        success = harness.run_full_test_with_files()
        #success = harness.run_integration_tests()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
