#!/usr/bin/env python3
"""
Configuration management - lightweight version
"""

import yaml
from pathlib import Path
from typing import Optional, Dict, Any

DEFAULT_CONFIG = {
    'base_path': '',
    'db_path': 'ai_data.db',
    'auto_apply': False,
    'backup_enabled': True,
    'logging_enabled': False,
    'logging_level': 'WARNING',
    'autopilot_enabled': False,
    'autopilot_silent': False,
    'poll_interval': 10.0,
    'min_ratio': 0.5,
    'max_ratio': 1.5,
    'throttle_updates': True,
    'lazy_load': True,
}


class ConfigManager:
    """Configuration manager with caching"""
    
    _instance = None
    _config = None
    _config_path = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._config = None
            cls._instance._config_path = None
        return cls._instance
    
    def load(self, config_file: str = "cfg.yml") -> Dict[str, Any]:
        """Load configuration from file"""
        self._config_path = Path(config_file)
        
        if not self._config_path.exists():
            self._config = DEFAULT_CONFIG.copy()
            self.save()
            return self._config
        
        try:
            with open(self._config_path, 'r') as f:
                loaded = yaml.safe_load(f)
                self._config = DEFAULT_CONFIG.copy()
                if loaded:
                    self._config.update(loaded)
        except Exception as e:
            print(f"Error loading config: {e}")
            self._config = DEFAULT_CONFIG.copy()
        
        return self._config
    
    def save(self) -> bool:
        """Save configuration to file"""
        if not self._config_path:
            self._config_path = Path("cfg.yml")
        
        try:
            with open(self._config_path, 'w') as f:
                yaml.dump(self._config, f, default_flow_style=False, indent=2)
            return True
        except Exception as e:
            print(f"Error saving config: {e}")
            return False
    
    def get(self, key: str, default=None):
        """Get configuration value"""
        if self._config is None:
            self.load()
        return self._config.get(key, default)
    
    def set(self, key: str, value) -> bool:
        """Set configuration value and save"""
        if self._config is None:
            self.load()
        self._config[key] = value
        return self.save()
    
    def get_base_path(self) -> Optional[Path]:
        """Get base path"""
        path_str = self.get('base_path', '')
        if path_str:
            path = Path(path_str)
            if path.exists():
                return path
        return None
    
    def get_results_file_path(self) -> Optional[Path]:
        """Get full path to raceresults.txt"""
        base = self.get_base_path()
        if base:
            return base / 'UserData' / 'Log' / 'Results' / 'raceresults.txt'
        return None
    
    def get_poll_interval(self) -> float:
        """Get poll interval"""
        return self.get('poll_interval', DEFAULT_CONFIG['poll_interval'])
    
    def get_db_path(self) -> str:
        """Get database path"""
        return self.get('db_path', DEFAULT_CONFIG['db_path'])
    
    def get_ratio_limits(self) -> tuple:
        """Get min and max ratio limits"""
        return (self.get('min_ratio', DEFAULT_CONFIG['min_ratio']), 
                self.get('max_ratio', DEFAULT_CONFIG['max_ratio']))
