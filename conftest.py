"""Configure pytest for the DNA project."""
import sys
from pathlib import Path

# Add dna-matrix to path so tests can import core modules
dna_matrix_path = Path(__file__).parent / "dna-matrix"
sys.path.insert(0, str(dna_matrix_path))
