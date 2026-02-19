# pipenv install; pipenv run pip install numpy matplotlib
# pipenv run python3 tire_slip_editor.py <path to .tyr file>
import re
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure
import sys

class TireCurveEditor:
    def __init__(self, filename):
        self.filename = filename
        self.data = self.parse_tire_file(filename)
        self.current_curve_index = 0
        self.modified_curves = {}
        
        # Create main window
        self.root = tk.Tk()
        self.root.title(f"Tire Curve Editor - {Path(filename).name}")
        self.root.geometry("1200x800")
        
        self.setup_ui()
        self.load_curve(0)
        
    def parse_tire_file(self, filename):
        """Parse the tire file and return structured data"""
        with open(filename, 'r') as f:
            self.original_content = f.read()
        
        # Parse slip curves
        slip_curve_pattern = r'(\[SLIPCURVE\]\s*Name="([^"]+)"\s*Step=([0-9.e+-]+)[^\n]*\s*DropoffFunction=([0-9.e+-]+)[^\n]*\s*Data:\s*((?:\d+\.\d+\s*)+))'
        slip_curves = []
        self.curve_matches = []
        
        for match in re.finditer(slip_curve_pattern, self.original_content, re.MULTILINE | re.DOTALL):
            full_match = match.group(1)
            name = match.group(2)
            step = float(match.group(3))
            dropoff = float(match.group(4))
            
            # Parse the data values
            data_str = match.group(5).strip()
            values = [float(x) for x in data_str.split()]
            
            slip_curves.append({
                'name': name,
                'step': step,
                'dropoff_function': dropoff,
                'values': values,
                'x_values': [i * step for i in range(len(values))],
                'full_match': full_match,
                'data_str': data_str
            })
            self.curve_matches.append(match)
        
        return {'slip_curves': slip_curves}
    
    def setup_ui(self):
        """Setup the user interface"""
        # Create main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Control panel
        control_frame = ttk.LabelFrame(main_frame, text="Controls", padding="10")
        control_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # Curve selection
        ttk.Label(control_frame, text="Select Curve:").grid(row=0, column=0, padx=5)
        self.curve_var = tk.StringVar()
        self.curve_combo = ttk.Combobox(control_frame, textvariable=self.curve_var, 
                                        values=[c['name'] for c in self.data['slip_curves']],
                                        state='readonly', width=20)
        self.curve_combo.grid(row=0, column=1, padx=5)
        self.curve_combo.bind('<<ComboboxSelected>>', self.on_curve_selected)
        
        # Step modification
        ttk.Label(control_frame, text="New Step:").grid(row=0, column=2, padx=(20,5))
        self.step_var = tk.StringVar()
        self.step_entry = ttk.Entry(control_frame, textvariable=self.step_var, width=15)
        self.step_entry.grid(row=0, column=3, padx=5)
        ttk.Button(control_frame, text="Apply Step", command=self.apply_step).grid(row=0, column=4, padx=5)
        
        # Modification buttons
        ttk.Label(control_frame, text="Modify Curve:").grid(row=1, column=0, padx=5, pady=10)
        ttk.Button(control_frame, text="Multiply by Factor", command=self.multiply_curve).grid(row=1, column=1, padx=2)
        ttk.Button(control_frame, text="Add Offset", command=self.add_offset).grid(row=1, column=2, padx=2)
        ttk.Button(control_frame, text="Smooth", command=self.smooth_curve).grid(row=1, column=3, padx=2)
        ttk.Button(control_frame, text="Reset to Original", command=self.reset_curve).grid(row=1, column=4, padx=2)
        
        # File operations
        file_frame = ttk.LabelFrame(control_frame, text="File Operations", padding="5")
        file_frame.grid(row=2, column=0, columnspan=5, pady=10, sticky=(tk.W, tk.E))
        
        ttk.Button(file_frame, text="Save Changes", command=self.save_changes).pack(side=tk.LEFT, padx=5)
        ttk.Button(file_frame, text="Save As...", command=self.save_as).pack(side=tk.LEFT, padx=5)
        ttk.Button(file_frame, text="Revert All", command=self.revert_all).pack(side=tk.LEFT, padx=5)
        
        # Status label
        self.status_var = tk.StringVar(value="Ready")
        status_label = ttk.Label(control_frame, textvariable=self.status_var, foreground="blue")
        status_label.grid(row=3, column=0, columnspan=5, pady=5)
        
        # Plot frame
        plot_frame = ttk.LabelFrame(main_frame, text="Curve Visualization", padding="10")
        plot_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Create matplotlib figure
        self.fig = Figure(figsize=(10, 6), dpi=100)
        self.ax = self.fig.add_subplot(111)
        
        # Embed in tkinter
        self.canvas = FigureCanvasTkAgg(self.fig, master=plot_frame)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=1)
        
        # Add toolbar
        toolbar_frame = ttk.Frame(plot_frame)
        toolbar_frame.pack(side=tk.BOTTOM, fill=tk.X)
        self.toolbar = NavigationToolbar2Tk(self.canvas, toolbar_frame)
        self.toolbar.update()
        
        # Statistics frame
        stats_frame = ttk.LabelFrame(main_frame, text="Curve Statistics", padding="10")
        stats_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=10)
        
        self.stats_text = tk.Text(stats_frame, height=4, width=80)
        self.stats_text.pack()
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(1, weight=1)
    
    def load_curve(self, index):
        """Load and display a curve"""
        self.current_curve_index = index
        curve = self.data['slip_curves'][index]
        
        # Use modified values if available
        if index in self.modified_curves:
            values = self.modified_curves[index]['values']
            step = self.modified_curves[index]['step']
        else:
            values = curve['values']
            step = curve['step']
        
        x_values = [i * step for i in range(len(values))]
        
        # Clear and redraw
        self.ax.clear()
        self.ax.plot(x_values, values, 'b-', linewidth=2, label=curve['name'])
        
        # Mark peak
        peak_idx = np.argmax(values)
        peak_x = x_values[peak_idx]
        peak_y = values[peak_idx]
        self.ax.plot(peak_x, peak_y, 'r*', markersize=12, label=f'Peak: {peak_y:.3f}')
        self.ax.axvline(x=peak_x, color='g', linestyle='--', alpha=0.5)
        
        # Customize
        self.ax.set_xlabel('Slip')
        self.ax.set_ylabel('Normalized Force')
        self.ax.set_title(f'{curve["name"]} - Step: {step}')
        self.ax.grid(True, alpha=0.3)
        self.ax.legend(loc='best')
        
        self.canvas.draw()
        
        # Update statistics
        self.update_statistics(values, step)
        
        # Update step entry
        self.step_var.set(str(step))
        
        # Update status
        if index in self.modified_curves:
            self.status_var.set(f"Curve modified (unsaved changes)")
        else:
            self.status_var.set(f"Original curve")
    
    def update_statistics(self, values, step):
        """Update statistics display"""
        x_values = [i * step for i in range(len(values))]
        peak_idx = np.argmax(values)
        
        stats = f"Points: {len(values)}\n"
        stats += f"Max Slip: {x_values[-1]:.3f}\n"
        stats += f"Peak Value: {values[peak_idx]:.3f} @ {x_values[peak_idx]:.3f}\n"
        stats += f"Min Value: {min(values):.3f}\n"
        stats += f"Mean Value: {np.mean(values):.3f}\n"
        stats += f"Step Size: {step}"
        
        self.stats_text.delete(1.0, tk.END)
        self.stats_text.insert(1.0, stats)
    
    def on_curve_selected(self, event):
        """Handle curve selection change"""
        selected_name = self.curve_var.get()
        for i, curve in enumerate(self.data['slip_curves']):
            if curve['name'] == selected_name:
                self.load_curve(i)
                break
    
    def apply_step(self):
        """Apply new step size to current curve"""
        try:
            new_step = float(self.step_var.get())
            if new_step <= 0:
                raise ValueError("Step must be positive")
            
            curve = self.data['slip_curves'][self.current_curve_index]
            
            # Store modified curve
            if self.current_curve_index not in self.modified_curves:
                self.modified_curves[self.current_curve_index] = {
                    'values': curve['values'].copy(),
                    'step': curve['step']
                }
            
            self.modified_curves[self.current_curve_index]['step'] = new_step
            self.load_curve(self.current_curve_index)
            
        except ValueError as e:
            messagebox.showerror("Error", f"Invalid step value: {e}")
    
    def multiply_curve(self):
        """Multiply curve values by a factor"""
        factor = simpledialog.askfloat("Multiply", "Enter multiplication factor:", 
                                       minvalue=0.0, maxvalue=10.0, initialvalue=1.0)
        if factor is not None:
            curve = self.data['slip_curves'][self.current_curve_index]
            
            # Store modified curve
            if self.current_curve_index not in self.modified_curves:
                self.modified_curves[self.current_curve_index] = {
                    'values': curve['values'].copy(),
                    'step': curve['step']
                }
            
            # Apply multiplication
            self.modified_curves[self.current_curve_index]['values'] = [
                v * factor for v in self.modified_curves[self.current_curve_index]['values']
            ]
            
            self.load_curve(self.current_curve_index)
    
    def add_offset(self):
        """Add offset to curve values"""
        offset = simpledialog.askfloat("Add Offset", "Enter offset value:", 
                                       initialvalue=0.0)
        if offset is not None:
            curve = self.data['slip_curves'][self.current_curve_index]
            
            # Store modified curve
            if self.current_curve_index not in self.modified_curves:
                self.modified_curves[self.current_curve_index] = {
                    'values': curve['values'].copy(),
                    'step': curve['step']
                }
            
            # Apply offset
            self.modified_curves[self.current_curve_index]['values'] = [
                v + offset for v in self.modified_curves[self.current_curve_index]['values']
            ]
            
            self.load_curve(self.current_curve_index)
    
    def smooth_curve(self):
        """Apply smoothing to the curve"""
        window = simpledialog.askinteger("Smooth", "Enter smoothing window size (odd number):", 
                                         minvalue=3, maxvalue=21, initialvalue=5)
        if window is not None and window % 2 == 1:
            curve = self.data['slip_curves'][self.current_curve_index]
            
            # Store modified curve
            if self.current_curve_index not in self.modified_curves:
                self.modified_curves[self.current_curve_index] = {
                    'values': curve['values'].copy(),
                    'step': curve['step']
                }
            
            # Apply smoothing (moving average)
            values = np.array(self.modified_curves[self.current_curve_index]['values'])
            kernel = np.ones(window) / window
            smoothed = np.convolve(values, kernel, mode='same')
            
            # Handle edges
            smoothed[:window//2] = values[:window//2]
            smoothed[-(window//2):] = values[-(window//2):]
            
            self.modified_curves[self.current_curve_index]['values'] = smoothed.tolist()
            self.load_curve(self.current_curve_index)
        elif window is not None:
            messagebox.showerror("Error", "Window size must be odd")
    
    def reset_curve(self):
        """Reset current curve to original"""
        if self.current_curve_index in self.modified_curves:
            del self.modified_curves[self.current_curve_index]
            self.load_curve(self.current_curve_index)
    
    def revert_all(self):
        """Revert all curves to original"""
        if messagebox.askyesno("Confirm", "Revert all changes?"):
            self.modified_curves.clear()
            self.load_curve(self.current_curve_index)
    
    def save_changes(self):
        """Save changes to the current file"""
        self.save_to_file(self.filename)
    
    def save_as(self):
        """Save to a new file"""
        from tkinter import filedialog
        filename = filedialog.asksaveasfilename(
            defaultextension=".tbc",
            filetypes=[("Tire files", "*.tbc"), ("Text files", "*.txt"), ("All files", "*.*")]
        )
        if filename:
            self.save_to_file(filename)
    
    def save_to_file(self, filename):
        """Save the modified curves to a file"""
        try:
            new_content = self.original_content
            
            # Apply modifications in reverse order to maintain string positions
            for idx in sorted(self.modified_curves.keys(), reverse=True):
                mod = self.modified_curves[idx]
                original_curve = self.data['slip_curves'][idx]
                
                # Format new data string
                values = mod['values']
                step = mod['step']
                
                # Format values with 6 decimal places, 10 per line
                data_lines = []
                for i in range(0, len(values), 10):
                    line_values = values[i:i+10]
                    data_lines.append(' '.join(f"{v:.6f}" for v in line_values))
                new_data_str = '\n'.join(data_lines)
                
                # Create new block
                new_block = f'[SLIPCURVE]\nName="{original_curve["name"]}"\nStep={step:.6f}            // Slip step\nDropoffFunction={original_curve["dropoff_function"]:.1f}      // see above            \nData:\n{new_data_str}'
                
                # Replace in content
                new_content = new_content.replace(original_curve['full_match'], new_block)
            
            # Write to file
            with open(filename, 'w') as f:
                f.write(new_content)
            
            # Update original content and clear modifications
            self.original_content = new_content
            self.modified_curves.clear()
            
            # Reparse the file to update matches
            self.data = self.parse_tire_file(filename)
            
            messagebox.showinfo("Success", f"Changes saved to {filename}")
            self.status_var.set("Changes saved")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save: {e}")
    
    def run(self):
        """Start the application"""
        self.root.mainloop()

def main():
    if len(sys.argv) < 2:
        print("Usage: python tire_editor.py <tire_file>")
        print("\nExample:")
        print("  python tire_editor.py tire.tbc")
        return
    
    filename = sys.argv[1]
    
    try:
        app = TireCurveEditor(filename)
        app.run()
    except FileNotFoundError:
        print(f"Error: File '{filename}' not found.")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
