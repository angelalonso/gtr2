#!/usr/bin/env python3
"""
Shared components and helper functions for the main window
"""

import logging
import re
import shutil
from pathlib import Path
from typing import Optional, Tuple, List, Any

from PyQt5.QtWidgets import QMessageBox, QWidget
from PyQt5.QtCore import Qt

from core_config import get_base_path, update_base_path
from gui_base_path_dialog import BasePathSelectionDialog

logger = logging.getLogger(__name__)


def clamp_ratio(ratio: float, min_ratio: float, max_ratio: float) -> float:
    """Clamp ratio to within min and max limits"""
    if ratio < min_ratio:
        return min_ratio
    if ratio > max_ratio:
        return max_ratio
    return ratio


def show_clamp_warning(parent, ratio_name: str, original_ratio: float, clamped_ratio: float, min_ratio: float, max_ratio: float):
    """Show a formatted warning message when ratio is clamped"""
    if clamped_ratio < original_ratio:
        # Hit upper limit (ratio was too high, clamped down to max_ratio)
        message = (
            f"WARNING: {ratio_name} = {original_ratio:.6f} exceeded the maximum allowed value of {max_ratio:.3f}.\n\n"
            f"The ratio has been clamped to {clamped_ratio:.6f}.\n\n"
            f"Consider setting a HIGHER AI Difficulty Level in GTR2.\n"
            f"Move the AI Difficulty slider in small increments (e.g., 100% -> 101% -> 102%).\n\n"
            f"This will make the AI drive faster,\n"
            f"which allows the ratio to stay within the valid range."
        )
    else:
        # Hit lower limit (ratio was too low, clamped up to min_ratio)
        message = (
            f"WARNING: {ratio_name} = {original_ratio:.6f} fell below the minimum allowed value of {min_ratio:.3f}.\n\n"
            f"The ratio has been clamped to {clamped_ratio:.6f}.\n\n"
            f"To fix this, set a LOWER AI Difficulty Level in GTR2.\n"
            f"Move the AI Difficulty slider in small increments (e.g., 110% -> 109% -> 108%).\n\n"
            f"This will make the AI drive slower,\n"
            f"which allows the ratio to stay within the valid range."
        )
    
    msg_box = QMessageBox(parent)
    msg_box.setWindowTitle(f"{ratio_name} Adjusted")
    msg_box.setIcon(QMessageBox.Warning)
    msg_box.setText(message)
    msg_box.setStyleSheet("""
        QMessageBox {
            background-color: #2b2b2b;
        }
        QMessageBox QLabel {
            color: #FFCC00;
            font-size: 12px;
            min-width: 500px;
        }
        QPushButton {
            background-color: #4CAF50;
            color: white;
            border: none;
            border-radius: 4px;
            padding: 8px 16px;
            font-weight: bold;
        }
        QPushButton:hover {
            background-color: #45a049;
        }
    """)
    msg_box.exec_()


class AIWFileManager:
    """Manages AIW file operations for the main window"""
    
    def __init__(self, config_file: str, db_path: str):
        self.config_file = config_file
        self.db_path = db_path
        self.aiw_accessible = True
        self.last_aiw_error = None
    
    def find_aiw_file(self, track_name: str = None) -> Optional[Path]:
        import re
        base_path = get_base_path(self.config_file)
        if not base_path:
            logger.error("No base path configured")
            return None
        
        track_name = track_name or getattr(self, 'current_track', None)
        if not track_name:
            logger.error("No track selected")
            return None
        
        locations_candidates = [
            base_path / "GameData" / "Locations",
            base_path / "GAMEDATA" / "Locations",
            base_path / "gamedata" / "locations",
        ]
        
        locations_dir = None
        for candidate in locations_candidates:
            if candidate.exists():
                locations_dir = candidate
                break
        
        if not locations_dir:
            logger.error(f"Locations directory not found. Tried: {locations_candidates}")
            return None
        
        track_lower = track_name.lower()
        for track_dir in locations_dir.iterdir():
            if track_dir.is_dir() and track_dir.name.lower() == track_lower:
                for ext in ["*.AIW", "*.aiw"]:
                    aiw_files = list(track_dir.glob(ext))
                    if aiw_files:
                        logger.debug(f"Found AIW file via folder match: {aiw_files[0]}")
                        return aiw_files[0]
        
        for ext in ["*.AIW", "*.aiw"]:
            for aiw_file in locations_dir.rglob(ext):
                aiw_stem = re.sub(r'^\d+', '', aiw_file.stem.lower())
                if aiw_stem == track_lower:
                    logger.debug(f"Found AIW file via stem match: {aiw_file}")
                    return aiw_file
        
        import re
        for track_dir in locations_dir.iterdir():
            if track_dir.is_dir():
                dir_lower = track_dir.name.lower()
                if re.search(r'\b' + re.escape(track_lower) + r'\b', dir_lower):
                    for ext in ["*.AIW", "*.aiw"]:
                        aiw_files = list(track_dir.glob(ext))
                        if aiw_files:
                            logger.debug(f"Found AIW file via folder word match: {aiw_files[0]}")
                            return aiw_files[0]
        
        logger.warning(f"AIW file not found for track: {track_name}")
        return None
    
    def read_aiw_ratios(self, aiw_path: Path) -> tuple:
        qual_ratio = None
        race_ratio = None
        
        try:
            raw = aiw_path.read_bytes()
            content = raw.replace(b"\x00", b"").decode("utf-8", errors="ignore")
            
            waypoint_match = re.search(r'\[Waypoint\](.*?)(?=\[|$)', content, re.DOTALL | re.IGNORECASE)
            if waypoint_match:
                section = waypoint_match.group(1)
                
                qual_match = re.search(r'QualRatio\s*=\s*\(?([\d.eE+-]+)\)?', section, re.IGNORECASE)
                if qual_match:
                    qual_ratio = float(qual_match.group(1))
                    logger.debug(f"Read QualRatio: {qual_ratio}")
                
                race_match = re.search(r'RaceRatio\s*=\s*\(?([\d.eE+-]+)\)?', section, re.IGNORECASE)
                if race_match:
                    race_ratio = float(race_match.group(1))
                    logger.debug(f"Read RaceRatio: {race_ratio}")
            
            return qual_ratio, race_ratio
            
        except Exception as e:
            logger.error(f"Error reading AIW ratios: {e}")
            return None, None
    
    def ensure_aiw_has_ratios(self, aiw_path: Path) -> bool:
        try:
            raw = aiw_path.read_bytes()
            content = raw.replace(b"\x00", b"").decode("utf-8", errors="ignore")
            
            has_qual = re.search(r'QualRatio\s*=', content, re.IGNORECASE) is not None
            has_race = re.search(r'RaceRatio\s*=', content, re.IGNORECASE) is not None
            
            if has_qual and has_race:
                return True
            
            backup_dir = Path(self.db_path).parent / "aiw_backups"
            backup_dir.mkdir(parents=True, exist_ok=True)
            backup_path = backup_dir / f"{aiw_path.stem}_ORIGINAL{aiw_path.suffix}"
            if not backup_path.exists():
                shutil.copy2(aiw_path, backup_path)
                logger.info(f"Created backup before adding ratios: {backup_path}")
            
            waypoint_pattern = re.compile(r'(\[Waypoint\](.*?)(?=\[|$))', re.DOTALL | re.IGNORECASE)
            waypoint_match = waypoint_pattern.search(content)
            
            if not waypoint_match:
                logger.warning(f"Cannot find Waypoint section in {aiw_path.name}")
                return False
            
            waypoint_section = waypoint_match.group(1)
            waypoint_start = waypoint_match.start()
            
            insert_pos = waypoint_start + len("[Waypoint]")
            
            best_adjust_match = re.search(r'BestAdjust\s*=', waypoint_section, re.IGNORECASE)
            if best_adjust_match:
                line_end = waypoint_section.find('\n', best_adjust_match.end())
                if line_end != -1:
                    insert_pos = waypoint_start + line_end + 1
            
            lines_to_insert = []
            if not has_qual:
                lines_to_insert.append("QualRatio = 1.000000")
            if not has_race:
                lines_to_insert.append("RaceRatio = 1.000000")
            
            if lines_to_insert:
                insert_text = "\n" + "\n".join(lines_to_insert)
                new_content = content[:insert_pos] + insert_text + content[insert_pos:]
                aiw_path.write_bytes(new_content.encode("utf-8", errors="ignore"))
                logger.info(f"Added missing ratios to {aiw_path.name}: {lines_to_insert}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error ensuring AIW has ratios: {e}")
            return False
    
    def check_aiw_accessible(self, parent, track: str, session_type: str) -> bool:
        aiw_path = self.find_aiw_file(track)
        if not aiw_path or not aiw_path.exists():
            self.aiw_accessible = False
            self.show_aiw_error_and_accessible(parent, f"update {session_type.upper()} ratio", 
                f"AIW file for track '{track}' not found in GameData/Locations/")
            return False
        self.aiw_accessible = True
        return True
    
    def show_aiw_error_and_accessible(self, parent, operation: str, error_detail: str = None):
        msg_box = QMessageBox(parent)
        msg_box.setWindowTitle("AIW File Not Found")
        msg_box.setIcon(QMessageBox.Critical)
        
        error_text = (
            f"Cannot {operation} because the AIW file could not be found.\n\n"
            f"This usually means the GTR2 base path is not configured correctly.\n\n"
        )
        
        if error_detail:
            error_text += f"Details: {error_detail}\n\n"
        
        error_text += (
            f"Please configure the correct GTR2 installation folder "
            f"(the one containing GameData and UserData directories)."
        )
        
        msg_box.setText(error_text)
        msg_box.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)
        msg_box.button(QMessageBox.Ok).setText("Configure GTR2 Path")
        
        result = msg_box.exec_()
        
        if result == QMessageBox.Ok:
            dialog = BasePathSelectionDialog(parent)
            if dialog.exec_() == QDialog.Accepted and dialog.selected_path:
                update_base_path(dialog.selected_path, self.config_file)
                self.aiw_accessible = True
                return True
        return False


class TargetIndicator(QWidget):
    """Target indicator widget for the status bar"""
    
    def __init__(self, parent, settings_getter):
        super().__init__(parent)
        self.parent = parent
        self.settings_getter = settings_getter
        self.setup_ui()
    
    def setup_ui(self):
        from PyQt5.QtWidgets import QHBoxLayout, QLabel, QPushButton, QFrame
        
        target_layout = QHBoxLayout(self)
        target_layout.setContentsMargins(5, 0, 10, 0)
        target_layout.setSpacing(8)
        
        target_label = QLabel("AI Target:")
        target_label.setStyleSheet("color: #FFA500; font-weight: bold; font-size: 11px;")
        target_layout.addWidget(target_label)
        
        self.target_display = QLabel("Not set")
        self.target_display.setStyleSheet("color: #4CAF50; font-family: monospace; font-size: 11px;")
        target_layout.addWidget(self.target_display)
        
        sep = QFrame()
        sep.setFrameShape(QFrame.VLine)
        sep.setStyleSheet("color: #555;")
        target_layout.addWidget(sep)
        
        target_btn = QPushButton("Configure")
        target_btn.setStyleSheet("""
            QPushButton {
                background-color: #FF9800;
                color: white;
                padding: 2px 8px;
                font-size: 10px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #F57C00;
            }
        """)
        target_btn.setFixedWidth(70)
        target_btn.clicked.connect(self.open_settings)
        target_layout.addWidget(target_btn)
        
        target_layout.addStretch()
    
    def open_settings(self):
        if hasattr(self.parent, 'open_advanced_settings_to_target'):
            self.parent.open_advanced_settings_to_target()
    
    def update_display(self):
        settings = self.settings_getter()
        mode = settings.get("mode", "percentage")
        error_margin = settings.get("error_margin", 0)
        if mode == "percentage":
            pct = settings.get("percentage", 50)
            if error_margin > 0:
                self.target_display.setText(f"{pct}% (+{error_margin:.2f}s)")
            else:
                self.target_display.setText(f"{pct}%")
        elif mode == "faster_than_best":
            offset = settings.get("offset_seconds", 0)
            if error_margin > 0:
                self.target_display.setText(f"{offset:+.2f}s (+{error_margin:.2f}s)")
            else:
                self.target_display.setText(f"{offset:+.2f}s")
        else:
            offset = settings.get("offset_seconds", 0)
            if error_margin > 0:
                self.target_display.setText(f"{offset:+.2f}s (+{error_margin:.2f}s)")
            else:
                self.target_display.setText(f"{offset:+.2f}s")
