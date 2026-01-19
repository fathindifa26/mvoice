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

# Quick check: ensure Playwright browsers are installed in user cache; if missing, install inside venv
# Do NOT run system-level deps here (bootstrap should handle that).
PLAYWRIGHT_CACHE_DIR="$HOME/.cache/ms-playwright"
need_playwright_install=false
if [ ! -d "$PLAYWRIGHT_CACHE_DIR" ]; then
  need_playwright_install=true
else
  # crude check for chromium executable
  if ! ls "$PLAYWRIGHT_CACHE_DIR"/*/chrome* >/dev/null 2>&1; then
    need_playwright_install=true
  fi
fi

if [ "$need_playwright_install" = true ]; then
  echo "Playwright browsers not found in cache — attempting 'python -m playwright install' (inside venv). This may take a few minutes..."
  # Ensure playwright package is installed
  python -m pip install --upgrade pip setuptools wheel >/dev/null 2>&1 || true
  python -m pip install playwright >/dev/null 2>&1 || true
  # Install browsers (non-root). If this fails, user should run bootstrap.sh manually.
  if python -m playwright install >/dev/null 2>&1; then
    echo "Playwright browsers installed." 
  else
    echo "Warning: 'playwright install' failed. Run 'python -m playwright install' or run bootstrap.sh." >&2
  fi
fi

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
  # add -- to separate xvfb-run options from the command
  CMD="xvfb-run -s \"-screen 0 1920x1080x24\" -- python pipeline.py --batch-size ${BATCH_SIZE}"
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

# Determine user context for tmux: if run with sudo, use the original user ($SUDO_USER)
IS_ROOT=false
if [ "$(id -u)" -eq 0 ]; then
  IS_ROOT=true
fi

if [ "$IS_ROOT" = true ] && [ -n "${SUDO_USER:-}" ]; then
  RUN_USER="$SUDO_USER"
else
  RUN_USER="$(id -un)"
fi

# TMUX_PREFIX will run tmux commands as RUN_USER when needed
TMUX_PREFIX=()
if [ "$IS_ROOT" = true ] && [ "$(id -un)" = "root" ] && [ "$RUN_USER" != "root" ]; then
  TMUX_PREFIX=(sudo -u "$RUN_USER")
fi

# Use tmux from the correct user context
if "${TMUX_PREFIX[@]}" tmux ls 2>/dev/null | grep -q "^${SESSION_NAME}:"; then
  echo "Tmux session $SESSION_NAME already exists. Attaching..."
  "${TMUX_PREFIX[@]}" tmux attach -t "$SESSION_NAME"
else
  # Create a small wrapper that activates venv and runs the command, appending logs
  WRAPPER="$ROOT_DIR/.run_pipeline_cmd.sh"
  cat > "$WRAPPER" <<EOF
#!/usr/bin/env bash
set -euo pipefail
cd "$ROOT_DIR"
if [ -f ".venv/bin/activate" ]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
fi
echo "=== RUN START \\$(date) (user=\\$(id -un)) ===" >> mvoice.log
echo "PATH=\\$PATH" >> mvoice.log
echo "Running: python pipeline.py --batch-size ${BATCH_SIZE} ${EXTRA_ARGS[*]}" >> mvoice.log

if command -v xvfb-run >/dev/null 2>&1; then
  echo "Using xvfb-run" >> mvoice.log
  xvfb-run -s "-screen 0 1920x1080x24" -- python pipeline.py --batch-size ${BATCH_SIZE} ${EXTRA_ARGS[*]} >> mvoice.log 2>&1 || echo "EXIT:$? at $(date)" >> mvoice.log
else
  echo "xvfb-run not found, running without Xvfb" >> mvoice.log
  python pipeline.py --batch-size ${BATCH_SIZE} ${EXTRA_ARGS[*]} >> mvoice.log 2>&1 || echo "EXIT:$? at $(date)" >> mvoice.log
fi

echo "=== RUN END $(date) ===" >> mvoice.log
EOF

  chmod +x "$WRAPPER"
  # Ensure wrapper ownership matches RUN_USER when using sudo
  if [ "$IS_ROOT" = true ] && [ -n "${SUDO_USER:-}" ] && [ "$RUN_USER" != "root" ]; then
    sudo chown "$RUN_USER":"$RUN_USER" "$WRAPPER" || true
  fi

  # Start wrapper inside tmux (as RUN_USER if needed)
  "${TMUX_PREFIX[@]}" tmux new -d -s "$SESSION_NAME" bash -lc "$WRAPPER; echo \"Wrapper finished (exit=\$?)\"; sleep 5"

  # Give tmux a moment to start; if the session disappears immediately, run in foreground for diagnostics
  sleep 3
  if ! "${TMUX_PREFIX[@]}" tmux ls 2>/dev/null | grep -q "^${SESSION_NAME}:"; then
    echo "Tmux session failed to start or exited immediately. Running pipeline in foreground for diagnostics..."
    echo "Command: $CMD"
    # Run wrapper in foreground (so logs are produced and visible)
    bash "$WRAPPER" 2>&1 | tee mvoice.log
    exit_code=${PIPESTATUS[0]:-0}
    echo "Foreground wrapper finished with exit=$exit_code"
    exit $exit_code
  else
    echo "Started detached tmux session '$SESSION_NAME'. To view logs: ${TMUX_PREFIX:+run as $RUN_USER }tmux attach -t $SESSION_NAME"
  fi
fi
