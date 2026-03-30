# pip install PyQt5 numpy scipy pyyaml
#!/usr/bin/env python3
"""
Live AI Tuner V2 - Automatic AI ratio adjustment based on race results
OPTIMIZED: Lazy imports, reduced startup time, lower CPU usage
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

from cfg_manage import get_or_prompt_base_path, get_logging_enabled


def setup_logging(logging_enabled=False):
    """Setup logging based on configuration - OPTIMIZED"""
    if not logging_enabled:
        # Disable logging completely with minimal overhead
        logging.basicConfig(level=logging.CRITICAL, handlers=[logging.NullHandler()])
        # Only suppress root logger
        logging.getLogger().setLevel(logging.CRITICAL)
        return None
    
    # Normal logging setup
    log_filename = f"live_ai_tuner_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_filename, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    return log_filename


class LiveAITuner:
    """Main application class coordinating all components - OPTIMIZED"""
    
    def __init__(self, base_path: Path, no_gui: bool = False):
        self.base_path = Path(base_path)
        self.no_gui = no_gui
        self.monitor = None
        self.main_window = None
        self.running = True
        self.app = None
        
        # Lazy-loaded components
        self._curve_manager = None
        self._aiw_manager = None
        
        # Get monitor folder
        self.monitor_folder = self.base_path / 'UserData'
        self.target_file = self.monitor_folder / 'Log' / 'Results' / 'raceresults.txt'
        
        # Ensure directories exist
        self.monitor_folder.mkdir(parents=True, exist_ok=True)
        (self.monitor_folder / 'Log' / 'Results').mkdir(parents=True, exist_ok=True)
        
        print(f"Base path: {self.base_path}")
        print(f"Target file: {self.target_file}")
    
    @property
    def curve_manager(self):
        """Lazy load curve manager"""
        if self._curve_manager is None:
            from global_curve import GlobalCurveManager
            from cfg_manage import get_formulas_dir
            self._curve_manager = GlobalCurveManager(get_formulas_dir())
        return self._curve_manager
    
    @property
    def aiw_manager(self):
        """Lazy load AIW manager"""
        if self._aiw_manager is None:
            from aiw_manager import AIWManager
            self._aiw_manager = AIWManager(self.base_path / 'backups')
        return self._aiw_manager
    
    def start(self):
        """Start the application"""
        if self.no_gui:
            self._run_console()
        else:
            self._run_gui()
    
    def _run_console(self):
        """Run in console mode (no GUI) - OPTIMIZED"""
        print("Starting in console mode...")
        
        from file_monitor import FileMonitor
        
        self.monitor = FileMonitor(
            watch_folder=self.monitor_folder,
            target_file=self.target_file,
            base_path=self.base_path,
            callback=self._on_race_results,
            console_mode=True
        )
        
        if self.monitor.start():
            print(f"Monitoring every {self.monitor.poll_interval} seconds. Press Ctrl+C to stop")
            try:
                while self.running:
                    time.sleep(0.5)  # Sleep with lower CPU usage
            except KeyboardInterrupt:
                print("\nShutting down...")
                self.stop()
    
    def _run_gui(self):
        """Run with GUI - OPTIMIZED with lazy imports"""
        # Import Qt only when needed
        from PyQt5.QtWidgets import QApplication
        
        self.app = QApplication(sys.argv)
        self.app.setStyle('Fusion')
        
        # Import MainWindow only after QApplication exists
        from gui import MainWindow
        
        # Create main window with lazy-loaded components
        self.main_window = MainWindow(self.base_path, self.monitor_folder, self.target_file)
        
        # Pass references to managers (they will be lazy-loaded)
        self.main_window.curve_manager = self.curve_manager
        self.main_window.aiw_manager = self.aiw_manager
        
        from file_monitor import FileMonitor
        
        self.monitor = FileMonitor(
            watch_folder=self.monitor_folder,
            target_file=self.target_file,
            base_path=self.base_path,
            callback=self._on_race_results,
            console_mode=False
        )
        
        if self.monitor.start():
            monitor_thread = threading.Thread(target=self._run_monitor, daemon=True)
            monitor_thread.start()
        
        self.main_window.show()
        sys.exit(self.app.exec_())
    
    def _run_monitor(self):
        """Run monitor in background thread - OPTIMIZED"""
        try:
            while self.running and self.monitor and self.monitor.running:
                time.sleep(0.5)  # Low CPU usage
        except Exception as e:
            print(f"Monitor thread error: {e}")
    
    def _on_race_results(self, data: dict):
        """Callback when race results are detected"""
        if self.main_window:
            self.main_window.on_race_results_detected(data)
        else:
            # Console mode - minimal output
            print(f"\nRace Results: {data.get('track_name')} | User: {data.get('user_best_lap')} | AI Best: {data.get('best_ai_lap')}")
    
    def stop(self):
        """Stop the application"""
        self.running = False
        if self.monitor:
            self.monitor.stop()
        if self.app:
            self.app.quit()


def main():
    """Main entry point - OPTIMIZED"""
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
    
    # Fast config loading without heavy imports
    config = None
    try:
        import yaml
        config_path = Path(args.config)
        if config_path.exists():
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
    except:
        pass
    
    logging_enabled = config.get('logging_enabled', False) if config else False
    setup_logging(logging_enabled)
    
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
