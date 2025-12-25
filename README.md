# DNA Matrix

> A decision engine disguised as a data system.

DNA Matrix models **variation over shared substrate**. Brands, people, companies, products, strategies, AI agents—they all share structural similarity. Meaningful difference comes from margins, weights, interactions, constraints, and rate of change.

## The Question It Answers

Not "What is this?" but **"What kind of thing is this becoming, and is that safe?"**

## Core Primitives (v0.1 Genome)

The system is built on 7 frozen primitives:

| Primitive | Purpose |
|-----------|---------|
| **weight** | Relative importance |
| **constraint** | Boundary on valid states |
| **conflict** | Competing forces |
| **baseline** | Reference state for comparison |
| **drift** | Deviation from baseline (computed) |
| **tradeoff** | Exchange of one value for another |
| **lineage** | Provenance and causal history |

## Key Concepts

- **Organism**: The entity being modeled (brand, person, agent, product, org)
- **Claim**: Atomic assertion about an organism through a lens
- **Mutation**: The only way claims change (append-only)
- **Conflict**: When claims cannot both be true
- **Projection**: Computed view (matrix, timeline, summary)

## Structural Invariants

1. Claims are the units of meaning
2. Mutations are the only way claims change
3. Lineage is append-only
4. Constraints attach to claims and validate mutations
5. Conflicts are relations between claims
6. Drift and coherence are computed from stored causes
7. Matrix is a projection, never the source of truth

## Documentation

See `/docs` for full specifications:

| Document | Purpose |
|----------|---------|
| [CONCEPT.md](docs/CONCEPT.md) | Why this system exists |
| [PRINCIPLES.md](docs/PRINCIPLES.md) | Non-negotiable laws |
| [PRIMITIVES.md](docs/PRIMITIVES.md) | The 7 frozen primitives |
| [ARCHITECTURE.md](docs/ARCHITECTURE.md) | Data structures and storage |
| [INTERACTIONS.md](docs/INTERACTIONS.md) | How primitives affect each other |
| [CONSTRAINT_LANGUAGE.md](docs/CONSTRAINT_LANGUAGE.md) | Rule syntax and validation |
| [CONFLICT_DETECTION.md](docs/CONFLICT_DETECTION.md) | When and how conflicts fire |
| [API_SCHEMAS.md](docs/API_SCHEMAS.md) | Request/response contracts |
| [SDK_SPECIFICATION.md](docs/SDK_SPECIFICATION.md) | Python SDK design |
| [IMPLEMENTATION_PLAN.md](docs/IMPLEMENTATION_PLAN.md) | 8-week build roadmap |

## Project Structure

```
dna-matrix/
├── core/
│   ├── models/          # Data models (Organism, Claim, etc.)
│   ├── engine/          # Mutation engine
│   ├── constraints/     # Constraint language + evaluation
│   ├── conflicts/       # Conflict detection + resolution
│   ├── query/           # Evaluate, simulate, diff, explain
│   └── projections/     # View generation
├── storage/
│   └── sqlite/          # SQLite implementation
├── api/
│   ├── routes/          # FastAPI endpoints
│   └── schemas/         # Request/response models
├── sdk/
│   └── dna_matrix/      # Python SDK
├── docs/                # Design specifications
└── tests/               # Test suite
```

## Quick Start

```bash
# Clone and setup
git clone <repo>
cd dna-matrix
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Run tests
pytest tests/ -v
```

## Development Status

**Phase 1: Foundation** (In Progress)
- [x] Core models (Organism, Claim, Value, etc.)
- [ ] SQLite storage layer
- [ ] Mutation engine
- [ ] Lineage tracking

See [IMPLEMENTATION_PLAN.md](docs/IMPLEMENTATION_PLAN.md) for full roadmap.

## License

TBD
