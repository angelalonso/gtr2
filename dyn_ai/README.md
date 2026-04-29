# dyn_ai — Live AI Tuner for GTR2 - v1.0.5

## What it does

Automatically adjusts AI difficulty to match your driving pace. Reads your lap times, calculates optimal AI speed ratio, and updates the track's AIW file.

---

## Current State

Usable, but needs some babysitting.

**USE AT YOUR OWN RISK.** Test on a separate install.

---

## Quick Start

1. Edit `cfg.yml` and `vehicle_classes.json` if needed
2. Run the application
3. Point it to your GTR2 install folder (with `GameData/`) - saved to `cfg.yml`

**Windows (easy):** Run the `.exe` from the zip  
**From source:**

pipenv install
pipenv run python3 dyn_ai.py

---

## Main Features

### Auto-harvest Data
Saves every race session to the database. Builds history of lap times vs AI ratios.

### Auto-calculate Ratios
When enabled: detects race results → analyzes historical data → fits curve `T = a/R + b` → updates AIW file.

### AI Target Positioning

⚠️ **WARNING: UNDER CONSTRUCTION** - Use with caution ⚠️

Controls where your lap time falls within AI range:

| Mode | Effect |
|------|--------|
| Percentage | 0% = fastest AI, 50% = middle, 100% = slowest AI |
| Seconds from fastest | Fixed offset from best AI time |
| Seconds from slowest | Fixed offset from worst AI time |

**Applied to ALL ratio calculations** (Auto-ratio, Manual edits, Advanced dialog)

**Dump Analysis:** Click "📊 Dump Qual Analysis" or "📊 Dump Race Analysis" in the AI Target tab to save detailed calculation logs to `ai_target_dumps/`

### Manual Controls
- Edit ratios directly (✎ button)
- Calculate ratio from lap time
- Save formulas manually

---

## Advanced Features

### Data Management
- Filter by track/vehicle class
- Visualize curves and data points
- Edit a/b parameters
- Auto-fit curve to data
- Delete individual data points

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
| cfg.yml | Configuration (GTR2 path, min/max ratio limits, etc.) |
| ai_data.db | SQLite database (data points, formulas) |
| vehicle_classes.json | Maps vehicle names to classes |
| aiw_backups/ | Original AIW backups |
| ai_target_dumps/ | Detailed calculation logs from Dump Analysis buttons |

---

## Tips

- More laps = better curve fit
- Formulas stored per track AND car class
- Error margin (0.5-1.0s) makes AI slightly slower
- Auto-calculate Ratios must be ON for automatic updates
- Use Dump Analysis buttons to debug AI Target calculations

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| "No base path configured" | Set `base_path` in cfg.yml |
| AI ratios not updating | Enable Auto-calculate Ratios (green) |
| Can't find AIW file | Verify GTR2 path and track folder exists |
| Ratio outside limits | Adjust `min_ratio`/`max_ratio` in cfg.yml |
| AI Target calculations not working | Feature is under construction - use Dump Analysis to see what's happening |

---

## Changelog v1.0.5

- **AI Target warning banner** - Red warning added to indicate feature is under construction
- **Improved AIW error handling** - Better error messages with "Configure GTR2 Path" button, prevents frontend changes when AIW not found
- **Dump Analysis moved to AI Target tab** - Removed from main screen, now available in Advanced → AI Target
- **Resizable main window fix** - Race and Quali panels now resize properly with window, buttons stay at bottom
- **Fixed dump_analysis crash** - Resolved "'RedesignedMainWindow' object is not callable" error

## Changelog v1.0.4

- AI Target settings now apply to **ALL** ratio calculations (auto-ratio, manual edits, advanced dialog)
- Added ratio limits (`min_ratio`/`max_ratio` in cfg.yml) with warning popups
- Fixed TypeError when AI times are None
- AIW not found now shows GUI error popup
- Auto-Fit no longer auto-calculates ratio (button turns orange until clicked)
- Added Revert buttons to main screen panels
- Added manual lap time editing in Advanced → Data Management
- Target indicator moved to status bar with quick-configure button
