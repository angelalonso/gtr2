# pip install PyQt5 watchdog numpy scipy pyyaml
#!/usr/bin/env python3
"""
Live AI Tuner V2 - Automatic AI ratio adjustment based on race results
Combines file monitoring with AIW editing capabilities
"""

import sys
import argparse
import logging
from pathlib import Path
from datetime import datetime
import threading
import time

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

from cfg_manage import get_or_prompt_base_path
from file_monitor import FileMonitor

# Configure logging
log_filename = f"live_ai_tuner_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_filename, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class LiveAITuner:
    """Main application class coordinating all components"""
    
    def __init__(self, base_path: Path, no_gui: bool = False):
        self.base_path = Path(base_path)
        self.no_gui = no_gui
        self.monitor = None
        self.main_window = None
        self.running = True
        self.app = None  # Will hold QApplication if in GUI mode
        
        # Get monitor folder (UserData)
        self.monitor_folder = self.base_path / 'UserData'
        self.target_file = self.monitor_folder / 'Log' / 'Results' / 'raceresults.txt'
        
        # Ensure directories exist
        self.monitor_folder.mkdir(parents=True, exist_ok=True)
        (self.monitor_folder / 'Log' / 'Results').mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Base path: {self.base_path}")
        logger.info(f"Monitor folder: {self.monitor_folder}")
        logger.info(f"Target file: {self.target_file}")
    
    def start(self):
        """Start the application"""
        if self.no_gui:
            self._run_console()
        else:
            self._run_gui()
    
    def _run_console(self):
        """Run in console mode (no GUI)"""
        logger.info("Starting in console mode...")
        
        # Create and start monitor
        self.monitor = FileMonitor(
            watch_folder=self.monitor_folder,
            target_file=self.target_file,
            base_path=self.base_path,
            callback=self._on_race_results,
            console_mode=True
        )
        
        if self.monitor.start():
            logger.info("Press Ctrl+C to stop")
            try:
                while self.running:
                    time.sleep(1)
            except KeyboardInterrupt:
                logger.info("\nShutting down...")
                self.stop()
    
    def _run_gui(self):
        """Run with GUI"""
        # Import Qt only when needed
        from PyQt5.QtWidgets import QApplication
        
        # Create QApplication first
        self.app = QApplication(sys.argv)
        self.app.setStyle('Fusion')
        
        # Now import MainWindow (after QApplication exists)
        from gui import MainWindow
        
        # Create main window
        self.main_window = MainWindow(self.base_path, self.monitor_folder, self.target_file)
        
        # Create monitor
        self.monitor = FileMonitor(
            watch_folder=self.monitor_folder,
            target_file=self.target_file,
            base_path=self.base_path,
            callback=self._on_race_results,
            console_mode=False
        )
        
        # Start monitor in background thread
        if self.monitor.start():
            monitor_thread = threading.Thread(target=self._run_monitor, daemon=True)
            monitor_thread.start()
        
        # Show window and run event loop
        self.main_window.show()
        sys.exit(self.app.exec_())
    
    def _run_monitor(self):
        """Run monitor in background thread"""
        try:
            while self.running and self.monitor and self.monitor.observer.is_alive():
                time.sleep(1)
        except Exception as e:
            logger.error(f"Monitor thread error: {e}")
    
    def _on_race_results(self, data: dict):
        """Callback when race results are detected"""
        if self.main_window:
            # Use Qt signal to safely update GUI from another thread
            self.main_window.on_race_results_detected(data)
        else:
            # Console mode - just log
            logger.info("=" * 60)
            logger.info("Race Results Detected!")
            logger.info(f"Track: {data.get('track_name')}")
            logger.info(f"Best AI Lap: {data.get('best_ai_lap')}")
            logger.info(f"Worst AI Lap: {data.get('worst_ai_lap')}")
            logger.info(f"User Best Lap: {data.get('user_best_lap')}")
            logger.info(f"Current QualRatio: {data.get('qual_ratio')}")
            logger.info(f"Current RaceRatio: {data.get('race_ratio')}")
            logger.info("=" * 60)
    
    def stop(self):
        """Stop the application"""
        self.running = False
        if self.monitor:
            self.monitor.stop()
        if self.app:
            self.app.quit()


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Live AI Tuner - Automatically adjust AI ratios based on race results'
    )
    parser.add_argument(
        '--config',
        default='cfg.yml',
        help='Path to configuration file (default: cfg.yml)'
    )
    parser.add_argument(
        '--no-gui',
        action='store_true',
        help='Run without GUI (console mode)'
    )
    parser.add_argument(
        '--base-path',
        help='Override base path from configuration file'
    )
    
    args = parser.parse_args()
    
    # Get base path
    if args.base_path:
        base_path = Path(args.base_path)
    else:
        base_path = get_or_prompt_base_path(args.config)
    
    if base_path is None:
        print("No base path selected. Exiting.")
        return 1
    
    # Create and run application
    tuner = LiveAITuner(base_path, no_gui=args.no_gui)
    tuner.start()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
