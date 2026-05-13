#!/usr/bin/env python3
"""
Backup Restore Tab for Setup Manager (Tkinter version)
Handles AIW file backup restoration
"""

import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path
from datetime import datetime
import shutil

from core_config import get_base_path


class BackupTab(tk.Frame):
    """Backup restore tab for AIW files"""
    
    def __init__(self, parent, db=None):
        super().__init__(parent)
        self.parent = parent
        self.db = db
        self.backups = []
        self.selected_backups = []
        
        self.configure(bg='#1e1e1e')
        self.setup_ui()
        self.refresh_backup_list()
    
    def setup_ui(self):
        # Info label
        info_frame = tk.Frame(self, bg='#2b2b2b', relief=tk.FLAT, bd=1)
        info_frame.pack(fill=tk.X, pady=(0, 15), padx=10)
        
        info_text = (
            "AIW Backup Restore\n\n"
            "When Autoratio modifies an AIW file, it creates a backup first.\n"
            "Use this section to restore original AIW files.\n\n"
            "Note: Restoring will undo any Autoratio changes made to that track."
        )
        info_label = tk.Label(info_frame, text=info_text, bg='#2b2b2b', fg='#FFA500',
                               justify=tk.LEFT, font=('Arial', 10))
        info_label.pack(padx=15, pady=15)
        
        # Backup list frame
        list_frame = tk.Frame(self, bg='#1e1e1e')
        list_frame.pack(fill=tk.BOTH, expand=True, pady=10, padx=10)
        
        tk.Label(list_frame, text="Available Backups:", bg='#1e1e1e', fg='white',
                 font=('Arial', 11, 'bold')).pack(anchor=tk.W, pady=(0, 5))
        
        # Listbox with scrollbar
        list_container = tk.Frame(list_frame, bg='#1e1e1e')
        list_container.pack(fill=tk.BOTH, expand=True)
        
        scrollbar = tk.Scrollbar(list_container)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.backup_listbox = tk.Listbox(list_container, bg='#2b2b2b', fg='#4CAF50',
                                          font=('Courier', 10), selectmode=tk.EXTENDED,
                                          yscrollcommand=scrollbar.set)
        self.backup_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.backup_listbox.bind('<<ListboxSelect>>', self.on_selection_change)
        scrollbar.config(command=self.backup_listbox.yview)
        
        # Buttons
        button_frame = tk.Frame(self, bg='#1e1e1e')
        button_frame.pack(pady=15, padx=10)
        
        refresh_btn = tk.Button(button_frame, text="Refresh List",
                                 bg='#2196F3', fg='white', font=('Arial', 10, 'bold'),
                                 relief=tk.FLAT, padx=15, pady=6,
                                 command=self.refresh_backup_list)
        refresh_btn.pack(side=tk.LEFT, padx=5)
        
        self.restore_selected_btn = tk.Button(button_frame, text="Restore Selected",
                                               bg='#FF9800', fg='white', font=('Arial', 10, 'bold'),
                                               relief=tk.FLAT, padx=15, pady=6,
                                               command=self.restore_selected,
                                               state=tk.DISABLED)
        self.restore_selected_btn.pack(side=tk.LEFT, padx=5)
        
        restore_all_btn = tk.Button(button_frame, text="Restore All",
                                     bg='#f44336', fg='white', font=('Arial', 10, 'bold'),
                                     relief=tk.FLAT, padx=15, pady=6,
                                     command=self.restore_all)
        restore_all_btn.pack(side=tk.LEFT, padx=5)
        
        # Status label
        self.status_label = tk.Label(self, text="", bg='#1e1e1e', fg='#888',
                                      font=('Arial', 9))
        self.status_label.pack(pady=(0, 10))
    
    def scan_aiw_backups(self):
        """Scan for AIW backup files"""
        backups = []
        seen_tracks = set()
        backup_dirs = []
        
        if self.db and hasattr(self.db, 'db_path'):
            backup_dirs.append(Path(self.db.db_path).parent / "aiw_backups")
        backup_dirs.append(Path.cwd() / "aiw_backups")
        
        for backup_dir in backup_dirs:
            if not backup_dir.exists():
                continue
            for backup_file in backup_dir.glob("*_ORIGINAL.AIW"):
                original_name = backup_file.name.replace("_ORIGINAL.AIW", ".AIW")
                track_name = original_name.replace(".AIW", "")
                
                unique_key = f"{track_name}_{original_name}"
                
                if unique_key not in seen_tracks:
                    seen_tracks.add(unique_key)
                    backups.append({
                        "track": track_name,
                        "original_file": original_name,
                        "backup_path": backup_file,
                        "backup_time": backup_file.stat().st_mtime if backup_file.exists() else 0,
                        "backup_dir": str(backup_dir)
                    })
        
        return sorted(backups, key=lambda x: x.get("track", ""))
    
    def refresh_backup_list(self):
        """Refresh the backup list display"""
        self.backup_listbox.delete(0, tk.END)
        self.backups = self.scan_aiw_backups()
        
        if not self.backups:
            self.backup_listbox.insert(tk.END, "No backups found")
            self.backup_listbox.config(fg='#888')
            return
        
        self.backup_listbox.config(fg='#4CAF50')
        for backup in self.backups:
            time_str = datetime.fromtimestamp(backup["backup_time"]).strftime("%Y-%m-%d %H:%M:%S")
            display_text = f"{backup['track']} - {backup['original_file']} (backup: {time_str})"
            self.backup_listbox.insert(tk.END, display_text)
        
        self.status_label.config(text=f"Found {len(self.backups)} backup(s)")
    
    def on_selection_change(self, event):
        """Handle selection change in listbox"""
        selection = self.backup_listbox.curselection()
        self.selected_backups = [self.backups[i] for i in selection if i < len(self.backups)]
        self.restore_selected_btn.config(state=tk.NORMAL if self.selected_backups else tk.DISABLED)
    
    def restore_aiw_backup(self, backup_info):
        """Restore a single AIW backup"""
        try:
            backup_path = backup_info["backup_path"]
            original_name = backup_info["original_file"]
            track_name = backup_info["track"]
            restore_path = None
            
            base_path = get_base_path()
            
            if base_path:
                locations_dir = base_path / "GameData" / "Locations"
                if locations_dir.exists():
                    track_lower = track_name.lower()
                    for track_dir in locations_dir.iterdir():
                        if track_dir.is_dir() and track_dir.name.lower() == track_lower:
                            aiw_path = track_dir / original_name
                            if aiw_path.exists():
                                restore_path = aiw_path
                                break
                    
                    if not restore_path:
                        for ext in ["*.AIW", "*.aiw"]:
                            for aiw_file in locations_dir.rglob(ext):
                                if aiw_file.name.lower() == original_name.lower():
                                    restore_path = aiw_file
                                    break
            
            if not restore_path:
                from tkinter import filedialog
                restore_path_str = filedialog.asksaveasfilename(
                    title="Save Restored AIW As",
                    initialdir=str(backup_path.parent),
                    initialfile=original_name,
                    defaultextension=".AIW",
                    filetypes=[("AIW Files", "*.AIW"), ("All Files", "*.*")]
                )
                if restore_path_str:
                    restore_path = Path(restore_path_str)
                else:
                    return False
            
            shutil.copy2(backup_path, restore_path)
            return True
            
        except Exception as e:
            self.status_label.config(text=f"Error restoring: {str(e)}")
            return False
    
    def restore_selected(self):
        """Restore selected backups"""
        if not self.selected_backups:
            messagebox.showwarning("No Selection", "Please select backups to restore.")
            return
        
        result = messagebox.askyesno("Confirm Restore", 
                                      f"Restore {len(self.selected_backups)} AIW file(s)?")
        if not result:
            return
        
        restored = 0
        for backup in self.selected_backups:
            if self.restore_aiw_backup(backup):
                restored += 1
        
        if restored > 0:
            messagebox.showinfo("Restore Complete", 
                                f"Successfully restored {restored} AIW file(s).")
            self.refresh_backup_list()
    
    def restore_all(self):
        """Restore all backups"""
        if not self.backups:
            messagebox.showinfo("No Backups", "No backups found to restore.")
            return
        
        result = messagebox.askyesno("Confirm Restore All", 
                                      f"Restore ALL {len(self.backups)} AIW backup(s)?")
        if not result:
            return
        
        restored = 0
        for backup in self.backups:
            if self.restore_aiw_backup(backup):
                restored += 1
        
        if restored > 0:
            messagebox.showinfo("Restore Complete", 
                                f"Successfully restored {restored} AIW file(s).")
            self.refresh_backup_list()
