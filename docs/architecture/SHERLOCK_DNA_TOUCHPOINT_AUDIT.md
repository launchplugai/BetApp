# Sherlock DNA Touchpoint Audit

**Status:** CANONICAL  
**Last Updated:** 2026-03-14

This document is the Sprint C code-backed audit of how Sherlock and DNA currently interact in the BetApp runtime.

## 1. Executive Summary

Current reality:

- Sherlock exists as a library and a runtime hook
- DNA primitives exist as contracts and in-memory translated artifacts
- the active runtime does not yet use Sherlock to request structured DNA fragments for protocol reasoning
- current Tier 1 protocols are still direct runtime heuristics using pipeline/context signals

This means the architecture direction is correct, but the working boundary is only partially implemented.

## 2. Current Sherlock Touchpoints

## 2.1 Library Layer

Primary library files:

- `sherlock/engine.py`
- `sherlock/models.py`
- `sherlock/audit.py`
- `sherlock/mutation.py`

Current role:

- deterministic claim investigation
- audit gate output
- final report generation

## 2.2 Runtime Hook

Primary runtime integration:

- `app/sherlock_hook.py`

Current role:

- derive a claim from evaluation output
- run Sherlock dry-run investigation
- translate `FinalReport` into in-memory DNA primitive representations
- expose results for debug/proof/explainability

## 2.3 Pipeline Use

Current runtime pipeline behavior:

- Sherlock is feature-flagged
- core evaluation still works without Sherlock
- Sherlock does not currently drive Tier 1 protocol retrieval

## 3. Current DNA Touchpoints

## 3.1 Contract Layer

Primary contracts:

- `docs/contracts/DNA_PRIMITIVES_CONTRACT.md`
- `docs/mappings/MAP_SHERLOCK_TO_DNA.md`

Current DNA representation is strongest in:

- primitive schemas
- translation rules from Sherlock reports
- explainability/proof summaries

## 3.2 Runtime Use

Current runtime uses DNA most strongly through:

- `core.evaluation` from `dna-matrix`
- proof summary / artifact count surfaces
- `app/sherlock_hook.py` in-memory primitive translation

Current gap:

DNA is not yet acting as an explicit fragment provider for protocol reasoning.

## 4. Protocol Touchpoints

Current Tier 1 protocol runtime:

- `app/services/dna_protocols.py`

Current data sources:

- normalized input text
- blocks
- entity extraction
- evaluation metadata
- NBA heuristic summaries
- context data

Current limitation:

protocols are still asking for data implicitly from runtime state, not explicitly from a DNA fragment adapter.

## 5. Boundary Gaps

1. Sherlock derives claims from evaluation output, but does not yet request structured DNA fragments.
2. DNA primitives are mostly translation/persistence artifacts, not a working query layer.
3. Protocols imply data requirements, but there is no shared requirement-to-fragment adapter yet.
4. Current runtime logic still blends:
   - pipeline metrics
   - protocol heuristics
   - context summaries
   without a formal DNA fragment seam.

## 6. Working Conclusion

The first practical Sherlock ↔ DNA milestone should not try to replace the existing pipeline.

It should:

- define structured data requirements for one real protocol slice
- define a DNA fragment adapter that can satisfy those requirements from current runtime/context state
- leave the current scoring engine intact

## 7. First Recommended Vertical Slice

Recommended first slice:

- NBA player/team context for fatigue, injury, and pace-sensitive protocol reasoning

Why:

- Tier 1 protocols already use this data
- existing runtime context and heuristics already expose part of it
- this slice is small enough to formalize without rewriting the app

## 8. Related Files

- `app/sherlock_hook.py`
- `app/services/dna_protocols.py`
- `app/pipeline.py`
- `docs/contracts/SYSTEM_CONTRACT_SDS.md`
- `docs/contracts/DNA_PRIMITIVES_CONTRACT.md`
- `docs/contracts/SHERLOCK_DNA_INTERACTION_CONTRACT.md`
