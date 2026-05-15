#!/usr/bin/env python3
"""
Laptimes and Ratios tab for Dyn AI Data Manager
Provides direct database editing with graph visualization and multi-select support
"""

from typing import List, Tuple

import numpy as np
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGroupBox, QComboBox, QTableWidget, QTableWidgetItem, QHeaderView,
    QMessageBox, QDialog, QFormLayout, QDoubleSpinBox, QApplication,
    QShortcut, QCheckBox
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QKeySequence

import pyqtgraph as pg

from gui_data_manager_common import SimpleCurveDatabase


class MultiDataPointEditDialog(QDialog):
    """Dialog for editing multiple data points at once"""
    
    def __init__(self, parent, selected_points: List[Tuple], tracks: List[str], vehicle_classes: List[str]):
        super().__init__(parent)
        self.selected_points = selected_points
        self.tracks = tracks
        self.vehicle_classes = vehicle_classes
        self.setup_ui()
    
    def setup_ui(self):
        self.setWindowTitle(f"Edit {len(self.selected_points)} Data Points")
        self.setFixedSize(550, 450)
        
        self.setStyleSheet("""
            QDialog {
                background-color: #2b2b2b;
            }
            QLabel {
                color: white;
            }
            QComboBox, QDoubleSpinBox {
                background-color: #3c3c3c;
                color: white;
                border: 1px solid #4CAF50;
                border-radius: 4px;
                padding: 6px;
                min-width: 150px;
            }
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton#cancel {
                background-color: #555;
            }
            QPushButton#cancel:hover {
                background-color: #666;
            }
            QCheckBox {
                color: white;
                spacing: 8px;
            }
        """)
        
        layout = QVBoxLayout(self)
        
        title = QLabel(f"Edit {len(self.selected_points)} Selected Data Points")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #FFA500;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        layout.addSpacing(15)
        
        info_label = QLabel("Leave a field empty or unchecked to keep original values for that field.")
        info_label.setStyleSheet("color: #888; font-size: 11px;")
        info_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(info_label)
        
        layout.addSpacing(10)
        
        form_layout = QFormLayout()
        
        # Check current values to determine if fields have mixed values
        tracks_set = set(p[1] for p in self.selected_points)
        classes_set = set(p[2] for p in self.selected_points)
        ratios_set = set(p[3] for p in self.selected_points)
        times_set = set(p[4] for p in self.selected_points)
        sessions_set = set(p[5] for p in self.selected_points)
        
        # Track
        self.track_check = QCheckBox("Change Track:")
        self.track_combo = QComboBox()
        self.track_combo.addItems(self.tracks)
        self.track_combo.setEnabled(False)
        self.track_check.toggled.connect(self.track_combo.setEnabled)
        track_layout = QHBoxLayout()
        track_layout.addWidget(self.track_combo)
        track_layout.addWidget(self.track_check)
        if len(tracks_set) == 1:
            self.track_combo.setCurrentText(list(tracks_set)[0])
        form_layout.addRow("Track:", track_layout)
        
        # Vehicle Class
        self.class_check = QCheckBox("Change Vehicle Class:")
        self.class_combo = QComboBox()
        self.class_combo.addItems(self.vehicle_classes)
        self.class_combo.setEnabled(False)
        self.class_check.toggled.connect(self.class_combo.setEnabled)
        class_layout = QHBoxLayout()
        class_layout.addWidget(self.class_combo)
        class_layout.addWidget(self.class_check)
        if len(classes_set) == 1:
            self.class_combo.setCurrentText(list(classes_set)[0])
        form_layout.addRow("Vehicle Class:", class_layout)
        
        # Ratio
        self.ratio_check = QCheckBox("Change Ratio:")
        self.ratio_spin = QDoubleSpinBox()
        self.ratio_spin.setRange(0.1, 3.0)
        self.ratio_spin.setDecimals(6)
        self.ratio_spin.setSingleStep(0.01)
        self.ratio_spin.setEnabled(False)
        self.ratio_check.toggled.connect(self.ratio_spin.setEnabled)
        ratio_layout = QHBoxLayout()
        ratio_layout.addWidget(self.ratio_spin)
        ratio_layout.addWidget(self.ratio_check)
        if len(ratios_set) == 1:
            self.ratio_spin.setValue(list(ratios_set)[0])
        form_layout.addRow("Ratio:", ratio_layout)
        
        # Lap Time
        self.time_check = QCheckBox("Change Lap Time:")
        self.time_spin = QDoubleSpinBox()
        self.time_spin.setRange(10.0, 500.0)
        self.time_spin.setDecimals(3)
        self.time_spin.setSingleStep(0.5)
        self.time_spin.setEnabled(False)
        self.time_check.toggled.connect(self.time_spin.setEnabled)
        time_layout = QHBoxLayout()
        time_layout.addWidget(self.time_spin)
        time_layout.addWidget(self.time_check)
        if len(times_set) == 1:
            self.time_spin.setValue(list(times_set)[0])
        form_layout.addRow("Lap Time (seconds):", time_layout)
        
        # Session Type
        self.session_check = QCheckBox("Change Session Type:")
        self.session_combo = QComboBox()
        self.session_combo.addItems(["qual", "race"])
        self.session_combo.setEnabled(False)
        self.session_check.toggled.connect(self.session_combo.setEnabled)
        session_layout = QHBoxLayout()
        session_layout.addWidget(self.session_combo)
        session_layout.addWidget(self.session_check)
        if len(sessions_set) == 1:
            self.session_combo.setCurrentText(list(sessions_set)[0])
        form_layout.addRow("Session Type:", session_layout)
        
        layout.addLayout(form_layout)
        
        layout.addSpacing(20)
        
        btn_layout = QHBoxLayout()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setObjectName("cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        
        save_btn = QPushButton("Apply Changes to All Selected")
        save_btn.clicked.connect(self.accept)
        btn_layout.addWidget(save_btn)
        
        layout.addLayout(btn_layout)
    
    def get_updates(self) -> dict:
        updates = {}
        
        if self.track_check.isChecked():
            updates['track'] = self.track_combo.currentText()
        
        if self.class_check.isChecked():
            updates['vehicle_class'] = self.class_combo.currentText()
        
        if self.ratio_check.isChecked():
            updates['ratio'] = self.ratio_spin.value()
        
        if self.time_check.isChecked():
            updates['lap_time'] = self.time_spin.value()
        
        if self.session_check.isChecked():
            updates['session_type'] = self.session_combo.currentText()
        
        return updates


class DatabaseManagerTab(QWidget):
    """Tab for direct database management with graph visualization and multi-select support"""
    
    data_changed = pyqtSignal()
    
    def __init__(self, db: SimpleCurveDatabase, parent=None):
        super().__init__(parent)
        self.db = db
        self.current_points = []
        self.selected_point_ids = set()
        self.selected_point_markers = []
        self.last_selected_row = -1
        self.setup_ui()
        self.setup_shortcuts()
        self.refresh_filters()
        self.refresh_table()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        
        filter_group = QGroupBox("Filter Data Points")
        filter_layout = QVBoxLayout(filter_group)
        
        filter_row1 = QHBoxLayout()
        filter_row1.addWidget(QLabel("Track:"))
        self.track_filter = QComboBox()
        self.track_filter.addItem("All")
        self.track_filter.currentTextChanged.connect(self.on_filter_changed)
        filter_row1.addWidget(self.track_filter)
        
        filter_row1.addSpacing(20)
        filter_row1.addWidget(QLabel("Vehicle Class:"))
        self.class_filter = QComboBox()
        self.class_filter.addItem("All")
        self.class_filter.currentTextChanged.connect(self.on_filter_changed)
        filter_row1.addWidget(self.class_filter)
        
        filter_row1.addSpacing(20)
        filter_row1.addWidget(QLabel("Session:"))
        self.session_filter = QComboBox()
        self.session_filter.addItems(["All", "qual", "race"])
        self.session_filter.currentTextChanged.connect(self.on_filter_changed)
        filter_row1.addWidget(self.session_filter)
        
        filter_row1.addStretch()
        filter_layout.addLayout(filter_row1)
        
        filter_row2 = QHBoxLayout()
        self.refresh_filters_btn = QPushButton("Refresh Filters")
        self.refresh_filters_btn.clicked.connect(self.refresh_filters)
        filter_row2.addWidget(self.refresh_filters_btn)
        
        self.search_btn = QPushButton("Apply Filter")
        self.search_btn.clicked.connect(self.refresh_table)
        filter_row2.addWidget(self.search_btn)
        
        filter_row2.addStretch()
        filter_layout.addLayout(filter_row2)
        
        layout.addWidget(filter_group)
        
        graph_group = QGroupBox("Data Point Visualization")
        graph_layout = QVBoxLayout(graph_group)
        
        self.plot_widget = pg.GraphicsLayoutWidget()
        self.plot_widget.setBackground('#2b2b2b')
        self.plot = self.plot_widget.addPlot()
        self.plot.setLabel('bottom', 'Ratio (R)', color='white', size='11pt')
        self.plot.setLabel('left', 'Lap Time (seconds)', color='white', size='11pt')
        self.plot.setTitle('Data Points - Click on points to select', color='#FFA500', size='12pt')
        self.plot.showGrid(x=True, y=True, alpha=0.3)
        self.plot.setXRange(0.4, 2.0)
        self.plot.setYRange(50, 200)
        self.plot.getAxis('bottom').setPen('white')
        self.plot.getAxis('bottom').setTextPen('white')
        self.plot.getAxis('left').setPen('white')
        self.plot.getAxis('left').setTextPen('white')
        self.plot.scene().sigMouseClicked.connect(self.on_plot_click)
        
        graph_layout.addWidget(self.plot_widget)
        layout.addWidget(graph_group, stretch=2)
        
        table_group = QGroupBox("Data Points")
        table_layout = QVBoxLayout(table_group)
        
        self.data_table = QTableWidget()
        self.data_table.setAlternatingRowColors(True)
        self.data_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.data_table.setSelectionMode(QTableWidget.ExtendedSelection)
        self.data_table.itemSelectionChanged.connect(self.on_table_selection_changed)
        self.data_table.setColumnCount(7)
        self.data_table.setHorizontalHeaderLabels(["ID", "Track", "Vehicle Class", "Ratio", "Lap Time (s)", "Session", "Created At"])
        self.data_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        table_layout.addWidget(self.data_table)
        
        action_layout = QHBoxLayout()
        self.select_all_btn = QPushButton("Select All")
        self.select_all_btn.clicked.connect(self.select_all)
        action_layout.addWidget(self.select_all_btn)
        
        self.edit_btn = QPushButton("Edit Selected (Enter)")
        self.edit_btn.clicked.connect(self.edit_selected)
        self.edit_btn.setEnabled(False)
        action_layout.addWidget(self.edit_btn)
        
        self.delete_btn = QPushButton("Delete Selected (Delete)")
        self.delete_btn.clicked.connect(self.delete_selected)
        self.delete_btn.setEnabled(False)
        self.delete_btn.setStyleSheet("background-color: #f44336;")
        action_layout.addWidget(self.delete_btn)
        
        action_layout.addStretch()
        
        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet("color: #888;")
        action_layout.addWidget(self.status_label)
        
        table_layout.addLayout(action_layout)
        layout.addWidget(table_group, stretch=1)
    
    def setup_shortcuts(self):
        """Set up keyboard shortcuts"""
        # Delete key shortcut
        self.delete_shortcut = QShortcut(QKeySequence.Delete, self)
        self.delete_shortcut.activated.connect(self.delete_selected)
        
        # Enter key shortcut for edit
        self.enter_shortcut = QShortcut(QKeySequence(Qt.Key_Return), self)
        self.enter_shortcut.activated.connect(self.edit_selected)
        
        # Also handle Enter on numpad
        self.enter_shortcut2 = QShortcut(QKeySequence(Qt.Key_Enter), self)
        self.enter_shortcut2.activated.connect(self.edit_selected)
    
    def refresh_filters(self):
        """Refresh the filter dropdowns with current database values"""
        current_track = self.track_filter.currentText()
        current_class = self.class_filter.currentText()
        
        self.track_filter.clear()
        self.class_filter.clear()
        
        self.track_filter.addItem("All")
        self.class_filter.addItem("All")
        
        tracks = self.db.get_all_tracks()
        for track in tracks:
            self.track_filter.addItem(track)
        
        classes = self.db.get_all_vehicle_classes()
        for cls in classes:
            self.class_filter.addItem(cls)
        
        if current_track != "All" and current_track in tracks:
            self.track_filter.setCurrentText(current_track)
        if current_class != "All" and current_class in classes:
            self.class_filter.setCurrentText(current_class)
    
    def refresh_table(self):
        """Refresh the table and graph based on current filters"""
        track = self.track_filter.currentText()
        if track == "All":
            track = None
        
        vehicle_class = self.class_filter.currentText()
        if vehicle_class == "All":
            vehicle_class = None
        
        session_type = self.session_filter.currentText()
        if session_type == "All":
            session_type = None
        
        self.current_points = self.db.get_data_points_filtered(track, vehicle_class, session_type)
        
        self.data_table.setRowCount(len(self.current_points))
        for row, point in enumerate(self.current_points):
            point_id = point[0]
            track_name = point[1]
            vehicle_class_name = point[2]
            ratio = point[3]
            lap_time = point[4]
            session = point[5]
            created_at = point[6] if len(point) > 6 else ""
            
            self.data_table.setItem(row, 0, QTableWidgetItem(str(point_id)))
            self.data_table.setItem(row, 1, QTableWidgetItem(track_name))
            self.data_table.setItem(row, 2, QTableWidgetItem(vehicle_class_name))
            self.data_table.setItem(row, 3, QTableWidgetItem(f"{ratio:.6f}"))
            self.data_table.setItem(row, 4, QTableWidgetItem(f"{lap_time:.3f}"))
            self.data_table.setItem(row, 5, QTableWidgetItem(session))
            self.data_table.setItem(row, 6, QTableWidgetItem(created_at))
        
        self.status_label.setText(f"Found {len(self.current_points)} data points")
        self.selected_point_ids.clear()
        self.last_selected_row = -1
        self.update_graph()
    
    def update_graph(self):
        """Update the graph with current data points"""
        self.plot.clear()
        
        if not self.current_points:
            self.plot.setTitle('No data points match the current filters', color='#FFA500', size='12pt')
            return
        
        self.plot.setTitle('Data Points - Click on points to select', color='#FFA500', size='12pt')
        
        qual_ratios = []
        qual_times = []
        race_ratios = []
        race_times = []
        
        # Store point data for click handling
        self.graph_points = []
        
        for point in self.current_points:
            point_id = point[0]
            ratio = point[3]
            lap_time = point[4]
            session = point[5]
            
            self.graph_points.append((point_id, ratio, lap_time, session))
            
            if session == "qual":
                qual_ratios.append(ratio)
                qual_times.append(lap_time)
            else:
                race_ratios.append(ratio)
                race_times.append(lap_time)
        
        # Plot qualifying points (yellow circles)
        if qual_ratios:
            qual_scatter = pg.ScatterPlotItem(
                qual_ratios, qual_times, 
                brush=pg.mkBrush('#FFFF00'), size=8, symbol='o', 
                pen=pg.mkPen('white', width=1)
            )
            self.plot.addItem(qual_scatter)
        
        # Plot race points (orange squares)
        if race_ratios:
            race_scatter = pg.ScatterPlotItem(
                race_ratios, race_times, 
                brush=pg.mkBrush('#FF6600'), size=8, symbol='s', 
                pen=pg.mkPen('white', width=1)
            )
            self.plot.addItem(race_scatter)
        
        # Highlight selected points
        self.selected_point_markers = []
        for point in self.current_points:
            if point[0] in self.selected_point_ids:
                marker = pg.ScatterPlotItem(
                    [point[3]], [point[4]], 
                    brush=pg.mkBrush('#FFFFFF'), size=14, symbol='o', 
                    pen=pg.mkPen('#FF0000', width=3)
                )
                self.plot.addItem(marker)
                self.selected_point_markers.append(marker)
        
        # Add legend with text only (no symbols, no lines)
        # Create a custom legend item that doesn't add plot elements
        legend = self.plot.addLegend()
        
        # For legend entries, we need to add items that exist in the plot
        # The trick is to add the actual scatter items to the legend
        # but we can control what they look like in the legend
        if qual_ratios:
            # Use the actual scatter item, but we can't remove its symbol from legend
            # Instead, create a simple text label approach - clear legend and add custom text items
            pass
        
        # Better approach: Remove the default legend and create a text-only legend
        self.plot.removeItem(legend)
        
        # Create a text-only legend manually
        legend_text = ""
        if qual_ratios:
            legend_text += f"Qualifying ({len(qual_ratios)})"
        if qual_ratios and race_ratios:
            legend_text += "  |  "
        if race_ratios:
            legend_text += f"Race ({len(race_ratios)})"
        
        if legend_text:
            # Add a text item as a pseudo-legend
            text_item = pg.TextItem(text=legend_text, color='#CCCCCC', anchor=(0, 1))
            text_item.setPos(self.plot.viewRange()[0][0] + 0.02, self.plot.viewRange()[1][1] - 2)
            self.plot.addItem(text_item)
    
    def on_plot_click(self, event):
        """Handle click on the graph to select a point with Ctrl/Shift support"""
        if self.plot.scene().mouseGrabberItem() is not None:
            return
        
        pos = event.scenePos()
        mouse_point = self.plot.vb.mapSceneToView(pos)
        
        # Find closest point
        closest_point = None
        closest_dist = float('inf')
        closest_idx = -1
        
        for idx, (point_id, ratio, lap_time, session) in enumerate(self.graph_points):
            dist = ((ratio - mouse_point.x()) ** 2 + (lap_time - mouse_point.y()) ** 2) ** 0.5
            if dist < closest_dist and dist < 0.05:
                closest_dist = dist
                closest_point = point_id
                closest_idx = idx
        
        if closest_point is not None:
            # Find the row for this point
            current_row = -1
            for row in range(self.data_table.rowCount()):
                if int(self.data_table.item(row, 0).text()) == closest_point:
                    current_row = row
                    break
            
            if current_row < 0:
                return
            
            # Handle selection modifiers
            modifiers = QApplication.keyboardModifiers()
            
            if modifiers == Qt.ControlModifier:
                # Ctrl: Toggle selection
                if closest_point in self.selected_point_ids:
                    self.selected_point_ids.remove(closest_point)
                else:
                    self.selected_point_ids.add(closest_point)
            elif modifiers == Qt.ShiftModifier and self.last_selected_row >= 0:
                # Shift: Select range between last click and this click
                start = min(self.last_selected_row, current_row)
                end = max(self.last_selected_row, current_row)
                for row in range(start, end + 1):
                    point_id = int(self.data_table.item(row, 0).text())
                    self.selected_point_ids.add(point_id)
            else:
                # No modifier: Single selection only
                self.selected_point_ids.clear()
                self.selected_point_ids.add(closest_point)
            
            # Update last selected row
            self.last_selected_row = current_row
            
            # Update table selection to match
            self.update_table_selection_from_ids()
            self.update_graph()
            self.update_button_states()
    
    def update_table_selection_from_ids(self):
        """Update table selection to match selected_point_ids"""
        self.data_table.clearSelection()
        for row in range(self.data_table.rowCount()):
            point_id = int(self.data_table.item(row, 0).text())
            if point_id in self.selected_point_ids:
                self.data_table.selectRow(row)
    
    def on_table_selection_changed(self):
        """Handle selection change in the table with Ctrl/Shift support"""
        # Get currently selected rows from the table
        selected_rows = set()
        for item in self.data_table.selectedItems():
            selected_rows.add(item.row())
        
        # Update selected_point_ids based on table selection
        new_selected_ids = set()
        for row in selected_rows:
            point_id = int(self.data_table.item(row, 0).text())
            new_selected_ids.add(point_id)
        
        # Update last selected row if there's a selection
        if selected_rows:
            self.last_selected_row = max(selected_rows)
        
        # Sync our internal set with the table
        self.selected_point_ids = new_selected_ids
        
        self.update_graph()
        self.update_button_states()
    
    def update_button_states(self):
        """Update button enabled states based on selection"""
        has_selection = len(self.selected_point_ids) > 0
        self.edit_btn.setEnabled(has_selection)
        self.delete_btn.setEnabled(has_selection)
        
        if has_selection:
            self.status_label.setText(f"{len(self.selected_point_ids)} data point(s) selected")
        else:
            self.status_label.setText(f"Found {len(self.current_points)} data points")
    
    def select_all(self):
        """Select all data points in the current filter"""
        self.selected_point_ids.clear()
        for point in self.current_points:
            self.selected_point_ids.add(point[0])
        self.update_table_selection_from_ids()
        self.update_graph()
        self.update_button_states()
        if self.current_points:
            self.last_selected_row = len(self.current_points) - 1
    
    def on_filter_changed(self):
        """Auto-refresh when filter changes"""
        self.selected_point_ids.clear()
        self.last_selected_row = -1
        self.refresh_table()
    
    def edit_selected(self):
        """Edit the selected data points"""
        if not self.selected_point_ids:
            QMessageBox.warning(self, "No Selection", "Please select data points to edit.")
            return
        
        selected_points = [p for p in self.current_points if p[0] in self.selected_point_ids]
        
        if not selected_points:
            return
        
        tracks = self.db.get_all_tracks()
        vehicle_classes = self.db.get_all_vehicle_classes()
        
        dialog = MultiDataPointEditDialog(self, selected_points, tracks, vehicle_classes)
        if dialog.exec_() == QDialog.Accepted:
            updates = dialog.get_updates()
            
            if not updates:
                QMessageBox.information(self, "No Changes", "No changes were specified.")
                return
            
            success_count = 0
            for point in selected_points:
                point_id = point[0]
                track = updates.get('track', point[1])
                vehicle_class = updates.get('vehicle_class', point[2])
                ratio = updates.get('ratio', point[3])
                lap_time = updates.get('lap_time', point[4])
                session_type = updates.get('session_type', point[5])
                
                if self.db.update_data_point(point_id, track, vehicle_class, ratio, lap_time, session_type):
                    success_count += 1
            
            if success_count > 0:
                QMessageBox.information(self, "Success", f"Updated {success_count} of {len(selected_points)} data points.")
                self.refresh_table()
                self.data_changed.emit()
            else:
                QMessageBox.critical(self, "Error", "Failed to update data points.")
    
    def delete_selected(self):
        """Delete the selected data points"""
        if not self.selected_point_ids:
            QMessageBox.warning(self, "No Selection", "Please select data points to delete.")
            return
        
        selected_points = [p for p in self.current_points if p[0] in self.selected_point_ids]
        
        if not selected_points:
            return
        
        reply = QMessageBox.question(
            self, 
            "Confirm Delete",
            f"Delete {len(selected_points)} selected data point(s)?\n\n"
            f"This action cannot be undone.",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            success_count = 0
            for point in selected_points:
                if self.db.delete_data_point(point[0]):
                    success_count += 1
            
            if success_count > 0:
                QMessageBox.information(self, "Success", f"Deleted {success_count} of {len(selected_points)} data points.")
                self.selected_point_ids.clear()
                self.last_selected_row = -1
                self.refresh_table()
                self.data_changed.emit()
            else:
                QMessageBox.critical(self, "Error", "Failed to delete data points.")
