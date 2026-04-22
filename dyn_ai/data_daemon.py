#!/usr/bin/env python3
"""
File monitoring daemon for raceresults.txt
Checks for changes every N seconds and shows popup when changes are detected
"""

import sys
import time
import threading
from pathlib import Path
from datetime import datetime
from typing import Optional, Callable

from PyQt5.QtWidgets import QApplication, QMessageBox, QSystemTrayIcon, QMenu, QWidget
from PyQt5.QtCore import QTimer, pyqtSignal, QObject
from PyQt5.QtGui import QIcon

from cfg_funcs import get_results_file_path, get_poll_interval, get_config_with_defaults


class FileChangeSignal(QObject):
    """Signal for thread-safe GUI updates"""
    file_changed = pyqtSignal(str, str)  # filename, timestamp


class FileMonitorDaemon(QObject):
    """Daemon that monitors a file for changes"""
    
    def __init__(self, file_path: Path, poll_interval: float = 5.0):
        super().__init__()
        self.file_path = file_path
        self.poll_interval = poll_interval
        self.running = False
        self.last_mtime = None
        self.last_size = None
        self.timer = None
        self.signal = FileChangeSignal()
        
    def start(self):
        """Start monitoring"""
        if not self.file_path.exists():
            print(f"Warning: File does not exist yet: {self.file_path}")
            # Create parent directories if needed
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
        """Check if file has changed"""
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
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                self.signal.file_changed.emit(str(self.file_path), timestamp)
                self.last_mtime = current_mtime
                self.last_size = current_size
            
        except Exception as e:
            print(f"Error checking file: {e}")
        finally:
            self._schedule_check()


class FileChangePopup(QWidget):
    """Popup window for file change notifications"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("File Change Detected")
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.Dialog)
        self.setMinimumWidth(400)
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the popup UI"""
        self.setStyleSheet("""
            QWidget {
                background-color: #2b2b2b;
            }
            QLabel {
                color: white;
                font-size: 12px;
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
        icon_label = QLabel("📁")
        icon_label.setStyleSheet("font-size: 24px;")
        title_layout.addWidget(icon_label)
        
        title_text = QLabel("File Change Detected!")
        title_text.setStyleSheet("font-size: 16px; font-weight: bold; color: #FFA500;")
        title_layout.addWidget(title_text)
        title_layout.addStretch()
        layout.addLayout(title_layout)
        
        layout.addSpacing(10)
        
        # File info
        self.file_label = QLabel()
        self.file_label.setWordWrap(True)
        self.file_label.setStyleSheet("color: #4CAF50; font-family: monospace;")
        layout.addWidget(self.file_label)
        
        # Timestamp
        self.time_label = QLabel()
        self.time_label.setStyleSheet("color: #888; font-size: 10px;")
        layout.addWidget(self.time_label)
        
        layout.addSpacing(10)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        open_btn = QPushButton("Open File")
        open_btn.clicked.connect(self.open_file)
        button_layout.addWidget(open_btn)
        
        ok_btn = QPushButton("OK")
        ok_btn.clicked.connect(self.close)
        button_layout.addWidget(ok_btn)
        
        layout.addLayout(button_layout)
        
        # Auto-close timer (5 seconds)
        self.close_timer = QTimer()
        self.close_timer.setSingleShot(True)
        self.close_timer.timeout.connect(self.close)
        
    def show_change(self, file_path: str, timestamp: str):
        """Show the change notification"""
        self.file_label.setText(f"File: {file_path}")
        self.time_label.setText(f"Time: {timestamp}")
        
        # Show window
        self.show()
        self.raise_()
        self.activateWindow()
        
        # Start auto-close timer
        self.close_timer.start(5000)
        
    def open_file(self):
        """Open the file with default application"""
        import subprocess
        import platform
        
        file_path = self.file_label.text().replace("File: ", "")
        if Path(file_path).exists():
            if platform.system() == "Windows":
                os.startfile(file_path)
            elif platform.system() == "Darwin":  # macOS
                subprocess.run(["open", file_path])
            else:  # Linux
                subprocess.run(["xdg-open", file_path])
        self.close()


class SystemTrayIcon(QSystemTrayIcon):
    """System tray icon for the daemon"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the system tray icon"""
        # Create a simple icon (using a circle emoji as fallback)
        self.setIcon(QIcon())
        self.setToolTip("File Monitor Daemon")
        
        # Create context menu
        menu = QMenu()
        
        show_action = menu.addAction("Show Monitor")
        show_action.triggered.connect(self.show_monitor)
        
        menu.addSeparator()
        
        quit_action = menu.addAction("Quit")
        quit_action.triggered.connect(self.quit_app)
        
        self.setContextMenu(menu)
        self.show()
        
    def show_monitor(self):
        """Show the main monitor window"""
        if self.parent():
            self.parent().show()
            self.parent().raise_()
            
    def quit_app(self):
        """Quit the application"""
        QApplication.quit()


class FileMonitorApp(QWidget):
    """Main application for file monitoring"""
    
    def __init__(self, config_file: str = "cfg.yml"):
        super().__init__()
        self.config_file = config_file
        self.daemon = None
        self.popup = None
        self.setup_ui()
        self.start_monitoring()
        
    def setup_ui(self):
        """Setup the main window UI"""
        self.setWindowTitle("File Monitor Daemon")
        self.setGeometry(300, 300, 500, 300)
        
        self.setStyleSheet("""
            QWidget {
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
            QPushButton#stop {
                background-color: #f44336;
            }
            QPushButton#stop:hover {
                background-color: #d32f2f;
            }
        """)
        
        layout = QVBoxLayout(self)
        
        # Title
        title = QLabel("File Monitor Daemon")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #FFA500;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        layout.addSpacing(10)
        
        # Status group
        status_group = QGroupBox("Status")
        status_layout = QVBoxLayout(status_group)
        
        self.status_label = QLabel("● Stopped")
        self.status_label.setStyleSheet("color: #f44336; font-weight: bold;")
        status_layout.addWidget(self.status_label)
        
        self.file_label = QLabel("File: Not loaded")
        self.file_label.setWordWrap(True)
        self.file_label.setStyleSheet("color: #888; font-family: monospace; font-size: 10px;")
        status_layout.addWidget(self.file_label)
        
        self.interval_label = QLabel("Poll interval: -- s")
        self.interval_label.setStyleSheet("color: #888;")
        status_layout.addWidget(self.interval_label)
        
        layout.addWidget(status_group)
        
        # Stats group
        stats_group = QGroupBox("Statistics")
        stats_layout = QVBoxLayout(stats_group)
        
        self.changes_label = QLabel("Changes detected: 0")
        stats_layout.addWidget(self.changes_label)
        
        self.last_change_label = QLabel("Last change: Never")
        stats_layout.addWidget(self.last_change_label)
        
        layout.addWidget(stats_group)
        
        layout.addSpacing(10)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.start_btn = QPushButton("Start Monitoring")
        self.start_btn.clicked.connect(self.start_monitoring)
        button_layout.addWidget(self.start_btn)
        
        self.stop_btn = QPushButton("Stop Monitoring")
        self.stop_btn.setObjectName("stop")
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self.stop_monitoring)
        button_layout.addWidget(self.stop_btn)
        
        layout.addLayout(button_layout)
        
        # Test button
        test_btn = QPushButton("Test Popup")
        test_btn.setStyleSheet("background-color: #2196F3;")
        test_btn.clicked.connect(self.test_popup)
        layout.addWidget(test_btn)
        
        layout.addStretch()
        
        # Status bar
        self.status_bar = self.statusBar() if hasattr(self, 'statusBar') else None
        
        self.change_count = 0
        self.last_change_time = None
        
    def start_monitoring(self):
        """Start the file monitoring daemon"""
        # Load config
        config = get_config_with_defaults(self.config_file)
        
        # Get file path
        file_path = get_results_file_path(self.config_file)
        if not file_path:
            self.status_label.setText("⚠ No base path configured")
            self.status_label.setStyleSheet("color: #FFA500; font-weight: bold;")
            return
        
        # Get poll interval
        poll_interval = get_poll_interval(self.config_file)
        
        # Create daemon
        self.daemon = FileMonitorDaemon(file_path, poll_interval)
        self.daemon.signal.file_changed.connect(self.on_file_changed)
        
        # Create popup
        self.popup = FileChangePopup(self)
        
        # Start daemon
        self.daemon.start()
        
        # Update UI
        self.status_label.setText("● Running")
        self.status_label.setStyleSheet("color: #4CAF50; font-weight: bold;")
        self.file_label.setText(f"File: {file_path}")
        self.interval_label.setText(f"Poll interval: {poll_interval} seconds")
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        
        print(f"Monitoring started for: {file_path}")
        
    def stop_monitoring(self):
        """Stop the file monitoring daemon"""
        if self.daemon:
            self.daemon.stop()
            self.daemon = None
            
        self.status_label.setText("● Stopped")
        self.status_label.setStyleSheet("color: #f44336; font-weight: bold;")
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        
        print("Monitoring stopped")
        
    def on_file_changed(self, file_path: str, timestamp: str):
        """Handle file change event"""
        self.change_count += 1
        self.last_change_time = timestamp
        
        # Update stats
        self.changes_label.setText(f"Changes detected: {self.change_count}")
        self.last_change_label.setText(f"Last change: {timestamp}")
        
        # Show popup
        if self.popup:
            self.popup.show_change(file_path, timestamp)
        
        # Also print to console
        print(f"\n{'='*60}")
        print(f"FILE CHANGE DETECTED!")
        print(f"  File: {file_path}")
        print(f"  Time: {timestamp}")
        print(f"  Total changes: {self.change_count}")
        print(f"{'='*60}\n")
        
        # Bring window to front
        self.show()
        self.raise_()
        self.activateWindow()
        
    def test_popup(self):
        """Test the popup notification"""
        if self.popup:
            self.popup.show_change("test_file.txt", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            
    def closeEvent(self, event):
        """Handle close event"""
        self.stop_monitoring()
        event.accept()


def run_daemon():
    """Run the file monitor daemon"""
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    # Create system tray icon
    tray = SystemTrayIcon()
    
    # Create main window
    window = FileMonitorApp()
    window.show()
    
    sys.exit(app.exec_())


if __name__ == "__main__":
    run_daemon()
