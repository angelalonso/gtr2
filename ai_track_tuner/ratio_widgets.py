"""
Reusable widgets for the Ratio Calculator
Contains all custom widgets used in the GUI
"""

from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from ratio_calc import TimeConverter, LapTimes, CalculationDetails


class ModernTimeSpinBox(QWidget):
    """
    Modern time input widget with separate fields for minutes, seconds, milliseconds
    """
    
    timeChanged = pyqtSignal(float)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.total_seconds = 0.0
        self.setup_ui()
        self.setup_connections()
        
    def setup_ui(self):
        # Main layout
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(1)
        
        # Container for better visual grouping
        container = QWidget()
        container.setStyleSheet("""
            QWidget {
                background-color: #2b2b2b;
                border: 2px solid #4CAF50;
                border-radius: 6px;
            }
        """)
        container_layout = QHBoxLayout(container)
        container_layout.setContentsMargins(5, 2, 5, 2)
        container_layout.setSpacing(2)
        
        # Minutes field
        self.minutes_spin = self.create_spinbox(0, 99, 70)
        container_layout.addWidget(self.minutes_spin)
        
        minutes_label = QLabel("min")
        minutes_label.setStyleSheet("color: #888; font-size: 11px;")
        container_layout.addWidget(minutes_label)
        
        # Separator
        sep1 = QLabel(":")
        sep1.setStyleSheet("color: #4CAF50; font-size: 18px; font-weight: bold;")
        container_layout.addWidget(sep1)
        
        # Seconds field
        self.seconds_spin = self.create_spinbox(0, 59, 60)
        container_layout.addWidget(self.seconds_spin)
        
        seconds_label = QLabel("sec")
        seconds_label.setStyleSheet("color: #888; font-size: 11px;")
        container_layout.addWidget(seconds_label)
        
        # Separator
        sep2 = QLabel(".")
        sep2.setStyleSheet("color: #4CAF50; font-size: 18px; font-weight: bold;")
        container_layout.addWidget(sep2)
        
        # Milliseconds field
        self.milliseconds_spin = self.create_spinbox(0, 999, 70)
        self.milliseconds_spin.setSingleStep(10)
        container_layout.addWidget(self.milliseconds_spin)
        
        milliseconds_label = QLabel("ms")
        milliseconds_label.setStyleSheet("color: #888; font-size: 11px;")
        container_layout.addWidget(milliseconds_label)
        
        main_layout.addWidget(container)
        main_layout.addStretch()
    
    def create_spinbox(self, min_val, max_val, width):
        """Create a styled spinbox"""
        spin = QSpinBox()
        spin.setRange(min_val, max_val)
        spin.setValue(0)
        spin.setFixedHeight(36)
        spin.setFixedWidth(width)
        spin.setAlignment(Qt.AlignRight)
        spin.setStyleSheet("""
            QSpinBox {
                background-color: #3c3c3c;
                color: #ffffff;
                border: 1px solid #4CAF50;
                border-radius: 4px;
                padding: 4px;
                font-family: 'Segoe UI', 'Arial', sans-serif;
                font-size: 14px;
                font-weight: bold;
            }
            QSpinBox:hover {
                border: 2px solid #45a049;
            }
            QSpinBox:focus {
                border: 2px solid #9C27B0;
            }
            QSpinBox::up-button, QSpinBox::down-button {
                width: 16px;
                height: 12px;
            }
        """)
        return spin
    
    def setup_connections(self):
        """Setup signal connections"""
        self.minutes_spin.valueChanged.connect(self.update_total_seconds)
        self.seconds_spin.valueChanged.connect(self.update_total_seconds)
        self.milliseconds_spin.valueChanged.connect(self.update_total_seconds)
    
    def update_total_seconds(self):
        """Update total seconds and emit signal"""
        self.total_seconds = TimeConverter.mmssms_to_seconds(
            self.minutes_spin.value(),
            self.seconds_spin.value(),
            self.milliseconds_spin.value()
        )
        self.timeChanged.emit(self.total_seconds)
    
    def set_time_from_seconds(self, seconds):
        """Set the time from total seconds"""
        minutes, secs, ms = TimeConverter.seconds_to_mmssms(seconds)
        
        # Block signals to avoid recursion
        self.minutes_spin.blockSignals(True)
        self.seconds_spin.blockSignals(True)
        self.milliseconds_spin.blockSignals(True)
        
        self.minutes_spin.setValue(minutes)
        self.seconds_spin.setValue(secs)
        self.milliseconds_spin.setValue(ms)
        
        self.minutes_spin.blockSignals(False)
        self.seconds_spin.blockSignals(False)
        self.milliseconds_spin.blockSignals(False)
        
        self.total_seconds = seconds
        self.timeChanged.emit(seconds)
    
    def value(self):
        """Get value in total seconds"""
        return self.total_seconds
    
    def setValue(self, seconds):
        """Set value from total seconds"""
        self.set_time_from_seconds(seconds)
    
    def clear(self):
        """Clear the time"""
        self.set_time_from_seconds(0)


class ModernCard(QFrame):
    """Modern card-style container with shadow and rounded corners"""
    
    def __init__(self, title="", parent=None):
        super().__init__(parent)
        self.title = title
        self.content_layout = None
        self.setup_ui()
        
    def setup_ui(self):
        self.setFrameStyle(QFrame.NoFrame)
        self.setStyleSheet("""
            ModernCard {
                background-color: #1e1e1e;
                border: 1px solid #333;
                border-radius: 8px;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)
        
        if self.title:
            title_label = QLabel(self.title)
            title_label.setStyleSheet("""
                QLabel {
                    color: #4CAF50;
                    font-size: 14px;
                    font-weight: bold;
                    padding-bottom: 5px;
                    border-bottom: 2px solid #4CAF50;
                }
            """)
            layout.addWidget(title_label)
        
        self.content_layout = QVBoxLayout()
        layout.addLayout(self.content_layout)
    
    def addWidget(self, widget):
        """Add widget to the card content"""
        if self.content_layout:
            self.content_layout.addWidget(widget)
    
    def addLayout(self, layout):
        """Add layout to the card content"""
        if self.content_layout:
            self.content_layout.addLayout(layout)


class ModernLabel(QLabel):
    """Styled label with consistent theming"""
    
    def __init__(self, text="", color="#ffffff", bold=False, font_size=12):
        super().__init__(text)
        weight = "bold" if bold else "normal"
        self.setStyleSheet(f"""
            QLabel {{
                color: {color};
                font-family: 'Segoe UI', 'Arial', sans-serif;
                font-size: {font_size}px;
                font-weight: {weight};
                padding: 2px;
            }}
        """)


class ValueDisplay(QWidget):
    """Displays a labeled value with consistent styling"""
    
    def __init__(self, label_text="", value_text="---", color="#ffffff", parent=None):
        super().__init__(parent)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 2, 5, 2)
        layout.setSpacing(10)
        
        self.label = QLabel(label_text + ":")
        self.label.setStyleSheet("color: #888; font-size: 12px;")
        self.label.setFixedWidth(100)
        layout.addWidget(self.label)
        
        self.value = QLabel(value_text)
        self.value.setStyleSheet(f"color: {color}; font-size: 12px; font-weight: bold;")
        self.value.setAlignment(Qt.AlignRight)
        layout.addWidget(self.value)
        
        layout.addStretch()
    
    def setValue(self, text, color=None):
        """Set the value text and optionally color"""
        self.value.setText(text)
        if color:
            self.value.setStyleSheet(f"color: {color}; font-size: 12px; font-weight: bold;")


class CalculationDetailsCard(ModernCard):
    """Card for displaying calculation details"""
    
    def __init__(self, title=""):
        super().__init__(title)
        self.setup_details_ui()
        
    def setup_details_ui(self):
        # AI Times section
        ai_group = QGroupBox("AI Times")
        ai_group.setStyleSheet("""
            QGroupBox {
                color: #888;
                border: 1px solid #333;
                border-radius: 4px;
                margin-top: 5px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
        """)
        ai_layout = QGridLayout(ai_group)
        
        self.ai_best = ValueDisplay("Best", "---", "#4CAF50")
        ai_layout.addWidget(self.ai_best, 0, 0)
        
        self.ai_worst = ValueDisplay("Worst", "---", "#f44336")
        ai_layout.addWidget(self.ai_worst, 0, 1)
        
        self.ai_avg = ValueDisplay("Average", "---", "#FFA500")
        ai_layout.addWidget(self.ai_avg, 1, 0)
        
        self.ai_spread = ValueDisplay("Spread", "---", "#FFA500")
        ai_layout.addWidget(self.ai_spread, 1, 1)
        
        self.addWidget(ai_group)
        
        # Player section
        player_group = QGroupBox("Player")
        player_group.setStyleSheet("""
            QGroupBox {
                color: #888;
                border: 1px solid #333;
                border-radius: 4px;
                margin-top: 5px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
        """)
        player_layout = QGridLayout(player_group)
        
        self.player_time = ValueDisplay("Time", "---", "#9C27B0")
        player_layout.addWidget(self.player_time, 0, 0)
        
        self.time_diff = ValueDisplay("Difference", "---", "#ffffff")
        player_layout.addWidget(self.time_diff, 0, 1)
        
        self.addWidget(player_group)
        
        # Results section
        results_group = QGroupBox("Results")
        results_group.setStyleSheet("""
            QGroupBox {
                color: #888;
                border: 1px solid #333;
                border-radius: 4px;
                margin-top: 5px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
        """)
        results_layout = QGridLayout(results_group)
        
        self.percent_diff = ValueDisplay("% Difference", "---", "#ffffff")
        results_layout.addWidget(self.percent_diff, 0, 0)
        
        self.adjusted_percent = ValueDisplay("Adjusted %", "---", "#ffffff")
        results_layout.addWidget(self.adjusted_percent, 0, 1)
        
        self.final_ratio = ValueDisplay("Final Ratio", "---", "#9C27B0")
        results_layout.addWidget(self.final_ratio, 1, 0, 1, 2)
        
        self.addWidget(results_group)
    
    def update_details(self, times: LapTimes, details: CalculationDetails = None):
        """Update the display with calculation details"""
        if times.are_valid():
            # Update AI times
            self.ai_best.setValue(TimeConverter.format_time(times.pole))
            self.ai_worst.setValue(TimeConverter.format_time(times.last_ai))
            self.ai_avg.setValue(TimeConverter.format_time(times.avg_ai))
            self.ai_spread.setValue(f"{times.ai_spread:.3f}s")
            self.player_time.setValue(TimeConverter.format_time(times.player))
            
            if details:
                # Update time difference with color coding
                diff_color = "#4CAF50" if details.time_difference < 0 else "#f44336"
                self.time_diff.setValue(f"{details.time_difference:+.3f}s", diff_color)
                
                # Update percentage with color coding
                pct_color = "#4CAF50" if details.percent_difference < 0 else "#f44336"
                self.percent_diff.setValue(f"{details.percent_difference:+.2f}%", pct_color)
                
                # Update adjusted values
                self.adjusted_percent.setValue(f"{details.adjusted_percent:+.2f}%")
                self.final_ratio.setValue(f"{details.ratio:.6f}", "#9C27B0")
            else:
                self.time_diff.setValue("---")
                self.percent_diff.setValue("---")
                self.adjusted_percent.setValue("---")
                self.final_ratio.setValue("---")
        else:
            self.clear()
    
    def clear(self):
        """Clear all displays"""
        self.ai_best.setValue("---")
        self.ai_worst.setValue("---")
        self.ai_avg.setValue("---")
        self.ai_spread.setValue("---")
        self.player_time.setValue("---")
        self.time_diff.setValue("---")
        self.percent_diff.setValue("---")
        self.adjusted_percent.setValue("---")
        self.final_ratio.setValue("---")
