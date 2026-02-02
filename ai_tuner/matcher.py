#!/usr/bin/env python3
# matcher.py - Driver matching logic

import os
from debug_logger import logger
# Add at the top of matcher.py
from debug_analyzer import DebugAnalyzer

class DriverMatcher:
    """Handles matching drivers from .car files with RCD data"""
    
    @staticmethod
    def match_drivers(car_drivers, driver_source_map, rcd_data, debug=False):
        """
        Match drivers from .car files with RCD data
        
        Args:
            car_drivers: Set of driver names from .car files
            driver_source_map: Dict mapping drivers to their source .car files
            rcd_data: Dict of driver data from RCD files
            debug: Enable debug output
        
        Returns:
            Tuple of (result_data, fieldnames, found_count, missing_count)
        """
        logger.section("MATCHING DRIVERS WITH RCD DATA")
        
        result_data = []
        fieldnames = ['Driver', 'Source_CAR_File', 'CAR_File_Path']
        found_drivers = []
        missing_drivers = []
        
        # Track which RCD drivers have already been used
        used_rcd_drivers = set()
        
        for driver in sorted(car_drivers):
            matched_driver = DriverMatcher._find_best_match(driver, rcd_data.keys(), used_rcd_drivers, debug)
            
            if matched_driver and matched_driver not in used_rcd_drivers:
                driver_info = rcd_data[matched_driver].copy()
                driver_info['Driver'] = matched_driver
                driver_info['Source_CAR_File'] = os.path.basename(
                    driver_source_map.get(driver, "Unknown")
                )
                driver_info['CAR_File_Path'] = driver_source_map.get(driver, "Unknown")
                
                if driver != matched_driver:
                    driver_info['Original_CAR_Name'] = driver
                
                # Update fieldnames
                for key in driver_info.keys():
                    if key not in fieldnames:
                        fieldnames.append(key)
                
                result_data.append(driver_info)
                found_drivers.append(driver)
                used_rcd_drivers.add(matched_driver)
                
                if driver == matched_driver:
                    logger.success(f"Found RCD data for: {driver}")
                else:
                    logger.success(f"Found RCD data for: {driver} -> matched as: {matched_driver}")
            elif matched_driver and matched_driver in used_rcd_drivers:
                # This RCD driver was already matched to another .car driver
                if debug:
                    logger.debug(f"RCD driver '{matched_driver}' already used, skipping duplicate for '{driver}'")
                # Still count as found but don't add duplicate
                found_drivers.append(driver)
            else:
                missing_drivers.append(driver)
                logger.error(f"No RCD data for: {driver}")
        
        DriverMatcher._show_matching_summary(car_drivers, found_drivers, missing_drivers, debug)
        
        # Debug: Show which .car files contributed to which drivers
        if debug and result_data:
            logger.subsection("DRIVER SOURCE ANALYSIS")
            for item in result_data:
                logger.debug(f"Driver: {item['Driver']}")
                logger.debug(f"  Source file: {item['Source_CAR_File']}")
                logger.debug(f"  Full path: {item.get('CAR_File_Path', 'N/A')}")
                if 'Original_CAR_Name' in item:
                    logger.debug(f"  Original name in .car: {item['Original_CAR_Name']}")
        
        if debug:
            DebugAnalyzer.analyze_duplicates(result_data, debug)

        return result_data, fieldnames, len(found_drivers), len(missing_drivers)
    
    @staticmethod
    def _find_best_match(driver_name, rcd_driver_names, used_rcd_drivers, debug=False):
        """Find the best matching driver in RCD data"""
        driver_lower = driver_name.lower()
        
        # 1. Try exact match (case-insensitive)
        for rcd_driver in rcd_driver_names:
            if rcd_driver.lower() == driver_lower and rcd_driver not in used_rcd_drivers:
                return rcd_driver
        
        # 2. Try to match by name parts
        driver_parts = driver_name.split()
        
        # If driver has multiple parts (e.g., "Matteo Bobbi")
        if len(driver_parts) > 1:
            # Try last name
            last_name = driver_parts[-1]
            for rcd_driver in rcd_driver_names:
                if rcd_driver not in used_rcd_drivers and last_name.lower() in rcd_driver.lower():
                    return rcd_driver
            
            # Try first name
            first_name = driver_parts[0]
            for rcd_driver in rcd_driver_names:
                if rcd_driver not in used_rcd_drivers and first_name.lower() in rcd_driver.lower():
                    return rcd_driver
        
        # 3. Try single word match (e.g., "Laurence")
        elif len(driver_parts) == 1:
            name_part = driver_parts[0].lower()
            for rcd_driver in rcd_driver_names:
                if rcd_driver not in used_rcd_drivers and name_part in rcd_driver.lower():
                    return rcd_driver
        
        # 4. Try any partial match
        for rcd_driver in rcd_driver_names:
            if rcd_driver not in used_rcd_drivers and (
                driver_lower in rcd_driver.lower() or 
                rcd_driver.lower() in driver_lower
            ):
                return rcd_driver
        
        return None
    
    @staticmethod
    def _show_matching_summary(car_drivers, found_drivers, missing_drivers, debug=False):
        """Show summary of matching results"""
        logger.section("MATCHING SUMMARY")
        logger.info(f"Drivers in .car files: {len(car_drivers)}")
        logger.info(f"Drivers with RCD data: {len(found_drivers)}")
        logger.info(f"Drivers missing RCD data: {len(missing_drivers)}")
        
        if missing_drivers and debug:
            logger.warning("Drivers missing RCD data:")
            for i, driver in enumerate(missing_drivers[:10], 1):
                logger.info(f"{i:3d}. {driver}")
            
            if len(missing_drivers) > 10:
                logger.info(f"... and {len(missing_drivers) - 10} more")
