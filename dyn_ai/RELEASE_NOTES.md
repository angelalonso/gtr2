# v1.1.0

Previous release notes are now obsolete since this is to a great extent a new program.

## Goals of this restart:

- Take back control of the code
- Make smaller, more lightweight executables
- Polish the user's experience
  - This is limited by having to produce 3 different programs instead of integrating everything in one.
  - On the other hand, the main program now only does one thing (hopefully better).

## Improvements

- I added a pre-run checks to guide the user a bit.
- I separated configuration/logging/imports screens into a program of its own.
- I "downgraded" most of the visuals to avoid having a 100M program that takes forever to start
- I streamlined repeated libraries and cleand up code (still doing that)
- I cleaned up the wine/cross-compilation to remove unused Libraries.
  - I also separated files to avoid loading unnecessary libraries (e.g.: PyQt5 on a program that only uses tkinter)
  - additionally I added compression
  - All this was done to avoid hitting github/gitlab limits of file size.
  - only the visualizer is now bigger than 50Mb, because it depends on things like Qt5

