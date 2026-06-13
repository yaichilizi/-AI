"""Compatibility entry point for the desktop app.

The implementation lives in main.py to avoid two divergent copies of the
same GUI and resume-analysis logic.
"""

from main import main


if __name__ == "__main__":
    main()
