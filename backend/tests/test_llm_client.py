"""AnthropicClient unit tests.

These mock the Anthropic SDK entirely — no network calls. The Anthropic SDK's
exception classes have non-trivial constructors, so we subclass them and
override ``__init__`` to construct instances cheaply.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from anthropic import (
    APIConnectionError,
    APIError,
    APIStatusError,
    APITimeoutError,
    RateLimitError,
)

from app.llm.client import AnthropicClient
from app.models import AtRiskAssessment, DimensionScore, Gap, ReadinessResult


# --- exception stubs that skip the SDK's strict __init__ ---------------------


class _FakeRateLimit(RateLimitError):
    def __init__(self) -> None:
        Exception.__init__(self, "test rate limit")


class _FakeTimeout(APITimeoutError):
    def __init__(self) -> None:
        Exception.__init__(self, "test timeout")


class _FakeAPIStatus(APIStatusError):
    def __init__(self) -> None:
        Exception.__init__(self, "test status")


class _FakeConnection(APIConnectionError):
    def __init__(self) -> None:
        Exception.__init__(self, "test connection")


# --- fixtures ---------------------------------------------------------------


@pytest.fixture(autouse=True)
def _clear_env_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)


def _gap() -> Gap:
    return Gap(
        subskill="quant_aptitude",
        dimension="Q",
        student_score=55.0,
        benchmark=80.0,
        gap_size=25.0,
        priority_score=8.75,
        rank=1,
        jd_frequency=0.71,
        signals=[],
    )


def _at_risk() -> AtRiskAssessment:
    return AtRiskAssessment(
        student_id="STU_X",
        risk_level="high",
        flagged=True,
        readiness=38.4,
        trajectory_slope=-3.5,
        days_to_placement=140,
        primary_gap=_gap(),
        contributing_signals=["Missed 4 of last 6 sessions"],
    )


def _readiness(overall: float = 63.0) -> ReadinessResult:
    return ReadinessResult(
        student_id="STU_X",
        track="BFSI",
        overall=overall,
        dimensions=[
            DimensionScore(
                dimension="E", score=70, benchmark=65, assessment_avg=70,
                attendance_pct=85, time_on_task_hrs=18, signals=[],
            ),
            DimensionScore(
                dimension="L", score=60, benchmark=70, assessment_avg=58,
                attendance_pct=90, time_on_task_hrs=22, signals=[],
            ),
            DimensionScore(
                dimension="Q", score=82, benchmark=78, assessment_avg=80,
                attendance_pct=90, time_on_task_hrs=25, signals=[],
            ),
            DimensionScore(
                dimension="D", score=45, benchmark=72, assessment_avg=40,
                attendance_pct=88, time_on_task_hrs=24, signals=[],
            ),
        ],
    )


def _llm_response(text: str) -> SimpleNamespace:
    """Stand-in for ``anthropic.types.Message`` — only ``.content[0].text`` matters."""
    return SimpleNamespace(content=[SimpleNamespace(text=text)])


def _client_with_mocked_sdk(monkeypatch: pytest.MonkeyPatch, *, backoff: float = 0.0):
    """Build an AnthropicClient whose internal SDK client is a MagicMock."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key-for-tests")
    sleeps: list[float] = []
    client = AnthropicClient(backoff_429_sec=backoff, sleep=sleeps.append)
    mock_sdk = MagicMock()
    client._client = mock_sdk  # type: ignore[attr-defined]
    return client, mock_sdk, sleeps


# --- fallback when no key (§5.1) --------------------------------------------


def test_no_api_key_uses_deterministic_gap_fallback() -> None:
    client = AnthropicClient(api_key=None)  # env stripped by autouse fixture
    out = client.gap_rationale(gap=_gap(), student_name="Priya", track_name="BFSI")
    assert "BFSI" in out
    assert "80" in out  # benchmark
    assert "55" in out  # score


def test_no_api_key_uses_deterministic_intervention_fallback() -> None:
    client = AnthropicClient(api_key=None)
    out = client.intervention_brief(
        at_risk=_at_risk(), student_name="Priya", track_name="BFSI"
    )
    assert len(out) == 3
    assert "Priya" in out[0]
    assert "38" in out[0]  # readiness
    assert "quant_aptitude" in out[1]
    assert "1:1" in out[2]


def test_no_api_key_fallback_is_cached(monkeypatch: pytest.MonkeyPatch) -> None:
    client = AnthropicClient(api_key=None)
    first = client.gap_rationale(gap=_gap(), student_name="X", track_name="BFSI")
    second = client.gap_rationale(gap=_gap(), student_name="X", track_name="BFSI")
    assert first == second
    # Internal cache should have exactly one entry for this call signature.
    assert len(client._cache) == 1  # type: ignore[attr-defined]


# --- happy path + caching ---------------------------------------------------


def test_gap_rationale_returns_first_sentence_and_caches(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, sdk, _ = _client_with_mocked_sdk(monkeypatch)
    sdk.messages.create.return_value = _llm_response(
        "Quant aptitude is required by 71% of BFSI JDs. A second sentence here."
    )

    a = client.gap_rationale(gap=_gap(), student_name="P", track_name="BFSI")
    b = client.gap_rationale(gap=_gap(), student_name="P", track_name="BFSI")

    assert a == "Quant aptitude is required by 71% of BFSI JDs."
    assert b == a
    # Second call must hit the cache, not the SDK.
    assert sdk.messages.create.call_count == 1


def test_intervention_brief_returns_three_lines_and_caches(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, sdk, _ = _client_with_mocked_sdk(monkeypatch)
    sdk.messages.create.return_value = _llm_response(
        "Readiness 38, declining.\n"
        "Primary gap: quant aptitude (Q).\n"
        "Missed sessions — schedule 1:1.\n"
        "An extra fourth line that must be dropped."
    )

    out_a = client.intervention_brief(
        at_risk=_at_risk(), student_name="P", track_name="BFSI"
    )
    out_b = client.intervention_brief(
        at_risk=_at_risk(), student_name="P", track_name="BFSI"
    )

    assert len(out_a) == 3
    assert "fourth line" not in " ".join(out_a)
    assert out_a == out_b
    assert sdk.messages.create.call_count == 1


# --- failure modes → fallback (§5.2–§5.5, §5.7) ----------------------------


def test_empty_llm_response_uses_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    client, sdk, _ = _client_with_mocked_sdk(monkeypatch)
    sdk.messages.create.return_value = _llm_response("   ")
    out = client.gap_rationale(gap=_gap(), student_name="P", track_name="BFSI")
    assert "BFSI" in out and "80" in out  # fallback template


def test_429_backs_off_then_succeeds(monkeypatch: pytest.MonkeyPatch) -> None:
    client, sdk, sleeps = _client_with_mocked_sdk(monkeypatch, backoff=0.5)
    sdk.messages.create.side_effect = [
        _FakeRateLimit(),
        _llm_response("After retry, this is the answer."),
    ]
    out = client.gap_rationale(gap=_gap(), student_name="P", track_name="BFSI")
    assert out == "After retry, this is the answer."
    assert sdk.messages.create.call_count == 2
    assert sleeps == [0.5]  # backoff slept exactly once


def test_429_repeated_uses_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    client, sdk, sleeps = _client_with_mocked_sdk(monkeypatch)
    sdk.messages.create.side_effect = [_FakeRateLimit(), _FakeRateLimit()]
    out = client.gap_rationale(gap=_gap(), student_name="P", track_name="BFSI")
    assert "BFSI" in out  # fallback
    assert sdk.messages.create.call_count == 2
    assert len(sleeps) == 1


def test_timeout_uses_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    client, sdk, _ = _client_with_mocked_sdk(monkeypatch)
    sdk.messages.create.side_effect = _FakeTimeout()
    out = client.gap_rationale(gap=_gap(), student_name="P", track_name="BFSI")
    assert "BFSI" in out
    assert sdk.messages.create.call_count == 1


def test_connection_error_uses_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    client, sdk, _ = _client_with_mocked_sdk(monkeypatch)
    sdk.messages.create.side_effect = _FakeConnection()
    out = client.gap_rationale(gap=_gap(), student_name="P", track_name="BFSI")
    assert "BFSI" in out


def test_api_status_error_uses_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    client, sdk, _ = _client_with_mocked_sdk(monkeypatch)
    sdk.messages.create.side_effect = _FakeAPIStatus()
    out = client.gap_rationale(gap=_gap(), student_name="P", track_name="BFSI")
    assert "BFSI" in out


def test_generic_api_error_uses_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    client, sdk, _ = _client_with_mocked_sdk(monkeypatch)

    class _FakeAPI(APIError):
        def __init__(self) -> None:
            Exception.__init__(self, "boom")

    sdk.messages.create.side_effect = _FakeAPI()
    out = client.gap_rationale(gap=_gap(), student_name="P", track_name="BFSI")
    assert "BFSI" in out


def test_malformed_response_shape_uses_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    """EdgeCases §5.7: SDK returns something we can't parse → best-effort, then fall back."""
    client, sdk, _ = _client_with_mocked_sdk(monkeypatch)
    sdk.messages.create.return_value = SimpleNamespace(content=[])  # no first element
    out = client.gap_rationale(gap=_gap(), student_name="P", track_name="BFSI")
    assert "BFSI" in out


# --- truncation tightening --------------------------------------------------


def test_truncation_only_first_sentence(monkeypatch: pytest.MonkeyPatch) -> None:
    client, sdk, _ = _client_with_mocked_sdk(monkeypatch)
    sdk.messages.create.return_value = _llm_response(
        "First clear sentence. Second one with extra detail."
    )
    out = client.gap_rationale(gap=_gap(), student_name="P", track_name="BFSI")
    assert out == "First clear sentence."
    assert "Second" not in out


def test_intervention_brief_drops_blank_lines(monkeypatch: pytest.MonkeyPatch) -> None:
    client, sdk, _ = _client_with_mocked_sdk(monkeypatch)
    sdk.messages.create.return_value = _llm_response(
        "Line one.\n\n   \nLine two.\n\nLine three.\nLine four."
    )
    out = client.intervention_brief(
        at_risk=_at_risk(), student_name="P", track_name="BFSI"
    )
    assert out == ["Line one.", "Line two.", "Line three."]


# --- cache isolation between callers ---------------------------------------


def test_cache_key_distinguishes_different_inputs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, sdk, _ = _client_with_mocked_sdk(monkeypatch)
    sdk.messages.create.side_effect = [
        _llm_response("Rationale for student A."),
        _llm_response("Rationale for student B."),
    ]
    a = client.gap_rationale(gap=_gap(), student_name="Student A", track_name="BFSI")
    b = client.gap_rationale(gap=_gap(), student_name="Student B", track_name="BFSI")
    assert a != b
    assert sdk.messages.create.call_count == 2


# --- readiness_narrative ----------------------------------------------------


def test_no_api_key_uses_deterministic_narrative_fallback() -> None:
    client = AnthropicClient(api_key=None)
    out = client.readiness_narrative(
        readiness=_readiness(overall=63.0), student_name="Priya", track_name="BFSI"
    )
    # New format: structured (band → exceeding → priority → CTA), no numbers,
    # no student name, and uses the full ELQD names.
    assert _has_no_digits(out)
    assert "Priya" not in out
    assert "BFSI" in out
    assert "borderline" in out  # 55 ≤ 63 < 70
    # In _readiness(), E and Q exceed their benchmarks; D and L fall short.
    assert "English" in out
    assert "Quant" in out
    assert "Domain" in out
    assert "Logic" in out
    # Domain has the largest shortfall, so it must precede Logic in the
    # priority sentence.
    assert out.index("Domain") < out.index("Logic")


def test_narrative_fallback_bands_by_overall() -> None:
    client = AnthropicClient(api_key=None)
    on_track = client.readiness_narrative(
        readiness=_readiness(overall=78.0), student_name="P", track_name="BFSI"
    )
    at_risk = client.readiness_narrative(
        readiness=_readiness(overall=40.0), student_name="P", track_name="BFSI"
    )
    assert "on track" in on_track
    assert "at risk of falling short" in at_risk
    assert _has_no_digits(on_track)
    assert _has_no_digits(at_risk)


def test_narrative_fallback_all_exceeding_skips_priority_sentence() -> None:
    """Strongest profile — no dimension below benchmark. Fallback should pivot
    the CTA to 'sustain what you've built' rather than listing priorities."""
    client = AnthropicClient(api_key=None)
    out = client.readiness_narrative(
        readiness=_readiness_all_exceeding(),
        student_name="X",
        track_name="BFSI",
    )
    assert "on track" in out
    assert "exceeding the benchmark" in out
    assert "priority areas" not in out
    assert "area to focus on" not in out
    assert _has_no_digits(out)


def test_narrative_returns_four_sentences_max_and_caches(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, sdk, _ = _client_with_mocked_sdk(monkeypatch)
    sdk.messages.create.return_value = _llm_response(
        "You're in the borderline band for BFSI, on the edge of placement-ready. "
        "You already exceed the benchmark in English and Quant. "
        "The path of focus runs through Domain and then Logic. "
        "Stay with that and a strong placement is within reach. "
        "A fifth sentence that must be dropped."
    )
    a = client.readiness_narrative(
        readiness=_readiness(), student_name="P", track_name="BFSI"
    )
    b = client.readiness_narrative(
        readiness=_readiness(), student_name="P", track_name="BFSI"
    )
    assert "borderline" in a
    assert "fifth sentence" not in a
    assert a == b
    assert sdk.messages.create.call_count == 1


def test_narrative_empty_response_uses_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    client, sdk, _ = _client_with_mocked_sdk(monkeypatch)
    sdk.messages.create.return_value = _llm_response("   ")
    out = client.readiness_narrative(
        readiness=_readiness(overall=63), student_name="P", track_name="BFSI"
    )
    # Fell back to deterministic structured prose — no numbers, but still
    # surfaces the band.
    assert _has_no_digits(out)
    assert "borderline" in out


def test_narrative_timeout_uses_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    client, sdk, _ = _client_with_mocked_sdk(monkeypatch)
    sdk.messages.create.side_effect = _FakeTimeout()
    out = client.readiness_narrative(
        readiness=_readiness(), student_name="P", track_name="BFSI"
    )
    assert "BFSI" in out
    assert _has_no_digits(out)


# --- helpers for the no-digit invariant ------------------------------------


def _has_no_digits(text: str) -> bool:
    import re

    return re.search(r"\d", text) is None


def _readiness_all_exceeding() -> ReadinessResult:
    return ReadinessResult(
        student_id="STU_Y",
        track="BFSI",
        overall=90.0,
        dimensions=[
            DimensionScore(
                dimension=dim, score=90, benchmark=70, assessment_avg=90,
                attendance_pct=92, time_on_task_hrs=25, signals=[],
            )
            for dim in ("E", "L", "Q", "D")
        ],
    )
