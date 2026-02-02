#!/usr/bin/env python3
# driver_table_viewer.py - Display driver data in a table format

import tkinter as tk
from tkinter import ttk
import pandas as pd
import os
from debug_logger import logger

class DriverTableViewer:
    """Display driver data in a table with variables as rows and drivers as columns"""
    
    def __init__(self, csv_file_path):
        self.csv_file_path = csv_file_path
        self.root = tk.Tk()
        self.root.title("GTR2 Driver Data Viewer")
        self.root.geometry("1200x700")
        
        # Load data
        self.df = self.load_csv()
        if self.df is None:
            return
        
        self.setup_ui()
    
    def load_csv(self):
        """Load CSV file"""
        if not os.path.exists(self.csv_file_path):
            logger.error(f"CSV file not found: {self.csv_file_path}")
            messagebox.showerror("Error", f"CSV file not found:\n{self.csv_file_path}")
            return None
        
        try:
            df = pd.read_csv(self.csv_file_path, encoding='utf-8')
            logger.info(f"Loaded CSV with {len(df)} drivers and {len(df.columns)} columns")
            return df
        except Exception as e:
            logger.error(f"Error loading CSV: {e}")
            messagebox.showerror("Error", f"Error loading CSV:\n{str(e)}")
            return None
    
    def setup_ui(self):
        """Setup the user interface"""
        # Main container
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Title
        title_label = ttk.Label(
            main_frame, 
            text=f"🚗 GTR2 Driver Data Viewer - {os.path.basename(self.csv_file_path)}", 
            font=("Arial", 14, "bold")
        )
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 10))
        
        # Statistics
        stats_text = f"Drivers: {len(self.df)} | Variables: {len(self.get_variables())} | Total cells: {len(self.df) * len(self.get_variables())}"
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
        canvas = tk.Canvas(table_frame)
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
        
        # Control buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=4, column=0, columnspan=3, pady=(10, 0))
        
        ttk.Button(button_frame, text="Export to Excel", command=self.export_to_excel).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Refresh", command=self.refresh).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Close", command=self.root.destroy).pack(side=tk.LEFT, padx=5)
        
        # Bind filter entry to apply on Enter key
        filter_entry.bind("<Return>", lambda e: self.apply_filter())
    
    def get_variables(self):
        """Get the list of variables to display (excluding metadata columns)"""
        metadata_columns = ['Driver', 'Source_CAR_File', 'CAR_File_Path', 'Original_CAR_Name']
        
        # Get all columns that are not metadata
        all_columns = list(self.df.columns)
        variables = [col for col in all_columns if col not in metadata_columns]
        
        # If we have the standard GTR2 variables, sort them in a logical order
        standard_order = [
            'Abbreviation', 'Nationality', 'NatAbbrev',
            'StartsDry', 'StartsWet', 'StartStalls', 
            'QualifyingAbility', 'RaceAbility', 'Consistency', 'RainAbility',
            'Passing', 'Crash', 'Recovery', 'CompletedLaps%', 'Script',
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
        """Create the table with variables as rows and drivers as columns"""
        # Get drivers and variables
        drivers = list(self.df['Driver'])
        variables = self.get_variables()
        
        # Create header row with driver names
        ttk.Label(self.table_inner, text="Variable", font=("Arial", 10, "bold"), 
                 relief="solid", borderwidth=1, width=20).grid(row=0, column=0, sticky="nsew")
        
        for col, driver in enumerate(drivers, 1):
            # Truncate long driver names
            display_name = driver[:20] + "..." if len(driver) > 20 else driver
            ttk.Label(self.table_inner, text=display_name, font=("Arial", 10, "bold"),
                     relief="solid", borderwidth=1, width=15, anchor="center").grid(
                         row=0, column=col, sticky="nsew")
        
        # Create data rows
        for row, variable in enumerate(variables, 1):
            # Variable name cell
            ttk.Label(self.table_inner, text=variable, font=("Arial", 9, "bold"),
                     relief="solid", borderwidth=1, anchor="w").grid(
                         row=row, column=0, sticky="nsew")
            
            # Data cells for each driver
            for col, driver in enumerate(drivers, 1):
                value = self.df.loc[self.df['Driver'] == driver, variable]
                if not value.empty:
                    cell_value = str(value.iloc[0])
                    # Format numeric values
                    try:
                        float_val = float(cell_value)
                        cell_value = f"{float_val:.3f}".rstrip('0').rstrip('.')
                    except (ValueError, TypeError):
                        pass
                else:
                    cell_value = ""
                
                # Create cell with appropriate styling
                cell = tk.Text(self.table_inner, height=1, width=15, wrap="none",
                              borderwidth=1, relief="solid", font=("Arial", 9))
                cell.insert("1.0", cell_value)
                cell.configure(state="disabled")  # Make read-only
                cell.grid(row=row, column=col, sticky="nsew")
        
        # Configure grid weights for resizing
        for i in range(len(variables) + 1):
            self.table_inner.rowconfigure(i, weight=1)
        for i in range(len(drivers) + 1):
            self.table_inner.columnconfigure(i, weight=1)
    
    def apply_filter(self):
        """Apply filter to the data"""
        filter_text = self.filter_var.get().lower()
        
        if not filter_text:
            return
        
        # Clear current table
        for widget in self.table_inner.winfo_children():
            widget.destroy()
        
        # Filter drivers and variables
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
        # Create header row
        ttk.Label(self.table_inner, text="Variable", font=("Arial", 10, "bold"), 
                 relief="solid", borderwidth=1, width=20).grid(row=0, column=0, sticky="nsew")
        
        for col, driver in enumerate(drivers, 1):
            display_name = driver[:20] + "..." if len(driver) > 20 else driver
            ttk.Label(self.table_inner, text=display_name, font=("Arial", 10, "bold"),
                     relief="solid", borderwidth=1, width=15, anchor="center").grid(
                         row=0, column=col, sticky="nsew")
        
        # Create data rows
        for row, variable in enumerate(variables, 1):
            ttk.Label(self.table_inner, text=variable, font=("Arial", 9, "bold"),
                     relief="solid", borderwidth=1, anchor="w").grid(
                         row=row, column=0, sticky="nsew")
            
            for col, driver in enumerate(drivers, 1):
                value = self.df.loc[self.df['Driver'] == driver, variable]
                if not value.empty:
                    cell_value = str(value.iloc[0])
                    try:
                        float_val = float(cell_value)
                        cell_value = f"{float_val:.3f}".rstrip('0').rstrip('.')
                    except (ValueError, TypeError):
                        pass
                else:
                    cell_value = ""
                
                cell = tk.Text(self.table_inner, height=1, width=15, wrap="none",
                              borderwidth=1, relief="solid", font=("Arial", 9))
                cell.insert("1.0", cell_value)
                cell.configure(state="disabled")
                cell.grid(row=row, column=col, sticky="nsew")
        
        # Configure grid
        for i in range(len(variables) + 1):
            self.table_inner.rowconfigure(i, weight=1)
        for i in range(len(drivers) + 1):
            self.table_inner.columnconfigure(i, weight=1)
    
    def clear_filter(self):
        """Clear filter and show all data"""
        self.filter_var.set("")
        
        # Clear current table
        for widget in self.table_inner.winfo_children():
            widget.destroy()
        
        # Recreate full table
        self.create_table()
    
    def refresh(self):
        """Refresh data from CSV file"""
        self.df = self.load_csv()
        if self.df is not None:
            # Clear current table
            for widget in self.table_inner.winfo_children():
                widget.destroy()
            
            # Recreate table
            self.create_table()
    
    def export_to_excel(self):
        """Export the current view to Excel"""
        try:
            import pandas as pd
            from tkinter import filedialog
            
            # Get current filter state
            filter_text = self.filter_var.get().lower()
            
            if filter_text:
                # Export filtered data
                drivers = list(self.df['Driver'])
                variables = self.get_variables()
                
                filtered_drivers = [d for d in drivers if filter_text in d.lower()]
                filtered_variables = [v for v in variables if filter_text in v.lower()]
                
                if not filtered_variables:
                    filtered_variables = variables
                
                # Create filtered DataFrame
                export_df = self.df[self.df['Driver'].isin(filtered_drivers)]
                export_df = export_df[['Driver'] + filtered_variables]
            else:
                # Export all data
                variables = self.get_variables()
                export_df = self.df[['Driver'] + variables]
            
            # Ask for save location
            filename = filedialog.asksaveasfilename(
                title="Save Excel File",
                defaultextension=".xlsx",
                filetypes=[("Excel files", "*.xlsx"), ("All files", "*.*")]
            )
            
            if filename:
                export_df.to_excel(filename, index=False)
                logger.success(f"Exported to: {filename}")
                tk.messagebox.showinfo("Success", f"Data exported to:\n{filename}")
        
        except ImportError:
            logger.error("OpenPyXL not installed. Install with: pip install openpyxl")
            tk.messagebox.showerror("Error", "OpenPyXL not installed.\nInstall with: pip install openpyxl")
        except Exception as e:
            logger.error(f"Error exporting to Excel: {e}")
            tk.messagebox.showerror("Error", f"Error exporting to Excel:\n{str(e)}")
    
    def on_canvas_configure(self, canvas, canvas_window):
        """Handle canvas resize"""
        canvas.itemconfig(canvas_window, width=canvas.winfo_width())
    
    def run(self):
        """Run the viewer application"""
        if self.df is not None:
            self.root.mainloop()


# Function to open viewer from main application
def open_driver_table_viewer(csv_file_path):
    """Open the driver table viewer"""
    viewer = DriverTableViewer(csv_file_path)
    viewer.run()
