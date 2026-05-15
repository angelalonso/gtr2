#!/usr/bin/env python3
"""
Configuration Tab for Setup Manager (Tkinter version)
Handles editing cfg.yml settings
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from pathlib import Path

from core_config import (
    load_config, save_config, get_config_with_defaults, DEFAULT_CONFIG,
    get_ratio_limits, get_nr_last_user_laptimes, get_outlier_settings
)


def get_cfg_dir(config_file: str = "cfg.yml") -> Path:
    """Get the directory where the cfg.yml file is located"""
    cfg_path = Path(config_file)
    if cfg_path.exists():
        return cfg_path.parent.absolute()
    # If cfg.yml doesn't exist, use current working directory
    return Path.cwd()


class ConfigTab(tk.Frame):
    """Configuration tab for editing cfg.yml"""
    
    def __init__(self, parent, config_file: str = "cfg.yml", db=None):
        super().__init__(parent)
        self.parent = parent
        self.config_file = config_file
        self.db = db
        self.config_widgets = {}
        
        self.configure(bg='#1e1e1e')
        self.setup_ui()
        self.load_configuration()
    
    def setup_ui(self):
        # Main container with scrollbar
        canvas = tk.Canvas(self, bg='#1e1e1e', highlightthickness=0)
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        self.scrollable_frame = tk.Frame(canvas, bg='#1e1e1e')
        
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        # Bind mouse wheel events for scrolling
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        
        def _on_mousewheel_linux(event):
            canvas.yview_scroll(int(-1 * event.num), "units")
        
        # Windows and macOS mouse wheel
        canvas.bind("<MouseWheel>", _on_mousewheel)
        # Linux mouse wheel (Button-4 and Button-5)
        canvas.bind("<Button-4>", lambda e: canvas.yview_scroll(-1, "units"))
        canvas.bind("<Button-5>", lambda e: canvas.yview_scroll(1, "units"))
        
        # Also bind the scrollable frame so scrolling works when mouse is over the content
        self.scrollable_frame.bind("<MouseWheel>", _on_mousewheel)
        self.scrollable_frame.bind("<Button-4>", lambda e: canvas.yview_scroll(-1, "units"))
        self.scrollable_frame.bind("<Button-5>", lambda e: canvas.yview_scroll(1, "units"))
        
        # Bind all child widgets recursively to enable scrolling anywhere in the tab
        def bind_recursive(widget):
            widget.bind("<MouseWheel>", _on_mousewheel)
            widget.bind("<Button-4>", lambda e: canvas.yview_scroll(-1, "units"))
            widget.bind("<Button-5>", lambda e: canvas.yview_scroll(1, "units"))
            for child in widget.winfo_children():
                bind_recursive(child)
        
        # Bind after the UI is fully built
        self.after(100, lambda: bind_recursive(self.scrollable_frame))
        
        canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Store canvas reference for potential later use
        self.canvas = canvas
        
        # Info header
        info_frame = tk.Frame(self.scrollable_frame, bg='#2b2b2b', relief=tk.FLAT, bd=1)
        info_frame.pack(fill=tk.X, pady=(0, 20), padx=10)
        
        info_label = tk.Label(info_frame, text="Configuration Settings (cfg.yml)",
                              bg='#2b2b2b', fg='#FFA500', font=('Arial', 14, 'bold'))
        info_label.pack(pady=10)
        
        info_desc = tk.Label(info_frame, 
            text="These settings are saved to cfg.yml. Some changes may require restart.",
            bg='#2b2b2b', fg='#888', font=('Arial', 10))
        info_desc.pack(pady=(0, 10))
        
        # Create form fields
        self.create_form_fields()
        
        # Buttons
        button_frame = tk.Frame(self.scrollable_frame, bg='#1e1e1e')
        button_frame.pack(pady=20)
        
        save_btn = tk.Button(button_frame, text="Save Configuration", 
                             bg='#4CAF50', fg='white', font=('Arial', 11, 'bold'),
                             relief=tk.FLAT, padx=20, pady=8,
                             command=self.save_configuration)
        save_btn.pack(side=tk.LEFT, padx=10)
        
        reload_btn = tk.Button(button_frame, text="Reload from cfg.yml",
                               bg='#2196F3', fg='white', font=('Arial', 11, 'bold'),
                               relief=tk.FLAT, padx=20, pady=8,
                               command=self.load_configuration)
        reload_btn.pack(side=tk.LEFT, padx=10)
    
    def create_form_fields(self):
        """Create all configuration form fields"""
        
        # Define field configurations
        # Format: (key, label, field_type, default, browse_type)
        # browse_type can be: None, "directory", "file"
        fields = [
            ("base_path", "GTR2 Base Path:", "entry", "", "directory"),
            ("formulas_dir", "Formulas Directory:", "entry", "./track_formulas", "directory"),
            ("db_path", "Database Path:", "entry", "ai_data.db", "file"),
            ("auto_apply", "Auto Apply:", "check", False, None),
            ("backup_enabled", "Backup Enabled:", "check", True, None),
            ("logging_enabled", "Logging Enabled:", "check", False, None),
            ("autopilot_enabled", "Autopilot Enabled:", "check", False, None),
            ("autopilot_silent", "Autopilot Silent:", "check", False, None),
            ("poll_interval", "Poll Interval (seconds):", "float", 5.0, None),
            ("min_ratio", "Minimum Ratio:", "float", 0.5, None),
            ("max_ratio", "Maximum Ratio:", "float", 1.5, None),
            ("nr_last_user_laptimes", "Number of Last User Laptimes to Keep:", "int", 1, None),
            ("outlier_method", "Outlier Detection Method:", "combo", "std", None),
            ("outlier_threshold", "Outlier Threshold:", "float", 2.0, None),
            ("outlier_min_points", "Min Points for Outlier Detection:", "int", 3, None),
        ]
        
        row = 0
        for key, label, field_type, default, browse_type in fields:
            # Label frame for each field
            field_frame = tk.Frame(self.scrollable_frame, bg='#2b2b2b', relief=tk.FLAT, bd=1)
            field_frame.pack(fill=tk.X, pady=5, padx=10)
            
            label_widget = tk.Label(field_frame, text=label, bg='#2b2b2b', fg='white',
                                     width=32, anchor='w', font=('Arial', 10))
            label_widget.pack(side=tk.LEFT, padx=10, pady=8)
            
            # Create value frame for entry + browse button
            value_frame = tk.Frame(field_frame, bg='#2b2b2b')
            value_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=10, pady=8)
            
            if field_type == "entry":
                widget = tk.Entry(value_frame, bg='#3c3c3c', fg='white',
                                   font=('Arial', 10), relief=tk.FLAT)
                widget.pack(side=tk.LEFT, fill=tk.X, expand=True)
                self.config_widgets[key] = widget
                
                # Add browse button if needed
                if browse_type == "directory":
                    browse_btn = tk.Button(value_frame, text="Browse...", 
                                           bg='#2196F3', fg='white',
                                           font=('Arial', 9), relief=tk.FLAT,
                                           padx=8, pady=2,
                                           command=lambda k=key: self.browse_directory(k))
                    browse_btn.pack(side=tk.RIGHT, padx=(5, 0))
                elif browse_type == "file":
                    browse_btn = tk.Button(value_frame, text="Browse...", 
                                           bg='#2196F3', fg='white',
                                           font=('Arial', 9), relief=tk.FLAT,
                                           padx=8, pady=2,
                                           command=lambda k=key: self.browse_file(k))
                    browse_btn.pack(side=tk.RIGHT, padx=(5, 0))
                    
            elif field_type == "check":
                var = tk.BooleanVar(value=default)
                widget = tk.Checkbutton(value_frame, variable=var, bg='#2b2b2b',
                                         activebackground='#2b2b2b', fg='white')
                widget.pack(side=tk.LEFT)
                self.config_widgets[key] = var
                
            elif field_type == "float":
                var = tk.DoubleVar(value=float(default))
                widget = tk.Spinbox(value_frame, from_=-999999, to=999999, 
                                     increment=0.1, textvariable=var,
                                     bg='#3c3c3c', fg='white', relief=tk.FLAT,
                                     width=15, font=('Arial', 10))
                widget.pack(side=tk.LEFT)
                self.config_widgets[key] = var
                
            elif field_type == "int":
                var = tk.IntVar(value=int(default))
                widget = tk.Spinbox(value_frame, from_=-999999, to=999999,
                                     increment=1, textvariable=var,
                                     bg='#3c3c3c', fg='white', relief=tk.FLAT,
                                     width=15, font=('Arial', 10))
                widget.pack(side=tk.LEFT)
                self.config_widgets[key] = var
                
            elif field_type == "combo":
                var = tk.StringVar(value=default)
                widget = ttk.Combobox(value_frame, textvariable=var,
                                       values=["std", "iqr", "percentile", "none"],
                                       state="readonly", width=15)
                widget.pack(side=tk.LEFT)
                self.config_widgets[key] = var
            
            # Tooltip
            tooltip = self.get_tooltip(key)
            if tooltip:
                tooltip_label = tk.Label(field_frame, text="?", bg='#FFA500', fg='#1e1e1e',
                                          font=('Arial', 8, 'bold'), width=2)
                tooltip_label.pack(side=tk.RIGHT, padx=10)
                self.create_tooltip(tooltip_label, tooltip)
            
            row += 1
    
    def get_starting_directory(self) -> str:
        """Get the directory where cfg.yml is located as starting path for file explorers"""
        cfg_dir = get_cfg_dir(self.config_file)
        return str(cfg_dir)
    
    def browse_directory(self, key: str):
        """Open directory browser dialog starting from cfg.yml directory"""
        current_value = self.config_widgets[key].get().strip()
        starting_dir = self.get_starting_directory()
        
        # If current value is a valid directory, use it instead
        if current_value and Path(current_value).exists() and Path(current_value).is_dir():
            starting_dir = current_value
        
        directory = filedialog.askdirectory(
            title=f"Select {self.get_field_label(key)}",
            initialdir=starting_dir
        )
        
        if directory:
            # Convert to relative path if it's under the cfg.yml directory
            cfg_dir = Path(self.get_starting_directory())
            try:
                rel_path = Path(directory).relative_to(cfg_dir)
                self.config_widgets[key].delete(0, tk.END)
                self.config_widgets[key].insert(0, str(rel_path))
            except ValueError:
                # Path is not under cfg.yml directory, use absolute path
                self.config_widgets[key].delete(0, tk.END)
                self.config_widgets[key].insert(0, directory)
    
    def browse_file(self, key: str):
        """Open file browser dialog starting from cfg.yml directory"""
        current_value = self.config_widgets[key].get().strip()
        starting_dir = self.get_starting_directory()
        
        # If current value exists, try to use its parent directory
        if current_value:
            path = Path(current_value)
            if path.exists():
                if path.is_file():
                    starting_dir = str(path.parent)
                elif path.is_dir():
                    starting_dir = str(path)
            elif path.parent.exists():
                starting_dir = str(path.parent)
        
        # Determine file types based on key
        if key == "db_path":
            filetypes = [("SQLite Database", "*.db"), ("All Files", "*.*")]
            title = "Select Database File"
        else:
            filetypes = [("All Files", "*.*")]
            title = f"Select {self.get_field_label(key)}"
        
        file_path = filedialog.asksaveasfilename(
            title=title,
            initialdir=starting_dir,
            defaultextension=".db" if key == "db_path" else "",
            filetypes=filetypes
        )
        
        if file_path:
            # Convert to relative path if it's under the cfg.yml directory
            cfg_dir = Path(self.get_starting_directory())
            try:
                rel_path = Path(file_path).relative_to(cfg_dir)
                self.config_widgets[key].delete(0, tk.END)
                self.config_widgets[key].insert(0, str(rel_path))
            except ValueError:
                # Path is not under cfg.yml directory, use absolute path
                self.config_widgets[key].delete(0, tk.END)
                self.config_widgets[key].insert(0, file_path)
    
    def get_field_label(self, key: str) -> str:
        """Get the human-readable label for a field"""
        labels = {
            "base_path": "GTR2 Base Path",
            "formulas_dir": "Formulas Directory",
            "db_path": "Database Path"
        }
        return labels.get(key, key)
    
    def get_tooltip(self, key: str) -> str:
        """Get tooltip text for a field"""
        tooltips = {
            "base_path": "Root folder of your GTR2 installation (contains GameData and UserData)",
            "formulas_dir": "Directory where track-specific formula files are stored",
            "db_path": "Path to the SQLite database file for storing data points",
            "outlier_method": "std: standard deviation\niqr: interquartile range\npercentile: percentile threshold\nnone: no outlier detection",
            "outlier_threshold": "Threshold for outlier detection (higher = fewer outliers removed)",
            "outlier_min_points": "Minimum number of points required before outlier detection runs",
            "nr_last_user_laptimes": "Number of historical user lap times to keep per combo",
            "min_ratio": "Minimum allowed AI ratio (prevents extreme values)",
            "max_ratio": "Maximum allowed AI ratio (prevents extreme values)",
            "poll_interval": "How often to check for new race results (seconds)",
        }
        return tooltips.get(key, "")
    
    def create_tooltip(self, widget, text: str):
        """Create a tooltip for a widget"""
        def enter(event):
            self.tooltip = tk.Toplevel(widget)
            self.tooltip.wm_overrideredirect(True)
            self.tooltip.geometry(f"+{event.x_root + 10}+{event.y_root + 10}")
            label = tk.Label(self.tooltip, text=text, bg='#FFA500', fg='#1e1e1e',
                             font=('Arial', 9), relief=tk.SOLID, bd=1,
                             padx=5, pady=3, justify=tk.LEFT)
            label.pack()
        
        def leave(event):
            if hasattr(self, 'tooltip') and self.tooltip:
                self.tooltip.destroy()
        
        widget.bind("<Enter>", enter)
        widget.bind("<Leave>", leave)
    
    def load_configuration(self):
        """Load configuration from file into UI"""
        config = get_config_with_defaults(self.config_file)
        
        for key, widget in self.config_widgets.items():
            value = config.get(key)
            
            if isinstance(widget, tk.Entry):
                widget.delete(0, tk.END)
                widget.insert(0, str(value) if value else "")
            elif isinstance(widget, tk.BooleanVar):
                widget.set(bool(value))
            elif isinstance(widget, tk.DoubleVar):
                widget.set(float(value) if value is not None else 0.0)
            elif isinstance(widget, tk.IntVar):
                widget.set(int(value) if value is not None else 0)
            elif isinstance(widget, tk.StringVar):
                widget.set(str(value) if value else "")
    
    def save_configuration(self):
        """Save configuration from UI to file"""
        config = load_config(self.config_file)
        if config is None:
            config = DEFAULT_CONFIG.copy()
        
        changes = []
        
        for key, widget in self.config_widgets.items():
            current_value = config.get(key)
            
            if isinstance(widget, tk.Entry):
                new_value = widget.get().strip()
                if str(current_value) != new_value:
                    config[key] = new_value
                    changes.append(f"{key}: '{current_value}' -> '{new_value}'")
                    
            elif isinstance(widget, tk.BooleanVar):
                new_value = widget.get()
                if new_value != current_value:
                    config[key] = new_value
                    changes.append(f"{key}: {current_value} -> {new_value}")
                    
            elif isinstance(widget, (tk.DoubleVar, tk.IntVar)):
                new_value = widget.get()
                if new_value != current_value:
                    config[key] = new_value
                    changes.append(f"{key}: {current_value} -> {new_value}")
                    
            elif isinstance(widget, tk.StringVar):
                new_value = widget.get()
                if new_value != current_value:
                    config[key] = new_value
                    changes.append(f"{key}: '{current_value}' -> '{new_value}'")
        
        if changes:
            if save_config(config, self.config_file):
                messagebox.showinfo("Success", 
                    f"Configuration saved successfully!\n\nChanges:\n" + "\n".join(changes))
                # Update parent config if needed
                if hasattr(self.parent, 'config'):
                    self.parent.config = config
            else:
                messagebox.showerror("Error", "Failed to save configuration")
        else:
            messagebox.showinfo("No Changes", "No configuration changes were made")
