#!/usr/bin/env python3
"""
Formula module for hyperbolic curve calculations
T = a / R + b
"""

import numpy as np
from typing import List, Tuple, Optional


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


def fit_curve(ratios: List[float], times: List[float]) -> Tuple[Optional[float], Optional[float], Optional[float], Optional[float]]:
    """
    Fit hyperbolic curve to data points using least squares
    
    Returns: (a, b, avg_error, max_error) or (None, None, None, None) if fit fails
    """
    if len(ratios) < 2:
        return None, None, None, None
    
    r_array = np.array(ratios)
    t_array = np.array(times)
    
    def _hyperbolic(R, a, b):
        return a / R + b
    
    try:
        # Initial guess using first two points
        r1, t1 = ratios[0], times[0]
        r2, t2 = ratios[1], times[1]
        inv_r1 = 1.0 / r1
        inv_r2 = 1.0 / r2
        
        if abs(inv_r1 - inv_r2) > 1e-9:
            a_guess = (t1 - t2) / (inv_r1 - inv_r2)
            b_guess = t1 - a_guess * inv_r1
        else:
            a_guess = 30.0
            b_guess = 70.0
        
        from scipy.optimize import curve_fit
        popt, _ = curve_fit(_hyperbolic, r_array, t_array, p0=[a_guess, b_guess])
        a, b = popt
        
        # Calculate errors
        predictions = _hyperbolic(r_array, a, b)
        errors = np.abs(t_array - predictions)
        avg_error = float(np.mean(errors))
        max_error = float(np.max(errors))
        
        return a, b, avg_error, max_error
        
    except Exception:
        return None, None, None, None


def calculate_derived_values(a: float, b: float) -> Tuple[float, float]:
    """Calculate derived values: M (time at R=1.0) and k (steepness)"""
    M = a + b
    k = a / M if M > 0 else 0
    return M, k


def get_formula_string(a: float, b: float) -> str:
    """Get formatted formula string"""
    return f"T = {a:.3f} / R + {b:.3f}"
