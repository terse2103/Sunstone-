"""Eval results endpoint — reads ``evals/results/report.json`` from disk.

Per EdgeCases §8.1, a missing report is not an error: return ``not_run``
with HTTP 200 so the frontend can render the empty state.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from fastapi import APIRouter
from pydantic import ValidationError

from app.models import EvalsReport

router = APIRouter(prefix="/api/evals", tags=["evals"])

log = logging.getLogger(__name__)

# backend/app/routes/evals.py → project root is 3 levels up.
PROJECT_ROOT = Path(__file__).resolve().parents[3]
REPORT_PATH = PROJECT_ROOT / "evals" / "results" / "report.json"


@router.get("/results", response_model=EvalsReport)
def get_results() -> EvalsReport:
    if not REPORT_PATH.exists():
        return EvalsReport(status="not_run", ran_at=None, suites=[])
    try:
        raw = json.loads(REPORT_PATH.read_text(encoding="utf-8"))
        return EvalsReport(**raw)
    except (json.JSONDecodeError, ValidationError, OSError) as exc:
        log.warning("evals.report.json unreadable (%s); reporting not_run", type(exc).__name__)
        return EvalsReport(status="not_run", ran_at=None, suites=[])
