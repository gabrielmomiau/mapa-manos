#!/usr/bin/env bash
set -euo pipefail

if command -v rpicam-hello >/dev/null 2>&1; then
  rpicam-hello -t 2000
elif command -v libcamera-hello >/dev/null 2>&1; then
  libcamera-hello -t 2000
else
  echo "No se encontro rpicam-hello/libcamera-hello. Instala: sudo apt install -y rpicam-apps"
fi
