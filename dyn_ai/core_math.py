#!/usr/bin/env python3
"""
Single source of truth for all mathematical operations.
NO database access, NO file I/O, NO GUI code.
"""

from typing import List, Tuple, Optional, Dict
from dataclasses import dataclass
import numpy as np

# Global constants - can be overridden by config
DEFAULT_A_VALUE = 32.0
MIN_RATIO = 0.3
MAX_RATIO = 3.0
MIN_B = 10.0
MAX_B = 200.0
MIN_A = 1.0


@dataclass
class FitStats:
    """Statistics from curve fitting"""
    avg_error: float = 0.0
    max_error: float = 0.0
    outliers_removed: int = 0
    points_used: int = 0
    method_used: str = "none"
    threshold_used: float = 0.0


def time_from_ratio(ratio: float, a: float, b: float) -> float:
    """
    Calculate lap time from ratio using T = a/R + b
    
    Args:
        ratio: AI ratio value
        a: Curve steepness parameter
        b: Asymptote (minimum theoretical lap time)
    
    Returns:
        Lap time in seconds
    """
    if ratio <= 0 or a <= 0:
        return b
    return a / ratio + b


def ratio_from_time(lap_time: float, a: float, b: float) -> Optional[float]:
    """
    Calculate ratio from lap time using R = a/(T - b)
    
    Args:
        lap_time: Lap time in seconds
        a: Curve steepness parameter
        b: Asymptote
    
    Returns:
        Ratio value, or None if calculation is invalid
    """
    denominator = lap_time - b
    if denominator <= 0 or a <= 0:
        return None
    return a / denominator


def clamp_ratio(ratio: float, min_ratio: float = MIN_RATIO, max_ratio: float = MAX_RATIO) -> float:
    """Clamp ratio to acceptable range"""
    return max(min_ratio, min(max_ratio, ratio))


def clamp_b(b: float, min_b: float = MIN_B, max_b: float = MAX_B) -> float:
    """Clamp b parameter to acceptable range"""
    return max(min_b, min(max_b, b))


def is_valid_formula(a: float, b: float) -> bool:
    """Check if formula parameters are valid"""
    return a >= MIN_A and MIN_B <= b <= MAX_B


def calculate_b_from_point(ratio: float, lap_time: float, a: float = DEFAULT_A_VALUE) -> float:
    """
    Calculate b parameter from a single data point.
    b = T - a/R
    """
    if ratio <= 0:
        return MIN_B
    b = lap_time - (a / ratio)
    return clamp_b(b)


def detect_outliers_std(
    ratios: List[float], 
    times: List[float], 
    a: float, 
    b: float, 
    std_multiplier: float = 2.0,
    min_points: int = 5
) -> Tuple[List[int], List[float], FitStats]:
    """
    Detect outliers using standard deviation method.
    Points with error > mean + std_multiplier * std_dev are considered outliers.
    """
    stats = FitStats(method_used="std", threshold_used=std_multiplier, points_used=len(ratios))
    
    if len(ratios) < min_points:
        return list(range(len(ratios))), [], stats
    
    predicted = [time_from_ratio(r, a, b) for r in ratios]
    errors = [abs(t - p) for t, p in zip(times, predicted)]
    
    mean_error = np.mean(errors)
    std_error = np.std(errors)
    
    if std_error < 0.01:
        return list(range(len(ratios))), errors, stats
    
    threshold = mean_error + (std_multiplier * std_error)
    
    outlier_indices = [i for i, err in enumerate(errors) if err > threshold]
    keep_indices = [i for i in range(len(ratios)) if i not in outlier_indices]
    
    stats.outliers_removed = len(outlier_indices)
    return keep_indices, errors, stats


def detect_outliers_iqr(
    ratios: List[float], 
    times: List[float], 
    a: float, 
    b: float, 
    iqr_multiplier: float = 1.5,
    min_points: int = 6
) -> Tuple[List[int], List[float], FitStats]:
    """Detect outliers using Interquartile Range (IQR) method."""
    stats = FitStats(method_used="iqr", threshold_used=iqr_multiplier, points_used=len(ratios))
    
    if len(ratios) < min_points:
        return list(range(len(ratios))), [], stats
    
    predicted = [time_from_ratio(r, a, b) for r in ratios]
    errors = [abs(t - p) for t, p in zip(times, predicted)]
    
    errors_sorted = sorted(errors)
    q1_idx = int(len(errors_sorted) * 0.25)
    q3_idx = int(len(errors_sorted) * 0.75)
    
    q1 = errors_sorted[q1_idx]
    q3 = errors_sorted[q3_idx]
    iqr = q3 - q1
    
    if iqr < 0.01:
        return list(range(len(ratios))), errors, stats
    
    threshold = q3 + (iqr_multiplier * iqr)
    
    outlier_indices = [i for i, err in enumerate(errors) if err > threshold]
    keep_indices = [i for i in range(len(ratios)) if i not in outlier_indices]
    
    stats.outliers_removed = len(outlier_indices)
    return keep_indices, errors, stats


def detect_outliers_percentile(
    ratios: List[float], 
    times: List[float], 
    a: float, 
    b: float, 
    percentile_threshold: float = 90.0,
    min_points: int = 4
) -> Tuple[List[int], List[float], FitStats]:
    """Detect outliers using percentile method."""
    stats = FitStats(method_used="percentile", threshold_used=percentile_threshold, points_used=len(ratios))
    
    if len(ratios) < min_points:
        return list(range(len(ratios))), [], stats
    
    predicted = [time_from_ratio(r, a, b) for r in ratios]
    errors = [abs(t - p) for t, p in zip(times, predicted)]
    
    errors_sorted = sorted(errors)
    percentile_idx = int(len(errors_sorted) * (percentile_threshold / 100.0))
    if percentile_idx >= len(errors_sorted):
        percentile_idx = len(errors_sorted) - 1
    threshold = errors_sorted[percentile_idx]
    
    outlier_indices = [i for i, err in enumerate(errors) if err > threshold]
    keep_indices = [i for i in range(len(ratios)) if i not in outlier_indices]
    
    stats.outliers_removed = len(outlier_indices)
    return keep_indices, errors, stats


def filter_outliers(
    ratios: List[float],
    times: List[float],
    a: float,
    b: float,
    method: str = "std",
    threshold: float = 2.0,
    min_points: int = 4
) -> Tuple[List[float], List[float], FitStats]:
    """
    Filter outliers from data points using specified method.
    
    Args:
        method: "std", "iqr", "percentile", or "none"
        threshold: Threshold parameter for the method
        min_points: Minimum points required before filtering
    
    Returns:
        (filtered_ratios, filtered_times, stats)
    """
    if len(ratios) < min_points or method == "none":
        return ratios, times, FitStats(points_used=len(ratios), method_used=method)
    
    if method == "std":
        keep_indices, _, stats = detect_outliers_std(ratios, times, a, b, threshold, min_points)
    elif method == "iqr":
        keep_indices, _, stats = detect_outliers_iqr(ratios, times, a, b, threshold, min_points)
    elif method == "percentile":
        keep_indices, _, stats = detect_outliers_percentile(ratios, times, a, b, threshold, min_points)
    else:
        return ratios, times, FitStats(points_used=len(ratios), method_used=method)
    
    if len(keep_indices) < 2:
        return ratios, times, FitStats(points_used=len(ratios), method_used=method)
    
    filtered_ratios = [ratios[i] for i in keep_indices]
    filtered_times = [times[i] for i in keep_indices]
    
    stats.points_used = len(filtered_ratios)
    return filtered_ratios, filtered_times, stats


def fit_hyperbolic(
    ratios: List[float], 
    times: List[float], 
    fixed_a: Optional[float] = None,
    outlier_method: str = "none",
    outlier_threshold: float = 2.0,
    min_points_after_filtering: int = 2
) -> Tuple[Optional[float], Optional[float], FitStats]:
    """
    Fit hyperbolic curve T = a/R + b to data points.
    
    This is the SINGLE function used by ALL components for curve fitting.
    
    Args:
        ratios: List of ratio values
        times: List of corresponding lap times
        fixed_a: If provided, only optimize b (keep a fixed)
        outlier_method: "std", "iqr", "percentile", or "none"
        outlier_threshold: Threshold for outlier detection
        min_points_after_filtering: Minimum points required after filtering
    
    Returns:
        (a, b, stats) where stats contains fit quality information
        Returns (None, None, stats) if fitting fails
    """
    stats = FitStats(method_used=outlier_method, threshold_used=outlier_threshold)
    
    if len(ratios) < 2:
        return None, None, stats
    
    # Initial guess for parameters
    if fixed_a is not None:
        a_guess = fixed_a
        # Guess b from first point
        if ratios[0] > 0:
            b_guess = clamp_b(times[0] - (a_guess / ratios[0]))
        else:
            b_guess = 70.0
    else:
        # Guess a and b from first two points
        try:
            r1, t1 = ratios[0], times[0]
            r2, t2 = ratios[1], times[1]
            inv_r1 = 1.0 / max(r1, 0.01)
            inv_r2 = 1.0 / max(r2, 0.01)
            
            if abs(inv_r1 - inv_r2) > 1e-9:
                a_guess = (t1 - t2) / (inv_r1 - inv_r2)
                b_guess = t1 - a_guess * inv_r1
            else:
                a_guess = DEFAULT_A_VALUE
                b_guess = 70.0
        except Exception:
            a_guess = DEFAULT_A_VALUE
            b_guess = 70.0
        
        a_guess = max(a_guess, MIN_A)
        b_guess = clamp_b(b_guess)
    
    # Apply outlier filtering if requested
    filtered_ratios, filtered_times, outlier_stats = filter_outliers(
        ratios, times, a_guess, b_guess, outlier_method, outlier_threshold, min_points=4
    )
    
    stats.outliers_removed = outlier_stats.outliers_removed
    
    if len(filtered_ratios) < min_points_after_filtering:
        # Not enough points after filtering, use original data
        filtered_ratios, filtered_times = ratios, times
        stats.outliers_removed = 0
    
    if len(filtered_ratios) < 2:
        return None, None, stats
    
    # Perform the fit
    try:
        from scipy.optimize import curve_fit
        
        r_array = np.array(filtered_ratios)
        t_array = np.array(filtered_times)
        
        def hyperbolic_func(R, a, b):
            R_safe = np.maximum(R, 0.01)
            return a / R_safe + b
        
        if fixed_a is not None:
            # Only optimize b
            def hyperbolic_func_b_only(R, b):
                R_safe = np.maximum(R, 0.01)
                return fixed_a / R_safe + b
            
            popt, _ = curve_fit(hyperbolic_func_b_only, r_array, t_array, p0=[b_guess])
            a = fixed_a
            b = popt[0]
        else:
            popt, _ = curve_fit(hyperbolic_func, r_array, t_array, p0=[a_guess, b_guess])
            a, b = popt
        
        a = max(a, MIN_A)
        b = clamp_b(b)
        
        # Calculate errors
        predictions = [time_from_ratio(r, a, b) for r in ratios]
        errors = [abs(t - p) for t, p in zip(times, predictions)]
        stats.avg_error = float(np.mean(errors))
        stats.max_error = float(np.max(errors))
        stats.points_used = len(filtered_ratios)
        
        return a, b, stats
        
    except Exception:
        return None, None, stats


def get_formula_string(a: float, b: float) -> str:
    """Get formatted formula string"""
    return f"T = {a:.4f} / R + {b:.4f}"
