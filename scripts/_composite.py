"""
_composite.py — Python mirror of `mcp/src/composite.ts`.

Same shape, same formulas, same test cases. Kept as a mirror because
scripts/*.py cannot import from TypeScript, and running a Node
subprocess per row during the sweep would multiply latency.

Single-source-of-truth rule (from docs/composite-methodology.md
§Implementation): `mcp/src/composite.ts` is authoritative. If the
formula changes there, this file must be updated in the same PR.
`test_composite.py` (co-located) mirrors `mcp/src/test-composite.ts`
and enforces parity on a golden fixture.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable, Literal, Optional

TaskFamily = Literal["code", "agentic", "longcontext"]
TASK_FAMILIES: tuple[TaskFamily, ...] = ("code", "agentic", "longcontext")

CapabilityBand = Literal["entry", "competent", "frontier"]

# Cutoffs per docs/composite-methodology.md §10.
# Values are provisional until first-sweep distribution locks them.
BAND_CUTOFFS = {"competent": 50.0, "frontier": 75.0}


@dataclass(frozen=True)
class BenchmarkObservation:
    id: str
    score: float
    trust: float  # 0..100 per benchmark-trust.ts; families use it as weight
    family: TaskFamily


@dataclass(frozen=True)
class BenchmarkAnchor:
    max: float
    min: float = 0.0


BenchmarkAnchors = dict[str, BenchmarkAnchor]


@dataclass(frozen=True)
class CompositeResult:
    composite: Optional[float]
    by_family: dict[TaskFamily, Optional[float]]
    band: Optional[CapabilityBand]
    benchmark_count: dict[TaskFamily, int]


def normalize(score: float, anchor: BenchmarkAnchor) -> float:
    """Per-benchmark min-max → [0, 100]. Clamps out-of-range scores."""
    lo, hi = anchor.min, anchor.max
    if not math.isfinite(score) or not math.isfinite(hi) or hi <= lo:
        return 0.0
    x = (score - lo) / (hi - lo)
    if x <= 0:
        return 0.0
    if x >= 1:
        return 100.0
    return x * 100.0


def compute_family_score(
    observations: Iterable[BenchmarkObservation],
    anchors: BenchmarkAnchors,
) -> Optional[float]:
    """Trust-weighted arithmetic mean over one family's observations.

    Returns None if no observation has positive trust with a known anchor.
    """
    weighted = 0.0
    trust_sum = 0.0
    for obs in observations:
        if not (obs.trust > 0):
            continue
        anchor = anchors.get(obs.id)
        if anchor is None:
            continue
        weighted += obs.trust * normalize(obs.score, anchor)
        trust_sum += obs.trust
    if trust_sum == 0:
        return None
    return weighted / trust_sum


def compute_composite(
    by_family: dict[TaskFamily, Optional[float]],
) -> Optional[float]:
    """Geometric mean of present family scores. See §7.2."""
    present = [by_family[f] for f in TASK_FAMILIES if by_family[f] is not None]
    if not present:
        return None
    if any((s or 0.0) <= 0 for s in present):
        return 0.0
    log_sum = sum(math.log(float(s)) for s in present)  # type: ignore[arg-type]
    return math.exp(log_sum / len(present))


def derive_band(composite: Optional[float]) -> Optional[CapabilityBand]:
    if composite is None:
        return None
    if composite < BAND_CUTOFFS["competent"]:
        return "entry"
    if composite < BAND_CUTOFFS["frontier"]:
        return "competent"
    return "frontier"


def compute_row(
    observations: Iterable[BenchmarkObservation],
    anchors: BenchmarkAnchors,
) -> CompositeResult:
    """End-to-end pipeline mirroring mcp/src/composite.ts::computeRow."""
    obs_list = list(observations)
    by_family_obs: dict[TaskFamily, list[BenchmarkObservation]] = {
        "code": [],
        "agentic": [],
        "longcontext": [],
    }
    benchmark_count: dict[TaskFamily, int] = {
        "code": 0,
        "agentic": 0,
        "longcontext": 0,
    }
    for obs in obs_list:
        by_family_obs[obs.family].append(obs)
        benchmark_count[obs.family] += 1
    by_family: dict[TaskFamily, Optional[float]] = {
        f: compute_family_score(by_family_obs[f], anchors) for f in TASK_FAMILIES
    }
    composite = compute_composite(by_family)
    band = derive_band(composite)
    return CompositeResult(
        composite=composite,
        by_family=by_family,
        band=band,
        benchmark_count=benchmark_count,
    )
