#!/usr/bin/env python3
"""
Base path selection dialog for Live AI Tuner - Tkinter version
"""

from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox


class BasePathSelectionDialog:
    """Dialog to select GTR2 installation base path using tkinter"""
    
    def __init__(self, parent=None):
        self.parent = parent
        self.selected_path = None
        self.dialog = None
        self.path_var = None
    
    def show(self):
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title("Select GTR2 Installation Path")
        self.dialog.geometry("600x300")
        self.dialog.resizable(False, False)
        self.dialog.configure(bg='#2b2b2b')
        self.dialog.transient(self.parent)
        self.dialog.grab_set()
        
        self.setup_ui()
        
        self.dialog.wait_window()
        return self.selected_path is not None
    
    def setup_ui(self):
        main_frame = tk.Frame(self.dialog, bg='#2b2b2b', padx=25, pady=25)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        title = tk.Label(main_frame, text="GTR2 Installation Path", bg='#2b2b2b',
                          fg='#FFA500', font=('Arial', 16, 'bold'))
        title.pack(pady=(0, 15))
        
        desc = tk.Label(main_frame,
                         text="Please select the root folder of your GTR2 installation.\n\n"
                              "This folder should contain the 'GameData' and 'UserData' directories.\n"
                              "Example: C:\\GTR2 or /home/user/GTR2",
                         bg='#2b2b2b', fg='#aaa', justify=tk.LEFT)
        desc.pack(pady=(0, 15))
        
        path_frame = tk.Frame(main_frame, bg='#2b2b2b')
        path_frame.pack(fill=tk.X, pady=10)
        
        tk.Label(path_frame, text="Path:", bg='#2b2b2b', fg='white').pack(side=tk.LEFT, padx=(0, 10))
        
        self.path_var = tk.StringVar()
        path_entry = tk.Entry(path_frame, textvariable=self.path_var, bg='#3c3c3c',
                               fg='white', font=('Arial', 11), relief=tk.FLAT)
        path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        
        browse_btn = tk.Button(path_frame, text="Browse...", bg='#2196F3', fg='white',
                                font=('Arial', 10), relief=tk.FLAT, padx=12, pady=4,
                                command=self.browse_path)
        browse_btn.pack(side=tk.RIGHT)
        
        self.validation_label = tk.Label(main_frame, text="", bg='#2b2b2b', fg='#FFA500',
                                          font=('Arial', 9))
        self.validation_label.pack(pady=10)
        
        button_frame = tk.Frame(main_frame, bg='#2b2b2b')
        button_frame.pack(pady=(20, 0))
        
        cancel_btn = tk.Button(button_frame, text="Cancel", bg='#f44336', fg='white',
                                font=('Arial', 11, 'bold'), relief=tk.FLAT, padx=20, pady=8,
                                command=self.cancel)
        cancel_btn.pack(side=tk.LEFT, padx=10)
        
        ok_btn = tk.Button(button_frame, text="OK", bg='#4CAF50', fg='white',
                            font=('Arial', 11, 'bold'), relief=tk.FLAT, padx=20, pady=8,
                            command=self.accept)
        ok_btn.pack(side=tk.LEFT, padx=10)
        
        self.dialog.bind('<Return>', lambda e: self.accept())
        self.dialog.bind('<Escape>', lambda e: self.cancel())
    
    def browse_path(self):
        directory = filedialog.askdirectory(
            title="Select GTR2 Installation Directory",
            parent=self.dialog
        )
        if directory:
            self.path_var.set(directory)
            self.validate_path(directory)
    
    def validate_path(self, path_str: str) -> bool:
        path = Path(path_str)
        
        if not path.exists():
            self.validation_label.config(text="X Path does not exist", fg='#f44336')
            return False
        
        game_data = path / "GameData"
        user_data = path / "UserData"
        
        if not game_data.exists():
            self.validation_label.config(text="X GameData directory not found in this path", fg='#f44336')
            return False
        
        if not user_data.exists():
            self.validation_label.config(text="X UserData directory not found in this path", fg='#f44336')
            return False
        
        log_results = user_data / "Log" / "Results"
        if not log_results.exists():
            self.validation_label.config(text="! Log/Results directory not found (may be created later)", fg='#FFA500')
        else:
            self.validation_label.config(text="Valid GTR2 installation path", fg='#4CAF50')
        
        return True
    
    def accept(self):
        path_str = self.path_var.get().strip()
        
        if not path_str:
            self.validation_label.config(text="X Please select a path", fg='#f44336')
            return
        
        if self.validate_path(path_str):
            self.selected_path = Path(path_str)
            self.dialog.destroy()
        else:
            reply = messagebox.askyesno(
                "Continue Anyway?",
                "The selected path does not appear to be a valid GTR2 installation.\n"
                "The application may not work correctly.\n\n"
                "Continue anyway?",
                parent=self.dialog
            )
            if reply:
                self.selected_path = Path(path_str)
                self.dialog.destroy()
    
    def cancel(self):
        self.selected_path = None
        self.dialog.destroy()
