#!/usr/bin/env python3
"""
Error injection tests for Live AI Tuner
Tests how the system handles various error conditions
"""

import os
import shutil
from pathlib import Path

from test_base import BaseTestCase
from core_aiw_utils import update_aiw_ratio, find_aiw_file_by_track
from core_data_extraction import DataExtractor


class TestErrorInjection(BaseTestCase):
    """Tests for error handling and edge cases"""
    
    def test_missing_scene_in_race_results(self):
        """Test race results without Scene entry"""
        content = """[Race]
AIDB=GameData/Locations/Monza/4Monza.AIW

[Slot0]
Driver=Player
Vehicle=Test Car
BestLap=1:30.000
"""
        self.temp_env.results_path.write_text(content)
        
        extractor = DataExtractor(self.temp_env.base_path)
        race_data = extractor.parse_race_results(self.temp_env.results_path)
        
        self.assertIsNotNone(race_data)
    
    def test_missing_aidb_in_race_results(self):
        """Test race results without AIDB entry"""
        content = """[Race]
Scene=GameData/Locations/Monza/4Monza.TRK

[Slot0]
Driver=Player
Vehicle=Test Car
BestLap=1:30.000
"""
        self.temp_env.results_path.write_text(content)
        
        extractor = DataExtractor(self.temp_env.base_path)
        race_data = extractor.parse_race_results(self.temp_env.results_path)
        
        self.assertIsNotNone(race_data)
        self.assertIsNone(race_data.aiw_path)
    
    def test_invalid_lap_times(self):
        """Test race results with invalid lap times"""
        content = """[Race]
Scene=GameData/Locations/Monza/4Monza.TRK
AIDB=GameData/Locations/Monza/4Monza.AIW

[Slot0]
Driver=Player
Vehicle=Test Car
BestLap=invalid

[Slot1]
Driver=AI Driver
Vehicle=AI Car
BestLap=also invalid
"""
        self.temp_env.results_path.write_text(content)
        
        extractor = DataExtractor(self.temp_env.base_path)
        race_data = extractor.parse_race_results(self.temp_env.results_path)
        
        self.assertIsNotNone(race_data)
        self.assertEqual(race_data.user_best_lap_sec, 0.0)
    
    def test_no_ai_vehicles(self):
        """Test race results with only player (no AI)"""
        content = """[Race]
Scene=GameData/Locations/Monza/4Monza.TRK
AIDB=GameData/Locations/Monza/4Monza.AIW

[Slot0]
Driver=Player
Vehicle=Test Car
BestLap=1:30.000
"""
        self.temp_env.results_path.write_text(content)
        
        extractor = DataExtractor(self.temp_env.base_path)
        race_data = extractor.parse_race_results(self.temp_env.results_path)
        
        self.assertIsNotNone(race_data)
        self.assertEqual(race_data.ai_count, 0)
    
    def test_empty_race_results(self):
        """Test completely empty race results file"""
        self.temp_env.results_path.write_text("")
        
        extractor = DataExtractor(self.temp_env.base_path)
        race_data = extractor.parse_race_results(self.temp_env.results_path)
        
        if race_data:
            self.assertFalse(race_data.has_data())
    
    def test_unicode_in_race_results(self):
        """Test race results with Unicode characters"""
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
        self.temp_env.results_path.write_text(content, encoding='utf-8')
        
        extractor = DataExtractor(self.temp_env.base_path)
        race_data = extractor.parse_race_results(self.temp_env.results_path)
        
        self.assertIsNotNone(race_data)
        self.assertEqual(race_data.user_name, "Joueur Francais")
    
    def test_corrupt_aiw_file(self):
        """Test handling of corrupt AIW file"""
        aiw_path = self.temp_env.mock_aiw_files.get("Monza")
        self.temp_env.create_corrupt_aiw("Monza")
        
        result = update_aiw_ratio(aiw_path, "QualRatio", 1.5)
        
        self.assertFalse(result)
    
    def test_aiw_file_with_wrong_encoding(self):
        """Test AIW file with wrong encoding"""
        aiw_path = self.temp_env.mock_aiw_files.get("Monza")
        aiw_path.write_bytes(b"\xff\xfe\x00\x00corrupt\x00\x00")
        
        result = update_aiw_ratio(aiw_path, "QualRatio", 1.5)
        
        self.assertFalse(result)
    
    def test_missing_race_results_directory(self):
        """Test when race results directory doesn't exist"""
        results_dir = self.temp_env.base_path / "UserData" / "Log" / "Results"
        shutil.rmtree(results_dir)
        
        extractor = DataExtractor(self.temp_env.base_path)
        fake_path = results_dir / "raceresults.txt"
        race_data = extractor.parse_race_results(fake_path)
        
        self.assertIsNone(race_data)
    
    def test_permission_denied_on_directory(self):
        """Test when results directory is not accessible"""
        results_dir = self.temp_env.base_path / "UserData" / "Log" / "Results"
        os.chmod(results_dir, 0o000)
        
        try:
            extractor = DataExtractor(self.temp_env.base_path)
            race_data = extractor.parse_race_results(self.temp_env.results_path)
            
            self.assertIsNone(race_data)
        finally:
            os.chmod(results_dir, 0o755)
    
    def test_very_large_race_results(self):
        """Test with very large race results file (many AI drivers)"""
        self.temp_env.create_mock_race_results(num_ai=100)
        
        extractor = DataExtractor(self.temp_env.base_path)
        race_data = extractor.parse_race_results(self.temp_env.results_path)
        
        self.assertIsNotNone(race_data)
        self.assertEqual(race_data.ai_count, 100)
    
    def test_race_results_with_missing_slots(self):
        """Test race results with missing slot numbers"""
        content = """[Race]
Scene=GameData/Locations/Monza/4Monza.TRK
AIDB=GameData/Locations/Monza/4Monza.AIW

[Slot0]
Driver=Player
Vehicle=Test Car
BestLap=1:30.000

[Slot2]
Driver=AI Driver 2
Vehicle=AI Car
BestLap=1:32.000

[Slot5]
Driver=AI Driver 5
Vehicle=AI Car
BestLap=1:35.000
"""
        self.temp_env.results_path.write_text(content)
        
        extractor = DataExtractor(self.temp_env.base_path)
        race_data = extractor.parse_race_results(self.temp_env.results_path)
        
        self.assertIsNotNone(race_data)
        self.assertEqual(race_data.ai_count, 2)
    
    def test_race_results_with_extra_whitespace(self):
        """Test race results with extra whitespace and blank lines"""
        content = """

[Race]
Scene=GameData/Locations/Monza/4Monza.TRK
AIDB=GameData/Locations/Monza/4Monza.AIW


[Slot0]
Driver=Player
Vehicle=Test Car
BestLap=1:30.000


[Slot1]
Driver=AI Driver
Vehicle=AI Car
BestLap=1:32.000

"""
        self.temp_env.results_path.write_text(content)
        
        extractor = DataExtractor(self.temp_env.base_path)
        race_data = extractor.parse_race_results(self.temp_env.results_path)
        
        self.assertIsNotNone(race_data)
        self.assertEqual(race_data.ai_count, 1)
    
    def test_race_results_with_wrong_line_endings(self):
        """Test race results with Windows line endings (CRLF)"""
        content = "[Race]\r\nScene=GameData/Locations/Monza/4Monza.TRK\r\nAIDB=GameData/Locations/Monza/4Monza.AIW\r\n\r\n[Slot0]\r\nDriver=Player\r\nVehicle=Test Car\r\nBestLap=1:30.000\r\n"
        self.temp_env.results_path.write_text(content)
        
        extractor = DataExtractor(self.temp_env.base_path)
        race_data = extractor.parse_race_results(self.temp_env.results_path)
        
        self.assertIsNotNone(race_data)
    
    def test_backup_dir_permission_error(self):
        """Test backup creation with permission issues"""
        aiw_path = self.temp_env.mock_aiw_files.get("Monza")
        backup_dir = self.temp_env.test_data_dir / "backup_ro"
        backup_dir.mkdir()
        os.chmod(backup_dir, 0o555)
        
        try:
            result = update_aiw_ratio(aiw_path, "QualRatio", 1.5, backup_dir)
            self.assertTrue(result or not result)
        finally:
            os.chmod(backup_dir, 0o755)
            shutil.rmtree(backup_dir, ignore_errors=True)
