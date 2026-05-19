#!/usr/bin/env python3
"""
Shared track scanning utilities for Live AI Tuner
Provides consistent track discovery across all modules
"""

import logging
from pathlib import Path
from typing import List, Optional
import sqlite3

logger = logging.getLogger(__name__)


def scan_tracks_from_filesystem(base_path: Path) -> List[str]:
    """
    Scan the Locations directory for actual track folders.
    
    Args:
        base_path: GTR2 installation path
    
    Returns:
        Sorted list of track names (folder names) that contain AIW files
    """
    tracks = []
    
    if not base_path or not base_path.exists():
        logger.warning(f"Base path not found: {base_path}")
        return tracks
    
    locations_dir = base_path / "GameData" / "Locations"
    if not locations_dir.exists():
        locations_dir = base_path / "GAMEDATA" / "Locations"
    
    if not locations_dir.exists():
        logger.warning(f"Locations directory not found: {locations_dir}")
        return tracks
    
    for track_dir in locations_dir.iterdir():
        if track_dir.is_dir():
            # Check if it contains an AIW file
            for ext in ["*.AIW", "*.aiw"]:
                aiw_files = list(track_dir.glob(ext))
                if aiw_files:
                    tracks.append(track_dir.name)
                    break
    
    return sorted(tracks)


def scan_tracks_from_database(db_path: str) -> List[str]:
    """
    Scan the database for tracks that have data points.
    
    Args:
        db_path: Path to the SQLite database
    
    Returns:
        Sorted list of track names from the database
    """
    tracks = []
    
    if not Path(db_path).exists():
        return tracks
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get tracks from data_points
        cursor.execute("SELECT DISTINCT track FROM data_points ORDER BY track")
        db_tracks = [row[0] for row in cursor.fetchall()]
        
        # Also get tracks from race_sessions if data_points is empty
        if not db_tracks:
            cursor.execute("SELECT DISTINCT track_name FROM race_sessions WHERE track_name IS NOT NULL ORDER BY track_name")
            db_tracks = [row[0] for row in cursor.fetchall()]
        
        # Also check formulas table for tracks
        try:
            cursor.execute("SELECT DISTINCT track FROM formulas WHERE track IS NOT NULL ORDER BY track")
            formula_tracks = [row[0] for row in cursor.fetchall()]
            for track in formula_tracks:
                if track not in db_tracks:
                    db_tracks.append(track)
        except sqlite3.OperationalError:
            pass
        
        conn.close()
        tracks = sorted(db_tracks)
        
    except Exception as e:
        logger.error(f"Error scanning tracks from database: {e}")
    
    return tracks


def get_available_tracks(base_path: Path, db_path: str = None) -> List[str]:
    """
    Get all available tracks by merging filesystem and database results.
    Prefers filesystem tracks (actual installed tracks) but includes database tracks.
    
    Args:
        base_path: GTR2 installation path
        db_path: Optional path to database for additional tracks
    
    Returns:
        Sorted list of unique track names
    """
    if not base_path:
        return []
    
    fs_tracks = scan_tracks_from_filesystem(base_path)
    
    all_tracks = set(fs_tracks)
    
    if db_path:
        db_tracks = scan_tracks_from_database(db_path)
        all_tracks.update(db_tracks)
    
    return sorted(all_tracks)


def find_aiw_file_for_track(track_name: str, base_path: Path) -> Optional[Path]:
    """
    Find AIW file for a given track name.
    Prioritizes exact folder name match.
    
    Args:
        track_name: Name of the track
        base_path: GTR2 installation path
    
    Returns:
        Path to AIW file or None if not found
    """
    if not track_name or not base_path:
        return None
    
    locations_dir = base_path / "GameData" / "Locations"
    if not locations_dir.exists():
        locations_dir = base_path / "GAMEDATA" / "Locations"
    
    if not locations_dir.exists():
        return None
    
    track_lower = track_name.lower()
    
    # First, look for exact folder name match
    for track_dir in locations_dir.iterdir():
        if track_dir.is_dir() and track_dir.name.lower() == track_lower:
            for ext in ["*.AIW", "*.aiw"]:
                aiw_files = list(track_dir.glob(ext))
                if aiw_files:
                    return aiw_files[0]
    
    # Second, look for folder where AIW stem exactly matches track name
    for track_dir in locations_dir.iterdir():
        if track_dir.is_dir():
            for ext in ["*.AIW", "*.aiw"]:
                for aiw_file in track_dir.glob(ext):
                    if aiw_file.stem.lower() == track_lower:
                        return aiw_file
    
    # Third, look for folder name containing track name
    for track_dir in locations_dir.iterdir():
        if track_dir.is_dir() and track_lower in track_dir.name.lower():
            for ext in ["*.AIW", "*.aiw"]:
                aiw_files = list(track_dir.glob(ext))
                if aiw_files:
                    return aiw_files[0]
    
    return None
