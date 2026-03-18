"""
Ratio Calculator GUI for AIW Ratio Editor - USER-FOCUSED DESIGN
Shows only essential information upfront, extra info in pop-up windows
"""

from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
import cfg_manage
import os
import numpy as np
from ratio_calc import (
    LapTimes, RatioConfig, RatioCalculator, 
    HistoricCSVHandler, CalculatedRatios, TimeConverter,
    AdjustableExponentialModel, PredictedTimes
)

class GraphWidget(QWidget):
    """Custom widget for drawing the formula graph"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(350)  # Increased for better label visibility
        self.setStyleSheet("""
            background-color: #1e1e1e;
            border: 2px solid #555;
            border-radius: 5px;
        """)
        
        # Data for plotting
        self.calculator = None
        self.config = None
        self.track_name = ""
        self.current_ratio = 1.0
        self.times = None
        self.new_ratio = None
        self.predicted_times = None
        self.track_params = None
    
    def set_data(self, calculator, config, track_name, current_ratio, times, new_ratio=None, predicted_times=None):
        """Set the data for plotting"""
        self.calculator = calculator
        self.config = config
        self.track_name = track_name
        self.current_ratio = current_ratio
        self.times = times
        self.new_ratio = new_ratio
        self.predicted_times = predicted_times
        self.track_params = calculator.track_db.get_parameters(track_name) if calculator else None
        self.update()  # Trigger repaint
    
    def paintEvent(self, event):
        """Custom paint event to draw the graph"""
        if not self.calculator or not self.config or not self.times:
            return
        
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Get widget dimensions
        rect = self.rect()
        margin = 70  # Increased margin for labels
        graph_width = rect.width() - 2 * margin
        graph_height = rect.height() - 2 * margin
        
        if graph_width <= 0 or graph_height <= 0:
            painter.end()
            return
        
        # Draw background
        painter.fillRect(rect, QColor(30, 30, 30))
        
        # Calculate ratio range
        min_ratio = self.config.exponential_min_ratio
        max_ratio = self.config.exponential_max_ratio
        
        # Calculate time range
        ratio_points = np.linspace(min_ratio, max_ratio, 100)
        time_points = []
        
        for r in ratio_points:
            try:
                t = self.calculator.exponential_model.time_from_ratio(r, self.track_params)
                time_points.append(t)
            except:
                time_points.append(0)
        
        if not time_points:
            painter.end()
            return
        
        valid_times = [t for t in time_points if t > 0]
        if not valid_times:
            painter.end()
            return
        
        min_time = min(valid_times) * 0.95
        max_time = max(valid_times) * 1.05
        
        # Draw grid
        painter.setPen(QPen(QColor(60, 60, 60), 1, Qt.DotLine))
        
        # Horizontal grid lines (time) with labels
        for i in range(6):
            y = margin + int(i * graph_height / 5)
            painter.drawLine(margin, y, margin + graph_width, y)
            
            # Time labels on left
            time_value = max_time - (i / 5) * (max_time - min_time)
            painter.setPen(QPen(QColor(150, 150, 150), 1))
            painter.drawText(margin - 55, y + 5, f"{time_value:.1f}s")
        
        # Vertical grid lines (ratio) with labels
        for i in range(6):
            x = margin + int(i * graph_width / 5)
            painter.drawLine(x, margin, x, margin + graph_height)
            
            # Ratio labels at bottom
            ratio_value = min_ratio + (i / 5) * (max_ratio - min_ratio)
            painter.setPen(QPen(QColor(150, 150, 150), 1))
            painter.drawText(x - 15, margin + graph_height + 20, f"{ratio_value:.1f}")
        
        # Draw axes
        painter.setPen(QPen(QColor(200, 200, 200), 2))
        painter.drawLine(margin, margin, margin, margin + graph_height)  # Y axis
        painter.drawLine(margin, margin + graph_height, margin + graph_width, margin + graph_height)  # X axis
        
        # Axis titles
        painter.setPen(QPen(QColor(255, 255, 255), 1))
        painter.drawText(margin - 65, margin - 15, "Time (s)")
        painter.drawText(margin + graph_width - 40, margin + graph_height + 35, "Ratio")
        
        # Draw the curve
        painter.setPen(QPen(QColor(76, 175, 80), 3))  # Green
        
        first_point = True
        last_x, last_y = 0, 0
        
        for r, t in zip(ratio_points, time_points):
            if t <= 0:
                continue
            
            # Map to pixel coordinates
            x = margin + int(((r - min_ratio) / (max_ratio - min_ratio)) * graph_width)
            y = margin + graph_height - int(((t - min_time) / (max_time - min_time)) * graph_height)
            
            if first_point:
                first_point = False
            else:
                painter.drawLine(last_x, last_y, x, y)
            
            last_x, last_y = x, y
        
        # Mark current ratio point
        if self.current_ratio:
            try:
                current_time = self.calculator.exponential_model.time_from_ratio(self.current_ratio, self.track_params)
                
                x = margin + int(((self.current_ratio - min_ratio) / (max_ratio - min_ratio)) * graph_width)
                y = margin + graph_height - int(((current_time - min_time) / (max_time - min_time)) * graph_height)
                
                # Draw circle
                painter.setBrush(QColor(255, 255, 255))
                painter.setPen(QPen(QColor(255, 255, 255), 2))
                painter.drawEllipse(x - 5, y - 5, 10, 10)
                
                # Add label with coordinates
                painter.setPen(QPen(QColor(255, 255, 255), 1))
                painter.drawText(x + 10, y - 10, f"Current\nR={self.current_ratio:.2f}\nT={current_time:.1f}s")
            except:
                pass
        
        # Mark user time (horizontal line)
        if self.times and self.times.player > 0:
            user_y = margin + graph_height - int(((self.times.player - min_time) / (max_time - min_time)) * graph_height)
            
            painter.setPen(QPen(QColor(156, 39, 176), 2, Qt.DashLine))  # Purple
            painter.drawLine(margin, user_y, margin + graph_width, user_y)
            
            painter.drawText(margin + 10, user_y - 5, f"User: {self.times.player:.3f}s")
        
        # Mark AI best/worst
        if self.times and self.times.pole > 0:
            best_y = margin + graph_height - int(((self.times.pole - min_time) / (max_time - min_time)) * graph_height)
            painter.setPen(QPen(QColor(76, 175, 80), 2, Qt.DashLine))  # Green
            painter.drawLine(margin, best_y, margin + graph_width, best_y)
            painter.drawText(margin + 10, best_y - 20, f"AI Best: {self.times.pole:.3f}s")
        
        if self.times and self.times.last_ai > 0:
            worst_y = margin + graph_height - int(((self.times.last_ai - min_time) / (max_time - min_time)) * graph_height)
            painter.setPen(QPen(QColor(244, 67, 54), 2, Qt.DashLine))  # Red
            painter.drawLine(margin, worst_y, margin + graph_width, worst_y)
            painter.drawText(margin + 10, worst_y - 35, f"AI Worst: {self.times.last_ai:.3f}s")
        
        # Mark target position
        if self.times and self.times.player > 0 and self.times.ai_spread > 0:
            target_position = self.config.goal_percent + self.config.goal_offset
            target_time = self.times.pole + (target_position / 100) * self.times.ai_spread
            
            target_y = margin + graph_height - int(((target_time - min_time) / (max_time - min_time)) * graph_height)
            painter.setPen(QPen(QColor(255, 165, 0), 2, Qt.DashLine))  # Orange
            painter.drawLine(margin, target_y, margin + graph_width, target_y)
            painter.drawText(margin + 10, target_y - 50, f"Target: {target_position:.1f}%")
        
        # Mark predicted times at new ratio
        if self.predicted_times:
            if self.predicted_times.best > 0:
                pred_best_y = margin + graph_height - int(((self.predicted_times.best - min_time) / (max_time - min_time)) * graph_height)
                painter.setPen(QPen(QColor(76, 175, 80), 2, Qt.DotLine))  # Green dotted
                painter.drawLine(margin, pred_best_y, margin + graph_width, pred_best_y)
                painter.drawText(margin + graph_width - 150, pred_best_y - 5, f"Pred Best: {self.predicted_times.best:.3f}s")
            
            if self.predicted_times.worst > 0:
                pred_worst_y = margin + graph_height - int(((self.predicted_times.worst - min_time) / (max_time - min_time)) * graph_height)
                painter.setPen(QPen(QColor(244, 67, 54), 2, Qt.DotLine))  # Red dotted
                painter.drawLine(margin, pred_worst_y, margin + graph_width, pred_worst_y)
                painter.drawText(margin + graph_width - 150, pred_worst_y - 20, f"Pred Worst: {self.predicted_times.worst:.3f}s")
            
            # Mark new ratio point
            if self.new_ratio:
                try:
                    new_time = self.calculator.exponential_model.time_from_ratio(self.new_ratio, self.track_params)
                    x = margin + int(((self.new_ratio - min_ratio) / (max_ratio - min_ratio)) * graph_width)
                    y = margin + graph_height - int(((new_time - min_time) / (max_time - min_time)) * graph_height)
                    
                    # Draw diamond
                    painter.setBrush(QColor(255, 165, 0))
                    painter.setPen(QPen(QColor(255, 165, 0), 2))
                    
                    points = [
                        QPoint(x, y - 6),
                        QPoint(x + 6, y),
                        QPoint(x, y + 6),
                        QPoint(x - 6, y)
                    ]
                    painter.drawPolygon(QPolygon(points))
                    
                    # Add label with coordinates
                    painter.setPen(QPen(QColor(255, 165, 0), 1))
                    painter.drawText(x + 10, y - 10, f"New\nR={self.new_ratio:.2f}\nT={new_time:.1f}s")
                except:
                    pass
        
        painter.end()


class PredictedTimesWindow(QDialog):
    """Pop-up window showing predicted AI times"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Predicted AI Times at New Ratio")
        self.setMinimumWidth(500)
        self.setMinimumHeight(400)
        
        # Set dark theme
        self.setStyleSheet("""
            QDialog {
                background-color: #2b2b2b;
            }
            QLabel {
                color: white;
                font-size: 12px;
            }
            QGroupBox {
                color: #4CAF50;
                font-weight: bold;
                border: 2px solid #555;
                border-radius: 5px;
                margin-top: 8px;
                padding-top: 8px;
                font-size: 13px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Qualifying predictions
        self.qual_group = QGroupBox("Qualifying - Predicted AI Times")
        qual_layout = QGridLayout(self.qual_group)
        qual_layout.setVerticalSpacing(15)
        qual_layout.setHorizontalSpacing(30)
        
        qual_layout.addWidget(QLabel("Best AI:"), 0, 0)
        self.qual_pred_best = QLabel("---")
        self.qual_pred_best.setStyleSheet("color: #4CAF50; font-size: 14px; font-weight: bold;")
        qual_layout.addWidget(self.qual_pred_best, 0, 1)
        
        qual_layout.addWidget(QLabel("Worst AI:"), 1, 0)
        self.qual_pred_worst = QLabel("---")
        self.qual_pred_worst.setStyleSheet("color: #f44336; font-size: 14px; font-weight: bold;")
        qual_layout.addWidget(self.qual_pred_worst, 1, 1)
        
        qual_layout.addWidget(QLabel("Median AI:"), 2, 0)
        self.qual_pred_median = QLabel("---")
        self.qual_pred_median.setStyleSheet("color: #FFA500; font-size: 14px; font-weight: bold;")
        qual_layout.addWidget(self.qual_pred_median, 2, 1)
        
        qual_layout.addWidget(QLabel("Spread:"), 3, 0)
        self.qual_pred_spread = QLabel("---")
        self.qual_pred_spread.setStyleSheet("color: #888; font-size: 14px; font-weight: bold;")
        qual_layout.addWidget(self.qual_pred_spread, 3, 1)
        
        layout.addWidget(self.qual_group)
        
        # Race predictions
        self.race_group = QGroupBox("Race - Predicted AI Times")
        race_layout = QGridLayout(self.race_group)
        race_layout.setVerticalSpacing(15)
        race_layout.setHorizontalSpacing(30)
        
        race_layout.addWidget(QLabel("Best AI:"), 0, 0)
        self.race_pred_best = QLabel("---")
        self.race_pred_best.setStyleSheet("color: #4CAF50; font-size: 14px; font-weight: bold;")
        race_layout.addWidget(self.race_pred_best, 0, 1)
        
        race_layout.addWidget(QLabel("Worst AI:"), 1, 0)
        self.race_pred_worst = QLabel("---")
        self.race_pred_worst.setStyleSheet("color: #f44336; font-size: 14px; font-weight: bold;")
        race_layout.addWidget(self.race_pred_worst, 1, 1)
        
        race_layout.addWidget(QLabel("Median AI:"), 2, 0)
        self.race_pred_median = QLabel("---")
        self.race_pred_median.setStyleSheet("color: #FFA500; font-size: 14px; font-weight: bold;")
        race_layout.addWidget(self.race_pred_median, 2, 1)
        
        race_layout.addWidget(QLabel("Spread:"), 3, 0)
        self.race_pred_spread = QLabel("---")
        self.race_pred_spread.setStyleSheet("color: #888; font-size: 14px; font-weight: bold;")
        race_layout.addWidget(self.race_pred_spread, 3, 1)
        
        layout.addWidget(self.race_group)
        
        # Close button
        close_btn = QPushButton("Close")
        close_btn.setFixedHeight(40)
        close_btn.setFixedWidth(200)
        close_btn.clicked.connect(self.accept)
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 3px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_layout.addWidget(close_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
    
    def update_times(self, qual_pred, race_pred):
        """Update the displayed times"""
        if qual_pred:
            self.qual_pred_best.setText(f"{qual_pred.best:.3f}s")
            self.qual_pred_worst.setText(f"{qual_pred.worst:.3f}s")
            self.qual_pred_median.setText(f"{qual_pred.median:.3f}s")
            self.qual_pred_spread.setText(f"{qual_pred.spread:.3f}s")
            self.qual_group.setVisible(True)
        else:
            self.qual_group.setVisible(False)
        
        if race_pred:
            self.race_pred_best.setText(f"{race_pred.best:.3f}s")
            self.race_pred_worst.setText(f"{race_pred.worst:.3f}s")
            self.race_pred_median.setText(f"{race_pred.median:.3f}s")
            self.race_pred_spread.setText(f"{race_pred.spread:.3f}s")
            self.race_group.setVisible(True)
        else:
            self.race_group.setVisible(False)


class FormulaDetailsWindow(QDialog):
    """Pop-up window showing formula and calculation details with live graph"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Formula & Calculation Details")
        self.setMinimumWidth(900)
        self.setMinimumHeight(800)
        
        # Store references for graph updates
        self.calculator = None
        self.config = None
        self.track_name = ""
        self.current_ratio = 1.0
        self.times = None
        self.last_results = None
        
        # Set dark theme
        self.setStyleSheet("""
            QDialog {
                background-color: #2b2b2b;
            }
            QLabel {
                color: white;
                font-size: 12px;
            }
            QGroupBox {
                color: #4CAF50;
                font-weight: bold;
                border: 2px solid #555;
                border-radius: 5px;
                margin-top: 8px;
                padding-top: 8px;
                font-size: 13px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
            QSpinBox, QDoubleSpinBox, QComboBox, QLineEdit {
                background-color: #3c3c3c;
                color: white;
                border: 1px solid #4CAF50;
                border-radius: 3px;
                padding: 5px;
                font-size: 12px;
                min-height: 25px;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Graph area
        graph_group = QGroupBox("Formula Visualization")
        graph_layout = QVBoxLayout(graph_group)
        
        self.graph_widget = GraphWidget()
        self.graph_widget.setMinimumHeight(300)
        graph_layout.addWidget(self.graph_widget)
        
        layout.addWidget(graph_group)
        
        # Method selection
        method_group = QGroupBox("Calculation Method")
        method_layout = QHBoxLayout(method_group)
        
        method_layout.addWidget(QLabel("Method:"))
        self.method_combo = QComboBox()
        self.method_combo.addItem("Linear (% ratio based)", False)
        self.method_combo.addItem("Exponential (track history based)", True)
        self.method_combo.setMinimumWidth(250)
        self.method_combo.currentIndexChanged.connect(self.on_method_changed)
        method_layout.addWidget(self.method_combo)
        method_layout.addStretch()
        
        layout.addWidget(method_group)
        
        # Linear parameters
        self.linear_group = QGroupBox("Linear Method Parameters")
        linear_layout = QGridLayout(self.linear_group)
        linear_layout.setVerticalSpacing(10)
        linear_layout.setHorizontalSpacing(15)
        
        linear_layout.addWidget(QLabel("Goal Percentage:"), 0, 0)
        self.goal_percent = QDoubleSpinBox()
        self.goal_percent.setRange(0, 100)
        self.goal_percent.setDecimals(1)
        self.goal_percent.setSingleStep(1)
        self.goal_percent.setSuffix("%")
        self.goal_percent.setMinimumWidth(120)
        self.goal_percent.valueChanged.connect(self.on_param_changed)
        linear_layout.addWidget(self.goal_percent, 0, 1)
        
        linear_layout.addWidget(QLabel("Goal Offset:"), 0, 2)
        self.goal_offset = QDoubleSpinBox()
        self.goal_offset.setRange(-100, 100)
        self.goal_offset.setDecimals(2)
        self.goal_offset.setSingleStep(0.1)
        self.goal_offset.setMinimumWidth(120)
        self.goal_offset.valueChanged.connect(self.on_param_changed)
        linear_layout.addWidget(self.goal_offset, 0, 3)
        
        linear_layout.addWidget(QLabel("Percent Ratio:"), 1, 0)
        self.percent_ratio = QDoubleSpinBox()
        self.percent_ratio.setRange(0.001, 1.0)
        self.percent_ratio.setDecimals(3)
        self.percent_ratio.setSingleStep(0.01)
        self.percent_ratio.setMinimumWidth(120)
        self.percent_ratio.valueChanged.connect(self.on_param_changed)
        linear_layout.addWidget(self.percent_ratio, 1, 1)
        
        linear_layout.addWidget(QLabel("Formula:"), 2, 0)
        self.linear_formula = QLabel("R = Current_Ratio + (Target% - Current_Position%) × Percent_Ratio")
        self.linear_formula.setWordWrap(True)
        self.linear_formula.setStyleSheet("""
            color: #4CAF50;
            font-family: 'Courier New', monospace;
            background-color: #1e1e1e;
            padding: 10px;
            border-radius: 3px;
        """)
        linear_layout.addWidget(self.linear_formula, 2, 1, 1, 3)
        
        layout.addWidget(self.linear_group)
        
        # Exponential parameters
        self.exponential_group = QGroupBox("Exponential Method Parameters")
        exp_layout = QGridLayout(self.exponential_group)
        exp_layout.setVerticalSpacing(10)
        exp_layout.setHorizontalSpacing(15)
        
        exp_layout.addWidget(QLabel("A (Time Range):"), 0, 0)
        self.exp_a = QDoubleSpinBox()
        self.exp_a.setRange(10, 1000)
        self.exp_a.setDecimals(1)
        self.exp_a.setSingleStep(10)
        self.exp_a.setSuffix(" s")
        self.exp_a.valueChanged.connect(self.on_param_changed)
        exp_layout.addWidget(self.exp_a, 0, 1)
        
        exp_layout.addWidget(QLabel("k (Decay Rate):"), 0, 2)
        self.exp_k = QDoubleSpinBox()
        self.exp_k.setRange(0.1, 10)
        self.exp_k.setDecimals(3)
        self.exp_k.setSingleStep(0.1)
        self.exp_k.valueChanged.connect(self.on_param_changed)
        exp_layout.addWidget(self.exp_k, 0, 3)
        
        exp_layout.addWidget(QLabel("B (Fastest Time):"), 1, 0)
        self.exp_b = QDoubleSpinBox()
        self.exp_b.setRange(30, 500)
        self.exp_b.setDecimals(1)
        self.exp_b.setSingleStep(5)
        self.exp_b.setSuffix(" s")
        self.exp_b.valueChanged.connect(self.on_param_changed)
        exp_layout.addWidget(self.exp_b, 1, 1)
        
        exp_layout.addWidget(QLabel("p (Power Factor):"), 1, 2)
        self.exp_p = QDoubleSpinBox()
        self.exp_p.setRange(0.1, 5)
        self.exp_p.setDecimals(2)
        self.exp_p.setSingleStep(0.1)
        self.exp_p.valueChanged.connect(self.on_param_changed)
        exp_layout.addWidget(self.exp_p, 1, 3)
        
        exp_layout.addWidget(QLabel("R₀ (Ratio Offset):"), 2, 0)
        self.exp_r0 = QDoubleSpinBox()
        self.exp_r0.setRange(-5, 5)
        self.exp_r0.setDecimals(2)
        self.exp_r0.setSingleStep(0.1)
        self.exp_r0.valueChanged.connect(self.on_param_changed)
        exp_layout.addWidget(self.exp_r0, 2, 1)
        
        exp_layout.addWidget(QLabel("Min Ratio:"), 2, 2)
        self.exp_min = QDoubleSpinBox()
        self.exp_min.setRange(0.01, 1)
        self.exp_min.setDecimals(2)
        self.exp_min.setSingleStep(0.05)
        self.exp_min.valueChanged.connect(self.on_param_changed)
        exp_layout.addWidget(self.exp_min, 2, 3)
        
        exp_layout.addWidget(QLabel("Max Ratio:"), 3, 0)
        self.exp_max = QDoubleSpinBox()
        self.exp_max.setRange(1, 20)
        self.exp_max.setDecimals(2)
        self.exp_max.setSingleStep(0.5)
        self.exp_max.valueChanged.connect(self.on_param_changed)
        exp_layout.addWidget(self.exp_max, 3, 1)
        
        exp_layout.addWidget(QLabel("Formula:"), 4, 0)
        self.exp_formula = QLabel()
        self.exp_formula.setWordWrap(True)
        self.exp_formula.setStyleSheet("""
            color: #4CAF50;
            font-family: 'Courier New', monospace;
            background-color: #1e1e1e;
            padding: 10px;
            border-radius: 3px;
        """)
        exp_layout.addWidget(self.exp_formula, 4, 1, 1, 3)
        
        layout.addWidget(self.exponential_group)
        
        # Edit parameters button
        self.edit_params_btn = QPushButton("✎ Advanced Exponential Parameters")
        self.edit_params_btn.setFixedHeight(35)
        self.edit_params_btn.setStyleSheet("background-color: #FFA500; color: black; font-weight: bold;")
        layout.addWidget(self.edit_params_btn)
        
        # Close button
        close_btn = QPushButton("Close")
        close_btn.setFixedHeight(40)
        close_btn.setFixedWidth(200)
        close_btn.clicked.connect(self.accept)
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 3px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_layout.addWidget(close_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
    
    def on_method_changed(self):
        """Handle method change"""
        use_exponential = (self.method_combo.currentIndex() == 1)
        self.linear_group.setVisible(not use_exponential)
        self.exponential_group.setVisible(use_exponential)
        self.update_graph()
    
    def on_param_changed(self):
        """Handle parameter changes"""
        self.update_graph()
    
    def update_from_config(self, calculator, config, track_name, current_ratio, times, last_results=None):
        """Update the display from config and data"""
        self.calculator = calculator
        self.config = config
        self.track_name = track_name
        self.current_ratio = current_ratio
        self.times = times
        self.last_results = last_results
        
        # Update method
        self.method_combo.setCurrentIndex(1 if config.use_exponential_model else 0)
        
        # Update linear params
        self.goal_percent.setValue(config.goal_percent)
        self.goal_offset.setValue(config.goal_offset)
        self.percent_ratio.setValue(config.percent_ratio)
        
        # Update exponential params
        self.exp_a.setValue(config.exponential_default_A)
        self.exp_k.setValue(config.exponential_default_k)
        self.exp_b.setValue(config.exponential_default_B)
        self.exp_p.setValue(config.exponential_power_factor)
        self.exp_r0.setValue(config.exponential_ratio_offset)
        self.exp_min.setValue(config.exponential_min_ratio)
        self.exp_max.setValue(config.exponential_max_ratio)
        
        # Update exponential formula
        R0 = config.exponential_ratio_offset
        if R0 >= 0:
            R0_str = f"+{R0:.2f}"
        else:
            R0_str = f"{R0:.2f}"
        
        if config.exponential_power_factor == 1.0:
            formula = f"R = {R0_str} + (-(1/{config.exponential_default_k:.3f}) × ln((T - {config.exponential_default_B:.1f})/{config.exponential_default_A:.1f}))"
        else:
            formula = f"R = {R0_str} + (-(1/{config.exponential_default_k:.3f}) × ln((T - {config.exponential_default_B:.1f})/{config.exponential_default_A:.1f}))^(1/{config.exponential_power_factor:.2f})"
        
        self.exp_formula.setText(formula)
        
        # Show/hide appropriate group
        self.linear_group.setVisible(not config.use_exponential_model)
        self.exponential_group.setVisible(config.use_exponential_model)
        
        # Update graph
        self.update_graph()
    
    def update_graph(self):
        """Update the graph with current parameters"""
        if not self.calculator or not self.times:
            return
        
        # Create a temporary config with current values
        temp_config = RatioConfig(
            historic_csv=self.config.historic_csv if self.config else "",
            goal_percent=self.goal_percent.value(),
            goal_offset=self.goal_offset.value(),
            percent_ratio=self.percent_ratio.value(),
            use_exponential_model=(self.method_combo.currentIndex() == 1),
            exponential_default_A=self.exp_a.value(),
            exponential_default_k=self.exp_k.value(),
            exponential_default_B=self.exp_b.value(),
            exponential_power_factor=self.exp_p.value(),
            exponential_ratio_offset=self.exp_r0.value(),
            exponential_min_ratio=self.exp_min.value(),
            exponential_max_ratio=self.exp_max.value()
        )
        
        # Update calculator with new params if in exponential mode
        if temp_config.use_exponential_model:
            self.calculator.configure_exponential_model(temp_config)
        
        # Get new ratio and predicted times if we have last_results
        new_ratio = None
        predicted_times = None
        
        if self.last_results:
            if self.last_results.has_qual_ratio():
                new_ratio = self.last_results.qual_ratio
                predicted_times = self.last_results.qual_details.predicted_times if self.last_results.qual_details else None
            elif self.last_results.has_race_ratio():
                new_ratio = self.last_results.race_ratio
                predicted_times = self.last_results.race_details.predicted_times if self.last_results.race_details else None
        
        # Update graph widget
        self.graph_widget.set_data(
            self.calculator,
            temp_config,
            self.track_name,
            self.current_ratio,
            self.times,
            new_ratio,
            predicted_times
        )


class ConfigWindow(QDialog):
    """Pop-up window showing configuration and CSV settings"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Configuration & CSV Settings")
        self.setMinimumWidth(600)
        self.setMinimumHeight(300)
        
        # Set dark theme
        self.setStyleSheet("""
            QDialog {
                background-color: #2b2b2b;
            }
            QLabel {
                color: white;
                font-size: 12px;
            }
            QGroupBox {
                color: #4CAF50;
                font-weight: bold;
                border: 2px solid #555;
                border-radius: 5px;
                margin-top: 8px;
                padding-top: 8px;
                font-size: 13px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
            QLineEdit {
                background-color: #3c3c3c;
                color: white;
                border: 1px solid #4CAF50;
                border-radius: 3px;
                padding: 5px;
                font-size: 12px;
                min-height: 25px;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # CSV section
        csv_group = QGroupBox("Historic Data CSV")
        csv_layout = QVBoxLayout(csv_group)
        
        csv_path_layout = QHBoxLayout()
        csv_path_layout.addWidget(QLabel("File path:"))
        self.csv_path = QLineEdit()
        self.csv_path.setReadOnly(True)
        csv_path_layout.addWidget(self.csv_path)
        
        self.csv_browse = QPushButton("Browse")
        self.csv_browse.setFixedWidth(100)
        self.csv_browse.setFixedHeight(30)
        csv_path_layout.addWidget(self.csv_browse)
        
        csv_layout.addLayout(csv_path_layout)
        
        layout.addWidget(csv_group)
        
        # Actions
        actions_group = QGroupBox("Actions")
        actions_layout = QHBoxLayout(actions_group)
        
        self.save_btn = QPushButton("Save Configuration to cfg.yml")
        self.save_btn.setFixedHeight(40)
        self.save_btn.setStyleSheet("background-color: #4CAF50; font-weight: bold;")
        actions_layout.addWidget(self.save_btn)
        
        layout.addWidget(actions_group)
        
        # Close button
        close_btn = QPushButton("Close")
        close_btn.setFixedHeight(40)
        close_btn.setFixedWidth(200)
        close_btn.clicked.connect(self.accept)
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 3px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_layout.addWidget(close_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
    
    def update_from_config(self, config):
        """Update the display from config"""
        self.csv_path.setText(config.historic_csv)


class ExponentialParamsDialog(QDialog):
    """Dialog for editing exponential model parameters"""
    
    def __init__(self, parent=None, current_params=None):
        super().__init__(parent)
        self.current_params = current_params or {}
        self.setup_ui()
        
    def setup_ui(self):
        self.setWindowTitle("Exponential Model Parameters")
        self.setModal(True)
        self.setMinimumWidth(500)
        
        layout = QVBoxLayout(self)
        
        # Formula display
        formula_group = QGroupBox("Current Formula")
        formula_layout = QVBoxLayout(formula_group)
        
        self.formula_label = QLabel()
        self.formula_label.setWordWrap(True)
        self.formula_label.setStyleSheet("""
            color: #4CAF50; 
            font-size: 13px; 
            font-weight: bold; 
            font-family: 'Courier New', monospace;
            background-color: #1e1e1e;
            padding: 10px;
            border: 1px solid #333;
            border-radius: 3px;
        """)
        self.formula_label.setAlignment(Qt.AlignCenter)
        formula_layout.addWidget(self.formula_label)
        
        layout.addWidget(formula_group)
        
        # Parameters group
        params_group = QGroupBox("Model Parameters")
        params_layout = QGridLayout(params_group)
        
        # Default A (time range)
        params_layout.addWidget(QLabel("A (Time Range):"), 0, 0)
        self.a_spin = QDoubleSpinBox()
        self.a_spin.setRange(10, 1000)
        self.a_spin.setDecimals(1)
        self.a_spin.setSingleStep(10)
        self.a_spin.setValue(self.current_params.get('default_A', 300.0))
        self.a_spin.setSuffix(" s")
        self.a_spin.valueChanged.connect(self.update_formula)
        params_layout.addWidget(self.a_spin, 0, 1)
        
        # Default k (decay constant)
        params_layout.addWidget(QLabel("k (Decay Rate):"), 0, 2)
        self.k_spin = QDoubleSpinBox()
        self.k_spin.setRange(0.1, 10)
        self.k_spin.setDecimals(3)
        self.k_spin.setSingleStep(0.1)
        self.k_spin.setValue(self.current_params.get('default_k', 3.0))
        self.k_spin.valueChanged.connect(self.update_formula)
        params_layout.addWidget(self.k_spin, 0, 3)
        
        # Default B (fastest time)
        params_layout.addWidget(QLabel("B (Fastest Time):"), 1, 0)
        self.b_spin = QDoubleSpinBox()
        self.b_spin.setRange(30, 500)
        self.b_spin.setDecimals(1)
        self.b_spin.setSingleStep(5)
        self.b_spin.setValue(self.current_params.get('default_B', 100.0))
        self.b_spin.setSuffix(" s")
        self.b_spin.valueChanged.connect(self.update_formula)
        params_layout.addWidget(self.b_spin, 1, 1)
        
        # Power factor (p)
        params_layout.addWidget(QLabel("p (Power Factor):"), 1, 2)
        self.p_spin = QDoubleSpinBox()
        self.p_spin.setRange(0.1, 5)
        self.p_spin.setDecimals(2)
        self.p_spin.setSingleStep(0.1)
        self.p_spin.setValue(self.current_params.get('power_factor', 1.0))
        self.p_spin.valueChanged.connect(self.update_formula)
        params_layout.addWidget(self.p_spin, 1, 3)
        
        # Ratio offset (R0)
        params_layout.addWidget(QLabel("R₀ (Ratio Offset):"), 2, 0)
        self.r0_spin = QDoubleSpinBox()
        self.r0_spin.setRange(-5, 5)
        self.r0_spin.setDecimals(2)
        self.r0_spin.setSingleStep(0.1)
        self.r0_spin.setValue(self.current_params.get('ratio_offset', 0.0))
        self.r0_spin.valueChanged.connect(self.update_formula)
        params_layout.addWidget(self.r0_spin, 2, 1)
        
        # Min ratio
        params_layout.addWidget(QLabel("Min Ratio:"), 2, 2)
        self.min_spin = QDoubleSpinBox()
        self.min_spin.setRange(0.01, 1)
        self.min_spin.setDecimals(2)
        self.min_spin.setSingleStep(0.05)
        self.min_spin.setValue(self.current_params.get('min_ratio', 0.1))
        params_layout.addWidget(self.min_spin, 2, 3)
        
        # Max ratio
        params_layout.addWidget(QLabel("Max Ratio:"), 3, 0)
        self.max_spin = QDoubleSpinBox()
        self.max_spin.setRange(1, 20)
        self.max_spin.setDecimals(2)
        self.max_spin.setSingleStep(0.5)
        self.max_spin.setValue(self.current_params.get('max_ratio', 10.0))
        params_layout.addWidget(self.max_spin, 3, 1)
        
        layout.addWidget(params_group)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.defaults_btn = QPushButton("Restore Defaults")
        self.defaults_btn.clicked.connect(self.restore_defaults)
        button_layout.addWidget(self.defaults_btn)
        
        button_layout.addStretch()
        
        self.ok_btn = QPushButton("OK")
        self.ok_btn.setFixedWidth(100)
        self.ok_btn.clicked.connect(self.accept)
        button_layout.addWidget(self.ok_btn)
        
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setFixedWidth(100)
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)
        
        layout.addLayout(button_layout)
        
        # Initial formula update
        self.update_formula()
    
    def update_formula(self):
        """Update the formula display with current parameters"""
        A = self.a_spin.value()
        k = self.k_spin.value()
        B = self.b_spin.value()
        p = self.p_spin.value()
        R0 = self.r0_spin.value()
        
        if R0 >= 0:
            R0_str = f"+{R0:.2f}"
        else:
            R0_str = f"{R0:.2f}"
        
        if p == 1.0:
            formula = f"R = {R0_str} + (-(1/{k:.3f}) × ln((T - {B:.1f})/{A:.1f}))"
        else:
            formula = f"R = {R0_str} + (-(1/{k:.3f}) × ln((T - {B:.1f})/{A:.1f}))^(1/{p:.2f})"
        
        self.formula_label.setText(formula)
    
    def restore_defaults(self):
        """Restore default parameter values"""
        self.a_spin.setValue(300.0)
        self.k_spin.setValue(3.0)
        self.b_spin.setValue(100.0)
        self.p_spin.setValue(1.0)
        self.r0_spin.setValue(0.0)
        self.min_spin.setValue(0.1)
        self.max_spin.setValue(10.0)
    
    def get_params(self):
        """Get the current parameter values"""
        return {
            'default_A': self.a_spin.value(),
            'default_k': self.k_spin.value(),
            'default_B': self.b_spin.value(),
            'power_factor': self.p_spin.value(),
            'ratio_offset': self.r0_spin.value(),
            'min_ratio': self.min_spin.value(),
            'max_ratio': self.max_spin.value()
        }


class RatioCalculatorDialog(QDialog):
    """Main dialog for ratio calculator - USER FOCUSED DESIGN"""
    
    def __init__(self, parent=None, track_name="", current_qual=1.0, current_race=1.0):
        super().__init__(parent)
        self.track_name = track_name
        self.current_qual = current_qual
        self.current_race = current_race
        self.new_qual = current_qual
        self.new_race = current_race
        self.calculator = RatioCalculator()
        
        # Pop-up windows (created on demand)
        self.predicted_window = None
        self.formula_window = None
        self.config_window = None
        
        # Store last calculation data
        self.last_results = None
        self.last_qual_times = None
        self.last_race_times = None
        
        # Load configuration
        self.config = RatioConfig(
            historic_csv=cfg_manage.get_historic_csv() or "",
            goal_percent=cfg_manage.get_goal_percent(),
            goal_offset=cfg_manage.get_goal_offset(),
            percent_ratio=cfg_manage.get_percent_ratio(),
            use_exponential_model=cfg_manage.get_use_exponential_model(),
            exponential_default_A=cfg_manage.get_exponential_param('default_A', 300.0),
            exponential_default_k=cfg_manage.get_exponential_param('default_k', 3.0),
            exponential_default_B=cfg_manage.get_exponential_param('default_B', 100.0),
            exponential_power_factor=cfg_manage.get_exponential_param('power_factor', 1.0),
            exponential_ratio_offset=cfg_manage.get_exponential_param('ratio_offset', 0.0),
            exponential_min_ratio=cfg_manage.get_exponential_param('min_ratio', 0.1),
            exponential_max_ratio=cfg_manage.get_exponential_param('max_ratio', 10.0)
        )
        
        # Initialize CSV handler
        self.csv_handler = HistoricCSVHandler(self.config.historic_csv)
        
        # Load historic data for exponential models if available
        if self.config.historic_csv and os.path.exists(self.config.historic_csv):
            self.calculator.load_historic_data(self.config.historic_csv)
        
        self.setup_ui()
        self.setup_connections()
        
    def setup_ui(self):
        self.setWindowTitle(f"Ratio Calculator - {self.track_name}")
        self.setModal(True)
        self.setMinimumWidth(900)
        self.setMinimumHeight(700)
        
        # Set dark theme
        self.setStyleSheet("""
            QDialog {
                background-color: #2b2b2b;
            }
            QLabel {
                color: white;
                font-size: 11px;
            }
            QGroupBox {
                color: #4CAF50;
                font-weight: bold;
                border: 2px solid #555;
                border-radius: 5px;
                margin-top: 8px;
                padding-top: 8px;
                font-size: 12px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 3px;
                padding: 6px;
                font-weight: bold;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:disabled {
                background-color: #666;
            }
            QSpinBox, QDoubleSpinBox, QComboBox, QLineEdit {
                background-color: #3c3c3c;
                color: white;
                border: 1px solid #4CAF50;
                border-radius: 3px;
                padding: 2px;
                font-size: 11px;
                min-height: 20px;
            }
        """)
        
        # Main layout
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(15, 15, 15, 15)
        
        # ===== TOP INFO BAR (ALWAYS VISIBLE, NON-INTRUSIVE) =====
        info_bar = QWidget()
        info_bar.setStyleSheet("""
            background-color: #3c3c3c;
            border-radius: 3px;
            padding: 5px;
        """)
        info_layout = QHBoxLayout(info_bar)
        info_layout.setContentsMargins(10, 5, 10, 5)
        
        # Track name
        track_label = QLabel(f"<b>Track:</b> {self.track_name}")
        track_label.setStyleSheet("color: #FFA500; font-size: 12px;")
        info_layout.addWidget(track_label)
        
        info_layout.addSpacing(20)
        
        # Current ratios
        info_layout.addWidget(QLabel("<b>Current Ratios:</b>"))
        
        qual_info = QLabel(f"Qual: {self.current_qual:.6f}")
        qual_info.setStyleSheet("color: #9C27B0;")
        info_layout.addWidget(qual_info)
        
        race_info = QLabel(f"Race: {self.current_race:.6f}")
        race_info.setStyleSheet("color: #9C27B0;")
        info_layout.addWidget(race_info)
        
        info_layout.addStretch()
        
        # CSV status indicator (compact)
        csv_status = QLabel("●" if self.csv_handler.is_valid() else "○")
        csv_status.setStyleSheet("color: #4CAF50; font-size: 16px;" if self.csv_handler.is_valid() else "color: #888; font-size: 16px;")
        csv_status.setToolTip("CSV file " + ("loaded" if self.csv_handler.is_valid() else "not found"))
        info_layout.addWidget(csv_status)
        
        layout.addWidget(info_bar)
        
        # ===== MAIN INPUT SECTION (PROMINENT) =====
        input_group = QGroupBox("Enter Lap Times")
        input_group.setStyleSheet("""
            QGroupBox {
                color: #FFA500;
                font-size: 14px;
                border: 2px solid #FFA500;
            }
        """)
        input_layout = QGridLayout(input_group)
        input_layout.setVerticalSpacing(10)
        input_layout.setHorizontalSpacing(15)
        
        # Headers
        input_layout.addWidget(QLabel(""), 0, 0)
        input_layout.addWidget(QLabel("Minutes"), 0, 1)
        input_layout.addWidget(QLabel("Seconds"), 0, 2)
        input_layout.addWidget(QLabel("Milliseconds"), 0, 3)
        input_layout.addWidget(QLabel("Total"), 0, 4)
        
        row = 1
        
        # Qualifying Best AI (required)
        input_layout.addWidget(QLabel("<b>Qual Best AI:</b>"), row, 0)
        self.qual_best_min = self.create_time_spinbox(0, 99)
        input_layout.addWidget(self.qual_best_min, row, 1)
        self.qual_best_sec = self.create_time_spinbox(0, 59)
        input_layout.addWidget(self.qual_best_sec, row, 2)
        self.qual_best_ms = self.create_time_spinbox(0, 999)
        self.qual_best_ms.setSingleStep(10)
        input_layout.addWidget(self.qual_best_ms, row, 3)
        self.qual_best_total = QLabel("0.000s")
        self.qual_best_total.setStyleSheet("color: #4CAF50; font-weight: bold;")
        input_layout.addWidget(self.qual_best_total, row, 4)
        row += 1
        
        # Qualifying Worst AI (required)
        input_layout.addWidget(QLabel("<b>Qual Worst AI:</b>"), row, 0)
        self.qual_worst_min = self.create_time_spinbox(0, 99)
        input_layout.addWidget(self.qual_worst_min, row, 1)
        self.qual_worst_sec = self.create_time_spinbox(0, 59)
        input_layout.addWidget(self.qual_worst_sec, row, 2)
        self.qual_worst_ms = self.create_time_spinbox(0, 999)
        self.qual_worst_ms.setSingleStep(10)
        input_layout.addWidget(self.qual_worst_ms, row, 3)
        self.qual_worst_total = QLabel("0.000s")
        self.qual_worst_total.setStyleSheet("color: #f44336; font-weight: bold;")
        input_layout.addWidget(self.qual_worst_total, row, 4)
        row += 1
        
        # Qualifying User (optional) - with subtle styling
        user_label = QLabel("Qual User (optional):")
        user_label.setStyleSheet("color: #888;")
        input_layout.addWidget(user_label, row, 0)
        self.qual_user_min = self.create_time_spinbox(0, 99)
        input_layout.addWidget(self.qual_user_min, row, 1)
        self.qual_user_sec = self.create_time_spinbox(0, 59)
        input_layout.addWidget(self.qual_user_sec, row, 2)
        self.qual_user_ms = self.create_time_spinbox(0, 999)
        self.qual_user_ms.setSingleStep(10)
        input_layout.addWidget(self.qual_user_ms, row, 3)
        self.qual_user_total = QLabel("0.000s")
        self.qual_user_total.setStyleSheet("color: #888; font-weight: bold;")
        input_layout.addWidget(self.qual_user_total, row, 4)
        row += 1
        
        # Separator
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        line.setStyleSheet("background-color: #555;")
        input_layout.addWidget(line, row, 0, 1, 5)
        row += 1
        
        # Race Best AI (optional) - with subtle styling
        race_best_label = QLabel("Race Best AI (optional):")
        race_best_label.setStyleSheet("color: #888;")
        input_layout.addWidget(race_best_label, row, 0)
        self.race_best_min = self.create_time_spinbox(0, 99)
        input_layout.addWidget(self.race_best_min, row, 1)
        self.race_best_sec = self.create_time_spinbox(0, 59)
        input_layout.addWidget(self.race_best_sec, row, 2)
        self.race_best_ms = self.create_time_spinbox(0, 999)
        self.race_best_ms.setSingleStep(10)
        input_layout.addWidget(self.race_best_ms, row, 3)
        self.race_best_total = QLabel("0.000s")
        self.race_best_total.setStyleSheet("color: #888;")
        input_layout.addWidget(self.race_best_total, row, 4)
        row += 1
        
        # Race Worst AI (optional)
        race_worst_label = QLabel("Race Worst AI (optional):")
        race_worst_label.setStyleSheet("color: #888;")
        input_layout.addWidget(race_worst_label, row, 0)
        self.race_worst_min = self.create_time_spinbox(0, 99)
        input_layout.addWidget(self.race_worst_min, row, 1)
        self.race_worst_sec = self.create_time_spinbox(0, 59)
        input_layout.addWidget(self.race_worst_sec, row, 2)
        self.race_worst_ms = self.create_time_spinbox(0, 999)
        self.race_worst_ms.setSingleStep(10)
        input_layout.addWidget(self.race_worst_ms, row, 3)
        self.race_worst_total = QLabel("0.000s")
        self.race_worst_total.setStyleSheet("color: #888;")
        input_layout.addWidget(self.race_worst_total, row, 4)
        row += 1
        
        # Race User (optional)
        race_user_label = QLabel("Race User (optional):")
        race_user_label.setStyleSheet("color: #888;")
        input_layout.addWidget(race_user_label, row, 0)
        self.race_user_min = self.create_time_spinbox(0, 99)
        input_layout.addWidget(self.race_user_min, row, 1)
        self.race_user_sec = self.create_time_spinbox(0, 59)
        input_layout.addWidget(self.race_user_sec, row, 2)
        self.race_user_ms = self.create_time_spinbox(0, 999)
        self.race_user_ms.setSingleStep(10)
        input_layout.addWidget(self.race_user_ms, row, 3)
        self.race_user_total = QLabel("0.000s")
        self.race_user_total.setStyleSheet("color: #888;")
        input_layout.addWidget(self.race_user_total, row, 4)
        
        layout.addWidget(input_group)
        
        # ===== RESULTS SECTION (SHOWN AFTER CALCULATION) =====
        self.results_group = QGroupBox("Results")
        self.results_group.setVisible(False)  # Hidden until calculation
        results_layout = QVBoxLayout(self.results_group)
        
        # Current position indicators
        pos_widget = QWidget()
        pos_layout = QHBoxLayout(pos_widget)
        pos_layout.setContentsMargins(0, 0, 0, 0)
        
        # Qualifying position
        qual_pos_group = QGroupBox("Qualifying")
        qual_pos_layout = QVBoxLayout(qual_pos_group)
        
        self.qual_current_pos = QLabel("Current: --")
        self.qual_current_pos.setStyleSheet("color: #888;")
        qual_pos_layout.addWidget(self.qual_current_pos)
        
        self.qual_target_pos = QLabel("Target: --")
        self.qual_target_pos.setStyleSheet("color: #4CAF50;")
        qual_pos_layout.addWidget(self.qual_target_pos)
        
        self.qual_ratio_change = QLabel("Change: --")
        self.qual_ratio_change.setStyleSheet("color: #9C27B0;")
        qual_pos_layout.addWidget(self.qual_ratio_change)
        
        pos_layout.addWidget(qual_pos_group)
        
        # Race position
        race_pos_group = QGroupBox("Race")
        race_pos_layout = QVBoxLayout(race_pos_group)
        
        self.race_current_pos = QLabel("Current: --")
        self.race_current_pos.setStyleSheet("color: #888;")
        race_pos_layout.addWidget(self.race_current_pos)
        
        self.race_target_pos = QLabel("Target: --")
        self.race_target_pos.setStyleSheet("color: #4CAF50;")
        race_pos_layout.addWidget(self.race_target_pos)
        
        self.race_ratio_change = QLabel("Change: --")
        self.race_ratio_change.setStyleSheet("color: #9C27B0;")
        race_pos_layout.addWidget(self.race_ratio_change)
        
        pos_layout.addWidget(race_pos_group)
        
        results_layout.addWidget(pos_widget)
        
        # New ratios (prominent)
        new_ratios_widget = QWidget()
        new_ratios_layout = QHBoxLayout(new_ratios_widget)
        new_ratios_layout.setContentsMargins(0, 10, 0, 10)
        
        new_ratios_layout.addStretch()
        
        new_ratios_layout.addWidget(QLabel("<b>New Ratios:</b>"))
        
        self.new_qual_label = QLabel(f"Qual: {self.current_qual:.6f}")
        self.new_qual_label.setStyleSheet("color: #9C27B0; font-size: 14px; font-weight: bold;")
        new_ratios_layout.addWidget(self.new_qual_label)
        
        new_ratios_layout.addSpacing(20)
        
        self.new_race_label = QLabel(f"Race: {self.current_race:.6f}")
        self.new_race_label.setStyleSheet("color: #9C27B0; font-size: 14px; font-weight: bold;")
        new_ratios_layout.addWidget(self.new_race_label)
        
        new_ratios_layout.addStretch()
        
        results_layout.addWidget(new_ratios_widget)
        
        layout.addWidget(self.results_group)
        
        # ===== BUTTONS FOR EXTRA INFORMATION (POP-UP WINDOWS) =====
        extra_buttons_layout = QHBoxLayout()
        extra_buttons_layout.setSpacing(10)
        
        # Predicted times button
        self.predicted_btn = QPushButton("Show Predicted AI Times")
        self.predicted_btn.setToolTip("Open window with predicted AI times at new ratio")
        self.predicted_btn.setFixedHeight(35)
        self.predicted_btn.setCursor(Qt.PointingHandCursor)
        self.predicted_btn.clicked.connect(self.show_predicted_times)
        self.predicted_btn.setEnabled(False)
        self.predicted_btn.setStyleSheet("""
            QPushButton {
                background-color: #FFA500;
                color: black;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #FFB52E;
            }
        """)
        extra_buttons_layout.addWidget(self.predicted_btn)
        
        # Formula details button
        self.formula_btn = QPushButton("Show Formula & Details")
        self.formula_btn.setToolTip("Open window with formula and calculation details")
        self.formula_btn.setFixedHeight(35)
        self.formula_btn.setCursor(Qt.PointingHandCursor)
        self.formula_btn.clicked.connect(self.show_formula_details)
        self.formula_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)
        extra_buttons_layout.addWidget(self.formula_btn)
        
        # Config button
        self.config_btn = QPushButton("Configuration & CSV")
        self.config_btn.setToolTip("Open window with configuration and CSV settings")
        self.config_btn.setFixedHeight(35)
        self.config_btn.setCursor(Qt.PointingHandCursor)
        self.config_btn.clicked.connect(self.show_config_window)
        self.config_btn.setStyleSheet("""
            QPushButton {
                background-color: #9C27B0;
                color: white;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #7B1FA2;
            }
        """)
        extra_buttons_layout.addWidget(self.config_btn)
        
        extra_buttons_layout.addStretch()
        
        layout.addLayout(extra_buttons_layout)
        
        # ===== ACTION BUTTONS =====
        button_layout = QHBoxLayout()
        
        self.calc_btn = QPushButton("CALCULATE")
        self.calc_btn.setToolTip("Calculate new ratios based on entered times")
        self.calc_btn.setFixedHeight(50)
        self.calc_btn.setFixedWidth(200)
        self.calc_btn.setCursor(Qt.PointingHandCursor)
        self.calc_btn.clicked.connect(self.calculate_ratios)
        self.calc_btn.setEnabled(False)
        self.calc_btn.setStyleSheet("""
            QPushButton {
                background-color: #9C27B0;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #7B1FA2;
            }
        """)
        button_layout.addWidget(self.calc_btn)
        
        button_layout.addStretch()
        
        self.apply_btn = QPushButton("APPLY RATIOS")
        self.apply_btn.setFixedHeight(50)
        self.apply_btn.setFixedWidth(200)
        self.apply_btn.setCursor(Qt.PointingHandCursor)
        self.apply_btn.clicked.connect(self.accept)
        self.apply_btn.setEnabled(False)
        self.apply_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        button_layout.addWidget(self.apply_btn)
        
        self.cancel_btn = QPushButton("CANCEL")
        self.cancel_btn.setFixedHeight(50)
        self.cancel_btn.setFixedWidth(200)
        self.cancel_btn.setCursor(Qt.PointingHandCursor)
        self.cancel_btn.clicked.connect(self.reject)
        self.cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #d32f2f;
            }
        """)
        button_layout.addWidget(self.cancel_btn)
        
        layout.addLayout(button_layout)
        
        # Status label
        self.status_label = QLabel("")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("color: #888; font-style: italic;")
        layout.addWidget(self.status_label)
    
    def setup_connections(self):
        """Setup signal connections for live updates"""
        # Qualifying connections
        self.qual_best_min.valueChanged.connect(self.update_qual_totals)
        self.qual_best_sec.valueChanged.connect(self.update_qual_totals)
        self.qual_best_ms.valueChanged.connect(self.update_qual_totals)
        self.qual_worst_min.valueChanged.connect(self.update_qual_totals)
        self.qual_worst_sec.valueChanged.connect(self.update_qual_totals)
        self.qual_worst_ms.valueChanged.connect(self.update_qual_totals)
        self.qual_user_min.valueChanged.connect(self.update_qual_totals)
        self.qual_user_sec.valueChanged.connect(self.update_qual_totals)
        self.qual_user_ms.valueChanged.connect(self.update_qual_totals)
        
        # Race connections
        self.race_best_min.valueChanged.connect(self.update_race_totals)
        self.race_best_sec.valueChanged.connect(self.update_race_totals)
        self.race_best_ms.valueChanged.connect(self.update_race_totals)
        self.race_worst_min.valueChanged.connect(self.update_race_totals)
        self.race_worst_sec.valueChanged.connect(self.update_race_totals)
        self.race_worst_ms.valueChanged.connect(self.update_race_totals)
        self.race_user_min.valueChanged.connect(self.update_race_totals)
        self.race_user_sec.valueChanged.connect(self.update_race_totals)
        self.race_user_ms.valueChanged.connect(self.update_race_totals)
        
        # Also update button state
        for spin in [self.qual_best_min, self.qual_best_sec, self.qual_best_ms,
                     self.qual_worst_min, self.qual_worst_sec, self.qual_worst_ms]:
            spin.valueChanged.connect(self.check_calc_button)
    
    def create_time_spinbox(self, min_val, max_val):
        """Create a compact spinbox for time input"""
        spin = QSpinBox()
        spin.setRange(min_val, max_val)
        spin.setValue(0)
        spin.setFixedHeight(24)
        spin.setFixedWidth(70)
        spin.setAlignment(Qt.AlignRight)
        return spin
    
    def update_qual_totals(self):
        """Update qualifying total displays"""
        best = self.get_time_value(self.qual_best_min, self.qual_best_sec, self.qual_best_ms)
        worst = self.get_time_value(self.qual_worst_min, self.qual_worst_sec, self.qual_worst_ms)
        user = self.get_time_value(self.qual_user_min, self.qual_user_sec, self.qual_user_ms)
        
        self.qual_best_total.setText(f"{best:.3f}s")
        self.qual_worst_total.setText(f"{worst:.3f}s")
        self.qual_user_total.setText(f"{user:.3f}s")
    
    def update_race_totals(self):
        """Update race total displays"""
        best = self.get_time_value(self.race_best_min, self.race_best_sec, self.race_best_ms)
        worst = self.get_time_value(self.race_worst_min, self.race_worst_sec, self.race_worst_ms)
        user = self.get_time_value(self.race_user_min, self.race_user_sec, self.race_user_ms)
        
        self.race_best_total.setText(f"{best:.3f}s")
        self.race_worst_total.setText(f"{worst:.3f}s")
        self.race_user_total.setText(f"{user:.3f}s")
    
    def get_time_value(self, min_spin, sec_spin, ms_spin):
        """Get total seconds from spinboxes"""
        return min_spin.value() * 60 + sec_spin.value() + ms_spin.value() / 1000.0
    
    def check_calc_button(self):
        """Enable calculate button if qualifying best and worst have values"""
        qual_best = self.get_time_value(self.qual_best_min, self.qual_best_sec, self.qual_best_ms) > 0
        qual_worst = self.get_time_value(self.qual_worst_min, self.qual_worst_sec, self.qual_worst_ms) > 0
        
        self.calc_btn.setEnabled(qual_best and qual_worst)
    
    def get_qual_times(self):
        """Get qualifying lap times"""
        best = self.get_time_value(self.qual_best_min, self.qual_best_sec, self.qual_best_ms)
        worst = self.get_time_value(self.qual_worst_min, self.qual_worst_sec, self.qual_worst_ms)
        user = self.get_time_value(self.qual_user_min, self.qual_user_sec, self.qual_user_ms)
        return LapTimes(best, worst, user)
    
    def get_race_times(self):
        """Get race lap times"""
        best = self.get_time_value(self.race_best_min, self.race_best_sec, self.race_best_ms)
        worst = self.get_time_value(self.race_worst_min, self.race_worst_sec, self.race_worst_ms)
        user = self.get_time_value(self.race_user_min, self.race_user_sec, self.race_user_ms)
        return LapTimes(best, worst, user)
    
    def show_predicted_times(self):
        """Show the predicted times pop-up window"""
        if not self.predicted_window:
            self.predicted_window = PredictedTimesWindow(self)
        
        # Update with current results if available
        if hasattr(self, 'last_results'):
            qual_pred = self.last_results.qual_details.predicted_times if self.last_results and self.last_results.qual_details else None
            race_pred = self.last_results.race_details.predicted_times if self.last_results and self.last_results.race_details else None
            self.predicted_window.update_times(qual_pred, race_pred)
        
        self.predicted_window.show()
        self.predicted_window.raise_()
    
    def show_formula_details(self):
        """Show the formula details pop-up window with graph"""
        if not self.formula_window:
            self.formula_window = FormulaDetailsWindow(self)
            # Connect the edit params button
            self.formula_window.edit_params_btn.clicked.connect(self.edit_exponential_params)
        
        # Get the appropriate times to show
        times = None
        if self.last_qual_times and self.last_qual_times.are_valid():
            times = self.last_qual_times
        elif self.last_race_times and self.last_race_times.are_valid():
            times = self.last_race_times
        
        if times:
            self.formula_window.update_from_config(
                self.calculator,
                self.config,
                self.track_name,
                self.current_qual,
                times,
                self.last_results
            )
        
        self.formula_window.show()
        self.formula_window.raise_()
    
    def show_config_window(self):
        """Show the configuration pop-up window"""
        if not self.config_window:
            self.config_window = ConfigWindow(self)
            # Connect buttons
            self.config_window.csv_browse.clicked.connect(self.browse_csv)
            self.config_window.save_btn.clicked.connect(self.save_configuration)
        
        self.config_window.update_from_config(self.config)
        self.config_window.show()
        self.config_window.raise_()
    
    def edit_exponential_params(self):
        """Open dialog to edit exponential parameters"""
        current_params = {
            'default_A': self.config.exponential_default_A,
            'default_k': self.config.exponential_default_k,
            'default_B': self.config.exponential_default_B,
            'power_factor': self.config.exponential_power_factor,
            'ratio_offset': self.config.exponential_ratio_offset,
            'min_ratio': self.config.exponential_min_ratio,
            'max_ratio': self.config.exponential_max_ratio
        }
        
        dialog = ExponentialParamsDialog(self, current_params)
        if dialog.exec_() == QDialog.Accepted:
            new_params = dialog.get_params()
            
            # Update config
            for key, value in new_params.items():
                setattr(self.config, key, value)
            
            # Update calculator
            self.calculator.configure_exponential_model(self.config)
            
            # Update formula window if open
            if self.formula_window and self.formula_window.isVisible():
                times = None
                if self.last_qual_times and self.last_qual_times.are_valid():
                    times = self.last_qual_times
                elif self.last_race_times and self.last_race_times.are_valid():
                    times = self.last_race_times
                
                if times:
                    self.formula_window.update_from_config(
                        self.calculator,
                        self.config,
                        self.track_name,
                        self.current_qual,
                        times,
                        self.last_results
                    )
            
            # Save to cfg.yml
            self.save_configuration()
    
    def browse_csv(self):
        """Browse for CSV file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Historic CSV File",
            self.config.historic_csv,
            "CSV Files (*.csv);;All Files (*)"
        )
        
        if file_path:
            self.config.historic_csv = file_path
            self.csv_handler = HistoricCSVHandler(self.config.historic_csv)
            if os.path.exists(file_path):
                self.calculator.load_historic_data(file_path)
            
            # Update config window if open
            if self.config_window and self.config_window.isVisible():
                self.config_window.update_from_config(self.config)
    
    def save_configuration(self):
        """Save configuration to file"""
        if self.config.historic_csv:
            cfg_manage.update_historic_csv(self.config.historic_csv)
        
        cfg_manage.update_goal_percent(self.config.goal_percent)
        cfg_manage.update_goal_offset(self.config.goal_offset)
        cfg_manage.update_percent_ratio(self.config.percent_ratio)
        cfg_manage.update_use_exponential_model(self.config.use_exponential_model)
        
        cfg_manage.update_exponential_param('default_A', self.config.exponential_default_A)
        cfg_manage.update_exponential_param('default_k', self.config.exponential_default_k)
        cfg_manage.update_exponential_param('default_B', self.config.exponential_default_B)
        cfg_manage.update_exponential_param('power_factor', self.config.exponential_power_factor)
        cfg_manage.update_exponential_param('ratio_offset', self.config.exponential_ratio_offset)
        cfg_manage.update_exponential_param('min_ratio', self.config.exponential_min_ratio)
        cfg_manage.update_exponential_param('max_ratio', self.config.exponential_max_ratio)
        
        QMessageBox.information(self, "Saved", "Configuration saved to cfg.yml")
    
    def calculate_ratios(self):
        """Calculate ratios and show results"""
        qual_times = self.get_qual_times()
        race_times = self.get_race_times()
        
        # Store times for graph
        self.last_qual_times = qual_times if qual_times.are_valid() else None
        self.last_race_times = race_times if race_times.are_valid() else None
        
        # Check if race times are all zero (not entered)
        race_has_data = (race_times.pole > 0 or race_times.last_ai > 0 or race_times.player > 0)
        
        # Save to CSV if handler is valid
        if self.csv_handler.is_valid() and (qual_times.pole > 0 or race_has_data):
            self.save_to_csv(qual_times, race_times)
            self.status_label.setText(f"✓ Saved to {os.path.basename(self.config.historic_csv)}")
        
        # Update config with current values from formula window if open
        if self.formula_window and self.formula_window.isVisible():
            self.config.use_exponential_model = (self.formula_window.method_combo.currentIndex() == 1)
            self.config.goal_percent = self.formula_window.goal_percent.value()
            self.config.goal_offset = self.formula_window.goal_offset.value()
            self.config.percent_ratio = self.formula_window.percent_ratio.value()
            
            self.config.exponential_default_A = self.formula_window.exp_a.value()
            self.config.exponential_default_k = self.formula_window.exp_k.value()
            self.config.exponential_default_B = self.formula_window.exp_b.value()
            self.config.exponential_power_factor = self.formula_window.exp_p.value()
            self.config.exponential_ratio_offset = self.formula_window.exp_r0.value()
            self.config.exponential_min_ratio = self.formula_window.exp_min.value()
            self.config.exponential_max_ratio = self.formula_window.exp_max.value()
        
        # Configure exponential model if needed
        if self.config.use_exponential_model:
            self.calculator.configure_exponential_model(self.config)
        
        # Calculate ratios
        self.last_results = self.calculator.calculate_all(
            qual_times, race_times, self.config, self.track_name,
            self.current_qual, self.current_race
        )
        
        # Update results display
        target = self.config.goal_percent + self.config.goal_offset
        
        # Show results section
        self.results_group.setVisible(True)
        
        # Update qualifying results
        if self.last_results.has_qual_ratio() and self.last_results.qual_details:
            self.new_qual = self.last_results.qual_ratio
            self.new_qual_label.setText(f"Qual: {self.new_qual:.6f}")
            
            self.qual_current_pos.setText(f"Current: {self.last_results.qual_details.current_position:.1f}%")
            self.qual_target_pos.setText(f"Target: {self.last_results.qual_details.target_position:.1f}%")
            self.qual_ratio_change.setText(f"Change: {self.last_results.qual_details.ratio_change:+.6f}")
            
            # Color code position
            if self.last_results.qual_details.current_position < 33:
                self.qual_current_pos.setStyleSheet("color: #4CAF50;")
            elif self.last_results.qual_details.current_position < 66:
                self.qual_current_pos.setStyleSheet("color: #FFA500;")
            else:
                self.qual_current_pos.setStyleSheet("color: #f44336;")
        else:
            self.qual_current_pos.setText("Current: --")
            self.qual_target_pos.setText(f"Target: {target:.1f}%")
            self.qual_ratio_change.setText("Change: --")
        
        # Update race results
        if self.last_results.has_race_ratio() and self.last_results.race_details:
            self.new_race = self.last_results.race_ratio
            self.new_race_label.setText(f"Race: {self.new_race:.6f}")
            
            self.race_current_pos.setText(f"Current: {self.last_results.race_details.current_position:.1f}%")
            self.race_target_pos.setText(f"Target: {self.last_results.race_details.target_position:.1f}%")
            self.race_ratio_change.setText(f"Change: {self.last_results.race_details.ratio_change:+.6f}")
            
            if self.last_results.race_details.current_position < 33:
                self.race_current_pos.setStyleSheet("color: #4CAF50;")
            elif self.last_results.race_details.current_position < 66:
                self.race_current_pos.setStyleSheet("color: #FFA500;")
            else:
                self.race_current_pos.setStyleSheet("color: #f44336;")
        else:
            if race_has_data:
                self.race_current_pos.setText("Current: --")
                self.race_target_pos.setText(f"Target: {target:.1f}%")
                self.race_ratio_change.setText("Change: --")
            else:
                # No race data entered
                self.race_current_pos.setText("Current: --")
                self.race_target_pos.setText("Target: --")
                self.race_ratio_change.setText("Change: --")
        
        # Enable predicted times button if we have predictions
        has_predictions = False
        qual_pred = None
        race_pred = None
        
        if self.last_results.qual_details and self.last_results.qual_details.predicted_times:
            has_predictions = True
            qual_pred = self.last_results.qual_details.predicted_times
        
        if self.last_results.race_details and self.last_results.race_details.predicted_times:
            has_predictions = True
            race_pred = self.last_results.race_details.predicted_times
        
        self.predicted_btn.setEnabled(has_predictions)
        
        # Update predicted times window if open
        if self.predicted_window and self.predicted_window.isVisible():
            self.predicted_window.update_times(qual_pred, race_pred)
        
        # Update formula window if open
        if self.formula_window and self.formula_window.isVisible():
            times = qual_times if qual_times.are_valid() else race_times
            if times.are_valid():
                self.formula_window.update_from_config(
                    self.calculator,
                    self.config,
                    self.track_name,
                    self.current_qual,
                    times,
                    self.last_results
                )
        
        # Enable apply button if any ratio calculated
        self.apply_btn.setEnabled(self.last_results.any_ratio_calculated())
        
        # Show message if no results
        if not self.last_results.any_ratio_calculated():
            msg = "Could not calculate new ratios.\n"
            if self.last_results.qual_error:
                msg += f"Qualifying: {self.last_results.qual_error}\n"
            if self.last_results.race_error:
                msg += f"Race: {self.last_results.race_error}"
            QMessageBox.warning(self, "Calculation Failed", msg)
    
    def save_to_csv(self, qual_times, race_times):
        """Save data to CSV"""
        import csv
        from datetime import datetime
        
        file_path = self.config.historic_csv
        if not file_path:
            return
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        row = [
            timestamp,
            self.track_name,
            f"{self.current_qual:.6f}",
            f"{qual_times.pole:.3f}" if qual_times.pole > 0 else "0",
            f"{qual_times.last_ai:.3f}" if qual_times.last_ai > 0 else "0",
            f"{qual_times.player:.3f}" if qual_times.player > 0 else "0",
            f"{self.current_race:.6f}",
            f"{race_times.pole:.3f}" if race_times.pole > 0 else "0",
            f"{race_times.last_ai:.3f}" if race_times.last_ai > 0 else "0",
            f"{race_times.player:.3f}" if race_times.player > 0 else "0"
        ]
        
        file_exists = os.path.isfile(file_path)
        
        try:
            with open(file_path, 'a', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile, delimiter=';')
                
                if not file_exists or os.path.getsize(file_path) == 0:
                    header = [
                        'Timestamp', 'Track Name', 'Current QualRatio',
                        'Qual AI Best (s)', 'Qual AI Worst (s)', 'Qual User (s)',
                        'Current RaceRatio', 'Race AI Best (s)', 'Race AI Worst (s)', 'Race User (s)'
                    ]
                    writer.writerow(header)
                
                writer.writerow(row)
                
                # Reload models after saving
                self.calculator.load_historic_data(file_path)
                
        except Exception as e:
            print(f"Error saving to CSV: {e}")
    
    def get_ratios(self):
        """Return the calculated ratios"""
        return self.new_qual, self.new_race
