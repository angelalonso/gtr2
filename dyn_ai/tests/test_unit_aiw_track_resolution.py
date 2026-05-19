#!/usr/bin/env python3
"""
Unit tests for AIW file resolution with similarly named tracks
Tests that exact matches are preferred over partial matches
"""

import sys
from pathlib import Path

# Add parent directory to path so we can import application modules
sys.path.insert(0, str(Path(__file__).parent.parent))

import unittest
import shutil
from pathlib import Path

from test_base import BaseTestCase
from core_aiw_utils import find_aiw_file_by_track, find_aiw_file_from_path
from core_data_extraction import DataExtractor


class TestAIWTrackResolution(BaseTestCase):
    """Test that the correct AIW file is selected with similarly named tracks"""
    
    def setUp(self):
        super().setUp()
        self._create_similar_tracks()
    
    def _create_similar_tracks(self):
        """Create tracks with similar names to test resolution priority"""
        locations_dir = self.temp_env.base_path / "GameData" / "Locations"
        
        # Create Testtrack folder with Testtrack.AIW
        track1_dir = locations_dir / "Testtrack"
        track1_dir.mkdir(parents=True, exist_ok=True)
        track1_aiw = track1_dir / "Testtrack.AIW"
        track1_aiw.write_text("""[Waypoint]
BestAdjust = 1.000000
QualRatio = 1.000000
RaceRatio = 1.000000
NumWaypoints = 100
""")
        self.temp_env.mock_aiw_files["Testtrack"] = track1_aiw
        
        # Create Testtrack2 folder with Testtrack2.AIW
        track2_dir = locations_dir / "Testtrack2"
        track2_dir.mkdir(parents=True, exist_ok=True)
        track2_aiw = track2_dir / "Testtrack2.AIW"
        track2_aiw.write_text("""[Waypoint]
BestAdjust = 1.000000
QualRatio = 2.000000
RaceRatio = 2.000000
NumWaypoints = 100
""")
        self.temp_env.mock_aiw_files["Testtrack2"] = track2_aiw
        
        # Create alternative AIW name (Testtrack.AIW inside Testtrack2 folder)
        track2_alt_aiw = track2_dir / "Testtrack.AIW"
        track2_alt_aiw.write_text("""[Waypoint]
BestAdjust = 1.000000
QualRatio = 3.000000
RaceRatio = 3.000000
NumWaypoints = 100
""")
    
    def test_exact_folder_match_preferred(self):
        """Test that when searching for 'Testtrack2', the exact folder match is preferred"""
        found = find_aiw_file_by_track("Testtrack2", self.temp_env.base_path)
        
        self.assertIsNotNone(found)
        # Should find AIW in Testtrack2 folder
        self.assertEqual(found.parent.name, "Testtrack2")
    
    def test_exact_folder_match_does_not_return_partial(self):
        """Test that searching for 'Testtrack2' does not return 'Testtrack' folder"""
        found = find_aiw_file_by_track("Testtrack2", self.temp_env.base_path)
        
        self.assertIsNotNone(found)
        self.assertNotEqual(found.parent.name, "Testtrack")
    
    def test_exact_folder_match_with_alternative_aiw_name(self):
        """Test that exact folder match returns the AIW file even if name differs"""
        # Remove the exact-named AIW to force using alternative
        exact_aiw = self.temp_env.mock_aiw_files["Testtrack2"]
        exact_aiw.unlink()
        
        found = find_aiw_file_by_track("Testtrack2", self.temp_env.base_path)
        
        self.assertIsNotNone(found)
        # Should still find the Testtrack2 folder, even if AIW is named differently
        self.assertEqual(found.parent.name, "Testtrack2")
    
    def test_partial_match_only_after_exact_fails(self):
        """Test that partial match is only used when exact match fails"""
        # Create a track that only exists as partial match
        locations_dir = self.temp_env.base_path / "GameData" / "Locations"
        partial_dir = locations_dir / "LongTrackName"
        partial_dir.mkdir(parents=True, exist_ok=True)
        partial_aiw = partial_dir / "LongTrackName.AIW"
        partial_aiw.write_text("""[Waypoint]
QualRatio = 1.500000
RaceRatio = 1.500000
""")
        
        # Search for "TrackName" - should find LongTrackName via partial match
        found = find_aiw_file_by_track("TrackName", self.temp_env.base_path)
        
        self.assertIsNotNone(found)
        self.assertEqual(found.parent.name, "LongTrackName")
    
    def test_case_insensitive_exact_match(self):
        """Test that case-insensitive exact match works correctly"""
        found = find_aiw_file_by_track("testtrack2", self.temp_env.base_path)
        
        self.assertIsNotNone(found)
        self.assertEqual(found.parent.name.lower(), "testtrack2")
    
    def test_find_testtrack_does_not_return_testtrack2(self):
        """Test that searching for 'Testtrack' does not return 'Testtrack2' folder"""
        found = find_aiw_file_by_track("Testtrack", self.temp_env.base_path)
        
        self.assertIsNotNone(found)
        self.assertEqual(found.parent.name, "Testtrack")
        self.assertNotEqual(found.parent.name, "Testtrack2")
    
    def test_race_results_parsing_resolves_correct_aiw(self):
        """Test that parsing raceresults.txt resolves the correct AIW path"""
        # Create a race results file for Testtrack2
        content = """[Race]
Scene=GAMEDATA\\LOCATIONS\\Testtrack2\\Testtrack2.TRK
AIDB=GAMEDATA\\LOCATIONS\\Testtrack2\\Testtrack2.AIW

[Slot0]
Driver=Player
Vehicle=Test Car
BestLap=1:30.000
"""
        self.temp_env.results_path.write_text(content)
        
        extractor = DataExtractor(self.temp_env.base_path)
        race_data = extractor.parse_race_results(self.temp_env.results_path)
        
        self.assertIsNotNone(race_data)
        self.assertIsNotNone(race_data.aiw_path)
        self.assertEqual(race_data.aiw_path.parent.name, "Testtrack2")
    
    def test_race_results_with_mismatched_aiw_name(self):
        """Test that race results referencing Testtrack2.AIW but file is Testtrack.AIW"""
        # Create race results that reference Testtrack2.AIW but the actual file is Testtrack.AIW
        content = """[Race]
Scene=GAMEDATA\\LOCATIONS\\Testtrack2\\Testtrack2.TRK
AIDB=GAMEDATA\\LOCATIONS\\Testtrack2\\Testtrack.AIW

[Slot0]
Driver=Player
Vehicle=Test Car
BestLap=1:30.000
"""
        self.temp_env.results_path.write_text(content)
        
        # Remove the exact-named AIW so only Testtrack.AIW remains in Testtrack2 folder
        exact_aiw = self.temp_env.mock_aiw_files["Testtrack2"]
        if exact_aiw and exact_aiw.exists():
            exact_aiw.unlink()
        
        extractor = DataExtractor(self.temp_env.base_path)
        race_data = extractor.parse_race_results(self.temp_env.results_path)
        
        self.assertIsNotNone(race_data)
        self.assertIsNotNone(race_data.aiw_path)
        self.assertEqual(race_data.aiw_path.parent.name, "Testtrack2")
    
    def test_priority_exact_folder_over_exact_stem(self):
        """Test that exact folder match takes priority over exact stem match elsewhere"""
        # Create a rogue AIW file with stem "Testtrack2" in a different folder
        locations_dir = self.temp_env.base_path / "GameData" / "Locations"
        rogue_dir = locations_dir / "RogueFolder"
        rogue_dir.mkdir(parents=True, exist_ok=True)
        rogue_aiw = rogue_dir / "Testtrack2.AIW"
        rogue_aiw.write_text("""[Waypoint]
QualRatio = 99.000000
RaceRatio = 99.000000
""")
        
        found = find_aiw_file_by_track("Testtrack2", self.temp_env.base_path)
        
        self.assertIsNotNone(found)
        # Should find the exact folder match, not the rogue file
        self.assertEqual(found.parent.name, "Testtrack2")
        self.assertNotEqual(found.parent.name, "RogueFolder")
    
    def test_find_aiw_from_path_with_partial_match(self):
        """Test find_aiw_file_from_path handles partial matches correctly"""
        # Use a path that doesn't exactly exist but should be found
        rel_path = "GameData/Locations/Testtrack2/Testtrack2.AIW"
        found = find_aiw_file_from_path(rel_path, self.temp_env.base_path)
        
        self.assertIsNotNone(found)
        self.assertEqual(found.parent.name, "Testtrack2")


class TestAIWTrackResolutionWithRealData(BaseTestCase):
    """Test AIW resolution with more complex real-world scenarios"""
    
    def setUp(self):
        super().setUp()
        self._create_complex_track_structure()
    
    def _create_complex_track_structure(self):
        """Create a more complex track structure with multiple variations"""
        locations_dir = self.temp_env.base_path / "GameData" / "Locations"
        
        # Case 1: Folder "Monza", AIW "4Monza.AIW"
        monza_dir = locations_dir / "Monza"
        monza_dir.mkdir(parents=True, exist_ok=True)
        monza_aiw = monza_dir / "4Monza.AIW"
        monza_aiw.write_text("""[Waypoint]
QualRatio = 1.000000
RaceRatio = 1.000000
""")
        
        # Case 2: Folder "Monza2004", AIW "Monza.AIW" (different name)
        monza2004_dir = locations_dir / "Monza2004"
        monza2004_dir.mkdir(parents=True, exist_ok=True)
        monza2004_aiw = monza2004_dir / "Monza.AIW"
        monza2004_aiw.write_text("""[Waypoint]
QualRatio = 1.200000
RaceRatio = 1.200000
""")
        
        # Case 3: Folder "Silverstone", AIW "Silverstone.AIW"
        silverstone_dir = locations_dir / "Silverstone"
        silverstone_dir.mkdir(parents=True, exist_ok=True)
        silverstone_aiw = silverstone_dir / "Silverstone.AIW"
        silverstone_aiw.write_text("""[Waypoint]
QualRatio = 0.900000
RaceRatio = 0.900000
""")
        
        self.temp_env.mock_aiw_files["Monza"] = monza_aiw
        self.temp_env.mock_aiw_files["Monza2004"] = monza2004_aiw
        self.temp_env.mock_aiw_files["Silverstone"] = silverstone_aiw
    
    def test_monza_finds_monza_not_monza2004(self):
        """Test that searching for 'Monza' finds Monza folder, not Monza2004"""
        found = find_aiw_file_by_track("Monza", self.temp_env.base_path)
        
        self.assertIsNotNone(found)
        self.assertEqual(found.parent.name, "Monza")
        self.assertNotEqual(found.parent.name, "Monza2004")
    
    def test_monza2004_finds_monza2004_folder(self):
        """Test that searching for 'Monza2004' finds the Monza2004 folder"""
        found = find_aiw_file_by_track("Monza2004", self.temp_env.base_path)
        
        self.assertIsNotNone(found)
        self.assertEqual(found.parent.name, "Monza2004")
    
    def test_silverstone_finds_correct_folder(self):
        """Test basic functionality for a normal track name"""
        found = find_aiw_file_by_track("Silverstone", self.temp_env.base_path)
        
        self.assertIsNotNone(found)
        self.assertEqual(found.parent.name, "Silverstone")
    
    def test_race_results_for_monza2004(self):
        """Test that race results for Monza2004 resolve to Monza2004 folder"""
        content = """[Race]
Scene=GAMEDATA\\LOCATIONS\\Monza2004\\Monza2004.TRK
AIDB=GAMEDATA\\LOCATIONS\\Monza2004\\Monza.AIW

[Slot0]
Driver=Player
Vehicle=Test Car
BestLap=1:30.000
"""
        self.temp_env.results_path.write_text(content)
        
        extractor = DataExtractor(self.temp_env.base_path)
        race_data = extractor.parse_race_results(self.temp_env.results_path)
        
        self.assertIsNotNone(race_data)
        self.assertIsNotNone(race_data.aiw_path)
        self.assertEqual(race_data.aiw_path.parent.name, "Monza2004")


class TestAIWResolutionEdgeCases(BaseTestCase):
    """Test edge cases for AIW resolution"""
    
    def test_track_name_with_spaces(self):
        """Test track name with spaces"""
        locations_dir = self.temp_env.base_path / "GameData" / "Locations"
        track_dir = locations_dir / "Test Track With Spaces"
        track_dir.mkdir(parents=True, exist_ok=True)
        aiw_file = track_dir / "Test Track With Spaces.AIW"
        aiw_file.write_text("""[Waypoint]
QualRatio = 1.000000
""")
        
        found = find_aiw_file_by_track("Test Track With Spaces", self.temp_env.base_path)
        
        self.assertIsNotNone(found)
        self.assertEqual(found.parent.name, "Test Track With Spaces")
    
    def test_track_name_with_underscores(self):
        """Test track name with underscores"""
        locations_dir = self.temp_env.base_path / "GameData" / "Locations"
        track_dir = locations_dir / "Test_Track_With_Underscores"
        track_dir.mkdir(parents=True, exist_ok=True)
        aiw_file = track_dir / "Test_Track_With_Underscores.AIW"
        aiw_file.write_text("""[Waypoint]
QualRatio = 1.000000
""")
        
        found = find_aiw_file_by_track("Test_Track_With_Underscores", self.temp_env.base_path)
        
        self.assertIsNotNone(found)
        self.assertEqual(found.parent.name, "Test_Track_With_Underscores")
    
    def test_track_name_with_numbers(self):
        """Test track name with numbers"""
        locations_dir = self.temp_env.base_path / "GameData" / "Locations"
        track_dir = locations_dir / "Track123"
        track_dir.mkdir(parents=True, exist_ok=True)
        aiw_file = track_dir / "Track123.AIW"
        aiw_file.write_text("""[Waypoint]
QualRatio = 1.000000
""")
        
        found = find_aiw_file_by_track("Track123", self.temp_env.base_path)
        
        self.assertIsNotNone(found)
        self.assertEqual(found.parent.name, "Track123")
    
    def test_aiw_file_with_different_extension_case(self):
        """Test AIW file with lowercase .aiw extension"""
        locations_dir = self.temp_env.base_path / "GameData" / "Locations"
        track_dir = locations_dir / "LowerCaseExt"
        track_dir.mkdir(parents=True, exist_ok=True)
        aiw_file = track_dir / "LowerCaseExt.aiw"
        aiw_file.write_text("""[Waypoint]
QualRatio = 1.000000
""")
        
        found = find_aiw_file_by_track("LowerCaseExt", self.temp_env.base_path)
        
        self.assertIsNotNone(found)
        self.assertEqual(found.parent.name, "LowerCaseExt")
    
    def test_no_aiw_file_in_folder(self):
        """Test track folder exists but has no AIW file"""
        locations_dir = self.temp_env.base_path / "GameData" / "Locations"
        track_dir = locations_dir / "EmptyFolder"
        track_dir.mkdir(parents=True, exist_ok=True)
        # No AIW file created
        
        found = find_aiw_file_by_track("EmptyFolder", self.temp_env.base_path)
        
        self.assertIsNone(found)
    
    def test_empty_locations_directory(self):
        """Test when Locations directory is empty"""
        locations_dir = self.temp_env.base_path / "GameData" / "Locations"
        # Remove all existing directories
        for item in locations_dir.iterdir():
            if item.is_dir():
                shutil.rmtree(item)
        
        found = find_aiw_file_by_track("AnyTrack", self.temp_env.base_path)
        
        self.assertIsNone(found)


def run_aiw_track_resolution_tests():
    """Run all AIW track resolution tests"""
    print("\n" + "=" * 60)
    print("AIW TRACK RESOLUTION TESTS")
    print("=" * 60)
    
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    suite.addTests(loader.loadTestsFromTestCase(TestAIWTrackResolution))
    suite.addTests(loader.loadTestsFromTestCase(TestAIWTrackResolutionWithRealData))
    suite.addTests(loader.loadTestsFromTestCase(TestAIWResolutionEdgeCases))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result


if __name__ == "__main__":
    run_aiw_track_resolution_tests()
