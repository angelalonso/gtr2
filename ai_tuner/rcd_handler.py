#!/usr/bin/env python3
# rcd_handler.py - Unified RCD file handling (finder + parser + updater)

import os
import shutil
from debug_logger import logger
from config import RCD_EXTENSIONS, ENCODINGS

# RCD field mapping using ONLY fields from the provided RCD example
RCD_FIELD_MAP = {
    'Abbreviation': 'Abbreviation',
    'Nationality': 'Nationality',
    'NatAbbrev': 'NatAbbrev',
    'StartsDry': 'StartsDry',
    'StartsWet': 'StartsWet',
    'StartStalls': 'StartStalls',
    'QualifyingAbility': 'QualifyingAbility',
    'RaceAbility': 'RaceAbility',
    'Consistency': 'Consistency',
    'RainAbility': 'RainAbility',
    'Passing': 'Passing',
    'Crash': 'Crash',
    'Recovery': 'Recovery',
    'CompletedLaps%': 'CompletedLaps%',
    'Script': 'Script',
    'TrackAggression': 'TrackAggression',
    'CorneringAdd': 'CorneringAdd',
    'CorneringMult': 'CorneringMult',
    'TCGripThreshold': 'TCGripThreshold',
    'TCThrottleFract': 'TCThrottleFract',
    'TCResponse': 'TCResponse',
    'MinRacingSkill': 'MinRacingSkill',
    'Composure': 'Composure',
    'RaceColdBrainMin': 'RaceColdBrainMin',
    'RaceColdBrainTime': 'RaceColdBrainTime',
    'QualColdBrainMin': 'QualColdBrainMin',
    'QualColdBrainTime': 'QualColdBrainTime',
}

class RcdHandler:
    """Unified handler for all RCD file operations (find, parse, update)"""
    
    def __init__(self, install_folder=None, teams_folder=None):
        self.install_folder = install_folder
        self.teams_folder = teams_folder
        self.backup_folder = "originals_backup"
        self._rcd_file_cache = {}  # Cache for faster lookups
    
    # =========================================================================
    # FINDING METHODS
    # =========================================================================
    
    def get_search_folders(self):
        """Get list of folders to search for .rcd files"""
        folders = []
        if self.install_folder:
            talent_folder = os.path.join(self.install_folder, "GameData", "Talent")
            folders.append(talent_folder)
        if self.teams_folder:
            folders.append(self.teams_folder)
        return folders
    
    def find_all_rcd_files(self, debug=False):
        """Find all .rcd files recursively in search folders"""
        all_rcd_files = []
        search_folders = self.get_search_folders()
        
        logger.section("SEARCHING FOR .RCD FILES")
        
        for i, folder_path in enumerate(search_folders, 1):
            logger.info(f"[{i}/{len(search_folders)}] Searching in: {folder_path}")
            
            if not os.path.exists(folder_path):
                logger.warning(f"Folder does not exist: {folder_path}")
                continue
            
            folder_rcd_files = self._scan_folder_for_rcd(folder_path)
            all_rcd_files.extend(folder_rcd_files)
            logger.info(f"Found {len(folder_rcd_files)} .rcd files in this folder")
        
        logger.info(f"Total .rcd files found: {len(all_rcd_files)}")
        
        # Build cache for faster driver lookups
        if all_rcd_files:
            self._build_driver_cache(all_rcd_files, debug)
        
        return all_rcd_files
    
    def _scan_folder_for_rcd(self, folder_path):
        """Scan a folder recursively for RCD files (optimized)"""
        rcd_files = []
        # Pre-compile extensions for faster checking
        extensions = tuple(ext.lower() for ext in RCD_EXTENSIONS)
        
        for root, _, files in os.walk(folder_path):
            for file in files:
                if file.lower().endswith(extensions):
                    rcd_files.append(os.path.join(root, file))
        
        return rcd_files
    
    def _build_driver_cache(self, rcd_files, debug=False):
        """Build a cache of driver -> file mapping for faster lookups"""
        logger.info("Building driver cache...")
        self._rcd_file_cache = {}
        
        for rcd_file in rcd_files:
            drivers = self._extract_driver_names(rcd_file)
            for driver in drivers:
                self._rcd_file_cache[driver] = rcd_file
        
        if debug:
            logger.debug(f"Driver cache built: {len(self._rcd_file_cache)} entries")
    
    def _extract_driver_names(self, file_path):
        """Quickly extract driver names from RCD file without full parsing"""
        drivers = []
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    line = line.split('//')[0].strip()
                    if line and '=' not in line and not line.startswith('{') and not line.startswith('}'):
                        drivers.append(line)
                        # Limit to first few drivers if we only need existence check
                        if len(drivers) > 10:  # Arbitrary limit for cache building
                            break
        except:
            pass
        return drivers
    
    # =========================================================================
    # PARSING METHODS (OPTIMIZED)
    # =========================================================================
    
    def parse_rcd_files(self, rcd_file_paths=None, debug=False):
        """Parse RCD files and extract driver data (optimized)"""
        if not rcd_file_paths:
            rcd_file_paths = self.find_all_rcd_files(debug)
        
        all_driver_data = {}
        
        logger.section("PARSING RCD FILES")
        
        # Process in batches for better performance
        batch_size = 5 if debug else 20
        for i in range(0, len(rcd_file_paths), batch_size):
            batch = rcd_file_paths[i:i + batch_size]
            
            for j, rcd_file_path in enumerate(batch, 1):
                file_index = i + j
                file_debug = debug or file_index <= 3
                
                if file_debug:
                    logger.progress(file_index, len(rcd_file_paths), 
                                  f"Parsing: {os.path.basename(rcd_file_path)}")
                
                driver_data = self._parse_single_rcd_fast(rcd_file_path, file_debug)
                all_driver_data.update(driver_data)
                
                if file_debug and driver_data:
                    logger.info(f"Found {len(driver_data)} driver(s) in this file")
            
            if i == 0 and not debug and len(rcd_file_paths) > batch_size:
                logger.info(f"... (parsing {len(rcd_file_paths) - batch_size} more files)")
        
        logger.info(f"Total drivers parsed from RCD: {len(all_driver_data)}")
        return all_driver_data
    
    def _parse_single_rcd_fast(self, rcd_file_path, debug=False):
        """Fast parsing of a single RCD file using field patterns"""
        content = self._read_file_fast(rcd_file_path, debug)
        if not content:
            return {}
        
        driver_data = {}
        current_driver = None
        lines = content.split('\n')
        
        for line in lines:
            # Skip comments early
            comment_idx = line.find('//')
            if comment_idx != -1:
                line = line[:comment_idx]
            
            line = line.strip()
            if not line:
                continue
            
            # Check if this is a driver name (no =, not { or })
            if '=' not in line and not line.startswith('{') and not line.startswith('}'):
                current_driver = line
                if current_driver:
                    driver_data[current_driver] = {'Driver': current_driver}
                    if debug:
                        logger.debug(f"Found driver: '{current_driver}'")
            
            # Check if this is a field we care about
            elif '=' in line and current_driver:
                # Fast split at first =
                parts = line.split('=', 1)
                if len(parts) == 2:
                    key = parts[0].strip()
                    
                    # Fast lookup in predefined patterns
                    if key in RCD_FIELD_MAP:
                        value = parts[1].split('//')[0].strip()
                        driver_data[current_driver][key] = value
        
        return driver_data
    
    def _read_file_fast(self, file_path, debug=False):
        """Optimized file reading with encoding fallback"""
        for encoding in ENCODINGS:
            try:
                with open(file_path, 'r', encoding=encoding, errors='ignore') as f:
                    return f.read()
            except:
                continue
        
        if debug:
            logger.error(f"Failed to read RCD file: {file_path}")
        return None
    
    # =========================================================================
    # UPDATING METHODS
    # =========================================================================
    
    def update_rcd_files(self, csv_data, fieldnames, create_backup=True):
        """Update RCD files with values from CSV data"""
        logger.section("UPDATING RCD FILES")
        
        # Create backup folder if needed
        backup_path = None
        if create_backup:
            backup_path = self._ensure_backup_folder()
            if backup_path:
                logger.info(f"Backup folder: {backup_path}")
        
        # Track statistics
        success_count = 0
        error_count = 0
        updated_drivers = []
        
        # Filter fieldnames to only include valid RCD fields
        valid_fieldnames = [field for field in fieldnames if field in RCD_FIELD_MAP]
        if valid_fieldnames != fieldnames:
            logger.warning(f"Some fieldnames are not valid RCD fields and will be ignored: "
                          f"{set(fieldnames) - set(valid_fieldnames)}")
        
        # Process each driver
        for driver_data in csv_data:
            driver_name = driver_data.get('Driver', '')
            if not driver_name:
                continue
            
            # Find RCD file using cache or search
            rcd_file_path = self.find_rcd_file_for_driver(driver_name)
            
            if rcd_file_path:
                # Create backup if requested
                if backup_path:
                    self._backup_if_needed(rcd_file_path, backup_path, driver_name)
                
                # Update RCD file
                if self._update_single_rcd(rcd_file_path, driver_name, driver_data, valid_fieldnames):
                    success_count += 1
                    updated_drivers.append(driver_name)
                    logger.success(f"Updated: {driver_name}")
                else:
                    error_count += 1
                    logger.error(f"Failed to update: {driver_name}")
            else:
                error_count += 1
                logger.error(f"RCD file not found for: {driver_name}")
        
        # Summary
        self._print_update_summary(success_count, error_count, updated_drivers)
        
        return success_count, error_count, backup_path
    
    def find_rcd_file_for_driver(self, driver_name):
        """Find RCD file for a driver (uses cache if available)"""
        # Check cache first
        if driver_name in self._rcd_file_cache:
            return self._rcd_file_cache[driver_name]
        
        # Fallback to search
        return self._search_driver_in_folders(driver_name)
    
    def _search_driver_in_folders(self, driver_name):
        """Search for driver in all RCD folders"""
        search_folders = self.get_search_folders()
        
        for folder in search_folders:
            if os.path.exists(folder):
                rcd_file = self._find_driver_in_folder(folder, driver_name)
                if rcd_file:
                    return rcd_file
        
        return None
    
    def _find_driver_in_folder(self, folder, driver_name):
        """Search for driver in a specific folder"""
        for root, _, files in os.walk(folder):
            for file in files:
                if file.lower().endswith('.rcd'):
                    file_path = os.path.join(root, file)
                    if self._driver_exists_in_file(file_path, driver_name):
                        return file_path
        return None
    
    def _driver_exists_in_file(self, file_path, driver_name):
        """Check if driver exists in file (optimized)"""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    line = line.split('//')[0].strip()
                    if line == driver_name:
                        return True
        except:
            pass
        return False
    
    def _ensure_backup_folder(self):
        """Create backup folder if it doesn't exist"""
        try:
            os.makedirs(self.backup_folder, exist_ok=True)
            return os.path.abspath(self.backup_folder)
        except Exception as e:
            logger.error(f"Failed to create backup folder: {e}")
            return None
    
    def _backup_if_needed(self, rcd_file_path, backup_path, driver_name):
        """Create backup if file hasn't been backed up yet"""
        try:
            rel_path = self._get_relative_path(rcd_file_path)
            if not rel_path:
                logger.warning(f"Cannot determine relative path for: {rcd_file_path}")
                return False
            
            backup_file_path = os.path.join(backup_path, rel_path)
            
            if os.path.exists(backup_file_path):
                return True  # Already backed up
            
            # Create parent directories
            os.makedirs(os.path.dirname(backup_file_path), exist_ok=True)
            
            # Copy file
            shutil.copy2(rcd_file_path, backup_file_path)
            logger.debug(f"Backup created for: {driver_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to backup {driver_name}: {e}")
            return False
    
    def _get_relative_path(self, file_path):
        """Get relative path from installation or teams folder"""
        # Try install folder first
        if self.install_folder and file_path.startswith(self.install_folder):
            return os.path.relpath(file_path, self.install_folder)
        
        # Try teams folder
        if self.teams_folder and file_path.startswith(self.teams_folder):
            # Try to preserve from GameData onward
            teams_parent = os.path.dirname(self.teams_folder)
            if file_path.startswith(teams_parent):
                return os.path.relpath(file_path, teams_parent)
        
        return None
    
    def _update_single_rcd(self, rcd_file_path, driver_name, driver_data, fieldnames):
        """Update a single RCD file with optimized parsing"""
        try:
            with open(rcd_file_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
            
            updated_lines = []
            in_target_block = False
            brace_depth = 0
            
            for line in lines:
                original = line.rstrip('\n')
                
                # Check for driver block start
                if not in_target_block:
                    clean_line = original.split('//')[0].strip()
                    if clean_line == driver_name:
                        in_target_block = True
                        brace_depth = 0
                
                # Process line
                if in_target_block:
                    # Update brace depth
                    brace_depth += original.count('{')
                    brace_depth -= original.count('}')
                    
                    # Check for fields to update
                    if '=' in original and brace_depth > 0:
                        updated_line = self._update_line_if_needed(original, driver_data, fieldnames)
                        updated_lines.append(updated_line + '\n')
                    else:
                        updated_lines.append(original + '\n')
                    
                    # Check if block ended
                    if brace_depth == 0 and in_target_block and '}' in original:
                        in_target_block = False
                else:
                    updated_lines.append(original + '\n')
            
            # Write back to file
            with open(rcd_file_path, 'w', encoding='utf-8') as f:
                f.writelines(updated_lines)
            
            return True
            
        except Exception as e:
            logger.error(f"Error updating {rcd_file_path}: {e}")
            return False
    
    def _update_line_if_needed(self, line, driver_data, fieldnames):
        """Update a single line if it contains a field we need to update"""
        # Find first = and preserve structure
        eq_index = line.find('=')
        if eq_index == -1:
            return line
        
        # Extract key
        key_part = line[:eq_index]
        key = key_part.strip()
        
        # Check if this is a field we want to update
        if key in fieldnames:
            new_value = driver_data.get(key, '')
            if str(new_value) != '':
                # Preserve indent and comments
                indent = key_part[:len(key_part) - len(key_part.lstrip())]
                value_part = line[eq_index + 1:]
                
                # Preserve comments
                comment = ''
                if '//' in value_part:
                    comment_idx = value_part.index('//')
                    comment = value_part[comment_idx:]
                    value_part = value_part[:comment_idx]
                
                return f"{indent}{key}={new_value}{comment}"
        
        return line
    
    def _print_update_summary(self, success_count, error_count, updated_drivers):
        """Print update summary"""
        logger.section("UPDATE SUMMARY")
        logger.info(f"Successfully updated: {success_count} drivers")
        logger.info(f"Failed to update: {error_count} drivers")
        
        if updated_drivers:
            logger.subsection("UPDATED DRIVERS")
            for i, driver in enumerate(updated_drivers[:20], 1):
                logger.info(f"{i:3d}. {driver}")
            if len(updated_drivers) > 20:
                logger.info(f"... and {len(updated_drivers) - 20} more")
