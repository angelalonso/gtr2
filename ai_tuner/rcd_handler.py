#!/usr/bin/env python3
# rcd_handler.py - .rcd file handling (finder + parser)

import os
from config import RCD_EXTENSIONS, ENCODINGS
from debug_logger import logger

class RcdHandler:
    """Handles all .rcd file operations"""
    
    @staticmethod
    def find_rcd_folders(install_folder, teams_folder):
        """Get list of folders to search for .rcd files"""
        talent_folder = os.path.join(install_folder, "GameData", "Talent")
        return [talent_folder, teams_folder]
    
    @staticmethod
    def find_rcd_files(folder_paths, debug=False):
        """Find all .rcd files recursively in multiple folders"""
        all_rcd_files = []
        
        logger.section("SEARCHING FOR .RCD FILES")
        
        for i, folder_path in enumerate(folder_paths, 1):
            logger.info(f"[{i}/{len(folder_paths)}] Searching in: {folder_path}")
            
            if not os.path.exists(folder_path):
                logger.warning(f"Folder does not exist: {folder_path}")
                continue
            
            folder_rcd_files = RcdHandler._find_rcd_files_in_folder(folder_path, debug)
            all_rcd_files.extend(folder_rcd_files)
            
            logger.info(f"Found {len(folder_rcd_files)} .rcd files in this folder")
        
        logger.info(f"Total .rcd files found: {len(all_rcd_files)}")
        return all_rcd_files
    
    @staticmethod
    def _find_rcd_files_in_folder(folder_path, debug=False):
        """Find .rcd files in a single folder recursively"""
        rcd_files = []
        
        for root, dirs, files in os.walk(folder_path):
            for file in files:
                if any(file.lower().endswith(ext) for ext in RCD_EXTENSIONS):
                    full_path = os.path.join(root, file)
                    rcd_files.append(full_path)
        
        return rcd_files
    
    @staticmethod
    def parse_rcd_files(rcd_file_paths, debug=False):
        """Parse multiple .rcd files and combine their data"""
        all_driver_data = {}
        
        logger.section("PARSING RCD FILES")
        
        for i, rcd_file_path in enumerate(rcd_file_paths, 1):
            file_debug = debug or i <= 3
            
            if file_debug:
                logger.progress(i, len(rcd_file_paths), f"Parsing: {os.path.basename(rcd_file_path)}")
            
            driver_data = RcdHandler._parse_rcd_file(rcd_file_path, file_debug)
            all_driver_data.update(driver_data)
            
            if file_debug and driver_data:
                logger.info(f"Found {len(driver_data)} driver(s) in this file")
            
            if i == 4 and not debug:
                logger.info("... (parsing remaining files silently)")
        
        logger.info(f"Total drivers parsed from RCD: {len(all_driver_data)}")
        return all_driver_data
    
    @staticmethod
    def _parse_rcd_file(rcd_file_path, debug=False):
        """Parse a single .rcd file"""
        content = RcdHandler._read_file_with_fallback(rcd_file_path, debug)
        if not content:
            return {}
        
        driver_data = {}
        current_driver = None
        lines = content.split('\n')
        
        for line in lines:
            line = line.split('//')[0].strip()
            
            if not line:
                continue
            
            if '=' not in line and not line.startswith('{') and not line.startswith('}'):
                current_driver = line.strip()
                if current_driver:
                    driver_data[current_driver] = {}
                    if debug:
                        logger.debug(f"Found driver: '{current_driver}'")
            
            elif '=' in line and current_driver:
                key_value = line.split('=', 1)
                if len(key_value) == 2:
                    key = key_value[0].strip()
                    value = key_value[1].strip()
                    driver_data[current_driver][key] = value
        
        return driver_data
    
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
        
        if debug:
            logger.error(f"Failed to read RCD file: {file_path}")
        return None
