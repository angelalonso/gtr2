#!/usr/bin/env python3
"""
Pytest configuration and fixtures for Dynamic AI tests
"""

import sys
import pytest
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from test_temp_env import TempTestEnvironment
from test_backup_manager import OriginalFileBackup


@pytest.fixture
def temp_env():
    """Fixture providing a temporary test environment"""
    env = TempTestEnvironment()
    env.create()
    yield env
    env.cleanup()


@pytest.fixture
def backup_manager():
    """Fixture providing backup manager for test isolation"""
    manager = OriginalFileBackup()
    
    # Backup important files before tests
    classes_path = project_root / "vehicle_classes.json"
    if classes_path.exists():
        manager.backup_file(classes_path)
    
    config_path = project_root / "cfg.yml"
    if config_path.exists():
        manager.backup_file(config_path)
    
    yield manager
    
    # Restore after tests
    manager.restore_all()
