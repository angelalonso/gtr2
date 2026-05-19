#!/usr/bin/env python3
"""
Formula module for hyperbolic curve calculations
T = a / R + b
Includes outlier detection and filtering

This module is now a wrapper around core_math for backward compatibility.
New code should import from core_math directly.
"""

import numpy as np
from typing import List, Tuple, Optional, Dict, Any
from dataclasses import dataclass

# Re-export everything from core_math
from core_math import (
    DEFAULT_A_VALUE,
    hyperbolic as hyperbolic_impl,
    ratio_from_time as ratio_from_time_impl,
    predict_ratios,
    predict_times,
    get_curve_points,
    detect_outliers_std,
    detect_outliers_iqr,
    detect_outliers_percentile,
    filter_outliers,
    fit_curve as fit_curve_impl,
    calculate_derived_values,
    get_formula_string,
    OutlierInfo
)

# For backward compatibility, provide the same function signatures
def hyperbolic(R: float, a: float, b: float) -> float:
    """Calculate lap time from ratio using hyperbolic formula"""
    return hyperbolic_impl(R, a, b)


def ratio_from_time(T: float, a: float, b: float) -> Optional[float]:
    """Calculate ratio from lap time using hyperbolic formula"""
    return ratio_from_time_impl(T, a, b)


@dataclass
class OutlierInfo:
    """Information about outliers detected in data"""
    total_points: int = 0
    outliers_removed: int = 0
    outliers: List[Tuple[float, float, float]] = None
    method_used: str = ""
    threshold_used: float = 0.0
    
    def __post_init__(self):
        if self.outliers is None:
            self.outliers = []


def fit_curve(
    ratios: List[float], 
    times: List[float], 
    verbose: bool = True,
    outlier_method: str = "none",
    outlier_threshold: float = 2.0,
    min_points_after_filtering: int = 2
) -> Tuple[Optional[float], Optional[float], Optional[float], Optional[float], Optional[OutlierInfo]]:
    """
    Fit hyperbolic curve to data points with optional outlier filtering.
    Wrapper around core_math.fit_hyperbolic for backward compatibility.
    """
    from core_math import fit_hyperbolic, FitStats
    
    a, b, stats = fit_hyperbolic(
        ratios, times,
        fixed_a=None,
        outlier_method=outlier_method,
        outlier_threshold=outlier_threshold,
        min_points_after_filtering=min_points_after_filtering
    )
    
    if verbose and stats.outliers_removed > 0:
        print(f"Outlier detection ({outlier_method}, threshold={outlier_threshold}):")
        print(f"  Total points: {len(ratios)}")
        print(f"  Outliers removed: {stats.outliers_removed}")
    
    # Convert FitStats to OutlierInfo for backward compatibility
    outlier_info = OutlierInfo(
        total_points=len(ratios),
        outliers_removed=stats.outliers_removed,
        outliers=[],
        method_used=outlier_method,
        threshold_used=outlier_threshold
    )
    
    if a is None or b is None:
        return None, None, None, None, outlier_info
    
    return a, b, stats.avg_error, stats.max_error, outlier_info
