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
            yaml.dump(config, f)
        print(f"Saved configuration to {config_file}")
        return True
    except Exception as e:
        print(f"Error saving to {config_file}: {e}")
        return False


def get_base_path_from_config(config_file="cfg.yml"):
    """
    Extract base path from configuration
    
    Args:
        config_file (str): Path to the configuration file
        
    Returns:
        Path or None: The base path if valid, None otherwise
    """
    config = load_config(config_file)
    
    if config and 'base_path' in config:
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
            # Save to config
            config = {'base_path': str(base_path)}
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
    config = load_config(config_file) or {}
    config['base_path'] = str(new_path)
    return save_config(config, config_file)
