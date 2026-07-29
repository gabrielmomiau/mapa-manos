#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

sudo apt update
sudo apt install -y \
  python3-venv \
  python3-pip \
  rpicam-apps \
  python3-picamera2 \
  python3-libcamera \
  libatlas-base-dev \
  libopenblas-dev \
  libjpeg-dev

if [[ ! -d .venv ]]; then
  python3 -m venv --system-site-packages .venv
fi

source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

echo "Entorno listo. Ejecuta: source .venv/bin/activate && uvicorn servidor.aplicacion:app --host 0.0.0.0 --port 8000"
