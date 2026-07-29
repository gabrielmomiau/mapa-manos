#!/usr/bin/env python3
import os
import subprocess
import sys

port = int(os.getenv("PORT", 8000))
print(f"🚀 Starting Manomapa on port {port}...")
sys.exit(subprocess.call([
    sys.executable, "-m", "uvicorn",
    "servidor.aplicacion:app",
    "--host", "0.0.0.0",
    "--port", str(port),
    "--log-level", "info"
]))
