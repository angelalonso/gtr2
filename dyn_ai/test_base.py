#!/usr/bin/env python3
"""
Base test case with automatic file restoration
"""

import unittest
from pathlib import Path

from PyQt5.QtWidgets import QApplication

from test_backup_manager import OriginalFileBackup
from test_temp_env import TempTestEnvironment


class BaseTestCase(unittest.TestCase):
    """Base test case that ensures no permanent file modifications"""
    
    @classmethod
    def setUpClass(cls):
        """Backup important files before any tests run"""
        cls.backup_manager = OriginalFileBackup()
        
        classes_path = Path(__file__).parent / "vehicle_classes.json"
        if classes_path.exists():
            cls.backup_manager.backup_file(classes_path)
        
        config_path = Path(__file__).parent / "cfg.yml"
        if config_path.exists():
            cls.backup_manager.backup_file(config_path)
        
        cls.app = QApplication.instance()
        if cls.app is None:
            cls.app = QApplication([])
    
    @classmethod
    def tearDownClass(cls):
        """Restore all backed up files after all tests"""
        cls.backup_manager.restore_all()
    
    def setUp(self):
        """Set up test environment - each test gets its own temp environment"""
        self.temp_env = TempTestEnvironment()
        self.temp_env.create()
    
    def tearDown(self):
        """Clean up after test"""
        self.temp_env.cleanup()
