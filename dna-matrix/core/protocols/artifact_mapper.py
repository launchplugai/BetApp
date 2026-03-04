# core/protocols/artifact_mapper.py
"""
Protocol → DNA Artifact Mapper.

Maps protocol signals into DNA-compatible artifacts so they
integrate cleanly into the existing contract validation
and Sherlock explainability systems.

Protocol artifacts follow the same contract as DNA artifacts:
- weight: risk adjustment from protocol
- evidence: structured proof of protocol trigger
- audit_note: validation status

All artifacts are derived=true, persisted=false, source="protocol_system".
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from core.protocols.models import (
    AggregatedRisk,
    ProtocolCategory,
    ProtocolSignal,
    RiskLevel,
)


def map_to_dna_artifacts(
    risk: AggregatedRisk,
    request_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Map protocol risk assessment to DNA-compatible artifacts.

    Args:
        risk: AggregatedRisk from protocol pipeline
        request_id: Optional evaluation request ID for lineage

    Returns:
        List of DNA-compatible artifact dicts
    """
    artifacts: List[Dict[str, Any]] = []
    run_id = str(uuid4())
    now = datetime.now(timezone.utc).isoformat()

    lineage = {
        "request_id": request_id or str(uuid4()),
        "run_id": run_id,
        "claim_id": f"protocol_{run_id[:8]}",
    }

    # 1. Weight artifacts — one per triggered protocol signal
    for result in risk.protocol_results:
        if not result.triggered:
            continue
        for signal in result.signals:
            artifacts.append(_build_weight_artifact(signal, lineage, now))

    # 2. Evidence artifacts — one per category with signals
    for cat in ProtocolCategory:
        cat_signals = risk.signals_by_category(cat)
        if cat_signals:
            artifacts.append(_build_evidence_artifact(cat, cat_signals, lineage, now))

    # 3. Audit note — overall protocol assessment
    artifacts.append(_build_audit_artifact(risk, lineage, now))

    return artifacts


def _build_weight_artifact(
    signal: ProtocolSignal,
    lineage: Dict[str, str],
    timestamp: str,
) -> Dict[str, Any]:
    """Build a weight artifact from a protocol signal."""
    return {
        "artifact_type": "weight",
        "derived": True,
        "persisted": False,
        "source": "protocol_system",
        "created_utc": timestamp,
        "lineage": lineage,
        "key": f"protocol_{signal.protocol_name}",
        "value": round(signal.fragility_delta, 2),
        "unit": "fragility_delta",
        "rationale": signal.explanation,
        "metadata": {
            "protocol": signal.protocol_name,
            "category": signal.category.value,
            "risk_level": signal.risk_level.value,
            "confidence": round(signal.confidence, 2),
        },
    }


def _build_evidence_artifact(
    category: ProtocolCategory,
    signals: List[ProtocolSignal],
    lineage: Dict[str, str],
    timestamp: str,
) -> Dict[str, Any]:
    """Build an evidence artifact for a protocol category."""
    evidence_items = []
    for signal in signals:
        for key, value in signal.evidence.items():
            evidence_items.append(f"{key}: {value}")

    return {
        "artifact_type": "evidence",
        "derived": True,
        "persisted": False,
        "source": "protocol_system",
        "created_utc": timestamp,
        "lineage": lineage,
        "key": f"protocol_category_{category.value}",
        "protocol_count": len(signals),
        "max_risk": max(s.risk_level.value for s in signals),
        "evidence": evidence_items[:10],  # cap at 10 items
        "explanations": [s.explanation for s in signals],
    }


def _build_audit_artifact(
    risk: AggregatedRisk,
    lineage: Dict[str, str],
    timestamp: str,
) -> Dict[str, Any]:
    """Build an audit note artifact for the protocol assessment."""
    notes = []
    notes.append(f"Protocol System evaluated {len(risk.protocol_results)} protocols")
    notes.append(f"{risk.triggered_count} protocols triggered")
    notes.append(f"Aggregate fragility: {risk.fragility_score:.3f}")
    notes.append(f"Aggregate confidence: {risk.confidence_score:.3f}")

    if risk.has_critical:
        notes.append("CRITICAL risk detected in one or more protocols")

    status = "PASS" if risk.fragility_score < 0.5 else "FAIL"

    return {
        "artifact_type": "audit_note",
        "derived": True,
        "persisted": False,
        "source": "protocol_system",
        "created_utc": timestamp,
        "lineage": lineage,
        "status": status,
        "notes": notes,
        "summary": risk.risk_summary,
    }
