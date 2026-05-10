#!/usr/bin/env python3
"""
Unit tests for hyperbolic formula calculations and data quality warnings
"""

import sys
from pathlib import Path

# Add parent directory to path so we can import application modules
sys.path.insert(0, str(Path(__file__).parent.parent))

import random
import unittest
import numpy as np

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
        times_with_outlier[6] = times_with_outlier[6] + 80.0
        
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


class TestDataQualityWarnings(unittest.TestCase):
    """Test data quality detection for auto-fit warnings"""
    
    def setUp(self):
        self.a = 32.0
        self.b = 70.0
    
    def test_detect_duplicate_ratio_warning(self):
        """Test detection of duplicate ratios with large time variation"""
        ratios = [1.0, 1.0, 1.0, 1.1, 1.2]
        times = [100.0, 105.0, 110.0, 102.0, 98.0]
        
        ratio_time_map = {}
        duplicate_varies = False
        for r, t in zip(ratios, times):
            r_key = round(r, 3)
            if r_key in ratio_time_map:
                if abs(t - ratio_time_map[r_key]) > 5.0:
                    duplicate_varies = True
            else:
                ratio_time_map[r_key] = t
        
        self.assertTrue(duplicate_varies, "Should detect duplicate ratio with >5s variation")
    
    def test_no_warning_for_consistent_duplicates(self):
        """Test that consistent duplicate ratios don't trigger warning"""
        ratios = [1.0, 1.0, 1.0, 1.1, 1.2]
        times = [100.0, 100.2, 100.1, 102.0, 98.0]
        
        ratio_time_map = {}
        duplicate_varies = False
        for r, t in zip(ratios, times):
            r_key = round(r, 3)
            if r_key in ratio_time_map:
                if abs(t - ratio_time_map[r_key]) > 5.0:
                    duplicate_varies = True
            else:
                ratio_time_map[r_key] = t
        
        self.assertFalse(duplicate_varies, "Small variation should not trigger warning")
    
    def test_detect_narrow_ratio_range(self):
        """Test detection of narrow ratio range (<0.2)"""
        ratios = [1.0, 1.05, 1.1, 1.12, 1.15]
        min_ratio = min(ratios)
        max_ratio = max(ratios)
        ratio_range = max_ratio - min_ratio
        
        self.assertLess(ratio_range, 0.2, "Ratio range should be less than 0.2")
    
    def test_detect_wide_ratio_range(self):
        """Test that wide ratio range does not trigger warning"""
        ratios = [0.6, 0.8, 1.0, 1.2, 1.4, 1.6]
        min_ratio = min(ratios)
        max_ratio = max(ratios)
        ratio_range = max_ratio - min_ratio
        
        self.assertGreater(ratio_range, 0.2, "Ratio range should be greater than 0.2")
    
    def test_calculate_correlation_strong(self):
        """Test correlation calculation for strong correlation"""
        ratios_strong = [0.6, 0.8, 1.0, 1.2, 1.4, 1.6]
        times_strong = [123.33, 110.0, 102.0, 96.67, 92.86, 90.0]
        r_array = np.array(ratios_strong)
        t_array = np.array(times_strong)
        inv_r = 1.0 / np.maximum(r_array, 0.01)
        correlation_strong = np.corrcoef(inv_r, t_array)[0, 1]
        
        self.assertGreater(correlation_strong, 0.5, "Strong correlation should be >0.5")
    
    def test_calculate_correlation_weak(self):
        """Test correlation calculation for weak correlation"""
        ratios_weak = [1.0, 1.0, 1.0, 1.0, 1.0]
        times_weak = [95.0, 100.0, 102.0, 98.0, 105.0]
        r_array2 = np.array(ratios_weak)
        t_array2 = np.array(times_weak)
        inv_r2 = 1.0 / np.maximum(r_array2, 0.01)
        
        if len(set(inv_r2)) == 1:
            correlation_weak = 0.0
        else:
            correlation_weak = np.corrcoef(inv_r2, t_array2)[0, 1]
        
        self.assertLess(correlation_weak, 0.5, "Weak correlation should be <0.5")
    
    def test_quality_rating_good(self):
        """Test Good quality rating for low error"""
        avg_error = 0.5
        
        if avg_error > 3.0:
            rating = "Poor"
        elif avg_error > 1.5:
            rating = "Fair"
        else:
            rating = "Good"
        
        self.assertEqual(rating, "Good")
    
    def test_quality_rating_fair(self):
        """Test Fair quality rating for medium error"""
        avg_error = 2.0
        
        if avg_error > 3.0:
            rating = "Poor"
        elif avg_error > 1.5:
            rating = "Fair"
        else:
            rating = "Good"
        
        self.assertEqual(rating, "Fair")
    
    def test_quality_rating_poor(self):
        """Test Poor quality rating for high error"""
        avg_error = 4.0
        
        if avg_error > 3.0:
            rating = "Poor"
        elif avg_error > 1.5:
            rating = "Fair"
        else:
            rating = "Good"
        
        self.assertEqual(rating, "Poor")


class TestFitCurveWithQualityTracking(unittest.TestCase):
    """Test that fit_curve returns data needed for quality assessment"""
    
    def setUp(self):
        self.a = 32.0
        self.b = 70.0
    
    def test_fit_returns_avg_error(self):
        """Test that fit_curve returns average error"""
        ratios = [0.6, 0.8, 1.0, 1.2, 1.4, 1.6]
        times = [hyperbolic(r, self.a, self.b) for r in ratios]
        
        a, b, avg_err, max_err, info = fit_curve(ratios, times, verbose=False)
        
        self.assertIsNotNone(avg_err)
        self.assertLess(avg_err, 0.01)
    
    def test_fit_returns_max_error(self):
        """Test that fit_curve returns max error"""
        ratios = [0.6, 0.8, 1.0, 1.2, 1.4, 1.6]
        times = [hyperbolic(r, self.a, self.b) for r in ratios]
        
        a, b, avg_err, max_err, info = fit_curve(ratios, times, verbose=False)
        
        self.assertIsNotNone(max_err)
        self.assertLess(max_err, 0.01)
    
    def test_fit_with_noisy_data_returns_meaningful_errors(self):
        """Test that fit returns meaningful error metrics for noisy data"""
        random.seed(42)
        ratios = [0.6, 0.8, 1.0, 1.2, 1.4, 1.6]
        times = [hyperbolic(r, self.a, self.b) + random.uniform(-1.0, 1.0) for r in ratios]
        
        a, b, avg_err, max_err, info = fit_curve(ratios, times, verbose=False)
        
        self.assertIsNotNone(avg_err)
        self.assertIsNotNone(max_err)
        self.assertGreater(avg_err, 0)
        self.assertGreater(max_err, 0)


def run_formula_tests():
    """Run all formula tests"""
    print("\n" + "=" * 60)
    print("FORMULA TESTS")
    print("=" * 60)
    
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    suite.addTests(loader.loadTestsFromTestCase(TestFormula))
    suite.addTests(loader.loadTestsFromTestCase(TestDataQualityWarnings))
    suite.addTests(loader.loadTestsFromTestCase(TestFitCurveWithQualityTracking))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result


def run_formula_with_quality_tests():
    """Run formula tests including quality tracking"""
    print("\n" + "=" * 60)
    print("FORMULA WITH QUALITY TRACKING TESTS")
    print("=" * 60)
    
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    suite.addTests(loader.loadTestsFromTestCase(TestFormula))
    suite.addTests(loader.loadTestsFromTestCase(TestDataQualityWarnings))
    suite.addTests(loader.loadTestsFromTestCase(TestFitCurveWithQualityTracking))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result


if __name__ == "__main__":
    run_formula_tests()
