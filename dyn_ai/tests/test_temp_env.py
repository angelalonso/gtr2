#!/usr/bin/env python3
"""
Temporary test environment with mock GTR2 structure
"""

import sys
from pathlib import Path

# Add parent directory to path so we can import application modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import os
import tempfile
import shutil
import json
from pathlib import Path
from typing import Dict, Optional, List, Tuple

import sys
sys.path.insert(0, str(Path(__file__).parent))

from core_config import DEFAULT_CONFIG, save_config


class TempTestEnvironment:
    """Create a temporary test environment with mock GTR2 structure"""
    
    def __init__(self):
        self.temp_dir = None
        self.test_data_dir = None
        self.base_path = None
        self.mock_aiw_files = {}
        self.config_path = None
        self.classes_path = None
        self.results_path = None
        
    def create(self):
        """Create the test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.test_data_dir = Path(self.temp_dir)
        self.base_path = self.test_data_dir / "GTR2"
        
        self._create_directory_structure()
        self._create_mock_config()
        self._create_mock_vehicle_classes()
        self._create_mock_aiw_files()
        self._create_mock_car_files()
        
        self.results_path = self.base_path / "UserData" / "Log" / "Results" / "raceresults.txt"
        
        return self
    
    def _create_directory_structure(self):
        """Create GTR2 directory structure"""
        self.base_path.mkdir(parents=True, exist_ok=True)
        
        locations_dir = self.base_path / "GameData" / "Locations"
        locations_dir.mkdir(parents=True, exist_ok=True)
        
        teams_dir = self.base_path / "GameData" / "Teams"
        teams_dir.mkdir(parents=True, exist_ok=True)
        
        results_dir = self.base_path / "UserData" / "Log" / "Results"
        results_dir.mkdir(parents=True, exist_ok=True)
    
    def _create_mock_config(self):
        """Create mock configuration file"""
        self.config_path = self.test_data_dir / "cfg_test.yml"
        config = DEFAULT_CONFIG.copy()
        config['base_path'] = str(self.base_path)
        config['db_path'] = str(self.test_data_dir / "test_data.db")
        config['min_ratio'] = 0.3
        config['max_ratio'] = 2.5
        save_config(config, str(self.config_path))
    
    def _create_mock_vehicle_classes(self):
        """Create mock vehicle classes file"""
        self.classes_path = self.test_data_dir / "vehicle_classes.json"
        classes = {
            "GT_0304": {
                "classes": ["GT_0304"],
                "vehicles": ["Test Car GT", "Ferrari 550", "Porsche 911 GT2"]
            },
            "NGT_0304": {
                "classes": ["NGT_0304"],
                "vehicles": ["Test Car NGT", "Ferrari 360", "Porsche GT3"]
            },
            "Formula_4": {
                "classes": ["Formula_4"],
                "vehicles": ["Formula 4", "Formula BMW", "F4"]
            },
            "OTHER": {
                "classes": ["OTHER"],
                "vehicles": ["Safety Car"]
            }
        }
        with open(self.classes_path, 'w') as f:
            json.dump(classes, f, indent=2)
    
    def _create_mock_aiw_files(self):
        """Create mock AIW files for various tracks"""
        tracks = [
            ("Monza", "4Monza"),
            ("Silverstone", "Silverstone"),
            ("Spa", "Spa"),
            ("Nurburgring", "Nurburgring"),
            ("Donington", "Donington")
        ]
        
        for track_name, aiw_stem in tracks:
            track_dir = self.base_path / "GameData" / "Locations" / track_name
            track_dir.mkdir(parents=True, exist_ok=True)
            aiw_path = track_dir / f"{aiw_stem}.AIW"
            
            content = f"""[Waypoint]
BestAdjust = 1.000000
QualRatio = 1.000000
RaceRatio = 1.000000
NumWaypoints = 100
"""
            aiw_path.write_text(content)
            self.mock_aiw_files[track_name] = aiw_path
            
            # Verify the file was created
            if not aiw_path.exists():
                print(f"Warning: Failed to create AIW file at {aiw_path}")
    
    def _create_mock_car_files(self):
        """Create mock car files"""
        car_data = [
            ("TestCarGT", "Test Car GT"),
            ("TestCarNGT", "Test Car NGT"),
            ("Ferrari550", "Ferrari 550"),
            ("Porsche911GT2", "Porsche 911 GT2"),
            ("Formula4", "Formula 4")
        ]
        
        teams_dir = self.base_path / "GameData" / "Teams"
        for filename, description in car_data:
            car_dir = teams_dir / filename
            car_dir.mkdir(parents=True, exist_ok=True)
            car_path = car_dir / f"{filename}.car"
            
            content = f"""[General]
Description = "{description}"
Year = 2004
Make = Test
"""
            car_path.write_text(content)
    
    def create_mock_race_results(self, 
                                 track: str = "Monza",
                                 user_vehicle: str = "Test Car GT",
                                 user_qual_time: float = 90.0,
                                 user_race_time: float = 88.0,
                                 ai_best_qual: float = 92.0,
                                 ai_worst_qual: float = 98.0,
                                 ai_best_race: float = 90.0,
                                 ai_worst_race: float = 96.0,
                                 num_ai: int = 10) -> Path:
        """Create a mock raceresults.txt file"""
        content = f"""[Race]
Scene=GAMEDATA\\LOCATIONS\\{track}\\{track}.TRK
AIDB=GAMEDATA\\LOCATIONS\\{track}\\{track}.AIW

[Slot0]
Driver=Player
Vehicle={user_vehicle}
Team=Player Team
QualTime={self._format_time(user_qual_time)}
BestLap={self._format_time(user_race_time)}
RaceTime={self._format_time(user_race_time * 20)}
Laps=20

"""
        for i in range(1, num_ai + 1):
            if i % 2 == 0:
                qual_time = ai_best_qual + (i / num_ai) * (ai_worst_qual - ai_best_qual)
                race_time = ai_best_race + (i / num_ai) * (ai_worst_race - ai_best_race)
            else:
                qual_time = ai_worst_qual - (i / num_ai) * (ai_worst_qual - ai_best_qual)
                race_time = ai_worst_race - (i / num_ai) * (ai_worst_race - ai_best_race)
            
            content += f"""
[Slot{i}]
Driver=AI Driver {i}
Vehicle=AI Car {i}
Team=AI Team {i}
QualTime={self._format_time(qual_time)}
BestLap={self._format_time(race_time)}
RaceTime={self._format_time(race_time * 20)}
Laps=20

"""
        
        self.results_path.parent.mkdir(parents=True, exist_ok=True)
        self.results_path.write_text(content)
        return self.results_path
    
    def _format_time(self, seconds: float) -> str:
        """Format seconds to MM:SS.mmm"""
        minutes = int(seconds) // 60
        secs = int(seconds) % 60
        ms = int((seconds - int(seconds)) * 1000)
        return f"{minutes}:{secs:02d}.{ms:03d}"
    
    def modify_aiw_ratios(self, track: str, qual_ratio: float = None, race_ratio: float = None):
        """Modify AIW file ratios"""
        if track not in self.mock_aiw_files:
            return False
        
        aiw_path = self.mock_aiw_files[track]
        if not aiw_path.exists():
            return False
            
        content = aiw_path.read_text()
        
        if qual_ratio is not None:
            content = content.replace("QualRatio = 1.000000", f"QualRatio = {qual_ratio:.6f}")
        if race_ratio is not None:
            content = content.replace("RaceRatio = 1.000000", f"RaceRatio = {race_ratio:.6f}")
        
        aiw_path.write_text(content)
        return True
    
    def get_aiw_ratios(self, track: str) -> Tuple[Optional[float], Optional[float]]:
        """Get current AIW ratios"""
        if track not in self.mock_aiw_files:
            return None, None
        
        aiw_path = self.mock_aiw_files[track]
        if not aiw_path.exists():
            return None, None
            
        content = aiw_path.read_text()
        
        qual_ratio = None
        race_ratio = None
        
        for line in content.split('\n'):
            if 'QualRatio' in line:
                try:
                    parts = line.split('=')
                    if len(parts) >= 2:
                        qual_ratio = float(parts[1].strip())
                except:
                    pass
            if 'RaceRatio' in line:
                try:
                    parts = line.split('=')
                    if len(parts) >= 2:
                        race_ratio = float(parts[1].strip())
                except:
                    pass
        
        return qual_ratio, race_ratio
    
    def make_aiw_readonly(self, track: str):
        """Make AIW file read-only to test write failures"""
        if track not in self.mock_aiw_files:
            return False
            
        aiw_path = self.mock_aiw_files[track]
        if not aiw_path.exists():
            return False
            
        try:
            os.chmod(aiw_path, 0o444)
            return True
        except Exception as e:
            print(f"Warning: Could not make {aiw_path} readonly: {e}")
            return False
    
    def make_aiw_writable(self, track: str):
        """Make AIW file writable again"""
        if track not in self.mock_aiw_files:
            return False
            
        aiw_path = self.mock_aiw_files[track]
        if not aiw_path.exists():
            return False
            
        try:
            os.chmod(aiw_path, 0o644)
            return True
        except Exception as e:
            print(f"Warning: Could not make {aiw_path} writable: {e}")
            return False
    
    def create_corrupt_aiw(self, track: str):
        """Create a corrupt AIW file"""
        if track not in self.mock_aiw_files:
            return False
            
        aiw_path = self.mock_aiw_files[track]
        if not aiw_path.exists():
            return False
            
        try:
            aiw_path.write_bytes(b"\x00\x00\xff\xffcorrupt data\x00\x00")
            return True
        except Exception as e:
            print(f"Warning: Could not corrupt {aiw_path}: {e}")
            return False
    
    def create_corrupt_race_results(self):
        """Create a corrupt raceresults.txt file"""
        try:
            self.results_path.parent.mkdir(parents=True, exist_ok=True)
            self.results_path.write_bytes(b"\x00\xff\x00\xffcorrupt data\x00\x00")
            return self.results_path
        except Exception as e:
            print(f"Warning: Could not create corrupt race results: {e}")
            return self.results_path
    
    def create_duplicate_aiw_files(self, track: str):
        """Create multiple AIW files with similar names in the same folder"""
        if track not in self.mock_aiw_files:
            return False
        
        aiw_path = self.mock_aiw_files[track]
        if not aiw_path.exists():
            return False
        
        track_dir = aiw_path.parent
        original_stem = aiw_path.stem
        
        try:
            duplicate_path = track_dir / f"1{original_stem}.AIW"
            if not duplicate_path.exists():
                shutil.copy2(aiw_path, duplicate_path)
            
            duplicate_path2 = track_dir / f"{original_stem}.aiw"
            if not duplicate_path2.exists():
                shutil.copy2(aiw_path, duplicate_path2)
            
            return True
        except Exception as e:
            print(f"Warning: Could not create duplicate AIW files: {e}")
            return False
    
    def create_race_results_with_missing_sections(self, missing: List[str] = None):
        """Create race results with missing sections"""
        if missing is None:
            missing = []
        
        content = "[Race]\n"
        if 'scene' not in missing:
            content += "Scene=GAMEDATA\\LOCATIONS\\Monza\\Monza.TRK\n"
        if 'aidb' not in missing:
            content += "AIDB=GAMEDATA\\LOCATIONS\\Monza\\Monza.AIW\n"
        
        content += "\n[Slot0]\nDriver=Player\nVehicle=Test Car\n"
        
        if 'best_lap' not in missing:
            content += "BestLap=1:30.000\n"
        if 'qual_time' not in missing:
            content += "QualTime=1:32.000\n"
        
        self.results_path.parent.mkdir(parents=True, exist_ok=True)
        self.results_path.write_text(content)
        return self.results_path
    
    def ensure_aiw_exists(self, track: str) -> bool:
        """Ensure AIW file exists for a track, creating if necessary"""
        if track in self.mock_aiw_files and self.mock_aiw_files[track].exists():
            return True
        
        # Create the missing AIW file
        track_dir = self.base_path / "GameData" / "Locations" / track
        track_dir.mkdir(parents=True, exist_ok=True)
        aiw_path = track_dir / f"{track}.AIW"
        
        content = f"""[Waypoint]
BestAdjust = 1.000000
QualRatio = 1.000000
RaceRatio = 1.000000
NumWaypoints = 100
"""
        aiw_path.write_text(content)
        self.mock_aiw_files[track] = aiw_path
        return True
    
    def cleanup(self):
        """Clean up test environment"""
        try:
            if self.temp_dir and Path(self.temp_dir).exists():
                shutil.rmtree(self.temp_dir, ignore_errors=True)
        except Exception:
            pass
    
    def __enter__(self):
        return self.create()
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup()
