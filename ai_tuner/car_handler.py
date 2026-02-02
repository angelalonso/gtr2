#!/usr/bin/env python3
# car_handler.py - .car file handling (finder + parser)

import os
import re
from config import CAR_EXTENSIONS, DRIVER_PATTERNS, ENCODINGS
from debug_logger import logger

class CarHandler:
    """Handles all .car file operations"""
    
    @staticmethod
    def find_car_files(folder_path, debug=False):
        """Find all .car files recursively in a folder"""
        if not os.path.exists(folder_path):
            logger.error(f"Teams folder does not exist: {folder_path}")
            return []
        
        logger.section("SEARCHING FOR .CAR FILES")
        logger.info(f"Search root: {folder_path}")
        
        found_files = []
        total_dirs = 0
        total_files = 0
        
        for root, dirs, files in os.walk(folder_path):
            total_dirs += 1
            
            if debug:
                logger.debug(f"Scanning directory: {os.path.relpath(root, folder_path)}")
            
            for file in files:
                total_files += 1
                if any(file.lower().endswith(ext) for ext in CAR_EXTENSIONS):
                    full_path = os.path.join(root, file)
                    found_files.append(full_path)
                    
                    if debug:
                        logger.debug(f"Found .car file: {file}")
        
        logger.info(f"Directories scanned: {total_dirs}")
        logger.info(f"Files scanned: {total_files}")
        logger.info(f"Total .car files found: {len(found_files)}")
        
        if debug and found_files:
            logger.subsection("FOUND .CAR FILES")
            for i, file_path in enumerate(found_files, 1):
                rel_path = os.path.relpath(file_path, folder_path)
                logger.debug(f"{i:3d}. {rel_path}")
        
        return found_files
    
    @staticmethod
    def extract_drivers(car_file_paths, debug=False):
        """Extract driver names from multiple .car files"""
        all_drivers = set()
        driver_source_map = {}
        
        logger.section("EXTRACTING DRIVERS FROM .CAR FILES")
        
        for i, car_file_path in enumerate(car_file_paths, 1):
            logger.progress(i, len(car_file_paths), f"Processing: {os.path.basename(car_file_path)}")
            
            drivers = CarHandler._extract_drivers_from_file(car_file_path, debug)
            
            for driver in drivers:
                clean_driver = CarHandler._clean_driver_name(driver)
                if not clean_driver:
                    continue
                    
                if clean_driver not in all_drivers:
                    if debug:
                        logger.debug(f"New driver found: '{clean_driver}' (original: '{driver}') from {os.path.basename(car_file_path)}")
                all_drivers.add(clean_driver)
                driver_source_map[clean_driver] = car_file_path
            
            if debug and drivers:
                logger.debug(f"Found {len(drivers)} driver(s) in this file:")
                for driver in drivers:
                    clean_driver = CarHandler._clean_driver_name(driver)
                    logger.debug(f"  - '{driver}' -> '{clean_driver}'")
        
        logger.info(f"Total unique drivers found: {len(all_drivers)}")
        
        if debug and all_drivers:
            logger.subsection("DRIVERS FOUND IN .CAR FILES")
            for i, driver in enumerate(sorted(all_drivers), 1):
                source_file = os.path.basename(driver_source_map.get(driver, "Unknown"))
                logger.info(f"{i:3d}. {driver:<30} (from: {source_file})")
        
        return all_drivers, driver_source_map
    
    @staticmethod
    def _extract_drivers_from_file(car_file_path, debug=False):
        """Extract driver names from a single .car file"""
        content = CarHandler._read_file_with_fallback(car_file_path, debug)
        if not content:
            return set()
        
        drivers = set()
        for pattern in DRIVER_PATTERNS:
            matches = re.findall(pattern, content, re.IGNORECASE)
            for driver in matches:
                if driver:
                    drivers.add(driver)
        
        return drivers
    
    @staticmethod
    def _read_file_with_fallback(file_path, debug=False):
        """Try to read a file with multiple encodings"""
        for encoding in ENCODINGS:
            try:
                with open(file_path, 'r', encoding=encoding, errors='ignore') as f:
                    content = f.read()
                return content
            except Exception:
                continue
        
        logger.error(f"Failed to read file: {file_path}")
        return None
    
    @staticmethod
    def _clean_driver_name(driver_name):
        """Clean up driver names"""
        if not driver_name:
            return ""
        
        driver_name = driver_name.strip('"\'')
        driver_name = driver_name.replace('"', '')
        driver_name = driver_name.strip()
        
        if driver_name.startswith('"'):
            driver_name = driver_name[1:].strip()
        
        return driver_name
