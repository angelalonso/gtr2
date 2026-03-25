"""
Race Results Parser - Extracts lap times and AI information from raceresults.txt
"""

import re
import logging
import os
from pathlib import Path
from typing import Optional, List, Dict
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class RaceResults:
    """Container for parsed race results"""
    track_name: Optional[str] = None
    aiw_file: Optional[str] = None
    aiw_path: Optional[Path] = None
    qual_ratio: Optional[float] = None
    race_ratio: Optional[float] = None
    best_ai_lap: Optional[str] = None
    worst_ai_lap: Optional[str] = None
    best_ai_driver: Optional[str] = None
    worst_ai_driver: Optional[str] = None
    user_best_lap: Optional[str] = None
    user_qualifying: Optional[str] = None
    user_name: Optional[str] = None
    drivers: List[Dict] = field(default_factory=list)
    
    def has_data(self) -> bool:
        """Check if we have any meaningful data"""
        return (self.best_ai_lap is not None or 
                self.user_best_lap is not None or
                self.user_qualifying is not None)
    
    def to_dict(self) -> dict:
        """Convert to dictionary for GUI"""
        return {
            'track_name': self.track_name,
            'aiw_file': self.aiw_file,
            'qual_ratio': self.qual_ratio,
            'race_ratio': self.race_ratio,
            'best_ai_lap': self.best_ai_lap,
            'worst_ai_lap': self.worst_ai_lap,
            'best_ai_driver': self.best_ai_driver,
            'worst_ai_driver': self.worst_ai_driver,
            'user_best_lap': self.user_best_lap,
            'user_qualifying': self.user_qualifying,
            'user_name': self.user_name,
            'drivers': self.drivers
        }


def parse_race_results(file_path: Path, base_path: Optional[Path] = None) -> Optional[RaceResults]:
    """
    Parse race results from raceresults.txt
    
    Args:
        file_path: Path to raceresults.txt
        base_path: Base game path for AIW file lookup
    
    Returns:
        RaceResults object or None if parsing failed
    """
    try:
        if not file_path.exists():
            logger.error(f"File not found: {file_path}")
            return None
        
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        results = RaceResults()
        
        # Parse header (Race section)
        race_match = re.search(r'\[Race\](.*?)(?=\[|$)', content, re.DOTALL)
        if race_match:
            race_section = race_match.group(1)
            
            # Track name
            scene_match = re.search(r'Scene=(.*?)(?:\n|$)', race_section, re.IGNORECASE)
            if scene_match:
                scene = scene_match.group(1).strip()
                track_name = Path(scene).stem
                track_name = re.sub(r'^\d+', '', track_name)
                results.track_name = track_name
            
            # AIW file - store as is, will handle case insensitivity later
            aiw_match = re.search(r'AIDB=(.*?)(?:\n|$)', race_section, re.IGNORECASE)
            if aiw_match:
                aiw_path_str = aiw_match.group(1).strip()
                results.aiw_path = Path(aiw_path_str)
                results.aiw_file = results.aiw_path.name
        
        # Parse driver slots
        slot_pattern = r'\[Slot(\d+)\](.*?)(?=\[Slot|\[END\]|$)'
        slots = re.findall(slot_pattern, content, re.DOTALL)
        
        ai_best_lap_seconds = float('inf')
        ai_worst_lap_seconds = -float('inf')
        ai_best_driver = None
        ai_worst_driver = None
        
        for slot_num, slot_content in slots:
            driver = {'slot': int(slot_num)}
            
            # Name
            name_match = re.search(r'Driver=(.*?)(?:\n|$)', slot_content)
            if name_match:
                driver['name'] = name_match.group(1).strip()
                if int(slot_num) == 0:
                    results.user_name = driver['name']
            
            # Qualifying time
            qual_match = re.search(r'QualTime=(.*?)(?:\n|$)', slot_content)
            if qual_match:
                driver['qual_time'] = qual_match.group(1).strip()
                if int(slot_num) == 0:
                    results.user_qualifying = driver['qual_time']
            
            # Best lap
            best_match = re.search(r'BestLap=(.*?)(?:\n|$)', slot_content)
            if best_match:
                driver['best_lap'] = best_match.group(1).strip()
                if int(slot_num) == 0:
                    results.user_best_lap = driver['best_lap']
            
            # Laps
            laps_match = re.search(r'Laps=(.*?)(?:\n|$)', slot_content)
            if laps_match:
                driver['laps'] = laps_match.group(1).strip()
            
            # Team
            team_match = re.search(r'Team=(.*?)(?:\n|$)', slot_content)
            if team_match:
                driver['team'] = team_match.group(1).strip()
            
            results.drivers.append(driver)
            
            # Track AI best/worst lap times
            if int(slot_num) != 0 and driver.get('best_lap'):
                lap_seconds = _time_to_seconds(driver['best_lap'])
                if lap_seconds:
                    if lap_seconds < ai_best_lap_seconds:
                        ai_best_lap_seconds = lap_seconds
                        ai_best_driver = driver
                    if lap_seconds > ai_worst_lap_seconds:
                        ai_worst_lap_seconds = lap_seconds
                        ai_worst_driver = driver
        
        if ai_best_driver:
            results.best_ai_lap = ai_best_driver['best_lap']
            results.best_ai_driver = ai_best_driver.get('name', 'Unknown')
        if ai_worst_driver:
            results.worst_ai_lap = ai_worst_driver['best_lap']
            results.worst_ai_driver = ai_worst_driver.get('name', 'Unknown')
        
        # Try to parse AIW file for ratios
        if results.aiw_file and base_path:
            _parse_aiw_ratios(results, base_path)
        
        logger.info(f"Parsed {len(results.drivers)} drivers from {file_path}")
        return results
        
    except Exception as e:
        logger.error(f"Error parsing race results: {e}", exc_info=True)
        return None


def _time_to_seconds(time_str: str) -> Optional[float]:
    """Convert time string to seconds"""
    if not time_str:
        return None
    
    try:
        if ':' in time_str:
            parts = time_str.split(':')
            minutes = int(parts[0])
            seconds = float(parts[1])
            return minutes * 60 + seconds
        else:
            return float(time_str)
    except (ValueError, IndexError):
        return None


def _parse_aiw_ratios(results: RaceResults, base_path: Path):
    """Parse AIW file to get QualRatio and RaceRatio with case-insensitive path handling"""
    try:
        # Find the AIW file with case-insensitive search
        aiw_path = _find_aiw_file_case_insensitive(results.aiw_file, results.track_name, base_path)
        
        if not aiw_path or not aiw_path.exists():
            logger.warning(f"AIW file not found: {results.aiw_file}")
            return
        
        logger.info(f"Found AIW file: {aiw_path}")
        
        # Read the AIW file
        with open(aiw_path, 'rb') as f:
            raw_content = f.read()
        
        # Decode (strip null bytes)
        content = raw_content.replace(b'\x00', b'').decode('utf-8', errors='ignore')
        
        # Find Waypoint section
        waypoint_match = re.search(r'\[Waypoint\](.*?)(?=\[|$)', content, re.DOTALL | re.IGNORECASE)
        if waypoint_match:
            waypoint_section = waypoint_match.group(1)
            
            # QualRatio
            quali_match = re.search(r'QualRatio\s*=\s*\(?([\d.]+)\)?', waypoint_section, re.IGNORECASE)
            if quali_match:
                results.qual_ratio = float(quali_match.group(1))
            
            # RaceRatio
            race_match = re.search(r'RaceRatio\s*=\s*\(?([\d.]+)\)?', waypoint_section, re.IGNORECASE)
            if race_match:
                results.race_ratio = float(race_match.group(1))
        
        logger.info(f"Ratios - Qual: {results.qual_ratio}, Race: {results.race_ratio}")
        
    except Exception as e:
        logger.error(f"Error parsing AIW file: {e}", exc_info=True)


def _find_aiw_file_case_insensitive(aiw_filename: str, track_name: str, base_path: Path) -> Optional[Path]:
    """
    Find AIW file with case-insensitive search
    Handles paths like GAMEDATA\LOCATIONS\Monza\4Monza.AIW -> GameData/Locations/Monza/4Monza.AIW
    """
    # First, try to construct the path from the filename and track name
    locations_path = base_path / 'GameData' / 'Locations'
    
    if not locations_path.exists():
        logger.warning(f"Locations path not found: {locations_path}")
        return None
    
    # Try different path variations
    possible_paths = []
    
    # Variation 1: Use track name with case-insensitive folder search
    if track_name:
        # Try to find the track folder case-insensitively
        for track_folder in locations_path.iterdir():
            if track_folder.is_dir() and track_folder.name.lower() == track_name.lower():
                # Look for AIW files in this folder
                for ext in ['.AIW', '.aiw', '.AIw']:
                    candidate = track_folder / f"{track_folder.name}{ext}"
                    if candidate.exists():
                        return candidate
                    
                    # Also try with the original filename
                    if aiw_filename:
                        candidate = track_folder / aiw_filename
                        if candidate.exists():
                            return candidate
                        
                        # Try different case combinations
                        for file in track_folder.glob('*.AIW'):
                            if file.name.lower() == aiw_filename.lower():
                                return file
    
    # Variation 2: Search recursively in GameData/Locations for any matching AIW file
    for root, dirs, files in os.walk(locations_path):
        for file in files:
            if file.lower() == aiw_filename.lower():
                return Path(root) / file
    
    # Variation 3: Try to reconstruct path from the original AIW path string
    if aiw_filename:
        # The path might be like "GAMEDATA\LOCATIONS\Monza\4Monza.AIW"
        # Convert to proper case by walking the directory structure
        path_parts = aiw_filename.replace('\\', '/').split('/')
        
        # Start from base_path
        current_path = base_path
        
        for part in path_parts[:-1]:  # Exclude the filename
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
                # Create the folder if it doesn't exist (should exist in game)
                current_path = current_path / part
                if not current_path.exists():
                    logger.warning(f"Path not found: {current_path}")
                    break
        
        # Check if the file exists
        candidate = current_path / path_parts[-1]
        if candidate.exists():
            return candidate
        
        # Try to find any file with matching name in the final directory
        if current_path.exists():
            for file in current_path.glob('*'):
                if file.name.lower() == path_parts[-1].lower():
                    return file
    
    return None


import os
