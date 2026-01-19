#!/usr/bin/env bash
set -euo pipefail

# Bootstrap script for Ubuntu/Debian VMs
# Installs system packages, creates venv, installs Python deps and Playwright browsers

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

echo "== MVoice bootstrap starting in $ROOT_DIR =="

echo "1) Updating apt and installing system packages (sudo may be required)"
sudo apt-get update
sudo apt-get install -y python3 python3-venv python3-pip xvfb tmux curl wget ca-certificates gnupg build-essential libnss3 libatk-bridge2.0-0 libx11-xcb1 libxcomposite1 libxdamage1 libxrandr2 libgbm1 libpangocairo-1.0-0 libxss1 fonts-liberation libasound2 || true

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

echo "4) Installing Playwright browsers"
# playwright CLI is available after installing playwright package into venv
if command -v playwright >/dev/null 2>&1; then
  playwright install chromium || true
  # attempt to install system deps for chromium (may require sudo)
  if command -v playwright >/dev/null 2>&1; then
    playwright install-deps chromium || true
  fi
else
  echo "Playwright not available in venv; ensure 'playwright' is in requirements.txt" >&2
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
