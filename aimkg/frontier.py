"""Frontier scoring (DESIGN.md §2.3). The Analyst rescores with this after each turn.

score = w_r*relevance + w_b*bridging + w_n*novelty + w_e*evidence - w_c*cost
All weights start at 1; the team tunes them against eval.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Weights:
    relevance: float = 1.0
    bridging: float = 1.0
    novelty: float = 1.0
    evidence: float = 1.0
    cost: float = 1.0


ASKED_BOOST = 3.0  # a task or a person asked for it


def relevance(hops: int, requested_by: str, read_count: int = 0) -> float:
    """Closer to the seed, and to what tasks read, is more relevant."""
    base = 1.0 / (1 + hops) + 0.1 * min(read_count, 10)
    return base * (ASKED_BOOST if requested_by in ("task", "person") else 1.0)


def score(*, hops: int, requested_by: str, bridging: bool, novelty: float,
          evidence: float, cost: float, read_count: int = 0, w: Weights | None = None) -> float:
    w = w or Weights()
    return (w.relevance * relevance(hops, requested_by, read_count)
            + w.bridging * (1.0 if bridging else 0.0)
            + w.novelty * max(0.0, min(1.0, novelty))
            + w.evidence * max(0.0, min(1.0, evidence))
            - w.cost * max(0.0, cost))
