#!/usr/bin/env python3
"""
Unit tests for vehicle classes management
"""

from test_base import BaseTestCase
from gui_vehicle_manager import VehicleClassesManager


class TestVehicleClasses(BaseTestCase):
    """Test vehicle classes management - uses isolated test file"""
    
    def test_manager_creation(self):
        """Test vehicle classes manager creation"""
        manager = VehicleClassesManager(self.temp_env.classes_path)
        self.assertTrue(self.temp_env.classes_path.exists())
    
    def test_get_all_classes(self):
        """Test getting all classes"""
        manager = VehicleClassesManager(self.temp_env.classes_path)
        classes = manager.get_all_classes()
        # There are 4 classes in the mock data: GT_0304, NGT_0304, Formula_4, OTHER
        self.assertEqual(len(classes), 4)
        self.assertIn("GT_0304", classes)
        self.assertIn("NGT_0304", classes)
    
    def test_get_vehicles_for_class(self):
        """Test getting vehicles for a class"""
        manager = VehicleClassesManager(self.temp_env.classes_path)
        vehicles = manager.get_vehicles_for_class("GT_0304")
        self.assertEqual(len(vehicles), 3)
        self.assertIn("Test Car GT", vehicles)
    
    def test_add_class(self):
        """Test adding a new class"""
        manager = VehicleClassesManager(self.temp_env.classes_path)
        
        result = manager.add_class("TEST_CLASS", ["TEST_CLASS"], ["Test Car 1", "Test Car 2"])
        self.assertTrue(result)
        
        vehicles = manager.get_vehicles_for_class("TEST_CLASS")
        self.assertEqual(len(vehicles), 2)
        self.assertIn("Test Car 1", vehicles)
    
    def test_add_duplicate_class(self):
        """Test adding a class that already exists"""
        manager = VehicleClassesManager(self.temp_env.classes_path)
        
        result = manager.add_class("GT_0304", ["GT_0304"], [])
        self.assertFalse(result)
    
    def test_add_vehicle(self):
        """Test adding a vehicle to a class"""
        manager = VehicleClassesManager(self.temp_env.classes_path)
        
        result = manager.add_vehicle("GT_0304", "New Test Car")
        self.assertTrue(result)
        
        vehicles = manager.get_vehicles_for_class("GT_0304")
        self.assertIn("New Test Car", vehicles)
    
    def test_add_duplicate_vehicle(self):
        """Test adding a vehicle that already exists in the class"""
        manager = VehicleClassesManager(self.temp_env.classes_path)
        
        result = manager.add_vehicle("GT_0304", "Test Car GT")
        self.assertFalse(result)
    
    def test_remove_vehicle(self):
        """Test removing a vehicle from a class"""
        manager = VehicleClassesManager(self.temp_env.classes_path)
        
        result = manager.remove_vehicle("GT_0304", "Test Car GT")
        self.assertTrue(result)
        
        vehicles = manager.get_vehicles_for_class("GT_0304")
        self.assertNotIn("Test Car GT", vehicles)
    
    def test_get_vehicle_class(self):
        """Test getting class for a vehicle"""
        manager = VehicleClassesManager(self.temp_env.classes_path)
        
        vehicle_class = manager.get_vehicle_class("Test Car GT")
        self.assertEqual(vehicle_class, "GT_0304")
    
    def test_get_vehicle_class_partial_match(self):
        """Test partial matching for vehicle class"""
        manager = VehicleClassesManager(self.temp_env.classes_path)
        
        # Add a vehicle that will match partially
        manager.add_vehicle("GT_0304", "Special GT Car")
        
        vehicle_class = manager.get_vehicle_class("GT Car")
        # Should find the class containing GT Car
        self.assertIsNotNone(vehicle_class)
    
    def test_get_vehicle_class_not_found(self):
        """Test getting class for unknown vehicle"""
        manager = VehicleClassesManager(self.temp_env.classes_path)
        
        vehicle_class = manager.get_vehicle_class("Non Existent Vehicle")
        self.assertIsNone(vehicle_class)
    
    def test_delete_class(self):
        """Test deleting a class"""
        manager = VehicleClassesManager(self.temp_env.classes_path)
        
        result = manager.delete_class("NGT_0304")
        self.assertTrue(result)
        
        classes = manager.get_all_classes()
        self.assertNotIn("NGT_0304", classes)
    
    def test_rename_class(self):
        """Test renaming a class"""
        manager = VehicleClassesManager(self.temp_env.classes_path)
        
        result = manager.rename_class("GT_0304", "GT_2004")
        self.assertTrue(result)
        
        classes = manager.get_all_classes()
        self.assertNotIn("GT_0304", classes)
        self.assertIn("GT_2004", classes)
        
        vehicles = manager.get_vehicles_for_class("GT_2004")
        self.assertEqual(len(vehicles), 3)
    
    def test_get_all_vehicles(self):
        """Test getting all vehicles from all classes"""
        manager = VehicleClassesManager(self.temp_env.classes_path)
        
        all_vehicles = manager.get_all_vehicles()
        # Count vehicles from mock data:
        # GT_0304: 3 vehicles
        # NGT_0304: 3 vehicles  
        # Formula_4: 3 vehicles (Formula 4, Formula BMW, F4)
        # OTHER: 1 vehicle (Safety Car)
        # Total = 10 vehicles
        self.assertEqual(len(all_vehicles), 10)
        self.assertIn("Test Car GT", all_vehicles)
        self.assertIn("Formula 4", all_vehicles)
        self.assertIn("Safety Car", all_vehicles)
    
    def test_get_unassigned_vehicles(self):
        """Test getting unassigned vehicles"""
        manager = VehicleClassesManager(self.temp_env.classes_path)
        
        all_vehicles = {"Test Car GT", "Test Car NGT", "Unknown Car", "Another Car"}
        unassigned = manager.get_unassigned_vehicles(all_vehicles)
        
        self.assertIn("Unknown Car", unassigned)
        self.assertIn("Another Car", unassigned)
        self.assertNotIn("Test Car GT", unassigned)
