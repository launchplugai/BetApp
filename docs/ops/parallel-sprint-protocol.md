# The OpenClaw Parallel Sprint Protocol (PSP)

**Version:** 1.0  
**Date:** 2026-02-14  
**Classification:** Canon - Mandatory for S22+  

---

## The Doctrine

> **Single-threaded development is a luxury. Parallel execution is survival.**

When features have clear component boundaries, we do not serialize. We parallelize. This document canonizes the 4-agent architecture proven effective during S20.

---

## Agent Hierarchy (Fixed)

| Tier | Codename | Model | Role | Scope |
|------|----------|-------|------|-------|
| **Brain** | Architect | Kimi 2.5 | Orchestration | Main session, task decomposition, validation, merge |
| **Hands-1** | Backend | Kimi Light | Implementation | Services, models, business logic |
| **Hands-2** | Frontend | Kimi Light | Implementation | UI, CSS, client-side JS |
| **Hands-3** | Data | Kimi Light | Implementation | Database, migrations, admin tools |
| **Hands-4** | Infra | Kimi Light | Implementation | Config, delivery, integrations |
| **Fingers** | Precision | Claude CLI | Detail work | Refactoring, complex algorithms, precision tasks |
| **Runner** | Validator | GPT-4 Mini | Execution | Smoke tests, validation, monitoring |

**Rule:** Never exceed 4 Hands agents simultaneously. Coordination overhead exceeds benefit at N=5+.

---

## Sprint Initiation Protocol

### Step 1: Architecture Decision (Brain only)
**Duration:** 5 minutes  
**Output:** Sprint spec with component boundaries

Before spawning agents, Brain must define:
1. **Component boundaries** - which files each Hand owns
2. **Interface contracts** - data structures each component expects/produces
3. **Integration points** - where components touch (minimize these)
4. **Validation criteria** - how we know it's done

**Template:**
```markdown
## Sprint [ID]: [Name]

### Components
- **Backend:** Services, models, API routes
- **Frontend:** Templates, JS, CSS
- **Data:** Migrations, admin, reporting
- **Infra:** Config, feature flags, delivery

### Interfaces
- Backend exposes: `ServiceX.process()` returns `ResultType`
- Frontend expects: API at `/api/feature` returns `SchemaY`
- Data provides: Tables with indexes on `(user_id, created_at)`
- Infra configures: `FEATURE_ENABLED` flag, defaults OFF

### Validation
- [ ] All tests pass (>90%)
- [ ] Migration runs successfully
- [ ] Feature flag defaults OFF
- [ ] No merge conflicts
```

---

### Step 2: Parallel Agent Spawn (Brain only)
**Duration:** 2 minutes  
**Command:** `sessions_spawn` with scoped tasks

Spawn order matters:
1. **Data first** (sets schema for others)
2. **Backend second** (implements interfaces)
3. **Frontend third** (consumes APIs)
4. **Infra last** (ties it together)

**Task specification must include:**
- Exact file paths (no ambiguity)
- Interface contracts from Step 1
- Explicit "DO NOT TOUCH" files
- Timeout (default: 10 minutes)

---

### Step 3: Execution Phase (Hands only)
**Duration:** 10-15 minutes  
**Brain activity:** Monitor, answer questions, no intervention

Hands work independently. Brain only responds to:
- Direct questions about interfaces
- Blockers requiring architectural change
- Completion notifications

**Brain does NOT:**
- Code review during execution
- Micromanage implementation
- Change interfaces mid-flight

---

### Step 4: Integration (Brain only)
**Duration:** 5 minutes  
**Actions:**
1. Check out all changes
2. Run compilation/imports check
3. Execute test suite
4. Fix obvious conflicts (usually imports)
5. Commit with comprehensive message

**Merge conflict resolution priority:**
1. Data agent wins on schema/migrations
2. Backend agent wins on API contracts
3. Frontend agent wins on UI decisions
4. Infra agent wins on config defaults

---

### Step 5: Deployment (Brain + Runner)
**Duration:** 5 minutes  
**Actions:**
1. Push to origin
2. Deploy via railway
3. Run smoke tests (Runner)
4. Verify feature flags are OFF
5. Document completion

---

## Handoff Protocols

### Between Backend and Frontend
**Interface:** JSON API contract

Backend provides:
```python
class ResponseSchema(BaseModel):
    success: bool
    data: Optional[Dict]
    error: Optional[str]
```

Frontend expects:
- Endpoint at documented path
- Status codes: 200 success, 400 client error, 500 server error
- Consistent error message format

---

### Between Data and Backend
**Interface:** SQLAlchemy models

Data owns:
- Table definitions
- Migration scripts
- Index decisions

Backend consumes:
- Models via `from app.models import X`
- Never writes raw SQL
- Assumes indexes exist for queries

---

### Between Infra and Everyone
**Interface:** Feature flags + Config

Infra provides:
```python
@dataclass
class AppConfig:
    FEATURE_ENABLED: bool = False  # ALWAYS default OFF
    FEATURE_KILL_SWITCH: bool = False
```

Everyone checks:
```python
if not config.FEATURE_ENABLED:
    return {"status": "disabled"}
```

---

## Conflict Prevention Rules

### Rule 1: File Ownership
Each Hand has exclusive write on assigned files. If overlap unavoidable:
- Backend writes the `.py` file
- Frontend writes the `.html` template that uses it
- Data writes the migration
- Infra updates imports/config

### Rule 2: Append-Only to Shared Files
For `__init__.py`, `main.py`, `config.py`:
- Add imports at end of file
- Never restructure existing code
- Brain resolves ordering post-merge

### Rule 3: Schema First
Data agent's migration is law. If Backend needs different schema:
- Backend adapts to schema, not vice versa
- Migration changes require Brain approval + restart

---

## Quality Gates

### Gate 1: Compilation (Automatic)
```bash
python3 -c "from app.main import app"  # Must import cleanly
```

### Gate 2: Unit Tests (Automatic)
```bash
pytest app/tests/test_{component}.py -v
# Minimum: 80% pass rate to merge
# Target: 90%+ pass rate
```

### Gate 3: Integration (Manual)
```bash
curl /health  # Service responds
git log -1   # Commit looks reasonable
```

### Gate 4: Safety (Manual)
- Feature flag defaults OFF
- Kill switch exists for risky features
- No secrets in code
- No breaking schema changes without migration

---

## Failure Modes

### Scenario: Agent Blocked
**Cause:** Unclear interface, missing dependency  
**Response:**
1. Agent asks Brain for clarification
2. Brain provides decision in 2 minutes or less
3. If requires architecture change → abort sprint, replan

### Scenario: Merge Conflict
**Cause:** Two agents touched same file  
**Response:**
1. Brain checks out both versions
2. Applies priority rules (Data > Backend > Frontend > Infra)
3. Fixes in main session
4. Re-runs Gate 1-2

### Scenario: Test Failure
**Cause:** Logic error, interface mismatch  
**Response:**
- If >20% failure → abort, fix in main session
- If <20% failure → document, commit, fix post-deploy

---

## Metrics to Track

For every parallel sprint, record:

| Metric | Target | S20 Actual |
|--------|--------|------------|
| Sequential estimate | - | 60-90 min |
| Parallel actual | <25 min | 15 min |
| Speedup | 3x+ | 4-6x |
| Test pass rate | >90% | 96% |
| Merge conflicts | <3 | 0 |
| Post-deploy bugs (7d) | <5 | TBD |

---

## Pre-Flight Checklist

Before initiating PSP:

- [ ] Sprint spec has clear component boundaries
- [ ] Interfaces are documented
- [ ] File ownership assigned (no overlaps)
- [ ] Database schema is stable
- [ ] Feature flag name decided
- [ ] Test strategy defined
- [ ] Rollback plan documented

---

## Post-Flight Checklist

After PSP completes:

- [ ] All Hands agents confirmed complete
- [ ] Brain merged successfully
- [ ] Gates 1-4 passed
- [ ] Deployed to production
- [ ] Feature flags OFF
- [ ] Metrics recorded
- [ ] Retrospective notes added to this doc

---

## Canon Addendum

### S20 Proven Effective
- 4 agents, 15 minutes, 96% tests, 0 conflicts
- Used for: Notifications + Protocol Observers

### When to Use PSP
- ✅ 3+ distinct components
- ✅ Clear interfaces possible
- ✅ Greenfield development
- ✅ Deadline pressure

### When to Avoid PSP
- ❌ Tight coupling unavoidable
- ❌ Architecture undecided
- ❌ Single-component feature
- ❌ Production incident (use Brain only)

---

## Command Reference

### Spawn Single Agent
```python
sessions_spawn({
    "task": "Detailed task description\n- File: path/to/file.py\n- Interface: expects X, produces Y\n- Do not touch: other/file.py",
    "agentId": "main",
    "runTimeoutSeconds": 600
})
```

### Monitor Progress
```python
sessions_list({"limit": 10})
sessions_history({"sessionKey": "...", "limit": 5})
```

### Emergency Abort
```python
process({"action": "kill", "sessionId": "..."})
```

---

**This protocol is canon.**

Use it for S22 Monte Carlo and all future sprints meeting criteria. Document deviations and their outcomes. Iterate protocol based on data.

---

*Canonized: 2026-02-14*  
*Proven: S20 (Notifications)*  
*Next: S22 (Monte Carlo)*
