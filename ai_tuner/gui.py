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
        self.root.title("GTR2 Talent Mass-Tweaker")
        self.root.geometry("500x350")
        self.root.resizable(True, True)
        
        # Variables
        self.config_file = tk.StringVar(value="cfg.yml")
        self.install_folder = tk.StringVar()
        self.teams_folder = tk.StringVar()
        self.debug_mode = tk.BooleanVar(value=False)
        
        # Store extraction results
        self.extraction_result = None
        self.extraction_fieldnames = None
        
        self.setup_ui()
        self.load_config()
    
    def setup_ui(self):
        """Setup the user interface"""
        # Main container
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Title
        title_label = ttk.Label(
            main_frame, 
            text="GTR2 Talent Mass-Tweaker", 
            font=("Arial", 16, "bold")
        )
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 20))
        
        # Description
        desc_label = ttk.Label(
            main_frame,
            text="Extract and edit driver talent data from .car and .rcd files for GTR2",
            wraplength=450
        )
        desc_label.grid(row=1, column=0, columnspan=3, pady=(0, 20))
        
        # GTR2 install folder selection
        ttk.Label(main_frame, text="GTR2 Installation Folder:").grid(
            row=2, column=0, sticky=tk.W, pady=5
        )
        
        install_entry = ttk.Entry(main_frame, textvariable=self.install_folder, width=40)
        install_entry.grid(row=2, column=1, padx=(10, 5), pady=5, sticky=(tk.W, tk.E))
        
        ttk.Button(main_frame, text="Browse...", command=self.browse_install).grid(
            row=2, column=2, padx=(0, 0), pady=5
        )
        
        # Teams folder selection
        ttk.Label(main_frame, text="Teams Folder:").grid(
            row=3, column=0, sticky=tk.W, pady=5
        )
        
        teams_entry = ttk.Entry(main_frame, textvariable=self.teams_folder, width=40)
        teams_entry.grid(row=3, column=1, padx=(10, 5), pady=5, sticky=(tk.W, tk.E))
        
        ttk.Button(main_frame, text="Browse...", command=self.browse_teams).grid(
            row=3, column=2, padx=(0, 0), pady=5
        )
        
        # Debug mode checkbox
        debug_check = ttk.Checkbutton(
            main_frame, 
            text="Enable Debug Mode (verbose output)", 
            variable=self.debug_mode
        )
        debug_check.grid(row=4, column=0, columnspan=3, pady=10, sticky=tk.W)
        
        # Status label
        self.status_label = ttk.Label(main_frame, text="Ready", foreground="green")
        self.status_label.grid(row=5, column=0, columnspan=3, pady=(10, 0))
        
        # Progress bar
        self.progress = ttk.Progressbar(main_frame, mode='indeterminate')
        self.progress.grid(row=6, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(10, 0))
        
        # Loading message (initially hidden)
        self.loading_label = ttk.Label(main_frame, text="", font=("Arial", 10, "italic"))
        self.loading_label.grid(row=7, column=0, columnspan=3, pady=(5, 0))
        
        # Buttons frame
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=8, column=0, columnspan=3, pady=(20, 0))
        
        # Single main action button
        self.main_action_button = ttk.Button(
            button_frame, 
            text="Extract & Edit Talent Data", 
            command=self.extract_and_edit,
            state='normal'
        )
        self.main_action_button.pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Button(button_frame, text="Exit", command=self.safe_quit).pack(
            side=tk.LEFT, padx=(10, 0)
        )
        
        # Help text
        help_text = """
Common GTR2 folder structure:
  GTR2 Installation: C:/Games/GTR2
  Teams Folder: C:/Games/GTR2/GameData/Teams

Click 'Extract & Edit Talent Data' to extract driver data and open the editor.
        """
        
        help_label = ttk.Label(main_frame, text=help_text, justify=tk.LEFT)
        help_label.grid(row=9, column=0, columnspan=3, pady=(20, 0), sticky=tk.W)
        
        # Configure grid weights
        main_frame.columnconfigure(1, weight=1)
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        
        # Track variable changes to auto-save config
        self.install_folder.trace_add("write", self.auto_save_config)
        self.teams_folder.trace_add("write", self.auto_save_config)
        self.debug_mode.trace_add("write", self.auto_save_config)
    
    def auto_save_config(self, *args):
        """Automatically save config when values change"""
        config_path = self.config_file.get()
        if config_path and os.path.exists(os.path.dirname(config_path) if os.path.dirname(config_path) else "."):
            self.save_config(silent=True)
    
    def extract_and_edit(self):
        """Extract data and then open editor directly"""
        # First extract the data
        if not self.start_extraction():
            return
        
        # The editor will be opened from handle_extraction_result
    
    def load_config(self):
        """Load configuration from YAML file"""
        config_path = self.config_file.get()
        if not config_path or not os.path.exists(config_path):
            # Create default config if it doesn't exist
            self.save_config(silent=True)
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
            
            if 'debug' in config:
                self.debug_mode.set(config['debug'])
            
            self.status_label.config(text=f"Loaded config from: {os.path.basename(config_path)}", foreground="green")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load config:\n{str(e)}")
    
    def save_config(self, silent=False):
        """Save configuration to YAML file"""
        config_path = self.config_file.get()
        if not config_path:
            return
        
        config = {
            'gtr2_install': self.install_folder.get(),
            'teams_folder': self.teams_folder.get(),
            'debug': self.debug_mode.get()
        }
        
        try:
            with open(config_path, 'w') as f:
                yaml.dump(config, f, default_flow_style=False)
            
            if not silent:
                self.status_label.config(text=f"Config saved: {os.path.basename(config_path)}", foreground="green")
                messagebox.showinfo("Success", f"Configuration saved to:\n{config_path}")
            
        except Exception as e:
            if not silent:
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
    
    def start_extraction(self):
        """Start the extraction process"""
        # Validate inputs
        if not self.install_folder.get():
            messagebox.showerror("Error", "Please select the GTR2 installation folder")
            return False
        
        if not self.teams_folder.get():
            messagebox.showerror("Error", "Please select the teams folder")
            return False
        
        # Check if folders exist
        if not os.path.exists(self.install_folder.get()):
            messagebox.showerror("Error", f"GTR2 folder does not exist:\n{self.install_folder.get()}")
            return False
        
        if not os.path.exists(self.teams_folder.get()):
            messagebox.showerror("Error", f"Teams folder does not exist:\n{self.teams_folder.get()}")
            return False
        
        # Show loading message and start progress bar
        self.loading_label.config(text="Processing data, please wait...", foreground="blue")
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
                if isinstance(child, ttk.Button):
                    child.state(['disabled'])
    
    def enable_buttons(self):
        """Enable buttons after processing"""
        self.main_action_button.state(['!disabled'])
        for widget in self.root.winfo_children():
            for child in widget.winfo_children():
                if isinstance(child, ttk.Button):
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
                    # Use default output filename
                    output_file = "result.csv"
                    csv_success = CSVWriter.write_drivers_to_csv(data, fieldnames, output_file)
                    
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
            # Update loading message to show we're preparing the editor
            self.loading_label.config(text="Preparing talent editor...", foreground="green")
            self.status_label.config(text="Extraction completed!", foreground="green")
            
            # Schedule the editor to open after a brief pause
            self.root.after(100, lambda: self.prepare_and_open_viewer(data, fieldnames))
        else:
            self.loading_label.config(text="", foreground="")
            self.status_label.config(text="Extraction failed", foreground="red")
            messagebox.showerror("Error", "Extraction process failed or no data found")
            self.enable_buttons()
    
    def prepare_and_open_viewer(self, data=None, fieldnames=None):
        """Prepare and open the editor with smoother transition"""
        try:
            # Update loading message
            self.loading_label.config(text="Opening talent editor...", foreground="green")
            
            # Force GUI update to show the message
            self.root.update_idletasks()
            
            # Create the editor in the background
            threading.Thread(target=self.create_and_show_editor, 
                           args=(data, fieldnames), 
                           daemon=True).start()
            
        except Exception as e:
            logger.error(f"Error preparing editor: {e}")
            messagebox.showerror("Error", f"Error preparing editor:\n{str(e)}")
            self.root.deiconify()
            self.loading_label.config(text="", foreground="")
            self.enable_buttons()
    
    def create_and_show_editor(self, data=None, fieldnames=None):
        """Create and show the editor in a separate thread"""
        try:
            from driver_table_editor import DriverTableEditor
            
            # Use provided data or load from file
            if data is None or fieldnames is None:
                output_file = "result.csv"
                if not os.path.exists(output_file):
                    self.root.after(0, lambda: messagebox.showwarning("Warning", 
                        f"Output file doesn't exist:\n{output_file}"))
                    self.root.after(0, lambda: self.loading_label.config(text="", foreground=""))
                    self.root.after(0, self.enable_buttons)
                    return
                
                # Load data from CSV
                import pandas as pd
                df = pd.read_csv(output_file, encoding='utf-8')
                data = df.to_dict('records')
                fieldnames = list(df.columns)
            
            # Create the editor (this can take a moment with large datasets)
            editor = DriverTableEditor(
                data, 
                fieldnames, 
                "result.csv",
                self.install_folder.get(),
                self.teams_folder.get()
            )
            
            # Schedule on main thread: hide main window and show editor
            self.root.after(0, self.show_editor, editor)
            
        except Exception as e:
            logger.error(f"Error creating editor: {e}")
            self.root.after(0, lambda: messagebox.showerror("Error", 
                f"Error creating editor:\n{str(e)}"))
            self.root.after(0, lambda: self.root.deiconify())
            self.root.after(0, lambda: self.loading_label.config(text="", foreground=""))
            self.root.after(0, self.enable_buttons)
    
    def show_editor(self, editor):
        """Show the editor and hide the main window"""
        try:
            # Hide main window
            self.root.withdraw()
            
            # Clear loading message
            self.loading_label.config(text="", foreground="")
            
            # Set focus to editor
            editor.root.focus_set()
            
            # Use wait_window to wait for the editor to close
            self.root.wait_window(editor.root)
            
            # When editor closes, show main window again
            self.root.deiconify()
            self.enable_buttons()
            self.status_label.config(text="Ready to extract again", foreground="green")
            
        except Exception as e:
            logger.error(f"Error showing editor: {e}")
            self.root.deiconify()
            self.loading_label.config(text="", foreground="")
            self.enable_buttons()
            messagebox.showerror("Error", f"Error showing editor:\n{str(e)}")
    
    def handle_extraction_error(self, error):
        """Handle extraction error on the main GUI thread"""
        self.progress.stop()
        self.loading_label.config(text="", foreground="")
        self.enable_buttons()
        
        logger.error(f"GUI extraction error: {error}")
        self.status_label.config(text=f"Error: {str(error)[:50]}...", foreground="red")
        messagebox.showerror("Error", f"An error occurred:\n{str(error)}")
    
    def safe_quit(self):
        """Safely quit the application"""
        try:
            self.root.quit()
            self.root.destroy()
        except:
            pass
    
    def run(self):
        """Run the GUI application"""
        self.root.mainloop()


# ADD THIS FUNCTION AT THE MODULE LEVEL
def run_gui():
    """Run the GUI version of the application"""
    gui = DriverExtractorGUI()
    gui.run()


# Optional: Add this to run the GUI if this file is executed directly
if __name__ == "__main__":
    run_gui()
