#!/usr/bin/env python3
# config.py - Configuration and constants

DEBUG = False

# File extensions to search for
CAR_EXTENSIONS = ['.car', '.CAR']
RCD_EXTENSIONS = ['.rcd', '.RCD']

# Default CSV output filename
DEFAULT_OUTPUT_FILE = "result.csv"

# Default config file
DEFAULT_CONFIG_FILE = "cfg.yml"

# Default folder structure (GTR2 specific)
DEFAULT_TEAMS_FOLDER = "GameData/Teams"

# Encoding to try (in order)
ENCODINGS = ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']

# Driver name patterns for .car files
DRIVER_PATTERNS = [
    r'Driver\d*\s*=\s*"([^"]*)"',        # Driver="Full Name"
    r'Driver\d*\s*=\s*"([^"\n\r]+)',      # Driver="Partial name...
    r'Driver\d*\s*=\s*([^\s\n\r]+)',      # Driver=Name (no quotes)
    r'DriverName\d*\s*=\s*"([^"]*)"',     # DriverName="Full Name"
]
