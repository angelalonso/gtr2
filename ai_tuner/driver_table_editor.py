#!/usr/bin/env python3
# driver_table_editor.py - Editable driver data table

import tkinter as tk
from tkinter import ttk, messagebox
import pandas as pd
import os
import threading
from debug_logger import logger

class DriverTableEditor:
    """Editable driver data table with variables as rows and drivers as columns"""
    
    def __init__(self, data, fieldnames, csv_file_path, install_folder=None, teams_folder=None):
        self.data = data  # List of dictionaries
        self.fieldnames = fieldnames  # List of column names
        self.csv_file_path = csv_file_path
        self.install_folder = install_folder
        self.teams_folder = teams_folder
        
        # Fields to exclude
        self.excluded_fields = ['Abbreviation', 'Nationality', 'NatAbbrev', 'Script']
        
        # Convert to DataFrame for easier manipulation
        self.df = pd.DataFrame(data)
        
        # Track changes
        self.changes_made = False
        self.cell_widgets = {}  # Store references to cell widgets
        
        self.root = tk.Toplevel()
        self.root.title(f"GTR2 Driver Data Editor - {os.path.basename(csv_file_path)}")
        self.root.geometry("1400x800")
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the user interface"""
        # Main container
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Title and buttons frame
        header_frame = ttk.Frame(main_frame)
        header_frame.grid(row=0, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # Title
        title_label = ttk.Label(
            header_frame, 
            text=f"🚗 GTR2 Driver Data Editor", 
            font=("Arial", 14, "bold")
        )
        title_label.pack(side=tk.LEFT)
        
        # Control buttons
        button_frame = ttk.Frame(header_frame)
        button_frame.pack(side=tk.RIGHT)
        
        # Single Save button that does both CSV and RCD updates
        self.save_button = ttk.Button(
            button_frame, 
            text="Save", 
            command=self.save_all,
            state='normal'
        )
        self.save_button.pack(side=tk.LEFT, padx=2)
        
        ttk.Button(button_frame, text="Close", command=self.on_close).pack(side=tk.LEFT, padx=2)
        
        # Statistics
        stats_text = f"Drivers: {len(self.df)} | Editable Variables: {len(self.get_variables())}"
        stats_label = ttk.Label(main_frame, text=stats_text)
        stats_label.grid(row=1, column=0, columnspan=3, pady=(0, 10))
        
        # Filter frame
        filter_frame = ttk.Frame(main_frame)
        filter_frame.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        
        ttk.Label(filter_frame, text="Filter:").pack(side=tk.LEFT, padx=(0, 5))
        self.filter_var = tk.StringVar()
        filter_entry = ttk.Entry(filter_frame, textvariable=self.filter_var, width=30)
        filter_entry.pack(side=tk.LEFT, padx=(0, 5))
        
        ttk.Button(filter_frame, text="Apply", command=self.apply_filter).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(filter_frame, text="Clear", command=self.clear_filter).pack(side=tk.LEFT)
        
        # Table frame with scrollbars
        table_frame = ttk.Frame(main_frame)
        table_frame.grid(row=3, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Create canvas and scrollbars
        canvas = tk.Canvas(table_frame, bg='white')
        h_scrollbar = ttk.Scrollbar(table_frame, orient="horizontal", command=canvas.xview)
        v_scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=canvas.yview)
        
        # Configure canvas
        canvas.configure(xscrollcommand=h_scrollbar.set, yscrollcommand=v_scrollbar.set)
        
        # Create inner frame for table
        self.table_inner = ttk.Frame(canvas)
        
        # Create window in canvas
        canvas_window = canvas.create_window((0, 0), window=self.table_inner, anchor="nw")
        
        # Grid scrollbars and canvas
        canvas.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        v_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        h_scrollbar.grid(row=1, column=0, sticky=(tk.W, tk.E))
        
        # Configure grid weights
        table_frame.columnconfigure(0, weight=1)
        table_frame.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(3, weight=1)
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        
        # Bind events for scrolling
        self.table_inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda e: self.on_canvas_configure(canvas, canvas_window))
        
        # Create table
        self.create_table()
        
        # Status bar
        self.status_label = ttk.Label(main_frame, text="Ready", foreground="green")
        self.status_label.grid(row=4, column=0, columnspan=3, pady=(10, 0))
        
        # Bind filter entry to apply on Enter key
        filter_entry.bind("<Return>", lambda e: self.apply_filter())
    
    def get_variables(self):
        """Get the list of variables to display (excluding metadata and excluded fields)"""
        metadata_columns = ['Driver', 'Source_CAR_File', 'CAR_File_Path', 'Original_CAR_Name']
        
        # Get all columns that are not metadata or excluded
        all_columns = list(self.df.columns)
        variables = [col for col in all_columns 
                    if col not in metadata_columns and col not in self.excluded_fields]
        
        # Sort in logical order (GTR2 variable order)
        standard_order = [
            'StartsDry', 'StartsWet', 'StartStalls', 
            'QualifyingAbility', 'RaceAbility', 'Consistency', 'RainAbility',
            'Passing', 'Crash', 'Recovery', 'CompletedLaps%',
            'TrackAggression', 'CorneringAdd', 'CorneringMult',
            'TCGripThreshold', 'TCThrottleFract', 'TCResponse',
            'MinRacingSkill', 'Composure',
            'RaceColdBrainMin', 'RaceColdBrainTime', 'QualColdBrainMin', 'QualColdBrainTime'
        ]
        
        # Sort variables: standard ones first in order, then others alphabetically
        sorted_vars = []
        for var in standard_order:
            if var in variables:
                sorted_vars.append(var)
                variables.remove(var)
        
        # Add remaining variables alphabetically
        sorted_vars.extend(sorted(variables))
        
        return sorted_vars
    
    def create_table(self):
        """Create the editable table with variables as rows and drivers as columns"""
        # Clear existing widgets
        for widget in self.table_inner.winfo_children():
            widget.destroy()
        
        # Clear cell widgets dictionary
        self.cell_widgets.clear()
        
        # Get drivers and variables
        drivers = list(self.df['Driver'])
        variables = self.get_variables()
        
        # Create header row with driver names
        ttk.Label(self.table_inner, text="Variable", font=("Arial", 10, "bold"), 
                 relief="solid", borderwidth=1, width=20, background="#f0f0f0").grid(
                     row=0, column=0, sticky="nsew")
        
        for col, driver in enumerate(drivers, 1):
            # Truncate long driver names
            display_name = driver[:20] + "..." if len(driver) > 20 else driver
            ttk.Label(self.table_inner, text=display_name, font=("Arial", 10, "bold"),
                     relief="solid", borderwidth=1, width=15, anchor="center", 
                     background="#f0f0f0").grid(row=0, column=col, sticky="nsew")
            
            # Store full name as tooltip
            label = self.table_inner.grid_slaves(row=0, column=col)[0]
            self.create_tooltip(label, driver)
        
        # Create data rows
        for row, variable in enumerate(variables, 1):
            # Variable name cell
            ttk.Label(self.table_inner, text=variable, font=("Arial", 9, "bold"),
                     relief="solid", borderwidth=1, anchor="w", 
                     background="#f0f0f0").grid(row=row, column=0, sticky="nsew")
            
            # Data cells for each driver
            for col, driver in enumerate(drivers, 1):
                value = self.df.loc[self.df['Driver'] == driver, variable]
                cell_value = ""
                if not value.empty:
                    cell_value = str(value.iloc[0])
                    # Format numeric values for display
                    try:
                        float_val = float(cell_value)
                        cell_value = f"{float_val:.3f}".rstrip('0').rstrip('.')
                    except (ValueError, TypeError):
                        pass
                
                # Create editable entry widget
                var = tk.StringVar(value=cell_value)
                entry = ttk.Entry(self.table_inner, textvariable=var, 
                                 font=("Arial", 9), width=15, justify='center')
                entry.grid(row=row, column=col, sticky="nsew", padx=1, pady=1)
                
                # Store reference to track changes
                key = (variable, driver)
                self.cell_widgets[key] = {
                    'widget': entry,
                    'var': var,
                    'original': cell_value
                }
                
                # Bind change event
                var.trace_add('write', lambda *args, k=key: self.on_cell_change(k))
        
        # Configure grid weights for resizing
        for i in range(len(variables) + 1):
            self.table_inner.rowconfigure(i, weight=1, minsize=30)
        for i in range(len(drivers) + 1):
            self.table_inner.columnconfigure(i, weight=1, minsize=100)
    
    def create_tooltip(self, widget, text):
        """Create a tooltip for a widget"""
        def on_enter(event):
            x, y, _, _ = widget.bbox("insert")
            x += widget.winfo_rootx() + 25
            y += widget.winfo_rooty() + 20
            
            # Create tooltip window
            self.tooltip = tk.Toplevel(widget)
            self.tooltip.wm_overrideredirect(True)
            self.tooltip.wm_geometry(f"+{x}+{y}")
            
            label = ttk.Label(self.tooltip, text=text, background="#ffffe0", 
                            relief="solid", borderwidth=1, padding=(5, 2))
            label.pack()
        
        def on_leave(event):
            if hasattr(self, 'tooltip'):
                self.tooltip.destroy()
        
        widget.bind("<Enter>", on_enter)
        widget.bind("<Leave>", on_leave)
    
    def on_cell_change(self, key):
        """Handle cell value change"""
        variable, driver = key
        widget_info = self.cell_widgets[key]
        new_value = widget_info['var'].get()
        
        # Compare with original value
        if new_value != widget_info['original']:
            # Update cell background to indicate change
            widget_info['widget'].configure(style='Changed.TEntry')
            self.changes_made = True
            self.status_label.config(text="Unsaved changes", foreground="orange")
        else:
            # Revert to normal style
            widget_info['widget'].configure(style='TEntry')
            
            # Check if all changes are reverted
            if not any(info['var'].get() != info['original'] 
                      for info in self.cell_widgets.values()):
                self.changes_made = False
                self.status_label.config(text="Ready", foreground="green")
    
    def apply_filter(self):
        """Apply filter to the data"""
        filter_text = self.filter_var.get().lower()
        
        if not filter_text:
            self.clear_filter()
            return
        
        # Get filtered drivers and variables
        drivers = list(self.df['Driver'])
        variables = self.get_variables()
        
        # Filter drivers by name
        filtered_drivers = [d for d in drivers if filter_text in d.lower()]
        
        # Filter variables by name
        filtered_variables = [v for v in variables if filter_text in v.lower()]
        
        # If no filtered variables, show all variables for filtered drivers
        if not filtered_variables:
            filtered_variables = variables
        
        # Create filtered table
        self.create_filtered_table(filtered_drivers, filtered_variables)
    
    def create_filtered_table(self, drivers, variables):
        """Create table with filtered drivers and variables"""
        # Clear current table
        for widget in self.table_inner.winfo_children():
            widget.destroy()
        
        # Clear cell widgets dictionary
        self.cell_widgets.clear()
        
        # Create header row
        ttk.Label(self.table_inner, text="Variable", font=("Arial", 10, "bold"), 
                 relief="solid", borderwidth=1, width=20, background="#f0f0f0").grid(
                     row=0, column=0, sticky="nsew")
        
        for col, driver in enumerate(drivers, 1):
            display_name = driver[:20] + "..." if len(driver) > 20 else driver
            ttk.Label(self.table_inner, text=display_name, font=("Arial", 10, "bold"),
                     relief="solid", borderwidth=1, width=15, anchor="center", 
                     background="#f0f0f0").grid(row=0, column=col, sticky="nsew")
            
            # Store full name as tooltip
            label = self.table_inner.grid_slaves(row=0, column=col)[0]
            self.create_tooltip(label, driver)
        
        # Create data rows
        for row, variable in enumerate(variables, 1):
            ttk.Label(self.table_inner, text=variable, font=("Arial", 9, "bold"),
                     relief="solid", borderwidth=1, anchor="w", 
                     background="#f0f0f0").grid(row=row, column=0, sticky="nsew")
            
            for col, driver in enumerate(drivers, 1):
                value = self.df.loc[self.df['Driver'] == driver, variable]
                cell_value = ""
                if not value.empty:
                    cell_value = str(value.iloc[0])
                    try:
                        float_val = float(cell_value)
                        cell_value = f"{float_val:.3f}".rstrip('0').rstrip('.')
                    except (ValueError, TypeError):
                        pass
                
                var = tk.StringVar(value=cell_value)
                entry = ttk.Entry(self.table_inner, textvariable=var, 
                                 font=("Arial", 9), width=15, justify='center')
                entry.grid(row=row, column=col, sticky="nsew", padx=1, pady=1)
                
                key = (variable, driver)
                self.cell_widgets[key] = {
                    'widget': entry,
                    'var': var,
                    'original': cell_value
                }
                
                var.trace_add('write', lambda *args, k=key: self.on_cell_change(k))
        
        # Configure grid
        for i in range(len(variables) + 1):
            self.table_inner.rowconfigure(i, weight=1, minsize=30)
        for i in range(len(drivers) + 1):
            self.table_inner.columnconfigure(i, weight=1, minsize=100)
    
    def clear_filter(self):
        """Clear filter and show all data"""
        self.filter_var.set("")
        self.create_table()
    
    def save_all(self):
        """Save changes to CSV and update RCD files in one operation"""
        if not self.changes_made:
            # No changes to save
            self.status_label.config(text="No changes to save", foreground="blue")
            return
        
        # Ask for confirmation before saving
        response = messagebox.askyesno(
            "Save Changes",
            "Save changes to CSV and update RCD files?\n\n"
            "A backup of original RCD files will be created."
        )
        
        if not response:
            return
        
        # Disable save button during operation
        self.save_button.state(['disabled'])
        self.status_label.config(text="Saving...", foreground="blue")
        
        # Run save operation in background thread
        thread = threading.Thread(target=self.run_save_all)
        thread.daemon = True
        thread.start()
    
    def run_save_all(self):
        """Run save operation in background thread"""
        try:
            # First save CSV changes
            self.save_csv_changes()
            
            # Then update RCD files if we have installation folders
            if self.install_folder and self.teams_folder:
                self.update_rcd_files_silent()
            
            # Schedule success update on main thread
            self.root.after(0, self.handle_save_success)
            
        except Exception as e:
            self.root.after(0, self.handle_save_error, e)
    
    def save_csv_changes(self):
        """Save changes to CSV file"""
        # Update DataFrame with changed values
        for (variable, driver), info in self.cell_widgets.items():
            new_value = info['var'].get()
            
            # Only update if changed
            if new_value != info['original']:
                # Find the row index for this driver
                row_idx = self.df.index[self.df['Driver'] == driver].tolist()[0]
                
                # Update the value
                self.df.at[row_idx, variable] = new_value
        
        # Save to CSV
        self.df.to_csv(self.csv_file_path, index=False, encoding='utf-8')
    
    def update_rcd_files_silent(self):
        """Update RCD files without showing success dialog"""
        try:
            # Import here to avoid circular imports
            from rcd_updater import RcdUpdater
            
            # Create updater
            updater = RcdUpdater(self.install_folder, self.teams_folder)
            
            # Get current data from DataFrame
            data = self.df.to_dict('records')
            
            # Filter fieldnames to exclude metadata fields
            editable_fields = [f for f in self.fieldnames 
                             if f not in ['Driver', 'Source_CAR_File', 'CAR_File_Path', 'Original_CAR_Name']
                             and f not in self.excluded_fields]
            
            # Update RCD files
            success_count, error_count, backup_path = updater.update_rcd_files(
                data, editable_fields, create_backup=True
            )
            
            # Store results for status display
            self.last_rcd_update_result = (success_count, error_count, backup_path)
            
        except Exception as e:
            raise Exception(f"RCD update failed: {str(e)}")
    
    def handle_save_success(self):
        """Handle successful save operation"""
        # Reset change tracking
        for info in self.cell_widgets.values():
            info['original'] = info['var'].get()
            info['widget'].configure(style='TEntry')
        
        self.changes_made = False
        self.save_button.state(['!disabled'])
        self.status_label.config(text="Saved successfully", foreground="green")
        
        logger.success(f"Saved changes to: {self.csv_file_path}")
        
        # Check if there were any RCD update errors
        if hasattr(self, 'last_rcd_update_result'):
            success_count, error_count, backup_path = self.last_rcd_update_result
            
            if error_count > 0:
                # Show error message only if there were errors
                messagebox.showerror(
                    "RCD Update Errors",
                    f"CSV saved successfully, but {error_count} RCD files failed to update.\n\n"
                    f"Backup created at:\n{backup_path}"
                )
            # No success message for RCD updates - only show on error
    
    def handle_save_error(self, error):
        """Handle save error on main thread"""
        self.save_button.state(['!disabled'])
        self.status_label.config(text=f"Save error: {str(error)[:50]}...", foreground="red")
        messagebox.showerror("Error", f"Error saving changes:\n{str(error)}")
    
    def on_canvas_configure(self, canvas, canvas_window):
        """Handle canvas resize"""
        canvas.itemconfig(canvas_window, width=canvas.winfo_width())
    
    def on_close(self):
        """Handle window close event"""
        if self.changes_made:
            response = messagebox.askyesnocancel(
                "Unsaved Changes",
                "You have unsaved changes. Would you like to save them before closing?"
            )
            
            if response is None:  # Cancel
                return
            elif response:  # Yes
                self.save_all()
                # Don't close immediately - wait for save to complete
                return
        
        self.root.destroy()
    
    def run(self):
        """Run the editor application"""
        # Create custom style for changed cells
        style = ttk.Style()
        style.configure('Changed.TEntry', fieldbackground='#fffacd')  # Light yellow
        
        self.root.mainloop()
