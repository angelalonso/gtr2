#!/bin/bash

set -e

COMPILEDIR="$HOME/.wine/drive_c/datamgmt_dyn_ai"
CWD=$(pwd)

echo "=== Building Dyn AI Data Manager ==="

# Clean and create build directory
rm -rf ${COMPILEDIR}
mkdir -p ${COMPILEDIR}

# Copy files
cp datamgmt_dyn_ai.py ${COMPILEDIR}/
[ -f "db_funcs.py" ] && cp db_funcs.py ${COMPILEDIR}/
[ -f "vehicle_classes.json" ] && cp vehicle_classes.json ${COMPILEDIR}/

cd ${COMPILEDIR}

# Install dependencies
wine python -m pip install --upgrade pip
wine python -m pip install PyQt5 pyyaml

# Build
wine python -m PyInstaller --onefile --windowed --name="datamgmt_dyn_ai" datamgmt_dyn_ai.py

# Copy result
if [ -f "dist/datamgmt_dyn_ai.exe" ]; then
    cp dist/datamgmt_dyn_ai.exe ${CWD}/
    echo "✓ Success! Executable: ${CWD}/datamgmt_dyn_ai.exe"
    wine datamgmt_dyn_ai
else
    echo "✗ Build failed"
    exit 1
fi

echo "=== Done ==="
