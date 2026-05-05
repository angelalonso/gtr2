#!/usr/bin/env python3
"""
Shared vehicle scanning utilities for Live AI Tuner
Provides consistent vehicle discovery across pre-run checks and data management
"""

import re
import json
import logging
from pathlib import Path
from typing import Set, Optional, Callable, Tuple

logger = logging.getLogger(__name__)


def scan_vehicles_from_gtr2(gtr2_path: Path, progress_callback: Optional[Callable] = None) -> Set[str]:
    """
    Scan GTR2 installation for all vehicle names from .car files.
    
    Args:
        gtr2_path: Path to GTR2 installation root (containing GameData/)
        progress_callback: Optional callback(current, total, message)
    
    Returns:
        Set of vehicle names found
    """
    vehicles = set()
    
    teams_dir = gtr2_path / "GameData" / "Teams"
    
    if not teams_dir.exists():
        logger.error(f"Teams directory not found: {teams_dir}")
        return vehicles
    
    car_files = []
    for ext in ['*.car', '*.CAR']:
        car_files.extend(teams_dir.rglob(ext))
    
    if not car_files:
        logger.warning(f"No .car files found in {teams_dir}")
        return vehicles
    
    total_files = len(car_files)
    logger.info(f"Scanning {total_files} car files for vehicle names...")
    
    for i, car_file in enumerate(car_files):
        if progress_callback:
            progress_callback(i + 1, total_files, f"Scanning: {car_file.name}")
        
        try:
            content = car_file.read_text(encoding='utf-8', errors='ignore')
            
            pattern = r'Description\s*=\s*"([^"]*)"'
            matches = re.findall(pattern, content, re.IGNORECASE)
            
            for description in matches:
                if description and description.strip():
                    vehicle = description.strip()
                    vehicles.add(vehicle)
            
            pattern_no_quotes = r'Description\s*=\s*([^\n\r]+)'
            matches_no_quotes = re.findall(pattern_no_quotes, content, re.IGNORECASE)
            
            for description in matches_no_quotes:
                if description and description.strip():
                    vehicle = description.strip().strip('"')
                    if vehicle:
                        vehicles.add(vehicle)
                        
        except Exception as e:
            logger.warning(f"Error reading {car_file}: {e}")
    
    return vehicles


def load_vehicle_classes(classes_path: Path) -> dict:
    """
    Load vehicle classes from JSON file.
    
    Args:
        classes_path: Path to vehicle_classes.json
    
    Returns:
        Dictionary of classes with their vehicles
    """
    if not classes_path.exists():
        return {}
    
    try:
        with open(classes_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading vehicle classes: {e}")
        return {}


def get_all_defined_vehicles(classes_data: dict) -> Set[str]:
    """
    Extract all vehicle names from vehicle_classes.json.
    
    Args:
        classes_data: Dictionary from load_vehicle_classes()
    
    Returns:
        Set of all vehicle names defined in the file
    """
    vehicles = set()
    for class_name, class_data in classes_data.items():
        if isinstance(class_data, dict) and 'vehicles' in class_data:
            vehicles.update(class_data['vehicles'])
        elif isinstance(class_data, list):
            vehicles.update(class_data)
    return vehicles


def find_missing_vehicles(gtr2_path: Path, classes_path: Path, progress_callback: Optional[Callable] = None) -> Tuple[Set[str], Set[str], Set[str]]:
    """
    Find vehicles in GTR2 that are not defined in vehicle_classes.json.
    
    Args:
        gtr2_path: Path to GTR2 installation
        classes_path: Path to vehicle_classes.json
        progress_callback: Optional progress callback
    
    Returns:
        Tuple of (all_vehicles, defined_vehicles, missing_vehicles)
    """
    all_vehicles = scan_vehicles_from_gtr2(gtr2_path, progress_callback)
    classes_data = load_vehicle_classes(classes_path)
    defined_vehicles = get_all_defined_vehicles(classes_data)
    
    missing_vehicles = all_vehicles - defined_vehicles
    
    return all_vehicles, defined_vehicles, missing_vehicles
