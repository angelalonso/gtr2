#!/usr/bin/env python3
"""
Autopilot module - lightweight version
"""

import logging
import re
import shutil
import json
from pathlib import Path
from typing import Optional, Dict, List, Tuple, Set, Any
from dataclasses import dataclass

from .database import DatabaseManager
from .formula import DEFAULT_A, ratio_from_time, hyperbolic

logger = logging.getLogger(__name__)

VEHICLE_CLASSES_FILE = Path(__file__).parent.parent / "vehicle_classes.json"
_BACKED_UP_AIW_FILES: Set[str] = set()


def load_vehicle_classes() -> Dict[str, Dict]:
    """Load vehicle class mappings"""
    default = {
        "Formula Cars": {"vehicles": ["Formula Senior", "Formula Junior", "Formula 3", "F4"]},
        "GT Cars": {"vehicles": ["Porsche 911", "Ferrari 550", "GT", "GTE", "GT3"]},
        "Prototype Cars": {"vehicles": ["LMP1", "LMP2", "Audi R8"]},
        "Production Cars": {"vehicles": ["BMW M3", "Audi R8 LMS"]}
    }
    
    if not VEHICLE_CLASSES_FILE.exists():
        with open(VEHICLE_CLASSES_FILE, 'w') as f:
            json.dump(default, f, indent=2)
        return default
    
    try:
        with open(VEHICLE_CLASSES_FILE, 'r') as f:
            return json.load(f)
    except Exception:
        return default


def get_vehicle_class(vehicle_name: str, mapping: Dict) -> str:
    """Get class for vehicle"""
    if not vehicle_name:
        return "Unknown"
    
    vehicle_lower = vehicle_name.lower().strip()
    
    for class_name, class_data in mapping.items():
        for v in class_data.get("vehicles", []):
            if v.lower() == vehicle_lower:
                return class_name
    
    for class_name, class_data in mapping.items():
        for v in class_data.get("vehicles", []):
            if v.lower() in vehicle_lower or vehicle_lower in v.lower():
                return class_name
    
    return vehicle_name


@dataclass
class Formula:
    track: str
    vehicle_class: str
    a: float
    b: float
    session_type: str
    data_points_used: int = 0
    
    def get_time(self, ratio: float) -> float:
        return hyperbolic(ratio, self.a, self.b)
    
    def get_ratio(self, lap_time: float) -> Optional[float]:
        return ratio_from_time(lap_time, self.a, self.b)
    
    def is_valid(self) -> bool:
        return self.a > 0 and self.b > 10 and self.b < 200


class FormulaManager:
    """Manage formulas with minimal overhead"""
    
    def __init__(self, db: DatabaseManager):
        self.db = db
        self._cache: Dict[str, Formula] = {}
        self._class_mapping = load_vehicle_classes()
    
    def _make_key(self, track: str, vehicle_class: str, session_type: str) -> str:
        return f"{track}|{vehicle_class}|{session_type}".lower()
    
    def get_formula(self, track: str, vehicle_name: str, session_type: str) -> Optional[Formula]:
        vehicle_class = get_vehicle_class(vehicle_name, self._class_mapping)
        return self.get_formula_by_class(track, vehicle_class, session_type)
    
    def get_formula_by_class(self, track: str, vehicle_class: str, session_type: str) -> Optional[Formula]:
        key = self._make_key(track, vehicle_class, session_type)
        
        if key in self._cache:
            return self._cache[key]
        
        result = self.db.get_formula(track, vehicle_class, session_type)
        if result:
            a, b = result
            formula = Formula(track, vehicle_class, a, b, session_type)
            self._cache[key] = formula
            return formula
        
        return None
    
    def save_formula(self, formula: Formula) -> bool:
        if not formula.is_valid():
            return False
        
        key = self._make_key(formula.track, formula.vehicle_class, formula.session_type)
        self._cache[key] = formula
        return self.db.save_formula(formula.track, formula.vehicle_class, 
                                    formula.session_type, formula.a, formula.b,
                                    formula.data_points_used)
    
    def reload(self):
        self._cache.clear()


class AutopilotEngine:
    """Lightweight autopilot engine"""
    
    def __init__(self, db: DatabaseManager, formula_manager: FormulaManager):
        self.db = db
        self.formula_manager = formula_manager
    
    def _backup_aiw_file(self, aiw_path: Path) -> bool:
        """Backup AIW file once per session"""
        global _BACKED_UP_AIW_FILES
        
        key = str(aiw_path.absolute())
        if key in _BACKED_UP_AIW_FILES:
            return True
        
        try:
            backup_dir = Path(self.db.db_path).parent / "aiw_backups"
            backup_dir.mkdir(parents=True, exist_ok=True)
            
            backup_path = backup_dir / f"{aiw_path.stem}_ORIGINAL{aiw_path.suffix}"
            if not backup_path.exists():
                shutil.copy2(aiw_path, backup_path)
            
            _BACKED_UP_AIW_FILES.add(key)
            return True
        except Exception:
            return False
    
    def _update_aiw_ratio(self, aiw_path: Path, ratio_name: str, new_ratio: float) -> bool:
        """Update ratio in AIW file"""
        try:
            if not aiw_path.exists():
                return False
            
            self._backup_aiw_file(aiw_path)
            
            raw = aiw_path.read_bytes()
            content = raw.replace(b"\x00", b"").decode("utf-8", errors="ignore")
            
            pattern = rf'({re.escape(ratio_name)}\s*=\s*\(?)\s*[0-9.eE+-]+\s*(\)?)'
            new_content, count = re.subn(pattern, 
                lambda m: f"{m.group(1)}{new_ratio:.6f}{m.group(2)}", 
                content, flags=re.IGNORECASE)
            
            if count > 0:
                aiw_path.write_bytes(new_content.encode("utf-8", errors="ignore"))
                return True
            return False
        except Exception:
            return False
    
    def calculate_ratio(self, lap_time: float, formula: Formula) -> Optional[float]:
        """Calculate ratio from lap time using formula"""
        if not formula or not formula.is_valid():
            return None
        return formula.get_ratio(lap_time)


class AutopilotManager:
    """Main autopilot manager"""
    
    def __init__(self, db: DatabaseManager):
        self.db = db
        self.formula_manager = FormulaManager(db)
        self.engine = AutopilotEngine(db, self.formula_manager)
        self.enabled = False
    
    def set_enabled(self, enabled: bool):
        self.enabled = enabled
    
    def process_new_data(self, race_data, aiw_path: Path) -> Dict[str, Any]:
        """Process new race data"""
        if not self.enabled:
            return {"success": False, "message": "Autopilot disabled"}
        
        result = {"qual_updated": False, "race_updated": False}
        
        # Process qualifying
        if race_data.qual_ratio and race_data.user_qualifying_sec > 0:
            vehicle_class = get_vehicle_class(race_data.user_vehicle or "Unknown", 
                                             load_vehicle_classes())
            formula = self.formula_manager.get_formula_by_class(
                race_data.track_name, vehicle_class, "qual")
            
            if formula and formula.is_valid():
                new_ratio = self.engine.calculate_ratio(race_data.user_qualifying_sec, formula)
                if new_ratio and abs(new_ratio - race_data.qual_ratio) > 0.00001:
                    if self.engine._update_aiw_ratio(aiw_path, "QualRatio", new_ratio):
                        result["qual_updated"] = True
        
        # Process race
        if race_data.race_ratio and race_data.user_best_lap_sec > 0:
            vehicle_class = get_vehicle_class(race_data.user_vehicle or "Unknown",
                                             load_vehicle_classes())
            formula = self.formula_manager.get_formula_by_class(
                race_data.track_name, vehicle_class, "race")
            
            if formula and formula.is_valid():
                new_ratio = self.engine.calculate_ratio(race_data.user_best_lap_sec, formula)
                if new_ratio and abs(new_ratio - race_data.race_ratio) > 0.00001:
                    if self.engine._update_aiw_ratio(aiw_path, "RaceRatio", new_ratio):
                        result["race_updated"] = True
        
        result["success"] = result["qual_updated"] or result["race_updated"]
        return result
    
    def get_status(self) -> Dict[str, Any]:
        return {"enabled": self.enabled}
    
    def reload_formulas(self):
        self.formula_manager.reload()
