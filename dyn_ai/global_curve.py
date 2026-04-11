"""
global_curve.py — GlobalCurve model (unchanged) + GlobalCurveManager
UPDATED: GlobalCurveManager now persists to SQLite via db_manager instead
         of reading/writing global_curve.json.  Pass db=None to fall back
         to the old JSON behaviour.
"""

import json
import numpy as np
from pathlib import Path
from typing import Optional, List, Tuple, Dict
from scipy.optimize import curve_fit
import logging

logger = logging.getLogger(__name__)


# ── GlobalCurve (model only — no I/O, unchanged) ──────────────────────────────

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
        self._prediction_cache: Dict[str, Dict[float, float]] = {}
        self._max_cache_size = 100

    def midpoint(self, ratio: float, a: float, b: float) -> float:
        return a / ratio + b

    def ratio_from_time(self, time: float, a: float, b: float) -> Optional[float]:
        denominator = time - b
        if denominator <= 0:
            return None
        return a / denominator

    def predict_ratio(self, time: float, track_name: str) -> Optional[float]:
        cache_key = round(time, 3)
        if track_name in self._prediction_cache:
            cached = self._prediction_cache[track_name].get(cache_key)
            if cached is not None:
                return cached

        result = None
        params = self.track_params.get(track_name)
        if params:
            result = self.ratio_from_time(time, params['a'], params['b'])

        if result is None:
            points = self.points_by_track.get(track_name, [])
            if len(points) == 1:
                result = self._bootstrap_one_point(time, track_name, points[0])
            elif len(points) >= 2:
                result = self._bootstrap_two_points(time, points)
            else:
                result = self._bootstrap_no_data(time, track_name)

        if result is not None:
            if track_name not in self._prediction_cache:
                self._prediction_cache[track_name] = {}
            cache = self._prediction_cache[track_name]
            if len(cache) >= self._max_cache_size:
                del cache[next(iter(cache))]
            cache[cache_key] = result

        return result

    def predict_time(self, ratio: float, track_name: str) -> Optional[float]:
        params = self.track_params.get(track_name)
        if params:
            return params['a'] / ratio + params['b']
        return None

    def _bootstrap_one_point(self, time, track_name, point):
        ratio0, mid0 = point
        M = mid0 / (self.global_k / ratio0 + 1 - self.global_k)
        a = self.global_k * M
        b = (1 - self.global_k) * M
        return self.ratio_from_time(time, a, b)

    def _bootstrap_two_points(self, time, points):
        if len(points) < 2:
            return None
        points_sorted = sorted(points, key=lambda x: x[0])
        r1, m1 = points_sorted[0]
        r2, m2 = points_sorted[1]
        try:
            inv_r1, inv_r2 = 1.0 / r1, 1.0 / r2
            denom = inv_r1 - inv_r2
            if abs(denom) < 1e-9:
                return self._bootstrap_one_point(time, "", points_sorted[0])
            a = (m1 - m2) / denom
            b = m1 - a * inv_r1
            if b <= 0 or b >= m1:
                return self._bootstrap_one_point(time, "", points_sorted[0])
            return self.ratio_from_time(time, a, b)
        except Exception as e:
            logger.error(f"Error in two-point bootstrap: {e}")
            return self._bootstrap_one_point(time, "", points_sorted[0])

    def _bootstrap_no_data(self, time, track_name):
        if self.track_params:
            first_track = next(iter(self.track_params.keys()))
            params = self.track_params[first_track]
            M = params['a'] + params['b']
            a = self.global_k * M
            b = (1 - self.global_k) * M
            return self.ratio_from_time(time, a, b)
        logger.warning(f"No data for track {track_name}, using fallback ratio=1.0")
        return 1.0

    def add_point(self, track_name: str, ratio: float, best_time: float, worst_time: float = None):
        midpoint = (best_time + worst_time) / 2 if worst_time is not None else best_time
        if track_name not in self.points_by_track:
            self.points_by_track[track_name] = []
        self.points_by_track[track_name].append((ratio, midpoint))
        self.points_by_track[track_name].sort(key=lambda x: x[0])
        if track_name in self._prediction_cache:
            del self._prediction_cache[track_name]
        self._update_track_params(track_name)

    def _update_track_params(self, track_name: str):
        points = self.points_by_track.get(track_name, [])
        n = len(points)
        if n == 0:
            return
        elif n == 1:
            ratio0, mid0 = points[0]
            M = mid0 / (self.global_k / ratio0 + 1 - self.global_k)
            self.track_params[track_name] = {'a': self.global_k * M, 'b': (1 - self.global_k) * M}
        elif n == 2:
            self._fit_two_points(track_name, points)
        else:
            self._fit_multiple_points(track_name, points)

    def _fit_two_points(self, track_name, points):
        try:
            r1, m1 = points[0]
            r2, m2 = points[1]
            inv_r1, inv_r2 = 1.0 / r1, 1.0 / r2
            denom = inv_r1 - inv_r2
            if abs(denom) < 1e-9:
                return
            a = (m1 - m2) / denom
            b = m1 - a * inv_r1
            if b > 0 and b < m1:
                self.track_params[track_name] = {'a': a, 'b': b}
        except Exception as e:
            logger.error(f"Error fitting two points: {e}")

    def _fit_multiple_points(self, track_name, points):
        try:
            ratios = np.array([p[0] for p in points])
            times = np.array([p[1] for p in points])

            def model(r, a, b):
                return a / r + b

            p0 = [self.global_k * np.mean(times), (1 - self.global_k) * np.mean(times)]
            popt, _ = curve_fit(model, ratios, times, p0=p0, maxfev=5000)
            a, b = popt
            if b > 0:
                self.track_params[track_name] = {'a': a, 'b': b}
        except Exception as e:
            logger.error(f"Error fitting multiple points for {track_name}: {e}")
            if len(points) >= 2:
                self._fit_two_points(track_name, points[-2:])

    def fit_global_k(self):
        k_values = []
        for params in self.track_params.values():
            M = params['a'] + params['b']
            if M > 0:
                k_values.append(params['a'] / M)
        if k_values:
            self.global_k = np.mean(k_values)
            self.K_STD = np.std(k_values)
            logger.info(f"Updated global k = {self.global_k:.4f} ± {self.K_STD:.4f}")
            return True
        return False

    # Additional helpers kept from original (get_readiness, get_outliers, etc.)
    def get_outliers(self, track_name: str, threshold: float = 2.5) -> List[Dict]:
        points = self.points_by_track.get(track_name, [])
        params = self.track_params.get(track_name)
        if not params or len(points) < 3:
            return []
        a, b = params['a'], params['b']
        errors = [abs(a / r + b - t) for r, t in points]
        mean_e = np.mean(errors)
        std_e = np.std(errors)
        if std_e < 1e-9:
            return []
        return [
            {'ratio': r, 'midpoint': t, 'error': e, 'z_score': (e - mean_e) / std_e}
            for (r, t), e in zip(points, errors)
            if (e - mean_e) / std_e > threshold
        ]

    def get_readiness(self, track_name: str) -> Dict:
        n = len(self.points_by_track.get(track_name, []))
        if n == 0:
            return dict(can_autopilot=False, needs_warning=True, n_points=0,
                        fit_quality='none', points_needed=2, min_points_needed=2,
                        message=f"No data for '{track_name}'.",
                        detailed_message=f"Need at least 2 data points for '{track_name}'.")
        if n == 1:
            return dict(can_autopilot=False, needs_warning=True, n_points=1,
                        fit_quality='bootstrap_1', points_needed=1, min_points_needed=1,
                        message=f"1 data point for '{track_name}' — bootstrap mode.",
                        detailed_message=f"1 point: using global k bootstrap. Prediction may be inaccurate.")
        if n == 2:
            return dict(can_autopilot=True, needs_warning=True, n_points=2,
                        fit_quality='exact_2', points_needed=0, min_points_needed=0,
                        message=f"2 data points for '{track_name}' — exact 2-point fit.",
                        detailed_message=f"2 points: exact fit, no error estimate yet.")
        return dict(can_autopilot=True, needs_warning=False, n_points=n,
                    fit_quality='least_squares', points_needed=0, min_points_needed=0,
                    message=f"{n} data points for '{track_name}' — robust least-squares fit.",
                    detailed_message=f"{n} points: least-squares fit.")

    def fit_track_explicit(self, track_name: str) -> Dict:
        self._update_track_params(track_name)
        return self.get_readiness(track_name)

    def get_track_multiplier(self, track_name: str) -> float:
        params = self.track_params.get(track_name)
        return (params['a'] + params['b']) if params else 100.0

    def get_curve_points(self, track_name: str, ratio_min=0.3, ratio_max=3.0, num_points=200):
        params = self.track_params.get(track_name)
        if not params:
            return [], []
        ratios = np.linspace(ratio_min, ratio_max, num_points)
        times = params['a'] / ratios + params['b']
        return ratios.tolist(), times.tolist()

    def get_stats(self) -> dict:
        total_points = sum(len(p) for p in self.points_by_track.values())
        all_errors = []
        for track_name, params in self.track_params.items():
            a, b = params['a'], params['b']
            for ratio, time in self.points_by_track.get(track_name, []):
                all_errors.append(abs(a / ratio + b - time))
        return {
            'total_tracks': len(self.points_by_track),
            'total_points': total_points,
            'global_k': self.global_k,
            'k_std': self.K_STD,
            'track_params': self.track_params,
            'avg_error': float(np.mean(all_errors)) if all_errors else 0,
        }

    def get_formula_string(self, track_name: str = None) -> str:
        if track_name and track_name in self.track_params:
            p = self.track_params[track_name]
            return f"T = {p['a']:.3f} / R + {p['b']:.3f}"
        return f"T = a / R + b (global k = {self.global_k:.4f})"

    def to_dict(self) -> dict:
        return {
            'track_params': self.track_params,
            'points_by_track': self.points_by_track,
            'global_k': self.global_k,
            'k_std': self.K_STD,
            'fit_error': self.fit_error,
        }

    @classmethod
    def from_dict(cls, data: dict):
        curve = cls()
        curve.track_params = data.get('track_params', {})
        curve.points_by_track = data.get('points_by_track', {})
        curve.global_k = data.get('global_k', cls.DEFAULT_K)
        curve.K_STD = data.get('k_std', cls.K_STD)
        curve.fit_error = data.get('fit_error')
        return curve


# ── GlobalCurveManager (I/O layer) ────────────────────────────────────────────

class GlobalCurveManager:
    """
    Manages loading and saving of the global curve.

    SQLite mode (preferred)
    -----------------------
    Pass a ``db_manager.Database`` instance.  All curve points, fitted
    parameters, and the global k value are stored in the database tables
    ``curve_points``, ``curve_params``, and ``curve_globals``.

    JSON fallback
    -------------
    If *db* is ``None`` (or the SQLite tables are empty on first run) the
    manager falls back to ``<formulas_dir>/global_curve.json``.  When a
    JSON file is found during the first load with a live DB, it is migrated
    into SQLite automatically and the old file is left in place as a backup.
    """

    def __init__(self, formulas_dir: str = './track_formulas', db=None):
        self.formulas_dir = Path(formulas_dir)
        self.formulas_dir.mkdir(parents=True, exist_ok=True)
        self.db = db
        self.curve = GlobalCurve()
        self.load()

    # ── Paths ─────────────────────────────────────────────────────────────────

    def get_curve_path(self) -> Path:
        return self.formulas_dir / 'global_curve.json'

    # ── Load ──────────────────────────────────────────────────────────────────

    def load(self) -> bool:
        if self.db is not None:
            loaded = self._load_from_db()
            if loaded:
                return True
            # DB empty — try to migrate from JSON
            json_path = self.get_curve_path()
            if json_path.exists():
                logger.info("Migrating global_curve.json → SQLite …")
                if self._load_from_json():
                    self._save_to_db()   # write everything into DB
                    logger.info("Migration complete.")
                    return True
            return False
        else:
            return self._load_from_json()

    def _load_from_db(self) -> bool:
        try:
            points_by_track = self.db.get_all_curve_points()
            if not points_by_track:
                return False  # DB is empty

            self.curve.points_by_track = points_by_track
            self.curve.track_params = self.db.get_all_curve_params()
            self.curve.global_k = self.db.get_curve_global('global_k', GlobalCurve.DEFAULT_K)
            self.curve.K_STD = self.db.get_curve_global('k_std', GlobalCurve.K_STD)

            logger.info(
                f"Loaded global curve from SQLite "
                f"({self.curve.get_stats()['total_points']} points)"
            )
            return True
        except Exception as e:
            logger.error(f"Error loading curve from DB: {e}")
            return False

    def _load_from_json(self) -> bool:
        path = self.get_curve_path()
        if not path.exists():
            return False
        try:
            with open(path, 'r') as f:
                data = json.load(f)
            self.curve = GlobalCurve.from_dict(data)
            logger.info(
                f"Loaded global curve from JSON "
                f"({self.curve.get_stats()['total_points']} points)"
            )
            return True
        except Exception as e:
            logger.error(f"Error loading curve from JSON: {e}")
            return False

    # ── Save ──────────────────────────────────────────────────────────────────

    def save(self) -> bool:
        if self.db is not None:
            return self._save_to_db()
        return self._save_to_json()

    def _save_to_db(self) -> bool:
        try:
            # Persist every point (insert-only; duplicates are harmless but
            # we clear and rewrite to avoid accumulating stale entries after
            # a point is removed via the curve editor).
            with self.db._connect() as con:
                con.execute("DELETE FROM curve_points")
                con.execute("DELETE FROM curve_params")

            for track_name, points in self.curve.points_by_track.items():
                for ratio, midpoint in points:
                    self.db.save_curve_point(track_name, ratio, midpoint)

            for track_name, params in self.curve.track_params.items():
                self.db.save_curve_params(track_name, params['a'], params['b'])

            self.db.save_curve_global('global_k', self.curve.global_k)
            self.db.save_curve_global('k_std', self.curve.K_STD)

            logger.info("Saved global curve to SQLite")
            return True
        except Exception as e:
            logger.error(f"Error saving curve to DB: {e}")
            return False

    def _save_to_json(self) -> bool:
        try:
            with open(self.get_curve_path(), 'w') as f:
                json.dump(self.curve.to_dict(), f, indent=2)
            logger.info("Saved global curve to JSON")
            return True
        except Exception as e:
            logger.error(f"Error saving curve to JSON: {e}")
            return False

    # ── Public helpers (delegating to GlobalCurve) ────────────────────────────

    def add_point(self, track_name: str, ratio: float, best_time: float,
                  worst_time: float = None) -> bool:
        self.curve.add_point(track_name, ratio, best_time, worst_time)
        self.curve.fit_global_k()
        return self.save()

    def fit_global_k(self) -> bool:
        return self.curve.fit_global_k()

    def fit_track(self, track_name: str) -> Dict:
        return self.curve.fit_track_explicit(track_name)

    def get_outliers(self, track_name: str, threshold: float = 2.5) -> List[Dict]:
        return self.curve.get_outliers(track_name, threshold)

    def get_readiness(self, track_name: str) -> Dict:
        return self.curve.get_readiness(track_name)

    def predict_ratio(self, time: float, track_name: str) -> Optional[float]:
        return self.curve.predict_ratio(time, track_name)

    def predict_time(self, ratio: float, track_name: str) -> Optional[float]:
        return self.curve.predict_time(ratio, track_name)

    def get_stats(self) -> dict:
        return self.curve.get_stats()

    def get_formula_string(self, track_name: str = None) -> str:
        return self.curve.get_formula_string(track_name)
