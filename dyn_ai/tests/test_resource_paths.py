#!/usr/bin/env python3
"""
Tests for resource path resolution in PyInstaller environment
"""

import sys
from pathlib import Path

# Add parent directory to path so we can import application modules
sys.path.insert(0, str(Path(__file__).parent.parent))

import unittest
import tempfile
import json
from pathlib import Path
from unittest.mock import patch, MagicMock


class TestResourcePaths(unittest.TestCase):
    """Test that resource paths resolve correctly in both dev and frozen modes"""
    
    def setUp(self):
        """Create a temporary directory structure mimicking PyInstaller"""
        self.temp_dir = tempfile.mkdtemp()
        self.exe_dir = Path(self.temp_dir) / "exe_dir"
        self.meipass_dir = Path(self.temp_dir) / "_MEIPASS"
        self.cwd = Path.cwd()
        
        self.exe_dir.mkdir()
        self.meipass_dir.mkdir()
        
        # Create test files
        self.test_files = ["cfg.yml", "vehicle_classes.json"]
        for filename in self.test_files:
            (self.exe_dir / filename).write_text(f"test_{filename}")
            (self.meipass_dir / filename).write_text(f"bundled_{filename}")
    
    def tearDown(self):
        """Clean up temporary directory"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_resource_path_in_dev_mode(self):
        """Test resource_path() in development mode (not frozen)"""
        # Import the function (will be added to gui_common)
        from gui_common import resource_path
        
        with patch('sys._MEIPASS', new_callable=lambda: None, create=True):
            with patch('sys.frozen', False):
                with patch('os.path.abspath', return_value=str(self.cwd)):
                    path = resource_path("test.txt")
                    # Should return cwd/test.txt
                    self.assertEqual(path, self.cwd / "test.txt")
    
    def test_resource_path_in_frozen_mode(self):
        """Test resource_path() when running as frozen executable"""
        from gui_common import resource_path
        
        with patch('sys._MEIPASS', str(self.meipass_dir)):
            with patch('sys.frozen', True):
                path = resource_path("test.txt")
                # Should return _MEIPASS/test.txt
                self.assertEqual(path, self.meipass_dir / "test.txt")
    
    def test_get_data_file_path_in_dev_mode(self):
        """Test get_data_file_path() in development mode"""
        from gui_common import get_data_file_path
        
        with patch('sys.frozen', False):
            with patch('sys.executable', str(self.exe_dir / "app.exe")):
                with patch('Path.cwd', return_value=self.cwd):
                    # File doesn't exist, should return cwd path
                    path = get_data_file_path("new_file.yml")
                    self.assertEqual(path, self.cwd / "new_file.yml")
    
    def test_get_data_file_path_in_frozen_mode_file_in_exe_dir(self):
        """Test get_data_file_path() when file exists in executable directory"""
        from gui_common import get_data_file_path
        
        with patch('sys.frozen', True):
            with patch('sys.executable', str(self.exe_dir / "app.exe")):
                path = get_data_file_path("cfg.yml")
                # Should find file in exe_dir first
                self.assertEqual(path, self.exe_dir / "cfg.yml")
                self.assertTrue(path.exists())
                self.assertEqual(path.read_text(), "test_cfg.yml")
    
    def test_get_data_file_path_in_frozen_mode_file_in_meipass(self):
        """Test get_data_file_path() when file only exists in _MEIPASS"""
        from gui_common import get_data_file_path
        
        # Remove from exe_dir
        (self.exe_dir / "vehicle_classes.json").unlink()
        
        with patch('sys.frozen', True):
            with patch('sys.executable', str(self.exe_dir / "app.exe")):
                with patch('sys._MEIPASS', str(self.meipass_dir)):
                    path = get_data_file_path("vehicle_classes.json")
                    # Should fall back to _MEIPASS
                    self.assertEqual(path, self.meipass_dir / "vehicle_classes.json")
                    self.assertTrue(path.exists())
                    self.assertEqual(path.read_text(), "bundled_vehicle_classes.json")
    
    def test_get_data_file_path_file_not_found(self):
        """Test get_data_file_path() when file doesn't exist anywhere"""
        from gui_common import get_data_file_path
        
        with patch('sys.frozen', True):
            with patch('sys.executable', str(self.exe_dir / "app.exe")):
                with patch('sys._MEIPASS', str(self.meipass_dir)):
                    path = get_data_file_path("nonexistent.txt")
                    # Should return exe_dir path as default
                    self.assertEqual(path, self.exe_dir / "nonexistent.txt")
                    self.assertFalse(path.exists())


class TestVehicleClassesPathResolution(unittest.TestCase):
    """Test that vehicle_classes.json is found correctly"""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.cwd_backup = Path.cwd()
        
    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def _create_mock_classes_file(self, dir_path: Path, content: dict):
        """Create a mock vehicle_classes.json file"""
        file_path = dir_path / "vehicle_classes.json"
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, 'w') as f:
            json.dump(content, f)
        return file_path
    
    def test_load_vehicle_classes_from_exe_dir(self):
        """Test load_vehicle_classes() finds file in executable directory"""
        from core_autopilot import load_vehicle_classes
        
        # Create mock classes file
        mock_classes = {"TestClass": {"vehicles": ["Test Car"]}}
        self._create_mock_classes_file(self.temp_dir, mock_classes)
        
        with patch('sys.frozen', True):
            with patch('sys.executable', str(Path(self.temp_dir) / "app.exe")):
                with patch('gui_common.get_data_file_path', 
                          return_value=Path(self.temp_dir) / "vehicle_classes.json"):
                    classes = load_vehicle_classes()
                    self.assertIsNotNone(classes)
                    self.assertIn("TestClass", classes)
    
    def test_load_vehicle_classes_creates_default_if_missing(self):
        """Test load_vehicle_classes() creates default file if missing"""
        from core_autopilot import load_vehicle_classes
        
        missing_dir = Path(self.temp_dir) / "missing"
        
        with patch('gui_common.get_data_file_path', 
                  return_value=missing_dir / "vehicle_classes.json"):
            classes = load_vehicle_classes()
            self.assertIsNotNone(classes)
            # Should have created the file
            self.assertTrue((missing_dir / "vehicle_classes.json").exists())
    
    def test_load_vehicle_classes_fallback_to_defaults_on_error(self):
        """Test load_vehicle_classes() falls back to defaults on error"""
        from core_autopilot import load_vehicle_classes
        
        # Create corrupted file
        corrupted_path = Path(self.temp_dir) / "vehicle_classes.json"
        corrupted_path.write_text("this is not valid json {")
        
        with patch('gui_common.get_data_file_path', return_value=corrupted_path):
            classes = load_vehicle_classes()
            self.assertIsNotNone(classes)
            # Should return defaults, not crash
            self.assertIn("Formula Cars", classes)


class TestPyInstallerBundleSimulation(unittest.TestCase):
    """Simulate PyInstaller bundle environment"""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.exe_dir = Path(self.temp_dir) / "dist"
        self.meipass_dir = self.exe_dir / "_internal"  # PyInstaller's typical _MEIPASS
        self.exe_dir.mkdir(parents=True)
        self.meipass_dir.mkdir()
        
    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def _create_bundle_structure(self):
        """Create a typical PyInstaller bundle structure"""
        # Executable
        exe_path = self.exe_dir / "dyn_ai.exe"
        exe_path.write_text("mock executable")
        
        # Bundled files in _internal (PyInstaller's _MEIPASS)
        source_files = ["cfg.yml", "vehicle_classes.json", "dyn_ai.py", 
                       "gui_common.py", "core_autopilot.py"]
        for filename in source_files:
            (self.meipass_dir / filename).write_text(f"# {filename} content")
        
        # User-editable files in exe directory (not bundled)
        (self.exe_dir / "cfg.yml").write_text("user_config: true")
        (self.exe_dir / "vehicle_classes.json").write_text('{"UserClass": {"vehicles": ["User Car"]}}')
        
        return exe_path
    
    def test_bundle_resolution_prefers_exe_dir(self):
        """Test that user files in exe directory are preferred over bundled"""
        self._create_bundle_structure()
        
        # Simulate running in frozen mode
        with patch('sys.frozen', True):
            with patch('sys.executable', str(self.exe_dir / "dyn_ai.exe")):
                with patch('sys._MEIPASS', str(self.meipass_dir)):
                    from gui_common import get_data_file_path
                    
                    # Should find user's cfg.yml in exe_dir, not bundled one
                    cfg_path = get_data_file_path("cfg.yml")
                    self.assertEqual(cfg_path, self.exe_dir / "cfg.yml")
                    self.assertEqual(cfg_path.read_text(), "user_config: true")
                    
                    # Should find user's vehicle_classes.json in exe_dir
                    classes_path = get_data_file_path("vehicle_classes.json")
                    self.assertEqual(classes_path, self.exe_dir / "vehicle_classes.json")
                    self.assertIn("UserClass", json.loads(classes_path.read_text()))
    
    def test_bundle_falls_back_to_meipass(self):
        """Test fallback to _MEIPASS when file not in exe_dir"""
        self._create_bundle_structure()
        
        # Remove user config from exe_dir
        (self.exe_dir / "cfg.yml").unlink()
        
        with patch('sys.frozen', True):
            with patch('sys.executable', str(self.exe_dir / "dyn_ai.exe")):
                with patch('sys._MEIPASS', str(self.meipass_dir)):
                    from gui_common import get_data_file_path
                    
                    # Should fall back to bundled file
                    cfg_path = get_data_file_path("cfg.yml")
                    self.assertEqual(cfg_path, self.meipass_dir / "cfg.yml")
    
    def test_full_module_import_paths(self):
        """Test that all modules can be imported and find their resources"""
        self._create_bundle_structure()
        
        # Add all required modules to the bundle simulation
        modules = [
            "gui_common", "gui_main_window", "gui_vehicle_manager", 
            "gui_advanced_settings", "gui_pre_run_check", "core_autopilot"
        ]
        for module in modules:
            (self.meipass_dir / f"{module}.py").write_text(f"# {module} content")
        
        with patch('sys.frozen', True):
            with patch('sys.executable', str(self.exe_dir / "dyn_ai.exe")):
                with patch('sys._MEIPASS', str(self.meipass_dir)):
                    # Add the temp dir to path to simulate bundled modules
                    if str(self.meipass_dir) not in sys.path:
                        sys.path.insert(0, str(self.meipass_dir))
                    
                    try:
                        # Try to import critical modules that use resource_path
                        from gui_common import get_data_file_path
                        from core_autopilot import load_vehicle_classes
                        
                        # This should work without errors
                        classes_path = get_data_file_path("vehicle_classes.json")
                        self.assertIsNotNone(classes_path)
                        
                        classes = load_vehicle_classes()
                        self.assertIsNotNone(classes)
                        
                    finally:
                        # Clean up path
                        if str(self.meipass_dir) in sys.path:
                            sys.path.remove(str(self.meipass_dir))


def run_resource_tests():
    """Run all resource path tests"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    suite.addTests(loader.loadTestsFromTestCase(TestResourcePaths))
    suite.addTests(loader.loadTestsFromTestCase(TestVehicleClassesPathResolution))
    suite.addTests(loader.loadTestsFromTestCase(TestPyInstallerBundleSimulation))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result


if __name__ == "__main__":
    run_resource_tests()
