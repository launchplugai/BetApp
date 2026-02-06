# TRUTH × EXPERIENCE Charter Enforcement

**Authority:** Project Governance  
**Status:** Binding  
**Reference:** [`docs/TRUTH_AND_EXPERIENCE.md`](../docs/TRUTH_AND_EXPERIENCE.md)

---

## Policy

**All development work must satisfy BOTH TRUTH and EXPERIENCE criteria.**

This is not aspirational. This is not "best effort." This is a **hard requirement**.

### Charter Violations

The following are **valid grounds for PR rejection**:

#### TRUTH Violations
- Tests fail or are missing
- Code changes lack verification
- Silent failures or edge case gaps
- Frozen engine code modified without authorization
- Business logic changes without test coverage

#### EXPERIENCE Violations
- Output is misleading or confusing
- User confidence is undermined
- Error messages are cryptic or absent
- Edge cases handled poorly (unclear outcomes)
- UX introduces doubt or uncertainty

### PR Review Standards

Every PR **must**:
1. Complete the TRUTH checklist in the PR template
2. Complete the EXPERIENCE checklist in the PR template
3. Confirm charter review checkbox
4. Provide evidence of both TRUTH and EXPERIENCE impact

**Reviewers are authorized to reject PRs that:**
- Skip checklist items without justification
- Satisfy TRUTH but ignore EXPERIENCE (or vice versa)
- Show charter compliance as "optional" or "deferred"

---

## Ticket and Sprint Standards

### Tickets
Every ticket **must include**:
- **How TRUTH is Advanced** section (mandatory, not empty)
- **How EXPERIENCE is Advanced** section (mandatory, not empty)

**Tickets without both sections are incomplete and cannot be started.**

### Sprints
Every sprint **must define**:
- Sprint TRUTH Objectives
- Sprint EXPERIENCE Objectives

**Sprints that only address one dimension are invalid.**

---

## Enforcement in Code Review

### Reviewer Checklist
- [ ] PR template checklist fully completed
- [ ] TRUTH impact clear and verified (tests pass)
- [ ] EXPERIENCE impact clear and demonstrated
- [ ] Charter reference acknowledged
- [ ] No conflicting evidence (e.g., tests pass but output misleading)

### Escalation
If TRUTH and EXPERIENCE conflict:
- **STOP immediately**
- Do NOT merge
- Escalate to project lead
- Document the conflict in the PR

**Example conflict:**
> "Tests pass (TRUTH ✓) but grounding score displays as confident when correlation flags exist (EXPERIENCE ✗)."

---

## Rationale

**Why is this binding?**

The DNA Bet Engine stakes its credibility on delivering BOTH:
1. **Correct** analysis (TRUTH)
2. **Trustworthy** presentation (EXPERIENCE)

Satisfying only one dimension is insufficient. A technically correct engine that confuses users is a failure. A reassuring UX built on shaky logic is worse.

**Charter violations threaten both product integrity and user trust.**

---

## No Exceptions

There are no "TRUTH-only" or "EXPERIENCE-only" tickets.

If a task genuinely cannot advance both dimensions:
- It may not belong in this project
- It requires explicit architectural review
- It cannot bypass charter compliance

**Governance is not optional.**

---

## Summary

✅ **Charter compliance is mandatory**  
✅ **Violations justify PR rejection**  
✅ **Both TRUTH and EXPERIENCE must advance**  
✅ **Enforcement applies to all PRs, tickets, and sprints**

**Questions?** Review [`docs/TRUTH_AND_EXPERIENCE.md`](../docs/TRUTH_AND_EXPERIENCE.md) or escalate to project lead.
