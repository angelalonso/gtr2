#!/usr/bin/env python3
"""
Autopilot module for Live AI Tuner
Automatically adjusts AIW ratios based on detected race data

Core principle: 
- Use base a=32 unless a formula exists for this track/car combo
- Calculate b from new data point: b = T - a/R
- This creates a simple formula that fits the new data point exactly
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

from formula_funcs import hyperbolic, get_formula_string
from db_funcs import CurveDatabase
from data_extraction import RaceData

logger = logging.getLogger(__name__)

# Path to vehicle classes configuration file
VEHICLE_CLASSES_FILE = Path(__file__).parent / "vehicle_classes.json"

# Track which AIW files have been backed up
_BACKED_UP_AIW_FILES: Set[str] = set()

# Default 'a' value for formulas
DEFAULT_A_VALUE = 32.0


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
        with open(VEHICLE_CLASSES_FILE, 'w') as f:
            json.dump(default_classes, f, indent=2)
        return default_classes
    
    try:
        with open(VEHICLE_CLASSES_FILE, 'r') as f:
            classes = json.load(f)
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
                return class_name
    
    for class_name, class_data in class_mapping.items():
        vehicles = class_data.get("vehicles", [])
        for v in vehicles:
            if v.lower() in vehicle_lower or vehicle_lower in v.lower():
                return class_name
    
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
    
    @classmethod
    def from_point(cls, track: str, vehicle_class: str, ratio: float, lap_time: float, session_type: str, a_value: float = DEFAULT_A_VALUE) -> 'Formula':
        """
        Create a formula from a single data point using fixed a value.
        b = T - a/R
        """
        b = lap_time - (a_value / ratio)
        b = max(10.0, min(200.0, b))
        
        logger.debug(f"  Created formula from point: a={a_value:.4f}, b={b:.4f}")
        
        return cls(
            track=track,
            vehicle_class=vehicle_class,
            a=a_value,
            b=b,
            session_type=session_type,
            confidence=0.5,
            data_points_used=1,
            vehicles_in_class={vehicle_class}
        )
    
    def adjust_height_to_point(self, ratio: float, lap_time: float) -> 'Formula':
        """
        Adjust the formula's height (b) to pass through the given point.
        Keeps the same slope (a), only changes b.
        b_new = T - a/R
        """
        old_b = self.b
        new_b = lap_time - (self.a / ratio)
        new_b = max(10.0, min(200.0, new_b))
        
        logger.debug(f"    Adjusting height: a={self.a:.4f} (unchanged), b={old_b:.4f} -> {new_b:.4f}")
        
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
        self._formulas: Dict[str, Dict[str, Dict[str, Formula]]] = {}
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
                a_value REAL DEFAULT 32.0,
                UNIQUE(track, vehicle_class, session_type)
            )
        """)
        
        # Check if a_value column exists, add if not
        cursor.execute("PRAGMA table_info(formulas)")
        columns = [col[1] for col in cursor.fetchall()]
        if 'a_value' not in columns:
            cursor.execute("ALTER TABLE formulas ADD COLUMN a_value REAL DEFAULT 32.0")
        
        conn.commit()
        conn.close()
    
    def _load_formulas(self):
        """Load all formulas from database"""
        self._formulas.clear()
        
        conn = sqlite3.connect(self.db.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT track, vehicle_class, a, b, session_type, confidence, 
                   data_points_used, avg_error, max_error, vehicles_in_class, a_value 
            FROM formulas
        """)
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
                if formula.vehicle_class not in self._formulas[formula.track]:
                    self._formulas[formula.track][formula.vehicle_class] = {}
                self._formulas[formula.track][formula.vehicle_class][formula.session_type] = formula
        
        logger.debug(f"Loaded {self.get_formula_count()} formulas from database")
    
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
            (track, vehicle_class, a, b, session_type, confidence, data_points_used, 
             avg_error, max_error, vehicles_in_class, last_used, a_value)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, ?)
        """, (formula.track, formula.vehicle_class, formula.a, formula.b, 
              formula.session_type, formula.confidence, formula.data_points_used,
              formula.avg_error, formula.max_error, vehicles_str, formula.a))
        conn.commit()
        conn.close()
        
        # Update cache
        if formula.track not in self._formulas:
            self._formulas[formula.track] = {}
        if formula.vehicle_class not in self._formulas[formula.track]:
            self._formulas[formula.track][formula.vehicle_class] = {}
        self._formulas[formula.track][formula.vehicle_class][formula.session_type] = formula
        
        logger.debug(f"Saved formula for {formula.track}/{formula.vehicle_class}/{formula.session_type}: {formula.get_formula_string()}")
        return True
    
    def update_formula_a_value(self, track: str, vehicle_class: str, session_type: str, a_value: float) -> bool:
        """Update the 'a' value for an existing formula"""
        formula = self.get_formula_by_class(track, vehicle_class, session_type)
        if not formula:
            return False
        
        new_formula = Formula(
            track=formula.track,
            vehicle_class=formula.vehicle_class,
            a=a_value,
            b=formula.b,
            session_type=formula.session_type,
            confidence=formula.confidence,
            data_points_used=formula.data_points_used,
            vehicles_in_class=formula.vehicles_in_class
        )
        return self.save_formula(new_formula)


class AutopilotEngine:
    """Autopilot engine that creates/adapts formulas and calculates new ratios"""
    
    def __init__(self, db: CurveDatabase, formula_manager: FormulaManager):
        self.db = db
        self.formula_manager = formula_manager
        self._class_mapping = load_vehicle_classes()
    
    def _backup_aiw_file(self, aiw_path: Path) -> bool:
        """Create a backup of an AIW file before modifying it - ONLY ONCE per file"""
        global _BACKED_UP_AIW_FILES
        
        aiw_key = str(aiw_path.absolute())
        if aiw_key in _BACKED_UP_AIW_FILES:
            return True
        
        try:
            backup_dir = Path(self.db.db_path).parent / "aiw_backups"
            backup_dir.mkdir(parents=True, exist_ok=True)
            
            backup_name = f"{aiw_path.stem}_ORIGINAL{aiw_path.suffix}"
            backup_path = backup_dir / backup_name
            
            if not backup_path.exists():
                shutil.copy2(aiw_path, backup_path)
                logger.debug(f"  Created backup: {backup_path}")
            
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
            SELECT ratio, lap_time 
            FROM data_points 
            WHERE track = ? AND vehicle_class = ? AND session_type = ?
        """, (track, vehicle_class, session_filter))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [(ratio, lap_time) for ratio, lap_time in rows]
    
    def _calculate_midpoint(self, points: List[Tuple[float, float]]) -> Tuple[Optional[float], Optional[float]]:
        """Calculate the midpoint (average) of all points"""
        if not points:
            return None, None
        
        avg_ratio = sum(p[0] for p in points) / len(points)
        avg_time = sum(p[1] for p in points) / len(points)
        
        if len(points) == 1:
            logger.debug(f"  Single data point: R={avg_ratio:.4f}, T={avg_time:.2f}s")
        else:
            logger.debug(f"  Using {len(points)} data points → midpoint: R={avg_ratio:.4f}, T={avg_time:.2f}s")
        
        return avg_ratio, avg_time
    
    def calculate_target_time_from_settings(self, best_ai_time, worst_ai_time, settings):
        """Calculate target AI time based on user's target settings."""
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
        else:
            offset = settings.get("offset_seconds", 0.0)
            target = worst_ai_time - offset
        
        error_margin = settings.get("error_margin", 0.0)
        target = target + error_margin
        
        target = max(best_ai_time, min(worst_ai_time + error_margin, target))
        
        return target
    
    def _get_or_create_formula(self, track: str, vehicle_class: str, session_type: str, 
                                current_ratio: float, target_time: float) -> Formula:
        """
        Get existing formula or create a new one from the data point.
        Uses base a=32 for new formulas.
        """
        # Try to get existing formula
        formula = self.formula_manager.get_formula_by_class(track, vehicle_class, session_type)
        
        if formula:
            old_formula_str = formula.get_formula_string()
            # Adapt the formula to the new point
            adapted = formula.adjust_height_to_point(current_ratio, target_time)
            logger.info(f"Formula for Track {track}, car class {vehicle_class} modified from {old_formula_str} to {adapted.get_formula_string()}")
            return adapted
        else:
            # Create new formula from point with base a=32
            logger.debug(f"  Creating new formula for {track}/{vehicle_class}/{session_type} (base a={DEFAULT_A_VALUE})")
            new_formula = Formula.from_point(track, vehicle_class, current_ratio, target_time, session_type, DEFAULT_A_VALUE)
            return new_formula
    
    def _calculate_new_ratio_from_user_time(self, formula: Formula, user_lap_time: float) -> Optional[float]:
        """
        Calculate what ratio would give the user's lap time using the current formula.
        This is the key method for adjusting AI difficulty to match user performance.
        """
        if user_lap_time <= 0:
            logger.debug(f"  No valid user lap time provided")
            return None
        
        new_ratio = formula.get_ratio_for_time(user_lap_time)
        
        if new_ratio and 0.3 < new_ratio < 3.0:
            logger.debug(f"  Calculated new ratio from user time {user_lap_time:.3f}s: {new_ratio:.6f}")
            return new_ratio
        else:
            logger.debug(f"  Calculated ratio {new_ratio} is out of valid range (0.3-3.0)")
            return None
    
    def _process_session(self, track: str, vehicle_class: str, session_type: str, 
                         current_ratio: float, user_lap_time: float, midpoint_time: float, aiw_path: Path,
                         ratio_name: str, ai_target_settings: Dict = None) -> Dict[str, Any]:
        """
        Process a single session (qualifying or race).
        Now properly calculates target ratio based on USER lap time, not AI midpoint.
        """
        result = {
            "updated": False,
            "old_ratio": current_ratio,
            "new_ratio": None,
            "formula": None
        }
        
        logger.debug(f"\n{'='*50}")
        logger.debug(f"[{session_type.upper()}] Processing {session_type} session")
        logger.debug(f"  Current ratio from AIW: {current_ratio:.6f}")
        logger.debug(f"  User lap time: {user_lap_time:.3f}s" if user_lap_time > 0 else "  User lap time: Not available")
        
        # CRITICAL FIX: If we have user lap time, that's what we should target
        # The goal is to make AI times match the user's performance level
        if user_lap_time > 0:
            # Use user's lap time as the target for formula creation/adaptation
            target_time_for_formula = user_lap_time
            logger.debug(f"  Using USER lap time as target: {target_time_for_formula:.3f}s")
        else:
            # Fallback to AI midpoint if no user time (e.g., first qualifying session)
            target_time_for_formula = midpoint_time
            logger.debug(f"  No user time - using AI midpoint as target: {target_time_for_formula:.3f}s")
        
        # Get or create formula using the target time
        formula = self._get_or_create_formula(track, vehicle_class, session_type, current_ratio, target_time_for_formula)
        logger.debug(f"  Formula: {formula.get_formula_string()}")
        
        # Save the formula
        self.formula_manager.save_formula(formula)
        result["formula"] = formula
        
        # Calculate what ratio would give the user's lap time (or target time)
        # This is the NEW ratio we should write to the AIW
        if user_lap_time > 0:
            # We have user data - calculate ratio that makes AI match user
            new_ratio = self._calculate_new_ratio_from_user_time(formula, user_lap_time)
            logger.debug(f"  Calculated new ratio from user time {user_lap_time:.3f}s: {new_ratio:.6f}" if new_ratio else "  Could not calculate new ratio from user time")
        else:
            # No user data - we can't calculate a meaningful new ratio
            # Keep current ratio, but we've created/updated the formula for future use
            new_ratio = None
            logger.debug(f"  No user time available - cannot calculate new ratio")
        
        # Apply AI target settings if provided and we have AI range data
        if ai_target_settings and new_ratio and new_ratio != current_ratio:
            # Get AI times for this session to apply target positioning
            existing_points = self._get_data_points(track, vehicle_class, session_type)
            if existing_points:
                ai_times = [t for _, t in existing_points]
                best_ai_time = min(ai_times)
                worst_ai_time = max(ai_times)
                
                target_time = self.calculate_target_time_from_settings(
                    best_ai_time, worst_ai_time, ai_target_settings
                )
                
                # Recalculate ratio for the target position
                adjusted_ratio = formula.get_ratio_for_time(target_time)
                if adjusted_ratio and 0.3 < adjusted_ratio < 3.0:
                    logger.debug(f"  Adjusted for AI target (position {ai_target_settings.get('percentage', 50)}%): {adjusted_ratio:.6f}")
                    new_ratio = adjusted_ratio
        
        # Apply the new ratio to the AIW file if we have one and it's different
        if new_ratio and abs(new_ratio - current_ratio) > 0.000001:
            logger.info(f"  Updating {ratio_name} from {current_ratio:.6f} to {new_ratio:.6f}")
            
            if self._update_aiw_ratio(aiw_path, ratio_name, new_ratio):
                result["updated"] = True
                result["new_ratio"] = new_ratio
                logger.debug(f"  Successfully updated {ratio_name} in AIW")
            else:
                logger.error(f"  Failed to update AIW file")
        else:
            if new_ratio:
                logger.debug(f"  New ratio {new_ratio:.6f} is essentially same as current {current_ratio:.6f} - no update needed")
            else:
                logger.debug(f"  No new ratio calculated - keeping current value")
        
        return result
    
    def process_race_data(self, race_data: RaceData, aiw_path: Path, ai_target_settings: Dict = None) -> Dict[str, Any]:
        """Process race data - create/adapt formulas and calculate new ratios"""
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
            "message": ""
        }
        
        if not race_data.track_name:
            result["message"] = "No track name"
            return result
        
        track = race_data.track_name
        user_vehicle = race_data.user_vehicle or "Unknown"
        vehicle_class = get_vehicle_class(user_vehicle, self._class_mapping)
        
        # Determine which sessions have data
        has_qual = race_data.qual_ratio and race_data.qual_best_ai_lap_sec > 0 and race_data.qual_worst_ai_lap_sec > 0
        has_race = race_data.race_ratio and race_data.best_ai_lap_sec > 0 and race_data.worst_ai_lap_sec > 0
        
        session_type_str = ""
        if has_qual and has_race:
            session_type_str = "both"
        elif has_qual:
            session_type_str = "qualifying"
        elif has_race:
            session_type_str = "race"
        else:
            session_type_str = "none"
        
        if session_type_str != "none":
            logger.info(f"New data received for Track {track}, {session_type_str} session, car class {vehicle_class}")
        
        logger.debug(f"\n{'='*70}")
        logger.debug(f"[AUTO] Processing race data")
        logger.debug(f"{'='*70}")
        logger.debug(f"  Track: '{track}'")
        logger.debug(f"  User Vehicle: '{user_vehicle}' -> Class: '{vehicle_class}'")
        logger.debug(f"  User Qualifying Time: {race_data.user_qualifying_sec:.3f}s" if race_data.user_qualifying_sec > 0 else "  User Qualifying Time: Not available")
        logger.debug(f"  User Best Race Time: {race_data.user_best_lap_sec:.3f}s" if race_data.user_best_lap_sec > 0 else "  User Best Race Time: Not available")
        
        # Process qualifying
        if has_qual:
            result["qual_old_ratio"] = race_data.qual_ratio
            qual_midpoint = (race_data.qual_best_ai_lap_sec + race_data.qual_worst_ai_lap_sec) / 2
            
            qual_result = self._process_session(
                track, vehicle_class, "qual",
                race_data.qual_ratio, 
                race_data.user_qualifying_sec,  # Pass user qualifying time
                qual_midpoint, 
                aiw_path, 
                "QualRatio",
                ai_target_settings
            )
            
            result["qual_updated"] = qual_result["updated"]
            result["qual_new_ratio"] = qual_result["new_ratio"]
            result["qual_formula"] = qual_result["formula"]
        
        # Process race
        if has_race:
            result["race_old_ratio"] = race_data.race_ratio
            race_midpoint = (race_data.best_ai_lap_sec + race_data.worst_ai_lap_sec) / 2
            
            race_result = self._process_session(
                track, vehicle_class, "race",
                race_data.race_ratio,
                race_data.user_best_lap_sec,  # Pass user best race time
                race_midpoint,
                aiw_path,
                "RaceRatio",
                ai_target_settings
            )
            
            result["race_updated"] = race_result["updated"]
            result["race_new_ratio"] = race_result["new_ratio"]
            result["race_formula"] = race_result["formula"]
        
        result["success"] = result["qual_updated"] or result["race_updated"]
        
        # Summary - only log details at DEBUG level
        logger.debug(f"\n{'='*70}")
        logger.debug(f"[AUTO] Summary")
        logger.debug(f"{'='*70}")
        if result["qual_updated"]:
            logger.debug(f"  QUALIFYING: {result['qual_old_ratio']:.6f} -> {result['qual_new_ratio']:.6f}")
        else:
            logger.debug(f"  QUALIFYING: No update")
        
        if result["race_updated"]:
            logger.debug(f"  RACE: {result['race_old_ratio']:.6f} -> {result['race_new_ratio']:.6f}")
        else:
            logger.debug(f"  RACE: No update")
        logger.debug(f"{'='*70}\n")
        
        return result
    
    def _update_aiw_ratio(self, aiw_path: Path, ratio_name: str, new_ratio: float) -> bool:
        try:
            if not aiw_path.exists():
                logger.error(f"AIW file not found: {aiw_path}")
                return False
            
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
    
    def calculate_ratio_from_formula(self, track: str, vehicle_class: str, session_type: str, lap_time: float) -> Optional[float]:
        """Calculate ratio from a formula for a given lap time"""
        formula = self.formula_manager.get_formula_by_class(track, vehicle_class, session_type)
        if not formula:
            # Use default formula with base a=32
            b = lap_time - (DEFAULT_A_VALUE / 1.0)  # Rough estimate
            b = max(10.0, min(200.0, b))
            formula = Formula(track, vehicle_class, DEFAULT_A_VALUE, b, session_type)
        
        return formula.get_ratio_for_time(lap_time)


class AutopilotManager:
    def __init__(self, db: CurveDatabase):
        self.db = db
        self.formula_manager = FormulaManager(db)
        self.engine = AutopilotEngine(db, self.formula_manager)
        self.enabled = False
    
    def set_enabled(self, enabled: bool):
        self.enabled = enabled
        logger.debug(f"Autoratio {'ENABLED' if enabled else 'DISABLED'}")
    
    def process_new_data(self, race_data: RaceData, aiw_path: Path, ai_target_settings: Dict = None) -> Dict[str, Any]:
        if not self.enabled:
            return {"success": False, "message": "Autoratio disabled"}
        return self.engine.process_race_data(race_data, aiw_path, ai_target_settings)
    
    def get_status(self) -> Dict[str, Any]:
        return {
            "enabled": self.enabled,
            "formula_count": self.formula_manager.get_formula_count(),
            "tracks_with_formulas": self.formula_manager.get_tracks_with_formulas()
        }
    
    def reload_formulas(self):
        self.formula_manager._load_formulas()
    
    def calculate_ratio(self, track: str, vehicle_class: str, session_type: str, lap_time: float) -> Optional[float]:
        """Calculate ratio for a given lap time using stored formula"""
        return self.engine.calculate_ratio_from_formula(track, vehicle_class, session_type, lap_time)


if __name__ == "__main__":
    from db_funcs import CurveDatabase
    db = CurveDatabase("ai_data.db")
    manager = AutopilotManager(db)
    print(f"Status: {manager.get_status()}")
