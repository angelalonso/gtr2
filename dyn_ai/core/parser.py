#!/usr/bin/env python3
"""
Race results parser - lightweight version
"""

import re
import traceback
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
    best_ai_lap_sec: float = 0.0
    worst_ai_lap_sec: float = 0.0
    qual_best_ai_lap_sec: float = 0.0
    qual_worst_ai_lap_sec: float = 0.0
    ai_count: int = 0
    ai_results: List[Dict] = field(default_factory=list)
    raw_content: str = ""
    
    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()
        if not self.race_id:
            self.race_id = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    
    def has_data(self) -> bool:
        return bool(self.track_name or self.aiw_file)
    
    def to_dict(self) -> Dict:
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
    
    def to_data_points_with_vehicles(self) -> List[Tuple[str, str, float, float, str]]:
        """Convert to data points with vehicle info"""
        points = []
        
        if self.qual_ratio:
            for ai in self.ai_results:
                if ai.get('qual_time_sec') and ai['qual_time_sec'] > 0:
                    points.append((self.track_name, ai.get('vehicle', 'Unknown'), 
                                  self.qual_ratio, ai['qual_time_sec'], 'qual'))
        
        if self.race_ratio:
            for ai in self.ai_results:
                if ai.get('best_lap_sec') and ai['best_lap_sec'] > 0:
                    points.append((self.track_name, ai.get('vehicle', 'Unknown'),
                                  self.race_ratio, ai['best_lap_sec'], 'race'))
        
        return points


class RaceDataParser:
    """Lightweight parser for race results files"""
    
    # Pre-compiled patterns
    SCENE_PATTERN = re.compile(r'Scene=(.*?)(?:\n|$)', re.IGNORECASE)
    AIDB_PATTERN = re.compile(r'AIDB=(.*?)(?:\n|$)', re.IGNORECASE)
    SLOT_PATTERN = re.compile(r'\[Slot(\d+)\](.*?)(?=\[Slot|\[END\]|$)', re.DOTALL)
    DRIVER_PATTERN = re.compile(r'Driver=(.*?)(?:\n|$)', re.IGNORECASE)
    VEHICLE_PATTERN = re.compile(r'Vehicle=(.*?)(?:\n|$)', re.IGNORECASE)
    QUAL_TIME_PATTERN = re.compile(r'QualTime=(.*?)(?:\n|$)', re.IGNORECASE)
    BEST_LAP_PATTERN = re.compile(r'BestLap=(.*?)(?:\n|$)', re.IGNORECASE)
    
    def parse(self, file_path: Path) -> Optional[RaceData]:
        """Parse raceresults.txt and return RaceData object"""
        try:
            if not file_path.exists():
                return None
            
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            if not content.strip():
                return None
            
            data = RaceData()
            data.raw_content = content[:5000]  # Keep only first 5KB for debugging
            
            self._parse_header(content, data)
            self._parse_drivers(content, data)
            
            return data if data.has_data() else None
            
        except Exception as e:
            print(f"Error parsing race results: {e}")
            return None
    
    def _parse_header(self, content: str, data: RaceData):
        """Parse header information"""
        race_match = re.search(r'\[Race\](.*?)(?=\[|$)', content, re.DOTALL)
        if race_match:
            race_section = race_match.group(1)
            
            scene_match = self.SCENE_PATTERN.search(race_section)
            if scene_match:
                scene = scene_match.group(1).strip().replace('\\', '/')
                scene_path = Path(scene)
                data.track_folder = scene_path.parent.name
                data.track_name = scene_path.stem
                data.track_name = re.sub(r'^\d+', '', data.track_name)
            
            aiw_match = self.AIDB_PATTERN.search(race_section)
            if aiw_match:
                aiw_path_str = aiw_match.group(1).strip().replace('\\', '/')
                data.aiw_path = Path(aiw_path_str)
                data.aiw_file = data.aiw_path.name
    
    def _parse_drivers(self, content: str, data: RaceData):
        """Parse driver information"""
        ai_times_qual = []
        ai_times_race = []
        
        for slot_str, slot_content in self.SLOT_PATTERN.findall(content):
            slot = int(slot_str)
            
            name = self._extract(slot_content, self.DRIVER_PATTERN)
            vehicle = self._extract(slot_content, self.VEHICLE_PATTERN)
            qual = self._extract(slot_content, self.QUAL_TIME_PATTERN)
            best = self._extract(slot_content, self.BEST_LAP_PATTERN)
            
            qual_sec = self._to_sec(qual)
            best_sec = self._to_sec(best)
            
            if slot == 0:
                data.user_name = name
                data.user_vehicle = vehicle
                data.user_best_lap = best
                data.user_best_lap_sec = best_sec or 0.0
                data.user_qualifying = qual
                data.user_qualifying_sec = qual_sec or 0.0
            else:
                data.ai_count += 1
                ai_result = {
                    'slot': slot,
                    'driver_name': name,
                    'vehicle': vehicle or 'Unknown',
                    'qual_time': qual,
                    'qual_time_sec': qual_sec,
                    'best_lap': best,
                    'best_lap_sec': best_sec,
                }
                data.ai_results.append(ai_result)
                
                if qual_sec and qual_sec > 0:
                    ai_times_qual.append(qual_sec)
                if best_sec and best_sec > 0:
                    ai_times_race.append(best_sec)
        
        # Calculate best/worst AI times
        if ai_times_qual:
            ai_times_qual.sort()
            data.qual_best_ai_lap_sec = ai_times_qual[0]
            data.qual_worst_ai_lap_sec = ai_times_qual[-1]
        
        if ai_times_race:
            ai_times_race.sort()
            data.best_ai_lap_sec = ai_times_race[0]
            data.worst_ai_lap_sec = ai_times_race[-1]
    
    def _extract(self, text: str, pattern: re.Pattern) -> Optional[str]:
        """Extract first match from text"""
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
                return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
            elif len(parts) == 2:
                return int(parts[0]) * 60 + float(parts[1])
            else:
                return float(time_str)
        except (ValueError, IndexError):
            return None
