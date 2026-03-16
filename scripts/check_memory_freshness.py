#!/usr/bin/env python3
from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
TODAY = date.today()

MARKDOWN_FILES = [
    Path("CONTEXT.md"),
    Path("docs/ops/CURRENT_EXECUTION_STATE.md"),
    Path("docs/ops/ACTIVE_WAKEUP_TARGET.md"),
    Path("docs/ops/FRONTEND_DEV_BOOTSTRAP.md"),
    Path("docs/ops/FRONTEND_DEV_BUILD_TRACKER.md"),
    Path("docs/ops/FRONTEND_DEV_CONTEXT_LOG.md"),
]
YAML_FILES = [
    Path("docs/ops/ACTIVE_WORKING_MEMORY_HANDOFF.yaml"),
]


@dataclass
class Surface:
    path: Path
    last_updated: str
    active_stream: str
    canonical_blocker: str
    canonical_next_move: str
    freshness_cadence: str
    stale: bool


def parse_markdown(path: Path) -> Surface:
    text = path.read_text()
    last_updated = normalize_last_updated(capture(text, r"(?mi)^\*\*Last Updated:\*\*\s*(.+)$|^(?i:Last updated):\s*(.+)$"))
    active_stream = capture(text, r"(?m)^- Active stream:\s*`?(.+?)`?\s*$")
    canonical_blocker = capture(text, r"(?m)^- Canonical blocker:\s*`?(.+?)`?\s*$")
    canonical_next_move = capture(text, r"(?m)^- Canonical next move:\s*`?(.+?)`?\s*$")
    freshness_cadence = capture(text, r"(?m)^- Freshness cadence:\s*`?(.+?)`?\s*$")
    stale = is_stale_date(last_updated)
    return Surface(path, last_updated, active_stream, canonical_blocker, canonical_next_move, freshness_cadence, stale)


def parse_yaml(path: Path) -> Surface:
    text = path.read_text()
    last_updated = capture(text, r"(?m)^last_verified_at:\s*(.+)$")
    active_stream = capture(text, r"(?m)^active_stream:\s*(.+)$")
    canonical_blocker = strip_quotes(capture(text, r"(?m)^canonical_blocker:\s*(.+)$"))
    canonical_next_move = strip_quotes(capture(text, r"(?m)^canonical_next_move:\s*(.+)$"))
    ttl_hours = capture(text, r"(?m)^freshness_ttl_hours:\s*(.+)$")
    freshness_cadence = f"Re-verify within {ttl_hours} hours while active"
    stale = is_stale_timestamp(last_updated, int(ttl_hours))
    return Surface(path, last_updated, active_stream, canonical_blocker, canonical_next_move, freshness_cadence, stale)


def capture(text: str, pattern: str) -> str:
    match = re.search(pattern, text)
    if not match:
        raise ValueError(f"Missing required field matching: {pattern}")
    for group in match.groups():
        if group is not None:
            return group.strip()
    return match.group(0).strip()


def strip_quotes(value: str) -> str:
    return value.strip().strip('"').strip("'")


def normalize_last_updated(raw: str) -> str:
    return raw.replace("*", "").strip()


def is_stale_date(raw: str) -> bool:
    parsed = datetime.strptime(raw, "%Y-%m-%d").date()
    return (TODAY - parsed).days > 1


def is_stale_timestamp(raw: str, ttl_hours: int) -> bool:
    stamp = datetime.fromisoformat(raw)
    if stamp.tzinfo is None:
        stamp = stamp.replace(tzinfo=timezone.utc)
    now = datetime.now(stamp.tzinfo)
    age_hours = (now - stamp).total_seconds() / 3600
    return age_hours > ttl_hours


def summarize(surfaces: list[Surface]) -> int:
    failed = False
    streams = {surface.active_stream for surface in surfaces}
    blockers = {surface.canonical_blocker for surface in surfaces}
    next_moves = {surface.canonical_next_move for surface in surfaces}

    print("Memory freshness report")
    print(f"Root: {ROOT}")
    print("")

    for surface in surfaces:
        status = "STALE" if surface.stale else "OK"
        print(f"[{status}] {surface.path}")
        print(f"  updated: {surface.last_updated}")
        print(f"  stream: {surface.active_stream}")
        print(f"  blocker: {surface.canonical_blocker}")
        print(f"  next: {surface.canonical_next_move}")
        print(f"  cadence: {surface.freshness_cadence}")
        if surface.stale:
            failed = True

    if len(streams) > 1:
        failed = True
        print("")
        print("Mismatch: active stream differs across memory surfaces.")
    if len(blockers) > 1:
        failed = True
        print("")
        print("Mismatch: canonical blocker differs across memory surfaces.")
    if len(next_moves) > 1:
        failed = True
        print("")
        print("Mismatch: canonical next move differs across memory surfaces.")

    print("")
    print("Result:", "FAIL" if failed else "PASS")
    return 1 if failed else 0


def main() -> int:
    try:
        surfaces = [parse_markdown(ROOT / path) for path in MARKDOWN_FILES]
        surfaces.extend(parse_yaml(ROOT / path) for path in YAML_FILES)
    except Exception as exc:  # pragma: no cover - operator-facing script
        print(f"Memory freshness check failed: {exc}", file=sys.stderr)
        return 2
    return summarize(surfaces)


if __name__ == "__main__":
    raise SystemExit(main())
