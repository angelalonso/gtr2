# What is this?

Program to modify Tracks to make AI be faster or slower both in Qualy and in the Race.

# How does it work?
## Python version (official)
- Install python dependencies:
'pipenv install; pipenv install PyQt5 pyyaml'
- Run the program:
'pipenv run python3 ai_track_tuner.py'
## Windows exe version (just a test version)
- Click on ai_track_tuner.exe


## Both
- Choose your GTR2 installation folder to search from (unless you did it already)
- Modify the track you want
- Once you save it, a backup of the original will be kept on backup_originals

# Ratio Calculator - Quick Explanation

The calculator determines how much to adjust AI speed so your lap time falls at a specific position within the AI range.

Current Position = ((Your Time - Best AI) / (Worst AI - Best AI)) × 100%
Target Position = Goal Percent + Goal Offset
Position Shift = Target - Current
New Ratio = Current Ratio + (Position Shift × Percent Ratio)

Example
    Best AI: 1:40, Worst AI: 2:00, Your time: 1:50
    Current position = 50%
    Target = 75%
    Shift = +25%
    New Ratio = 1.00 + (25 × 0.01) = 1.25

Parameters
    Goal Percent: Where you want to be (0-100%, with 0 being the best lap)
    Goal Offset: Fine-tuning adjustment - Useful to put goal outside of the range, accepts also negatives
    Percent Ratio: Ratio change per 1% shift (default 0.01)

# NEXTUP / WISHLIST
- Test if changing AIW while GTR2 is running modifies the game without having to close and reopen.
- If so, look for a way to detect a session results on the fly
- Link everything together and see how a session modifies the next one
