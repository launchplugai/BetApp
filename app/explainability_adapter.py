# app/explainability_adapter.py
"""
Sherlock Read-Only Explainability Adapter (Ticket 18)

Transforms Sherlock FinalReport into structured Explainability Blocks
for future UI consumption.

Scope (Locked):
- Read Sherlock FinalReport
- Transform into Explainability Blocks
- Attach blocks to response under debug.explainability
- NO UI rendering
- NO tier logic
- NO persistence

Contracts referenced:
- docs/contracts/SCH_SDK_CONTRACT.md#section-4-finalreport-schema
- docs/mappings/MAP_SHERLOCK_TO_DNA.md#section-8-complete-translation-example
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from enum import Enum

_logger = logging.getLogger(__name__)


# =============================================================================
# Explainability Block Types
# =============================================================================


class BlockType(str, Enum):
    """Types of explainability blocks."""
    INVESTIGATION_SUMMARY = "investigation_summary"
    CLAIM = "claim"
    EVIDENCE = "evidence"
    ARGUMENT_PRO = "argument_pro"
    ARGUMENT_CON = "argument_con"
    VERDICT = "verdict"
    AUDIT = "audit"
    DNA_PREVIEW = "dna_preview"


# =============================================================================
# Explainability Block Schema
# =============================================================================


@dataclass(frozen=True)
class ExplainabilityBlock:
    """
    A single block of explainability content.

    Blocks are structured units that a future UI can render.
    Each block has:
    - type: What kind of content (claim, evidence, argument, etc.)
    - title: Human-readable header
    - content: The main content (varies by type)
    - metadata: Additional context (confidence, source, etc.)
    - sequence: Ordering hint for rendering
    """
    block_type: BlockType
    title: str
    content: Dict[str, Any]
    metadata: Dict[str, Any] = field(default_factory=dict)
    sequence: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for JSON serialization."""
        return {
            "block_type": self.block_type.value,
            "title": self.title,
            "content": self.content,
            "metadata": self.metadata,
            "sequence": self.sequence,
        }


@dataclass(frozen=True)
class ExplainabilityOutput:
    """
    Complete explainability output from the adapter.

    Contains:
    - enabled: Whether Sherlock was enabled
    - blocks: List of ExplainabilityBlock objects
    - summary: Quick summary for debugging
    - generated_at: Timestamp of generation
    """
    enabled: bool
    blocks: List[ExplainabilityBlock]
    summary: Dict[str, Any]
    generated_at: str

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for JSON serialization."""
        return {
            "enabled": self.enabled,
            "blocks": [b.to_dict() for b in self.blocks],
            "summary": self.summary,
            "generated_at": self.generated_at,
            "block_count": len(self.blocks),
        }


# =============================================================================
# Block Builders
# =============================================================================


def _build_investigation_summary_block(
    sherlock_result: Dict[str, Any],
    sequence: int,
) -> ExplainabilityBlock:
    """Build the investigation summary block."""
    return ExplainabilityBlock(
        block_type=BlockType.INVESTIGATION_SUMMARY,
        title="Investigation Overview",
        content={
            "claim_text": sherlock_result.get("claim_text", ""),
            "iterations_completed": sherlock_result.get("iterations_completed", 0),
            "verdict": sherlock_result.get("verdict", "unknown"),
            "confidence": sherlock_result.get("confidence", 0.0),
            "audit_passed": sherlock_result.get("audit_passed", False),
        },
        metadata={
            "audit_score": sherlock_result.get("audit_score", 0.0),
        },
        sequence=sequence,
    )


def _build_claim_block(
    sherlock_result: Dict[str, Any],
    sequence: int,
) -> ExplainabilityBlock:
    """Build the claim block showing what was investigated."""
    claim_text = sherlock_result.get("claim_text", "")

    return ExplainabilityBlock(
        block_type=BlockType.CLAIM,
        title="Investigated Claim",
        content={
            "claim_text": claim_text,
            "formatted": f'"{claim_text}"' if claim_text else "(no claim)",
        },
        metadata={
            "source": "sherlock_derived",
        },
        sequence=sequence,
    )


def _build_verdict_block(
    sherlock_result: Dict[str, Any],
    sequence: int,
) -> ExplainabilityBlock:
    """Build the verdict block showing the investigation conclusion."""
    verdict = sherlock_result.get("verdict", "unknown")
    confidence = sherlock_result.get("confidence", 0.0)

    # Map verdict to display properties
    verdict_display = {
        "true": {"label": "True", "color_hint": "green"},
        "likely_true": {"label": "Likely True", "color_hint": "light_green"},
        "unclear": {"label": "Unclear", "color_hint": "yellow"},
        "likely_false": {"label": "Likely False", "color_hint": "orange"},
        "false": {"label": "False", "color_hint": "red"},
        "non_falsifiable": {"label": "Non-Falsifiable", "color_hint": "gray"},
        "error": {"label": "Error", "color_hint": "red"},
    }

    display = verdict_display.get(verdict, {"label": verdict.title(), "color_hint": "gray"})

    return ExplainabilityBlock(
        block_type=BlockType.VERDICT,
        title="Investigation Verdict",
        content={
            "verdict": verdict,
            "verdict_label": display["label"],
            "confidence": confidence,
            "confidence_percent": f"{confidence * 100:.0f}%",
        },
        metadata={
            "color_hint": display["color_hint"],
        },
        sequence=sequence,
    )


def _build_audit_block(
    sherlock_result: Dict[str, Any],
    sequence: int,
) -> ExplainabilityBlock:
    """Build the audit block showing logic audit results."""
    audit_passed = sherlock_result.get("audit_passed", False)
    audit_score = sherlock_result.get("audit_score", 0.0)

    return ExplainabilityBlock(
        block_type=BlockType.AUDIT,
        title="Logic Audit",
        content={
            "passed": audit_passed,
            "passed_label": "Passed" if audit_passed else "Failed",
            "weighted_score": audit_score,
            "score_percent": f"{audit_score * 100:.0f}%",
            "threshold": 0.85,  # Default threshold from contract
            "threshold_percent": "85%",
        },
        metadata={
            "color_hint": "green" if audit_passed else "red",
            "quality_gate": True,
        },
        sequence=sequence,
    )


def _build_dna_preview_block(
    dna_artifact: Dict[str, Any],
    sequence: int,
) -> ExplainabilityBlock:
    """Build the DNA preview block showing what would be persisted."""
    primitives = dna_artifact.get("primitives", {})

    # Count primitives
    primitive_counts = {
        "weights": len(primitives.get("weights", [])),
        "constraints": len(primitives.get("constraints", [])),
        "conflicts": len(primitives.get("conflicts", [])),
        "baseline": 1 if primitives.get("baseline") else 0,
        "drifts": len(primitives.get("drifts", [])),
        "tradeoffs": len(primitives.get("tradeoffs", [])),
        "lineage": len(primitives.get("lineage", [])),
    }

    total_primitives = sum(primitive_counts.values())

    return ExplainabilityBlock(
        block_type=BlockType.DNA_PREVIEW,
        title="DNA Matrix Preview",
        content={
            "quarantined": dna_artifact.get("quarantined", True),
            "quarantine_label": "Quarantined" if dna_artifact.get("quarantined", True) else "Active",
            "total_primitives": total_primitives,
            "primitive_counts": primitive_counts,
            "audit_passed": dna_artifact.get("audit_passed", False),
        },
        metadata={
            "sherlock_report_id": dna_artifact.get("sherlock_report_id", ""),
            "created_at": dna_artifact.get("created_at", ""),
            "preview_only": True,  # Emphasize this is not persisted
        },
        sequence=sequence,
    )


# =============================================================================
# Main Adapter Function
# =============================================================================


def transform_sherlock_to_explainability(
    sherlock_result: Optional[Dict[str, Any]],
) -> Optional[ExplainabilityOutput]:
    """
    Transform Sherlock hook result into Explainability Blocks.

    Args:
        sherlock_result: Dict from SherlockHookResult.to_dict(), or None

    Returns:
        ExplainabilityOutput if Sherlock was enabled and produced output,
        None if Sherlock was disabled or no result available.

    Contracts referenced:
        - docs/contracts/SCH_SDK_CONTRACT.md#section-4-finalreport-schema
    """
    # Early exit if no result
    if sherlock_result is None:
        _logger.debug("[EXPLAINABILITY] No Sherlock result to transform")
        return None

    # Check if Sherlock was enabled
    if not sherlock_result.get("enabled", False):
        _logger.debug("[EXPLAINABILITY] Sherlock was disabled")
        return ExplainabilityOutput(
            enabled=False,
            blocks=[],
            summary={"reason": "sherlock_disabled"},
            generated_at=datetime.now(timezone.utc).isoformat(),
        )

    _logger.info("[EXPLAINABILITY] Transforming Sherlock result to explainability blocks")

    blocks: List[ExplainabilityBlock] = []
    sequence = 0

    # Block 1: Investigation Summary
    blocks.append(_build_investigation_summary_block(sherlock_result, sequence))
    sequence += 1

    # Block 2: Claim
    blocks.append(_build_claim_block(sherlock_result, sequence))
    sequence += 1

    # Block 3: Verdict
    blocks.append(_build_verdict_block(sherlock_result, sequence))
    sequence += 1

    # Block 4: Audit
    blocks.append(_build_audit_block(sherlock_result, sequence))
    sequence += 1

    # Block 5: DNA Preview (if DNA recording was enabled)
    dna_artifact = sherlock_result.get("dna_artifact")
    if dna_artifact:
        blocks.append(_build_dna_preview_block(dna_artifact, sequence))
        sequence += 1

    # Build summary
    summary = {
        "verdict": sherlock_result.get("verdict", "unknown"),
        "confidence": sherlock_result.get("confidence", 0.0),
        "audit_passed": sherlock_result.get("audit_passed", False),
        "iterations": sherlock_result.get("iterations_completed", 0),
        "has_dna_preview": dna_artifact is not None,
    }

    _logger.info(f"[EXPLAINABILITY] Generated {len(blocks)} blocks")

    return ExplainabilityOutput(
        enabled=True,
        blocks=blocks,
        summary=summary,
        generated_at=datetime.now(timezone.utc).isoformat(),
    )


def attach_explainability_to_debug(
    debug_dict: Dict[str, Any],
    sherlock_result: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Attach explainability output to a debug dict.

    This is a convenience function that transforms Sherlock result
    and attaches it under the 'explainability' key.

    Args:
        debug_dict: Existing debug dict to augment
        sherlock_result: Sherlock hook result dict

    Returns:
        The debug_dict with 'explainability' key added
    """
    explainability = transform_sherlock_to_explainability(sherlock_result)

    if explainability:
        debug_dict["explainability"] = explainability.to_dict()
    else:
        debug_dict["explainability"] = None

    return debug_dict
