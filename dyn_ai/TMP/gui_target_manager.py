#!/usr/bin/env python3
"""
Target management for AI tuning
"""

from typing import Dict, Optional


class TargetManager:
    """Manages AI target calculations"""
    
    def __init__(self, settings: Dict):
        self.settings = settings
    
    def calculate_target_lap_time(self, best_ai: float, worst_ai: float) -> float:
        """Calculate target lap time based on settings"""
        mode = self.settings.get("mode", "percentage")
        error_margin = self.settings.get("error_margin", 0.0)
        
        if mode == "percentage":
            pct = self.settings.get("percentage", 50) / 100.0
            target = best_ai + (worst_ai - best_ai) * pct
        elif mode == "faster_than_best":
            offset = self.settings.get("offset_seconds", 0.0)
            target = best_ai + offset
        else:
            offset = self.settings.get("offset_seconds", 0.0)
            target = worst_ai - offset
        
        if error_margin > 0:
            target = target + error_margin
        
        target = max(best_ai, min(worst_ai + error_margin, target))
        
        return target


class RatioCalculator:
    """Calculates ratios based on user times and formulas"""
    
    def __init__(self, qual_b: float, race_b: float):
        self.qual_b = qual_b
        self.race_b = race_b
        self.a = 32.0  # DEFAULT_A_VALUE
    
    def calculate_ratio_from_user_time(self, session_type: str, user_time: float) -> Optional[float]:
        """Calculate ratio from user lap time"""
        if session_type == "qual":
            b = self.qual_b
        else:
            b = self.race_b
        
        denominator = user_time - b
        
        if denominator <= 0:
            return None
        
        ratio = self.a / denominator
        return ratio
    
    def update_formula_b(self, session_type: str, b: float):
        """Update the b parameter for a session type"""
        if session_type == "qual":
            self.qual_b = b
        else:
            self.race_b = b
