"""Compatibility entrypoint used by docker/docker-compose.yml."""

from pathlib import Path
import importlib.util

_spec = importlib.util.spec_from_file_location("streamlit_app", "streamlit/app.py")
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
