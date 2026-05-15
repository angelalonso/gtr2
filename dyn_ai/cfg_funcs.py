#!/usr/bin/env python3
"""
Configuration management for Live AI Tuner
Handles loading, saving, and validating the configuration from cfg.yml
"""

import yaml
from pathlib import Path
import os
from typing import Optional, Dict, Any


DEFAULT_CONFIG = {
    'base_path': '',
   # 'formulas_dir': './track_formulas',
    'db_path': 'ai_data.db',
    'auto_apply': False,
    'backup_enabled': True,
    'logging_enabled': False,
    'autopilot_enabled': False,
    'autopilot_silent': False,
    'poll_interval': 5.0,  # seconds
    'min_ratio': 0.5,
    'max_ratio': 1.5,
}


def load_config(config_file: str = "cfg.yml") -> Optional[Dict[str, Any]]:
    """Load configuration from YAML file"""
    config_path = Path(config_file)
    
    if not config_path.exists():
        return None
    
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
            return config
    except Exception as e:
        print(f"Error reading {config_file}: {e}")
        return None


def save_config(config: Dict[str, Any], config_file: str = "cfg.yml") -> bool:
    """Save configuration to YAML file"""
    try:
        with open(config_file, 'w') as f:
            yaml.dump(config, f, default_flow_style=False, indent=2)
        return True
    except Exception as e:
        print(f"Error saving to {config_file}: {e}")
        return False


def get_config_with_defaults(config_file: str = "cfg.yml") -> Dict[str, Any]:
    """Get configuration with defaults applied"""
    config = load_config(config_file)
    
    if config is None:
        return DEFAULT_CONFIG.copy()
    
    modified = False
    for key, default_value in DEFAULT_CONFIG.items():
        if key not in config:
            config[key] = default_value
            modified = True
    
    if modified:
        save_config(config, config_file)
    
    return config


def get_base_path(config_file: str = "cfg.yml") -> Optional[Path]:
    """Get base path from config"""
    config = get_config_with_defaults(config_file)
    
    if config and config.get('base_path'):
        path = Path(config['base_path'])
        if path.exists():
            return path
    
    return None


def update_base_path(new_path: Path, config_file: str = "cfg.yml") -> bool:
    """Update base path in config"""
    config = get_config_with_defaults(config_file)
    config['base_path'] = str(new_path)
    return save_config(config, config_file)


def get_results_file_path(config_file: str = "cfg.yml") -> Optional[Path]:
    """Get the full path to raceresults.txt from config"""
    base_path = get_base_path(config_file)
    if base_path:
        return base_path / 'UserData' / 'Log' / 'Results' / 'raceresults.txt'
    return None


def get_poll_interval(config_file: str = "cfg.yml") -> float:
    """Get file poll interval from config"""
    config = get_config_with_defaults(config_file)
    return config.get('poll_interval', DEFAULT_CONFIG['poll_interval'])


def update_poll_interval(interval: float, config_file: str = "cfg.yml") -> bool:
    """Update poll interval in config"""
    config = get_config_with_defaults(config_file)
    config['poll_interval'] = interval
    return save_config(config, config_file)


def get_db_path(config_file: str = "cfg.yml") -> str:
    """Get database path from config"""
    config = get_config_with_defaults(config_file)
    return config.get('db_path', DEFAULT_CONFIG['db_path'])


def update_db_path(path: str, config_file: str = "cfg.yml") -> bool:
    """Update database path in config"""
    config = get_config_with_defaults(config_file)
    config['db_path'] = str(path)
    return save_config(config, config_file)


def get_autopilot_enabled(config_file: str = "cfg.yml") -> bool:
    """Get autopilot enabled status from config"""
    config = get_config_with_defaults(config_file)
    return config.get('autopilot_enabled', False)


def update_autopilot_enabled(enabled: bool, config_file: str = "cfg.yml") -> bool:
    """Update autopilot enabled status in config"""
    config = get_config_with_defaults(config_file)
    config['autopilot_enabled'] = enabled
    return save_config(config, config_file)


def get_autopilot_silent(config_file: str = "cfg.yml") -> bool:
    """Get autopilot silent mode from config"""
    config = get_config_with_defaults(config_file)
    return config.get('autopilot_silent', False)


def update_autopilot_silent(silent: bool, config_file: str = "cfg.yml") -> bool:
    """Update autopilot silent mode in config"""
    config = get_config_with_defaults(config_file)
    config['autopilot_silent'] = silent
    return save_config(config, config_file)


def get_backup_enabled(config_file: str = "cfg.yml") -> bool:
    """Get backup enabled status from config"""
    config = get_config_with_defaults(config_file)
    return config.get('backup_enabled', True)


def get_logging_enabled(config_file: str = "cfg.yml") -> bool:
    """Get logging enabled status from config"""
    config = get_config_with_defaults(config_file)
    return config.get('logging_enabled', False)


def create_default_config_if_missing(config_file: str = "cfg.yml") -> bool:
    """Create default config file if it doesn't exist"""
    if not Path(config_file).exists():
        return save_config(DEFAULT_CONFIG, config_file)
    return True


def get_ratio_limits(config_file: str = "cfg.yml") -> tuple:
    """Get min and max ratio limits from config"""
    config = get_config_with_defaults(config_file)
    min_ratio = config.get('min_ratio', DEFAULT_CONFIG['min_ratio'])
    max_ratio = config.get('max_ratio', DEFAULT_CONFIG['max_ratio'])
    return min_ratio, max_ratio


def update_ratio_limits(min_ratio: float, max_ratio: float, config_file: str = "cfg.yml") -> bool:
    """Update ratio limits in config"""
    config = get_config_with_defaults(config_file)
    config['min_ratio'] = min_ratio
    config['max_ratio'] = max_ratio
    return save_config(config, config_file)


if __name__ == "__main__":
    # Test config loading
    print("Testing configuration loading...")
    create_default_config_if_missing()
    config = get_config_with_defaults()
    print(f"Config loaded: {config}")
    print(f"Results file path: {get_results_file_path()}")
