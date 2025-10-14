#!/usr/bin/env bash
set -euo pipefail
export DRY_RUN=1
python scripts/canary.py --config "${1:-configs/example_mom12_1.yaml}"
