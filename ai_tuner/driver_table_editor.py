#!/usr/bin/env python3
# driver_table_editor.py - Editable driver data table (VIRTUAL VERSION - FAST)

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import pandas as pd
import os
import threading
from debug_logger import logger
from rcd_handler import RcdHandler  # Changed import

class DriverTableEditor:
    """Editable driver data table with virtual scrolling for performance"""
    
    def __init__(self, data, fieldnames, csv_file_path, install_folder=None, teams_folder=None):
        self.data = data  # List of dictionaries
        self.fieldnames = fieldnames  # List of column names
        self.csv_file_path = csv_file_path
        self.install_folder = install_folder
        self.teams_folder = teams_folder
        
        # Initialize RCD handler if we have folders
        self.rcd_handler = None
        if self.install_folder and self.teams_folder:
            self.rcd_handler = RcdHandler(install_folder, teams_folder)
        
        # Fields to exclude
        self.excluded_fields = ['Abbreviation', 'Nationality', 'NatAbbrev', 'Script']
        
        # Convert to DataFrame for easier manipulation
        self.df = pd.DataFrame(data)
        
        # Track changes
        self.changes_made = False
        
        self.root = tk.Toplevel()
        self.root.title(f"GTR2 Driver Data Editor - {os.path.basename(csv_file_path)}")
        self.root.geometry("1400x800")
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        
        # Pre-calculate data
        self.prepare_data()
        
        self.setup_ui()
    
    def prepare_data(self):
        """Pre-calculate and prepare data for faster access"""
        # Get all drivers and variables
        self.all_drivers = list(self.df['Driver'])
        self.all_variables = self.get_variables()
        
        # Create dictionaries for faster lookup
        self.driver_to_index = {driver: idx for idx, driver in enumerate(self.all_drivers)}
        self.variable_to_index = {variable: idx for idx, variable in enumerate(self.all_variables)}
        
        # Store original values for change tracking
        self.original_values = {}
        self.current_values = {}
        
        for variable in self.all_variables:
            for driver in self.all_drivers:
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
                
                key = (variable, driver)
                self.original_values[key] = cell_value
                self.current_values[key] = cell_value
        
        # Track visibility state
        self.driver_visible = {driver: True for driver in self.all_drivers}
        self.variable_visible = {variable: True for variable in self.all_variables}
        self.is_filtered = False
        
        # Get filtered lists
        self.update_filtered_lists()
    
    def get_variables(self):
        """Get the list of variables to display (excluding metadata and excluded fields)"""
        metadata_columns = ['Driver', 'Source_CAR_File', 'CAR_File_Path', 'Original_CAR_Name']
        
        # Get all columns that are not metadata or excluded
        all_columns = list(self.df.columns)
        variables = [col for col in all_columns 
                    if col not in metadata_columns and col not in self.excluded_fields]
        
        # Import RCD_FIELD_MAP from config
        from config import RCD_FIELD_MAP
        
        # Sort variables: RCD field map order first, then others alphabetically
        sorted_vars = []
        
        # First, add variables from RCD_FIELD_MAP in their defined order
        for var in RCD_FIELD_MAP:
            if var in variables:
                sorted_vars.append(var)
                variables.remove(var)
        
        # Add remaining variables alphabetically
        sorted_vars.extend(sorted(variables))
        
        return sorted_vars

    def update_filtered_lists(self):
        """Update lists of visible drivers and variables"""
        self.visible_drivers = [d for d in self.all_drivers if self.driver_visible[d]]
        self.visible_variables = [v for v in self.all_variables if self.variable_visible[v]]
    
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
            text="GTR2 Driver Data Editor", 
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
        self.stats_label = ttk.Label(main_frame, text="")
        self.stats_label.grid(row=1, column=0, columnspan=3, pady=(0, 10))
        self.update_stats()
        
        # Filter frame
        filter_frame = ttk.Frame(main_frame)
        filter_frame.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        
        ttk.Label(filter_frame, text="Filter:").pack(side=tk.LEFT, padx=(0, 5))
        self.filter_var = tk.StringVar()
        filter_entry = ttk.Entry(filter_frame, textvariable=self.filter_var, width=30)
        filter_entry.pack(side=tk.LEFT, padx=(0, 5))
        
        ttk.Button(filter_frame, text="Apply", command=self.apply_filter).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(filter_frame, text="Clear", command=self.clear_filter).pack(side=tk.LEFT)
        
        # Table container
        table_container = ttk.Frame(main_frame)
        table_container.grid(row=3, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        
        # Create Treeview with scrollbars - store column IDs
        columns = ["Variable"] + self.all_drivers
        self.tree = ttk.Treeview(table_container, columns=columns, show="headings", height=25)
        
        # Store column IDs for easy reference
        self.column_ids = columns
        
        # Configure scrollbars
        v_scrollbar = ttk.Scrollbar(table_container, orient="vertical", command=self.tree.yview)
        h_scrollbar = ttk.Scrollbar(table_container, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
        
        # Grid everything
        self.tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        v_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        h_scrollbar.grid(row=1, column=0, sticky=(tk.W, tk.E))
        
        # Configure weights
        table_container.columnconfigure(0, weight=1)
        table_container.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(3, weight=1)
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        
        # Configure tree columns
        self.tree.heading("Variable", text="Variable")
        self.tree.column("Variable", width=200, minwidth=150)
        
        for driver in self.all_drivers:
            display_name = driver[:15] + "..." if len(driver) > 15 else driver
            self.tree.heading(driver, text=display_name)
            self.tree.column(driver, width=100, minwidth=80)
        
        # Populate tree with data
        self.populate_tree()
        
        # Bind cell editing
        self.tree.bind("<Double-1>", self.on_cell_double_click)
        
        # Status bar
        self.status_label = ttk.Label(main_frame, text="Ready", foreground="green")
        self.status_label.grid(row=4, column=0, columnspan=3, pady=(10, 0))
        
        # Bind filter entry to apply on Enter key
        filter_entry.bind("<Return>", lambda e: self.apply_filter())
    
    def populate_tree(self):
        """Populate the tree with data from visible variables"""
        # Clear existing items
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        # Add rows for visible variables
        for variable in self.visible_variables:
            values = [variable]
            for driver in self.visible_drivers:
                key = (variable, driver)
                values.append(self.current_values.get(key, ""))
            
            item_id = self.tree.insert("", "end", values=values)
            # Store variable name in item for reference
            self.tree.set(item_id, "Variable", variable)
    
    def update_stats(self):
        """Update statistics label"""
        visible_drivers = sum(1 for v in self.driver_visible.values() if v)
        visible_variables = sum(1 for v in self.variable_visible.values() if v)
        
        if self.is_filtered:
            stats_text = f"Drivers: {visible_drivers}/{len(self.all_drivers)} | Variables: {visible_variables}/{len(self.all_variables)} (Filtered)"
        else:
            stats_text = f"Drivers: {len(self.all_drivers)} | Variables: {len(self.all_variables)}"
        
        self.stats_label.config(text=stats_text)
    
    def apply_filter(self):
        """Apply filter to the data"""
        filter_text = self.filter_var.get().strip().lower()
        
        if not filter_text:
            self.clear_filter()
            return
        
        import time
        start_time = time.time()
        
        # Reset all to visible first
        for driver in self.all_drivers:
            self.driver_visible[driver] = False
        for variable in self.all_variables:
            self.variable_visible[variable] = False
        
        # Find matches
        filtered_drivers = [d for d in self.all_drivers if filter_text in d.lower()]
        filtered_variables = [v for v in self.all_variables if filter_text in v.lower()]
        
        # Determine what to show
        if filtered_drivers:
            # Show matching drivers with all variables
            for driver in filtered_drivers:
                self.driver_visible[driver] = True
            for variable in self.all_variables:
                self.variable_visible[variable] = True
        elif filtered_variables:
            # Show matching variables with all drivers
            for driver in self.all_drivers:
                self.driver_visible[driver] = True
            for variable in filtered_variables:
                self.variable_visible[variable] = True
        else:
            # No matches
            self.status_label.config(text=f"No matches found for: {filter_text}", foreground="orange")
            return
        
        self.is_filtered = True
        self.update_filtered_lists()
        
        # Update tree columns based on visible drivers
        self.update_tree_columns()
        
        # Repopulate tree with filtered data
        self.populate_tree()
        
        # Update status
        elapsed = time.time() - start_time
        visible_drivers_count = len(self.visible_drivers)
        visible_variables_count = len(self.visible_variables)
        self.status_label.config(
            text=f"Showing {visible_drivers_count} drivers, {visible_variables_count} variables in {elapsed:.2f}s", 
            foreground="blue"
        )
        self.update_stats()
    
    def update_tree_columns(self):
        """Update tree columns based on visible drivers"""
        # Show/hide columns
        for col in self.column_ids:
            if col == "Variable":
                continue
            
            if self.driver_visible.get(col, False):
                self.tree.column(col, stretch=True, width=100)
            else:
                self.tree.column(col, stretch=False, minwidth=0, width=0)
    
    def clear_filter(self):
        """Clear filter and show all data"""
        self.filter_var.set("")
        self.is_filtered = False
        
        # Set all to visible
        for driver in self.all_drivers:
            self.driver_visible[driver] = True
        for variable in self.all_variables:
            self.variable_visible[variable] = True
        
        self.update_filtered_lists()
        
        # Show all columns
        for col in self.column_ids:
            if col != "Variable":
                self.tree.column(col, stretch=True, width=100)
        
        # Repopulate tree
        self.populate_tree()
        
        self.status_label.config(text="Filter cleared", foreground="green")
        self.update_stats()
    
    def on_cell_double_click(self, event):
        """Handle double-click on cell for editing"""
        # Identify region
        region = self.tree.identify_region(event.x, event.y)
        
        if region == "cell":
            # Get item and column
            item = self.tree.identify_row(event.y)
            column = self.tree.identify_column(event.x)
            
            if item and column != "#0":  # Not the tree column
                # Get column index and name
                col_index = int(column[1:]) - 1  # Convert "#1" to 0, "#2" to 1, etc.
                
                # Get variable from the item
                variable = self.tree.item(item)['values'][0]
                
                # If clicking on Variable column (index 0), don't edit
                if col_index == 0:
                    return
                
                # Get driver name for this column
                if col_index - 1 < len(self.visible_drivers):
                    driver = self.visible_drivers[col_index - 1]
                else:
                    return
                
                # Get current value
                key = (variable, driver)
                current_value = self.current_values.get(key, "")
                
                # Edit cell using simpledialog (no grab issues)
                self.edit_cell_simple(item, driver, variable, current_value)
    
    def edit_cell_simple(self, item, driver, variable, current_value):
        """Edit cell using tkinter's simpledialog (reliable and simple)"""
        # Use tkinter's built-in simpledialog for reliable editing
        new_value = simpledialog.askstring(
            f"Edit {variable}",
            f"Driver: {driver}\nVariable: {variable}\n\nEnter new value:",
            initialvalue=current_value,
            parent=self.root
        )
        
        if new_value is not None and new_value != current_value:
            # Update value
            key = (variable, driver)
            self.current_values[key] = new_value
            self.changes_made = True
            self.status_label.config(text="Unsaved changes", foreground="orange")
            
            # Update tree display
            self.update_tree_cell(item, driver, new_value)
    
    def update_tree_cell(self, item, driver, new_value):
        """Update a single cell in the tree"""
        # Get current values
        values = list(self.tree.item(item)['values'])
        
        # Find driver index in visible_drivers
        try:
            driver_index = self.visible_drivers.index(driver)
            # Update value (add 1 for Variable column)
            values[driver_index + 1] = new_value
            self.tree.item(item, values=values)
        except (ValueError, IndexError):
            pass  # Driver not in visible list
    
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
            
            # Then update RCD files if we have a handler
            if self.rcd_handler:
                self.update_rcd_files_silent()
            
            # Schedule success update on main thread
            self.root.after(0, self.handle_save_success)
            
        except Exception as e:
            self.root.after(0, self.handle_save_error, e)
    
    def save_csv_changes(self):
        """Save changes to CSV file"""
        # Update DataFrame with changed values
        for (variable, driver), new_value in self.current_values.items():
            original_value = self.original_values.get((variable, driver), "")
            
            # Only update if changed
            if new_value != original_value:
                # Find the row index for this driver
                row_idx = self.df.index[self.df['Driver'] == driver].tolist()[0]
                
                # Update the value
                self.df.at[row_idx, variable] = new_value
        
        # Save to CSV
        self.df.to_csv(self.csv_file_path, index=False, encoding='utf-8')
    
    def update_rcd_files_silent(self):
        """Update RCD files without showing success dialog"""
        try:
            # Get current data from DataFrame
            data = self.df.to_dict('records')
            
            # Filter fieldnames to exclude metadata fields
            editable_fields = [f for f in self.fieldnames 
                             if f not in ['Driver', 'Source_CAR_File', 'CAR_File_Path', 'Original_CAR_Name']
                             and f not in self.excluded_fields]
            
            # Update RCD files using the unified handler
            success_count, error_count, backup_path = self.rcd_handler.update_rcd_files(
                data, editable_fields, create_backup=True
            )
            
            # Store results for status display
            self.last_rcd_update_result = (success_count, error_count, backup_path)
            
        except Exception as e:
            raise Exception(f"RCD update failed: {str(e)}")
    
    def handle_save_success(self):
        """Handle successful save operation"""
        # Reset change tracking
        self.original_values = self.current_values.copy()
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
    
    def handle_save_error(self, error):
        """Handle save error on main thread"""
        self.save_button.state(['!disabled'])
        self.status_label.config(text=f"Save error: {str(error)[:50]}...", foreground="red")
        messagebox.showerror("Error", f"Error saving changes:\n{str(error)}")
    
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
