"""Configure pytest for the DNA project."""
import os
import sys
from pathlib import Path

# =============================================================================
# CI/Test Environment Configuration
# =============================================================================
# Set environment for tests BEFORE any imports
# This ensures rate limiting bypass is active for all tests
os.environ.setdefault("ENV", "test")
os.environ.setdefault("DNA_RATE_LIMIT_MODE", "ci")

# Add dna-matrix to path so tests can import core modules
# This must happen at module level (before test collection)
dna_matrix_path = Path(__file__).parent / "dna-matrix"
if str(dna_matrix_path) not in sys.path:
    sys.path.insert(0, str(dna_matrix_path))

# Also add app path for integration tests
app_path = Path(__file__).parent
if str(app_path) not in sys.path:
    sys.path.insert(0, str(app_path))


def pytest_configure(config):
    """Ensure paths and environment are set before test collection."""
    # Ensure CI mode is set for rate limiter
    os.environ.setdefault("ENV", "test")
    os.environ.setdefault("DNA_RATE_LIMIT_MODE", "ci")

    dna_path = str(Path(__file__).parent / "dna-matrix")
    if dna_path not in sys.path:
        sys.path.insert(0, dna_path)
