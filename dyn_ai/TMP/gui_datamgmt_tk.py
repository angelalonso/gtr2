#!/usr/bin/env python3
"""
Data Management Tab for Setup Manager (Tkinter version)
Launches the standalone Data Manager application
"""

import tkinter as tk
from tkinter import ttk, messagebox
import subprocess
import sys
from pathlib import Path


class DataManagementTab(tk.Frame):
    """Data Management tab - launches the external Data Manager"""
    
    def __init__(self, parent, db_path: str = "ai_data.db"):
        super().__init__(parent)
        self.parent = parent
        self.db_path = db_path
        
        self.configure(bg='#1e1e1e')
        self.setup_ui()
        self.refresh_stats()
    
    def setup_ui(self):
        # Info section
        info_frame = tk.Frame(self, bg='#2b2b2b', relief=tk.FLAT, bd=1)
        info_frame.pack(fill=tk.X, pady=(0, 20), padx=10)
        
        info_text = (
            "Data Management\n\n"
            "This tool allows you to:\n"
            "• View and edit all data points (lap times and ratios)\n"
            "• Filter by track, vehicle class, and session type\n"
            "• Delete outliers or incorrect data points\n"
            "• Manage vehicle classes and assignments\n"
            "• Import race data from CSV files\n\n"
            "Click the button below to open the Data Manager."
        )
        info_label = tk.Label(info_frame, text=info_text, bg='#2b2b2b', fg='#FFA500',
                               justify=tk.LEFT, font=('Arial', 10))
        info_label.pack(padx=15, pady=15)
        
        # Stats section
        stats_frame = tk.LabelFrame(self, text="Database Statistics", bg='#1e1e1e',
                                     fg='#4CAF50', font=('Arial', 11, 'bold'))
        stats_frame.pack(fill=tk.X, pady=10, padx=10)
        
        self.stats_text = tk.Text(stats_frame, bg='#2b2b2b', fg='#888',
                                   font=('Courier', 10), height=8,
                                   relief=tk.FLAT, wrap=tk.WORD)
        self.stats_text.pack(fill=tk.X, padx=10, pady=10)
        
        # Refresh button for stats
        refresh_stats_btn = tk.Button(stats_frame, text="Refresh Statistics",
                                       bg='#2196F3', fg='white', font=('Arial', 9),
                                       relief=tk.FLAT, padx=10, pady=4,
                                       command=self.refresh_stats)
        refresh_stats_btn.pack(pady=(0, 10))
        
        # Launch button
        button_frame = tk.Frame(self, bg='#1e1e1e')
        button_frame.pack(pady=30)
        
        launch_btn = tk.Button(button_frame, text="Open Dyn AI Data Manager",
                                bg='#9C27B0', fg='white', font=('Arial', 12, 'bold'),
                                relief=tk.FLAT, padx=30, pady=12,
                                command=self.launch_data_manager)
        launch_btn.pack()
        
        # Status
        self.status_label = tk.Label(self, text="Ready", bg='#1e1e1e', fg='#888',
                                      font=('Arial', 9))
        self.status_label.pack(pady=(20, 0))
    
    def refresh_stats(self):
        """Refresh database statistics display"""
        try:
            import sqlite3
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM data_points")
            total_points = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(DISTINCT track) FROM data_points")
            total_tracks = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(DISTINCT vehicle_class) FROM data_points")
            total_classes = cursor.fetchone()[0]
            
            cursor.execute("SELECT session_type, COUNT(*) FROM data_points GROUP BY session_type")
            by_session = cursor.fetchall()
            
            cursor.execute("SELECT COUNT(*) FROM race_sessions")
            total_races = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM formulas")
            total_formulas = cursor.fetchone()[0]
            
            conn.close()
            
            stats = f"""Total Data Points: {total_points}
Unique Tracks: {total_tracks}
Unique Vehicle Classes: {total_classes}
Total Race Sessions: {total_races}
Saved Formulas: {total_formulas}

By Session Type:"""
            
            for session, count in by_session:
                stats += f"\n  {session}: {count}"
            
            self.stats_text.delete(1.0, tk.END)
            self.stats_text.insert(1.0, stats)
            self.stats_text.config(fg='#4CAF50')
            
        except Exception as e:
            self.stats_text.delete(1.0, tk.END)
            self.stats_text.insert(1.0, f"Error reading database: {str(e)}")
            self.stats_text.config(fg='#f44336')
    
    def launch_data_manager(self):
        """Launch the data manager application"""
        from gui_common import get_data_file_path
        script_dir = get_data_file_path("")
        exe_path = script_dir / "datamgmt_dyn_ai.exe"
        py_path = script_dir / "dyn_ai_data_manager.py"
        
        self.status_label.config(text="Launching Data Manager...")
        self.update()
        
        try:
            if exe_path.exists():
                subprocess.Popen([str(exe_path)], shell=False)
                self.status_label.config(text="Data Manager launched")
            elif py_path.exists():
                python_exe = sys.executable
                subprocess.Popen([python_exe, str(py_path)], shell=False)
                self.status_label.config(text="Data Manager launched")
            else:
                messagebox.showerror("File Not Found", 
                    "Data Manager not found in the application directory.\n\n"
                    f"Expected locations:\n{exe_path}\n{py_path}")
                self.status_label.config(text="Ready")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to start Data Manager:\n{str(e)}")
            self.status_label.config(text=f"Error: {str(e)[:50]}")
