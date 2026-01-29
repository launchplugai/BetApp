# app/tests/test_module_boundaries.py
"""
Module Boundary Enforcement Tests (Ticket 18).

Enforces HARD MODULE WALLS per the Deliberate Monorepo Strategy:
- dna-matrix/* MUST NOT import app/*
- Future sherlock/* MUST NOT import app/*
- app/* MAY import from dna-matrix/* (one-way dependency)
- Dormant modules (alerts/, context/, auth/, billing/, persistence/)
  MUST NOT import from app/* when activated

These tests fail if forbidden imports are detected, preventing
accidental coupling between library-grade code and runtime code.
"""
import ast
import os
from pathlib import Path
from typing import Generator

import pytest


# =============================================================================
# Boundary Definitions
# =============================================================================

# Modules that MUST NOT import from app/*
LIBRARY_MODULES = [
    "dna-matrix",  # Core evaluation engine (library-grade)
]

# Future modules that will also be library-grade when created
FUTURE_LIBRARY_MODULES = [
    "sherlock",  # Sherlock logic (when created)
]

# Dormant modules that should not have app/* imports
DORMANT_MODULES = [
    "alerts",
    "context",
    "auth",
    "billing",
    "persistence",
]

# Forbidden import patterns (importing FROM app)
FORBIDDEN_IMPORT_SOURCES = [
    "app",
    "app.",
]


# =============================================================================
# AST-based Import Detection
# =============================================================================


def get_imports_from_file(filepath: Path) -> list[str]:
    """
    Parse a Python file and extract all import statements.

    Returns a list of module names that are imported.
    """
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            source = f.read()
    except (OSError, UnicodeDecodeError):
        return []

    try:
        tree = ast.parse(source, filename=str(filepath))
    except SyntaxError:
        return []

    imports = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.append(node.module)
                # Also capture full paths like "from app.config import X"
                for alias in node.names:
                    imports.append(f"{node.module}.{alias.name}")

    return imports


def find_python_files(directory: Path) -> Generator[Path, None, None]:
    """Recursively find all Python files in a directory."""
    if not directory.exists():
        return

    for filepath in directory.rglob("*.py"):
        # Skip __pycache__ and test files
        if "__pycache__" in str(filepath):
            continue
        yield filepath


def check_forbidden_imports(
    module_path: Path, forbidden_sources: list[str]
) -> list[tuple[Path, str]]:
    """
    Check all Python files in a module for forbidden imports.

    Returns a list of (filepath, import_name) tuples for violations.
    """
    violations = []

    for filepath in find_python_files(module_path):
        imports = get_imports_from_file(filepath)
        for imp in imports:
            for forbidden in forbidden_sources:
                if imp == forbidden or imp.startswith(f"{forbidden}."):
                    violations.append((filepath, imp))

    return violations


# =============================================================================
# Test Cases
# =============================================================================


def get_repo_root() -> Path:
    """Get the repository root directory."""
    # Navigate up from app/tests to find repo root
    return Path(__file__).resolve().parent.parent.parent


class TestModuleBoundaries:
    """Test suite for module boundary enforcement."""

    def test_dna_matrix_does_not_import_app(self):
        """
        dna-matrix/ MUST NOT import from app/*.

        The core evaluation engine is library-grade code that
        should have no dependencies on the FastAPI application.
        """
        repo_root = get_repo_root()
        dna_matrix_path = repo_root / "dna-matrix"

        if not dna_matrix_path.exists():
            pytest.skip("dna-matrix/ directory not found")

        violations = check_forbidden_imports(
            dna_matrix_path, FORBIDDEN_IMPORT_SOURCES
        )

        if violations:
            violation_details = "\n".join(
                f"  - {filepath.relative_to(repo_root)}: imports '{imp}'"
                for filepath, imp in violations
            )
            pytest.fail(
                f"Module boundary violation: dna-matrix/ imports from app/*\n"
                f"Violations:\n{violation_details}\n\n"
                f"dna-matrix/ is library-grade code and MUST NOT depend on app/"
            )

    def test_dormant_modules_do_not_import_app(self):
        """
        Dormant modules (alerts/, context/, auth/, etc.) MUST NOT import app/*.

        When these modules are activated in their designated sprints,
        they should remain independent of the FastAPI application layer.
        """
        repo_root = get_repo_root()
        all_violations = []

        for module_name in DORMANT_MODULES:
            module_path = repo_root / module_name

            if not module_path.exists():
                continue

            violations = check_forbidden_imports(
                module_path, FORBIDDEN_IMPORT_SOURCES
            )

            for filepath, imp in violations:
                all_violations.append((module_name, filepath, imp))

        if all_violations:
            violation_details = "\n".join(
                f"  - {module}/{filepath.relative_to(repo_root)}: imports '{imp}'"
                for module, filepath, imp in all_violations
            )
            pytest.fail(
                f"Module boundary violation: dormant modules import from app/*\n"
                f"Violations:\n{violation_details}\n\n"
                f"Dormant modules should remain independent of app/"
            )

    def test_future_sherlock_does_not_import_app(self):
        """
        sherlock/ (when created) MUST NOT import from app/*.

        This test passes if sherlock/ doesn't exist yet.
        When created, it must be library-grade code.
        """
        repo_root = get_repo_root()
        sherlock_path = repo_root / "sherlock"

        if not sherlock_path.exists():
            # Pass - sherlock doesn't exist yet, which is fine
            return

        violations = check_forbidden_imports(
            sherlock_path, FORBIDDEN_IMPORT_SOURCES
        )

        if violations:
            violation_details = "\n".join(
                f"  - {filepath.relative_to(repo_root)}: imports '{imp}'"
                for filepath, imp in violations
            )
            pytest.fail(
                f"Module boundary violation: sherlock/ imports from app/*\n"
                f"Violations:\n{violation_details}\n\n"
                f"sherlock/ is library-grade code and MUST NOT depend on app/"
            )


class TestBoundaryContract:
    """Verify the boundary contract is documented and enforced."""

    def test_contract_documentation_exists(self):
        """
        Module boundary contract documentation must exist.
        """
        repo_root = get_repo_root()
        contract_path = repo_root / "docs" / "contracts" / "MODULE_BOUNDARY_CONTRACT.md"

        # Contract will be created as part of this ticket
        # This test documents the requirement
        if not contract_path.exists():
            pytest.skip(
                "MODULE_BOUNDARY_CONTRACT.md not yet created. "
                "This is expected during initial implementation."
            )

    def test_library_modules_are_independent(self):
        """
        All library modules should be importable without app/ dependencies.

        This verifies that library code can be used standalone.
        """
        repo_root = get_repo_root()

        for module_name in LIBRARY_MODULES:
            module_path = repo_root / module_name

            if not module_path.exists():
                continue

            violations = check_forbidden_imports(
                module_path, FORBIDDEN_IMPORT_SOURCES
            )

            assert not violations, (
                f"{module_name}/ has forbidden imports from app/*. "
                f"Library modules must be independent."
            )


# =============================================================================
# Boundary Report (for debugging)
# =============================================================================


def generate_boundary_report() -> dict:
    """
    Generate a report of all module boundaries and their status.

    Returns a dict with boundary status for each module.
    """
    repo_root = get_repo_root()
    report = {
        "repo_root": str(repo_root),
        "library_modules": {},
        "dormant_modules": {},
        "boundary_contract_version": "1.0.0",
    }

    # Check library modules
    for module_name in LIBRARY_MODULES:
        module_path = repo_root / module_name
        if module_path.exists():
            violations = check_forbidden_imports(
                module_path, FORBIDDEN_IMPORT_SOURCES
            )
            report["library_modules"][module_name] = {
                "exists": True,
                "violations": len(violations),
                "status": "PASS" if not violations else "FAIL",
            }
        else:
            report["library_modules"][module_name] = {
                "exists": False,
                "violations": 0,
                "status": "N/A",
            }

    # Check dormant modules
    for module_name in DORMANT_MODULES:
        module_path = repo_root / module_name
        if module_path.exists():
            violations = check_forbidden_imports(
                module_path, FORBIDDEN_IMPORT_SOURCES
            )
            report["dormant_modules"][module_name] = {
                "exists": True,
                "violations": len(violations),
                "status": "PASS" if not violations else "FAIL",
            }
        else:
            report["dormant_modules"][module_name] = {
                "exists": False,
                "violations": 0,
                "status": "N/A",
            }

    return report


if __name__ == "__main__":
    # Run as script to see boundary report
    import json

    report = generate_boundary_report()
    print(json.dumps(report, indent=2))
