#!/usr/bin/env python3
"""
AI Target Analyzer - Lightweight version for data dump and decision logging
"""

import json
import csv
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum


class CalculationStepType(Enum):
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
    step_type: CalculationStepType
    description: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AITargetAnalysis:
    analysis_id: str
    timestamp: str
    session_type: str
    track_name: str
    vehicle_class: str
    ai_range: Dict[str, Optional[float]] = field(default_factory=dict)
    user_lap_time: Optional[float] = None
    current_ratio: Optional[float] = None
    formula: Dict[str, float] = field(default_factory=dict)
    target_mode: str = "percentage"
    target_settings: Dict[str, Any] = field(default_factory=dict)
    target_lap_time: Optional[float] = None
    calculated_ratio: Optional[float] = None
    final_ratio: Optional[float] = None
    steps: List[CalculationStep] = field(default_factory=list)
    success: bool = False
    message: str = ""
    
    def add_step(self, step_type: CalculationStepType, description: str, data: Dict[str, Any] = None):
        self.steps.append(CalculationStep(step_type=step_type, description=description, data=data or {}))
    
    def to_dict(self) -> Dict[str, Any]:
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
            "steps": [{"type": s.step_type.value, "timestamp": s.timestamp, 
                      "description": s.description, "data": s.data} for s in self.steps],
            "success": self.success,
            "message": self.message
        }
    
    def to_text(self) -> str:
        lines = []
        lines.append("=" * 80)
        lines.append(f"AI TARGET ANALYSIS - {self.analysis_id}")
        lines.append(f"Timestamp: {self.timestamp}")
        lines.append(f"Session: {self.session_type.upper()} | Track: {self.track_name}")
        lines.append(f"Vehicle: {self.vehicle_class}")
        lines.append("=" * 80)
        
        if self.ai_range.get("best"):
            lines.append(f"AI Best: {self.ai_range['best']:.3f}s")
        if self.ai_range.get("worst"):
            lines.append(f"AI Worst: {self.ai_range['worst']:.3f}s")
        if self.user_lap_time:
            lines.append(f"User Lap: {self.user_lap_time:.3f}s")
        
        lines.append(f"\nTarget Mode: {self.target_mode}")
        lines.append(f"Target Settings: {self.target_settings}")
        
        if self.target_lap_time:
            lines.append(f"\nTarget Lap Time: {self.target_lap_time:.3f}s")
        if self.calculated_ratio:
            lines.append(f"Calculated Ratio: {self.calculated_ratio:.6f}")
        
        lines.append(f"\nSuccess: {'✓' if self.success else '✗'}")
        lines.append(f"Message: {self.message}")
        lines.append("=" * 80)
        
        return "\n".join(lines)


class AITargetAnalyzer:
    def __init__(self, dump_dir: str = "ai_target_dumps"):
        self.dump_dir = Path(dump_dir)
        self.dump_dir.mkdir(parents=True, exist_ok=True)
        self.current_analysis = None
    
    def start_analysis(self, session_type: str, track_name: str, vehicle_class: str) -> str:
        analysis_id = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        self.current_analysis = AITargetAnalysis(
            analysis_id=analysis_id,
            timestamp=datetime.now().isoformat(),
            session_type=session_type,
            track_name=track_name,
            vehicle_class=vehicle_class
        )
        return analysis_id
    
    def add_input_data(self, best_ai, worst_ai, user_lap_time, current_ratio, formula_a=32.0, formula_b=70.0):
        if not self.current_analysis:
            return
        self.current_analysis.ai_range = {"best": best_ai, "worst": worst_ai}
        self.current_analysis.user_lap_time = user_lap_time
        self.current_analysis.current_ratio = current_ratio
        self.current_analysis.formula = {"a": formula_a, "b": formula_b}
    
    def add_target_settings(self, mode: str, settings: Dict):
        if not self.current_analysis:
            return
        self.current_analysis.target_mode = mode
        self.current_analysis.target_settings = settings
    
    def add_calculation_step(self, description: str, data: Dict = None):
        if not self.current_analysis:
            return
        self.current_analysis.add_step(CalculationStepType.CALCULATION, description, data)
    
    def add_range_check(self, description: str, data: Dict = None):
        if not self.current_analysis:
            return
        self.current_analysis.add_step(CalculationStepType.RANGE_CHECK, description, data)
    
    def add_error(self, description: str, data: Dict = None):
        if not self.current_analysis:
            return
        self.current_analysis.add_step(CalculationStepType.ERROR, description, data)
    
    def set_result(self, target_lap_time, calculated_ratio, final_ratio, success, message):
        if not self.current_analysis:
            return
        self.current_analysis.target_lap_time = target_lap_time
        self.current_analysis.calculated_ratio = calculated_ratio
        self.current_analysis.final_ratio = final_ratio
        self.current_analysis.success = success
        self.current_analysis.message = message
    
    def finalize_and_dump(self) -> Path:
        if not self.current_analysis:
            raise ValueError("No analysis in progress")
        
        analysis = self.current_analysis
        
        json_path = self.dump_dir / f"{analysis.analysis_id}_{analysis.session_type}.json"
        with open(json_path, 'w') as f:
            json.dump(analysis.to_dict(), f, indent=2)
        
        txt_path = self.dump_dir / f"{analysis.analysis_id}_{analysis.session_type}.txt"
        with open(txt_path, 'w') as f:
            f.write(analysis.to_text())
        
        self.current_analysis = None
        return txt_path
