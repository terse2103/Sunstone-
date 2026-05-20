"""Vercel Python serverless entry point.

Re-exports the FastAPI app from ``backend/app/main.py``. Vercel's Python
runtime detects the module-level ``app`` callable and routes the rewritten
``/api/*`` traffic into it. See ``docs/architecture.md`` §8.

Path shim: the backend package lives under ``backend/`` rather than at the
repo root, so we add ``<repo>/backend`` to ``sys.path`` before importing.

Lifespan note: Vercel's Python runtime supports ASGI lifespan events, but as
a defensive measure we also trigger ``seed.load()`` at import-time so that a
cold container is never left with empty STUDENTS/BENCHMARKS dicts (which
would surface as confusing 404s on the first request).
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = REPO_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.data import seed  # noqa: E402
from app.main import app  # noqa: E402  re-export for Vercel

if not seed.STUDENTS:
    seed.load()

__all__ = ["app"]
