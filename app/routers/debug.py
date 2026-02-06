# app/routers/debug.py
"""
Debug Router - System introspection endpoints (Ticket 18).

Provides visibility into:
- Build/deploy info
- Contract versions
- Feature flag states
- Module boundary status
- Sherlock/DNA proof system status

These endpoints expose NON-SENSITIVE metadata only.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.build_info import get_build_info
from app.config import load_config
from app.proof import get_proof_summary, get_recent_proofs

_logger = logging.getLogger(__name__)

router = APIRouter(prefix="/debug", tags=["Debug"])

# =============================================================================
# Contract Versions
# =============================================================================

# Contract version constants (update when contracts change)
CONTRACT_VERSIONS = {
    "module_boundary": "1.0.0",
    "evaluation_response": "1.0.0",
    "tier_policy": "1.0.0",
    "proof_record": "1.0.0",
}


# =============================================================================
# Endpoints
# =============================================================================


@router.get("/contracts")
async def get_contracts():
    """
    Get contract and system status information.

    Returns:
        JSON with:
        - git_sha: Current deploy commit
        - build_time_utc: When the build was created
        - contract_versions: Version of each contract
        - flag_states: Current feature flag values
        - module_boundary_status: Library module independence status
    """
    # Build info
    build_info = get_build_info()

    # Config (feature flags)
    config = load_config(fail_fast=False)

    # Module boundary status (run boundary check)
    boundary_status = _check_module_boundaries()

    # Proof system status
    proof_summary = get_proof_summary()

    return {
        "git_sha": build_info.commit,
        "build_time_utc": build_info.build_time_utc,
        "server_time_utc": datetime.now(timezone.utc).isoformat(),
        "contract_versions": CONTRACT_VERSIONS,
        "flag_states": {
            "leading_light_enabled": config.leading_light_enabled,
            "voice_enabled": config.voice_enabled,
            "sherlock_enabled": config.sherlock_enabled,
            "dna_recording_enabled": config.dna_recording_enabled,
        },
        "module_boundary_status": boundary_status,
        "proof_system": proof_summary,
    }


@router.get("/sherlock-dna/recent")
async def get_recent_proof_records(limit: int = 10):
    """
    Get recent Sherlock/DNA proof records.

    Args:
        limit: Maximum number of records to return (default 10, max 50)

    Returns:
        JSON with recent proof records (no PII, derived data only)
    """
    # Clamp limit
    limit = min(max(1, limit), 50)

    config = load_config(fail_fast=False)
    proofs = get_recent_proofs(limit)

    return {
        "sherlock_enabled": config.sherlock_enabled,
        "dna_recording_enabled": config.dna_recording_enabled,
        "record_count": len(proofs),
        "records": proofs,
    }


# =============================================================================
# Module Boundary Check
# =============================================================================


def _check_module_boundaries() -> dict:
    """
    Check module boundaries at runtime.

    Returns status for each library module.
    This is a lightweight check - full validation is in tests.
    """
    repo_root = Path(__file__).resolve().parent.parent.parent

    library_modules = {
        "dna-matrix": repo_root / "dna-matrix",
    }

    dormant_modules = {
        "alerts": repo_root / "alerts",
        "context": repo_root / "context",
        "auth": repo_root / "auth",
        "billing": repo_root / "billing",
        "persistence": repo_root / "persistence",
    }

    future_modules = {
        "sherlock": repo_root / "sherlock",
    }

    result = {
        "library_modules": {},
        "dormant_modules": {},
        "future_modules": {},
        "overall_status": "PASS",
    }

    # Check library modules exist
    for name, path in library_modules.items():
        result["library_modules"][name] = {
            "exists": path.exists(),
            "status": "OK" if path.exists() else "MISSING",
        }

    # Check dormant modules
    for name, path in dormant_modules.items():
        result["dormant_modules"][name] = {
            "exists": path.exists(),
            "status": "DORMANT" if path.exists() else "N/A",
        }

    # Check future modules (should not exist yet)
    for name, path in future_modules.items():
        result["future_modules"][name] = {
            "exists": path.exists(),
            "status": "EXISTS" if path.exists() else "NOT_YET_CREATED",
        }

    return result


@router.get("/ocr-health")
async def ocr_health_check():
    """Check if OCR dependencies are configured."""
    import os
    
    openai_key_present = bool(os.environ.get("OPENAI_API_KEY"))
    openai_key_length = len(os.environ.get("OPENAI_API_KEY", "")) if openai_key_present else 0
    leading_light_enabled = os.environ.get("LEADING_LIGHT_ENABLED", "false").lower() == "true"
    
    def _diagnose():
        if not leading_light_enabled:
            return "LEADING_LIGHT_ENABLED is not set to 'true' in Railway environment variables"
        if not openai_key_present:
            return "OPENAI_API_KEY is missing from Railway environment variables"
        if openai_key_length < 20:
            return "OPENAI_API_KEY is too short (should be ~51 chars, starts with sk-)"
        return "Configuration looks good"
    
    return {
        "ocr_ready": openai_key_present and leading_light_enabled,
        "openai_api_key": {
            "present": openai_key_present,
            "length": openai_key_length,
            "valid_format": openai_key_length > 20 and os.environ.get("OPENAI_API_KEY", "").startswith("sk-") if openai_key_present else False
        },
        "leading_light_enabled": leading_light_enabled,
        "diagnosis": _diagnose()
    }
