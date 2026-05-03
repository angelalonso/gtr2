#!/usr/bin/env python3
"""
Style definitions for lightweight GUI
"""

DARK_STYLE = """
QMainWindow, QWidget { background-color: #1e1e1e; }
QLabel { color: white; }
QGroupBox { 
    color: #4CAF50; 
    border: 1px solid #555; 
    border-radius: 4px; 
    margin-top: 8px; 
    padding-top: 8px;
}
QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; }
QPushButton { 
    background-color: #4CAF50; 
    color: white; 
    border: none; 
    border-radius: 3px; 
    padding: 6px 12px;
}
QPushButton:hover { background-color: #45a049; }
QPushButton:disabled { background-color: #555; color: #888; }
QDoubleSpinBox, QSpinBox { 
    background-color: #3c3c3c; 
    color: white; 
    border: 1px solid #4CAF50; 
    border-radius: 3px; 
    padding: 3px;
}
QCheckBox { color: white; }
QRadioButton { color: white; }
QListWidget { 
    background-color: #2b2b2b; 
    color: white; 
    border: 1px solid #555; 
    border-radius: 3px;
}
QListWidget::item:selected { background-color: #4CAF50; }
QStatusBar { color: #888; }
"""


def apply_dark_theme(app):
    """Apply dark theme to application"""
    app.setStyle('Fusion')
    app.setStyleSheet(DARK_STYLE)
