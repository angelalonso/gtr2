#!/usr/bin/env python3
"""
Formula module for hyperbolic curve calculations
T = a / R + b
Includes outlier detection and filtering
"""

import numpy as np
from typing import List, Tuple, Optional, Dict, Any
from dataclasses import dataclass

DEFAULT_A_VALUE = 32.0


@dataclass
class OutlierInfo:
    """Information about outliers detected in data"""
    total_points: int = 0
    outliers_removed: int = 0
    outliers: List[Tuple[float, float, float]] = None  # (ratio, lap_time, error)
    method_used: str = ""
    threshold_used: float = 0.0
    
    def __post_init__(self):
        if self.outliers is None:
            self.outliers = []


def hyperbolic(R: float, a: float, b: float) -> float:
    """Calculate lap time from ratio using hyperbolic formula"""
    if a <= 0 or R <= 0:
        return b
    return a / R + b


def ratio_from_time(T: float, a: float, b: float) -> Optional[float]:
    """
    Calculate ratio from lap time using hyperbolic formula.
    
    Returns None if:
    - a <= 0 (invalid parameter)
    - T <= b (would result in infinite or negative ratio)
    """
    if a <= 0:
        return None
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
    ratios = np.maximum(ratios, 0.01)
    times = a / ratios + b
    return ratios, times


def detect_outliers_std(
    ratios: List[float], 
    times: List[float], 
    a: float, 
    b: float, 
    std_multiplier: float = 2.0,
    min_points: int = 5
) -> Tuple[List[int], List[float], OutlierInfo]:
    """
    Detect outliers using standard deviation method.
    Points with error > mean + std_multiplier * std_dev are considered outliers.
    """
    if len(ratios) < min_points:
        return list(range(len(ratios))), [], OutlierInfo(
            total_points=len(ratios),
            outliers_removed=0,
            outliers=[],
            method_used="std",
            threshold_used=std_multiplier
        )
    
    predicted = [hyperbolic(r, a, b) for r in ratios]
    errors = [abs(t - p) for t, p in zip(times, predicted)]
    
    mean_error = np.mean(errors)
    std_error = np.std(errors)
    
    if std_error < 0.01:
        return list(range(len(ratios))), errors, OutlierInfo(
            total_points=len(ratios),
            outliers_removed=0,
            outliers=[],
            method_used="std",
            threshold_used=std_multiplier
        )
    
    threshold = mean_error + (std_multiplier * std_error)
    
    outlier_indices = [i for i, err in enumerate(errors) if err > threshold]
    outlier_info = []
    for i in outlier_indices:
        outlier_info.append((ratios[i], times[i], errors[i]))
    
    keep_indices = [i for i in range(len(ratios)) if i not in outlier_indices]
    
    return keep_indices, errors, OutlierInfo(
        total_points=len(ratios),
        outliers_removed=len(outlier_indices),
        outliers=outlier_info,
        method_used="std",
        threshold_used=std_multiplier
    )


def detect_outliers_iqr(
    ratios: List[float], 
    times: List[float], 
    a: float, 
    b: float, 
    iqr_multiplier: float = 1.5,
    min_points: int = 6
) -> Tuple[List[int], List[float], OutlierInfo]:
    """
    Detect outliers using Interquartile Range (IQR) method.
    """
    if len(ratios) < min_points:
        return list(range(len(ratios))), [], OutlierInfo(
            total_points=len(ratios),
            outliers_removed=0,
            outliers=[],
            method_used="iqr",
            threshold_used=iqr_multiplier
        )
    
    predicted = [hyperbolic(r, a, b) for r in ratios]
    errors = [abs(t - p) for t, p in zip(times, predicted)]
    
    errors_sorted = sorted(errors)
    q1_idx = int(len(errors_sorted) * 0.25)
    q3_idx = int(len(errors_sorted) * 0.75)
    
    q1 = errors_sorted[q1_idx]
    q3 = errors_sorted[q3_idx]
    iqr = q3 - q1
    
    if iqr < 0.01:
        return list(range(len(ratios))), errors, OutlierInfo(
            total_points=len(ratios),
            outliers_removed=0,
            outliers=[],
            method_used="iqr",
            threshold_used=iqr_multiplier
        )
    
    threshold = q3 + (iqr_multiplier * iqr)
    
    outlier_indices = [i for i, err in enumerate(errors) if err > threshold]
    outlier_info = []
    for i in outlier_indices:
        outlier_info.append((ratios[i], times[i], errors[i]))
    
    keep_indices = [i for i in range(len(ratios)) if i not in outlier_indices]
    
    return keep_indices, errors, OutlierInfo(
        total_points=len(ratios),
        outliers_removed=len(outlier_indices),
        outliers=outlier_info,
        method_used="iqr",
        threshold_used=iqr_multiplier
    )


def detect_outliers_percentile(
    ratios: List[float], 
    times: List[float], 
    a: float, 
    b: float, 
    percentile_threshold: float = 90.0,
    min_points: int = 4
) -> Tuple[List[int], List[float], OutlierInfo]:
    """
    Detect outliers using percentile method.
    """
    if len(ratios) < min_points:
        return list(range(len(ratios))), [], OutlierInfo(
            total_points=len(ratios),
            outliers_removed=0,
            outliers=[],
            method_used="percentile",
            threshold_used=percentile_threshold
        )
    
    predicted = [hyperbolic(r, a, b) for r in ratios]
    errors = [abs(t - p) for t, p in zip(times, predicted)]
    
    errors_sorted = sorted(errors)
    percentile_idx = int(len(errors_sorted) * (percentile_threshold / 100.0))
    if percentile_idx >= len(errors_sorted):
        percentile_idx = len(errors_sorted) - 1
    threshold = errors_sorted[percentile_idx]
    
    outlier_indices = [i for i, err in enumerate(errors) if err > threshold]
    outlier_info = []
    for i in outlier_indices:
        outlier_info.append((ratios[i], times[i], errors[i]))
    
    keep_indices = [i for i in range(len(ratios)) if i not in outlier_indices]
    
    return keep_indices, errors, OutlierInfo(
        total_points=len(ratios),
        outliers_removed=len(outlier_indices),
        outliers=outlier_info,
        method_used="percentile",
        threshold_used=percentile_threshold
    )


def filter_outliers(
    ratios: List[float],
    times: List[float],
    a: float,
    b: float,
    method: str = "std",
    threshold: float = 2.0,
    min_points: int = 4
) -> Tuple[List[float], List[float], OutlierInfo]:
    """
    Filter outliers from data points using specified method.
    """
    if len(ratios) < min_points or method == "none":
        return ratios, times, OutlierInfo(
            total_points=len(ratios),
            outliers_removed=0,
            outliers=[],
            method_used=method,
            threshold_used=threshold
        )
    
    if method == "std":
        keep_indices, errors, info = detect_outliers_std(ratios, times, a, b, threshold, min_points)
    elif method == "iqr":
        keep_indices, errors, info = detect_outliers_iqr(ratios, times, a, b, threshold, min_points)
    elif method == "percentile":
        keep_indices, errors, info = detect_outliers_percentile(ratios, times, a, b, threshold, min_points)
    else:
        return ratios, times, OutlierInfo(
            total_points=len(ratios),
            outliers_removed=0,
            outliers=[],
            method_used=method,
            threshold_used=threshold
        )
    
    filtered_ratios = [ratios[i] for i in keep_indices]
    filtered_times = [times[i] for i in keep_indices]
    
    return filtered_ratios, filtered_times, info


def fit_curve(
    ratios: List[float], 
    times: List[float], 
    verbose: bool = True,
    outlier_method: str = "none",
    outlier_threshold: float = 2.0,
    min_points_after_filtering: int = 2
) -> Tuple[Optional[float], Optional[float], Optional[float], Optional[float], Optional[OutlierInfo]]:
    """
    Fit hyperbolic curve to data points using least squares with optional outlier filtering.
    """
    print(f"\n  [fit_curve] CALLED with {len(ratios)} data points")
    
    if len(ratios) < 2:
        print(f"  [fit_curve] ERROR: Need at least 2 points, got {len(ratios)}")
        return None, None, None, None, None
    
    print(f"  [fit_curve] Data points:")
    for i, (r, t) in enumerate(zip(ratios, times)):
        print(f"    {i+1}: R={r:.6f}, T={t:.3f}")
    
    r_array = np.array(ratios)
    t_array = np.array(times)
    
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
    
    a_guess = max(a_guess, 1.0)
    b_guess = max(b_guess, 10.0)
    
    outlier_info = None
    filtered_ratios, filtered_times = ratios, times
    
    if outlier_method != "none" and len(ratios) >= 4:
        filtered_ratios, filtered_times, outlier_info = filter_outliers(
            ratios, times, a_guess, b_guess, outlier_method, outlier_threshold, min_points=4
        )
        
        if verbose and outlier_info and outlier_info.outliers_removed > 0:
            print(f"  [fit_curve] Outlier detection ({outlier_method}, threshold={outlier_threshold}):")
            print(f"    Total points: {outlier_info.total_points}")
            print(f"    Outliers removed: {outlier_info.outliers_removed}")
            for r, t, err in outlier_info.outliers:
                print(f"      Removed: R={r:.6f}, T={t:.3f}, error={err:.3f}s")
        
        if len(filtered_ratios) < min_points_after_filtering:
            print(f"  [fit_curve] After filtering, only {len(filtered_ratios)} points remain. Using original data.")
            filtered_ratios, filtered_times = ratios, times
            if outlier_info:
                outlier_info.outliers_removed = 0
                outlier_info.outliers = []
    
    if len(filtered_ratios) < 2:
        print(f"  [fit_curve] WARNING: Not enough points after filtering ({len(filtered_ratios)}), using original data")
        filtered_ratios, filtered_times = ratios, times
    
    r_filtered = np.array(filtered_ratios)
    t_filtered = np.array(filtered_times)
    
    def _hyperbolic(R, a, b):
        R_safe = np.maximum(R, 0.01)
        return a / R_safe + b
    
    try:
        from scipy.optimize import curve_fit
        
        print(f"  [fit_curve] Calling scipy.optimize.curve_fit with {len(filtered_ratios)} points...")
        popt, _ = curve_fit(_hyperbolic, r_filtered, t_filtered, p0=[a_guess, b_guess])
        a, b = popt
        
        a = max(a, 1.0)
        b = max(b, 10.0)
        
        print(f"  [fit_curve] curve_fit result: a={a:.6f}, b={b:.6f}")
        
        predictions = _hyperbolic(r_array, a, b)
        errors = np.abs(t_array - predictions)
        avg_error = float(np.mean(errors))
        max_error = float(np.max(errors))
        
        print(f"  [fit_curve] Fit complete: {get_formula_string(a, b)}")
        print(f"  [fit_curve] Avg error: {avg_error:.4f}s, Max error: {max_error:.4f}s")
        
        for i, (r, t, pred, err) in enumerate(zip(ratios, times, predictions, errors)):
            print(f"    Point {i+1}: predicted T={pred:.3f}s, error={err:.3f}s")
        
        return a, b, avg_error, max_error, outlier_info
        
    except Exception as e:
        print(f"  [fit_curve] EXCEPTION: {e}")
        import traceback
        traceback.print_exc()
        return None, None, None, None, outlier_info


def calculate_derived_values(a: float, b: float) -> Tuple[float, float]:
    """Calculate derived values: M (time at R=1.0) and k (steepness)"""
    M = a + b
    k = a / M if M > 0 else 0
    return M, k


def get_formula_string(a: float, b: float) -> str:
    """Get formatted formula string"""
    return f"T = {a:.4f} / R + {b:.4f}"
