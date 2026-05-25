#!/usr/bin/env bash
set -euo pipefail

# Run repository test suite
exec python -m pytest tests -v
