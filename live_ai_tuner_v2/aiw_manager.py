"""
AIW File Manager - Reading, writing, and backing up AIW files
"""

import os
import re
import shutil
import logging
from pathlib import Path
from typing import Optional, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)


class AIWManager:
    """Manages AIW file operations"""
    
    def __init__(self, backup_dir: Path = None):
        self.backup_dir = Path(backup_dir) if backup_dir else Path("./backups")
        self.backup_dir.mkdir(parents=True, exist_ok=True)
    
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
        # The path might be like "GAMEDATA\LOCATIONS\Monza\4Monza.AIW"
        # Convert to proper case by walking the directory structure
        if aiw_filename:
            # Clean up the path
            clean_path = aiw_filename.replace('\\', '/')
            path_parts = clean_path.split('/')
            
            # Start from base_path
            current_path = base_path
            
            for i, part in enumerate(path_parts[:-1]):  # Exclude the filename
                # Try to find the folder case-insensitively
                found = False
                part_lower = part.lower()
                
                if current_path.exists():
                    for item in current_path.iterdir():
                        if item.is_dir() and item.name.lower() == part_lower:
                            current_path = item
                            found = True
                            break
                
                if not found:
                    # Try with the original case
                    candidate = current_path / part
                    if candidate.exists() and candidate.is_dir():
                        current_path = candidate
                        found = True
                
                if not found:
                    logger.debug(f"Could not find path component: {part}")
                    break
            
            # Check if the file exists
            candidate = current_path / path_parts[-1]
            if candidate.exists() and candidate.is_file():
                logger.info(f"Found AIW file via path reconstruction: {candidate}")
                return candidate
            
            # Try to find any file with matching name in the final directory
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
            
            # Remove null bytes and decode
            content = raw_content.replace(b'\x00', b'').decode('utf-8', errors='ignore')
            
            qual_ratio = None
            race_ratio = None
            
            # Find Waypoint section
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
    
    def update_ratio(self, aiw_path: Path, ratio_type: str, new_value: float) -> bool:
        """
        Update a single ratio in the AIW file
        
        Args:
            aiw_path: Path to AIW file
            ratio_type: "QualRatio" or "RaceRatio"
            new_value: New ratio value
        
        Returns:
            True if successful
        """
        try:
            with open(aiw_path, 'rb') as f:
                raw_content = f.read()
            
            content = raw_content.replace(b'\x00', b'').decode('utf-8', errors='ignore')
            
            # Pattern to match the ratio
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
    
    def create_backup(self, aiw_path: Path) -> Optional[Path]:
        """
        Create a backup of the AIW file
        
        Returns:
            Path to backup file or None if failed
        """
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = self.backup_dir / f"{aiw_path.stem}_{timestamp}{aiw_path.suffix}"
            
            shutil.copy2(aiw_path, backup_path)
            logger.info(f"Created backup: {backup_path}")
            return backup_path
            
        except Exception as e:
            logger.error(f"Error creating backup: {e}")
            return None
    
    def restore_from_backup(self, aiw_path: Path, backup_path: Path) -> bool:
        """
        Restore AIW file from backup
        
        Returns:
            True if successful
        """
        try:
            if not backup_path.exists():
                logger.error(f"Backup file not found: {backup_path}")
                return False
            
            shutil.copy2(backup_path, aiw_path)
            logger.info(f"Restored from backup: {backup_path} -> {aiw_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error restoring from backup: {e}")
            return False
    
    def get_latest_backup(self, aiw_path: Path) -> Optional[Path]:
        """
        Get the most recent backup for an AIW file
        
        Returns:
            Path to latest backup or None
        """
        backups = list(self.backup_dir.glob(f"{aiw_path.stem}_*{aiw_path.suffix}"))
        if backups:
            return max(backups, key=lambda p: p.stat().st_mtime)
        return None


import os
