#!/usr/bin/env python3
"""
Race Data Import tab for Setup Manager (Tkinter version)
Imports race data from CSV files
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import csv
import sqlite3
from pathlib import Path
from typing import List, Dict, Tuple


class ImportTab(tk.Frame):
    """Race Data Import tab"""
    
    def __init__(self, parent, db_path: str):
        super().__init__(parent)
        self.parent = parent
        self.db_path = db_path
        self.data_file_path = None
        
        self.configure(bg='#1e1e1e')
        self.setup_ui()
    
    def setup_ui(self):
        # File selection frame
        file_frame = tk.LabelFrame(self, text="Race Data File", bg='#1e1e1e', fg='#4CAF50',
                                    font=('Arial', 11, 'bold'))
        file_frame.pack(fill=tk.X, padx=10, pady=10)
        
        file_inner = tk.Frame(file_frame, bg='#1e1e1e')
        file_inner.pack(padx=10, pady=10)
        
        row1 = tk.Frame(file_inner, bg='#1e1e1e')
        row1.pack(fill=tk.X, pady=5)
        
        tk.Label(row1, text="Data File (CSV):", bg='#1e1e1e', fg='white').pack(side=tk.LEFT, padx=5)
        
        self.data_file_label = tk.Label(row1, text="No file selected", bg='#1e1e1e', 
                                         fg='#888', font=('Courier', 10))
        self.data_file_label.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        browse_btn = tk.Button(row1, text="Browse...", bg='#2196F3', fg='white',
                                command=self.browse_data_file)
        browse_btn.pack(side=tk.RIGHT, padx=5)
        
        row2 = tk.Frame(file_inner, bg='#1e1e1e')
        row2.pack(fill=tk.X, pady=5)
        
        tk.Label(row2, text="Database:", bg='#1e1e1e', fg='white').pack(side=tk.LEFT, padx=5)
        
        self.db_label = tk.Label(row2, text=self.db_path, bg='#1e1e1e',
                                  fg='#4CAF50', font=('Courier', 10))
        self.db_label.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        # Options frame
        options_frame = tk.LabelFrame(self, text="Import Options", bg='#1e1e1e', fg='#4CAF50',
                                       font=('Arial', 11, 'bold'))
        options_frame.pack(fill=tk.X, padx=10, pady=10)
        
        options_inner = tk.Frame(options_frame, bg='#1e1e1e')
        options_inner.pack(padx=10, pady=10)
        
        self.import_qual_var = tk.BooleanVar(value=True)
        qual_cb = tk.Checkbutton(options_inner, text="Import Qualifying Data",
                                  variable=self.import_qual_var,
                                  bg='#1e1e1e', fg='white', selectcolor='#1e1e1e')
        qual_cb.pack(anchor=tk.W, pady=2)
        
        self.import_race_var = tk.BooleanVar(value=True)
        race_cb = tk.Checkbutton(options_inner, text="Import Race Data",
                                  variable=self.import_race_var,
                                  bg='#1e1e1e', fg='white', selectcolor='#1e1e1e')
        race_cb.pack(anchor=tk.W, pady=2)
        
        self.skip_duplicates_var = tk.BooleanVar(value=True)
        dup_cb = tk.Checkbutton(options_inner, text="Skip Duplicates",
                                 variable=self.skip_duplicates_var,
                                 bg='#1e1e1e', fg='white', selectcolor='#1e1e1e')
        dup_cb.pack(anchor=tk.W, pady=2)
        
        # Preview frame
        preview_frame = tk.LabelFrame(self, text="Data Preview", bg='#1e1e1e', fg='#4CAF50',
                                       font=('Arial', 11, 'bold'))
        preview_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Treeview for preview
        columns = ("Vehicle", "Track", "Qual Ratio", "Race Ratio", "Qual Best", "Race Best")
        self.preview_tree = ttk.Treeview(preview_frame, columns=columns, show="headings", height=10)
        
        for col in columns:
            self.preview_tree.heading(col, text=col)
            self.preview_tree.column(col, width=120)
        
        scrollbar = ttk.Scrollbar(preview_frame, orient=tk.VERTICAL, command=self.preview_tree.yview)
        self.preview_tree.configure(yscrollcommand=scrollbar.set)
        
        self.preview_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        refresh_btn = tk.Button(preview_frame, text="Refresh Preview", bg='#2196F3', fg='white',
                                 command=self.refresh_preview)
        refresh_btn.pack(pady=5)
        
        # Progress frame
        progress_frame = tk.LabelFrame(self, text="Import Progress", bg='#1e1e1e', fg='#4CAF50',
                                        font=('Arial', 11, 'bold'))
        progress_frame.pack(fill=tk.X, padx=10, pady=10)
        
        progress_inner = tk.Frame(progress_frame, bg='#1e1e1e')
        progress_inner.pack(padx=10, pady=10, fill=tk.X)
        
        self.progress_bar = ttk.Progressbar(progress_inner, mode='determinate')
        self.progress_bar.pack(fill=tk.X, pady=5)
        
        self.progress_label = tk.Label(progress_inner, text="Ready", bg='#1e1e1e', fg='#888')
        self.progress_label.pack()
        
        # Import button
        import_btn = tk.Button(self, text="Start Import", bg='#4CAF50', fg='white',
                                font=('Arial', 12, 'bold'), padx=30, pady=10,
                                command=self.start_import)
        import_btn.pack(pady=10)
    
    def browse_data_file(self):
        """Browse for data file"""
        file_path = filedialog.askopenfilename(
            title="Select Race Data File",
            filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")]
        )
        if file_path:
            self.data_file_path = file_path
            self.data_file_label.config(text=file_path, fg='#4CAF50')
            self.refresh_preview()
    
    def refresh_preview(self):
        """Refresh the preview display"""
        # Clear tree
        for item in self.preview_tree.get_children():
            self.preview_tree.delete(item)
        
        if not self.data_file_path or not Path(self.data_file_path).exists():
            return
        
        try:
            with open(self.data_file_path, 'r', encoding='utf-8-sig') as f:
                sample = f.read(4096)
                f.seek(0)
                
                delimiter = ';' if ';' in sample else ','
                reader = csv.DictReader(f, delimiter=delimiter)
                
                for i, row in enumerate(reader):
                    if i >= 20:  # Show only first 20 rows
                        break
                    
                    self.preview_tree.insert("", tk.END, values=(
                        row.get('User Vehicle', 'Unknown')[:20],
                        row.get('Track Name', 'Unknown')[:20],
                        row.get('Current QualRatio', ''),
                        row.get('Current RaceRatio', ''),
                        row.get('Qual AI Best (s)', ''),
                        row.get('Race AI Best (s)', '')
                    ))
            
            self.progress_label.config(text=f"Preview: {i+1} rows shown")
            
        except Exception as e:
            self.progress_label.config(text=f"Error loading preview: {str(e)}")
    
    def start_import(self):
        """Start the import process"""
        if not self.data_file_path:
            messagebox.showwarning("No File", "Please select a data file first.")
            return
        
        if not Path(self.data_file_path).exists():
            messagebox.showerror("File Not Found", f"File not found: {self.data_file_path}")
            return
        
        result = messagebox.askyesno("Confirm Import",
                                      f"Import data from:\n{self.data_file_path}\n\n"
                                      f"Qualifying: {'ON' if self.import_qual_var.get() else 'OFF'}\n"
                                      f"Race: {'ON' if self.import_race_var.get() else 'OFF'}\n"
                                      f"Skip duplicates: {'ON' if self.skip_duplicates_var.get() else 'OFF'}\n\n"
                                      f"Continue?")
        
        if not result:
            return
        
        # Run import
        self.progress_bar['value'] = 0
        self.progress_label.config(text="Importing...")
        self.update()
        
        try:
            qual_added, race_added, qual_skipped, race_skipped = self.do_import()
            
            messagebox.showinfo("Import Complete",
                                 f"Qualifying points added: {qual_added}\n"
                                 f"Race points added: {race_added}\n"
                                 f"Qualifying skipped (duplicates): {qual_skipped}\n"
                                 f"Race skipped (duplicates): {race_skipped}\n\n"
                                 f"Total added: {qual_added + race_added}")
            
            self.progress_label.config(text=f"Import complete: {qual_added + race_added} points added")
            self.progress_bar['value'] = 100
            
        except Exception as e:
            messagebox.showerror("Import Error", str(e))
            self.progress_label.config(text=f"Error: {str(e)}")
    
    def do_import(self) -> Tuple[int, int, int, int]:
        """Perform the actual import"""
        qual_added = 0
        race_added = 0
        qual_skipped = 0
        race_skipped = 0
        
        with open(self.data_file_path, 'r', encoding='utf-8-sig') as f:
            sample = f.read(4096)
            f.seek(0)
            
            delimiter = ';' if ';' in sample else ','
            reader = csv.DictReader(f, delimiter=delimiter)
            rows = list(reader)
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            for i, row in enumerate(rows):
                track = row.get('Track Name', 'Unknown').strip()
                vehicle = row.get('User Vehicle', 'Unknown').strip()
                
                # Progress update
                if i % 10 == 0:
                    percent = int((i / len(rows)) * 100)
                    self.progress_bar['value'] = percent
                    self.progress_label.config(text=f"Processing: {track} ({i+1}/{len(rows)})")
                    self.update()
                
                # Qualifying data
                if self.import_qual_var.get():
                    try:
                        qual_ratio = float(row.get('Current QualRatio', '0'))
                        qual_best = float(row.get('Qual AI Best (s)', '0'))
                        qual_worst = float(row.get('Qual AI Worst (s)', '0'))
                        
                        if qual_ratio > 0 and qual_best > 0 and qual_worst > 0:
                            midpoint = (qual_best + qual_worst) / 2
                            
                            # Check for duplicates
                            if self.skip_duplicates_var.get():
                                cursor.execute("""
                                    SELECT COUNT(*) FROM data_points 
                                    WHERE track = ? AND vehicle_class = ? AND ratio = ? AND lap_time = ? AND session_type = 'qual'
                                """, (track, vehicle, qual_ratio, midpoint))
                                if cursor.fetchone()[0] > 0:
                                    qual_skipped += 1
                                else:
                                    cursor.execute("""
                                        INSERT INTO data_points (track, vehicle_class, ratio, lap_time, session_type)
                                        VALUES (?, ?, ?, ?, 'qual')
                                    """, (track, vehicle, qual_ratio, midpoint))
                                    qual_added += 1
                            else:
                                cursor.execute("""
                                    INSERT INTO data_points (track, vehicle_class, ratio, lap_time, session_type)
                                    VALUES (?, ?, ?, ?, 'qual')
                                """, (track, vehicle, qual_ratio, midpoint))
                                qual_added += 1
                    except (ValueError, KeyError):
                        pass
                
                # Race data
                if self.import_race_var.get():
                    try:
                        race_ratio = float(row.get('Current RaceRatio', '0'))
                        race_best = float(row.get('Race AI Best (s)', '0'))
                        race_worst = float(row.get('Race AI Worst (s)', '0'))
                        
                        if race_ratio > 0 and race_best > 0 and race_worst > 0:
                            midpoint = (race_best + race_worst) / 2
                            
                            if self.skip_duplicates_var.get():
                                cursor.execute("""
                                    SELECT COUNT(*) FROM data_points 
                                    WHERE track = ? AND vehicle_class = ? AND ratio = ? AND lap_time = ? AND session_type = 'race'
                                """, (track, vehicle, race_ratio, midpoint))
                                if cursor.fetchone()[0] > 0:
                                    race_skipped += 1
                                else:
                                    cursor.execute("""
                                        INSERT INTO data_points (track, vehicle_class, ratio, lap_time, session_type)
                                        VALUES (?, ?, ?, ?, 'race')
                                    """, (track, vehicle, race_ratio, midpoint))
                                    race_added += 1
                            else:
                                cursor.execute("""
                                    INSERT INTO data_points (track, vehicle_class, ratio, lap_time, session_type)
                                    VALUES (?, ?, ?, ?, 'race')
                                """, (track, vehicle, race_ratio, midpoint))
                                race_added += 1
                    except (ValueError, KeyError):
                        pass
            
            conn.commit()
            conn.close()
        
        return qual_added, race_added, qual_skipped, race_skipped
