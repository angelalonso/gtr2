"""
Data structures and CSV handling for AIW Ratio Editor
"""

from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple
import csv
from pathlib import Path
from datetime import datetime


@dataclass
class LapTimes:
    """Container for lap time data"""
    pole: float = 0.0
    last_ai: float = 0.0
    player: float = 0.0
    ratio: float = 1.0
    
    @property
    def avg_ai(self) -> float:
        if self.pole > 0 and self.last_ai > 0:
            return (self.pole + self.last_ai) / 2
        return 0.0
    
    @property
    def ai_spread(self) -> float:
        if self.pole > 0 and self.last_ai > 0:
            return self.last_ai - self.pole
        return 0.0
    
    def are_valid(self) -> bool:
        return self.pole > 0 and self.last_ai > 0


class HistoricDataStore:
    """Stores and manages historic lap time data"""
    
    def __init__(self, csv_path: Optional[str] = None):
        self.csv_path = Path(csv_path) if csv_path else None
        self.qualifying_data: Dict[str, List[Tuple[float, float, float, float, str]]] = {}
        self.race_data: Dict[str, List[Tuple[float, float, float, float, str]]] = {}
        
        if self.csv_path and self.csv_path.exists():
            self.load_data()
    
    def load_data(self):
        """Load historic data from CSV"""
        if not self.csv_path or not self.csv_path.exists():
            return
        
        try:
            with open(self.csv_path, 'r') as f:
                reader = csv.DictReader(f, delimiter=';')
                
                for row in reader:
                    track = row.get('Track Name', '')
                    if not track:
                        continue
                    
                    # Qualifying data
                    try:
                        qual_ratio = float(row.get('Current QualRatio', '1.0'))
                        qual_best = float(row.get('Qual AI Best (s)', '0'))
                        qual_worst = float(row.get('Qual AI Worst (s)', '0'))
                        qual_user = float(row.get('Qual User (s)', '0'))
                        timestamp = row.get('Timestamp', '')
                        
                        if qual_best > 0 and qual_worst > 0:
                            if track not in self.qualifying_data:
                                self.qualifying_data[track] = []
                            self.qualifying_data[track].append((qual_ratio, qual_best, qual_worst, qual_user, timestamp))
                    except (ValueError, KeyError):
                        pass
                    
                    # Race data
                    try:
                        race_ratio = float(row.get('Current RaceRatio', '1.0'))
                        race_best = float(row.get('Race AI Best (s)', '0'))
                        race_worst = float(row.get('Race AI Worst (s)', '0'))
                        race_user = float(row.get('Race User (s)', '0'))
                        timestamp = row.get('Timestamp', '')
                        
                        if race_best > 0 and race_worst > 0:
                            if track not in self.race_data:
                                self.race_data[track] = []
                            self.race_data[track].append((race_ratio, race_best, race_worst, race_user, timestamp))
                    except (ValueError, KeyError):
                        pass
                    
        except Exception as e:
            print(f"Error loading historic data: {e}")
    
    def get_qualifying_points(self, track_name: str) -> List[Tuple[float, float, float, float, str]]:
        """Get qualifying data points for a track"""
        if track_name in self.qualifying_data:
            return self.qualifying_data[track_name]
        
        track_lower = track_name.lower()
        for key, points in self.qualifying_data.items():
            if track_lower in key.lower() or key.lower() in track_lower:
                return points
        
        return []
    
    def get_race_points(self, track_name: str) -> List[Tuple[float, float, float, float, str]]:
        """Get race data points for a track"""
        if track_name in self.race_data:
            return self.race_data[track_name]
        
        track_lower = track_name.lower()
        for key, points in self.race_data.items():
            if track_lower in key.lower() or key.lower() in track_lower:
                return points
        
        return []
    
    def add_data_point(self, track_name: str, times: LapTimes, is_qualifying: bool):
        """Add a new data point to the in-memory store"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        point = (times.ratio, times.pole, times.last_ai, times.player, timestamp)
        
        if is_qualifying:
            if track_name not in self.qualifying_data:
                self.qualifying_data[track_name] = []
            self.qualifying_data[track_name].append(point)
        else:
            if track_name not in self.race_data:
                self.race_data[track_name] = []
            self.race_data[track_name].append(point)
    
    def save_to_csv(self, track_name: str, times: LapTimes, is_qualifying: bool):
        """Save a data point to CSV file"""
        if not self.csv_path:
            return False
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        file_exists = self.csv_path.exists()
        
        try:
            self.csv_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.csv_path, 'a', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile, delimiter=';')
                
                if not file_exists or self.csv_path.stat().st_size == 0:
                    header = [
                        'Timestamp', 'Track Name', 'Current QualRatio',
                        'Qual AI Best (s)', 'Qual AI Worst (s)', 'Qual User (s)',
                        'Current RaceRatio', 'Race AI Best (s)', 'Race AI Worst (s)', 'Race User (s)'
                    ]
                    writer.writerow(header)
                
                if is_qualifying:
                    row = [
                        timestamp,
                        track_name,
                        f"{times.ratio:.6f}",
                        f"{times.pole:.3f}",
                        f"{times.last_ai:.3f}",
                        f"{times.player:.3f}" if times.player > 0 else "",
                        "", "", "", ""
                    ]
                else:
                    row = [
                        timestamp,
                        track_name,
                        "",
                        "", "", "",
                        f"{times.ratio:.6f}",
                        f"{times.pole:.3f}",
                        f"{times.last_ai:.3f}",
                        f"{times.player:.3f}" if times.player > 0 else ""
                    ]
                writer.writerow(row)
            
            self.add_data_point(track_name, times, is_qualifying)
            return True
            
        except Exception as e:
            print(f"Error saving to CSV: {e}")
            return False


class TimeConverter:
    """Utility for converting between time formats"""
    
    @staticmethod
    def seconds_to_mmssms(seconds: float) -> Tuple[int, int, int]:
        total_seconds = max(0, seconds)
        minutes = int(total_seconds) // 60
        secs = int(total_seconds) % 60
        ms = int((total_seconds - int(total_seconds)) * 1000)
        return minutes, secs, ms
    
    @staticmethod
    def mmssms_to_seconds(minutes: int, seconds: int, milliseconds: int) -> float:
        return minutes * 60 + seconds + milliseconds / 1000.0
    
    @staticmethod
    def format_time(seconds: float) -> str:
        minutes, secs, ms = TimeConverter.seconds_to_mmssms(seconds)
        return f"{minutes}:{secs:02d}.{ms:03d}"
