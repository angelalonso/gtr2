#!/usr/bin/env python3
"""
Autopilot module for Live AI Tuner
Automatically adjusts AIW ratios based on detected race data and existing formulas

Core principle: Use the same fit_curve function as the manual "Auto-fit" button
- Fits hyperbolic curve T = a/R + b to ALL available data points
- When multiple lap times exist for the same ratio, use the average (midpoint)
- The more data points we have, the more accurate the curve becomes
"""

import logging
import re
import sqlite3
from pathlib import Path
from typing import Optional, Dict, List, Tuple, Any
from dataclasses import dataclass
from datetime import datetime
from collections import defaultdict

from formula_funcs import fit_curve, hyperbolic, get_formula_string
from db_funcs import CurveDatabase
from data_extraction import RaceData

logger = logging.getLogger(__name__)


@dataclass
class Formula:
    """Represents a stored formula for a track and vehicle"""
    track: str
    vehicle: str
    a: float
    b: float
    session_type: str = "both"
    created_at: str = ""
    last_used: str = ""
    confidence: float = 1.0
    data_points_used: int = 0
    avg_error: float = 0.0
    max_error: float = 0.0
    
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
        """Check if formula is valid (a > 0, b > 0, b < typical lap time)"""
        return self.a > 0 and self.b > 0 and self.b < 300
    
    def get_formula_string(self) -> str:
        return f"T = {self.a:.4f} / R + {self.b:.4f}"


class FormulaManager:
    """Manages formulas for tracks and vehicles"""
    
    def __init__(self, db: CurveDatabase):
        self.db = db
        self._formulas: Dict[str, Dict[str, Formula]] = {}
        self._load_formulas()
    
    def _migrate_formulas_table(self, cursor):
        """Add missing columns to formulas table if needed"""
        cursor.execute("PRAGMA table_info(formulas)")
        existing_columns = [row[1] for row in cursor.fetchall()]
        
        for col in ['data_points_used', 'confidence', 'avg_error', 'max_error']:
            if col not in existing_columns:
                print(f"  [FormulaManager] Adding {col} column")
                cursor.execute(f"ALTER TABLE formulas ADD COLUMN {col} DEFAULT 0")
    
    def _load_formulas(self):
        """Load all formulas from database"""
        self._formulas.clear()
        
        conn = sqlite3.connect(self.db.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS formulas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                track TEXT NOT NULL,
                vehicle TEXT NOT NULL,
                a REAL NOT NULL,
                b REAL NOT NULL,
                session_type TEXT NOT NULL,
                confidence REAL DEFAULT 1.0,
                data_points_used INTEGER DEFAULT 0,
                avg_error REAL DEFAULT 0.0,
                max_error REAL DEFAULT 0.0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                last_used TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(track, vehicle, session_type)
            )
        """)
        
        self._migrate_formulas_table(cursor)
        conn.commit()
        
        cursor.execute("SELECT track, vehicle, a, b, session_type, confidence, data_points_used, avg_error, max_error FROM formulas")
        rows = cursor.fetchall()
        conn.close()
        
        print(f"\n[FormulaManager] Loading formulas from database...")
        print(f"  Found {len(rows)} formula records")
        
        if len(rows) == 0:
            print(f"  No formulas found in database")
        else:
            for row in rows:
                formula = Formula(
                    track=row[0], vehicle=row[1], a=row[2], b=row[3],
                    session_type=row[4], confidence=row[5], data_points_used=row[6],
                    avg_error=row[7], max_error=row[8]
                )
                if formula.is_valid():
                    key = f"{formula.vehicle}_{formula.session_type}"
                    if formula.track not in self._formulas:
                        self._formulas[formula.track] = {}
                    self._formulas[formula.track][key] = formula
                    print(f"  ✓ Loaded: [{formula.track}] [{formula.vehicle}] ({formula.session_type}): {formula.get_formula_string()} (points={formula.data_points_used}, error={formula.avg_error:.3f}s)")
                else:
                    print(f"  ✗ Skipped invalid: [{formula.track}] [{formula.vehicle}] ({formula.session_type}): a={formula.a:.2f}, b={formula.b:.2f}")
        
        # Print summary by track
        print(f"\n[FormulaManager] Summary by track:")
        for track in self._formulas:
            print(f"  Track: {track}")
            for key, formula in self._formulas[track].items():
                print(f"    - {formula.vehicle} ({formula.session_type}): {formula.get_formula_string()}")
        
        print(f"\n[FormulaManager] Total valid formulas loaded: {self.get_formula_count()}")
    
    def get_formula(self, track: str, vehicle: str, session_type: str) -> Optional[Formula]:
        """Get formula - tries exact match first, then case-insensitive"""
        key = f"{vehicle}_{session_type}"
        track_dict = self._formulas.get(track, {})
        
        # Try exact match
        formula = track_dict.get(key)
        if formula:
            print(f"  [FormulaManager] Found exact match: {track}/{vehicle} ({session_type})")
            return formula
        
        # Try case-insensitive match
        for existing_key, existing_formula in track_dict.items():
            if existing_key.lower() == key.lower():
                print(f"  [FormulaManager] Found case-insensitive match: {track}/{existing_formula.vehicle} ({session_type}) -> using for {vehicle}")
                return existing_formula
        
        print(f"  [FormulaManager] No formula found for {track}/{vehicle} ({session_type})")
        print(f"  Available formulas for this track: {list(track_dict.keys())}")
        return None
    
    def get_all_formulas_for_track(self, track: str) -> List[Formula]:
        return list(self._formulas.get(track, {}).values())
    
    def get_all_formulas(self) -> List[Formula]:
        formulas = []
        for track_dict in self._formulas.values():
            formulas.extend(track_dict.values())
        return formulas
    
    def get_formula_count(self) -> int:
        return sum(len(track_dict) for track_dict in self._formulas.values())
    
    def get_tracks_with_formulas(self) -> List[str]:
        return [track for track, formulas in self._formulas.items() if formulas]
    
    def save_formula(self, formula: Formula) -> bool:
        if not formula.is_valid():
            print(f"  [FormulaManager] WARNING: Not saving invalid formula: a={formula.a:.2f}, b={formula.b:.2f}")
            return False
        
        print(f"  [FormulaManager] Saving formula for [{formula.track}] [{formula.vehicle}] ({formula.session_type})")
        print(f"    a={formula.a:.6f}, b={formula.b:.6f}")
        print(f"    points={formula.data_points_used}, avg_error={formula.avg_error:.3f}s")
        
        conn = sqlite3.connect(self.db.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO formulas 
            (track, vehicle, a, b, session_type, confidence, data_points_used, avg_error, max_error, last_used)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, (formula.track, formula.vehicle, formula.a, formula.b, 
              formula.session_type, formula.confidence, formula.data_points_used,
              formula.avg_error, formula.max_error))
        conn.commit()
        conn.close()
        
        # Update cache
        key = f"{formula.vehicle}_{formula.session_type}"
        if formula.track not in self._formulas:
            self._formulas[formula.track] = {}
        self._formulas[formula.track][key] = formula
        
        print(f"  [FormulaManager] Formula saved successfully")
        return True


class AutopilotEngine:
    """Autopilot engine that aggregates points by ratio before fitting"""
    
    def __init__(self, db: CurveDatabase, formula_manager: FormulaManager):
        self.db = db
        self.formula_manager = formula_manager
        self.silent_mode = False
    
    def _aggregate_points_by_ratio(self, points: List[Tuple[float, float]]) -> List[Tuple[float, float]]:
        """
        Aggregate points by ratio, using average lap time for each unique ratio.
        This prevents fitting issues when multiple lap times exist for the same ratio.
        """
        if not points:
            return []
        
        # Group by ratio (rounded to 6 decimal places for consistency)
        ratio_groups = defaultdict(list)
        for ratio, lap_time in points:
            ratio_groups[ratio].append(lap_time)
        
        # Calculate average for each ratio
        aggregated = []
        for ratio, lap_times in ratio_groups.items():
            avg_lap_time = sum(lap_times) / len(lap_times)
            aggregated.append((ratio, avg_lap_time))
            if len(lap_times) > 1:
                print(f"    Aggregated {len(lap_times)} points at R={ratio:.6f}: avg T={avg_lap_time:.3f}s (range: {min(lap_times):.3f}-{max(lap_times):.3f}s)")
        
        # Sort by ratio
        aggregated.sort(key=lambda x: x[0])
        return aggregated
    
    def _get_all_data_points(self, track: str, vehicle: str, session_type: str) -> List[Tuple[float, float]]:
        """Get all data points for a track/vehicle/session from the database"""
        print(f"    Querying database for existing points (track='{track}', vehicle='{vehicle}', session='{session_type}')...")
        points = self.db.get_data_points(
            [track], [vehicle],
            session_type == "qual",
            session_type == "race",
            False
        )
        print(f"    Found {len(points)} raw points in database")
        
        # Show raw points
        for i, (r, t, st) in enumerate(points):
            print(f"      Raw point {i+1}: R={r:.6f}, T={t:.3f} ({st})")
        
        # Convert to simple list of (ratio, lap_time)
        simple_points = [(p[0], p[1]) for p in points]
        
        # Aggregate by ratio
        aggregated = self._aggregate_points_by_ratio(simple_points)
        print(f"    After aggregation: {len(aggregated)} unique ratios")
        
        return aggregated
    
    def _calculate_simple_formula(self, ratio: float, lap_time: float) -> Tuple[float, float]:
        """
        Calculate a simple formula from a single data point.
        Uses default slope of 30, adjusts b to hit the point.
        """
        default_a = 30.0
        b = lap_time - (default_a / ratio)
        b = max(10.0, min(200.0, b))
        return default_a, b
    
    def process_race_data(self, race_data: RaceData, aiw_path: Path) -> Dict[str, Any]:
        """
        Process race data - aggregate points by ratio, then use fit_curve
        """
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
        vehicle = race_data.user_vehicle or "Unknown"
        
        print(f"\n{'='*70}")
        print(f"🤖 AUTOPILOT - Processing race data")
        print(f"{'='*70}")
        print(f"  Track: '{track}'")
        print(f"  Vehicle: '{vehicle}'")
        print(f"  AIW path: {aiw_path}")
        
        # Process qualifying
        if race_data.qual_ratio and race_data.qual_best_ai_lap_sec > 0 and race_data.qual_worst_ai_lap_sec > 0:
            result["qual_old_ratio"] = race_data.qual_ratio
            qual_midpoint = (race_data.qual_best_ai_lap_sec + race_data.qual_worst_ai_lap_sec) / 2
            
            print(f"\n{'─'*50}")
            print(f"📊 QUALIFYING Session")
            print(f"  Current ratio in AIW: {race_data.qual_ratio:.6f}")
            print(f"  Best AI time: {race_data.qual_best_ai_lap_sec:.3f}s")
            print(f"  Worst AI time: {race_data.qual_worst_ai_lap_sec:.3f}s")
            print(f"  Target lap time (midpoint): {qual_midpoint:.3f}s")
            print(f"  New data point: (R={race_data.qual_ratio:.6f}, T={qual_midpoint:.3f})")
            
            # Get ALL existing points from database (already aggregated)
            all_points = self._get_all_data_points(track, vehicle, "qual")
            
            # Add the new point
            all_points.append((race_data.qual_ratio, qual_midpoint))
            print(f"  Total points before aggregation: {len(all_points)}")
            
            # Aggregate again to handle any duplicates with the new point
            all_points = self._aggregate_points_by_ratio(all_points)
            print(f"  Total unique ratios after aggregation: {len(all_points)}")
            
            if len(all_points) >= 2:
                print(f"\n  >>> Fitting curve with {len(all_points)} unique ratio points...")
                ratios = [p[0] for p in all_points]
                times = [p[1] for p in all_points]
                
                # Show the points being fitted
                print(f"  Points for fitting:")
                for i, (r, t) in enumerate(zip(ratios, times)):
                    print(f"    {i+1}: R={r:.6f}, T={t:.3f}")
                
                # Call fit_curve
                a, b, avg_error, max_error = fit_curve(ratios, times, verbose=True)
                
                if a is not None and b is not None and a > 0 and b > 0:
                    print(f"\n  ✓ fit_curve SUCCEEDED for QUALIFYING")
                    print(f"    a={a:.6f}, b={b:.6f}")
                    print(f"    Formula: {get_formula_string(a, b)}")
                    
                    formula = Formula(
                        track=track, vehicle=vehicle, a=a, b=b,
                        session_type="qual",
                        confidence=min(1.0, len(all_points) / 10.0),
                        data_points_used=len(all_points),
                        avg_error=avg_error,
                        max_error=max_error
                    )
                    self.formula_manager.save_formula(formula)
                    result["qual_formula"] = formula
                    
                    new_ratio = formula.get_ratio_for_time(qual_midpoint)
                    print(f"  Target lap time: {qual_midpoint:.3f}s")
                    print(f"  Calculated new ratio: {new_ratio:.6f}")
                    
                    if new_ratio is not None and 0.3 < new_ratio < 3.0:
                        if self._update_aiw_ratio(aiw_path, "QualRatio", new_ratio):
                            result["qual_updated"] = True
                            result["qual_new_ratio"] = new_ratio
                            result["method"] = "fit_curve_aggregated"
                            print(f"\n  ✅ QualRatio UPDATED in AIW: {race_data.qual_ratio:.6f} → {new_ratio:.6f}")
                        else:
                            print(f"\n  ❌ Failed to update AIW file")
                    else:
                        print(f"\n  ❌ Invalid ratio: {new_ratio} (outside 0.3-3.0 range)")
                else:
                    print(f"\n  ❌ fit_curve FAILED for QUALIFYING (invalid a={a}, b={b})")
                    # Fallback to simple formula
                    print(f"  Falling back to simple formula...")
                    a, b = self._calculate_simple_formula(race_data.qual_ratio, qual_midpoint)
                    formula = Formula(
                        track=track, vehicle=vehicle, a=a, b=b,
                        session_type="qual",
                        confidence=0.3,
                        data_points_used=len(all_points),
                        avg_error=0,
                        max_error=0
                    )
                    self.formula_manager.save_formula(formula)
                    new_ratio = formula.get_ratio_for_time(qual_midpoint)
                    if new_ratio and 0.3 < new_ratio < 3.0:
                        if self._update_aiw_ratio(aiw_path, "QualRatio", new_ratio):
                            result["qual_updated"] = True
                            result["qual_new_ratio"] = new_ratio
                            result["method"] = "simple_formula_fallback"
                            print(f"\n  ✅ QualRatio UPDATED using fallback: {new_ratio:.6f}")
            else:
                print(f"\n  ⚠ Need at least 2 unique ratios to fit (have {len(all_points)})")
                # With only 1 unique ratio, use simple formula
                a, b = self._calculate_simple_formula(race_data.qual_ratio, qual_midpoint)
                formula = Formula(
                    track=track, vehicle=vehicle, a=a, b=b,
                    session_type="qual",
                    confidence=0.2,
                    data_points_used=1,
                    avg_error=0,
                    max_error=0
                )
                self.formula_manager.save_formula(formula)
                new_ratio = formula.get_ratio_for_time(qual_midpoint)
                if new_ratio and 0.3 < new_ratio < 3.0:
                    if self._update_aiw_ratio(aiw_path, "QualRatio", new_ratio):
                        result["qual_updated"] = True
                        result["qual_new_ratio"] = new_ratio
                        result["method"] = "single_point_formula"
                        print(f"\n  ✅ QualRatio UPDATED (single point): {new_ratio:.6f}")
        
        # Process race
        if race_data.race_ratio and race_data.best_ai_lap_sec > 0 and race_data.worst_ai_lap_sec > 0:
            result["race_old_ratio"] = race_data.race_ratio
            race_midpoint = (race_data.best_ai_lap_sec + race_data.worst_ai_lap_sec) / 2
            
            print(f"\n{'─'*50}")
            print(f"🏁 RACE Session")
            print(f"  Current ratio in AIW: {race_data.race_ratio:.6f}")
            print(f"  Best AI time: {race_data.best_ai_lap_sec:.3f}s")
            print(f"  Worst AI time: {race_data.worst_ai_lap_sec:.3f}s")
            print(f"  Target lap time (midpoint): {race_midpoint:.3f}s")
            print(f"  New data point: (R={race_data.race_ratio:.6f}, T={race_midpoint:.3f})")
            
            # Get ALL existing points from database (already aggregated)
            all_points = self._get_all_data_points(track, vehicle, "race")
            
            # Add the new point
            all_points.append((race_data.race_ratio, race_midpoint))
            print(f"  Total points before aggregation: {len(all_points)}")
            
            # Aggregate again to handle any duplicates with the new point
            all_points = self._aggregate_points_by_ratio(all_points)
            print(f"  Total unique ratios after aggregation: {len(all_points)}")
            
            if len(all_points) >= 2:
                print(f"\n  >>> Fitting curve with {len(all_points)} unique ratio points...")
                ratios = [p[0] for p in all_points]
                times = [p[1] for p in all_points]
                
                # Show the points being fitted
                print(f"  Points for fitting:")
                for i, (r, t) in enumerate(zip(ratios, times)):
                    print(f"    {i+1}: R={r:.6f}, T={t:.3f}")
                
                # Call fit_curve
                a, b, avg_error, max_error = fit_curve(ratios, times, verbose=True)
                
                if a is not None and b is not None and a > 0 and b > 0:
                    print(f"\n  ✓ fit_curve SUCCEEDED for RACE")
                    print(f"    a={a:.6f}, b={b:.6f}")
                    print(f"    Formula: {get_formula_string(a, b)}")
                    
                    formula = Formula(
                        track=track, vehicle=vehicle, a=a, b=b,
                        session_type="race",
                        confidence=min(1.0, len(all_points) / 10.0),
                        data_points_used=len(all_points),
                        avg_error=avg_error,
                        max_error=max_error
                    )
                    self.formula_manager.save_formula(formula)
                    result["race_formula"] = formula
                    
                    new_ratio = formula.get_ratio_for_time(race_midpoint)
                    print(f"  Target lap time: {race_midpoint:.3f}s")
                    print(f"  Calculated new ratio: {new_ratio:.6f}")
                    
                    if new_ratio is not None and 0.3 < new_ratio < 3.0:
                        if self._update_aiw_ratio(aiw_path, "RaceRatio", new_ratio):
                            result["race_updated"] = True
                            result["race_new_ratio"] = new_ratio
                            result["method"] = "fit_curve_aggregated"
                            print(f"\n  ✅ RaceRatio UPDATED in AIW: {race_data.race_ratio:.6f} → {new_ratio:.6f}")
                        else:
                            print(f"\n  ❌ Failed to update AIW file")
                    else:
                        print(f"\n  ❌ Invalid ratio: {new_ratio} (outside 0.3-3.0 range)")
                else:
                    print(f"\n  ❌ fit_curve FAILED for RACE (invalid a={a}, b={b})")
                    # Fallback to simple formula
                    print(f"  Falling back to simple formula...")
                    a, b = self._calculate_simple_formula(race_data.race_ratio, race_midpoint)
                    formula = Formula(
                        track=track, vehicle=vehicle, a=a, b=b,
                        session_type="race",
                        confidence=0.3,
                        data_points_used=len(all_points),
                        avg_error=0,
                        max_error=0
                    )
                    self.formula_manager.save_formula(formula)
                    new_ratio = formula.get_ratio_for_time(race_midpoint)
                    if new_ratio and 0.3 < new_ratio < 3.0:
                        if self._update_aiw_ratio(aiw_path, "RaceRatio", new_ratio):
                            result["race_updated"] = True
                            result["race_new_ratio"] = new_ratio
                            result["method"] = "simple_formula_fallback"
                            print(f"\n  ✅ RaceRatio UPDATED using fallback: {new_ratio:.6f}")
            else:
                print(f"\n  ⚠ Need at least 2 unique ratios to fit (have {len(all_points)})")
                a, b = self._calculate_simple_formula(race_data.race_ratio, race_midpoint)
                formula = Formula(
                    track=track, vehicle=vehicle, a=a, b=b,
                    session_type="race",
                    confidence=0.2,
                    data_points_used=1,
                    avg_error=0,
                    max_error=0
                )
                self.formula_manager.save_formula(formula)
                new_ratio = formula.get_ratio_for_time(race_midpoint)
                if new_ratio and 0.3 < new_ratio < 3.0:
                    if self._update_aiw_ratio(aiw_path, "RaceRatio", new_ratio):
                        result["race_updated"] = True
                        result["race_new_ratio"] = new_ratio
                        result["method"] = "single_point_formula"
                        print(f"\n  ✅ RaceRatio UPDATED (single point): {new_ratio:.6f}")
        
        result["success"] = result["qual_updated"] or result["race_updated"]
        
        print(f"\n{'='*70}")
        if result["success"]:
            print(f"✅ AUTOPILOT COMPLETE")
            if result["qual_updated"]:
                print(f"  🟡 Qualifying: {result['qual_old_ratio']:.6f} → {result['qual_new_ratio']:.6f} ({result['method']})")
            if result["race_updated"]:
                print(f"  🟠 Race: {result['race_old_ratio']:.6f} → {result['race_new_ratio']:.6f} ({result['method']})")
        else:
            print(f"⚠ AUTOPILOT - No updates performed")
            if result["message"]:
                print(f"  Reason: {result['message']}")
        print(f"{'='*70}\n")
        
        return result
    
    def _update_aiw_ratio(self, aiw_path: Path, ratio_name: str, new_ratio: float) -> bool:
        """Update a ratio in the AIW file"""
        try:
            if not aiw_path.exists():
                print(f"    ✗ AIW file not found: {aiw_path}")
                return False
            
            print(f"    Reading AIW file: {aiw_path}")
            raw = aiw_path.read_bytes()
            content = raw.replace(b"\x00", b"").decode("utf-8", errors="ignore")
            
            # Update ratio
            pattern = rf'({re.escape(ratio_name)}\s*=\s*\(?)\s*[0-9.eE+-]+\s*(\)?)'
            new_content, count = re.subn(
                pattern,
                lambda m: f"{m.group(1)}{new_ratio:.6f}{m.group(2)}",
                content,
                flags=re.IGNORECASE
            )
            
            if count > 0:
                aiw_path.write_bytes(new_content.encode("utf-8", errors="ignore"))
                print(f"    ✓ Updated {ratio_name} to {new_ratio:.6f}")
                return True
            else:
                print(f"    ⚠ Could not find {ratio_name} pattern in AIW file")
                return False
                
        except Exception as e:
            print(f"    ✗ Failed to update {ratio_name}: {e}")
            return False


class AutopilotManager:
    """Main manager for autopilot functionality"""
    
    def __init__(self, db: CurveDatabase):
        self.db = db
        self.formula_manager = FormulaManager(db)
        self.engine = AutopilotEngine(db, self.formula_manager)
        self.enabled = False
        self.silent = False
    
    def set_enabled(self, enabled: bool):
        self.enabled = enabled
        if enabled:
            print("\n🤖 AUTOPILOT ENABLED - Aggregating points by ratio before fitting")
        else:
            print("\n🤖 AUTOPILOT DISABLED")
    
    def set_silent(self, silent: bool):
        self.silent = silent
        self.engine.silent_mode = silent
    
    def process_new_data(self, race_data: RaceData, aiw_path: Path) -> Dict[str, Any]:
        if not self.enabled:
            print("\n🤖 Autopilot is disabled - skipping")
            return {"success": False, "message": "Autopilot disabled"}
        if not race_data or not race_data.has_data():
            print("\n🤖 No valid race data - skipping")
            return {"success": False, "message": "No valid race data"}
        if not aiw_path or not aiw_path.exists():
            print(f"\n🤖 AIW file not found: {aiw_path}")
            return {"success": False, "message": f"AIW file not found: {aiw_path}"}
        
        return self.engine.process_race_data(race_data, aiw_path)
    
    def get_status(self) -> Dict[str, Any]:
        return {
            "enabled": self.enabled,
            "silent": self.silent,
            "formula_count": self.formula_manager.get_formula_count(),
            "tracks_with_formulas": self.formula_manager.get_tracks_with_formulas()
        }
    
    def reload_formulas(self):
        print("\n🤖 Reloading formulas from database...")
        self.formula_manager._load_formulas()


if __name__ == "__main__":
    from db_funcs import CurveDatabase
    db = CurveDatabase("ai_data.db")
    manager = AutopilotManager(db)
    manager.set_enabled(True)
    print(f"Status: {manager.get_status()}")
