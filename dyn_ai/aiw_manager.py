"""
AIW File Manager - Reading, writing, and backing up AIW files
OPTIMIZED: Reduced file operations, caching, and lazy loading
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
        """Find AIW file with caching"""
        cache_key = f"{track_name}_{aiw_filename}".lower()
        
        if cache_key in self._aiw_path_cache:
            cached_path = self._aiw_path_cache[cache_key]
            if cached_path.exists():
                return cached_path
            else:
                del self._aiw_path_cache[cache_key]
        
        locations_path = base_path / 'GameData' / 'Locations'
        
        if not locations_path.exists():
            return None
        
        found_path = None
        
        # Strategy 1: Use track name with case-insensitive folder search
        if track_name:
            track_lower = track_name.lower()
            try:
                for track_folder in locations_path.iterdir():
                    if track_folder.is_dir() and track_folder.name.lower() == track_lower:
                        # Look for AIW files
                        for file in track_folder.glob('*'):
                            if file.is_file() and file.name.lower() == aiw_filename.lower():
                                found_path = file
                                break
                        
                        if not found_path:
                            for ext in ['.AIW', '.aiw']:
                                candidate = track_folder / f"{track_folder.name}{ext}"
                                if candidate.exists():
                                    found_path = candidate
                                    break
                        
                        if found_path:
                            break
            except OSError:
                pass
        
        # Strategy 2: Search recursively
        if not found_path:
            try:
                for root, dirs, files in os.walk(locations_path):
                    for file in files:
                        if file.lower() == aiw_filename.lower():
                            found_path = Path(root) / file
                            break
                    if found_path:
                        break
            except OSError:
                pass
        
        if found_path:
            self._aiw_path_cache[cache_key] = found_path
        
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
        """Update a single ratio in the AIW file"""
        try:
            if create_backup:
                original_backup = self.create_backup_before_modification(aiw_path, track_name)
            
            with open(aiw_path, 'rb') as f:
                raw_content = f.read()
            
            content = raw_content.replace(b'\x00', b'').decode('utf-8', errors='ignore')
            
            pattern = rf'({ratio_type}\s*=\s*\(?)\s*[0-9.eE+-]+\s*(\)?)'
            
            def replacer(m):
                return f"{m.group(1)}{new_value:.6f}{m.group(2)}"
            
            new_content = re.sub(pattern, replacer, content, flags=re.IGNORECASE)
            
            if new_content != content:
                with open(aiw_path, 'wb') as f:
                    f.write(new_content.encode('utf-8', errors='ignore'))
                
                # Clear cache for this file
                cache_key = str(aiw_path)
                if cache_key in self._aiw_ratio_cache:
                    del self._aiw_ratio_cache[cache_key]
                
                logger.info(f"Updated {ratio_type} in {aiw_path.name} to {new_value:.6f}")
                return True
            else:
                logger.warning(f"Pattern not found for {ratio_type} in {aiw_path.name}")
                return False
                
        except Exception as e:
            logger.error(f"Error updating ratio in {aiw_path}: {e}")
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
