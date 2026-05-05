#!/usr/bin/env python3
"""
Unit tests for configuration management
"""

import unittest
from pathlib import Path

from test_base import BaseTestCase


class TestConfig(BaseTestCase):
    """Test configuration management"""
    
    def test_default_config_creation(self):
        """Test that default config is created when missing"""
        from core_config import create_default_config_if_missing
        
        temp_config = self.temp_env.test_data_dir / "cfg_new.yml"
        self.assertFalse(temp_config.exists())
        
        result = create_default_config_if_missing(str(temp_config))
        
        self.assertTrue(result)
        self.assertTrue(temp_config.exists())
    
    def test_config_loading(self):
        """Test loading configuration"""
        from core_config import load_config
        
        loaded = load_config(str(self.temp_env.config_path))
        self.assertEqual(loaded['base_path'], str(self.temp_env.base_path))
    
    def test_config_save(self):
        """Test saving configuration"""
        from core_config import load_config, save_config
        
        loaded = load_config(str(self.temp_env.config_path))
        loaded['test_key'] = 'test_value'
        
        result = save_config(loaded, str(self.temp_env.config_path))
        self.assertTrue(result)
        
        reloaded = load_config(str(self.temp_env.config_path))
        self.assertEqual(reloaded.get('test_key'), 'test_value')
    
    def test_ratio_limits(self):
        """Test ratio limits retrieval and update"""
        from core_config import get_ratio_limits, update_ratio_limits
        
        min_r, max_r = get_ratio_limits(str(self.temp_env.config_path))
        self.assertEqual(min_r, 0.3)
        self.assertEqual(max_r, 2.5)
        
        update_ratio_limits(0.4, 2.0, str(self.temp_env.config_path))
        min_r, max_r = get_ratio_limits(str(self.temp_env.config_path))
        self.assertEqual(min_r, 0.4)
        self.assertEqual(max_r, 2.0)
    
    def test_base_path(self):
        """Test base path operations"""
        from core_config import get_base_path, update_base_path
        
        current = get_base_path(str(self.temp_env.config_path))
        self.assertEqual(str(current), str(self.temp_env.base_path))
        
        new_path = self.temp_env.test_data_dir / "new_gtr2_path"
        new_path.mkdir()
        
        result = update_base_path(new_path, str(self.temp_env.config_path))
        self.assertTrue(result)
        
        updated = get_base_path(str(self.temp_env.config_path))
        self.assertEqual(str(updated), str(new_path))
    
    def test_poll_interval(self):
        """Test poll interval operations"""
        from core_config import get_poll_interval, update_poll_interval
        
        interval = get_poll_interval(str(self.temp_env.config_path))
        self.assertEqual(interval, 5.0)
        
        update_poll_interval(2.5, str(self.temp_env.config_path))
        interval = get_poll_interval(str(self.temp_env.config_path))
        self.assertEqual(interval, 2.5)
    
    def test_db_path(self):
        """Test database path operations"""
        from core_config import get_db_path, update_db_path
        
        db_path = get_db_path(str(self.temp_env.config_path))
        self.assertEqual(db_path, str(self.temp_env.test_data_dir / "test_data.db"))
        
        new_path = str(self.temp_env.test_data_dir / "new_data.db")
        update_db_path(new_path, str(self.temp_env.config_path))
        
        updated = get_db_path(str(self.temp_env.config_path))
        self.assertEqual(updated, new_path)
