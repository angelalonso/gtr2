#!/usr/bin/env python3
# rcd_updater.py - Update RCD files with edited values

import os
import shutil
from datetime import datetime
from debug_logger import logger

class RcdUpdater:
    """Update RCD files with edited values from CSV"""
    
    def __init__(self, install_folder, teams_folder):
        self.install_folder = install_folder
        self.teams_folder = teams_folder
        self.backup_folder = None
    
    def update_rcd_files(self, csv_data, fieldnames, create_backup=True):
        """
        Update RCD files with values from CSV data
        
        Args:
            csv_data: List of dictionaries with driver data
            fieldnames: List of field names
            create_backup: Whether to create backup of original files
        
        Returns:
            Tuple of (success_count, error_count, backup_path)
        """
        logger.section("UPDATING RCD FILES")
        
        # Create backup folder if needed
        backup_path = None
        if create_backup:
            backup_path = self.create_backup_folder()
            if backup_path:
                logger.info(f"Backup folder created: {backup_path}")
        
        # Track statistics
        success_count = 0
        error_count = 0
        updated_drivers = []
        
        # Process each driver
        for driver_data in csv_data:
            driver_name = driver_data.get('Driver', '')
            if not driver_name:
                continue
            
            # Find RCD file for this driver
            rcd_file_path = self.find_rcd_file_for_driver(driver_name)
            
            if rcd_file_path:
                # Create backup if requested
                if backup_path:
                    self.backup_rcd_file(rcd_file_path, backup_path, driver_name)
                
                # Update RCD file
                if self.update_single_rcd_file(rcd_file_path, driver_data, fieldnames):
                    success_count += 1
                    updated_drivers.append(driver_name)
                    logger.success(f"Updated: {driver_name} -> {os.path.basename(rcd_file_path)}")
                else:
                    error_count += 1
                    logger.error(f"Failed to update: {driver_name}")
            else:
                error_count += 1
                logger.error(f"RCD file not found for: {driver_name}")
        
        # Summary
        logger.section("UPDATE SUMMARY")
        logger.info(f"Successfully updated: {success_count} drivers")
        logger.info(f"Failed to update: {error_count} drivers")
        
        if updated_drivers:
            logger.subsection("UPDATED DRIVERS")
            for i, driver in enumerate(updated_drivers[:20], 1):
                logger.info(f"{i:3d}. {driver}")
            if len(updated_drivers) > 20:
                logger.info(f"... and {len(updated_drivers) - 20} more")
        
        return success_count, error_count, backup_path
    
    def create_backup_folder(self):
        """Create a backup folder with timestamp"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_folder = f"rcd_backup_{timestamp}"
        
        try:
            os.makedirs(backup_folder, exist_ok=True)
            self.backup_folder = backup_folder
            return os.path.abspath(backup_folder)
        except Exception as e:
            logger.error(f"Failed to create backup folder: {e}")
            return None
    
    def backup_rcd_file(self, rcd_file_path, backup_path, driver_name):
        """Create a backup of an RCD file"""
        try:
            # Create safe filename from driver name
            safe_name = "".join(c if c.isalnum() or c in " _-" else "_" for c in driver_name)
            backup_file = os.path.join(backup_path, f"{safe_name}.rcd")
            
            # Copy the file
            shutil.copy2(rcd_file_path, backup_file)
            logger.debug(f"Backup created: {os.path.basename(backup_file)}")
            return True
        except Exception as e:
            logger.error(f"Failed to backup {driver_name}: {e}")
            return False
    
    def find_rcd_file_for_driver(self, driver_name):
        """Find RCD file containing data for a specific driver"""
        # Search in standard GTR2 locations
        search_folders = [
            os.path.join(self.install_folder, "GameData", "Talent"),
            self.teams_folder,
            os.path.join(self.teams_folder, "..", "Talent"),  # Parent folder might have Talent
        ]
        
        for folder in search_folders:
            if os.path.exists(folder):
                rcd_file = self.search_driver_in_folder(folder, driver_name)
                if rcd_file:
                    return rcd_file
        
        return None
    
    def search_driver_in_folder(self, folder, driver_name):
        """Search for driver in RCD files within a folder"""
        for root, dirs, files in os.walk(folder):
            for file in files:
                if file.lower().endswith('.rcd'):
                    file_path = os.path.join(root, file)
                    if self.driver_in_rcd_file(file_path, driver_name):
                        return file_path
        return None
    
    def driver_in_rcd_file(self, file_path, driver_name):
        """Check if a driver is defined in an RCD file"""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
            
            for line in lines:
                # Skip comments and whitespace
                clean_line = line.split('//')[0].strip()
                if clean_line and '=' not in clean_line and not clean_line.startswith('{') and not clean_line.startswith('}'):
                    # This is a driver name line
                    if clean_line == driver_name:
                        return True
            return False
        except Exception:
            return False
    
    def update_single_rcd_file(self, rcd_file_path, driver_data, fieldnames):
        """Update a single RCD file with new values"""
        try:
            # Read the file
            with open(rcd_file_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
            
            # Parse and update
            updated_lines = []
            in_target_driver_block = False
            brace_depth = 0
            driver_name = driver_data.get('Driver', '')
            
            for line in lines:
                original_line = line.rstrip('\n')
                
                # Check if this is the start of our driver's block
                if not in_target_driver_block:
                    clean_line = original_line.split('//')[0].strip()
                    if clean_line == driver_name:
                        in_target_driver_block = True
                        brace_depth = 0
                        updated_lines.append(original_line + '\n')
                        continue
                
                # If we're in our driver's block
                if in_target_driver_block:
                    # Track braces
                    if '{' in original_line:
                        brace_depth += original_line.count('{')
                    if '}' in original_line:
                        brace_depth -= original_line.count('}')
                    
                    # Check for key-value pairs to update
                    if '=' in original_line and brace_depth > 0:
                        # Split at first = and preserve comments
                        parts = original_line.split('=', 1)
                        if len(parts) == 2:
                            key_part = parts[0].strip()
                            value_comment_part = parts[1]
                            
                            # Check if this is a field we want to update
                            for field in fieldnames:
                                if field.lower() == key_part.lower():
                                    # Get new value from driver_data
                                    new_value = driver_data.get(field, '')
                                    if str(new_value) != '':
                                        # Preserve comments
                                        comment = ''
                                        if '//' in value_comment_part:
                                            comment_idx = value_comment_part.index('//')
                                            comment = value_comment_part[comment_idx:]
                                            value_comment_part = value_comment_part[:comment_idx]
                                        
                                        # Update the line
                                        indent = parts[0][:len(parts[0]) - len(parts[0].lstrip())]
                                        new_line = f"{indent}{key_part}={new_value}{comment}\n"
                                        updated_lines.append(new_line)
                                        break
                            else:
                                # Not a field we're updating, keep original
                                updated_lines.append(original_line + '\n')
                        else:
                            updated_lines.append(original_line + '\n')
                    else:
                        updated_lines.append(original_line + '\n')
                    
                    # Check if we've left the driver's block
                    if brace_depth == 0 and in_target_driver_block and '}' in original_line:
                        in_target_driver_block = False
                else:
                    # Outside target driver block, keep original
                    updated_lines.append(original_line + '\n')
            
            # Write updated content back to file
            with open(rcd_file_path, 'w', encoding='utf-8') as f:
                f.writelines(updated_lines)
            
            return True
            
        except Exception as e:
            logger.error(f"Error updating {rcd_file_path}: {e}")
            return False
