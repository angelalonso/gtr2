#!/usr/bin/env python3
"""
Main test runner for Live AI Tuner
Runs all tests and reports results
"""

import sys
from pathlib import Path

# Add parent directory to path so we can import application modules
sys.path.insert(0, str(Path(__file__).parent.parent))

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
from test_resource_paths import run_resource_tests
from test_pyinstaller_compatibility import run_pyinstaller_tests
from test_unit_data_manager import run_data_manager_tests
from test_unit_gui_dialogs import run_dialog_tests
from test_unit_user_laptimes import run_user_laptimes_tests
from test_unit_median_ratio import run_median_ratio_tests
from test_unit_ratio_calculation import run_ratio_calculation_tests
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


def run_formula_unit_tests():
    """Run only formula unit tests including ratio calculation"""
    print("\n" + "=" * 60)
    print("RUNNING FORMULA UNIT TESTS")
    print("=" * 60)
    
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    suite.addTests(loader.loadTestsFromTestCase(TestFormula))
    
    # Also run ratio calculation tests as part of formula tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Run ratio calculation tests separately and combine results
    ratio_result = run_ratio_calculation_tests()
    
    # Combine results - if either fails, overall fails
    if result.wasSuccessful() and ratio_result.wasSuccessful():
        return result
    else:
        # Create a failing result
        return type('Result', (), {'wasSuccessful': lambda: False})()
    
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


def run_resource_unit_tests():
    """Run resource path resolution tests"""
    print("\n" + "=" * 60)
    print("RUNNING RESOURCE PATH TESTS")
    print("=" * 60)
    
    result = run_resource_tests()
    return result


def run_pyinstaller_compatibility_tests():
    """Run PyInstaller compatibility tests"""
    print("\n" + "=" * 60)
    print("RUNNING PYINSTALLER COMPATIBILITY TESTS")
    print("=" * 60)
    
    result = run_pyinstaller_tests()
    return result


def run_data_manager_unit_tests():
    """Run data manager tests"""
    print("\n" + "=" * 60)
    print("RUNNING DATA MANAGER TESTS")
    print("=" * 60)
    
    result = run_data_manager_tests()
    return result


def run_gui_dialog_unit_tests():
    """Run GUI dialog tests"""
    print("\n" + "=" * 60)
    print("RUNNING GUI DIALOG TESTS")
    print("=" * 60)
    
    result = run_dialog_tests()
    return result


def run_user_laptimes_tests():
    """Run user laptimes tests"""
    print("\n" + "=" * 60)
    print("RUNNING USER LAPTIMES TESTS")
    print("=" * 60)
    
    from test_unit_user_laptimes import run_user_laptimes_tests as _run_user_laptimes_tests
    return _run_user_laptimes_tests()


def run_median_ratio_tests():
    """Run median ratio tests"""
    print("\n" + "=" * 60)
    print("RUNNING MEDIAN RATIO TESTS")
    print("=" * 60)
    
    from test_unit_median_ratio import run_median_ratio_tests as _run_median_ratio_tests
    return _run_median_ratio_tests()


def run_ratio_calculation_tests():
    """Run ratio calculation tests"""
    print("\n" + "=" * 60)
    print("RUNNING RATIO CALCULATION TESTS")
    print("=" * 60)
    
    from test_unit_ratio_calculation import run_ratio_calculation_tests as _run_ratio_calculation_tests
    return _run_ratio_calculation_tests()


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
    
    resource_result = run_resource_unit_tests()
    
    pyinstaller_result = run_pyinstaller_compatibility_tests()
    
    data_manager_result = run_data_manager_unit_tests()
    
    gui_dialog_result = run_gui_dialog_unit_tests()
    
    # User laptimes and median ratio tests
    user_laptimes_result = run_user_laptimes_tests()
    median_ratio_result = run_median_ratio_tests()
    
    # Ratio calculation tests (now part of formula tests)
    ratio_calculation_result = run_ratio_calculation_tests()
    
    simulation_results = run_simulation_tests()
    
    backup_manager.restore_all()
    
    print("\n" + "=" * 60)
    print("FINAL SUMMARY")
    print("=" * 60)
    
    unit_passed = unit_result.wasSuccessful()
    sim_passed = all(r.success for r in simulation_results)
    user_laptimes_passed = user_laptimes_result.wasSuccessful()
    median_ratio_passed = median_ratio_result.wasSuccessful()
    ratio_calculation_passed = ratio_calculation_result.wasSuccessful()
    
    print(f"Unit Tests: {'PASS' if unit_passed else 'FAIL'}")
    print(f"PLR Tests: {'PASS' if plr_result else 'FAIL'}")
    print(f"Outlier Detection Tests: {'PASS' if outlier_result else 'FAIL'}")
    print(f"Resource Path Tests: {'PASS' if resource_result else 'FAIL'}")
    print(f"PyInstaller Compatibility Tests: {'PASS' if pyinstaller_result else 'FAIL'}")
    print(f"Data Manager Tests: {'PASS' if data_manager_result.wasSuccessful() else 'FAIL'}")
    print(f"GUI Dialog Tests: {'PASS' if gui_dialog_result.wasSuccessful() else 'FAIL'}")
    print(f"User Laptimes Tests: {'PASS' if user_laptimes_passed else 'FAIL'}")
    print(f"Median Ratio Tests: {'PASS' if median_ratio_passed else 'FAIL'}")
    print(f"Ratio Calculation Tests: {'PASS' if ratio_calculation_passed else 'FAIL'}")
    print(f"Simulation Tests: {'PASS' if sim_passed else 'FAIL'}")
    
    all_passed = (unit_passed and plr_result and outlier_result and 
                  resource_result and pyinstaller_result and sim_passed and
                  data_manager_result.wasSuccessful() and
                  gui_dialog_result.wasSuccessful() and
                  user_laptimes_passed and median_ratio_passed and
                  ratio_calculation_passed)
    
    if all_passed:
        print("\nALL TESTS PASSED")
        return 0
    else:
        print("\nSOME TESTS FAILED")
        return 1


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Live AI Tuner Test Suite')
    parser.add_argument('--formula', action='store_true', help='Run only formula unit tests (includes ratio calculation)')
    parser.add_argument('--unit', action='store_true', help='Run only unit tests')
    parser.add_argument('--plr', action='store_true', help='Run only PLR tests')
    parser.add_argument('--outlier', action='store_true', help='Run only outlier detection tests')
    parser.add_argument('--resource', action='store_true', help='Run only resource path tests')
    parser.add_argument('--pyinstaller', action='store_true', help='Run only PyInstaller compatibility tests')
    parser.add_argument('--datamanager', action='store_true', help='Run only data manager tests')
    parser.add_argument('--dialogs', action='store_true', help='Run only GUI dialog tests')
    parser.add_argument('--simulation', action='store_true', help='Run only simulation tests')
    parser.add_argument('--ratio', action='store_true', help='Run only ratio calculation tests')
    parser.add_argument('--all', action='store_true', help='Run all tests')
    
    args = parser.parse_args()
    
    if args.formula:
        result = run_formula_unit_tests()
        # result is a TestResult object
        return 0 if (hasattr(result, 'wasSuccessful') and result.wasSuccessful()) else 1
    elif args.unit:
        result = run_unit_tests()
        return 0 if result.wasSuccessful() else 1
    elif args.plr:
        result = run_plr_unit_tests()
        return 0 if result else 1
    elif args.outlier:
        result = run_outlier_unit_tests()
        return 0 if result else 1
    elif args.resource:
        result = run_resource_unit_tests()
        return 0 if result else 1
    elif args.pyinstaller:
        result = run_pyinstaller_compatibility_tests()
        return 0 if result else 1
    elif args.datamanager:
        result = run_data_manager_unit_tests()
        return 0 if result.wasSuccessful() else 1
    elif args.dialogs:
        result = run_gui_dialog_unit_tests()
        return 0 if result.wasSuccessful() else 1
    elif args.simulation:
        results = run_simulation_tests()
        return 0 if all(r.success for r in results) else 1
    elif args.ratio:
        result = run_ratio_calculation_tests()
        return 0 if result.wasSuccessful() else 1
    else:
        return run_all_tests()


if __name__ == "__main__":
    sys.exit(main())
