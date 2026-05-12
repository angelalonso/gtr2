#!/usr/bin/env python3
"""
Comprehensive unit tests for ratio calculation logic
Tests median calculation with multiple user laptimes and sequential updates
"""

import sys
from pathlib import Path

# Add parent directory to path so we can import application modules
sys.path.insert(0, str(Path(__file__).parent.parent))

import unittest
import statistics
import tempfile
import json
from typing import List, Tuple, Optional
from dataclasses import dataclass
from unittest.mock import MagicMock, patch

from test_base import BaseTestCase
from core_database import CurveDatabase
from core_formula import hyperbolic, ratio_from_time, fit_curve


@dataclass
class RatioCalculationResult:
    """Result of a ratio calculation test"""
    scenario_name: str
    user_laptimes: List[float]
    ai_laptimes: List[float]
    expected_ratio: float
    actual_ratio: Optional[float] = None
    median_user_time: Optional[float] = None
    median_ai_time: Optional[float] = None
    calculated_ratio: Optional[float] = None
    passed: bool = False
    error_message: str = ""


class TestRatioCalculation(BaseTestCase):
    """Test ratio calculation from user and AI laptimes"""
    
    def setUp(self):
        super().setUp()
        self.db_path = self.temp_env.test_data_dir / "ratio_test.db"
        self.db = CurveDatabase(str(self.db_path))
    
    def calculate_ratio_from_times(self, user_times: List[float], ai_times: List[float]) -> Optional[float]:
        """
        Calculate ratio from user and AI laptimes.
        This simulates the core logic: ratio = median_user_time / median_ai_time
        """
        if not user_times or not ai_times:
            return None
        
        median_user = statistics.median(user_times)
        median_ai = statistics.median(ai_times)
        
        if median_ai <= 0:
            return None
        
        return median_user / median_ai
    
    def test_single_user_single_ai(self):
        """Test ratio with single user lap and single AI lap"""
        user_times = [90.0]
        ai_times = [100.0]
        
        ratio = self.calculate_ratio_from_times(user_times, ai_times)
        
        self.assertIsNotNone(ratio)
        self.assertAlmostEqual(ratio, 0.9, places=3)
    
    def test_multiple_user_laptimes_odd_count(self):
        """Test ratio with odd number of user laptimes (median is middle value)"""
        user_times = [85.0, 90.0, 95.0]  # Median = 90.0
        ai_times = [100.0, 100.0, 100.0]  # Median = 100.0
        
        ratio = self.calculate_ratio_from_times(user_times, ai_times)
        
        self.assertIsNotNone(ratio)
        self.assertAlmostEqual(ratio, 0.9, places=3)  # 90.0 / 100.0 = 0.9
    
    def test_multiple_user_laptimes_even_count(self):
        """Test ratio with even number of user laptimes (median is average of two middle)"""
        user_times = [85.0, 88.0, 92.0, 95.0]  # Median = (88.0 + 92.0) / 2 = 90.0
        ai_times = [100.0, 100.0, 100.0, 100.0]  # Median = 100.0
        
        ratio = self.calculate_ratio_from_times(user_times, ai_times)
        
        self.assertIsNotNone(ratio)
        self.assertAlmostEqual(ratio, 0.9, places=3)
    
    def test_multiple_ai_laptimes(self):
        """Test ratio with multiple AI laptimes"""
        user_times = [90.0, 90.0, 90.0]
        ai_times = [95.0, 100.0, 105.0]  # Median = 100.0
        
        ratio = self.calculate_ratio_from_times(user_times, ai_times)
        
        self.assertIsNotNone(ratio)
        self.assertAlmostEqual(ratio, 0.9, places=3)
    
    def test_ratio_with_outliers_user_times(self):
        """Test that ratio calculation is robust to outlier user times (uses median)"""
        user_times = [80.0, 90.0, 100.0, 110.0, 200.0]  # Outlier at 200
        # Median of user_times = 100.0 (not 116.0 which would be mean)
        ai_times = [100.0, 100.0, 100.0, 100.0, 100.0]
        
        ratio = self.calculate_ratio_from_times(user_times, ai_times)
        
        self.assertIsNotNone(ratio)
        self.assertAlmostEqual(ratio, 1.0, places=3)  # 100.0 / 100.0 = 1.0
    
    def test_ratio_with_outliers_ai_times(self):
        """Test that ratio calculation is robust to outlier AI times (uses median)"""
        user_times = [100.0, 100.0, 100.0, 100.0, 100.0]
        ai_times = [90.0, 95.0, 100.0, 105.0, 200.0]  # Outlier at 200
        # Median of ai_times = 100.0 (not 118.0 which would be mean)
        
        ratio = self.calculate_ratio_from_times(user_times, ai_times)
        
        self.assertIsNotNone(ratio)
        self.assertAlmostEqual(ratio, 1.0, places=3)  # 100.0 / 100.0 = 1.0
    
    def test_ratio_with_both_outliers(self):
        """Test ratio with outliers on both sides"""
        user_times = [80.0, 90.0, 100.0, 110.0, 300.0]
        ai_times = [85.0, 95.0, 100.0, 105.0, 250.0]
        # Median user = 100.0, Median AI = 100.0
        
        ratio = self.calculate_ratio_from_times(user_times, ai_times)
        
        self.assertIsNotNone(ratio)
        self.assertAlmostEqual(ratio, 1.0, places=3)
    
    def test_ratio_with_varying_data_points(self):
        """Test ratio with varying number of data points (2 vs 5)"""
        user_times = [88.0, 92.0]  # Median = 90.0
        ai_times = [95.0, 98.0, 100.0, 102.0, 105.0]  # Median = 100.0
        
        ratio = self.calculate_ratio_from_times(user_times, ai_times)
        
        self.assertIsNotNone(ratio)
        self.assertAlmostEqual(ratio, 0.9, places=3)
    
    def test_empty_user_times(self):
        """Test ratio calculation with no user times"""
        user_times = []
        ai_times = [100.0, 100.0, 100.0]
        
        ratio = self.calculate_ratio_from_times(user_times, ai_times)
        
        self.assertIsNone(ratio)
    
    def test_empty_ai_times(self):
        """Test ratio calculation with no AI times"""
        user_times = [90.0, 90.0, 90.0]
        ai_times = []
        
        ratio = self.calculate_ratio_from_times(user_times, ai_times)
        
        self.assertIsNone(ratio)


class TestSequentialRatioUpdates(BaseTestCase):
    """Test how ratio changes as new laptimes are added sequentially"""
    
    def setUp(self):
        super().setUp()
        self.db_path = self.temp_env.test_data_dir / "sequential_test.db"
        self.db = CurveDatabase(str(self.db_path))
    
    def calculate_ratio_from_times(self, user_times: List[float], ai_times: List[float]) -> Optional[float]:
        """Helper to calculate ratio from times"""
        if not user_times or not ai_times:
            return None
        median_user = statistics.median(user_times)
        median_ai = statistics.median(ai_times)
        if median_ai <= 0:
            return None
        return median_user / median_ai
    
    def test_sequential_updates_converging(self):
        """Test that ratio converges as more data points are added"""
        # Start with limited data
        user_times_1 = [90.0]
        ai_times_1 = [100.0]
        ratio_1 = self.calculate_ratio_from_times(user_times_1, ai_times_1)
        
        # Add more data that supports the same ratio
        user_times_2 = [90.0, 89.0, 91.0]
        ai_times_2 = [100.0, 99.0, 101.0]
        ratio_2 = self.calculate_ratio_from_times(user_times_2, ai_times_2)
        
        # Ratio should remain similar
        self.assertAlmostEqual(ratio_1, 0.9, places=3)
        self.assertAlmostEqual(ratio_2, 0.9, places=3)
        self.assertAlmostEqual(ratio_1, ratio_2, places=2)
    
    def test_sequential_updates_drifting(self):
        """Test ratio changes as user improves over time"""
        # Initial slower laps
        user_times_1 = [100.0, 102.0, 98.0]
        ai_times_1 = [100.0, 100.0, 100.0]
        ratio_1 = self.calculate_ratio_from_times(user_times_1, ai_times_1)
        
        # User improves significantly
        # Sorted user_times_2: [84, 85, 86, 98, 100, 102] -> median = (86 + 98) / 2 = 92.0
        user_times_2 = [100.0, 102.0, 98.0, 85.0, 86.0, 84.0]
        ai_times_2 = [100.0, 100.0, 100.0, 100.0, 100.0, 100.0]
        ratio_2 = self.calculate_ratio_from_times(user_times_2, ai_times_2)
        
        # Ratio should decrease (user is faster)
        self.assertGreater(ratio_1, ratio_2)
        self.assertAlmostEqual(ratio_1, 1.0, places=1)
        # The correct median is 92.0, so ratio = 92.0 / 100.0 = 0.92
        self.assertAlmostEqual(ratio_2, 0.92, places=2)
    
    def test_sequential_updates_with_new_slower_laps(self):
        """Test ratio changes when user becomes slower"""
        # Initial fast laps
        user_times_1 = [85.0, 86.0, 84.0]
        ai_times_1 = [100.0, 100.0, 100.0]
        ratio_1 = self.calculate_ratio_from_times(user_times_1, ai_times_1)
        
        # User becomes slower with additional laps
        # Sorted user_times_2: [84, 85, 86, 95, 95, 96] -> median = (86 + 95) / 2 = 90.5
        user_times_2 = [85.0, 86.0, 84.0, 95.0, 96.0, 95.0]
        ai_times_2 = [100.0, 100.0, 100.0, 100.0, 100.0, 100.0]
        ratio_2 = self.calculate_ratio_from_times(user_times_2, ai_times_2)
        
        # Ratio should increase (user is slower)
        self.assertLess(ratio_1, ratio_2)
        self.assertAlmostEqual(ratio_1, 0.85, places=2)
        self.assertAlmostEqual(ratio_2, 0.905, places=3)
    
    def test_median_stability_with_large_changes(self):
        """Test that median is stable when large changes occur in new data"""
        # Baseline data
        user_times_baseline = [90.0, 91.0, 89.0, 90.0, 91.0]
        ai_times = [100.0] * 5
        
        # Add extreme new lap time (very fast)
        user_times_with_extreme = user_times_baseline + [60.0]
        
        # Median should not change dramatically
        median_baseline = statistics.median(user_times_baseline)
        median_with_extreme = statistics.median(user_times_with_extreme)
        
        # With median, one extreme value doesn't change the median much
        self.assertAlmostEqual(median_baseline, 90.0, places=1)
        self.assertAlmostEqual(median_with_extreme, 90.0, places=1)
    
    def test_ratio_convergence_with_more_data(self):
        """Test that ratio converges to expected value as data increases"""
        true_ratio = 0.85
        ai_median = 100.0
        user_median = true_ratio * ai_median  # 85.0
        
        # Simulate progressive data collection
        ratios_over_time = []
        
        for n in range(1, 20):
            # Generate n user times around the true median
            import random
            random.seed(42)
            user_times = [user_median + random.uniform(-3, 3) for _ in range(n)]
            ai_times = [ai_median + random.uniform(-2, 2) for _ in range(n)]
            
            ratio = self.calculate_ratio_from_times(user_times, ai_times)
            if ratio:
                ratios_over_time.append(ratio)
        
        # Final ratio should be close to true ratio
        if ratios_over_time:
            final_ratio = ratios_over_time[-1]
            self.assertAlmostEqual(final_ratio, true_ratio, delta=0.05)


class TestFormulaRatioIntegration(BaseTestCase):
    """Test integration between ratio calculation and hyperbolic formula"""
    
    def setUp(self):
        super().setUp()
        self.db_path = self.temp_env.test_data_dir / "formula_integration.db"
        self.db = CurveDatabase(str(self.db_path))
    
    def test_ratio_to_time_to_ratio_consistency(self):
        """Test that ratio -> hyperbola time -> ratio returns original value"""
        test_cases = [
            (0.6, 32.0, 70.0),
            (0.8, 32.0, 70.0),
            (1.0, 32.0, 70.0),
            (1.2, 32.0, 70.0),
            (1.4, 32.0, 70.0),
            (1.6, 32.0, 70.0),
        ]
        
        for ratio, a, b in test_cases:
            time = hyperbolic(ratio, a, b)
            calculated_ratio = ratio_from_time(time, a, b)
            self.assertIsNotNone(calculated_ratio)
            self.assertAlmostEqual(ratio, calculated_ratio, places=5)
    
    def test_ratio_calculation_with_formula_fit(self):
        """Test that ratio calculation works with fitted formula parameters"""
        # Simulate data points
        ratios = [0.7, 0.8, 0.9, 1.0, 1.1, 1.2, 1.3]
        actual_a, actual_b = 30.0, 68.0
        times = [hyperbolic(r, actual_a, actual_b) for r in ratios]
        
        # Fit curve
        fitted_a, fitted_b, avg_err, max_err, info = fit_curve(ratios, times, verbose=False)
        
        self.assertIsNotNone(fitted_a)
        self.assertIsNotNone(fitted_b)
        self.assertAlmostEqual(fitted_a, actual_a, delta=1.0)
        self.assertAlmostEqual(fitted_b, actual_b, delta=1.0)
    
    def test_calculate_ratio_with_realistic_data(self):
        """Test full workflow: user laps -> ratio -> formula -> expected AI adjustment"""
        # Simulate a race session
        user_laps = [85.0, 86.0, 84.5, 85.5, 85.0]
        ai_laps = [95.0, 96.0, 94.5, 95.5, 95.0]
        
        # Calculate current ratio
        median_user = statistics.median(user_laps)
        median_ai = statistics.median(ai_laps)
        current_ratio = median_user / median_ai
        
        # Target ratio (if we want user and AI to be equal)
        target_ratio = 1.0
        
        # Calculate adjustment needed
        adjustment = target_ratio / current_ratio
        
        # User is faster than AI (current_ratio < 1.0), so AI needs to be slowed down (adjustment > 1.0)
        self.assertLess(current_ratio, 1.0)
        self.assertGreater(adjustment, 1.0)
        
        # New AI ratio should be current_ratio * adjustment = 1.0
        new_ratio = current_ratio * adjustment
        self.assertAlmostEqual(new_ratio, 1.0, places=5)
    
    def test_median_vs_mean_for_ratio_robustness(self):
        """Compare median vs mean for ratio calculation with outliers"""
        # Data with outlier
        user_laps = [85.0, 86.0, 84.0, 85.0, 200.0]  # Outlier at 200
        ai_laps = [95.0, 96.0, 94.0, 95.0, 96.0]
        
        ratio_with_median = statistics.median(user_laps) / statistics.median(ai_laps)
        ratio_with_mean = statistics.mean(user_laps) / statistics.mean(ai_laps)
        
        # Median should be more robust
        # With outlier, mean is skewed higher, so ratio_with_mean is higher
        self.assertGreater(ratio_with_mean, ratio_with_median)
        
        # Ratio with median should be around 0.89-0.90
        # Ratio with mean would be around 1.1-1.2 (incorrect due to outlier)
        self.assertAlmostEqual(ratio_with_median, 0.894, places=2)
        self.assertGreater(ratio_with_mean, 1.0)


class TestEdgeCases(BaseTestCase):
    """Test edge cases in ratio calculation"""
    
    def test_identical_user_and_ai_times(self):
        """Test ratio when user and AI have identical times"""
        user_times = [100.0, 101.0, 99.0]
        ai_times = [100.0, 101.0, 99.0]
        
        median_user = statistics.median(user_times)
        median_ai = statistics.median(ai_times)
        ratio = median_user / median_ai
        
        self.assertAlmostEqual(ratio, 1.0, places=5)
    
    def test_user_faster_than_ai(self):
        """Test ratio when user is faster than AI"""
        user_times = [80.0, 82.0, 81.0]
        ai_times = [100.0, 102.0, 101.0]
        
        median_user = statistics.median(user_times)
        median_ai = statistics.median(ai_times)
        ratio = median_user / median_ai
        
        self.assertLess(ratio, 1.0)
        # Sorted user: [80,81,82] -> median = 81
        # Sorted AI: [100,101,102] -> median = 101
        # ratio = 81 / 101 = 0.80198...
        self.assertAlmostEqual(ratio, 81.0 / 101.0, places=3)
    
    def test_user_slower_than_ai(self):
        """Test ratio when user is slower than AI"""
        user_times = [120.0, 122.0, 121.0]
        ai_times = [100.0, 102.0, 101.0]
        
        median_user = statistics.median(user_times)
        median_ai = statistics.median(ai_times)
        ratio = median_user / median_ai
        
        self.assertGreater(ratio, 1.0)
        # Sorted user: [120,121,122] -> median = 121
        # Sorted AI: [100,101,102] -> median = 101
        # ratio = 121 / 101 = 1.198...
        self.assertAlmostEqual(ratio, 121.0 / 101.0, places=3)
    
    def test_zero_or_negative_lap_times(self):
        """Test handling of invalid lap times"""
        user_times = [85.0, 0.0, -5.0, 90.0]
        ai_times = [95.0, 100.0, 0.0, 105.0]
        
        # Filter out invalid times
        valid_user = [t for t in user_times if t > 0]  # [85.0, 90.0]
        valid_ai = [t for t in ai_times if t > 0]      # [95.0, 100.0, 105.0]
        
        # valid_user median = (85.0 + 90.0) / 2 = 87.5
        # valid_ai median = 100.0
        # ratio = 87.5 / 100 = 0.875
        median_user = statistics.median(valid_user)
        median_ai = statistics.median(valid_ai)
        ratio = median_user / median_ai
        
        self.assertAlmostEqual(ratio, 87.5 / 100.0, places=3)
    
    def test_single_valid_lap_after_filtering(self):
        """Test ratio calculation when only one valid lap remains after filtering"""
        user_times = [85.0, 0.0, -10.0]
        ai_times = [100.0, 0.0, 0.0]
        
        valid_user = [t for t in user_times if t > 0]
        valid_ai = [t for t in ai_times if t > 0]
        
        ratio = self.calculate_ratio_from_times(valid_user, valid_ai)
        
        self.assertIsNotNone(ratio)
        self.assertAlmostEqual(ratio, 0.85, places=3)
    
    def calculate_ratio_from_times(self, user_times: List[float], ai_times: List[float]) -> Optional[float]:
        """Helper to calculate ratio"""
        if not user_times or not ai_times:
            return None
        return statistics.median(user_times) / statistics.median(ai_times)
    
    def test_large_number_of_laps(self):
        """Test ratio calculation with many laps (performance and correctness)"""
        import random
        random.seed(42)
        
        true_ratio = 0.9
        ai_median = 100.0
        user_median = true_ratio * ai_median  # 90.0
        
        user_times = [user_median + random.uniform(-5, 5) for _ in range(1000)]
        ai_times = [ai_median + random.uniform(-5, 5) for _ in range(1000)]
        
        ratio = self.calculate_ratio_from_times(user_times, ai_times)
        
        self.assertIsNotNone(ratio)
        self.assertAlmostEqual(ratio, true_ratio, delta=0.02)


def run_ratio_calculation_tests():
    """Run all ratio calculation tests"""
    print("\n" + "=" * 60)
    print("RATIO CALCULATION TESTS")
    print("=" * 60)
    
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    suite.addTests(loader.loadTestsFromTestCase(TestRatioCalculation))
    suite.addTests(loader.loadTestsFromTestCase(TestSequentialRatioUpdates))
    suite.addTests(loader.loadTestsFromTestCase(TestFormulaRatioIntegration))
    suite.addTests(loader.loadTestsFromTestCase(TestEdgeCases))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result


if __name__ == "__main__":
    run_ratio_calculation_tests()
