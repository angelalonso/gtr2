#!/usr/bin/env python3
# file_finder.py - File searching utilities

import os
from config import CAR_EXTENSIONS, RCD_EXTENSIONS
from debug_logger import logger

class FileFinder:
    """Handles finding files with specific extensions"""
    
    @staticmethod
    def find_files(folder_path, extensions, recursive=True, debug=False):
        """
        Find files with specific extensions in a folder
        
        Args:
            folder_path: Path to search in
            extensions: List of file extensions to look for
            recursive: Whether to search recursively
            debug: Enable debug output
        
        Returns:
            List of full paths to found files
        """
        if not os.path.exists(folder_path):
            logger.error(f"Folder does not exist: {folder_path}")
            return []
        
        logger.section(f"SEARCHING FOR {extensions[0].upper()} FILES")
        logger.info(f"Search root: {folder_path}")
        
        found_files = []
        
        if recursive:
            # Recursive search
            for root, dirs, files in os.walk(folder_path):
                folder_files = FileFinder._check_files_in_folder(root, files, extensions, debug)
                found_files.extend(folder_files)
                
                if debug and folder_files:
                    logger.debug(f"Found {len(folder_files)} files in {os.path.relpath(root, folder_path)}")
        else:
            # Non-recursive search
            try:
                files = os.listdir(folder_path)
                folder_files = FileFinder._check_files_in_folder(folder_path, files, extensions, debug)
                found_files.extend(folder_files)
            except Exception as e:
                logger.error(f"Error listing directory {folder_path}: {e}")
        
        # Summary
        logger.info(f"Total files found: {len(found_files)}")
        
        if debug and found_files:
            logger.subsection("FOUND FILES")
            for i, file_path in enumerate(found_files[:10], 1):  # Show first 10
                rel_path = os.path.relpath(file_path, folder_path)
                logger.info(f"{i:3d}. {rel_path}")
            
            if len(found_files) > 10:
                logger.info(f"... and {len(found_files) - 10} more files")
        
        return found_files
    
    @staticmethod
    def _check_files_in_folder(folder_path, files, extensions, debug=False):
        """Check files in a specific folder for matching extensions"""
        found_files = []
        
        for file in files:
            # Check all extensions (case-insensitive)
            if any(file.lower().endswith(ext.lower()) for ext in extensions):
                full_path = os.path.join(folder_path, file)
                found_files.append(full_path)
                
                if debug:
                    logger.debug(f"Found: {file}")
        
        return found_files
    
    @staticmethod
    def find_car_files(folder_path, debug=False):
        """Find .car files"""
        return FileFinder.find_files(folder_path, CAR_EXTENSIONS, recursive=True, debug=debug)
    
    @staticmethod
    def find_rcd_files(folder_paths, debug=False):
        """Find .rcd files in multiple folders"""
        all_rcd_files = []
        
        for i, folder_path in enumerate(folder_paths, 1):
            if os.path.exists(folder_path):
                logger.info(f"[{i}/{len(folder_paths)}] Searching in: {folder_path}")
                rcd_files = FileFinder.find_files(folder_path, RCD_EXTENSIONS, recursive=True, debug=debug)
                all_rcd_files.extend(rcd_files)
                logger.info(f"Found {len(rcd_files)} .rcd files in this folder")
            else:
                logger.warning(f"[{i}/{len(folder_paths)}] Folder does not exist: {folder_path}")
        
        logger.info(f"Total .rcd files found: {len(all_rcd_files)}")
        return all_rcd_files
