"""Configure pytest for the DNA project."""
import sys
from pathlib import Path

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
    """Ensure paths are set before test collection."""
    dna_path = str(Path(__file__).parent / "dna-matrix")
    if dna_path not in sys.path:
        sys.path.insert(0, dna_path)
