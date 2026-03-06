"""
Wiring contract tests — driven by docs/designs/09-ui-schematics.contracts.json.

These tests make the repo fail loudly when someone:
- Adds a screen without updating the contract
- Bypasses AUTH with raw sessionStorage access
- Forgets to extend base.html
- Mismatches auth requirements between SCREENS dict and contract
- Removes an evaluate route alias

Run: pytest tests/contracts/test_wiring_contracts.py -v
"""
import json
import re
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
CONTRACTS_PATH = REPO_ROOT / "docs" / "designs" / "09-ui-schematics.contracts.json"
TEMPLATES_DIR = REPO_ROOT / "app" / "templates"
WEB_ROUTER_PATH = REPO_ROOT / "app" / "routers" / "web.py"


@pytest.fixture(scope="module")
def contracts():
    """Load the contracts JSON."""
    assert CONTRACTS_PATH.exists(), f"Contracts file missing: {CONTRACTS_PATH}"
    with open(CONTRACTS_PATH) as f:
        return json.load(f)


@pytest.fixture(scope="module")
def screens_dict():
    """Extract the SCREENS dict from web.py at import time."""
    # Import the actual SCREENS dict from the router module
    import sys
    sys.path.insert(0, str(REPO_ROOT))
    from app.routers.web import SCREENS
    return SCREENS


# ===========================================================================
# 1. Screen Registry Parity
# ===========================================================================

class TestScreenRegistryParity:
    """SCREENS dict in web.py must match contracts JSON exactly."""

    def test_same_screen_names(self, contracts, screens_dict):
        """Contract and SCREENS dict must list the same screens."""
        contract_screens = set(contracts["screens"].keys())
        code_screens = set(screens_dict.keys())
        assert contract_screens == code_screens, (
            f"Mismatch!\n"
            f"  In contract but not code: {contract_screens - code_screens}\n"
            f"  In code but not contract: {code_screens - contract_screens}"
        )

    def test_auth_requirements_match(self, contracts, screens_dict):
        """require_auth must be identical in contract and SCREENS dict."""
        for name, spec in contracts["screens"].items():
            code_auth = screens_dict[name]["require_auth"]
            contract_auth = spec["require_auth"]
            assert code_auth == contract_auth, (
                f"Screen '{name}': code says require_auth={code_auth}, "
                f"contract says {contract_auth}"
            )

    def test_template_paths_match(self, contracts, screens_dict):
        """Template paths must be identical in contract and SCREENS dict."""
        for name, spec in contracts["screens"].items():
            code_template = screens_dict[name]["template"]
            contract_template = spec["template"]
            assert code_template == contract_template, (
                f"Screen '{name}': code template='{code_template}', "
                f"contract template='{contract_template}'"
            )


# ===========================================================================
# 2. Template Files Exist
# ===========================================================================

class TestTemplateFilesExist:
    """Every template referenced in the contract must exist on disk."""

    def test_all_templates_exist(self, contracts):
        for name, spec in contracts["screens"].items():
            template_path = TEMPLATES_DIR / spec["template"]
            assert template_path.exists(), (
                f"Screen '{name}' references template '{spec['template']}' "
                f"but file not found at {template_path}"
            )

    def test_base_template_exists(self, contracts):
        base = contracts["template_contract"]["base_template"]
        assert (TEMPLATES_DIR / base).exists(), f"Base template '{base}' not found"


# ===========================================================================
# 3. Template Inheritance
# ===========================================================================

class TestTemplateInheritance:
    """Templates that should extend base.html must actually do so."""

    def test_screens_extend_base(self, contracts):
        marker = contracts["template_contract"]["extends_marker"]
        for name, spec in contracts["screens"].items():
            if not spec["extends_base"]:
                continue  # skip screens that intentionally don't extend base
            template_path = TEMPLATES_DIR / spec["template"]
            content = template_path.read_text()
            assert marker in content, (
                f"Screen '{name}' ({spec['template']}) must contain "
                f"'{marker}' but doesn't"
            )

    def test_non_extending_screens_documented(self, contracts):
        """Screens that don't extend base.html must be explicitly marked."""
        non_extending = [
            name for name, spec in contracts["screens"].items()
            if not spec["extends_base"]
        ]
        # Onboarding is the only known exception
        assert non_extending == ["onboarding"], (
            f"Unexpected screens not extending base.html: {non_extending}. "
            f"If intentional, update the contract."
        )


# ===========================================================================
# 4. No Raw Token Access in Authenticated Screens
# ===========================================================================

class TestNoRawTokenAccess:
    """Authenticated screens must not bypass AUTH utility."""

    def test_no_raw_session_storage_token_access(self, contracts):
        rule = contracts["auth_contract"]["rules"]["no_raw_token_access"]
        pattern = re.compile(rule["forbidden_pattern"])
        for screen_name in rule["applies_to_screens"]:
            spec = contracts["screens"][screen_name]
            template_path = TEMPLATES_DIR / spec["template"]
            content = template_path.read_text()
            matches = pattern.findall(content)
            assert not matches, (
                f"Screen '{screen_name}' has raw token access: "
                f"found {len(matches)} occurrence(s) of "
                f"sessionStorage.getItem('dna_auth_token'). "
                f"Use AUTH.getAccessToken() instead."
            )


# ===========================================================================
# 5. Evaluate Route Exists
# ===========================================================================

class TestEvaluateRoute:
    """The evaluate endpoint must be wired at all declared paths."""

    def test_evaluate_routes_in_code(self, contracts):
        """All evaluate paths must appear as decorators in web.py."""
        web_code = WEB_ROUTER_PATH.read_text()
        for path in contracts["routes"]["evaluate"]["paths"]:
            # Look for the path in a router decorator
            assert path in web_code, (
                f"Evaluate path '{path}' not found in {WEB_ROUTER_PATH}"
            )

    def test_evaluate_uses_post(self, contracts):
        """Evaluate must be POST only."""
        web_code = WEB_ROUTER_PATH.read_text()
        for path in contracts["routes"]["evaluate"]["paths"]:
            # Should appear in a @router.post decorator
            decorator_pattern = f'@router.post("{path}")'
            assert decorator_pattern in web_code, (
                f"Expected {decorator_pattern} in web.py"
            )


# ===========================================================================
# 6. AUTH Utility Required Methods
# ===========================================================================

class TestAuthUtility:
    """auth.js must export all required methods."""

    @pytest.fixture(scope="class")
    def auth_js_content(self):
        auth_path = REPO_ROOT / "app" / "web_assets" / "static" / "js" / "auth.js"
        assert auth_path.exists(), f"auth.js not found at {auth_path}"
        return auth_path.read_text()

    def test_all_required_methods_exist(self, contracts, auth_js_content):
        for method in contracts["auth_contract"]["required_methods"]:
            assert method in auth_js_content, (
                f"AUTH.{method} not found in auth.js"
            )


# ===========================================================================
# 7. Protocol Endpoints Exist
# ===========================================================================

class TestProtocolEndpoints:
    """Protocol router must expose all contracted endpoints."""

    @pytest.fixture(scope="class")
    def protocol_router_code(self):
        path = REPO_ROOT / "app" / "protocol" / "router.py"
        assert path.exists(), f"Protocol router not found at {path}"
        return path.read_text()

    def test_feed_endpoint_exists(self, contracts, protocol_router_code):
        """GET /api/protocols/{id}/feed must exist."""
        assert "/feed" in protocol_router_code, (
            "Protocol feed endpoint not found in router.py"
        )

    def test_snapshot_v2_endpoint_exists(self, contracts, protocol_router_code):
        """GET /api/protocols/{id}/snapshot-v2 must exist."""
        assert "/snapshot-v2" in protocol_router_code, (
            "Protocol snapshot-v2 endpoint not found in router.py"
        )


# ===========================================================================
# 8. Bet Model Has Traceability Fields
# ===========================================================================

class TestBetModelFields:
    """Bet model must have all spec-required traceability fields."""

    def test_bet_model_has_required_fields(self, contracts):
        import sys
        sys.path.insert(0, str(REPO_ROOT))
        from app.models import Bet
        column_names = {c.name for c in Bet.__table__.columns}
        required = contracts["persistence_contract"]["bet_fields"]
        missing = [f for f in required if f not in column_names]
        assert not missing, (
            f"Bet model missing fields: {missing}. "
            f"Has: {sorted(column_names)}"
        )


# ===========================================================================
# 9. Protocol Model Has Strategy Fields
# ===========================================================================

class TestProtocolModelFields:
    """Protocol model must have rules, enabled, visibility."""

    def test_protocol_model_has_required_fields(self, contracts):
        import sys
        sys.path.insert(0, str(REPO_ROOT))
        from app.protocol.models import Protocol
        column_names = {c.name for c in Protocol.__table__.columns}
        required = contracts["protocol_contract"]["model_fields"]
        missing = [f for f in required if f not in column_names]
        assert not missing, (
            f"Protocol model missing fields: {missing}. "
            f"Has: {sorted(column_names)}"
        )


# ===========================================================================
# 10. History Filters
# ===========================================================================

class TestHistoryFilters:
    """History endpoint must support all contracted filters."""

    @pytest.fixture(scope="class")
    def bets_router_code(self):
        path = REPO_ROOT / "app" / "routers" / "bets.py"
        assert path.exists()
        return path.read_text()

    def test_history_supports_contracted_filters(self, contracts, bets_router_code):
        """GET /api/bets/history must accept all filter params."""
        required_filters = contracts["persistence_contract"]["filterable_by"]
        for f in required_filters:
            assert f in bets_router_code, (
                f"History endpoint missing filter param '{f}' in bets.py"
            )


# ===========================================================================
# 11. Contract Version & Completeness
# ===========================================================================

class TestContractMeta:
    """Basic contract file sanity."""

    def test_has_version(self, contracts):
        assert "version" in contracts

    def test_has_screens(self, contracts):
        assert len(contracts["screens"]) > 0

    def test_has_evaluate_contract(self, contracts):
        assert "evaluate_contract" in contracts

    def test_has_auth_contract(self, contracts):
        assert "auth_contract" in contracts

    def test_has_protocol_contract(self, contracts):
        assert "protocol_contract" in contracts

    def test_has_persistence_contract(self, contracts):
        assert "persistence_contract" in contracts

    def test_has_error_contract(self, contracts):
        assert "error_contract" in contracts["evaluate_contract"]

    def test_has_global_error_contract(self, contracts):
        assert "error_contract" in contracts

    def test_has_preferences_contract(self, contracts):
        assert "preferences_contract" in contracts


# ===========================================================================
# 12. Global Error Handler Exists
# ===========================================================================

class TestGlobalErrorHandler:
    """main.py must have global exception handlers for standard error envelope."""

    @pytest.fixture(scope="class")
    def main_code(self):
        path = REPO_ROOT / "app" / "main.py"
        assert path.exists()
        return path.read_text()

    def test_http_exception_handler_exists(self, main_code):
        """Global HTTPException handler must exist."""
        assert "exception_handler(HTTPException)" in main_code, (
            "Global HTTPException handler not found in main.py"
        )

    def test_validation_exception_handler_exists(self, main_code):
        """Global RequestValidationError handler must exist."""
        assert "exception_handler(RequestValidationError)" in main_code, (
            "RequestValidationError handler not found in main.py"
        )

    def test_error_envelope_shape(self, main_code):
        """Error handler must produce {error: {code, message, details}}."""
        assert '"code"' in main_code and '"message"' in main_code and '"details"' in main_code, (
            "Error handler must include code, message, details fields"
        )


# ===========================================================================
# 13. Preferences Applied in Evaluate
# ===========================================================================

class TestPreferencesInEvaluate:
    """Evaluate endpoint must support preferences_applied block."""

    @pytest.fixture(scope="class")
    def web_code(self):
        return WEB_ROUTER_PATH.read_text()

    def test_preferences_applied_block_exists(self, web_code):
        """evaluate_proxy must include preferences_applied in response."""
        assert "preferences_applied" in web_code, (
            "preferences_applied block not found in web.py evaluate endpoint"
        )

    def test_loads_user_preferences(self, web_code):
        """evaluate_proxy must load UserPreferences when auth present."""
        assert "UserPreferences" in web_code, (
            "UserPreferences import not found in web.py"
        )

    def test_risk_profile_included(self, web_code):
        """preferences_applied must include risk_profile."""
        assert "risk_profile" in web_code, (
            "risk_profile not found in web.py preferences block"
        )
