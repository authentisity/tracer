import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1] / "tracer-backend"
sys.path.insert(0, str(BACKEND_DIR))

from main import app as fastapi_app  # noqa: E402


async def app(scope, receive, send):
    if scope["type"] == "http" and scope.get("path", "").startswith("/api"):
        scope = dict(scope)
        scope["root_path"] = f"{scope.get('root_path', '')}/api"
        scope["path"] = scope["path"][4:] or "/"
    await fastapi_app(scope, receive, send)
