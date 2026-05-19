#!/usr/bin/env python3
"""
AI time management for the main window
Handles fetching AI times and updating formulas
"""

import logging
import sqlite3
from typing import List, Tuple, Optional

from core_formula import DEFAULT_A_VALUE
from core_autopilot import Formula

logger = logging.getLogger(__name__)


class AITimeManager:
    """Manages AI time fetching and formula updates"""
    
    def __init__(self, db, autopilot_manager):
        self.db = db
        self.autopilot_manager = autopilot_manager
    
    def get_ai_times_for_track(self, track: str, session_type: str) -> Tuple[Optional[float], Optional[float]]:
        """Get best and worst AI times for a track"""
        conn = sqlite3.connect(self.db.db_path)
        cursor = conn.cursor()
        
        if session_type == "qual":
            cursor.execute("""
                SELECT qual_time_sec FROM ai_results ar
                JOIN race_sessions rs ON ar.race_id = rs.race_id
                WHERE rs.track_name = ? AND ar.qual_time_sec > 0
                ORDER BY ar.qual_time_sec LIMIT 1
            """, (track,))
            best_row = cursor.fetchone()
            cursor.execute("""
                SELECT qual_time_sec FROM ai_results ar
                JOIN race_sessions rs ON ar.race_id = rs.race_id
                WHERE rs.track_name = ? AND ar.qual_time_sec > 0
                ORDER BY ar.qual_time_sec DESC LIMIT 1
            """, (track,))
            worst_row = cursor.fetchone()
        else:
            cursor.execute("""
                SELECT best_lap_sec FROM ai_results ar
                JOIN race_sessions rs ON ar.race_id = rs.race_id
                WHERE rs.track_name = ? AND ar.best_lap_sec > 0
                ORDER BY ar.best_lap_sec LIMIT 1
            """, (track,))
            best_row = cursor.fetchone()
            cursor.execute("""
                SELECT best_lap_sec FROM ai_results ar
                JOIN race_sessions rs ON ar.race_id = rs.race_id
                WHERE rs.track_name = ? AND ar.best_lap_sec > 0
                ORDER BY ar.best_lap_sec DESC LIMIT 1
            """, (track,))
            worst_row = cursor.fetchone()
        
        conn.close()
        best = best_row[0] if best_row else None
        worst = worst_row[0] if worst_row else None
        return best, worst
    
    def fit_b_from_data_points(self, session_type: str, ratio: float, ai_times: List[float]) -> Optional[float]:
        """Calculate b parameter from data points"""
        if not ai_times:
            return None
        b_values = []
        for ai_time in ai_times:
            if ai_time is not None and ai_time > 0:
                b = ai_time - (DEFAULT_A_VALUE / ratio)
                b_values.append(b)
        if not b_values:
            return None
        avg_b = sum(b_values) / len(b_values)
        avg_b = max(10.0, min(200.0, avg_b))
        return avg_b
    
    def update_formula_from_new_data(self, track: str, vehicle_class: str, race_data, session_type: str) -> bool:
        """Update formula from new race data"""
        if not track or not vehicle_class:
            return False
        
        if session_type == "qual":
            current_ratio = race_data.qual_ratio
            best_ai = race_data.qual_best_ai_lap_sec
            worst_ai = race_data.qual_worst_ai_lap_sec
        else:
            current_ratio = race_data.race_ratio
            best_ai = race_data.best_ai_lap_sec
            worst_ai = race_data.worst_ai_lap_sec
        
        if not current_ratio or current_ratio <= 0:
            return False
        
        ai_times = []
        if best_ai and best_ai > 0:
            ai_times.append(best_ai)
        if worst_ai and worst_ai > 0:
            ai_times.append(worst_ai)
        
        for ai in race_data.ai_results:
            if session_type == "qual":
                qual_time = ai.get('qual_time_sec')
                if qual_time is not None and qual_time > 0:
                    ai_times.append(qual_time)
            else:
                best_lap = ai.get('best_lap_sec')
                if best_lap is not None and best_lap > 0:
                    ai_times.append(best_lap)
        
        if not ai_times:
            return False
        
        new_b = self.fit_b_from_data_points(session_type, current_ratio, ai_times)
        if new_b is None:
            return False
        
        formula = Formula(
            track=track,
            vehicle_class=vehicle_class,
            a=DEFAULT_A_VALUE,
            b=new_b,
            session_type=session_type,
            data_points_used=len(ai_times),
            confidence=0.7 if len(ai_times) >= 2 else 0.5
        )
        
        if formula.is_valid():
            self.autopilot_manager.formula_manager.save_formula(formula)
            return new_b
        return False
    
    def update_formulas_from_autopilot(self, track: str, vehicle_class: str, 
                                        qual_b: list, race_b: list) -> Tuple[float, float]:
        """Update formula values from autopilot"""
        qual_formula = self.autopilot_manager.formula_manager.get_formula_by_class(
            track, vehicle_class, "qual")
        if qual_formula and qual_formula.is_valid():
            qual_b[0] = qual_formula.b
        else:
            qual_b[0] = 70.0
        
        race_formula = self.autopilot_manager.formula_manager.get_formula_by_class(
            track, vehicle_class, "race")
        if race_formula and race_formula.is_valid():
            race_b[0] = race_formula.b
        else:
            race_b[0] = 70.0
        
        return qual_b[0], race_b[0]
