#!/usr/bin/env bash
# Bootstrap script for a fresh Ubuntu 22.04+ EC2 instance.
# ponytail: no Docker, no nginx, no CI/CD pipeline for a single-instance demo
# — a venv and two systemd units are the whole deployment.
set -euo pipefail

REPO_URL="https://github.com/AmanDataGuy/parcelpilot-support-agent.git"
APP_DIR="${HOME}/parcelpilot"

sudo apt-get update -y
sudo apt-get install -y python3-venv python3-pip git

if [ ! -d "$APP_DIR" ]; then
  git clone "$REPO_URL" "$APP_DIR"
fi
cd "$APP_DIR"

python3 -m venv .venv
./.venv/bin/pip install --upgrade pip
./.venv/bin/pip install -r backend/requirements.txt -r frontend/requirements.txt

if [ ! -f .env ]; then
  cp .env.example .env
  echo
  echo "Created $APP_DIR/.env — edit it and set GEMINI_API_KEY before starting services."
fi

echo
echo "Setup complete. Next steps:"
echo "  1. nano $APP_DIR/.env            # set GEMINI_API_KEY"
echo "  2. sudo cp $APP_DIR/deploy/*.service /etc/systemd/system/"
echo "  3. sudo systemctl daemon-reload"
echo "  4. sudo systemctl enable --now parcelpilot-backend parcelpilot-frontend"
