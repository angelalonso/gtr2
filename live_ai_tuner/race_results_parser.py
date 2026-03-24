"""
Race Results Parser for rFactor 2/GTR2
Parses the raceresults.txt file and extracts race information
"""

import os
import re
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import tkinter as tk
from tkinter import ttk

logger = logging.getLogger(__name__)


class RaceResultsParser:
    """Parse and analyze race results from raceresults.txt"""
    
    def __init__(self, file_path: Path, base_path: Optional[Path] = None):
        """
        Initialize the parser with the results file path
        
        Args:
            file_path: Path to raceresults.txt file
            base_path: Base path for the game installation (to find AIW files)
        """
        self.file_path = Path(file_path)
        self.base_path = Path(base_path) if base_path else None
        self.track_name = None
        self.aiw_file = None
        self.aiw_path = None
        self.qualiratio = None
        self.raceratio = None
        self.drivers = []
        self.user_driver = None
        self.parse_successful = False
        
    def parse(self) -> bool:
        """
        Parse the results file
        
        Returns:
            bool: True if parsing was successful, False otherwise
        """
        try:
            logger.info(f"=" * 60)
            logger.info(f"Starting to parse race results file")
            logger.info(f"File path: {self.file_path}")
            logger.info(f"Base path: {self.base_path}")
            logger.info(f"=" * 60)
            
            if not self.file_path.exists():
                logger.error(f"Results file not found: {self.file_path}")
                return False
            
            # Read the file
            with open(self.file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            logger.info(f"Successfully read results file, length: {len(content)} characters")
            
            # Parse track and AIW information
            self._parse_header(content)
            
            # Parse driver slots
            self._parse_drivers(content)
            
            # Identify user driver (Slot000 is typically the user)
            self._identify_user_driver()
            
            # Parse AIW file if available
            if self.aiw_file and self.base_path:
                logger.info(f"Looking for AIW file: {self.aiw_file}")
                self._parse_aiw_file()
            else:
                if not self.aiw_file:
                    logger.warning("No AIW file found in results file")
                if not self.base_path:
                    logger.warning("No base path provided for AIW file lookup")
            
            self.parse_successful = True
            logger.info(f"Successfully parsed {len(self.drivers)} drivers from {self.file_path}")
            if self.qualiratio is not None and self.raceratio is not None:
                logger.info(f"AIW ratios - QualRatio: {self.qualiratio}, RaceRatio: {self.raceratio}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error parsing results file: {e}", exc_info=True)
            return False
    
    def _parse_header(self, content: str):
        """Parse the header section to get track and AIW information"""
        logger.info("Parsing header section...")
        
        # Find the Race section
        race_match = re.search(r'\[Race\](.*?)(?=\[|$)', content, re.DOTALL)
        if race_match:
            race_section = race_match.group(1)
            logger.info(f"Found Race section")
            
            # Extract Scene (track)
            scene_match = re.search(r'Scene=(.*?)(?:\n|$)', race_section, re.IGNORECASE)
            if scene_match:
                scene = scene_match.group(1).strip()
                logger.info(f"Found Scene: {scene}")
                # Extract track name from path (remove .TRK extension and path)
                track_name = Path(scene).stem
                # Clean up the track name
                if track_name:
                    # Remove numbers at the start if present (e.g., "4Monza" -> "Monza")
                    track_name = re.sub(r'^\d+', '', track_name)
                self.track_name = track_name
                logger.info(f"Track name: {self.track_name}")
            else:
                logger.warning("No Scene entry found in Race section")
            
            # Extract AIW file
            aiw_match = re.search(r'AIDB=(.*?)(?:\n|$)', race_section, re.IGNORECASE)
            if aiw_match:
                aiw_path = aiw_match.group(1).strip()
                logger.info(f"Found AIDB: {aiw_path}")
                # Store the full path for later use
                self.aiw_path = Path(aiw_path)
                # Get just the filename without path
                self.aiw_file = self.aiw_path.name
                logger.info(f"AIW file: {self.aiw_file}")
            else:
                logger.warning("No AIDB entry found in Race section")
        else:
            logger.warning("No Race section found in results file")
            # Try to find AIW in the whole file as fallback
            aiw_match = re.search(r'AIDB=(.*?)(?:\n|$)', content, re.IGNORECASE)
            if aiw_match:
                aiw_path = aiw_match.group(1).strip()
                logger.info(f"Found AIDB in full file: {aiw_path}")
                self.aiw_path = Path(aiw_path)
                self.aiw_file = self.aiw_path.name
    
    def _parse_aiw_file(self):
        """Parse the AIW file to extract qualiratio and raceratio"""
        try:
            logger.info(f"Attempting to parse AIW file...")
            logger.info(f"AIW path from results: {self.aiw_path}")
            logger.info(f"AIW path type: {type(self.aiw_path)}")
            logger.info(f"AIW file name: {self.aiw_file}")
            logger.info(f"Track name: {self.track_name}")
            
            # Construct the full path to the AIW file
            if self.aiw_path:
                logger.info(f"Base path: {self.base_path}")
                logger.info(f"Base path exists: {self.base_path.exists()}")
                
                # The AIW path from results is like: GAMEDATA\LOCATIONS\Monza\4Monza.AIW
                # Convert to string and split properly
                aiw_path_str = str(self.aiw_path)
                logger.info(f"AIW path as string: {aiw_path_str}")
                
                # Split on both backslash and forward slash
                import re
                path_parts = re.split(r'[\\/]', aiw_path_str)
                logger.info(f"Split path parts: {path_parts}")
                logger.info(f"Number of parts: {len(path_parts)}")
                
                # We need to find the track folder and filename
                # The path should be something like: ['GAMEDATA', 'LOCATIONS', 'Monza', '4Monza.AIW']
                if len(path_parts) >= 2:
                    # Get the track folder (usually the second last part before filename)
                    # But let's find the filename first
                    filename = path_parts[-1] if path_parts else self.aiw_file
                    logger.info(f"Filename: {filename}")
                    
                    # The track folder is usually the part before filename
                    if len(path_parts) >= 2:
                        track_folder = path_parts[-2] if len(path_parts) >= 2 else None
                        logger.info(f"Track folder from path: {track_folder}")
                        
                        # If we don't have a track folder from the path, try using the track name
                        if not track_folder or track_folder.upper() == 'LOCATIONS':
                            track_folder = self.track_name
                            logger.info(f"Using track name as folder: {track_folder}")
                        
                        # Construct the path with correct case
                        # Try multiple possible paths
                        possible_paths = []
                        
                        # Path 1: Standard path with GameData/Locations
                        if track_folder:
                            path1 = self.base_path / 'GameData' / 'Locations' / track_folder / filename
                            possible_paths.append(path1)
                            logger.info(f"Path 1 (standard): {path1}")
                            
                            # Path 2: Try with track folder in original case
                            path2 = self.base_path / 'GameData' / 'Locations' / track_folder / filename
                            possible_paths.append(path2)
                            
                            # Path 3: Try with different case for track folder
                            track_variations = [
                                track_folder,
                                track_folder.lower(),
                                track_folder.upper(),
                                track_folder.capitalize(),
                                track_folder.title()
                            ]
                            
                            for track_var in set(track_variations):
                                if track_var != track_folder:
                                    var_path = self.base_path / 'GameData' / 'Locations' / track_var / filename
                                    possible_paths.append(var_path)
                                    logger.info(f"  Track variation: {track_var} -> {var_path}")
                        
                        # Path 4: Search in GameData/Locations for any matching folder
                        locations_path = self.base_path / 'GameData' / 'Locations'
                        logger.info(f"Checking locations path: {locations_path}")
                        logger.info(f"Locations path exists: {locations_path.exists()}")
                        
                        if locations_path.exists():
                            logger.info(f"Contents of {locations_path}:")
                            for item in locations_path.iterdir():
                                logger.info(f"  - {item.name} (is_dir: {item.is_dir()})")
                                if item.is_dir() and track_folder and item.name.lower() == track_folder.lower():
                                    track_path = item / filename
                                    logger.info(f"Found matching track folder: {item}")
                                    possible_paths.append(track_path)
                        
                        # Path 5: Walk through entire GameData to find any AIW file
                        game_data_path = self.base_path / 'GameData'
                        logger.info(f"Searching in GameData: {game_data_path}")
                        logger.info(f"GameData exists: {game_data_path.exists()}")
                        
                        if game_data_path.exists():
                            logger.info(f"Walking through GameData to find {filename}...")
                            for root, dirs, files in os.walk(game_data_path):
                                for file in files:
                                    if file.lower() == filename.lower():
                                        found_path = Path(root) / file
                                        logger.info(f"Found AIW file via walk: {found_path}")
                                        possible_paths.append(found_path)
                                        break
                                else:
                                    continue
                                break
                        
                        # Path 6: Try without GameData in path (direct from base)
                        if track_folder:
                            path6 = self.base_path / 'Locations' / track_folder / filename
                            possible_paths.append(path6)
                            logger.info(f"Path 6 (no GameData): {path6}")
                        
                        # Remove duplicates while preserving order
                        seen = set()
                        unique_paths = []
                        for path in possible_paths:
                            if path not in seen:
                                seen.add(path)
                                unique_paths.append(path)
                        
                        logger.info("=" * 80)
                        logger.info(f"Checking {len(unique_paths)} possible AIW file paths:")
                        for i, path in enumerate(unique_paths, 1):
                            logger.info(f"  Path {i}: {path}")
                            logger.info(f"    Exists: {path.exists()}")
                            if path.exists():
                                logger.info(f"    Is file: {path.is_file()}")
                                try:
                                    logger.info(f"    Size: {path.stat().st_size} bytes")
                                except:
                                    logger.info(f"    Size: Unable to read")
                        logger.info("=" * 80)
                        
                        # Find the actual file
                        actual_path = None
                        for path in unique_paths:
                            if path.exists() and path.is_file():
                                actual_path = path
                                logger.info(f"✓✓✓ Found AIW file at: {actual_path} ✓✓✓")
                                break
                        
                        if not actual_path:
                            logger.error(f"✗✗✗ AIW file not found in any location ✗✗✗")
                            logger.info("Please check if the file exists at any of these locations:")
                            for path in unique_paths[:5]:  # Show first 5 paths
                                logger.info(f"  - {path}")
                            return
                        
                        logger.info(f"Reading AIW file: {actual_path}")
                        logger.info(f"File size: {actual_path.stat().st_size} bytes")
                        
                        # Read the file in binary mode to handle null bytes
                        with open(actual_path, 'rb') as f:
                            raw_content = f.read()
                        
                        logger.info(f"Raw content length: {len(raw_content)} bytes")
                        
                        # Count null bytes
                        null_count = raw_content.count(b'\x00')
                        logger.info(f"Null bytes in file: {null_count}")
                        
                        # Decode the binary content
                        aiw_content = None
                        for encoding in ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']:
                            try:
                                cleaned = raw_content.replace(b'\x00', b'')
                                aiw_content = cleaned.decode(encoding, errors='ignore')
                                logger.info(f"Successfully decoded with {encoding}")
                                logger.info(f"Decoded length: {len(aiw_content)} characters")
                                break
                            except Exception as e:
                                logger.warning(f"Failed to decode with {encoding}: {e}")
                                continue
                        
                        if not aiw_content:
                            aiw_content = raw_content.decode('utf-8', errors='ignore')
                            logger.info("Decoded with utf-8 ignoring errors")
                            logger.info(f"Decoded length: {len(aiw_content)} characters")
                        
                        # Log first 1000 characters
                        logger.info("=" * 80)
                        logger.info("First 1000 characters of decoded AIW content:")
                        logger.info(aiw_content[:1000])
                        logger.info("=" * 80)
                        
                        # Look for the [Waypoint] section
                        waypoint_match = re.search(r'\[Waypoint\](.*?)(?=\[|$)', aiw_content, re.DOTALL | re.IGNORECASE)
                        if waypoint_match:
                            waypoint_section = waypoint_match.group(1)
                            logger.info(f"Found [Waypoint] section, length: {len(waypoint_section)} characters")
                            
                            # Search for QualRatio
                            logger.info("Searching for QualRatio...")
                            quali_match = re.search(r'QualRatio\s*=\s*\(?([\d.]+)\)?', waypoint_section, re.IGNORECASE)
                            if quali_match:
                                self.qualiratio = float(quali_match.group(1))
                                logger.info(f"✓ Found QualRatio: {self.qualiratio}")
                            else:
                                logger.warning("QualRatio not found in Waypoint section")
                                # Show lines containing Ratio in the Waypoint section
                                ratio_lines = [line for line in waypoint_section.split('\n') if 'ratio' in line.lower()]
                                if ratio_lines:
                                    logger.info(f"Lines containing 'ratio' in Waypoint section:")
                                    for line in ratio_lines[:5]:
                                        logger.info(f"  {line}")
                            
                            # Search for RaceRatio
                            logger.info("Searching for RaceRatio...")
                            race_match = re.search(r'RaceRatio\s*=\s*\(?([\d.]+)\)?', waypoint_section, re.IGNORECASE)
                            if race_match:
                                self.raceratio = float(race_match.group(1))
                                logger.info(f"✓ Found RaceRatio: {self.raceratio}")
                            else:
                                logger.warning("RaceRatio not found in Waypoint section")
                        else:
                            logger.warning("No [Waypoint] section found in AIW file")
                            # Search for any ratio lines in the entire file
                            ratio_lines = [line for line in aiw_content.split('\n') if 'ratio' in line.lower()]
                            if ratio_lines:
                                logger.info(f"Lines containing 'ratio' in entire file:")
                                for line in ratio_lines[:10]:
                                    logger.info(f"  {line}")
                    
        except Exception as e:
            logger.error(f"Error parsing AIW file: {e}", exc_info=True)
            import traceback
            logger.error(traceback.format_exc())
        
        logger.info(f"Final results - QualRatio: {self.qualiratio}, RaceRatio: {self.raceratio}")
    
    def _try_alternative_aiw_paths(self) -> Optional[Path]:
        """Try alternative paths to find the AIW file"""
        try:
            # If we have track name, try to find AIW file in that track folder
            if self.track_name:
                logger.info(f"Searching for AIW file using track name: {self.track_name}")
                
                # Try common track name variations
                track_variations = [
                    self.track_name,
                    self.track_name.lower(),
                    self.track_name.upper(),
                    self.track_name.capitalize(),
                    self.track_name.title(),
                    f"4{self.track_name}",  # Some tracks have numbers prefix
                    f"4{self.track_name.lower()}",
                    f"4{self.track_name.upper()}"
                ]
                
                for track_var in set(track_variations):
                    # Try to find any .aiw file in the track folder
                    if self.base_path:
                        # Check in GameData/Locations/TrackName/
                        track_path = self.base_path / 'GameData' / 'Locations' / track_var
                        logger.info(f"Checking track path: {track_path}")
                        
                        if track_path.exists():
                            logger.info(f"Track folder exists: {track_path}")
                            for aiw_file in track_path.glob('*.AIW'):
                                logger.info(f"Found AIW file in track folder: {aiw_file}")
                                return aiw_file
                            for aiw_file in track_path.glob('*.aiw'):
                                logger.info(f"Found AIW file in track folder: {aiw_file}")
                                return aiw_file
                            for aiw_file in track_path.glob('*.AIw'):
                                logger.info(f"Found AIW file in track folder: {aiw_file}")
                                return aiw_file
                        else:
                            logger.debug(f"Track path does not exist: {track_path}")
                        
                        # Try without GameData in path
                        alt_track_path = self.base_path / 'Locations' / track_var
                        logger.info(f"Checking alternative track path: {alt_track_path}")
                        
                        if alt_track_path.exists():
                            logger.info(f"Alternative track folder exists: {alt_track_path}")
                            for aiw_file in alt_track_path.glob('*.AIW'):
                                logger.info(f"Found AIW file in alt track folder: {aiw_file}")
                                return aiw_file
                            for aiw_file in alt_track_path.glob('*.aiw'):
                                logger.info(f"Found AIW file in alt track folder: {aiw_file}")
                                return aiw_file
            
            return None
            
        except Exception as e:
            logger.error(f"Error trying alternative AIW paths: {e}")
            return None
    
    def _find_aiw_file(self, path: Path) -> Optional[Path]:
        """
        Find the AIW file handling case-insensitivity on Windows and trying common variations
        
        Args:
            path: The expected path to the AIW file
        
        Returns:
            Path to the actual file if found, None otherwise
        """
        try:
            # First try the exact path
            if path.exists() and path.is_file():
                logger.info(f"Found AIW file at exact path: {path}")
                return path
            
            # Try with .AIW uppercase extension
            if path.suffix.lower() == '.aiw':
                uppercase_path = path.with_suffix('.AIW')
                if uppercase_path.exists() and uppercase_path.is_file():
                    logger.info(f"Found AIW file at uppercase path: {uppercase_path}")
                    return uppercase_path
                
                # Try with .AIw extension
                mixed_path = path.with_suffix('.AIw')
                if mixed_path.exists() and mixed_path.is_file():
                    logger.info(f"Found AIW file at mixed case path: {mixed_path}")
                    return mixed_path
            
            # Try to find by walking the directory structure
            if path.parent.exists():
                parent = path.parent
                filename = path.name
                logger.info(f"Searching in {parent} for files matching {filename}")
                
                # Walk through the directory to find matching files
                for root, dirs, files in os.walk(parent):
                    for file in files:
                        if file.lower() == filename.lower():
                            found_path = Path(root) / file
                            logger.info(f"Found AIW file via walk: {found_path}")
                            return found_path
                
                # Also try to find any .AIW file in the parent directory
                for file in parent.glob('*.AIW'):
                    logger.info(f"Found alternative AIW file: {file}")
                    return file
                for file in parent.glob('*.aiw'):
                    logger.info(f"Found alternative AIW file: {file}")
                    return file
            
            return None
            
        except Exception as e:
            logger.error(f"Error finding AIW file: {e}")
            return None
    
    def _parse_drivers(self, content: str):
        """Parse all driver slots from the content"""
        # Find all slot sections
        slot_pattern = r'\[Slot(\d+)\](.*?)(?=\[Slot|\[END\]|$)'
        slots = re.findall(slot_pattern, content, re.DOTALL)
        
        logger.info(f"Found {len(slots)} driver slots")
        
        for slot_num, slot_content in slots:
            driver_data = {
                'slot': int(slot_num),
                'name': None,
                'vehicle': None,
                'vehicle_number': None,
                'team': None,
                'qual_time': None,
                'best_lap': None,
                'laps': None,
                'race_time': None
            }
            
            # Parse each field
            name_match = re.search(r'Driver=(.*?)(?:\n|$)', slot_content)
            if name_match:
                driver_data['name'] = name_match.group(1).strip()
            
            vehicle_match = re.search(r'Vehicle=(.*?)(?:\n|$)', slot_content)
            if vehicle_match:
                driver_data['vehicle'] = vehicle_match.group(1).strip()
            
            vehicle_num_match = re.search(r'VehicleNumber=(.*?)(?:\n|$)', slot_content)
            if vehicle_num_match:
                driver_data['vehicle_number'] = vehicle_num_match.group(1).strip()
            
            team_match = re.search(r'Team=(.*?)(?:\n|$)', slot_content)
            if team_match:
                driver_data['team'] = team_match.group(1).strip()
            
            qual_match = re.search(r'QualTime=(.*?)(?:\n|$)', slot_content)
            if qual_match:
                driver_data['qual_time'] = qual_match.group(1).strip()
            
            best_lap_match = re.search(r'BestLap=(.*?)(?:\n|$)', slot_content)
            if best_lap_match:
                driver_data['best_lap'] = best_lap_match.group(1).strip()
            
            laps_match = re.search(r'Laps=(.*?)(?:\n|$)', slot_content)
            if laps_match:
                driver_data['laps'] = laps_match.group(1).strip()
            
            race_time_match = re.search(r'RaceTime=(.*?)(?:\n|$)', slot_content)
            if race_time_match:
                driver_data['race_time'] = race_time_match.group(1).strip()
            
            self.drivers.append(driver_data)
            logger.debug(f"Parsed driver slot {slot_num}: {driver_data['name']}")
        
        if len(self.drivers) > 0:
            logger.info(f"Sample driver data (slot 0): {self.drivers[0] if self.drivers else 'None'}")
    
    def _identify_user_driver(self):
        """Identify the user driver (typically Slot000)"""
        for driver in self.drivers:
            if driver['slot'] == 0:
                self.user_driver = driver
                logger.info(f"User driver identified: {driver['name']}")
                break
    
    def _time_to_seconds(self, time_str: str) -> Optional[float]:
        """
        Convert a time string to seconds for comparison
        
        Args:
            time_str: Time string in format like "1:55.364" or "1:57.861"
        
        Returns:
            float: Time in seconds, or None if invalid
        """
        if not time_str:
            return None
        
        try:
            # Handle mm:ss.sss format
            if ':' in time_str:
                parts = time_str.split(':')
                minutes = int(parts[0])
                seconds = float(parts[1])
                return minutes * 60 + seconds
            else:
                # Handle just seconds
                return float(time_str)
        except (ValueError, IndexError):
            return None
    
    def get_ai_drivers(self) -> List[Dict]:
        """Get all AI drivers (all drivers except Slot000)"""
        return [d for d in self.drivers if d['slot'] != 0]
    
    def get_best_qualifying_ai(self) -> Tuple[Optional[Dict], Optional[str]]:
        """
        Get the best qualifying time among AI drivers
        
        Returns:
            Tuple of (driver_data, time_string) or (None, None) if no qualifying times
        """
        ai_drivers = self.get_ai_drivers()
        best_driver = None
        best_time = None
        best_time_seconds = float('inf')
        
        for driver in ai_drivers:
            if driver['qual_time']:
                time_seconds = self._time_to_seconds(driver['qual_time'])
                if time_seconds and time_seconds < best_time_seconds:
                    best_time_seconds = time_seconds
                    best_driver = driver
                    best_time = driver['qual_time']
        
        return best_driver, best_time
    
    def get_worst_qualifying_ai(self) -> Tuple[Optional[Dict], Optional[str]]:
        """
        Get the worst qualifying time among AI drivers
        
        Returns:
            Tuple of (driver_data, time_string) or (None, None) if no qualifying times
        """
        ai_drivers = self.get_ai_drivers()
        worst_driver = None
        worst_time = None
        worst_time_seconds = -float('inf')
        
        for driver in ai_drivers:
            if driver['qual_time']:
                time_seconds = self._time_to_seconds(driver['qual_time'])
                if time_seconds and time_seconds > worst_time_seconds:
                    worst_time_seconds = time_seconds
                    worst_driver = driver
                    worst_time = driver['qual_time']
        
        return worst_driver, worst_time
    
    def get_user_qualifying(self) -> Optional[str]:
        """Get user's qualifying time"""
        if self.user_driver and self.user_driver['qual_time']:
            return self.user_driver['qual_time']
        return None
    
    def get_best_race_lap_ai(self) -> Tuple[Optional[Dict], Optional[str]]:
        """
        Get the best race lap time among AI drivers
        
        Returns:
            Tuple of (driver_data, time_string) or (None, None) if no lap times
        """
        ai_drivers = self.get_ai_drivers()
        best_driver = None
        best_time = None
        best_time_seconds = float('inf')
        
        for driver in ai_drivers:
            if driver['best_lap']:
                time_seconds = self._time_to_seconds(driver['best_lap'])
                if time_seconds and time_seconds < best_time_seconds:
                    best_time_seconds = time_seconds
                    best_driver = driver
                    best_time = driver['best_lap']
        
        return best_driver, best_time
    
    def get_worst_race_lap_ai(self) -> Tuple[Optional[Dict], Optional[str]]:
        """
        Get the worst race lap time among AI drivers
        
        Returns:
            Tuple of (driver_data, time_string) or (None, None) if no lap times
        """
        ai_drivers = self.get_ai_drivers()
        worst_driver = None
        worst_time = None
        worst_time_seconds = -float('inf')
        
        for driver in ai_drivers:
            if driver['best_lap']:
                time_seconds = self._time_to_seconds(driver['best_lap'])
                if time_seconds and time_seconds > worst_time_seconds:
                    worst_time_seconds = time_seconds
                    worst_driver = driver
                    worst_time = driver['best_lap']
        
        return worst_driver, worst_time
    
    def get_best_user_lap(self) -> Optional[str]:
        """Get user's best race lap time"""
        if self.user_driver and self.user_driver['best_lap']:
            return self.user_driver['best_lap']
        return None
    
    def get_track_info(self) -> Tuple[Optional[str], Optional[str]]:
        """Get track name and AIW file being used"""
        return self.track_name, self.aiw_file
    
    def get_aiw_ratios(self) -> Tuple[Optional[float], Optional[float]]:
        """Get qualiratio and raceratio from AIW file"""
        return self.qualiratio, self.raceratio


class RaceResultsPopup:
    """Popup window to display race results analysis"""
    
    def __init__(self, parser: RaceResultsParser):
        """
        Initialize the popup with parsed results
        
        Args:
            parser: RaceResultsParser instance with parsed data
        """
        self.parser = parser
        self.window = None
        
    def show(self):
        """Create and display the results popup window"""
        try:
            logger.info("Creating race results popup window...")
            
            # Check if we have any data to show
            if not self.parser.parse_successful:
                logger.error("Cannot show popup: parser was not successful")
                return
            
            if len(self.parser.drivers) == 0:
                logger.error("Cannot show popup: no drivers parsed")
                return
            
            logger.info(f"Creating popup with {len(self.parser.drivers)} drivers")
            logger.info(f"User driver: {self.parser.user_driver}")
            logger.info(f"Track: {self.parser.track_name}")
            logger.info(f"AIW file: {self.parser.aiw_file}")
            logger.info(f"QualRatio: {self.parser.qualiratio}")
            logger.info(f"RaceRatio: {self.parser.raceratio}")
            
            self.window = tk.Toplevel()
            self.window.title("Race Results Analysis")
            self.window.geometry("700x650")
            
            # Center the window on screen
            self.window.update_idletasks()
            width = self.window.winfo_width()
            height = self.window.winfo_height()
            x = (self.window.winfo_screenwidth() // 2) - (width // 2)
            y = (self.window.winfo_screenheight() // 2) - (height // 2)
            self.window.geometry(f'{width}x{height}+{x}+{y}')
            
            # Make window grab focus
            self.window.lift()
            self.window.focus_force()
            self.window.grab_set()
            
            # Configure window
            self.window.configure(bg='#f0f0f0')
            
            # Main frame
            main_frame = tk.Frame(self.window, bg='#f0f0f0')
            main_frame.pack(expand=True, fill='both', padx=20, pady=20)
            
            # Title
            title_label = tk.Label(
                main_frame,
                text="Race Results Analysis",
                font=('Arial', 14, 'bold'),
                bg='#f0f0f0',
                fg='#333'
            )
            title_label.pack(pady=(0, 10))
            
            # Track info and AIW ratios
            track_name, aiw_file = self.parser.get_track_info()
            qualiratio, raceratio = self.parser.get_aiw_ratios()
            
            info_frame = tk.Frame(main_frame, bg='#f0f0f0')
            info_frame.pack(fill='x', pady=(0, 15))
            
            if track_name:
                track_label = tk.Label(
                    info_frame,
                    text=f"Track: {track_name}",
                    font=('Arial', 10, 'bold'),
                    bg='#f0f0f0',
                    fg='#666'
                )
                track_label.pack()
            
            if aiw_file:
                aiw_label = tk.Label(
                    info_frame,
                    text=f"AIW: {aiw_file}",
                    font=('Arial', 9),
                    bg='#f0f0f0',
                    fg='#888'
                )
                aiw_label.pack()
            
            # AIW Ratios section
            if qualiratio is not None or raceratio is not None:
                ratios_frame = tk.Frame(info_frame, bg='#f0f0f0')
                ratios_frame.pack(pady=(5, 0))
                
                if qualiratio is not None:
                    quali_ratio_label = tk.Label(
                        ratios_frame,
                        text=f"Qual Ratio: {qualiratio:.2f}",
                        font=('Arial', 9, 'bold'),
                        bg='#f0f0f0',
                        fg='#5bc0de'
                    )
                    quali_ratio_label.pack(side='left', padx=(0, 10))
                
                if raceratio is not None:
                    race_ratio_label = tk.Label(
                        ratios_frame,
                        text=f"Race Ratio: {raceratio:.2f}",
                        font=('Arial', 9, 'bold'),
                        bg='#f0f0f0',
                        fg='#5bc0de'
                    )
                    race_ratio_label.pack(side='left')
            
            # Separator
            separator = ttk.Separator(main_frame, orient='horizontal')
            separator.pack(fill='x', pady=10)
            
            # Create notebook for tabs
            notebook = ttk.Notebook(main_frame)
            notebook.pack(fill='both', expand=True, pady=10)
            
            # Qualifying tab
            quali_frame = tk.Frame(notebook, bg='#f0f0f0')
            notebook.add(quali_frame, text="Qualifying")
            self._create_quali_tab(quali_frame)
            
            # Race tab
            race_frame = tk.Frame(notebook, bg='#f0f0f0')
            notebook.add(race_frame, text="Race Laps")
            self._create_race_tab(race_frame)
            
            # AIW Info tab
            aiw_frame = tk.Frame(notebook, bg='#f0f0f0')
            notebook.add(aiw_frame, text="AIW Info")
            self._create_aiw_tab(aiw_frame)
            
            # All drivers tab
            drivers_frame = tk.Frame(notebook, bg='#f0f0f0')
            notebook.add(drivers_frame, text="All Drivers")
            self._create_drivers_tab(drivers_frame)
            
            # Close button
            button_frame = tk.Frame(main_frame, bg='#f0f0f0')
            button_frame.pack(pady=(10, 0))
            
            close_button = ttk.Button(
                button_frame,
                text="Close",
                command=self.close,
                width=15
            )
            close_button.pack()
            
            # Bind keyboard shortcuts
            self.window.bind('<Return>', lambda e: self.close())
            self.window.bind('<Escape>', lambda e: self.close())
            
            # Ensure window is on top
            self.window.attributes('-topmost', True)
            
            # Handle window close
            self.window.protocol("WM_DELETE_WINDOW", self.close)
            
            logger.info("Race results popup window created successfully")
            
            # Wait for window
            self.window.wait_window()
            
        except Exception as e:
            logger.error(f"Error creating popup window: {e}", exc_info=True)
    
    def _create_quali_tab(self, parent):
        """Create the qualifying tab content"""
        try:
            # Best AI Qualifying
            best_ai, best_time = self.parser.get_best_qualifying_ai()
            self._create_info_row(
                parent,
                "Best AI Qualifying:",
                f"{best_time if best_time else 'N/A'}",
                f"({best_ai['name'] if best_ai else 'No AI drivers'})" if best_ai else "",
                0
            )
            
            # Worst AI Qualifying
            worst_ai, worst_time = self.parser.get_worst_qualifying_ai()
            self._create_info_row(
                parent,
                "Worst AI Qualifying:",
                f"{worst_time if worst_time else 'N/A'}",
                f"({worst_ai['name'] if worst_ai else 'No AI drivers'})" if worst_ai else "",
                1
            )
            
            # User Qualifying
            user_quali = self.parser.get_user_qualifying()
            user_text = user_quali if user_quali else "None (No qualifying time)"
            self._create_info_row(
                parent,
                "User Qualifying:",
                user_text,
                "",
                2
            )
            
            # Add some spacing and note about qualifying
            note_frame = tk.Frame(parent, bg='#f0f0f0')
            note_frame.pack(fill='x', pady=(20, 0))
            
            note_label = tk.Label(
                note_frame,
                text="Note: Qualifying times are from the qualifying session.",
                font=('Arial', 8),
                bg='#f0f0f0',
                fg='#888'
            )
            note_label.pack()
        except Exception as e:
            logger.error(f"Error creating quali tab: {e}", exc_info=True)
    
    def _create_race_tab(self, parent):
        """Create the race laps tab content"""
        try:
            # Best AI Race Lap
            best_ai, best_time = self.parser.get_best_race_lap_ai()
            self._create_info_row(
                parent,
                "Best AI Race Lap:",
                f"{best_time if best_time else 'N/A'}",
                f"({best_ai['name'] if best_ai else 'No AI drivers'})" if best_ai else "",
                0
            )
            
            # Worst AI Race Lap
            worst_ai, worst_time = self.parser.get_worst_race_lap_ai()
            self._create_info_row(
                parent,
                "Worst AI Race Lap:",
                f"{worst_time if worst_time else 'N/A'}",
                f"({worst_ai['name'] if worst_ai else 'No AI drivers'})" if worst_ai else "",
                1
            )
            
            # Best User Lap
            user_best = self.parser.get_best_user_lap()
            user_text = user_best if user_best else "No lap times recorded"
            self._create_info_row(
                parent,
                "Best User Lap:",
                user_text,
                "",
                2
            )
            
            # Add some spacing and note
            note_frame = tk.Frame(parent, bg='#f0f0f0')
            note_frame.pack(fill='x', pady=(20, 0))
            
            note_label = tk.Label(
                note_frame,
                text="Note: Best lap times are the fastest lap achieved during the race.",
                font=('Arial', 8),
                bg='#f0f0f0',
                fg='#888'
            )
            note_label.pack()
        except Exception as e:
            logger.error(f"Error creating race tab: {e}", exc_info=True)
    
    def _create_aiw_tab(self, parent):
        """Create the AIW information tab"""
        try:
            qualiratio, raceratio = self.parser.get_aiw_ratios()
            track_name, aiw_file = self.parser.get_track_info()
            
            # Title
            title_label = tk.Label(
                parent,
                text="AIW File Information",
                font=('Arial', 11, 'bold'),
                bg='#f0f0f0',
                fg='#333'
            )
            title_label.pack(pady=(10, 15))
            
            # AIW File info frame
            aiw_frame = tk.Frame(parent, bg='#f0f0f0', relief='groove', bd=1)
            aiw_frame.pack(fill='x', padx=20, pady=5)
            
            if aiw_file:
                file_label = tk.Label(
                    aiw_frame,
                    text=f"File: {aiw_file}",
                    font=('Arial', 10),
                    bg='#f0f0f0',
                    fg='#333',
                    anchor='w'
                )
                file_label.pack(fill='x', padx=10, pady=(10, 5))
            
            # Ratios frame
            ratios_frame = tk.Frame(parent, bg='#f0f0f0', relief='groove', bd=1)
            ratios_frame.pack(fill='x', padx=20, pady=10)
            
            ratios_title = tk.Label(
                ratios_frame,
                text="AI Difficulty Ratios",
                font=('Arial', 10, 'bold'),
                bg='#f0f0f0',
                fg='#5bc0de'
            )
            ratios_title.pack(pady=(10, 5))
            
            if qualiratio is not None:
                quali_frame = tk.Frame(ratios_frame, bg='#f0f0f0')
                quali_frame.pack(fill='x', padx=10, pady=5)
                
                quali_label = tk.Label(
                    quali_frame,
                    text="Qual Ratio:",
                    font=('Arial', 9, 'bold'),
                    bg='#f0f0f0',
                    fg='#333',
                    width=15,
                    anchor='w'
                )
                quali_label.pack(side='left')
                
                quali_value = tk.Label(
                    quali_frame,
                    text=f"{qualiratio:.2f}",
                    font=('Arial', 9),
                    bg='#f0f0f0',
                    fg='#5cb85c'
                )
                quali_value.pack(side='left')
                
                quali_desc = tk.Label(
                    quali_frame,
                    text="(Higher = faster AI in qualifying)",
                    font=('Arial', 8),
                    bg='#f0f0f0',
                    fg='#888'
                )
                quali_desc.pack(side='left', padx=(10, 0))
            
            if raceratio is not None:
                race_frame = tk.Frame(ratios_frame, bg='#f0f0f0')
                race_frame.pack(fill='x', padx=10, pady=5)
                
                race_label = tk.Label(
                    race_frame,
                    text="Race Ratio:",
                    font=('Arial', 9, 'bold'),
                    bg='#f0f0f0',
                    fg='#333',
                    width=15,
                    anchor='w'
                )
                race_label.pack(side='left')
                
                race_value = tk.Label(
                    race_frame,
                    text=f"{raceratio:.2f}",
                    font=('Arial', 9),
                    bg='#f0f0f0',
                    fg='#5cb85c'
                )
                race_value.pack(side='left')
                
                race_desc = tk.Label(
                    race_frame,
                    text="(Higher = faster AI in race)",
                    font=('Arial', 8),
                    bg='#f0f0f0',
                    fg='#888'
                )
                race_desc.pack(side='left', padx=(10, 0))
            
            if qualiratio is None and raceratio is None:
                no_ratios = tk.Label(
                    ratios_frame,
                    text="No ratio data found in AIW file",
                    font=('Arial', 9),
                    bg='#f0f0f0',
                    fg='#d9534f'
                )
                no_ratios.pack(pady=10)
            
            # Information about ratios
            info_frame = tk.Frame(parent, bg='#f0f0f0')
            info_frame.pack(fill='x', padx=20, pady=15)
            
            info_text = tk.Label(
                info_frame,
                text="AI Difficulty Ratio Explanation:\n"
                     "• 1.00 = Normal AI difficulty\n"
                     "• > 1.00 = AI is faster (higher difficulty)\n"
                     "• < 1.00 = AI is slower (lower difficulty)",
                font=('Arial', 8),
                bg='#f0f0f0',
                fg='#666',
                justify='left'
            )
            info_text.pack()
        except Exception as e:
            logger.error(f"Error creating AIW tab: {e}", exc_info=True)
    
    def _create_drivers_tab(self, parent):
        """Create the all drivers tab with a treeview"""
        try:
            # Create treeview frame
            tree_frame = tk.Frame(parent, bg='white')
            tree_frame.pack(fill='both', expand=True, padx=5, pady=5)
            
            # Create scrollbars
            v_scrollbar = ttk.Scrollbar(tree_frame, orient='vertical')
            h_scrollbar = ttk.Scrollbar(tree_frame, orient='horizontal')
            
            # Create treeview
            columns = ('Slot', 'Name', 'Team', 'Qual Time', 'Best Lap', 'Laps')
            tree = ttk.Treeview(
                tree_frame,
                columns=columns,
                show='headings',
                height=15,
                yscrollcommand=v_scrollbar.set,
                xscrollcommand=h_scrollbar.set
            )
            
            # Configure scrollbars
            v_scrollbar.config(command=tree.yview)
            h_scrollbar.config(command=tree.xview)
            
            # Define column headings
            tree.heading('Slot', text='Slot')
            tree.heading('Name', text='Driver Name')
            tree.heading('Team', text='Team')
            tree.heading('Qual Time', text='Qualifying')
            tree.heading('Best Lap', text='Best Lap')
            tree.heading('Laps', text='Laps')
            
            # Define column widths
            tree.column('Slot', width=50, anchor='center')
            tree.column('Name', width=150)
            tree.column('Team', width=180)
            tree.column('Qual Time', width=80, anchor='center')
            tree.column('Best Lap', width=80, anchor='center')
            tree.column('Laps', width=60, anchor='center')
            
            # Pack tree and scrollbars
            tree.grid(row=0, column=0, sticky='nsew')
            v_scrollbar.grid(row=0, column=1, sticky='ns')
            h_scrollbar.grid(row=1, column=0, sticky='ew')
            
            tree_frame.grid_rowconfigure(0, weight=1)
            tree_frame.grid_columnconfigure(0, weight=1)
            
            # Add data
            for driver in self.parser.drivers:
                # Highlight user (Slot000) with a tag
                tag = 'user' if driver['slot'] == 0 else 'ai'
                
                values = (
                    driver['slot'],
                    driver['name'] if driver['name'] else '-',
                    driver['team'] if driver['team'] else '-',
                    driver['qual_time'] if driver['qual_time'] else '-',
                    driver['best_lap'] if driver['best_lap'] else '-',
                    driver['laps'] if driver['laps'] else '-'
                )
                
                tree.insert('', 'end', values=values, tags=(tag,))
            
            # Configure tags for colors
            tree.tag_configure('user', background='#e6f3ff')
            tree.tag_configure('ai', background='white')
            
            logger.info(f"Added {len(self.parser.drivers)} drivers to the treeview")
        except Exception as e:
            logger.error(f"Error creating drivers tab: {e}", exc_info=True)
    
    def _create_info_row(self, parent, label_text, value_text, extra_text, row):
        """Create a row with label, value, and optional extra text"""
        try:
            frame = tk.Frame(parent, bg='#f0f0f0')
            frame.pack(fill='x', pady=8)
            
            # Label
            label = tk.Label(
                frame,
                text=label_text,
                font=('Arial', 10, 'bold'),
                bg='#f0f0f0',
                width=20,
                anchor='w'
            )
            label.pack(side='left', padx=(0, 10))
            
            # Value
            value_color = '#5cb85c' if 'Best' in label_text else '#d9534f' if 'Worst' in label_text else '#333'
            value = tk.Label(
                frame,
                text=value_text,
                font=('Arial', 10),
                bg='#f0f0f0',
                fg=value_color
            )
            value.pack(side='left')
            
            # Extra text (driver name, etc.)
            if extra_text:
                extra = tk.Label(
                    frame,
                    text=extra_text,
                    font=('Arial', 9),
                    bg='#f0f0f0',
                    fg='#666'
                )
                extra.pack(side='left', padx=(5, 0))
        except Exception as e:
            logger.error(f"Error creating info row: {e}", exc_info=True)
    
    def close(self):
        """Close the popup window"""
        if self.window:
            self.window.grab_release()
            self.window.destroy()
            self.window = None
            logger.info("Race results popup closed")


def analyze_race_results(file_path: Path, base_path: Optional[Path] = None) -> bool:
    """
    Main function to analyze race results and show popup
    
    Args:
        file_path: Path to the raceresults.txt file
        base_path: Base path for the game installation (to find AIW files)
    
    Returns:
        bool: True if analysis was successful, False otherwise
    """
    try:
        logger.info("=" * 60)
        logger.info("Starting race results analysis")
        logger.info(f"File path: {file_path}")
        logger.info(f"Base path: {base_path}")
        logger.info("=" * 60)
        
        # Parse the results
        parser = RaceResultsParser(file_path, base_path)
        if not parser.parse():
            logger.error("Failed to parse race results")
            return False
        
        logger.info(f"Successfully parsed {len(parser.drivers)} drivers")
        logger.info(f"Parse successful: {parser.parse_successful}")
        
        # Show the results popup
        popup = RaceResultsPopup(parser)
        popup.show()
        
        logger.info("Race results analysis completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"Error analyzing race results: {e}", exc_info=True)
        return False
