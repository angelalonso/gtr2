#!/usr/bin/env python3
"""
GUI module for curve viewer
Provides reusable GUI components and dialogs using pyqtgraph for lightweight plotting
"""

import numpy as np
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QListWidget, 
    QDoubleSpinBox, QPushButton, QGroupBox, QSplitter, 
    QMessageBox, QAbstractItemView, QComboBox, QDialog,
    QDialogButtonBox, QListWidgetItem, QSlider, QSpinBox,
    QCheckBox, QTabWidget, QTableWidget, QTableWidgetItem,
    QHeaderView, QScrollArea
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor
import pyqtgraph as pg


class MultiTrackSelectionDialog(QDialog):
    """Dialog for selecting multiple tracks"""
    
    def __init__(self, all_tracks, current_track, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select Multiple Tracks")
        self.setGeometry(300, 300, 400, 500)
        self.all_tracks = all_tracks
        self.current_track = current_track
        self.selected_tracks = [current_track] if current_track else []
        
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Instructions
        info_label = QLabel("Select tracks to display data from.\n"
                           "Ctrl+Click = multi-select | Shift+Click = range")
        info_label.setStyleSheet("color: #888; font-size: 10px;")
        info_label.setWordWrap(True)
        layout.addWidget(info_label)
        
        # Track list
        self.track_list = QListWidget()
        self.track_list.setSelectionMode(QAbstractItemView.ExtendedSelection)
        
        # Add items and select the current track
        for i, track in enumerate(self.all_tracks):
            item = QListWidgetItem(track)
            self.track_list.addItem(item)
            if track == self.current_track:
                item.setSelected(True)
                self.track_list.setCurrentItem(item)
        
        layout.addWidget(self.track_list)
        
        # Buttons
        btn_layout = QHBoxLayout()
        select_all_btn = QPushButton("Select All")
        select_all_btn.clicked.connect(self.track_list.selectAll)
        btn_layout.addWidget(select_all_btn)
        
        clear_btn = QPushButton("Clear All")
        clear_btn.clicked.connect(self.track_list.clearSelection)
        btn_layout.addWidget(clear_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        
        # Dialog buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
    def get_selected_tracks(self):
        return [item.text() for item in self.track_list.selectedItems()]


class AdvancedSettingsDialog(QDialog):
    """Advanced settings window with data management and logging options"""
    
    def __init__(self, parent=None, db=None, log_window=None):
        super().__init__(parent)
        self.parent = parent
        self.db = db
        self.log_window = log_window
        self.setWindowTitle("Advanced Settings")
        self.setGeometry(200, 200, 700, 500)
        self.setMinimumWidth(600)
        self.setMinimumHeight(400)
        
        self.setup_ui()
        self.load_data()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Create tab widget
        tabs = QTabWidget()
        
        # Tab 1: AI Target Settings
        target_tab = QWidget()
        target_layout = QVBoxLayout(target_tab)
        
        # Explanation
        target_info = QLabel(
            "🎯 AI Target Percentage\n\n"
            "This controls how fast the AI should be compared to your best lap.\n"
            "• 100% = AI matches your best lap exactly\n"
            "• 95% = AI is 5% SLOWER than you (easier race)\n"
            "• 105% = AI is 5% FASTER than you (harder race)\n\n"
            "The tool will automatically adjust AI ratios to hit this target."
        )
        target_info.setStyleSheet("color: #FFA500; background-color: #2b2b2b; padding: 10px; border-radius: 5px;")
        target_info.setWordWrap(True)
        target_layout.addWidget(target_info)
        
        target_layout.addSpacing(10)
        
        # Target percentage slider
        target_percent_layout = QHBoxLayout()
        target_percent_layout.addWidget(QLabel("AI Target Percentage:"))
        
        self.target_percent_spin = QSpinBox()
        self.target_percent_spin.setRange(80, 120)
        self.target_percent_spin.setValue(100)
        self.target_percent_spin.setSuffix("%")
        self.target_percent_spin.setToolTip("100% = AI matches your time, lower = easier, higher = harder")
        target_percent_layout.addWidget(self.target_percent_spin)
        
        self.target_percent_slider = QSlider(Qt.Horizontal)
        self.target_percent_slider.setRange(80, 120)
        self.target_percent_slider.setValue(100)
        self.target_percent_slider.setTickPosition(QSlider.TicksBelow)
        self.target_percent_slider.setTickInterval(5)
        self.target_percent_slider.valueChanged.connect(self.on_target_percent_changed)
        self.target_percent_spin.valueChanged.connect(self.on_target_percent_spin_changed)
        target_percent_layout.addWidget(self.target_percent_slider)
        
        target_layout.addLayout(target_percent_layout)
        
        # Target description
        self.target_description = QLabel("Current: AI will match your best lap time")
        self.target_description.setStyleSheet("color: #4CAF50; font-weight: bold;")
        target_layout.addWidget(self.target_description)
        
        target_layout.addSpacing(20)
        
        # Apply button
        apply_target_btn = QPushButton("Apply Target Percentage to Next Calculation")
        apply_target_btn.setStyleSheet("background-color: #FF9800;")
        apply_target_btn.clicked.connect(self.apply_target_percentage)
        target_layout.addWidget(apply_target_btn)
        
        target_layout.addStretch()
        tabs.addTab(target_tab, "🎯 AI Target")
        
        # Tab 2: Data Management
        data_tab = QWidget()
        data_layout = QVBoxLayout(data_tab)
        
        # Data points list
        data_layout.addWidget(QLabel("📊 Data Points in Database:"))
        
        self.data_table = QTableWidget()
        self.data_table.setColumnCount(5)
        self.data_table.setHorizontalHeaderLabels(["Track", "Vehicle", "Ratio", "Lap Time", "Session"])
        self.data_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.data_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.data_table.setAlternatingRowColors(True)
        data_layout.addWidget(self.data_table)
        
        # Data management buttons
        data_btn_layout = QHBoxLayout()
        
        refresh_btn = QPushButton("Refresh List")
        refresh_btn.clicked.connect(self.load_data)
        data_btn_layout.addWidget(refresh_btn)
        
        delete_selected_btn = QPushButton("Delete Selected")
        delete_selected_btn.setStyleSheet("background-color: #f44336;")
        delete_selected_btn.clicked.connect(self.delete_selected_points)
        data_btn_layout.addWidget(delete_selected_btn)
        
        delete_all_btn = QPushButton("Delete All for Track")
        delete_all_btn.setStyleSheet("background-color: #f44336;")
        delete_all_btn.clicked.connect(self.delete_all_for_track)
        data_btn_layout.addWidget(delete_all_btn)
        
        data_btn_layout.addStretch()
        data_layout.addLayout(data_btn_layout)
        
        tabs.addTab(data_tab, "🗑️ Data Management")
        
        # Tab 3: Logging & Settings
        settings_tab = QWidget()
        settings_layout = QVBoxLayout(settings_tab)
        
        # Logging options
        log_group = QGroupBox("📝 Logging Options")
        log_layout = QVBoxLayout(log_group)
        
        self.show_log_checkbox = QCheckBox("Show Log Window on Startup")
        self.show_log_checkbox.setChecked(False)
        log_layout.addWidget(self.show_log_checkbox)
        
        self.silent_mode_checkbox = QCheckBox("Silent Mode (suppress popup notifications)")
        if self.parent and hasattr(self.parent, 'autopilot_silent'):
            self.silent_mode_checkbox.setChecked(self.parent.autopilot_silent)
        self.silent_mode_checkbox.toggled.connect(self.on_silent_mode_toggled)
        log_layout.addWidget(self.silent_mode_checkbox)
        
        self.verbose_logging_checkbox = QCheckBox("Verbose Logging (more details)")
        log_layout.addWidget(self.verbose_logging_checkbox)
        
        settings_layout.addWidget(log_group)
        
        # Show log button
        show_log_btn = QPushButton("📋 Show Log Window")
        show_log_btn.setStyleSheet("background-color: #2196F3;")
        show_log_btn.clicked.connect(self.show_log_window)
        settings_layout.addWidget(show_log_btn)
        
        # Track changes list
        changes_group = QGroupBox("📋 Session Changes History")
        changes_layout = QVBoxLayout(changes_group)
        
        self.changes_list = QListWidget()
        changes_layout.addWidget(self.changes_list)
        
        clear_changes_btn = QPushButton("Clear History")
        clear_changes_btn.clicked.connect(self.changes_list.clear)
        changes_layout.addWidget(clear_changes_btn)
        
        settings_layout.addWidget(changes_group)
        
        settings_layout.addStretch()
        tabs.addTab(settings_tab, "⚙️ Settings & Logs")
        
        layout.addWidget(tabs)
        
        # Dialog buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Close)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
        self.setStyleSheet("""
            QDialog {
                background-color: #1e1e1e;
            }
            QTabWidget::pane {
                background-color: #2b2b2b;
                border: 1px solid #555;
            }
            QTabBar::tab {
                background-color: #3c3c3c;
                color: white;
                padding: 8px 12px;
                margin-right: 2px;
            }
            QTabBar::tab:selected {
                background-color: #4CAF50;
            }
            QTableWidget {
                background-color: #2b2b2b;
                color: white;
                alternate-background-color: #3c3c3c;
                gridline-color: #555;
            }
            QHeaderView::section {
                background-color: #3c3c3c;
                color: white;
                padding: 4px;
            }
            QListWidget {
                background-color: #2b2b2b;
                color: white;
            }
        """)
    
    def on_target_percent_changed(self, value):
        """Handle target percentage slider change"""
        self.target_percent_spin.blockSignals(True)
        self.target_percent_spin.setValue(value)
        self.target_percent_spin.blockSignals(False)
        self.update_target_description(value)
    
    def on_target_percent_spin_changed(self, value):
        """Handle target percentage spinbox change"""
        self.target_percent_slider.blockSignals(True)
        self.target_percent_slider.setValue(value)
        self.target_percent_slider.blockSignals(False)
        self.update_target_description(value)
    
    def update_target_description(self, percent):
        """Update the target description text"""
        if percent == 100:
            desc = "AI will match your best lap time exactly"
        elif percent < 100:
            diff = 100 - percent
            desc = f"AI will be {diff}% SLOWER than you (easier race)"
        else:
            diff = percent - 100
            desc = f"AI will be {diff}% FASTER than you (harder race)"
        self.target_description.setText(f"Current: {desc}")
    
    def apply_target_percentage(self):
        """Apply the target percentage to the parent"""
        percent = self.target_percent_spin.value() / 100.0
        if self.parent:
            self.parent.target_percentage = percent
            self.parent.statusBar().showMessage(f"AI Target set to {self.target_percent_spin.value()}%", 3000)
            # Add to changes list
            self.add_change_entry("Settings", f"AI Target Percentage set to {self.target_percent_spin.value()}%")
    
    def load_data(self):
        """Load data points from database into table"""
        if not self.db:
            return
        
        try:
            import sqlite3
            conn = sqlite3.connect(self.db.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT track, vehicle, ratio, lap_time, session_type 
                FROM data_points 
                ORDER BY track, session_type, ratio
            """)
            
            rows = cursor.fetchall()
            conn.close()
            
            self.data_table.setRowCount(len(rows))
            for i, row in enumerate(rows):
                for j, value in enumerate(row):
                    item = QTableWidgetItem(str(value))
                    self.data_table.setItem(i, j, item)
            
            # Color rows by session type
            for i, row in enumerate(rows):
                session_type = row[4]
                if session_type == 'qual':
                    color = QColor(58, 58, 0)  # dark yellow
                elif session_type == 'race':
                    color = QColor(58, 26, 0)  # dark orange
                else:
                    color = QColor(42, 0, 58)  # dark purple
                
                for j in range(5):
                    item = self.data_table.item(i, j)
                    if item:
                        item.setBackground(color)
            
            self.data_table.resizeRowsToContents()
            
        except Exception as e:
            print(f"Error loading data: {e}")
    
    def delete_selected_points(self):
        """Delete selected data points from database"""
        selected_rows = set()
        for item in self.data_table.selectedItems():
            selected_rows.add(item.row())
        
        if not selected_rows:
            QMessageBox.warning(self, "No Selection", "Please select data points to delete.")
            return
        
        reply = QMessageBox.question(
            self, "Confirm Delete",
            f"Delete {len(selected_rows)} data point(s)?\nThis cannot be undone.",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
        
        try:
            import sqlite3
            conn = sqlite3.connect(self.db.db_path)
            cursor = conn.cursor()
            
            deleted = 0
            for row_idx in sorted(selected_rows, reverse=True):
                track = self.data_table.item(row_idx, 0).text()
                vehicle = self.data_table.item(row_idx, 1).text()
                ratio = float(self.data_table.item(row_idx, 2).text())
                lap_time = float(self.data_table.item(row_idx, 3).text())
                session_type = self.data_table.item(row_idx, 4).text()
                
                cursor.execute("""
                    DELETE FROM data_points 
                    WHERE track = ? AND vehicle = ? AND ratio = ? 
                    AND lap_time = ? AND session_type = ?
                """, (track, vehicle, ratio, lap_time, session_type))
                deleted += cursor.rowcount
            
            conn.commit()
            conn.close()
            
            self.add_change_entry("Data", f"Deleted {deleted} data point(s)")
            self.load_data()  # Refresh
            
            if self.parent:
                self.parent.load_data()
                self.parent.update_display()
            
            QMessageBox.information(self, "Success", f"Deleted {deleted} data point(s).")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to delete: {e}")
    
    def delete_all_for_track(self):
        """Delete all data points for a selected track"""
        selected_rows = self.data_table.selectedItems()
        if not selected_rows:
            QMessageBox.warning(self, "No Selection", "Please select a data point to identify the track.")
            return
        
        track_name = self.data_table.item(selected_rows[0].row(), 0).text()
        
        reply = QMessageBox.question(
            self, "Confirm Delete",
            f"Delete ALL data points for track '{track_name}'?\nThis cannot be undone.",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
        
        try:
            import sqlite3
            conn = sqlite3.connect(self.db.db_path)
            cursor = conn.cursor()
            
            cursor.execute("DELETE FROM data_points WHERE track = ?", (track_name,))
            deleted = cursor.rowcount
            
            conn.commit()
            conn.close()
            
            self.add_change_entry("Data", f"Deleted all {deleted} data point(s) for track '{track_name}'")
            self.load_data()  # Refresh
            
            if self.parent:
                self.parent.load_data()
                self.parent.update_display()
            
            QMessageBox.information(self, "Success", f"Deleted {deleted} data point(s) for '{track_name}'.")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to delete: {e}")
    
    def on_silent_mode_toggled(self, checked):
        """Handle silent mode toggle"""
        if self.parent:
            self.parent.autopilot_silent = checked
            if hasattr(self.parent, 'autopilot_manager'):
                self.parent.autopilot_manager.set_silent(checked)
            self.add_change_entry("Settings", f"Silent Mode {'ON' if checked else 'OFF'}")
    
    def show_log_window(self):
        """Show the log window"""
        if self.log_window:
            self.log_window.show()
            self.log_window.raise_()
    
    def add_change_entry(self, category, message):
        """Add an entry to the changes history list"""
        from datetime import datetime
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.changes_list.addItem(f"[{timestamp}] [{category}] {message}")
        self.changes_list.scrollToBottom()


def create_control_panel(parent=None):
    """Create the left control panel with all widgets"""
    panel = QWidget(parent)
    panel.setMaximumWidth(400)  # Limit width to 1/3 of typical window
    panel.setMinimumWidth(250)
    layout = QVBoxLayout(panel)
    layout.setSpacing(10)
    
    # Instructions
    info_label = QLabel("Select vehicles to display data points.\n"
                       "Ctrl+Click = multi-select | Click = single")
    info_label.setStyleSheet("color: #888; font-size: 10px;")
    info_label.setWordWrap(True)
    layout.addWidget(info_label)
    
    # Track selection - now single track with multi-select button
    track_group = QGroupBox("Track")
    track_layout = QVBoxLayout(track_group)
    
    # Current track display
    current_track_layout = QHBoxLayout()
    current_track_label = QLabel("Current:")
    current_track_label.setStyleSheet("color: #FFA500; font-weight: bold;")
    current_track_layout.addWidget(current_track_label)
    
    current_track_display = QLabel("-")
    current_track_display.setStyleSheet("color: #4CAF50; font-family: monospace; font-weight: bold;")
    current_track_display.setWordWrap(True)
    current_track_layout.addWidget(current_track_display, 1)
    track_layout.addLayout(current_track_layout)
    
    # Multi-select button
    multi_track_btn = QPushButton("📋 Select Multiple Tracks...")
    multi_track_btn.setStyleSheet("""
        QPushButton {
            background-color: #2196F3;
            color: white;
            padding: 6px;
            font-size: 11px;
        }
        QPushButton:hover {
            background-color: #1976D2;
        }
    """)
    multi_track_btn.setToolTip("Open dialog to select multiple tracks for data comparison")
    track_layout.addWidget(multi_track_btn)
    
    # Hidden track list for internal use (kept for compatibility but not shown)
    track_list = QListWidget()
    track_list.setVisible(False)
    
    layout.addWidget(track_group)
    
    # Vehicle selection
    vehicle_group = QGroupBox("Vehicles")
    vehicle_layout = QVBoxLayout(vehicle_group)
    vehicle_list = QListWidget()
    vehicle_list.setSelectionMode(QAbstractItemView.ExtendedSelection)
    vehicle_layout.addWidget(vehicle_list)
    
    vehicle_btn_layout = QHBoxLayout()
    select_all_vehicles = QPushButton("Select All")
    clear_vehicles = QPushButton("Clear")
    vehicle_btn_layout.addWidget(select_all_vehicles)
    vehicle_btn_layout.addWidget(clear_vehicles)
    vehicle_layout.addLayout(vehicle_btn_layout)
    layout.addWidget(vehicle_group)
    
    # Data type selector
    type_group = QGroupBox("Data Types")
    type_layout = QHBoxLayout(type_group)
    type_layout.setSpacing(8)
    
    qual_btn = QPushButton("Quali")
    qual_btn.setCheckable(True)
    qual_btn.setChecked(True)
    qual_btn.setStyleSheet("""
        QPushButton {
            background-color: #4CAF50;
            color: white;
            padding: 4px 8px;
            font-size: 11px;
        }
        QPushButton:checked {
            background-color: #FFFF00;
            color: black;
            font-weight: bold;
        }
    """)
    type_layout.addWidget(qual_btn)
    
    race_btn = QPushButton("Race")
    race_btn.setCheckable(True)
    race_btn.setChecked(True)
    race_btn.setStyleSheet("""
        QPushButton {
            background-color: #4CAF50;
            color: white;
            padding: 4px 8px;
            font-size: 11px;
        }
        QPushButton:checked {
            background-color: #FF6600;
            color: white;
            font-weight: bold;
        }
    """)
    type_layout.addWidget(race_btn)
    
    unkn_btn = QPushButton("Unknw")
    unkn_btn.setCheckable(True)
    unkn_btn.setChecked(True)
    unkn_btn.setStyleSheet("""
        QPushButton {
            background-color: #4CAF50;
            color: white;
            padding: 4px 8px;
            font-size: 11px;
        }
        QPushButton:checked {
            background-color: #FF00FF;
            color: white;
            font-weight: bold;
        }
    """)
    type_layout.addWidget(unkn_btn)
    
    type_layout.addStretch()
    layout.addWidget(type_group)
    
    # Formula parameters - now with curve selector
    param_group = QGroupBox("Manual Curve Parameters: T = a / R + b")
    param_layout = QVBoxLayout(param_group)
    
    # Curve selector (Quali or Race)
    curve_selector_layout = QHBoxLayout()
    curve_selector_label = QLabel("Edit curve:")
    curve_selector_label.setStyleSheet("color: #FFA500; font-weight: bold;")
    curve_selector_layout.addWidget(curve_selector_label)
    
    curve_selector = QComboBox()
    curve_selector.addItem("🏁 Qualifying (Yellow)", "qual")
    curve_selector.addItem("🏎️ Race (Orange)", "race")
    curve_selector.setStyleSheet("""
        QComboBox {
            background-color: #3c3c3c;
            color: white;
            border: 1px solid #4CAF50;
            border-radius: 3px;
            padding: 4px;
        }
        QComboBox::drop-down {
            border: none;
        }
        QComboBox::down-arrow {
            image: none;
            border-left: 5px solid transparent;
            border-right: 5px solid transparent;
            border-top: 5px solid white;
            margin-right: 5px;
        }
    """)
    curve_selector_layout.addWidget(curve_selector)
    curve_selector_layout.addStretch()
    param_layout.addLayout(curve_selector_layout)
    
    # Current formula display
    current_formula_label = QLabel("Current formula: T = -- / R + --")
    current_formula_label.setStyleSheet("color: #4CAF50; font-family: monospace; font-size: 11px;")
    current_formula_label.setWordWrap(True)
    param_layout.addWidget(current_formula_label)
    
    param_layout.addSpacing(5)
    
    # a parameter
    a_layout = QHBoxLayout()
    a_label = QLabel("Height (a):")
    a_label.setToolTip("Controls how steep the curve is. Higher = more sensitive to ratio changes")
    a_layout.addWidget(a_label)
    a_spin = QDoubleSpinBox()
    a_spin.setRange(0.01, 500.0)
    a_spin.setDecimals(3)
    a_spin.setSingleStep(1.0)
    a_spin.setValue(30.0)
    a_layout.addWidget(a_spin)
    param_layout.addLayout(a_layout)
    
    # b parameter
    b_layout = QHBoxLayout()
    b_label = QLabel("Base (b):")
    b_label.setToolTip("Minimum lap time in seconds. The curve approaches this as ratio increases")
    b_layout.addWidget(b_label)
    b_spin = QDoubleSpinBox()
    b_spin.setRange(0.01, 200.0)
    b_spin.setDecimals(3)
    b_spin.setSingleStep(0.5)
    b_spin.setValue(70.0)
    b_layout.addWidget(b_spin)
    param_layout.addLayout(b_layout)
    
    # Apply button for manual edits
    apply_btn = QPushButton("Apply to Selected Curve")
    apply_btn.setStyleSheet("background-color: #2196F3;")
    param_layout.addWidget(apply_btn)
    
    # Derived values
    info_layout = QVBoxLayout()
    k_label = QLabel("Steepness k = a/(a+b) = ---")
    k_label.setToolTip("k close to 0 = shallow curve, k close to 1 = steep curve")
    k_label.setStyleSheet("color: #888;")
    info_layout.addWidget(k_label)
    
    m_label = QLabel("Time at R=1.0 = a+b = ---")
    m_label.setStyleSheet("color: #888;")
    info_layout.addWidget(m_label)
    
    param_layout.addLayout(info_layout)
    layout.addWidget(param_group)
    
    # Autopilot group (simplified - silent mode moved to advanced)
    autopilot_group = QGroupBox("[AUTO] Autopilot")
    autopilot_layout = QVBoxLayout(autopilot_group)
    
    # Autopilot enable/disable
    autopilot_enable_btn = QPushButton("Autopilot is OFF")
    autopilot_enable_btn.setCheckable(True)
    autopilot_enable_btn.setStyleSheet("""
        QPushButton {
            background-color: #555;
            color: white;
        }
        QPushButton:checked {
            background-color: #FF9800;
            color: white;
            font-weight: bold;
        }
    """)
    autopilot_layout.addWidget(autopilot_enable_btn)
    
    # Autopilot info label
    autopilot_info = QLabel("When enabled, automatically adjusts AIW ratios\nbased on detected race data.")
    autopilot_info.setStyleSheet("color: #888; font-size: 9px;")
    autopilot_info.setWordWrap(True)
    autopilot_layout.addWidget(autopilot_info)
    
    autopilot_status = QLabel("Status: Disabled")
    autopilot_status.setStyleSheet("color: #FF9800; font-size: 10px;")
    autopilot_layout.addWidget(autopilot_status)
    
    layout.addWidget(autopilot_group)
    
    # Buttons
    btn_layout = QVBoxLayout()
    
    fit_btn = QPushButton("Auto-Fit to Selected Data")
    fit_btn.setStyleSheet("background-color: #4CAF50;")
    btn_layout.addWidget(fit_btn)
    
    reset_btn = QPushButton("Reset View")
    btn_layout.addWidget(reset_btn)
    
    # Advanced button (above exit)
    advanced_btn = QPushButton("⚙️ Advanced Settings")
    advanced_btn.setStyleSheet("background-color: #9C27B0;")
    btn_layout.addWidget(advanced_btn)
    
    exit_btn = QPushButton("Exit")
    exit_btn.setStyleSheet("background-color: #f44336;")
    btn_layout.addWidget(exit_btn)
    
    layout.addLayout(btn_layout)
    layout.addStretch()
    
    # Stats label
    stats_label = QLabel("")
    stats_label.setStyleSheet("color: #888; padding: 5px;")
    stats_label.setWordWrap(True)
    layout.addWidget(stats_label)
    
    return {
        'panel': panel,
        'track_list': track_list,  # Kept for compatibility but hidden
        'current_track_display': current_track_display,
        'multi_track_btn': multi_track_btn,
        'vehicle_list': vehicle_list,
        'qual_btn': qual_btn,
        'race_btn': race_btn,
        'unkn_btn': unkn_btn,
        'a_spin': a_spin,
        'b_spin': b_spin,
        'k_label': k_label,
        'm_label': m_label,
        'fit_btn': fit_btn,
        'reset_btn': reset_btn,
        'exit_btn': exit_btn,
        'stats_label': stats_label,
        'select_all_vehicles': select_all_vehicles,
        'clear_vehicles': clear_vehicles,
        'autopilot_enable_btn': autopilot_enable_btn,
        'autopilot_status': autopilot_status,
        'curve_selector': curve_selector,
        'current_formula_label': current_formula_label,
        'apply_btn': apply_btn,
        'advanced_btn': advanced_btn  # Add advanced button reference
    }


def create_plot_widget(parent=None):
    """Create the plot widget using pyqtgraph for lightweight rendering"""
    widget = QWidget(parent)
    layout = QVBoxLayout(widget)
    layout.setContentsMargins(0, 0, 0, 0)
    
    # Create GraphicsLayoutWidget for plotting
    plot_widget = pg.GraphicsLayoutWidget()
    plot_widget.setBackground('#2b2b2b')
    
    # Create plot item
    plot = plot_widget.addPlot()
    plot.setLabel('bottom', 'Ratio (R)', color='white', size='11pt')
    plot.setLabel('left', 'Lap Time (seconds)', color='white', size='11pt')
    plot.setTitle('Hyperbolic Curve: T = a / R + b', color='#FFA500', size='12pt')
    plot.showGrid(x=True, y=True, alpha=0.3)
    plot.setXRange(0.4, 2.0)
    plot.setYRange(50, 200)
    
    # Style the axes
    plot.getAxis('bottom').setPen('white')
    plot.getAxis('bottom').setTextPen('white')
    plot.getAxis('left').setPen('white')
    plot.getAxis('left').setTextPen('white')
    
    # Store plot reference and curve/point items for updating
    plot_data = {
        'widget': plot_widget,
        'plot': plot,
        'curve_line': None,
        'quali_scatter': None,
        'race_scatter': None,
        'unknown_scatter': None,
        'legend': None,
        'parent_widget': widget
    }
    
    layout.addWidget(plot_widget)
    
    return plot_data


def update_plot(plot_data, a: float, b: float, points_data: dict):
    """
    Update the plot with new curve and points
    This is kept for compatibility with existing code
    """
    plot = plot_data['plot']
    
    # Generate curve points
    ratios = np.linspace(0.4, 2.0, 200)
    times = a / ratios + b
    
    # Update or create curve line
    if plot_data['curve_line'] is None:
        plot_data['curve_line'] = plot.plot(ratios, times, pen=pg.mkPen(color='#00FFFF', width=2.5))
    else:
        plot_data['curve_line'].setData(ratios, times)
    
    # Get point data
    quali_points = points_data.get('quali', [])
    race_points = points_data.get('race', [])
    unknown_points = points_data.get('unknown', [])
    
    # Update quali points (yellow circles)
    if quali_points:
        r = [p[0] for p in quali_points]
        t = [p[1] for p in quali_points]
        if plot_data['quali_scatter'] is None:
            plot_data['quali_scatter'] = pg.ScatterPlotItem(
                r, t, brush=pg.mkBrush('#FFFF00'), size=6,
                symbol='o', pen=None
            )
            plot.addItem(plot_data['quali_scatter'])
        else:
            plot_data['quali_scatter'].setData(r, t)
    elif plot_data['quali_scatter'] is not None:
        plot.removeItem(plot_data['quali_scatter'])
        plot_data['quali_scatter'] = None
    
    # Update race points (orange squares)
    if race_points:
        r = [p[0] for p in race_points]
        t = [p[1] for p in race_points]
        if plot_data['race_scatter'] is None:
            plot_data['race_scatter'] = pg.ScatterPlotItem(
                r, t, brush=pg.mkBrush('#FF6600'), size=6,
                symbol='s', pen=None
            )
            plot.addItem(plot_data['race_scatter'])
        else:
            plot_data['race_scatter'].setData(r, t)
    elif plot_data['race_scatter'] is not None:
        plot.removeItem(plot_data['race_scatter'])
        plot_data['race_scatter'] = None
    
    # Update unknown points (magenta triangles)
    if unknown_points:
        r = [p[0] for p in unknown_points]
        t = [p[1] for p in unknown_points]
        if plot_data['unknown_scatter'] is None:
            plot_data['unknown_scatter'] = pg.ScatterPlotItem(
                r, t, brush=pg.mkBrush('#FF00FF'), size=6,
                symbol='t', pen=None
            )
            plot.addItem(plot_data['unknown_scatter'])
        else:
            plot_data['unknown_scatter'].setData(r, t)
    elif plot_data['unknown_scatter'] is not None:
        plot.removeItem(plot_data['unknown_scatter'])
        plot_data['unknown_scatter'] = None
    
    # Update legend - remove old and create new
    if plot_data['legend'] is not None:
        plot.scene().removeItem(plot_data['legend'])
        plot_data['legend'] = None
    
    # Create new legend
    plot_data['legend'] = plot.addLegend()
    
    # Add items to legend
    if plot_data['curve_line']:
        plot_data['legend'].addItem(plot_data['curve_line'], f'T = {a:.3f}/R + {b:.3f}')
    if quali_points:
        plot_data['legend'].addItem(plot_data['quali_scatter'], f'Qualifying ({len(quali_points)})')
    if race_points:
        plot_data['legend'].addItem(plot_data['race_scatter'], f'Race ({len(race_points)})')
    if unknown_points:
        plot_data['legend'].addItem(plot_data['unknown_scatter'], f'Unknown ({len(unknown_points)})')


def reset_plot_view(plot_data):
    """Reset the plot to default view"""
    plot = plot_data['plot']
    plot.setXRange(0.4, 2.0)
    plot.setYRange(50, 200)


def setup_dark_theme(app):
    """Apply dark theme styling to the application"""
    app.setStyle('Fusion')
    app.setStyleSheet("""
        QMainWindow, QWidget {
            background-color: #1e1e1e;
        }
        QLabel {
            color: white;
        }
        QGroupBox {
            color: #4CAF50;
            border: 2px solid #555;
            border-radius: 5px;
            margin-top: 8px;
            padding-top: 8px;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 5px 0 5px;
        }
        QListWidget {
            background-color: #2b2b2b;
            color: white;
            border: 1px solid #4CAF50;
            border-radius: 3px;
            outline: none;
        }
        QListWidget::item:selected {
            background-color: #4CAF50;
            color: white;
        }
        QListWidget::item:hover {
            background-color: #3c3c3c;
        }
        QDoubleSpinBox {
            background-color: #3c3c3c;
            color: white;
            border: 1px solid #4CAF50;
            border-radius: 3px;
            padding: 4px;
        }
        QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {
            background-color: #4CAF50;
            width: 16px;
        }
        QPushButton {
            background-color: #4CAF50;
            color: white;
            border: none;
            border-radius: 4px;
            padding: 8px;
            font-weight: bold;
        }
        QPushButton:hover {
            background-color: #45a049;
        }
        QStatusBar {
            color: #888;
        }
    """)


def show_error_dialog(parent, title: str, message: str):
    """Show an error message dialog"""
    msg = QMessageBox(parent)
    msg.setWindowTitle(title)
    msg.setIcon(QMessageBox.Critical)
    msg.setText(message)
    msg.exec_()


def show_info_dialog(parent, title: str, message: str):
    """Show an information message dialog"""
    msg = QMessageBox(parent)
    msg.setWindowTitle(title)
    msg.setIcon(QMessageBox.Information)
    msg.setText(message)
    msg.exec_()


def show_warning_dialog(parent, title: str, message: str):
    """Show a warning message dialog"""
    msg = QMessageBox(parent)
    msg.setWindowTitle(title)
    msg.setIcon(QMessageBox.Warning)
    msg.setText(message)
    msg.exec_()
