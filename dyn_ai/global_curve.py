"""
Global Curve Model - Hyperbolic relationship between Ratio and Lap Time
OPTIMIZED: Added caching, lazy numpy loading, reduced calculations
"""

import json
import numpy as np
from pathlib import Path
from typing import Optional, List, Tuple, Dict
from scipy.optimize import curve_fit
import logging

logger = logging.getLogger(__name__)


class GlobalCurve:
    """
    Hyperbolic curve model: T = a / R + b
    OPTIMIZED: Cached predictions and lazy numpy imports
    """
    
    DEFAULT_K = 0.297
    K_STD = 0.056
    
    def __init__(self):
        self.track_params: Dict[str, Dict[str, float]] = {}
        self.points_by_track: Dict[str, List[Tuple[float, float]]] = {}
        self.fit_error = None
        self.global_k = self.DEFAULT_K
        
        # Cache for predictions
        self._prediction_cache: Dict[str, Dict[float, float]] = {}  # track_name -> {time: ratio}
        self._max_cache_size = 100  # Limit cache size per track
        
    def midpoint(self, ratio: float, a: float, b: float) -> float:
        """Hyperbolic function: T = a / R + b"""
        return a / ratio + b
    
    def ratio_from_time(self, time: float, a: float, b: float) -> Optional[float]:
        """Inverse hyperbolic: R = a / (T - b)"""
        denominator = time - b
        if denominator <= 0:
            return None
        return a / denominator
    
    def predict_ratio(self, time: float, track_name: str) -> Optional[float]:
        """
        Predict ratio for a given lap time on a specific track
        OPTIMIZED: Uses cache for repeated calculations
        """
        # Check cache first
        cache_key = round(time, 3)  # Round to 3 decimals for cache
        if track_name in self._prediction_cache:
            cached = self._prediction_cache[track_name].get(cache_key)
            if cached is not None:
                logger.debug(f"Cache hit for {track_name} at time {time:.3f}")
                return cached
        
        logger.info(f"Predicting ratio for {track_name}: time={time:.3f}s")
        
        result = None
        
        # Try fitted parameters first
        params = self.track_params.get(track_name)
        if params:
            logger.info(f"Using fitted parameters for {track_name}: a={params['a']:.3f}, b={params['b']:.3f}")
            result = self.ratio_from_time(time, params['a'], params['b'])
            if result:
                logger.info(f"Predicted ratio from fit: {result:.6f}")
            else:
                logger.warning(f"Time {time:.3f}s is below floor b={params['b']:.3f}s")
        
        # Bootstrap from available points if no fit or fit failed
        if result is None:
            points = self.points_by_track.get(track_name, [])
            logger.info(f"Bootstrap mode for {track_name}: {len(points)} points available")
            
            if len(points) == 1:
                result = self._bootstrap_one_point(time, track_name, points[0])
            elif len(points) >= 2:
                result = self._bootstrap_two_points(time, points)
            else:
                result = self._bootstrap_no_data(time, track_name)
            
            if result:
                logger.info(f"Predicted ratio from bootstrap: {result:.6f}")
        
        # Store in cache if valid
        if result is not None:
            if track_name not in self._prediction_cache:
                self._prediction_cache[track_name] = {}
            
            # Limit cache size
            cache = self._prediction_cache[track_name]
            if len(cache) >= self._max_cache_size:
                # Remove oldest entry (simple FIFO)
                oldest_key = next(iter(cache))
                del cache[oldest_key]
            
            cache[cache_key] = result
        
        return result
    
    def _bootstrap_one_point(self, time: float, track_name: str, point: Tuple[float, float]) -> Optional[float]:
        """Bootstrap from a single data point using global k prior"""
        ratio0, mid0 = point
        M = mid0 / (self.global_k / ratio0 + 1 - self.global_k)
        a = self.global_k * M
        b = (1 - self.global_k) * M
        return self.ratio_from_time(time, a, b)
    
    def _bootstrap_two_points(self, time: float, points: List[Tuple[float, float]]) -> Optional[float]:
        """Solve exactly for a and b from two data points"""
        if len(points) < 2:
            return None
        
        points_sorted = sorted(points, key=lambda x: x[0])
        r1, m1 = points_sorted[0]
        r2, m2 = points_sorted[1]
        
        try:
            inv_r1 = 1.0 / r1
            inv_r2 = 1.0 / r2
            
            denominator = inv_r1 - inv_r2
            if abs(denominator) < 1e-9:
                return self._bootstrap_one_point(time, "", points_sorted[0])
            
            a = (m1 - m2) / denominator
            b = m1 - a * inv_r1
            
            if b <= 0 or b >= m1:
                return self._bootstrap_one_point(time, "", points_sorted[0])
            
            return self.ratio_from_time(time, a, b)
        except Exception as e:
            logger.error(f"Error in two-point bootstrap: {e}")
            return self._bootstrap_one_point(time, "", points_sorted[0])
    
    def _bootstrap_no_data(self, time: float, track_name: str) -> Optional[float]:
        """No data for this track yet - use global defaults"""
        if self.points_by_track:
            first_track = next(iter(self.track_params.keys())) if self.track_params else None
            if first_track and first_track in self.track_params:
                params = self.track_params[first_track]
                M = params['a'] + params['b']
                a = self.global_k * M
                b = (1 - self.global_k) * M
                return self.ratio_from_time(time, a, b)
        
        logger.warning(f"No data for track {track_name}, using fallback ratio=1.0")
        return 1.0
    
    def add_point(self, track_name: str, ratio: float, best_time: float, worst_time: float = None):
        """Add a data point for a track"""
        if worst_time is not None:
            midpoint = (best_time + worst_time) / 2
        else:
            midpoint = best_time
        
        if track_name not in self.points_by_track:
            self.points_by_track[track_name] = []
        self.points_by_track[track_name].append((ratio, midpoint))
        self.points_by_track[track_name].sort(key=lambda x: x[0])
        
        # Clear cache for this track since data changed
        if track_name in self._prediction_cache:
            del self._prediction_cache[track_name]
        
        self._update_track_params(track_name)
    
    def _update_track_params(self, track_name: str):
        """Update fitted parameters for a track based on available points"""
        points = self.points_by_track.get(track_name, [])
        n_points = len(points)
        
        if n_points == 0:
            return
        elif n_points == 1:
            ratio0, mid0 = points[0]
            M = mid0 / (self.global_k / ratio0 + 1 - self.global_k)
            self.track_params[track_name] = {
                'a': self.global_k * M,
                'b': (1 - self.global_k) * M
            }
        elif n_points == 2:
            self._fit_two_points(track_name, points)
        else:
            self._fit_multiple_points(track_name, points)
    
    def _fit_two_points(self, track_name: str, points: List[Tuple[float, float]]):
        """Fit two points exactly"""
        try:
            r1, m1 = points[0]
            r2, m2 = points[1]
            inv_r1 = 1.0 / r1
            inv_r2 = 1.0 / r2
            
            denominator = inv_r1 - inv_r2
            if abs(denominator) < 1e-9:
                raise ValueError("Points too close")
            
            a = (m1 - m2) / denominator
            b = m1 - a * inv_r1
            
            if b <= 0 or b >= m1:
                raise ValueError("Invalid parameters")
            
            self.track_params[track_name] = {'a': a, 'b': b}
        except Exception as e:
            logger.warning(f"Two-point fit failed for {track_name}: {e}, using bootstrap")
            ratio0, mid0 = points[0]
            M = mid0 / (self.global_k / ratio0 + 1 - self.global_k)
            self.track_params[track_name] = {
                'a': self.global_k * M,
                'b': (1 - self.global_k) * M
            }
    
    def _fit_multiple_points(self, track_name: str, points: List[Tuple[float, float]]):
        """Least squares fit for 3+ points - optimized"""
        ratios = np.array([p[0] for p in points])
        times = np.array([p[1] for p in points])
        
        def hyperbolic_func(R, a, b):
            return a / R + b
        
        try:
            # Use first two points for initial guess
            r1, m1 = points[0]
            r2, m2 = points[1]
            inv_r1 = 1.0 / r1
            inv_r2 = 1.0 / r2
            
            denominator = inv_r1 - inv_r2
            if abs(denominator) < 1e-9:
                a_guess = 30.0
                b_guess = 70.0
            else:
                a_guess = (m1 - m2) / denominator
                b_guess = m1 - a_guess * inv_r1
                
                if b_guess <= 0 or b_guess >= m1:
                    a_guess = 30.0
                    b_guess = 70.0
            
            bounds = ([0.1, 30], [500, 200])
            popt, _ = curve_fit(hyperbolic_func, ratios, times, p0=[a_guess, b_guess], bounds=bounds, maxfev=500)
            a, b = popt
            
            if b <= 0 or b >= np.min(times):
                raise ValueError("Invalid fit parameters")
            
            self.track_params[track_name] = {'a': a, 'b': b}
            logger.info(f"Fitted {track_name}: a={a:.3f}, b={b:.3f}")
            
        except Exception as e:
            logger.error(f"Error fitting track {track_name}: {e}, using bootstrap")
            ratio0, mid0 = points[0]
            M = mid0 / (self.global_k / ratio0 + 1 - self.global_k)
            self.track_params[track_name] = {
                'a': self.global_k * M,
                'b': (1 - self.global_k) * M
            }
    
    def fit_global_k(self):
        """Fit the global k parameter from all tracks' a and b values"""
        k_values = []
        for track_name, params in self.track_params.items():
            M = params['a'] + params['b']
            if M > 0:
                k = params['a'] / M
                k_values.append(k)
        
        if k_values:
            self.global_k = np.mean(k_values)
            self.K_STD = np.std(k_values)
            logger.info(f"Updated global k = {self.global_k:.4f} ± {self.K_STD:.4f} from {len(k_values)} tracks")
            return True
        return False
    
    def get_track_multiplier(self, track_name: str) -> float:
        """Return the multiplier (M = a + b) for a track"""
        params = self.track_params.get(track_name)
        if params:
            return params['a'] + params['b']
        return 100.0
    
    def get_curve_points(self, track_name: str, ratio_min=0.3, ratio_max=3.0, num_points=200):
        """Get points for plotting the curve - optimized with numpy"""
        params = self.track_params.get(track_name)
        if not params:
            return [], []
        
        ratios = np.linspace(ratio_min, ratio_max, num_points)
        times = params['a'] / ratios + params['b']
        return ratios.tolist(), times.tolist()
    
    def get_stats(self) -> dict:
        """Get statistics about the model - optimized"""
        total_points = sum(len(points) for points in self.points_by_track.values())
        
        # Calculate average error only if we have parameters
        all_errors = []
        if self.track_params:
            for track_name, params in self.track_params.items():
                points = self.points_by_track.get(track_name, [])
                a, b = params['a'], params['b']
                for ratio, time in points:
                    predicted = a / ratio + b
                    all_errors.append(abs(predicted - time))
        
        avg_error = np.mean(all_errors) if all_errors else 0
        
        return {
            'total_tracks': len(self.points_by_track),
            'total_points': total_points,
            'global_k': self.global_k,
            'k_std': self.K_STD,
            'track_params': self.track_params,
            'avg_error': avg_error
        }
    
    def get_formula_string(self, track_name: str = None) -> str:
        """Get a readable formula string"""
        if track_name and track_name in self.track_params:
            params = self.track_params[track_name]
            return f"T = {params['a']:.3f} / R + {params['b']:.3f}"
        else:
            return f"T = a / R + b (global k = {self.global_k:.4f})"
    
    def to_dict(self) -> dict:
        """Convert to dictionary for saving"""
        return {
            'track_params': self.track_params,
            'points_by_track': self.points_by_track,
            'global_k': self.global_k,
            'k_std': self.K_STD,
            'fit_error': self.fit_error
        }
    
    @classmethod
    def from_dict(cls, data: dict):
        """Create from dictionary"""
        curve = cls()
        curve.track_params = data.get('track_params', {})
        curve.points_by_track = data.get('points_by_track', {})
        curve.global_k = data.get('global_k', cls.DEFAULT_K)
        curve.K_STD = data.get('k_std', cls.K_STD)
        curve.fit_error = data.get('fit_error')
        return curve


class GlobalCurveManager:
    """Manages loading and saving of the global curve - OPTIMIZED"""
    
    def __init__(self, formulas_dir: str = './track_formulas'):
        self.formulas_dir = Path(formulas_dir)
        self.formulas_dir.mkdir(parents=True, exist_ok=True)
        self.curve = GlobalCurve()
        self.load()
    
    def get_curve_path(self) -> Path:
        return self.formulas_dir / 'global_curve.json'
    
    def load(self) -> bool:
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
        try:
            with open(self.get_curve_path(), 'w') as f:
                json.dump(self.curve.to_dict(), f, indent=2)
            logger.info("Saved global curve")
            return True
        except Exception as e:
            logger.error(f"Error saving curve: {e}")
            return False
    
    def add_point(self, track_name: str, ratio: float, best_time: float, worst_time: float = None) -> bool:
        """Add a point and save"""
        self.curve.add_point(track_name, ratio, best_time, worst_time)
        self.curve.fit_global_k()
        return self.save()
    
    def fit_global_k(self) -> bool:
        """Fit global k parameter"""
        return self.curve.fit_global_k()
    
    def predict_ratio(self, time: float, track_name: str) -> Optional[float]:
        """Predict ratio for given lap time"""
        return self.curve.predict_ratio(time, track_name)
    
    def predict_time(self, ratio: float, track_name: str) -> Optional[float]:
        """Predict lap time for given ratio"""
        return self.curve.predict_time(ratio, track_name)
    
    def get_stats(self) -> dict:
        return self.curve.get_stats()
    
    def get_formula_string(self, track_name: str = None) -> str:
        return self.curve.get_formula_string(track_name)
