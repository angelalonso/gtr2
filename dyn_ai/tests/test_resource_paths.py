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
import importlib
from pathlib import Path
from unittest.mock import patch, MagicMock


class TestResourcePaths(unittest.TestCase):
    """Test that resource paths resolve correctly in both dev and frozen modes"""
    
    def setUp(self):
        """Create a temporary directory structure mimicking PyInstaller"""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.exe_dir = self.temp_dir / "exe_dir"
        self.meipass_dir = self.temp_dir / "_MEIPASS"
        self.cwd = Path.cwd()
        
        self.exe_dir.mkdir(parents=True, exist_ok=True)
        self.meipass_dir.mkdir(parents=True, exist_ok=True)
        
        # Create test files
        self.test_files = ["cfg.yml", "vehicle_classes.json"]
        for filename in self.test_files:
            (self.exe_dir / filename).write_text(f"test_{filename}")
            (self.meipass_dir / filename).write_text(f"bundled_{filename}")
        
        # Save original sys module
        self.original_sys = sys.modules['sys']
    
    def tearDown(self):
        """Clean up temporary directory"""
        import shutil
        shutil.rmtree(str(self.temp_dir), ignore_errors=True)
        # Restore original sys
        sys.modules['sys'] = self.original_sys
        if 'gui_common' in sys.modules:
            importlib.reload(sys.modules['gui_common'])
    
    def _patch_sys_module(self, frozen=True, meipass_path=None, executable_path=None):
        """Helper to patch sys module without using patch()"""
        mock_sys = type('MockSys', (), {})()
        mock_sys.frozen = frozen
        if meipass_path:
            mock_sys._MEIPASS = str(meipass_path)
        if executable_path:
            mock_sys.executable = str(executable_path)
        # Copy over essential attributes
        mock_sys.path = self.original_sys.path.copy() if hasattr(self.original_sys, 'path') else []
        mock_sys.modules = self.original_sys.modules
        sys.modules['sys'] = mock_sys
        return mock_sys
    
    def _restore_sys_module(self):
        """Restore original sys module"""
        sys.modules['sys'] = self.original_sys
    
    def test_resource_path_in_dev_mode(self):
        """Test resource_path() in development mode (not frozen)"""
        self._patch_sys_module(frozen=False)
        
        try:
            if 'gui_common' in sys.modules:
                importlib.reload(sys.modules['gui_common'])
            
            from gui_common import resource_path
            
            with patch('os.path.abspath', return_value=str(self.cwd)):
                path = resource_path("test.txt")
                self.assertEqual(path, self.cwd / "test.txt")
        finally:
            self._restore_sys_module()
            if 'gui_common' in sys.modules:
                importlib.reload(sys.modules['gui_common'])
    
    def test_resource_path_in_frozen_mode(self):
        """Test resource_path() when running as frozen executable"""
        self._patch_sys_module(frozen=True, meipass_path=self.meipass_dir)
        
        try:
            if 'gui_common' in sys.modules:
                importlib.reload(sys.modules['gui_common'])
            
            from gui_common import resource_path
            path = resource_path("test.txt")
            self.assertEqual(path, self.meipass_dir / "test.txt")
        finally:
            self._restore_sys_module()
            if 'gui_common' in sys.modules:
                importlib.reload(sys.modules['gui_common'])
    
    def test_get_data_file_path_in_dev_mode(self):
        """Test get_data_file_path() in development mode"""
        self._patch_sys_module(frozen=False, executable_path=self.exe_dir / "app.exe")
        
        try:
            if 'gui_common' in sys.modules:
                importlib.reload(sys.modules['gui_common'])
            
            from gui_common import get_data_file_path
            
            # Mock Path.cwd without using patch('Path.cwd')
            with patch('pathlib.Path.cwd', return_value=self.cwd):
                path = get_data_file_path("new_file.yml")
                self.assertEqual(path, self.cwd / "new_file.yml")
        finally:
            self._restore_sys_module()
            if 'gui_common' in sys.modules:
                importlib.reload(sys.modules['gui_common'])
    
    def test_get_data_file_path_in_frozen_mode_file_in_exe_dir(self):
        """Test get_data_file_path() when file exists in executable directory"""
        self._patch_sys_module(frozen=True, meipass_path=self.meipass_dir, 
                               executable_path=self.exe_dir / "app.exe")
        
        try:
            if 'gui_common' in sys.modules:
                importlib.reload(sys.modules['gui_common'])
            
            from gui_common import get_data_file_path
            
            path = get_data_file_path("cfg.yml")
            self.assertEqual(path, self.exe_dir / "cfg.yml")
            self.assertTrue(path.exists())
            self.assertEqual(path.read_text(), "test_cfg.yml")
        finally:
            self._restore_sys_module()
            if 'gui_common' in sys.modules:
                importlib.reload(sys.modules['gui_common'])
    
    def test_get_data_file_path_in_frozen_mode_file_in_meipass(self):
        """Test get_data_file_path() when file only exists in _MEIPASS"""
        # Remove from exe_dir
        (self.exe_dir / "vehicle_classes.json").unlink()
        
        self._patch_sys_module(frozen=True, meipass_path=self.meipass_dir,
                               executable_path=self.exe_dir / "app.exe")
        
        try:
            if 'gui_common' in sys.modules:
                importlib.reload(sys.modules['gui_common'])
            
            from gui_common import get_data_file_path
            
            path = get_data_file_path("vehicle_classes.json")
            self.assertEqual(path, self.meipass_dir / "vehicle_classes.json")
            self.assertTrue(path.exists())
            self.assertEqual(path.read_text(), "bundled_vehicle_classes.json")
        finally:
            self._restore_sys_module()
            if 'gui_common' in sys.modules:
                importlib.reload(sys.modules['gui_common'])
    
    def test_get_data_file_path_file_not_found(self):
        """Test get_data_file_path() when file doesn't exist anywhere"""
        self._patch_sys_module(frozen=True, meipass_path=self.meipass_dir,
                               executable_path=self.exe_dir / "app.exe")
        
        try:
            if 'gui_common' in sys.modules:
                importlib.reload(sys.modules['gui_common'])
            
            from gui_common import get_data_file_path
            
            path = get_data_file_path("nonexistent.txt")
            self.assertEqual(path, self.exe_dir / "nonexistent.txt")
            self.assertFalse(path.exists())
        finally:
            self._restore_sys_module()
            if 'gui_common' in sys.modules:
                importlib.reload(sys.modules['gui_common'])


class TestVehicleClassesPathResolution(unittest.TestCase):
    """Test that vehicle_classes.json is found correctly"""
    
    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp())
        self.original_sys = sys.modules['sys']
        
    def tearDown(self):
        import shutil
        shutil.rmtree(str(self.temp_dir), ignore_errors=True)
        sys.modules['sys'] = self.original_sys
    
    def _patch_sys_module(self, frozen=True, meipass_path=None, executable_path=None):
        mock_sys = type('MockSys', (), {})()
        mock_sys.frozen = frozen
        if meipass_path:
            mock_sys._MEIPASS = str(meipass_path)
        if executable_path:
            mock_sys.executable = str(executable_path)
        if hasattr(self.original_sys, 'path'):
            mock_sys.path = self.original_sys.path.copy()
        if hasattr(self.original_sys, 'modules'):
            mock_sys.modules = self.original_sys.modules
        sys.modules['sys'] = mock_sys
    
    def _restore_sys_module(self):
        sys.modules['sys'] = self.original_sys
    
    def _create_mock_classes_file(self, dir_path: Path, content: dict):
        file_path = dir_path / "vehicle_classes.json"
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, 'w') as f:
            json.dump(content, f)
        return file_path
    
    def test_load_vehicle_classes_from_exe_dir(self):
        """Test load_vehicle_classes() finds file in executable directory"""
        mock_classes = {"TestClass": {"vehicles": ["Test Car"]}}
        self._create_mock_classes_file(self.temp_dir, mock_classes)
        
        self._patch_sys_module(frozen=True, meipass_path=self.temp_dir / "_MEIPASS",
                               executable_path=self.temp_dir / "app.exe")
        
        try:
            if 'gui_common' in sys.modules:
                importlib.reload(sys.modules['gui_common'])
            if 'core_autopilot' in sys.modules:
                importlib.reload(sys.modules['core_autopilot'])
            
            from core_autopilot import load_vehicle_classes
            
            with patch('gui_common.get_data_file_path', 
                      return_value=self.temp_dir / "vehicle_classes.json"):
                classes = load_vehicle_classes()
                self.assertIsNotNone(classes)
                self.assertIn("TestClass", classes)
        finally:
            self._restore_sys_module()
    
    def test_load_vehicle_classes_creates_default_if_missing(self):
        """Test load_vehicle_classes() creates default file if missing"""
        missing_dir = self.temp_dir / "missing"
        
        self._patch_sys_module(frozen=True, meipass_path=missing_dir / "_MEIPASS",
                               executable_path=missing_dir / "app.exe")
        
        try:
            if 'gui_common' in sys.modules:
                importlib.reload(sys.modules['gui_common'])
            if 'core_autopilot' in sys.modules:
                importlib.reload(sys.modules['core_autopilot'])
            
            from core_autopilot import load_vehicle_classes
            
            with patch('gui_common.get_data_file_path', 
                      return_value=missing_dir / "vehicle_classes.json"):
                classes = load_vehicle_classes()
                self.assertIsNotNone(classes)
        finally:
            self._restore_sys_module()
    
    def test_load_vehicle_classes_fallback_to_defaults_on_error(self):
        """Test load_vehicle_classes() falls back to defaults on error"""
        corrupted_path = self.temp_dir / "vehicle_classes.json"
        corrupted_path.write_text("this is not valid json {")
        
        self._patch_sys_module(frozen=True, meipass_path=self.temp_dir / "_MEIPASS",
                               executable_path=self.temp_dir / "app.exe")
        
        try:
            if 'gui_common' in sys.modules:
                importlib.reload(sys.modules['gui_common'])
            if 'core_autopilot' in sys.modules:
                importlib.reload(sys.modules['core_autopilot'])
            
            from core_autopilot import load_vehicle_classes
            
            with patch('gui_common.get_data_file_path', return_value=corrupted_path):
                classes = load_vehicle_classes()
                self.assertIsNotNone(classes)
                self.assertIn("Formula Cars", classes)
        finally:
            self._restore_sys_module()


class TestPyInstallerBundleSimulation(unittest.TestCase):
    """Simulate PyInstaller bundle environment"""
    
    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp())
        self.exe_dir = self.temp_dir / "dist"
        self.meipass_dir = self.exe_dir / "_internal"
        self.exe_dir.mkdir(parents=True, exist_ok=True)
        self.meipass_dir.mkdir(parents=True, exist_ok=True)
        self.original_sys = sys.modules['sys']
        
    def tearDown(self):
        import shutil
        shutil.rmtree(str(self.temp_dir), ignore_errors=True)
        sys.modules['sys'] = self.original_sys
    
    def _patch_sys_module(self, frozen=True, meipass_path=None, executable_path=None):
        mock_sys = type('MockSys', (), {})()
        mock_sys.frozen = frozen
        if meipass_path:
            mock_sys._MEIPASS = str(meipass_path)
        if executable_path:
            mock_sys.executable = str(executable_path)
        if hasattr(self.original_sys, 'path'):
            mock_sys.path = self.original_sys.path.copy()
        if hasattr(self.original_sys, 'modules'):
            mock_sys.modules = self.original_sys.modules
        sys.modules['sys'] = mock_sys
    
    def _restore_sys_module(self):
        sys.modules['sys'] = self.original_sys
    
    def _create_bundle_structure(self):
        exe_path = self.exe_dir / "dyn_ai.exe"
        exe_path.write_text("mock executable")
        
        source_files = ["cfg.yml", "vehicle_classes.json", "dyn_ai.py", 
                       "gui_common.py", "core_autopilot.py"]
        for filename in source_files:
            (self.meipass_dir / filename).write_text(f"# {filename} content")
        
        (self.exe_dir / "cfg.yml").write_text("user_config: true")
        (self.exe_dir / "vehicle_classes.json").write_text('{"UserClass": {"vehicles": ["User Car"]}}')
        
        return exe_path
    
    def test_bundle_resolution_prefers_exe_dir(self):
        """Test that user files in exe directory are preferred over bundled"""
        self._create_bundle_structure()
        
        self._patch_sys_module(frozen=True, meipass_path=self.meipass_dir,
                               executable_path=self.exe_dir / "dyn_ai.exe")
        
        try:
            if 'gui_common' in sys.modules:
                importlib.reload(sys.modules['gui_common'])
            
            from gui_common import get_data_file_path
            
            cfg_path = get_data_file_path("cfg.yml")
            self.assertEqual(cfg_path, self.exe_dir / "cfg.yml")
            self.assertEqual(cfg_path.read_text(), "user_config: true")
            
            classes_path = get_data_file_path("vehicle_classes.json")
            self.assertEqual(classes_path, self.exe_dir / "vehicle_classes.json")
            self.assertIn("UserClass", json.loads(classes_path.read_text()))
        finally:
            self._restore_sys_module()
    
    def test_bundle_falls_back_to_meipass(self):
        """Test fallback to _MEIPASS when file not in exe_dir"""
        self._create_bundle_structure()
        
        (self.exe_dir / "cfg.yml").unlink()
        
        self._patch_sys_module(frozen=True, meipass_path=self.meipass_dir,
                               executable_path=self.exe_dir / "dyn_ai.exe")
        
        try:
            if 'gui_common' in sys.modules:
                importlib.reload(sys.modules['gui_common'])
            
            from gui_common import get_data_file_path
            
            cfg_path = get_data_file_path("cfg.yml")
            self.assertEqual(cfg_path, self.meipass_dir / "cfg.yml")
        finally:
            self._restore_sys_module()
    
    def test_full_module_import_paths(self):
        """Test that all modules can be imported and find their resources"""
        self._create_bundle_structure()
        
        modules = [
            "gui_common", "gui_main_window", "gui_vehicle_manager", 
            "gui_advanced_settings", "gui_pre_run_check", "core_autopilot",
            "gui_data_manager", "gui_data_manager_common", "gui_data_manager_database",
            "gui_data_manager_import", "gui_data_manager_vehicle"
        ]
        for module in modules:
            (self.meipass_dir / f"{module}.py").write_text(f"# {module} content")
        
        self._patch_sys_module(frozen=True, meipass_path=self.meipass_dir,
                               executable_path=self.exe_dir / "dyn_ai.exe")
        
        try:
            if str(self.meipass_dir) not in sys.path:
                sys.path.insert(0, str(self.meipass_dir))
            
            try:
                from gui_common import get_data_file_path
                from core_autopilot import load_vehicle_classes
                
                classes_path = get_data_file_path("vehicle_classes.json")
                self.assertIsNotNone(classes_path)
                
                classes = load_vehicle_classes()
                self.assertIsNotNone(classes)
            finally:
                if str(self.meipass_dir) in sys.path:
                    sys.path.remove(str(self.meipass_dir))
        finally:
            self._restore_sys_module()


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
