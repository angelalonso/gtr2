#!/usr/bin/env python3
"""
Formula module for hyperbolic curve calculations
T = a / R + b
"""

import numpy as np
from typing import List, Tuple, Optional

DEFAULT_A_VALUE = 32.0


def hyperbolic(R: float, a: float, b: float) -> float:
    """Calculate lap time from ratio using hyperbolic formula"""
    return a / R + b


def ratio_from_time(T: float, a: float, b: float) -> Optional[float]:
    """Calculate ratio from lap time using hyperbolic formula"""
    denominator = T - b
    if denominator <= 0:
        return None
    return a / denominator


def predict_ratios(times: List[float], a: float, b: float) -> List[Optional[float]]:
    """Predict ratios for multiple lap times"""
    return [ratio_from_time(T, a, b) for T in times]


def predict_times(ratios: List[float], a: float, b: float) -> List[float]:
    """Predict lap times for multiple ratios"""
    return [hyperbolic(R, a, b) for R in ratios]


def get_curve_points(a: float, b: float, r_min: float = 0.4, r_max: float = 2.0, num_points: int = 200) -> Tuple[np.ndarray, np.ndarray]:
    """Generate points for plotting the curve"""
    ratios = np.linspace(r_min, r_max, num_points)
    times = a / ratios + b
    return ratios, times


def fit_curve(ratios: List[float], times: List[float], verbose: bool = True) -> Tuple[Optional[float], Optional[float], Optional[float], Optional[float]]:
    """
    Fit hyperbolic curve to data points using least squares
    
    Returns: (a, b, avg_error, max_error) or (None, None, None, None) if fit fails
    """
    print(f"\n  [fit_curve] CALLED with {len(ratios)} data points")
    
    if len(ratios) < 2:
        print(f"  [fit_curve] ERROR: Need at least 2 points, got {len(ratios)}")
        return None, None, None, None
    
    print(f"  [fit_curve] Data points:")
    for i, (r, t) in enumerate(zip(ratios, times)):
        print(f"    {i+1}: R={r:.6f}, T={t:.3f}")
    
    r_array = np.array(ratios)
    t_array = np.array(times)
    
    def _hyperbolic(R, a, b):
        return a / R + b
    
    try:
        r1, t1 = ratios[0], times[0]
        r2, t2 = ratios[1], times[1]
        inv_r1 = 1.0 / r1
        inv_r2 = 1.0 / r2
        
        print(f"  [fit_curve] First two points: ({r1}, {t1}) and ({r2}, {t2})")
        print(f"  [fit_curve] Inverse ratios: inv_r1={inv_r1:.6f}, inv_r2={inv_r2:.6f}")
        
        if abs(inv_r1 - inv_r2) > 1e-9:
            a_guess = (t1 - t2) / (inv_r1 - inv_r2)
            b_guess = t1 - a_guess * inv_r1
            print(f"  [fit_curve] Calculated guess: a={a_guess:.4f}, b={b_guess:.4f}")
        else:
            a_guess = DEFAULT_A_VALUE
            b_guess = 70.0
            print(f"  [fit_curve] Using default guess: a={a_guess:.4f}, b={b_guess:.4f}")
        
        from scipy.optimize import curve_fit
        print(f"  [fit_curve] Calling scipy.optimize.curve_fit...")
        popt, _ = curve_fit(_hyperbolic, r_array, t_array, p0=[a_guess, b_guess])
        a, b = popt
        print(f"  [fit_curve] curve_fit result: a={a:.6f}, b={b:.6f}")
        
        predictions = _hyperbolic(r_array, a, b)
        errors = np.abs(t_array - predictions)
        avg_error = float(np.mean(errors))
        max_error = float(np.max(errors))
        
        print(f"  [fit_curve] Fit complete: {get_formula_string(a, b)}")
        print(f"  [fit_curve] Avg error: {avg_error:.4f}s, Max error: {max_error:.4f}s")
        
        for i, (r, t, pred, err) in enumerate(zip(ratios, times, predictions, errors)):
            print(f"    Point {i+1}: predicted T={pred:.3f}s, error={err:.3f}s")
        
        return a, b, avg_error, max_error
        
    except Exception as e:
        print(f"  [fit_curve] EXCEPTION: {e}")
        import traceback
        traceback.print_exc()
        return None, None, None, None


def calculate_derived_values(a: float, b: float) -> Tuple[float, float]:
    """Calculate derived values: M (time at R=1.0) and k (steepness)"""
    M = a + b
    k = a / M if M > 0 else 0
    return M, k


def get_formula_string(a: float, b: float) -> str:
    """Get formatted formula string"""
    return f"T = {a:.4f} / R + {b:.4f}"
