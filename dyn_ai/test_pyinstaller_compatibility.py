#!/usr/bin/env python3
"""
Tests to ensure the application is compatible with PyInstaller bundling
"""

import unittest
import sys
import subprocess
import tempfile
import json
from pathlib import Path
from unittest.mock import patch, MagicMock


class TestPyInstallerCompatibility(unittest.TestCase):
    """Test that all modules can work when bundled"""
    
    def test_all_modules_have_resource_path_helper(self):
        """Test that modules needing resource paths import the helper"""
        modules_to_check = [
            "gui_main_window",
            "gui_vehicle_manager", 
            "gui_advanced_settings",
            "gui_pre_run_check",
            "core_autopilot"
        ]
        
        for module_name in modules_to_check:
            with self.subTest(module=module_name):
                # Check that the module can be imported and has necessary imports
                # This is a static analysis test
                module_path = Path(__file__).parent / f"{module_name}.py"
                if module_path.exists():
                    content = module_path.read_text()
                    self.assertIn(
                        "get_data_file_path", content,
                        f"{module_name}.py should import get_data_file_path"
                    )
    
    def test_no_hardcoded_paths(self):
        """Test that no modules use Path(__file__).parent for data files"""
        problematic_patterns = [
            r"Path\(__file__\).*parent.*/.*\.json",
            r"Path\(__file__\).*parent.*/.*\.yml",
            r"__file__.*\.parent.*/.*\.yml",
        ]
        
        modules_to_check = [
            "gui_main_window", "gui_vehicle_manager", "gui_advanced_settings",
            "gui_pre_run_check", "core_autopilot", "core_config"
        ]
        
        for module_name in modules_to_check:
            module_path = Path(__file__).parent / f"{module_name}.py"
            if module_path.exists():
                content = module_path.read_text()
                for pattern in problematic_patterns:
                    import re
                    matches = re.findall(pattern, content, re.IGNORECASE)
                    # Allow exceptions for specific cases
                    if matches and "vehicle_classes.json" not in str(matches):
                        self.fail(
                            f"{module_name}.py contains hardcoded path pattern '{pattern}': {matches}"
                        )


class TestBundledFileAccess(unittest.TestCase):
    """Test that bundled files can be accessed correctly"""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.bundle_dir = Path(self.temp_dir) / "_MEIPASS"
        self.bundle_dir.mkdir(parents=True)
        
    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def create_bundled_file(self, filename: str, content: str):
        """Create a file in the simulated bundle directory"""
        file_path = self.bundle_dir / filename
        file_path.write_text(content)
        return file_path
    
    def test_sys_meipass_exists_when_frozen(self):
        """Test that sys._MEIPASS exists in frozen mode"""
        with patch('sys.frozen', True):
            with patch('sys._MEIPASS', str(self.bundle_dir)):
                from gui_common import resource_path
                # Should use _MEIPASS
                path = resource_path("test.txt")
                self.assertEqual(path, self.bundle_dir / "test.txt")
    
    def test_sys_meipass_fallback_when_not_frozen(self):
        """Test fallback when sys._MEIPASS doesn't exist"""
        with patch('sys.frozen', False):
            with patch('sys._MEIPASS', new_callable=lambda: None):
                with patch('os.path.abspath', return_value=str(self.temp_dir)):
                    from gui_common import resource_path
                    path = resource_path("test.txt")
                    self.assertEqual(path, Path(self.temp_dir) / "test.txt")
    
    def test_all_bundled_files_are_included(self):
        """Test that all required files would be bundled"""
        required_files = [
            "cfg.yml",
            "vehicle_classes.json",
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
            "monitor_file_daemon.py",
            "dyn_ai_data_manager.py",
        ]
        
        # In a real test, you would check the PyInstaller spec file
        # For now, just verify files exist in source
        source_dir = Path(__file__).parent
        missing = []
        for filename in required_files:
            if not (source_dir / filename).exists():
                missing.append(filename)
        
        if missing:
            self.fail(f"Missing source files: {missing}")


class TestModuleInitializationOrder(unittest.TestCase):
    """Test that modules initialize correctly when imported"""
    
    def test_gui_common_imports_without_error(self):
        """Test that gui_common can be imported without errors"""
        try:
            from gui_common import get_data_file_path, resource_path
            self.assertTrue(callable(get_data_file_path))
            self.assertTrue(callable(resource_path))
        except Exception as e:
            self.fail(f"gui_common import failed: {e}")
    
    def test_core_autopilot_imports_without_error(self):
        """Test that core_autopilot can be imported without errors"""
        try:
            from core_autopilot import load_vehicle_classes, get_vehicle_class
            self.assertTrue(callable(load_vehicle_classes))
            self.assertTrue(callable(get_vehicle_class))
        except Exception as e:
            self.fail(f"core_autopilot import failed: {e}")
    
    def test_circular_imports(self):
        """Test for circular imports between modules"""
        modules = [
            "gui_common",
            "gui_main_window", 
            "gui_vehicle_manager",
            "gui_advanced_settings",
            "gui_pre_run_check",
            "core_autopilot",
            "core_config",
        ]
        
        import importlib
        for module_name in modules:
            try:
                # Force reload to check for circular import issues
                if module_name in sys.modules:
                    importlib.reload(sys.modules[module_name])
                else:
                    importlib.import_module(module_name)
            except Exception as e:
                if "circular import" in str(e).lower():
                    self.fail(f"Circular import detected in {module_name}: {e}")


def run_pyinstaller_tests():
    """Run all PyInstaller compatibility tests"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    suite.addTests(loader.loadTestsFromTestCase(TestPyInstallerCompatibility))
    suite.addTests(loader.loadTestsFromTestCase(TestBundledFileAccess))
    suite.addTests(loader.loadTestsFromTestCase(TestModuleInitializationOrder))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result


if __name__ == "__main__":
    run_pyinstaller_tests()
