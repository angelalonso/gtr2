# v1.1.0

Previous release notes are now obsolete since this is to a great extent a new program.

## Goals of this restart:

- Take back control of the code
- Make smaller, more lightweight executables
- Polish the user's experience
  - This is limited by having to produce 3 different programs instead of integrating everything in one.
  - On the other hand, the main program now only does one thing (hopefully better).

## Improvements

- Added pre-run checks to guide the user.
- Separated configuration/logging/imports screens into a program of its own.
- "Downgraded" most of the visuals to avoid having a 100M program that takes forever to start.
- Streamlined repeated libraries and cleaned up code.
- Refactored main window into modular components: track selector and ratio panel are now separate files.
- Cleaned up wine/cross-compilation to remove unused Libraries.
  - Separated files to avoid loading unnecessary libraries (e.g., PyQt5 on a program that only uses tkinter).
  - Added compression.
  - All this was done to avoid hitting github/gitlab limits of file size.
  - Only the visualizer is now bigger than 50MB, because it depends on things like Qt5.
