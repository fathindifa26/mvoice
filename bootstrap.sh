#!/usr/bin/env bash
set -euo pipefail

# Bootstrap script for Ubuntu/Debian VMs
# Installs system packages, creates venv, installs Python deps and Playwright browsers

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

echo "== MVoice bootstrap starting in $ROOT_DIR =="

echo "1) Updating apt and installing base system packages (sudo may be required)"
sudo apt-get update
sudo apt-get install -y \
  python3 python3-venv python3-pip xvfb tmux curl wget ca-certificates gnupg build-essential \
  libnss3 libatk-bridge2.0-0 libx11-xcb1 libxcomposite1 libxdamage1 libxrandr2 libgbm1 \
  libpangocairo-1.0-0 libxss1 fonts-liberation libasound2 || true

echo "2) Creating virtual environment .venv (if missing)"
if [ ! -d ".venv" ]; then
  python3 -m venv .venv
fi

echo "3) Activating virtualenv and installing Python requirements"
source .venv/bin/activate
python -m pip install --upgrade pip
if [ -f requirements.txt ]; then
  pip install -r requirements.txt
else
  echo "No requirements.txt found. Please ensure dependencies are installed." >&2
fi

echo "4) Installing additional system libraries required by Playwright"
# These packages satisfy Playwright browser dependencies on Ubuntu/Debian
sudo apt-get install -y \
  libgtk-3-0 libgdk-pixbuf2.0-0 libxcursor1 libcairo2 libxcb1 libxkbcommon0 libxcb-dri3-0 || true

echo "5) Ensure Playwright Python package and browsers are installed in venv"
if [ -f ".venv/bin/activate" ]; then
  # activate venv and install playwright package + browsers
  # shellcheck disable=SC1091
  source .venv/bin/activate
  python -m pip install --upgrade pip || true
  python -m pip install playwright || true
  # Install the browser binaries (into the user's cache)
  python -m playwright install || true
  # Try Playwright helper to install missing system deps (may require sudo)
  # Use the Playwright CLI from the virtualenv so sudo finds the correct script
  if [ -x ".venv/bin/playwright" ]; then
    sudo .venv/bin/playwright install-deps chromium || true
  else
    echo "Playwright CLI not found in .venv; skipping install-deps (you can run: sudo .venv/bin/playwright install-deps chromium)" >&2
  fi
fi

echo "5) Make helper script executable"
if [ -f run_pipeline.sh ]; then
  chmod +x run_pipeline.sh
fi

echo
echo "Bootstrap complete. Next steps:"
echo "- Upload the following files into this project directory on the VM (mandatory):"
echo "    1) auth_state.json"
echo "    2) data.csv"
echo
echo "Example from your local machine (replace user@host and path):"
echo "  scp auth_state.json data.csv user@server:/home/user/MVoice/"
echo
echo "After uploading, run the pipeline with the helper script:"
echo "  ./run_pipeline.sh --batch-size 10"

# Check for required files and print status
missing=0
for f in auth_state.json data.csv; do
  if [ ! -f "$f" ]; then
    echo "[MISSING] $f"
    missing=1
  else
    echo "[OK]     $f"
  fi
done

if [ $missing -ne 0 ]; then
  echo
  echo "Please upload the missing files and re-run ./run_pipeline.sh when ready." >&2
  exit 0
fi

echo
echo "All required files present. You can now run ./run_pipeline.sh to start the pipeline."
