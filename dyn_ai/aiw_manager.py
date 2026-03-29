"""
AIW File Manager - Reading, writing, and backing up AIW files
"""

import re
import shutil
import logging
from pathlib import Path
from typing import Optional, Tuple, List
from datetime import datetime

logger = logging.getLogger(__name__)


class AIWManager:
    """Manages AIW file operations with proper backup preservation"""
    
    def __init__(self, backup_dir: Path = None):
        self.backup_dir = Path(backup_dir) if backup_dir else Path("./backups")
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        # Track which tracks have had their original backup created
        self.backup_created_for_track = set()
    
    def find_aiw_file(self, aiw_filename: str, track_name: str, base_path: Path) -> Optional[Path]:
        """
        Find the AIW file in the game directory with case-insensitive search
        
        Args:
            aiw_filename: Name of the AIW file (e.g., "4Monza.AIW")
            track_name: Name of the track
            base_path: Base game path
        
        Returns:
            Path to AIW file or None if not found
        """
        locations_path = base_path / 'GameData' / 'Locations'
        
        if not locations_path.exists():
            logger.warning(f"Locations path not found: {locations_path}")
            return None
        
        # Try different search strategies
        
        # Strategy 1: Use track name with case-insensitive folder search
        if track_name:
            for track_folder in locations_path.iterdir():
                if track_folder.is_dir() and track_folder.name.lower() == track_name.lower():
                    # Look for AIW files in this folder
                    for file in track_folder.glob('*'):
                        if file.is_file() and file.name.lower() == aiw_filename.lower():
                            logger.info(f"Found AIW file via track folder: {file}")
                            return file
                    
                    # Also try common naming patterns
                    for ext in ['.AIW', '.aiw', '.AIw']:
                        candidate = track_folder / f"{track_folder.name}{ext}"
                        if candidate.exists():
                            logger.info(f"Found AIW file via track name: {candidate}")
                            return candidate
        
        # Strategy 2: Search recursively in GameData/Locations
        for root, dirs, files in os.walk(locations_path):
            for file in files:
                if file.lower() == aiw_filename.lower():
                    found_path = Path(root) / file
                    logger.info(f"Found AIW file via recursive search: {found_path}")
                    return found_path
        
        # Strategy 3: Try to reconstruct path from the original AIW path string
        if aiw_filename:
            clean_path = aiw_filename.replace('\\', '/')
            path_parts = clean_path.split('/')
            
            current_path = base_path
            
            for i, part in enumerate(path_parts[:-1]):
                found = False
                part_lower = part.lower()
                
                if current_path.exists():
                    for item in current_path.iterdir():
                        if item.is_dir() and item.name.lower() == part_lower:
                            current_path = item
                            found = True
                            break
                
                if not found:
                    candidate = current_path / part
                    if candidate.exists() and candidate.is_dir():
                        current_path = candidate
                        found = True
                
                if not found:
                    logger.debug(f"Could not find path component: {part}")
                    break
            
            candidate = current_path / path_parts[-1]
            if candidate.exists() and candidate.is_file():
                logger.info(f"Found AIW file via path reconstruction: {candidate}")
                return candidate
            
            if current_path.exists():
                for file in current_path.glob('*'):
                    if file.is_file() and file.name.lower() == path_parts[-1].lower():
                        logger.info(f"Found AIW file via filename match: {file}")
                        return file
        
        logger.warning(f"AIW file not found: {aiw_filename}")
        return None
    
    def read_ratios(self, aiw_path: Path) -> Tuple[Optional[float], Optional[float]]:
        """
        Read QualRatio and RaceRatio from AIW file
        
        Returns:
            Tuple of (qual_ratio, race_ratio)
        """
        try:
            if not aiw_path.exists():
                logger.error(f"AIW file not found: {aiw_path}")
                return None, None
            
            with open(aiw_path, 'rb') as f:
                raw_content = f.read()
            
            content = raw_content.replace(b'\x00', b'').decode('utf-8', errors='ignore')
            
            qual_ratio = None
            race_ratio = None
            
            waypoint_match = re.search(r'\[Waypoint\](.*?)(?=\[|$)', content, re.DOTALL | re.IGNORECASE)
            if waypoint_match:
                waypoint_section = waypoint_match.group(1)
                
                quali_match = re.search(r'QualRatio\s*=\s*\(?([\d.]+)\)?', waypoint_section, re.IGNORECASE)
                if quali_match:
                    qual_ratio = float(quali_match.group(1))
                
                race_match = re.search(r'RaceRatio\s*=\s*\(?([\d.]+)\)?', waypoint_section, re.IGNORECASE)
                if race_match:
                    race_ratio = float(race_match.group(1))
            
            logger.info(f"Read ratios from {aiw_path.name}: Qual={qual_ratio}, Race={race_ratio}")
            return qual_ratio, race_ratio
            
        except Exception as e:
            logger.error(f"Error reading AIW file {aiw_path}: {e}")
            return None, None
    
    def create_original_backup(self, aiw_path: Path, track_name: str) -> Optional[Path]:
        """
        Create a backup of the original AIW file (only once per track, never overwrite)
        
        Args:
            aiw_path: Path to AIW file
            track_name: Name of the track for tracking
        
        Returns:
            Path to backup file or None if failed
        """
        try:
            if not aiw_path.exists():
                logger.error(f"AIW file not found: {aiw_path}")
                return None
            
            # Check if we've already created backup for this track
            if track_name in self.backup_created_for_track:
                logger.info(f"Original backup already created for track {track_name}, skipping")
                return self.get_original_backup(aiw_path)
            
            # Create a permanent original backup filename
            # Format: {track_name}_ORIGINAL{extension}
            original_backup_name = f"{track_name}_ORIGINAL{aiw_path.suffix}"
            original_backup_path = self.backup_dir / original_backup_name
            
            # Only create backup if it doesn't exist
            if not original_backup_path.exists():
                shutil.copy2(aiw_path, original_backup_path)
                self.backup_created_for_track.add(track_name)
                logger.info(f"Created original backup: {original_backup_path}")
                return original_backup_path
            else:
                self.backup_created_for_track.add(track_name)
                logger.info(f"Original backup already exists: {original_backup_path}")
                return original_backup_path
                
        except Exception as e:
            logger.error(f"Error creating original backup: {e}")
            return None
    
    def create_backup_before_modification(self, aiw_path: Path, track_name: str) -> Optional[Path]:
        """
        Create original backup only if not already created for this track
        
        Args:
            aiw_path: Path to AIW file
            track_name: Name of the track
        
        Returns:
            Path to original backup or None if failed
        """
        # Only create original backup, no timestamp backups
        return self.create_original_backup(aiw_path, track_name)
    
    def update_ratio(self, aiw_path: Path, ratio_type: str, new_value: float, 
                     track_name: str, create_backup: bool = True) -> bool:
        """
        Update a single ratio in the AIW file
        
        Args:
            aiw_path: Path to AIW file
            ratio_type: "QualRatio" or "RaceRatio"
            new_value: New ratio value
            track_name: Name of the track
            create_backup: Whether to create backup before modifying
        
        Returns:
            True if successful
        """
        try:
            # Create original backup before modification if requested and not already created
            if create_backup:
                original_backup = self.create_backup_before_modification(aiw_path, track_name)
                if original_backup:
                    logger.info(f"Original backup: {original_backup}")
            
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
                logger.info(f"Updated {ratio_type} in {aiw_path.name} to {new_value:.6f}")
                return True
            else:
                logger.warning(f"Pattern not found for {ratio_type} in {aiw_path.name}")
                return False
                
        except Exception as e:
            logger.error(f"Error updating ratio in {aiw_path}: {e}")
            return False
    
    def restore_original(self, aiw_path: Path, track_name: str) -> bool:
        """
        Restore the original AIW file from the permanent original backup
        
        Args:
            aiw_path: Path to AIW file
            track_name: Name of the track
        
        Returns:
            True if successful
        """
        try:
            original_backup = self.backup_dir / f"{track_name}_ORIGINAL{aiw_path.suffix}"
            
            if not original_backup.exists():
                logger.error(f"Original backup not found: {original_backup}")
                return False
            
            # Restore from original
            shutil.copy2(original_backup, aiw_path)
            logger.info(f"Restored original from: {original_backup}")
            return True
            
        except Exception as e:
            logger.error(f"Error restoring original: {e}")
            return False
    
    def get_original_backup(self, aiw_path: Path) -> Optional[Path]:
        """
        Get the path to the original backup file
        
        Returns:
            Path to original backup or None if not found
        """
        track_name = aiw_path.stem
        original_backup = self.backup_dir / f"{track_name}_ORIGINAL{aiw_path.suffix}"
        
        if original_backup.exists():
            return original_backup
        return None
    
    def get_backup_info(self, aiw_path: Path, track_name: str) -> dict:
        """
        Get information about backups for an AIW file
        
        Returns:
            Dictionary with backup information
        """
        original = self.get_original_backup(aiw_path)
        
        info = {
            'original_exists': original is not None,
            'original_path': str(original) if original else None,
            'backup_created': track_name in self.backup_created_for_track
        }
        
        return info
    
    def has_original_backup(self, aiw_path: Path, track_name: str) -> bool:
        """Check if original backup exists"""
        return track_name in self.backup_created_for_track or self.get_original_backup(aiw_path) is not None


import os
