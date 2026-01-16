#!/usr/bin/env python3
"""Test runner that properly configures Python path before running pytest."""
import sys
from pathlib import Path

# Add dna-matrix to path BEFORE importing pytest
dna_matrix_path = Path(__file__).parent / "dna-matrix"
sys.path.insert(0, str(dna_matrix_path))

# Also add project root for app imports
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Now import and run pytest
import pytest

if __name__ == "__main__":
    # Pass through any command line arguments
    sys.exit(pytest.main(sys.argv[1:]))
