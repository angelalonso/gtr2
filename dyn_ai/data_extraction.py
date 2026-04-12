#!/usr/bin/env python3
"""
Data extraction module for parsing race results and AIW files
Extracts track info, AIW ratios, and lap times from raceresults.txt
"""

import re
import os
from pathlib import Path
from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class RaceData:
    """Container for extracted race data"""
    race_id: Optional[str] = None
    timestamp: Optional[str] = None
    track_name: Optional[str] = None
    track_folder: Optional[str] = None
    aiw_file: Optional[str] = None
    aiw_path: Optional[Path] = None
    qual_ratio: Optional[float] = None
    race_ratio: Optional[float] = None
    user_name: Optional[str] = None
    user_vehicle: Optional[str] = None
    user_best_lap: Optional[str] = None
    user_best_lap_sec: float = 0.0
    user_qualifying: Optional[str] = None
    user_qualifying_sec: float = 0.0
    best_ai_lap: Optional[str] = None
    best_ai_lap_sec: float = 0.0
    worst_ai_lap: Optional[str] = None
    worst_ai_lap_sec: float = 0.0
    qual_best_ai_lap: Optional[str] = None
    qual_best_ai_lap_sec: float = 0.0
    qual_worst_ai_lap: Optional[str] = None
    qual_worst_ai_lap_sec: float = 0.0
    ai_count: int = 0
    ai_results: List[Dict] = field(default_factory=list)
    raw_content: str = ""
    
    def __post_init__(self):
        """Set defaults after initialization"""
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()
        if not self.race_id:
            self.race_id = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    
    def has_data(self) -> bool:
        """Check if any data was extracted"""
        return bool(self.track_name or self.aiw_file or self.qual_ratio or self.race_ratio)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for database storage"""
        return {
            'race_id': self.race_id,
            'timestamp': self.timestamp,
            'track_name': self.track_name,
            'track_folder': self.track_folder,
            'aiw_file': self.aiw_file,
            'qual_ratio': self.qual_ratio,
            'race_ratio': self.race_ratio,
            'user_name': self.user_name,
            'user_vehicle': self.user_vehicle,
            'user_best_lap': self.user_best_lap,
            'user_best_lap_sec': self.user_best_lap_sec,
            'user_qualifying': self.user_qualifying,
            'user_qualifying_sec': self.user_qualifying_sec,
            'ai_results': self.ai_results,
        }
    
    def to_data_points(self) -> List[Tuple[str, float, float, str]]:
        """Convert to data points for curve database"""
        points = []
        
        # Add qualifying data point if available
        if self.qual_ratio and self.qual_best_ai_lap_sec > 0 and self.qual_worst_ai_lap_sec > 0:
            midpoint = (self.qual_best_ai_lap_sec + self.qual_worst_ai_lap_sec) / 2
            points.append((self.track_name, self.qual_ratio, midpoint, 'qual'))
        
        # Add race data point if available
        if self.race_ratio and self.best_ai_lap_sec > 0 and self.worst_ai_lap_sec > 0:
            midpoint = (self.best_ai_lap_sec + self.worst_ai_lap_sec) / 2
            points.append((self.track_name, self.race_ratio, midpoint, 'race'))
        
        return points


class DataExtractor:
    """Extracts race data from raceresults.txt and AIW files"""
    
    # Pre-compiled patterns for performance
    SCENE_PATTERN = re.compile(r'Scene=(.*?)(?:\n|$)', re.IGNORECASE)
    AIDB_PATTERN = re.compile(r'AIDB=(.*?)(?:\n|$)', re.IGNORECASE)
    SLOT_PATTERN = re.compile(r'\[Slot(\d+)\](.*?)(?=\[Slot|\[END\]|$)', re.DOTALL)
    DRIVER_PATTERN = re.compile(r'Driver=(.*?)(?:\n|$)', re.IGNORECASE)
    VEHICLE_PATTERN = re.compile(r'Vehicle=(.*?)(?:\n|$)', re.IGNORECASE)
    TEAM_PATTERN = re.compile(r'Team=(.*?)(?:\n|$)', re.IGNORECASE)
    QUAL_TIME_PATTERN = re.compile(r'QualTime=(.*?)(?:\n|$)', re.IGNORECASE)
    BEST_LAP_PATTERN = re.compile(r'BestLap=(.*?)(?:\n|$)', re.IGNORECASE)
    RACE_TIME_PATTERN = re.compile(r'RaceTime=(.*?)(?:\n|$)', re.IGNORECASE)
    LAPS_PATTERN = re.compile(r'Laps=(.*?)(?:\n|$)', re.IGNORECASE)
    
    # AIW patterns
    WAYPOINT_PATTERN = re.compile(r'\[Waypoint\](.*?)(?=\[|$)', re.DOTALL | re.IGNORECASE)
    QUAL_RATIO_PATTERN = re.compile(r'QualRatio\s*=\s*\(?([\d.eE+-]+)\)?', re.IGNORECASE)
    RACE_RATIO_PATTERN = re.compile(r'RaceRatio\s*=\s*\(?([\d.eE+-]+)\)?', re.IGNORECASE)
    
    def __init__(self, base_path: Optional[Path] = None):
        self.base_path = Path(base_path) if base_path else None
        self._aiw_cache: Dict[str, Path] = {}
    
    def parse_race_results(self, file_path: Path) -> Optional[RaceData]:
        """Parse raceresults.txt and return RaceData object"""
        try:
            if not file_path.exists():
                print(f"File not found: {file_path}")
                return None
            
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            data = RaceData()  # This will auto-set timestamp and race_id
            data.raw_content = content
            
            # Parse header info
            self._parse_header(content, data)
            
            # Parse driver slots
            self._parse_drivers(content, data)
            
            # Parse AIW ratios if we have AIW file and base path
            if data.aiw_file and self.base_path:
                self._parse_aiw_ratios(data)
            
            return data
            
        except Exception as e:
            print(f"Error parsing race results: {e}")
            traceback.print_exc()
            return None
    
    def _parse_header(self, content: str, data: RaceData):
        """Parse header information (track, AIW)"""
        # Look for Race section
        race_match = re.search(r'\[Race\](.*?)(?=\[|$)', content, re.DOTALL)
        if race_match:
            race_section = race_match.group(1)
            
            # Extract scene (track)
            scene_match = self.SCENE_PATTERN.search(race_section)
            if scene_match:
                scene = scene_match.group(1).strip().replace('\\', '/')
                scene_path = Path(scene)
                data.track_folder = scene_path.parent.name
                track_name = scene_path.stem
                # Strip leading digits from track name
                track_name = re.sub(r'^\d+', '', track_name)
                data.track_name = track_name
            
            # Extract AIW file
            aiw_match = self.AIDB_PATTERN.search(race_section)
            if aiw_match:
                aiw_path_str = aiw_match.group(1).strip().replace('\\', '/')
                data.aiw_path = Path(aiw_path_str)
                data.aiw_file = data.aiw_path.name
    
    def _parse_drivers(self, content: str, data: RaceData):
        """Parse driver information from slots"""
        ai_times_qual = []
        ai_times_race = []
        slot_counter = 0
        
        for slot_str, slot_content in self.SLOT_PATTERN.findall(content):
            slot = int(slot_str)
            slot_counter += 1
            
            name = self._extract(slot_content, self.DRIVER_PATTERN)
            vehicle = self._extract(slot_content, self.VEHICLE_PATTERN)
            team = self._extract(slot_content, self.TEAM_PATTERN)
            qual = self._extract(slot_content, self.QUAL_TIME_PATTERN)
            best = self._extract(slot_content, self.BEST_LAP_PATTERN)
            rtime = self._extract(slot_content, self.RACE_TIME_PATTERN)
            laps_s = self._extract(slot_content, self.LAPS_PATTERN)
            
            laps = int(laps_s) if laps_s and laps_s.isdigit() else None
            qual_sec = self._to_sec(qual)
            best_sec = self._to_sec(best)
            rtime_sec = self._to_sec(rtime)
            
            if slot == 0:
                # User driver
                data.user_name = name
                data.user_vehicle = vehicle
                data.user_best_lap = best
                data.user_best_lap_sec = best_sec or 0.0
                data.user_qualifying = qual
                data.user_qualifying_sec = qual_sec or 0.0
            else:
                # AI driver
                data.ai_count += 1
                ai_result = {
                    'slot': slot,
                    'driver_name': name,
                    'vehicle': vehicle,
                    'team': team,
                    'qual_time': qual,
                    'qual_time_sec': qual_sec,
                    'best_lap': best,
                    'best_lap_sec': best_sec,
                    'race_time': rtime,
                    'race_time_sec': rtime_sec,
                    'laps': laps
                }
                data.ai_results.append(ai_result)
                
                if qual_sec and qual_sec > 0:
                    ai_times_qual.append((qual_sec, qual))
                if best_sec and best_sec > 0:
                    ai_times_race.append((best_sec, best))
        
        # Calculate best/worst AI times
        if ai_times_qual:
            ai_times_qual.sort(key=lambda x: x[0])
            data.qual_best_ai_lap_sec, data.qual_best_ai_lap = ai_times_qual[0]
            data.qual_worst_ai_lap_sec, data.qual_worst_ai_lap = ai_times_qual[-1]
        
        if ai_times_race:
            ai_times_race.sort(key=lambda x: x[0])
            data.best_ai_lap_sec, data.best_ai_lap = ai_times_race[0]
            data.worst_ai_lap_sec, data.worst_ai_lap = ai_times_race[-1]
    
    def _parse_aiw_ratios(self, data: RaceData):
        """Parse QualRatio and RaceRatio from AIW file"""
        if not data.aiw_file:
            return
        
        # Find AIW file
        aiw_path = self._find_aiw_file(data.aiw_file, data.track_folder)
        
        if not aiw_path or not aiw_path.exists():
            print(f"AIW file not found: {data.aiw_file}")
            return
        
        data.aiw_path = aiw_path
        
        try:
            with open(aiw_path, 'rb') as f:
                raw = f.read()
            
            # Remove null bytes and decode
            content = raw.replace(b'\x00', b'').decode('utf-8', errors='ignore')
            
            # Find Waypoint section
            wp_match = self.WAYPOINT_PATTERN.search(content)
            if wp_match:
                section = wp_match.group(1)
                
                # Extract QualRatio
                q_match = self.QUAL_RATIO_PATTERN.search(section)
                if q_match:
                    data.qual_ratio = float(q_match.group(1))
                
                # Extract RaceRatio
                r_match = self.RACE_RATIO_PATTERN.search(section)
                if r_match:
                    data.race_ratio = float(r_match.group(1))
                    
        except Exception as e:
            print(f"Error parsing AIW ratios: {e}")
    
    def _find_aiw_file(self, aiw_filename: str, track_folder: Optional[str]) -> Optional[Path]:
        """Find AIW file using case-insensitive search"""
        if not self.base_path:
            return None
        
        # Check cache
        cache_key = f"{track_folder}_{aiw_filename}".lower()
        if cache_key in self._aiw_cache:
            cached = self._aiw_cache[cache_key]
            if cached.exists():
                return cached
            del self._aiw_cache[cache_key]
        
        locations_path = self.base_path / 'GameData' / 'Locations'
        if not locations_path.exists():
            return None
        
        filename_norm = Path(aiw_filename).name.lower()
        
        # Strategy 1: Use track folder
        if track_folder:
            track_lower = track_folder.lower()
            for folder in locations_path.iterdir():
                if folder.is_dir() and folder.name.lower() == track_lower:
                    # Look for exact filename match
                    for f in folder.iterdir():
                        if f.is_file() and f.name.lower() == filename_norm:
                            self._aiw_cache[cache_key] = f
                            return f
                    
                    # Look for any AIW file
                    for ext in ['*.AIW', '*.aiw']:
                        candidates = list(folder.glob(ext))
                        if candidates:
                            self._aiw_cache[cache_key] = candidates[0]
                            return candidates[0]
        
        # Strategy 2: Recursive search
        for root, _, files in os.walk(locations_path):
            for f in files:
                if f.lower() == filename_norm:
                    path = Path(root) / f
                    self._aiw_cache[cache_key] = path
                    return path
        
        return None
    
    def _extract(self, text: str, pattern: re.Pattern) -> Optional[str]:
        """Extract first match from text using pattern"""
        m = pattern.search(text)
        return m.group(1).strip() if m else None
    
    def _to_sec(self, time_str: Optional[str]) -> Optional[float]:
        """Convert time string to seconds"""
        if not time_str:
            return None
        
        time_str = time_str.strip()
        try:
            parts = time_str.split(':')
            if len(parts) == 3:
                # h:mm:ss.ms
                return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
            elif len(parts) == 2:
                # m:ss.ms
                return int(parts[0]) * 60 + float(parts[1])
            else:
                return float(time_str)
        except (ValueError, IndexError):
            return None


def format_time(seconds: float) -> str:
    """Format seconds as mm:ss.ms"""
    if seconds <= 0:
        return 'N/A'
    minutes = int(seconds) // 60
    secs = int(seconds) % 60
    ms = int((seconds - int(seconds)) * 1000)
    return f"{minutes}:{secs:02d}.{ms:03d}"


def get_display_text(data: RaceData) -> str:
    """Generate display text for popup"""
    lines = []
    lines.append("=" * 50)
    lines.append(f"🏁 {data.track_name or 'Unknown Track'} 🏁")
    lines.append("=" * 50)
    
    # AIW info
    if data.aiw_file:
        lines.append(f"\n📄 AIW File: {data.aiw_file}")
    
    # Ratios
    if data.qual_ratio is not None:
        lines.append(f"\n📊 Current Ratios:")
        lines.append(f"   Qualifying: {data.qual_ratio:.6f}")
    if data.race_ratio is not None:
        lines.append(f"   Race: {data.race_ratio:.6f}")
    
    # User info
    if data.user_name:
        lines.append(f"\n👤 Driver: {data.user_name}")
    if data.user_vehicle:
        lines.append(f"   Vehicle: {data.user_vehicle}")
    
    # User lap times
    if data.user_qualifying:
        lines.append(f"\n⏱️ Your Times:")
        lines.append(f"   Qualifying: {data.user_qualifying}")
    if data.user_best_lap:
        lines.append(f"   Best Lap: {data.user_best_lap}")
    
    # AI times
    ai_lines = []
    if data.qual_best_ai_lap:
        ai_lines.append(f"   Qual Best: {data.qual_best_ai_lap}")
    if data.qual_worst_ai_lap:
        ai_lines.append(f"   Qual Worst: {data.qual_worst_ai_lap}")
    if data.best_ai_lap:
        ai_lines.append(f"   Race Best: {data.best_ai_lap}")
    if data.worst_ai_lap:
        ai_lines.append(f"   Race Worst: {data.worst_ai_lap}")
    
    if ai_lines:
        lines.append(f"\n🤖 AI Times ({data.ai_count} drivers):")
        lines.extend(ai_lines)
    
    # AIW path
    if data.aiw_path:
        lines.append(f"\n📁 AIW Path: {data.aiw_path}")
    
    lines.append("\n" + "=" * 50)
    
    return "\n".join(lines)


if __name__ == "__main__":
    # Test the extractor
    import sys
    import traceback
    
    if len(sys.argv) > 1:
        test_file = Path(sys.argv[1])
    else:
        test_file = Path("test_mocks/UserData/Log/Results/raceresults.txt")
    
    if test_file.exists():
        print(f"Testing extraction on: {test_file}")
        extractor = DataExtractor()
        data = extractor.parse_race_results(test_file)
        
        if data and data.has_data():
            print(get_display_text(data))
            print("\nData points for curve:")
            for point in data.to_data_points():
                print(f"  {point[0]}: R={point[1]:.4f}, T={point[2]:.3f}s ({point[3]})")
            print(f"\nRace ID: {data.race_id}")
            print(f"Timestamp: {data.timestamp}")
        else:
            print("No data extracted")
    else:
        print(f"Test file not found: {test_file}")
