"""
Track Formula Management - Global curve with track-specific scaling
"""

import json
import numpy as np
from pathlib import Path
from typing import Dict, Optional, List, Tuple
from scipy.optimize import curve_fit, minimize


class GlobalCurve:
    """
    Global curve that defines the relationship between Ratio and Lap Time
    Formula: T = A * exp(-k * R) + B
    But each track has its own scaling factor (multiplier) that adjusts the curve
    """
    
    def __init__(self):
        self.A = 300.0  # Time range above minimum
        self.k = 3.0    # Decay constant
        self.B = 100.0  # Fastest possible time (asymptote)
        self.track_multipliers: Dict[str, float] = {}  # Track name -> multiplier
        self.fit_error = None
        self.points_by_track: Dict[str, List[Tuple[float, float]]] = {}  # Track -> [(ratio, time)]
    
    def global_func(self, R, A, k, B):
        """Global exponential function"""
        return A * np.exp(-k * R) + B
    
    def predict_time(self, ratio: float, track_name: str) -> Optional[float]:
        """Predict time for a given ratio on a specific track"""
        multiplier = self.track_multipliers.get(track_name, 1.0)
        base_time = self.global_func(ratio, self.A, self.k, self.B)
        return base_time * multiplier
    
    def predict_ratio(self, time: float, track_name: str, tolerance=0.001, max_iter=100) -> Optional[float]:
        """Predict ratio for a given time on a specific track using binary search"""
        multiplier = self.track_multipliers.get(track_name, 1.0)
        
        # Get ratio range
        if track_name not in self.points_by_track or not self.points_by_track[track_name]:
            return None
        
        ratios = [p[0] for p in self.points_by_track[track_name]]
        r_min = min(ratios)
        r_max = max(ratios)
        
        # Scale time to global curve
        global_time = time / multiplier
        
        # Check if global_time is within range
        t_min = self.global_func(r_min, self.A, self.k, self.B)
        t_max = self.global_func(r_max, self.A, self.k, self.B)
        
        if global_time < min(t_min, t_max) or global_time > max(t_min, t_max):
            return None
        
        # Binary search on global curve
        left, right = r_min, r_max
        
        if t_min > t_max:
            for _ in range(max_iter):
                mid = (left + right) / 2
                t_mid = self.global_func(mid, self.A, self.k, self.B)
                if abs(t_mid - global_time) < tolerance:
                    return mid
                if t_mid > global_time:
                    left = mid
                else:
                    right = mid
        else:
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
        # Sort by ratio
        self.points_by_track[track_name].sort(key=lambda x: x[0])
    
    def remove_point(self, track_name: str, index: int):
        """Remove a data point"""
        if track_name in self.points_by_track and 0 <= index < len(self.points_by_track[track_name]):
            del self.points_by_track[track_name][index]
            if not self.points_by_track[track_name]:
                del self.points_by_track[track_name]
    
    def get_points(self, track_name: str) -> List[Tuple[float, float]]:
        """Get all points for a track"""
        return self.points_by_track.get(track_name, [])
    
    def fit_global_curve(self):
        """
        Fit the global curve to all points from all tracks.
        Each track has its own multiplier, but the curve shape is shared.
        """
        # Collect all data points
        all_ratios = []
        all_times = []
        track_indicators = []  # Track index for each point
        track_names_list = list(self.points_by_track.keys())
        
        for track_idx, track_name in enumerate(track_names_list):
            for ratio, time in self.points_by_track[track_name]:
                all_ratios.append(ratio)
                all_times.append(time)
                track_indicators.append(track_idx)
        
        if len(all_ratios) < 3:
            return False, "Need at least 3 points across all tracks"
        
        # Optimization function
        def objective(params):
            A, k, B = params[:3]
            multipliers = params[3:]
            
            total_error = 0
            for i, (R, T) in enumerate(zip(all_ratios, all_times)):
                track_idx = track_indicators[i]
                multiplier = multipliers[track_idx]
                predicted = (A * np.exp(-k * R) + B) * multiplier
                total_error += (predicted - T) ** 2
            
            return total_error
        
        # Initial guesses
        # Global curve parameters
        times = np.array(all_times)
        ratios = np.array(all_ratios)
        
        # Guess asymptotic as 95% of min time
        B_guess = np.min(times) * 0.95
        A_guess = np.max(times) - B_guess
        k_guess = 2.0
        
        initial_params = [A_guess, k_guess, B_guess]
        
        # Initial multipliers (all 1.0)
        for track_name in track_names_list:
            initial_params.append(1.0)
        
        # Bounds
        bounds = [(0.01, 1000), (0.1, 10), (0.01, np.max(times))]
        for _ in track_names_list:
            bounds.append((0.1, 10))  # Multiplier bounds
        
        try:
            result = minimize(objective, initial_params, bounds=bounds, method='L-BFGS-B')
            if result.success:
                self.A, self.k, self.B = result.x[:3]
                for i, track_name in enumerate(track_names_list):
                    self.track_multipliers[track_name] = result.x[3 + i]
                
                # Calculate R²
                predictions = []
                for i, (R, T) in enumerate(zip(all_ratios, all_times)):
                    track_idx = track_indicators[i]
                    multiplier = self.track_multipliers[track_names_list[track_idx]]
                    predicted = (self.A * np.exp(-self.k * R) + self.B) * multiplier
                    predictions.append(predicted)
                
                ss_res = np.sum((np.array(all_times) - np.array(predictions)) ** 2)
                ss_tot = np.sum((np.array(all_times) - np.mean(all_times)) ** 2)
                self.fit_error = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
                
                return True, f"Fit successful! R² = {self.fit_error:.6f}"
            else:
                return False, f"Optimization failed: {result.message}"
        except Exception as e:
            return False, f"Fit error: {str(e)}"
    
    def get_curve_points(self, track_name: str, ratio_min=None, ratio_max=None, num_points=200):
        """Get points for plotting the curve for a specific track"""
        multiplier = self.track_multipliers.get(track_name, 1.0)
        
        if ratio_min is None:
            ratio_min = 0.3
        if ratio_max is None:
            ratio_max = 3.0
        
        ratios = np.linspace(ratio_min, ratio_max, num_points)
        times = [(self.A * np.exp(-self.k * R) + self.B) * multiplier for R in ratios]
        
        return ratios, times
    
    def get_global_curve_points(self, ratio_min=None, ratio_max=None, num_points=200):
        """Get points for plotting the global (unscaled) curve"""
        if ratio_min is None:
            ratio_min = 0.3
        if ratio_max is None:
            ratio_max = 3.0
        
        ratios = np.linspace(ratio_min, ratio_max, num_points)
        times = [self.global_func(R, self.A, self.k, self.B) for R in ratios]
        
        return ratios, times
    
    def get_track_multiplier(self, track_name: str) -> float:
        """Get the multiplier for a track"""
        return self.track_multipliers.get(track_name, 1.0)
    
    def get_formula_string(self, track_name: str = None) -> str:
        """Get a readable formula string"""
        if track_name:
            multiplier = self.track_multipliers.get(track_name, 1.0)
            return f"T = {self.A:.4f} × e^(-{self.k:.4f} × R) × {multiplier:.4f} + {self.B:.4f} × {multiplier:.4f}"
        else:
            return f"Global: T = {self.A:.4f} × e^(-{self.k:.4f} × R) + {self.B:.4f}"
    
    def get_stats(self) -> dict:
        """Get statistics about the model"""
        total_points = sum(len(points) for points in self.points_by_track.values())
        return {
            'total_tracks': len(self.points_by_track),
            'total_points': total_points,
            'global_A': self.A,
            'global_k': self.k,
            'global_B': self.B,
            'r_squared': self.fit_error,
            'track_multipliers': self.track_multipliers
        }
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization"""
        return {
            'A': self.A,
            'k': self.k,
            'B': self.B,
            'track_multipliers': self.track_multipliers,
            'points_by_track': self.points_by_track,
            'fit_error': self.fit_error
        }
    
    @classmethod
    def from_dict(cls, data: dict):
        """Create from dictionary"""
        curve = cls()
        curve.A = data['A']
        curve.k = data['k']
        curve.B = data['B']
        curve.track_multipliers = data['track_multipliers']
        curve.points_by_track = data['points_by_track']
        curve.fit_error = data.get('fit_error')
        return curve


class GlobalFormulaManager:
    """Manages saving and loading the global curve"""
    
    def __init__(self, formulas_dir: str = './global_formula'):
        self.formulas_dir = Path(formulas_dir)
        self.formulas_dir.mkdir(parents=True, exist_ok=True)
        self.global_curve = GlobalCurve()
        self.load_curve()
    
    def get_curve_path(self) -> Path:
        """Get the file path for the global curve"""
        return self.formulas_dir / "global_curve.json"
    
    def save_curve(self) -> bool:
        """Save the global curve to disk"""
        try:
            file_path = self.get_curve_path()
            with open(file_path, 'w') as f:
                json.dump(self.global_curve.to_dict(), f, indent=2)
            return True
        except Exception as e:
            print(f"Error saving curve: {e}")
            return False
    
    def load_curve(self) -> bool:
        """Load the global curve from disk"""
        file_path = self.get_curve_path()
        if not file_path.exists():
            return False
        
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
            self.global_curve = GlobalCurve.from_dict(data)
            return True
        except Exception as e:
            print(f"Error loading curve: {e}")
            return False
    
    def add_point(self, track_name: str, ratio: float, time: float):
        """Add a data point and save"""
        self.global_curve.add_point(track_name, ratio, time)
        self.save_curve()
    
    def remove_point(self, track_name: str, index: int):
        """Remove a data point and save"""
        self.global_curve.remove_point(track_name, index)
        self.save_curve()
    
    def fit_curve(self):
        """Fit the global curve and save"""
        success, message = self.global_curve.fit_global_curve()
        if success:
            self.save_curve()
        return success, message
    
    def get_track_multiplier(self, track_name: str) -> float:
        """Get multiplier for a track"""
        return self.global_curve.get_track_multiplier(track_name)
    
    def get_track_points(self, track_name: str) -> List[Tuple[float, float]]:
        """Get points for a specific track"""
        return self.global_curve.get_points(track_name)
    
    def get_all_tracks(self) -> List[str]:
        """Get all track names that have data"""
        return list(self.global_curve.points_by_track.keys())
    
    def get_stats(self) -> dict:
        """Get statistics"""
        return self.global_curve.get_stats()
