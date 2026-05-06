#!/usr/bin/env python3
"""
Unit tests for hyperbolic formula calculations
"""

import random
import unittest

from test_base import BaseTestCase
from core_formula import hyperbolic, ratio_from_time, fit_curve, DEFAULT_A_VALUE, get_formula_string, calculate_derived_values, OutlierInfo


class TestFormula(BaseTestCase):
    """Test hyperbolic formula calculations"""
    
    def test_hyperbolic_calculation(self):
        """Test hyperbolic function T = a / R + b"""
        a, b = 32.0, 70.0
        
        test_cases = [
            (0.6, 123.33333333333333),
            (0.8, 110.0),
            (1.0, 102.0),
            (1.2, 96.66666666666667),
            (1.4, 92.85714285714286),
            (1.6, 90.0),
        ]
        
        for R, expected_T in test_cases:
            T = hyperbolic(R, a, b)
            self.assertAlmostEqual(T, expected_T, places=5)
    
    def test_ratio_from_time(self):
        """Test calculating ratio from lap time"""
        a, b = 32.0, 70.0
        
        R = ratio_from_time(102.0, a, b)
        self.assertAlmostEqual(R, 1.0, places=5)
        
        R = ratio_from_time(110.0, a, b)
        self.assertAlmostEqual(R, 0.8, places=5)
        
        R = ratio_from_time(90.0, a, b)
        self.assertAlmostEqual(R, 1.6, places=5)
        
        invalid = ratio_from_time(70.0, a, b)
        self.assertIsNone(invalid)
        
        invalid = ratio_from_time(60.0, a, b)
        self.assertIsNone(invalid)
    
    def test_fit_curve(self):
        """Test curve fitting with sample data"""
        a, b = 32.0, 70.0
        ratios = [0.6, 0.8, 1.0, 1.2, 1.4, 1.6]
        times = [hyperbolic(r, a, b) for r in ratios]
        
        fitted_a, fitted_b, avg_err, max_err, info = fit_curve(ratios, times, verbose=False)
        
        self.assertIsNotNone(fitted_a)
        self.assertIsNotNone(fitted_b)
        self.assertAlmostEqual(fitted_a, a, delta=0.1)
        self.assertAlmostEqual(fitted_b, b, delta=0.1)
    
    def test_fit_curve_with_noise(self):
        """Test curve fitting with noisy data"""
        a, b = 32.0, 70.0
        ratios = [0.6, 0.8, 1.0, 1.2, 1.4, 1.6]
        times = [hyperbolic(r, a, b) for r in ratios]
        
        random.seed(42)
        times_noisy = [t + random.uniform(-0.5, 0.5) for t in times]
        
        fitted_a, fitted_b, avg_err, max_err, info = fit_curve(ratios, times_noisy, verbose=False)
        
        self.assertIsNotNone(fitted_a)
        self.assertIsNotNone(fitted_b)
        self.assertAlmostEqual(fitted_a, a, delta=5.0)
        self.assertAlmostEqual(fitted_b, b, delta=3.0)
    
    def test_fit_curve_insufficient_data(self):
        """Test curve fitting with insufficient data points"""
        a, b, avg_err, max_err, info = fit_curve([1.0], [100.0], verbose=False)
        self.assertIsNone(a)
        self.assertIsNone(b)
    
    def test_fit_curve_empty_data(self):
        """Test curve fitting with empty data"""
        a, b, avg_err, max_err, info = fit_curve([], [], verbose=False)
        self.assertIsNone(a)
        self.assertIsNone(b)
    
    def test_get_formula_string(self):
        """Test formula string formatting"""
        formula_str = get_formula_string(32.0, 70.0)
        self.assertEqual(formula_str, "T = 32.0000 / R + 70.0000")
    
    def test_calculate_derived_values(self):
        """Test derived values calculation"""
        M, k = calculate_derived_values(32.0, 70.0)
        self.assertAlmostEqual(M, 102.0)
        self.assertAlmostEqual(k, 32.0 / 102.0, places=5)
    
    def test_fit_curve_with_outlier_filtering_std(self):
        """Test curve fitting with std outlier filtering"""
        a, b = 32.0, 70.0
        ratios = [0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 1.1, 1.2, 1.3, 1.4, 1.5, 1.6]
        times = [hyperbolic(r, a, b) for r in ratios]
        times_with_outlier = times.copy()
        times_with_outlier[6] = times_with_outlier[6] + 50.0
        
        fitted_a, fitted_b, avg_err, max_err, info = fit_curve(
            ratios, times_with_outlier, verbose=False,
            outlier_method="std", outlier_threshold=2.0
        )
        
        self.assertIsNotNone(fitted_a)
        self.assertIsNotNone(fitted_b)
        self.assertIsNotNone(info)
        self.assertEqual(info.outliers_removed, 1)
    
    def test_fit_curve_with_outlier_filtering_percentile(self):
        """Test curve fitting with percentile outlier filtering"""
        a, b = 32.0, 70.0
        ratios = [0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 1.1, 1.2, 1.3, 1.4, 1.5, 1.6]
        times = [hyperbolic(r, a, b) for r in ratios]
        times_with_outlier = times.copy()
        times_with_outlier[6] = times_with_outlier[6] + 80.0  # Larger outlier
        
        fitted_a, fitted_b, avg_err, max_err, info = fit_curve(
            ratios, times_with_outlier, verbose=False,
            outlier_method="percentile", outlier_threshold=90.0
        )
        
        self.assertIsNotNone(fitted_a)
        self.assertIsNotNone(fitted_b)
        self.assertIsNotNone(info)
        self.assertEqual(info.outliers_removed, 1)
    
    def test_fit_curve_without_outlier_filtering(self):
        """Test curve fitting with outlier but no filtering"""
        a, b = 32.0, 70.0
        ratios = [0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 1.1, 1.2, 1.3, 1.4, 1.5, 1.6]
        times = [hyperbolic(r, a, b) for r in ratios]
        times_with_outlier = times.copy()
        times_with_outlier[6] = times_with_outlier[6] + 50.0
        
        fitted_a, fitted_b, avg_err, max_err, info = fit_curve(
            ratios, times_with_outlier, verbose=False,
            outlier_method="none"
        )
        
        self.assertIsNotNone(fitted_a)
        self.assertIsNotNone(fitted_b)
        self.assertIsNone(info)


if __name__ == "__main__":
    unittest.main()
