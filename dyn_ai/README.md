# dyn_ai — Live AI Tuner for GTR2 - v1.1.0

## What it does

Automatically adjusts AI difficulty to match your driving pace. Reads your lap times, calculates optimal AI speed ratio, and updates the track's AIW file.

---

## Current State

Usable, stable release with less requirements.

**USE AT YOUR OWN RISK.** Test on a separate GTR2 install.

---

## Quick Start

1. Download dyn_ai.zip and dyn_ai.z01 
2. Uncompress to a folder of your liking. Get in that folder.
3. Run dyn_ai.exe, follow instructions.
4. Leave it running and boot GTR2.

---

## Main Features

### Auto-harvest Data
Saves every race session to the database. Builds history of lap times + Track + Car class + AI ratios.

### Auto-calculate Ratios
When enabled: detects race results → analyzes historical data → fits curve `T = a/R + b` → updates AIW file.

### Outlier Detection
Automatically filters out anomalous data points when auto-fitting curves:

| Method | Description | Default Threshold |
|--------|-------------|-------------------|
| Standard Deviation | Removes points with error > mean + N*std_dev | 2.0 |
| IQR (Interquartile Range) | Removes points with error > Q3 + multiplier*IQR | 1.5 |
| Percentile | Removes points above specified percentile | 90% |

Configure in `cfg.yml`:
- outlier_method: std (std, iqr, percentile, or none)
- outlier_threshold: 2.0 (Method-specific threshold)
- outlier_min_points: 3 (Minimum points before attempting detection)

When outliers are detected, a message shows how many were removed from the fit. If data quality is poor, the auto-fit will show warning dialogs explaining the issues.

### Data Quality Warnings
TODO: Adapt this doc
When auto-fitting curves, the system now detects and warns about:
- Duplicate ratio values with widely varying lap times (over 5 seconds difference)
- Narrow ratio ranges (less than 0.2) causing unreliable fits
- Weak correlation between ratio and lap time (correlation less than 0.5)
- High prediction errors after fitting (average error over 2 seconds)

These warnings help identify problematic data that should be reviewed or removed.

### Manual Controls
- Edit ratios directly (Edit button or press Enter on selected item)
- Revert to previous ratio (Revert button)
- Calculate ratio from lap time
- Change formulas manually

---

## Advanced Features

### Dyn AI Setup (Standalone Tool)
TODO: Adapt this doc
Comprehensive database management utility with multiple tabs:

**Laptimes and Ratios Tab:**
- View all data points in a sortable table
- Filter by track, vehicle class, and session type
- Visualize data points on an interactive graph (yellow circles for qualifying, orange squares for race)
- Click on graph points to select corresponding table rows
- Ctrl+Click to select/deselect individual points
- Shift+Click to select ranges of points
- Select All button for bulk operations
- Edit multiple points at once with the multi-edit dialog (checkboxes let you choose which fields to change)
- Delete selected points in bulk
- Keyboard shortcuts: Enter to edit selected items, Delete to remove selected items
- Perfect for removing outliers or correcting incorrect data

**Vehicle Classes Tab:**
- Launch the standalone Vehicle Manager dialog
- Add, rename, or delete vehicle classes
- Add, edit, or remove vehicles from classes
- Import vehicles from GTR2 installation
- Batch assign unassigned vehicles to classes
- Changes are saved to vehicle_classes.json

**Race Data Import Tab:**
- Import race data from CSV files (compatible with historic.csv format)
- Automatically calculates midpoint = (AI Best + AI Worst) / 2
- Separates qualifying and race session data
- Duplicate detection prevents redundant entries

**About Tab:**
- Complete documentation for all features

### Formula Management (Advanced → Formula Management)
- Visualize hyperbolic curves and data points
- Edit a/b parameters with real-time graph updates
- Auto-fit curve with outlier detection and data quality warnings
- Toggle qualifying/race data visibility

### AIW Backup Restore
Automatic backups (`*_ORIGINAL.AIW`). Restore individual or all tracks.

### Log Viewer
Filter by ERROR/WARNING/INFO/DEBUG/ALL levels.

### Configuration Editor (Advanced → Configuration)
- Edit all cfg.yml settings from within the application
- Live updates for settings that don't require restart
- Clear indication of which settings need application restart

---

## Understanding the Formula

**T = a / R + b**

| Variable | Meaning |
|----------|---------|
| T | Lap time (seconds) |
| R | AI speed ratio (QualRatio/RaceRatio) |
| a | Curve slope (fixed at 32) |
| b | Curve height (base lap time) |

Higher R = faster AI | Lower R = slower AI

---

## Files

| File | Purpose |
|------|---------|
| cfg.yml | Configuration (GTR2 path, min/max ratio limits, outlier settings, etc.) |
| ai_data.db | SQLite database (data points, formulas) |
| vehicle_classes.json | Maps vehicle names to classes |
| aiw_backups/ | Original AIW backups |
| ai_target_dumps/ | Detailed calculation logs from Dump Analysis buttons |

### cfg.yml Example
```
base_path: C:\GTR2
db_path: ai_data.db
poll_interval: 5.0
min_ratio: 0.5
max_ratio: 1.5
autopilot_enabled: true
outlier_method: std
outlier_threshold: 2.0
outlier_min_points: 3
```

---

## Tips

- More laps = better curve fit
- Formulas stored per track AND car class
- Error margin (0.5-1.0s) makes AI slightly slower
- Auto-calculate Ratios must be ON for automatic updates
- Use the Laptimes and Ratios tab in Dyn AI Data Manager to review and remove problematic data points
- Track name must be selected before AI ratios are displayed (select via Advanced → Formula Management)
- Outlier detection helps ignore crashes or anomalous laps when auto-fitting
- Use Ctrl+Click and Shift+Click for multi-selection in the Laptimes and Ratios table
- Press Enter to edit selected items, Delete to remove them

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| "No base path configured" | Set `base_path` in cfg.yml |
| AI ratios not updating | Enable Auto-calculate Ratios (green) |
| Can't find AIW file | Verify GTR2 path and track folder exists |
| Ratio outside limits | Adjust `min_ratio`/`max_ratio` in cfg.yml - THIS MAY PRODUCE MAYHEM |
| No ratios shown on main screen | Select a track first via Advanced → Formula Management |
| AIW file has malformed ratios | Fixed in v1.0.6 - now adds each ratio on separate line |
| Wrong track AIW gets updated (e.g., Donington 2003 updates Donington 2004) | See Known Issues below |
| "Extra Stats" error in pre-run checks | Set `Extra Stats="0"` in your GTR2 PLR file (use Fix PLR File button) |
| Auto-fit includes bad laps | Enable outlier detection in cfg.yml (outlier_method: std) or manually remove bad points in Laptimes and Ratios tab |
| Auto-fit produces poor results | Check the Laptimes and Ratios graph for scattered data. Remove outliers manually using multi-select and delete |
| Data quality warnings appear | Review your database for inconsistent data points. Use the Laptimes and Ratios tab to identify and remove problematic entries |

---

## Known Issues

### Track Name Matching Problem

**Symptom:** When racing on Donington 2003, the Donington 2004 AIW file gets updated instead.

**Root Cause:** The application uses case-insensitive partial matching to find AIW files. It searches for a folder name containing the track name. For "Donington 2003", it finds "Donington 2004" because "Donington" matches both.

**How track matching works:**
1. `raceresults.txt` contains `Scene=...\Testtrack2\Testtrack2.TRK`
2. The parser extracts `Testtrack2` as the track folder name
3. The application looks for a folder in `GameData/Locations/` with matching name
4. It uses exact folder name matching first, then falls back to partial matching

**Current Fix in v1.0.7:** The matching logic now prioritizes exact folder name matching before falling back to partial matching. This should resolve the issue for most cases.

**If you still experience the issue:**
- Ensure your track folder names in `GameData/Locations/` are unique and descriptive
- For conflicting tracks (e.g., "Donington" vs "Donington 2003" vs "Donington 2004"), consider renaming folders or using the exact match in `raceresults.txt`

---

## Changelog v1.0.8

**Laptimes and Ratios Tab (Database Manager):**

- Renamed from "Database Manager" to "Laptimes and Ratios" and moved to first tab position
- Added multi-select support with Ctrl+Click and Shift+Click for selecting multiple data points
- Added Select All button for bulk operations
- Replaced "Delete All Filtered" button with Select All + Delete Selected workflow
- Added multi-edit dialog allowing batch updates to multiple selected points:
  - Each field has a checkbox to enable/disable changing that field
  - Fields with mixed values across selection show the current value but can be overridden
  - Empty/unchanged fields preserve original values
- Added Delete key shortcut to delete selected items
- Added Enter key shortcut to edit selected items
- Removed symbol icons from graph legend, now shows clean text-only labels: "Qualifying (X)" and "Race (Y)"
- Fixed legend generating vertical lines by implementing text-only pseudo-legend
- Improved data quality warnings during auto-fit with specific recommendations

**Data Quality Warnings:**

- Auto-fit now detects and warns about:
  - Duplicate ratio values with lap time variations over 5 seconds
  - Narrow ratio ranges (less than 0.2)
  - Weak correlation (less than 0.5) between ratio and lap time
  - High prediction errors (average error over 2 seconds)
- Warning dialogs provide specific recommendations for fixing data quality issues

**Dyn AI Data Manager Restructuring:**

- Split monolithic gui_data_manager.py into modular files:
  - gui_data_manager_common.py: Shared database class
  - gui_data_manager_database.py: Laptimes and Ratios tab
  - gui_data_manager_vehicle.py: Vehicle Classes tab
  - gui_data_manager_import.py: Race Data Import tab
- Removed redundant Database Info tab
- Reordered tabs: Laptimes and Ratios, Vehicle Classes, Race Data Import, About
- Button text now shows keyboard shortcuts: "Edit Selected (Enter)", "Delete Selected (Delete)"

**Manual Lap Time Dialog Fix:**

- Fixed missing QDialog import causing NameError when editing user lap times
- Enter key now correctly saves the current value instead of canceling

---

## Changelog v1.0.7

**Ratio Clamping:**

- Calculated ratios outside min/max limits are now clamped to the limit value instead of being rejected
- A warning dialog informs you when clamping occurs
- Applies to auto-ratio calculations, manual edits, and advanced dialog saves
- No more silent rejection of out-of-range ratios

**Vehicle Classes Manager Cleanup:**

- Removed redundant "Quick Add" input field from the vehicle manager interface
- Cleaner, more focused UI for managing vehicle classes

**Pre-Run Check Screen:**
- Added comprehensive pre-run verification before application starts
- Checks: cfg.yml, vehicle_classes.json, GTR2 base path, GTR2 executable
- Added PLR file validation (Extra Stats must be 0)
- Added "Fix PLR File" button to automatically correct Extra Stats setting
- Continue button is greyed out until all checks pass
- "How to Use" section with colored text (white for steps, yellow for TIPS header)

**Outlier Detection:**
- Added three outlier detection methods for auto-fit: Std Dev, IQR, Percentile
- Configurable via cfg.yml (outlier_method, outlier_threshold, outlier_min_points)
- Shows message when outliers are removed during auto-fit
- Helps ignore anomalous laps (crashes, off-track excursions)

**Track Matching Fix:**
- Improved AIW file matching to prioritize exact folder name matches
- Partial matching only used as fallback
- Should resolve issues where wrong track's AIW gets updated (e.g., Donington 2003 vs Donington 2004)

**PLR File Validation:**
- Pre-run check now verifies GTR2 PLR file has Extra Stats="0"
- Without this setting, GTR2 does not write race results
- Automatic fix button available in pre-run check dialog

**Code Organization:**
- Split `dyn_ai.py` into multiple files for better maintainability:
  - `main_window.py` - Main application window
  - `pre_run_check.py` - Pre-run verification dialog
  - `dialogs_base_path.py` - Base path selection dialog
  - `dialogs_info_message.py` - Info dialog (kept for compatibility)

**Testing:**
- Added comprehensive unit tests for:
  - Outlier detection (std, iqr, percentile methods)
  - PLR file validation and fixing
  - Pre-run check integration
  - Formula cross-validation
  - Ratio clamping functionality

---

## Changelog v1.0.6

**Main Screen Improvements:**
- Main screen no longer shows any track until explicitly selected via Advanced → Data Management
- Track label now displays "- No Track Selected -" at startup
- Quali-Ratio and Race-Ratio panels show blank (--) until a track is chosen
- Load AIW ratios only after track selection

**AIW File Format Fix:**
- Fixed bug where missing QualRatio/RaceRatio were added with wrong format
- Each ratio now appears on its own line with proper indentation

**Data Management Tab Redesign (Advanced → Data Management):**
- Removed the Data Points table area for cleaner interface
- Graph area is now more prominent and visible
- Added "Open Dyn AI Data Manager" button to launch `datamgmt_dyn_ai.exe` (or `.py` if running from source)
- Provides quick access to vehicle class management and CSV import

---

## Changelog v1.0.5

- **AI Target warning banner** - Red warning added to indicate feature is under construction
- **Improved AIW error handling** - Better error messages with "Configure GTR2 Path" button, prevents frontend changes when AIW not found
- **Dump Analysis moved to AI Target tab** - Removed from main screen, now available in Advanced → AI Target
- **Resizable main window fix** - Race and Quali panels now resize properly with window, buttons stay at bottom
- **Fixed dump_analysis crash** - Resolved "'RedesignedMainWindow' object is not callable" error

---

## Changelog v1.0.4

- AI Target settings now apply to ALL ratio calculations (auto-ratio, manual edits, advanced dialog)
- Added ratio limits (`min_ratio`/`max_ratio` in cfg.yml) with warning popups
- Fixed TypeError when AI times are None
- AIW not found now shows GUI error popup
- Auto-Fit no longer auto-calculates ratio (button turns orange until clicked)
- Added Revert buttons to main screen panels
- Added manual lap time editing in Advanced → Data Management
- Target indicator moved to status bar with quick-configure button
