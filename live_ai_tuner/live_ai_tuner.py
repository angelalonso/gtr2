import os
import sys
import time
import logging
import threading
from datetime import datetime
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import tkinter as tk
from tkinter import ttk

# Try to import yaml, provide helpful error if missing
try:
    import yaml
except ImportError:
    print("Error: PyYAML is required. Install it with: pip install pyyaml")
    sys.exit(1)

# Configure logging to both file and console
log_filename = f"file_monitor_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

# Create file handler
file_handler = logging.FileHandler(log_filename, encoding='utf-8')
file_handler.setLevel(logging.INFO)
file_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
file_handler.setFormatter(file_formatter)

# Create console handler
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_formatter = logging.Formatter('%(asctime)s - %(message)s', datefmt='%H:%M:%S')
console_handler.setFormatter(console_formatter)

# Configure root logger
logging.basicConfig(
    level=logging.INFO,
    handlers=[file_handler, console_handler]
)
logger = logging.getLogger(__name__)

class NotificationWindow:
    """Popup notification window with countdown"""
    
    def __init__(self, file_path, event_type):
        self.file_path = file_path
        self.event_type = event_type
        self.window = None
        self.countdown = 5
        self.countdown_label = None
        self.running = True
        
    def show(self):
        """Create and show the notification window"""
        self.window = tk.Toplevel()
        self.window.title("File Change Detected")
        self.window.geometry("500x200")
        
        # Center the window on screen
        self.window.update_idletasks()
        width = self.window.winfo_width()
        height = self.window.winfo_height()
        x = (self.window.winfo_screenwidth() // 2) - (width // 2)
        y = (self.window.winfo_screenheight() // 2) - (height // 2)
        self.window.geometry(f'{width}x{height}+{x}+{y}')
        
        # Make window grab focus
        self.window.lift()
        self.window.focus_force()
        self.window.grab_set()
        
        # Configure window
        self.window.configure(bg='#f0f0f0')
        
        # Main frame
        main_frame = tk.Frame(self.window, bg='#f0f0f0')
        main_frame.pack(expand=True, fill='both', padx=20, pady=20)
        
        # Event type with color coding
        event_colors = {
            'created': '#5cb85c',  # green
            'modified': '#f0ad4e',  # orange
            'deleted': '#d9534f',   # red
            'moved': '#5bc0de'       # blue
        }
        color = event_colors.get(self.event_type, '#d9534f')
        
        event_label = tk.Label(
            main_frame,
            text=f"{self.event_type.upper()}",
            font=('Arial', 12, 'bold'),
            bg='#f0f0f0',
            fg=color
        )
        event_label.pack(pady=(0, 10))
        
        # File path
        file_label = tk.Label(
            main_frame,
            text=f"File:\n{self.file_path}",
            font=('Arial', 10),
            bg='#f0f0f0',
            justify='center',
            wraplength=450
        )
        file_label.pack(pady=(0, 15))
        
        # Timestamp
        timestamp = datetime.now().strftime('%H:%M:%S')
        time_label = tk.Label(
            main_frame,
            text=f"Time: {timestamp}",
            font=('Arial', 8),
            bg='#f0f0f0',
            fg='#666'
        )
        time_label.pack(pady=(0, 5))
        
        # Countdown label
        self.countdown_label = tk.Label(
            main_frame,
            text=f"Closing in {self.countdown} seconds...",
            font=('Arial', 9),
            bg='#f0f0f0',
            fg='#666'
        )
        self.countdown_label.pack(pady=(0, 10))
        
        # OK button
        ok_button = ttk.Button(
            main_frame,
            text="OK (Enter/Esc)",
            command=self.close,
            width=20
        )
        ok_button.pack()
        ok_button.focus_set()
        
        # Bind keyboard shortcuts
        self.window.bind('<Return>', lambda e: self.close())
        self.window.bind('<Escape>', lambda e: self.close())
        
        # Start countdown
        self.update_countdown()
        
        # Ensure window is on top
        self.window.attributes('-topmost', True)
        
        # Wait for window to close
        self.window.protocol("WM_DELETE_WINDOW", self.close)
        self.window.wait_window()
    
    def update_countdown(self):
        """Update countdown timer"""
        if self.running and self.countdown > 0:
            if self.countdown_label:
                self.countdown_label.config(
                    text=f"Closing in {self.countdown} seconds..."
                )
            self.countdown -= 1
            self.window.after(1000, self.update_countdown)
        elif self.running:
            self.close()
    
    def close(self):
        """Close the notification window"""
        self.running = False
        if self.window:
            self.window.grab_release()
            self.window.destroy()
            self.window = None

class MainWindow:
    """Main GUI window showing listening status"""
    
    def __init__(self, watch_folder):
        self.watch_folder = watch_folder
        self.root = None
        self.status_label = None
        self.log_text = None
        
    def show(self):
        """Create and show the main window"""
        self.root = tk.Tk()
        self.root.title("File Monitor")
        self.root.geometry("600x500")
        
        # Center the window on screen
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f'{width}x{height}+{x}+{y}')
        
        # Configure window
        self.root.configure(bg='#f0f0f0')
        
        # Top frame for status
        top_frame = tk.Frame(self.root, bg='#f0f0f0')
        top_frame.pack(fill='x', padx=20, pady=(20, 10))
        
        # Status text
        title_label = tk.Label(
            top_frame,
            text="File Monitor Active",
            font=('Arial', 12, 'bold'),
            bg='#f0f0f0'
        )
        title_label.pack()
        
        self.status_label = tk.Label(
            top_frame,
            text=f"Listening on:\n{self.watch_folder}",
            font=('Arial', 10),
            bg='#f0f0f0',
            justify='center',
            wraplength=550
        )
        self.status_label.pack(pady=(5, 10))
        
        # Status indicator (text-based)
        status_indicator = tk.Label(
            top_frame,
            text="● ACTIVE",
            font=('Arial', 9, 'bold'),
            bg='#f0f0f0',
            fg='#5cb85c'
        )
        status_indicator.pack()
        
        # Separator
        separator = ttk.Separator(self.root, orient='horizontal')
        separator.pack(fill='x', padx=20, pady=10)
        
        # Log frame
        log_frame = tk.Frame(self.root, bg='#f0f0f0')
        log_frame.pack(fill='both', expand=True, padx=20, pady=(0, 10))
        
        log_label = tk.Label(
            log_frame,
            text="Recent Changes:",
            font=('Arial', 10, 'bold'),
            bg='#f0f0f0',
            anchor='w'
        )
        log_label.pack(fill='x', pady=(0, 5))
        
        # Text widget for logs
        log_container = tk.Frame(log_frame, bg='white', relief='sunken', bd=1)
        log_container.pack(fill='both', expand=True)
        
        self.log_text = tk.Text(
            log_container,
            wrap='word',
            font=('Consolas', 9),
            bg='white',
            fg='black',
            height=15
        )
        self.log_text.pack(side='left', fill='both', expand=True)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(log_container, orient='vertical', command=self.log_text.yview)
        scrollbar.pack(side='right', fill='y')
        self.log_text.configure(yscrollcommand=scrollbar.set)
        
        # Button frame
        button_frame = tk.Frame(self.root, bg='#f0f0f0')
        button_frame.pack(fill='x', padx=20, pady=(0, 20))
        
        # Quit button
        quit_button = ttk.Button(
            button_frame,
            text="Quit",
            command=self.quit,
            width=15
        )
        quit_button.pack()
        
        # Handle window close
        self.root.protocol("WM_DELETE_WINDOW", self.quit)
        
        # Start GUI
        self.root.mainloop()
    
    def add_log_entry(self, event_type, file_path, size_info=None):
        """Add an entry to the log display"""
        if self.log_text:
            timestamp = datetime.now().strftime('%H:%M:%S')
            
            # Color coding for different event types
            tags = []
            if event_type == 'created':
                tag = f"created_{timestamp}"
                self.log_text.tag_config(tag, foreground='#5cb85c')
                tags.append(tag)
            elif event_type == 'modified':
                tag = f"modified_{timestamp}"
                self.log_text.tag_config(tag, foreground='#f0ad4e')
                tags.append(tag)
            elif event_type == 'deleted':
                tag = f"deleted_{timestamp}"
                self.log_text.tag_config(tag, foreground='#d9534f')
                tags.append(tag)
            elif event_type == 'moved':
                tag = f"moved_{timestamp}"
                self.log_text.tag_config(tag, foreground='#5bc0de')
                tags.append(tag)
            
            log_entry = f"[{timestamp}] {event_type.upper()}: {file_path}"
            if size_info:
                log_entry += f" {size_info}"
            log_entry += "\n"
            
            self.log_text.insert('end', log_entry, tuple(tags))
            self.log_text.see('end')  # Auto-scroll to bottom
            
            # Limit log size to prevent memory issues (keep last 1000 lines)
            line_count = int(self.log_text.index('end-1c').split('.')[0])
            if line_count > 1000:
                self.log_text.delete('1.0', f'{line_count - 1000}.0')
    
    def update_status(self, message):
        """Update the status message"""
        if self.status_label:
            self.status_label.config(text=message)
    
    def quit(self):
        """Quit the application"""
        self.root.quit()
        self.root.destroy()

class FileChangeHandler(FileSystemEventHandler):
    """Handles file system events and detects content changes"""
    
    def __init__(self, watch_folder, main_window):
        super().__init__()
        self.watch_folder = Path(watch_folder)
        self.file_states = {}  # Store file size and modification time
        self.main_window = main_window
        
    def show_notification(self, file_path, event_type, size_info=None):
        """Show popup notification for file change"""
        try:
            # Create notification window in a separate thread to avoid blocking
            def show_window():
                notification = NotificationWindow(file_path, event_type)
                notification.show()
            
            # Add to GUI log
            if self.main_window:
                self.main_window.add_log_entry(event_type, file_path, size_info)
            
            # Log to console and file
            log_message = f"{event_type.upper()}: {file_path}"
            if size_info:
                log_message += f" - {size_info}"
            logger.info(log_message)
            
            # Run notification in separate thread
            thread = threading.Thread(target=show_window, daemon=True)
            thread.start()
        except Exception as e:
            logger.error(f"Error showing notification: {e}")
    
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
            self.show_notification(str(file_path), 'created')
    
    def on_deleted(self, event):
        """Called when a file is deleted"""
        if not event.is_directory:
            file_path = Path(event.src_path)
            logger.info(f"File deleted: {file_path}")
            if str(file_path) in self.file_states:
                del self.file_states[str(file_path)]
            self.show_notification(str(file_path), 'deleted')
    
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
            
            self.show_notification(f"{src_path} -> {dest_path}", 'moved')
    
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
                self.show_notification(str(file_path), 'created')
                return
            
            # Check if file content changed (by size or modification time)
            if (current_state['size'] != previous_state['size'] or 
                current_state['mtime'] != previous_state['mtime']):
                
                size_info = f"Size: {previous_state['size']} -> {current_state['size']} bytes"
                logger.info(f"File content changed: {file_path}")
                logger.info(f"  {size_info}")
                
                # Update stored state
                self.file_states[str(file_path)] = current_state
                
                # Show notification
                self.show_notification(str(file_path), 'modified', size_info)
                
        except (OSError, IOError) as e:
            logger.error(f"Error checking file {file_path}: {e}")

class FileMonitor:
    """Main file monitor class"""
    
    def __init__(self, watch_folder, main_window, recursive=True):
        self.watch_folder = Path(watch_folder)
        self.recursive = recursive
        self.observer = Observer()
        self.event_handler = FileChangeHandler(self.watch_folder, main_window)
        
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
        logger.info(f"Log file: {log_filename}")
        
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

def run_monitor_in_thread(monitor):
    """Run monitor in a separate thread"""
    try:
        while monitor.observer.is_alive():
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("\nShutting down...")
        monitor.stop()

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
    parser.add_argument(
        '--no-gui',
        action='store_true',
        help='Run without GUI (console mode)'
    )
    
    args = parser.parse_args()
    
    # Set logging level based on quiet mode
    if args.quiet:
        logger.setLevel(logging.WARNING)
        console_handler.setLevel(logging.WARNING)
    
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
    
    if args.no_gui:
        # Console mode
        monitor = FileMonitor(
            monitor_folder,
            main_window=None,
            recursive=not args.no_recursive
        )
        
        if monitor.start():
            logger.info("Press Ctrl+C to stop monitoring")
            try:
                while monitor.observer.is_alive():
                    time.sleep(1)
            except KeyboardInterrupt:
                logger.info("\nShutting down...")
                monitor.stop()
    else:
        # GUI mode
        try:
            # Create main window
            main_window = MainWindow(str(monitor_folder))
            
            # Create and start monitor
            monitor = FileMonitor(
                monitor_folder,
                main_window,
                recursive=not args.no_recursive
            )
            
            if monitor.start():
                # Run monitor in separate thread
                monitor_thread = threading.Thread(
                    target=run_monitor_in_thread,
                    args=(monitor,),
                    daemon=True
                )
                monitor_thread.start()
                
                # Start GUI (this blocks)
                main_window.show()
                
                # Clean up when GUI closes
                monitor.stop()
        except Exception as e:
            logger.error(f"Error starting GUI: {e}")
            sys.exit(1)

if __name__ == "__main__":
    main()
