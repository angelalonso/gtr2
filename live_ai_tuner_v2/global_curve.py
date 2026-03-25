"""
Global Curve Model - Exponential curve fitting for ratio vs lap time relationship
Formula: T = A * exp(-k * R) + B
"""

import json
import numpy as np
from pathlib import Path
from typing import Optional, List, Tuple, Dict
from scipy.optimize import minimize
import logging

logger = logging.getLogger(__name__)


class GlobalCurve:
    """
    Global curve that defines the relationship between Ratio and Lap Time
    Each track can have its own scaling multiplier
    """
    
    def __init__(self):
        self.A = 300.0      # Time range above minimum
        self.k = 3.0        # Decay constant
        self.B = 100.0      # Fastest possible time (asymptote)
        self.track_multipliers: Dict[str, float] = {}
        self.points_by_track: Dict[str, List[Tuple[float, float]]] = {}
        self.r_squared = None
    
    def global_func(self, R: float, A: float, k: float, B: float) -> float:
        """Global exponential function"""
        return A * np.exp(-k * R) + B
    
    def predict_time(self, ratio: float, track_name: str) -> Optional[float]:
        """Predict time for a given ratio on a specific track"""
        multiplier = self.track_multipliers.get(track_name, 1.0)
        base_time = self.global_func(ratio, self.A, self.k, self.B)
        return base_time * multiplier
    
    def predict_ratio(self, time: float, track_name: str, 
                      tolerance: float = 0.001, max_iter: int = 100) -> Optional[float]:
        """
        Predict ratio for a given time on a specific track using binary search
        """
        multiplier = self.track_multipliers.get(track_name, 1.0)
        global_time = time / multiplier
        
        # Determine search range from track data or defaults
        if track_name in self.points_by_track and self.points_by_track[track_name]:
            ratios = [p[0] for p in self.points_by_track[track_name]]
            r_min = min(ratios)
            r_max = max(ratios)
        else:
            r_min = 0.3
            r_max = 3.0
        
        # Check if time is within range
        t_min = self.global_func(r_min, self.A, self.k, self.B)
        t_max = self.global_func(r_max, self.A, self.k, self.B)
        
        if global_time < min(t_min, t_max) or global_time > max(t_min, t_max):
            logger.debug(f"Time {global_time:.2f}s outside range [{min(t_min,t_max):.2f}, {max(t_min,t_max):.2f}]")
            return None
        
        # Binary search
        left, right = r_min, r_max
        
        if t_min > t_max:  # Decreasing function
            for _ in range(max_iter):
                mid = (left + right) / 2
                t_mid = self.global_func(mid, self.A, self.k, self.B)
                if abs(t_mid - global_time) < tolerance:
                    return mid
                if t_mid > global_time:
                    left = mid
                else:
                    right = mid
        else:  # Increasing function
            for _ in range(max_iter):
                mid = (left + right) / 2
                t_mid = self.global_func(mid, self.A, self.k, self.B)
                if abs(t_mid - global_time) < tolerance:
                    return mid
                if t_mid < global_time:
                    left = mid
                else:
                    right = mid
        
        return (left + right) / 2
    
    def add_point(self, track_name: str, ratio: float, time: float):
        """Add a data point for a track"""
        if track_name not in self.points_by_track:
            self.points_by_track[track_name] = []
        self.points_by_track[track_name].append((ratio, time))
        self.points_by_track[track_name].sort(key=lambda x: x[0])
    
    def fit_curve(self) -> Tuple[bool, str]:
        """
        Fit the global curve to all points from all tracks
        Each track has its own multiplier
        """
        # Collect all points
        all_ratios = []
        all_times = []
        track_indices = []
        track_names = list(self.points_by_track.keys())
        
        for track_idx, track_name in enumerate(track_names):
            for ratio, time in self.points_by_track[track_name]:
                all_ratios.append(ratio)
                all_times.append(time)
                track_indices.append(track_idx)
        
        if len(all_ratios) < 3:
            return False, f"Need at least 3 points (have {len(all_ratios)})"
        
        def objective(params):
            A, k, B = params[:3]
            multipliers = params[3:]
            total_error = 0
            for i, (R, T) in enumerate(zip(all_ratios, all_times)):
                track_idx = track_indices[i]
                multiplier = multipliers[track_idx]
                predicted = (A * np.exp(-k * R) + B) * multiplier
                total_error += (predicted - T) ** 2
            return total_error
        
        # Initial guesses
        times = np.array(all_times)
        B_guess = np.min(times) * 0.95
        A_guess = np.max(times) - B_guess
        k_guess = 2.0
        
        initial_params = [A_guess, k_guess, B_guess]
        for _ in track_names:
            initial_params.append(1.0)
        
        bounds = [(10, 1000), (0.1, 10), (30, 200)]
        for _ in track_names:
            bounds.append((0.1, 10))
        
        try:
            result = minimize(objective, initial_params, bounds=bounds, method='L-BFGS-B')
            if result.success:
                self.A, self.k, self.B = result.x[:3]
                for i, name in enumerate(track_names):
                    self.track_multipliers[name] = result.x[3 + i]
                
                # Calculate R²
                predictions = []
                for i, (R, T) in enumerate(zip(all_ratios, all_times)):
                    track_idx = track_indices[i]
                    multiplier = self.track_multipliers[track_names[track_idx]]
                    predicted = (self.A * np.exp(-self.k * R) + self.B) * multiplier
                    predictions.append(predicted)
                
                ss_res = np.sum((np.array(all_times) - np.array(predictions)) ** 2)
                ss_tot = np.sum((np.array(all_times) - np.mean(all_times)) ** 2)
                self.r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
                
                return True, f"Fit successful! R² = {self.r_squared:.6f}"
            else:
                return False, f"Optimization failed: {result.message}"
        except Exception as e:
            return False, f"Error: {str(e)}"
    
    def get_stats(self) -> dict:
        """Get statistics about the model"""
        total_points = sum(len(points) for points in self.points_by_track.values())
        return {
            'total_tracks': len(self.points_by_track),
            'total_points': total_points,
            'A': self.A,
            'k': self.k,
            'B': self.B,
            'r_squared': self.r_squared,
            'track_multipliers': self.track_multipliers
        }
    
    def get_track_multiplier(self, track_name: str) -> float:
        """Get multiplier for a track"""
        return self.track_multipliers.get(track_name, 1.0)
    
    def get_formula_string(self) -> str:
        """Get formula as string"""
        return f"T = {self.A:.2f} × e^(-{self.k:.4f} × R) + {self.B:.2f}"
    
    def to_dict(self) -> dict:
        """Convert to dictionary for saving"""
        return {
            'A': self.A,
            'k': self.k,
            'B': self.B,
            'track_multipliers': self.track_multipliers,
            'points_by_track': self.points_by_track,
            'r_squared': self.r_squared
        }
    
    @classmethod
    def from_dict(cls, data: dict):
        """Create from dictionary"""
        curve = cls()
        curve.A = data.get('A', 300.0)
        curve.k = data.get('k', 3.0)
        curve.B = data.get('B', 100.0)
        curve.track_multipliers = data.get('track_multipliers', {})
        curve.points_by_track = data.get('points_by_track', {})
        curve.r_squared = data.get('r_squared')
        return curve


class GlobalCurveManager:
    """Manages loading and saving of the global curve"""
    
    def __init__(self, formulas_dir: str = './track_formulas'):
        self.formulas_dir = Path(formulas_dir)
        self.formulas_dir.mkdir(parents=True, exist_ok=True)
        self.curve = GlobalCurve()
        self.load()
    
    def get_curve_path(self) -> Path:
        """Get path to saved curve file"""
        return self.formulas_dir / 'global_curve.json'
    
    def load(self) -> bool:
        """Load curve from disk"""
        path = self.get_curve_path()
        if not path.exists():
            return False
        
        try:
            with open(path, 'r') as f:
                data = json.load(f)
            self.curve = GlobalCurve.from_dict(data)
            logger.info(f"Loaded global curve with {self.curve.get_stats()['total_points']} points")
            return True
        except Exception as e:
            logger.error(f"Error loading curve: {e}")
            return False
    
    def save(self) -> bool:
        """Save curve to disk"""
        try:
            with open(self.get_curve_path(), 'w') as f:
                json.dump(self.curve.to_dict(), f, indent=2)
            logger.info("Saved global curve")
            return True
        except Exception as e:
            logger.error(f"Error saving curve: {e}")
            return False
    
    def add_point(self, track_name: str, ratio: float, time: float) -> bool:
        """Add a point and save"""
        self.curve.add_point(track_name, ratio, time)
        return self.save()
    
    def fit_curve(self) -> Tuple[bool, str]:
        """Fit curve and save if successful"""
        success, message = self.curve.fit_curve()
        if success:
            self.save()
        return success, message
    
    def predict_ratio(self, time: float, track_name: str) -> Optional[float]:
        """Predict ratio for given time on a track"""
        return self.curve.predict_ratio(time, track_name)
    
    def predict_time(self, ratio: float, track_name: str) -> Optional[float]:
        """Predict time for given ratio on a track"""
        return self.curve.predict_time(ratio, track_name)
    
    def get_stats(self) -> dict:
        """Get curve statistics"""
        return self.curve.get_stats()
    
    def get_track_multiplier(self, track_name: str) -> float:
        """Get track multiplier"""
        return self.curve.get_track_multiplier(track_name)
