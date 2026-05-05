#!/usr/bin/env python3
"""
Autopilot module for Live AI Tuner
Automatically adjusts AIW ratios based on detected race data
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

from core_formula import hyperbolic, get_formula_string, DEFAULT_A_VALUE
from core_database import CurveDatabase
from core_data_extraction import RaceData
from core_config import get_base_path
from core_aiw_utils import find_aiw_file_from_path, find_aiw_file_by_track, update_aiw_ratio, ensure_aiw_has_ratios

logger = logging.getLogger(__name__)

VEHICLE_CLASSES_FILE = Path(__file__).parent / "vehicle_classes.json"
_BACKED_UP_AIW_FILES: Set[str] = set()


def load_vehicle_classes() -> Dict[str, Dict]:
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
    def __init__(self, db: CurveDatabase):
        self.db = db
        self._formulas: Dict[str, Dict[str, Dict[str, Formula]]] = {}
        self._class_mapping = load_vehicle_classes()
        self._init_database()
        self._load_formulas()
    
    def _init_database(self):
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
        
        cursor.execute("PRAGMA table_info(formulas)")
        columns = [col[1] for col in cursor.fetchall()]
        if 'a_value' not in columns:
            cursor.execute("ALTER TABLE formulas ADD COLUMN a_value REAL DEFAULT 32.0")
        
        conn.commit()
        conn.close()
    
    def _load_formulas(self):
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
        
        if formula.track not in self._formulas:
            self._formulas[formula.track] = {}
        if formula.vehicle_class not in self._formulas[formula.track]:
            self._formulas[formula.track][formula.vehicle_class] = {}
        self._formulas[formula.track][formula.vehicle_class][formula.session_type] = formula
        
        logger.debug(f"Saved formula for {formula.track}/{formula.vehicle_class}/{formula.session_type}: {formula.get_formula_string()}")
        return True
    
    def update_formula_a_value(self, track: str, vehicle_class: str, session_type: str, a_value: float) -> bool:
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
    def __init__(self, db: CurveDatabase, formula_manager: FormulaManager):
        self.db = db
        self.formula_manager = formula_manager
        self._class_mapping = load_vehicle_classes()
    
    def _backup_aiw_file(self, aiw_path: Path) -> bool:
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
    
    def calculate_target_time_from_settings(self, best_ai_time, worst_ai_time, settings):
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
        formula = self.formula_manager.get_formula_by_class(track, vehicle_class, session_type)
        if formula:
            old_formula_str = formula.get_formula_string()
            adapted = formula.adjust_height_to_point(current_ratio, target_time)
            logger.info(f"Formula for Track {track}, car class {vehicle_class} modified from {old_formula_str} to {adapted.get_formula_string()}")
            return adapted
        else:
            logger.debug(f"  Creating new formula for {track}/{vehicle_class}/{session_type} (base a={DEFAULT_A_VALUE})")
            new_formula = Formula.from_point(track, vehicle_class, current_ratio, target_time, session_type, DEFAULT_A_VALUE)
            return new_formula
    
    def _calculate_new_ratio_direct(self, user_lap_time: float, a: float, b: float) -> Optional[float]:
        if user_lap_time <= 0:
            logger.debug(f"  No valid user lap time provided")
            return None
        
        denominator = user_lap_time - b
        if denominator <= 0:
            logger.debug(f"  Denominator <= 0: {user_lap_time:.3f} - {b:.2f} = {denominator:.3f}")
            return None
        
        new_ratio = a / denominator
        
        if 0.3 < new_ratio < 3.0:
            logger.debug(f"  DIRECT calculation: R = {a:.2f} / ({user_lap_time:.3f} - {b:.2f}) = {new_ratio:.6f}")
            return new_ratio
        else:
            logger.debug(f"  Calculated ratio {new_ratio} is out of valid range (0.3-3.0)")
            return None
    
    def _find_aiw_file_for_track(self, track_name: str, base_path: Path) -> Optional[Path]:
        return find_aiw_file_by_track(track_name, base_path)
    
    def _update_aiw_ratio(self, aiw_path: Path, ratio_name: str, new_ratio: float) -> bool:
        backup_dir = Path(self.db.db_path).parent / "aiw_backups"
        return update_aiw_ratio(aiw_path, ratio_name, new_ratio, backup_dir)
    
    def _process_session(self, track: str, vehicle_class: str, session_type: str, 
                         current_ratio: float, user_lap_time: float, midpoint_time: float, 
                         aiw_path: Path, ratio_name: str, ai_target_settings: Dict = None,
                         race_data_aiw_path: Path = None) -> Dict[str, Any]:
        
        result = {"updated": False, "old_ratio": current_ratio, "new_ratio": None, "formula": None, "message": ""}
        
        logger.debug(f"\n{'='*50}")
        logger.debug(f"[{session_type.upper()}] Processing {session_type} session")
        logger.debug(f"  Current ratio from AIW: {current_ratio:.6f}")
        logger.debug(f"  User lap time: {user_lap_time:.3f}s" if user_lap_time > 0 else "  User lap time: Not available")
        
        actual_aiw_path = None
        
        if race_data_aiw_path and race_data_aiw_path.exists():
            actual_aiw_path = race_data_aiw_path
            logger.info(f"  Using AIW path from race_data: {actual_aiw_path}")
        elif aiw_path and aiw_path.exists():
            actual_aiw_path = aiw_path
            logger.info(f"  Using AIW path from config: {actual_aiw_path}")
        else:
            base_path = get_base_path()
            if base_path:
                actual_aiw_path = self._find_aiw_file_for_track(track, base_path)
                if actual_aiw_path:
                    logger.info(f"  Found AIW via track search: {actual_aiw_path}")
        
        if actual_aiw_path:
            logger.info(f"AIW path resolution for {session_type}: using {actual_aiw_path}")
        else:
            logger.error(f"AIW path resolution for {session_type}: FAILED - no path found")
            result["message"] = f"AIW file not found for track: {track}"
            return result
        
        if not actual_aiw_path or not actual_aiw_path.exists():
            logger.error(f"  Cannot find AIW file for track: {track}")
            result["message"] = f"AIW file not found for track: {track}"
            return result
        
        backup_dir = Path(self.db.db_path).parent / "aiw_backups"
        ensure_aiw_has_ratios(actual_aiw_path, backup_dir)
        
        existing_formula = self.formula_manager.get_formula_by_class(track, vehicle_class, session_type)
        
        if existing_formula and existing_formula.is_valid():
            a = existing_formula.a
            b = existing_formula.b
            logger.debug(f"  Using existing formula: a={a:.2f}, b={b:.2f}")
            result["formula"] = existing_formula
        else:
            a = DEFAULT_A_VALUE
            if current_ratio > 0 and user_lap_time > 0:
                b = user_lap_time - (a / current_ratio)
                b = max(10.0, min(200.0, b))
                logger.debug(f"  No formula found, estimating b from current data: b={b:.2f}")
            else:
                b = 70.0
                logger.debug(f"  No formula found, using default b={b:.2f}")
        
        new_ratio = None
        if user_lap_time > 0:
            denominator = user_lap_time - b
            if denominator > 0:
                new_ratio = a / denominator
                logger.debug(f"  DIRECT new ratio: {new_ratio:.6f} (T={user_lap_time:.3f}, b={b:.2f})")
            else:
                logger.debug(f"  Cannot calculate ratio: denominator <= 0: {user_lap_time:.3f} - {b:.2f} = {denominator:.3f}")
        
        if ai_target_settings and new_ratio and new_ratio != current_ratio:
            existing_points = self._get_data_points(track, vehicle_class, session_type)
            if existing_points:
                ai_times = [t for _, t in existing_points]
                best_ai_time = min(ai_times)
                worst_ai_time = max(ai_times)
                
                target_time = self.calculate_target_time_from_settings(best_ai_time, worst_ai_time, ai_target_settings)
                denominator = target_time - b
                if denominator > 0:
                    adjusted_ratio = a / denominator
                    if 0.3 < adjusted_ratio < 3.0:
                        logger.debug(f"  Adjusted for AI target (position {ai_target_settings.get('percentage', 50)}%): {adjusted_ratio:.6f}")
                        new_ratio = adjusted_ratio
        
        if new_ratio and abs(new_ratio - current_ratio) > 0.000001:
            logger.info(f"  Updating {ratio_name} from {current_ratio:.6f} to {new_ratio:.6f}")
            if self._update_aiw_ratio(actual_aiw_path, ratio_name, new_ratio):
                result["updated"] = True
                result["new_ratio"] = new_ratio
                logger.info(f"  Successfully updated {ratio_name} in AIW")
            else:
                logger.error(f"  Failed to update AIW file")
                result["message"] = f"Failed to update {ratio_name} in AIW file"
        
        if user_lap_time > 0:
            target_time_for_formula = user_lap_time
            if existing_formula:
                updated_formula = existing_formula.adjust_height_to_point(current_ratio, target_time_for_formula)
                self.formula_manager.save_formula(updated_formula)
                logger.debug(f"  Updated formula with new data point")
                result["formula"] = updated_formula
            else:
                new_formula = Formula.from_point(track, vehicle_class, current_ratio, target_time_for_formula, session_type, a)
                self.formula_manager.save_formula(new_formula)
                logger.debug(f"  Created new formula from data point")
                result["formula"] = new_formula
        
        return result
    
    def process_race_data(self, race_data: RaceData, aiw_path: Path, ai_target_settings: Dict = None) -> Dict[str, Any]:
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
        
        race_aiw_path = race_data.aiw_path if hasattr(race_data, 'aiw_path') and race_data.aiw_path else None
        if race_aiw_path and race_aiw_path.exists():
            logger.info(f"  Using AIW path from race_data: {race_aiw_path}")
        
        has_qual = (race_data.qual_ratio is not None and race_data.qual_ratio > 0 and 
                    race_data.qual_best_ai_lap_sec > 0 and race_data.qual_worst_ai_lap_sec > 0)
        has_race = (race_data.race_ratio is not None and race_data.race_ratio > 0 and 
                    race_data.best_ai_lap_sec > 0 and race_data.worst_ai_lap_sec > 0)
        
        session_type_str = ""
        if has_qual and has_race:
            session_type_str = "both"
        elif has_qual:
            session_type_str = "qualifying"
        elif has_race:
            session_type_str = "race"
        
        if session_type_str != "none":
            logger.info(f"New data received for Track {track}, {session_type_str} session, car class {vehicle_class}")
        
        logger.debug(f"\n{'='*70}")
        logger.debug(f"[AUTO] Processing race data")
        logger.debug(f"{'='*70}")
        logger.debug(f"  Track: '{track}'")
        logger.debug(f"  User Vehicle: '{user_vehicle}' -> Class: '{vehicle_class}'")
        
        if has_qual:
            result["qual_old_ratio"] = race_data.qual_ratio
            qual_result = self._process_session(
                track, vehicle_class, "qual",
                race_data.qual_ratio, race_data.user_qualifying_sec,
                (race_data.qual_best_ai_lap_sec + race_data.qual_worst_ai_lap_sec) / 2,
                aiw_path, "QualRatio", ai_target_settings, race_aiw_path
            )
            result["qual_updated"] = qual_result["updated"]
            result["qual_new_ratio"] = qual_result["new_ratio"]
            result["qual_formula"] = qual_result["formula"]
        
        if has_race:
            result["race_old_ratio"] = race_data.race_ratio
            race_result = self._process_session(
                track, vehicle_class, "race",
                race_data.race_ratio, race_data.user_best_lap_sec,
                (race_data.best_ai_lap_sec + race_data.worst_ai_lap_sec) / 2,
                aiw_path, "RaceRatio", ai_target_settings, race_aiw_path
            )
            result["race_updated"] = race_result["updated"]
            result["race_new_ratio"] = race_result["new_ratio"]
            result["race_formula"] = race_result["formula"]
        
        result["success"] = result["qual_updated"] or result["race_updated"]
        
        logger.debug(f"\n{'='*70}")
        logger.debug(f"[AUTO] Summary")
        logger.debug(f"{'='*70}")
        if result["qual_updated"]:
            logger.debug(f"  QUALIFYING: {result['qual_old_ratio']:.6f} -> {result['qual_new_ratio']:.6f}")
        if result["race_updated"]:
            logger.debug(f"  RACE: {result['race_old_ratio']:.6f} -> {result['race_new_ratio']:.6f}")
        logger.debug(f"{'='*70}\n")
        
        return result
    
    def calculate_ratio_from_formula(self, track: str, vehicle_class: str, session_type: str, lap_time: float) -> Optional[float]:
        formula = self.formula_manager.get_formula_by_class(track, vehicle_class, session_type)
        if not formula:
            b = lap_time - (DEFAULT_A_VALUE / 1.0)
            b = max(10.0, min(200.0, b))
            formula = Formula(track, vehicle_class, DEFAULT_A_VALUE, b, session_type)
        
        denominator = lap_time - formula.b
        if denominator <= 0:
            return None
        return formula.a / denominator


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
        return self.engine.calculate_ratio_from_formula(track, vehicle_class, session_type, lap_time)
