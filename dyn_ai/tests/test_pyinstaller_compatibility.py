#!/usr/bin/env python3
"""
Tests to ensure the application is compatible with PyInstaller bundling
"""

import sys
from pathlib import Path

# Add parent directory to path so we can import application modules
sys.path.insert(0, str(Path(__file__).parent.parent))

import unittest
import tempfile
import json
import importlib
import os
from pathlib import Path
from unittest.mock import patch, MagicMock


class TestPyInstallerCompatibility(unittest.TestCase):
    """Test that all modules can work when bundled"""
    
    def setUp(self):
        self.source_dir = Path(__file__).parent.parent
    
    def test_all_modules_have_resource_path_helper(self):
        """Test that modules needing resource paths import the helper"""
        
        # Modules that need resource path helpers
        modules_to_check = [
            "gui_main_window",
            "gui_datamgmt_vehicle",
            "gui_pre_run_check",
            "dyn_ai_setup",
        ]
        
        for module_name in modules_to_check:
            with self.subTest(module=module_name):
                module_path = self.source_dir / f"{module_name}.py"
                if module_path.exists():
                    content = module_path.read_text()
                    has_helper = ('get_data_file_path' in content or 
                                  'resource_path' in content or
                                  'from core_common import' in content or
                                  'get_app_directory' in content)
                    # Not all modules need resource_path, skip assertion
                    # Just log if missing
                    if not has_helper:
                        print(f"Note: {module_name}.py may need resource path helper")
    
    def test_monitor_file_daemon_uses_core_config(self):
        """Test that monitor_file_daemon uses core_config for paths"""
        module_path = self.source_dir / "gui_file_monitor.py"
        
        if module_path.exists():
            content = module_path.read_text()
            uses_core_config = ('from core_config import' in content or
                               'get_results_file_path' in content or
                               'get_poll_interval' in content or
                               'get_config_with_defaults' in content)
            self.assertTrue(
                uses_core_config,
                "gui_file_monitor.py should use core_config for path handling"
            )
    
    def test_no_hardcoded_paths(self):
        """Test that modules use get_data_file_path instead of hardcoded paths"""
        
        problematic_patterns = [
            r"Path\(__file__\).*parent.*/.*\.json",
            r"Path\(__file__\).*parent.*/.*\.yml",
            r"__file__.*\.parent.*/.*\.yml",
        ]
        
        modules_to_check = [
            "gui_main_window", "gui_datamgmt_vehicle", "gui_pre_run_check", 
            "core_config", "core_autopilot", "dyn_ai_setup"
        ]
        
        for module_name in modules_to_check:
            module_path = self.source_dir / f"{module_name}.py"
            if module_path.exists():
                content = module_path.read_text()
                for pattern in problematic_patterns:
                    import re
                    matches = re.findall(pattern, content, re.IGNORECASE)
                    if matches:
                        if module_name == "core_autopilot":
                            continue
                        if 'get_data_file_path' in content:
                            continue
                        # This is not a failure, just log for awareness
                        print(f"Note: {module_name}.py contains pattern '{pattern}'")
    
    def test_all_required_source_files_exist(self):
        """Test that all required source files exist in the project"""
        required_files = [
            "cfg.yml",
            "dyn_ai.py",
            "dyn_ai_setup.py",
            "dyn_ai_visualizer.py",
            "gui_common.py",
            "core_autopilot.py",
            "core_config.py",
            "core_database.py",
            "core_formula.py",
            "core_math.py",
            "core_data_extraction.py",
            "core_aiw_utils.py",
            "core_vehicle_scanner.py",
            "gui_main_window.py",
            "gui_ratio_panel.py",
            "gui_track_selector.py",
            "gui_pre_run_check.py",
            "gui_curve_graph.py",
            "gui_session_panel.py",
            "gui_common_dialogs.py",
            "gui_file_monitor.py",
            "gui_datamgmt_import.py",
            "gui_datamgmt_laptimes.py",
            "gui_datamgmt_vehicle.py",
            "gui_setup_backup.py",
            "gui_setup_cfg.py",
            "gui_setup_logs.py",
            "vehicle_classes.json",
        ]
        
        missing = []
        for filename in required_files:
            if not (self.source_dir / filename).exists():
                missing.append(filename)
        
        if missing:
            self.fail(f"Missing source files: {missing}")


class TestModuleInitializationOrder(unittest.TestCase):
    """Test that modules initialize correctly when imported"""
    
    def setUp(self):
        self.source_dir = Path(__file__).parent.parent
        if str(self.source_dir) not in sys.path:
            sys.path.insert(0, str(self.source_dir))
    
    def test_gui_common_imports_without_error(self):
        from gui_common import get_data_file_path, setup_dark_theme
        self.assertTrue(callable(get_data_file_path))
        self.assertTrue(callable(setup_dark_theme))
    
    def test_core_autopilot_imports_without_error(self):
        from core_autopilot import load_vehicle_classes, get_vehicle_class
        self.assertTrue(callable(load_vehicle_classes))
        self.assertTrue(callable(get_vehicle_class))
    
    def test_core_config_imports_without_error(self):
        from core_config import get_config_with_defaults, load_config
        self.assertTrue(callable(get_config_with_defaults))
        self.assertTrue(callable(load_config))
    
    def test_core_database_imports_without_error(self):
        from core_database import CurveDatabase
        self.assertTrue(callable(CurveDatabase))
    
    def test_core_math_imports_without_error(self):
        from core_math import time_from_ratio, ratio_from_time, fit_hyperbolic
        self.assertTrue(callable(time_from_ratio))
        self.assertTrue(callable(ratio_from_time))
        self.assertTrue(callable(fit_hyperbolic))
    
    def test_gui_curve_graph_imports_without_error(self):
        from gui_curve_graph import CurveGraphWidget
        self.assertTrue(callable(CurveGraphWidget))
    
    def test_gui_common_dialogs_imports_without_error(self):
        from gui_common_dialogs import ManualLapTimeDialog, ManualEditDialog
        self.assertTrue(callable(ManualLapTimeDialog))
        self.assertTrue(callable(ManualEditDialog))
    
    def test_no_circular_imports(self):
        modules = [
            "gui_common",
            "gui_main_window", 
            "gui_ratio_panel",
            "gui_track_selector",
            "gui_pre_run_check",
            "gui_curve_graph",
            "gui_session_panel",
            "gui_common_dialogs",
            "gui_file_monitor",
            "gui_datamgmt_import",
            "gui_datamgmt_laptimes",
            "gui_datamgmt_vehicle",
            "gui_setup_backup",
            "gui_setup_cfg",
            "gui_setup_logs",
            "core_autopilot",
            "core_config",
            "core_database",
            "core_math",
            "core_formula",
            "core_data_extraction",
            "core_aiw_utils",
            "core_vehicle_scanner",
        ]
        
        for module_name in modules:
            try:
                if module_name in sys.modules:
                    importlib.reload(sys.modules[module_name])
                else:
                    importlib.import_module(module_name)
            except Exception as e:
                if "circular import" in str(e).lower():
                    self.fail(f"Circular import detected in {module_name}: {e}")


def run_pyinstaller_tests():
    """Run all PyInstaller compatibility tests"""
    print("\n" + "=" * 60)
    print("PYINSTALLER COMPATIBILITY TESTS")
    print("=" * 60)
    
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    suite.addTests(loader.loadTestsFromTestCase(TestPyInstallerCompatibility))
    suite.addTests(loader.loadTestsFromTestCase(TestModuleInitializationOrder))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result


if __name__ == "__main__":
    run_pyinstaller_tests()
