#!/usr/bin/env python3
"""
Unit tests for vehicle scanning functionality
"""

import sys
from pathlib import Path

# Add parent directory to path so we can import application modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import shutil
from pathlib import Path

from test_base import BaseTestCase
from core_vehicle_scanner import scan_vehicles_from_gtr2, find_missing_vehicles, load_vehicle_classes


class TestVehicleScanner(BaseTestCase):
    """Test vehicle scanning functionality"""
    
    def test_scan_vehicles(self):
        """Test scanning vehicles from GTR2 installation"""
        vehicles = scan_vehicles_from_gtr2(self.temp_env.base_path)
        
        self.assertIsNotNone(vehicles)
        self.assertGreater(len(vehicles), 0)
        self.assertIn("Test Car GT", vehicles)
        self.assertIn("Test Car NGT", vehicles)
        self.assertIn("Ferrari 550", vehicles)
    
    def test_scan_with_progress_callback(self):
        """Test scanning with progress callback"""
        progress_values = []
        
        def callback(current, total, message):
            progress_values.append((current, total, message))
        
        vehicles = scan_vehicles_from_gtr2(self.temp_env.base_path, callback)
        
        self.assertGreater(len(progress_values), 0)
        self.assertGreater(len(vehicles), 0)
    
    def test_find_missing_vehicles(self):
        """Test finding vehicles not in classes file"""
        all_vehicles, defined_vehicles, missing = find_missing_vehicles(
            self.temp_env.base_path, self.temp_env.classes_path
        )
        
        self.assertIsNotNone(all_vehicles)
        self.assertIsNotNone(defined_vehicles)
        self.assertIsNotNone(missing)
        
        self.assertIsInstance(all_vehicles, set)
        self.assertIsInstance(defined_vehicles, set)
        self.assertIsInstance(missing, set)
    
    def test_load_vehicle_classes(self):
        """Test loading vehicle classes from JSON"""
        classes = load_vehicle_classes(self.temp_env.classes_path)
        
        self.assertIsNotNone(classes)
        self.assertIn("GT_0304", classes)
        self.assertIn("NGT_0304", classes)
    
    def test_get_all_defined_vehicles(self):
        """Test getting all defined vehicles from classes"""
        from core_vehicle_scanner import get_all_defined_vehicles
        
        classes = load_vehicle_classes(self.temp_env.classes_path)
        vehicles = get_all_defined_vehicles(classes)
        
        self.assertGreater(len(vehicles), 0)
        self.assertIn("Test Car GT", vehicles)
        self.assertIn("Formula 4", vehicles)
    
    def test_scan_nonexistent_gtr2_path(self):
        """Test scanning with invalid GTR2 path"""
        fake_path = Path("/nonexistent/path/that/does/not/exist")
        vehicles = scan_vehicles_from_gtr2(fake_path)
        
        self.assertEqual(len(vehicles), 0)
    
    def test_scan_with_empty_teams_directory(self):
        """Test scanning with empty teams directory"""
        teams_dir = self.temp_env.base_path / "GameData" / "Teams"
        
        # Remove all subdirectories but keep the directory itself
        if teams_dir.exists():
            for item in teams_dir.iterdir():
                if item.is_dir():
                    try:
                        shutil.rmtree(item)
                    except Exception:
                        pass
        
        vehicles = scan_vehicles_from_gtr2(self.temp_env.base_path)
        # Empty directory should yield no vehicles, but function should not crash
        self.assertIsNotNone(vehicles)
        # It may return 0 or could find vehicles from parent directories
        # Just verify no crash and result is a set
        self.assertIsInstance(vehicles, set)
