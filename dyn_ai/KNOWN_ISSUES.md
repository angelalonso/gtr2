# Known Issues

- On dyn_ai_setup, if you modify vehicle_classes.json manually while the program runs, the lists will not be up to date. Reopen the application and it should be fine again.

- If you update the Ratio through the visualizer, the main dyn_ai does not get updated (but the file does).

- The track selection on dyn_ai and dyn_ai_visualizer does not use the same list.

- The import area is not stable enough; it has been barely tested.

- Sometimes the visualizer does not show current data and needs the "Refresh" button to be pushed.

- UI scaling on small screens - The Tkinter and PyQt5 interfaces do not scale well on low-resolution displays (e.g., 1366x768). Widgets may overlap, text may be cut off, and scroll areas are required for full access.

- Race results parsing fragility - The parser relies on specific formatting of raceresults.txt. If GTR2 produces non-standard output (mods, language packs, or corrupted files), extraction may fail silently or produce incomplete data.

- Vehicle class mismatches - The vehicle classification system depends on exact string matching between extracted Vehicle= field and entries in vehicle_classes.json. Slight naming differences cause misclassification or fallback to "Unknown".

- AIW file locking - If GTR2 is running and has the AIW file open, the program may be unable to write updated ratios. No retry mechanism exists.

- Concurrent database access - The file monitor runs in a background thread and may attempt to write to SQLite while the visualizer is reading. Occasional "database is locked" errors can occur.

- PLR file detection - The pre-run check expects Extra Stats = "0" but the PLR file may use different quoting styles or whitespace. The regex pattern handles common cases but may miss exotic formatting.

- Missing AIW ratios - Some track AIW files lack QualRatio or RaceRatio entries entirely. The program adds them with default 1.0, modifying the original file (though a backup is created first).

- Median calculation edge cases - With nr_last_user_laptimes set to 1, median equals the single value, providing no outlier protection.

