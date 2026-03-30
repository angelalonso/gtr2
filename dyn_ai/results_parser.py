"""
Race Results Parser - Extracts lap times and AI information from raceresults.txt
OPTIMIZED: Faster regex, reduced allocations
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
    """Container for parsed race results - OPTIMIZED"""
    track_name: Optional[str] = None
    track_folder: Optional[str] = None
    aiw_file: Optional[str] = None
    aiw_path: Optional[Path] = None
    qual_ratio: Optional[float] = None
    race_ratio: Optional[float] = None
    
    # AI lap times - Qualifying (as seconds for calculations)
    qual_best_ai_lap_sec: float = 0.0
    qual_worst_ai_lap_sec: float = 0.0
    qual_best_ai_lap: Optional[str] = None
    qual_worst_ai_lap: Optional[str] = None
    
    # AI lap times - Race (as seconds for calculations)
    best_ai_lap_sec: float = 0.0
    worst_ai_lap_sec: float = 0.0
    best_ai_lap: Optional[str] = None
    worst_ai_lap: Optional[str] = None
    
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
            'qual_best_ai_lap': self.qual_best_ai_lap,
            'qual_worst_ai_lap': self.qual_worst_ai_lap,
            'qual_best_ai_lap_sec': self.qual_best_ai_lap_sec,
            'qual_worst_ai_lap_sec': self.qual_worst_ai_lap_sec,
            'best_ai_lap': self.best_ai_lap,
            'worst_ai_lap': self.worst_ai_lap,
            'best_ai_lap_sec': self.best_ai_lap_sec,
            'worst_ai_lap_sec': self.worst_ai_lap_sec,
            'user_best_lap': self.user_best_lap,
            'user_qualifying': self.user_qualifying,
            'user_name': self.user_name,
            'drivers': self.drivers
        }


# Pre-compiled regex patterns for better performance
_SCENE_PATTERN = re.compile(r'Scene=(.*?)(?:\n|$)', re.IGNORECASE)
_AIDB_PATTERN = re.compile(r'AIDB=(.*?)(?:\n|$)', re.IGNORECASE)
_SLOT_PATTERN = re.compile(r'\[Slot(\d+)\](.*?)(?=\[Slot|\[END\]|$)', re.DOTALL)
_DRIVER_PATTERN = re.compile(r'Driver=(.*?)(?:\n|$)', re.IGNORECASE)
_QUAL_TIME_PATTERN = re.compile(r'QualTime=(.*?)(?:\n|$)', re.IGNORECASE)
_BEST_LAP_PATTERN = re.compile(r'BestLap=(.*?)(?:\n|$)', re.IGNORECASE)
_LAPS_PATTERN = re.compile(r'Laps=(.*?)(?:\n|$)', re.IGNORECASE)
_TEAM_PATTERN = re.compile(r'Team=(.*?)(?:\n|$)', re.IGNORECASE)


def parse_race_results(file_path: Path, base_path: Optional[Path] = None) -> Optional[RaceResults]:
    """
    Parse race results from raceresults.txt - OPTIMIZED
    """
    try:
        if not file_path.exists():
            logger.error(f"File not found: {file_path}")
            return None
        
        # Read file once
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        results = RaceResults()
        
        # Parse header (Race section) - use pre-compiled patterns
        race_match = re.search(r'\[Race\](.*?)(?=\[|$)', content, re.DOTALL)
        if race_match:
            race_section = race_match.group(1)
            
            scene_match = _SCENE_PATTERN.search(race_section)
            if scene_match:
                scene = scene_match.group(1).strip()
                scene_normalized = scene.replace('\\', '/')
                scene_path = Path(scene_normalized)
                results.track_folder = scene_path.parent.name
                
                track_name = scene_path.stem
                track_name = re.sub(r'^\d+', '', track_name)
                results.track_name = track_name
                logger.info(f"Track: {results.track_name} (folder: {results.track_folder})")
            
            aiw_match = _AIDB_PATTERN.search(race_section)
            if aiw_match:
                aiw_path_str = aiw_match.group(1).strip()
                results.aiw_path = Path(aiw_path_str)
                results.aiw_file = results.aiw_path.name
                logger.info(f"AIW file from results: {results.aiw_file}")
        
        # Parse driver slots - use pre-compiled pattern
        slots = _SLOT_PATTERN.findall(content)
        
        # Optimize: Use local variables for better performance
        race_best_sec = float('inf')
        race_worst_sec = -float('inf')
        race_best_str = None
        race_worst_str = None
        
        qual_best_sec = float('inf')
        qual_worst_sec = -float('inf')
        qual_best_str = None
        qual_worst_str = None
        
        for slot_num, slot_content in slots:
            driver = {'slot': int(slot_num)}
            
            name_match = _DRIVER_PATTERN.search(slot_content)
            if name_match:
                driver['name'] = name_match.group(1).strip()
                if int(slot_num) == 0:
                    results.user_name = driver['name']
            
            qual_match = _QUAL_TIME_PATTERN.search(slot_content)
            if qual_match:
                driver['qual_time'] = qual_match.group(1).strip()
                if int(slot_num) == 0:
                    results.user_qualifying = driver['qual_time']
            
            best_match = _BEST_LAP_PATTERN.search(slot_content)
            if best_match:
                driver['best_lap'] = best_match.group(1).strip()
                if int(slot_num) == 0:
                    results.user_best_lap = driver['best_lap']
            
            laps_match = _LAPS_PATTERN.search(slot_content)
            if laps_match:
                driver['laps'] = laps_match.group(1).strip()
            
            team_match = _TEAM_PATTERN.search(slot_content)
            if team_match:
                driver['team'] = team_match.group(1).strip()
            
            results.drivers.append(driver)
            
            # Process AI times - only for non-user drivers
            if int(slot_num) != 0:
                if driver.get('best_lap'):
                    lap_sec = _time_to_seconds(driver['best_lap'])
                    if lap_sec:
                        if lap_sec < race_best_sec:
                            race_best_sec = lap_sec
                            race_best_str = driver['best_lap']
                        if lap_sec > race_worst_sec:
                            race_worst_sec = lap_sec
                            race_worst_str = driver['best_lap']
                
                if driver.get('qual_time'):
                    qual_sec = _time_to_seconds(driver['qual_time'])
                    if qual_sec:
                        if qual_sec < qual_best_sec:
                            qual_best_sec = qual_sec
                            qual_best_str = driver['qual_time']
                        if qual_sec > qual_worst_sec:
                            qual_worst_sec = qual_sec
                            qual_worst_str = driver['qual_time']
        
        # Set race AI times
        if race_best_str:
            results.best_ai_lap = race_best_str
            results.best_ai_lap_sec = race_best_sec if race_best_sec != float('inf') else 0.0
        if race_worst_str:
            results.worst_ai_lap = race_worst_str
            results.worst_ai_lap_sec = race_worst_sec if race_worst_sec != -float('inf') else 0.0
        
        # Set qualifying AI times
        if qual_best_str:
            results.qual_best_ai_lap = qual_best_str
            results.qual_best_ai_lap_sec = qual_best_sec if qual_best_sec != float('inf') else 0.0
        if qual_worst_str:
            results.qual_worst_ai_lap = qual_worst_str
            results.qual_worst_ai_lap_sec = qual_worst_sec if qual_worst_sec != -float('inf') else 0.0
        
        # Parse AIW ratios if needed
        if results.aiw_file and base_path:
            _parse_aiw_ratios(results, base_path)
        
        logger.info(f"Parsed {len(results.drivers)} drivers")
        return results
        
    except Exception as e:
        logger.error(f"Error parsing race results: {e}", exc_info=True)
        return None


def _time_to_seconds(time_str: str) -> Optional[float]:
    """Convert time string to seconds - OPTIMIZED"""
    if not time_str:
        return None
    
    try:
        if ':' in time_str:
            parts = time_str.split(':')
            return int(parts[0]) * 60 + float(parts[1])
        else:
            return float(time_str)
    except (ValueError, IndexError):
        return None


# Cache for AIW file paths to avoid repeated searching
_AIW_CACHE = {}
_CACHE_MAX_SIZE = 50


def _parse_aiw_ratios(results: RaceResults, base_path: Path):
    """Parse AIW file to get QualRatio and RaceRatio - with caching"""
    try:
        track_folder = results.track_folder or results.track_name
        
        # Check cache first
        cache_key = f"{track_folder}_{results.aiw_file}"
        if cache_key in _AIW_CACHE:
            aiw_path = _AIW_CACHE[cache_key]
            logger.info(f"Using cached AIW path: {aiw_path}")
        else:
            aiw_path = _find_aiw_file_case_insensitive(results.aiw_file, track_folder, base_path)
            if aiw_path:
                # Cache the result
                if len(_AIW_CACHE) >= _CACHE_MAX_SIZE:
                    # Remove oldest entry
                    _AIW_CACHE.pop(next(iter(_AIW_CACHE)))
                _AIW_CACHE[cache_key] = aiw_path
        
        if not aiw_path or not aiw_path.exists():
            logger.warning(f"AIW file not found: {results.aiw_file}")
            return
        
        # Read and parse AIW file
        with open(aiw_path, 'rb') as f:
            raw_content = f.read()
        
        # Fast decode - remove null bytes efficiently
        content = raw_content.replace(b'\x00', b'').decode('utf-8', errors='ignore')
        
        # Find Waypoint section
        waypoint_match = re.search(r'\[Waypoint\](.*?)(?=\[|$)', content, re.DOTALL | re.IGNORECASE)
        if waypoint_match:
            waypoint_section = waypoint_match.group(1)
            
            quali_match = re.search(r'QualRatio\s*=\s*\(?([\d.]+)\)?', waypoint_section, re.IGNORECASE)
            if quali_match:
                results.qual_ratio = float(quali_match.group(1))
            
            race_match = re.search(r'RaceRatio\s*=\s*\(?([\d.]+)\)?', waypoint_section, re.IGNORECASE)
            if race_match:
                results.race_ratio = float(race_match.group(1))
        
        logger.info(f"Ratios - Qual: {results.qual_ratio}, Race: {results.race_ratio}")
        
    except Exception as e:
        logger.error(f"Error parsing AIW file: {e}")


def _find_aiw_file_case_insensitive(aiw_filename: str, track_folder: str, base_path: Path) -> Optional[Path]:
    """Find AIW file with case-insensitive search - OPTIMIZED"""
    locations_path = base_path / 'GameData' / 'Locations'
    
    if not locations_path.exists():
        return None
    
    # Strategy 1: Look in the track folder
    if track_folder:
        track_folder_lower = track_folder.lower()
        try:
            for folder in locations_path.iterdir():
                if folder.is_dir() and folder.name.lower() == track_folder_lower:
                    # Check for exact AIW filename match
                    for file in folder.iterdir():
                        if file.is_file() and file.name.lower() == aiw_filename.lower():
                            return file
                    
                    # Try folder name + .AIW
                    for ext in ['.AIW', '.aiw']:
                        candidate = folder / f"{folder.name}{ext}"
                        if candidate.exists():
                            return candidate
                    
                    # Return first AIW file found
                    for file in folder.glob('*.AIW'):
                        return file
                    for file in folder.glob('*.aiw'):
                        return file
        except OSError:
            pass
    
    # Strategy 2: Quick recursive search with early exit
    try:
        for root, dirs, files in os.walk(locations_path):
            for file in files:
                if file.lower() == aiw_filename.lower():
                    return Path(root) / file
    except OSError:
        pass
    
    return None
