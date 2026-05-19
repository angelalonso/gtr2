#!/usr/bin/env python3
"""
Logs Tab for Setup Manager (Tkinter version)
Displays application logs with filtering, reading from rotating log files
"""

import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
import logging
import threading
from pathlib import Path
from typing import List, Tuple, Optional

from core_log_manager import LogReader, get_log_reader


class LogsTab(tk.Frame):
    """Logs tab for displaying application logs from rotating log files"""
    
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.log_buffer = []
        self.max_lines = 1000
        self.current_level = "INFO"
        self.log_reader = get_log_reader()
        self.current_log_path = None
        self.update_timer = None
        self.is_running = True
        
        self.configure(bg='#1e1e1e')
        self.setup_ui()
        
        # Start periodic log updates
        self.start_log_updates()
    
    def setup_ui(self):
        # Control bar
        control_frame = tk.Frame(self, bg='#1e1e1e')
        control_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Level selector
        tk.Label(control_frame, text="Show level:", bg='#1e1e1e', fg='white').pack(side=tk.LEFT, padx=5)
        
        self.level_var = tk.StringVar(value="INFO")
        level_combo = ttk.Combobox(control_frame, textvariable=self.level_var,
                                    values=["ERROR", "WARNING", "INFO", "DEBUG", "ALL"],
                                    state="readonly", width=10)
        level_combo.pack(side=tk.LEFT, padx=5)
        level_combo.bind("<<ComboboxSelected>>", self.on_level_changed)
        
        # Max lines
        tk.Label(control_frame, text="Max lines:", bg='#1e1e1e', fg='white').pack(side=tk.LEFT, padx=(20, 5))
        
        self.max_lines_var = tk.IntVar(value=1000)
        max_lines_spin = tk.Spinbox(control_frame, from_=100, to=10000, increment=100,
                                     textvariable=self.max_lines_var, width=8,
                                     bg='#3c3c3c', fg='white', relief=tk.FLAT)
        max_lines_spin.pack(side=tk.LEFT, padx=5)
        max_lines_spin.bind("<Return>", self.on_max_lines_changed)
        
        # Auto-scroll
        self.auto_scroll_var = tk.BooleanVar(value=True)
        auto_scroll_cb = tk.Checkbutton(control_frame, text="Auto-scroll", bg='#fbfbfb',
                                         variable=self.auto_scroll_var,
                                         activebackground='#fbfbfb', fg='#555')
        auto_scroll_cb.pack(side=tk.LEFT, padx=20)
        
        # File info label
        self.file_info_label = tk.Label(control_frame, text="", bg='#1e1e1e', fg='#888',
                                         font=('Arial', 8))
        self.file_info_label.pack(side=tk.LEFT, padx=20)
        
        # Clear button
        clear_btn = tk.Button(control_frame, text="Clear Display",
                               bg='#f44336', fg='white', font=('Arial', 9),
                               relief=tk.FLAT, padx=10, pady=4,
                               command=self.clear_display)
        clear_btn.pack(side=tk.RIGHT, padx=5)
        
        # Refresh button
        refresh_btn = tk.Button(control_frame, text="Refresh",
                                 bg='#2196F3', fg='white', font=('Arial', 9),
                                 relief=tk.FLAT, padx=10, pady=4,
                                 command=self.manual_refresh)
        refresh_btn.pack(side=tk.RIGHT, padx=5)
        
        # Log display
        log_frame = tk.Frame(self, bg='#1e1e1e')
        log_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        
        scrollbar = tk.Scrollbar(log_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.log_text = tk.Text(log_frame, bg='#1e1e1e', fg='#d4d4d4',
                                 font=('Courier', 10), wrap=tk.WORD,
                                 yscrollcommand=scrollbar.set)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.log_text.yview)
        
        # Configure text tags for colors
        self.log_text.tag_config("ERROR", foreground="#f44336")
        self.log_text.tag_config("WARNING", foreground="#ff9800")
        self.log_text.tag_config("INFO", foreground="#4caf50")
        self.log_text.tag_config("DEBUG", foreground="#9e9e9e")
        
        # Status
        self.status_label = tk.Label(self, text="Ready", bg='#1e1e1e', fg='#888',
                                      font=('Arial', 9))
        self.status_label.pack(pady=(0, 10))
    
    def get_root(self):
        """Get the root window (top-level Tk instance)"""
        return self.winfo_toplevel()
    
    def start_log_updates(self):
        """Start periodic log updates"""
        self.update_timer = threading.Timer(1.0, self._check_for_updates)
        self.update_timer.daemon = True
        self.update_timer.start()
    
    def _check_for_updates(self):
        """Check for new log entries and update display"""
        if not self.is_running:
            return
        
        # Check if log file has changed
        current_log = self.log_reader.get_current_log_file()
        if current_log != self.current_log_path:
            # Log file has changed (new session started)
            self.current_log_path = current_log
            self.log_reader.reset_position()
            # Full refresh
            self.get_root().after(0, self.full_refresh)
        else:
            # Read new lines
            new_lines = self.log_reader.read_new_lines()
            if new_lines:
                self.get_root().after(0, lambda: self._add_new_lines(new_lines))
        
        # Update file info
        if current_log:
            self.get_root().after(0, lambda: self._update_file_info(current_log))
        
        # Schedule next check
        if self.is_running:
            self.update_timer = threading.Timer(1.0, self._check_for_updates)
            self.update_timer.daemon = True
            self.update_timer.start()
    
    def _add_new_lines(self, lines: List[str]):
        """Add new log lines to the display"""
        for line in lines:
            self._parse_and_add_log_line(line)
        
        self._apply_max_lines()
        
        if self.auto_scroll_var.get():
            self.log_text.see(tk.END)
        
        self.status_label.config(text=f"Showing {len(self.log_buffer)} log entries")
    
    def _parse_and_add_log_line(self, line: str):
        """Parse a log line and add it to the buffer"""
        # Parse log format: [timestamp] [LEVEL] message
        import re
        pattern = r'\[(.*?)\]\s+\[(ERROR|WARNING|INFO|DEBUG)\]\s+(.*)$'
        match = re.match(pattern, line)
        
        if match:
            timestamp, level, message = match.groups()
            self.log_buffer.append((level, line))
        else:
            # Plain line without formatting
            self.log_buffer.append(("INFO", line))
        
        # Trim buffer if needed
        if len(self.log_buffer) > self.max_lines_var.get() * 2:
            self.log_buffer = self.log_buffer[-self.max_lines_var.get():]
    
    def _update_file_info(self, log_path: Path):
        """Update the file info label"""
        if log_path:
            size_kb = log_path.stat().st_size / 1024
            self.file_info_label.config(text=f"Log: {log_path.name} ({size_kb:.1f} KB)")
    
    def full_refresh(self):
        """Perform a full refresh of the log display"""
        self.log_buffer.clear()
        content = self.log_reader.get_current_log_content()
        
        for line in content.split('\n'):
            if line.strip():
                self._parse_and_add_log_line(line)
        
        self._apply_max_lines()
        self.update_display()
        self.status_label.config(text=f"Loaded {len(self.log_buffer)} log entries")
        
        if self.auto_scroll_var.get():
            self.log_text.see(tk.END)
    
    def manual_refresh(self):
        """Manually refresh the log display"""
        self.log_reader.reset_position()
        self.full_refresh()
    
    def _apply_max_lines(self):
        """Apply max lines limit to buffer"""
        max_lines = self.max_lines_var.get()
        if len(self.log_buffer) > max_lines:
            self.log_buffer = self.log_buffer[-max_lines:]
    
    def update_display(self):
        """Update the log display with current buffer"""
        level_map = {"ERROR": 40, "WARNING": 30, "INFO": 20, "DEBUG": 10, "ALL": 0}
        min_level = level_map.get(self.current_level, 20)
        level_values = {"ERROR": 40, "WARNING": 30, "INFO": 20, "DEBUG": 10}
        
        self.log_text.delete(1.0, tk.END)
        
        for level, formatted in self.log_buffer:
            if self.current_level == "ALL" or level_values.get(level, 0) >= min_level:
                tag = level if level in ["ERROR", "WARNING", "INFO", "DEBUG"] else "INFO"
                self.log_text.insert(tk.END, formatted + "\n", tag)
    
    def on_level_changed(self, event=None):
        """Handle level selection change"""
        self.current_level = self.level_var.get()
        self.update_display()
    
    def on_max_lines_changed(self, event=None):
        """Handle max lines change"""
        max_lines = self.max_lines_var.get()
        if len(self.log_buffer) > max_lines:
            self.log_buffer = self.log_buffer[-max_lines:]
        self.update_display()
    
    def clear_display(self):
        """Clear the log display only (does not delete log files)"""
        result = messagebox.askyesno("Clear Display", "Clear the log display? (Log files will not be deleted)")
        if result:
            self.log_buffer.clear()
            self.log_text.delete(1.0, tk.END)
            self.status_label.config(text="Display cleared")
    
    def destroy(self):
        """Clean up on destruction"""
        self.is_running = False
        if self.update_timer:
            self.update_timer.cancel()
        super().destroy()
