#!/usr/bin/env bash
set -euo pipefail

# Minimal runner: activate venv, create detached tmux session and run pipeline
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

# Optional first arg is batch size
BATCH_SIZE="${1:-10}"

if [ ! -d ".venv" ]; then
  echo "Virtualenv not found. Run ./bootstrap.sh first." >&2
  exit 1
fi

# Activate venv
# shellcheck disable=SC1091
source .venv/bin/activate

echo "Starting pipeline in detached tmux session: mvoice"
echo "Command: xvfb-run python pipeline.py --batch-size $BATCH_SIZE"

# Start tmux detached session running pipeline (uses xvfb-run)
tmux new -d -s mvoice bash -lc "xvfb-run python pipeline.py --batch-size $BATCH_SIZE"

echo "Started detached tmux session 'mvoice'. To attach: tmux attach -t mvoice"

