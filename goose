#!/usr/bin/env bash

# Resolve the absolute path of this script's directory, following symlinks
PROJECT_DIR="$(dirname "$(realpath "$0")")"

# Execute make inside the project directory, forwarding all arguments
exec make -C "$PROJECT_DIR" "$@"
