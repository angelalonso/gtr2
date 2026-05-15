#!/bin/bash

set -e

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Navigate to the parent directory (where the project files are)
cd "${SCRIPT_DIR}/.."

COMPILEDIR="$HOME/.wine/drive_c/dyn_ai_main"
CWD=$(pwd)

echo "=== Starting build process ==="
echo "Working directory: ${CWD}"

# Clean up previous builds
rm -rf ${COMPILEDIR}
mkdir -p ${COMPILEDIR}

# Copy ALL files from current directory
echo "Copying files to ${COMPILEDIR}..."

cp gui_pre_run_check_light.py ${COMPILEDIR}/
cp gui_main_window_tk.py ${COMPILEDIR}/
cp core_config.py ${COMPILEDIR}/
cp core_database.py ${COMPILEDIR}/
cp core_formula.py ${COMPILEDIR}/
cp core_data_extraction.py ${COMPILEDIR}/
cp core_autopilot.py ${COMPILEDIR}/
cp core_common.py ${COMPILEDIR}/
cp gui_base_path_dialog_tk.py ${COMPILEDIR}/
cp gui_file_monitor.py ${COMPILEDIR}/
cp core_aiw_utils.py ${COMPILEDIR}/
cp core_user_laptimes.py ${COMPILEDIR}/
cp dyn_ai.py ${COMPILEDIR}/

cd ${COMPILEDIR}

# Install dependencies (including PyInstaller)
echo "Installing dependencies..."
## wine python -m pip install --upgrade pip
## wine python -m pip install watchdog pyyaml numpy scipy matplotlib PyQt5 pyinstaller
#### wine python -m venv clean_venv
#### wine clean_venv/Scripts/python.exe -m pip install pyyaml numpy pyinstaller

# Build with PyInstaller - using --add-data for all required files
echo "Building executable with PyInstaller..."
##wine python -m PyInstaller \
##    --upx-dir /usr/bin/ \
##    --onefile \
##    --windowed \
##    --add-data="gui_pre_run_check_light.py;." \
##    --add-data="gui_main_window_tk.py;." \
##    --add-data="core_config.py;." \
##    --add-data="core_database.py;." \
##    --add-data="core_formula.py;." \
##    --add-data="core_data_extraction.py;." \
##    --add-data="core_autopilot.py;." \
##    --add-data="core_common.py;." \
##    --add-data="gui_base_path_dialog_tk.py;." \
##    --add-data="gui_file_monitor.py;." \
##    --add-data="core_aiw_utils.py;." \
##    --add-data="core_user_laptimes.py;." \
wine python -m PyInstaller \
    --upx-dir /usr/bin/ \
    --onefile \
    --windowed \
    --exclude-module PIL \
    --exclude-module PyQt5 \
    --exclude-module colorama \
    --exclude-module contourpy \
    --exclude-module cycler \
    --exclude-module fonttools \
    --exclude-module kiwisolver \
    --exclude-module matplotlib \
    --exclude-module pandas \
    --exclude-module pyparsing \
    --exclude-module pyqtgraph \
    --exclude-module scipy \
    --exclude-module watchdog \
    --name="dyn_ai" \
    --hidden-import=gui_pre_run_check_light \
    --hidden-import=gui_main_window_tk \
    --hidden-import=core_config \
    --hidden-import=core_database \
    --hidden-import=core_formula \
    --hidden-import=core_data_extraction \
    --hidden-import=core_autopilot \
    --hidden-import=core_common \
    --hidden-import=gui_base_path_dialog_tk \
    --hidden-import=gui_file_monitor \
    --hidden-import=core_aiw_utils \
    --hidden-import=core_user_laptimes \
    dyn_ai.py

# Check if build succeeded
if [ -f "dist/dyn_ai.exe" ]; then
    echo "Build successful!"
    
    # Copy back to original directory (parent of script directory)
    cp dist/dyn_ai.exe ${CWD}/
    echo "Copied executable to ${CWD}/dyn_ai.exe"
    
    # Also copy required data files to be alongside the exe
    cp cfg.yml ${CWD}/ 2>/dev/null || true
    cp vehicle_classes.json ${CWD}/ 2>/dev/null || true
    
    echo "Build completed! Make sure cfg.yml and vehicle_classes.json are in the same folder as dyn_ai.exe"
else
    echo "ERROR: Build failed - executable not created"
    exit 1
fi

echo "=== Build process completed ==="

# Return to original directory (optional)
cd "${SCRIPT_DIR}"
