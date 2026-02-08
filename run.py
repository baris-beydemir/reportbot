#!/usr/bin/env python3
"""Convenience script to run ReportBot."""

# Setup runtime paths for PyInstaller bundle (must be first!)
import src.runtime_helper  # noqa: F401

from src.main import main

if __name__ == "__main__":
    main()
