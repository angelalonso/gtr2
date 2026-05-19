#!/usr/bin/env python3
"""
Laptimes and Ratios tab for Setup Manager (Tkinter version)
Provides database editing with graph visualization and multi-select support
"""

import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3
from pathlib import Path
from typing import List, Tuple


class LaptimesTab(tk.Frame):
    """Laptimes and Ratios tab for managing data points"""
    
    def __init__(self, parent, db_path: str):
        super().__init__(parent)
        self.parent = parent
        self.db_path = db_path
        self.current_points = []
        self.selected_point_ids = set()
        
        self.configure(bg='#1e1e1e')
        self.setup_ui()
        self.refresh_filters()
        self.refresh_table()
    
    def setup_ui(self):
        # Filter frame
        filter_frame = tk.LabelFrame(self, text="Filter Data Points", 
                                      bg='#1e1e1e', fg='#4CAF50',
                                      font=('Arial', 11, 'bold'))
        filter_frame.pack(fill=tk.X, padx=10, pady=10)
        
        filter_inner = tk.Frame(filter_frame, bg='#1e1e1e')
        filter_inner.pack(padx=10, pady=10)
        
        # Row 1
        row1 = tk.Frame(filter_inner, bg='#1e1e1e')
        row1.pack(fill=tk.X, pady=5)
        
        tk.Label(row1, text="Track:", bg='#1e1e1e', fg='white').pack(side=tk.LEFT, padx=5)
        self.track_filter = ttk.Combobox(row1, values=["All"], state="readonly", width=25)
        self.track_filter.pack(side=tk.LEFT, padx=5)
        self.track_filter.bind("<<ComboboxSelected>>", self.on_filter_changed)
        
        tk.Label(row1, text="Vehicle Class:", bg='#1e1e1e', fg='white').pack(side=tk.LEFT, padx=(20, 5))
        self.class_filter = ttk.Combobox(row1, values=["All"], state="readonly", width=25)
        self.class_filter.pack(side=tk.LEFT, padx=5)
        self.class_filter.bind("<<ComboboxSelected>>", self.on_filter_changed)
        
        tk.Label(row1, text="Session:", bg='#1e1e1e', fg='white').pack(side=tk.LEFT, padx=(20, 5))
        self.session_filter = ttk.Combobox(row1, values=["All", "qual", "race"], state="readonly", width=15)
        self.session_filter.pack(side=tk.LEFT, padx=5)
        self.session_filter.bind("<<ComboboxSelected>>", self.on_filter_changed)
        
        # Row 2
        row2 = tk.Frame(filter_inner, bg='#1e1e1e')
        row2.pack(fill=tk.X, pady=5)
        
        refresh_btn = tk.Button(row2, text="Refresh Filters", bg='#2196F3', fg='white',
                                 command=self.refresh_filters)
        refresh_btn.pack(side=tk.LEFT, padx=5)
        
        apply_btn = tk.Button(row2, text="Apply Filter", bg='#4CAF50', fg='white',
                               command=self.refresh_table)
        apply_btn.pack(side=tk.LEFT, padx=5)
        
        # Table frame
        table_frame = tk.LabelFrame(self, text="Data Points", bg='#1e1e1e', fg='#4CAF50',
                                     font=('Arial', 11, 'bold'))
        table_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Treeview for data
        columns = ("ID", "Track", "Vehicle Class", "Ratio", "Lap Time (s)", "Session", "Created At")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=15)
        
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=100)
        
        self.tree.column("ID", width=50)
        self.tree.column("Track", width=120)
        self.tree.column("Vehicle Class", width=120)
        self.tree.column("Ratio", width=100)
        self.tree.column("Lap Time (s)", width=100)
        self.tree.column("Session", width=80)
        self.tree.column("Created At", width=150)
        
        scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Selection bindings
        self.tree.bind("<<TreeviewSelect>>", self.on_selection_changed)
        
        # Action buttons
        action_frame = tk.Frame(table_frame, bg='#1e1e1e')
        action_frame.pack(fill=tk.X, pady=10)
        
        select_all_btn = tk.Button(action_frame, text="Select All", bg='#2196F3', fg='white',
                                    command=self.select_all)
        select_all_btn.pack(side=tk.LEFT, padx=5)
        
        self.edit_btn = tk.Button(action_frame, text="Edit Selected", bg='#FF9800', fg='white',
                                   command=self.edit_selected, state=tk.DISABLED)
        self.edit_btn.pack(side=tk.LEFT, padx=5)
        
        self.delete_btn = tk.Button(action_frame, text="Delete Selected", bg='#f44336', fg='white',
                                     command=self.delete_selected, state=tk.DISABLED)
        self.delete_btn.pack(side=tk.LEFT, padx=5)
        
        # Status
        self.status_label = tk.Label(self, text="Ready", bg='#1e1e1e', fg='#888')
        self.status_label.pack(pady=5)
    
    def get_tracks(self) -> List[str]:
        """Get all unique tracks from database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT track FROM data_points ORDER BY track")
        tracks = [row[0] for row in cursor.fetchall()]
        conn.close()
        return tracks
    
    def get_classes(self) -> List[str]:
        """Get all unique vehicle classes from database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT vehicle_class FROM data_points ORDER BY vehicle_class")
        classes = [row[0] for row in cursor.fetchall()]
        conn.close()
        return classes
    
    def refresh_filters(self):
        """Refresh filter dropdowns"""
        current_track = self.track_filter.get()
        current_class = self.class_filter.get()
        
        tracks = ["All"] + self.get_tracks()
        classes = ["All"] + self.get_classes()
        
        self.track_filter['values'] = tracks
        self.class_filter['values'] = classes
        
        if current_track in tracks:
            self.track_filter.set(current_track)
        else:
            self.track_filter.set("All")
        
        if current_class in classes:
            self.class_filter.set(current_class)
        else:
            self.class_filter.set("All")
    
    def refresh_table(self):
        """Refresh the table with current filters"""
        track = self.track_filter.get()
        if track == "All":
            track = None
        
        vehicle_class = self.class_filter.get()
        if vehicle_class == "All":
            vehicle_class = None
        
        session_type = self.session_filter.get()
        if session_type == "All":
            session_type = None
        
        # Build query
        query = """
            SELECT id, track, vehicle_class, ratio, lap_time, session_type, created_at 
            FROM data_points WHERE 1=1
        """
        params = []
        
        if track:
            query += " AND track = ?"
            params.append(track)
        
        if vehicle_class:
            query += " AND vehicle_class = ?"
            params.append(vehicle_class)
        
        if session_type:
            query += " AND session_type = ?"
            params.append(session_type)
        
        query += " ORDER BY track, vehicle_class, ratio"
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(query, params)
        self.current_points = cursor.fetchall()
        conn.close()
        
        # Clear tree
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        # Insert data
        for point in self.current_points:
            self.tree.insert("", tk.END, values=(
                point[0], point[1], point[2], f"{point[3]:.6f}", 
                f"{point[4]:.3f}", point[5], point[6] if len(point) > 6 else ""
            ))
        
        self.status_label.config(text=f"Found {len(self.current_points)} data points")
        self.selected_point_ids.clear()
        self.update_button_states()
    
    def on_filter_changed(self, event=None):
        """Handle filter change"""
        self.selected_point_ids.clear()
        self.refresh_table()
    
    def on_selection_changed(self, event=None):
        """Handle selection change in tree"""
        selected = self.tree.selection()
        self.selected_point_ids.clear()
        
        for item in selected:
            values = self.tree.item(item)['values']
            if values:
                self.selected_point_ids.add(int(values[0]))
        
        self.update_button_states()
    
    def update_button_states(self):
        """Update button enabled states"""
        has_selection = len(self.selected_point_ids) > 0
        self.edit_btn.config(state=tk.NORMAL if has_selection else tk.DISABLED)
        self.delete_btn.config(state=tk.NORMAL if has_selection else tk.DISABLED)
        
        if has_selection:
            self.status_label.config(text=f"{len(self.selected_point_ids)} data point(s) selected")
        else:
            self.status_label.config(text=f"Found {len(self.current_points)} data points")
    
    def select_all(self):
        """Select all data points"""
        self.tree.selection_set(self.tree.get_children())
    
    def edit_selected(self):
        """Edit selected data points"""
        if not self.selected_point_ids:
            messagebox.showwarning("No Selection", "Please select data points to edit.")
            return
        
        # Simple edit dialog for now - can be expanded
        selected_points = [p for p in self.current_points if p[0] in self.selected_point_ids]
        
        if not selected_points:
            return
        
        # Show edit dialog for first selected point
        point = selected_points[0]
        
        dialog = tk.Toplevel(self)
        dialog.title(f"Edit Data Point (ID: {point[0]})")
        dialog.geometry("400x350")
        dialog.configure(bg='#2b2b2b')
        dialog.transient(self)
        dialog.grab_set()
        
        frame = tk.Frame(dialog, bg='#2b2b2b', padx=20, pady=20)
        frame.pack(fill=tk.BOTH, expand=True)
        
        tk.Label(frame, text="Track:", bg='#2b2b2b', fg='white').pack(anchor=tk.W, pady=5)
        track_entry = tk.Entry(frame, bg='#3c3c3c', fg='white', width=40)
        track_entry.insert(0, point[1])
        track_entry.pack(fill=tk.X, pady=5)
        
        tk.Label(frame, text="Vehicle Class:", bg='#2b2b2b', fg='white').pack(anchor=tk.W, pady=5)
        class_entry = tk.Entry(frame, bg='#3c3c3c', fg='white', width=40)
        class_entry.insert(0, point[2])
        class_entry.pack(fill=tk.X, pady=5)
        
        tk.Label(frame, text="Ratio:", bg='#2b2b2b', fg='white').pack(anchor=tk.W, pady=5)
        ratio_entry = tk.Entry(frame, bg='#3c3c3c', fg='white', width=40)
        ratio_entry.insert(0, f"{point[3]:.6f}")
        ratio_entry.pack(fill=tk.X, pady=5)
        
        tk.Label(frame, text="Lap Time (seconds):", bg='#2b2b2b', fg='white').pack(anchor=tk.W, pady=5)
        time_entry = tk.Entry(frame, bg='#3c3c3c', fg='white', width=40)
        time_entry.insert(0, f"{point[4]:.3f}")
        time_entry.pack(fill=tk.X, pady=5)
        
        tk.Label(frame, text="Session Type:", bg='#2b2b2b', fg='white').pack(anchor=tk.W, pady=5)
        session_combo = ttk.Combobox(frame, values=["qual", "race"], state="readonly")
        session_combo.set(point[5])
        session_combo.pack(fill=tk.X, pady=5)
        
        def save_changes():
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                for pid in self.selected_point_ids:
                    cursor.execute("""
                        UPDATE data_points 
                        SET track = ?, vehicle_class = ?, ratio = ?, lap_time = ?, session_type = ?
                        WHERE id = ?
                    """, (track_entry.get(), class_entry.get(), float(ratio_entry.get()),
                          float(time_entry.get()), session_combo.get(), pid))
                
                conn.commit()
                conn.close()
                
                messagebox.showinfo("Success", f"Updated {len(self.selected_point_ids)} data point(s)")
                dialog.destroy()
                self.refresh_table()
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to update: {str(e)}")
        
        button_frame = tk.Frame(frame, bg='#2b2b2b')
        button_frame.pack(pady=20)
        
        tk.Button(button_frame, text="Cancel", command=dialog.destroy,
                  bg='#555', fg='white', padx=15, pady=5).pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="Save", command=save_changes,
                  bg='#4CAF50', fg='white', padx=15, pady=5).pack(side=tk.LEFT, padx=5)
    
    def delete_selected(self):
        """Delete selected data points"""
        if not self.selected_point_ids:
            messagebox.showwarning("No Selection", "Please select data points to delete.")
            return
        
        result = messagebox.askyesno("Confirm Delete",
                                      f"Delete {len(self.selected_point_ids)} selected data point(s)?\n\nThis action cannot be undone.")
        
        if not result:
            return
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            for pid in self.selected_point_ids:
                cursor.execute("DELETE FROM data_points WHERE id = ?", (pid,))
            
            conn.commit()
            conn.close()
            
            messagebox.showinfo("Success", f"Deleted {len(self.selected_point_ids)} data point(s)")
            self.selected_point_ids.clear()
            self.refresh_table()
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to delete: {str(e)}")
