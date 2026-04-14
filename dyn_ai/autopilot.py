#!/usr/bin/env python3
"""
Autopilot module for Live AI Tuner
Automatically adjusts AIW ratios based on detected race data and existing formulas

Core principle: 
- Use existing formulas as templates (keep the slope 'a' from similar data)
- Only adjust the height 'b' to fit the new data point
- This preserves the track characteristics learned from other sessions/cars
"""

import logging
import re
import sqlite3
import json
from pathlib import Path
from typing import Optional, Dict, List, Tuple, Any, Set
from dataclasses import dataclass, field
from datetime import datetime
from collections import defaultdict

from formula_funcs import fit_curve, hyperbolic, get_formula_string
from db_funcs import CurveDatabase
from data_extraction import RaceData

logger = logging.getLogger(__name__)

# Path to vehicle classes configuration file
VEHICLE_CLASSES_FILE = Path(__file__).parent / "vehicle_classes.json"


def load_vehicle_classes() -> Dict[str, Dict]:
    """Load vehicle class mappings from JSON file"""
    default_classes = {
        "Formula Cars": {
            "vehicles": ["Formula Senior", "Formula Junior", "Formula 3", "Formula Renault", "Formula Ford", "f4", "F4", "F3", "F2", "F1"]
        },
        "GT Cars": {
            "vehicles": ["Porsche 911", "Porsche 996", "Ferrari 550", "Ferrari 360", "Lamborghini Murcielago", "Saleen S7", "Corvette C5R", "Dodge Viper", "Aston Martin DBR9", "Maserati MC12", "gt", "GT", "GTE", "GT3"]
        },
        "Prototype Cars": {
            "vehicles": ["LMP1", "LMP2", "Audi R8", "Bentley Speed 8", "Cadillac LMP"]
        },
        "Production Cars": {
            "vehicles": ["BMW M3", "Audi R8 LMS", "Mercedes SLS"]
        }
    }
    
    if not VEHICLE_CLASSES_FILE.exists():
        logger.info(f"Creating default vehicle_classes.json file")
        with open(VEHICLE_CLASSES_FILE, 'w') as f:
            json.dump(default_classes, f, indent=2)
        return default_classes
    
    try:
        with open(VEHICLE_CLASSES_FILE, 'r') as f:
            classes = json.load(f)
        logger.debug(f"Loaded {len(classes)} vehicle classes from {VEHICLE_CLASSES_FILE}")
        return classes
    except Exception as e:
        logger.warning(f"Error loading {VEHICLE_CLASSES_FILE}: {e}, using defaults")
        return default_classes


def get_vehicle_class(vehicle_name: str, class_mapping: Dict[str, Dict]) -> str:
    """Get the class for a vehicle based on the loaded mapping."""
    vehicle_lower = vehicle_name.lower().strip()
    
    for class_name, class_data in class_mapping.items():
        vehicles = class_data.get("vehicles", [])
        for v in vehicles:
            if v.lower() == vehicle_lower:
                logger.debug(f"Mapped '{vehicle_name}' -> '{class_name}'")
                return class_name
    
    for class_name, class_data in class_mapping.items():
        vehicles = class_data.get("vehicles", [])
        for v in vehicles:
            if v.lower() in vehicle_lower or vehicle_lower in v.lower():
                logger.debug(f"Mapped '{vehicle_name}' -> '{class_name}' (partial)")
                return class_name
    
    logger.debug(f"No class for '{vehicle_name}', using as own class")
    return vehicle_name


@dataclass
class Formula:
    """Represents a stored formula for a track and vehicle class"""
    track: str
    vehicle_class: str
    a: float
    b: float
    session_type: str = "both"
    created_at: str = ""
    last_used: str = ""
    confidence: float = 1.0
    data_points_used: int = 0
    avg_error: float = 0.0
    max_error: float = 0.0
    vehicles_in_class: Set[str] = field(default_factory=set)
    
    def get_time_at_ratio(self, ratio: float) -> float:
        return hyperbolic(ratio, self.a, self.b)
    
    def get_ratio_for_time(self, lap_time: float) -> Optional[float]:
        denominator = lap_time - self.b
        if denominator <= 0:
            return None
        if self.a <= 0:
            return None
        return self.a / denominator
    
    def is_valid(self) -> bool:
        return self.a > 0 and self.b > 0 and self.b < 300
    
    def get_formula_string(self) -> str:
        return f"T = {self.a:.4f} / R + {self.b:.4f}"
    
    def adjust_height_to_point(self, ratio: float, lap_time: float) -> 'Formula':
        """
        Adjust the formula's height (b) to pass through the given point.
        Keeps the same slope (a), only changes b.
        b_new = T - a/R
        """
        old_b = self.b
        new_b = lap_time - (self.a / ratio)
        # Ensure b is reasonable
        new_b = max(10.0, min(200.0, new_b))
        
        logger.debug(f"Adjusting height: a={self.a:.4f} (unchanged), b={old_b:.4f} -> {new_b:.4f}")
        
        return Formula(
            track=self.track,
            vehicle_class=self.vehicle_class,
            a=self.a,
            b=new_b,
            session_type=self.session_type,
            confidence=self.confidence,
            data_points_used=self.data_points_used + 1,
            avg_error=self.avg_error,
            max_error=self.max_error,
            vehicles_in_class=self.vehicles_in_class.union({self.vehicle_class})
        )


class FormulaManager:
    """Manages formulas for tracks and vehicle classes"""
    
    def __init__(self, db: CurveDatabase):
        self.db = db
        self._formulas: Dict[str, Dict[str, Formula]] = {}
        self._class_mapping = load_vehicle_classes()
        self._init_database()
        self._load_formulas()
    
    def _init_database(self):
        """Initialize or migrate the database schema"""
        conn = sqlite3.connect(self.db.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS formulas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                track TEXT NOT NULL,
                vehicle_class TEXT NOT NULL,
                a REAL NOT NULL,
                b REAL NOT NULL,
                session_type TEXT NOT NULL,
                confidence REAL DEFAULT 1.0,
                data_points_used INTEGER DEFAULT 0,
                avg_error REAL DEFAULT 0.0,
                max_error REAL DEFAULT 0.0,
                vehicles_in_class TEXT DEFAULT '',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                last_used TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(track, vehicle_class, session_type)
            )
        """)
        
        conn.commit()
        conn.close()
    
    def _load_formulas(self):
        """Load all formulas from database"""
        self._formulas.clear()
        
        conn = sqlite3.connect(self.db.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT track, vehicle_class, a, b, session_type, confidence, data_points_used, avg_error, max_error, vehicles_in_class FROM formulas")
        rows = cursor.fetchall()
        conn.close()
        
        logger.debug(f"Loading formulas from database...")
        
        for row in rows:
            vehicles_str = row[9] if len(row) > 9 else ""
            vehicles_set = set(vehicles_str.split(',')) if vehicles_str else set()
            
            formula = Formula(
                track=row[0], vehicle_class=row[1], a=row[2], b=row[3],
                session_type=row[4], confidence=row[5], data_points_used=row[6],
                avg_error=row[7], max_error=row[8], vehicles_in_class=vehicles_set
            )
            if formula.is_valid():
                if formula.track not in self._formulas:
                    self._formulas[formula.track] = {}
                self._formulas[formula.track][formula.vehicle_class] = formula
                logger.debug(f"Loaded: [{formula.track}] [{formula.vehicle_class}] ({formula.session_type})")
        
        logger.info(f"Loaded {self.get_formula_count()} formulas from database")
    
    def get_formula(self, track: str, vehicle_name: str, session_type: str) -> Optional[Formula]:
        vehicle_class = get_vehicle_class(vehicle_name, self._class_mapping)
        track_dict = self._formulas.get(track, {})
        return track_dict.get(vehicle_class)
    
    def get_formula_by_class(self, track: str, vehicle_class: str, session_type: str) -> Optional[Formula]:
        track_dict = self._formulas.get(track, {})
        return track_dict.get(vehicle_class)
    
    def get_all_formulas_for_track(self, track: str) -> List[Formula]:
        return list(self._formulas.get(track, {}).values())
    
    def get_all_formulas_for_session(self, session_type: str) -> List[Formula]:
        formulas = []
        for track_dict in self._formulas.values():
            for formula in track_dict.values():
                if formula.session_type == session_type:
                    formulas.append(formula)
        return formulas
    
    def get_all_formulas(self) -> List[Formula]:
        formulas = []
        for track_dict in self._formulas.values():
            formulas.extend(track_dict.values())
        return formulas
    
    def get_formula_count(self) -> int:
        return sum(len(track_dict) for track_dict in self._formulas.values())
    
    def save_formula(self, formula: Formula) -> bool:
        if not formula.is_valid():
            logger.warning(f"Not saving invalid formula")
            return False
        
        conn = sqlite3.connect(self.db.db_path)
        cursor = conn.cursor()
        
        vehicles_str = ','.join(formula.vehicles_in_class)
        
        cursor.execute("""
            INSERT OR REPLACE INTO formulas 
            (track, vehicle_class, a, b, session_type, confidence, data_points_used, avg_error, max_error, vehicles_in_class, last_used)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, (formula.track, formula.vehicle_class, formula.a, formula.b, 
              formula.session_type, formula.confidence, formula.data_points_used,
              formula.avg_error, formula.max_error, vehicles_str))
        conn.commit()
        conn.close()
        
        # Update cache
        if formula.track not in self._formulas:
            self._formulas[formula.track] = {}
        self._formulas[formula.track][formula.vehicle_class] = formula
        
        logger.info(f"Saved formula: {formula.get_formula_string()}")
        return True


class AutopilotEngine:
    """Autopilot engine that adapts existing formulas to new data points"""
    
    def __init__(self, db: CurveDatabase, formula_manager: FormulaManager):
        self.db = db
        self.formula_manager = formula_manager
        self.silent_mode = False
        self._class_mapping = load_vehicle_classes()
    
    def _get_data_points(self, track: str, vehicle_class: str, session_type: str) -> List[Tuple[float, float]]:
        """Get all data points for a track/class from database"""
        conn = sqlite3.connect(self.db.db_path)
        cursor = conn.cursor()
        
        session_filter = "qual" if session_type == "qual" else "race"
        
        cursor.execute("""
            SELECT ratio, lap_time, vehicle 
            FROM data_points 
            WHERE track = ? AND session_type = ?
        """, (track, session_filter))
        
        rows = cursor.fetchall()
        
        points = []
        for ratio, lap_time, vehicle in rows:
            vehicle_class_of_point = get_vehicle_class(vehicle, self._class_mapping)
            if vehicle_class_of_point == vehicle_class:
                points.append((ratio, lap_time))
        
        conn.close()
        logger.debug(f"Found {len(points)} data points for {track}/{vehicle_class} ({session_type})")
        return points
    
    def _calculate_midpoint(self, points: List[Tuple[float, float]]) -> Tuple[float, float]:
        """Calculate the midpoint (average) of all points"""
        if not points:
            return None, None
        
        avg_ratio = sum(p[0] for p in points) / len(points)
        avg_time = sum(p[1] for p in points) / len(points)
        
        if len(points) == 1:
            logger.info(f"Single data point: R={avg_ratio:.4f}, T={avg_time:.2f}s")
        else:
            logger.info(f"Using {len(points)} data points → midpoint: R={avg_ratio:.4f}, T={avg_time:.2f}s")
        
        return avg_ratio, avg_time
    
    def _get_template_formula(self, track: str, vehicle_class: str, session_type: str) -> Optional[Formula]:
        """
        Get a template formula to adapt:
        1. Same track, same class, opposite session (qual <-> race)
        2. Same track, any class, same session (average of all)
        3. Any track, same class, same session (global by class)
        4. Any track, any class, same session (global average)
        5. Default formula
        """
        opposite_session = "race" if session_type == "qual" else "qual"
        
        # Method 1: Same track, same class, opposite session
        formula = self.formula_manager.get_formula_by_class(track, vehicle_class, opposite_session)
        if formula:
            logger.info(f"Using template: same track/class from {opposite_session} session")
            logger.info(f"  Template formula: {formula.get_formula_string()}")
            return formula
        
        # Method 2: Same track, any class, same session
        track_formulas = self.formula_manager.get_all_formulas_for_track(track)
        same_session_formulas = [f for f in track_formulas if f.session_type == session_type and f.is_valid()]
        
        if same_session_formulas:
            avg_a = sum(f.a for f in same_session_formulas) / len(same_session_formulas)
            avg_b = sum(f.b for f in same_session_formulas) / len(same_session_formulas)
            logger.info(f"Using template: average of {len(same_session_formulas)} formula(s) from same track")
            logger.info(f"  Template: a={avg_a:.4f}, b={avg_b:.4f}")
            return Formula(
                track=track,
                vehicle_class=vehicle_class,
                a=avg_a,
                b=avg_b,
                session_type=session_type,
                confidence=0.5,
                data_points_used=0
            )
        
        # Method 3: Any track, same class, same session
        all_formulas = self.formula_manager.get_all_formulas()
        same_class_same_session = [f for f in all_formulas if f.vehicle_class == vehicle_class and f.session_type == session_type and f.is_valid()]
        
        if same_class_same_session:
            avg_a = sum(f.a for f in same_class_same_session) / len(same_class_same_session)
            avg_b = sum(f.b for f in same_class_same_session) / len(same_class_same_session)
            logger.info(f"Using template: global average for {vehicle_class} class ({len(same_class_same_session)} formulas)")
            logger.info(f"  Template: a={avg_a:.4f}, b={avg_b:.4f}")
            return Formula(
                track=track,
                vehicle_class=vehicle_class,
                a=avg_a,
                b=avg_b,
                session_type=session_type,
                confidence=0.3,
                data_points_used=0
            )
        
        # Method 4: Any track, any class, same session
        all_same_session = [f for f in all_formulas if f.session_type == session_type and f.is_valid()]
        
        if all_same_session:
            avg_a = sum(f.a for f in all_same_session) / len(all_same_session)
            avg_b = sum(f.b for f in all_same_session) / len(all_same_session)
            logger.info(f"Using template: global average from all tracks ({len(all_same_session)} formulas)")
            logger.info(f"  Template: a={avg_a:.4f}, b={avg_b:.4f}")
            return Formula(
                track=track,
                vehicle_class=vehicle_class,
                a=avg_a,
                b=avg_b,
                session_type=session_type,
                confidence=0.2,
                data_points_used=0
            )
        
        # Method 5: Default formula
        logger.info(f"Using default formula (a=30.0, b=70.0) - no existing formulas found")
        logger.info(f"  This will adapt to your data as you collect more points")
        return Formula(
            track=track,
            vehicle_class=vehicle_class,
            a=30.0,
            b=70.0,
            session_type=session_type,
            confidence=0.1,
            data_points_used=0
        )
    
    def process_race_data(self, race_data: RaceData, aiw_path: Path) -> Dict[str, Any]:
        """Process race data - adapt existing formulas to new data points"""
        result = {
            "success": False,
            "qual_updated": False,
            "race_updated": False,
            "qual_new_ratio": None,
            "race_new_ratio": None,
            "qual_old_ratio": None,
            "race_old_ratio": None,
            "method": None,
            "message": ""
        }
        
        if not race_data.track_name:
            result["message"] = "No track name"
            return result
        
        track = race_data.track_name
        user_vehicle = race_data.user_vehicle or "Unknown"
        vehicle_class = get_vehicle_class(user_vehicle, self._class_mapping)
        
        logger.info(f"Processing race data for track '{track}', vehicle class '{vehicle_class}'")
        
        # Process qualifying
        if race_data.qual_ratio and race_data.qual_best_ai_lap_sec > 0 and race_data.qual_worst_ai_lap_sec > 0:
            result["qual_old_ratio"] = race_data.qual_ratio
            qual_midpoint = (race_data.qual_best_ai_lap_sec + race_data.qual_worst_ai_lap_sec) / 2
            
            logger.info(f"[Qualifying] New data: R={race_data.qual_ratio:.4f}, T={qual_midpoint:.2f}s")
            
            # Get existing data points for this class
            existing_points = self._get_data_points(track, vehicle_class, "qual")
            
            # Combine existing and new points
            all_points = existing_points + [(race_data.qual_ratio, qual_midpoint)]
            
            # Calculate the midpoint (average) of ALL points
            target_ratio, target_time = self._calculate_midpoint(all_points)
            
            if target_ratio is not None:
                # Get template formula
                template = self._get_template_formula(track, vehicle_class, "qual")
                
                # Adjust the template to hit the target point
                adapted_formula = template.adjust_height_to_point(target_ratio, target_time)
                logger.info(f"Adapted formula: {adapted_formula.get_formula_string()}")
                
                # Verify the adapted formula hits the target point
                verify_time = adapted_formula.get_time_at_ratio(target_ratio)
                logger.debug(f"Verification: at R={target_ratio:.4f}, T={verify_time:.2f}s (target {target_time:.2f}s)")
                
                # Save the formula
                self.formula_manager.save_formula(adapted_formula)
                
                # Calculate new ratio for the target lap time
                new_ratio = adapted_formula.get_ratio_for_time(qual_midpoint)
                
                if new_ratio and 0.3 < new_ratio < 3.0:
                    logger.info(f"New ratio needed: {new_ratio:.4f} (was {race_data.qual_ratio:.4f})")
                    
                    if self._update_aiw_ratio(aiw_path, "QualRatio", new_ratio):
                        result["qual_updated"] = True
                        result["qual_new_ratio"] = new_ratio
                        result["method"] = "adapt_template"
                        logger.info(f"✓ QualRatio updated in AIW")
                    else:
                        logger.error(f"Failed to update AIW file")
                else:
                    logger.warning(f"Invalid ratio calculated: {new_ratio}")
        
        # Process race
        if race_data.race_ratio and race_data.best_ai_lap_sec > 0 and race_data.worst_ai_lap_sec > 0:
            result["race_old_ratio"] = race_data.race_ratio
            race_midpoint = (race_data.best_ai_lap_sec + race_data.worst_ai_lap_sec) / 2
            
            logger.info(f"[Race] New data: R={race_data.race_ratio:.4f}, T={race_midpoint:.2f}s")
            
            # Get existing data points for this class
            existing_points = self._get_data_points(track, vehicle_class, "race")
            
            # Combine existing and new points
            all_points = existing_points + [(race_data.race_ratio, race_midpoint)]
            
            # Calculate the midpoint (average) of ALL points
            target_ratio, target_time = self._calculate_midpoint(all_points)
            
            if target_ratio is not None:
                # Get template formula
                template = self._get_template_formula(track, vehicle_class, "race")
                
                # Adjust the template to hit the target point
                adapted_formula = template.adjust_height_to_point(target_ratio, target_time)
                logger.info(f"Adapted formula: {adapted_formula.get_formula_string()}")
                
                # Verify the adapted formula hits the target point
                verify_time = adapted_formula.get_time_at_ratio(target_ratio)
                logger.debug(f"Verification: at R={target_ratio:.4f}, T={verify_time:.2f}s (target {target_time:.2f}s)")
                
                # Save the formula
                self.formula_manager.save_formula(adapted_formula)
                
                # Calculate new ratio for the target lap time
                new_ratio = adapted_formula.get_ratio_for_time(race_midpoint)
                
                if new_ratio and 0.3 < new_ratio < 3.0:
                    logger.info(f"New ratio needed: {new_ratio:.4f} (was {race_data.race_ratio:.4f})")
                    
                    if self._update_aiw_ratio(aiw_path, "RaceRatio", new_ratio):
                        result["race_updated"] = True
                        result["race_new_ratio"] = new_ratio
                        result["method"] = "adapt_template"
                        logger.info(f"✓ RaceRatio updated in AIW")
                    else:
                        logger.error(f"Failed to update AIW file")
                else:
                    logger.warning(f"Invalid ratio calculated: {new_ratio}")
        
        result["success"] = result["qual_updated"] or result["race_updated"]
        if not result["success"]:
            result["message"] = "No qualifying or race data available"
        
        return result
    
    def _update_aiw_ratio(self, aiw_path: Path, ratio_name: str, new_ratio: float) -> bool:
        try:
            if not aiw_path.exists():
                return False
            
            raw = aiw_path.read_bytes()
            content = raw.replace(b"\x00", b"").decode("utf-8", errors="ignore")
            
            pattern = rf'({re.escape(ratio_name)}\s*=\s*\(?)\s*[0-9.eE+-]+\s*(\)?)'
            new_content, count = re.subn(pattern, lambda m: f"{m.group(1)}{new_ratio:.6f}{m.group(2)}", content, flags=re.IGNORECASE)
            
            if count > 0:
                aiw_path.write_bytes(new_content.encode("utf-8", errors="ignore"))
                return True
            return False
        except Exception:
            return False


class AutopilotManager:
    def __init__(self, db: CurveDatabase):
        self.db = db
        self.formula_manager = FormulaManager(db)
        self.engine = AutopilotEngine(db, self.formula_manager)
        self.enabled = False
        self.silent = False
    
    def set_enabled(self, enabled: bool):
        self.enabled = enabled
        logger.info(f"Autopilot {'ENABLED' if enabled else 'DISABLED'}")
    
    def set_silent(self, silent: bool):
        self.silent = silent
        self.engine.silent_mode = silent
    
    def process_new_data(self, race_data: RaceData, aiw_path: Path) -> Dict[str, Any]:
        if not self.enabled:
            return {"success": False, "message": "Autopilot disabled"}
        return self.engine.process_race_data(race_data, aiw_path)
    
    def get_status(self) -> Dict[str, Any]:
        return {
            "enabled": self.enabled,
            "silent": self.silent,
            "formula_count": self.formula_manager.get_formula_count(),
            "tracks_with_formulas": list(self.formula_manager._formulas.keys())
        }
    
    def reload_formulas(self):
        self.formula_manager._load_formulas()


if __name__ == "__main__":
    from db_funcs import CurveDatabase
    db = CurveDatabase("ai_data.db")
    manager = AutopilotManager(db)
    manager.set_enabled(True)
    print(f"Status: {manager.get_status()}")
