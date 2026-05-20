"""FastAPI application bootstrap.

Lifespan loads the seed data (fail-fast on malformed seed per EdgeCases
§1.3 / §1.5 / §2.2) and constructs a single AnthropicClient stored on
``app.state.llm``. Routers are mounted under ``/api/...``.
"""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.data import seed
from app.llm.client import AnthropicClient

# Local dev convenience: read backend/.env into os.environ before the app
# is constructed. Hosted environments inject env vars directly and ignore
# the absence of a .env file.
load_dotenv()
from app.routes import auth as auth_routes
from app.routes import counselor as counselor_routes
from app.routes import evals as evals_routes
from app.routes import student as student_routes

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)


def _parse_allowed_origins() -> list[str]:
    raw = os.environ.get("ALLOWED_ORIGINS", "http://localhost:5173")
    return [origin.strip() for origin in raw.split(",") if origin.strip()]


@asynccontextmanager
async def lifespan(app: FastAPI):
    seed.load()
    log.info(
        "seed loaded: %d students across %d tracks",
        len(seed.STUDENTS),
        len(seed.BENCHMARKS),
    )
    app.state.llm = AnthropicClient()
    yield
    # Nothing to tear down — seed is in-memory, the SDK client closes on GC.


app = FastAPI(title="PlacementIQ API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_parse_allowed_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_routes.router)
app.include_router(student_routes.router)
app.include_router(counselor_routes.router)
app.include_router(evals_routes.router)


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}
