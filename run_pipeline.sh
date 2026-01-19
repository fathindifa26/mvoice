#!/usr/bin/env bash
set -euo pipefail

# Simple runner for MVoice pipeline on a VM
# Usage: ./run_pipeline.sh [--batch-size N] [--headless] [-d]

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

BATCH_SIZE=10
DELETE_AFTER=true
EXTRA_ARGS=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --batch-size)
      BATCH_SIZE="$2"; shift 2;;
    --no-delete)
      DELETE_AFTER=false; shift;;
    --headless)
      EXTRA_ARGS+=("--headless"); shift;;
    *)
      EXTRA_ARGS+=("$1"); shift;;
  esac
done

if [ ! -d ".venv" ]; then
  echo "Virtualenv not found. Run ./bootstrap.sh first." >&2
  exit 1
fi

source .venv/bin/activate

for f in auth_state.json data.csv; do
  if [ ! -f "$f" ]; then
    echo "Required file missing: $f" >&2
    echo "Please upload $f to this directory (scp from local machine)." >&2
    exit 1
  fi
done

SESSION_NAME="mvoice"
CMD=""

# Prefer xvfb-run if available
if command -v xvfb-run >/dev/null 2>&1; then
  CMD="xvfb-run -s \"-screen 0 1920x1080x24\" python pipeline.py --batch-size ${BATCH_SIZE}"
else
  CMD="python pipeline.py --batch-size ${BATCH_SIZE}"
fi

# Respect delete option
if [ "$DELETE_AFTER" = false ]; then
  CMD+=" --no-delete"
fi

# Append extra args like --headless
for a in "${EXTRA_ARGS[@]}"; do
  CMD+=" $a"
done

echo "Starting pipeline in tmux session: $SESSION_NAME"
echo "Command: $CMD"

if tmux ls | grep -q "^${SESSION_NAME}:" 2>/dev/null; then
  echo "Tmux session $SESSION_NAME already exists. Attaching..."
  tmux attach -t "$SESSION_NAME"
else
  tmux new -d -s "$SESSION_NAME" bash -lc "$CMD; echo \"Pipeline finished (exit=$?)\"; sleep 5"
  echo "Started detached tmux session '$SESSION_NAME'. To view logs: tmux attach -t $SESSION_NAME"
fi
