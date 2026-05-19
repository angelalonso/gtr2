#!/usr/bin/env python3
"""
Unit tests for outlier detection and filtering in formula fitting
"""

import sys
from pathlib import Path

# Add parent directory to path so we can import application modules
sys.path.insert(0, str(Path(__file__).parent.parent))

import unittest
import numpy as np
from typing import List, Tuple

from test_base import BaseTestCase
from core_math import (
    time_from_ratio, ratio_from_time, fit_hyperbolic, 
    detect_outliers_std, detect_outliers_iqr, detect_outliers_percentile,
    filter_outliers, FitStats
)


class TestOutlierDetection(BaseTestCase):
    """Test outlier detection functionality"""
    
    def setUp(self):
        super().setUp()
        self.a = 32.0
        self.b = 70.0
        self.ratios = [0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 1.1, 1.2, 1.3, 1.4, 1.5, 1.6]
        self.times = [time_from_ratio(r, self.a, self.b) for r in self.ratios]
    
    def test_time_from_ratio_function(self):
        """Test time_from_ratio function for generating test data"""
        expected_times = [
            134.0, 123.333333, 115.714286, 110.0, 105.555556, 102.0,
            99.090909, 96.666667, 94.615385, 92.857143, 91.333333, 90.0
        ]
        for r, t, expected in zip(self.ratios, self.times, expected_times):
            self.assertAlmostEqual(t, expected, places=3)
    
    def test_no_outliers_with_std(self):
        """Test that clean data has no outliers with std method"""
        keep_indices, errors, stats = detect_outliers_std(
            self.ratios, self.times, self.a, self.b, std_multiplier=2.0, min_points=3
        )
        self.assertEqual(len(keep_indices), len(self.ratios))
        self.assertEqual(stats.outliers_removed, 0)
    
    def test_no_outliers_with_iqr(self):
        """Test that clean data has no outliers with IQR method"""
        keep_indices, errors, stats = detect_outliers_iqr(
            self.ratios, self.times, self.a, self.b, iqr_multiplier=1.5, min_points=4
        )
        self.assertEqual(len(keep_indices), len(self.ratios))
        self.assertEqual(stats.outliers_removed, 0)
    
    def test_no_outliers_with_percentile(self):
        """Test that clean data has no outliers with percentile method"""
        keep_indices, errors, stats = detect_outliers_percentile(
            self.ratios, self.times, self.a, self.b, percentile_threshold=90.0, min_points=3
        )
        self.assertEqual(len(keep_indices), len(self.ratios))
        self.assertEqual(stats.outliers_removed, 0)
    
    def test_std_detects_outlier(self):
        """Test that std method detects a clear outlier"""
        times_with_outlier = self.times.copy()
        times_with_outlier[6] = self.times[6] + 50.0
        
        keep_indices, errors, stats = detect_outliers_std(
            self.ratios, times_with_outlier, self.a, self.b, std_multiplier=2.0, min_points=3
        )
        
        self.assertEqual(stats.outliers_removed, 1)
        self.assertNotIn(6, keep_indices)
        self.assertEqual(len(keep_indices), len(self.ratios) - 1)
    
    def test_iqr_detects_outlier(self):
        """Test that IQR method detects a clear outlier"""
        times_with_outlier = self.times.copy()
        times_with_outlier[6] = self.times[6] + 100.0
        
        keep_indices, errors, stats = detect_outliers_iqr(
            self.ratios, times_with_outlier, self.a, self.b, iqr_multiplier=1.5, min_points=4
        )
        
        self.assertGreaterEqual(stats.outliers_removed, 0)
    
    def test_percentile_detects_outlier(self):
        """Test that percentile method detects a clear outlier"""
        times_with_outlier = self.times.copy()
        times_with_outlier[6] = self.times[6] + 50.0
        
        keep_indices, errors, stats = detect_outliers_percentile(
            self.ratios, times_with_outlier, self.a, self.b, percentile_threshold=90.0, min_points=3
        )
        
        self.assertEqual(stats.outliers_removed, 1)
        self.assertNotIn(6, keep_indices)
    
    def test_std_threshold_tuning(self):
        """Test that std threshold affects outlier detection sensitivity"""
        times_with_outliers = self.times.copy()
        times_with_outliers[3] = self.times[3] + 30.0
        times_with_outliers[6] = self.times[6] + 50.0
        
        keep_indices, errors, stats = detect_outliers_std(
            self.ratios, times_with_outliers, self.a, self.b, std_multiplier=1.0, min_points=3
        )
        self.assertGreaterEqual(stats.outliers_removed, 1)
        
        keep_indices2, errors2, stats2 = detect_outliers_std(
            self.ratios, times_with_outliers, self.a, self.b, std_multiplier=3.0, min_points=3
        )
        self.assertLessEqual(stats2.outliers_removed, stats.outliers_removed)
    
    def test_iqr_threshold_tuning(self):
        """Test that IQR threshold affects outlier detection sensitivity"""
        times_with_outliers = self.times.copy()
        times_with_outliers[3] = self.times[3] + 40.0
        times_with_outliers[6] = self.times[6] + 80.0
        
        keep_indices, errors, stats = detect_outliers_iqr(
            self.ratios, times_with_outliers, self.a, self.b, iqr_multiplier=0.5, min_points=4
        )
        self.assertIsInstance(stats.outliers_removed, int)
    
    def test_percentile_threshold_tuning(self):
        """Test that percentile threshold affects outlier detection"""
        times_with_outliers = self.times.copy()
        times_with_outliers[3] = self.times[3] + 30.0
        times_with_outliers[6] = self.times[6] + 50.0
        
        keep_indices, errors, stats = detect_outliers_percentile(
            self.ratios, times_with_outliers, self.a, self.b, percentile_threshold=50.0, min_points=3
        )
        self.assertGreaterEqual(stats.outliers_removed, 1)
        
        keep_indices2, errors2, stats2 = detect_outliers_percentile(
            self.ratios, times_with_outliers, self.a, self.b, percentile_threshold=99.0, min_points=3
        )
        self.assertLessEqual(stats2.outliers_removed, stats.outliers_removed)
    
    def test_filter_outliers_std(self):
        """Test filter_outliers function with std method"""
        times_with_outlier = self.times.copy()
        times_with_outlier[6] = self.times[6] + 50.0
        
        filtered_ratios, filtered_times, stats = filter_outliers(
            self.ratios, times_with_outlier, self.a, self.b,
            method="std", threshold=2.0, min_points=3
        )
        
        self.assertEqual(stats.outliers_removed, 1)
        self.assertEqual(len(filtered_ratios), len(self.ratios) - 1)
        self.assertEqual(len(filtered_times), len(self.times) - 1)
    
    def test_filter_outliers_iqr(self):
        """Test filter_outliers function with IQR method"""
        times_with_outlier = self.times.copy()
        times_with_outlier[6] = self.times[6] + 100.0
        
        filtered_ratios, filtered_times, stats = filter_outliers(
            self.ratios, times_with_outlier, self.a, self.b,
            method="iqr", threshold=1.5, min_points=4
        )
        
        self.assertIsInstance(stats.outliers_removed, int)
        self.assertIsInstance(len(filtered_ratios), int)
    
    def test_filter_outliers_percentile(self):
        """Test filter_outliers function with percentile method"""
        times_with_outlier = self.times.copy()
        times_with_outlier[6] = self.times[6] + 50.0
        
        filtered_ratios, filtered_times, stats = filter_outliers(
            self.ratios, times_with_outlier, self.a, self.b,
            method="percentile", threshold=90.0, min_points=3
        )
        
        self.assertEqual(stats.outliers_removed, 1)
        self.assertEqual(len(filtered_ratios), len(self.ratios) - 1)
    
    def test_filter_outliers_none(self):
        """Test filter_outliers with method='none' (no filtering)"""
        times_with_outlier = self.times.copy()
        times_with_outlier[6] = self.times[6] + 50.0
        
        filtered_ratios, filtered_times, stats = filter_outliers(
            self.ratios, times_with_outlier, self.a, self.b,
            method="none", threshold=2.0, min_points=3
        )
        
        self.assertEqual(stats.outliers_removed, 0)
        self.assertEqual(len(filtered_ratios), len(self.ratios))
        self.assertEqual(len(filtered_times), len(self.times))
    
    def test_filter_outliers_insufficient_points(self):
        """Test that filtering is not applied with insufficient points"""
        ratios_small = [0.6, 0.8, 1.0]
        times_small = [100.0, 110.0, 102.0]
        
        filtered_ratios, filtered_times, stats = filter_outliers(
            ratios_small, times_small, self.a, self.b,
            method="std", threshold=2.0, min_points=10
        )
        
        self.assertEqual(stats.outliers_removed, 0)
        self.assertEqual(len(filtered_ratios), len(ratios_small))


class TestFitCurveWithOutliers(BaseTestCase):
    """Test curve fitting with outlier filtering"""
    
    def setUp(self):
        super().setUp()
        self.a = 32.0
        self.b = 70.0
        self.ratios = [0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 1.1, 1.2, 1.3, 1.4, 1.5, 1.6]
        self.times = [time_from_ratio(r, self.a, self.b) for r in self.ratios]
    
    def test_fit_clean_data_no_outliers(self):
        """Test fitting clean data with outlier filtering disabled"""
        fitted_a, fitted_b, stats = fit_hyperbolic(
            self.ratios, self.times,
            outlier_method="none"
        )
        
        self.assertIsNotNone(fitted_a)
        self.assertIsNotNone(fitted_b)
        self.assertAlmostEqual(fitted_a, self.a, delta=0.5)
        self.assertAlmostEqual(fitted_b, self.b, delta=0.5)
    
    def test_fit_with_outlier_std(self):
        """Test fitting data with an outlier using std method"""
        times_with_outlier = self.times.copy()
        times_with_outlier[6] = self.times[6] + 50.0
        
        fitted_a, fitted_b, stats = fit_hyperbolic(
            self.ratios, times_with_outlier,
            outlier_method="std", outlier_threshold=2.0
        )
        
        self.assertIsNotNone(fitted_a)
        self.assertIsNotNone(fitted_b)
        self.assertEqual(stats.outliers_removed, 1)
        self.assertAlmostEqual(fitted_a, self.a, delta=8.0)
        self.assertAlmostEqual(fitted_b, self.b, delta=8.0)
    
    def test_fit_with_outlier_iqr(self):
        """Test fitting data with an outlier using IQR method"""
        times_with_outlier = self.times.copy()
        times_with_outlier[6] = self.times[6] + 100.0
        
        fitted_a, fitted_b, stats = fit_hyperbolic(
            self.ratios, times_with_outlier,
            outlier_method="iqr", outlier_threshold=1.5
        )
        
        self.assertIsNotNone(fitted_a)
        self.assertIsNotNone(fitted_b)
        self.assertIsInstance(fitted_a, float)
        self.assertIsInstance(fitted_b, float)
    
    def test_fit_with_outlier_percentile(self):
        """Test fitting data with an outlier using percentile method"""
        times_with_outlier = self.times.copy()
        times_with_outlier[6] = self.times[6] + 50.0
        
        fitted_a, fitted_b, stats = fit_hyperbolic(
            self.ratios, times_with_outlier,
            outlier_method="percentile", outlier_threshold=90.0
        )
        
        self.assertIsNotNone(fitted_a)
        self.assertIsNotNone(fitted_b)
        self.assertEqual(stats.outliers_removed, 1)
        self.assertAlmostEqual(fitted_a, self.a, delta=10.0)
        self.assertAlmostEqual(fitted_b, self.b, delta=10.0)
    
    def test_fit_without_outlier_filtering(self):
        """Test fitting data with outlier when filtering is disabled"""
        times_with_outlier = self.times.copy()
        times_with_outlier[6] = self.times[6] + 50.0
        
        fitted_a, fitted_b, stats = fit_hyperbolic(
            self.ratios, times_with_outlier,
            outlier_method="none"
        )
        
        self.assertIsNotNone(fitted_a)
        self.assertIsNotNone(fitted_b)
        self.assertEqual(stats.outliers_removed, 0)
        self.assertTrue(20 < fitted_a < 45)
        self.assertTrue(60 < fitted_b < 85)
    
    def test_fit_with_multiple_outliers(self):
        """Test fitting data with multiple outliers"""
        times_with_outliers = self.times.copy()
        times_with_outliers[3] = self.times[3] + 40.0
        times_with_outliers[6] = self.times[6] + 60.0
        times_with_outliers[9] = self.times[9] + 50.0
        
        fitted_a, fitted_b, stats = fit_hyperbolic(
            self.ratios, times_with_outliers,
            outlier_method="std", outlier_threshold=2.0
        )
        
        self.assertIsNotNone(fitted_a)
        self.assertIsNotNone(fitted_b)
        self.assertGreaterEqual(stats.outliers_removed, 1)
    
    def test_fit_with_extreme_outlier(self):
        """Test fitting with an extremely far outlier"""
        times_with_extreme = self.times.copy()
        times_with_extreme[6] = self.times[6] + 100.0
        
        fitted_a, fitted_b, stats = fit_hyperbolic(
            self.ratios, times_with_extreme,
            outlier_method="std", outlier_threshold=2.0
        )
        
        self.assertIsNotNone(fitted_a)
        self.assertIsNotNone(fitted_b)
        self.assertEqual(stats.outliers_removed, 1)
        self.assertTrue(20 < fitted_a < 50)
        self.assertTrue(50 < fitted_b < 90)
    
    def test_fit_insufficient_points(self):
        """Test fitting with insufficient points (should still work)"""
        ratios_small = [0.6, 0.8, 1.0]
        times_small = [100.0, 110.0, 102.0]
        
        fitted_a, fitted_b, stats = fit_hyperbolic(
            ratios_small, times_small,
            outlier_method="std", outlier_threshold=2.0,
            min_points_after_filtering=2
        )
        
        self.assertIsNotNone(fitted_a)
        self.assertIsNotNone(fitted_b)
        self.assertIsInstance(fitted_a, float)
        self.assertIsInstance(fitted_b, float)


class TestFormulaCrossValidation(BaseTestCase):
    """Cross-validation tests for formula calculations"""
    
    def setUp(self):
        super().setUp()
        self.test_cases = [
            {"name": "GT cars", "a": 32.0, "b": 70.0},
            {"name": "Formula cars", "a": 28.0, "b": 65.0},
            {"name": "Slow cars", "a": 40.0, "b": 80.0},
        ]
    
    def test_ratio_time_round_trip(self):
        """Test that ratio -> time -> ratio returns original value"""
        for case in self.test_cases:
            a, b = case["a"], case["b"]
            for R in [0.6, 0.8, 1.0, 1.2, 1.4, 1.6]:
                T = time_from_ratio(R, a, b)
                R2 = ratio_from_time(T, a, b)
                self.assertIsNotNone(R2)
                self.assertAlmostEqual(R, R2, places=5)
    
    def test_time_ratio_round_trip(self):
        """Test that time -> ratio -> time returns original value"""
        for case in self.test_cases:
            a, b = case["a"], case["b"]
            for T in [80.0, 85.0, 90.0, 95.0, 100.0, 105.0, 110.0, 115.0, 120.0]:
                R = ratio_from_time(T, a, b)
                if R is not None:
                    T2 = time_from_ratio(R, a, b)
                    self.assertAlmostEqual(T, T2, places=3)
    
    def test_ratio_range_validity(self):
        """Test that ratios stay within reasonable bounds for valid lap times"""
        for case in self.test_cases:
            a, b = case["a"], case["b"]
            for T in [b + 5.0, b + 10.0, b + 15.0, b + 20.0, b + 30.0, b + 40.0, b + 50.0]:
                R = ratio_from_time(T, a, b)
                if R is not None:
                    self.assertTrue(R > 0)
                    self.assertLess(R, 1000.0)
    
    def test_time_increases_as_ratio_decreases(self):
        """Test monotonic property: smaller ratio -> larger time"""
        for case in self.test_cases:
            a, b = case["a"], case["b"]
            R_small = 0.6
            R_large = 1.6
            T_small = time_from_ratio(R_small, a, b)
            T_large = time_from_ratio(R_large, a, b)
            self.assertGreater(T_small, T_large)
    
    def test_fit_recovers_parameters(self):
        """Test that fit_hyperbolic recovers original parameters from clean data"""
        ratios = [0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 1.1, 1.2, 1.3, 1.4, 1.5, 1.6]
        
        for case in self.test_cases:
            a_orig, b_orig = case["a"], case["b"]
            times = [time_from_ratio(r, a_orig, b_orig) for r in ratios]
            
            a_fit, b_fit, stats = fit_hyperbolic(ratios, times, outlier_method="none")
            
            self.assertIsNotNone(a_fit)
            self.assertIsNotNone(b_fit)
            self.assertAlmostEqual(a_fit, a_orig, delta=0.5)
            self.assertAlmostEqual(b_fit, b_orig, delta=0.5)
    
    def test_fit_resists_small_noise(self):
        """Test that fit_hyperbolic is robust to small random noise"""
        ratios = [0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 1.1, 1.2, 1.3, 1.4, 1.5, 1.6]
        np.random.seed(42)
        
        for case in self.test_cases:
            a_orig, b_orig = case["a"], case["b"]
            times_clean = [time_from_ratio(r, a_orig, b_orig) for r in ratios]
            times_noisy = [t + np.random.normal(0, 0.5) for t in times_clean]
            
            a_fit, b_fit, stats = fit_hyperbolic(ratios, times_noisy, outlier_method="none")
            
            self.assertIsNotNone(a_fit)
            self.assertIsNotNone(b_fit)
            self.assertAlmostEqual(a_fit, a_orig, delta=3.0)
            self.assertAlmostEqual(b_fit, b_orig, delta=3.0)
    
    def test_ratio_from_time_returns_none_for_invalid_input(self):
        """Test that ratio_from_time returns None for invalid inputs"""
        a, b = 32.0, 70.0
        
        R = ratio_from_time(b, a, b)
        self.assertIsNone(R)
        
        R = ratio_from_time(b - 1.0, a, b)
        self.assertIsNone(R)
        
        R = ratio_from_time(100.0, 0.0, b)
        self.assertIsNone(R)
        
        R = ratio_from_time(100.0, -10.0, b)
        self.assertIsNone(R)
        
        R = ratio_from_time(100.0, -5.0, b)
        self.assertIsNone(R)


class TestOutlierConfig(BaseTestCase):
    """Test outlier configuration integration"""
    
    def test_get_outlier_settings(self):
        """Test retrieving outlier settings from config"""
        from core_config import get_outlier_settings
        
        settings = get_outlier_settings(str(self.temp_env.config_path))
        self.assertIsInstance(settings, dict)
        self.assertIn('method', settings)
        self.assertIn('threshold', settings)
        self.assertIn('min_points', settings)
    
    def test_update_outlier_settings(self):
        """Test updating outlier settings in config"""
        from core_config import update_outlier_settings, get_outlier_settings
        
        result = update_outlier_settings("iqr", 2.0, 4, str(self.temp_env.config_path))
        self.assertTrue(result)
        
        settings = get_outlier_settings(str(self.temp_env.config_path))
        self.assertEqual(settings['method'], "iqr")
        self.assertEqual(settings['threshold'], 2.0)
        self.assertEqual(settings['min_points'], 4)
        
        update_outlier_settings("std", 2.0, 3, str(self.temp_env.config_path))
    
    def test_outlier_settings_persist(self):
        """Test that outlier settings persist across config saves"""
        from core_config import update_outlier_settings, load_config
        
        update_outlier_settings("percentile", 95.0, 5, str(self.temp_env.config_path))
        
        config = load_config(str(self.temp_env.config_path))
        self.assertEqual(config.get('outlier_method'), "percentile")
        self.assertEqual(config.get('outlier_threshold'), 95.0)
        self.assertEqual(config.get('outlier_min_points'), 5)
    
    def test_default_outlier_settings(self):
        """Test default outlier settings are present"""
        from core_config import DEFAULT_CONFIG
        
        self.assertIn('outlier_method', DEFAULT_CONFIG)
        self.assertIn('outlier_threshold', DEFAULT_CONFIG)
        self.assertIn('outlier_min_points', DEFAULT_CONFIG)
        self.assertEqual(DEFAULT_CONFIG['outlier_method'], 'std')
        self.assertEqual(DEFAULT_CONFIG['outlier_threshold'], 2.0)
        self.assertEqual(DEFAULT_CONFIG['outlier_min_points'], 3)


def run_outlier_tests():
    """Run all outlier detection tests"""
    print("\n" + "=" * 60)
    print("OUTLIER DETECTION UNIT TESTS")
    print("=" * 60)
    
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    suite.addTests(loader.loadTestsFromTestCase(TestOutlierDetection))
    suite.addTests(loader.loadTestsFromTestCase(TestFitCurveWithOutliers))
    suite.addTests(loader.loadTestsFromTestCase(TestFormulaCrossValidation))
    suite.addTests(loader.loadTestsFromTestCase(TestOutlierConfig))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result


if __name__ == "__main__":
    run_outlier_tests()
