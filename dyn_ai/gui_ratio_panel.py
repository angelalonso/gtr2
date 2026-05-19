#!/usr/bin/env python3
"""
Ratio panel component for Live AI Tuner - Tkinter version
Provides the Qualifying and Race ratio display panels
"""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional
import logging

from core_math import get_formula_string

logger = logging.getLogger(__name__)


class RatioPanel(tk.Frame):
    """Panel for displaying Qualifying or Race ratio information"""
    
    def __init__(self, parent, main_window, title: str, min_ratio: float, max_ratio: float):
        super().__init__(parent)
        self.title = title
        self.current_ratio = None
        self.last_read_ratio = None
        self.previous_ratio = None
        self.min_ratio = min_ratio
        self.max_ratio = max_ratio
        self.main_window = main_window
        self.setup_ui()
        logger.debug(f"RatioPanel created for {title} with main_window reference")
        
    def setup_ui(self):
        self.configure(bg='#2b2b2b')
        
        # Make panel scrollable for small screens
        canvas = tk.Canvas(self, bg='#2b2b2b', highlightthickness=0)
        scrollbar = tk.Scrollbar(self, orient=tk.VERTICAL, command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg='#2b2b2b')
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        main_frame = tk.Frame(scrollable_frame, bg='#2b2b2b')
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Title and buttons row
        title_frame = tk.Frame(main_frame, bg='#2b2b2b')
        title_frame.pack(fill=tk.X, pady=(0, 15))
        
        title_label = tk.Label(title_frame, text=self.title, bg='#2b2b2b', fg='#aaa',
                                font=('Arial', 16, 'bold'))
        title_label.pack(side=tk.LEFT)
        
        button_frame = tk.Frame(title_frame, bg='#2b2b2b')
        button_frame.pack(side=tk.RIGHT)
        
        self.revert_btn = tk.Button(button_frame, text="Revert", bg='#FF9800', fg='black',
                                     font=('Arial', 10, 'bold'), relief=tk.FLAT, padx=12, pady=4,
                                     state=tk.DISABLED, command=self.on_revert)
        self.revert_btn.pack(side=tk.LEFT, padx=5)
        
        self.edit_btn = tk.Button(button_frame, text="Edit", bg='#555', fg='black',
                                   font=('Arial', 10, 'bold'), relief=tk.FLAT, padx=12, pady=4,
                                   command=self.on_edit, state=tk.DISABLED)
        self.edit_btn.pack(side=tk.LEFT, padx=5)
        
        # Ratio display
        ratio_label = tk.Label(main_frame, text="Current Ratio:", bg='#2b2b2b', fg='#888',
                                font=('Arial', 11))
        ratio_label.pack()
        
        self.ratio_value = tk.Label(main_frame, text="-", bg='#2b2b2b', fg='#FFA500',
                                     font=('Courier', 38, 'bold'))
        self.ratio_value.pack(pady=5)
        
        self.last_read_value = tk.Label(main_frame, text="last ratio read: --", bg='#2b2b2b',
                                         fg='#666', font=('Courier', 10))
        self.last_read_value.pack()
        
        # AI range
        ai_label = tk.Label(main_frame, text="Expected Best Laptimes:", bg='#2b2b2b', fg='#888',
                             font=('Arial', 11))
        ai_label.pack(pady=(20, 5))
        
        self.ai_range = tk.Label(main_frame, text="AI: -- - --", bg='#2b2b2b', fg='#FFA500',
                                  font=('Courier', 14))
        self.ai_range.pack()
        
        # User time
        self.user_time = tk.Label(main_frame, text="User: --", bg='#2b2b2b', fg='#4CAF50',
                                   font=('Courier', 14, 'bold'))
        self.user_time.pack(pady=10)
        
        # Formula
        self.formula = tk.Label(main_frame, text="", bg='#2b2b2b', fg='#888',
                                 font=('Courier', 10))
        self.formula.pack(pady=10)
        
        # Accuracy indicator frame
        self.accuracy_frame = tk.Frame(main_frame, bg='#3c3c3c', relief=tk.FLAT, bd=0)
        self.accuracy_frame.pack(fill=tk.X, pady=10)
        self.accuracy_frame.pack_forget()
        
        self.accuracy_label = tk.Label(self.accuracy_frame, text="", bg='#3c3c3c', fg='#4CAF50',
                                        font=('Arial', 10))
        self.accuracy_label.pack(pady=5)
        
        self.progress_bar = ttk.Progressbar(self.accuracy_frame, length=150, mode='determinate')
        self.progress_bar.pack(pady=5)
    
    def get_current_ratio_value(self) -> Optional[float]:
        """Get the current ratio value from the panel or main window"""
        if self.current_ratio is not None:
            return self.current_ratio
        if self.last_read_ratio is not None:
            return self.last_read_ratio
        if self.main_window:
            if self.title == "Quali-Ratio":
                return self.main_window.last_qual_ratio
            else:
                return self.main_window.last_race_ratio
        return None
    
    def update_ratio(self, ratio: float):
        logger.debug(f"[RatioPanel.{self.title}] update_ratio called with ratio={ratio}")
        
        if ratio is not None:
            # Store previous ratio before updating
            if self.current_ratio is not None and ratio != self.current_ratio:
                self.previous_ratio = self.current_ratio
                self.revert_btn.config(state=tk.NORMAL)
                logger.debug(f"[RatioPanel.{self.title}] Stored previous_ratio={self.previous_ratio}")
            self.current_ratio = ratio
            self.ratio_value.config(text=f"{ratio:.6f}")
        else:
            self.current_ratio = None
            self.ratio_value.config(text="-")
    
    def update_last_read_ratio(self, ratio: float):
        self.last_read_ratio = ratio
        if ratio is not None:
            self.last_read_value.config(text=f"last ratio read: {ratio:.6f}", fg='#FFA500')
        else:
            self.last_read_value.config(text="last ratio read: --", fg='#666')
    
    def update_ai_range(self, best: float, worst: float):
        if best is not None and worst is not None:
            minutes_best = int(best) // 60
            secs_best = best % 60
            minutes_worst = int(worst) // 60
            secs_worst = worst % 60
            self.ai_range.config(text=f"AI: {minutes_best}:{secs_best:06.3f} - {minutes_worst}:{secs_worst:06.3f}")
        else:
            self.ai_range.config(text="AI: -- - --")
    
    def update_user_time(self, time_sec: float):
        if time_sec is not None and time_sec > 0:
            minutes = int(time_sec) // 60
            seconds = time_sec % 60
            self.user_time.config(text=f"User: {minutes}:{seconds:06.3f}")
        else:
            self.user_time.config(text="User: --")
    
    def update_formula(self, a: float, b: float):
        self.formula.config(text=get_formula_string(a, b))
    
    def update_accuracy(self, confidence: float, data_points_used: int,
                        avg_error: float = None, max_error: float = None,
                        outliers: int = 0):
        if data_points_used == 0:
            self.accuracy_frame.pack_forget()
            return
        
        self.accuracy_frame.pack(fill=tk.X, pady=10)
        
        if confidence >= 0.8:
            color = "#4CAF50"
            quality_text = "Excellent"
        elif confidence >= 0.6:
            color = "#FFC107"
            quality_text = "Good"
        elif confidence >= 0.4:
            color = "#FF9800"
            quality_text = "Fair"
        else:
            color = "#f44336"
            quality_text = "Poor"
        
        percent = int(confidence * 100)
        self.progress_bar['value'] = percent
        
        if avg_error is not None and avg_error > 0:
            self.accuracy_label.config(
                text=f"Data Quality: {quality_text} ({percent}%) - {data_points_used} points, avg error: {avg_error:.2f}s",
                fg=color
            )
        else:
            self.accuracy_label.config(
                text=f"Data Quality: {quality_text} ({percent}%) - {data_points_used} points",
                fg=color
            )
    
    def set_edit_enabled(self, enabled: bool):
        state = tk.NORMAL if enabled else tk.DISABLED
        self.edit_btn.config(state=state, bg=f"{'#84C7FC' if enabled else '#555'}")
    
    def on_edit(self):
        logger.debug(f"[RatioPanel.{self.title}] on_edit called")
        
        # Get the current ratio value to edit
        edit_value = self.get_current_ratio_value()
        
        if edit_value is None:
            edit_value = 1.000
        
        logger.debug(f"[RatioPanel.{self.title}] Using edit_value={edit_value}")
        
        # Create edit dialog
        dialog = tk.Toplevel(self)
        dialog.title(f"Edit {self.title}")
        dialog.geometry("400x300")
        dialog.configure(bg='#2b2b2b')
        dialog.transient(self)
        dialog.grab_set()
        
        frame = tk.Frame(dialog, bg='#2b2b2b', padx=20, pady=20)
        frame.pack(fill=tk.BOTH, expand=True)
        
        tk.Label(frame, text=f"Current {self.title}:", bg='#2b2b2b', fg='#888').pack()
        current_value_label = tk.Label(frame, text=f"{edit_value:.6f}", bg='#2b2b2b', fg='#4CAF50',
                                        font=('Courier', 14))
        current_value_label.pack(pady=5)
        
        tk.Label(frame, text=f"New {self.title} (min: {self.min_ratio}, max: {self.max_ratio}):",
                 bg='#2b2b2b', fg='#888').pack(pady=(15, 5))
        
        # Use a StringVar so the spinbox always shows exactly what we set.
        spinbox = tk.Spinbox(frame, from_=self.min_ratio, to=self.max_ratio, increment=0.01,
                              width=15, font=('Courier', 12),
                              bg='#3c3c3c', fg='white')
        spinbox.pack()
        
        # Explicitly set the initial value
        spinbox.delete(0, tk.END)
        spinbox.insert(0, f"{edit_value:.6f}")
        
        # Preview label
        preview_var = tk.StringVar(value=f"Will write: {edit_value:.6f}")
        preview_label = tk.Label(frame, textvariable=preview_var, bg='#2b2b2b', fg='#888', font=('Arial', 9))
        preview_label.pack(pady=10)
        
        def on_spin_change(*args):
            try:
                val = float(spinbox.get())
                preview_var.set(f"Will write: {val:.6f}")
            except ValueError:
                pass
        
        spinbox.bind('<KeyRelease>', on_spin_change)
        spinbox.bind('<<Increment>>', on_spin_change)
        spinbox.bind('<<Decrement>>', on_spin_change)
        
        button_frame = tk.Frame(frame, bg='#2b2b2b')
        button_frame.pack(pady=20)
        
        def apply():
            try:
                new_ratio = float(spinbox.get())
            except ValueError:
                messagebox.showwarning("Invalid Value",
                    "Please enter a valid number.")
                return
            logger.debug(f"[RatioPanel.{self.title}] Apply clicked, new_ratio={new_ratio}")
            dialog.destroy()
            if self.main_window and hasattr(self.main_window, 'on_manual_edit'):
                session = "qual" if self.title == "Quali-Ratio" else "race"
                self.main_window.on_manual_edit(session, new_ratio)
            else:
                logger.error(f"[RatioPanel.{self.title}] main_window or on_manual_edit not available")
        
        tk.Button(button_frame, text="Cancel", command=dialog.destroy,
                  bg='#555', fg='white', padx=15, pady=5).pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="Apply", command=apply,
                  bg='#4CAF50', fg='white', padx=15, pady=5).pack(side=tk.LEFT, padx=5)
        
        # Bind Enter key to apply
        spinbox.bind('<Return>', lambda e: apply())
        dialog.bind('<Return>', lambda e: apply())
    
    def on_revert(self):
        logger.debug(f"[RatioPanel.{self.title}] on_revert called, previous_ratio={self.previous_ratio}")
        
        if self.previous_ratio is not None:
            if self.main_window and hasattr(self.main_window, 'on_revert_ratio'):
                session = "qual" if self.title == "Quali-Ratio" else "race"
                self.main_window.on_revert_ratio(session)
        else:
            messagebox.showwarning("Cannot Revert", "No previous ratio value available to revert to.")
    
    def revert_success(self):
        self.previous_ratio = None
        self.revert_btn.config(state=tk.DISABLED)
