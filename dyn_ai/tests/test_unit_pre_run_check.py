#!/usr/bin/env python3
"""
Unit tests for pre-run check dialog PLR file validation
"""

import sys
from pathlib import Path

# Add parent directory to path so we can import application modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import os
import re
from pathlib import Path
from typing import Tuple

from test_base import BaseTestCase
from core_config import update_base_path, get_base_path, get_config_with_defaults


class TestPreRunCheckPLR(BaseTestCase):
    """Test pre-run check PLR file validation"""
    
    def setUp(self):
        super().setUp()
        userdata_dir = self.temp_env.base_path / "UserData"
        userdata_dir.mkdir(parents=True, exist_ok=True)
        self._clear_plr_files()
    
    def tearDown(self):
        self._clear_plr_files()
        super().tearDown()
    
    def _clear_plr_files(self):
        """Clear all PLR files from UserData"""
        userdata_dir = self.temp_env.base_path / "UserData"
        if userdata_dir.exists():
            for ext in ["*.PLR", "*.plr"]:
                for f in userdata_dir.glob(ext):
                    try:
                        f.unlink()
                    except Exception:
                        pass
            for subdir in userdata_dir.iterdir():
                if subdir.is_dir():
                    for ext in ["*.PLR", "*.plr"]:
                        for f in subdir.glob(ext):
                            try:
                                f.unlink()
                            except Exception:
                                pass
                    # Also check one level deeper
                    for deeper in subdir.iterdir():
                        if deeper.is_dir():
                            for ext in ["*.PLR", "*.plr"]:
                                for f in deeper.glob(ext):
                                    try:
                                        f.unlink()
                                    except Exception:
                                        pass
    
    def _create_plr_file(self, content: str, filename: str = "TestPlayer.PLR", subdir: str = None) -> Path:
        """Create a PLR file in the test environment"""
        if subdir:
            # Split the subdir path into parts and create nested directories
            subdir_parts = subdir.split('/')
            plr_dir = self.temp_env.base_path / "UserData"
            for part in subdir_parts:
                plr_dir = plr_dir / part
            plr_dir.mkdir(parents=True, exist_ok=True)
        else:
            plr_dir = self.temp_env.base_path / "UserData"
            plr_dir.mkdir(parents=True, exist_ok=True)
        
        plr_path = plr_dir / filename
        plr_path.write_text(content, encoding='utf-8')
        return plr_path
    
    def _simulate_plr_check(self) -> Tuple[bool, str]:
        """Simulate the PLR check from PreRunCheckDialog"""
        config = get_config_with_defaults(str(self.temp_env.config_path))
        base_path = config.get('base_path', '')
        
        if not base_path:
            return False, "No base path configured in cfg.yml"
        
        base_path_obj = Path(base_path)
        
        userdata_dir = base_path_obj / "UserData"
        if not userdata_dir.exists():
            return False, "UserData directory not found"
        
        plr_path = None
        
        # First check root of UserData
        for ext in ["*.PLR", "*.plr"]:
            plr_files = sorted(list(userdata_dir.glob(ext)))
            if plr_files:
                plr_path = plr_files[0]
                break
        
        # If not found in root, check subdirectories recursively
        if not plr_path:
            for ext in ["*.PLR", "*.plr"]:
                plr_files = sorted(list(userdata_dir.rglob(ext)))
                if plr_files:
                    plr_path = plr_files[0]
                    break
        
        if not plr_path:
            return False, "No PLR file found in UserData directory"
        
        try:
            content = plr_path.read_text(encoding='utf-8', errors='ignore')
            
            pattern = r'Extra\s+Stats\s*=\s*"([^"]*)"'
            match = re.search(pattern, content, re.IGNORECASE)
            
            if not match:
                pattern_no_quotes = r'Extra\s+Stats\s*=\s*([0-9.eE+-]+)'
                match = re.search(pattern_no_quotes, content, re.IGNORECASE)
                if not match:
                    return False, f"Extra Stats setting not found in {plr_path.name}"
            
            value = match.group(1).strip()
            
            try:
                float_val = float(value)
                if float_val == 0.0:
                    return True, "Extra Stats is properly set to 0"
                else:
                    return False, f"Extra Stats is set to {value} in {plr_path.name} (must be 0)"
            except ValueError:
                if value == "0":
                    return True, "Extra Stats is properly set to 0"
                else:
                    return False, f"Extra Stats is set to '{value}' in {plr_path.name} (must be 0)"
                
        except Exception as e:
            return False, f"Error reading PLR file: {str(e)}"
    
    def test_pre_run_check_passes_with_correct_plr(self):
        """Test that pre-run check passes when PLR has Extra Stats=0"""
        self._clear_plr_files()
        plr_path = self._create_plr_file('[ Game Options ]\nExtra Stats="0"\n', filename="Good.PLR")
        
        passed, message = self._simulate_plr_check()
        
        self.assertTrue(passed, message)
    
    def test_pre_run_check_fails_with_incorrect_plr(self):
        """Test that pre-run check fails when PLR has Extra Stats=1"""
        self._clear_plr_files()
        plr_path = self._create_plr_file('[ Game Options ]\nExtra Stats="1"\n', filename="Bad.PLR")
        
        passed, message = self._simulate_plr_check()
        
        self.assertFalse(passed, "Should fail but passed")
        self.assertIn("1", message)
    
    def test_pre_run_check_finds_plr_in_subfolder(self):
        """Test that pre-run check finds PLR file in subfolder"""
        self._clear_plr_files()
        # Create PLR file in a nested subdirectory
        plr_path = self._create_plr_file(
            '[ Game Options ]\nExtra Stats="0"\n', 
            filename="SubfolderProfile.PLR", 
            subdir="Profiles/MyProfile"
        )
        
        # Verify the file was created in the correct location
        expected_path = self.temp_env.base_path / "UserData" / "Profiles" / "MyProfile" / "SubfolderProfile.PLR"
        self.assertTrue(expected_path.exists(), f"PLR file not created at {expected_path}")
        
        passed, message = self._simulate_plr_check()
        
        self.assertTrue(passed, f"Should find PLR in subfolder but failed: {message}")
    
    def test_pre_run_check_with_missing_plr(self):
        """Test that pre-run check fails when no PLR file exists"""
        self._clear_plr_files()
        
        passed, message = self._simulate_plr_check()
        
        self.assertFalse(passed, "Should fail with missing PLR file")
        self.assertIn("No PLR file found", message)
    
    def test_pre_run_check_without_userdata_directory(self):
        """Test that pre-run check fails when UserData directory doesn't exist"""
        userdata_dir = self.temp_env.base_path / "UserData"
        if userdata_dir.exists():
            import shutil
            shutil.rmtree(userdata_dir)
        
        passed, message = self._simulate_plr_check()
        
        self.assertFalse(passed, "Should fail when UserData directory missing")
        self.assertIn("UserData directory not found", message)
    
    def test_pre_run_check_plr_case_insensitive_filename(self):
        """Test that pre-run check finds PLR with different case"""
        self._clear_plr_files()
        plr_path = self._create_plr_file('[ Game Options ]\nExtra Stats="0"\n', filename="lowercase.plr")
        
        passed, message = self._simulate_plr_check()
        
        self.assertTrue(passed, message)
    
    def test_pre_run_check_plr_uppercase_extension(self):
        """Test that pre-run check finds PLR with uppercase extension"""
        self._clear_plr_files()
        plr_path = self._create_plr_file('[ Game Options ]\nExtra Stats="0"\n', filename="Uppercase.PLR")
        
        passed, message = self._simulate_plr_check()
        
        self.assertTrue(passed, message)
    
    def test_pre_run_check_plr_various_formats(self):
        """Test that pre-run check handles various formatting"""
        test_cases = [
            ('Extra Stats="0"', True),
            ('Extra Stats = "0"', True),
            ('Extra   Stats   =   "0"', True),
            ('extra stats="0"', True),
            ('Extra Stats="1"', False),
            ('Extra Stats="0.0"', True),
            ('Extra Stats="0.000"', True),
            ('Extra Stats=0', True),
            ('Extra Stats=0.0', True),
        ]
        
        for line, should_pass in test_cases:
            self._clear_plr_files()
            plr_path = self._create_plr_file(f'[ Game Options ]\n{line}\n', filename="FormatTest.PLR")
            
            passed, message = self._simulate_plr_check()
            
            if should_pass:
                self.assertTrue(passed, f"Should pass for '{line}' but failed: {message}")
            else:
                self.assertFalse(passed, f"Should fail for '{line}' but passed")
    
    def test_pre_run_check_multiple_plr_files(self):
        """Test that pre-run check uses first PLR file when multiple exist"""
        self._clear_plr_files()
        
        # Create files with specific names to ensure alphabetical order
        plr_first = self._create_plr_file('[ Game Options ]\nExtra Stats="1"\n', filename="AAA_First.PLR")
        plr_second = self._create_plr_file('[ Game Options ]\nExtra Stats="0"\n', filename="BBB_Second.PLR")
        
        passed, message = self._simulate_plr_check()
        
        # Should fail because the first file (AAA_First.PLR) has Extra Stats=1
        self.assertFalse(passed, "Should fail because first PLR (AAA_First.PLR) has Extra Stats=1")
        self.assertIn("1", message)


def run_pre_run_check_plr_tests():
    """Run all pre-run check PLR tests"""
    print("\n" + "=" * 60)
    print("PRE-RUN CHECK PLR TESTS")
    print("=" * 60)
    
    import unittest
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestPreRunCheckPLR)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


if __name__ == "__main__":
    run_pre_run_check_plr_tests()
