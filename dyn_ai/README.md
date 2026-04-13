# dyn_ai — Live AI Tuner for GTR2 - v0.9.10

This tool watches your race results and helps you tweak the AI difficulty ratios so they match your pace.

---

## Current State

Buggy, but not unusable.

Still: USE IT AT YOUR OWN RISK, probably on a SEPARATED DROP and please, ping me with as many bugs as you can.

---

## Quick Start

**Windows (easy mode):**  
Open dyn_ai.zip, grab the `.exe` from the zip, run it, done.

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
3. When the session ends(click on "Continue"), the tool picks up `raceresults.txt` automatically
4. It shows you the current ratios, your lap times...
5. Hit on "Save to Historic.csv" to have the data added. The more data the easier it will be to get your curve right.
6. Click on "Open GLobal Curve Editor", and play around with the parameters until you make a curve that fits your points.
7. Hit on "Apply to AI Tuner"
8. Calculate for Quali and/or Race ratios
9. When you are ready, choose which one to apply and... hit **Apply Selected Changes**
10. Repeat after every session (the more data, the more obvious the curve will become, the less you will have to change the formula)

---

## What You Can Do

- **Auto-tune AI ratios** (QualRatio + RaceRatio) per track based on your actual lap times
- **Autopilot mode** — set it and forget it, ratios update after every session - This needs AT LEAST to have the curve correctly set once.
- **Backups** — your original AIW file is backed up once before any changes, never overwritten
- **Restore original** — one click to undo everything and go back to stock
- **Manual override** — punch in your own ratio values if you know what you're doing
- **Per-track formulas** — drop custom formula files in `track_formulas/` for specific tracks

---

## How the Idea Works

It just creates a formula that matches Ratio (qualratio and raceratio from the Track's AIW) with the AI's laptimes.

The GUI itself shows the parameters being used for that.

The idea is that you add your laptime (or it is read automatically from a session) and it can calculate the required ratio for the AI to be around your laptime.

For that it uses the middle point between best and worst times from the AI, so there is some kind of error rate accepted, which makes sense.

To help the calculations, make sure you enter the "Global Curve Editor" and understand how the values will be calculated.

---

## Config (`cfg.yml`)

| Key | What it does |
|---|---|
| `base_path` | Path to your GTR2 install |
| `auto_apply` | Apply changes without asking - Don't do that just yet|
| `autopilot_enabled` | Full auto mode - Avoid this as well |
| `backup_enabled` | Keep original AIW backups - keep this on |
| `logging_enabled` | Write a log file |
| `formulas_dir` | Where track formula files live |

---

## Known issues
- It is still slow-ish
- It needs some babysitting - Get data, check the graph editor, save... 
- The Autopilot sort of works, but needs constant attention, you should probably not make it fully silent
- The autofit curve does not always work and probably it should autocorrect the issues it finds (like a datapoint that makes no sense)
- A proper historic.csv for all tracks would be very good to have, regardless of car.
- The crosscompilation (linux to windows) seems to produce a good .exe BUT it does not always run on wine. I am using it instead of using pytohn though.
- A lot of logs are produced. It needs a way to lower the verbosity.

## Wishlist
- We need a way to not always set the middle point in terms of laptime. E.g.: "I want a ratio that makes my laptime top-ten" or "I want to be 0.5 secs faster than the fastest AI". The idea is to adapt the challenge
- We should also keep the formulas or the historic, there is some duplicated data there.
- On those formulas: we should probably make better use of them. Have a working curve for Monza on a car? reuse it for a different car consciously, adapt only if it doesn'T work.

## TODO NEXT
- Simplify code A LOT
- one Gui that is simple and works.
  - simplify what is seen even more, give stuff proper name
  - Improve list of tracks, show current
  - show only lines for the data enabled - unknown on all
- establish a way to automagically find the best formula with just one or two data points
- Focus program on an approximation: what ratios do we need for a given Laptime?
