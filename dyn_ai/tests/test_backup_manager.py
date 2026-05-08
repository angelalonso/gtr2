#!/usr/bin/env python3
"""
Backup manager for tests - ensures tests don't permanently modify original files
"""

import sys
from pathlib import Path

# Add parent directory to path so we can import application modules
sys.path.insert(0, str(Path(__file__).parent.parent))

import shutil
import tempfile
from pathlib import Path
from typing import Dict, Optional


class OriginalFileBackup:
    """
    Manages backups of original files before tests modify them.
    Ensures all modifications are restored after tests.
    """
    
    _instance = None
    _backups = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._backups = {}
        return cls._instance
    
    def backup_file(self, file_path: Path) -> bool:
        """Create a backup of a file before modifying it"""
        if not file_path.exists():
            return False
        
        file_key = str(file_path.absolute())
        
        if file_key in self._backups:
            return True
        
        backup_dir = Path(tempfile.gettempdir()) / "live_ai_tuner_test_backups"
        backup_dir.mkdir(parents=True, exist_ok=True)
        
        backup_path = backup_dir / f"{file_path.name}.backup"
        shutil.copy2(file_path, backup_path)
        self._backups[file_key] = backup_path
        return True
    
    def restore_all(self):
        """Restore all backed up files to their original state"""
        for original_path_str, backup_path in self._backups.items():
            original_path = Path(original_path_str)
            if original_path.exists() and backup_path.exists():
                shutil.copy2(backup_path, original_path)
            elif backup_path.exists():
                shutil.copy2(backup_path, original_path)
        
        self.cleanup_backups()
    
    def cleanup_backups(self):
        """Delete all backup files without restoring"""
        for backup_path in self._backups.values():
            if backup_path.exists():
                backup_path.unlink()
        
        backup_dir = Path(tempfile.gettempdir()) / "live_ai_tuner_test_backups"
        if backup_dir.exists():
            shutil.rmtree(backup_dir, ignore_errors=True)
        
        self._backups.clear()
    
    def get_backup_path(self, original_path: Path) -> Optional[Path]:
        """Get backup path for an original file"""
        file_key = str(original_path.absolute())
        return self._backups.get(file_key)
    
    def is_backed_up(self, file_path: Path) -> bool:
        """Check if a file has been backed up"""
        return str(file_path.absolute()) in self._backups
