"""Pytest configuration.

The codebase uses absolute imports like `from app...`.
When running tests from the `backend/` folder without packaging the project,
Python may not automatically include this folder on `sys.path`.

This keeps local dev/testing friction low by ensuring `backend/` is on sys.path.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
