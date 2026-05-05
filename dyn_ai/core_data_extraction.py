#!/usr/bin/env python3
"""
Data extraction module for parsing race results and AIW files
Extracts track info, AIW ratios, and lap times from raceresults.txt
"""

import re
import os
import traceback
import logging
from pathlib import Path
from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass, field
from datetime import datetime

from core_aiw_utils import find_aiw_file_from_path, update_aiw_ratio, ensure_aiw_has_ratios

logger = logging.getLogger(__name__)


@dataclass
class RaceData:
    """Container for extracted race data"""
    race_id: Optional[str] = None
    timestamp: Optional[str] = None
    track_name: Optional[str] = None
    track_folder: Optional[str] = None
    aiw_file: Optional[str] = None
    aiw_path: Optional[Path] = None
    aiw_relative_path: Optional[str] = None
    aiw_error: Optional[str] = None
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
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()
        if not self.race_id:
            self.race_id = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    
    def has_data(self) -> bool:
        return bool(self.track_name or self.aiw_file or self.qual_ratio or self.race_ratio)
    
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
        """Convert to data points with CORRECT VEHICLE for each AI driver"""
        points = []
        
        if self.qual_ratio:
            for ai in self.ai_results:
                if ai.get('qual_time_sec') and ai['qual_time_sec'] > 0:
                    vehicle = ai.get('vehicle', 'Unknown')
                    points.append((self.track_name, vehicle, self.qual_ratio, ai['qual_time_sec'], 'qual'))
        
        if self.race_ratio:
            for ai in self.ai_results:
                if ai.get('best_lap_sec') and ai['best_lap_sec'] > 0:
                    vehicle = ai.get('vehicle', 'Unknown')
                    points.append((self.track_name, vehicle, self.race_ratio, ai['best_lap_sec'], 'race'))
        
        return points
    
    def get_all_ai_times(self, session_type: str = "race") -> List[float]:
        times = []
        for ai in self.ai_results:
            if session_type == "qual" and ai.get('qual_time_sec'):
                times.append(ai['qual_time_sec'])
            elif session_type == "race" and ai.get('best_lap_sec'):
                times.append(ai['best_lap_sec'])
        return sorted(times)
    
    def get_ai_statistics(self, session_type: str = "race") -> Dict:
        times = self.get_all_ai_times(session_type)
        if not times:
            return {"count": 0, "min": 0, "max": 0, "mean": 0, "median": 0, "std": 0}
        
        import statistics
        return {
            "count": len(times),
            "min": min(times),
            "max": max(times),
            "mean": statistics.mean(times),
            "median": statistics.median(times),
            "std": statistics.stdev(times) if len(times) > 1 else 0
        }


class DataExtractor:
    """Extracts race data from raceresults.txt and AIW files"""
    
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
    
    WAYPOINT_PATTERN = re.compile(r'\[Waypoint\](.*?)(?=\[|$)', re.DOTALL | re.IGNORECASE)
    QUAL_RATIO_PATTERN = re.compile(r'QualRatio\s*=\s*\(?([\d.eE+-]+)\)?', re.IGNORECASE)
    RACE_RATIO_PATTERN = re.compile(r'RaceRatio\s*=\s*\(?([\d.eE+-]+)\)?', re.IGNORECASE)
    
    def __init__(self, base_path: Optional[Path] = None):
        self.base_path = Path(base_path) if base_path else None
        self._aiw_cache: Dict[str, Path] = {}
    
    def parse_race_results(self, file_path: Path) -> Optional[RaceData]:
        try:
            if not file_path.exists():
                print(f"File not found: {file_path}")
                return None
            
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            data = RaceData()
            data.raw_content = content
            
            self._parse_header(content, data)
            self._parse_drivers(content, data)
            
            print(f"\n[DataExtractor] Parsed race data for {data.track_name or 'Unknown'}:")
            print(f"  User: {data.user_name or 'Unknown'} ({data.user_vehicle or 'Unknown'})")
            print(f"  AI Drivers: {data.ai_count}")
            
            if data.aiw_relative_path and self.base_path:
                self._resolve_aiw_path(data)
            
            return data
            
        except Exception as e:
            print(f"Error parsing race results: {e}")
            traceback.print_exc()
            return None
    
    def _parse_header(self, content: str, data: RaceData):
        race_match = re.search(r'\[Race\](.*?)(?=\[|$)', content, re.DOTALL)
        if race_match:
            race_section = race_match.group(1)
            
            scene_match = self.SCENE_PATTERN.search(race_section)
            if scene_match:
                scene = scene_match.group(1).strip().replace('\\', '/')
                scene_path = Path(scene)
                data.track_folder = scene_path.parent.name
                track_name = scene_path.stem
                track_name = re.sub(r'^\d+', '', track_name)
                data.track_name = track_name
            
            aiw_match = self.AIDB_PATTERN.search(race_section)
            if aiw_match:
                aiw_path_str = aiw_match.group(1).strip().replace('\\', '/')
                data.aiw_relative_path = aiw_path_str
                data.aiw_file = Path(aiw_path_str).name
    
    def _resolve_aiw_path(self, data: RaceData):
        if not data.aiw_relative_path or not self.base_path:
            error_msg = f"No AIW relative path or base path to resolve (path={data.aiw_relative_path}, base={self.base_path})"
            logger.error(error_msg)
            data.aiw_error = error_msg
            return
        
        logger.info(f"Resolving AIW path from: {data.aiw_relative_path}")
        logger.info(f"Base path: {self.base_path}")
        
        aiw_path = find_aiw_file_from_path(data.aiw_relative_path, self.base_path)
        
        if aiw_path and aiw_path.exists():
            data.aiw_path = aiw_path
            logger.info(f"Successfully resolved AIW path: {aiw_path}")
            self._parse_aiw_ratios(data)
        else:
            error_msg = f"AIW file not found for path: {data.aiw_relative_path}"
            logger.error(error_msg)
            logger.error(f"  Full base path: {self.base_path}")
            logger.error(f"  Expected location: {self.base_path / data.aiw_relative_path}")
            data.aiw_error = error_msg
    
    def _parse_aiw_ratios(self, data: RaceData):
        if not data.aiw_path or not data.aiw_path.exists():
            error_msg = f"AIW file not found: {data.aiw_path}"
            logger.error(error_msg)
            data.aiw_error = error_msg
            return
        
        try:
            with open(data.aiw_path, 'rb') as f:
                raw = f.read()
            
            content = raw.replace(b'\x00', b'').decode('utf-8', errors='ignore')
            
            wp_match = self.WAYPOINT_PATTERN.search(content)
            if wp_match:
                section = wp_match.group(1)
                
                q_match = self.QUAL_RATIO_PATTERN.search(section)
                if q_match:
                    data.qual_ratio = float(q_match.group(1))
                    print(f"  QualRatio from AIW: {data.qual_ratio:.6f}")
                
                r_match = self.RACE_RATIO_PATTERN.search(section)
                if r_match:
                    data.race_ratio = float(r_match.group(1))
                    print(f"  RaceRatio from AIW: {data.race_ratio:.6f}")
                    
        except Exception as e:
            print(f"Error parsing AIW ratios: {e}")
    
    def _parse_drivers(self, content: str, data: RaceData):
        ai_times_qual = []
        ai_times_race = []
        
        for slot_str, slot_content in self.SLOT_PATTERN.findall(content):
            slot = int(slot_str)
            
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
                    ai_times_qual.append((qual_sec, name, vehicle))
                if best_sec and best_sec > 0:
                    ai_times_race.append((best_sec, name, vehicle))
        
        if ai_times_qual:
            ai_times_qual.sort(key=lambda x: x[0])
            data.qual_best_ai_lap_sec, data.qual_best_ai_lap, _ = ai_times_qual[0]
            data.qual_worst_ai_lap_sec, data.qual_worst_ai_lap, _ = ai_times_qual[-1]
            print(f"  Qualifying: {len(ai_times_qual)} AI times, best={data.qual_best_ai_lap_sec:.3f}s, worst={data.qual_worst_ai_lap_sec:.3f}s")
        
        if ai_times_race:
            ai_times_race.sort(key=lambda x: x[0])
            data.best_ai_lap_sec, data.best_ai_lap, _ = ai_times_race[0]
            data.worst_ai_lap_sec, data.worst_ai_lap, _ = ai_times_race[-1]
            print(f"  Race: {len(ai_times_race)} AI times, best={data.best_ai_lap_sec:.3f}s, worst={data.worst_ai_lap_sec:.3f}s")
    
    def _extract(self, text: str, pattern: re.Pattern) -> Optional[str]:
        m = pattern.search(text)
        return m.group(1).strip() if m else None
    
    def _to_sec(self, time_str: Optional[str]) -> Optional[float]:
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


def format_time(seconds: float) -> str:
    if seconds <= 0:
        return 'N/A'
    minutes = int(seconds) // 60
    secs = int(seconds) % 60
    ms = int((seconds - int(seconds)) * 1000)
    return f"{minutes}:{secs:02d}.{ms:03d}"
