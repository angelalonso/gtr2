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
    track_folder: Optional[str] = None  # Store the actual folder name
    aiw_file: Optional[str] = None
    aiw_path: Optional[Path] = None
    qual_ratio: Optional[float] = None
    race_ratio: Optional[float] = None
    
    # AI lap times - Qualifying (as strings for display)
    qual_best_ai_lap: Optional[str] = None
    qual_worst_ai_lap: Optional[str] = None
    qual_best_ai_driver: Optional[str] = None
    qual_worst_ai_driver: Optional[str] = None
    
    # AI lap times - Qualifying (as seconds for calculations)
    qual_best_ai_lap_sec: float = 0.0
    qual_worst_ai_lap_sec: float = 0.0
    
    # AI lap times - Race (as strings for display)
    best_ai_lap: Optional[str] = None
    worst_ai_lap: Optional[str] = None
    best_ai_driver: Optional[str] = None
    worst_ai_driver: Optional[str] = None
    
    # AI lap times - Race (as seconds for calculations)
    best_ai_lap_sec: float = 0.0
    worst_ai_lap_sec: float = 0.0
    
    user_best_lap: Optional[str] = None
    user_qualifying: Optional[str] = None
    user_name: Optional[str] = None
    drivers: List[Dict] = field(default_factory=list)
    
    def has_data(self) -> bool:
        """Check if we have any meaningful data"""
        return (self.best_ai_lap is not None or 
                self.qual_best_ai_lap is not None or
                self.user_best_lap is not None or
                self.user_qualifying is not None)
    
    def to_dict(self) -> dict:
        """Convert to dictionary for GUI"""
        return {
            'track_name': self.track_name,
            'track_folder': self.track_folder,
            'aiw_file': self.aiw_file,
            'qual_ratio': self.qual_ratio,
            'race_ratio': self.race_ratio,
            # Qualifying AI times (strings for display)
            'qual_best_ai_lap': self.qual_best_ai_lap,
            'qual_worst_ai_lap': self.qual_worst_ai_lap,
            'qual_best_ai_driver': self.qual_best_ai_driver,
            'qual_worst_ai_driver': self.qual_worst_ai_driver,
            # Qualifying AI times (seconds for calculations)
            'qual_best_ai_lap_sec': self.qual_best_ai_lap_sec,
            'qual_worst_ai_lap_sec': self.qual_worst_ai_lap_sec,
            # Race AI times (strings for display)
            'best_ai_lap': self.best_ai_lap,
            'worst_ai_lap': self.worst_ai_lap,
            'best_ai_driver': self.best_ai_driver,
            'worst_ai_driver': self.worst_ai_driver,
            # Race AI times (seconds for calculations)
            'best_ai_lap_sec': self.best_ai_lap_sec,
            'worst_ai_lap_sec': self.worst_ai_lap_sec,
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
            
            # Track name - extract from Scene
            scene_match = re.search(r'Scene=(.*?)(?:\n|$)', race_section, re.IGNORECASE)
            if scene_match:
                scene = scene_match.group(1).strip()
                # scene is like "GAMEDATA\LOCATIONS\Monza\4Monza.TRK"
                # or "GameData/Locations/Monza/4Monza.trk"
                
                # Convert backslashes to forward slashes for consistent handling
                scene_normalized = scene.replace('\\', '/')
                
                # Extract the track folder name (the part before the filename)
                # Path like: .../Locations/Monza/4Monza.TRK
                scene_path = Path(scene_normalized)
                
                # The track folder is the parent directory of the TRK file
                # e.g., "Monza"
                track_folder = scene_path.parent.name
                results.track_folder = track_folder
                
                # Clean track name - remove numbers prefix if present
                track_name = scene_path.stem
                track_name = re.sub(r'^\d+', '', track_name)
                results.track_name = track_name
                
                logger.info(f"Track: {results.track_name} (folder: {results.track_folder})")
                logger.info(f"Scene: {scene}")
            
            # AIW file - store the raw path, we'll handle case insensitivity in finder
            aiw_match = re.search(r'AIDB=(.*?)(?:\n|$)', race_section, re.IGNORECASE)
            if aiw_match:
                aiw_path_str = aiw_match.group(1).strip()
                results.aiw_path = Path(aiw_path_str)
                results.aiw_file = results.aiw_path.name
                logger.info(f"AIW file from results: {results.aiw_file}")
        
        # Parse driver slots
        slot_pattern = r'\[Slot(\d+)\](.*?)(?=\[Slot|\[END\]|$)'
        slots = re.findall(slot_pattern, content, re.DOTALL)
        
        # Track AI best/worst lap times (Race)
        race_best_lap_seconds = float('inf')
        race_worst_lap_seconds = -float('inf')
        race_best_driver = None
        race_worst_driver = None
        race_best_lap_str = None
        race_worst_lap_str = None
        
        # Track AI best/worst lap times (Qualifying)
        qual_best_lap_seconds = float('inf')
        qual_worst_lap_seconds = -float('inf')
        qual_best_driver = None
        qual_worst_driver = None
        qual_best_lap_str = None
        qual_worst_lap_str = None
        
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
            
            # Best lap (Race)
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
            
            # Track AI race best/worst lap times (from BestLap)
            if int(slot_num) != 0 and driver.get('best_lap'):
                lap_seconds = _time_to_seconds(driver['best_lap'])
                if lap_seconds:
                    if lap_seconds < race_best_lap_seconds:
                        race_best_lap_seconds = lap_seconds
                        race_best_driver = driver
                        race_best_lap_str = driver['best_lap']
                    if lap_seconds > race_worst_lap_seconds:
                        race_worst_lap_seconds = lap_seconds
                        race_worst_driver = driver
                        race_worst_lap_str = driver['best_lap']
            
            # Track AI qualifying best/worst lap times
            if int(slot_num) != 0 and driver.get('qual_time'):
                qual_seconds = _time_to_seconds(driver['qual_time'])
                if qual_seconds:
                    if qual_seconds < qual_best_lap_seconds:
                        qual_best_lap_seconds = qual_seconds
                        qual_best_driver = driver
                        qual_best_lap_str = driver['qual_time']
                    if qual_seconds > qual_worst_lap_seconds:
                        qual_worst_lap_seconds = qual_seconds
                        qual_worst_driver = driver
                        qual_worst_lap_str = driver['qual_time']
        
        # Set race AI times
        if race_best_driver:
            results.best_ai_lap = race_best_lap_str
            results.best_ai_driver = race_best_driver.get('name', 'Unknown')
            results.best_ai_lap_sec = race_best_lap_seconds if race_best_lap_seconds != float('inf') else 0.0
        if race_worst_driver:
            results.worst_ai_lap = race_worst_lap_str
            results.worst_ai_driver = race_worst_driver.get('name', 'Unknown')
            results.worst_ai_lap_sec = race_worst_lap_seconds if race_worst_lap_seconds != -float('inf') else 0.0
        
        # Set qualifying AI times
        if qual_best_driver:
            results.qual_best_ai_lap = qual_best_lap_str
            results.qual_best_ai_driver = qual_best_driver.get('name', 'Unknown')
            results.qual_best_ai_lap_sec = qual_best_lap_seconds if qual_best_lap_seconds != float('inf') else 0.0
        if qual_worst_driver:
            results.qual_worst_ai_lap = qual_worst_lap_str
            results.qual_worst_ai_driver = qual_worst_driver.get('name', 'Unknown')
            results.qual_worst_ai_lap_sec = qual_worst_lap_seconds if qual_worst_lap_seconds != -float('inf') else 0.0
        
        # Try to parse AIW file for ratios
        if results.aiw_file and base_path:
            # Use track_folder for better matching (this is the actual folder name like "Monza")
            _parse_aiw_ratios(results, base_path)
        
        logger.info(f"Parsed {len(results.drivers)} drivers from {file_path}")
        logger.info(f"Race AI - Best: {results.best_ai_lap} ({results.best_ai_lap_sec:.3f}s), Worst: {results.worst_ai_lap} ({results.worst_ai_lap_sec:.3f}s)")
        logger.info(f"Qual AI - Best: {results.qual_best_ai_lap} ({results.qual_best_ai_lap_sec:.3f}s), Worst: {results.qual_worst_ai_lap} ({results.qual_worst_ai_lap_sec:.3f}s)")
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
    """Parse AIW file to get QualRatio and RaceRatio"""
    try:
        # Use track_folder (like "Monza") for finding the AIW file
        track_folder = results.track_folder
        if not track_folder:
            track_folder = results.track_name
        
        # Find the AIW file using our case-insensitive finder
        aiw_path = _find_aiw_file_case_insensitive(results.aiw_file, track_folder, base_path)
        
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


def _find_aiw_file_case_insensitive(aiw_filename: str, track_folder: str, base_path: Path) -> Optional[Path]:
    """
    Find AIW file with case-insensitive search.
    This version works with the actual folder name like "Monza".
    """
    locations_path = base_path / 'GameData' / 'Locations'
    
    if not locations_path.exists():
        logger.warning(f"Locations path not found: {locations_path}")
        return None
    
    # Strategy 1: Look in the track folder (case-insensitive)
    if track_folder:
        for folder in locations_path.iterdir():
            if folder.is_dir() and folder.name.lower() == track_folder.lower():
                # Found the correct folder
                logger.info(f"Found track folder: {folder}")
                
                # Look for the AIW file (case-insensitive)
                for file in folder.glob('*'):
                    if file.is_file() and file.name.lower() == aiw_filename.lower():
                        logger.info(f"Found AIW file: {file}")
                        return file
                
                # Also try common naming patterns (folder name + .AIW)
                for ext in ['.AIW', '.aiw', '.AIw']:
                    candidate = folder / f"{folder.name}{ext}"
                    if candidate.exists():
                        logger.info(f"Found AIW file via folder name: {candidate}")
                        return candidate
                
                # Look for any AIW file in the folder
                for file in folder.glob('*.AIW'):
                    return file
                for file in folder.glob('*.aiw'):
                    return file
    
    # Strategy 2: Search recursively through all locations
    for root, dirs, files in os.walk(locations_path):
        for file in files:
            if file.lower() == aiw_filename.lower():
                found_path = Path(root) / file
                logger.info(f"Found AIW file via recursive search: {found_path}")
                return found_path
    
    # Strategy 3: Try to reconstruct path from the original AIW path string
    # The path might be like "GAMEDATA\LOCATIONS\Monza\4Monza.AIW"
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


import os
