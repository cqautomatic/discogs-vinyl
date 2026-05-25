#!/usr/bin/env bash
set -euo pipefail

# Run the SiS Streamlit app locally for validation
APP="$(cd "$(dirname "$0")"/.. && pwd)/streamlit_app_sis.py"
exec streamlit run "$APP" --server.headless true
