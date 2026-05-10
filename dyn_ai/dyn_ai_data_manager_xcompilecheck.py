#!/usr/bin/env python3
"""
Simple dependency analyzer - outputs PyInstaller flags for cross-compilation
"""

import os
import re
import sys
from pathlib import Path
from typing import Set

def find_python_files(directory: str) -> Set[Path]:
    """Find all Python files in directory"""
    python_files = set()
    for root, dirs, files in os.walk(directory):
        # Skip common directories
        dirs[:] = [d for d in dirs if d not in {'__pycache__', 'venv', 'env', 'build', 'dist'}]
        for file in files:
            if file.endswith('.py'):
                python_files.add(Path(root) / file)
    return python_files

def extract_imports(python_files: Set[Path]) -> Set[str]:
    """Extract all imports from Python files"""
    imports = set()
    
    for file_path in python_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                # Match import statements
                matches = re.findall(r'^(?:import|from)\s+([a-zA-Z_][a-zA-Z0-9_]*)', content, re.MULTILINE)
                imports.update(matches)
        except:
            pass
    
    return imports

def get_local_modules(directory: str) -> Set[str]:
    """Get names of local Python modules (files without .py)"""
    modules = set()
    for file in Path(directory).glob('*.py'):
        modules.add(file.stem)
    return modules

def main():
    # Get project directory (parent of where script is run from)
    script_dir = Path(__file__).parent
    project_dir = script_dir.parent if script_dir.name == 'tools' else script_dir
    
    print(f"Analyzing: {project_dir}", file=sys.stderr)
    
    # Find all Python files
    python_files = find_python_files(project_dir)
    
    # Extract all imports
    all_imports = extract_imports(python_files)
    
    # Get local modules
    local_modules = get_local_modules(project_dir)
    
    # Python standard library (common ones)
    stdlib = {'sys', 'os', 're', 'json', 'csv', 'datetime', 'time', 'math', 
              'random', 'collections', 'itertools', 'functools', 'argparse',
              'logging', 'configparser', 'subprocess', 'threading', 'socket'}
    
    # Filter to external dependencies only
    external_deps = {imp for imp in all_imports 
                    if imp not in local_modules 
                    and imp not in stdlib
                    and not imp.startswith('_')}
    
    # Output hidden imports
    print("\n# Add these to your PyInstaller command:")
    for dep in sorted(external_deps):
        print(f"--hidden-import={dep} \\")
    
    # Find data files
    data_extensions = {'.json', '.yml', '.yaml', '.csv', '.txt', '.xml'}
    data_files = []
    for ext in data_extensions:
        data_files.extend(Path(project_dir).glob(f'*{ext}'))
    
    if data_files:
        print("\n# Add these data files:")
        for data_file in data_files:
            print(f"--add-data=\"{data_file.name};.\" \\")
    
    # Also output pip install command
    if external_deps:
        print(f"\n# Install dependencies:")
        print(f"wine python -m pip install {' '.join(sorted(external_deps))} PyQt5 pyyaml numpy pandas")
    
    print(f"\n# Found {len(external_deps)} external dependencies", file=sys.stderr)

if __name__ == "__main__":
    main()
