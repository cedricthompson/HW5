#!/bin/sh
# Start the campus-customs MCP server with the project's Python env (.venv).
cd "$(dirname "$0")/.." || exit 1
if [ -x .venv/bin/python ]; then exec .venv/bin/python mcp_server/server.py; fi
echo "No Python env found. Run: python3 -m venv .venv && .venv/bin/pip install -r requirements.txt" >&2
exit 1
