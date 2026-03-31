"""
AIW File Manager - Reading, writing, and backing up AIW files
OPTIMIZED: Reduced file operations, caching, and lazy loading
UPDATED: Case-insensitive search with full path logging
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
    
    def __init__(self, backup_dir: Path = None):
        self.backup_dir = Path(backup_dir) if backup_dir else Path("./backups")
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.backup_created_for_track = set()
        
        # Cache for AIW file paths
        self._aiw_path_cache: Dict[str, Path] = {}
        self._aiw_ratio_cache: Dict[str, Tuple[Optional[float], Optional[float]]] = {}
        
    def find_aiw_file(self, aiw_filename: str, track_name: str, base_path: Path) -> Optional[Path]:
        """Find AIW file with caching and case-insensitive search"""
        cache_key = f"{track_name}_{aiw_filename}".lower()
        
        if cache_key in self._aiw_path_cache:
            cached_path = self._aiw_path_cache[cache_key]
            if cached_path.exists():
                logger.info(f"Found AIW (cached): {cached_path}")
                return cached_path
            else:
                del self._aiw_path_cache[cache_key]
        
        locations_path = base_path / 'GameData' / 'Locations'
        logger.info(f"Searching for AIW: {aiw_filename}")
        logger.info(f"  Base path: {base_path}")
        logger.info(f"  Locations path: {locations_path}")
        
        if not locations_path.exists():
            logger.error(f"Locations path does not exist: {locations_path}")
            return None
        
        # Normalize the AIW filename (handle backslashes, case)
        aiw_filename_normalized = Path(aiw_filename).name  # Get just the filename
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
                        
                        # Look for AIW files in this folder
                        for file in track_folder.glob('*'):
                            if file.is_file() and file.name.lower() == aiw_filename_normalized.lower():
                                found_path = file
                                logger.info(f"      Found exact match: {file}")
                                break
                        
                        if not found_path:
                            # Try with .AIW extension using folder name
                            for ext in ['.AIW', '.aiw']:
                                candidate = track_folder / f"{track_folder.name}{ext}"
                                if candidate.exists():
                                    found_path = candidate
                                    logger.info(f"      Found by folder name: {candidate}")
                                    break
                        
                        if not found_path:
                            # Try any AIW file in the folder
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
                # Normalize path separators
                normalized_path = aiw_filename.replace('\\', '/')
                parts = normalized_path.split('/')
                
                # Find Locations in the path
                if 'Locations' in parts:
                    loc_index = parts.index('Locations')
                    if loc_index + 1 < len(parts):
                        track_folder_name = parts[loc_index + 1]
                        logger.info(f"  Extracted track folder: {track_folder_name}")
                        
                        # Search in that specific folder
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
            self._aiw_path_cache[cache_key] = found_path
        else:
            logger.error(f"✗ AIW file NOT found: {aiw_filename_normalized}")
            logger.error(f"  Search locations:")
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
            
            # Read file
            with open(aiw_path, 'rb') as f:
                raw_content = f.read()
            
            # Fast decode
            content = raw_content.replace(b'\x00', b'').decode('utf-8', errors='ignore')
            
            qual_ratio = None
            race_ratio = None
            
            # Use compiled regex for better performance
            waypoint_match = re.search(r'\[Waypoint\](.*?)(?=\[|$)', content, re.DOTALL | re.IGNORECASE)
            if waypoint_match:
                waypoint_section = waypoint_match.group(1)
                
                quali_match = re.search(r'QualRatio\s*=\s*\(?([\d.]+)\)?', waypoint_section, re.IGNORECASE)
                if quali_match:
                    qual_ratio = float(quali_match.group(1))
                
                race_match = re.search(r'RaceRatio\s*=\s*\(?([\d.]+)\)?', waypoint_section, re.IGNORECASE)
                if race_match:
                    race_ratio = float(race_match.group(1))
            
            result = (qual_ratio, race_ratio)
            self._aiw_ratio_cache[cache_key] = result
            return result
            
        except Exception as e:
            logger.error(f"Error reading AIW file {aiw_path}: {e}")
            return None, None
    
    def create_original_backup(self, aiw_path: Path, track_name: str) -> Optional[Path]:
        """Create a backup of the original AIW file (only once per track)"""
        try:
            if not aiw_path.exists():
                return None
            
            if track_name in self.backup_created_for_track:
                return self.get_original_backup(aiw_path)
            
            original_backup_name = f"{track_name}_ORIGINAL{aiw_path.suffix}"
            original_backup_path = self.backup_dir / original_backup_name
            
            if not original_backup_path.exists():
                shutil.copy2(aiw_path, original_backup_path)
                logger.info(f"Created original backup: {original_backup_path}")
            
            self.backup_created_for_track.add(track_name)
            return original_backup_path
                
        except Exception as e:
            logger.error(f"Error creating original backup: {e}")
            return None
    
    def create_backup_before_modification(self, aiw_path: Path, track_name: str) -> Optional[Path]:
        """Create original backup only if not already created"""
        return self.create_original_backup(aiw_path, track_name)

    def update_ratio(self, aiw_path: Path, ratio_type: str, new_value: float, 
                     track_name: str, create_backup: bool = True) -> bool:
        """Update a single ratio in the AIW file with detailed debugging"""
        try:
            logger.info("=" * 60)
            logger.info(f"UPDATE_RATIO: Starting update")
            logger.info(f"  File: {aiw_path}")
            logger.info(f"  Ratio type: {ratio_type}")
            logger.info(f"  New value: {new_value:.6f}")
            logger.info(f"  Track: {track_name}")
            
            # Check if file exists and is readable
            if not aiw_path.exists():
                logger.error(f"  File does not exist: {aiw_path}")
                return False
            
            # Get file size and permissions
            try:
                file_stat = aiw_path.stat()
                logger.info(f"  File size: {file_stat.st_size} bytes")
                logger.info(f"  File permissions: {oct(file_stat.st_mode)}")
            except Exception as e:
                logger.error(f"  Cannot stat file: {e}")
            
            # Create backup if requested
            if create_backup:
                logger.info(f"  Creating backup...")
                original_backup = self.create_backup_before_modification(aiw_path, track_name)
                if original_backup:
                    logger.info(f"  Backup created: {original_backup}")
                else:
                    logger.warning(f"  Backup creation failed or skipped")
            
            # Read the file
            logger.info(f"  Reading file...")
            with open(aiw_path, 'rb') as f:
                raw_content = f.read()
            
            logger.info(f"  Read {len(raw_content)} bytes")
            
            # Decode content (remove null bytes)
            content = raw_content.replace(b'\x00', b'').decode('utf-8', errors='ignore')
            logger.info(f"  Decoded content length: {len(content)} chars")
            
            # Show first 500 chars for debugging
            logger.debug(f"  Content preview: {content[:500]}...")
            
            # Search for the pattern
            pattern = rf'({ratio_type}\s*=\s*\(?)\s*[0-9.eE+-]+\s*(\)?)'
            logger.info(f"  Searching for pattern: {pattern}")
            
            # Check if pattern exists before replacement
            match_found = re.search(pattern, content, flags=re.IGNORECASE)
            if match_found:
                old_value_str = match_found.group(0)
                logger.info(f"  Found match: {old_value_str}")
            else:
                logger.warning(f"  Pattern NOT found for {ratio_type}")
                logger.info(f"  Searching for any {ratio_type} occurrences...")
                # Show all lines containing the ratio type
                lines = content.split('\n')
                for i, line in enumerate(lines):
                    if ratio_type.lower() in line.lower():
                        logger.info(f"    Line {i}: {line.strip()}")
                return False
            
            # Perform replacement
            def replacer(m):
                new_text = f"{m.group(1)}{new_value:.6f}{m.group(2)}"
                logger.debug(f"  Replacing: '{m.group(0)}' -> '{new_text}'")
                return new_text
            
            new_content = re.sub(pattern, replacer, content, flags=re.IGNORECASE)
            
            # Check if content actually changed
            if new_content != content:
                logger.info(f"  Content changed (diff length: {len(new_content)} vs {len(content)})")
                
                # Show the specific change
                import difflib
                diff = list(difflib.unified_diff(
                    content.splitlines(keepends=True),
                    new_content.splitlines(keepends=True),
                    fromfile='original',
                    tofile='modified',
                    n=3
                ))
                for line in diff[:20]:  # Show first 20 lines of diff
                    logger.debug(f"    {line.rstrip()}")
                
                # Write back to file
                logger.info(f"  Writing to file...")
                try:
                    # Write as bytes
                    output_bytes = new_content.encode('utf-8', errors='ignore')
                    logger.info(f"  Writing {len(output_bytes)} bytes")
                    
                    with open(aiw_path, 'wb') as f:
                        f.write(output_bytes)
                        f.flush()  # Force flush to disk
                        os.fsync(f.fileno())  # Force OS to write
                    
                    logger.info(f"  File written successfully")
                    
                    # Verify the write
                    logger.info(f"  Verifying write...")
                    with open(aiw_path, 'rb') as f:
                        verify_raw = f.read()
                    verify_content = verify_raw.replace(b'\x00', b'').decode('utf-8', errors='ignore')
                    
                    # Check if our change is still there
                    verify_match = re.search(pattern, verify_content, flags=re.IGNORECASE)
                    if verify_match:
                        verify_value = verify_match.group(0)
                        logger.info(f"  Verification: Found {verify_value}")
                        
                        # Extract the actual numeric value
                        num_match = re.search(r'[\d.]+', verify_value)
                        if num_match:
                            actual_value = float(num_match.group())
                            if abs(actual_value - new_value) < 0.0001:
                                logger.info(f"  ✓ Value verified: {actual_value:.6f}")
                            else:
                                logger.error(f"  ✗ Value mismatch: expected {new_value:.6f}, got {actual_value:.6f}")
                    else:
                        logger.error(f"  ✗ Pattern not found after write!")
                    
                    # Clear cache for this file
                    cache_key = str(aiw_path)
                    if cache_key in self._aiw_ratio_cache:
                        del self._aiw_ratio_cache[cache_key]
                        logger.info(f"  Cleared cache for {cache_key}")
                    
                    logger.info(f"  ✓ UPDATE_RATIO: SUCCESS for {ratio_type}")
                    logger.info("=" * 60)
                    return True
                    
                except Exception as e:
                    logger.error(f"  Error writing file: {e}", exc_info=True)
                    return False
            else:
                logger.warning(f"  Content did not change after replacement attempt")
                logger.warning(f"  Pattern may not match correctly")
                return False
                    
        except Exception as e:
            logger.error(f"Error updating ratio in {aiw_path}: {e}", exc_info=True)
            return False

    def restore_original(self, aiw_path: Path, track_name: str) -> bool:
        """Restore the original AIW file"""
        try:
            original_backup = self.backup_dir / f"{track_name}_ORIGINAL{aiw_path.suffix}"
            
            if not original_backup.exists():
                return False
            
            shutil.copy2(original_backup, aiw_path)
            
            # Clear cache for this file
            cache_key = str(aiw_path)
            if cache_key in self._aiw_ratio_cache:
                del self._aiw_ratio_cache[cache_key]
            
            logger.info(f"Restored original from: {original_backup}")
            return True
            
        except Exception as e:
            logger.error(f"Error restoring original: {e}")
            return False
    
    def get_original_backup(self, aiw_path: Path) -> Optional[Path]:
        """Get the path to the original backup file"""
        track_name = aiw_path.stem
        original_backup = self.backup_dir / f"{track_name}_ORIGINAL{aiw_path.suffix}"
        
        if original_backup.exists():
            return original_backup
        return None
    
    def get_backup_info(self, aiw_path: Path, track_name: str) -> dict:
        """Get information about backups"""
        original = self.get_original_backup(aiw_path)
        
        return {
            'original_exists': original is not None,
            'original_path': str(original) if original else None,
            'backup_created': track_name in self.backup_created_for_track
        }
    
    def has_original_backup(self, aiw_path: Path, track_name: str) -> bool:
        """Check if original backup exists"""
        return track_name in self.backup_created_for_track or self.get_original_backup(aiw_path) is not None
