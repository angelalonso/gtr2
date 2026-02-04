#!/usr/bin/env python3
# main.py - Main entry point (GUI only version)

import sys
import os

def main():
    """Main function - launches GUI"""
    try:
        # Check if tkinter is available
        import tkinter as tk
        from tkinter import messagebox
        
        # Launch the GUI
        from gui import run_gui
        run_gui()
        
    except ImportError as e:
        # Handle missing tkinter
        print("\n" + "="*60)
        print("ERROR: Missing GUI Dependencies")
        print("="*60)
        print("\nTkinter is required but not available.")
        print("\nInstallation instructions:")
        print("- Windows: Usually included with Python installation")
        print("- Linux: sudo apt-get install python3-tk")
        print("- macOS: Install ActiveTcl from http://www.activestate.com/activetcl")
        print("\nAlternatively, install via package manager:")
        print("  pip install tk")
        print("="*60)
        sys.exit(1)
        
    except Exception as e:
        # Handle any other errors
        print(f"\nError launching GUI: {e}")
        print("\nPlease ensure all dependencies are installed:")
        print("  pip install pandas pyyaml")
        sys.exit(1)

if __name__ == "__main__":
    main()
