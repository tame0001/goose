#!/bin/bash

# Change directory to the location of the script
cd "$(dirname "$0")"
# Run the TUI using uv
uv run python main.py
