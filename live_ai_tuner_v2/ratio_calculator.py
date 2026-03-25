"""
Ratio Calculator - Helper functions for ratio calculations
"""

import logging
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


class RatioCalculator:
    """
    Ratio calculation helper - can be extended for different calculation methods
    """
    
    def __init__(self):
        self.calculation_method = "global_curve"  # Future: can be configurable
    
    def calculate_ratio(self, user_time: float, best_ai_time: float, 
                        worst_ai_time: float, current_ratio: float = 1.0) -> float:
        """
        Calculate optimal ratio based on lap times
        
        Simple formula: Ratio = (user_time / target_time) * current_ratio
        where target_time is the desired AI time
        """
        # Target AI time - we want AI to be around user time
        target_time = user_time
        
        # If we have AI times, use average
        if best_ai_time and worst_ai_time:
            avg_ai_time = (best_ai_time + worst_ai_time) / 2
            if avg_ai_time > 0:
                # Ratio adjustment factor
                factor = target_time / avg_ai_time
                return current_ratio * factor
        
        # Fallback: simple adjustment
        if best_ai_time and best_ai_time > 0:
            factor = user_time / best_ai_time
            return current_ratio * factor
        
        return current_ratio
    
    def format_time(self, seconds: float) -> str:
        """Format seconds as mm:ss.ms"""
        minutes = int(seconds) // 60
        secs = int(seconds) % 60
        ms = int((seconds - int(seconds)) * 1000)
        return f"{minutes}:{secs:02d}.{ms:03d}"
    
    def parse_time(self, time_str: str) -> Optional[float]:
        """Parse time string to seconds"""
        try:
            time_str = time_str.strip()
            if ':' in time_str:
                parts = time_str.split(':')
                minutes = int(parts[0])
                seconds = float(parts[1])
                return minutes * 60 + seconds
            else:
                return float(time_str)
        except (ValueError, IndexError):
            return None
