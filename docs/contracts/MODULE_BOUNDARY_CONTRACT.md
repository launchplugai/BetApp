# Module Boundary Contract

> **Version:** 1.0.0 | **Created:** 2026-01-29 | **Status:** ACTIVE

---

## Purpose

This contract defines the HARD MODULE WALLS that enforce separation between library-grade code and runtime code in the DNA Bet Engine monorepo.

The goal is to maintain a **Deliberate Monorepo** strategy where:
- Library modules can be extracted and used independently
- Runtime code (FastAPI app) can import libraries but not vice versa
- Clear boundaries prevent accidental coupling

---

## Module Categories

### 1. Library Modules (MUST NOT import `app/*`)

| Module | Path | Description |
|--------|------|-------------|
| **dna-matrix** | `/dna-matrix/` | Core evaluation engine (frozen) |
| **sherlock** | `/sherlock/` | Sherlock logic (future) |

These modules are library-grade and:
- Can be used outside of the FastAPI application
- MUST NOT have any imports from `app/*`
- Should only depend on standard library and whitelisted packages

### 2. Runtime Module (MAY import library modules)

| Module | Path | Description |
|--------|------|-------------|
| **app** | `/app/` | FastAPI application (routes, UI, integration) |

The runtime module:
- MAY import from library modules (one-way dependency)
- Contains all FastAPI-specific code
- Handles HTTP routing, templates, middleware

### 3. Dormant Modules (MUST NOT import `app/*` when activated)

| Module | Path | Sprint | Description |
|--------|------|--------|-------------|
| alerts | `/alerts/` | Sprint 4 | Proactive signals |
| context | `/context/` | Sprint 3 | Injury/weather/trade data |
| auth | `/auth/` | Future | JWT authentication |
| billing | `/billing/` | Sprint 5 | Stripe payments |
| persistence | `/persistence/` | Future | Database storage |

When activated, these modules:
- MUST remain independent of `app/*`
- Should be library-grade code
- `app/*` may import from them (one-way)

---

## Boundary Rules

### HARD RULES (Enforced by Tests)

1. **`dna-matrix/*` MUST NOT import `app/*`**
   - The core engine is library-grade
   - No FastAPI dependencies allowed
   - Violation = test failure

2. **Dormant modules MUST NOT import `app/*`**
   - When activated, they remain library-grade
   - Violation = test failure

3. **Future `sherlock/*` MUST NOT import `app/*`**
   - When created, it will be library-grade
   - Test enforced from creation

4. **`app/*` MAY import from library modules**
   - This is the intended one-way dependency
   - `app/pipeline.py` imports from `core.evaluation`

### SOFT RULES (Design Guidance)

1. No circular dependencies between modules
2. Minimize dependencies between dormant modules
3. Keep library modules focused and cohesive

---

## Enforcement

### Automated Tests

Module boundaries are enforced by `app/tests/test_module_boundaries.py`:

```bash
pytest app/tests/test_module_boundaries.py -v
```

Tests check:
- All Python files in library modules for forbidden imports
- Uses AST parsing to detect `import app.*` and `from app.* import`
- Fails immediately on any violation

### Runtime Check

The `/debug/contracts` endpoint reports boundary status:

```bash
curl http://localhost:8000/debug/contracts | jq .module_boundary_status
```

---

## Violation Response

If a boundary violation is detected:

1. **CI/Test Failure**: Tests must fail
2. **Block Merge**: PR cannot be merged with violations
3. **Fix Required**: Developer must refactor to remove the import
4. **No Exceptions**: "I need it for convenience" is not valid

---

## Adding New Modules

When adding a new top-level module:

1. **Get PO Approval**: Module scope gate requires approval
2. **Decide Category**: Library or runtime?
3. **Update This Contract**: Add to appropriate category table
4. **Add Boundary Tests**: Update test file to include new module
5. **Document Dependencies**: Specify what it may/must not import

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-01-29 | Initial contract (Ticket 18) |

---

## Related Documents

- `CLAUDE.md`: Project governance and module scope gate
- `docs/RALPH_LOOP.md`: Sprint advancement gates
- `app/tests/test_module_boundaries.py`: Automated enforcement
