import os
import sys
import time
import logging
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# Try to import yaml, provide helpful error if missing
try:
    import yaml
except ImportError:
    print("Error: PyYAML is required. Install it with: pip install pyyaml")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

class FileChangeHandler(FileSystemEventHandler):
    """Handles file system events and detects content changes"""
    
    def __init__(self, watch_folder):
        super().__init__()
        self.watch_folder = Path(watch_folder)
        self.file_states = {}  # Store file size and modification time
        
    def on_modified(self, event):
        """Called when a file is modified"""
        if not event.is_directory:
            file_path = Path(event.src_path)
            self._check_file_change(file_path)
    
    def on_created(self, event):
        """Called when a file is created"""
        if not event.is_directory:
            file_path = Path(event.src_path)
            logger.info(f"File created: {file_path}")
            self._track_file(file_path)
    
    def on_deleted(self, event):
        """Called when a file is deleted"""
        if not event.is_directory:
            file_path = Path(event.src_path)
            logger.info(f"File deleted: {file_path}")
            if str(file_path) in self.file_states:
                del self.file_states[str(file_path)]
    
    def on_moved(self, event):
        """Called when a file is moved/renamed"""
        if not event.is_directory:
            src_path = Path(event.src_path)
            dest_path = Path(event.dest_path)
            logger.info(f"File moved: {src_path} -> {dest_path}")
            
            # Update tracking if we were tracking the source
            if str(src_path) in self.file_states:
                self.file_states[str(dest_path)] = self.file_states.pop(str(src_path))
                self._track_file(dest_path)
    
    def _track_file(self, file_path):
        """Track initial state of a file"""
        try:
            if file_path.exists() and file_path.is_file():
                stat_info = file_path.stat()
                self.file_states[str(file_path)] = {
                    'size': stat_info.st_size,
                    'mtime': stat_info.st_mtime
                }
        except (OSError, IOError) as e:
            logger.error(f"Error tracking file {file_path}: {e}")
    
    def _check_file_change(self, file_path):
        """Check if file content has actually changed"""
        try:
            if not file_path.exists() or not file_path.is_file():
                return
            
            current_state = {
                'size': file_path.stat().st_size,
                'mtime': file_path.stat().st_mtime
            }
            
            previous_state = self.file_states.get(str(file_path))
            
            # If we haven't seen this file before, track it
            if previous_state is None:
                self.file_states[str(file_path)] = current_state
                logger.info(f"New file detected: {file_path}")
                return
            
            # Check if file content changed (by size or modification time)
            if (current_state['size'] != previous_state['size'] or 
                current_state['mtime'] != previous_state['mtime']):
                
                logger.info(f"File content changed: {file_path}")
                logger.info(f"  Size: {previous_state['size']} -> {current_state['size']} bytes")
                
                # Update stored state
                self.file_states[str(file_path)] = current_state
                
        except (OSError, IOError) as e:
            logger.error(f"Error checking file {file_path}: {e}")

class FileMonitor:
    """Main file monitor class"""
    
    def __init__(self, watch_folder, recursive=True):
        self.watch_folder = Path(watch_folder)
        self.recursive = recursive
        self.observer = Observer()
        self.event_handler = FileChangeHandler(self.watch_folder)
        
    def start(self):
        """Start monitoring the folder"""
        if not self.watch_folder.exists():
            logger.error(f"Folder does not exist: {self.watch_folder}")
            return False
        
        if not self.watch_folder.is_dir():
            logger.error(f"Path is not a directory: {self.watch_folder}")
            return False
        
        # Schedule monitoring
        self.observer.schedule(
            self.event_handler, 
            str(self.watch_folder), 
            recursive=self.recursive
        )
        self.observer.start()
        
        # Track existing files
        self._track_existing_files()
        
        logger.info(f"Started monitoring folder: {self.watch_folder}")
        logger.info(f"Recursive mode: {self.recursive}")
        logger.info("Press Ctrl+C to stop monitoring")
        
        return True
    
    def _track_existing_files(self):
        """Track all existing files in the watch folder"""
        pattern = "**/*" if self.recursive else "*"
        for file_path in self.watch_folder.glob(pattern):
            if file_path.is_file():
                self.event_handler._track_file(file_path)
        
        file_count = len(self.event_handler.file_states)
        logger.info(f"Tracking {file_count} existing files")
    
    def stop(self):
        """Stop monitoring the folder"""
        self.observer.stop()
        self.observer.join()
        logger.info("Stopped monitoring")
    
    def run(self):
        """Run the monitor until interrupted"""
        try:
            while self.observer.is_alive():
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("\nShutting down...")
            self.stop()

def load_config(config_path='cfg.yml'):
    """Load configuration from YAML file"""
    config_path = Path(config_path)
    
    if not config_path.exists():
        logger.error(f"Configuration file not found: {config_path}")
        return None
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        if not config or 'base_path' not in config:
            logger.error("Configuration file must contain 'base_path'")
            return None
        
        return config
    except yaml.YAMLError as e:
        logger.error(f"Error parsing YAML configuration: {e}")
        return None
    except Exception as e:
        logger.error(f"Error reading configuration file: {e}")
        return None

def get_monitor_folder(base_path):
    """Construct the full folder path to monitor"""
    base_path = Path(base_path)
    
    # Add 'UserData' subfolder (works on both Windows and Linux)
    monitor_folder = base_path / 'UserData'
    
    # Check if folder exists
    if not monitor_folder.exists():
        logger.warning(f"UserData folder does not exist: {monitor_folder}")
        logger.info("Creating UserData folder...")
        try:
            monitor_folder.mkdir(parents=True, exist_ok=True)
            logger.info(f"Created UserData folder: {monitor_folder}")
        except Exception as e:
            logger.error(f"Failed to create UserData folder: {e}")
            return None
    
    return monitor_folder

def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Monitor UserData folder for file content changes'
    )
    parser.add_argument(
        '--config',
        default='cfg.yml',
        help='Path to configuration file (default: cfg.yml)'
    )
    parser.add_argument(
        '--no-recursive',
        action='store_true',
        help='Do not monitor subfolders recursively'
    )
    parser.add_argument(
        '--quiet',
        action='store_true',
        help='Reduce output (only show actual file changes)'
    )
    parser.add_argument(
        '--base-path',
        help='Override base path from configuration file'
    )
    
    args = parser.parse_args()
    
    # Set logging level based on quiet mode
    if args.quiet:
        logger.setLevel(logging.WARNING)
    
    # Load configuration
    config = load_config(args.config)
    if not config and not args.base_path:
        logger.error("No valid configuration found. Please provide cfg.yml or use --base-path")
        sys.exit(1)
    
    # Determine base path
    if args.base_path:
        base_path = args.base_path
    else:
        base_path = config['base_path']
    
    logger.info(f"Using base path: {base_path}")
    
    # Get the folder to monitor (base_path/UserData)
    monitor_folder = get_monitor_folder(base_path)
    if not monitor_folder:
        sys.exit(1)
    
    logger.info(f"Monitoring folder: {monitor_folder}")
    
    # Create and start monitor
    monitor = FileMonitor(
        monitor_folder,
        recursive=not args.no_recursive
    )
    
    if monitor.start():
        monitor.run()

if __name__ == "__main__":
    main()
