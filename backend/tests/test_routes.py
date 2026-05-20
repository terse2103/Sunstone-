"""Integration tests for the API routes.

We use ``with TestClient(app)`` so the lifespan handler fires (loads seed,
constructs AnthropicClient). No ``ANTHROPIC_API_KEY`` is set in the test env,
so LLM calls return the deterministic templated fallbacks — perfect for
predictable assertions (EdgeCases §5.1).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.routes.counselor import reset_actions


@pytest.fixture(autouse=True)
def _no_anthropic_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)


@pytest.fixture(autouse=True)
def _clean_counselor_actions() -> None:
    reset_actions()
    yield
    reset_actions()


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


# --- healthz / OpenAPI ------------------------------------------------------


def test_healthz_returns_ok(client: TestClient) -> None:
    r = client.get("/api/healthz")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_openapi_lists_all_routes(client: TestClient) -> None:
    r = client.get("/openapi.json")
    assert r.status_code == 200
    paths = r.json()["paths"]
    expected = {
        "/api/healthz",
        "/api/auth/login",
        "/api/students",
        "/api/students/{student_id}",
        "/api/students/{student_id}/readiness",
        "/api/students/{student_id}/narrative",
        "/api/students/{student_id}/gaps",
        "/api/counselor/at-risk",
        "/api/counselor/students/{student_id}/brief",
        "/api/counselor/students/{student_id}/action",
        "/api/evals/results",
    }
    missing = expected - paths.keys()
    assert not missing, f"missing routes in OpenAPI: {missing}"


# --- auth -------------------------------------------------------------------


def test_login_student_with_valid_id(client: TestClient) -> None:
    r = client.post("/api/auth/login", json={"role": "student", "student_id": "STU_001"})
    assert r.status_code == 200
    assert r.json() == {"role": "student", "student_id": "STU_001"}


def test_login_student_with_unknown_id_404(client: TestClient) -> None:
    r = client.post("/api/auth/login", json={"role": "student", "student_id": "STU_999"})
    assert r.status_code == 404
    assert r.json()["detail"] == "unknown_student_id"


def test_login_student_without_id_422(client: TestClient) -> None:
    r = client.post("/api/auth/login", json={"role": "student"})
    assert r.status_code == 422


def test_login_counselor_no_id(client: TestClient) -> None:
    r = client.post("/api/auth/login", json={"role": "counselor"})
    assert r.status_code == 200
    body = r.json()
    assert body["role"] == "counselor"
    assert body["student_id"] is None


def test_login_invalid_role_422(client: TestClient) -> None:
    r = client.post("/api/auth/login", json={"role": "admin"})
    assert r.status_code == 422


# --- students ---------------------------------------------------------------


def test_list_students_returns_summary_shape(client: TestClient) -> None:
    r = client.get("/api/students")
    assert r.status_code == 200
    body = r.json()
    assert len(body) == 12
    first = body[0]
    assert {"id", "name", "program", "campus", "career_track"} <= set(first.keys())
    # Summary should NOT include nested assessments.
    assert "assessments" not in first


def test_get_student_full_profile(client: TestClient) -> None:
    r = client.get("/api/students/STU_001")
    assert r.status_code == 200
    body = r.json()
    assert body["id"] == "STU_001"
    assert "assessments" in body and len(body["assessments"]) > 0


def test_get_student_unknown_404(client: TestClient) -> None:
    r = client.get("/api/students/STU_999")
    assert r.status_code == 404


def test_readiness_shape_and_bounds(client: TestClient) -> None:
    r = client.get("/api/students/STU_001/readiness")
    assert r.status_code == 200
    body = r.json()
    assert body["student_id"] == "STU_001"
    assert 0 <= body["overall"] <= 100
    assert {d["dimension"] for d in body["dimensions"]} == {"E", "L", "Q", "D"}


def test_readiness_unknown_student_404(client: TestClient) -> None:
    assert client.get("/api/students/STU_999/readiness").status_code == 404


def test_narrative_returns_non_empty_text(client: TestClient) -> None:
    """No API key → fallback narrative path. Should always be non-empty."""
    r = client.get("/api/students/STU_001/narrative")
    assert r.status_code == 200
    body = r.json()
    assert body["student_id"] == "STU_001"
    assert body["text"], "narrative text must be non-empty"
    # Fallback narrative names the track.
    assert "BFSI" in body["text"]


def test_narrative_unknown_student_404(client: TestClient) -> None:
    assert client.get("/api/students/STU_999/narrative").status_code == 404


def test_gaps_default_returns_at_most_three_with_rationale(client: TestClient) -> None:
    """STU_003 is the BFSI at-risk student → guaranteed to have gaps."""
    r = client.get("/api/students/STU_003/gaps")
    assert r.status_code == 200
    body = r.json()
    assert 1 <= len(body) <= 3
    for gap in body:
        assert gap["rationale"], "fallback rationale should be non-empty"
        assert "BFSI" in gap["rationale"]  # fallback template includes track name
        assert {"subskill", "dimension", "gap_size", "priority_score", "rank"} <= set(
            gap.keys()
        )


def test_gaps_respects_n_query_param(client: TestClient) -> None:
    r = client.get("/api/students/STU_003/gaps?n=1")
    assert r.status_code == 200
    assert len(r.json()) == 1


def test_gaps_validates_n_range(client: TestClient) -> None:
    assert client.get("/api/students/STU_003/gaps?n=0").status_code == 422
    assert client.get("/api/students/STU_003/gaps?n=-1").status_code == 422


def test_gaps_unknown_student_404(client: TestClient) -> None:
    assert client.get("/api/students/STU_999/gaps").status_code == 404


# --- counselor --------------------------------------------------------------


def test_at_risk_returns_flagged_students_sorted_by_readiness(
    client: TestClient,
) -> None:
    r = client.get("/api/counselor/at-risk")
    assert r.status_code == 200
    flagged = r.json()
    # Per the sanity check, 4 seed students are flagged (STU_003, 007, 010, 012).
    assert len(flagged) == 4
    ids = {a["student_id"] for a in flagged}
    assert ids == {"STU_003", "STU_007", "STU_010", "STU_012"}
    # All entries are actually flagged.
    assert all(a["flagged"] for a in flagged)
    # Sorted ascending by readiness (most at-risk first).
    readinesses = [a["readiness"] for a in flagged]
    assert readinesses == sorted(readinesses)


def test_brief_returns_three_lines(client: TestClient) -> None:
    r = client.get("/api/counselor/students/STU_003/brief")
    assert r.status_code == 200
    body = r.json()
    assert body["student_id"] == "STU_003"
    assert len(body["lines"]) == 3
    assert all(isinstance(line, str) and line for line in body["lines"])
    assert body["contributing_signals"]  # at-risk students have signals


def test_brief_unknown_student_404(client: TestClient) -> None:
    assert client.get("/api/counselor/students/STU_999/brief").status_code == 404


def test_action_marks_student_returns_204(client: TestClient) -> None:
    from app.routes import counselor

    r = client.post("/api/counselor/students/STU_003/action")
    assert r.status_code == 204
    assert r.content == b""
    assert "STU_003" in counselor.actions_taken()


def test_action_is_idempotent(client: TestClient) -> None:
    from app.routes import counselor

    client.post("/api/counselor/students/STU_003/action")
    r = client.post("/api/counselor/students/STU_003/action")
    assert r.status_code == 204
    assert counselor.actions_taken() == frozenset({"STU_003"})


def test_action_unknown_student_404(client: TestClient) -> None:
    assert client.post("/api/counselor/students/STU_999/action").status_code == 404


# --- evals ------------------------------------------------------------------


def test_evals_missing_report_returns_not_run(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """EdgeCases §8.1: missing report → 200 with status=not_run."""
    from app.routes import evals as evals_routes

    fake_path = tmp_path / "report_does_not_exist.json"
    monkeypatch.setattr(evals_routes, "REPORT_PATH", fake_path)

    r = client.get("/api/evals/results")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "not_run"
    assert body["ran_at"] is None
    assert body["suites"] == []


def test_evals_present_report_returned(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from app.routes import evals as evals_routes

    payload = {
        "status": "pass",
        "ran_at": "2026-05-20T10:00:00Z",
        "suites": [
            {
                "name": "score_calibration",
                "status": "pass",
                "metrics": {"directional_accuracy": 1.0},
                "cases": [],
            }
        ],
    }
    report_path = tmp_path / "report.json"
    report_path.write_text(json.dumps(payload), encoding="utf-8")
    monkeypatch.setattr(evals_routes, "REPORT_PATH", report_path)

    r = client.get("/api/evals/results")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "pass"
    assert body["suites"][0]["name"] == "score_calibration"


def test_evals_malformed_report_falls_back_to_not_run(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from app.routes import evals as evals_routes

    bad_path = tmp_path / "report.json"
    bad_path.write_text("{ this is not valid json", encoding="utf-8")
    monkeypatch.setattr(evals_routes, "REPORT_PATH", bad_path)

    r = client.get("/api/evals/results")
    assert r.status_code == 200
    assert r.json()["status"] == "not_run"
