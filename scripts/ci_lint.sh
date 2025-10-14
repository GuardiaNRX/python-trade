#!/usr/bin/env bash
set -euo pipefail
ruff check .
vulture . --min-confidence 80 --whitelist vulture_whitelist.py --exclude backtests/results,backtests/reports,data/http_cache,data/source_snapshots,data/cache
echo "Lint OK"
