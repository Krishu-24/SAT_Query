"""
Deterministic query → required-input derivation for validation.

This is NOT a task router and does not select models. It only extracts
what inputs a query needs so InputValidator can check sufficiency /
compatibility before routing.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional


SPATIAL_PATTERNS: list[tuple[str, str]] = [
    (r"\bnorth[-\s]?east\b|\bnortheast\b|\bne\b", "northeast"),
    (r"\bnorth[-\s]?west\b|\bnorthwest\b|\bnw\b", "northwest"),
    (r"\bsouth[-\s]?east\b|\bsoutheast\b|\bse\b", "southeast"),
    (r"\bsouth[-\s]?west\b|\bsouthwest\b|\bsw\b", "southwest"),
    (r"\beastern\b|\beast\b", "east"),
    (r"\bwestern\b|\bwest\b", "west"),
    (r"\bnorthern\b|\bnorth\b", "north"),
    (r"\bsouthern\b|\bsouth\b", "south"),
    (r"\bcenter\b|\bcentral\b|\bmiddle\b", "center"),
    (r"\bleft\b", "left"),
    (r"\bright\b", "right"),
    (r"\bupper\b|\btop\b", "upper"),
    (r"\blower\b|\bbottom\b", "lower"),
    (r"\bnear the river\b|\baround the river\b", "near_river"),
    (r"\baround the city center\b|\bnear the city\b", "near_city_center"),
]

CHANGE_KW = [
    "change", "changed", "changes", "differ", "difference", "before", "after",
    "increase", "decrease", "grew", "expand", "between the two", "between these",
    "temporal", "bitemporal", "greener", "getting greener",
]

EXTERNAL_INFO_KW = [
    "population density", "population of", "census", "gdp", "unemployment",
    "crime rate", "election", "weather forecast", "stock price",
]


@dataclass
class QueryRequirements:
    """What the query needs from inputs — independent of model inference."""

    needs_temporal_pair: bool = False
    needs_cross_modal: bool = False
    requires_modality: Optional[str] = None  # "optical" | "sar" | None
    requires_same_location: bool = False
    requires_distinct_dates: bool = False
    mentioned_years: list[str] = field(default_factory=list)
    spatial_constraint: Optional[str] = None
    target_hints: list[str] = field(default_factory=list)
    is_ambiguous_change: bool = False
    is_external_information: bool = False
    is_compound: bool = False
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "needs_temporal_pair": self.needs_temporal_pair,
            "needs_cross_modal": self.needs_cross_modal,
            "requires_modality": self.requires_modality,
            "requires_same_location": self.requires_same_location,
            "requires_distinct_dates": self.requires_distinct_dates,
            "mentioned_years": self.mentioned_years,
            "spatial_constraint": self.spatial_constraint,
            "target_hints": self.target_hints,
            "is_ambiguous_change": self.is_ambiguous_change,
            "is_external_information": self.is_external_information,
            "is_compound": self.is_compound,
            "notes": self.notes,
        }


def _has_any(text: str, words: list[str]) -> bool:
    return any(w in text for w in words)


def derive_query_requirements(query: str) -> QueryRequirements:
    q = (query or "").lower().strip()
    req = QueryRequirements()

    years = re.findall(r"\b((?:19|20)\d{2})\b", q)
    req.mentioned_years = years

    for pattern, label in SPATIAL_PATTERNS:
        if re.search(pattern, q):
            req.spatial_constraint = label
            break

    change_like = _has_any(q, CHANGE_KW) or bool(
        re.search(r"\bbetween\b.+\band\b", q)
    )
    if change_like:
        req.needs_temporal_pair = True
        req.requires_same_location = True
        req.requires_distinct_dates = True

    # Explicit modality wording
    wants_sar = bool(re.search(r"\bsar\b|\bsynthetic aperture\b|\bradar\b", q))
    wants_optical = bool(
        re.search(r"\boptical\b|\bsentinel-?2\b|\brgb\b|\bmultispectral\b", q)
    )
    if wants_sar and wants_optical:
        req.needs_cross_modal = True
        req.requires_modality = None
    elif wants_sar:
        req.requires_modality = "sar"
    elif wants_optical and "compare optical" in q:
        req.requires_modality = "optical"

    if re.search(r"compare optical and sar|optical and sar|using optical and sar", q):
        req.needs_cross_modal = True

    if _has_any(q, EXTERNAL_INFO_KW):
        req.is_external_information = True
        req.notes.append(
            "Query appears to require external demographic/economic data "
            "not present in satellite imagery alone."
        )

    # Ambiguous change phrasing
    ambiguous_patterns = [
        r"^what changed\??$",
        r"^has this changed\??$",
        r"^find the difference\??$",
        r"^is this (area )?getting greener\??$",
        r"^has this changed\b",
    ]
    if any(re.search(p, q) for p in ambiguous_patterns):
        req.is_ambiguous_change = True
        req.needs_temporal_pair = True
        req.requires_same_location = True

    # Compound: multiple clauses / multiple verbs of analysis
    compound_markers = [
        " and then ", " then ", " and calculate ", " and determine ",
        "identify the", "determine whether", "calculate the",
    ]
    verbish = sum(
        1 for v in ("identify", "determine", "calculate", "highlight", "compare", "locate")
        if v in q
    )
    if verbish >= 2 or any(m in q for m in compound_markers):
        req.is_compound = True

    # Soft target hints (not semantic detection)
    for hint in ("water", "flood", "forest", "agriculture", "built-up", "building", "railway"):
        if hint in q:
            req.target_hints.append(hint)

    return req
