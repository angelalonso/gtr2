#!/usr/bin/env python3
"""
Unit tests for PLR file checking functionality
Tests the pre-run check for Extra Stats setting in GTR2 PLR files
"""

import os
import shutil
import re
from pathlib import Path
from typing import Tuple

from test_base import BaseTestCase
from core_config import update_base_path, get_base_path, get_config_with_defaults


class TestPLRCheck(BaseTestCase):
    """Test PLR file checking functionality"""
    
    def setUp(self):
        super().setUp()
        # Ensure UserData directory exists
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
    
    def _create_plr_file(self, content: str, filename: str = "TestPlayer.PLR", subdir: str = None) -> Path:
        """Create a PLR file in the test environment"""
        if subdir:
            plr_dir = self.temp_env.base_path / "UserData" / subdir
        else:
            plr_dir = self.temp_env.base_path / "UserData"
        plr_dir.mkdir(parents=True, exist_ok=True)
        
        plr_path = plr_dir / filename
        plr_path.write_text(content, encoding='utf-8')
        return plr_path
    
    def _check_plr_file(self, plr_path: Path) -> Tuple[bool, str]:
        """Simulate the PLR check from PreRunCheckDialog"""
        try:
            content = plr_path.read_text(encoding='utf-8', errors='ignore')
            
            pattern = r'Extra\s+Stats\s*=\s*"([^"]*)"'
            match = re.search(pattern, content, re.IGNORECASE)
            
            if not match:
                pattern_no_quotes = r'Extra\s+Stats\s*=\s*([0-9.eE+-]+)'
                match = re.search(pattern_no_quotes, content, re.IGNORECASE)
                if not match:
                    return False, "Extra Stats setting not found"
            
            value = match.group(1).strip()
            
            try:
                float_val = float(value)
                if float_val == 0.0:
                    return True, "Extra Stats is 0"
                else:
                    return False, f"Extra Stats is set to {value} (must be 0)"
            except ValueError:
                if value == "0":
                    return True, "Extra Stats is 0"
                else:
                    return False, f"Extra Stats is set to '{value}' (must be 0)"
                
        except Exception as e:
            return False, f"Error reading PLR file: {str(e)}"
    
    def _find_plr_file(self) -> Tuple[Path, str]:
        """Simulate finding PLR file from PreRunCheckDialog"""
        base_path = get_base_path(str(self.temp_env.config_path))
        
        if not base_path:
            return None, "Base path not configured"
        
        userdata_dir = base_path / "UserData"
        if not userdata_dir.exists():
            return None, f"UserData directory not found: {userdata_dir}"
        
        # Use sorted to ensure consistent order
        for ext in ["*.PLR", "*.plr"]:
            plr_files = sorted(list(userdata_dir.glob(ext)))
            if plr_files:
                return plr_files[0], f"Found PLR file: {plr_files[0].name}"
        
        for item in sorted(userdata_dir.iterdir()):
            if item.is_dir():
                for ext in ["*.PLR", "*.plr"]:
                    plr_files = sorted(list(item.glob(ext)))
                    if plr_files:
                        return plr_files[0], f"Found PLR file: {plr_files[0].name} (in {item.name})"
        
        return None, "No .PLR file found in UserData directory"
    
    def _fix_plr_file(self, plr_path: Path) -> bool:
        """Simulate fixing PLR file from PreRunCheckDialog"""
        try:
            content = plr_path.read_text(encoding='utf-8', errors='ignore')
            
            # Check if already correct
            pattern = r'Extra\s+Stats\s*=\s*"0"'
            if re.search(pattern, content, re.IGNORECASE):
                return True  # Already correct, no fix needed
            
            pattern_no_quotes = r'Extra\s+Stats\s*=\s*0'
            if re.search(pattern_no_quotes, content, re.IGNORECASE):
                return True  # Already correct, no fix needed
            
            # Create backup
            backup_path = plr_path.with_suffix(plr_path.suffix + ".backup")
            backup_content = content
            backup_path.write_text(backup_content, encoding='utf-8')
            
            # Fix the content
            pattern_quotes = r'(Extra\s+Stats\s*=\s*)"[^"]*"'
            replacement = r'\1"0"'
            
            new_content = re.sub(pattern_quotes, replacement, content, flags=re.IGNORECASE)
            
            pattern_no_quotes = r'(Extra\s+Stats\s*=\s*)([0-9.eE+-]+)'
            new_content = re.sub(pattern_no_quotes, r'\g<1>"0"', new_content, flags=re.IGNORECASE)
            
            if new_content == content:
                # No pattern found, add the setting
                new_content = content + '\nExtra Stats="0"\n'
            
            plr_path.write_text(new_content, encoding='utf-8')
            return True
            
        except Exception as e:
            return False
    
    def test_plr_file_with_extra_stats_zero(self):
        """Test PLR file with Extra Stats="0" (should pass)"""
        plr_content = '[ Game Options ]\nExtra Stats="0"\n'
        plr_path = self._create_plr_file(plr_content)
        
        passed, message = self._check_plr_file(plr_path)
        self.assertTrue(passed, message)
    
    def test_plr_file_with_extra_stats_one(self):
        """Test PLR file with Extra Stats="1" (should fail)"""
        plr_content = '[ Game Options ]\nExtra Stats="1"\n'
        plr_path = self._create_plr_file(plr_content)
        
        passed, message = self._check_plr_file(plr_path)
        self.assertFalse(passed, "Should fail but passed")
        self.assertIn("1", message)
    
    def test_plr_file_with_extra_stats_zero_point_zero(self):
        """Test PLR file with Extra Stats="0.0" (should pass)"""
        plr_content = '[ Game Options ]\nExtra Stats="0.0"\n'
        plr_path = self._create_plr_file(plr_content)
        
        passed, message = self._check_plr_file(plr_path)
        self.assertTrue(passed, message)
    
    def test_plr_file_with_extra_stats_zero_point_zero_zero_zero(self):
        """Test PLR file with Extra Stats="0.00000" (should pass)"""
        plr_content = '[ Game Options ]\nExtra Stats="0.00000"\n'
        plr_path = self._create_plr_file(plr_content)
        
        passed, message = self._check_plr_file(plr_path)
        self.assertTrue(passed, message)
    
    def test_plr_file_with_extra_stats_one_point_zero(self):
        """Test PLR file with Extra Stats="1.0" (should fail)"""
        plr_content = '[ Game Options ]\nExtra Stats="1.0"\n'
        plr_path = self._create_plr_file(plr_content)
        
        passed, message = self._check_plr_file(plr_path)
        self.assertFalse(passed, "Should fail but passed")
    
    def test_plr_file_without_extra_stats(self):
        """Test PLR file missing Extra Stats setting (should fail)"""
        plr_content = '[ Game Options ]\nDamage Multiplier="100"\n'
        plr_path = self._create_plr_file(plr_content)
        
        passed, message = self._check_plr_file(plr_path)
        self.assertFalse(passed, "Should fail but passed")
        self.assertIn("not found", message.lower())
    
    def test_plr_file_with_lowercase_key(self):
        """Test PLR file with lowercase 'extra stats' (should still work)"""
        plr_content = '[ Game Options ]\nextra stats="0"\n'
        plr_path = self._create_plr_file(plr_content)
        
        passed, message = self._check_plr_file(plr_path)
        self.assertTrue(passed, message)
    
    def test_plr_file_with_mixed_case(self):
        """Test PLR file with mixed case 'Extra stats' (should still work)"""
        plr_content = '[ Game Options ]\nExtra stats="0"\n'
        plr_path = self._create_plr_file(plr_content)
        
        passed, message = self._check_plr_file(plr_path)
        self.assertTrue(passed, message)
    
    def test_plr_file_with_extra_spaces(self):
        """Test PLR file with multiple spaces around equals sign"""
        plr_content = '[ Game Options ]\nExtra   Stats    =    "0"\n'
        plr_path = self._create_plr_file(plr_content)
        
        passed, message = self._check_plr_file(plr_path)
        self.assertTrue(passed, message)
    
    def test_plr_file_without_quotes(self):
        """Test PLR file with Extra Stats without quotes"""
        plr_content = '[ Game Options ]\nExtra Stats=0\n'
        plr_path = self._create_plr_file(plr_content)
        
        passed, message = self._check_plr_file(plr_path)
        self.assertTrue(passed, message)
    
    def test_plr_file_in_subdirectory(self):
        """Test PLR file in a subdirectory (nested profile)"""
        plr_content = '[ Game Options ]\nExtra Stats="0"\n'
        plr_path = self._create_plr_file(plr_content, filename="Profile.PLR", subdir="Player1")
        
        passed, message = self._check_plr_file(plr_path)
        self.assertTrue(passed, message)
    
    def test_plr_file_uppercase_extension(self):
        """Test PLR file with .PLR uppercase extension"""
        plr_content = '[ Game Options ]\nExtra Stats="0"\n'
        plr_path = self._create_plr_file(plr_content, filename="Test.PLR")
        
        passed, message = self._check_plr_file(plr_path)
        self.assertTrue(passed, message)
    
    def test_plr_file_lowercase_extension(self):
        """Test PLR file with .plr lowercase extension"""
        plr_content = '[ Game Options ]\nExtra Stats="0"\n'
        plr_path = self._create_plr_file(plr_content, filename="Test.plr")
        
        passed, message = self._check_plr_file(plr_path)
        self.assertTrue(passed, message)
    
    def test_plr_file_with_trailing_comment(self):
        """Test PLR file with trailing comment"""
        plr_content = '[ Game Options ]\nExtra Stats="0"  ; This is the setting\n'
        plr_path = self._create_plr_file(plr_content)
        
        passed, message = self._check_plr_file(plr_path)
        self.assertTrue(passed, message)
    
    def test_empty_plr_file(self):
        """Test empty PLR file (should fail)"""
        plr_content = ''
        plr_path = self._create_plr_file(plr_content)
        
        passed, message = self._check_plr_file(plr_path)
        self.assertFalse(passed, "Empty PLR file should fail")
    
    def test_plr_file_with_extra_stats_two(self):
        """Test PLR file with Extra Stats="2" (should fail)"""
        plr_content = '[ Game Options ]\nExtra Stats="2"\n'
        plr_path = self._create_plr_file(plr_content)
        
        passed, message = self._check_plr_file(plr_path)
        self.assertFalse(passed, "Should fail but passed")
    
    def test_plr_file_with_extra_stats_negative_one(self):
        """Test PLR file with Extra Stats="-1" (should fail)"""
        plr_content = '[ Game Options ]\nExtra Stats="-1"\n'
        plr_path = self._create_plr_file(plr_content)
        
        passed, message = self._check_plr_file(plr_path)
        self.assertFalse(passed, "Should fail but passed")
    
    def test_find_plr_file_in_userdata_root(self):
        """Test finding PLR file directly in UserData directory"""
        plr_content = '[ Game Options ]\nExtra Stats="0"\n'
        expected_filename = "FindTest.PLR"
        plr_path = self._create_plr_file(plr_content, filename=expected_filename)
        
        found_path, message = self._find_plr_file()
        
        self.assertIsNotNone(found_path, message)
        self.assertEqual(found_path.name, expected_filename)
    
    def test_find_plr_file_in_subdirectory(self):
        """Test finding PLR file in subdirectory of UserData"""
        plr_content = '[ Game Options ]\nExtra Stats="0"\n'
        expected_filename = "SubdirProfile.PLR"
        plr_path = self._create_plr_file(plr_content, filename=expected_filename, subdir="PlayerProfile")
        
        found_path, message = self._find_plr_file()
        
        self.assertIsNotNone(found_path, message)
        self.assertEqual(found_path.name, expected_filename)
    
    def test_find_plr_file_case_insensitive(self):
        """Test finding PLR file with different case"""
        plr_content = '[ Game Options ]\nExtra Stats="0"\n'
        plr_path = self._create_plr_file(plr_content, filename="CaseTest.plr")
        
        found_path, message = self._find_plr_file()
        
        self.assertIsNotNone(found_path, message)
        self.assertEqual(found_path.name.lower(), "casetest.plr")
    
    def test_multiple_plr_files(self):
        """Test finding PLR file when multiple exist (should find first alphabetically)"""
        self._clear_plr_files()
        # Create files with specific names to ensure order
        plr_first = self._create_plr_file('[ Game Options ]\nExtra Stats="1"\n', filename="AAA_First.PLR")
        plr_second = self._create_plr_file('[ Game Options ]\nExtra Stats="0"\n', filename="BBB_Second.PLR")
        
        found_path, message = self._find_plr_file()
        
        self.assertIsNotNone(found_path, message)
        # Should find the first alphabetically (AAA_First.PLR)
        self.assertEqual(found_path.name, "AAA_First.PLR")
    
    def test_no_plr_file_exists(self):
        """Test when no PLR file exists (should fail gracefully)"""
        self._clear_plr_files()
        
        found_path, message = self._find_plr_file()
        
        self.assertIsNone(found_path)
        self.assertIn("No .PLR file found", message)
    
    def test_fix_plr_file_from_one_to_zero(self):
        """Test fixing PLR file from Extra Stats="1" to "0"""
        plr_content = '[ Game Options ]\nExtra Stats="1"\n'
        plr_path = self._create_plr_file(plr_content)
        
        success = self._fix_plr_file(plr_path)
        self.assertTrue(success, "Failed to fix PLR file")
        
        fixed_content = plr_path.read_text()
        self.assertIn('Extra Stats="0"', fixed_content)
        self.assertNotIn('Extra Stats="1"', fixed_content)
    
    def test_fix_plr_file_from_one_point_zero_to_zero(self):
        """Test fixing PLR file from Extra Stats="1.0" to "0"""
        plr_content = '[ Game Options ]\nExtra Stats="1.0"\n'
        plr_path = self._create_plr_file(plr_content)
        
        success = self._fix_plr_file(plr_path)
        self.assertTrue(success, "Failed to fix PLR file")
        
        fixed_content = plr_path.read_text()
        self.assertIn('Extra Stats="0"', fixed_content)
    
    def test_fix_plr_file_creates_backup(self):
        """Test that fixing PLR file creates a backup"""
        plr_content = '[ Game Options ]\nExtra Stats="1"\n'
        plr_path = self._create_plr_file(plr_content)
        
        success = self._fix_plr_file(plr_path)
        self.assertTrue(success, "Failed to fix PLR file")
        
        backup_path = plr_path.with_suffix(plr_path.suffix + ".backup")
        self.assertTrue(backup_path.exists(), "Backup file not created")
        
        backup_content = backup_path.read_text()
        self.assertIn('Extra Stats="1"', backup_content)
    
    def test_fix_already_correct_plr_file(self):
        """Test fixing PLR file that already has Extra Stats="0" (should succeed)"""
        plr_content = '[ Game Options ]\nExtra Stats="0"\n'
        plr_path = self._create_plr_file(plr_content)
        
        success = self._fix_plr_file(plr_path)
        self.assertTrue(success, "Processing already correct PLR file should succeed")
        
        fixed_content = plr_path.read_text()
        self.assertIn('Extra Stats="0"', fixed_content)
    
    def test_fix_already_correct_plr_file_no_quotes(self):
        """Test fixing PLR file that already has Extra Stats=0 without quotes (should succeed)"""
        plr_content = '[ Game Options ]\nExtra Stats=0\n'
        plr_path = self._create_plr_file(plr_content)
        
        success = self._fix_plr_file(plr_path)
        self.assertTrue(success, "Processing already correct PLR file should succeed")
    
    def test_real_gtr2_plr_format(self):
        """Test with real GTR2 PLR file format"""
        plr_content = '[ Game Options ]\nExtra Stats="0"\nWrite Shared Memory="0"\n'
        plr_path = self._create_plr_file(plr_content)
        
        passed, message = self._check_plr_file(plr_path)
        self.assertTrue(passed, message)
    
    def test_real_gtr2_plr_format_with_bad_extra_stats(self):
        """Test with real GTR2 PLR format but Extra Stats="1" (should fail)"""
        plr_content = '[ Game Options ]\nExtra Stats="1"\nWrite Shared Memory="0"\n'
        plr_path = self._create_plr_file(plr_content)
        
        passed, message = self._check_plr_file(plr_path)
        self.assertFalse(passed, "Should fail but passed")
    
    def test_plr_file_with_unicode_characters(self):
        """Test PLR file with Unicode characters"""
        plr_content = '[ Game Options ]\nExtra Stats="0"\nDriver Name="José Driver"\n'
        plr_path = self._create_plr_file(plr_content)
        
        passed, message = self._check_plr_file(plr_path)
        self.assertTrue(passed, message)


def run_plr_tests():
    """Run all PLR tests and report results"""
    print("\n" + "=" * 60)
    print("PLR FILE CHECK TESTS")
    print("=" * 60)
    
    import unittest
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestPLRCheck)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


if __name__ == "__main__":
    run_plr_tests()
