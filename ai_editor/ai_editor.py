# pipenv install; pipenv run pip install PyQt5 pyqtgraph
# pipenv run python3 ai_editor
"""
Car File Explorer - Recursively search and display .car files
Usage: python3 car_explorer.py <path>
"""

import sys
import os
from pathlib import Path
from typing import List, Optional
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
import pyqtgraph as pg
from dataclasses import dataclass
from datetime import datetime

@dataclass
class CarFile:
    """Represents a .car file found in the search"""
    path: str
    filename: str
    size: int
    modified: float
    directory: str
    
    @property
    def size_str(self) -> str:
        """Convert size to human readable format"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if self.size < 1024.0:
                return f"{self.size:.1f} {unit}"
            self.size /= 1024.0
        return f"{self.size:.1f} TB"
    
    @property
    def modified_str(self) -> str:
        """Convert modified time to string"""
        return datetime.fromtimestamp(self.modified).strftime("%Y-%m-%d %H:%M:%S")
    
    @property
    def parent_dir(self) -> str:
        """Get the parent directory name"""
        return os.path.basename(self.directory)

class SearchWorker(QThread):
    """Worker thread for searching files without freezing UI"""
    fileFound = pyqtSignal(str)  # Emit when a file is found
    searchFinished = pyqtSignal(list)  # Emit when search is complete
    progressUpdate = pyqtSignal(int, int)  # Current, Total
    
    def __init__(self, root_path: str):
        super().__init__()
        self.root_path = root_path
        self.is_running = True
        
    def run(self):
        """Perform the recursive search"""
        car_files = []
        total_files = 0
        processed = 0
        
        # First count total files for progress
        for root, dirs, files in os.walk(self.root_path):
            total_files += len([f for f in files if f.lower().endswith('.car')])
        
        # Now search
        for root, dirs, files in os.walk(self.root_path):
            if not self.is_running:
                break
                
            for file in files:
                if not self.is_running:
                    break
                    
                if file.lower().endswith('.car'):
                    full_path = os.path.join(root, file)
                    try:
                        stat = os.stat(full_path)
                        car_file = CarFile(
                            path=full_path,
                            filename=file,
                            size=stat.st_size,
                            modified=stat.st_mtime,
                            directory=root
                        )
                        car_files.append(car_file)
                        self.fileFound.emit(full_path)
                    except (OSError, PermissionError):
                        # Skip files we can't access
                        pass
                
                processed += 1
                self.progressUpdate.emit(processed, total_files)
        
        self.searchFinished.emit(car_files)
    
    def stop(self):
        """Stop the search"""
        self.is_running = False

class CarFileModel(QAbstractListModel):
    """Model for displaying car files"""
    
    def __init__(self):
        super().__init__()
        self.car_files: List[CarFile] = []
        self.filtered_files: List[CarFile] = []
        self.filter_text = ""
        self.sort_column = 0  # Default sort by filename
        self.sort_order = Qt.AscendingOrder
        
    def rowCount(self, parent=QModelIndex()):
        return len(self.filtered_files)
    
    def columnCount(self, parent=QModelIndex()):
        return 4  # Filename, Directory, Size, Modified
    
    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid() or index.row() >= len(self.filtered_files):
            return QVariant()
        
        car_file = self.filtered_files[index.row()]
        col = index.column()
        
        if role == Qt.DisplayRole:
            if col == 0:
                return car_file.filename
            elif col == 1:
                return car_file.parent_dir
            elif col == 2:
                return car_file.size_str
            elif col == 3:
                return car_file.modified_str
        
        elif role == Qt.UserRole:
            return car_file.path  # Store full path for tooltips/actions
        
        elif role == Qt.ToolTipRole:
            return f"Path: {car_file.path}\nSize: {car_file.size_str}\nModified: {car_file.modified_str}"
        
        elif role == Qt.ForegroundRole:
            # Color code by file age or other criteria
            if col == 0:
                # Newer files in green, older in gray
                age_days = (datetime.now().timestamp() - car_file.modified) / (24 * 3600)
                if age_days < 7:
                    return QBrush(QColor(76, 175, 80))  # Green for recent
                elif age_days > 30:
                    return QBrush(QColor(150, 150, 150))  # Gray for old
            elif col == 2:  # Size column
                if car_file.size > 1024 * 1024:  # > 1MB
                    return QBrush(QColor(255, 165, 0))  # Orange for large files
        
        return QVariant()
    
    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            headers = ['Filename', 'Directory', 'Size', 'Modified']
            return headers[section]
        return QVariant()
    
    def sort(self, column, order=Qt.AscendingOrder):
        """Sort the filtered files"""
        self.sort_column = column
        self.sort_order = order
        
        def sort_key(file):
            if column == 0:
                return file.filename.lower()
            elif column == 1:
                return file.parent_dir.lower()
            elif column == 2:
                return file.size
            elif column == 3:
                return file.modified
        
        self.filtered_files.sort(key=sort_key, reverse=(order == Qt.DescendingOrder))
        self.layoutChanged.emit()
    
    def filter(self, text: str):
        """Filter files by text"""
        self.filter_text = text.lower()
        self.update_filter()
    
    def update_filter(self):
        """Update the filtered list based on current filter text"""
        if not self.filter_text:
            self.filtered_files = self.car_files.copy()
        else:
            self.filtered_files = [
                f for f in self.car_files
                if self.filter_text in f.filename.lower() 
                or self.filter_text in f.parent_dir.lower()
                or self.filter_text in f.directory.lower()
            ]
        
        # Re-apply current sort
        self.sort(self.sort_column, self.sort_order)
    
    def set_files(self, files: List[CarFile]):
        """Set the list of car files"""
        self.car_files = files
        self.update_filter()

class StatisticsWidget(QWidget):
    """Widget for displaying search statistics and charts"""
    
    def __init__(self):
        super().__init__()
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Stats display
        stats_group = QGroupBox("Search Statistics")
        stats_layout = QGridLayout()
        
        self.total_files_label = QLabel("0")
        self.total_files_label.setStyleSheet("font-size: 20px; font-weight: bold; color: #4CAF50;")
        stats_layout.addWidget(QLabel("Total .car files:"), 0, 0)
        stats_layout.addWidget(self.total_files_label, 0, 1)
        
        self.total_size_label = QLabel("0 B")
        self.total_size_label.setStyleSheet("font-size: 20px; font-weight: bold; color: #2196F3;")
        stats_layout.addWidget(QLabel("Total size:"), 1, 0)
        stats_layout.addWidget(self.total_size_label, 1, 1)
        
        self.avg_size_label = QLabel("0 B")
        stats_layout.addWidget(QLabel("Average size:"), 2, 0)
        stats_layout.addWidget(self.avg_size_label, 2, 1)
        
        self.directory_count_label = QLabel("0")
        stats_layout.addWidget(QLabel("Directories:"), 3, 0)
        stats_layout.addWidget(self.directory_count_label, 3, 1)
        
        stats_group.setLayout(stats_layout)
        layout.addWidget(stats_group)
        
        # Chart widget
        self.plot_widget = pg.PlotWidget(title="File Size Distribution")
        self.plot_widget.setLabel('bottom', 'File Size (MB)')
        self.plot_widget.setLabel('left', 'Count')
        self.plot_widget.showGrid(x=True, y=True, alpha=0.3)
        layout.addWidget(self.plot_widget, 1)
        
        self.setLayout(layout)
    
    def update_stats(self, files: List[CarFile]):
        """Update statistics with current file list"""
        if not files:
            return
        
        total_size = sum(f.size for f in files)
        avg_size = total_size / len(files)
        directories = len(set(f.directory for f in files))
        
        # Format sizes
        def format_size(size):
            for unit in ['B', 'KB', 'MB', 'GB']:
                if size < 1024.0:
                    return f"{size:.1f} {unit}"
                size /= 1024.0
            return f"{size:.1f} TB"
        
        self.total_files_label.setText(str(len(files)))
        self.total_size_label.setText(format_size(total_size))
        self.avg_size_label.setText(format_size(avg_size))
        self.directory_count_label.setText(str(directories))
        
        # Create histogram of file sizes (in MB)
        sizes_mb = [f.size / (1024 * 1024) for f in files]  # Convert to MB
        
        # Create histogram bins
        if sizes_mb:
            max_size = max(sizes_mb)
            bins = np.linspace(0, max_size, 20)
            counts, edges = np.histogram(sizes_mb, bins=bins)
            
            # Clear and redraw
            self.plot_widget.clear()
            
            # Create bar graph
            x_centers = (edges[:-1] + edges[1:]) / 2
            bar_width = (edges[1] - edges[0]) * 0.8
            
            bg = pg.BarGraphItem(
                x=x_centers, 
                height=counts, 
                width=bar_width,
                brush='g',
                pen='w'
            )
            self.plot_widget.addItem(bg)

class MainWindow(QMainWindow):
    def __init__(self, search_path: str):
        super().__init__()
        self.search_path = os.path.abspath(search_path)
        self.search_worker = None
        self.car_files: List[CarFile] = []
        self.setup_ui()
        self.start_search()
    
    def setup_ui(self):
        self.setWindowTitle(f"Car File Explorer - {self.search_path}")
        self.setGeometry(100, 100, 1400, 800)
        
        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(5, 5, 5, 5)
        
        # Top toolbar
        toolbar = QToolBar()
        self.addToolBar(toolbar)
        
        # Search path display
        path_label = QLabel(f"📁 {self.search_path}")
        path_label.setStyleSheet("""
            QLabel {
                background-color: #3c3c3c;
                padding: 5px 10px;
                border-radius: 3px;
                font-family: monospace;
                color: #4CAF50;
            }
        """)
        toolbar.addWidget(path_label)
        
        toolbar.addSeparator()
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximumWidth(200)
        self.progress_bar.setVisible(False)
        toolbar.addWidget(self.progress_bar)
        
        toolbar.addSeparator()
        
        # Stop button
        self.stop_btn = QPushButton("⏹ Stop")
        self.stop_btn.clicked.connect(self.stop_search)
        self.stop_btn.setEnabled(False)
        toolbar.addWidget(self.stop_btn)
        
        # Refresh button
        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.clicked.connect(self.start_search)
        toolbar.addWidget(refresh_btn)
        
        # Export button
        export_btn = QPushButton("💾 Export List")
        export_btn.clicked.connect(self.export_file_list)
        toolbar.addWidget(export_btn)
        
        toolbar.addSeparator()
        
        # Search/filter box
        toolbar.addWidget(QLabel("🔍 Filter:"))
        self.filter_box = QLineEdit()
        self.filter_box.setPlaceholderText("Type to filter files...")
        self.filter_box.setMaximumWidth(200)
        self.filter_box.textChanged.connect(self.filter_files)
        toolbar.addWidget(self.filter_box)
        
        # Status label
        self.status_label = QLabel("Ready")
        toolbar.addWidget(self.status_label)
        
        # Main content splitter
        splitter = QSplitter(Qt.Horizontal)
        
        # Left side - File list
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        # File count label
        self.file_count_label = QLabel("Found 0 .car files")
        self.file_count_label.setStyleSheet("""
            QLabel {
                background-color: #3c3c3c;
                padding: 5px;
                border-radius: 3px;
                font-weight: bold;
            }
        """)
        left_layout.addWidget(self.file_count_label)
        
        # File list view
        self.file_view = QTableView()
        self.file_view.setSelectionBehavior(QTableView.SelectRows)
        self.file_view.setAlternatingRowColors(True)
        self.file_view.setSortingEnabled(True)
        self.file_view.verticalHeader().setVisible(False)
        self.file_view.horizontalHeader().setStretchLastSection(True)
        self.file_view.setEditTriggers(QTableView.NoEditTriggers)
        self.file_view.doubleClicked.connect(self.open_car_file)
        
        # Set model
        self.model = CarFileModel()
        self.file_view.setModel(self.model)
        
        # Set column widths
        self.file_view.setColumnWidth(0, 250)  # Filename
        self.file_view.setColumnWidth(1, 150)  # Directory
        self.file_view.setColumnWidth(2, 80)   # Size
        self.file_view.setColumnWidth(3, 150)  # Modified
        
        left_layout.addWidget(self.file_view)
        
        # Right side - Statistics
        self.stats_widget = StatisticsWidget()
        
        # Add widgets to splitter
        splitter.addWidget(left_widget)
        splitter.addWidget(self.stats_widget)
        splitter.setSizes([800, 600])
        
        main_layout.addWidget(splitter)
        
        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready to search")
    
    def start_search(self):
        """Start the recursive search"""
        if not os.path.exists(self.search_path):
            QMessageBox.critical(self, "Error", f"Path does not exist: {self.search_path}")
            return
        
        # Clear existing data
        self.car_files = []
        self.model.set_files([])
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(True)
        self.stop_btn.setEnabled(True)
        
        # Create and start worker thread
        self.search_worker = SearchWorker(self.search_path)
        self.search_worker.fileFound.connect(self.on_file_found)
        self.search_worker.searchFinished.connect(self.on_search_finished)
        self.search_worker.progressUpdate.connect(self.on_progress_update)
        self.search_worker.start()
        
        self.status_bar.showMessage("Searching...")
    
    def stop_search(self):
        """Stop the current search"""
        if self.search_worker:
            self.search_worker.stop()
            self.stop_btn.setEnabled(False)
            self.status_bar.showMessage("Search stopped")
    
    def on_file_found(self, file_path: str):
        """Called when a file is found"""
        # File is added directly to the list via search_finished
        pass
    
    def on_progress_update(self, current: int, total: int):
        """Update progress bar"""
        if total > 0:
            self.progress_bar.setMaximum(total)
            self.progress_bar.setValue(current)
    
    def on_search_finished(self, files: List[CarFile]):
        """Called when search is complete"""
        self.car_files = files
        self.model.set_files(files)
        self.stats_widget.update_stats(files)
        
        self.progress_bar.setVisible(False)
        self.stop_btn.setEnabled(False)
        
        # Update labels
        self.file_count_label.setText(f"Found {len(files)} .car files")
        self.status_bar.showMessage(f"Search complete. Found {len(files)} .car files")
        
        # Clean up worker
        if self.search_worker:
            self.search_worker.deleteLater()
            self.search_worker = None
    
    def filter_files(self, text: str):
        """Filter the file list"""
        self.model.filter(text)
        self.file_count_label.setText(f"Showing {len(self.model.filtered_files)} of {len(self.car_files)} .car files")
    
    def open_car_file(self, index: QModelIndex):
        """Open the selected car file"""
        if index.isValid():
            file_path = self.model.filtered_files[index.row()].path
            self.status_bar.showMessage(f"Opening: {file_path}")
            
            # Here you could launch your car file editor
            # For now, just show a message
            QMessageBox.information(self, "Open File", 
                f"Would open car file:\n{file_path}\n\n"
                f"(Integrate with your car file editor here)")
    
    def export_file_list(self):
        """Export the list of files to a text file"""
        if not self.car_files:
            QMessageBox.warning(self, "No Files", "No files to export")
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, 
            "Export File List",
            "car_files_list.txt",
            "Text Files (*.txt);;CSV Files (*.csv)"
        )
        
        if file_path:
            try:
                with open(file_path, 'w') as f:
                    if file_path.endswith('.csv'):
                        # CSV format
                        f.write("Filename,Directory,Size (bytes),Modified,Full Path\n")
                        for car_file in self.car_files:
                            f.write(f'"{car_file.filename}","{car_file.directory}",{car_file.size},"{car_file.modified_str}","{car_file.path}"\n')
                    else:
                        # Text format
                        f.write(f"Car Files found in: {self.search_path}\n")
                        f.write(f"Total: {len(self.car_files)} files\n")
                        f.write("=" * 80 + "\n\n")
                        
                        for car_file in sorted(self.car_files, key=lambda x: x.filename):
                            f.write(f"File: {car_file.filename}\n")
                            f.write(f"Path: {car_file.directory}\n")
                            f.write(f"Size: {car_file.size_str}\n")
                            f.write(f"Modified: {car_file.modified_str}\n")
                            f.write("-" * 40 + "\n")
                
                self.status_bar.showMessage(f"Exported to: {file_path}")
                QMessageBox.information(self, "Success", f"Exported {len(self.car_files)} files to:\n{file_path}")
                
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to export: {str(e)}")

def main():
    if len(sys.argv) != 2:
        print("Usage: python3 car_explorer.py <path>")
        print("\nSearches recursively for .car files in the given path")
        sys.exit(1)
    
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    # Set dark theme (matching the torque editor style)
    app.setStyleSheet("""
        QMainWindow, QDialog {
            background-color: #2b2b2b;
        }
        QToolBar {
            background-color: #3c3c3c;
            border: none;
            spacing: 5px;
            padding: 3px;
        }
        QToolBar::separator {
            width: 1px;
            background: #555;
            margin: 5px;
        }
        QGroupBox {
            color: #ffffff;
            border: 1px solid #555;
            border-radius: 5px;
            margin-top: 1ex;
            font-weight: normal;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 5px 0 5px;
            color: #4CAF50;
        }
        QLabel {
            color: #ffffff;
        }
        QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {
            background-color: #3c3c3c;
            color: #ffffff;
            border: 1px solid #555;
            border-radius: 3px;
            padding: 4px;
            selection-background-color: #4CAF50;
        }
        QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {
            border: 1px solid #4CAF50;
        }
        QTableView {
            background-color: #2b2b2b;
            color: #ffffff;
            border: 1px solid #555;
            gridline-color: #3c3c3c;
            outline: none;
        }
        QTableView::item {
            padding: 5px;
            border-bottom: 1px solid #3c3c3c;
        }
        QTableView::item:selected {
            background-color: #4CAF50;
            color: white;
        }
        QTableView::item:alternate {
            background-color: #333333;
        }
        QTableView::item:hover {
            background-color: #3c3c3c;
        }
        QHeaderView::section {
            background-color: #3c3c3c;
            color: #ffffff;
            padding: 5px;
            border: 1px solid #555;
            font-weight: bold;
        }
        QHeaderView::section:hover {
            background-color: #4c4c4c;
        }
        QPushButton {
            background-color: #3c3c3c;
            color: white;
            border: 1px solid #555;
            border-radius: 3px;
            padding: 5px 10px;
        }
        QPushButton:hover {
            background-color: #4c4c4c;
            border: 1px solid #4CAF50;
        }
        QPushButton:pressed {
            background-color: #2c2c2c;
        }
        QPushButton:disabled {
            background-color: #2b2b2b;
            color: #666;
        }
        QProgressBar {
            border: 1px solid #555;
            border-radius: 3px;
            text-align: center;
            color: white;
        }
        QProgressBar::chunk {
            background-color: #4CAF50;
            border-radius: 3px;
        }
        QStatusBar {
            color: #ffffff;
            background-color: #3c3c3c;
            border-top: 1px solid #555;
        }
        QScrollBar:vertical {
            background-color: #2b2b2b;
            width: 12px;
            border-radius: 6px;
        }
        QScrollBar::handle:vertical {
            background-color: #555;
            border-radius: 6px;
            min-height: 20px;
        }
        QScrollBar::handle:vertical:hover {
            background-color: #4CAF50;
        }
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
            border: none;
            background: none;
        }
    """)
    
    window = MainWindow(sys.argv[1])
    window.show()
    
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
