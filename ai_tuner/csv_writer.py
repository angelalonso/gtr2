#!/usr/bin/env python3
# csv_writer.py - CSV output handling

import csv
import os
from debug_logger import logger

class CSVWriter:
    """Handles writing driver data to CSV files"""
    
    @staticmethod
    def write_drivers_to_csv(driver_data, fieldnames, output_file="result.csv"):
        """
        Write driver data to a CSV file
        
        Args:
            driver_data: List of driver data dictionaries
            fieldnames: List of field names for CSV header
            output_file: Output CSV filename
        
        Returns:
            True if successful, False otherwise
        """
        if not driver_data:
            logger.error("No data to write to CSV")
            return False
        
        logger.info(f"Writing {len(driver_data)} drivers to {output_file}")
        
        try:
            with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                
                for driver_info in driver_data:
                    row = {field: driver_info.get(field, '') for field in fieldnames}
                    writer.writerow(row)
            
            CSVWriter._show_success_message(output_file, len(driver_data))
            return True
            
        except Exception as e:
            logger.error(f"Error writing CSV file: {e}")
            return False
    
    @staticmethod
    def _show_success_message(output_file, num_drivers):
        """Display success message with CSV preview"""
        logger.success(f"Successfully saved {num_drivers} drivers to {output_file}")
        logger.info(f"File location: {os.path.abspath(output_file)}")
        
        # Show preview
        logger.subsection("CSV PREVIEW (first 3 rows)")
        try:
            with open(output_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()[:4]
                for line in lines:
                    print(f"  {line.rstrip()}")
        except Exception as e:
            logger.debug(f"Could not show preview: {e}")
