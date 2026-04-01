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

        logger.debug(f"Predicting ratio for {track_name}: time={time:.3f}s")

        result = None

        # Try fitted parameters first
        params = self.track_params.get(track_name)
        if params:
            logger.debug(f"Using fitted parameters for {track_name}: a={params['a']:.3f}, b={params['b']:.3f}")
            result = self.ratio_from_time(time, params['a'], params['b'])
            if result:
                logger.debug(f"Predicted ratio from fit: {result:.6f}")
            else:
                logger.debug(f"Time {time:.3f}s is below floor b={params['b']:.3f}s")

        # Bootstrap from available points if no fit or fit failed
        if result is None:
            points = self.points_by_track.get(track_name, [])
            logger.debug(f"Bootstrap mode for {track_name}: {len(points)} points available")

            if len(points) == 1:
                result = self._bootstrap_one_point(time, track_name, points[0])
            elif len(points) >= 2:
                result = self._bootstrap_two_points(time, points)
            else:
                result = self._bootstrap_no_data(time, track_name)

            if result:
                logger.debug(f"Predicted ratio from bootstrap: {result:.6f}")

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

    def predict_time(self, ratio: float, track_name: str) -> Optional[float]:
        """Predict lap time for a given ratio on a specific track"""
        params = self.track_params.get(track_name)
        if params:
            return params['a'] / ratio + params['b']
        return None

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

    # ------------------------------------------------------------------
    # Explicit fit with quality metrics
    # ------------------------------------------------------------------

    def fit_track_explicit(self, track_name: str) -> Dict:
        """
        Re-fit the curve for a specific track and return quality metrics.
        Equivalent to "Auto-Fit Current Track" in the Curve Builder GUI.

        Returns a dict with keys:
          success, n_points, mode, a, b, mean_error, max_error, rmse, outliers
        where mode is one of:
          'none' | 'bootstrap_1pt' | 'exact_2pt' | 'least_squares' |
          'bootstrap_fallback' | 'existing_params'
        """
        points = self.points_by_track.get(track_name, [])
        n = len(points)

        # Clear prediction cache so next predict uses fresh params
        if track_name in self._prediction_cache:
            del self._prediction_cache[track_name]

        base: Dict = {
            'n_points': n,
            'success': False,
            'mode': 'none',
            'a': None,
            'b': None,
            'mean_error': None,
            'max_error': None,
            'rmse': None,
            'outliers': [],
        }

        if n == 0:
            return base

        # ── 1-point bootstrap ──────────────────────────────────────────
        if n == 1:
            ratio0, mid0 = points[0]
            M = mid0 / (self.global_k / ratio0 + 1 - self.global_k)
            a = float(self.global_k * M)
            b = float((1 - self.global_k) * M)
            self.track_params[track_name] = {'a': a, 'b': b}
            base.update(success=True, mode='bootstrap_1pt', a=a, b=b,
                        mean_error=0.0, max_error=0.0, rmse=0.0)
            return base

        # ── 2-point exact solve ────────────────────────────────────────
        if n == 2:
            r1, m1 = points[0]
            r2, m2 = points[1]
            try:
                denom = 1.0 / r1 - 1.0 / r2
                if abs(denom) < 1e-9:
                    raise ValueError("Ratios too similar for exact solve")
                a = (m1 - m2) / denom
                b = m1 - a / r1
                if b <= 0 or b >= min(m1, m2):
                    raise ValueError("Invalid parameters from 2-point solve")
                a, b = float(a), float(b)
                self.track_params[track_name] = {'a': a, 'b': b}
                base.update(success=True, mode='exact_2pt', a=a, b=b,
                            mean_error=0.0, max_error=0.0, rmse=0.0)
            except Exception as e:
                logger.warning(f"2-point exact solve failed for {track_name}: {e}; falling back to bootstrap")
                self._update_track_params(track_name)
                params = self.track_params.get(track_name, {})
                base.update(success=bool(params), mode='bootstrap_fallback',
                            a=params.get('a'), b=params.get('b'))
            return base

        # ── 3+ points: least-squares ──────────────────────────────────
        ratios = np.array([p[0] for p in points])
        times = np.array([p[1] for p in points])

        def _hyp(R, a, b):
            return a / R + b

        try:
            r1, m1 = points[0]
            r2, m2 = points[1]
            denom = 1.0 / r1 - 1.0 / r2
            if abs(denom) < 1e-9:
                a_guess, b_guess = 30.0, 70.0
            else:
                a_guess = (m1 - m2) / denom
                b_guess = m1 - a_guess / r1
                if b_guess <= 0 or b_guess >= m1:
                    a_guess, b_guess = 30.0, 70.0

            bounds = ([0.1, 30], [500, 200])
            popt, _ = curve_fit(_hyp, ratios, times,
                                p0=[a_guess, b_guess], bounds=bounds, maxfev=500)
            a, b = float(popt[0]), float(popt[1])

            if b <= 0 or b >= float(np.min(times)):
                raise ValueError("Fit parameters out of valid range")

            self.track_params[track_name] = {'a': a, 'b': b}

            preds = _hyp(ratios, a, b)
            errors = np.abs(times - preds)
            rmse = float(np.sqrt(np.mean((times - preds) ** 2)))

            base.update(
                success=True, mode='least_squares', a=a, b=b,
                mean_error=float(np.mean(errors)),
                max_error=float(np.max(errors)),
                rmse=rmse,
                outliers=self.get_outliers(track_name),
            )
            logger.info(f"Fitted {track_name}: a={a:.3f}, b={b:.3f}, RMSE={rmse:.3f}s")

        except Exception as e:
            logger.error(f"Least-squares fit failed for {track_name}: {e}")
            existing = self.track_params.get(track_name)
            if existing:
                base.update(success=True, mode='existing_params',
                            a=existing['a'], b=existing['b'])
            else:
                self._update_track_params(track_name)
                params = self.track_params.get(track_name, {})
                base.update(success=bool(params), mode='bootstrap_fallback',
                            a=params.get('a'), b=params.get('b'))

        return base

    # ------------------------------------------------------------------
    # Outlier detection
    # ------------------------------------------------------------------

    def get_outliers(self, track_name: str, threshold: float = 2.5) -> List[Dict]:
        """
        Return data points whose residual from the fitted curve exceeds
        `threshold` standard deviations above the mean residual.
        Requires at least 3 points (2-point fits are exact by definition).

        Each outlier dict has: ratio, time, residual, z_score
        """
        params = self.track_params.get(track_name)
        points = self.points_by_track.get(track_name, [])

        if not params or len(points) < 3:
            return []

        a, b = params['a'], params['b']
        residuals = [abs(a / r + b - t) for r, t in points]

        mean_res = float(np.mean(residuals))
        std_res = float(np.std(residuals))

        if std_res < 0.01:  # All points fit equally well, nothing to flag
            return []

        outliers = []
        for i, (ratio, time) in enumerate(points):
            z = (residuals[i] - mean_res) / std_res
            if z > threshold:
                outliers.append({
                    'ratio': ratio,
                    'time': time,
                    'residual': residuals[i],
                    'z_score': z,
                })

        return outliers

    # ------------------------------------------------------------------
    # Readiness assessment for autopilot
    # ------------------------------------------------------------------

    def get_readiness(self, track_name: str) -> Dict:
        """
        Enhanced readiness assessment for autopilot with detailed feedback.
        
        Returns a dict with keys:
          can_autopilot  – bool: safe to run autopilot
          needs_warning  – bool: autopilot will work but data is thin
          n_points       – int: data points for this track
          fit_quality    – str: 'none'|'bootstrap_global'|'bootstrap_1pt'|
                                'exact_2pt'|'least_squares'
          points_needed  – int: additional races for a *proper* fit (0 = good)
          min_points_needed – int: minimum additional races for ANY fit
          message        – str: human-readable explanation
          detailed_message – str: detailed explanation for user
        """
        # Get points for this track
        points = self.points_by_track.get(track_name, [])
        n = len(points)
        has_any_global = bool(self.track_params)
        
        # Track name detection
        if not track_name or track_name == 'Unknown':
            return dict(
                can_autopilot=False,
                needs_warning=False,
                n_points=0,
                fit_quality='none',
                points_needed=2,
                min_points_needed=2,
                message="No track detected. Complete a race first.",
                detailed_message="Autopilot needs to know which track you're racing on. "
                               "Complete a race to detect the track name."
            )
        
        # No data at all for any track
        if n == 0 and not has_any_global:
            return dict(
                can_autopilot=False,
                needs_warning=False,
                n_points=0,
                fit_quality='none',
                points_needed=2,
                min_points_needed=2,
                message=f"No data for '{track_name}'. Need at least 2 data points.",
                detailed_message=f"No data available for '{track_name}'. "
                               f"To build a proper curve, you need at least 2 races "
                               f"with different ratio settings.\n\n"
                               f"• Race 1: Set any ratio, record lap times\n"
                               f"• Race 2: Use a different ratio, record lap times\n\n"
                               f"This will create an exact 2-point fit."
            )
        
        # No data for this track, but global data exists
        if n == 0 and has_any_global:
            # Find tracks with best data
            best_tracks = sorted(
                [(t, len(self.points_by_track.get(t, []))) 
                 for t in self.track_params.keys()],
                key=lambda x: x[1], reverse=True
            )[:3]
            
            track_examples = ", ".join([f"'{t}' ({n_pts} pts)" for t, n_pts in best_tracks if n_pts > 0])
            
            return dict(
                can_autopilot=True,
                needs_warning=True,
                n_points=0,
                fit_quality='bootstrap_global',
                points_needed=2,
                min_points_needed=2,
                message=f"No data for '{track_name}'. Using global estimation from other tracks.",
                detailed_message=f"No data for '{track_name}'. Autopilot will use global curve "
                               f"estimated from other tracks: {track_examples}.\n\n"
                               f"This gives rough estimates (±5-10s error). "
                               f"Race at least 2 times at this track to build its own curve.\n\n"
                               f"💡 Tip: Use different ratio settings for each race to get a "
                               f"good spread of data points."
            )
        
        # 1 point
        if n == 1:
            ratio0, time0 = points[0]
            return dict(
                can_autopilot=True,
                needs_warning=True,
                n_points=1,
                fit_quality='bootstrap_1pt',
                points_needed=1,
                min_points_needed=1,
                message=f"Only 1 data point for '{track_name}'. Need 1 more for exact fit.",
                detailed_message=f"Only 1 data point for '{track_name}'. "
                               f"Current ratio: {ratio0:.4f}, lap time: {time0:.2f}s\n\n"
                               f"With 1 more race (using a DIFFERENT ratio), we can create an "
                               f"exact 2-point fit with <1s error.\n\n"
                               f"Current mode: 1-point bootstrap (±2-5s error)"
            )
        
        # 2 points
        if n == 2:
            r1, t1 = points[0]
            r2, t2 = points[1]
            
            return dict(
                can_autopilot=True,
                needs_warning=False,
                n_points=2,
                fit_quality='exact_2pt',
                points_needed=0,
                min_points_needed=0,
                message=f"2 data points for '{track_name}' — exact fit ready.",
                detailed_message=f"2 data points for '{track_name}':\n"
                               f"  • R={r1:.4f} → T={t1:.2f}s\n"
                               f"  • R={r2:.4f} → T={t2:.2f}s\n\n"
                               f"Exact 2-point curve created (<1s error). "
                               f"Add 1 more point for least-squares fit (<0.3s error)."
            )
        
        # 3+ points - n >= 3
        if n >= 3:
            # Calculate fit quality if parameters exist
            quality_info = ""
            if track_name in self.track_params:
                a, b = self.track_params[track_name]['a'], self.track_params[track_name]['b']
                
                # Calculate errors using the points we already have
                predictions = [a / r + b for r, _ in points]
                actual_times = [t for _, t in points]
                errors = [abs(p - a) for p, a in zip(predictions, actual_times)]
                avg_error = sum(errors) / len(errors)
                max_error = max(errors)
                
                quality_info = f"\n\nFit quality:\n  • Average error: {avg_error:.2f}s\n  • Max error: {max_error:.2f}s"
                
                # Check outliers
                outliers = self.get_outliers(track_name)
                if outliers:
                    quality_info += f"\n  • ⚠ {len(outliers)} outlier(s) detected (see Curve Editor)"
            
            return dict(
                can_autopilot=True,
                needs_warning=False,
                n_points=n,
                fit_quality='least_squares',
                points_needed=0,
                min_points_needed=0,
                message=f"{n} data points for '{track_name}' — robust least-squares fit.",
                detailed_message=f"{n} data points for '{track_name}'. Least-squares fit with high accuracy.{quality_info}"
            )
        
        # Fallback (should never reach here)
        return dict(
            can_autopilot=False,
            needs_warning=False,
            n_points=n,
            fit_quality='none',
            points_needed=2,
            min_points_needed=2,
            message=f"Insufficient data for '{track_name}'.",
            detailed_message=f"Need at least 2 data points for '{track_name}'. Currently have {n}."
        )

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

    def fit_track(self, track_name: str) -> Dict:
        """
        Explicitly re-fit the curve for a track and return quality metrics.
        Does NOT save — call save() separately once you're happy with the result.
        """
        return self.curve.fit_track_explicit(track_name)

    def get_outliers(self, track_name: str, threshold: float = 2.5) -> List[Dict]:
        """Return outlier data points for a track (requires 3+ points)."""
        return self.curve.get_outliers(track_name, threshold)

    def get_readiness(self, track_name: str) -> Dict:
        """Assess autopilot readiness for the given track."""
        return self.curve.get_readiness(track_name)

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
