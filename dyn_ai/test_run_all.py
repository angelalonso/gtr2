#!/usr/bin/env python3
"""
Main test runner for Live AI Tuner
Runs all tests and reports results
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from test_backup_manager import OriginalFileBackup
from test_unit_config import TestConfig
from test_unit_database import TestDatabase
from test_unit_formula import TestFormula
from test_unit_aiw_utils import TestAIWUtils
from test_unit_vehicle_classes import TestVehicleClasses
from test_unit_data_extraction import TestDataExtraction
from test_unit_vehicle_scanner import TestVehicleScanner
from test_unit_plr_check import run_plr_tests
from test_unit_pre_run_check import run_pre_run_check_plr_tests
from test_unit_outlier_detection import run_outlier_tests
from test_error_injection import TestErrorInjection
from test_simulation_harness import run_simulation_tests
import unittest


def run_unit_tests():
    """Run all unit tests"""
    print("\n" + "=" * 60)
    print("RUNNING UNIT TESTS")
    print("=" * 60)
    
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    suite.addTests(loader.loadTestsFromTestCase(TestConfig))
    suite.addTests(loader.loadTestsFromTestCase(TestDatabase))
    suite.addTests(loader.loadTestsFromTestCase(TestFormula))
    suite.addTests(loader.loadTestsFromTestCase(TestAIWUtils))
    suite.addTests(loader.loadTestsFromTestCase(TestVehicleClasses))
    suite.addTests(loader.loadTestsFromTestCase(TestDataExtraction))
    suite.addTests(loader.loadTestsFromTestCase(TestVehicleScanner))
    suite.addTests(loader.loadTestsFromTestCase(TestErrorInjection))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result


def run_plr_unit_tests():
    """Run PLR-specific unit tests"""
    print("\n" + "=" * 60)
    print("RUNNING PLR UNIT TESTS")
    print("=" * 60)
    
    plr_result = run_plr_tests()
    pre_run_result = run_pre_run_check_plr_tests()
    
    print(f"\nPLR Tests Result: {'PASS' if plr_result else 'FAIL'}")
    print(f"Pre-run Check PLR Tests Result: {'PASS' if pre_run_result else 'FAIL'}")
    
    return plr_result and pre_run_result


def run_outlier_unit_tests():
    """Run outlier detection unit tests"""
    print("\n" + "=" * 60)
    print("RUNNING OUTLIER DETECTION UNIT TESTS")
    print("=" * 60)
    
    result = run_outlier_tests()
    return result


def run_all_tests():
    """Run all tests including simulations"""
    print("\n" + "=" * 60)
    print("LIVE AI TUNER - COMPREHENSIVE TEST SUITE")
    print("=" * 60)
    print("\nNOTE: All tests use isolated temporary directories")
    print("      Original vehicle_classes.json and cfg.yml are preserved")
    print("=" * 60)
    
    backup_manager = OriginalFileBackup()
    
    classes_path = Path(__file__).parent / "vehicle_classes.json"
    if classes_path.exists():
        backup_manager.backup_file(classes_path)
    
    config_path = Path(__file__).parent / "cfg.yml"
    if config_path.exists():
        backup_manager.backup_file(config_path)
    
    unit_result = run_unit_tests()
    
    plr_result = run_plr_unit_tests()
    
    outlier_result = run_outlier_unit_tests()
    
    simulation_results = run_simulation_tests()
    
    backup_manager.restore_all()
    
    print("\n" + "=" * 60)
    print("FINAL SUMMARY")
    print("=" * 60)
    
    unit_passed = unit_result.wasSuccessful()
    sim_passed = all(r.success for r in simulation_results)
    
    print(f"Unit Tests: {'PASS' if unit_passed else 'FAIL'}")
    print(f"PLR Tests: {'PASS' if plr_result else 'FAIL'}")
    print(f"Outlier Detection Tests: {'PASS' if outlier_result else 'FAIL'}")
    print(f"Simulation Tests: {'PASS' if sim_passed else 'FAIL'}")
    
    if unit_passed and plr_result and outlier_result and sim_passed:
        print("\nALL TESTS PASSED")
        return 0
    else:
        print("\nSOME TESTS FAILED")
        return 1


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Live AI Tuner Test Suite')
    parser.add_argument('--unit', action='store_true', help='Run only unit tests')
    parser.add_argument('--plr', action='store_true', help='Run only PLR tests')
    parser.add_argument('--outlier', action='store_true', help='Run only outlier detection tests')
    parser.add_argument('--simulation', action='store_true', help='Run only simulation tests')
    parser.add_argument('--all', action='store_true', help='Run all tests')
    
    args = parser.parse_args()
    
    if args.unit:
        result = run_unit_tests()
        return 0 if result.wasSuccessful() else 1
    elif args.plr:
        result = run_plr_unit_tests()
        return 0 if result else 1
    elif args.outlier:
        result = run_outlier_unit_tests()
        return 0 if result else 1
    elif args.simulation:
        results = run_simulation_tests()
        return 0 if all(r.success for r in results) else 1
    else:
        return run_all_tests()


if __name__ == "__main__":
    sys.exit(main())
