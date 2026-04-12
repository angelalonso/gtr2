#!/usr/bin/env python3
"""
Simple Curve Viewer - Uses minimal SQLite database
Displays hyperbolic curve T = a/R + b with data points from database
Includes file monitoring daemon for raceresults.txt (runs silently in background)
"""

import sys
import threading
from pathlib import Path
from typing import List, Tuple, Optional

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout, QSplitter,
    QLabel, QTextEdit, QPushButton, QVBoxLayout
)
from PyQt5.QtCore import Qt, pyqtSignal, QObject, QTimer

from db_funcs import CurveDatabase
from formula_funcs import (
    get_curve_points, fit_curve, 
    calculate_derived_values, get_formula_string
)
from gui_funcs import (
    create_control_panel, create_plot_widget, update_plot, reset_plot_view,
    setup_dark_theme, show_error_dialog, show_info_dialog, show_warning_dialog
)
from cfg_funcs import (
    get_config_with_defaults, get_results_file_path, get_poll_interval,
    get_db_path, create_default_config_if_missing, get_base_path
)
from data_extraction import DataExtractor, RaceData, get_display_text


class FileChangeSignal(QObject):
    """Signal for thread-safe GUI updates"""
    file_changed = pyqtSignal(object)  # RaceData object


class FileMonitorDaemon(QObject):
    """Daemon that monitors a file for changes and extracts data"""
    
    def __init__(self, file_path: Path, base_path: Path, poll_interval: float = 5.0):
        super().__init__()
        self.file_path = file_path
        self.base_path = base_path
        self.poll_interval = poll_interval
        self.running = False
        self.last_mtime = None
        self.last_size = None
        self.timer = None
        self.signal = FileChangeSignal()
        self.extractor = DataExtractor(base_path)
        
    def start(self):
        """Start monitoring"""
        if not self.file_path.exists():
            print(f"Warning: File does not exist yet: {self.file_path}")
            self.file_path.parent.mkdir(parents=True, exist_ok=True)
        
        self._update_file_state()
        self.running = True
        self._schedule_check()
        print(f"Started monitoring: {self.file_path}")
        print(f"Poll interval: {self.poll_interval} seconds")
        
    def stop(self):
        """Stop monitoring"""
        self.running = False
        if self.timer:
            self.timer.cancel()
        print("Stopped monitoring")
    
    def _schedule_check(self):
        """Schedule the next file check"""
        if self.running:
            self.timer = threading.Timer(self.poll_interval, self._check_file)
            self.timer.daemon = True
            self.timer.start()
    
    def _update_file_state(self):
        """Update stored file state"""
        try:
            if self.file_path.exists():
                stat = self.file_path.stat()
                self.last_mtime = stat.st_mtime
                self.last_size = stat.st_size
        except Exception:
            pass
    
    def _check_file(self):
        """Check if file has changed and extract data"""
        try:
            if not self.running:
                return
            
            if not self.file_path.exists():
                self._schedule_check()
                return
            
            try:
                stat = self.file_path.stat()
                current_mtime = stat.st_mtime
                current_size = stat.st_size
            except OSError:
                self._schedule_check()
                return
            
            changed = (
                self.last_mtime is None
                or current_mtime != self.last_mtime
                or current_size != self.last_size
            )
            
            if changed:
                # Extract data from the file
                race_data = self.extractor.parse_race_results(self.file_path)
                
                if race_data and race_data.has_data():
                    self.signal.file_changed.emit(race_data)
                else:
                    # Still emit but with empty data to show file changed
                    self.signal.file_changed.emit(None)
                
                self.last_mtime = current_mtime
                self.last_size = current_size
            
        except Exception as e:
            print(f"Error checking file: {e}")
        finally:
            self._schedule_check()


class FileChangePopup(QWidget):
    """Popup window for file change notifications with race data"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Race Results Detected")
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.Dialog)
        self.setMinimumWidth(500)
        self.setMinimumHeight(400)
        self.current_data = None
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the popup UI"""
        self.setStyleSheet("""
            QWidget {
                background-color: #2b2b2b;
                border-radius: 8px;
            }
            QLabel {
                color: white;
                font-size: 12px;
            }
            QTextEdit {
                background-color: #1e1e1e;
                color: #4CAF50;
                border: 1px solid #4CAF50;
                border-radius: 4px;
                font-family: monospace;
                font-size: 11px;
            }
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        
        layout = QVBoxLayout(self)
        
        # Icon and title
        title_layout = QHBoxLayout()
        icon_label = QLabel("🏁")
        icon_label.setStyleSheet("font-size: 28px;")
        title_layout.addWidget(icon_label)
        
        title_text = QLabel("RACE RESULTS DETECTED!")
        title_text.setStyleSheet("font-size: 16px; font-weight: bold; color: #FFA500;")
        title_layout.addWidget(title_text)
        title_layout.addStretch()
        layout.addLayout(title_layout)
        
        layout.addSpacing(10)
        
        # Data display area
        self.data_text = QTextEdit()
        self.data_text.setReadOnly(True)
        self.data_text.setMaximumHeight(300)
        layout.addWidget(self.data_text)
        
        layout.addSpacing(10)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        ok_btn = QPushButton("OK")
        ok_btn.clicked.connect(self.close)
        button_layout.addStretch()
        button_layout.addWidget(ok_btn)
        button_layout.addStretch()
        
        layout.addLayout(button_layout)
        
        # Auto-close timer (10 seconds)
        self.close_timer = QTimer()
        self.close_timer.setSingleShot(True)
        self.close_timer.timeout.connect(self.close)
        
    def show_change(self, race_data: RaceData):
        """Show the change notification with race data"""
        self.current_data = race_data
        
        if race_data:
            display_text = get_display_text(race_data)
            self.data_text.setText(display_text)
            self.setWindowTitle(f"Race Results - {race_data.track_name or 'Unknown Track'}")
        else:
            self.data_text.setText("File changed but no race data could be extracted.")
            self.setWindowTitle("File Change Detected")
        
        # Show window
        self.show()
        self.raise_()
        self.activateWindow()
        
        # Start auto-close timer
        self.close_timer.start(10000)


class SimpleCurveViewer(QMainWindow):
    """Lightweight GUI for viewing hyperbolic curves with simple SQLite storage"""
    
    def __init__(self, db_path: str = "ai_data.db", config_file: str = "cfg.yml"):
        super().__init__()
        self.setWindowTitle("Curve Viewer - T = a/R + b")
        self.setGeometry(100, 100, 1200, 700)
        
        # Config
        self.config_file = config_file
        self.config = get_config_with_defaults(config_file)
        
        # Database handler
        self.db = CurveDatabase(db_path)
        
        # Daemon
        self.daemon = None
        self.popup = None
        self.last_race_data = None
        
        # Current state
        self.current_a: float = 30.0
        self.current_b: float = 70.0
        
        # Filter state
        self.show_qualifying: bool = True
        self.show_race: bool = True
        self.show_unknown: bool = True
        
        # Cache for tracks and vehicles
        self.all_tracks: List[str] = []
        self.all_vehicles: List[str] = []
        
        self.setup_ui()
        self.load_data()
        self.update_display()
        
        # Auto-start daemon if base path is configured
        base_path = get_base_path(config_file)
        if base_path:
            self.start_daemon()
    
    def setup_ui(self):
        """Setup the user interface"""
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(5, 5, 5, 5)
        
        # Create control panel
        controls = create_control_panel(self)
        self.controls = controls
        
        # Store references to controls
        self.track_list = controls['track_list']
        self.vehicle_list = controls['vehicle_list']
        self.qual_btn = controls['qual_btn']
        self.race_btn = controls['race_btn']
        self.unkn_btn = controls['unkn_btn']
        self.a_spin = controls['a_spin']
        self.b_spin = controls['b_spin']
        self.k_label = controls['k_label']
        self.m_label = controls['m_label']
        self.stats_label = controls['stats_label']
        
        # Connect signals
        self.track_list.itemSelectionChanged.connect(self.on_selection_changed)
        self.vehicle_list.itemSelectionChanged.connect(self.on_selection_changed)
        self.qual_btn.clicked.connect(self.on_filter_buttons)
        self.race_btn.clicked.connect(self.on_filter_buttons)
        self.unkn_btn.clicked.connect(self.on_filter_buttons)
        self.a_spin.valueChanged.connect(self.on_param_changed)
        self.b_spin.valueChanged.connect(self.on_param_changed)
        controls['fit_btn'].clicked.connect(self.auto_fit)
        controls['reset_btn'].clicked.connect(self.reset_view)
        controls['exit_btn'].clicked.connect(self.close)
        controls['select_all_tracks'].clicked.connect(lambda: self.track_list.selectAll())
        controls['clear_tracks'].clicked.connect(lambda: self.track_list.clearSelection())
        controls['select_all_vehicles'].clicked.connect(lambda: self.vehicle_list.selectAll())
        controls['clear_vehicles'].clicked.connect(lambda: self.vehicle_list.clearSelection())
        
        # Create plot widget using pyqtgraph
        self.plot_data = create_plot_widget(self)
        
        # Splitter
        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(controls['panel'])
        splitter.addWidget(self.plot_data['widget'])
        splitter.setSizes([340, 860])
        main_layout.addWidget(splitter)
        
        # Create popup
        self.popup = FileChangePopup(self)
        
        # Update labels
        self._update_labels()
    
    def start_daemon(self):
        """Start the file monitoring daemon silently"""
        # Get file path from config
        file_path = get_results_file_path(self.config_file)
        if not file_path:
            print("No base path configured in cfg.yml - daemon not started")
            return
        
        # Get base path
        base_path = get_base_path(self.config_file)
        if not base_path:
            print("Base path not configured - daemon not started")
            return
        
        # Get poll interval
        poll_interval = get_poll_interval(self.config_file)
        
        # Create and start daemon
        self.daemon = FileMonitorDaemon(file_path, base_path, poll_interval)
        self.daemon.signal.file_changed.connect(self.on_file_changed)
        self.daemon.start()
        
        print(f"Daemon started silently - monitoring: {file_path}")
    
    def stop_daemon(self):
        """Stop the file monitoring daemon"""
        if self.daemon:
            self.daemon.stop()
            self.daemon = None
        print("Daemon stopped")
    
    def on_file_changed(self, race_data: RaceData):
        """Handle file change event from daemon - save to DB and update graph"""
        from datetime import datetime
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        if race_data:
            # Save to database
            print(f"\n{'='*60}")
            print(f"[{timestamp}] SAVING RACE DATA TO DATABASE")
            print(f"{'='*60}")
            
            # Save the race session
            race_dict = race_data.to_dict()
            race_id = self.db.save_race_session(race_dict)
            
            if race_id:
                print(f"✓ Race session saved with ID: {race_id}")
                
                # Add data points to curve database
                points_added = 0
                for track, ratio, lap_time, session_type in race_data.to_data_points():
                    # Use the user's vehicle or "Unknown" as the vehicle for the data point
                    vehicle = race_data.user_vehicle if race_data.user_vehicle else "Unknown"
                    if self.db.add_data_point(track, vehicle, ratio, lap_time, session_type):
                        points_added += 1
                        print(f"  ✓ Added {session_type} point: {track} R={ratio:.4f} T={lap_time:.3f}s")
                
                # Reload data to update the graph
                self.load_data()
                
                # Auto-select the track that was just detected
                if race_data.track_name and race_data.track_name in self.all_tracks:
                    # Find and select the track in the list
                    items = self.track_list.findItems(race_data.track_name, Qt.MatchExactly)
                    if items:
                        self.track_list.clearSelection()
                        items[0].setSelected(True)
                        # Also select all vehicles to show all data for this track
                        self.vehicle_list.selectAll()
                        print(f"✓ Auto-selected track: {race_data.track_name}")
                
                # Update the graph
                self.update_display()
                
                # Show popup with data
                if self.popup:
                    self.popup.show_change(race_data)
                
                print(f"\n✓ Graph updated with new data points")
            else:
                print(f"✗ Failed to save race session")
        else:
            print(f"\n[{timestamp}] File changed but no race data extracted")
    
    def load_data(self):
        """Load tracks and vehicles from database"""
        if not self.db.database_exists():
            print(f"Database not found: {self.db.db_path}")
            print("Run db_funcs.py first to import your data")
            return
        
        self.all_tracks = self.db.get_all_tracks()
        self.all_vehicles = self.db.get_all_vehicles()
        stats = self.db.get_stats()
        
        # Populate lists (preserve selection if possible)
        current_track = None
        if self.track_list.selectedItems():
            current_track = self.track_list.selectedItems()[0].text()
        
        self.track_list.clear()
        for track in self.all_tracks:
            self.track_list.addItem(track)
        
        self.vehicle_list.clear()
        for vehicle in self.all_vehicles:
            self.vehicle_list.addItem(vehicle)
        
        # Restore selection or select first track
        if current_track and current_track in self.all_tracks:
            items = self.track_list.findItems(current_track, Qt.MatchExactly)
            if items:
                items[0].setSelected(True)
        elif self.all_tracks:
            self.track_list.setCurrentRow(0)
        
        # Select all vehicles by default if nothing selected
        if not self.vehicle_list.selectedItems() and self.all_vehicles:
            self.vehicle_list.selectAll()
        
        # Update stats label
        type_str = ", ".join([f"{t}: {c}" for t, c in stats['by_type'].items()])
        self.stats_label.setText(f"Points: {stats['total_points']} | Races: {stats['total_races']}\n{type_str}")
        
        print(f"Loaded {stats['total_points']} points, {stats['total_races']} races from database")
        print(f"  Tracks: {stats['total_tracks']}")
        print(f"  Vehicles: {stats['total_vehicles']}")
    
    def get_selected_data(self) -> dict:
        """Get all data points from selected tracks and vehicles, filtered by type"""
        selected_tracks = [item.text() for item in self.track_list.selectedItems()]
        selected_vehicles = [item.text() for item in self.vehicle_list.selectedItems()]
        
        points = self.db.get_data_points(
            selected_tracks, 
            selected_vehicles,
            self.show_qualifying,
            self.show_race,
            self.show_unknown
        )
        
        # Organize by type
        result = {'quali': [], 'race': [], 'unknown': []}
        for ratio, lap_time, session_type in points:
            if session_type == 'qual':
                result['quali'].append((ratio, lap_time))
            elif session_type == 'race':
                result['race'].append((ratio, lap_time))
            else:
                result['unknown'].append((ratio, lap_time))
        
        return result
    
    def on_selection_changed(self):
        """Handle selection changes"""
        self.update_display()
    
    def on_filter_buttons(self):
        """Handle filter button toggles"""
        self.show_qualifying = self.qual_btn.isChecked()
        self.show_race = self.race_btn.isChecked()
        self.show_unknown = self.unkn_btn.isChecked()
        self.update_display()
    
    def on_param_changed(self):
        """Handle parameter changes"""
        self.current_a = self.a_spin.value()
        self.current_b = self.b_spin.value()
        self._update_labels()
        self.update_display()
    
    def _update_labels(self):
        """Update derived value labels"""
        M, k = calculate_derived_values(self.current_a, self.current_b)
        self.k_label.setText(f"Steepness k = a/(a+b) = {k:.4f}")
        self.m_label.setText(f"Time at R=1.0 = {M:.3f} s")
    
    def auto_fit(self):
        """Fit hyperbolic curve to selected data points"""
        points_data = self.get_selected_data()
        all_points = points_data['quali'] + points_data['race'] + points_data['unknown']
        
        if len(all_points) < 2:
            show_warning_dialog(self, "Insufficient Data", 
                               f"Need at least 2 data points to fit.\nCurrently have {len(all_points)} selected.\n\n"
                               f"Select more tracks/vehicles or add more data points.")
            return
        
        ratios = [p[0] for p in all_points]
        times = [p[1] for p in all_points]
        
        a, b, avg_error, max_error = fit_curve(ratios, times)
        
        if a is not None:
            self.a_spin.setValue(a)
            self.b_spin.setValue(b)
            
            show_info_dialog(self, "Fit Complete",
                           f"Fitted curve: {get_formula_string(a, b)}\n"
                           f"Data points used: {len(all_points)}\n"
                           f"Average error: {avg_error:.3f} seconds\n"
                           f"Max error: {max_error:.3f} seconds")
        else:
            show_error_dialog(self, "Fit Failed", "Could not fit curve to selected data points.")
    
    def update_display(self):
        """Update the plot"""
        points_data = self.get_selected_data()
        update_plot(self.plot_data, self.current_a, self.current_b, points_data)
        
        # Update status bar
        selected_tracks = len(self.track_list.selectedItems())
        selected_vehicles = len(self.vehicle_list.selectedItems())
        total_points = len(points_data['quali']) + len(points_data['race']) + len(points_data['unknown'])
        self.statusBar().showMessage(
            f"Tracks: {selected_tracks} | Vehicles: {selected_vehicles} | Data points: {total_points}"
        )
    
    def reset_view(self):
        """Reset the plot to default view"""
        reset_plot_view(self.plot_data)
    
    def closeEvent(self, event):
        """Handle close event - stop daemon"""
        self.stop_daemon()
        event.accept()


def main():
    # Create default config if missing
    create_default_config_if_missing()
    
    # Get database path from config
    db_path = get_db_path()
    
    # Check if database exists
    if not Path(db_path).exists():
        print(f"\n{'='*60}")
        print("DATABASE NOT FOUND")
        print(f"{'='*60}")
        print(f"\nDatabase '{db_path}' does not exist.")
        print("\nPlease run the importer first to migrate your existing data:")
        print("  python db_funcs.py")
        print(f"\n{'='*60}\n")
        
        response = input("Create an empty database and continue? (y/n): ").lower().strip()
        if response == 'y':
            from db_funcs import CurveDatabase
            CurveDatabase(db_path)
            print(f"\nCreated empty database: {db_path}\n")
        else:
            print("\nExiting. Run db_funcs.py first.\n")
            return
    
    app = QApplication(sys.argv)
    setup_dark_theme(app)
    
    window = SimpleCurveViewer(db_path)
    window.show()
    
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
