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

MISSING=()
for f in auth_state.json data.csv; do
  if [ ! -f "$f" ]; then
    MISSING+=("$f")
  fi
done

if [ ${#MISSING[@]} -ne 0 ]; then
  echo "Required files missing: ${MISSING[*]}"
  echo "Searching fallback locations (/root and \$HOME) for the missing files..."

  found_dir=""

  # Build candidate directories to search for uploaded files.
  # Include /root, current $HOME, the original sudo user's home (if run with sudo),
  # and every directory under /home.
  try_dirs=(/root "$HOME")
  if [ -n "${SUDO_USER:-}" ]; then
    try_dirs+=("/home/$SUDO_USER")
  fi
  for d in /home/*; do
    [ -d "$d" ] && try_dirs+=("$d")
  done

  # Deduplicate and ensure directories exist
  declare -A _seen_dirs
  unique_dirs=()
  for td in "${try_dirs[@]}"; do
    if [ -n "$td" ] && [ -d "$td" ] && [ -z "${_seen_dirs[$td]:-}" ]; then
      _seen_dirs[$td]=1
      unique_dirs+=("$td")
    fi
  done

  for try_dir in "${unique_dirs[@]}"; do
    ok=true
    for f in "${MISSING[@]}"; do
      if [ ! -f "$try_dir/$f" ]; then
        ok=false
        break
      fi
    done
    if [ "$ok" = true ]; then
      found_dir="$try_dir"
      break
    fi
  done

  if [ -n "$found_dir" ]; then
    echo "Found all missing files in: $found_dir"
    echo "Attempting to move files into project directory ($ROOT_DIR)..."
    for f in "${MISSING[@]}"; do
      src="$found_dir/$f"
      dest="$ROOT_DIR/$f"
      # Prefer mv if writable, otherwise use sudo cp
      if [ -w "$src" ]; then
        mv "$src" "$dest"
      else
        sudo cp "$src" "$dest"
        sudo chown "$(id -u):$(id -g)" "$dest" || true
      fi
      echo "Moved: $f -> $dest"
    done
  else
    echo "Could not find both files in fallback locations." >&2
    echo "Please upload auth_state.json and data.csv to this directory (scp from local machine)." >&2
    exit 1
  fi
fi

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
