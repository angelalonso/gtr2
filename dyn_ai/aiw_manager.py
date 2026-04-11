"""
AIW File Manager - Reading, writing, and backing up AIW files
OPTIMIZED: Reduced file operations, caching, and lazy loading
UPDATED: Case-insensitive search with full path logging
UPDATED: SQLite-backed path cache and ratio change history via db_manager
"""

import os
import re
import shutil
import logging
from pathlib import Path
from typing import Optional, Tuple, List, Dict
from datetime import datetime

logger = logging.getLogger(__name__)


class AIWManager:
    """Manages AIW file operations with proper backup preservation - OPTIMIZED"""
    
    def __init__(self, backup_dir: Path = None, db=None):
        """
        Parameters
        ----------
        db : db_manager.Database | None
            When provided the manager uses SQLite for AIW path caching and
            logs every ratio write (successful or not) to ``ratio_updates``.
        """
        self.backup_dir = Path(backup_dir) if backup_dir else Path("./backups")
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.backup_created_for_track = set()
        self.db = db  # ← SQLite handle (may be None)
        
        # In-memory cache still used as a fast L1 layer in front of SQLite
        self._aiw_path_cache: Dict[str, Path] = {}
        self._aiw_ratio_cache: Dict[str, Tuple[Optional[float], Optional[float]]] = {}

    # ── Internal cache helpers ────────────────────────────────────────────────

    def _cache_get_path(self, cache_key: str) -> Optional[Path]:
        """Check L1 (memory) then L2 (SQLite) for a cached AIW path."""
        if cache_key in self._aiw_path_cache:
            p = self._aiw_path_cache[cache_key]
            if p.exists():
                return p
            # Stale — evict both layers
            del self._aiw_path_cache[cache_key]
            if self.db:
                self.db.invalidate_aiw_cache(cache_key)
            return None

        if self.db:
            stored = self.db.get_cached_aiw_path(cache_key)
            if stored:
                p = Path(stored)
                if p.exists():
                    self._aiw_path_cache[cache_key] = p  # promote to L1
                    return p
                # Stale DB entry
                self.db.invalidate_aiw_cache(cache_key)

        return None

    def _cache_set_path(self, cache_key: str, path: Path) -> None:
        """Write to both L1 and L2 caches."""
        self._aiw_path_cache[cache_key] = path
        if self.db:
            self.db.set_cached_aiw_path(cache_key, str(path))

    # ── Public API ────────────────────────────────────────────────────────────
        
    def find_aiw_file(self, aiw_filename: str, track_name: str, base_path: Path) -> Optional[Path]:
        """Find AIW file with caching and case-insensitive search"""
        cache_key = f"{track_name}_{aiw_filename}".lower()
        
        cached = self._cache_get_path(cache_key)
        if cached is not None:
            logger.info(f"Found AIW (cached): {cached}")
            return cached
        
        locations_path = base_path / 'GameData' / 'Locations'
        logger.info(f"Searching for AIW: {aiw_filename}")
        logger.info(f"  Base path: {base_path}")
        logger.info(f"  Locations path: {locations_path}")
        
        if not locations_path.exists():
            logger.error(f"Locations path does not exist: {locations_path}")
            return None
        
        aiw_filename_normalized = Path(aiw_filename).name
        logger.info(f"  Looking for filename: {aiw_filename_normalized}")
        
        found_path = None
        
        # Strategy 1: Use track name with case-insensitive folder search
        if track_name:
            track_lower = track_name.lower()
            logger.info(f"  Searching for track folder: {track_name} (case-insensitive)")
            
            try:
                for track_folder in locations_path.iterdir():
                    if track_folder.is_dir() and track_folder.name.lower() == track_lower:
                        logger.info(f"    Found matching folder: {track_folder}")
                        
                        for file in track_folder.glob('*'):
                            if file.is_file() and file.name.lower() == aiw_filename_normalized.lower():
                                found_path = file
                                logger.info(f"      Found exact match: {file}")
                                break
                        
                        if not found_path:
                            for ext in ['.AIW', '.aiw']:
                                candidate = track_folder / f"{track_folder.name}{ext}"
                                if candidate.exists():
                                    found_path = candidate
                                    logger.info(f"      Found by folder name: {candidate}")
                                    break
                        
                        if not found_path:
                            for ext_glob in ['*.AIW', '*.aiw']:
                                candidates = list(track_folder.glob(ext_glob))
                                if candidates:
                                    found_path = candidates[0]
                                    logger.info(f"      Found any AIW file: {found_path}")
                                    break
                        
                        if found_path:
                            break
                            
            except OSError as e:
                logger.error(f"Error iterating locations: {e}")
        
        # Strategy 2: Search recursively (case-insensitive)
        if not found_path:
            logger.info(f"  Searching recursively in: {locations_path}")
            try:
                for root, dirs, files in os.walk(locations_path):
                    for file in files:
                        if file.lower() == aiw_filename_normalized.lower():
                            found_path = Path(root) / file
                            logger.info(f"    Found via recursive search: {found_path}")
                            break
                    if found_path:
                        break
            except OSError as e:
                logger.error(f"Error in recursive search: {e}")
        
        # Strategy 3: Try to extract track from path if filename has full path
        if not found_path and ('\\' in aiw_filename or '/' in aiw_filename):
            logger.info(f"  Attempting to parse full path: {aiw_filename}")
            try:
                normalized_path = aiw_filename.replace('\\', '/')
                parts = normalized_path.split('/')
                
                if 'Locations' in parts:
                    loc_index = parts.index('Locations')
                    if loc_index + 1 < len(parts):
                        track_folder_name = parts[loc_index + 1]
                        logger.info(f"  Extracted track folder: {track_folder_name}")
                        
                        track_folder_path = locations_path / track_folder_name
                        if track_folder_path.exists():
                            logger.info(f"  Checking folder: {track_folder_path}")
                            for file in track_folder_path.glob('*'):
                                if file.is_file() and file.name.lower() == aiw_filename_normalized.lower():
                                    found_path = file
                                    logger.info(f"    Found via path parsing: {found_path}")
                                    break
            except Exception as e:
                logger.error(f"Error parsing path: {e}")
        
        if found_path:
            logger.info(f"✓ AIW file found: {found_path} (exists: {found_path.exists()})")
            self._cache_set_path(cache_key, found_path)  # ← persist to SQLite
        else:
            logger.error(f"✗ AIW file NOT found: {aiw_filename_normalized}")
            if locations_path.exists():
                for folder in locations_path.iterdir():
                    if folder.is_dir():
                        logger.error(f"    - {folder.name}")
                        aiw_files = list(folder.glob('*.AIW')) + list(folder.glob('*.aiw'))
                        for af in aiw_files:
                            logger.error(f"        {af.name}")
        
        return found_path
    
    def read_ratios(self, aiw_path: Path) -> Tuple[Optional[float], Optional[float]]:
        """Read QualRatio and RaceRatio with caching"""
        cache_key = str(aiw_path)
        
        if cache_key in self._aiw_ratio_cache:
            return self._aiw_ratio_cache[cache_key]
        
        try:
            if not aiw_path.exists():
                return None, None
            
            with open(aiw_path, 'rb') as f:
                raw_content = f.read()
            
            content = raw_content.replace(b'\x00', b'').decode('utf-8', errors='ignore')
            
            qual_ratio = None
            race_ratio = None
            
            waypoint_match = re.search(r'\[Waypoint\](.*?)(?=\[|$)', content, re.DOTALL | re.IGNORECASE)
            if waypoint_match:
                section = waypoint_match.group(1)
                
                q_match = re.search(r'QualRatio\s*=\s*\(?([\d.eE+-]+)\)?', section, re.IGNORECASE)
                if q_match:
                    qual_ratio = float(q_match.group(1))
                
                r_match = re.search(r'RaceRatio\s*=\s*\(?([\d.eE+-]+)\)?', section, re.IGNORECASE)
                if r_match:
                    race_ratio = float(r_match.group(1))
            
            result = (qual_ratio, race_ratio)
            self._aiw_ratio_cache[cache_key] = result
            return result
            
        except Exception as e:
            logger.error(f"Error reading ratios from {aiw_path}: {e}")
            return None, None

    def update_ratio(
        self,
        aiw_path: Path,
        ratio_type: str,
        new_value: float,
        track_name: str = "",
        create_backup: bool = True,
    ) -> bool:
        """
        Update a ratio value in an AIW file.
        Logs the change (old value → new value, success flag) to SQLite.
        """
        logger.info("=" * 60)
        logger.info(f"UPDATE_RATIO: {ratio_type} = {new_value:.6f}")
        logger.info(f"  File: {aiw_path}")
        logger.info(f"  Track: {track_name}")

        # Read old value for history log
        old_qual, old_race = self.read_ratios(aiw_path)
        old_value = old_qual if ratio_type.lower() == 'qualratio' else old_race

        success = False
        try:
            if not aiw_path.exists():
                logger.error(f"  File does not exist: {aiw_path}")
                return False

            try:
                file_stat = aiw_path.stat()
                logger.info(f"  File size: {file_stat.st_size} bytes")
                logger.info(f"  File permissions: {oct(file_stat.st_mode)}")
            except Exception as e:
                logger.error(f"  Cannot stat file: {e}")

            if create_backup:
                logger.info(f"  Creating backup...")
                original_backup = self.create_backup_before_modification(aiw_path, track_name)
                if original_backup:
                    logger.info(f"  Backup created: {original_backup}")
                else:
                    logger.warning(f"  Backup creation failed or skipped")

            logger.info(f"  Reading file...")
            with open(aiw_path, 'rb') as f:
                raw_content = f.read()

            logger.info(f"  Read {len(raw_content)} bytes")
            content = raw_content.replace(b'\x00', b'').decode('utf-8', errors='ignore')
            logger.info(f"  Decoded content length: {len(content)} chars")

            pattern = rf'({ratio_type}\s*=\s*\(?)\s*[0-9.eE+-]+\s*(\)?)'
            logger.info(f"  Searching for pattern: {pattern}")

            match_found = re.search(pattern, content, flags=re.IGNORECASE)
            if match_found:
                logger.info(f"  Found match: {match_found.group(0)}")
            else:
                logger.warning(f"  Pattern NOT found for {ratio_type}")
                lines = content.split('\n')
                for i, line in enumerate(lines):
                    if ratio_type.lower() in line.lower():
                        logger.info(f"    Line {i}: {line.strip()}")
                return False

            def replacer(m):
                new_text = f"{m.group(1)}{new_value:.6f}{m.group(2)}"
                logger.debug(f"  Replacing: '{m.group(0)}' -> '{new_text}'")
                return new_text

            new_content = re.sub(pattern, replacer, content, flags=re.IGNORECASE)

            if new_content != content:
                logger.info(f"  Content changed")

                import difflib
                diff = list(difflib.unified_diff(
                    content.splitlines(keepends=True),
                    new_content.splitlines(keepends=True),
                    fromfile='original',
                    tofile='modified',
                    n=3,
                ))
                for line in diff[:20]:
                    logger.debug(f"    {line.rstrip()}")

                logger.info(f"  Writing to file...")
                try:
                    output_bytes = new_content.encode('utf-8', errors='ignore')
                    logger.info(f"  Writing {len(output_bytes)} bytes")

                    with open(aiw_path, 'wb') as f:
                        f.write(output_bytes)
                        f.flush()
                        os.fsync(f.fileno())

                    logger.info(f"  File written successfully")

                    # Verify
                    with open(aiw_path, 'rb') as f:
                        verify_raw = f.read()
                    verify_content = verify_raw.replace(b'\x00', b'').decode('utf-8', errors='ignore')

                    verify_match = re.search(pattern, verify_content, flags=re.IGNORECASE)
                    if verify_match:
                        num_match = re.search(r'[\d.]+', verify_match.group(0))
                        if num_match:
                            actual_value = float(num_match.group())
                            if abs(actual_value - new_value) < 0.0001:
                                logger.info(f"  ✓ Value verified: {actual_value:.6f}")
                            else:
                                logger.error(f"  ✗ Value mismatch: expected {new_value:.6f}, got {actual_value:.6f}")
                    else:
                        logger.error(f"  ✗ Pattern not found after write!")

                    # Clear ratio cache for this file
                    cache_key = str(aiw_path)
                    if cache_key in self._aiw_ratio_cache:
                        del self._aiw_ratio_cache[cache_key]
                        logger.info(f"  Cleared ratio cache for {cache_key}")

                    logger.info(f"  ✓ UPDATE_RATIO: SUCCESS for {ratio_type}")
                    logger.info("=" * 60)
                    success = True
                    return True

                except Exception as e:
                    logger.error(f"  Error writing file: {e}", exc_info=True)
                    return False
            else:
                logger.warning(f"  Content did not change after replacement attempt")
                return False

        except Exception as e:
            logger.error(f"Error updating ratio in {aiw_path}: {e}", exc_info=True)
            return False

        finally:
            # ── Log to SQLite regardless of outcome ───────────────────────
            if self.db is not None:
                try:
                    self.db.log_ratio_update(
                        track_name=track_name,
                        aiw_path=str(aiw_path),
                        ratio_type=ratio_type,
                        old_value=old_value,
                        new_value=new_value,
                        success=success,
                    )
                except Exception as db_err:
                    logger.error(f"DB ratio log failed (non-fatal): {db_err}")

    def create_backup_before_modification(self, aiw_path: Path, track_name: str) -> Optional[Path]:
        """Create a backup of the AIW file before modifying it"""
        try:
            original_backup = self.backup_dir / f"{track_name}_ORIGINAL{aiw_path.suffix}"
            
            if original_backup.exists():
                logger.info(f"Original backup already exists: {original_backup}")
                self.backup_created_for_track.add(track_name)
                return original_backup
            
            shutil.copy2(aiw_path, original_backup)
            self.backup_created_for_track.add(track_name)
            logger.info(f"Created original backup: {original_backup}")
            return original_backup
            
        except Exception as e:
            logger.error(f"Error creating backup: {e}")
            return None

    def restore_original(self, aiw_path: Path, track_name: str) -> bool:
        """Restore the original AIW file"""
        try:
            original_backup = self.backup_dir / f"{track_name}_ORIGINAL{aiw_path.suffix}"
            
            if not original_backup.exists():
                return False
            
            shutil.copy2(original_backup, aiw_path)
            
            cache_key = str(aiw_path)
            if cache_key in self._aiw_ratio_cache:
                del self._aiw_ratio_cache[cache_key]
            
            logger.info(f"Restored original from: {original_backup}")
            return True
            
        except Exception as e:
            logger.error(f"Error restoring original: {e}")
            return False
    
    def get_original_backup(self, aiw_path: Path) -> Optional[Path]:
        track_name = aiw_path.stem
        original_backup = self.backup_dir / f"{track_name}_ORIGINAL{aiw_path.suffix}"
        return original_backup if original_backup.exists() else None
    
    def get_backup_info(self, aiw_path: Path, track_name: str) -> dict:
        original = self.get_original_backup(aiw_path)
        return {
            'original_exists': original is not None,
            'original_path': str(original) if original else None,
            'backup_created': track_name in self.backup_created_for_track,
        }
    
    def has_original_backup(self, aiw_path: Path, track_name: str) -> bool:
        return track_name in self.backup_created_for_track or self.get_original_backup(aiw_path) is not None
