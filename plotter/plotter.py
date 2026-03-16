# pipenv run pip install pyqtgraph PyQt5 numpy
import sys
import csv
import numpy as np
from pathlib import Path
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
import pyqtgraph as pg
from collections import defaultdict

class FilterWidget(QWidget):
    def __init__(self, column_name, values, parent=None):
        super().__init__(parent)
        self.column_name = column_name
        self.values = sorted(set(str(v) for v in values if v))
        self.checkboxes = []
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Header with select all/none
        header = QHBoxLayout()
        header.addWidget(QLabel(f"<b>{self.column_name}</b>"))
        header.addStretch()
        
        select_all_btn = QPushButton("All")
        select_all_btn.setMaximumWidth(40)
        select_all_btn.setMaximumHeight(25)
        select_all_btn.clicked.connect(self.select_all)
        header.addWidget(select_all_btn)
        
        select_none_btn = QPushButton("None")
        select_none_btn.setMaximumWidth(40)
        select_none_btn.setMaximumHeight(25)
        select_none_btn.clicked.connect(self.select_none)
        header.addWidget(select_none_btn)
        
        layout.addLayout(header)
        
        # Scrollable area for checkboxes
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setMaximumHeight(150)
        scroll.setMinimumHeight(100)
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        scroll_layout.setContentsMargins(0, 0, 0, 0)
        scroll_layout.setSpacing(2)
        
        for value in self.values:
            cb = QCheckBox(str(value))
            cb.setChecked(True)
            self.checkboxes.append(cb)
            scroll_layout.addWidget(cb)
        
        scroll_layout.addStretch()
        scroll.setWidget(scroll_widget)
        layout.addWidget(scroll)
        
        self.setLayout(layout)
        self.setMaximumHeight(250)
        self.setMinimumHeight(150)
    
    def select_all(self):
        for cb in self.checkboxes:
            cb.setChecked(True)
    
    def select_none(self):
        for cb in self.checkboxes:
            cb.setChecked(False)
    
    def get_selected_values(self):
        selected = []
        for cb in self.checkboxes:
            if cb.isChecked():
                selected.append(cb.text())
        return selected

class DataPlotter(QMainWindow):
    def __init__(self, filename):
        super().__init__()
        self.filename = filename
        self.data = []
        self.columns = []
        self.x_column = None
        self.y_columns = []
        self.filters = {}
        self.plot_items = []
        self.setup_ui()
        self.load_data()
        
    def setup_ui(self):
        self.setWindowTitle(f"Data Plotter - {Path(self.filename).name}")
        
        # Get screen geometry to set appropriate size
        screen = QApplication.primaryScreen().geometry()
        available_width = screen.width() - 100  # Leave some margin
        available_height = screen.height() - 100
        
        # Set window size to 80% of screen but not exceeding screen bounds
        window_width = min(int(available_width * 0.8), 1400)
        window_height = min(int(available_height * 0.8), 900)
        
        # Center the window
        x = (screen.width() - window_width) // 2
        y = (screen.height() - window_height) // 2
        self.setGeometry(x, y, window_width, window_height)
        
        # Set maximum size to prevent going off screen
        self.setMaximumSize(screen.width() - 50, screen.height() - 50)
        
        self.setStyleSheet("""
            QMainWindow { background-color: #2b2b2b; }
            QLabel { color: #f0f0f0; }
            QGroupBox { 
                color: #4CAF50; 
                border: 1px solid #444;
                border-radius: 5px;
                margin-top: 10px;
                font-weight: bold;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
            QComboBox, QListWidget {
                background-color: #3a3a3a;
                color: #f0f0f0;
                border: 1px solid #555;
                border-radius: 3px;
                padding: 5px;
            }
            QListWidget {
                min-height: 80px;
                max-height: 150px;
            }
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 5px 10px;
                border-radius: 3px;
                font-weight: bold;
                min-width: 70px;
                max-height: 30px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
            }
            QPushButton:disabled {
                background-color: #666;
                color: #aaa;
            }
            QCheckBox {
                color: #f0f0f0;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
            }
            QScrollArea {
                background-color: #3a3a3a;
                border: 1px solid #555;
                border-radius: 3px;
            }
        """)
        
        # Central widget with splitter
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(5)
        
        # Create splitter with size constraints
        splitter = QSplitter(Qt.Horizontal)
        splitter.setChildrenCollapsible(False)  # Prevent panels from collapsing
        main_layout.addWidget(splitter)
        
        # Left panel - Controls (fixed width)
        left_panel = QWidget()
        left_panel.setMaximumWidth(350)
        left_panel.setMinimumWidth(280)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(5, 5, 5, 5)
        left_layout.setSpacing(5)
        
        # File info
        info_group = QGroupBox("File Information")
        info_group.setMaximumHeight(100)
        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)
        self.file_label = QLabel(f"File: {Path(self.filename).name}")
        self.file_label.setStyleSheet("color: #4CAF50;")
        self.file_label.setWordWrap(True)
        info_layout.addWidget(self.file_label)
        
        self.row_count_label = QLabel("Rows: 0")
        info_layout.addWidget(self.row_count_label)
        
        self.col_count_label = QLabel("Columns: 0")
        info_layout.addWidget(self.col_count_label)
        info_group.setLayout(info_layout)
        left_layout.addWidget(info_group)
        
        # Axis selection
        axis_group = QGroupBox("Axis Selection")
        axis_group.setMaximumHeight(200)
        axis_layout = QVBoxLayout()
        axis_layout.setSpacing(5)
        
        axis_layout.addWidget(QLabel("X Axis:"))
        self.x_combo = QComboBox()
        self.x_combo.setMaxVisibleItems(15)
        self.x_combo.currentTextChanged.connect(self.on_x_axis_changed)
        axis_layout.addWidget(self.x_combo)
        
        axis_layout.addWidget(QLabel("Y Axes (Ctrl+click to select multiple):"))
        self.y_list = QListWidget()
        self.y_list.setSelectionMode(QListWidget.MultiSelection)
        self.y_list.setMaximumHeight(120)
        self.y_list.itemSelectionChanged.connect(self.on_y_axes_changed)
        axis_layout.addWidget(self.y_list)
        
        axis_group.setLayout(axis_layout)
        left_layout.addWidget(axis_group)
        
        # Filters
        self.filter_group = QGroupBox("Filters")
        self.filter_layout = QVBoxLayout()
        self.filter_layout.setSpacing(2)
        self.filter_group.setLayout(self.filter_layout)
        left_layout.addWidget(self.filter_group)
        
        # Button layout
        button_layout = QHBoxLayout()
        button_layout.setSpacing(5)
        
        self.apply_filters_btn = QPushButton("Apply Filters")
        self.apply_filters_btn.clicked.connect(self.apply_filters)
        self.apply_filters_btn.setStyleSheet("""
            QPushButton {
                background-color: #ff9800;
            }
            QPushButton:hover {
                background-color: #f57c00;
            }
        """)
        button_layout.addWidget(self.apply_filters_btn)
        
        self.clear_filters_btn = QPushButton("Clear Filters")
        self.clear_filters_btn.clicked.connect(self.clear_filters)
        self.clear_filters_btn.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
            }
            QPushButton:hover {
                background-color: #d32f2f;
            }
        """)
        button_layout.addWidget(self.clear_filters_btn)
        
        left_layout.addLayout(button_layout)
        
        # Export button
        self.export_btn = QPushButton("Export Plot")
        self.export_btn.clicked.connect(self.export_plot)
        self.export_btn.setMaximumHeight(30)
        left_layout.addWidget(self.export_btn)
        
        left_layout.addStretch()
        
        # Right panel - Plot
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(5, 5, 5, 5)
        right_layout.setSpacing(5)
        
        # Plot widget
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setLabel('left', 'Y Values')
        self.plot_widget.setLabel('bottom', 'X Values')
        self.plot_widget.showGrid(x=True, y=True)
        self.plot_widget.setBackground('#1e1e1e')
        self.plot_widget.addLegend(offset=(10, 10))
        self.plot_widget.setMinimumHeight(400)
        right_layout.addWidget(self.plot_widget)
        
        # Legend checkboxes for toggling visibility (scrollable if too many)
        legend_scroll = QScrollArea()
        legend_scroll.setWidgetResizable(True)
        legend_scroll.setMaximumHeight(80)
        legend_scroll.setMinimumHeight(50)
        legend_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        legend_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        self.legend_widget = QWidget()
        legend_layout = QHBoxLayout(self.legend_widget)
        legend_layout.setContentsMargins(5, 2, 5, 2)
        legend_layout.setSpacing(10)
        legend_layout.addWidget(QLabel("Show:"))
        self.series_checkboxes = {}
        
        legend_scroll.setWidget(self.legend_widget)
        right_layout.addWidget(legend_scroll)
        
        # Status bar
        self.status_bar = QStatusBar()
        self.status_bar.setMaximumHeight(25)
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")
        
        # Add panels to splitter with size constraints
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        
        # Set initial splitter sizes (left panel fixed width, right panel takes rest)
        splitter.setSizes([300, self.width() - 300])
        splitter.setStretchFactor(0, 0)  # Left panel doesn't stretch
        splitter.setStretchFactor(1, 1)  # Right panel stretches
        
    def load_data(self):
        try:
            with open(self.filename, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f, delimiter=';')
                self.columns = reader.fieldnames
                
                # Load data
                self.data = []
                for row in reader:
                    processed_row = {}
                    for col in self.columns:
                        val = row[col].strip()
                        # Try to convert to float if possible
                        try:
                            processed_row[col] = float(val) if val else np.nan
                        except ValueError:
                            processed_row[col] = val
                    self.data.append(processed_row)
            
            # Update info labels
            self.row_count_label.setText(f"Rows: {len(self.data)}")
            self.col_count_label.setText(f"Columns: {len(self.columns)}")
            
            # Populate combo boxes
            self.x_combo.clear()
            self.x_combo.addItems(self.columns)
            
            self.y_list.clear()
            self.y_list.addItems(self.columns)
            
            # Create filter widgets for each column
            self.create_filter_widgets()
            
            self.status_bar.showMessage(f"Loaded {len(self.data)} rows", 3000)
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load data: {e}")
            self.status_bar.showMessage(f"Error loading data: {e}")
    
    def create_filter_widgets(self):
        # Clear existing filters
        for i in reversed(range(self.filter_layout.count())):
            widget = self.filter_layout.itemAt(i).widget()
            if widget:
                widget.deleteLater()
        
        self.filters.clear()
        
        # Create filter for each column (limit to reasonable number)
        filter_count = 0
        for col in self.columns:
            values = [row[col] for row in self.data if row[col] not in (None, '', np.nan)]
            if values and not all(isinstance(v, (int, float)) for v in values):
                # Only create filters for non-numeric columns
                if filter_count < 8:  # Limit to 8 filters to avoid overcrowding
                    filter_widget = FilterWidget(col, values)
                    self.filters[col] = filter_widget
                    self.filter_layout.addWidget(filter_widget)
                    filter_count += 1
                else:
                    # Add note about more columns
                    if filter_count == 8:
                        note = QLabel("(More columns not shown to save space)")
                        note.setStyleSheet("color: #888; font-style: italic;")
                        note.setWordWrap(True)
                        self.filter_layout.addWidget(note)
    
    def on_x_axis_changed(self, text):
        self.x_column = text
        self.update_plot()
    
    def on_y_axes_changed(self):
        selected = self.y_list.selectedItems()
        self.y_columns = [item.text() for item in selected]
        self.update_plot()
    
    def apply_filters(self):
        self.update_plot()
        self.status_bar.showMessage("Filters applied", 2000)
    
    def clear_filters(self):
        for filter_widget in self.filters.values():
            filter_widget.select_all()
        self.update_plot()
        self.status_bar.showMessage("Filters cleared", 2000)
    
    def get_filtered_data(self):
        if not self.data:
            return []
        
        filtered = []
        for row in self.data:
            include = True
            for col, filter_widget in self.filters.items():
                selected = filter_widget.get_selected_values()
                if str(row[col]) not in selected:
                    include = False
                    break
            if include:
                filtered.append(row)
        
        return filtered
    
    def update_plot(self):
        if not self.x_column or not self.y_columns:
            return
        
        # Clear existing plots
        self.plot_widget.clear()
        self.plot_items.clear()
        
        # Clear legend checkboxes
        for i in reversed(range(self.legend_widget.layout().count())):
            item = self.legend_widget.layout().itemAt(i)
            if item and item.widget():
                item.widget().deleteLater()
        self.series_checkboxes.clear()
        
        # Add back the "Show:" label
        self.legend_widget.layout().addWidget(QLabel("Show:"))
        
        # Get filtered data
        filtered_data = self.get_filtered_data()
        
        if not filtered_data:
            self.status_bar.showMessage("No data matches filters")
            return
        
        # Group data by categorical columns for coloring
        categorical_cols = []
        if filtered_data:
            first_row = filtered_data[0]
            for col in self.columns:
                if col != self.x_column and col not in self.y_columns:
                    if not isinstance(first_row.get(col, ''), (int, float)):
                        categorical_cols.append(col)
        
        # Create color map for grouping
        colors = ['#ff6b6b', '#4ecdc4', '#45b7d1', '#96ceb4', '#ffe66d', '#ff9f1c', 
                  '#c77dff', '#f6ae9d', '#6c5b7b', '#f08a5d', '#a8e6cf', '#d4a5a5']
        
        if categorical_cols:
            # Group by the first categorical column
            group_col = categorical_cols[0]
            groups = defaultdict(list)
            
            for row in filtered_data:
                group_val = str(row.get(group_col, 'Unknown'))
                groups[group_val].append(row)
            
            # Plot each group with different color
            for i, (group_val, group_data) in enumerate(groups.items()):
                color = colors[i % len(colors)]
                self.plot_group(group_data, group_val, color)
        else:
            # No grouping, plot all together
            self.plot_group(filtered_data, "All Data", '#4CAF50')
        
        # Update legend visibility controls (limit to avoid overcrowding)
        for col, plot_item in self.plot_items[:20]:  # Limit to first 20 series
            cb = QCheckBox(col)
            cb.setChecked(True)
            cb.toggled.connect(lambda checked, p=plot_item: p.setVisible(checked))
            cb.setStyleSheet("color: #f0f0f0;")
            self.legend_widget.layout().addWidget(cb)
            self.series_checkboxes[col] = cb
        
        if len(self.plot_items) > 20:
            note = QLabel(f"... and {len(self.plot_items) - 20} more")
            note.setStyleSheet("color: #888; font-style: italic;")
            self.legend_widget.layout().addWidget(note)
        
        self.plot_widget.autoRange()
        self.status_bar.showMessage(f"Showing {len(filtered_data)} rows, {len(self.plot_items)} series", 3000)
    
    def plot_group(self, group_data, group_name, color):
        if not group_data or not self.x_column or not self.y_columns:
            return
        
        x_vals = []
        for row in group_data:
            try:
                val = float(row.get(self.x_column, np.nan))
                if not np.isnan(val):
                    x_vals.append(val)
            except (ValueError, TypeError):
                x_vals.append(np.nan)
        
        for y_col in self.y_columns:
            y_vals = []
            valid_indices = []
            for i, row in enumerate(group_data):
                try:
                    val = float(row.get(y_col, np.nan))
                    if not np.isnan(val) and not np.isnan(x_vals[i]):
                        y_vals.append(val)
                        valid_indices.append(i)
                except (ValueError, TypeError):
                    pass
            
            if y_vals:
                valid_x = [x_vals[i] for i in valid_indices]
                plot_name = f"{group_name} - {y_col}" if group_name != "All Data" else y_col
                
                # Sort by x for better line plots
                sorted_indices = np.argsort(valid_x)
                sorted_x = [valid_x[i] for i in sorted_indices]
                sorted_y = [y_vals[i] for i in sorted_indices]
                
                # Use different styles based on data size
                if len(sorted_x) > 100:
                    # For large datasets, use line only
                    pen = pg.mkPen(color=color, width=1.5)
                    plot_item = self.plot_widget.plot(sorted_x, sorted_y, 
                                                     pen=pen, 
                                                     name=plot_name)
                elif len(sorted_x) > 20:
                    # For medium datasets, use line with dots
                    pen = pg.mkPen(color=color, width=1.5)
                    plot_item = self.plot_widget.plot(sorted_x, sorted_y, 
                                                     pen=pen, 
                                                     symbol='o',
                                                     symbolBrush=color,
                                                     symbolSize=4,
                                                     name=plot_name)
                else:
                    # For small datasets, use dots only
                    plot_item = self.plot_widget.plot(sorted_x, sorted_y, 
                                                     pen=None,
                                                     symbol='o',
                                                     symbolBrush=color,
                                                     symbolSize=6,
                                                     name=plot_name)
                
                self.plot_items.append((plot_name, plot_item))
    
    def export_plot(self):
        if not self.plot_items:
            QMessageBox.warning(self, "Warning", "No plot to export")
            return
        
        fname, _ = QFileDialog.getSaveFileName(
            self, "Export Plot", str(Path.home() / "plot.png"),
            "PNG Images (*.png);;All files (*.*)"
        )
        
        if fname:
            try:
                # Ensure file has .png extension
                if not fname.lower().endswith('.png'):
                    fname += '.png'
                
                exporter = pg.exporters.ImageExporter(self.plot_widget.plotItem)
                exporter.parameters()['width'] = 1920
                exporter.export(fname)
                self.status_bar.showMessage(f"Plot exported to {fname}", 3000)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to export: {e}")

def main():
    if len(sys.argv) < 2:
        print("Usage: python plotter.py <csv_file>")
        print("\nExample:")
        print("  python plotter.py historic.csv")
        return
    
    filename = sys.argv[1]
    
    try:
        app = QApplication(sys.argv)
        
        # Set dark theme
        app.setStyle('Fusion')
        dark_palette = QPalette()
        dark_palette.setColor(QPalette.Window, QColor(53, 53, 53))
        dark_palette.setColor(QPalette.WindowText, Qt.white)
        dark_palette.setColor(QPalette.Base, QColor(25, 25, 25))
        dark_palette.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
        dark_palette.setColor(QPalette.ToolTipBase, Qt.white)
        dark_palette.setColor(QPalette.ToolTipText, Qt.white)
        dark_palette.setColor(QPalette.Text, Qt.white)
        dark_palette.setColor(QPalette.Button, QColor(53, 53, 53))
        dark_palette.setColor(QPalette.ButtonText, Qt.white)
        dark_palette.setColor(QPalette.BrightText, Qt.red)
        dark_palette.setColor(QPalette.Link, QColor(42, 130, 218))
        dark_palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
        dark_palette.setColor(QPalette.HighlightedText, Qt.black)
        app.setPalette(dark_palette)
        
        window = DataPlotter(filename)
        window.show()
        sys.exit(app.exec_())
        
    except FileNotFoundError:
        print(f"Error: File '{filename}' not found.")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
