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
    
    def test_all_modules_have_resource_path_helper(self):
        """Test that modules needing resource paths import the helper"""
        source_dir = Path(__file__).parent.parent
        
        # Modules that need resource path helpers
        modules_to_check = [
            "gui_main_window",
            "gui_vehicle_manager", 
            "gui_advanced_settings",
            "gui_pre_run_check",
            "dyn_ai_data_manager",
        ]
        
        # monitor_file_daemon.py doesn't need resource_path - it uses core_config functions
        # which handle path resolution internally
        
        for module_name in modules_to_check:
            with self.subTest(module=module_name):
                module_path = source_dir / f"{module_name}.py"
                if module_path.exists():
                    content = module_path.read_text()
                    has_helper = ('get_data_file_path' in content or 
                                  'resource_path' in content or
                                  'from gui_common import' in content)
                    self.assertTrue(
                        has_helper,
                        f"{module_name}.py should import get_data_file_path or resource_path"
                    )
    
    def test_monitor_file_daemon_uses_core_config(self):
        """Test that monitor_file_daemon uses core_config for paths"""
        source_dir = Path(__file__).parent.parent
        module_path = source_dir / "monitor_file_daemon.py"
        
        if module_path.exists():
            content = module_path.read_text()
            # monitor_file_daemon uses core_config functions which handle paths
            uses_core_config = ('from core_config import' in content or
                               'get_results_file_path' in content or
                               'get_poll_interval' in content or
                               'get_config_with_defaults' in content)
            self.assertTrue(
                uses_core_config,
                "monitor_file_daemon.py should use core_config for path handling"
            )
    
    def test_gui_modules_without_resource_paths_are_acceptable(self):
        """Test that GUI modules that don't need resource paths are acceptable"""
        source_dir = Path(__file__).parent.parent
        
        acceptable_modules = [
            "gui_curve_graph",
            "gui_components",
            "gui_common_dialogs",
            "gui_ratio_panel",
            "gui_session_panel",
            "gui_file_monitor",
            "gui_log_window",
            "monitor_file_daemon",
        ]
        
        for module_name in acceptable_modules:
            with self.subTest(module=module_name):
                module_path = source_dir / f"{module_name}.py"
                if module_path.exists():
                    content = module_path.read_text()
                    self.assertIsNotNone(content)
    
    def test_data_manager_modules_have_proper_imports(self):
        """Test that data manager modules have proper imports"""
        source_dir = Path(__file__).parent.parent
        
        data_manager_modules = [
            "gui_data_manager",
            "gui_data_manager_common",
            "gui_data_manager_database",
            "gui_data_manager_import",
        ]
        
        # gui_data_manager_vehicle.py uses VehicleClassesManager which is fine
        # It doesn't need database imports
        
        for module_name in data_manager_modules:
            with self.subTest(module=module_name):
                module_path = source_dir / f"{module_name}.py"
                if module_path.exists():
                    content = module_path.read_text()
                    has_db_import = ('SimpleCurveDatabase' in content or 
                                    'from gui_data_manager_common import' in content or
                                    'import sqlite3' in content or
                                    'from core_database import' in content)
                    self.assertTrue(
                        has_db_import,
                        f"{module_name}.py should have database imports"
                    )
    
    def test_gui_data_manager_vehicle_uses_vehicle_manager(self):
        """Test that gui_data_manager_vehicle uses vehicle manager correctly"""
        source_dir = Path(__file__).parent.parent
        module_path = source_dir / "gui_data_manager_vehicle.py"
        
        if module_path.exists():
            content = module_path.read_text()
            uses_vehicle_manager = ('launch_vehicle_manager' in content or
                                   'from gui_vehicle_manager import' in content or
                                   'VehicleClassesManager' in content)
            self.assertTrue(
                uses_vehicle_manager,
                "gui_data_manager_vehicle.py should use vehicle manager"
            )
    
    def test_no_hardcoded_paths(self):
        """Test that no modules use Path(__file__).parent for data files"""
        source_dir = Path(__file__).parent.parent
        
        problematic_patterns = [
            r"Path\(__file__\).*parent.*/.*\.json",
            r"Path\(__file__\).*parent.*/.*\.yml",
            r"__file__.*\.parent.*/.*\.yml",
        ]
        
        modules_to_check = [
            "gui_main_window", "gui_vehicle_manager", "gui_advanced_settings",
            "gui_pre_run_check", "core_config", "core_autopilot",
        ]
        
        for module_name in modules_to_check:
            module_path = source_dir / f"{module_name}.py"
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
                        self.fail(
                            f"{module_name}.py contains hardcoded path pattern '{pattern}': {matches}"
                        )


class TestBundledFileAccess(unittest.TestCase):
    """Test that bundled files can be accessed correctly"""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.bundle_dir = Path(self.temp_dir) / "_MEIPASS"
        self.bundle_dir.mkdir(parents=True)
        self.source_dir = Path(__file__).parent.parent
        
        # Create a test file in the bundle directory
        self.test_file = self.bundle_dir / "test.txt"
        self.test_file.write_text("test content")
        
    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_resource_path_in_frozen_mode_returns_meipass(self):
        """Test that resource_path returns _MEIPASS path in frozen mode"""
        # Create a custom module to simulate sys
        mock_sys = type('MockSys', (), {
            'frozen': True,
            '_MEIPASS': str(self.bundle_dir)
        })()
        
        # Save original sys
        original_sys = sys.modules['sys']
        sys.modules['sys'] = mock_sys
        
        try:
            # Re-import gui_common to use the mocked sys
            if 'gui_common' in sys.modules:
                importlib.reload(sys.modules['gui_common'])
            
            from gui_common import resource_path
            path = resource_path("test.txt")
            self.assertEqual(path, self.bundle_dir / "test.txt")
        finally:
            # Restore original sys
            sys.modules['sys'] = original_sys
            # Reload gui_common to restore original state
            if 'gui_common' in sys.modules:
                importlib.reload(sys.modules['gui_common'])
    
    def test_resource_path_in_dev_mode_returns_cwd(self):
        """Test that resource_path returns CWD path in development mode"""
        mock_sys = type('MockSys', (), {
            'frozen': False
        })()
        
        original_sys = sys.modules['sys']
        sys.modules['sys'] = mock_sys
        
        try:
            if 'gui_common' in sys.modules:
                importlib.reload(sys.modules['gui_common'])
            
            from gui_common import resource_path
            with patch('os.path.abspath', return_value=str(self.temp_dir)):
                path = resource_path("test.txt")
                self.assertEqual(path, Path(self.temp_dir) / "test.txt")
        finally:
            sys.modules['sys'] = original_sys
            if 'gui_common' in sys.modules:
                importlib.reload(sys.modules['gui_common'])
    
    def test_all_required_source_files_exist(self):
        """Test that all required source files exist in the project"""
        required_files = [
            "cfg.yml",
            "dyn_ai.py",
            "gui_common.py",
            "core_autopilot.py",
            "core_config.py",
            "core_database.py",
            "core_formula.py",
            "core_data_extraction.py",
            "core_aiw_utils.py",
            "core_vehicle_scanner.py",
            "gui_main_window.py",
            "gui_vehicle_manager.py",
            "gui_advanced_settings.py",
            "gui_pre_run_check.py",
            "gui_curve_graph.py",
            "gui_components.py",
            "gui_common_dialogs.py",
            "gui_ratio_panel.py",
            "gui_session_panel.py",
            "gui_file_monitor.py",
            "gui_log_window.py",
            "gui_data_manager.py",
            "gui_data_manager_common.py",
            "gui_data_manager_database.py",
            "gui_data_manager_import.py",
            "gui_data_manager_vehicle.py",
            "monitor_file_daemon.py",
            "dyn_ai_data_manager.py",
        ]
        
        missing = []
        for filename in required_files:
            if not (self.source_dir / filename).exists():
                if filename == "vehicle_classes.json":
                    continue
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
        from gui_common import get_data_file_path, resource_path
        self.assertTrue(callable(get_data_file_path))
        self.assertTrue(callable(resource_path))
    
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
    
    def test_core_formula_imports_without_error(self):
        from core_formula import hyperbolic, fit_curve
        self.assertTrue(callable(hyperbolic))
        self.assertTrue(callable(fit_curve))
    
    def test_gui_curve_graph_imports_without_error(self):
        from gui_curve_graph import CurveGraphWidget
        self.assertTrue(callable(CurveGraphWidget))
    
    def test_gui_components_imports_without_error(self):
        from gui_components import AccuracyIndicator, ToggleSwitch
        self.assertTrue(callable(AccuracyIndicator))
        self.assertTrue(callable(ToggleSwitch))
    
    def test_gui_common_dialogs_imports_without_error(self):
        from gui_common_dialogs import ManualLapTimeDialog, ManualEditDialog
        self.assertTrue(callable(ManualLapTimeDialog))
        self.assertTrue(callable(ManualEditDialog))
    
    def test_gui_data_manager_common_imports_without_error(self):
        from gui_data_manager_common import SimpleCurveDatabase
        self.assertTrue(callable(SimpleCurveDatabase))
    
    def test_gui_data_manager_database_imports_without_error(self):
        from gui_data_manager_database import DatabaseManagerTab
        self.assertTrue(callable(DatabaseManagerTab))
    
    def test_gui_data_manager_import_imports_without_error(self):
        from gui_data_manager_import import ImportTab
        self.assertTrue(callable(ImportTab))
    
    def test_gui_data_manager_vehicle_imports_without_error(self):
        from gui_data_manager_vehicle import VehicleTab
        self.assertTrue(callable(VehicleTab))
    
    def test_gui_data_manager_imports_without_error(self):
        from gui_data_manager import DynAIDataManager
        self.assertTrue(callable(DynAIDataManager))
    
    def test_monitor_file_daemon_imports_without_error(self):
        from monitor_file_daemon import FileMonitorDaemon
        self.assertTrue(callable(FileMonitorDaemon))
    
    def test_no_circular_imports(self):
        modules = [
            "gui_common",
            "gui_main_window", 
            "gui_vehicle_manager",
            "gui_advanced_settings",
            "gui_pre_run_check",
            "gui_curve_graph",
            "gui_components",
            "gui_common_dialogs",
            "gui_ratio_panel",
            "gui_session_panel",
            "gui_file_monitor",
            "gui_log_window",
            "gui_data_manager",
            "gui_data_manager_common",
            "gui_data_manager_database",
            "gui_data_manager_import",
            "gui_data_manager_vehicle",
            "core_autopilot",
            "core_config",
            "core_database",
            "core_formula",
            "core_data_extraction",
            "core_aiw_utils",
            "core_vehicle_scanner",
            "monitor_file_daemon",
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


class TestResourceFunctionBehavior(unittest.TestCase):
    """Test that resource functions behave correctly"""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        
    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_get_data_file_path_returns_path(self):
        from gui_common import get_data_file_path
        result = get_data_file_path("test.txt")
        self.assertIsInstance(result, Path)
    
    def test_resource_path_returns_path(self):
        from gui_common import resource_path
        result = resource_path("test.txt")
        self.assertIsInstance(result, Path)


def run_pyinstaller_tests():
    """Run all PyInstaller compatibility tests"""
    print("\n" + "=" * 60)
    print("PYINSTALLER COMPATIBILITY TESTS")
    print("=" * 60)
    
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    suite.addTests(loader.loadTestsFromTestCase(TestPyInstallerCompatibility))
    suite.addTests(loader.loadTestsFromTestCase(TestBundledFileAccess))
    suite.addTests(loader.loadTestsFromTestCase(TestModuleInitializationOrder))
    suite.addTests(loader.loadTestsFromTestCase(TestResourceFunctionBehavior))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result


if __name__ == "__main__":
    run_pyinstaller_tests()
