"""Evidence rules for learner records.

Observed means the learner demonstrated the claim in a response.
Inferred means the claim was estimated or self-reported. An inference is not a confirmed fact.
"""

from __future__ import annotations

EVIDENCE_OBSERVED = "observed"
EVIDENCE_INFERRED = "inferred"
EVIDENCE_KINDS = (EVIDENCE_OBSERVED, EVIDENCE_INFERRED)

PROVENANCE_LEARNER_RESPONSE = "learner_response"
PROVENANCE_ASSESSMENT = "assessment"
PROVENANCE_SYSTEM_ESTIMATE = "system_estimate"
PROVENANCE_LEARNER_REPORT = "learner_report"

OBSERVED_PROVENANCE = (PROVENANCE_LEARNER_RESPONSE, PROVENANCE_ASSESSMENT)
INFERRED_PROVENANCE = (PROVENANCE_SYSTEM_ESTIMATE, PROVENANCE_LEARNER_REPORT)

EVIDENCE_CONSTRAINT = (
    "(evidence_kind = 'observed' AND provenance IN ('learner_response', 'assessment')) "
    "OR (evidence_kind = 'inferred' AND provenance IN ('system_estimate', 'learner_report'))"
)


def pair_is_valid(evidence_kind: str, provenance: str) -> bool:
    if evidence_kind == EVIDENCE_OBSERVED:
        return provenance in OBSERVED_PROVENANCE
    if evidence_kind == EVIDENCE_INFERRED:
        return provenance in INFERRED_PROVENANCE
    return False


def is_confirmed(evidence_kind: str) -> bool:
    return evidence_kind == EVIDENCE_OBSERVED
