#!/usr/bin/env python3
"""
Logs Tab for Setup Manager (Tkinter version)
Displays application logs with filtering
"""

import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
import logging


class LogHandler(logging.Handler):
    """Custom logging handler that sends logs to the UI"""
    
    def __init__(self, callback):
        super().__init__()
        self.callback = callback
    
    def emit(self, record):
        try:
            msg = self.format(record)
            level = record.levelname
            self.callback(level, msg)
        except Exception:
            pass


class LogsTab(tk.Frame):
    """Logs tab for displaying application logs"""
    
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.log_buffer = []
        self.max_lines = 1000
        self.current_level = "INFO"
        self.log_handler = None
        
        self.configure(bg='#1e1e1e')
        self.setup_ui()
        self.setup_logging()
    
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
        auto_scroll_cb = tk.Checkbutton(control_frame, text="Auto-scroll",
                                         variable=self.auto_scroll_var,
                                         bg='#1e1e1e', fg='white',
                                         activebackground='#1e1e1e')
        auto_scroll_cb.pack(side=tk.LEFT, padx=20)
        
        # Clear button
        clear_btn = tk.Button(control_frame, text="Clear Log",
                               bg='#f44336', fg='white', font=('Arial', 9),
                               relief=tk.FLAT, padx=10, pady=4,
                               command=self.clear_log)
        clear_btn.pack(side=tk.RIGHT, padx=5)
        
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
    
    def setup_logging(self):
        """Set up logging to capture logs from the application"""
        self.log_handler = LogHandler(self.add_log)
        self.log_handler.setFormatter(logging.Formatter('%(message)s'))
        logging.getLogger().addHandler(self.log_handler)
    
    def add_log(self, level: str, message: str):
        """Add a log message to the display"""
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        formatted = f"[{timestamp}] [{level:7}] {message}"
        
        self.log_buffer.append((level, formatted))
        
        if len(self.log_buffer) > self.max_lines_var.get():
            self.log_buffer = self.log_buffer[-self.max_lines_var.get():]
        
        self.update_display()
    
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
        
        if self.auto_scroll_var.get():
            self.log_text.see(tk.END)
        
        self.status_label.config(text=f"Showing {len(self.log_buffer)} log entries")
    
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
    
    def clear_log(self):
        """Clear the log buffer and display"""
        result = messagebox.askyesno("Clear Log", "Clear all log entries?")
        if result:
            self.log_buffer.clear()
            self.log_text.delete(1.0, tk.END)
            self.status_label.config(text="Log cleared")
    
    def destroy(self):
        """Clean up on destruction"""
        if self.log_handler:
            logging.getLogger().removeHandler(self.log_handler)
        super().destroy()
