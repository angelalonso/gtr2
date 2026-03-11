"""
Configuration management for AIW Ratio Editor
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
        
        # Instructions
        instructions = QLabel(
            "Please select the base directory of your game.\n"
            "The program will look for AIW files in:\n"
            "<selected_path>/GameData/Locations/"
        )
        instructions.setWordWrap(True)
        instructions.setStyleSheet("color: #888; padding: 10px; font-size: 12px;")
        layout.addWidget(instructions)
        
        # Path input area
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
        browse_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 4px;
                font-family: 'Segoe UI', 'Arial', sans-serif;
                font-size: 12px;
                font-weight: bold;
                text-align: center;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
            }
        """)
        browse_btn.clicked.connect(self.browse_folder)
        
        path_layout.addWidget(self.path_edit)
        path_layout.addWidget(browse_btn)
        layout.addLayout(path_layout)
        
        # Preview of where it will look
        self.preview_label = QLabel()
        self.preview_label.setStyleSheet("color: #4CAF50; font-family: monospace; padding: 5px; font-size: 12px;")
        layout.addWidget(self.preview_label)
        
        # Error label
        self.error_label = QLabel()
        self.error_label.setStyleSheet("color: #f44336; padding: 5px; font-size: 12px;")
        self.error_label.setWordWrap(True)
        layout.addWidget(self.error_label)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.ok_btn = QPushButton("OK")
        self.ok_btn.setFixedHeight(32)
        self.ok_btn.setFixedWidth(100)
        self.ok_btn.setCursor(Qt.PointingHandCursor)
        self.ok_btn.clicked.connect(self.validate_and_accept)
        self.ok_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 4px;
                font-family: 'Segoe UI', 'Arial', sans-serif;
                font-size: 12px;
                font-weight: bold;
                text-align: center;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
            }
        """)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setFixedHeight(32)
        cancel_btn.setFixedWidth(100)
        cancel_btn.setCursor(Qt.PointingHandCursor)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                border: none;
                border-radius: 4px;
                font-family: 'Segoe UI', 'Arial', sans-serif;
                font-size: 12px;
                font-weight: bold;
                text-align: center;
            }
            QPushButton:hover {
                background-color: #d32f2f;
            }
            QPushButton:pressed {
                background-color: #b71c1c;
            }
        """)
        cancel_btn.clicked.connect(self.reject)
        
        button_layout.addStretch()
        button_layout.addWidget(self.ok_btn)
        button_layout.addWidget(cancel_btn)
        layout.addLayout(button_layout)
        
        # Connect path edit changes to preview update
        self.path_edit.textChanged.connect(self.update_preview)
        
        # Initial preview update
        self.update_preview()
    
    def browse_folder(self):
        """Open folder browser dialog"""
        folder = QFileDialog.getExistingDirectory(
            self, 
            "Select Game Base Directory",
            self.path_edit.text() if self.path_edit.text() else os.path.expanduser("~")
        )
        if folder:
            self.path_edit.setText(folder)
    
    def update_preview(self):
        """Update the preview of where the program will look"""
        path_text = self.path_edit.text().strip()
        if path_text:
            preview_path = Path(path_text) / "GameData" / "Locations"
            self.preview_label.setText(f"Will scan: {preview_path}")
            
            # Check if the path exists and show appropriate color
            if preview_path.exists():
                self.preview_label.setStyleSheet("color: #4CAF50; font-family: monospace; padding: 5px; font-size: 12px;")
            else:
                self.preview_label.setStyleSheet("color: #FFA500; font-family: monospace; padding: 5px; font-size: 12px;")
        else:
            self.preview_label.setText("")
    
    def validate_and_accept(self):
        """Validate the selected path and accept if valid"""
        path_text = self.path_edit.text().strip()
        
        if not path_text:
            self.error_label.setText("Please select a path")
            return
        
        path = Path(path_text)
        
        # Check if the Locations directory exists (or can be created)
        locations_path = path / "GameData" / "Locations"
        
        if not path.exists():
            self.error_label.setText("The selected path does not exist")
            return
        
        if not locations_path.exists():
            # Warn but don't prevent selection
            reply = QMessageBox.question(
                self,
                "Path Warning",
                f"The Locations directory does not exist at:\n{locations_path}\n\n"
                f"This may mean you've selected the wrong folder.\n"
                f"Do you want to use this path anyway?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply != QMessageBox.Yes:
                return
        
        self.selected_path = path
        self.accept()


# Default configuration values
DEFAULT_CONFIG = {
    'base_path': '',
    'historic_csv': '',
    'goal_percent': 50.0,  # Default to 50% (middle)
    'goal_offset': 0.0,     # Default to 0 offset
    'percent_ratio': 1.0    # Default to 1:1 ratio
}


def load_config(config_file="cfg.yml"):
    """
    Load configuration from YAML file
    
    Args:
        config_file (str): Path to the configuration file
        
    Returns:
        dict: Configuration dictionary or None if file doesn't exist
    """
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
    """
    Save configuration to YAML file
    
    Args:
        config (dict): Configuration dictionary to save
        config_file (str): Path to the configuration file
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        with open(config_file, 'w') as f:
            yaml.dump(config, f, default_flow_style=False, indent=2)
        print(f"Saved configuration to {config_file}")
        return True
    except Exception as e:
        print(f"Error saving to {config_file}: {e}")
        return False


def get_config_with_defaults(config_file="cfg.yml"):
    """
    Load configuration and ensure all default keys exist
    
    Args:
        config_file (str): Path to the configuration file
        
    Returns:
        dict: Configuration dictionary with all default keys present
    """
    config = load_config(config_file)
    
    if config is None:
        # No config file exists, return defaults
        print(f"No configuration file found at {config_file}, using defaults")
        return DEFAULT_CONFIG.copy()
    
    # Check for missing keys and add defaults
    modified = False
    for key, default_value in DEFAULT_CONFIG.items():
        if key not in config:
            print(f"Adding missing configuration key '{key}' with default value: {default_value}")
            config[key] = default_value
            modified = True
    
    # Save if we added any missing keys
    if modified:
        save_config(config, config_file)
    
    return config


def get_base_path_from_config(config_file="cfg.yml"):
    """
    Extract base path from configuration
    
    Args:
        config_file (str): Path to the configuration file
        
    Returns:
        Path or None: The base path if valid, None otherwise
    """
    config = get_config_with_defaults(config_file)
    
    if config and config.get('base_path'):
        path = Path(config['base_path'])
        if path.exists():
            return path
        else:
            print(f"Warning: Path from {config_file} does not exist: {path}")
    
    return None


def prompt_for_base_path():
    """
    Show dialog to prompt user for base path
    
    Returns:
        Path or None: Selected path or None if cancelled
    """
    from PyQt5.QtWidgets import QApplication
    
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    
    dialog = PathSelectionDialog()
    if dialog.exec_() == QDialog.Accepted:
        return dialog.selected_path
    
    return None


def get_or_prompt_base_path(config_file="cfg.yml"):
    """
    Get base path from config or prompt user if not available/invalid
    
    Args:
        config_file (str): Path to the configuration file
        
    Returns:
        Path or None: The base path or None if user cancelled
    """
    # Try to get from config first
    base_path = get_base_path_from_config(config_file)
    
    if base_path is None:
        # Prompt user
        base_path = prompt_for_base_path()
        
        if base_path is not None:
            # Save to config (preserving other values)
            config = get_config_with_defaults(config_file)
            config['base_path'] = str(base_path)
            save_config(config, config_file)
    
    return base_path


def update_base_path(new_path, config_file="cfg.yml"):
    """
    Update the base path in the configuration file
    
    Args:
        new_path (str or Path): New base path to save
        config_file (str): Path to the configuration file
        
    Returns:
        bool: True if successful, False otherwise
    """
    config = get_config_with_defaults(config_file)
    config['base_path'] = str(new_path)
    return save_config(config, config_file)


# New functions for additional configuration parameters

def get_config_value(key, default=None, config_file="cfg.yml"):
    """
    Get a specific configuration value
    
    Args:
        key (str): Configuration key to retrieve
        default: Default value if key doesn't exist
        config_file (str): Path to the configuration file
        
    Returns:
        The configuration value or default if not found
    """
    config = get_config_with_defaults(config_file)
    return config.get(key, default)


def set_config_value(key, value, config_file="cfg.yml"):
    """
    Set a specific configuration value
    
    Args:
        key (str): Configuration key to set
        value: Value to set
        config_file (str): Path to the configuration file
        
    Returns:
        bool: True if successful, False otherwise
    """
    config = get_config_with_defaults(config_file)
    config[key] = value
    return save_config(config, config_file)


def validate_historic_csv(path, config_file="cfg.yml"):
    """
    Validate that a historic CSV file exists and can be read
    
    Args:
        path (str or Path): Path to the CSV file
        config_file (str): Path to the configuration file (for logging)
        
    Returns:
        bool: True if valid, False otherwise
    """
    if not path:
        return False
    
    csv_path = Path(path)
    
    if not csv_path.exists():
        print(f"Warning: Historic CSV file does not exist: {csv_path}")
        return False
    
    if not csv_path.is_file():
        print(f"Warning: Historic CSV path is not a file: {csv_path}")
        return False
    
    if csv_path.suffix.lower() != '.csv':
        print(f"Warning: Historic CSV file does not have .csv extension: {csv_path}")
        return False
    
    return True


def validate_goal_percent(value, config_file="cfg.yml"):
    """
    Validate that a goal percent value is a number
    
    Args:
        value: Value to validate
        config_file (str): Path to the configuration file (for logging)
        
    Returns:
        bool: True if valid, False otherwise
    """
    try:
        float_val = float(value)
        return True
    except (TypeError, ValueError):
        print(f"Warning: Goal percent must be a number, got: {value}")
        return False


def validate_goal_offset(value, config_file="cfg.yml"):
    """
    Validate that a goal offset value is a number
    
    Args:
        value: Value to validate
        config_file (str): Path to the configuration file (for logging)
        
    Returns:
        bool: True if valid, False otherwise
    """
    try:
        float_val = float(value)
        return True
    except (TypeError, ValueError):
        print(f"Warning: Goal offset must be a number, got: {value}")
        return False


def validate_percent_ratio(value, config_file="cfg.yml"):
    """
    Validate that a percent ratio value is a number
    
    Args:
        value: Value to validate
        config_file (str): Path to the configuration file (for logging)
        
    Returns:
        bool: True if valid, False otherwise
    """
    try:
        float_val = float(value)
        return True
    except (TypeError, ValueError):
        print(f"Warning: Percent ratio must be a number, got: {value}")
        return False


def get_historic_csv(config_file="cfg.yml"):
    """
    Get the historic CSV path from configuration
    
    Args:
        config_file (str): Path to the configuration file
        
    Returns:
        str or None: The historic CSV path if valid, None otherwise
    """
    config = get_config_with_defaults(config_file)
    
    if config and 'historic_csv' in config:
        path = config['historic_csv']
        if path and validate_historic_csv(path, config_file):
            return path
        elif path:
            print(f"Warning: Historic CSV from {config_file} is invalid: {path}")
    
    return None


def get_goal_percent(config_file="cfg.yml"):
    """
    Get the goal percent from configuration
    
    Args:
        config_file (str): Path to the configuration file
        
    Returns:
        float: The goal percent (defaults to 50.0 if not found or invalid)
    """
    config = get_config_with_defaults(config_file)
    
    if config and 'goal_percent' in config:
        value = config['goal_percent']
        if validate_goal_percent(value, config_file):
            return float(value)
        else:
            print(f"Warning: Goal percent from {config_file} is invalid: {value}")
    
    return DEFAULT_CONFIG['goal_percent']


def get_goal_offset(config_file="cfg.yml"):
    """
    Get the goal offset from configuration
    
    Args:
        config_file (str): Path to the configuration file
        
    Returns:
        float: The goal offset (defaults to 0.0 if not found or invalid)
    """
    config = get_config_with_defaults(config_file)
    
    if config and 'goal_offset' in config:
        value = config['goal_offset']
        if validate_goal_offset(value, config_file):
            return float(value)
        else:
            print(f"Warning: Goal offset from {config_file} is invalid: {value}")
    
    return DEFAULT_CONFIG['goal_offset']


def get_percent_ratio(config_file="cfg.yml"):
    """
    Get the percent ratio from configuration
    
    Args:
        config_file (str): Path to the configuration file
        
    Returns:
        float: The percent ratio (defaults to 1.0 if not found or invalid)
    """
    config = get_config_with_defaults(config_file)
    
    if config and 'percent_ratio' in config:
        value = config['percent_ratio']
        if validate_percent_ratio(value, config_file):
            return float(value)
        else:
            print(f"Warning: Percent ratio from {config_file} is invalid: {value}")
    
    return DEFAULT_CONFIG['percent_ratio']


def update_historic_csv(path, config_file="cfg.yml"):
    """
    Update the historic CSV path in the configuration file
    
    Args:
        path (str or Path): New historic CSV path to save
        config_file (str): Path to the configuration file
        
    Returns:
        bool: True if successful, False otherwise
    """
    config = get_config_with_defaults(config_file)
    config['historic_csv'] = str(path) if path else ''
    return save_config(config, config_file)


def update_goal_percent(value, config_file="cfg.yml"):
    """
    Update the goal percent in the configuration file
    
    Args:
        value (float or int): New goal percent to save
        config_file (str): Path to the configuration file
        
    Returns:
        bool: True if successful, False otherwise
    """
    config = get_config_with_defaults(config_file)
    config['goal_percent'] = float(value)
    return save_config(config, config_file)


def update_goal_offset(value, config_file="cfg.yml"):
    """
    Update the goal offset in the configuration file
    
    Args:
        value (float or int): New goal offset to save
        config_file (str): Path to the configuration file
        
    Returns:
        bool: True if successful, False otherwise
    """
    config = get_config_with_defaults(config_file)
    config['goal_offset'] = float(value)
    return save_config(config, config_file)


def update_percent_ratio(value, config_file="cfg.yml"):
    """
    Update the percent ratio in the configuration file
    
    Args:
        value (float or int): New percent ratio to save
        config_file (str): Path to the configuration file
        
    Returns:
        bool: True if successful, False otherwise
    """
    config = get_config_with_defaults(config_file)
    config['percent_ratio'] = float(value)
    return save_config(config, config_file)


def get_all_config_values(config_file="cfg.yml"):
    """
    Get all configuration values with defaults applied
    
    Args:
        config_file (str): Path to the configuration file
        
    Returns:
        dict: Complete configuration dictionary
    """
    return get_config_with_defaults(config_file)


def reset_to_defaults(config_file="cfg.yml"):
    """
    Reset configuration to default values
    
    Args:
        config_file (str): Path to the configuration file
        
    Returns:
        bool: True if successful, False otherwise
    """
    return save_config(DEFAULT_CONFIG.copy(), config_file)


def validate_all_config_values(config_file="cfg.yml"):
    """
    Validate all configuration values
    
    Args:
        config_file (str): Path to the configuration file
        
    Returns:
        dict: Dictionary with validation results for each key
    """
    config = get_config_with_defaults(config_file)
    
    results = {
        'base_path': {
            'present': 'base_path' in config,
            'valid': Path(config.get('base_path', '')).exists() if config.get('base_path') else False,
            'value': config.get('base_path', '')
        },
        'historic_csv': {
            'present': 'historic_csv' in config,
            'valid': validate_historic_csv(config.get('historic_csv', ''), config_file) if config.get('historic_csv') else False,
            'value': config.get('historic_csv', '')
        },
        'goal_percent': {
            'present': 'goal_percent' in config,
            'valid': validate_goal_percent(config.get('goal_percent'), config_file),
            'value': config.get('goal_percent', DEFAULT_CONFIG['goal_percent'])
        },
        'goal_offset': {
            'present': 'goal_offset' in config,
            'valid': validate_goal_offset(config.get('goal_offset'), config_file),
            'value': config.get('goal_offset', DEFAULT_CONFIG['goal_offset'])
        },
        'percent_ratio': {
            'present': 'percent_ratio' in config,
            'valid': validate_percent_ratio(config.get('percent_ratio'), config_file),
            'value': config.get('percent_ratio', DEFAULT_CONFIG['percent_ratio'])
        }
    }
    
    return results

def ensure_historic_csv_exists(config_file="cfg.yml"):
    """
    Ensure the historic CSV file path exists in config and create default if needed
    """
    config = get_config_with_defaults(config_file)
    
    if not config.get('historic_csv'):
        # Set default CSV path
        default_csv = str(Path.cwd() / "historic.csv")
        config['historic_csv'] = default_csv
        save_config(config, config_file)
        print(f"Created default historic CSV path: {default_csv}")
    
    return config['historic_csv']
