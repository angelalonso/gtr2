#!/usr/bin/env python3
"""
Dyn AI Data Management Tool
Manages vehicle classes and imports race data into the Dynamic AI SQLite database
"""

import sys
from pathlib import Path

from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QLabel, QTabWidget
from PyQt5.QtCore import Qt

from gui_data_manager_common import SimpleCurveDatabase
from gui_data_manager_database import DatabaseManagerTab
from gui_data_manager_vehicle import VehicleTab
from gui_data_manager_import import ImportTab


class DynAIDataManager(QMainWindow):
    """Main GUI window for Dyn AI Data Management"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Dyn AI Data Manager - Dynamic AI")
        self.setGeometry(100, 100, 1400, 900)
        
        self.db_path = "ai_data.db"
        self.simple_db = SimpleCurveDatabase(self.db_path)
        
        self.setup_ui()
        self.apply_styles()
    
    def setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        title = QLabel("Dyn AI Data Manager")
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: #4CAF50;")
        title.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title)
        
        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget)
        
        # Laptimes and Ratios tab (first)
        self.db_manager_tab = DatabaseManagerTab(self.simple_db, self)
        self.db_manager_tab.data_changed.connect(self.on_data_changed)
        self.tab_widget.addTab(self.db_manager_tab, "Laptimes and Ratios")
        
        # Vehicle Classes tab (second)
        self.vehicle_tab = VehicleTab(self)
        self.tab_widget.addTab(self.vehicle_tab, "Vehicle Classes")
        
        # Race Data Import tab (third)
        self.import_tab = ImportTab(self.db_path, self)
        self.tab_widget.addTab(self.import_tab, "Race Data Import")
        
        # About tab (fourth)
        about_tab = self.create_about_tab()
        self.tab_widget.addTab(about_tab, "About")
        
        self.statusBar().showMessage("Ready")
    
    def create_about_tab(self):
        from PyQt5.QtWidgets import QTextEdit
        
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        about_text = QTextEdit()
        about_text.setReadOnly(True)
        about_text.setHtml("""
        <h2>Dyn AI Data Manager</h2>
        <p>Comprehensive data management tool for the Dynamic AI system.</p>
        
        <h3>Laptimes and Ratios:</h3>
        <ul>
            <li>View all data points in a sortable table</li>
            <li>Filter by track, vehicle class, and session type</li>
            <li>Visualize data points on an interactive graph</li>
            <li>Click on graph points to select corresponding table rows</li>
            <li>Ctrl+Click to select/deselect individual points</li>
            <li>Shift+Click to select ranges of points</li>
            <li>Select All button for bulk operations</li>
            <li>Edit multiple points at once with the multi-edit dialog</li>
            <li>Delete selected points in bulk</li>
            <li>Perfect for removing outliers or correcting incorrect data</li>
        </ul>
        
        <h3>Vehicle Classes Management:</h3>
        <ul>
            <li>Launch the standalone Vehicle Manager dialog</li>
            <li>Add, rename, or delete vehicle classes</li>
            <li>Add, edit, or remove vehicles from classes</li>
            <li>Import vehicles from GTR2 installation</li>
            <li>Batch assign unassigned vehicles to classes</li>
            <li>Changes are saved to vehicle_classes.json</li>
        </ul>
        
        <h3>Race Data Import:</h3>
        <ul>
            <li>Import race data from CSV files (compatible with historic.csv format)</li>
            <li>Automatically calculates midpoint = (AI Best + AI Worst) / 2</li>
            <li>Separates qualifying and race session data</li>
            <li>Duplicate detection prevents redundant entries</li>
        </ul>
        """)
        layout.addWidget(about_text)
        
        return tab
    
    def apply_styles(self):
        self.setStyleSheet("""
            QMainWindow {
                background-color: #1e1e1e;
            }
            QWidget {
                background-color: #1e1e1e;
                color: #ffffff;
            }
            QGroupBox {
                color: #4CAF50;
                border: 2px solid #555;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
                font-weight: bold;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
            QTableWidget {
                background-color: #2b2b2b;
                alternate-background-color: #3c3c3c;
                gridline-color: #555;
                selection-background-color: #4CAF50;
            }
            QTableWidget::item {
                padding: 4px;
            }
            QHeaderView::section {
                background-color: #3c3c3c;
                color: white;
                padding: 6px;
                border: none;
            }
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
            QProgressBar {
                border: 1px solid #555;
                border-radius: 4px;
                text-align: center;
                color: white;
            }
            QProgressBar::chunk {
                background-color: #4CAF50;
                border-radius: 3px;
            }
            QCheckBox {
                spacing: 8px;
            }
            QTabWidget::pane {
                border: 1px solid #555;
                background-color: #2b2b2b;
            }
            QTabBar::tab {
                background-color: #3c3c3c;
                padding: 8px 16px;
                margin-right: 2px;
            }
            QTabBar::tab:selected {
                background-color: #4CAF50;
            }
            QTextEdit {
                background-color: #2b2b2b;
                border: 1px solid #555;
                border-radius: 4px;
                font-family: monospace;
            }
            QListWidget {
                background-color: #2b2b2b;
                color: white;
                border: 1px solid #555;
                border-radius: 4px;
                outline: none;
            }
            QListWidget::item:selected {
                background-color: #4CAF50;
            }
            QLineEdit {
                background-color: #3c3c3c;
                color: white;
                border: 1px solid #555;
                border-radius: 4px;
                padding: 6px;
            }
            QSplitter::handle {
                background-color: #555;
            }
            QComboBox {
                background-color: #3c3c3c;
                color: white;
                border: 1px solid #4CAF50;
                border-radius: 4px;
                padding: 6px;
                min-width: 150px;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox::down-arrow {
                image: none;
                border: none;
            }
        """)
    
    def refresh_db_manager_tab(self):
        """Refresh the database manager tab"""
        if hasattr(self, 'db_manager_tab'):
            self.db_manager_tab.refresh_filters()
            self.db_manager_tab.refresh_table()
    
    def on_data_changed(self):
        """Called when data is changed in the database manager tab"""
        pass


def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    window = DynAIDataManager()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
