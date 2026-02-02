#!/usr/bin/env python3
# debug_analyzer.py - Debug analysis for duplication issues

from debug_logger import logger

class DebugAnalyzer:
    """Analyze duplication issues in matching"""
    
    @staticmethod
    def analyze_duplicates(result_data, debug=False):
        """Analyze duplicate entries in result data"""
        if not result_data:
            return
        
        # Group by driver name
        driver_groups = {}
        for i, item in enumerate(result_data):
            driver = item['Driver']
            if driver not in driver_groups:
                driver_groups[driver] = []
            driver_groups[driver].append((i, item))
        
        # Find duplicates
        duplicates = {driver: items for driver, items in driver_groups.items() if len(items) > 1}
        
        if duplicates:
            logger.section("DUPLICATE ANALYSIS")
            logger.warning(f"Found {len(duplicates)} drivers with duplicate entries")
            
            for driver, items in duplicates.items():
                logger.warning(f"\nDriver: {driver}")
                logger.warning(f"Number of duplicates: {len(items)}")
                
                for i, (index, item) in enumerate(items, 1):
                    logger.warning(f"\n  Entry {i} (index {index}):")
                    logger.warning(f"    Source file: {item.get('Source_CAR_File', 'N/A')}")
                    logger.warning(f"    Full path: {item.get('CAR_File_Path', 'N/A')}")
                    logger.warning(f"    Original name: {item.get('Original_CAR_Name', 'N/A')}")
        
        # Also check for .car files contributing to multiple drivers
        if debug:
            DebugAnalyzer._analyze_car_file_contributions(result_data)
    
    @staticmethod
    def _analyze_car_file_contributions(result_data):
        """Analyze which .car files contribute to which drivers"""
        car_file_map = {}
        
        for item in result_data:
            car_file = item.get('CAR_File_Path', 'Unknown')
            driver = item['Driver']
            
            if car_file not in car_file_map:
                car_file_map[car_file] = []
            car_file_map[car_file].append(driver)
        
        # Show .car files with multiple drivers
        multi_driver_files = {file: drivers for file, drivers in car_file_map.items() if len(drivers) > 1}
        
        if multi_driver_files:
            logger.subsection(".CAR FILES WITH MULTIPLE DRIVERS")
            for car_file, drivers in multi_driver_files.items():
                file_name = car_file.split('/')[-1] if '/' in car_file else car_file.split('\\')[-1]
                logger.debug(f"{file_name}:")
                for driver in drivers:
                    logger.debug(f"  - {driver}")
