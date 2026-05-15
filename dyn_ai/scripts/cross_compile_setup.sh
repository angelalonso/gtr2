#!/bin/bash

set -e

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Navigate to the parent directory (where the project files are)
cd "${SCRIPT_DIR}/.."

COMPILEDIR="$HOME/.wine/drive_c/dyn_ai_setup"
CWD=$(pwd)

echo "=== Starting build process ==="
echo "Working directory: ${CWD}"

# Clean up previous builds
rm -rf ${COMPILEDIR}
mkdir -p ${COMPILEDIR}

# Copy ALL files from current directory
echo "Copying files to ${COMPILEDIR}..."

cp core_config.py ${COMPILEDIR}/
cp core_database.py ${COMPILEDIR}/
cp core_vehicle_scanner.py ${COMPILEDIR}/
cp gui_pre_run_check_light.py ${COMPILEDIR}/
cp gui_advanced_settings.py ${COMPILEDIR}/
cp gui_advanced_settings_tk.py ${COMPILEDIR}/
cp gui_backup_tk.py ${COMPILEDIR}/
cp gui_logs_tk.py ${COMPILEDIR}/
cp gui_datamgmt_import.py ${COMPILEDIR}/
cp gui_datamgmt_laptimes.py ${COMPILEDIR}/
cp gui_datamgmt_vehicle.py ${COMPILEDIR}/
cp dyn_ai_setup.py ${COMPILEDIR}/

cd ${COMPILEDIR}

# Install dependencies (including PyInstaller)
echo "Installing dependencies..."
## wine python -m pip install --upgrade pip
## wine python -m pip install watchdog pyyaml numpy scipy matplotlib PyQt5 pyinstaller

# Build with PyInstaller - using --add-data for all required files
echo "Building executable with PyInstaller..."

wine python -m PyInstaller \
    --upx-dir /usr/bin/ \
    --onefile \
    --windowed \
    --exclude-module matplotlib \
    --exclude-module contourpy \
    --exclude-module cycler \
    --exclude-module fonttools \
    --exclude-module kiwisolver \
    --exclude-module pyparsing \
    --exclude-module PyQt5 \
    --exclude-module pyqtgraph \
    --exclude-module pandas \
    --exclude-module scipy \
    --exclude-module PIL \
    --exclude-module watchdog \
    --exclude-module colorama \
    --name="dyn_ai_setup" \
    --hidden-import=core_config \
    --hidden-import=core_database \
    --hidden-import=core_vehicle_scanner \
    --hidden-import=gui_advanced_settings \
    --hidden-import=gui_advanced_settings_tk \
    --hidden-import=gui_backup_tk \
    --hidden-import=gui_logs_tk \
    --hidden-import=gui_datamgmt_import \
    --hidden-import=gui_datamgmt_laptimes \
    --hidden-import=gui_datamgmt_vehicle \
    --hidden-import=gui_pre_run_check_light \
    dyn_ai_setup.py

# Check if build succeeded
if [ -f "dist/dyn_ai_setup.exe" ]; then
    echo "Build successful!"
    
    # Copy back to original directory (parent of script directory)
    cp dist/dyn_ai_setup.exe ${CWD}/
    echo "Copied executable to ${CWD}/dyn_ai_setup.exe"
    
    # Also copy required data files to be alongside the exe
    cp cfg.yml ${CWD}/ 2>/dev/null || true
    cp vehicle_classes.json ${CWD}/ 2>/dev/null || true
    
    echo "Build completed! Make sure cfg.yml and vehicle_classes.json are in the same folder as dyn_ai_setup.exe"
else
    echo "ERROR: Build failed - executable not created"
    exit 1
fi

echo "=== Build process completed ==="

# Return to original directory (optional)
cd "${SCRIPT_DIR}"

