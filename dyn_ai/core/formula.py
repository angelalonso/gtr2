#!/usr/bin/env python3
"""
Formula calculations - lightweight version without scipy dependency
"""

import math
from typing import List, Tuple, Optional

DEFAULT_A = 32.0
DEFAULT_B = 70.0


def hyperbolic(ratio: float, a: float = DEFAULT_A, b: float = DEFAULT_B) -> float:
    """Calculate lap time from ratio: T = a/R + b"""
    if ratio <= 0:
        return b + 100  # Fallback for invalid ratio
    return a / ratio + b


def ratio_from_time(time: float, a: float = DEFAULT_A, b: float = DEFAULT_B) -> Optional[float]:
    """Calculate ratio from lap time: R = a/(T - b)"""
    denominator = time - b
    if denominator <= 1e-6:
        return None
    return a / denominator


def predict_time(ratio: float, a: float, b: float) -> float:
    """Predict lap time from ratio"""
    return hyperbolic(ratio, a, b)


def fit_curve_simple(ratios: List[float], times: List[float]) -> Tuple[Optional[float], Optional[float], Optional[float], Optional[float]]:
    """
    Fit hyperbolic curve T = a/R + b to data points using a simplified method.
    Uses the fact that a is the slope when plotting T vs 1/R.
    
    Returns: (a, b, avg_error, max_error) or (None, None, None, None)
    """
    if len(ratios) < 2:
        return None, None, None, None
    
    # Transform to linear: T = a*(1/R) + b
    inv_ratios = [1.0 / r for r in ratios]
    
    # Simple linear regression
    n = len(inv_ratios)
    sum_x = sum(inv_ratios)
    sum_y = sum(times)
    sum_xy = sum(x * y for x, y in zip(inv_ratios, times))
    sum_xx = sum(x * x for x in inv_ratios)
    
    denominator = n * sum_xx - sum_x * sum_x
    if abs(denominator) < 1e-9:
        return None, None, None, None
    
    a = (n * sum_xy - sum_x * sum_y) / denominator
    b = (sum_y - a * sum_x) / n
    
    # Ensure b is reasonable
    b = max(10.0, min(200.0, b))
    
    # Calculate errors
    errors = []
    for r, t in zip(ratios, times):
        predicted = a / r + b
        errors.append(abs(predicted - t))
    
    avg_error = sum(errors) / n
    max_error = max(errors)
    
    return a, b, avg_error, max_error


def formula_string(a: float, b: float) -> str:
    """Get formatted formula string"""
    return f"T = {a:.4f} / R + {b:.4f}"
