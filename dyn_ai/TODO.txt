# TO DO

## Code Improvements

- Make a more stable use of track names and selection
- When opening Setup or Graph/Visualizer, the user should know it is loading (disable the button).
- Extract hardcoded values - Move DEFAULT_A_VALUE (32.0), ratio bounds (0.3-3.0), b limits (10-200), and plot ranges to configuration file.
- Implement async database operations - Replace blocking SQLite calls with a queue-based system to prevent UI freezes.
- Improve outlier detection - Currently runs only during auto-fit. Extend to real-time data point addition.
- Add formula versioning - Track formula history per (track, class, session) to allow reverting.
- Implement session merging - When multiple qualifying sessions occur for same track/class, merge data points intelligently.
- Code should be smaller; executable files should all be under 50MB.

## Feature Additions

- Add the possibility to import raceresults when the user has extra stats=1.
- Add an AI-target: let the user decide if their time should be top 10% of AI laptimes, or bottom 25%, etc.
- Investigate the use of weather (probably can be gotten from some files as well) to improve data.
- Investigate the use of the variable aiRange and what it does.
- Multi-vehicle per session support - Currently each race data point stores only user's vehicle class. Add ability to track and learn from all AI vehicles in the session.
- Export/import formulas - Add JSON export of all formulas for sharing or backup.
- Track-specific a parameter - Allow a to vary per track rather than global constant.
- Real-time ratio adjustment - While GTR2 is running, apply ratio changes immediately if the sim supports hot-reloading AIW files.
- Performance graph overlay - In visualizer, show predicted vs actual lap times as scatter plot with regression line.
- Command-line interface - Add CLI mode for batch processing race results without GUI.

## Performance & Reliability

- Add connection pooling for SQLite - Reuse database connections across threads.
- Implement file monitoring fallback - If inotify (Linux) or ReadDirectoryChangesW (Windows) is available, use it instead of polling.
- Add validation for AIW file integrity - Before writing ratio, verify file is not corrupted.
- Implement graceful degradation - If AIW file cannot be found, show warning but continue monitoring.

## Testing & Documentation

- Test the pre-check tests themselves.
- Add more unit tests - Core formula calculations, AIW parsing, data extraction, and outlier detection.
- Add "perfect data" to simulation testing - Data that should produce Ratios of 0.5, 1.0, 1.5, etc. Also test median formula with multiple laptimes.
- Expand logging - Add debug-level logging for all regex operations, file searches, and database queries.
- Create schema migration system - Database schema changes currently require manual intervention or fresh database.
