# dyn_ai — Live AI Tuner for GTR2 - v1.0.7

## What it does

Automatically adjusts AI difficulty to match your driving pace. Reads your lap times, calculates optimal AI speed ratio, and updates the track's AIW file.

---

## Current State

Usable, stable release with improved UI, AIW handling, and outlier detection.

**USE AT YOUR OWN RISK.** Test on a separate install.

---

## Quick Start

1. Check and edit `cfg.yml` and `vehicle_classes.json` if needed
2. Run the application
3. Pre-run checks will verify your setup:
   - Configuration file (cfg.yml)
   - Vehicle classes file (vehicle_classes.json)
   - GTR2 base path (must contain GameData/ and UserData/)
   - GTR2 executable
   - GTR2 PLR file (Extra Stats setting)
4. Point it to your GTR2 install folder (with `GameData/`) if not already configured - saved to `cfg.yml`

**Windows (easy):** Run the `.exe` from the zip  
**From source:**

pipenv install
pipenv run python3 dyn_ai.py

---

## Main Features

### Pre-Run Checks
Automatically verifies before launching:
- cfg.yml exists and is valid
- vehicle_classes.json exists and has correct structure
- GTR2 base path is configured and valid
- GTR2.exe is present
- GTR2 PLR file has `Extra Stats="0"` (required for race results to be written)

Once all checks pass, usage instructions are displayed. The Continue button is greyed out until all checks pass.

### Auto-harvest Data
Saves every race session to the database. Builds history of lap times vs AI ratios.

### Auto-calculate Ratios
When enabled: detects race results → analyzes historical data → fits curve `T = a/R + b` → updates AIW file.

### Outlier Detection (New)
Automatically filters out anomalous data points when auto-fitting curves:

| Method | Description | Default Threshold |
|--------|-------------|-------------------|
| Standard Deviation | Removes points with error > mean + N*std_dev | 2.0 |
| IQR (Interquartile Range) | Removes points with error > Q3 + multiplier*IQR | 1.5 |
| Percentile | Removes points above specified percentile | 90% |

Configure in `cfg.yml`:
outlier_method: std      # std, iqr, percentile, or none
outlier_threshold: 2.0   # Method-specific threshold
outlier_min_points: 3    # Minimum points before attempting detection

When outliers are detected, a message shows how many were removed from the fit.

### AI Target Positioning

TBD

### Manual Controls
- Edit ratios directly (Edit button)
- Revert to previous ratio (Revert button)
- Calculate ratio from lap time
- Save formulas manually

---

## Advanced Features

### Data Management
- Filter by track/vehicle class
- Visualize curves and data points
- Edit a/b parameters
- Auto-fit curve with outlier detection
- **Launch Dyn AI Data Manager** - Button to open external vehicle class management tool

### AI Target Analysis (Advanced → AI Target)
- **Warning banner** indicates feature is under construction
- Position your lap time within AI range (percentage or fixed offset)
- Apply error margin to make AI slightly slower
- **Dump Analysis buttons** save detailed calculation logs for debugging
- All settings applied to both Qualifying and Race sessions

### AIW Backup Restore
Automatic backups (`*_ORIGINAL.AIW`). Restore individual or all tracks.

### Log Viewer
Filter by ERROR/WARNING/INFO/DEBUG/ALL levels.

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
base_path: C:\GTR2
db_path: ai_data.db
poll_interval: 5.0
min_ratio: 0.5
max_ratio: 1.5
autopilot_enabled: true
outlier_method: std
outlier_threshold: 2.0
outlier_min_points: 3

---

## Tips

- More laps = better curve fit
- Formulas stored per track AND car class
- Error margin (0.5-1.0s) makes AI slightly slower
- Auto-calculate Ratios must be ON for automatic updates
- Use Dump Analysis buttons to debug AI Target calculations
- Track name must be selected before AI ratios are displayed
- Outlier detection helps ignore crashes or anomalous laps when auto-fitting

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| "No base path configured" | Set `base_path` in cfg.yml |
| AI ratios not updating | Enable Auto-calculate Ratios (green) |
| Can't find AIW file | Verify GTR2 path and track folder exists |
| Ratio outside limits | Adjust `min_ratio`/`max_ratio` in cfg.yml - THIS MAY PRODUCE MAYHEM |
| No ratios shown on main screen | Select a track first via Advanced → Data Management |
| AIW file has malformed ratios | Fixed in v1.0.6 - now adds each ratio on separate line |
| Wrong track AIW gets updated (e.g., Donington 2003 updates Donington 2004) | See Known Issues below |
| "Extra Stats" error in pre-run checks | Set `Extra Stats="0"` in your GTR2 PLR file (use Fix PLR File button) |
| Auto-fit includes bad laps | Enable outlier detection in cfg.yml (outlier_method: std) |

---

## Known Issues

### Track Name Matching Problem

**Symptom:** When racing on Donington 2003, the Donington 2004 AIW file gets updated instead.

**Root Cause:** The application uses case-insensitive partial matching to find AIW files. It searches for a folder name containing the track name. For "Donington 2003", it finds "Donington 2004" because "Donington" matches both.

**How track matching works:**
1. `raceresults.txt` contains `Scene=...\Testtrack2\Testtrack2.TRK`
2. The parser extracts `Testtrack2` as the track folder name
3. The application looks for a folder in `GameData/Locations/` with matching name
4. It uses `if track_dir.name.lower() == track_lower` for exact matching
5. If not found, it falls back to `if track_lower in track_dir.name.lower()` (partial match)

**Current Fix in v1.0.7:** The matching logic now prioritizes exact folder name matching before falling back to partial matching. This should resolve the issue for most cases.

**If you still experience the issue:**
- Ensure your track folder names in `GameData/Locations/` are unique and descriptive
- For conflicting tracks (e.g., "Donington" vs "Donington 2003" vs "Donington 2004"), consider renaming folders or using the exact match in `raceresults.txt`

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

**Outlier Detection (New):**
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

- AI Target settings now apply to **ALL** ratio calculations (auto-ratio, manual edits, advanced dialog)
- Added ratio limits (`min_ratio`/`max_ratio` in cfg.yml) with warning popups
- Fixed TypeError when AI times are None
- AIW not found now shows GUI error popup
- Auto-Fit no longer auto-calculates ratio (button turns orange until clicked)
- Added Revert buttons to main screen panels
- Added manual lap time editing in Advanced → Data Management
- Target indicator moved to status bar with quick-configure button
