"""
Race Results Parser for rFactor 2/GTR2
Parses the raceresults.txt file and extracts race information
"""

import re
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import tkinter as tk
from tkinter import ttk

logger = logging.getLogger(__name__)


class RaceResultsParser:
    """Parse and analyze race results from raceresults.txt"""
    
    def __init__(self, file_path: Path):
        """
        Initialize the parser with the results file path
        
        Args:
            file_path: Path to raceresults.txt file
        """
        self.file_path = Path(file_path)
        self.track_name = None
        self.aiw_file = None
        self.drivers = []
        self.user_driver = None
        
    def parse(self) -> bool:
        """
        Parse the results file
        
        Returns:
            bool: True if parsing was successful, False otherwise
        """
        try:
            if not self.file_path.exists():
                logger.error(f"Results file not found: {self.file_path}")
                return False
            
            with open(self.file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # Parse track and AIW information
            self._parse_header(content)
            
            # Parse driver slots
            self._parse_drivers(content)
            
            # Identify user driver (Slot000 is typically the user)
            self._identify_user_driver()
            
            logger.info(f"Successfully parsed {len(self.drivers)} drivers from {self.file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error parsing results file: {e}")
            return False
    
    def _parse_header(self, content: str):
        """Parse the header section to get track and AIW information"""
        # Find the Race section
        race_match = re.search(r'\[Race\](.*?)\[', content, re.DOTALL)
        if race_match:
            race_section = race_match.group(1)
            
            # Extract Scene (track)
            scene_match = re.search(r'Scene=(.*?)(?:\n|$)', race_section)
            if scene_match:
                scene = scene_match.group(1).strip()
                # Extract track name from path (remove .TRK extension and path)
                track_name = Path(scene).stem
                # Clean up the track name
                if track_name:
                    # Remove numbers at the start if present (e.g., "4Monza" -> "Monza")
                    track_name = re.sub(r'^\d+', '', track_name)
                self.track_name = track_name
            
            # Extract AIW file
            aiw_match = re.search(r'AIDB=(.*?)(?:\n|$)', race_section)
            if aiw_match:
                aiw_path = aiw_match.group(1).strip()
                # Get just the filename without path
                self.aiw_file = Path(aiw_path).name
                # Case-insensitive .aiw extension check
                if not self.aiw_file.lower().endswith('.aiw'):
                    self.aiw_file += '.aiw'  # Add if missing
                else:
                    self.aiw_file = self.aiw_file
    
    def _parse_drivers(self, content: str):
        """Parse all driver slots from the content"""
        # Find all slot sections
        slot_pattern = r'\[Slot(\d+)\](.*?)(?=\[Slot|\[END\]|$)'
        slots = re.findall(slot_pattern, content, re.DOTALL)
        
        for slot_num, slot_content in slots:
            driver_data = {
                'slot': int(slot_num),
                'name': None,
                'vehicle': None,
                'vehicle_number': None,
                'team': None,
                'qual_time': None,
                'best_lap': None,
                'laps': None,
                'race_time': None
            }
            
            # Parse each field
            name_match = re.search(r'Driver=(.*?)(?:\n|$)', slot_content)
            if name_match:
                driver_data['name'] = name_match.group(1).strip()
            
            vehicle_match = re.search(r'Vehicle=(.*?)(?:\n|$)', slot_content)
            if vehicle_match:
                driver_data['vehicle'] = vehicle_match.group(1).strip()
            
            vehicle_num_match = re.search(r'VehicleNumber=(.*?)(?:\n|$)', slot_content)
            if vehicle_num_match:
                driver_data['vehicle_number'] = vehicle_num_match.group(1).strip()
            
            team_match = re.search(r'Team=(.*?)(?:\n|$)', slot_content)
            if team_match:
                driver_data['team'] = team_match.group(1).strip()
            
            qual_match = re.search(r'QualTime=(.*?)(?:\n|$)', slot_content)
            if qual_match:
                driver_data['qual_time'] = qual_match.group(1).strip()
            
            best_lap_match = re.search(r'BestLap=(.*?)(?:\n|$)', slot_content)
            if best_lap_match:
                driver_data['best_lap'] = best_lap_match.group(1).strip()
            
            laps_match = re.search(r'Laps=(.*?)(?:\n|$)', slot_content)
            if laps_match:
                driver_data['laps'] = laps_match.group(1).strip()
            
            race_time_match = re.search(r'RaceTime=(.*?)(?:\n|$)', slot_content)
            if race_time_match:
                driver_data['race_time'] = race_time_match.group(1).strip()
            
            self.drivers.append(driver_data)
    
    def _identify_user_driver(self):
        """Identify the user driver (typically Slot000)"""
        for driver in self.drivers:
            if driver['slot'] == 0:
                self.user_driver = driver
                break
    
    def _time_to_seconds(self, time_str: str) -> Optional[float]:
        """
        Convert a time string to seconds for comparison
        
        Args:
            time_str: Time string in format like "1:55.364" or "1:57.861"
        
        Returns:
            float: Time in seconds, or None if invalid
        """
        if not time_str:
            return None
        
        try:
            # Handle mm:ss.sss format
            if ':' in time_str:
                parts = time_str.split(':')
                minutes = int(parts[0])
                seconds = float(parts[1])
                return minutes * 60 + seconds
            else:
                # Handle just seconds
                return float(time_str)
        except (ValueError, IndexError):
            return None
    
    def get_ai_drivers(self) -> List[Dict]:
        """Get all AI drivers (all drivers except Slot000)"""
        return [d for d in self.drivers if d['slot'] != 0]
    
    def get_best_qualifying_ai(self) -> Tuple[Optional[Dict], Optional[str]]:
        """
        Get the best qualifying time among AI drivers
        
        Returns:
            Tuple of (driver_data, time_string) or (None, None) if no qualifying times
        """
        ai_drivers = self.get_ai_drivers()
        best_driver = None
        best_time = None
        best_time_seconds = float('inf')
        
        for driver in ai_drivers:
            if driver['qual_time']:
                time_seconds = self._time_to_seconds(driver['qual_time'])
                if time_seconds and time_seconds < best_time_seconds:
                    best_time_seconds = time_seconds
                    best_driver = driver
                    best_time = driver['qual_time']
        
        return best_driver, best_time
    
    def get_worst_qualifying_ai(self) -> Tuple[Optional[Dict], Optional[str]]:
        """
        Get the worst qualifying time among AI drivers
        
        Returns:
            Tuple of (driver_data, time_string) or (None, None) if no qualifying times
        """
        ai_drivers = self.get_ai_drivers()
        worst_driver = None
        worst_time = None
        worst_time_seconds = -float('inf')
        
        for driver in ai_drivers:
            if driver['qual_time']:
                time_seconds = self._time_to_seconds(driver['qual_time'])
                if time_seconds and time_seconds > worst_time_seconds:
                    worst_time_seconds = time_seconds
                    worst_driver = driver
                    worst_time = driver['qual_time']
        
        return worst_driver, worst_time
    
    def get_user_qualifying(self) -> Optional[str]:
        """Get user's qualifying time"""
        if self.user_driver and self.user_driver['qual_time']:
            return self.user_driver['qual_time']
        return None
    
    def get_best_race_lap_ai(self) -> Tuple[Optional[Dict], Optional[str]]:
        """
        Get the best race lap time among AI drivers
        
        Returns:
            Tuple of (driver_data, time_string) or (None, None) if no lap times
        """
        ai_drivers = self.get_ai_drivers()
        best_driver = None
        best_time = None
        best_time_seconds = float('inf')
        
        for driver in ai_drivers:
            if driver['best_lap']:
                time_seconds = self._time_to_seconds(driver['best_lap'])
                if time_seconds and time_seconds < best_time_seconds:
                    best_time_seconds = time_seconds
                    best_driver = driver
                    best_time = driver['best_lap']
        
        return best_driver, best_time
    
    def get_worst_race_lap_ai(self) -> Tuple[Optional[Dict], Optional[str]]:
        """
        Get the worst race lap time among AI drivers
        
        Returns:
            Tuple of (driver_data, time_string) or (None, None) if no lap times
        """
        ai_drivers = self.get_ai_drivers()
        worst_driver = None
        worst_time = None
        worst_time_seconds = -float('inf')
        
        for driver in ai_drivers:
            if driver['best_lap']:
                time_seconds = self._time_to_seconds(driver['best_lap'])
                if time_seconds and time_seconds > worst_time_seconds:
                    worst_time_seconds = time_seconds
                    worst_driver = driver
                    worst_time = driver['best_lap']
        
        return worst_driver, worst_time
    
    def get_best_user_lap(self) -> Optional[str]:
        """Get user's best race lap time"""
        if self.user_driver and self.user_driver['best_lap']:
            return self.user_driver['best_lap']
        return None
    
    def get_track_info(self) -> Tuple[Optional[str], Optional[str]]:
        """Get track name and AIW file being used"""
        return self.track_name, self.aiw_file


class RaceResultsPopup:
    """Popup window to display race results analysis"""
    
    def __init__(self, parser: RaceResultsParser):
        """
        Initialize the popup with parsed results
        
        Args:
            parser: RaceResultsParser instance with parsed data
        """
        self.parser = parser
        self.window = None
        
    def show(self):
        """Create and display the results popup window"""
        self.window = tk.Toplevel()
        self.window.title("Race Results Analysis")
        self.window.geometry("600x500")
        
        # Center the window on screen
        self.window.update_idletasks()
        width = self.window.winfo_width()
        height = self.window.winfo_height()
        x = (self.window.winfo_screenwidth() // 2) - (width // 2)
        y = (self.window.winfo_screenheight() // 2) - (height // 2)
        self.window.geometry(f'{width}x{height}+{x}+{y}')
        
        # Make window grab focus
        self.window.lift()
        self.window.focus_force()
        self.window.grab_set()
        
        # Configure window
        self.window.configure(bg='#f0f0f0')
        
        # Main frame
        main_frame = tk.Frame(self.window, bg='#f0f0f0')
        main_frame.pack(expand=True, fill='both', padx=20, pady=20)
        
        # Title
        title_label = tk.Label(
            main_frame,
            text="Race Results Analysis",
            font=('Arial', 14, 'bold'),
            bg='#f0f0f0',
            fg='#333'
        )
        title_label.pack(pady=(0, 10))
        
        # Track info
        track_name, aiw_file = self.parser.get_track_info()
        if track_name or aiw_file:
            track_frame = tk.Frame(main_frame, bg='#f0f0f0')
            track_frame.pack(fill='x', pady=(0, 15))
            
            if track_name:
                track_label = tk.Label(
                    track_frame,
                    text=f"Track: {track_name}",
                    font=('Arial', 10, 'bold'),
                    bg='#f0f0f0',
                    fg='#666'
                )
                track_label.pack()
            
            if aiw_file:
                aiw_label = tk.Label(
                    track_frame,
                    text=f"AIW: {aiw_file}",
                    font=('Arial', 9),
                    bg='#f0f0f0',
                    fg='#888'
                )
                aiw_label.pack()
        
        # Separator
        separator = ttk.Separator(main_frame, orient='horizontal')
        separator.pack(fill='x', pady=10)
        
        # Create notebook for tabs
        notebook = ttk.Notebook(main_frame)
        notebook.pack(fill='both', expand=True, pady=10)
        
        # Qualifying tab
        quali_frame = tk.Frame(notebook, bg='#f0f0f0')
        notebook.add(quali_frame, text="Qualifying")
        self._create_quali_tab(quali_frame)
        
        # Race tab
        race_frame = tk.Frame(notebook, bg='#f0f0f0')
        notebook.add(race_frame, text="Race Laps")
        self._create_race_tab(race_frame)
        
        # All drivers tab
        drivers_frame = tk.Frame(notebook, bg='#f0f0f0')
        notebook.add(drivers_frame, text="All Drivers")
        self._create_drivers_tab(drivers_frame)
        
        # Close button
        button_frame = tk.Frame(main_frame, bg='#f0f0f0')
        button_frame.pack(pady=(10, 0))
        
        close_button = ttk.Button(
            button_frame,
            text="Close",
            command=self.close,
            width=15
        )
        close_button.pack()
        
        # Bind keyboard shortcuts
        self.window.bind('<Return>', lambda e: self.close())
        self.window.bind('<Escape>', lambda e: self.close())
        
        # Ensure window is on top
        self.window.attributes('-topmost', True)
        
        # Handle window close
        self.window.protocol("WM_DELETE_WINDOW", self.close)
        
        # Wait for window
        self.window.wait_window()
    
    def _create_quali_tab(self, parent):
        """Create the qualifying tab content"""
        # Best AI Qualifying
        best_ai, best_time = self.parser.get_best_qualifying_ai()
        self._create_info_row(
            parent,
            "Best AI Qualifying:",
            f"{best_time if best_time else 'N/A'}",
            f"({best_ai['name'] if best_ai else 'No AI drivers'})" if best_ai else "",
            0
        )
        
        # Worst AI Qualifying
        worst_ai, worst_time = self.parser.get_worst_qualifying_ai()
        self._create_info_row(
            parent,
            "Worst AI Qualifying:",
            f"{worst_time if worst_time else 'N/A'}",
            f"({worst_ai['name'] if worst_ai else 'No AI drivers'})" if worst_ai else "",
            1
        )
        
        # User Qualifying
        user_quali = self.parser.get_user_qualifying()
        user_text = user_quali if user_quali else "None (No qualifying time)"
        self._create_info_row(
            parent,
            "User Qualifying:",
            user_text,
            "",
            2
        )
        
        # Add some spacing and note about qualifying
        note_frame = tk.Frame(parent, bg='#f0f0f0')
        note_frame.pack(fill='x', pady=(20, 0))
        
        note_label = tk.Label(
            note_frame,
            text="Note: Qualifying times are from the qualifying session.",
            font=('Arial', 8),
            bg='#f0f0f0',
            fg='#888'
        )
        note_label.pack()
    
    def _create_race_tab(self, parent):
        """Create the race laps tab content"""
        # Best AI Race Lap
        best_ai, best_time = self.parser.get_best_race_lap_ai()
        self._create_info_row(
            parent,
            "Best AI Race Lap:",
            f"{best_time if best_time else 'N/A'}",
            f"({best_ai['name'] if best_ai else 'No AI drivers'})" if best_ai else "",
            0
        )
        
        # Worst AI Race Lap
        worst_ai, worst_time = self.parser.get_worst_race_lap_ai()
        self._create_info_row(
            parent,
            "Worst AI Race Lap:",
            f"{worst_time if worst_time else 'N/A'}",
            f"({worst_ai['name'] if worst_ai else 'No AI drivers'})" if worst_ai else "",
            1
        )
        
        # Best User Lap
        user_best = self.parser.get_best_user_lap()
        user_text = user_best if user_best else "No lap times recorded"
        self._create_info_row(
            parent,
            "Best User Lap:",
            user_text,
            "",
            2
        )
        
        # Add some spacing and note
        note_frame = tk.Frame(parent, bg='#f0f0f0')
        note_frame.pack(fill='x', pady=(20, 0))
        
        note_label = tk.Label(
            note_frame,
            text="Note: Best lap times are the fastest lap achieved during the race.",
            font=('Arial', 8),
            bg='#f0f0f0',
            fg='#888'
        )
        note_label.pack()
    
    def _create_drivers_tab(self, parent):
        """Create the all drivers tab with a treeview"""
        # Create treeview frame
        tree_frame = tk.Frame(parent, bg='white')
        tree_frame.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Create scrollbars
        v_scrollbar = ttk.Scrollbar(tree_frame, orient='vertical')
        h_scrollbar = ttk.Scrollbar(tree_frame, orient='horizontal')
        
        # Create treeview
        columns = ('Slot', 'Name', 'Team', 'Qual Time', 'Best Lap', 'Laps')
        tree = ttk.Treeview(
            tree_frame,
            columns=columns,
            show='headings',
            height=15,
            yscrollcommand=v_scrollbar.set,
            xscrollcommand=h_scrollbar.set
        )
        
        # Configure scrollbars
        v_scrollbar.config(command=tree.yview)
        h_scrollbar.config(command=tree.xview)
        
        # Define column headings
        tree.heading('Slot', text='Slot')
        tree.heading('Name', text='Driver Name')
        tree.heading('Team', text='Team')
        tree.heading('Qual Time', text='Qualifying')
        tree.heading('Best Lap', text='Best Lap')
        tree.heading('Laps', text='Laps')
        
        # Define column widths
        tree.column('Slot', width=50, anchor='center')
        tree.column('Name', width=150)
        tree.column('Team', width=180)
        tree.column('Qual Time', width=80, anchor='center')
        tree.column('Best Lap', width=80, anchor='center')
        tree.column('Laps', width=60, anchor='center')
        
        # Pack tree and scrollbars
        tree.grid(row=0, column=0, sticky='nsew')
        v_scrollbar.grid(row=0, column=1, sticky='ns')
        h_scrollbar.grid(row=1, column=0, sticky='ew')
        
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)
        
        # Add data
        for driver in self.parser.drivers:
            # Highlight user (Slot000) with a tag
            tag = 'user' if driver['slot'] == 0 else 'ai'
            
            values = (
                driver['slot'],
                driver['name'],
                driver['team'],
                driver['qual_time'] if driver['qual_time'] else '-',
                driver['best_lap'] if driver['best_lap'] else '-',
                driver['laps'] if driver['laps'] else '-'
            )
            
            tree.insert('', 'end', values=values, tags=(tag,))
        
        # Configure tags for colors
        tree.tag_configure('user', background='#e6f3ff')
        tree.tag_configure('ai', background='white')
    
    def _create_info_row(self, parent, label_text, value_text, extra_text, row):
        """Create a row with label, value, and optional extra text"""
        frame = tk.Frame(parent, bg='#f0f0f0')
        frame.pack(fill='x', pady=8)
        
        # Label
        label = tk.Label(
            frame,
            text=label_text,
            font=('Arial', 10, 'bold'),
            bg='#f0f0f0',
            width=20,
            anchor='w'
        )
        label.pack(side='left', padx=(0, 10))
        
        # Value
        value_color = '#5cb85c' if 'Best' in label_text else '#d9534f' if 'Worst' in label_text else '#333'
        value = tk.Label(
            frame,
            text=value_text,
            font=('Arial', 10),
            bg='#f0f0f0',
            fg=value_color
        )
        value.pack(side='left')
        
        # Extra text (driver name, etc.)
        if extra_text:
            extra = tk.Label(
                frame,
                text=extra_text,
                font=('Arial', 9),
                bg='#f0f0f0',
                fg='#666'
            )
            extra.pack(side='left', padx=(5, 0))
    
    def close(self):
        """Close the popup window"""
        if self.window:
            self.window.grab_release()
            self.window.destroy()
            self.window = None


def analyze_race_results(file_path: Path) -> bool:
    """
    Main function to analyze race results and show popup
    
    Args:
        file_path: Path to the raceresults.txt file
    
    Returns:
        bool: True if analysis was successful, False otherwise
    """
    try:
        # Parse the results
        parser = RaceResultsParser(file_path)
        if not parser.parse():
            logger.error("Failed to parse race results")
            return False
        
        # Show the results popup
        popup = RaceResultsPopup(parser)
        popup.show()
        
        return True
        
    except Exception as e:
        logger.error(f"Error analyzing race results: {e}")
        return False
