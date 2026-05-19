#!/usr/bin/env python3
"""
Track selector dialog for Live AI Tuner - Tkinter version
Provides manual track selection from available AIW files
"""

import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path
from typing import Optional, List
import logging

from core_track_scanner import get_available_tracks

logger = logging.getLogger(__name__)


class TrackSelectorDialog:
    """Dialog for manually selecting a track from available AIW files - simple click to select"""
    
    def __init__(self, parent, base_path: Path, db_path: str = None):
        self.parent = parent
        self.base_path = base_path
        self.db_path = db_path
        self.selected_track = None
        self.dialog = None
        self.track_listbox = None
        self.search_var = None
        self.tracks = []
        self.filtered_tracks = []
    
    def show(self) -> Optional[str]:
        """Show the dialog and return the selected track name"""
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title("Select Track")
        self.dialog.geometry("450x400")
        self.dialog.minsize(400, 350)
        self.dialog.configure(bg='#2b2b2b')
        self.dialog.transient(self.parent)
        self.dialog.grab_set()
        
        self.setup_ui()
        self.scan_tracks()
        
        # Bind Escape key to close without selection
        self.dialog.bind('<Escape>', lambda e: self.cancel())
        
        self.dialog.wait_window()
        return self.selected_track
    
    def setup_ui(self):
        main_frame = tk.Frame(self.dialog, bg='#2b2b2b', padx=20, pady=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        title = tk.Label(main_frame, text="Select Track", bg='#2b2b2b',
                         fg='#FFA500', font=('Arial', 16, 'bold'))
        title.pack(pady=(0, 15))
        
        info_label = tk.Label(main_frame, text="Click on a track to select it. Press ESC to cancel.",
                              bg='#2b2b2b', fg='#888', font=('Arial', 10))
        info_label.pack(pady=(0, 10))
        
        # Search frame
        search_frame = tk.Frame(main_frame, bg='#2b2b2b')
        search_frame.pack(fill=tk.X, pady=(0, 10))
        
        tk.Label(search_frame, text="Search:", bg='#2b2b2b', fg='white').pack(side=tk.LEFT, padx=(0, 10))
        self.search_var = tk.StringVar()
        self.search_var.trace('w', lambda *args: self.filter_tracks())
        search_entry = tk.Entry(search_frame, textvariable=self.search_var, bg='#3c3c3c',
                                 fg='white', font=('Arial', 10), relief=tk.FLAT)
        search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Track list with scrollbar
        list_frame = tk.Frame(main_frame, bg='#2b2b2b')
        list_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        scrollbar = tk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.track_listbox = tk.Listbox(list_frame, bg='#1e1e1e', fg='#4CAF50',
                                         font=('Courier', 11), selectmode=tk.SINGLE,
                                         yscrollcommand=scrollbar.set)
        self.track_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.track_listbox.yview)
        
        # Bind click to select and close
        self.track_listbox.bind('<ButtonRelease-1>', self.on_track_selected)
        
        # Status label
        self.status_label = tk.Label(main_frame, text="", bg='#2b2b2b', fg='#888',
                                      font=('Arial', 9))
        self.status_label.pack(pady=(0, 10))
    
    def scan_tracks(self):
        """Scan for available tracks using the unified scanner"""
        if not self.base_path or not self.base_path.exists():
            self.status_label.config(text="Base path not configured", fg='#f44336')
            return
        
        self.tracks = get_available_tracks(self.base_path, self.db_path)
        
        if not self.tracks:
            self.status_label.config(text="No tracks found", fg='#f44336')
            return
        
        self.filtered_tracks = self.tracks.copy()
        self.update_listbox()
        self.status_label.config(text=f"Found {len(self.tracks)} tracks (click to select)")
    
    def filter_tracks(self):
        """Filter tracks based on search text"""
        search_text = self.search_var.get().lower()
        if search_text:
            self.filtered_tracks = [t for t in self.tracks if search_text in t.lower()]
        else:
            self.filtered_tracks = self.tracks.copy()
        self.update_listbox()
    
    def update_listbox(self):
        """Update the listbox with filtered tracks"""
        self.track_listbox.delete(0, tk.END)
        for track in self.filtered_tracks:
            self.track_listbox.insert(tk.END, track)
        
        if not self.filtered_tracks:
            self.track_listbox.insert(tk.END, "No tracks found")
            self.track_listbox.config(fg='#888')
        else:
            self.track_listbox.config(fg='#4CAF50')
    
    def on_track_selected(self, event):
        """Handle track selection - select on click and close"""
        selection = self.track_listbox.curselection()
        if selection and self.filtered_tracks:
            idx = selection[0]
            if idx < len(self.filtered_tracks):
                self.selected_track = self.filtered_tracks[idx]
                self.dialog.destroy()
    
    def cancel(self):
        """Cancel the selection"""
        self.selected_track = None
        self.dialog.destroy()
