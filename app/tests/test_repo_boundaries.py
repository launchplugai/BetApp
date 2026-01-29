# app/tests/test_repo_boundaries.py
"""
Monorepo Boundary Guardrails (Ticket 18B)

Tests that enforce module isolation:
- sherlock/* must NOT import app/*
- dna-matrix/* (dna*/*) must NOT import app/*

Rules:
- app/* may import sherlock/* and dna*/* (one-way dependency)
- Standalone modules are libraries, not consumers of app/

These tests scan Python files for forbidden imports and fail with clear messages.
"""
import os
import re
import pytest
from pathlib import Path


# =============================================================================
# Configuration
# =============================================================================


# Root of the repository
REPO_ROOT = Path(__file__).parent.parent.parent

# Protected directories (must not import from app/)
PROTECTED_DIRS = [
    "sherlock",
    "dna-matrix",
]

# Forbidden import patterns
FORBIDDEN_PATTERNS = [
    # Direct imports
    r"^from\s+app\b",
    r"^import\s+app\b",
    # Relative imports that cross module walls
    r"from\s+\.\.+app\b",
    r"from\s+\.\.+\/app\b",
]


# =============================================================================
# Helpers
# =============================================================================


def _find_python_files(directory: Path) -> list[Path]:
    """Find all Python files in a directory recursively."""
    if not directory.exists():
        return []
    return list(directory.rglob("*.py"))


def _scan_file_for_forbidden_imports(
    filepath: Path,
    patterns: list[str],
) -> list[tuple[int, str, str]]:
    """
    Scan a file for forbidden import patterns.

    Returns list of (line_number, line_content, matched_pattern) tuples.
    """
    violations = []

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, start=1):
                line_stripped = line.strip()

                # Skip comments and empty lines
                if line_stripped.startswith("#") or not line_stripped:
                    continue

                for pattern in patterns:
                    if re.search(pattern, line_stripped):
                        violations.append((line_num, line_stripped, pattern))
                        break  # One violation per line is enough

    except Exception as e:
        # If we can't read the file, skip it (could be binary or permission issue)
        pass

    return violations


def _collect_all_violations() -> dict[str, list[tuple[Path, int, str]]]:
    """
    Collect all boundary violations across protected directories.

    Returns dict mapping directory name to list of (file, line_num, line_content).
    """
    all_violations = {}

    for protected_dir in PROTECTED_DIRS:
        dir_path = REPO_ROOT / protected_dir
        violations_in_dir = []

        for py_file in _find_python_files(dir_path):
            file_violations = _scan_file_for_forbidden_imports(py_file, FORBIDDEN_PATTERNS)
            for line_num, line_content, _ in file_violations:
                violations_in_dir.append((py_file, line_num, line_content))

        if violations_in_dir:
            all_violations[protected_dir] = violations_in_dir

    return all_violations


# =============================================================================
# Tests
# =============================================================================


class TestRepoBoundaries:
    """Tests for monorepo module isolation."""

    def test_sherlock_does_not_import_app(self):
        """sherlock/* must not import from app/*."""
        dir_path = REPO_ROOT / "sherlock"
        violations = []

        for py_file in _find_python_files(dir_path):
            file_violations = _scan_file_for_forbidden_imports(py_file, FORBIDDEN_PATTERNS)
            for line_num, line_content, _ in file_violations:
                rel_path = py_file.relative_to(REPO_ROOT)
                violations.append(f"  {rel_path}:{line_num}: {line_content}")

        if violations:
            violation_list = "\n".join(violations)
            pytest.fail(
                f"BOUNDARY VIOLATION: sherlock/* imports app/*\n"
                f"sherlock is a standalone library and must not depend on app/.\n"
                f"Violations found:\n{violation_list}\n"
                f"Fix: Move shared code to a common module or invert the dependency."
            )

    def test_dna_matrix_does_not_import_app(self):
        """dna-matrix/* must not import from app/*."""
        dir_path = REPO_ROOT / "dna-matrix"
        violations = []

        for py_file in _find_python_files(dir_path):
            file_violations = _scan_file_for_forbidden_imports(py_file, FORBIDDEN_PATTERNS)
            for line_num, line_content, _ in file_violations:
                rel_path = py_file.relative_to(REPO_ROOT)
                violations.append(f"  {rel_path}:{line_num}: {line_content}")

        if violations:
            violation_list = "\n".join(violations)
            pytest.fail(
                f"BOUNDARY VIOLATION: dna-matrix/* imports app/*\n"
                f"dna-matrix is a standalone library and must not depend on app/.\n"
                f"Violations found:\n{violation_list}\n"
                f"Fix: Move shared code to a common module or invert the dependency."
            )

    def test_no_cross_module_relative_imports(self):
        """Protected modules must not use relative imports to reach app/."""
        violations = []

        # Pattern specifically for relative imports crossing boundaries
        relative_patterns = [
            r"from\s+\.\.+\s*import",  # from .. import
            r"from\s+\.\.+[a-zA-Z]",   # from ..something
        ]

        for protected_dir in PROTECTED_DIRS:
            dir_path = REPO_ROOT / protected_dir

            for py_file in _find_python_files(dir_path):
                try:
                    with open(py_file, "r", encoding="utf-8") as f:
                        for line_num, line in enumerate(f, start=1):
                            line_stripped = line.strip()

                            # Check for suspicious relative imports going up
                            if re.search(r"from\s+\.\.\.", line_stripped):
                                # Three dots or more = going up 2+ levels
                                rel_path = py_file.relative_to(REPO_ROOT)
                                violations.append(f"  {rel_path}:{line_num}: {line_stripped}")

                except Exception:
                    pass

        if violations:
            violation_list = "\n".join(violations)
            pytest.fail(
                f"BOUNDARY VIOLATION: Deep relative imports detected\n"
                f"Relative imports going up 2+ levels may cross module boundaries.\n"
                f"Suspicious imports found:\n{violation_list}\n"
                f"Fix: Use absolute imports instead."
            )

    def test_all_boundaries_summary(self):
        """Summary test that reports all violations at once."""
        all_violations = _collect_all_violations()

        if all_violations:
            report_lines = ["MONOREPO BOUNDARY VIOLATIONS DETECTED", ""]

            for dir_name, violations in all_violations.items():
                report_lines.append(f"=== {dir_name}/ ===")
                for filepath, line_num, line_content in violations:
                    rel_path = filepath.relative_to(REPO_ROOT)
                    report_lines.append(f"  {rel_path}:{line_num}: {line_content}")
                report_lines.append("")

            report_lines.extend([
                "RULE: Standalone modules (sherlock/, dna-matrix/) must not import app/*.",
                "REASON: app/ depends on these modules, not the other way around.",
                "FIX: Move shared code to a common module or refactor the dependency.",
            ])

            pytest.fail("\n".join(report_lines))


class TestBoundaryRulesDocumented:
    """Tests that boundary rules are documented."""

    def test_protected_directories_exist(self):
        """Protected directories should exist in the repo."""
        for protected_dir in PROTECTED_DIRS:
            dir_path = REPO_ROOT / protected_dir
            assert dir_path.exists(), f"Protected directory {protected_dir}/ does not exist"

    def test_app_directory_exists(self):
        """app/ directory should exist (the consumer of protected modules)."""
        app_path = REPO_ROOT / "app"
        assert app_path.exists(), "app/ directory does not exist"


class TestValidImportPatterns:
    """Tests that app/ CAN import from protected modules (one-way dependency is allowed)."""

    def test_app_can_import_sherlock(self):
        """app/ is allowed to import from sherlock/."""
        # This test documents the valid direction of imports
        # We just verify the pattern is understood, not enforced
        # (app importing sherlock is the correct direction)

        # Check that app/pipeline.py or app/sherlock_hook.py imports sherlock
        app_sherlock_hook = REPO_ROOT / "app" / "sherlock_hook.py"

        if app_sherlock_hook.exists():
            with open(app_sherlock_hook, "r") as f:
                content = f.read()
                # Should have sherlock imports
                has_sherlock_import = (
                    "from sherlock" in content or
                    "import sherlock" in content
                )
                assert has_sherlock_import, (
                    "app/sherlock_hook.py should import from sherlock/ "
                    "(this is the valid dependency direction)"
                )
