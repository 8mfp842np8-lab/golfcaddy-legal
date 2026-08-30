#!/usr/bin/env python3
"""Startet den Kickbase-MCP-Server unabhaengig vom Arbeitsverzeichnis."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from kickbase_mcp.server import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
