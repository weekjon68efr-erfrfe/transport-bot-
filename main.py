"""WSGI entrypoint expected by some hosts (e.g. Gunicorn configured with `main:app`).
This imports the Flask `app` instance from `app.py` so Gunicorn can load it.
"""
from app import app

# Expose as module-level variable `app` (already imported)
