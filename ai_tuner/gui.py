#!/usr/bin/env python3
# gui.py - Simple GUI for selecting folders

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import threading
import yaml
from debug_logger import logger

class DriverExtractorGUI:
    """Simple GUI for the Driver Extractor tool"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("GTR2 Driver Data Extractor")
        self.root.geometry("700x500")
        self.root.resizable(True, True)
        
        # Set icon if available
        try:
            self.root.iconbitmap("icon.ico")
        except:
            pass
        
        # Variables
        self.config_file = tk.StringVar()
        self.install_folder = tk.StringVar()
        self.teams_folder = tk.StringVar()
        self.output_file = tk.StringVar(value="result.csv")
        self.debug_mode = tk.BooleanVar(value=False)
        
        # Store extraction results
        self.extraction_result = None
        self.extraction_fieldnames = None
        
        self.setup_ui()
        self.load_default_config()
    
    def setup_ui(self):
        """Setup the user interface"""
        # Main container
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Title
        title_label = ttk.Label(
            main_frame, 
            text="🚗 GTR2 Driver Data Extractor", 
            font=("Arial", 16, "bold")
        )
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 20))
        
        # Description
        desc_label = ttk.Label(
            main_frame,
            text="Extract and edit driver data from .car and .rcd files for GTR2",
            wraplength=600
        )
        desc_label.grid(row=1, column=0, columnspan=3, pady=(0, 10))
        
        # Config file selection
        ttk.Label(main_frame, text="Configuration File (cfg.yml):").grid(
            row=2, column=0, sticky=tk.W, pady=5
        )
        
        config_entry = ttk.Entry(main_frame, textvariable=self.config_file, width=50)
        config_entry.grid(row=2, column=1, padx=(10, 5), pady=5, sticky=(tk.W, tk.E))
        
        ttk.Button(main_frame, text="Load", command=self.load_config).grid(
            row=2, column=2, padx=(0, 0), pady=5
        )
        
        # Separator
        ttk.Separator(main_frame, orient='horizontal').grid(
            row=3, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=15
        )
        
        # GTR2 install folder selection
        ttk.Label(main_frame, text="GTR2 Installation Folder:").grid(
            row=4, column=0, sticky=tk.W, pady=5
        )
        
        install_entry = ttk.Entry(main_frame, textvariable=self.install_folder, width=50)
        install_entry.grid(row=4, column=1, padx=(10, 5), pady=5, sticky=(tk.W, tk.E))
        
        ttk.Button(main_frame, text="Browse...", command=self.browse_install).grid(
            row=4, column=2, padx=(0, 0), pady=5
        )
        
        # Teams folder selection
        ttk.Label(main_frame, text="Teams Folder:").grid(
            row=5, column=0, sticky=tk.W, pady=5
        )
        
        teams_entry = ttk.Entry(main_frame, textvariable=self.teams_folder, width=50)
        teams_entry.grid(row=5, column=1, padx=(10, 5), pady=5, sticky=(tk.W, tk.E))
        
        ttk.Button(main_frame, text="Browse...", command=self.browse_teams).grid(
            row=5, column=2, padx=(0, 0), pady=5
        )
        
        # Auto-detect button
        ttk.Button(main_frame, text="Auto-detect GTR2", command=self.auto_detect_gtr2).grid(
            row=6, column=1, columnspan=2, pady=(5, 15), sticky=tk.W
        )
        
        # Output file
        ttk.Label(main_frame, text="Output CSV File:").grid(
            row=7, column=0, sticky=tk.W, pady=5
        )
        
        output_entry = ttk.Entry(main_frame, textvariable=self.output_file, width=50)
        output_entry.grid(row=7, column=1, padx=(10, 5), pady=5, sticky=(tk.W, tk.E))
        
        ttk.Button(main_frame, text="Browse...", command=self.browse_output).grid(
            row=7, column=2, padx=(0, 0), pady=5
        )
        
        # Debug mode checkbox
        debug_check = ttk.Checkbutton(
            main_frame, 
            text="Enable Debug Mode (verbose output)", 
            variable=self.debug_mode
        )
        debug_check.grid(row=8, column=0, columnspan=3, pady=10, sticky=tk.W)
        
        # Status label
        self.status_label = ttk.Label(main_frame, text="Ready", foreground="green")
        self.status_label.grid(row=9, column=0, columnspan=3, pady=(10, 0))
        
        # Progress bar
        self.progress = ttk.Progressbar(main_frame, mode='indeterminate')
        self.progress.grid(row=10, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(10, 0))
        
        # Buttons frame
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=11, column=0, columnspan=3, pady=(20, 0))
        
        # Single main action button
        self.main_action_button = ttk.Button(
            button_frame, 
            text="Extract & Edit Data", 
            command=self.extract_and_edit,
            state='normal'
        )
        self.main_action_button.pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Button(button_frame, text="Save Config", command=self.save_config).pack(
            side=tk.LEFT, padx=(10, 10)
        )
        ttk.Button(button_frame, text="Clear All", command=self.clear_all).pack(
            side=tk.LEFT, padx=(10, 10)
        )
        ttk.Button(button_frame, text="Exit", command=self.root.quit).pack(
            side=tk.LEFT, padx=(10, 0)
        )
        
        # Help text
        help_text = """
Common GTR2 folder structure:
  GTR2 Installation: C:/Games/GTR2
  Teams Folder: C:/Games/GTR2/GameData/Teams

Click 'Extract & Edit Data' to extract driver data and open the editor.
        """
        
        help_label = ttk.Label(main_frame, text=help_text, justify=tk.LEFT)
        help_label.grid(row=12, column=0, columnspan=3, pady=(20, 0), sticky=tk.W)
        
        # Configure grid weights
        main_frame.columnconfigure(1, weight=1)
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
    
    def extract_and_edit(self):
        """Extract data and then open editor directly"""
        # First extract the data
        if not self.start_extraction():
            return
        
        # The editor will be opened from handle_extraction_result
    
    def load_default_config(self):
        """Try to load default config file"""
        default_config = "cfg.yml"
        if os.path.exists(default_config):
            self.config_file.set(default_config)
            self.load_config()
    
    def load_config(self):
        """Load configuration from YAML file"""
        config_path = self.config_file.get()
        if not config_path or not os.path.exists(config_path):
            messagebox.showwarning("Warning", f"Config file not found: {config_path}")
            return
        
        try:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
            
            if 'gtr2_install' in config:
                self.install_folder.set(config['gtr2_install'])
            
            if 'teams_folder' in config:
                self.teams_folder.set(config['teams_folder'])
            elif self.install_folder.get() and not self.teams_folder.get():
                # Auto-set teams folder
                teams_path = os.path.join(self.install_folder.get(), "GameData", "Teams")
                self.teams_folder.set(teams_path)
            
            if 'output_file' in config:
                self.output_file.set(config['output_file'])
            
            if 'debug' in config:
                self.debug_mode.set(config['debug'])
            
            self.status_label.config(text=f"Loaded config: {os.path.basename(config_path)}", foreground="green")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load config:\n{str(e)}")
    
    def save_config(self):
        """Save configuration to YAML file"""
        config_path = self.config_file.get()
        if not config_path:
            config_path = filedialog.asksaveasfilename(
                title="Save Configuration",
                defaultextension=".yml",
                filetypes=[("YAML files", "*.yml"), ("All files", "*.*")]
            )
            if not config_path:
                return
            self.config_file.set(config_path)
        
        config = {
            'gtr2_install': self.install_folder.get(),
            'teams_folder': self.teams_folder.get(),
            'output_file': self.output_file.get(),
            'debug': self.debug_mode.get()
        }
        
        try:
            with open(config_path, 'w') as f:
                yaml.dump(config, f, default_flow_style=False)
            
            self.status_label.config(text=f"Config saved: {os.path.basename(config_path)}", foreground="green")
            messagebox.showinfo("Success", f"Configuration saved to:\n{config_path}")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save config:\n{str(e)}")
    
    def browse_install(self):
        """Browse for GTR2 installation folder"""
        folder = filedialog.askdirectory(title="Select GTR2 Installation Folder")
        if folder:
            self.install_folder.set(folder)
            
            # Auto-set teams folder to default location
            default_teams = os.path.join(folder, "GameData", "Teams")
            if os.path.exists(default_teams):
                self.teams_folder.set(default_teams)
            else:
                # Clear teams folder if default doesn't exist
                self.teams_folder.set("")
                
                # Suggest where it should be
                self.status_label.config(
                    text=f"Note: Default Teams folder not found at:\n{default_teams}", 
                    foreground="orange"
                )
    
    def browse_teams(self):
        """Browse for teams folder, starting at default GTR2 location"""
        # Determine initial directory
        initial_dir = self.teams_folder.get()
        
        # If no teams folder is set, try to use default based on GTR2 install
        if not initial_dir and self.install_folder.get():
            default_teams = os.path.join(self.install_folder.get(), "GameData", "Teams")
            if os.path.exists(default_teams):
                initial_dir = default_teams
            else:
                # Try just the GameData folder
                game_data = os.path.join(self.install_folder.get(), "GameData")
                if os.path.exists(game_data):
                    initial_dir = game_data
                else:
                    # Fall back to GTR2 install folder
                    initial_dir = self.install_folder.get()
        
        # If still no initial directory, use current directory
        if not initial_dir:
            initial_dir = "."
        
        folder = filedialog.askdirectory(
            title="Select Teams Folder",
            initialdir=initial_dir
        )
        
        if folder:
            self.teams_folder.set(folder)
    
    def browse_output(self):
        """Browse for output file"""
        filename = filedialog.asksaveasfilename(
            title="Save Output CSV File",
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        if filename:
            self.output_file.set(filename)
    
    def auto_detect_gtr2(self):
        """Try to auto-detect GTR2 installation"""
        common_paths = [
            "C:/Program Files/GTR2",
            "C:/Program Files (x86)/GTR2",
            "C:/Games/GTR2",
            "D:/Games/GTR2",
            os.path.expanduser("~/Games/GTR2"),
            "/Program Files/GTR2",
            "/Program Files (x86)/GTR2",
            "/usr/local/games/GTR2",
            os.path.expanduser("~/.wine/drive_c/Program Files/GTR2"),
            os.path.expanduser("~/.wine/drive_c/Program Files (x86)/GTR2"),
            os.path.expanduser("~/.local/share/Steam/steamapps/common/GTR2"),
        ]
        
        found_paths = []
        for path in common_paths:
            if os.path.exists(path):
                found_paths.append(path)
        
        if found_paths:
            # Let user choose if multiple found
            if len(found_paths) == 1:
                selected_path = found_paths[0]
            else:
                # Create a simple selection dialog
                selection_dialog = tk.Toplevel(self.root)
                selection_dialog.title("Select GTR2 Installation")
                selection_dialog.geometry("500x300")
                selection_dialog.transient(self.root)
                selection_dialog.grab_set()
                
                ttk.Label(selection_dialog, text="Multiple GTR2 installations found. Select one:", 
                         font=("Arial", 10, "bold")).pack(pady=10)
                
                selected_path = tk.StringVar(value=found_paths[0])
                
                listbox = tk.Listbox(selection_dialog, selectmode=tk.SINGLE, height=min(len(found_paths), 10))
                for path in found_paths:
                    listbox.insert(tk.END, path)
                listbox.pack(pady=10, padx=20, fill=tk.BOTH, expand=True)
                
                def on_select():
                    try:
                        selected_path.set(listbox.get(listbox.curselection()))
                        selection_dialog.destroy()
                    except:
                        pass
                
                def on_cancel():
                    selected_path.set("")
                    selection_dialog.destroy()
                
                button_frame = ttk.Frame(selection_dialog)
                button_frame.pack(pady=10)
                
                ttk.Button(button_frame, text="Select", command=on_select).pack(side=tk.LEFT, padx=5)
                ttk.Button(button_frame, text="Cancel", command=on_cancel).pack(side=tk.LEFT, padx=5)
                
                # Wait for dialog to close
                self.root.wait_window(selection_dialog)
            
            if selected_path and selected_path.get():
                self.install_folder.set(selected_path.get())
                # Auto-set teams folder
                default_teams = os.path.join(selected_path.get(), "GameData", "Teams")
                if os.path.exists(default_teams):
                    self.teams_folder.set(default_teams)
                    self.status_label.config(text=f"Auto-detected GTR2 at: {selected_path.get()}", foreground="green")
                else:
                    self.teams_folder.set("")
                    self.status_label.config(
                        text=f"GTR2 found but Teams folder not at:\n{default_teams}", 
                        foreground="orange"
                    )
        else:
            messagebox.showinfo("Info", "Could not auto-detect GTR2 installation.")
    
    def clear_all(self):
        """Clear all fields"""
        self.config_file.set("")
        self.install_folder.set("")
        self.teams_folder.set("")
        self.output_file.set("result.csv")
        self.debug_mode.set(False)
        self.status_label.config(text="Ready", foreground="green")
    
    def start_extraction(self):
        """Start the extraction process"""
        # Validate inputs
        if not self.install_folder.get():
            messagebox.showerror("Error", "Please select the GTR2 installation folder")
            return False
        
        if not self.teams_folder.get():
            messagebox.showerror("Error", "Please select the teams folder")
            return False
        
        if not self.output_file.get():
            messagebox.showerror("Error", "Please specify an output file")
            return False
        
        # Check if folders exist
        if not os.path.exists(self.install_folder.get()):
            messagebox.showerror("Error", f"GTR2 folder does not exist:\n{self.install_folder.get()}")
            return False
        
        if not os.path.exists(self.teams_folder.get()):
            messagebox.showerror("Error", f"Teams folder does not exist:\n{self.teams_folder.get()}")
            return False
        
        # Start extraction in background thread to keep GUI responsive
        self.status_label.config(text="Processing...", foreground="blue")
        self.progress.start()
        
        # Disable buttons during processing
        self.disable_buttons()
        
        # Run extraction in a separate thread
        thread = threading.Thread(target=self.run_extraction)
        thread.daemon = True
        thread.start()
        
        return True
    
    def disable_buttons(self):
        """Disable buttons during processing"""
        self.main_action_button.state(['disabled'])
        for widget in self.root.winfo_children():
            for child in widget.winfo_children():
                if isinstance(child, ttk.Button) and child != self.main_action_button:
                    child.state(['disabled'])
    
    def enable_buttons(self):
        """Enable buttons after processing"""
        self.main_action_button.state(['!disabled'])
        for widget in self.root.winfo_children():
            for child in widget.winfo_children():
                if isinstance(child, ttk.Button) and child != self.main_action_button:
                    child.state(['!disabled'])
    
    def run_extraction(self):
        """Run the extraction in a separate thread"""
        try:
            # Import inside thread to avoid circular imports
            from processor import DriverProcessor
            from csv_writer import CSVWriter
            
            # Create processor
            processor = DriverProcessor(
                self.install_folder.get(),
                self.teams_folder.get(),
                self.debug_mode.get()
            )
            
            # Process data
            result = processor.process()
            
            # Save results to CSV
            if result:
                data, fieldnames = result
                if data:
                    csv_success = CSVWriter.write_drivers_to_csv(data, fieldnames, self.output_file.get())
                    
                    # Store results for viewer
                    self.extraction_result = data
                    self.extraction_fieldnames = fieldnames
                    
                    # Schedule GUI updates on the main thread
                    self.root.after(0, self.handle_extraction_result, csv_success, data, fieldnames)
                else:
                    self.root.after(0, self.handle_extraction_result, False, None, None)
            else:
                self.root.after(0, self.handle_extraction_result, False, None, None)
            
        except Exception as e:
            # Schedule error display on the main thread
            self.root.after(0, self.handle_extraction_error, e)
    
    def handle_extraction_result(self, csv_success, data, fieldnames):
        """Handle extraction result on the main GUI thread"""
        self.progress.stop()
        
        if csv_success and data:
            self.status_label.config(text="Extraction completed! Opening editor...", foreground="green")
            
            # Open editor directly without asking for confirmation
            self.root.after(100, lambda: self.open_viewer(data, fieldnames))
        else:
            self.status_label.config(text="Extraction failed", foreground="red")
            messagebox.showerror("Error", "Extraction process failed or no data found")
            self.enable_buttons()
    
    def open_viewer(self, data=None, fieldnames=None):
        """Open the driver data editor directly"""
        try:
            from driver_table_editor import DriverTableEditor
            
            # Use provided data or load from file
            if data is None or fieldnames is None:
                output_file = self.output_file.get()
                if not os.path.exists(output_file):
                    messagebox.showwarning("Warning", f"Output file doesn't exist:\n{output_file}")
                    self.enable_buttons()
                    return
                
                # Load data from CSV
                import pandas as pd
                df = pd.read_csv(output_file, encoding='utf-8')
                data = df.to_dict('records')
                fieldnames = list(df.columns)
            
            # Hide main window while editor is open
            self.root.withdraw()
            
            # Open editor with installation folders
            editor = DriverTableEditor(
                data, 
                fieldnames, 
                self.output_file.get(),
                self.install_folder.get(),
                self.teams_folder.get()
            )
            editor.run()
            
            # Show main window again after editor closes
            self.root.deiconify()
            self.enable_buttons()
            
        except Exception as e:
            logger.error(f"Error opening editor: {e}")
            messagebox.showerror("Error", f"Error opening editor:\n{str(e)}")
            self.enable_buttons()
    
    def handle_extraction_error(self, error):
        """Handle extraction error on the main GUI thread"""
        self.progress.stop()
        self.enable_buttons()
        
        logger.error(f"GUI extraction error: {error}")
        self.status_label.config(text=f"Error: {str(error)[:50]}...", foreground="red")
        messagebox.showerror("Error", f"An error occurred:\n{str(error)}")
    
    def run(self):
        """Run the GUI application"""
        self.root.mainloop()

def run_gui():
    """Run the GUI version of the application"""
    gui = DriverExtractorGUI()
    gui.run()
