#!/usr/bin/env python3
"""
Shared AIW file utilities for Live AI Tuner
Provides consistent AIW file finding across all modules
"""

import re
import shutil
import logging
from pathlib import Path
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


def find_aiw_file_from_path(relative_path: str, base_path: Path) -> Optional[Path]:
    """
    Find AIW file from a relative path (like from raceresults.txt).
    Handles case-insensitive paths and different path separators.
    
    Args:
        relative_path: Path like "GAMEDATA/LOCATIONS/Testtrack2/Testtrack2.AIW"
        base_path: Base GTR2 installation path
    
    Returns:
        Full Path to AIW file or None if not found
    """
    if not relative_path or not base_path:
        logger.error(f"find_aiw_file_from_path: missing params - relative_path={relative_path}, base_path={base_path}")
        return None
    
    normalized = str(relative_path).replace('\\', '/')
    logger.info(f"find_aiw_file_from_path: looking for '{normalized}'")
    logger.info(f"  Base path: {base_path}")
    
    full_path = base_path / normalized
    if full_path.exists():
        logger.info(f"Found AIW via exact path: {full_path}")
        return full_path
    else:
        logger.debug(f"Exact path not found: {full_path}")
    
    path_variants = []
    
    if 'GAMEDATA' in normalized:
        path_variants.append(normalized.replace('GAMEDATA', 'GameData'))
    if 'gamedata' in normalized:
        path_variants.append(normalized.replace('gamedata', 'GameData'))
    if 'GameData' in normalized:
        path_variants.append(normalized.replace('GameData', 'GAMEDATA'))
    
    if 'LOCATIONS' in normalized:
        path_variants.append(normalized.replace('LOCATIONS', 'Locations'))
    if 'Locations' in normalized:
        path_variants.append(normalized.replace('Locations', 'LOCATIONS'))
    
    for variant in path_variants:
        test_path = base_path / variant
        if test_path.exists():
            logger.info(f"Found AIW via path variant: {test_path}")
            return test_path
        else:
            logger.debug(f"Path variant not found: {test_path}")
    
    path_parts = normalized.split('/')
    if path_parts and path_parts[0] == '':
        path_parts = path_parts[1:]
    
    current_path = base_path
    
    for i, part in enumerate(path_parts):
        if i == len(path_parts) - 1:
            if current_path.exists() and current_path.is_dir():
                found = False
                for file_path in current_path.iterdir():
                    if file_path.is_file() and file_path.name.lower() == part.lower():
                        logger.info(f"Found AIW via case-insensitive filename: {file_path}")
                        return file_path
                if not found:
                    logger.debug(f"No file matching '{part}' found in {current_path}")
        else:
            next_path = None
            if current_path.exists() and current_path.is_dir():
                for item in current_path.iterdir():
                    if item.is_dir() and item.name.lower() == part.lower():
                        next_path = item
                        break
            
            if next_path:
                current_path = next_path
                logger.debug(f"Found directory '{part}' as '{current_path.name}'")
            else:
                logger.debug(f"Could not find directory '{part}' in {current_path}")
                current_path = None
                break
    
    if current_path and current_path.exists() and current_path.is_dir():
        expected_filename = path_parts[-1] if path_parts else ""
        expected_stem = Path(expected_filename).stem
        for ext in ['.AIW', '.aiw']:
            test_name = expected_stem + ext
            for file_path in current_path.iterdir():
                if file_path.is_file() and file_path.name.lower() == test_name.lower():
                    logger.info(f"Found AIW via case-insensitive filename with extension: {file_path}")
                    return file_path
    
    filename = Path(normalized).name
    locations_candidates = [
        base_path / "GameData" / "Locations",
        base_path / "GAMEDATA" / "Locations",
    ]
    
    for locations_dir in locations_candidates:
        if locations_dir.exists():
            logger.debug(f"Searching for '{filename}' in {locations_dir}")
            for aiw_file in locations_dir.rglob(filename):
                if aiw_file.name == filename:
                    logger.info(f"Found AIW via exact filename search: {aiw_file}")
                    return aiw_file
            for aiw_file in locations_dir.rglob(filename.lower()):
                if aiw_file.name.lower() == filename.lower():
                    logger.info(f"Found AIW via case-insensitive filename search: {aiw_file}")
                    return aiw_file
    
    logger.warning(f"AIW file NOT found for path: {relative_path}")
    logger.warning(f"  Normalized path: {normalized}")
    logger.warning(f"  Base path: {base_path}")
    logger.warning(f"  Expected full path: {base_path / normalized}")
    return None


def find_aiw_file_by_track(track_name: str, base_path: Path) -> Optional[Path]:
    """
    Find AIW file by track name (fallback when no relative path available).
    
    Args:
        track_name: Name of the track (e.g., "Donington", "Monza")
        base_path: Base GTR2 installation path
    
    Returns:
        Full Path to AIW file or None if not found
    """
    if not track_name or not base_path:
        logger.error(f"find_aiw_file_by_track: missing params - track_name={track_name}, base_path={base_path}")
        return None
    
    logger.info(f"find_aiw_file_by_track: looking for track '{track_name}'")
    
    locations_candidates = [
        base_path / "GameData" / "Locations",
        base_path / "GAMEDATA" / "Locations",
    ]
    
    locations_dir = None
    for candidate in locations_candidates:
        if candidate.exists():
            locations_dir = candidate
            logger.debug(f"Found Locations directory: {locations_dir}")
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
                    logger.info(f"Found AIW via exact folder match: {aiw_files[0]}")
                    return aiw_files[0]
            logger.debug(f"Folder '{track_dir.name}' matched but no AIW file found")
    
    for ext in ["*.AIW", "*.aiw"]:
        for aiw_file in locations_dir.rglob(ext):
            if aiw_file.stem.lower() == track_lower:
                logger.info(f"Found AIW via exact stem match: {aiw_file}")
                return aiw_file
    
    logger.warning(f"AIW file NOT found for track: {track_name}")
    logger.warning(f"  Locations directory: {locations_dir}")
    logger.warning(f"  Available folders in Locations: {[d.name for d in locations_dir.iterdir() if d.is_dir()]}")
    return None


def update_aiw_ratio(aiw_path: Path, ratio_name: str, new_ratio: float, backup_dir: Optional[Path] = None) -> bool:
    """
    Update a ratio in the AIW file.
    
    Args:
        aiw_path: Path to the AIW file
        ratio_name: "QualRatio" or "RaceRatio"
        new_ratio: New ratio value
        backup_dir: Directory to store backups (if None, no backup created)
    
    Returns:
        True if successful, False otherwise
    """
    try:
        if not aiw_path:
            logger.error(f"update_aiw_ratio: aiw_path is None")
            return False
        
        if not aiw_path.exists():
            logger.error(f"update_aiw_ratio: AIW file not found: {aiw_path}")
            return False
        
        logger.info(f"update_aiw_ratio: updating {ratio_name} to {new_ratio:.6f} in {aiw_path}")
        
        if backup_dir:
            backup_dir = Path(backup_dir)
            backup_dir.mkdir(parents=True, exist_ok=True)
            backup_path = backup_dir / f"{aiw_path.stem}_ORIGINAL{aiw_path.suffix}"
            if not backup_path.exists():
                shutil.copy2(aiw_path, backup_path)
                logger.info(f"Created backup: {backup_path}")
            else:
                logger.info(f"Original backup exists: {backup_path}")
        else:
            logger.error(f"{backup_dir} does not exist")
        
        raw = aiw_path.read_bytes()
        content = raw.replace(b"\x00", b"").decode("utf-8", errors="ignore")
        
        pattern = rf'({re.escape(ratio_name)}\s*=\s*\(?)\s*[0-9.eE+-]+\s*(\)?)'
        new_content, count = re.subn(
            pattern,
            lambda m: f"{m.group(1)}{new_ratio:.6f}{m.group(2)}",
            content,
            flags=re.IGNORECASE
        )
        
        if count > 0:
            aiw_path.write_bytes(new_content.encode("utf-8", errors="ignore"))
            logger.info(f"Updated {ratio_name} to {new_ratio:.6f} in {aiw_path.name}")
            return True
        else:
            logger.warning(f"Could not find {ratio_name} pattern in {aiw_path.name}")
            return False
            
    except Exception as e:
        logger.error(f"Error updating AIW ratio: {e}")
        return False


def ensure_aiw_has_ratios(aiw_path: Path, backup_dir: Optional[Path] = None) -> bool:
    """
    Ensure AIW file has both QualRatio and RaceRatio entries.
    Adds them with default values if missing.
    
    Args:
        aiw_path: Path to the AIW file
        backup_dir: Directory to store backups
    
    Returns:
        True if successful, False otherwise
    """
    try:
        if not aiw_path:
            logger.error(f"ensure_aiw_has_ratios: aiw_path is None")
            return False
        
        if not aiw_path.exists():
            logger.error(f"ensure_aiw_has_ratios: AIW file not found: {aiw_path}")
            return False
        
        raw = aiw_path.read_bytes()
        content = raw.replace(b"\x00", b"").decode("utf-8", errors="ignore")
        
        has_qual = re.search(r'QualRatio\s*=', content, re.IGNORECASE) is not None
        has_race = re.search(r'RaceRatio\s*=', content, re.IGNORECASE) is not None
        
        if has_qual and has_race:
            logger.debug(f"AIW {aiw_path.name} already has both ratios")
            return True
        
        logger.info(f"AIW {aiw_path.name} missing ratios: qual={has_qual}, race={has_race}")
        
        if backup_dir:
            backup_dir = Path(backup_dir)
            backup_dir.mkdir(parents=True, exist_ok=True)
            backup_path = backup_dir / f"{aiw_path.stem}_ORIGINAL{aiw_path.suffix}"
            if not backup_path.exists():
                shutil.copy2(aiw_path, backup_path)
                logger.info(f"------------------- Created backup before adding ratios: {backup_path}")
        
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
