#!/usr/bin/env python3
"""
Unit tests for nr_last_user_laptimes configuration setting
"""

import sys
from pathlib import Path

# Add parent directory to path so we can import application modules
sys.path.insert(0, str(Path(__file__).parent.parent))

import unittest
from pathlib import Path
import tempfile
import json

from test_base import BaseTestCase
from core_config import (
    get_config_with_defaults, save_config, load_config,
    get_nr_last_user_laptimes, update_nr_last_user_laptimes, DEFAULT_CONFIG
)


class TestConfigUserLaptimes(BaseTestCase):
    """Test nr_last_user_laptimes configuration"""
    
    def test_default_value_in_config(self):
        """Test that nr_last_user_laptimes has default value 1"""
        self.assertIn('nr_last_user_laptimes', DEFAULT_CONFIG)
        self.assertEqual(DEFAULT_CONFIG['nr_last_user_laptimes'], 1)
    
    def test_get_nr_last_user_laptimes(self):
        """Test retrieving nr_last_user_laptimes from config"""
        value = get_nr_last_user_laptimes(str(self.temp_env.config_path))
        self.assertEqual(value, 1)
    
    def test_update_nr_last_user_laptimes(self):
        """Test updating nr_last_user_laptimes in config"""
        result = update_nr_last_user_laptimes(5, str(self.temp_env.config_path))
        self.assertTrue(result)
        
        value = get_nr_last_user_laptimes(str(self.temp_env.config_path))
        self.assertEqual(value, 5)
    
    def test_nr_last_user_laptimes_validation(self):
        """Test that nr_last_user_laptimes can be set to various values"""
        test_values = [1, 2, 3, 5, 10, 100]
        
        for test_value in test_values:
            update_nr_last_user_laptimes(test_value, str(self.temp_env.config_path))
            value = get_nr_last_user_laptimes(str(self.temp_env.config_path))
            self.assertEqual(value, test_value)
    
    def test_config_save_preserves_value(self):
        """Test that nr_last_user_laptimes is preserved on config save"""
        update_nr_last_user_laptimes(7, str(self.temp_env.config_path))
        
        config = load_config(str(self.temp_env.config_path))
        self.assertEqual(config.get('nr_last_user_laptimes'), 7)
        
        save_config(config, str(self.temp_env.config_path))
        
        reloaded = load_config(str(self.temp_env.config_path))
        self.assertEqual(reloaded.get('nr_last_user_laptimes'), 7)


def run_config_user_laptimes_tests():
    """Run config user laptimes tests"""
    print("\n" + "=" * 60)
    print("CONFIG USER LAPTIMES TESTS")
    print("=" * 60)
    
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestConfigUserLaptimes)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result


if __name__ == "__main__":
    run_config_user_laptimes_tests()
