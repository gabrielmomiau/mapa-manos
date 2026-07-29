#!/usr/bin/env python3
import os
import subprocess
import sys

port = os.getenv("PORT", "8000")
print(f"Starting on port {port}")
subprocess.run([
    sys.executable, "-m", "uvicorn",
    "servidor.aplicacion:app",
    "--host", "0.0.0.0",
    "--port", port
])
