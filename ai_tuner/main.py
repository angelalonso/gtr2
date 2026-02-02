#!/usr/bin/env python3
# main.py - Main entry point

import sys
import os
import argparse
from config import DEFAULT_OUTPUT_FILE
from debug_logger import logger

def load_configuration(args):
    """Load configuration from YAML file or arguments"""
    config = {
        'install_folder': args.install,
        'teams_folder': args.teams,
        'output_file': args.output,
        'debug': args.debug
    }
    
    # Load from YAML if specified
    if args.config and os.path.exists(args.config):
        try:
            import yaml
            with open(args.config, 'r') as f:
                yaml_config = yaml.safe_load(f)
            
            # Override with YAML values if not specified in args
            if not config['install_folder'] and 'gtr2_install' in yaml_config:
                config['install_folder'] = yaml_config['gtr2_install']
            if not config['teams_folder'] and 'teams_folder' in yaml_config:
                config['teams_folder'] = yaml_config['teams_folder']
            elif not config['teams_folder'] and config['install_folder']:
                # Default teams folder location
                config['teams_folder'] = os.path.join(config['install_folder'], "GameData", "Teams")
            
            logger.info(f"Loaded configuration from: {args.config}")
            
        except ImportError:
            logger.error("PyYAML not installed. Install with: pip install pyyaml")
            sys.exit(1)
        except Exception as e:
            logger.error(f"Error loading config file: {e}")
    
    # Validate
    if not config['install_folder']:
        logger.error("Install folder not specified. Use --install or --config")
        return None
    
    if not config['teams_folder']:
        logger.error("Teams folder not specified. Use --teams or --config")
        return None
    
    return config

def run_cli(config):
    """Run in command-line mode"""
    from processor import DriverProcessor
    from csv_writer import CSVWriter
    
    # Validate folders
    if not os.path.exists(config['install_folder']):
        logger.error(f"Install folder does not exist: {config['install_folder']}")
        return False
    
    if not os.path.exists(config['teams_folder']):
        logger.error(f"Teams folder does not exist: {config['teams_folder']}")
        return False
    
    # Print header
    print("\n" + "*" * 80)
    print("🚗 GTR2 DRIVER DATA EXTRACTION TOOL")
    print("*" * 80)
    print(f"Version: 5.0 (With YAML config)")
    print(f"Mode: Command Line")
    print(f"GTR2 Install: {config['install_folder']}")
    print(f"Teams Folder: {config['teams_folder']}")
    print(f"Debug mode: {'ENABLED' if config['debug'] else 'DISABLED'}")
    print(f"Output file: {config['output_file']}")
    print("*" * 80 + "\n")
    
    # Create and run processor
    processor = DriverProcessor(
        config['install_folder'], 
        config['teams_folder'], 
        config['debug']
    )
    result = processor.process()
    
    # Save results
    if result:
        data, fieldnames = result
        if data:
            if CSVWriter.write_drivers_to_csv(data, fieldnames, config['output_file']):
                logger.section("✅ PROCESS COMPLETED SUCCESSFULLY", width=80)
                return True
    
    logger.section("❌ PROCESS COMPLETED WITH ERRORS", width=80)
    return False

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description='Extract driver data from .car and .rcd files',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --config cfg.yml
  %(prog)s --gui
  %(prog)s --view result.csv
  %(prog)s --update result.csv --install "C:/Games/GTR2" --teams "C:/Games/GTR2/GameData/Teams"
  %(prog)s --install "C:/Games/GTR2" --teams "C:/Games/GTR2/GameData/Teams" --debug
        """
    )
    
    parser.add_argument('--config', '-c', 
                       help='Path to configuration YAML file')
    parser.add_argument('--install', '-i', 
                       help='Path to GTR2 installation folder')
    parser.add_argument('--teams', '-t', 
                       help='Path to teams folder')
    parser.add_argument('--debug', '-d', 
                       action='store_true', 
                       help='Enable detailed debug output')
    parser.add_argument('--output', '-o', 
                       default=DEFAULT_OUTPUT_FILE,
                       help=f'Output CSV filename (default: {DEFAULT_OUTPUT_FILE})')
    parser.add_argument('--gui', 
                       action='store_true', 
                       help='Launch graphical interface')
    parser.add_argument('--view', 
                       help='View and edit existing CSV file')
    parser.add_argument('--update', 
                       help='Update RCD files from CSV file')
    
    return parser.parse_args()

def main():
    """Main function"""
    args = parse_arguments()
    
    if args.update:
        # Update RCD files from CSV
        if not args.install or not args.teams:
            logger.error("Error: Both --install and --teams are required for RCD update")
            sys.exit(1)
        
        try:
            from rcd_updater import RcdUpdater
            import pandas as pd
            
            # Load CSV data
            df = pd.read_csv(args.update, encoding='utf-8')
            data = df.to_dict('records')
            fieldnames = list(df.columns)
            
            # Filter fieldnames
            excluded_fields = ['Abbreviation', 'Nationality', 'NatAbbrev', 'Script']
            metadata_fields = ['Driver', 'Source_CAR_File', 'CAR_File_Path', 'Original_CAR_Name']
            editable_fields = [f for f in fieldnames 
                             if f not in metadata_fields and f not in excluded_fields]
            
            # Create updater and update files
            updater = RcdUpdater(args.install, args.teams)
            success_count, error_count, backup_path = updater.update_rcd_files(
                data, editable_fields, create_backup=True
            )
            
            logger.section("RCD UPDATE COMPLETED")
            logger.info(f"Successfully updated: {success_count} drivers")
            logger.info(f"Failed to update: {error_count} drivers")
            if backup_path:
                logger.info(f"Backup created at: {backup_path}")
            
            sys.exit(0 if success_count > 0 else 1)
            
        except Exception as e:
            logger.error(f"Error updating RCD files: {e}")
            sys.exit(1)
            
    elif args.view:
        # View and edit existing CSV file
        try:
            from driver_table_editor import DriverTableEditor
            import pandas as pd
            
            # Load data from CSV
            df = pd.read_csv(args.view, encoding='utf-8')
            data = df.to_dict('records')
            fieldnames = list(df.columns)
            
            # Open editor (without installation folders for CLI view)
            editor = DriverTableEditor(data, fieldnames, args.view)
            editor.run()
            sys.exit(0)
            
        except Exception as e:
            logger.error(f"Error opening editor: {e}")
            sys.exit(1)
    elif args.gui:
        # Run GUI mode
        try:
            from gui import run_gui
            run_gui()
            sys.exit(0)
        except ImportError as e:
            logger.error(f"Failed to load GUI: {e}")
            sys.exit(1)
        except Exception as e:
            logger.error(f"Error launching GUI: {e}")
            sys.exit(1)
    else:
        # Run CLI mode
        config = load_configuration(args)
        if not config:
            sys.exit(1)
        
        success = run_cli(config)
        sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
