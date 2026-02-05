#!/usr/bin/env python3
# processor.py - Main processing logic

import os
from debug_logger import logger

class DriverProcessor:
    """Main driver data processor"""
    
    def __init__(self, install_folder, teams_folder, debug_mode=False):
        self.install_folder = os.path.abspath(install_folder)
        self.teams_folder = os.path.abspath(teams_folder)
        self.debug_mode = debug_mode
        logger.debug_mode = debug_mode
        
        # Initialize handlers
        self.rcd_handler = None
    
    def process(self):
        """Main processing pipeline"""
        # Import here to avoid circular imports
        from car_handler import CarHandler
        from rcd_handler import RcdHandler
        from matcher import DriverMatcher
        
        logger.section("GTR2 DRIVER DATA EXTRACTION STARTED", width=80)
        logger.info(f"GTR2 Install: {self.install_folder}")
        logger.info(f"Teams folder: {self.teams_folder}")
        
        # Step 1: Process .car files
        car_result = self._process_car_files(CarHandler)
        if not car_result:
            return None, None
        
        car_drivers, driver_source_map = car_result
        
        # Step 2: Process .rcd files
        rcd_data = self._process_rcd_files(RcdHandler)
        if not rcd_data:
            return None, None
        
        # Step 3: Match drivers
        match_result = DriverMatcher.match_drivers(
            car_drivers, driver_source_map, rcd_data, self.debug_mode
        )
        
        result_data, fieldnames, found_count, missing_count = match_result
        
        if found_count == 0:
            logger.error("No drivers matched with RCD data")
            return None, None
        
        return result_data, fieldnames
    
    def _process_car_files(self, CarHandler):
        """Process .car files to extract drivers"""
        # Find .car files
        car_files = CarHandler.find_car_files(self.teams_folder, self.debug_mode)
        if not car_files:
            logger.error("No .car files found. Cannot continue.")
            return None
        
        # Extract drivers from .car files
        car_drivers, driver_source_map = CarHandler.extract_drivers(car_files, self.debug_mode)
        if not car_drivers:
            logger.error("No drivers found in .car files. Cannot continue.")
            return None
        
        return car_drivers, driver_source_map
    
    def _process_rcd_files(self, RcdHandler):
        """Process .rcd files to extract driver data"""
        # Create RCD handler instance
        self.rcd_handler = RcdHandler(self.install_folder, self.teams_folder)
        
        # Get RCD folders for checking
        rcd_folders = self.rcd_handler.get_search_folders()
        
        # Check RCD folders
        logger.section("CHECKING RCD FOLDERS")
        for folder in rcd_folders:
            if os.path.exists(folder):
                logger.success(f"Folder exists: {folder}")
            else:
                logger.warning(f"Folder does not exist: {folder}")
        
        # Find and parse .rcd files in one step
        rcd_data = self.rcd_handler.parse_rcd_files(debug=self.debug_mode)
        
        if not rcd_data:
            logger.error("No driver data found in RCD files. Cannot continue.")
            return None
        
        return rcd_data
