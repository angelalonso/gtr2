#!/bin/bash

set -e  # Exit on error

COMPILEDIR="$HOME/.wine/drive_c/dyn_ai"
CWD=$(pwd)

echo "=== Starting build process ==="

# Clean up previous builds
rm -rf ${COMPILEDIR}/build ${COMPILEDIR}/dist
rm -f ${COMPILEDIR}/*.py ${COMPILEDIR}/*.spec 
rm -f ${COMPILEDIR}/Pipfile ${COMPILEDIR}/Pipfile.lock

# Create compile directory
mkdir -p ${COMPILEDIR}

# Copy ALL files from current directory
echo "Copying files to ${COMPILEDIR}..."
cp -R ./* ${COMPILEDIR}/

cd ${COMPILEDIR}

# Install dependencies
echo "Installing dependencies..."
wine python -m pip install --upgrade pip
wine python -m pip install watchdog pyyaml numpy scipy matplotlib PyQt5

# Build with PyInstaller, explicitly adding all Python files
echo "Building executable with PyInstaller..."
wine python -m PyInstaller \
    --onefile \
    --windowed \
    --add-data="aiw_manager.py;." \
    --add-data="cfg_manage.py;." \
    --add-data="file_monitor.py;." \
    --add-data="global_curve_builder.py;." \
    --add-data="global_curve.py;." \
    --add-data="gui.py;." \
    --add-data="ratio_calculator.py;." \
    --add-data="results_parser.py;." \
    --hidden-import=aiw_manager \
    --hidden-import=cfg_manage \
    --hidden-import=file_monitor \
    --hidden-import=global_curve_builder \
    --hidden-import=global_curve \
    --hidden-import=gui \
    --hidden-import=ratio_calculator \
    --hidden-import=results_parser \
    dyn_ai.py

# Check if build succeeded
if [ -f "dist/dyn_ai.exe" ]; then
    echo "Build successful!"
    
    # Copy back to original directory
    cp dist/dyn_ai.exe ${CWD}/
    echo "Copied executable to ${CWD}/dyn_ai.exe"
    
    # Optional: Test the executable
    echo "Testing executable..."
    wine dyn_ai.exe --help 2>&1 | head -5 || echo "Test completed"
    
else
    echo "ERROR: Build failed - executable not created"
    exit 1
fi

echo "=== Build process completed ==="

# zip -s 49m -r dyn_ai.zip dyn_ai.exe
