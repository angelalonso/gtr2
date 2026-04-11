# pip install PyQt5 numpy scipy pyyaml
#!/usr/bin/env python3
"""
Live AI Tuner V2 - Automatic AI ratio adjustment based on race results
OPTIMIZED: Lazy imports, reduced startup time, lower CPU usage
UPDATED: SQLite persistence via db_manager
"""

import sys
import argparse
import logging
from pathlib import Path
from datetime import datetime
import threading
import time

sys.path.insert(0, str(Path(__file__).parent))

from cfg_manage import (
    get_or_prompt_base_path, 
    get_logging_enabled, 
    get_db_path,
    get_track_formula_db_path  # ← Add this import
)

from track_formula_db import TrackFormulaDB


def setup_logging(logging_enabled=False):
    if not logging_enabled:
        logging.basicConfig(level=logging.CRITICAL, handlers=[logging.NullHandler()])
        logging.getLogger().setLevel(logging.CRITICAL)
        return None

    log_filename = f"live_ai_tuner_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_filename, encoding='utf-8'),
            logging.StreamHandler(),
        ],
    )
    return log_filename


class LiveAITuner:
    """Main application class coordinating all components"""

    def __init__(self, base_path: Path, no_gui: bool = False, config_file: str = "cfg.yml"):
        self.base_path = Path(base_path)
        self.no_gui = no_gui
        self.monitor = None
        self.main_window = None
        self.running = True
        self.app = None

        # ── Open both SQLite databases ────────────────────────────────────────
        from db_manager import Database
        from track_formula_db import TrackFormulaDB  # ← Make sure this is here
        
        db_path = get_db_path(config_file)
        self.db = Database(db_path)
        print(f"Main database: {db_path}")
        
        track_formula_db_path = get_track_formula_db_path(config_file)  # ← Now defined
        self.track_formula_db = TrackFormulaDB(track_formula_db_path)
        print(f"Track formula database: {track_formula_db_path}")

        # Lazy-loaded components
        self._curve_manager = None
        self._aiw_manager = None

        self.monitor_folder = self.base_path / 'UserData'
        self.target_file = self.monitor_folder / 'Log' / 'Results' / 'raceresults.txt'

        self.monitor_folder.mkdir(parents=True, exist_ok=True)
        (self.monitor_folder / 'Log' / 'Results').mkdir(parents=True, exist_ok=True)

        print(f"Base path: {self.base_path}")
        print(f"Target file: {self.target_file}")

    @property
    def curve_manager(self):
        if self._curve_manager is None:
            from global_curve import GlobalCurveManager
            from cfg_manage import get_formulas_dir
            # Pass the db so the curve is persisted in SQLite
            self._curve_manager = GlobalCurveManager(get_formulas_dir(), db=self.db)
        return self._curve_manager

    @property
    def aiw_manager(self):
        if self._aiw_manager is None:
            from aiw_manager import AIWManager
            # Pass the db so path cache + ratio history are persisted
            self._aiw_manager = AIWManager(self.base_path / 'backups', db=self.db)
        return self._aiw_manager

    def start(self):
        if self.no_gui:
            self._run_console()
        else:
            self._run_gui()

    def _run_console(self):
        print("Starting in console mode...")
        from file_monitor import FileMonitor

        self.monitor = FileMonitor(
            watch_folder=self.monitor_folder,
            target_file=self.target_file,
            base_path=self.base_path,
            callback=self._on_race_results,
            console_mode=True,
            db=self.db,          # ← inject DB
        )

        if self.monitor.start():
            print(f"Monitoring every {self.monitor.poll_interval} seconds. Press Ctrl+C to stop")
            try:
                while self.running:
                    time.sleep(0.5)
            except KeyboardInterrupt:
                print("\nShutting down...")
                self.stop()

    def _run_gui(self):
        from PyQt5.QtWidgets import QApplication
        self.app = QApplication(sys.argv)
        self.app.setStyle('Fusion')

        from gui import MainWindow
        self.main_window = MainWindow(self.base_path, self.monitor_folder, self.target_file)
        self.main_window.curve_manager = self.curve_manager
        self.main_window.aiw_manager = self.aiw_manager
        self.main_window.db = self.db           # ← expose DB to GUI if needed

        from file_monitor import FileMonitor
        self.monitor = FileMonitor(
            watch_folder=self.monitor_folder,
            target_file=self.target_file,
            base_path=self.base_path,
            callback=self._on_race_results,
            console_mode=False,
            db=self.db,          # ← inject DB
        )

        if self.monitor.start():
            monitor_thread = threading.Thread(target=self._run_monitor, daemon=True)
            monitor_thread.start()

        self.main_window.show()
        sys.exit(self.app.exec_())

    def _run_monitor(self):
        try:
            while self.running and self.monitor and self.monitor.running:
                time.sleep(0.5)
        except Exception as e:
            print(f"Monitor thread error: {e}")

    def _on_race_results(self, data: dict):
        if self.main_window:
            self.main_window.on_race_results_detected(data)
        else:
            print(
                f"\nRace Results: {data.get('track_name')} "
                f"| User: {data.get('user_best_lap')} "
                f"| AI Best: {data.get('best_ai_lap')}"
            )

    def stop(self):
        self.running = False
        if self.monitor:
            self.monitor.stop()
        if self.app:
            self.app.quit()


def main():
    parser = argparse.ArgumentParser(
        description='Live AI Tuner - Automatically adjust AI ratios based on race results'
    )
    parser.add_argument('--config', default='cfg.yml',
                        help='Path to configuration file (default: cfg.yml)')
    parser.add_argument('--no-gui', action='store_true',
                        help='Run without GUI (console mode)')
    parser.add_argument('--base-path', help='Override base path from configuration file')

    args = parser.parse_args()

    config = None
    try:
        import yaml
        config_path = Path(args.config)
        if config_path.exists():
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
    except Exception:
        pass

    logging_enabled = config.get('logging_enabled', False) if config else False
    setup_logging(logging_enabled)

    if args.base_path:
        base_path = Path(args.base_path)
    else:
        base_path = get_or_prompt_base_path(args.config)

    if base_path is None:
        print("No base path selected. Exiting.")
        return 1

    tuner = LiveAITuner(base_path, no_gui=args.no_gui, config_file=args.config)
    tuner.start()
    return 0


if __name__ == "__main__":
    sys.exit(main())
