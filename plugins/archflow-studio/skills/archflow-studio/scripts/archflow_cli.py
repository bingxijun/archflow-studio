#!/usr/bin/env python3
"""Run the bundled ArchFlow CLI without installing a Python package."""

from archflow.cli import main


if __name__ == "__main__":
    raise SystemExit(main())
