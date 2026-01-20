#!/usr/bin/env bash
set -euo pipefail

# Minimal bootstrap for Ubuntu/Debian per user request.
# Runs system updates, installs Python/xvfb/tmux, creates venv,
# installs Python deps and Playwright browsers.

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

echo "== Minimal MVoice bootstrap starting in $ROOT_DIR =="

echo "1) Update system packages"
sudo apt-get update
sudo apt-get upgrade -y

echo "2) Install Python and essentials"
sudo apt-get install -y python3 python3-pip python3-venv

echo "3) Install virtual display and tmux"
sudo apt-get install -y xvfb tmux

echo "4) Create virtualenv"
if [ ! -d ".venv" ]; then
  python3 -m venv .venv
fi

echo "5) Activate venv and install Python requirements"
# shellcheck disable=SC1091
source .venv/bin/activate
python -m pip install --upgrade pip
if [ -f requirements.txt ]; then
  pip install -r requirements.txt
else
  echo "No requirements.txt found. Please ensure dependencies are installed." >&2
fi

echo "6) Install Playwright Python package and browsers"
python -m pip install --upgrade pip
python -m pip install playwright || true
# Install browser binaries into the current user's cache
python -m playwright install || true
# Install system deps for Chromium (may require sudo)
if [ -x ".venv/bin/playwright" ]; then
  echo "Installing Playwright system deps for chromium (may prompt for sudo)"
  sudo .venv/bin/playwright install-deps chromium || true
else
  echo "Playwright CLI not found in .venv; skipping install-deps. You can run: sudo .venv/bin/playwright install-deps chromium" >&2
fi

echo "7) Make helper script executable"
if [ -f run_pipeline.sh ]; then
  chmod +x run_pipeline.sh || true
fi

echo
echo "Bootstrap finished. Next steps:" 
echo "  1) Upload auth_state.json and data.csv into $ROOT_DIR"
echo "  2) Run ./run_pipeline.sh --batch-size 10"

exit 0