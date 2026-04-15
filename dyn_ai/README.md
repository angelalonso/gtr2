# dyn_ai — Live AI Tuner for GTR2 - v0.9.13

This tool watches your race results and helps you tweak the AI difficulty ratios so they match your pace.

---

## Current State

Buggy, but not unusable.

Still: USE IT AT YOUR OWN RISK, probably on a SEPARATED DROP and please, ping me with as many bugs as you can.

---

## Quick Start

**Windows (easy mode):**  
Open dyn_ai_v0.9.13.zip, grab the `.exe` from the zip, run it, done.

**From source:**
```bash
pipenv install
pipenv run python3 dyn_ai.py
```

First launch will ask you to point it at your GTR2 install folder (the one that has `GameData/` in it). It saves that to `cfg.yml` so you only do this once.

---

## How to Use It

1. Launch the tool — GUI pops up
2. Go race (qual + race)
3. When the session ends (click on "Continue"), the tool picks up `raceresults.txt` automatically
4. It shows you the current ratios, your lap times...
5. Hit on "Save to Historic.csv" to have the data added. The more data the easier it will be to get your curve right.
6. Click on "Open Global Curve Editor", and play around with the parameters until you make a curve that fits your points.
7. Hit on "Apply to AI Tuner"
8. Calculate for Quali and/or Race ratios
9. When you are ready, choose which one to apply and... hit **Apply Selected Changes**
10. Repeat after every session (the more data, the more obvious the curve will become, the less you will have to change the formula)

---

## What You Can Do

- **Auto-tune AI ratios** (QualRatio + RaceRatio) per track based on your actual lap times
- **Autopilot mode** — set it and forget it, ratios update after every session
- **Backups** — your original AIW file is backed up once before any changes, never overwritten
- **Restore original** — one click to undo everything and go back to stock
- **Manual override** — punch in your own ratio values if you know what you're doing
- **Per-track formulas** — drop custom formula files in `track_formulas/` for specific tracks
- **Log Viewer** — separate window to see detailed logs without console clutter

---

## How Autopilot Determines the Formula

The autopilot uses a **smart template adaptation system**:

### Core Principle

- **Keep the slope (`a`)** from similar track/vehicle data
- **Only adjust the height (`b`)** to fit new data points
- This preserves the track characteristics learned from other sessions

### Formula: T = a / R + b

- `T` = Lap time (seconds)
- `R` = AI difficulty ratio (QualRatio or RaceRatio)
- `a` = Steepness (how sensitive the AI is to ratio changes)
- `b` = Base time (theoretical minimum lap time as ratio → infinity)

### Template Selection Hierarchy

When autopilot receives a new data point (R, T), it:

1. **Looks for existing formulas** for this track and vehicle class
2. **If none exist**, it tries in order:
   - Same track, same class, opposite session (qual ↔ race)
   - Same track, any class, same session (averages all formulas)
   - Any track, same class, same session (global by vehicle class)
   - Any track, any class, same session (global average)
   - Default formula (a=30.0, b=70.0)

3. **Adapts the template** by solving for `b`:

   `b_new = T_target - a_template / R_target`

4. **Saves the adapted formula** for future sessions

### Example "Train of Thought"


[INFO] Processing race data for track 'Monza', vehicle class 'GT Cars'
[INFO] [Qualifying] New data: R=0.8500, T=95.20s
[INFO] Single data point: R=0.8500, T=95.20s
[INFO] Using template: global average for GT Cars class (3 formulas)
[INFO]   Template: a=28.50, b=68.20
[DEBUG] Adjusting height: a=28.50 (unchanged), b=68.20 -> 71.67
[INFO] Adapted formula: T = 28.5000 / R + 71.6670
[INFO] New ratio needed: 0.9120 (was 0.8500)
[INFO] ✓ QualRatio updated in AIW


This approach means:
- **First data point** → uses default formula, adapts height
- **Second+ data points** → builds a more accurate curve
- **Different vehicle classes** → share knowledge within class
- **Different tracks** → can transfer learning between similar tracks

---

## AI Target - Make Races Easier or Harder

This setting changes how fast the AI drivers are compared to you.

### What The Numbers Mean

| Setting | What Happens |
|---------|--------------|
| 100% | AI is exactly as fast as your best lap |
| 95% | AI is 5% SLOWER (you win easier) |
| 105% | AI is 5% FASTER (harder to win) |

### How It Works (Simple Version)

1. The game uses a math formula: `AI Lap Time = a / Ratio + b`
2. We know `a` and `b` from your past races (the yellow/orange curves)
3. We know your best lap time from the race
4. We pick a target AI time (your time × percentage)
5. We solve the formula backwards to find the new Ratio
6. The tool writes that Ratio to the AIW file

### Example

Your best lap: 90 seconds
Target: 95% (easier race)

Target AI time = 90 × 0.95 = 85.5 seconds

Formula says: 85.5 = 28 / Ratio + 68
So Ratio = 1.46

The tool sets RaceRatio = 1.46 in the AIW file
text


**Lower number = harder AI, Higher number = easier AI** (because Ratio works backwards)

---

## Graph Features

The graph shows **two curves**:
- **Yellow line** = Qualifying formula (`T = a_qual / R + b_qual`)
- **Orange line** = Race formula (`T = a_race / R + b_race`)

**Data points** are shown as:
- Yellow circles = Qualifying data points
- Orange squares = Race data points  
- Magenta triangles = Unknown type

**Filters** (buttons at bottom of control panel):
- **Quali** toggle → shows/hides the yellow qualifying curve AND qualifying data points
- **Race** toggle → shows/hides the orange race curve AND race data points
- **Unkn** toggle → shows/hides unknown data points

---

## Logging System

Logs are now handled cleanly:
- **Separate Log Window** (click "Show Log Window" button)
- **Log levels**: ERROR, WARNING, INFO, DEBUG, ALL
- **Filter by level** using dropdown
- **Adjust max lines** (100-10000)
- **Auto-scroll** option
- **Clear button** to reset display

Console output is minimized by default; use the log window for detailed debugging.

---

## Config (`cfg.yml`)

| Key | What it does |
|-----|---------------|
| `base_path` | Path to your GTR2 install |
| `auto_apply` | Apply changes without asking |
| `autopilot_enabled` | Full auto mode |
| `autopilot_silent` | Suppress autopilot popups |
| `backup_enabled` | Keep original AIW backups |
| `logging_enabled` | Write a log file |
| `formulas_dir` | Where track formula files live |
| `poll_interval` | How often to check for new results (seconds) |

---

## Known Issues

- The autofit curve doesn't always work perfectly
- The cross-compilation (linux to windows) produces a good .exe BUT it does not always run on wine
- Vehicle class detection relies on substring matching (can be improved)

## Wishlist

- Ability to target specific positions (e.g., "make me top-5" instead of midpoint)
  - There is a rough implementation on advanced
- Better formula sharing across similar tracks
- Export/import formulas for sharing between users
- A proper DB for all tracks would be very good to have

## TODO NEXT

- Simplify code A LOT
- One GUI that is simple and works
- Improve vehicle class detection with fuzzy matching
- Add ability to manually edit formulas directly

