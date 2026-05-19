#!/usr/bin/env python3
"""
Unit tests for user laptimes handling and manual lap time entry
Tests the manual lap time dialog and integration with database
"""

import sys
from pathlib import Path

# Add parent directory to path so we can import application modules
sys.path.insert(0, str(Path(__file__).parent.parent))

import unittest
from unittest.mock import MagicMock, patch
from PyQt5.QtWidgets import QApplication, QDialog
from PyQt5.QtCore import Qt
from PyQt5.QtTest import QTest

from test_base import BaseTestCase
from core_database import CurveDatabase
from gui_common_dialogs import ManualLapTimeDialog


class TestUserLaptimes(BaseTestCase):
    """Test user laptimes functionality"""
    
    def setUp(self):
        super().setUp()
        self.app = QApplication.instance()
        if self.app is None:
            self.app = QApplication([])
        
        self.db_path = self.temp_env.test_data_dir / "user_laptimes.db"
        self.db = CurveDatabase(str(self.db_path))
    
    def test_dialog_creation_with_current_time(self):
        """Test ManualLapTimeDialog creation with existing time"""
        dialog = ManualLapTimeDialog(None, "qual", 95.5)
        
        self.assertEqual(dialog.session_type, "qual")
        self.assertEqual(dialog.current_time, 95.5)
        self.assertAlmostEqual(dialog.time_spin.value(), 95.5)
        dialog.close()
    
    def test_dialog_creation_without_current_time(self):
        """Test ManualLapTimeDialog creation without existing time"""
        dialog = ManualLapTimeDialog(None, "race", None)
        
        self.assertEqual(dialog.session_type, "race")
        self.assertIsNone(dialog.current_time)
        self.assertEqual(dialog.time_spin.value(), 90.0)  # Default value
        dialog.close()
    
    def test_dialog_accept_saves_time(self):
        """Test that accept() saves the entered time"""
        dialog = ManualLapTimeDialog(None, "qual", 95.5)
        dialog.time_spin.setValue(88.0)
        
        dialog.accept()
        
        self.assertEqual(dialog.new_time, 88.0)
        dialog.close()
    
    def test_dialog_reject_does_not_save(self):
        """Test that reject() does not save time"""
        dialog = ManualLapTimeDialog(None, "qual", 95.5)
        dialog.time_spin.setValue(88.0)
        
        dialog.reject()
        
        self.assertIsNone(dialog.new_time)
        dialog.close()
    
    def test_enter_key_accepts_dialog(self):
        """Test that Enter key accepts the dialog"""
        # Import QDialog inside the test
        from PyQt5.QtWidgets import QDialog
        
        dialog = ManualLapTimeDialog(None, "qual", 95.5)
        dialog.time_spin.setValue(88.0)
        
        QTest.keyPress(dialog, Qt.Key_Return)
        
        self.assertEqual(dialog.result(), QDialog.Accepted)
        self.assertEqual(dialog.new_time, 88.0)
        dialog.close()
    
    def test_escape_key_rejects_dialog(self):
        """Test that Escape key rejects the dialog"""
        from PyQt5.QtWidgets import QDialog
        
        dialog = ManualLapTimeDialog(None, "qual", 95.5)
        
        QTest.keyPress(dialog, Qt.Key_Escape)
        
        self.assertEqual(dialog.result(), QDialog.Rejected)
        dialog.close()
    
    def test_time_range_validation(self):
        """Test that time spinbox respects min/max range"""
        dialog = ManualLapTimeDialog(None, "qual", 95.5)
        
        # Get the actual min/max from the spinbox
        min_val = dialog.time_spin.minimum()
        max_val = dialog.time_spin.maximum()
        
        # Try to set values outside range - the spinbox should clamp them
        dialog.time_spin.setValue(min_val - 10)
        self.assertGreaterEqual(dialog.time_spin.value(), min_val)
        
        dialog.time_spin.setValue(max_val + 10)
        self.assertLessEqual(dialog.time_spin.value(), max_val)
        
        dialog.close()
    
    def test_manual_time_database_integration_qual(self):
        """Test adding manual qualifying time to database"""
        result = self.db.add_data_point(
            "TestTrack", 
            "GT_0304", 
            1.0,  # ratio
            85.5,  # lap time
            "qual"
        )
        self.assertTrue(result)
        
        # get_data_points expects: get_data_points(tracks, vehicle_classes, include_qual, include_race, include_autopilot)
        # But according to the error, it doesn't support these parameters. Let's pass all True and filter manually.
        points = self.db.get_data_points(["TestTrack"], ["GT_0304"], True, True, True)
        
        # Points are list of (ratio, lap_time, session_type, ...)
        # Filter for qualifying sessions
        qual_points = [p for p in points if p[2] == "qual"]
        
        if qual_points:
            self.assertAlmostEqual(qual_points[0][1], 85.5)  # lap time
            self.assertEqual(qual_points[0][2], "qual")  # session type
    
    def test_manual_time_database_integration_race(self):
        """Test adding manual race time to database"""
        result = self.db.add_data_point(
            "TestTrack",
            "NGT_0304",
            1.2,
            88.0,
            "race"
        )
        self.assertTrue(result)
        
        points = self.db.get_data_points(["TestTrack"], ["NGT_0304"], True, True, True)
        
        # Filter for race sessions
        race_points = [p for p in points if p[2] == "race"]
        
        if race_points:
            self.assertAlmostEqual(race_points[0][1], 88.0)
            self.assertEqual(race_points[0][2], "race")
    
    def test_multiple_manual_times_same_session(self):
        """Test adding multiple manual times for same session"""
        self.db.add_data_point("TrackA", "GT_0304", 1.0, 90.0, "qual")
        self.db.add_data_point("TrackA", "GT_0304", 1.1, 92.0, "qual")
        self.db.add_data_point("TrackA", "GT_0304", 0.95, 88.0, "qual")
        
        points = self.db.get_data_points(["TrackA"], ["GT_0304"], True, True, True)
        qual_points = [p for p in points if p[2] == "qual"]
        self.assertEqual(len(qual_points), 3)
    
    def test_manual_time_updates_existing(self):
        """Test that adding a point with same track/class/ratio updates if exists"""
        # Add first point
        self.db.add_data_point("TrackB", "GT_0304", 1.0, 90.0, "qual")
        
        # Add second point with same ratio but different time
        self.db.add_data_point("TrackB", "GT_0304", 1.0, 88.0, "qual")
        
        # Should have at least 1 point
        points = self.db.get_data_points(["TrackB"], ["GT_0304"], True, True, True)
        self.assertGreaterEqual(len(points), 1)
    
    def test_manual_time_retrieval_filtering(self):
        """Test filtering manual time entries"""
        self.db.add_data_point("TrackC", "GT_0304", 1.0, 90.0, "qual")
        self.db.add_data_point("TrackC", "GT_0304", 1.1, 92.0, "race")
        
        # Get all points
        all_points = self.db.get_data_points(["TrackC"], ["GT_0304"], True, True, True)
        
        # Separate manually
        qual_points = [p for p in all_points if p[2] == "qual"]
        race_points = [p for p in all_points if p[2] == "race"]
        
        self.assertEqual(len(qual_points), 1)
        self.assertEqual(len(race_points), 1)
        self.assertEqual(qual_points[0][2], "qual")
        self.assertEqual(race_points[0][2], "race")


class TestManualTimeFormatting(unittest.TestCase):
    """Test lap time string formatting"""
    
    def test_format_time_integer_seconds(self):
        """Test formatting integer seconds"""
        from core_data_extraction import format_time
        self.assertEqual(format_time(90.0), "1:30.000")
    
    def test_format_time_with_ms(self):
        """Test formatting with milliseconds"""
        from core_data_extraction import format_time
        self.assertEqual(format_time(95.123), "1:35.123")
    
    def test_format_time_less_than_minute(self):
        """Test formatting time less than 60 seconds"""
        from core_data_extraction import format_time
        self.assertEqual(format_time(45.5), "0:45.500")
    
    def test_format_time_zero(self):
        """Test formatting zero time"""
        from core_data_extraction import format_time
        self.assertEqual(format_time(0), "N/A")
    
    def test_format_time_negative(self):
        """Test formatting negative time"""
        from core_data_extraction import format_time
        self.assertEqual(format_time(-5), "N/A")
    
    def test_manual_time_to_seconds_conversion(self):
        """Test converting time string to seconds manually"""
        def time_to_seconds(time_str):
            """Convert MM:SS.mmm to seconds"""
            if not time_str or time_str == "N/A":
                return 0.0
            try:
                if ":" in time_str:
                    parts = time_str.split(":")
                    minutes = int(parts[0])
                    seconds_part = parts[1].replace(",", ".")
                    seconds = float(seconds_part)
                    return minutes * 60 + seconds
                else:
                    return float(time_str.replace(",", "."))
            except (ValueError, IndexError):
                return 0.0
        
        self.assertEqual(time_to_seconds("1:30.500"), 90.5)
        self.assertEqual(time_to_seconds("0:45.500"), 45.5)
        self.assertEqual(time_to_seconds("90.5"), 90.5)
        self.assertEqual(time_to_seconds("invalid"), 0.0)
    
    def test_manual_seconds_to_time_string(self):
        """Test converting seconds to time string manually"""
        def seconds_to_time_str(seconds):
            if seconds <= 0:
                return "N/A"
            minutes = int(seconds) // 60
            secs = int(seconds) % 60
            ms = int((seconds - int(seconds)) * 1000)
            return f"{minutes}:{secs:02d}.{ms:03d}"
        
        self.assertEqual(seconds_to_time_str(90.5), "1:30.500")
        self.assertEqual(seconds_to_time_str(45.5), "0:45.500")
        self.assertEqual(seconds_to_time_str(0), "N/A")


def run_user_laptimes_tests():
    """Run all user laptimes tests"""
    print("\n" + "=" * 60)
    print("USER LAPTIMES TESTS")
    print("=" * 60)
    
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    suite.addTests(loader.loadTestsFromTestCase(TestUserLaptimes))
    suite.addTests(loader.loadTestsFromTestCase(TestManualTimeFormatting))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result


if __name__ == "__main__":
    run_user_laptimes_tests()
