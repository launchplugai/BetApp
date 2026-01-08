"""Configure pytest for dna-matrix."""
import sys
from pathlib import Path

# Add dna-matrix to path so tests can import core modules
sys.path.insert(0, str(Path(__file__).parent.parent))
