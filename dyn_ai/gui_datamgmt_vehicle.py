#!/usr/bin/env python3
"""
Vehicle Classes tab for Setup Manager (Tkinter version)
Manages vehicle classes and assignments - embedded directly in the tab
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import json
import threading
from pathlib import Path
from typing import List, Set, Optional

from core_vehicle_scanner import scan_vehicles_from_gtr2
from core_config import get_base_path, get_config_with_defaults


def get_vehicle_classes_path() -> Path:
    """Get the path to vehicle_classes.json"""
    import sys
    if getattr(sys, 'frozen', False):
        exe_dir = Path(sys.executable).parent
        classes_path = exe_dir / "vehicle_classes.json"
        if classes_path.exists():
            return classes_path
        return Path.cwd() / "vehicle_classes.json"
    else:
        try:
            from gui_common import get_data_file_path
            return get_data_file_path("vehicle_classes.json")
        except ImportError:
            return Path.cwd() / "vehicle_classes.json"


DEFAULT_VEHICLE_CLASSES = {
    "GT_0304": {
        "classes": ["GT_0304"],
        "vehicles": [
            "Chrysler Viper GTS-R",
            "Ferrari 550 Maranello",
            "Ferrari 550",
            "Ferrari 575 GTC",
            "Lamborghini Murcielago R-GT",
            "Lister Storm",
            "Porsche 911 GT2",
            "Saleen S7-R",
            "Porsche 996"
        ]
    },
    "NGT_0304": {
        "classes": ["NGT_0304"],
        "vehicles": [
            "Ferrari 360 GTC",
            "Ferrari 360 Modena",
            "Porsche GT3-RS",
            "Porsche GT3-RSR",
            "TVR T400R",
            "Nissan 350Z"
        ]
    },
    "Spa_0304": {
        "classes": ["Spa_0304"],
        "vehicles": [
            "BMW M3",
            "BMW M3 GTR",
            "BMW Z3 M",
            "Chevrolet Corvette C5-R",
            "Gillet Vertigo Streiff",
            "Lotus Elise",
            "Morgan Aero 8",
            "Mosler MT900R",
            "Porsche 911 Biturbo",
            "Porsche 911 GT3 Cup",
            "Seat Toledo GT",
            "Viper Competition Coupe"
        ]
    },
    "OTHER": {
        "classes": ["OTHER"],
        "vehicles": [
            "2003 SafetyCar"
        ]
    }
}


class VehicleClassesManager:
    """Manages the vehicle_classes.json file"""
    
    def __init__(self, file_path: Path = None):
        self.file_path = file_path or get_vehicle_classes_path()
        self.data = {}
        self.load()
    
    def load(self) -> bool:
        if not self.file_path.exists():
            self.data = DEFAULT_VEHICLE_CLASSES.copy()
            self.save()
            return True
        
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                self.data = json.load(f)
            return True
        except Exception as e:
            print(f"Error loading vehicle classes: {e}")
            self.data = DEFAULT_VEHICLE_CLASSES.copy()
            return False
    
    def save(self) -> bool:
        try:
            self.file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.file_path, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"Error saving vehicle classes: {e}")
            return False
    
    def get_all_classes(self) -> List[str]:
        return list(self.data.keys())
    
    def get_vehicles_for_class(self, class_name: str) -> List[str]:
        if class_name in self.data:
            return self.data[class_name].get("vehicles", [])
        return []
    
    def get_all_vehicles(self) -> Set[str]:
        all_vehicles = set()
        for class_data in self.data.values():
            all_vehicles.update(class_data.get("vehicles", []))
        return all_vehicles
    
    def get_vehicle_class(self, vehicle_name: str) -> Optional[str]:
        vehicle_lower = vehicle_name.lower().strip()
        for class_name, class_data in self.data.items():
            for vehicle in class_data.get("vehicles", []):
                if vehicle.lower() == vehicle_lower:
                    return class_name
        return None
    
    def add_class(self, class_name: str, classes_list: List[str] = None, vehicles: List[str] = None) -> bool:
        if class_name in self.data:
            return False
        self.data[class_name] = {
            "classes": classes_list or [class_name],
            "vehicles": vehicles or []
        }
        return self.save()
    
    def delete_class(self, class_name: str) -> bool:
        if class_name not in self.data:
            return False
        del self.data[class_name]
        return self.save()
    
    def rename_class(self, old_name: str, new_name: str) -> bool:
        if old_name not in self.data or new_name in self.data:
            return False
        self.data[new_name] = self.data.pop(old_name)
        if new_name not in self.data[new_name]["classes"]:
            self.data[new_name]["classes"] = [new_name]
        return self.save()
    
    def add_vehicle(self, class_name: str, vehicle_name: str) -> bool:
        if class_name not in self.data:
            return False
        if vehicle_name not in self.data[class_name]["vehicles"]:
            self.data[class_name]["vehicles"].append(vehicle_name)
            self.data[class_name]["vehicles"].sort()
            return self.save()
        return False
    
    def add_vehicles_batch(self, class_name: str, vehicle_names: List[str]) -> int:
        if class_name not in self.data:
            return 0
        added = 0
        for vehicle_name in vehicle_names:
            if vehicle_name not in self.data[class_name]["vehicles"]:
                self.data[class_name]["vehicles"].append(vehicle_name)
                added += 1
        if added > 0:
            self.data[class_name]["vehicles"].sort()
            self.save()
        return added
    
    def remove_vehicle(self, class_name: str, vehicle_name: str) -> bool:
        if class_name not in self.data:
            return False
        if vehicle_name in self.data[class_name]["vehicles"]:
            self.data[class_name]["vehicles"].remove(vehicle_name)
            return self.save()
        return False
    
    def remove_vehicles_batch(self, class_name: str, vehicle_names: List[str]) -> int:
        if class_name not in self.data:
            return 0
        removed = 0
        for vehicle_name in vehicle_names:
            if vehicle_name in self.data[class_name]["vehicles"]:
                self.data[class_name]["vehicles"].remove(vehicle_name)
                removed += 1
        if removed > 0:
            self.data[class_name]["vehicles"].sort()
            self.save()
        return removed
    
    def update_vehicle(self, class_name: str, old_name: str, new_name: str) -> bool:
        if class_name not in self.data:
            return False
        vehicles = self.data[class_name]["vehicles"]
        if old_name in vehicles:
            idx = vehicles.index(old_name)
            vehicles[idx] = new_name
            vehicles.sort()
            return self.save()
        return False
    
    def get_unassigned_vehicles(self, all_vehicles: Set[str]) -> List[str]:
        assigned = self.get_all_vehicles()
        unassigned = all_vehicles - assigned
        return sorted(unassigned)


class AddEditClassDialog(tk.Toplevel):
    """Dialog for adding or editing a vehicle class"""
    
    def __init__(self, parent, class_name: str = None, vehicles: List[str] = None):
        super().__init__(parent)
        self.parent = parent
        self.class_name = class_name
        self.vehicles = vehicles or []
        self.result = None
        
        self.title("Edit Class" if class_name else "Add New Class")
        self.geometry("500x400")
        self.configure(bg='#2b2b2b')
        self.transient(parent)
        self.grab_set()
        
        self.setup_ui()
        
        if class_name:
            self.class_name_entry.insert(0, class_name)
            self.class_name_entry.config(state='readonly')
            self.load_vehicles()
    
    def setup_ui(self):
        frame = tk.Frame(self, bg='#2b2b2b', padx=20, pady=20)
        frame.pack(fill=tk.BOTH, expand=True)
        
        tk.Label(frame, text="Class Name:", bg='#2b2b2b', fg='white').pack(anchor=tk.W, pady=5)
        self.class_name_entry = tk.Entry(frame, bg='#3c3c3c', fg='white', width=40)
        self.class_name_entry.pack(fill=tk.X, pady=5)
        
        tk.Label(frame, text="Vehicles in this class:", bg='#2b2b2b', fg='white').pack(anchor=tk.W, pady=(10, 5))
        
        list_frame = tk.Frame(frame, bg='#2b2b2b')
        list_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        scrollbar = tk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.vehicles_listbox = tk.Listbox(list_frame, bg='#3c3c3c', fg='white',
                                            selectmode=tk.EXTENDED,
                                            exportselection=False,
                                            yscrollcommand=scrollbar.set)
        self.vehicles_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.vehicles_listbox.yview)
        
        btn_frame = tk.Frame(frame, bg='#2b2b2b')
        btn_frame.pack(fill=tk.X, pady=10)
        
        tk.Button(btn_frame, text="Add Vehicle", bg='#4CAF50', fg='white',
                  command=self.add_vehicle).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Edit Vehicle", bg='#2196F3', fg='white',
                  command=self.edit_vehicle).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Remove Vehicle(s)", bg='#f44336', fg='white',
                  command=self.remove_vehicles).pack(side=tk.LEFT, padx=5)
        
        dialog_btn_frame = tk.Frame(frame, bg='#2b2b2b')
        dialog_btn_frame.pack(fill=tk.X, pady=(20, 0))
        
        tk.Button(dialog_btn_frame, text="Cancel", command=self.destroy,
                  bg='#555', fg='white', padx=15, pady=5).pack(side=tk.RIGHT, padx=5)
        tk.Button(dialog_btn_frame, text="Save", command=self.save,
                  bg='#4CAF50', fg='white', padx=15, pady=5).pack(side=tk.RIGHT, padx=5)
    
    def load_vehicles(self):
        self.vehicles_listbox.delete(0, tk.END)
        for vehicle in sorted(self.vehicles):
            self.vehicles_listbox.insert(tk.END, vehicle)
    
    def add_vehicle(self):
        dialog = tk.Toplevel(self)
        dialog.title("Add Vehicle")
        dialog.geometry("350x150")
        dialog.configure(bg='#2b2b2b')
        dialog.transient(self)
        dialog.grab_set()
        
        frame = tk.Frame(dialog, bg='#2b2b2b', padx=20, pady=20)
        frame.pack(fill=tk.BOTH, expand=True)
        
        tk.Label(frame, text="Vehicle name:", bg='#2b2b2b', fg='white').pack(anchor=tk.W)
        entry = tk.Entry(frame, bg='#3c3c3c', fg='white', width=40)
        entry.pack(fill=tk.X, pady=5)
        entry.focus()
        
        def save():
            name = entry.get().strip()
            if name and name not in self.vehicles:
                self.vehicles.append(name)
                self.vehicles.sort()
                self.load_vehicles()
            dialog.destroy()
        
        tk.Button(frame, text="Cancel", command=dialog.destroy,
                  bg='#555', fg='white').pack(side=tk.RIGHT, padx=5, pady=10)
        tk.Button(frame, text="Add", command=save,
                  bg='#4CAF50', fg='white').pack(side=tk.RIGHT, padx=5, pady=10)
        
        entry.bind('<Return>', lambda e: save())
    
    def edit_vehicle(self):
        selection = self.vehicles_listbox.curselection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a vehicle to edit.")
            return
        
        old_name = self.vehicles_listbox.get(selection[0])
        
        dialog = tk.Toplevel(self)
        dialog.title("Edit Vehicle")
        dialog.geometry("350x150")
        dialog.configure(bg='#2b2b2b')
        dialog.transient(self)
        dialog.grab_set()
        
        frame = tk.Frame(dialog, bg='#2b2b2b', padx=20, pady=20)
        frame.pack(fill=tk.BOTH, expand=True)
        
        tk.Label(frame, text="New vehicle name:", bg='#2b2b2b', fg='white').pack(anchor=tk.W)
        entry = tk.Entry(frame, bg='#3c3c3c', fg='white', width=40)
        entry.insert(0, old_name)
        entry.pack(fill=tk.X, pady=5)
        entry.focus()
        
        def save():
            new_name = entry.get().strip()
            if new_name and new_name != old_name:
                idx = self.vehicles.index(old_name)
                self.vehicles[idx] = new_name
                self.vehicles.sort()
                self.load_vehicles()
            dialog.destroy()
        
        tk.Button(frame, text="Cancel", command=dialog.destroy,
                  bg='#555', fg='white').pack(side=tk.RIGHT, padx=5, pady=10)
        tk.Button(frame, text="Save", command=save,
                  bg='#4CAF50', fg='white').pack(side=tk.RIGHT, padx=5, pady=10)
        
        entry.bind('<Return>', lambda e: save())
    
    def remove_vehicles(self):
        selection = self.vehicles_listbox.curselection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select vehicles to remove.")
            return
        
        for idx in selection:
            vehicle = self.vehicles_listbox.get(idx)
            if vehicle in self.vehicles:
                self.vehicles.remove(vehicle)
        
        self.load_vehicles()
    
    def save(self):
        class_name = self.class_name_entry.get().strip()
        if not class_name:
            messagebox.showwarning("Invalid", "Class name cannot be empty.")
            return
        self.result = (class_name, self.vehicles)
        self.destroy()


class VehicleImportWorker(threading.Thread):
    """Worker thread for importing vehicles from GTR2"""
    
    def __init__(self, gtr2_path: Path, callback, progress_callback=None):
        super().__init__()
        self.gtr2_path = gtr2_path
        self.callback = callback
        self.progress_callback = progress_callback
        self.daemon = True
    
    def run(self):
        try:
            vehicles = scan_vehicles_from_gtr2(self.gtr2_path, self.progress_callback)
            self.callback(vehicles, None)
        except Exception as e:
            self.callback(None, str(e))


class VehicleTab(tk.Frame):
    """Vehicle Classes tab - embedded vehicle manager"""
    
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.manager = VehicleClassesManager()
        self.imported_vehicles = set()
        self.current_class = None
        self.gtr2_path = None
        
        self.configure(bg='#1e1e1e')
        self.setup_ui()
        self.load_classes()
        self.load_gtr2_path_from_config()
    
    def load_gtr2_path_from_config(self):
        """Load GTR2 path from cfg.yml and update the display"""
        config = get_config_with_defaults()
        base_path = config.get('base_path', '')
        
        if base_path and Path(base_path).exists():
            self.gtr2_path = Path(base_path)
            self.gtr2_path_label.config(text=str(self.gtr2_path), fg='#4CAF50')
            self.import_btn.config(state=tk.NORMAL)
            self.import_status.config(text="GTR2 path loaded from cfg.yml. Click 'Import Cars' to scan vehicles.")
        else:
            self.gtr2_path_label.config(text="No GTR2 folder selected. Please browse to select or configure in cfg.yml.", fg='#888')
            self.import_btn.config(state=tk.DISABLED)
            self.import_status.config(text="")
    
    def setup_ui(self):
        # Main horizontal split
        paned = tk.PanedWindow(self, orient=tk.HORIZONTAL, bg='#1e1e1e', sashwidth=2)
        paned.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Left panel - Class list
        left_frame = tk.Frame(paned, bg='#1e1e1e')
        paned.add(left_frame, width=400)
        
        classes_frame = tk.LabelFrame(left_frame, text="Vehicle Classes", bg='#1e1e1e',
                      fg='#FFA500', font=('Arial', 10, 'bold'))
        classes_frame.pack(fill=tk.BOTH, expand=True)
        
        classes_inner = tk.Frame(classes_frame, bg='#1e1e1e')
        classes_inner.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        classes_list_frame = tk.Frame(classes_inner, bg='#1e1e1e')
        classes_list_frame.pack(fill=tk.BOTH, expand=True)
        
        classes_scrollbar = tk.Scrollbar(classes_list_frame)
        classes_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # exportselection=False prevents this listbox from losing its highlight
        # when the user clicks in another listbox (vehicles or unassigned).
        self.classes_listbox = tk.Listbox(classes_list_frame, bg='#2b2b2b', fg='#4CAF50',
                                         selectmode=tk.SINGLE,
                                         exportselection=False,
                                         yscrollcommand=classes_scrollbar.set,
                                         font=('Arial', 10))
        self.classes_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        classes_scrollbar.config(command=self.classes_listbox.yview)
        
        self.classes_listbox.bind('<<ListboxSelect>>', self.on_class_selected)
        
        class_btn_frame = tk.Frame(classes_frame, bg='#1e1e1e')
        class_btn_frame.pack(fill=tk.X, pady=10)
        
        tk.Button(class_btn_frame, text="Add Class", bg='#4CAF50', fg='white',
                  command=self.add_class).pack(side=tk.LEFT, padx=2)
        tk.Button(class_btn_frame, text="Rename", bg='#2196F3', fg='white',
                  command=self.rename_class).pack(side=tk.LEFT, padx=2)
        tk.Button(class_btn_frame, text="Delete", bg='#f44336', fg='white',
                  command=self.delete_class).pack(side=tk.LEFT, padx=2)
        
        # Middle panel - Vehicles in selected class
        middle_frame = tk.Frame(paned, bg='#1e1e1e')
        paned.add(middle_frame, width=500)
        
        self.selected_class_label = tk.Label(middle_frame, text="No class selected",
                                              bg='#1e1e1e', fg='#FFA500',
                                              font=('Arial', 12, 'bold'))
        self.selected_class_label.pack(anchor=tk.W, pady=(0, 5))
        
        tk.Label(middle_frame, text="Vehicles in this class:", bg='#1e1e1e', fg='white').pack(anchor=tk.W)
        
        vehicle_list_frame = tk.Frame(middle_frame, bg='#1e1e1e')
        vehicle_list_frame.pack(fill=tk.BOTH, expand=True)
        
        vehicle_scrollbar = tk.Scrollbar(vehicle_list_frame)
        vehicle_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # exportselection=False prevents this listbox from clearing its selection
        # when the user clicks in another listbox.
        self.vehicles_listbox = tk.Listbox(vehicle_list_frame, bg='#2b2b2b', fg='white',
                                            selectmode=tk.EXTENDED,
                                            exportselection=False,
                                            yscrollcommand=vehicle_scrollbar.set,
                                            font=('Courier', 10))
        self.vehicles_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vehicle_scrollbar.config(command=self.vehicles_listbox.yview)
        
        vehicle_btn_frame = tk.Frame(middle_frame, bg='#1e1e1e')
        vehicle_btn_frame.pack(fill=tk.X, pady=10)
        
        tk.Button(vehicle_btn_frame, text="Add Vehicle", bg='#4CAF50', fg='white',
                  command=self.add_vehicle).pack(side=tk.LEFT, padx=2)
        tk.Button(vehicle_btn_frame, text="Edit Vehicle", bg='#2196F3', fg='white',
                  command=self.edit_vehicle).pack(side=tk.LEFT, padx=2)
        tk.Button(vehicle_btn_frame, text="Remove Vehicle(s)", bg='#f44336', fg='white',
                  command=self.remove_vehicles).pack(side=tk.LEFT, padx=2)
        
        # Right panel - Unassigned vehicles
        right_frame = tk.Frame(paned, bg='#1e1e1e')
        paned.add(right_frame, width=450)
        
        # Unassigned vehicles section
        unassigned_frame = tk.LabelFrame(right_frame, text="Unassigned Vehicles", bg='#1e1e1e',
                                          fg='#FFA500', font=('Arial', 10, 'bold'))
        unassigned_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        unassigned_inner = tk.Frame(unassigned_frame, bg='#1e1e1e')
        unassigned_inner.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        unassigned_list_frame = tk.Frame(unassigned_inner, bg='#1e1e1e')
        unassigned_list_frame.pack(fill=tk.BOTH, expand=True)
        
        unassigned_scrollbar = tk.Scrollbar(unassigned_list_frame)
        unassigned_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # exportselection=False is the key fix: without it, clicking here would
        # steal the selection from class_listbox, triggering <<ListboxSelect>>
        # on it, which caused on_class_selected to clear current_class and the
        # vehicles list.
        self.unassigned_listbox = tk.Listbox(unassigned_list_frame, bg='#2b2b2b', fg='#FFA500',
                                              selectmode=tk.EXTENDED,
                                              exportselection=False,
                                              yscrollcommand=unassigned_scrollbar.set,
                                              font=('Ariel', 10))
        self.unassigned_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        unassigned_scrollbar.config(command=self.unassigned_listbox.yview)
        
        self.unassigned_listbox.bind('<<ListboxSelect>>', self.on_unassigned_selected)
        
        transfer_frame = tk.Frame(unassigned_inner, bg='#1e1e1e')
        transfer_frame.pack(fill=tk.X, pady=10)
        
        self.add_to_class_btn = tk.Button(transfer_frame, text="Add Selected to Class",
                                           bg='#4CAF50', fg='white',
                                           command=self.add_selected_to_class, state=tk.DISABLED)
        self.add_to_class_btn.pack(side=tk.LEFT, padx=2)
        
        tk.Button(transfer_frame, text="Refresh", bg='#2196F3', fg='white',
                  command=self.refresh_unassigned_list).pack(side=tk.LEFT, padx=2)
        
        bottom_frame = tk.Frame(self, bg='#1e1e1e')
        bottom_frame.pack(fill=tk.X, padx=10, pady=10)
        
        save_btn = tk.Button(bottom_frame, text="Save", bg='#4CAF50', fg='white',
                              font=('Arial', 14, 'bold'), padx=50, pady=18,
                              command=self.save_data)
        save_btn.pack(side=tk.RIGHT, padx=5)

        import_frame = tk.LabelFrame(bottom_frame, text="Get list of vehicles installed", bg='#1e1e1e',
                                      fg='#4CAF50', font=('Arial', 10, 'bold'))
        import_frame.pack(fill=tk.X, pady=(0, 10))
        
        import_inner = tk.Frame(import_frame, bg='#1e1e1e')
        import_inner.pack(padx=10, pady=10, fill=tk.X)
        
        
        import_btn_frame = tk.Frame(import_inner, bg='#1e1e1e')
        import_btn_frame.pack(side=tk.LEFT) ##

        self.gtr2_path_label = tk.Label(import_inner, text="",
                                         bg='#1e1e1e', fg='#888', font=('Arial', 10))
        self.gtr2_path_label.pack(side=tk.LEFT) ## 
        
        self.import_btn = tk.Button(import_btn_frame, text="Import Cars from: ", bg='#FF9800', fg='white',
                                     command=self.import_cars, state=tk.DISABLED)
        self.import_btn.pack(side=tk.LEFT, padx=2)

        self.import_status = tk.Label(import_inner, text="", bg='#1e1e1e', fg='#888', font=('Arial', 9))
        self.import_status.pack(side=tk.RIGHT) ##
        
        self.import_progress = ttk.Progressbar(import_inner, mode='indeterminate')
        self.import_progress.pack(fill=tk.X, pady=5)
        self.import_progress.pack_forget()
        
    
    def close_without_saving(self):
        if self.parent and hasattr(self.parent, 'destroy'):
            self.parent.destroy()
    
    def save_data(self):
        if self.manager.save():
            messagebox.showinfo("Success", "Vehicle classes saved successfully!")
        else:
            messagebox.showerror("Error", "Failed to save vehicle classes.")
    
    def save_and_close(self):
        if self.manager.save():
            messagebox.showinfo("Success", "Vehicle classes saved successfully!")
            if self.parent and hasattr(self.parent, 'destroy'):
                self.parent.destroy()
        else:
            messagebox.showerror("Error", "Failed to save vehicle classes.")
    
    def load_classes(self):
        self.classes_listbox.delete(0, tk.END)
        for class_name in self.manager.get_all_classes():
            self.classes_listbox.insert(tk.END, class_name)
    
    def on_class_selected(self, event=None):
        """Called only when the class listbox selection actually changes"""
        selection = self.classes_listbox.curselection()
        if not selection:
            # No class selected - keep current_class as None
            if self.current_class is not None:
                self.current_class = None
                self.selected_class_label.config(text="No class selected")
                self.vehicles_listbox.delete(0, tk.END)
        else:
            class_name = self.classes_listbox.get(selection[0])
            if class_name != self.current_class:
                self.current_class = class_name
                self.selected_class_label.config(text=f"Class: {self.current_class}")
                self.refresh_vehicles_list()
        
        # Update add button state
        self.update_add_button_state()
    
    def refresh_vehicles_list(self):
        """Refresh the vehicles listbox for the current class"""
        self.vehicles_listbox.delete(0, tk.END)
        if self.current_class:
            for vehicle in self.manager.get_vehicles_for_class(self.current_class):
                self.vehicles_listbox.insert(tk.END, vehicle)
    
    def on_unassigned_selected(self, event=None):
        """Called when unassigned vehicles are selected - does NOT change class selection"""
        # Just update the button state - preserve self.current_class
        self.update_add_button_state()
    
    def update_add_button_state(self):
        """Enable add button only if a class is selected AND at least one unassigned vehicle is selected"""
        class_selected = (self.current_class is not None)
        unassigned_selected = bool(self.unassigned_listbox.curselection())
        
        if class_selected and unassigned_selected:
            self.add_to_class_btn.config(state=tk.NORMAL)
        else:
            self.add_to_class_btn.config(state=tk.DISABLED)
    
    def add_class(self):
        dialog = AddEditClassDialog(self)
        self.wait_window(dialog)
        
        if dialog.result:
            class_name, vehicles = dialog.result
            if self.manager.add_class(class_name, [class_name], vehicles):
                self.load_classes()
                messagebox.showinfo("Success", f"Added class: {class_name}")
            else:
                messagebox.showerror("Error", f"Class '{class_name}' already exists.")
    
    def rename_class(self):
        if not self.current_class:
            messagebox.showwarning("No Selection", "Please select a class to rename.")
            return
        
        dialog = tk.Toplevel(self)
        dialog.title("Rename Class")
        dialog.geometry("350x120")
        dialog.configure(bg='#2b2b2b')
        dialog.transient(self)
        dialog.grab_set()
        
        frame = tk.Frame(dialog, bg='#2b2b2b', padx=20, pady=20)
        frame.pack(fill=tk.BOTH, expand=True)
        
        tk.Label(frame, text="New class name:", bg='#2b2b2b', fg='white').pack(anchor=tk.W)
        entry = tk.Entry(frame, bg='#3c3c3c', fg='white', width=30)
        entry.insert(0, self.current_class)
        entry.pack(fill=tk.X, pady=5)
        entry.focus()
        
        def save():
            new_name = entry.get().strip()
            if new_name and new_name != self.current_class:
                if self.manager.rename_class(self.current_class, new_name):
                    self.load_classes()
                    # Find the renamed class in the list and select it
                    for i in range(self.class_listbox.size()):
                        if self.class_listbox.get(i) == new_name:
                            self.class_listbox.selection_clear(0, tk.END)
                            self.class_listbox.selection_set(i)
                            self.class_listbox.see(i)
                            self.current_class = new_name
                            self.selected_class_label.config(text=f"Class: {self.current_class}")
                            self.refresh_vehicles_list()
                            break
                    messagebox.showinfo("Success", f"Renamed to '{new_name}'")
                else:
                    messagebox.showerror("Error", f"Name '{new_name}' may already exist.")
            dialog.destroy()
        
        tk.Button(frame, text="Cancel", command=dialog.destroy,
                  bg='#555', fg='white').pack(side=tk.RIGHT, padx=5)
        tk.Button(frame, text="Save", command=save,
                  bg='#4CAF50', fg='white').pack(side=tk.RIGHT, padx=5)
        
        entry.bind('<Return>', lambda e: save())
    
    def delete_class(self):
        if not self.current_class:
            messagebox.showwarning("No Selection", "Please select a class to delete.")
            return
        
        result = messagebox.askyesno("Confirm Delete",
                                      f"Delete class '{self.current_class}' and all its vehicles?\nThis cannot be undone.")
        
        if result:
            deleted_class = self.current_class
            if self.manager.delete_class(deleted_class):
                self.load_classes()
                self.current_class = None
                self.selected_class_label.config(text="No class selected")
                self.vehicles_listbox.delete(0, tk.END)
                self.refresh_unassigned_list()
                messagebox.showinfo("Success", f"Deleted class: {deleted_class}")
    
    def add_vehicle(self):
        if not self.current_class:
            messagebox.showwarning("No Selection", "Please select a class first.")
            return
        
        dialog = tk.Toplevel(self)
        dialog.title("Add Vehicle")
        dialog.geometry("350x120")
        dialog.configure(bg='#2b2b2b')
        dialog.transient(self)
        dialog.grab_set()
        
        frame = tk.Frame(dialog, bg='#2b2b2b', padx=20, pady=20)
        frame.pack(fill=tk.BOTH, expand=True)
        
        tk.Label(frame, text=f"Vehicle name for class '{self.current_class}':",
                 bg='#2b2b2b', fg='white').pack(anchor=tk.W)
        entry = tk.Entry(frame, bg='#3c3c3c', fg='white', width=40)
        entry.pack(fill=tk.X, pady=5)
        entry.focus()
        
        def save():
            name = entry.get().strip()
            if name:
                if self.manager.add_vehicle(self.current_class, name):
                    self.refresh_vehicles_list()
                    self.refresh_unassigned_list()
                    messagebox.showinfo("Success", f"Added '{name}' to '{self.current_class}'")
                else:
                    messagebox.showerror("Error", "Failed to add vehicle.")
            dialog.destroy()
        
        tk.Button(frame, text="Cancel", command=dialog.destroy,
                  bg='#555', fg='white').pack(side=tk.RIGHT, padx=5)
        tk.Button(frame, text="Add", command=save,
                  bg='#4CAF50', fg='white').pack(side=tk.RIGHT, padx=5)
        
        entry.bind('<Return>', lambda e: save())
    
    def edit_vehicle(self):
        if not self.current_class:
            messagebox.showwarning("No Selection", "Please select a class.")
            return
        
        selection = self.vehicles_listbox.curselection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a vehicle to edit.")
            return
        
        old_name = self.vehicles_listbox.get(selection[0])
        
        dialog = tk.Toplevel(self)
        dialog.title("Edit Vehicle")
        dialog.geometry("350x120")
        dialog.configure(bg='#2b2b2b')
        dialog.transient(self)
        dialog.grab_set()
        
        frame = tk.Frame(dialog, bg='#2b2b2b', padx=20, pady=20)
        frame.pack(fill=tk.BOTH, expand=True)
        
        tk.Label(frame, text="New vehicle name:", bg='#2b2b2b', fg='white').pack(anchor=tk.W)
        entry = tk.Entry(frame, bg='#3c3c3c', fg='white', width=40)
        entry.insert(0, old_name)
        entry.pack(fill=tk.X, pady=5)
        entry.focus()
        
        def save():
            new_name = entry.get().strip()
            if new_name and new_name != old_name:
                if self.manager.update_vehicle(self.current_class, old_name, new_name):
                    self.refresh_vehicles_list()
                    self.refresh_unassigned_list()
                    messagebox.showinfo("Success", "Vehicle updated")
                else:
                    messagebox.showerror("Error", "Failed to update vehicle.")
            dialog.destroy()
        
        tk.Button(frame, text="Cancel", command=dialog.destroy,
                  bg='#555', fg='white').pack(side=tk.RIGHT, padx=5)
        tk.Button(frame, text="Save", command=save,
                  bg='#4CAF50', fg='white').pack(side=tk.RIGHT, padx=5)
        
        entry.bind('<Return>', lambda e: save())
    
    def remove_vehicles(self):
        if not self.current_class:
            messagebox.showwarning("No Selection", "Please select a class.")
            return
        
        selection = self.vehicles_listbox.curselection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select vehicles to remove.")
            return
        
        vehicle_names = [self.vehicles_listbox.get(idx) for idx in selection]
        
        result = messagebox.askyesno("Confirm Remove",
                                      f"Remove {len(vehicle_names)} vehicle(s) from '{self.current_class}'?\nThey will become unassigned.")
        
        if result:
            removed = self.manager.remove_vehicles_batch(self.current_class, vehicle_names)
            self.refresh_vehicles_list()
            self.refresh_unassigned_list()
            messagebox.showinfo("Success", f"Removed {removed} vehicle(s).")
    
    def select_gtr2_folder(self):
        folder = filedialog.askdirectory(title="Select GTR2 Installation Folder")
        if folder:
            self.gtr2_path = Path(folder)
            self.gtr2_path_label.config(text=str(self.gtr2_path), fg='#4CAF50')
            self.import_btn.config(state=tk.NORMAL)
            self.import_status.config(text="Ready to import. Click 'Import Cars'")
    
    def update_progress_on_main_thread(self, current, total, message):
        if total > 0:
            self.import_progress['maximum'] = total
            self.import_progress['value'] = current
        self.import_status.config(text=f"{message} ({current}/{total})")
    
    def import_cars(self):
        if not self.gtr2_path:
            messagebox.showwarning("No Folder", "Please select GTR2 installation folder first.")
            return
        
        teams_dir = self.gtr2_path / "GameData" / "Teams"
        if not teams_dir.exists():
            messagebox.showerror("Invalid Path", 
                                  f"Teams directory not found:\n{teams_dir}\n\nPlease select the correct GTR2 installation folder.")
            return
        
        self.import_btn.config(state=tk.DISABLED)
        self.import_progress.pack(fill=tk.X, pady=5)
        self.import_progress.start()
        self.import_status.config(text="Importing vehicles... Please wait.")
        
        def on_progress(current, total, message):
            self.after(0, lambda: self.update_progress_on_main_thread(current, total, message))
        
        def on_import_complete(vehicles, error):
            self.after(0, lambda: self._handle_import_complete(vehicles, error))
        
        worker = VehicleImportWorker(self.gtr2_path, on_import_complete, on_progress)
        worker.start()
    
    def _handle_import_complete(self, vehicles, error):
        self.import_progress.stop()
        self.import_progress.pack_forget()
        self.import_btn.config(state=tk.NORMAL)
        
        if error:
            self.import_status.config(text=f"Error: {error}")
            messagebox.showerror("Import Error", error)
        else:
            self.imported_vehicles = vehicles
            self.refresh_unassigned_list()
            self.import_status.config(text=f"Imported {len(vehicles)} vehicles")
            messagebox.showinfo("Import Complete",
                                  f"Found {len(vehicles)} unique vehicles.\n\n"
                                  f"Unassigned vehicles are shown in the right panel.\n"
                                  f"Select a class, then select vehicles and click 'Add Selected to Class'.")
    
    def refresh_unassigned_list(self):
        self.unassigned_listbox.delete(0, tk.END)
        
        if not hasattr(self, 'imported_vehicles') or not self.imported_vehicles:
            self.unassigned_listbox.insert(tk.END, "No vehicles imported yet. Click 'Import Cars' first.")
            self.update_add_button_state()
            return
        
        unassigned = self.manager.get_unassigned_vehicles(self.imported_vehicles)
        
        if unassigned:
            for vehicle in unassigned:
                self.unassigned_listbox.insert(tk.END, vehicle)
        else:
            self.unassigned_listbox.insert(tk.END, "All vehicles are assigned to classes!")
        
        self.update_add_button_state()
    
    def add_selected_to_class(self):
        if not self.current_class:
            messagebox.showwarning("No Class", "Please select a class first.")
            return
        
        selection = self.unassigned_listbox.curselection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select vehicles to add.")
            return
        
        vehicle_names = [self.unassigned_listbox.get(idx) for idx in selection]
        
        result = messagebox.askyesno("Confirm Assignment",
                                      f"Add {len(vehicle_names)} vehicle(s) to class '{self.current_class}'?")
        
        if result:
            added = self.manager.add_vehicles_batch(self.current_class, vehicle_names)
            if added > 0:
                self.refresh_unassigned_list()
                self.refresh_vehicles_list()
                messagebox.showinfo("Success", f"Added {added} vehicle(s) to '{self.current_class}'")
            else:
                messagebox.showerror("Error", "Failed to add vehicles.")
