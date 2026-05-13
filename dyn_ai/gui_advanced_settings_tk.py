#!/usr/bin/env python3
"""
Configuration Tab for Setup Manager (Tkinter version)
Handles editing cfg.yml settings
"""

import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path

from core_config import (
    load_config, save_config, get_config_with_defaults, DEFAULT_CONFIG,
    get_ratio_limits, get_nr_last_user_laptimes, get_outlier_settings
)


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
        
        canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
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
        fields = [
            ("base_path", "GTR2 Base Path:", "entry", ""),
            ("formulas_dir", "Formulas Directory:", "entry", "./track_formulas"),
            ("db_path", "Database Path:", "entry", "ai_data.db"),
            ("auto_apply", "Auto Apply:", "check", False),
            ("backup_enabled", "Backup Enabled:", "check", True),
            ("logging_enabled", "Logging Enabled:", "check", False),
            ("autopilot_enabled", "Autopilot Enabled:", "check", False),
            ("autopilot_silent", "Autopilot Silent:", "check", False),
            ("poll_interval", "Poll Interval (seconds):", "float", 5.0),
            ("min_ratio", "Minimum Ratio:", "float", 0.5),
            ("max_ratio", "Maximum Ratio:", "float", 1.5),
            ("nr_last_user_laptimes", "Number of Last User Laptimes to Keep:", "int", 1),
            ("outlier_method", "Outlier Detection Method:", "combo", "std"),
            ("outlier_threshold", "Outlier Threshold:", "float", 2.0),
            ("outlier_min_points", "Min Points for Outlier Detection:", "int", 3),
        ]
        
        row = 0
        for key, label, field_type, default in fields:
            # Label frame for each field
            field_frame = tk.Frame(self.scrollable_frame, bg='#2b2b2b', relief=tk.FLAT, bd=1)
            field_frame.pack(fill=tk.X, pady=5, padx=10)
            
            label_widget = tk.Label(field_frame, text=label, bg='#2b2b2b', fg='white',
                                     width=30, anchor='w', font=('Arial', 10))
            label_widget.pack(side=tk.LEFT, padx=10, pady=8)
            
            if field_type == "entry":
                widget = tk.Entry(field_frame, bg='#3c3c3c', fg='white',
                                   font=('Arial', 10), relief=tk.FLAT)
                widget.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=10, pady=8)
                self.config_widgets[key] = widget
                
            elif field_type == "check":
                var = tk.BooleanVar(value=default)
                widget = tk.Checkbutton(field_frame, variable=var, bg='#2b2b2b',
                                         activebackground='#2b2b2b', fg='white')
                widget.pack(side=tk.LEFT, padx=10, pady=8)
                self.config_widgets[key] = var
                
            elif field_type == "float":
                var = tk.DoubleVar(value=float(default))
                widget = tk.Spinbox(field_frame, from_=-999999, to=999999, 
                                     increment=0.1, textvariable=var,
                                     bg='#3c3c3c', fg='white', relief=tk.FLAT,
                                     width=15, font=('Arial', 10))
                widget.pack(side=tk.LEFT, padx=10, pady=8)
                self.config_widgets[key] = var
                
            elif field_type == "int":
                var = tk.IntVar(value=int(default))
                widget = tk.Spinbox(field_frame, from_=-999999, to=999999,
                                     increment=1, textvariable=var,
                                     bg='#3c3c3c', fg='white', relief=tk.FLAT,
                                     width=15, font=('Arial', 10))
                widget.pack(side=tk.LEFT, padx=10, pady=8)
                self.config_widgets[key] = var
                
            elif field_type == "combo":
                var = tk.StringVar(value=default)
                widget = ttk.Combobox(field_frame, textvariable=var,
                                       values=["std", "iqr", "percentile", "none"],
                                       state="readonly", width=15)
                widget.pack(side=tk.LEFT, padx=10, pady=8)
                self.config_widgets[key] = var
            
            # Tooltip
            tooltip = self.get_tooltip(key)
            if tooltip:
                tooltip_label = tk.Label(field_frame, text="?", bg='#FFA500', fg='#1e1e1e',
                                          font=('Arial', 8, 'bold'), width=2)
                tooltip_label.pack(side=tk.RIGHT, padx=10)
                self.create_tooltip(tooltip_label, tooltip)
            
            row += 1
    
    def get_tooltip(self, key: str) -> str:
        """Get tooltip text for a field"""
        tooltips = {
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
