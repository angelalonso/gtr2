#!/usr/bin/env python3
"""
Automated test runner for Live AI Tuner
Supports batch testing, continuous testing, and report generation
All tests use isolated environments - no permanent modifications
"""

import sys
import os
import json
import time
import argparse
import subprocess
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QTimer, QEventLoop, QObject, pyqtSignal

from test_suite import TempTestEnvironment, WaitForSignal, OriginalFileBackup


class TestRunner(QObject):
    """Automated test runner with reporting"""
    
    test_started = pyqtSignal(str)
    test_completed = pyqtSignal(str, bool, str)
    progress_updated = pyqtSignal(int, int)
    
    def __init__(self):
        super().__init__()
        self.results = []
        self.start_time = None
        self.end_time = None
        self.backup_manager = OriginalFileBackup()
    
    def run_all_tests(self) -> Dict[str, Any]:
        """Run all automated tests"""
        self.start_time = datetime.now()
        self.results = []
        
        # Backup original files before starting
        classes_path = Path(__file__).parent / "vehicle_classes.json"
        if classes_path.exists():
            self.backup_manager.backup_file(classes_path)
        
        config_path = Path(__file__).parent / "cfg.yml"
        if config_path.exists():
            self.backup_manager.backup_file(config_path)
        
        tests = [
            ("config_load", self.test_config_load),
            ("config_save", self.test_config_save),
            ("ratio_limits", self.test_ratio_limits),
            ("database_create", self.test_database_create),
            ("database_add_point", self.test_database_add_point),
            ("formula_calculation", self.test_formula_calculation),
            ("formula_fit", self.test_formula_fit),
            ("aiw_find", self.test_aiw_find),
            ("aiw_update", self.test_aiw_update),
            ("aiw_backup", self.test_aiw_backup),
            ("aiw_readonly", self.test_aiw_readonly),
            ("aiw_duplicate", self.test_aiw_duplicate),
            ("race_parse_valid", self.test_race_parse_valid),
            ("race_parse_corrupt", self.test_race_parse_corrupt),
            ("race_parse_missing", self.test_race_parse_missing),
            ("race_parse_unicode", self.test_race_parse_unicode),
            ("vehicle_scan", self.test_vehicle_scan),
            ("vehicle_class_add", self.test_vehicle_class_add),
            ("vehicle_class_delete", self.test_vehicle_class_delete),
            ("backup_restore", self.test_backup_restore),
            ("error_missing_aiw", self.test_error_missing_aiw),
            ("error_permission_denied", self.test_error_permission_denied),
            ("error_corrupt_race", self.test_error_corrupt_race),
        ]
        
        total = len(tests)
        for i, (name, test_func) in enumerate(tests):
            self.test_started.emit(name)
            try:
                success, message = test_func()
                self.results.append({
                    "name": name,
                    "success": success,
                    "message": message,
                    "timestamp": datetime.now().isoformat()
                })
                self.test_completed.emit(name, success, message)
            except Exception as e:
                self.results.append({
                    "name": name,
                    "success": False,
                    "message": str(e),
                    "timestamp": datetime.now().isoformat()
                })
                self.test_completed.emit(name, False, str(e))
            
            self.progress_updated.emit(i + 1, total)
        
        # Restore original files
        self.backup_manager.restore_all()
        
        self.end_time = datetime.now()
        return self.get_report()
    
    def get_report(self) -> Dict[str, Any]:
        """Get test results report"""
        total = len(self.results)
        passed = sum(1 for r in self.results if r["success"])
        failed = total - passed
        
        duration = (self.end_time - self.start_time).total_seconds() if self.end_time and self.start_time else 0
        
        return {
            "total_tests": total,
            "passed": passed,
            "failed": failed,
            "success_rate": (passed / total * 100) if total > 0 else 0,
            "duration_seconds": duration,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "results": self.results
        }
    
    def save_report(self, filepath: Path):
        """Save test report to JSON file"""
        report = self.get_report()
        with open(filepath, 'w') as f:
            json.dump(report, f, indent=2)
    
    def print_report(self):
        """Print test report to console"""
        report = self.get_report()
        
        print("\n" + "=" * 70)
        print("TEST REPORT")
        print("=" * 70)
        print(f"Total tests: {report['total_tests']}")
        print(f"Passed: {report['passed']}")
        print(f"Failed: {report['failed']}")
        print(f"Success rate: {report['success_rate']:.1f}%")
        print(f"Duration: {report['duration_seconds']:.2f} seconds")
        print("\n" + "-" * 70)
        
        for result in report["results"]:
            status = "PASS" if result["success"] else "FAIL"
            print(f"[{status}] {result['name']}")
            if not result["success"] and result["message"]:
                print(f"      {result['message']}")
        
        print("=" * 70)
    
    # =========================================================================
    # Unit Tests (all using isolated environments)
    # =========================================================================
    
    def test_config_load(self) -> Tuple[bool, str]:
        """Test configuration loading"""
        with TempTestEnvironment() as env:
            from core_config import load_config
            
            config = load_config(str(env.config_path))
            if config is None:
                return False, "Failed to load config"
            
            if config.get('base_path') != str(env.base_path):
                return False, f"Base path mismatch: {config.get('base_path')} vs {env.base_path}"
            
            return True, "Config loaded successfully"
    
    def test_config_save(self) -> Tuple[bool, str]:
        """Test configuration saving"""
        with TempTestEnvironment() as env:
            from core_config import load_config, save_config
            
            config = load_config(str(env.config_path))
            config['test_key'] = 'test_value'
            
            if not save_config(config, str(env.config_path)):
                return False, "Failed to save config"
            
            loaded = load_config(str(env.config_path))
            if loaded.get('test_key') != 'test_value':
                return False, "Saved value not found"
            
            return True, "Config saved and reloaded successfully"
    
    def test_ratio_limits(self) -> Tuple[bool, str]:
        """Test ratio limits functionality"""
        with TempTestEnvironment() as env:
            from core_config import get_ratio_limits, update_ratio_limits
            
            min_r, max_r = get_ratio_limits(str(env.config_path))
            
            if min_r != 0.3 or max_r != 2.5:
                return False, f"Unexpected limits: {min_r}, {max_r}"
            
            update_ratio_limits(0.4, 2.0, str(env.config_path))
            min_r, max_r = get_ratio_limits(str(env.config_path))
            
            if min_r != 0.4 or max_r != 2.0:
                return False, f"Failed to update limits: {min_r}, {max_r}"
            
            return True, "Ratio limits work correctly"
    
    def test_database_create(self) -> Tuple[bool, str]:
        """Test database creation"""
        with TempTestEnvironment() as env:
            from core_database import CurveDatabase
            
            db_path = env.test_data_dir / "new_db.db"
            db = CurveDatabase(str(db_path))
            
            if not db_path.exists():
                return False, "Database file not created"
            
            if not db.database_exists():
                return False, "database_exists() returns False"
            
            return True, "Database created successfully"
    
    def test_database_add_point(self) -> Tuple[bool, str]:
        """Test adding data points to database"""
        with TempTestEnvironment() as env:
            from core_database import CurveDatabase
            
            db_path = env.test_data_dir / "test.db"
            db = CurveDatabase(str(db_path))
            
            result = db.add_data_point("Monza", "GT_0304", 1.2, 95.5, "race")
            if not result:
                return False, "Failed to add data point"
            
            points = db.get_data_points(["Monza"], ["GT_0304"], True, True, True)
            if len(points) != 1:
                return False, f"Expected 1 point, got {len(points)}"
            
            ratio, lap_time, session = points[0]
            if abs(ratio - 1.2) > 0.001:
                return False, f"Ratio mismatch: {ratio}"
            if abs(lap_time - 95.5) > 0.001:
                return False, f"Lap time mismatch: {lap_time}"
            
            return True, "Data point added and retrieved correctly"
    
    def test_formula_calculation(self) -> Tuple[bool, str]:
        """Test hyperbolic formula calculations"""
        from core_formula import hyperbolic, ratio_from_time
        
        a, b = 32.0, 70.0
        
        test_cases = [
            (0.6, 123.333333),
            (0.8, 110.0),
            (1.0, 102.0),
            (1.2, 96.666667),
            (1.4, 92.857143),
            (1.6, 90.0),
        ]
        
        for R, expected_T in test_cases:
            T = hyperbolic(R, a, b)
            if abs(T - expected_T) > 0.001:
                return False, f"At R={R}: expected {expected_T:.3f}, got {T:.3f}"
        
        for R, T in test_cases:
            calc_R = ratio_from_time(T, a, b)
            if calc_R is None or abs(calc_R - R) > 0.001:
                return False, f"At T={T}: expected R={R}, got {calc_R}"
        
        return True, "Formula calculations correct"
    
    def test_formula_fit(self) -> Tuple[bool, str]:
        """Test curve fitting"""
        from core_formula import hyperbolic, fit_curve
        import random
        
        a, b = 32.0, 70.0
        ratios = [0.6, 0.8, 1.0, 1.2, 1.4, 1.6]
        times = [hyperbolic(r, a, b) for r in ratios]
        
        times_noisy = [t + random.uniform(-0.3, 0.3) for t in times]
        
        fitted_a, fitted_b, avg_err, max_err = fit_curve(ratios, times_noisy, verbose=False)
        
        if fitted_a is None or fitted_b is None:
            return False, "Fit returned None"
        
        if abs(fitted_a - a) > 10.0:
            return False, f"A value too far off: {fitted_a} vs {a}"
        
        if abs(fitted_b - b) > 5.0:
            return False, f"B value too far off: {fitted_b} vs {b}"
        
        return True, f"Curve fit successful: a={fitted_a:.2f}, b={fitted_b:.2f}"
    
    def test_aiw_find(self) -> Tuple[bool, str]:
        """Test AIW file finding"""
        with TempTestEnvironment() as env:
            from core_aiw_utils import find_aiw_file_by_track
            
            found = find_aiw_file_by_track("Monza", env.base_path)
            if found is None:
                return False, "Failed to find Monza AIW"
            
            if not found.exists():
                return False, f"Found path does not exist: {found}"
            
            found = find_aiw_file_by_track("monza", env.base_path)
            if found is None:
                return False, "Case-insensitive search failed"
            
            return True, "AIW file found correctly"
    
    def test_aiw_update(self) -> Tuple[bool, str]:
        """Test AIW ratio update"""
        with TempTestEnvironment() as env:
            from core_aiw_utils import update_aiw_ratio
            
            aiw_path = env.mock_aiw_files.get("Monza")
            if not aiw_path:
                return False, "No AIW file for Monza"
            
            result = update_aiw_ratio(aiw_path, "QualRatio", 1.234567)
            if not result:
                return False, "Failed to update ratio"
            
            new_content = aiw_path.read_text()
            if "QualRatio = 1.234567" not in new_content:
                return False, "Ratio not updated correctly"
            
            return True, "AIW ratio updated successfully"
    
    def test_aiw_backup(self) -> Tuple[bool, str]:
        """Test AIW backup creation"""
        with TempTestEnvironment() as env:
            from core_aiw_utils import update_aiw_ratio
            
            aiw_path = env.mock_aiw_files.get("Monza")
            if not aiw_path:
                return False, "No AIW file for Monza"
            
            backup_dir = env.test_data_dir / "backups"
            
            result = update_aiw_ratio(aiw_path, "QualRatio", 1.5, backup_dir)
            if not result:
                return False, "Failed to update ratio"
            
            backup_files = list(backup_dir.glob("*_ORIGINAL.AIW"))
            if len(backup_files) != 1:
                return False, f"Expected 1 backup, got {len(backup_files)}"
            
            return True, "Backup created successfully"
    
    def test_aiw_readonly(self) -> Tuple[bool, str]:
        """Test handling of read-only AIW file"""
        with TempTestEnvironment() as env:
            from core_aiw_utils import update_aiw_ratio
            
            aiw_path = env.mock_aiw_files.get("Monza")
            if not aiw_path:
                return False, "No AIW file for Monza"
            
            env.make_aiw_readonly("Monza")
            
            result = update_aiw_ratio(aiw_path, "QualRatio", 1.5)
            
            env.make_aiw_writable("Monza")
            
            return True, "Read-only handling works (no crash)"
    
    def test_aiw_duplicate(self) -> Tuple[bool, str]:
        """Test handling of duplicate AIW files"""
        with TempTestEnvironment() as env:
            from core_aiw_utils import find_aiw_file_by_track
            
            env.create_duplicate_aiw_files("Monza")
            
            found = find_aiw_file_by_track("Monza", env.base_path)
            
            if found is None:
                return False, "Failed to find AIW with duplicates present"
            
            return True, f"Found AIW despite duplicates: {found.name}"
    
    def test_race_parse_valid(self) -> Tuple[bool, str]:
        """Test parsing valid race results"""
        with TempTestEnvironment() as env:
            from core_data_extraction import DataExtractor
            
            env.create_mock_race_results(
                user_qual_time=90.0,
                user_race_time=88.0,
                ai_best_qual=92.0,
                ai_worst_qual=98.0
            )
            
            extractor = DataExtractor(env.base_path)
            race_data = extractor.parse_race_results(env.results_path)
            
            if race_data is None:
                return False, "Failed to parse race results"
            
            if race_data.track_name != "Monza":
                return False, f"Wrong track: {race_data.track_name}"
            
            if race_data.user_qualifying_sec <= 0:
                return False, "No qualifying time extracted"
            
            if race_data.user_best_lap_sec <= 0:
                return False, "No race time extracted"
            
            return True, "Valid race results parsed correctly"
    
    def test_race_parse_corrupt(self) -> Tuple[bool, str]:
        """Test parsing corrupt race results"""
        with TempTestEnvironment() as env:
            from core_data_extraction import DataExtractor
            
            env.create_corrupt_race_results()
            
            extractor = DataExtractor(env.base_path)
            race_data = extractor.parse_race_results(env.results_path)
            
            if race_data and race_data.has_data():
                return False, "Corrupt file returned data"
            
            return True, "Corrupt file handled gracefully"
    
    def test_race_parse_missing(self) -> Tuple[bool, str]:
        """Test parsing missing race results file"""
        with TempTestEnvironment() as env:
            from core_data_extraction import DataExtractor
            
            fake_path = env.base_path / "nonexistent.txt"
            extractor = DataExtractor(env.base_path)
            race_data = extractor.parse_race_results(fake_path)
            
            if race_data is not None:
                return False, "Non-existent file returned data"
            
            return True, "Missing file handled correctly"
    
    def test_race_parse_unicode(self) -> Tuple[bool, str]:
        """Test parsing race results with Unicode"""
        with TempTestEnvironment() as env:
            from core_data_extraction import DataExtractor
            
            content = """[Race]
Scene=GameData/Locations/Monza/4Monza.TRK
AIDB=GameData/Locations/Monza/4Monza.AIW

[Slot0]
Driver=Joueur Francais
Vehicle=Voiture de Test
BestLap=1:30.000

[Slot1]
Driver=Fahrer Deutsch
Vehicle=Testwagen
BestLap=1:31.000
"""
            env.results_path.write_text(content, encoding='utf-8')
            
            extractor = DataExtractor(env.base_path)
            race_data = extractor.parse_race_results(env.results_path)
            
            if race_data is None:
                return False, "Failed to parse Unicode results"
            
            if race_data.user_name != "Joueur Francais":
                return False, f"Wrong driver name: {race_data.user_name}"
            
            return True, "Unicode results parsed correctly"
    
    def test_vehicle_scan(self) -> Tuple[bool, str]:
        """Test vehicle scanning"""
        with TempTestEnvironment() as env:
            from core_vehicle_scanner import scan_vehicles_from_gtr2
            
            vehicles = scan_vehicles_from_gtr2(env.base_path)
            
            if len(vehicles) == 0:
                return False, "No vehicles found"
            
            if "Test Car GT" not in vehicles:
                return False, "Test Car GT not found"
            
            return True, f"Found {len(vehicles)} vehicles"
    
    def test_vehicle_class_add(self) -> Tuple[bool, str]:
        """Test adding vehicle class - uses isolated test file"""
        with TempTestEnvironment() as env:
            from gui_vehicle_manager import VehicleClassesManager
            
            manager = VehicleClassesManager(env.classes_path)
            
            result = manager.add_class("NEW_CLASS", ["NEW_CLASS"], ["New Car 1", "New Car 2"])
            if not result:
                return False, "Failed to add class"
            
            vehicles = manager.get_vehicles_for_class("NEW_CLASS")
            if len(vehicles) != 2:
                return False, f"Expected 2 vehicles, got {len(vehicles)}"
            
            return True, "Class added successfully"
    
    def test_vehicle_class_delete(self) -> Tuple[bool, str]:
        """Test deleting vehicle class - uses isolated test file"""
        with TempTestEnvironment() as env:
            from gui_vehicle_manager import VehicleClassesManager
            
            manager = VehicleClassesManager(env.classes_path)
            
            manager.add_class("DELETE_ME", ["DELETE_ME"], ["Test Car"])
            
            result = manager.delete_class("DELETE_ME")
            if not result:
                return False, "Failed to delete class"
            
            vehicles = manager.get_vehicles_for_class("DELETE_ME")
            if len(vehicles) != 0:
                return False, "Class still exists after delete"
            
            return True, "Class deleted successfully"
    
    def test_backup_restore(self) -> Tuple[bool, str]:
        """Test backup and restore functionality"""
        with TempTestEnvironment() as env:
            from core_aiw_utils import update_aiw_ratio
            import shutil
            
            aiw_path = env.mock_aiw_files.get("Monza")
            if not aiw_path:
                return False, "No AIW file for Monza"
            
            original_content = aiw_path.read_text()
            backup_dir = env.test_data_dir / "backups"
            
            update_aiw_ratio(aiw_path, "QualRatio", 2.0, backup_dir)
            
            backup_files = list(backup_dir.glob("*_ORIGINAL.AIW"))
            if not backup_files:
                return False, "No backup created"
            
            shutil.copy2(backup_files[0], aiw_path)
            restored_content = aiw_path.read_text()
            
            if original_content.strip() != restored_content.strip():
                return False, "Restored content differs from original"
            
            return True, "Backup and restore works correctly"
    
    def test_error_missing_aiw(self) -> Tuple[bool, str]:
        """Test handling when AIW file is missing"""
        with TempTestEnvironment() as env:
            from core_aiw_utils import update_aiw_ratio
            
            fake_path = env.base_path / "fake.AIW"
            
            result = update_aiw_ratio(fake_path, "QualRatio", 1.5)
            
            if result is None:
                return False, "Function returned None (unexpected)"
            
            return True, "Missing AIW handled correctly (no crash)"
    
    def test_error_permission_denied(self) -> Tuple[bool, str]:
        """Test handling when write permission is denied"""
        with TempTestEnvironment() as env:
            from core_aiw_utils import update_aiw_ratio
            import os
            
            aiw_path = env.mock_aiw_files.get("Monza")
            if not aiw_path:
                return False, "No AIW file for Monza"
            
            os.chmod(aiw_path, 0o444)
            
            try:
                result = update_aiw_ratio(aiw_path, "QualRatio", 1.5)
            except Exception as e:
                return False, f"Exception was raised: {e}"
            finally:
                os.chmod(aiw_path, 0o644)
            
            return True, "Permission denied handled correctly"
    
    def test_error_corrupt_race(self) -> Tuple[bool, str]:
        """Test handling of corrupt race results file"""
        with TempTestEnvironment() as env:
            from core_data_extraction import DataExtractor
            
            env.results_path.write_bytes(b"\x00\xff\x00\xff corrupt data \x00\x00")
            
            extractor = DataExtractor(env.base_path)
            
            try:
                race_data = extractor.parse_race_results(env.results_path)
                return True, "Corrupt race file handled gracefully"
            except Exception as e:
                return False, f"Exception on corrupt file: {e}"


# =============================================================================
# Main Entry Point
# =============================================================================

def main():
    parser = argparse.ArgumentParser(description='Live AI Tuner Test Automation')
    parser.add_argument('--output', type=str, help='Output report file path')
    parser.add_argument('--list', action='store_true', help='List available tests')
    
    args = parser.parse_args()
    
    if args.list:
        runner = TestRunner()
        tests = [name for name, _ in runner.__class__.__dict__.items() 
                if name.startswith('test_')]
        print("Available tests:")
        for test in sorted(tests):
            print(f"  - {test}")
        return 0
    
    # Run once
    runner = TestRunner()
    runner.run_all_tests()
    runner.print_report()
    
    if args.output:
        output_path = Path(args.output)
        runner.save_report(output_path)
        print(f"\nReport saved to: {output_path}")
    
    return 1 if runner.get_report()["failed"] > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
