#!/usr/bin/env python3
"""
Unit tests for AIW file utilities
"""

import sys
from pathlib import Path

# Add parent directory to path so we can import application modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import os
import shutil

from test_base import BaseTestCase
from core_aiw_utils import (
    find_aiw_file_by_track, find_aiw_file_from_path,
    update_aiw_ratio, ensure_aiw_has_ratios
)


class TestAIWUtils(BaseTestCase):
    """Test AIW file utilities"""
    
    def test_find_aiw_file_by_track(self):
        """Test finding AIW file by track name"""
        found = find_aiw_file_by_track("Monza", self.temp_env.base_path)
        self.assertIsNotNone(found)
        self.assertEqual(found, self.temp_env.mock_aiw_files.get("Monza"))
        
        not_found = find_aiw_file_by_track("NonExistentTrack", self.temp_env.base_path)
        self.assertIsNone(not_found)
    
    def test_find_aiw_file_by_track_case_insensitive(self):
        """Test case-insensitive track name matching"""
        found = find_aiw_file_by_track("monza", self.temp_env.base_path)
        self.assertIsNotNone(found)
    
    def test_find_aiw_file_from_path(self):
        """Test finding AIW file from relative path"""
        rel_path = "GameData/Locations/Monza/4Monza.AIW"
        found = find_aiw_file_from_path(rel_path, self.temp_env.base_path)
        self.assertIsNotNone(found)
    
    def test_find_aiw_file_from_path_case_insensitive(self):
        """Test case-insensitive path matching"""
        rel_path_upper = "GAMEDATA/LOCATIONS/MONZA/4MONZA.AIW"
        found = find_aiw_file_from_path(rel_path_upper, self.temp_env.base_path)
        self.assertIsNotNone(found)
    
    def test_find_aiw_file_from_path_with_backslashes(self):
        """Test path with backslashes"""
        rel_path = "GameData\\Locations\\Monza\\4Monza.AIW"
        found = find_aiw_file_from_path(rel_path, self.temp_env.base_path)
        self.assertIsNotNone(found)
    
    def test_update_aiw_ratio(self):
        """Test updating ratios in AIW file"""
        aiw_path = self.temp_env.mock_aiw_files.get("Monza")
        backup_dir = self.temp_env.test_data_dir / "backups"
        
        result = update_aiw_ratio(aiw_path, "QualRatio", 1.234567, backup_dir)
        self.assertTrue(result)
        
        content = aiw_path.read_text()
        self.assertIn("QualRatio = 1.234567", content)
    
    def test_update_race_ratio(self):
        """Test updating RaceRatio in AIW file"""
        aiw_path = self.temp_env.mock_aiw_files.get("Monza")
        
        result = update_aiw_ratio(aiw_path, "RaceRatio", 0.876543)
        self.assertTrue(result)
        
        content = aiw_path.read_text()
        self.assertIn("RaceRatio = 0.876543", content)
    
    def test_ensure_aiw_has_ratios(self):
        """Test that missing ratios are added"""
        aiw_path = self.temp_env.mock_aiw_files.get("Monza")
        
        content = aiw_path.read_text()
        content_no_ratios = content.replace("QualRatio = 1.000000\n", "")
        content_no_ratios = content_no_ratios.replace("RaceRatio = 1.000000\n", "")
        aiw_path.write_text(content_no_ratios)
        
        result = ensure_aiw_has_ratios(aiw_path)
        self.assertTrue(result)
        
        content = aiw_path.read_text()
        self.assertIn("QualRatio = 1.000000", content)
        self.assertIn("RaceRatio = 1.000000", content)
    
    def test_update_nonexistent_aiw(self):
        """Test updating a non-existent AIW file"""
        fake_path = self.temp_env.base_path / "fake.AIW"
        result = update_aiw_ratio(fake_path, "QualRatio", 1.0)
        self.assertFalse(result)
    
    def test_readonly_aiw_handling(self):
        """Test handling of read-only AIW files"""
        aiw_path = self.temp_env.mock_aiw_files.get("Monza")
        
        os.chmod(aiw_path, 0o444)
        
        try:
            result = update_aiw_ratio(aiw_path, "QualRatio", 1.5)
            self.assertFalse(result)
        finally:
            os.chmod(aiw_path, 0o644)
    
    def test_backup_creation(self):
        """Test that backup is created when updating"""
        aiw_path = self.temp_env.mock_aiw_files.get("Monza")
        backup_dir = self.temp_env.test_data_dir / "backups"
        
        update_aiw_ratio(aiw_path, "QualRatio", 2.0, backup_dir)
        
        backup_files = list(backup_dir.glob("*_ORIGINAL.AIW"))
        self.assertEqual(len(backup_files), 1)
    
    def test_restore_from_backup(self):
        """Test restoring from backup"""
        aiw_path = self.temp_env.mock_aiw_files.get("Monza")
        backup_dir = self.temp_env.test_data_dir / "backups"
        
        original_content = aiw_path.read_text()
        
        update_aiw_ratio(aiw_path, "QualRatio", 2.0, backup_dir)
        
        backup_files = list(backup_dir.glob("*_ORIGINAL.AIW"))
        shutil.copy2(backup_files[0], aiw_path)
        
        restored_content = aiw_path.read_text()
        self.assertEqual(original_content.strip(), restored_content.strip())
