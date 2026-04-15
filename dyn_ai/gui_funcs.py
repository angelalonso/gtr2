#!/usr/bin/env python3
"""
GUI module for curve viewer
Provides reusable GUI components and dialogs using pyqtgraph for lightweight plotting
"""

import numpy as np
import shutil
from pathlib import Path
from datetime import datetime
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QListWidget, 
    QDoubleSpinBox, QPushButton, QGroupBox, QSplitter, 
    QMessageBox, QAbstractItemView, QComboBox, QDialog,
    QDialogButtonBox, QListWidgetItem, QSlider, QSpinBox,
    QCheckBox, QTabWidget, QTableWidget, QTableWidgetItem,
    QHeaderView, QScrollArea, QFileDialog, QSizePolicy, QRadioButton
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
        
        info_label = QLabel("Select tracks to display data from.\n"
                           "Ctrl+Click = multi-select | Shift+Click = range")
        info_label.setStyleSheet("color: #888; font-size: 10px;")
        info_label.setWordWrap(True)
        layout.addWidget(info_label)
        
        self.track_list = QListWidget()
        self.track_list.setSelectionMode(QAbstractItemView.ExtendedSelection)
        
        for i, track in enumerate(self.all_tracks):
            item = QListWidgetItem(track)
            self.track_list.addItem(item)
            if track == self.current_track:
                item.setSelected(True)
                self.track_list.setCurrentItem(item)
        
        layout.addWidget(self.track_list)
        
        btn_layout = QHBoxLayout()
        select_all_btn = QPushButton("Select All")
        select_all_btn.clicked.connect(self.track_list.selectAll)
        btn_layout.addWidget(select_all_btn)
        
        clear_btn = QPushButton("Clear All")
        clear_btn.clicked.connect(self.track_list.clearSelection)
        btn_layout.addWidget(clear_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        
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
        self.setGeometry(200, 200, 750, 650)
        self.setMinimumWidth(650)
        self.setMinimumHeight(550)
        
        # AI Target settings
        self.target_mode = "percentage"  # percentage, faster_than_best, slower_than_worst
        self.target_percentage = 50
        self.target_offset_seconds = 0.0
        self.ai_error_margin = 0.0
        
        self.setup_ui()
        self.load_data()
        self.refresh_backup_list()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        tabs = QTabWidget()
        
        # ========== TAB 1: AI TARGET SETTINGS ==========
        target_tab = QWidget()
        target_layout = QVBoxLayout(target_tab)
        
        target_info = QLabel(
            "AI Target Positioning\n\n"
            "This controls where your lap time should fall within the AI's lap time range.\n\n"
            "The AI's best and worst lap times create a range. You choose where you want to be.\n"
            "Example: If AI runs 90s to 95s, 50% = 92.5s target."
        )
        target_info.setStyleSheet("color: #FFA500; background-color: #2b2b2b; padding: 10px; border-radius: 5px;")
        target_info.setWordWrap(True)
        target_layout.addWidget(target_info)
        
        target_layout.addSpacing(10)
        
        # Mode selection
        mode_group = QGroupBox("Target Mode")
        mode_layout = QVBoxLayout(mode_group)
        
        self.percentage_radio = QRadioButton("Percentage within AI range")
        self.percentage_radio.setChecked(True)
        self.percentage_radio.toggled.connect(self.on_target_mode_changed)
        mode_layout.addWidget(self.percentage_radio)
        
        pct_desc = QLabel("  0% = match fastest AI, 50% = middle, 100% = match slowest AI")
        pct_desc.setStyleSheet("color: #888; font-size: 10px; margin-left: 20px;")
        pct_desc.setWordWrap(True)
        mode_layout.addWidget(pct_desc)
        
        mode_layout.addSpacing(5)
        
        self.faster_radio = QRadioButton("Fixed seconds from fastest AI")
        self.faster_radio.toggled.connect(self.on_target_mode_changed)
        mode_layout.addWidget(self.faster_radio)
        
        self.slower_radio = QRadioButton("Fixed seconds from slowest AI")
        self.slower_radio.toggled.connect(self.on_target_mode_changed)
        mode_layout.addWidget(self.slower_radio)
        
        target_layout.addWidget(mode_group)
        
        target_layout.addSpacing(10)
        
        # Percentage controls
        percent_group = QGroupBox("Percentage Setting")
        percent_layout = QVBoxLayout(percent_group)
        
        percent_slider_layout = QHBoxLayout()
        percent_slider_layout.addWidget(QLabel("Position in AI range:"))
        
        self.target_percent_slider = QSlider(Qt.Horizontal)
        self.target_percent_slider.setRange(0, 100)
        self.target_percent_slider.setValue(50)
        self.target_percent_slider.setTickPosition(QSlider.TicksBelow)
        self.target_percent_slider.setTickInterval(10)
        self.target_percent_slider.valueChanged.connect(self.on_percent_changed)
        percent_slider_layout.addWidget(self.target_percent_slider)
        
        self.target_percent_spin = QSpinBox()
        self.target_percent_spin.setRange(0, 100)
        self.target_percent_spin.setValue(50)
        self.target_percent_spin.setSuffix("%")
        self.target_percent_spin.valueChanged.connect(self.on_percent_spin_changed)
        percent_slider_layout.addWidget(self.target_percent_spin)
        
        percent_layout.addLayout(percent_slider_layout)
        
        self.percent_description = QLabel("You will be exactly in the MIDDLE of the AI range")
        self.percent_description.setStyleSheet("color: #4CAF50; font-weight: bold;")
        percent_layout.addWidget(self.percent_description)
        
        target_layout.addWidget(percent_group)
        
        # Absolute offset controls
        absolute_group = QGroupBox("Fixed Offset Setting")
        absolute_layout = QVBoxLayout(absolute_group)
        
        offset_layout = QHBoxLayout()
        offset_layout.addWidget(QLabel("Offset:"))
        
        self.target_offset_spin = QDoubleSpinBox()
        self.target_offset_spin.setRange(-10.0, 10.0)
        self.target_offset_spin.setDecimals(2)
        self.target_offset_spin.setSingleStep(0.1)
        self.target_offset_spin.setValue(0.0)
        self.target_offset_spin.setSuffix(" seconds")
        self.target_offset_spin.valueChanged.connect(self.on_offset_changed)
        offset_layout.addWidget(self.target_offset_spin)
        
        offset_layout.addStretch()
        absolute_layout.addLayout(offset_layout)
        
        self.offset_description = QLabel("You will be 0.00 seconds from the reference AI time")
        self.offset_description.setStyleSheet("color: #4CAF50; font-weight: bold;")
        absolute_layout.addWidget(self.offset_description)
        
        target_layout.addWidget(absolute_group)
        
        target_layout.addSpacing(10)
        
        # Error margin (makes AI slower)
        error_group = QGroupBox("AI Error Margin (Makes AI Slower)")
        error_layout = QVBoxLayout(error_group)
        
        error_info = QLabel("Adds extra time to ALL AI lap times. This makes the AI slower overall.")
        error_info.setStyleSheet("color: #888; font-size: 10px;")
        error_info.setWordWrap(True)
        error_layout.addWidget(error_info)
        
        error_slider_layout = QHBoxLayout()
        error_slider_layout.addWidget(QLabel("Extra time:"))
        
        self.error_margin_slider = QSlider(Qt.Horizontal)
        self.error_margin_slider.setRange(0, 500)
        self.error_margin_slider.setValue(0)
        self.error_margin_slider.setTickPosition(QSlider.TicksBelow)
        self.error_margin_slider.setTickInterval(50)
        self.error_margin_slider.valueChanged.connect(self.on_error_margin_changed)
        error_slider_layout.addWidget(self.error_margin_slider)
        
        self.error_margin_spin = QDoubleSpinBox()
        self.error_margin_spin.setRange(0, 5.0)
        self.error_margin_spin.setDecimals(2)
        self.error_margin_spin.setSingleStep(0.1)
        self.error_margin_spin.setValue(0.0)
        self.error_margin_spin.setSuffix(" seconds")
        self.error_margin_spin.valueChanged.connect(self.on_error_margin_spin_changed)
        error_slider_layout.addWidget(self.error_margin_spin)
        
        error_layout.addLayout(error_slider_layout)
        
        target_layout.addWidget(error_group)
        
        target_layout.addSpacing(10)
        
        apply_target_btn = QPushButton("Apply Target Settings")
        apply_target_btn.setStyleSheet("background-color: #FF9800;")
        apply_target_btn.clicked.connect(self.apply_target_settings)
        target_layout.addWidget(apply_target_btn)
        
        target_layout.addStretch()
        tabs.addTab(target_tab, "AI Target")
        
        # ========== TAB 2: DATA MANAGEMENT ==========
        data_tab = QWidget()
        data_layout = QVBoxLayout(data_tab)
        
        data_layout.addWidget(QLabel("Data Points in Database:"))
        
        self.data_table = QTableWidget()
        self.data_table.setColumnCount(5)
        self.data_table.setHorizontalHeaderLabels(["Track", "Vehicle", "Ratio", "Lap Time", "Session"])
        self.data_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.data_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.data_table.setAlternatingRowColors(True)
        data_layout.addWidget(self.data_table)
        
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
        
        tabs.addTab(data_tab, "Data Management")
        
        # ========== TAB 3: BACKUP RESTORE ==========
        backup_tab = QWidget()
        backup_layout = QVBoxLayout(backup_tab)
        
        backup_info = QLabel(
            "AIW Backup Restore\n\n"
            "When Autopilot modifies an AIW file, it creates a backup first.\n"
            "Use this section to restore original AIW files.\n\n"
            "Note: Restoring will undo any Autopilot changes made to that track."
        )
        backup_info.setStyleSheet("color: #FFA500; background-color: #2b2b2b; padding: 10px; border-radius: 5px;")
        backup_info.setWordWrap(True)
        backup_layout.addWidget(backup_info)
        
        backup_layout.addSpacing(10)
        
        backup_layout.addWidget(QLabel("Available Backups:"))
        self.backup_list = QListWidget()
        self.backup_list.setSelectionMode(QAbstractItemView.ExtendedSelection)
        backup_layout.addWidget(self.backup_list)
        
        backup_btn_layout = QHBoxLayout()
        
        refresh_backups_btn = QPushButton("Refresh List")
        refresh_backups_btn.clicked.connect(self.refresh_backup_list)
        backup_btn_layout.addWidget(refresh_backups_btn)
        
        restore_selected_btn = QPushButton("Restore Selected")
        restore_selected_btn.setStyleSheet("background-color: #FF9800;")
        restore_selected_btn.clicked.connect(self.restore_selected_backups)
        backup_btn_layout.addWidget(restore_selected_btn)
        
        restore_all_btn = QPushButton("Restore All")
        restore_all_btn.setStyleSheet("background-color: #f44336;")
        restore_all_btn.clicked.connect(self.restore_all_backups)
        backup_btn_layout.addWidget(restore_all_btn)
        
        backup_btn_layout.addStretch()
        backup_layout.addLayout(backup_btn_layout)
        
        backup_layout.addStretch()
        tabs.addTab(backup_tab, "Backup Restore")
        
        # ========== TAB 4: SETTINGS & LOGS ==========
        settings_tab = QWidget()
        settings_layout = QVBoxLayout(settings_tab)
        
        log_group = QGroupBox("Logging Options")
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
        
        show_log_btn = QPushButton("Show Log Window")
        show_log_btn.setStyleSheet("background-color: #2196F3;")
        show_log_btn.clicked.connect(self.show_log_window)
        settings_layout.addWidget(show_log_btn)
        
        changes_group = QGroupBox("Session Changes History")
        changes_layout = QVBoxLayout(changes_group)
        
        self.changes_list = QListWidget()
        changes_layout.addWidget(self.changes_list)
        
        clear_changes_btn = QPushButton("Clear History")
        clear_changes_btn.clicked.connect(self.changes_list.clear)
        changes_layout.addWidget(clear_changes_btn)
        
        settings_layout.addWidget(changes_group)
        
        settings_layout.addStretch()
        tabs.addTab(settings_tab, "Settings & Logs")
        
        layout.addWidget(tabs)
        
        button_box = QDialogButtonBox(QDialogButtonBox.Close)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
        self.update_mode_visibility()
        
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
            QGroupBox {
                color: #4CAF50;
            }
            QRadioButton {
                color: white;
            }
        """)
    
    def on_target_mode_changed(self):
        if self.percentage_radio.isChecked():
            self.target_mode = "percentage"
        elif self.faster_radio.isChecked():
            self.target_mode = "faster_than_best"
        else:
            self.target_mode = "slower_than_worst"
        self.update_mode_visibility()
    
    def update_mode_visibility(self):
        for child in self.findChildren(QGroupBox):
            if "Percentage Setting" in child.title():
                child.setVisible(self.target_mode == "percentage")
            elif "Fixed Offset Setting" in child.title():
                child.setVisible(self.target_mode != "percentage")
        self.update_mode_description()
    
    def update_mode_description(self):
        if self.target_mode == "percentage":
            pct = self.target_percent_slider.value()
            if pct == 0:
                desc = "You will match the FASTEST AI lap time"
            elif pct == 100:
                desc = "You will match the SLOWEST AI lap time"
            elif pct == 50:
                desc = "You will be exactly in the MIDDLE of the AI range"
            else:
                desc = f"You will be {pct}% from fastest AI to slowest AI"
            self.percent_description.setText(desc)
        elif self.target_mode == "faster_than_best":
            offset = self.target_offset_spin.value()
            if offset == 0:
                desc = "You will match the fastest AI lap time"
            elif offset > 0:
                desc = f"You will be {offset:.2f} seconds SLOWER than the fastest AI"
            else:
                desc = f"You will be {abs(offset):.2f} seconds FASTER than the fastest AI"
            self.offset_description.setText(desc)
        else:
            offset = self.target_offset_spin.value()
            if offset == 0:
                desc = "You will match the slowest AI lap time"
            elif offset > 0:
                desc = f"You will be {offset:.2f} seconds FASTER than the slowest AI"
            else:
                desc = f"You will be {abs(offset):.2f} seconds SLOWER than the slowest AI"
            self.offset_description.setText(desc)
    
    def on_percent_changed(self, value):
        self.target_percent_spin.blockSignals(True)
        self.target_percent_spin.setValue(value)
        self.target_percent_spin.blockSignals(False)
        self.target_percentage = value
        self.update_mode_description()
    
    def on_percent_spin_changed(self, value):
        self.target_percent_slider.blockSignals(True)
        self.target_percent_slider.setValue(value)
        self.target_percent_slider.blockSignals(False)
        self.target_percentage = value
        self.update_mode_description()
    
    def on_offset_changed(self, value):
        self.target_offset_seconds = value
        self.update_mode_description()
    
    def on_error_margin_changed(self, value):
        seconds = value / 100.0
        self.error_margin_spin.blockSignals(True)
        self.error_margin_spin.setValue(seconds)
        self.error_margin_spin.blockSignals(False)
        self.ai_error_margin = seconds
    
    def on_error_margin_spin_changed(self, value):
        self.error_margin_slider.blockSignals(True)
        self.error_margin_slider.setValue(int(value * 100))
        self.error_margin_slider.blockSignals(False)
        self.ai_error_margin = value
    
    def calculate_target_time(self, best_ai_time, worst_ai_time):
        if best_ai_time <= 0 or worst_ai_time <= 0:
            return best_ai_time if best_ai_time > 0 else worst_ai_time
        
        ai_range = worst_ai_time - best_ai_time
        
        if self.target_mode == "percentage":
            pct = self.target_percentage / 100.0
            target = best_ai_time + (ai_range * pct)
        elif self.target_mode == "faster_than_best":
            target = best_ai_time + self.target_offset_seconds
        else:
            target = worst_ai_time - self.target_offset_seconds
        
        target = target + self.ai_error_margin
        target = max(best_ai_time, min(worst_ai_time + self.ai_error_margin, target))
        
        return target
    
    def apply_target_settings(self):
        settings = {
            "mode": self.target_mode,
            "percentage": self.target_percentage,
            "offset_seconds": self.target_offset_seconds,
            "error_margin": self.ai_error_margin
        }
        
        if self.parent:
            self.parent.ai_target_settings = settings
            self.parent.statusBar().showMessage(f"AI Target settings applied", 3000)
            
            if self.target_mode == "percentage":
                msg = f"AI Target: Position at {self.target_percentage}% within AI range"
            elif self.target_mode == "faster_than_best":
                offset = self.target_offset_seconds
                if offset == 0:
                    msg = "AI Target: Match fastest AI"
                elif offset > 0:
                    msg = f"AI Target: {offset:.2f}s slower than fastest AI"
                else:
                    msg = f"AI Target: {abs(offset):.2f}s faster than fastest AI"
            else:
                offset = self.target_offset_seconds
                if offset == 0:
                    msg = "AI Target: Match slowest AI"
                elif offset > 0:
                    msg = f"AI Target: {offset:.2f}s faster than slowest AI"
                else:
                    msg = f"AI Target: {abs(offset):.2f}s slower than slowest AI"
            
            if self.ai_error_margin > 0:
                msg += f" + {self.ai_error_margin:.2f}s error margin"
            
            self.add_change_entry("AI Target", msg)
        
        QMessageBox.information(self, "Settings Applied", 
            f"AI Target settings have been applied.\n\n{msg}\n\n"
            f"These settings will be used the next time Autopilot runs.")
    
    def load_data(self):
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
            
            for i, row in enumerate(rows):
                session_type = row[4]
                if session_type == 'qual':
                    color = QColor(58, 58, 0)
                elif session_type == 'race':
                    color = QColor(58, 26, 0)
                else:
                    color = QColor(42, 0, 58)
                
                for j in range(5):
                    item = self.data_table.item(i, j)
                    if item:
                        item.setBackground(color)
            
            self.data_table.resizeRowsToContents()
            
        except Exception as e:
            print(f"Error loading data: {e}")
    
    def delete_selected_points(self):
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
            self.load_data()
            
            if self.parent:
                self.parent.load_data()
                self.parent.update_display()
            
            QMessageBox.information(self, "Success", f"Deleted {deleted} data point(s).")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to delete: {e}")
    
    def delete_all_for_track(self):
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
            self.load_data()
            
            if self.parent:
                self.parent.load_data()
                self.parent.update_display()
            
            QMessageBox.information(self, "Success", f"Deleted {deleted} data point(s) for '{track_name}'.")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to delete: {e}")
    
    def on_silent_mode_toggled(self, checked):
        if self.parent:
            self.parent.autopilot_silent = checked
            if hasattr(self.parent, 'autopilot_manager'):
                self.parent.autopilot_manager.set_silent(checked)
            self.add_change_entry("Settings", f"Silent Mode {'ON' if checked else 'OFF'}")
    
    def show_log_window(self):
        if self.log_window:
            self.log_window.show()
            self.log_window.raise_()
    
    def add_change_entry(self, category, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.changes_list.addItem(f"[{timestamp}] [{category}] {message}")
        self.changes_list.scrollToBottom()
    
    def scan_aiw_backups(self):
        backups = []
        
        backup_dirs = []
        if self.parent and hasattr(self.parent, 'db'):
            backup_dirs.append(Path(self.parent.db.db_path).parent / "aiw_backups")
        backup_dirs.append(Path.cwd() / "aiw_backups")
        
        for backup_dir in backup_dirs:
            if not backup_dir.exists():
                continue
            
            for backup_file in backup_dir.glob("*_ORIGINAL.AIW"):
                original_name = backup_file.name.replace("_ORIGINAL.AIW", ".AIW")
                track_name = self._get_track_from_backup(backup_file, original_name)
                backups.append({
                    "track": track_name,
                    "original_file": original_name,
                    "backup_path": backup_file,
                    "backup_time": backup_file.stat().st_mtime if backup_file.exists() else 0
                })
            
            for backup_file in backup_dir.glob("*.bak"):
                backups.append({
                    "track": "Unknown",
                    "original_file": backup_file.name.replace(".bak", ""),
                    "backup_path": backup_file,
                    "backup_time": backup_file.stat().st_mtime if backup_file.exists() else 0
                })
        
        return sorted(backups, key=lambda x: x.get("track", ""))
    
    def _get_track_from_backup(self, backup_path, original_name):
        if self.parent and hasattr(self.parent, 'daemon') and self.parent.daemon:
            base_path = self.parent.daemon.base_path
            locations_dir = base_path / "GameData" / "Locations"
            
            if locations_dir.exists():
                for track_dir in locations_dir.iterdir():
                    if track_dir.is_dir():
                        aiw_path = track_dir / original_name
                        if aiw_path.exists():
                            return track_dir.name
        
        return original_name.replace(".AIW", "")
    
    def restore_aiw_backup(self, backup_info):
        try:
            backup_path = backup_info["backup_path"]
            original_name = backup_info["original_file"]
            
            restore_path = None
            
            if self.parent and hasattr(self.parent, 'daemon') and self.parent.daemon:
                base_path = self.parent.daemon.base_path
                locations_dir = base_path / "GameData" / "Locations"
                
                if locations_dir.exists():
                    for track_dir in locations_dir.iterdir():
                        if track_dir.is_dir():
                            aiw_path = track_dir / original_name
                            if aiw_path.exists():
                                restore_path = aiw_path
                                break
            
            if not restore_path:
                restore_path_str, _ = QFileDialog.getSaveFileName(
                    self, "Save Restored AIW As", 
                    str(backup_path.parent / original_name),
                    "AIW Files (*.AIW)"
                )
                if restore_path_str:
                    restore_path = Path(restore_path_str)
                else:
                    return False
            
            shutil.copy2(backup_path, restore_path)
            
            if self.parent and hasattr(self.parent, 'autopilot_manager'):
                self.parent.autopilot_manager.reload_formulas()
                self.parent._update_formulas_from_autopilot()
                self.parent.update_display()
            
            return True
            
        except Exception as e:
            print(f"Error restoring backup: {e}")
            return False
    
    def restore_all_aiw_backups(self):
        backups = self.scan_aiw_backups()
        if not backups:
            return 0
        
        restored = 0
        for backup in backups:
            if self.restore_aiw_backup(backup):
                restored += 1
        
        return restored
    
    def refresh_backup_list(self):
        self.backup_list.clear()
        backups = self.scan_aiw_backups()
        
        if not backups:
            self.backup_list.addItem("No backups found")
            return
        
        for backup in backups:
            time_str = datetime.fromtimestamp(backup["backup_time"]).strftime("%Y-%m-%d %H:%M:%S")
            item_text = f"{backup['track']} - {backup['original_file']} (backup: {time_str})"
            self.backup_list.addItem(item_text)
            self.backup_list.item(self.backup_list.count() - 1).setData(Qt.UserRole, backup)
    
    def restore_selected_backups(self):
        selected_items = self.backup_list.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "No Selection", "Please select backups to restore.")
            return
        
        track_names = []
        for item in selected_items:
            backup = item.data(Qt.UserRole)
            if backup:
                track_names.append(backup.get("track", backup.get("original_file", "Unknown")))
        
        reply = QMessageBox.question(
            self, "Confirm Restore",
            f"Restore {len(selected_items)} AIW file(s)?\n\nTracks: {', '.join(track_names)}\n\nThis will undo Autopilot changes.",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
        
        restored = 0
        for item in selected_items:
            backup = item.data(Qt.UserRole)
            if backup and self.restore_aiw_backup(backup):
                restored += 1
        
        if restored > 0:
            self.add_change_entry("Backup", f"Restored {restored} AIW file(s)")
            QMessageBox.information(self, "Restore Complete", f"Successfully restored {restored} AIW file(s).")
            self.refresh_backup_list()
        else:
            QMessageBox.warning(self, "Restore Failed", "Could not restore selected backups.")
    
    def restore_all_backups(self):
        backups = self.scan_aiw_backups()
        if not backups:
            QMessageBox.information(self, "No Backups", "No backups found to restore.")
            return
        
        reply = QMessageBox.question(
            self, "Confirm Restore All",
            f"Restore ALL {len(backups)} AIW backup(s)?\n\nThis will undo ALL Autopilot changes.",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
        
        restored = self.restore_all_aiw_backups()
        
        if restored > 0:
            self.add_change_entry("Backup", f"Restored all {restored} AIW file(s)")
            QMessageBox.information(self, "Restore Complete", f"Successfully restored {restored} AIW file(s).")
            self.refresh_backup_list()
        else:
            QMessageBox.warning(self, "Restore Failed", "Could not restore backups.")


def create_control_panel(parent=None):
    """Create the left control panel with all widgets"""
    panel = QWidget(parent)
    panel.setMaximumWidth(400)
    panel.setMinimumWidth(250)
    layout = QVBoxLayout(panel)
    layout.setSpacing(10)
    
    def make_btn(text, checkable=False, height=30, bg_color=None, checked_color=None):
        btn = QPushButton(text)
        if checkable:
            btn.setCheckable(True)
        
        btn.setFixedHeight(height)
        btn.setMinimumHeight(height)
        btn.setMaximumHeight(height)
        btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        
        style = f"""
            QPushButton {{
                height: {height}px;
                padding: 4px 8px;
                font-size: 11px;
                border-radius: 4px;
            }}
        """
        if bg_color:
            style += f"QPushButton {{ background-color: {bg_color}; color: white; }}"
        if checked_color:
            style += f"QPushButton:checked {{ background-color: {checked_color}; color: black if checked_color == '#FFFF00' else 'white'; }}"
        
        btn.setStyleSheet(style)
        return btn
    
    info_label = QLabel("Select vehicles to display data points.\n"
                       "Ctrl+Click = multi-select | Click = single")
    info_label.setStyleSheet("color: #888; font-size: 10px;")
    info_label.setWordWrap(True)
    layout.addWidget(info_label)
    
    track_group = QGroupBox("Track")
    track_layout = QVBoxLayout(track_group)
    
    current_track_layout = QHBoxLayout()
    current_track_label = QLabel("Current:")
    current_track_label.setStyleSheet("color: #FFA500; font-weight: bold;")
    current_track_layout.addWidget(current_track_label)
    
    current_track_display = QLabel("-")
    current_track_display.setStyleSheet("color: #4CAF50; font-family: monospace; font-weight: bold;")
    current_track_display.setWordWrap(True)
    current_track_layout.addWidget(current_track_display, 1)
    track_layout.addLayout(current_track_layout)
    
    multi_track_btn = make_btn("Select Multiple Tracks...", height=30, bg_color="#2196F3")
    track_layout.addWidget(multi_track_btn)
    
    track_list = QListWidget()
    track_list.setVisible(False)
    layout.addWidget(track_group)
    
    vehicle_group = QGroupBox("Vehicles")
    vehicle_layout = QVBoxLayout(vehicle_group)
    vehicle_list = QListWidget()
    vehicle_list.setSelectionMode(QAbstractItemView.ExtendedSelection)
    vehicle_layout.addWidget(vehicle_list)
    
    vehicle_btn_layout = QHBoxLayout()
    select_all_vehicles = make_btn("Select All", height=28)
    clear_vehicles = make_btn("Clear", height=28)
    vehicle_btn_layout.addWidget(select_all_vehicles)
    vehicle_btn_layout.addWidget(clear_vehicles)
    vehicle_layout.addLayout(vehicle_btn_layout)
    layout.addWidget(vehicle_group)
    
    type_group = QGroupBox("Data Types")
    type_layout = QHBoxLayout(type_group)
    type_layout.setSpacing(8)
    
    qual_btn = make_btn("Quali", checkable=True, height=28, bg_color="#4CAF50", checked_color="#FFFF00")
    qual_btn.setChecked(True)
    type_layout.addWidget(qual_btn)
    
    race_btn = make_btn("Race", checkable=True, height=28, bg_color="#4CAF50", checked_color="#FF6600")
    race_btn.setChecked(True)
    type_layout.addWidget(race_btn)
    
    unkn_btn = make_btn("Unknw", checkable=True, height=28, bg_color="#4CAF50", checked_color="#FF00FF")
    unkn_btn.setChecked(True)
    type_layout.addWidget(unkn_btn)
    
    type_layout.addStretch()
    layout.addWidget(type_group)
    
    param_group = QGroupBox("Manual Curve Parameters: T = a / R + b")
    param_layout = QVBoxLayout(param_group)
    
    curve_selector_layout = QHBoxLayout()
    curve_selector_label = QLabel("Edit curve:")
    curve_selector_label.setStyleSheet("color: #FFA500; font-weight: bold;")
    curve_selector_layout.addWidget(curve_selector_label)
    
    curve_selector = QComboBox()
    curve_selector.addItem("Qualifying (Yellow)", "qual")
    curve_selector.addItem("Race (Orange)", "race")
    curve_selector.setFixedHeight(28)
    curve_selector.setStyleSheet("""
        QComboBox {
            background-color: #3c3c3c;
            color: white;
            border: 1px solid #4CAF50;
            border-radius: 3px;
            padding: 4px;
        }
    """)
    curve_selector_layout.addWidget(curve_selector)
    curve_selector_layout.addStretch()
    param_layout.addLayout(curve_selector_layout)
    
    current_formula_label = QLabel("Current formula: T = -- / R + --")
    current_formula_label.setStyleSheet("color: #4CAF50; font-family: monospace; font-size: 11px;")
    current_formula_label.setWordWrap(True)
    param_layout.addWidget(current_formula_label)
    
    param_layout.addSpacing(5)
    
    a_layout = QHBoxLayout()
    a_label = QLabel("Height (a):")
    a_layout.addWidget(a_label)
    a_spin = QDoubleSpinBox()
    a_spin.setRange(0.01, 500.0)
    a_spin.setDecimals(3)
    a_spin.setSingleStep(1.0)
    a_spin.setValue(30.0)
    a_spin.setFixedHeight(28)
    a_layout.addWidget(a_spin)
    param_layout.addLayout(a_layout)
    
    b_layout = QHBoxLayout()
    b_label = QLabel("Base (b):")
    b_layout.addWidget(b_label)
    b_spin = QDoubleSpinBox()
    b_spin.setRange(0.01, 200.0)
    b_spin.setDecimals(3)
    b_spin.setSingleStep(0.5)
    b_spin.setValue(70.0)
    b_spin.setFixedHeight(28)
    b_layout.addWidget(b_spin)
    param_layout.addLayout(b_layout)
    
    apply_btn = make_btn("Apply to Selected Curve", height=32, bg_color="#2196F3")
    param_layout.addWidget(apply_btn)
    
    info_layout = QVBoxLayout()
    k_label = QLabel("Steepness k = a/(a+b) = ---")
    k_label.setStyleSheet("color: #888;")
    info_layout.addWidget(k_label)
    m_label = QLabel("Time at R=1.0 = a+b = ---")
    m_label.setStyleSheet("color: #888;")
    info_layout.addWidget(m_label)
    param_layout.addLayout(info_layout)
    layout.addWidget(param_group)
    
    autopilot_group = QGroupBox("Autopilot")
    autopilot_layout = QVBoxLayout(autopilot_group)
    
    autopilot_enable_btn = make_btn("Autopilot is OFF", checkable=True, height=32, bg_color="#555", checked_color="#FF9800")
    autopilot_layout.addWidget(autopilot_enable_btn)
    
    autopilot_info = QLabel("When enabled, automatically adjusts AIW ratios\nbased on detected race data.")
    autopilot_info.setStyleSheet("color: #888; font-size: 9px;")
    autopilot_info.setWordWrap(True)
    autopilot_layout.addWidget(autopilot_info)
    
    autopilot_status = QLabel("Status: Disabled")
    autopilot_status.setStyleSheet("color: #FF9800; font-size: 10px;")
    autopilot_layout.addWidget(autopilot_status)
    
    layout.addWidget(autopilot_group)
    
    btn_layout = QVBoxLayout()
    btn_layout.setSpacing(8)
    
    fit_btn = make_btn("Auto-Fit to Selected Data", height=32, bg_color="#4CAF50")
    btn_layout.addWidget(fit_btn)
    
    reset_btn = make_btn("Reset View", height=32)
    btn_layout.addWidget(reset_btn)
    
    advanced_btn = make_btn("Advanced Settings", height=32, bg_color="#9C27B0")
    btn_layout.addWidget(advanced_btn)
    
    exit_btn = make_btn("Exit", height=32, bg_color="#f44336")
    btn_layout.addWidget(exit_btn)
    
    layout.addLayout(btn_layout)
    layout.addStretch()
    
    stats_label = QLabel("")
    stats_label.setStyleSheet("color: #888; padding: 5px;")
    stats_label.setWordWrap(True)
    layout.addWidget(stats_label)
    
    return {
        'panel': panel,
        'track_list': track_list,
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
        'advanced_btn': advanced_btn
    }


def create_plot_widget(parent=None):
    """Create the plot widget using pyqtgraph for lightweight rendering"""
    widget = QWidget(parent)
    layout = QVBoxLayout(widget)
    layout.setContentsMargins(0, 0, 0, 0)
    
    plot_widget = pg.GraphicsLayoutWidget()
    plot_widget.setBackground('#2b2b2b')
    
    plot = plot_widget.addPlot()
    plot.setLabel('bottom', 'Ratio (R)', color='white', size='11pt')
    plot.setLabel('left', 'Lap Time (seconds)', color='white', size='11pt')
    plot.setTitle('Hyperbolic Curve: T = a / R + b', color='#FFA500', size='12pt')
    plot.showGrid(x=True, y=True, alpha=0.3)
    plot.setXRange(0.4, 2.0)
    plot.setYRange(50, 200)
    
    plot.getAxis('bottom').setPen('white')
    plot.getAxis('bottom').setTextPen('white')
    plot.getAxis('left').setPen('white')
    plot.getAxis('left').setTextPen('white')
    
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
    """Update the plot with new curve and points"""
    plot = plot_data['plot']
    
    ratios = np.linspace(0.4, 2.0, 200)
    times = a / ratios + b
    
    if plot_data['curve_line'] is None:
        plot_data['curve_line'] = plot.plot(ratios, times, pen=pg.mkPen(color='#00FFFF', width=2.5))
    else:
        plot_data['curve_line'].setData(ratios, times)
    
    quali_points = points_data.get('quali', [])
    race_points = points_data.get('race', [])
    unknown_points = points_data.get('unknown', [])
    
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
    
    if plot_data['legend'] is not None:
        plot.scene().removeItem(plot_data['legend'])
        plot_data['legend'] = None
    
    plot_data['legend'] = plot.addLegend()
    
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
            padding: 6px 12px;
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
