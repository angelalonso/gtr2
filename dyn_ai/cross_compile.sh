#!/bin/bash

set -e

COMPILEDIR="$HOME/.wine/drive_c/dyn_ai"
CWD=$(pwd)

echo "=== Starting build process ==="

# Clean up previous builds
rm -rf ${COMPILEDIR}
mkdir -p ${COMPILEDIR}

# Copy ALL files from current directory
echo "Copying files to ${COMPILEDIR}..."
cp -R ./* ${COMPILEDIR}/

cd ${COMPILEDIR}

# Install dependencies (including PyInstaller)
echo "Installing dependencies..."
wine python -m pip install --upgrade pip
wine python -m pip install watchdog pyyaml numpy scipy matplotlib PyQt5 pyinstaller

# Build with PyInstaller - using --add-data for all required files
echo "Building executable with PyInstaller..."
wine python -m PyInstaller \
    --onefile \
    --windowed \
    --name="dyn_ai" \
    --add-data="cfg_funcs.py;." \
    --add-data="core_aiw_utils.py;." \
    --add-data="core_autopilot.py;." \
    --add-data="core_config.py;." \
    --add-data="core_database.py;." \
    --add-data="core_data_extraction.py;." \
    --add-data="core_formula.py;." \
    --add-data="core_vehicle_scanner.py;." \
    --add-data="dyn_ai.py;." \
    --add-data="gui_advanced_settings.py;." \
    --add-data="gui_base_path_dialog.py;." \
    --add-data="gui_common.py;." \
    --add-data="gui_common_dialogs.py;." \
    --add-data="gui_components.py;." \
    --add-data="gui_curve_graph.py;." \
    --add-data="gui_data_manager.py;." \
    --add-data="gui_file_monitor.py;." \
    --add-data="gui_log_window.py;." \
    --add-data="gui_main_window.py;." \
    --add-data="gui_pre_run_check.py;." \
    --add-data="gui_ratio_panel.py;." \
    --add-data="gui_session_panel.py;." \
    --add-data="gui_vehicle_manager.py;." \
    --add-data="monitor_file_daemon.py;." \
    --add-data="dyn_ai_data_manager.py;." \
    --collect-data=pyqtgraph \
    --hidden-import=cfg_funcs \
    --hidden-import=core_aiw_utils \
    --hidden-import=core_autopilot \
    --hidden-import=core_config \
    --hidden-import=core_database \
    --hidden-import=core_data_extraction \
    --hidden-import=core_formula \
    --hidden-import=core_vehicle_scanner \
    --hidden-import=dyn_ai \
    --hidden-import=gui_advanced_settings \
    --hidden-import=gui_base_path_dialog \
    --hidden-import=gui_common \
    --hidden-import=gui_common_dialogs \
    --hidden-import=gui_components \
    --hidden-import=gui_curve_graph \
    --hidden-import=gui_data_manager \
    --hidden-import=gui_file_monitor \
    --hidden-import=gui_log_window \
    --hidden-import=gui_main_window \
    --hidden-import=gui_pre_run_check \
    --hidden-import=gui_ratio_panel \
    --hidden-import=gui_session_panel \
    --hidden-import=gui_vehicle_manager \
    --hidden-import=monitor_file_daemon \
    --hidden-import=pyqtgraph \
    dyn_ai.py

# Check if build succeeded
if [ -f "dist/dyn_ai.exe" ]; then
    echo "Build successful!"
    
    # Copy back to original directory
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
