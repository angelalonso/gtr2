#!/usr/bin/env python3
"""
Dynamic AI - Formula Visualizer (Standalone)
Shows curve graphs and formula management
Runs its own pre-run checks before starting
"""

import sys
import logging
from pathlib import Path

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout
)
from PyQt5.QtCore import Qt

from core_database import CurveDatabase
from core_config import get_db_path, get_config_with_defaults, create_default_config_if_missing
from gui_curve_graph import CurveGraphWidget
from gui_session_panel import SessionPanel
from gui_common import setup_dark_theme
from gui_pre_run_check_light import run_pre_run_check


logger = logging.getLogger(__name__)


class FormulaVisualizer(QMainWindow):
    """Standalone Formula Visualizer window"""
    
    def __init__(self, config_file: str = "cfg.yml"):
        super().__init__()
        self.config_file = config_file
        self.config = get_config_with_defaults(config_file)
        self.db_path = get_db_path(config_file)
        self.db = CurveDatabase(self.db_path)
        
        self.setWindowTitle("Dynamic AI - Formula Visualizer")
        self.setGeometry(100, 100, 1200, 800)
        self.setMinimumWidth(1000)
        self.setMinimumHeight(700)
        
        self.setup_ui()
        self.load_initial_data()
    
    def setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Curve graph
        self.curve_graph = CurveGraphWidget(self.db, self)
        layout.addWidget(self.curve_graph, stretch=3)
        
        # Session panels
        middle_layout = QHBoxLayout()
        middle_layout.setSpacing(15)
        
        self.qual_panel = SessionPanel("qual", "Qualifying Session", self.db, self)
        self.qual_panel.formula_changed.connect(self.on_formula_changed)
        self.qual_panel.show_data_toggled.connect(self.on_show_data_toggled)
        middle_layout.addWidget(self.qual_panel)
        
        self.race_panel = SessionPanel("race", "Race Session", self.db, self)
        self.race_panel.formula_changed.connect(self.on_formula_changed)
        self.race_panel.show_data_toggled.connect(self.on_show_data_toggled)
        middle_layout.addWidget(self.race_panel)
        
        layout.addLayout(middle_layout, stretch=1)
    
    def load_initial_data(self):
        """Load initial data into the visualizer"""
        if self.curve_graph:
            self.curve_graph.load_data()
            self.curve_graph.full_refresh()
    
    def on_formula_changed(self, session_type: str, a: float, b: float):
        """Handle formula changes from panels"""
        if self.curve_graph:
            if session_type == "qual":
                self.curve_graph.qual_a = a
                self.curve_graph.qual_b = b
            else:
                self.curve_graph.race_a = a
                self.curve_graph.race_b = b
            self.curve_graph.update_graph()
    
    def on_show_data_toggled(self, session_type: str, show: bool):
        """Handle show/hide data toggles"""
        if self.curve_graph:
            if session_type == "qual":
                self.curve_graph.set_show_qualifying(show)
            else:
                self.curve_graph.set_show_race(show)


def main():
    # Ensure config and database exist
    create_default_config_if_missing()
    db_path = get_db_path()
    if not Path(db_path).exists():
        CurveDatabase(db_path)
    
    # Run pre-run checks
    if not run_pre_run_check("cfg.yml"):
        print("Pre-run checks failed or cancelled. Exiting.")
        sys.exit(1)
    
    setup_dark_theme(QApplication.instance() or QApplication(sys.argv))
    
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    
    window = FormulaVisualizer()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
