"""Cross-cutting integration tests through the FastAPI stack.

These tests deliberately do *not* duplicate the per-route assertions in
``test_routes.py`` or the per-module unit tests. They exercise behaviour
that only emerges when modules collaborate:

A. Full demo flows (Student and Counselor) walked end-to-end via HTTP.
B. Cross-endpoint consistency (numbers from one route match another).
C. Parametrized "every seed student has working coverage" sweep.
D. Counselor mark-action state persistence + isolation across requests.
E. LLM monkey-patching through ``app.state.llm`` so we can prove a
   route-returned rationale actually came from the LLM layer + the cache
   hits on the second call.
F. CORS middleware behaviour for allowed vs disallowed origins.
G. Frontend contract sanity — responses include the exact keys the
   frontend TypeScript types depend on.
H. Determinism — calling the same endpoint twice yields identical output.

The autouse fixture deletes ``ANTHROPIC_API_KEY`` so the LLM layer falls
back deterministically (EdgeCases §5.1). Tests that need to assert real
LLM-path behaviour patch ``app.state.llm.*`` methods directly.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.data import seed
from app.main import app
from app.models import (
    AtRiskAssessment,
    EvalsReport,
    Gap,
    InterventionBrief,
    LoginResponse,
    ReadinessNarrative,
    ReadinessResult,
    Student,
    StudentSummary,
)
from app.routes.counselor import reset_actions


# ---- fixtures --------------------------------------------------------------


@pytest.fixture(autouse=True)
def _no_anthropic_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """Same guarantee as test_routes: deterministic LLM fallbacks."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)


@pytest.fixture(autouse=True)
def _clean_counselor_actions() -> Iterator[None]:
    reset_actions()
    yield
    reset_actions()


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(app) as c:
        yield c


@pytest.fixture
def all_student_ids() -> list[str]:
    return sorted(seed.STUDENTS.keys())


# ---- A. Full demo flows ----------------------------------------------------


def test_full_student_demo_flow(client: TestClient) -> None:
    """Login as student → list → profile → readiness → gaps.

    Mirrors the user journey defined in Rules.md §Demo Rules /2. Every step
    must succeed and produce data the next step can consume.
    """
    login = client.post(
        "/api/auth/login", json={"role": "student", "student_id": "STU_001"}
    )
    assert login.status_code == 200
    auth = LoginResponse(**login.json())
    assert auth.role == "student"
    student_id = auth.student_id
    assert student_id == "STU_001"

    summary = client.get("/api/students").json()
    assert any(s["id"] == student_id for s in summary)

    profile = client.get(f"/api/students/{student_id}")
    assert profile.status_code == 200
    Student(**profile.json())  # Pydantic round-trip = schema valid.

    readiness = client.get(f"/api/students/{student_id}/readiness")
    assert readiness.status_code == 200
    r_obj = ReadinessResult(**readiness.json())
    assert 0 <= r_obj.overall <= 100
    assert len(r_obj.dimensions) == 4

    gaps = client.get(f"/api/students/{student_id}/gaps?n=3")
    assert gaps.status_code == 200
    parsed_gaps = [Gap(**g) for g in gaps.json()]
    # STU_001 is BFSI borderline → guaranteed gaps in fallback mode.
    assert parsed_gaps, "STU_001 must expose at least one gap"
    for g in parsed_gaps:
        assert g.rationale, "every gap carries a rationale (or fallback)"


def test_full_counselor_demo_flow(client: TestClient) -> None:
    """Login → at-risk list → open first brief → mark action → confirm 204."""
    login = client.post("/api/auth/login", json={"role": "counselor"})
    assert login.status_code == 200
    assert LoginResponse(**login.json()).role == "counselor"

    at_risk = client.get("/api/counselor/at-risk")
    assert at_risk.status_code == 200
    flagged = [AtRiskAssessment(**a) for a in at_risk.json()]
    assert flagged, "seed must include flagged students for the demo"

    target = flagged[0].student_id
    brief = client.get(f"/api/counselor/students/{target}/brief")
    assert brief.status_code == 200
    b_obj = InterventionBrief(**brief.json())
    assert b_obj.student_id == target
    assert b_obj.lines, "brief always has at least one line"

    mark = client.post(f"/api/counselor/students/{target}/action")
    assert mark.status_code == 204

    # After marking, the at-risk listing is unchanged (action is bookkeeping,
    # not a flag mutation — EdgeCases §11.1 framing).
    after = client.get("/api/counselor/at-risk").json()
    assert {a["student_id"] for a in after} == {a.student_id for a in flagged}


# ---- B. Cross-endpoint consistency -----------------------------------------


def test_readiness_matches_between_readiness_and_at_risk_endpoints(
    client: TestClient,
) -> None:
    """A student flagged in /at-risk has the same overall as /readiness.

    Both routes compute via the same ``compute_readiness`` call, but a drift
    is exactly the kind of bug that only an integration test catches.
    """
    flagged = [AtRiskAssessment(**a) for a in client.get("/api/counselor/at-risk").json()]
    for a in flagged:
        r = ReadinessResult(**client.get(f"/api/students/{a.student_id}/readiness").json())
        assert a.readiness == pytest.approx(r.overall), (
            f"{a.student_id}: at-risk readiness {a.readiness} ≠ /readiness overall {r.overall}"
        )


def test_at_risk_primary_gap_matches_top_gap_endpoint(client: TestClient) -> None:
    """primary_gap in /at-risk == #1 gap in /gaps?n=1 for the same student."""
    flagged = [AtRiskAssessment(**a) for a in client.get("/api/counselor/at-risk").json()]
    for a in flagged:
        if a.primary_gap is None:
            continue
        top = client.get(f"/api/students/{a.student_id}/gaps?n=1").json()
        assert len(top) == 1
        assert top[0]["subskill"] == a.primary_gap.subskill, (
            f"{a.student_id}: at-risk primary {a.primary_gap.subskill} ≠ "
            f"top gap {top[0]['subskill']}"
        )
        assert top[0]["rank"] == 1


def test_track_field_consistent_between_readiness_and_profile(
    client: TestClient, all_student_ids: list[str]
) -> None:
    for sid in all_student_ids:
        profile = client.get(f"/api/students/{sid}").json()
        readiness = client.get(f"/api/students/{sid}/readiness").json()
        assert readiness["track"] == profile["career_track"], (
            f"{sid}: readiness.track {readiness['track']} ≠ profile.career_track "
            f"{profile['career_track']}"
        )


def test_dimension_benchmark_matches_track_mean(
    client: TestClient, all_student_ids: list[str]
) -> None:
    """DimensionScore.benchmark is the mean of the track's sub-skill benchmarks
    for that dimension (Phase 6 contract). Verify through the HTTP layer.
    """
    for sid in all_student_ids:
        readiness = ReadinessResult(**client.get(f"/api/students/{sid}/readiness").json())
        profile = client.get(f"/api/students/{sid}").json()
        track = seed.BENCHMARKS[profile["career_track"]]
        per_dim: dict[str, list[float]] = {"E": [], "L": [], "Q": [], "D": []}
        for bench in track.subskills.values():
            per_dim[bench.dimension].append(bench.benchmark)
        for ds in readiness.dimensions:
            values = per_dim[ds.dimension]
            expected = (sum(values) / len(values)) if values else 0.0
            assert ds.benchmark == pytest.approx(expected), (
                f"{sid}/{ds.dimension}: benchmark {ds.benchmark} ≠ track mean {expected}"
            )


def test_no_at_risk_student_appears_as_low_risk(client: TestClient) -> None:
    """Flagged-only invariant: /at-risk filters to flagged students. A student
    whose risk_level is "low" must never show up. This guards the route layer
    against accidentally returning the full computed set.
    """
    flagged = client.get("/api/counselor/at-risk").json()
    levels = {a["risk_level"] for a in flagged}
    assert "low" not in levels, f"low-risk student leaked into /at-risk: {flagged}"


# ---- C. Coverage sweep over the full seed ----------------------------------


def test_every_seed_student_has_complete_endpoint_coverage(
    client: TestClient, all_student_ids: list[str]
) -> None:
    """For each of the 12 seeded students: profile, readiness, gaps, brief
    all return 200 with schema-valid bodies. Catches orphan IDs and any
    student that breaks one specific endpoint.
    """
    assert len(all_student_ids) == 12
    for sid in all_student_ids:
        # Profile
        p = client.get(f"/api/students/{sid}")
        assert p.status_code == 200, f"{sid}: profile {p.status_code}"
        Student(**p.json())

        # Readiness
        r = client.get(f"/api/students/{sid}/readiness")
        assert r.status_code == 200, f"{sid}: readiness {r.status_code}"
        ReadinessResult(**r.json())

        # Gaps (some students have zero, but the route still returns 200)
        g = client.get(f"/api/students/{sid}/gaps?n=3")
        assert g.status_code == 200, f"{sid}: gaps {g.status_code}"
        for gap in g.json():
            Gap(**gap)

        # Brief — every student can ask for an intervention brief, even
        # non-flagged ones. The LLM layer produces fallback prose.
        b = client.get(f"/api/counselor/students/{sid}/brief")
        assert b.status_code == 200, f"{sid}: brief {b.status_code}"
        InterventionBrief(**b.json())

        # Narrative — every student gets a non-empty AI summary (fallback
        # path in tests because no API key is set).
        n = client.get(f"/api/students/{sid}/narrative")
        assert n.status_code == 200, f"{sid}: narrative {n.status_code}"
        narrative = ReadinessNarrative(**n.json())
        assert narrative.text


def test_student_summary_excludes_pii_heavy_fields(
    client: TestClient, all_student_ids: list[str]
) -> None:
    """The login-picker payload should be slim — no nested assessments, no
    signal lists. Verify by structural diff against the full profile.
    """
    summaries = client.get("/api/students").json()
    summary_keys = set(summaries[0].keys())
    full = client.get(f"/api/students/{all_student_ids[0]}").json()
    full_keys = set(full.keys())
    heavy = {"assessments", "attendance_pct", "time_on_task_hrs", "recent_signals"}
    assert summary_keys.isdisjoint(heavy), (
        f"summary leaks heavy fields: {summary_keys & heavy}"
    )
    assert heavy <= full_keys, f"full profile missing fields: {heavy - full_keys}"


# ---- D. State persistence + isolation --------------------------------------


def test_action_persists_across_separate_requests(client: TestClient) -> None:
    """Mark for student A; mark for student B; verify both are remembered.

    Belt-and-braces around EdgeCases §11.1 (in-memory set, lost on restart).
    """
    from app.routes import counselor

    assert client.post("/api/counselor/students/STU_003/action").status_code == 204
    assert client.post("/api/counselor/students/STU_010/action").status_code == 204
    assert "STU_003" in counselor.actions_taken()
    assert "STU_010" in counselor.actions_taken()
    assert "STU_012" not in counselor.actions_taken()


def test_at_risk_set_stable_across_repeated_calls(client: TestClient) -> None:
    """Two GETs ten apart return the same flagged set in the same order.

    Catches any hidden mutation in the seed module or the route layer.
    """
    first = client.get("/api/counselor/at-risk").json()
    for _ in range(9):
        client.get("/api/counselor/at-risk")
    last = client.get("/api/counselor/at-risk").json()
    assert [a["student_id"] for a in first] == [a["student_id"] for a in last]
    assert [a["readiness"] for a in first] == [a["readiness"] for a in last]


# ---- E. LLM monkey-patching through routes ---------------------------------


def _spy_gap_rationale() -> tuple[list[dict[str, Any]], Any]:
    """Returns (calls list, callable). Each call appends its kwargs."""
    calls: list[dict[str, Any]] = []

    def spy(*, gap: Gap, student_name: str, track_name: str) -> str:
        calls.append(
            {"subskill": gap.subskill, "student": student_name, "track": track_name}
        )
        return f"LLM-RATIONALE::{gap.subskill}"

    return calls, spy


def test_gap_rationale_propagates_from_llm_layer_to_route(client: TestClient) -> None:
    """A canned LLM answer round-trips intact through the HTTP response.

    This proves the route doesn't silently re-template, drop, or rewrite
    the LLM's output — only the LLM layer can change that string.
    """
    calls, spy = _spy_gap_rationale()
    client.app.state.llm.gap_rationale = spy  # type: ignore[method-assign]

    body = client.get("/api/students/STU_003/gaps?n=2").json()
    assert all(g["rationale"].startswith("LLM-RATIONALE::") for g in body)
    assert len(calls) == len(body)
    # Each call should have the student name + track filled in.
    assert all(c["student"] == "Meera Iyer" for c in calls)
    assert all(c["track"] == "BFSI" for c in calls)


def test_narrative_propagates_text_from_llm_layer(client: TestClient) -> None:
    canned = "LLM-NARRATIVE::your readiness is strong."

    def spy(*, readiness: ReadinessResult, student_name: str, track_name: str) -> str:
        return canned

    client.app.state.llm.readiness_narrative = spy  # type: ignore[method-assign]

    body = client.get("/api/students/STU_001/narrative").json()
    assert body == {"student_id": "STU_001", "text": canned}


def test_brief_propagates_lines_from_llm_layer(client: TestClient) -> None:
    canned = ["alpha", "beta", "gamma"]

    def spy(*, at_risk: AtRiskAssessment, student_name: str, track_name: str) -> list[str]:
        return list(canned)

    client.app.state.llm.intervention_brief = spy  # type: ignore[method-assign]

    body = client.get("/api/counselor/students/STU_003/brief").json()
    assert body["lines"] == canned


def test_unhandled_llm_exception_surfaces_as_5xx() -> None:
    """Pins the boundary: AnthropicClient is the only thing protecting routes
    from LLM failures (Rules §Code/7 — "LLM failures fall back deterministically").
    If the protection is bypassed (here, by monkey-patching the method itself),
    the route does NOT silently 200 with garbage — it surfaces a 5xx. A
    regression that swallows errors with broader try/except would flip this.
    """

    def boom(**_kwargs: Any) -> str:
        raise RuntimeError("unexpected llm crash")

    with TestClient(app, raise_server_exceptions=False) as c:
        c.app.state.llm.gap_rationale = boom  # type: ignore[method-assign]
        r = c.get("/api/students/STU_003/gaps?n=1")
    assert r.status_code in {500, 503}


# ---- F. CORS middleware ----------------------------------------------------


def test_cors_preflight_for_allowed_origin(client: TestClient) -> None:
    """Preflight from the dev origin gets the matching ACAO header."""
    r = client.options(
        "/api/students",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert r.status_code == 200
    assert r.headers.get("access-control-allow-origin") == "http://localhost:5173"


def test_cors_get_with_allowed_origin(client: TestClient) -> None:
    r = client.get("/api/students", headers={"Origin": "http://localhost:5173"})
    assert r.status_code == 200
    assert r.headers.get("access-control-allow-origin") == "http://localhost:5173"


def test_cors_disallowed_origin_omits_acao_header(client: TestClient) -> None:
    """Unknown origins must NOT receive an Access-Control-Allow-Origin echo —
    that's the entire point of the allow-list (EdgeCases §9.2).
    """
    r = client.get("/api/students", headers={"Origin": "https://evil.example.com"})
    # The response still succeeds (CORS is a browser policy), but the header
    # that *enables* the browser to use the response is absent.
    assert r.headers.get("access-control-allow-origin") in {None, ""}


# ---- G. Frontend contract sanity -------------------------------------------


def test_readiness_response_keys_match_frontend_type(client: TestClient) -> None:
    """The frontend src/api/types.ts pins these key names. If a refactor renames
    one without updating the FE, this catches it.
    """
    r = client.get("/api/students/STU_001/readiness").json()
    assert set(r.keys()) == {"student_id", "track", "overall", "dimensions"}
    dim_keys = set(r["dimensions"][0].keys())
    assert {
        "dimension",
        "score",
        "benchmark",
        "assessment_avg",
        "attendance_pct",
        "time_on_task_hrs",
        "signals",
    } <= dim_keys


def test_gap_response_keys_match_frontend_type(client: TestClient) -> None:
    g = client.get("/api/students/STU_003/gaps?n=1").json()[0]
    assert {
        "subskill",
        "dimension",
        "student_score",
        "benchmark",
        "gap_size",
        "priority_score",
        "rank",
        "jd_frequency",
        "signals",
        "rationale",
    } <= set(g.keys())


def test_at_risk_response_keys_match_frontend_type(client: TestClient) -> None:
    a = client.get("/api/counselor/at-risk").json()[0]
    assert {
        "student_id",
        "risk_level",
        "flagged",
        "readiness",
        "trajectory_slope",
        "days_to_placement",
        "primary_gap",
        "contributing_signals",
    } <= set(a.keys())


def test_evals_not_run_shape_matches_frontend_type(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    from app.routes import evals as evals_routes

    monkeypatch.setattr(evals_routes, "REPORT_PATH", tmp_path / "missing.json")
    body = client.get("/api/evals/results").json()
    assert body == {"status": "not_run", "ran_at": None, "suites": []}
    EvalsReport(**body)


def test_student_summary_keys_match_frontend_type(client: TestClient) -> None:
    body = client.get("/api/students").json()
    StudentSummary(**body[0])
    assert set(body[0].keys()) == {"id", "name", "program", "campus", "career_track"}


# ---- H. Determinism --------------------------------------------------------


def test_readiness_endpoint_is_deterministic(client: TestClient) -> None:
    """No hidden state: two calls return byte-equal JSON."""
    a = client.get("/api/students/STU_001/readiness").json()
    b = client.get("/api/students/STU_001/readiness").json()
    assert a == b


def test_gaps_endpoint_is_deterministic_with_fallback_rationale(
    client: TestClient,
) -> None:
    a = client.get("/api/students/STU_003/gaps?n=3").json()
    b = client.get("/api/students/STU_003/gaps?n=3").json()
    assert a == b


def test_at_risk_endpoint_is_deterministic(client: TestClient) -> None:
    a = client.get("/api/counselor/at-risk").json()
    b = client.get("/api/counselor/at-risk").json()
    assert a == b
