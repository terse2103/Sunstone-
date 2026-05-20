"""Thin Anthropic API wrapper with cache, timeout, fallback, and truncation.

Two narrative tasks live here: ``gap_rationale`` and ``intervention_brief``.
The rest of the app composes them.

Design constraints (Rules §Code/2, §Code/7):
- ``llm/`` may import only ``models/``, the Anthropic SDK, and stdlib. Notably,
  no imports from ``core/`` or ``routes/``.
- Every API failure path returns a deterministic fallback so a route never
  returns 500 because of LLM trouble.

Cache: ``(function_name, sha256(inputs))`` → string. Lives on the instance, so
test isolation is per-client. The deployed app uses a single shared instance.
"""

from __future__ import annotations

import hashlib
import logging
import os
import re
import time
from typing import Callable

from anthropic import (
    Anthropic,
    APIConnectionError,
    APIError,
    APIStatusError,
    APITimeoutError,
    RateLimitError,
)

from app.llm.prompts import (
    GAP_RATIONALE_SYSTEM,
    INTERVENTION_BRIEF_SYSTEM,
    READINESS_NARRATIVE_SYSTEM,
    render_gap_rationale,
    render_intervention_brief,
    render_readiness_narrative,
)
from app.models import AtRiskAssessment, Gap, ReadinessResult

log = logging.getLogger(__name__)

DEFAULT_MODEL = "claude-haiku-4-5-20251001"
DEFAULT_TIMEOUT_SEC = 8.0
DEFAULT_BACKOFF_429_SEC = 1.0

MAX_GAP_RATIONALE_TOKENS = 120
MAX_INTERVENTION_TOKENS = 220
MAX_NARRATIVE_TOKENS = 260

BRIEF_LINE_COUNT = 3
NARRATIVE_MAX_SENTENCES = 4

_FALLBACK_GAP_TMPL = (
    "Below the {track} benchmark of {benchmark:.0f} (your score: {score:.0f})."
)

_DIMENSION_LABELS = {"E": "English", "L": "Logic", "Q": "Quant", "D": "Domain"}


class AnthropicClient:
    def __init__(
        self,
        *,
        api_key: str | None = None,
        model: str = DEFAULT_MODEL,
        timeout: float = DEFAULT_TIMEOUT_SEC,
        backoff_429_sec: float = DEFAULT_BACKOFF_429_SEC,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._model = model
        self._timeout = timeout
        self._backoff_sec = backoff_429_sec
        self._sleep = sleep
        self._cache: dict[str, str] = {}

        key = api_key if api_key is not None else os.environ.get("ANTHROPIC_API_KEY")
        if key:
            # Pass the timeout to the SDK as well so the wrapper bound matches
            # what the SDK enforces internally on the HTTP layer.
            self._client: Anthropic | None = Anthropic(api_key=key, timeout=timeout)
        else:
            self._client = None
            log.warning(
                "ANTHROPIC_API_KEY missing — LLM calls will return deterministic "
                "fallbacks (EdgeCases §5.1)."
            )

    # ---- public API --------------------------------------------------------

    def gap_rationale(
        self,
        *,
        gap: Gap,
        student_name: str,
        track_name: str,
    ) -> str:
        """One-sentence rationale for a single gap. Always returns a non-empty string."""
        cache_key = _cache_key("gap_rationale", gap.model_dump_json(), student_name, track_name)
        if cache_key in self._cache:
            return self._cache[cache_key]

        fallback = _fallback_gap_rationale(gap, track_name)

        if self._client is None:
            return self._remember(cache_key, fallback)

        user_prompt = render_gap_rationale(
            gap=gap, student_name=student_name, track_name=track_name
        )
        raw = self._call(
            system=GAP_RATIONALE_SYSTEM,
            user=user_prompt,
            max_tokens=MAX_GAP_RATIONALE_TOKENS,
            tag="gap_rationale",
        )
        if not raw:
            return self._remember(cache_key, fallback)

        rationale = _truncate_to_sentence(raw)
        if not rationale:
            log.warning("llm.gap_rationale: response truncated to empty; using fallback")
            return self._remember(cache_key, fallback)
        if rationale != raw.strip():
            log.info("llm.gap_rationale: truncated response to first sentence")
        return self._remember(cache_key, rationale)

    def intervention_brief(
        self,
        *,
        at_risk: AtRiskAssessment,
        student_name: str,
        track_name: str,
    ) -> list[str]:
        """3-line counselor brief. Always returns a non-empty list."""
        cache_key = _cache_key(
            "intervention_brief",
            at_risk.model_dump_json(),
            student_name,
            track_name,
        )
        if cache_key in self._cache:
            return self._cache[cache_key].split("\n")

        fallback = _fallback_intervention_brief(at_risk, student_name, track_name)

        if self._client is None:
            return self._remember(cache_key, "\n".join(fallback)).split("\n")

        user_prompt = render_intervention_brief(
            at_risk=at_risk, student_name=student_name, track_name=track_name
        )
        raw = self._call(
            system=INTERVENTION_BRIEF_SYSTEM,
            user=user_prompt,
            max_tokens=MAX_INTERVENTION_TOKENS,
            tag="intervention_brief",
        )
        if not raw:
            return self._remember(cache_key, "\n".join(fallback)).split("\n")

        lines = _truncate_to_lines(raw, BRIEF_LINE_COUNT)
        if not lines:
            log.warning("llm.intervention_brief: response truncated to empty; using fallback")
            return self._remember(cache_key, "\n".join(fallback)).split("\n")
        if len(_split_nonempty_lines(raw)) > BRIEF_LINE_COUNT:
            log.info("llm.intervention_brief: truncated response to first %d lines", BRIEF_LINE_COUNT)

        return self._remember(cache_key, "\n".join(lines)).split("\n")

    def readiness_narrative(
        self,
        *,
        readiness: ReadinessResult,
        student_name: str,
        track_name: str,
    ) -> str:
        """2-3 sentence narrative summary of the readiness score. Always non-empty."""
        cache_key = _cache_key(
            "readiness_narrative",
            readiness.model_dump_json(),
            student_name,
            track_name,
        )
        if cache_key in self._cache:
            return self._cache[cache_key]

        fallback = _fallback_readiness_narrative(readiness, track_name)

        if self._client is None:
            return self._remember(cache_key, fallback)

        user_prompt = render_readiness_narrative(
            readiness=readiness, student_name=student_name, track_name=track_name
        )
        raw = self._call(
            system=READINESS_NARRATIVE_SYSTEM,
            user=user_prompt,
            max_tokens=MAX_NARRATIVE_TOKENS,
            tag="readiness_narrative",
        )
        if not raw:
            return self._remember(cache_key, fallback)

        narrative = _truncate_to_sentences(raw, NARRATIVE_MAX_SENTENCES)
        if not narrative:
            log.warning(
                "llm.readiness_narrative: response truncated to empty; using fallback"
            )
            return self._remember(cache_key, fallback)
        if narrative != raw.strip():
            log.info("llm.readiness_narrative: truncated response to first %d sentences", NARRATIVE_MAX_SENTENCES)
        return self._remember(cache_key, narrative)

    def clear_cache(self) -> None:
        self._cache.clear()

    # ---- internals ---------------------------------------------------------

    def _call(self, *, system: str, user: str, max_tokens: int, tag: str) -> str:
        """Single API call with at most one 429 retry. Returns '' on failure."""
        assert self._client is not None
        try:
            return self._invoke(system=system, user=user, max_tokens=max_tokens)
        except RateLimitError:
            log.warning("llm.%s: rate-limited, backing off %.1fs once", tag, self._backoff_sec)
            self._sleep(self._backoff_sec)
            try:
                return self._invoke(system=system, user=user, max_tokens=max_tokens)
            except RateLimitError:
                log.warning("llm.%s: rate-limited after retry, falling back", tag)
                return ""
            except (APITimeoutError, APIConnectionError, APIStatusError, APIError) as exc:
                log.warning("llm.%s: retry failed (%s); falling back", tag, type(exc).__name__)
                return ""
        except APITimeoutError:
            log.warning("llm.%s: request timed out after %.1fs; falling back", tag, self._timeout)
            return ""
        except (APIConnectionError, APIStatusError, APIError) as exc:
            log.warning("llm.%s: %s; falling back", tag, type(exc).__name__)
            return ""

    def _invoke(self, *, system: str, user: str, max_tokens: int) -> str:
        assert self._client is not None
        msg = self._client.messages.create(
            model=self._model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        # EdgeCases §5.7: best-effort parse of an unexpected shape.
        try:
            return (msg.content[0].text or "").strip()
        except (AttributeError, IndexError, TypeError):
            log.warning("llm: malformed response shape; falling back")
            return ""

    def _remember(self, key: str, value: str) -> str:
        self._cache[key] = value
        return value


# --- module-level helpers ---------------------------------------------------


def _cache_key(*parts: str) -> str:
    h = hashlib.sha256()
    for p in parts:
        h.update(p.encode("utf-8"))
        h.update(b"\x00")  # separator so concatenation isn't ambiguous
    return h.hexdigest()


_SENTENCE_END = re.compile(r"([.!?])\s")


def _truncate_to_sentence(text: str) -> str:
    """First sentence — stop at the first `.`, `!`, or `?` followed by space.

    If no sentence boundary exists, return the whole stripped string.
    """
    s = text.strip()
    if not s:
        return ""
    m = _SENTENCE_END.search(s)
    if m:
        return s[: m.end() - 1].strip()
    return s


def _truncate_to_sentences(text: str, n: int) -> str:
    """Return up to the first ``n`` sentence-terminated segments."""
    s = text.strip()
    if not s:
        return ""
    out: list[str] = []
    cursor = 0
    for m in _SENTENCE_END.finditer(s):
        out.append(s[cursor : m.end() - 1].strip())
        cursor = m.end()
        if len(out) == n:
            break
    if len(out) < n:
        tail = s[cursor:].strip()
        if tail:
            out.append(tail)
    return " ".join(seg for seg in out if seg)


def _split_nonempty_lines(text: str) -> list[str]:
    return [ln.strip() for ln in text.splitlines() if ln.strip()]


def _truncate_to_lines(text: str, n: int) -> list[str]:
    return _split_nonempty_lines(text)[:n]


def _fallback_gap_rationale(gap: Gap, track_name: str) -> str:
    return _FALLBACK_GAP_TMPL.format(
        track=track_name, benchmark=gap.benchmark, score=gap.student_score
    )


def _fallback_readiness_narrative(readiness: ReadinessResult, track_name: str) -> str:
    """Deterministic narrative used when the LLM is unavailable.

    Mirrors the structure dictated by ``READINESS_NARRATIVE_SYSTEM``: band,
    optional exceeding sentence, optional priority-path sentence, call to
    action — and crucially uses no numbers.
    """
    overall = readiness.overall
    if overall >= 70:
        band_clause = f"on track for a strong placement in {track_name}"
    elif overall >= 55:
        band_clause = (
            f"in the borderline band for {track_name} — close to "
            "placement-ready, but not quite over the line yet"
        )
    else:
        band_clause = (
            f"at risk of falling short of a {track_name} placement as "
            "things stand today"
        )

    exceeding = sorted(
        (d for d in readiness.dimensions if d.score >= d.benchmark),
        key=lambda d: -(d.score - d.benchmark),
    )
    below = sorted(
        (d for d in readiness.dimensions if d.score < d.benchmark),
        key=lambda d: -(d.benchmark - d.score),
    )

    pieces = [f"You're {band_clause}."]

    if exceeding:
        names = [_DIMENSION_LABELS[d.dimension] for d in exceeding]
        pieces.append(
            "You're already exceeding the benchmark in "
            f"{_join_with_and(names)}."
        )

    if below:
        names = [_DIMENSION_LABELS[d.dimension] for d in below]
        if len(names) == 1:
            pieces.append(f"The area to focus on is {names[0]}.")
        else:
            pieces.append(
                "The priority areas to work on, in order, are "
                f"{_join_with_and(names)}."
            )
        pieces.append(
            "Steady, focused effort on those will move you toward the "
            "placement you're working for."
        )
    else:
        pieces.append(
            "Keep that depth of preparation up and your placement outcome "
            "should reflect the work you've already put in."
        )

    return " ".join(pieces)


def _join_with_and(items: list[str]) -> str:
    if len(items) == 1:
        return items[0]
    if len(items) == 2:
        return f"{items[0]} and {items[1]}"
    return f"{', '.join(items[:-1])}, and {items[-1]}"


def _fallback_intervention_brief(
    at_risk: AtRiskAssessment, student_name: str, track_name: str
) -> list[str]:
    direction = "no trend data"
    if at_risk.trajectory_slope is not None:
        if at_risk.trajectory_slope > 0:
            direction = "improving"
        elif at_risk.trajectory_slope < 0:
            direction = "declining"
        else:
            direction = "flat"

    line1 = (
        f"{student_name} ({track_name}): readiness {at_risk.readiness:.0f}, "
        f"trajectory {direction}."
    )
    if at_risk.primary_gap is not None:
        line2 = (
            f"Primary gap: {at_risk.primary_gap.subskill} "
            f"({at_risk.primary_gap.dimension}) — "
            f"{at_risk.primary_gap.gap_size:.0f} pts below benchmark; "
            f"risk level {at_risk.risk_level}."
        )
    else:
        line2 = f"No single dominant gap identified; risk level {at_risk.risk_level}."

    signal = (
        at_risk.contributing_signals[0]
        if at_risk.contributing_signals
        else "Review recent activity"
    )
    line3 = (
        f"{signal}. Recommended next step: schedule a 1:1 within the "
        f"{at_risk.days_to_placement}-day placement window."
    )
    return [line1, line2, line3]
