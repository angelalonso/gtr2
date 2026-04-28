#!/usr/bin/env python3
"""
AI Target Analyzer - Data dump and decision logging for AI target calculations
Provides detailed logging of the entire decision-making process
"""

import json
import csv
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum


class CalculationStepType(Enum):
    """Types of calculation steps"""
    INPUT_DATA = "INPUT_DATA"
    TARGET_SETTINGS = "TARGET_SETTINGS"
    FORMULA_USED = "FORMULA_USED"
    CALCULATION = "CALCULATION"
    RANGE_CHECK = "RANGE_CHECK"
    DECISION = "DECISION"
    WARNING = "WARNING"
    ERROR = "ERROR"
    RESULT = "RESULT"


@dataclass
class CalculationStep:
    """Single step in the calculation process"""
    step_type: CalculationStepType
    description: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AITargetAnalysis:
    """Complete analysis of an AI target calculation"""
    analysis_id: str
    timestamp: str
    session_type: str  # "qual" or "race"
    track_name: str
    vehicle_class: str
    
    # Input data
    ai_range: Dict[str, Optional[float]] = field(default_factory=dict)
    user_lap_time: Optional[float] = None
    current_ratio: Optional[float] = None
    formula: Dict[str, float] = field(default_factory=dict)
    
    # Target settings
    target_mode: str = "percentage"
    target_settings: Dict[str, Any] = field(default_factory=dict)
    
    # Calculation results
    target_lap_time: Optional[float] = None
    calculated_ratio: Optional[float] = None
    final_ratio: Optional[float] = None
    
    # Decision logs
    steps: List[CalculationStep] = field(default_factory=list)
    
    # Final status
    success: bool = False
    message: str = ""
    
    def add_step(self, step_type: CalculationStepType, description: str, data: Dict[str, Any] = None):
        """Add a calculation step to the analysis"""
        self.steps.append(CalculationStep(
            step_type=step_type,
            description=description,
            data=data or {}
        ))
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "analysis_id": self.analysis_id,
            "timestamp": self.timestamp,
            "session_type": self.session_type,
            "track_name": self.track_name,
            "vehicle_class": self.vehicle_class,
            "ai_range": self.ai_range,
            "user_lap_time": self.user_lap_time,
            "current_ratio": self.current_ratio,
            "formula": self.formula,
            "target_mode": self.target_mode,
            "target_settings": self.target_settings,
            "target_lap_time": self.target_lap_time,
            "calculated_ratio": self.calculated_ratio,
            "final_ratio": self.final_ratio,
            "steps": [
                {
                    "type": s.step_type.value,
                    "timestamp": s.timestamp,
                    "description": s.description,
                    "data": s.data
                }
                for s in self.steps
            ],
            "success": self.success,
            "message": self.message
        }
    
    def to_text(self) -> str:
        """Convert to human-readable text format"""
        lines = []
        lines.append("=" * 80)
        lines.append(f"AI TARGET ANALYSIS - {self.analysis_id}")
        lines.append(f"Timestamp: {self.timestamp}")
        lines.append(f"Session Type: {self.session_type.upper()}")
        lines.append(f"Track: {self.track_name}")
        lines.append(f"Vehicle Class: {self.vehicle_class}")
        lines.append("=" * 80)
        lines.append("")
        
        lines.append("📊 INPUT DATA")
        lines.append("-" * 40)
        if self.ai_range.get("best"):
            lines.append(f"  AI Best Lap: {self.ai_range['best']:.3f}s")
        else:
            lines.append("  AI Best Lap: Not available")
        if self.ai_range.get("worst"):
            lines.append(f"  AI Worst Lap: {self.ai_range['worst']:.3f}s")
        else:
            lines.append("  AI Worst Lap: Not available")
        if self.ai_range.get("range"):
            lines.append(f"  AI Range Width: {self.ai_range['range']:.3f}s")
        if self.user_lap_time:
            lines.append(f"  User Lap Time: {self.user_lap_time:.3f}s")
        if self.current_ratio:
            lines.append(f"  Current Ratio: {self.current_ratio:.6f}")
        lines.append("")
        
        lines.append("📐 FORMULA")
        lines.append("-" * 40)
        if self.formula:
            lines.append(f"  Formula: T = {self.formula.get('a', 32):.2f} / R + {self.formula.get('b', 70):.2f}")
            lines.append(f"  'a' (slope/steepness): {self.formula.get('a', 32):.2f} (fixed at 32)")
            lines.append(f"  'b' (baseline time): {self.formula.get('b', 70):.2f}s")
        else:
            lines.append("  Formula: Default (a=32, b=70)")
        lines.append("")
        
        lines.append("🎯 TARGET SETTINGS")
        lines.append("-" * 40)
        if self.target_mode == "percentage":
            pct = self.target_settings.get("percentage", 50)
            lines.append(f"  Mode: Percentage within AI range")
            lines.append(f"  Target Position: {pct}% from fastest to slowest AI")
            if pct == 0:
                lines.append(f"  Goal: Match the FASTEST AI lap time")
            elif pct == 100:
                lines.append(f"  Goal: Match the SLOWEST AI lap time")
            elif pct == 50:
                lines.append(f"  Goal: Be exactly in the MIDDLE of the AI range")
            else:
                lines.append(f"  Goal: Be {pct}% from fastest to slowest AI")
        elif self.target_mode == "faster_than_best":
            offset = self.target_settings.get("offset_seconds", 0)
            lines.append(f"  Mode: Fixed offset from fastest AI")
            if offset == 0:
                lines.append(f"  Goal: Match the fastest AI lap time")
            elif offset > 0:
                lines.append(f"  Goal: Be {offset:.2f} seconds SLOWER than fastest AI")
            else:
                lines.append(f"  Goal: Be {abs(offset):.2f} seconds FASTER than fastest AI")
        else:
            offset = self.target_settings.get("offset_seconds", 0)
            lines.append(f"  Mode: Fixed offset from slowest AI")
            if offset == 0:
                lines.append(f"  Goal: Match the slowest AI lap time")
            elif offset > 0:
                lines.append(f"  Goal: Be {offset:.2f} seconds FASTER than slowest AI")
            else:
                lines.append(f"  Goal: Be {abs(offset):.2f} seconds SLOWER than slowest AI")
        
        error_margin = self.target_settings.get("error_margin", 0)
        if error_margin > 0:
            lines.append(f"  Error Margin: +{error_margin:.2f}s (makes AI slower)")
        lines.append("")
        
        lines.append("🔢 CALCULATION STEPS")
        lines.append("-" * 40)
        for i, step in enumerate(self.steps, 1):
            icon = self._get_step_icon(step.step_type)
            lines.append(f"  {i}. {icon} {step.description}")
            if step.data:
                for key, value in step.data.items():
                    if isinstance(value, float):
                        lines.append(f"       {key}: {value:.6f}" if "ratio" in key.lower() or "time" in key.lower() else f"       {key}: {value:.3f}" if isinstance(value, float) else f"       {key}: {value}")
                    else:
                        lines.append(f"       {key}: {value}")
        lines.append("")
        
        lines.append("📈 RESULTS")
        lines.append("-" * 40)
        if self.target_lap_time:
            lines.append(f"  Target Lap Time: {self.target_lap_time:.3f}s")
        if self.calculated_ratio:
            lines.append(f"  Calculated Ratio: {self.calculated_ratio:.6f}")
        if self.final_ratio:
            lines.append(f"  Final Ratio: {self.final_ratio:.6f}")
        lines.append(f"  Success: {'✓' if self.success else '✗'}")
        lines.append(f"  Message: {self.message}")
        lines.append("")
        lines.append("=" * 80)
        
        return "\n".join(lines)
    
    def _get_step_icon(self, step_type: CalculationStepType) -> str:
        """Get icon for step type"""
        icons = {
            CalculationStepType.INPUT_DATA: "📊",
            CalculationStepType.TARGET_SETTINGS: "🎯",
            CalculationStepType.FORMULA_USED: "📐",
            CalculationStepType.CALCULATION: "🔢",
            CalculationStepType.RANGE_CHECK: "⚠️",
            CalculationStepType.DECISION: "🤔",
            CalculationStepType.WARNING: "⚠️",
            CalculationStepType.ERROR: "❌",
            CalculationStepType.RESULT: "✅"
        }
        return icons.get(step_type, "•")


class AITargetAnalyzer:
    """Analyzer for AI target calculations - logs all decisions and data"""
    
    def __init__(self, dump_dir: str = "ai_target_dumps"):
        self.dump_dir = Path(dump_dir)
        self.dump_dir.mkdir(parents=True, exist_ok=True)
        self.current_analysis: Optional[AITargetAnalysis] = None
    
    def start_analysis(self, session_type: str, track_name: str, vehicle_class: str) -> str:
        """Start a new analysis session"""
        analysis_id = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        self.current_analysis = AITargetAnalysis(
            analysis_id=analysis_id,
            timestamp=datetime.now().isoformat(),
            session_type=session_type,
            track_name=track_name,
            vehicle_class=vehicle_class
        )
        return analysis_id
    
    def add_input_data(
        self, 
        best_ai: Optional[float], 
        worst_ai: Optional[float],
        user_lap_time: Optional[float],
        current_ratio: Optional[float],
        formula_a: float = 32.0,
        formula_b: float = 70.0
    ):
        """Record input data for the calculation"""
        if not self.current_analysis:
            return
        
        self.current_analysis.ai_range = {
            "best": best_ai,
            "worst": worst_ai,
            "range": (worst_ai - best_ai) if best_ai and worst_ai else None
        }
        self.current_analysis.user_lap_time = user_lap_time
        self.current_analysis.current_ratio = current_ratio
        self.current_analysis.formula = {"a": formula_a, "b": formula_b}
        
        # Add steps for each input
        if best_ai and worst_ai:
            range_width = worst_ai - best_ai
            self.current_analysis.add_step(
                CalculationStepType.INPUT_DATA,
                f"AI lap time range: {best_ai:.3f}s (fastest) to {worst_ai:.3f}s (slowest), range width = {range_width:.3f}s",
                {"best_ai": best_ai, "worst_ai": worst_ai, "range_width": range_width}
            )
        elif best_ai:
            self.current_analysis.add_step(
                CalculationStepType.INPUT_DATA,
                f"Only best AI time available: {best_ai:.3f}s",
                {"best_ai": best_ai}
            )
        elif worst_ai:
            self.current_analysis.add_step(
                CalculationStepType.INPUT_DATA,
                f"Only worst AI time available: {worst_ai:.3f}s",
                {"worst_ai": worst_ai}
            )
        else:
            self.current_analysis.add_step(
                CalculationStepType.ERROR,
                "No AI lap time data available",
                {}
            )
        
        if user_lap_time and user_lap_time > 0:
            self.current_analysis.add_step(
                CalculationStepType.INPUT_DATA,
                f"User lap time: {user_lap_time:.3f}s",
                {"user_lap_time": user_lap_time}
            )
        
        if current_ratio:
            self.current_analysis.add_step(
                CalculationStepType.INPUT_DATA,
                f"Current ratio in AIW: {current_ratio:.6f}",
                {"current_ratio": current_ratio}
            )
        
        self.current_analysis.add_step(
            CalculationStepType.FORMULA_USED,
            f"Using formula: T = {formula_a:.2f} / R + {formula_b:.2f}",
            {"a": formula_a, "b": formula_b}
        )
    
    def add_target_settings(self, mode: str, settings: Dict[str, Any]):
        """Record target settings"""
        if not self.current_analysis:
            return
        
        self.current_analysis.target_mode = mode
        self.current_analysis.target_settings = settings
        
        if mode == "percentage":
            pct = settings.get("percentage", 50)
            self.current_analysis.add_step(
                CalculationStepType.TARGET_SETTINGS,
                f"Target mode: Percentage within AI range ({pct}% from fastest to slowest AI)",
                {"percentage": pct}
            )
        elif mode == "faster_than_best":
            offset = settings.get("offset_seconds", 0)
            desc = f"Target mode: Faster than best AI" + (f" ({offset:+.2f}s)" if offset != 0 else "")
            self.current_analysis.add_step(
                CalculationStepType.TARGET_SETTINGS,
                desc,
                {"offset_seconds": offset}
            )
        else:
            offset = settings.get("offset_seconds", 0)
            desc = f"Target mode: Slower than worst AI" + (f" ({offset:+.2f}s)" if offset != 0 else "")
            self.current_analysis.add_step(
                CalculationStepType.TARGET_SETTINGS,
                desc,
                {"offset_seconds": offset}
            )
        
        error_margin = settings.get("error_margin", 0)
        if error_margin > 0:
            self.current_analysis.add_step(
                CalculationStepType.TARGET_SETTINGS,
                f"Error margin: +{error_margin:.2f}s (adds extra time to make AI slightly slower)",
                {"error_margin": error_margin}
            )
    
    def add_calculation_step(self, description: str, data: Dict[str, Any] = None):
        """Add a calculation step"""
        if not self.current_analysis:
            return
        self.current_analysis.add_step(
            CalculationStepType.CALCULATION,
            description,
            data
        )
    
    def add_range_check(self, description: str, data: Dict[str, Any] = None):
        """Add a range check step"""
        if not self.current_analysis:
            return
        self.current_analysis.add_step(
            CalculationStepType.RANGE_CHECK,
            description,
            data
        )
    
    def add_decision(self, description: str, data: Dict[str, Any] = None):
        """Add a decision step"""
        if not self.current_analysis:
            return
        self.current_analysis.add_step(
            CalculationStepType.DECISION,
            description,
            data
        )
    
    def add_warning(self, description: str, data: Dict[str, Any] = None):
        """Add a warning"""
        if not self.current_analysis:
            return
        self.current_analysis.add_step(
            CalculationStepType.WARNING,
            description,
            data
        )
    
    def add_error(self, description: str, data: Dict[str, Any] = None):
        """Add an error"""
        if not self.current_analysis:
            return
        self.current_analysis.add_step(
            CalculationStepType.ERROR,
            description,
            data
        )
    
    def set_result(
        self, 
        target_lap_time: float, 
        calculated_ratio: float, 
        final_ratio: float,
        success: bool,
        message: str
    ):
        """Set the final result of the calculation"""
        if not self.current_analysis:
            return
        
        self.current_analysis.target_lap_time = target_lap_time
        self.current_analysis.calculated_ratio = calculated_ratio
        self.current_analysis.final_ratio = final_ratio
        self.current_analysis.success = success
        self.current_analysis.message = message
        
        if success:
            self.current_analysis.add_step(
                CalculationStepType.RESULT,
                f"Calculation successful: New ratio = {final_ratio:.6f} (target lap time: {target_lap_time:.3f}s)",
                {"new_ratio": final_ratio, "target_lap_time": target_lap_time}
            )
        else:
            self.current_analysis.add_step(
                CalculationStepType.ERROR,
                f"Calculation failed: {message}",
                {}
            )
    
    def finalize_and_dump(self) -> Path:
        """Finalize the analysis and dump to files"""
        if not self.current_analysis:
            raise ValueError("No analysis in progress")
        
        analysis = self.current_analysis
        
        # Dump as JSON
        json_path = self.dump_dir / f"{analysis.analysis_id}_{analysis.session_type}.json"
        with open(json_path, 'w') as f:
            json.dump(analysis.to_dict(), f, indent=2)
        
        # Dump as text
        txt_path = self.dump_dir / f"{analysis.analysis_id}_{analysis.session_type}.txt"
        with open(txt_path, 'w') as f:
            f.write(analysis.to_text())
        
        # Also append to CSV log
        csv_path = self.dump_dir / "ai_target_log.csv"
        self._append_to_csv(analysis, csv_path)
        
        self.current_analysis = None
        return txt_path
    
    def _append_to_csv(self, analysis: AITargetAnalysis, csv_path: Path):
        """Append analysis summary to CSV file"""
        file_exists = csv_path.exists()
        
        with open(csv_path, 'a', newline='') as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow([
                    "Analysis ID", "Timestamp", "Session", "Track", "Vehicle Class",
                    "Target Mode", "Target Setting", "Error Margin",
                    "AI Best", "AI Worst", "AI Range",
                    "User Lap Time", "Current Ratio",
                    "Formula A", "Formula B",
                    "Target Lap Time", "Calculated Ratio", "Final Ratio",
                    "Success", "Message"
                ])
            
            writer.writerow([
                analysis.analysis_id,
                analysis.timestamp,
                analysis.session_type,
                analysis.track_name,
                analysis.vehicle_class,
                analysis.target_mode,
                analysis.target_settings.get("percentage", analysis.target_settings.get("offset_seconds", 0)),
                analysis.target_settings.get("error_margin", 0),
                analysis.ai_range.get("best", ""),
                analysis.ai_range.get("worst", ""),
                analysis.ai_range.get("range", ""),
                analysis.user_lap_time or "",
                analysis.current_ratio or "",
                analysis.formula.get("a", ""),
                analysis.formula.get("b", ""),
                analysis.target_lap_time or "",
                analysis.calculated_ratio or "",
                analysis.final_ratio or "",
                "Yes" if analysis.success else "No",
                analysis.message
            ])


class DataDumpButton:
    """Helper class to create a data dump button with analysis integration"""
    
    def __init__(self, parent, analyzer: AITargetAnalyzer = None):
        self.parent = parent
        self.analyzer = analyzer or AITargetAnalyzer()
        self.current_analysis_id = None
    
    def create_button(self, session_type: str):
        """Create a button that triggers a data dump"""
        from PyQt5.QtWidgets import QPushButton
        
        button = QPushButton("📊 Dump Analysis")
        button.setObjectName("dump_btn")
        button.setToolTip("Dump detailed analysis of current AI target calculation to file")
        button.setStyleSheet("""
            QPushButton#dump_btn {
                background-color: #9C27B0;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 6px 12px;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton#dump_btn:hover {
                background-color: #7B1FA2;
            }
        """)
        
        # Store session type
        button.session_type = session_type
        button.clicked.connect(lambda: self.on_dump_clicked(session_type))
        
        return button
    
    def on_dump_clicked(self, session_type: str):
        """Handle dump button click"""
        from PyQt5.QtWidgets import QMessageBox
        
        # Collect current state from parent
        if hasattr(self.parent, 'current_track'):
            track = self.parent.current_track
        else:
            track = "Unknown"
        
        if hasattr(self.parent, 'current_vehicle_class'):
            vehicle_class = self.parent.current_vehicle_class
        else:
            vehicle_class = "Unknown"
        
        # Get AI range
        if session_type == "qual":
            best_ai = getattr(self.parent, 'qual_best_ai', None)
            worst_ai = getattr(self.parent, 'qual_worst_ai', None)
            formula_b = getattr(self.parent, 'qual_b', 70.0)
            user_time = getattr(self.parent, 'user_qualifying_sec', None)
            current_ratio = getattr(self.parent, 'last_qual_ratio', None)
        else:
            best_ai = getattr(self.parent, 'race_best_ai', None)
            worst_ai = getattr(self.parent, 'race_worst_ai', None)
            formula_b = getattr(self.parent, 'race_b', 70.0)
            user_time = getattr(self.parent, 'user_best_lap_sec', None)
            current_ratio = getattr(self.parent, 'last_race_ratio', None)
        
        # Get target settings
        target_settings = getattr(self.parent, 'ai_target_settings', {
            "mode": "percentage",
            "percentage": 50,
            "offset_seconds": 0.0,
            "error_margin": 0.0
        })
        
        # Create analysis
        analysis_id = self.analyzer.start_analysis(session_type, track, vehicle_class)
        
        # Add input data
        self.analyzer.add_input_data(
            best_ai=best_ai,
            worst_ai=worst_ai,
            user_lap_time=user_time if user_time and user_time > 0 else None,
            current_ratio=current_ratio,
            formula_a=32.0,
            formula_b=formula_b
        )
        
        # Add target settings
        self.analyzer.add_target_settings(
            mode=target_settings.get("mode", "percentage"),
            settings=target_settings
        )
        
        # Calculate target lap time (simulate the calculation)
        if best_ai and worst_ai and best_ai > 0 and worst_ai > 0:
            target_time = self._calculate_target_time(best_ai, worst_ai, target_settings)
            self.analyzer.add_calculation_step(
                f"Calculated target lap time: {target_time:.3f}s",
                {"best_ai": best_ai, "worst_ai": worst_ai, "target_time": target_time}
            )
            
            # Calculate ratio from formula
            denominator = target_time - formula_b
            if denominator > 0:
                calculated_ratio = 32.0 / denominator
                self.analyzer.add_calculation_step(
                    f"Calculated ratio from target: R = a/(T-b) = 32.0/({target_time:.3f} - {formula_b:.2f}) = {calculated_ratio:.6f}",
                    {"calculated_ratio": calculated_ratio}
                )
                
                # Check range limits
                min_ratio, max_ratio = 0.5, 1.5
                in_range = min_ratio <= calculated_ratio <= max_ratio
                if in_range:
                    self.analyzer.add_range_check(
                        f"Ratio {calculated_ratio:.6f} is within allowed range ({min_ratio} - {max_ratio})",
                        {"in_range": True}
                    )
                else:
                    self.analyzer.add_range_check(
                        f"Ratio {calculated_ratio:.6f} is OUTSIDE allowed range ({min_ratio} - {max_ratio})",
                        {"in_range": False, "min_ratio": min_ratio, "max_ratio": max_ratio}
                    )
                
                self.analyzer.set_result(
                    target_lap_time=target_time,
                    calculated_ratio=calculated_ratio,
                    final_ratio=calculated_ratio,
                    success=in_range,
                    message=f"Analysis complete. Ratio is {'within' if in_range else 'outside'} limits."
                )
            else:
                self.analyzer.add_error(
                    f"Cannot calculate ratio: T-b = {target_time:.3f} - {formula_b:.2f} = {denominator:.3f} (must be positive)",
                    {}
                )
                self.analyzer.set_result(
                    target_lap_time=target_time,
                    calculated_ratio=None,
                    final_ratio=None,
                    success=False,
                    message="Cannot calculate ratio: T-b must be positive"
                )
        else:
            self.analyzer.add_error(
                "Insufficient AI data to calculate target",
                {"best_ai": best_ai, "worst_ai": worst_ai}
            )
            self.analyzer.set_result(
                target_lap_time=None,
                calculated_ratio=None,
                final_ratio=None,
                success=False,
                message="Insufficient AI data"
            )
        
        # Finalize and dump
        dump_path = self.analyzer.finalize_and_dump()
        
        QMessageBox.information(
            self.parent, 
            "Data Dump Complete", 
            f"Analysis dumped to:\n{dump_path}\n\n"
            f"Also saved to:\n{self.analyzer.dump_dir}/ai_target_log.csv"
        )
    
    def _calculate_target_time(self, best_ai: float, worst_ai: float, settings: Dict) -> float:
        """Calculate target lap time based on settings"""
        mode = settings.get("mode", "percentage")
        error_margin = settings.get("error_margin", 0.0)
        
        if mode == "percentage":
            pct = settings.get("percentage", 50) / 100.0
            target = best_ai + (worst_ai - best_ai) * pct
        elif mode == "faster_than_best":
            offset = settings.get("offset_seconds", 0.0)
            target = best_ai + offset
        else:
            offset = settings.get("offset_seconds", 0.0)
            target = worst_ai - offset
        
        target = target + error_margin
        target = max(best_ai, min(worst_ai + error_margin, target))
        
        return target
