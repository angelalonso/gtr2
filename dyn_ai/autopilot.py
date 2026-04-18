# autopilot.py - Fixed AIW backup (only once)
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
import shutil
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

# Track which AIW files have been backed up (global set to avoid double backups)
_BACKED_UP_AIW_FILES: Set[str] = set()


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
    if not vehicle_name:
        return "Unknown"
    
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
        
        logger.info(f"    Adjusting height: a={self.a:.4f} (unchanged), b={old_b:.4f} -> {new_b:.4f}")
        
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
        self._formulas: Dict[str, Dict[str, Dict[str, Formula]]] = {}  # track -> vehicle_class -> session_type -> Formula
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
        
        logger.info(f"Loading formulas from database...")
        
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
                if formula.vehicle_class not in self._formulas[formula.track]:
                    self._formulas[formula.track][formula.vehicle_class] = {}
                self._formulas[formula.track][formula.vehicle_class][formula.session_type] = formula
                logger.debug(f"Loaded: [{formula.track}] [{formula.vehicle_class}] [{formula.session_type}] -> {formula.get_formula_string()}")
        
        logger.info(f"Loaded {self.get_formula_count()} formulas from database")
    
    def get_formula(self, track: str, vehicle_name: str, session_type: str) -> Optional[Formula]:
        vehicle_class = get_vehicle_class(vehicle_name, self._class_mapping)
        track_dict = self._formulas.get(track, {})
        class_dict = track_dict.get(vehicle_class, {})
        return class_dict.get(session_type)
    
    def get_formula_by_class(self, track: str, vehicle_class: str, session_type: str) -> Optional[Formula]:
        track_dict = self._formulas.get(track, {})
        class_dict = track_dict.get(vehicle_class, {})
        return class_dict.get(session_type)
    
    def get_all_formulas_for_track(self, track: str) -> List[Formula]:
        formulas = []
        track_dict = self._formulas.get(track, {})
        for class_dict in track_dict.values():
            formulas.extend(class_dict.values())
        return formulas
    
    def get_all_formulas_for_session(self, session_type: str) -> List[Formula]:
        formulas = []
        for track_dict in self._formulas.values():
            for class_dict in track_dict.values():
                formula = class_dict.get(session_type)
                if formula:
                    formulas.append(formula)
        return formulas
    
    def get_all_formulas(self) -> List[Formula]:
        formulas = []
        for track_dict in self._formulas.values():
            for class_dict in track_dict.values():
                formulas.extend(class_dict.values())
        return formulas
    
    def get_formula_count(self) -> int:
        count = 0
        for track_dict in self._formulas.values():
            for class_dict in track_dict.values():
                count += len(class_dict)
        return count
    
    def get_tracks_with_formulas(self) -> List[str]:
        return list(self._formulas.keys())
    
    def save_formula(self, formula: Formula) -> bool:
        if not formula.is_valid():
            logger.warning(f"Not saving invalid formula: {formula.get_formula_string()}")
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
        if formula.vehicle_class not in self._formulas[formula.track]:
            self._formulas[formula.track][formula.vehicle_class] = {}
        self._formulas[formula.track][formula.vehicle_class][formula.session_type] = formula
        
        logger.info(f"Saved formula for {formula.track}/{formula.vehicle_class}/{formula.session_type}: {formula.get_formula_string()}")
        return True


class AutopilotEngine:
    """Autopilot engine that adapts existing formulas to new data points"""
    
    def __init__(self, db: CurveDatabase, formula_manager: FormulaManager):
        self.db = db
        self.formula_manager = formula_manager
        self.silent_mode = False
        self._class_mapping = load_vehicle_classes()
    
    def _backup_aiw_file(self, aiw_path: Path) -> bool:
        """Create a backup of an AIW file before modifying it - ONLY ONCE per file"""
        global _BACKED_UP_AIW_FILES
        
        # Check if already backed up in this session
        aiw_key = str(aiw_path.absolute())
        if aiw_key in _BACKED_UP_AIW_FILES:
            logger.debug(f"  AIW already backed up in this session: {aiw_path.name}")
            return True
        
        try:
            # Create backup directory
            backup_dir = Path(self.db.db_path).parent / "aiw_backups"
            backup_dir.mkdir(parents=True, exist_ok=True)
            
            # Create backup filename
            backup_name = f"{aiw_path.stem}_ORIGINAL{aiw_path.suffix}"
            backup_path = backup_dir / backup_name
            
            # Only backup if not already backed up (persistent check)
            if not backup_path.exists():
                shutil.copy2(aiw_path, backup_path)
                logger.info(f"  Created backup: {backup_path}")
            else:
                logger.debug(f"  Backup already exists: {backup_path}")
            
            _BACKED_UP_AIW_FILES.add(aiw_key)
            return True
        except Exception as e:
            logger.error(f"  Failed to backup AIW: {e}")
            return False
    
    def _get_data_points(self, track: str, vehicle_class: str, session_type: str) -> List[Tuple[float, float]]:
        """Get all data points for a track/class from database"""
        conn = sqlite3.connect(self.db.db_path)
        cursor = conn.cursor()
        
        session_filter = "qual" if session_type == "qual" else "race"
        
        cursor.execute("""
            SELECT ratio, lap_time, vehicle_class 
            FROM data_points 
            WHERE track = ? AND session_type = ? AND vehicle_class = ?
        """, (track, session_filter, vehicle_class))
        
        rows = cursor.fetchall()
        conn.close()
        
        points = [(ratio, lap_time) for ratio, lap_time, _ in rows]
        logger.debug(f"Found {len(points)} data points for {track}/{vehicle_class} ({session_type})")
        return points
    
    def _calculate_midpoint(self, points: List[Tuple[float, float]]) -> Tuple[Optional[float], Optional[float]]:
        """Calculate the midpoint (average) of all points"""
        if not points:
            return None, None
        
        avg_ratio = sum(p[0] for p in points) / len(points)
        avg_time = sum(p[1] for p in points) / len(points)
        
        if len(points) == 1:
            logger.info(f"  Single data point: R={avg_ratio:.4f}, T={avg_time:.2f}s")
        else:
            logger.info(f"  Using {len(points)} data points → midpoint: R={avg_ratio:.4f}, T={avg_time:.2f}s")
        
        return avg_ratio, avg_time
    
    def calculate_target_time_from_settings(self, best_ai_time, worst_ai_time, settings):
        """
        Calculate target AI time based on user's target settings.
        
        Args:
            best_ai_time: Fastest AI lap time in seconds
            worst_ai_time: Slowest AI lap time in seconds
            settings: Dict with keys: mode, percentage, offset_seconds, error_margin
    
        Returns:
            Target AI lap time in seconds
        """
        if best_ai_time <= 0 or worst_ai_time <= 0:
            return best_ai_time if best_ai_time > 0 else worst_ai_time
        
        ai_range = worst_ai_time - best_ai_time
        mode = settings.get("mode", "percentage")
        
        if mode == "percentage":
            pct = settings.get("percentage", 50) / 100.0
            target = best_ai_time + (ai_range * pct)
        elif mode == "faster_than_best":
            offset = settings.get("offset_seconds", 0.0)
            target = best_ai_time + offset
        else:  # slower_than_worst
            offset = settings.get("offset_seconds", 0.0)
            target = worst_ai_time - offset
        
        # Apply error margin (makes AI slower)
        error_margin = settings.get("error_margin", 0.0)
        target = target + error_margin
        
        # Ensure target is within reasonable bounds
        target = max(best_ai_time, min(worst_ai_time + error_margin, target))
        
        return target
    
    def _get_template_formula(self, track: str, vehicle_class: str, session_type: str) -> Formula:
        """
        Get a template formula to adapt:
        1. Same track, same class, same session (use existing formula for this track/class/session)
        2. Same track, same class, opposite session (qual <-> race)
        3. Same track, any class, same session (average of all formulas for this track)
        4. Any track, same class, same session (global by class)
        5. Any track, any class, same session (global average)
        6. Default formula
        """
        opposite_session = "race" if session_type == "qual" else "qual"
        
        # Method 1: Same track, same class, same session (existing formula)
        formula = self.formula_manager.get_formula_by_class(track, vehicle_class, session_type)
        if formula:
            logger.info(f"  Using existing formula for {track}/{vehicle_class}/{session_type}")
            logger.info(f"    Template: {formula.get_formula_string()}")
            return formula
        
        # Method 2: Same track, same class, opposite session
        opposite_formula = self.formula_manager.get_formula_by_class(track, vehicle_class, opposite_session)
        if opposite_formula:
            existing_points = self._get_data_points(track, vehicle_class, session_type)
            if len(existing_points) == 0:
                logger.info(f"  Using template: same track/class from {opposite_session} session (no existing {session_type} data)")
                logger.info(f"    Template: {opposite_formula.get_formula_string()}")
                return opposite_formula
            else:
                logger.info(f"  Have {len(existing_points)} existing {session_type} points, not using opposite session template")
        
        # Method 3: Same track, any class, same session (average of all)
        track_formulas = self.formula_manager.get_all_formulas_for_track(track)
        same_session_formulas = [f for f in track_formulas if f.session_type == session_type and f.is_valid()]
        
        if same_session_formulas:
            avg_a = sum(f.a for f in same_session_formulas) / len(same_session_formulas)
            avg_b = sum(f.b for f in same_session_formulas) / len(same_session_formulas)
            logger.info(f"  Using template: average of {len(same_session_formulas)} formula(s) from same track ({session_type})")
            logger.info(f"    Template: a={avg_a:.4f}, b={avg_b:.4f}")
            return Formula(
                track=track,
                vehicle_class=vehicle_class,
                a=avg_a,
                b=avg_b,
                session_type=session_type,
                confidence=0.5,
                data_points_used=0
            )
        
        # Method 4: Any track, same class, same session
        all_formulas = self.formula_manager.get_all_formulas()
        same_class_same_session = [f for f in all_formulas if f.vehicle_class == vehicle_class and f.session_type == session_type and f.is_valid()]
        
        if same_class_same_session:
            avg_a = sum(f.a for f in same_class_same_session) / len(same_class_same_session)
            avg_b = sum(f.b for f in same_class_same_session) / len(same_class_same_session)
            logger.info(f"  Using template: global average for {vehicle_class} class ({len(same_class_same_session)} formulas)")
            logger.info(f"    Template: a={avg_a:.4f}, b={avg_b:.4f}")
            return Formula(
                track=track,
                vehicle_class=vehicle_class,
                a=avg_a,
                b=avg_b,
                session_type=session_type,
                confidence=0.3,
                data_points_used=0
            )
        
        # Method 5: Any track, any class, same session
        all_same_session = [f for f in all_formulas if f.session_type == session_type and f.is_valid()]
        
        if all_same_session:
            avg_a = sum(f.a for f in all_same_session) / len(all_same_session)
            avg_b = sum(f.b for f in all_same_session) / len(all_same_session)
            logger.info(f"  Using template: global average from all tracks ({len(all_same_session)} formulas)")
            logger.info(f"    Template: a={avg_a:.4f}, b={avg_b:.4f}")
            return Formula(
                track=track,
                vehicle_class=vehicle_class,
                a=avg_a,
                b=avg_b,
                session_type=session_type,
                confidence=0.2,
                data_points_used=0
            )
        
        # Method 6: Default formula
        logger.info(f"  Using default formula (a=30.0, b=70.0) - no existing formulas found")
        logger.info(f"    This will adapt to your data as you collect more points")
        return Formula(
            track=track,
            vehicle_class=vehicle_class,
            a=30.0,
            b=70.0,
            session_type=session_type,
            confidence=0.1,
            data_points_used=0
        )
    
    def _process_session(self, track: str, vehicle_class: str, session_type: str, 
                         current_ratio: float, midpoint_time: float, aiw_path: Path,
                         ratio_name: str, ai_target_settings: Dict = None) -> Dict[str, Any]:
        """Process a single session (qualifying or race)"""
        result = {
            "updated": False,
            "old_ratio": current_ratio,
            "new_ratio": None,
            "formula": None
        }
        
        logger.info(f"\n{'='*50}")
        logger.info(f"[{session_type.upper()}] Processing {session_type} session")
        
        # Get existing data points for this class and session
        existing_points = self._get_data_points(track, vehicle_class, session_type)
        
        if existing_points and ai_target_settings:
            # Calculate best and worst AI times from existing points
            ai_times = [t for _, t in existing_points]
            best_ai_time = min(ai_times)
            worst_ai_time = max(ai_times)
            ai_range = worst_ai_time - best_ai_time
            
            logger.info(f"  AI range: {best_ai_time:.2f}s (best) to {worst_ai_time:.2f}s (worst) = {ai_range:.2f}s spread")
            
            # Calculate target time based on settings
            target_time = self.calculate_target_time_from_settings(
                best_ai_time, worst_ai_time, ai_target_settings
            )
            logger.info(f"  Target AI time from settings: {target_time:.2f}s")
        else:
            target_time = midpoint_time
            if existing_points:
                logger.info(f"  Using default target: {target_time:.2f}s (midpoint)")
            else:
                logger.info(f"  No existing points, using target: {target_time:.2f}s")
        
        logger.info(f"  New data point: R={current_ratio:.4f}, T={midpoint_time:.2f}s")
        logger.info(f"  Target point for formula: R={current_ratio:.4f}, T={target_time:.2f}s")
        
        # Get template formula
        template = self._get_template_formula(track, vehicle_class, session_type)
        
        # Adjust the template to hit the target point
        adapted_formula = template.adjust_height_to_point(current_ratio, target_time)
        logger.info(f"  Adapted formula: {adapted_formula.get_formula_string()}")
        
        # Save the formula
        self.formula_manager.save_formula(adapted_formula)
        result["formula"] = adapted_formula
        
        # Calculate new ratio for the target lap time
        new_ratio = adapted_formula.get_ratio_for_time(midpoint_time)
        
        if new_ratio and 0.3 < new_ratio < 3.0:
            logger.info(f"  New {ratio_name} needed: {new_ratio:.4f} (was {current_ratio:.4f})")
            
            if self._update_aiw_ratio(aiw_path, ratio_name, new_ratio):
                result["updated"] = True
                result["new_ratio"] = new_ratio
                logger.info(f"  Updated {ratio_name} in AIW")
            else:
                logger.error(f"  Failed to update AIW file")
        else:
            logger.warning(f"  Invalid ratio calculated: {new_ratio}")
        
        return result
    
    def process_race_data(self, race_data: RaceData, aiw_path: Path, ai_target_settings: Dict = None) -> Dict[str, Any]:
        """Process race data - adapt existing formulas to new data points for BOTH sessions"""
        result = {
            "success": False,
            "qual_updated": False,
            "race_updated": False,
            "qual_new_ratio": None,
            "race_new_ratio": None,
            "qual_old_ratio": None,
            "race_old_ratio": None,
            "qual_formula": None,
            "race_formula": None,
            "method": None,
            "message": ""
        }
        
        if not race_data.track_name:
            result["message"] = "No track name"
            return result
        
        track = race_data.track_name
        user_vehicle = race_data.user_vehicle or "Unknown"
        vehicle_class = get_vehicle_class(user_vehicle, self._class_mapping)
        
        logger.info(f"\n{'='*70}")
        logger.info(f"[AUTO] Autopilot - Processing race data")
        logger.info(f"{'='*70}")
        logger.info(f"  Track: '{track}'")
        logger.info(f"  User Vehicle: '{user_vehicle}' -> Class: '{vehicle_class}'")
        
        # Process qualifying
        if race_data.qual_ratio and race_data.qual_best_ai_lap_sec > 0 and race_data.qual_worst_ai_lap_sec > 0:
            result["qual_old_ratio"] = race_data.qual_ratio
            qual_midpoint = (race_data.qual_best_ai_lap_sec + race_data.qual_worst_ai_lap_sec) / 2
            
            qual_result = self._process_session(
                track, vehicle_class, "qual",
                race_data.qual_ratio, qual_midpoint, aiw_path, "QualRatio",
                ai_target_settings
            )
            
            result["qual_updated"] = qual_result["updated"]
            result["qual_new_ratio"] = qual_result["new_ratio"]
            result["qual_formula"] = qual_result["formula"]
        
        # Process race (separately!)
        if race_data.race_ratio and race_data.best_ai_lap_sec > 0 and race_data.worst_ai_lap_sec > 0:
            result["race_old_ratio"] = race_data.race_ratio
            race_midpoint = (race_data.best_ai_lap_sec + race_data.worst_ai_lap_sec) / 2
            
            race_result = self._process_session(
                track, vehicle_class, "race",
                race_data.race_ratio, race_midpoint, aiw_path, "RaceRatio",
                ai_target_settings
            )
            
            result["race_updated"] = race_result["updated"]
            result["race_new_ratio"] = race_result["new_ratio"]
            result["race_formula"] = race_result["formula"]
        
        result["success"] = result["qual_updated"] or result["race_updated"]
        
        # Summary
        logger.info(f"\n{'='*70}")
        logger.info(f"[AUTO] Autopilot Summary")
        logger.info(f"{'='*70}")
        if result["qual_updated"]:
            logger.info(f"  QUALIFYING: {result['qual_old_ratio']:.4f} -> {result['qual_new_ratio']:.4f}")
            if result["qual_formula"]:
                logger.info(f"    Formula: {result['qual_formula'].get_formula_string()}")
        else:
            logger.info(f"  QUALIFYING: No update (missing data or invalid ratio)")
        
        if result["race_updated"]:
            logger.info(f"  RACE: {result['race_old_ratio']:.4f} -> {result['race_new_ratio']:.4f}")
            if result["race_formula"]:
                logger.info(f"    Formula: {result['race_formula'].get_formula_string()}")
        else:
            logger.info(f"  RACE: No update (missing data or invalid ratio)")
        logger.info(f"{'='*70}\n")
        
        return result
    
    def _update_aiw_ratio(self, aiw_path: Path, ratio_name: str, new_ratio: float) -> bool:
        try:
            if not aiw_path.exists():
                logger.error(f"AIW file not found: {aiw_path}")
                return False
            
            # Create backup before modifying (only once per file)
            self._backup_aiw_file(aiw_path)
            
            raw = aiw_path.read_bytes()
            content = raw.replace(b"\x00", b"").decode("utf-8", errors="ignore")
            
            pattern = rf'({re.escape(ratio_name)}\s*=\s*\(?)\s*[0-9.eE+-]+\s*(\)?)'
            new_content, count = re.subn(pattern, lambda m: f"{m.group(1)}{new_ratio:.6f}{m.group(2)}", content, flags=re.IGNORECASE)
            
            if count > 0:
                aiw_path.write_bytes(new_content.encode("utf-8", errors="ignore"))
                logger.debug(f"Updated {ratio_name} to {new_ratio:.6f} in {aiw_path.name}")
                return True
            else:
                logger.warning(f"Could not find {ratio_name} pattern in {aiw_path.name}")
                return False
        except Exception as e:
            logger.error(f"Error updating AIW ratio: {e}")
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
    
    def process_new_data(self, race_data: RaceData, aiw_path: Path, ai_target_settings: Dict = None) -> Dict[str, Any]:
        if not self.enabled:
            return {"success": False, "message": "Autopilot disabled"}
        return self.engine.process_race_data(race_data, aiw_path, ai_target_settings)
    
    def get_status(self) -> Dict[str, Any]:
        return {
            "enabled": self.enabled,
            "silent": self.silent,
            "formula_count": self.formula_manager.get_formula_count(),
            "tracks_with_formulas": self.formula_manager.get_tracks_with_formulas()
        }
    
    def reload_formulas(self):
        self.formula_manager._load_formulas()


if __name__ == "__main__":
    from db_funcs import CurveDatabase
    db = CurveDatabase("ai_data.db")
    manager = AutopilotManager(db)
    manager.set_enabled(True)
    print(f"Status: {manager.get_status()}")
