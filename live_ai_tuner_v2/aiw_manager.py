"""
AIW File Manager - Reading, writing, and backing up AIW files
"""

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
        Find the AIW file in the game directory
        
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
        
        # Search recursively for the exact filename
        for root, dirs, files in os.walk(locations_path):
            for file in files:
                if file.lower() == aiw_filename.lower():
                    found_path = Path(root) / file
                    logger.info(f"Found AIW file: {found_path}")
                    return found_path
        
        # Try with track name variations
        if track_name:
            track_variations = [
                track_name,
                track_name.lower(),
                track_name.capitalize(),
                track_name.title(),
                f"4{track_name}",
                f"4{track_name.lower()}"
            ]
            
            for variation in set(track_variations):
                track_path = locations_path / variation
                if track_path.exists():
                    for ext in ['.AIW', '.aiw', '.AIw']:
                        candidate = track_path / f"{variation}{ext}"
                        if candidate.exists():
                            logger.info(f"Found AIW file via track folder: {candidate}")
                            return candidate
                    
                    # Also search for any AIW file in the folder
                    for file in track_path.glob('*.AIW'):
                        return file
                    for file in track_path.glob('*.aiw'):
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
