#!/usr/bin/env python3
"""
Unit tests for database operations
"""

import sys
from pathlib import Path

# Add parent directory to path so we can import application modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from test_base import BaseTestCase
from core_database import CurveDatabase


class TestDatabase(BaseTestCase):
    """Test database operations"""
    
    def test_database_creation(self):
        """Test that database is created with correct schema"""
        db_path = self.temp_env.test_data_dir / "test.db"
        db = CurveDatabase(str(db_path))
        
        self.assertTrue(db_path.exists())
        self.assertTrue(db.database_exists())
    
    def test_add_data_point(self):
        """Test adding a data point"""
        db_path = self.temp_env.test_data_dir / "test.db"
        db = CurveDatabase(str(db_path))
        
        result = db.add_data_point("Monza", "GT_0304", 1.2, 95.5, "race")
        self.assertTrue(result)
        
        points = db.get_data_points(["Monza"], ["GT_0304"], True, True, True)
        self.assertEqual(len(points), 1)
        self.assertAlmostEqual(points[0][0], 1.2)
        self.assertAlmostEqual(points[0][1], 95.5)
        self.assertEqual(points[0][2], "race")
    
    def test_get_stats(self):
        """Test getting database statistics"""
        db_path = self.temp_env.test_data_dir / "test.db"
        db = CurveDatabase(str(db_path))
        
        db.add_data_point("Monza", "GT_0304", 1.2, 95.5, "race")
        db.add_data_point("Monza", "GT_0304", 1.3, 94.5, "qual")
        db.add_data_point("Spa", "NGT_0304", 1.1, 110.0, "race")
        
        stats = db.get_stats()
        self.assertEqual(stats['total_points'], 3)
        self.assertEqual(stats['total_tracks'], 2)
        self.assertEqual(stats['total_vehicle_classes'], 2)
    
    def test_get_all_tracks(self):
        """Test getting all tracks from database"""
        db_path = self.temp_env.test_data_dir / "test.db"
        db = CurveDatabase(str(db_path))
        
        db.add_data_point("Monza", "GT_0304", 1.2, 95.5, "race")
        db.add_data_point("Spa", "NGT_0304", 1.1, 110.0, "race")
        db.add_data_point("Monza", "GT_0304", 1.3, 94.5, "qual")
        
        tracks = db.get_all_tracks()
        self.assertEqual(len(tracks), 2)
        self.assertIn("Monza", tracks)
        self.assertIn("Spa", tracks)
    
    def test_get_all_vehicle_classes(self):
        """Test getting all vehicle classes from database"""
        db_path = self.temp_env.test_data_dir / "test.db"
        db = CurveDatabase(str(db_path))
        
        db.add_data_point("Monza", "GT_0304", 1.2, 95.5, "race")
        db.add_data_point("Monza", "NGT_0304", 1.3, 94.5, "qual")
        
        classes = db.get_all_vehicle_classes()
        self.assertEqual(len(classes), 2)
        self.assertIn("GT_0304", classes)
        self.assertIn("NGT_0304", classes)
    
    def test_save_race_session(self):
        """Test saving a complete race session"""
        db_path = self.temp_env.test_data_dir / "test.db"
        db = CurveDatabase(str(db_path))
        
        race_data = {
            'track_name': 'Monza',
            'user_name': 'Test Driver',
            'user_vehicle': 'Test Car',
            'user_best_lap_sec': 88.5,
            'user_qualifying_sec': 90.0,
            'ai_results': [
                {'slot': 1, 'driver_name': 'AI1', 'best_lap_sec': 92.0, 'qual_time_sec': 94.0},
                {'slot': 2, 'driver_name': 'AI2', 'best_lap_sec': 95.0, 'qual_time_sec': 97.0}
            ]
        }
        
        race_id = db.save_race_session(race_data)
        self.assertIsNotNone(race_id)
        
        sessions = db.get_race_sessions(limit=10)
        self.assertEqual(len(sessions), 1)
        self.assertEqual(sessions[0]['track_name'], 'Monza')
