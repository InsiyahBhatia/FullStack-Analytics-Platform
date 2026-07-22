"""Compatibility entrypoint used by docker/docker-compose.yml."""

from pathlib import Path

code = Path("streamlit/app.py").read_text(encoding="utf-8")
exec(compile(code, "streamlit/app.py", "exec"))
