"""
Configuration management for Live AI Tuner
Handles loading, saving, and validating the configuration from cfg.yml
"""

import yaml
from pathlib import Path
import os
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QFileDialog, QMessageBox
from PyQt5.QtCore import Qt


class PathSelectionDialog(QDialog):
    """Dialog for selecting the base path when cfg.yml is missing or path is invalid"""
    
    def __init__(self, parent=None, current_path=None):
        super().__init__(parent)
        self.selected_path = current_path
        self.setup_ui()
        
    def setup_ui(self):
        self.setWindowTitle("Select Game Base Path")
        self.setModal(True)
        self.setMinimumWidth(500)
        
        layout = QVBoxLayout(self)
        
        instructions = QLabel(
            "Please select the base directory of your game.\n"
            "The program will look for AIW files and monitor:\n"
            "<selected_path>/UserData/Log/Results/raceresults.txt"
        )
        instructions.setWordWrap(True)
        instructions.setStyleSheet("color: #888; padding: 10px; font-size: 12px;")
        layout.addWidget(instructions)
        
        path_layout = QHBoxLayout()
        
        self.path_edit = QLineEdit()
        self.path_edit.setPlaceholderText("Select or enter the game base path...")
        self.path_edit.setFixedHeight(30)
        if self.selected_path:
            self.path_edit.setText(str(self.selected_path))
        
        browse_btn = QPushButton("Browse...")
        browse_btn.setFixedHeight(30)
        browse_btn.setFixedWidth(100)
        browse_btn.setCursor(Qt.PointingHandCursor)
        browse_btn.clicked.connect(self.browse_folder)
        
        path_layout.addWidget(self.path_edit)
        path_layout.addWidget(browse_btn)
        layout.addLayout(path_layout)
        
        self.preview_label = QLabel()
        self.preview_label.setStyleSheet("color: #4CAF50; font-family: monospace; padding: 5px; font-size: 12px;")
        layout.addWidget(self.preview_label)
        
        self.error_label = QLabel()
        self.error_label.setStyleSheet("color: #f44336; padding: 5px; font-size: 12px;")
        self.error_label.setWordWrap(True)
        layout.addWidget(self.error_label)
        
        button_layout = QHBoxLayout()
        
        self.ok_btn = QPushButton("OK")
        self.ok_btn.setFixedHeight(32)
        self.ok_btn.setFixedWidth(100)
        self.ok_btn.clicked.connect(self.validate_and_accept)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setFixedHeight(32)
        cancel_btn.setFixedWidth(100)
        cancel_btn.clicked.connect(self.reject)
        
        button_layout.addStretch()
        button_layout.addWidget(self.ok_btn)
        button_layout.addWidget(cancel_btn)
        layout.addLayout(button_layout)
        
        self.path_edit.textChanged.connect(self.update_preview)
        self.update_preview()
    
    def browse_folder(self):
        folder = QFileDialog.getExistingDirectory(
            self, 
            "Select Game Base Directory",
            self.path_edit.text() if self.path_edit.text() else os.path.expanduser("~")
        )
        if folder:
            self.path_edit.setText(folder)
    
    def update_preview(self):
        path_text = self.path_edit.text().strip()
        if path_text:
            preview_path = Path(path_text) / "UserData" / "Log" / "Results"
            self.preview_label.setText(f"Will monitor: {preview_path / 'raceresults.txt'}")
            
            if preview_path.exists():
                self.preview_label.setStyleSheet("color: #4CAF50; font-family: monospace; padding: 5px; font-size: 12px;")
            else:
                self.preview_label.setStyleSheet("color: #FFA500; font-family: monospace; padding: 5px; font-size: 12px;")
        else:
            self.preview_label.setText("")
    
    def validate_and_accept(self):
        path_text = self.path_edit.text().strip()
        
        if not path_text:
            self.error_label.setText("Please select a path")
            return
        
        path = Path(path_text)
        
        if not path.exists():
            self.error_label.setText("The selected path does not exist")
            return
        
        self.selected_path = path
        self.accept()


DEFAULT_CONFIG = {
    'base_path': '',
    'formulas_dir': './track_formulas',
    'db_path': 'live_ai_tuner.db',
    'track_formula_db_path': 'track_formulas.db',  # ← New
    'auto_apply': False,
    'backup_enabled': True,
    'logging_enabled': False,
    'autopilot_enabled': False,
    'autopilot_silent': False,
}


def load_config(config_file="cfg.yml"):
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


def save_config(config, config_file="cfg.yml"):
    try:
        with open(config_file, 'w') as f:
            yaml.dump(config, f, default_flow_style=False, indent=2)
        return True
    except Exception as e:
        print(f"Error saving to {config_file}: {e}")
        return False


def get_config_with_defaults(config_file="cfg.yml"):
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


def get_base_path_from_config(config_file="cfg.yml"):
    config = get_config_with_defaults(config_file)
    
    if config and config.get('base_path'):
        path = Path(config['base_path'])
        if path.exists():
            return path
    
    return None


def prompt_for_base_path():
    from PyQt5.QtWidgets import QApplication
    
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    
    dialog = PathSelectionDialog()
    if dialog.exec_() == QDialog.Accepted:
        return dialog.selected_path
    
    return None


def get_or_prompt_base_path(config_file="cfg.yml"):
    base_path = get_base_path_from_config(config_file)
    
    if base_path is None:
        base_path = prompt_for_base_path()
        
        if base_path is not None:
            config = get_config_with_defaults(config_file)
            config['base_path'] = str(base_path)
            save_config(config, config_file)
    
    return base_path


def update_base_path(new_path, config_file="cfg.yml"):
    config = get_config_with_defaults(config_file)
    config['base_path'] = str(new_path)
    return save_config(config, config_file)


def get_formulas_dir(config_file="cfg.yml"):
    config = get_config_with_defaults(config_file)
    return config.get('formulas_dir', './track_formulas')


def update_formulas_dir(path, config_file="cfg.yml"):
    config = get_config_with_defaults(config_file)
    config['formulas_dir'] = str(path)
    return save_config(config, config_file)


# ── New: database path ────────────────────────────────────────────────────────

def get_db_path(config_file="cfg.yml") -> str:
    """Return the path to the SQLite database file."""
    config = get_config_with_defaults(config_file)
    return config.get('db_path', DEFAULT_CONFIG['db_path'])


def update_db_path(path, config_file="cfg.yml") -> bool:
    """Update the SQLite database path in the config file."""
    config = get_config_with_defaults(config_file)
    config['db_path'] = str(path)
    return save_config(config, config_file)

def get_track_formula_db_path(config_file="cfg.yml") -> str:
    """Return the path to the track formula SQLite database file."""
    config = get_config_with_defaults(config_file)
    return config.get('track_formula_db_path', 'track_formulas.db')


def update_track_formula_db_path(path, config_file="cfg.yml") -> bool:
    """Update the track formula database path in the config file."""
    config = get_config_with_defaults(config_file)
    config['track_formula_db_path'] = str(path)
    return save_config(config, config_file)

# ── Existing helpers (unchanged) ──────────────────────────────────────────────

def get_auto_apply(config_file="cfg.yml"):
    config = get_config_with_defaults(config_file)
    return config.get('auto_apply', False)


def update_auto_apply(value, config_file="cfg.yml"):
    config = get_config_with_defaults(config_file)
    config['auto_apply'] = value
    return save_config(config, config_file)


def get_backup_enabled(config_file="cfg.yml"):
    config = get_config_with_defaults(config_file)
    return config.get('backup_enabled', True)


def update_backup_enabled(value, config_file="cfg.yml"):
    config = get_config_with_defaults(config_file)
    config['backup_enabled'] = value
    return save_config(config, config_file)


def get_logging_enabled(config_file="cfg.yml"):
    config = get_config_with_defaults(config_file)
    return config.get('logging_enabled', False)


def update_logging_enabled(value, config_file="cfg.yml"):
    config = get_config_with_defaults(config_file)
    config['logging_enabled'] = value
    return save_config(config, config_file)


def get_autopilot_enabled(config_file="cfg.yml"):
    config = get_config_with_defaults(config_file)
    return config.get('autopilot_enabled', False)


def update_autopilot_enabled(value, config_file="cfg.yml"):
    config = get_config_with_defaults(config_file)
    config['autopilot_enabled'] = value
    return save_config(config, config_file)


def get_autopilot_silent(config_file="cfg.yml"):
    config = get_config_with_defaults(config_file)
    return config.get('autopilot_silent', False)


def update_autopilot_silent(value, config_file="cfg.yml"):
    config = get_config_with_defaults(config_file)
    config['autopilot_silent'] = value
    return save_config(config, config_file)
