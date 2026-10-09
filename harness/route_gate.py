# -*- coding: utf-8 -*-
r"""route_gate.py — minimal, self-contained reproduction of the "green gate" failure.

Three checks:

  (1) ROUTE_PATH_MISSING      every path referenced by the route table must exist on disk
  (2) RESIDENT_NO_PROVENANCE  every resident entry must carry a provenance mark
  (3) NONVACUOUS_SECTION      the section parser must actually have parsed something

Exit codes:  0 = green | 2 = red | 3 = PROBE_FAULT (the gate itself is broken)

Note on runnability: this file *compiles* either way. Delete the two constants
marked below and it still passes `compile(src, path, "exec")` — it just dies at
runtime with a NameError. See route_gate.before.py for that state.
"""
import os
import re
import sys

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
TARGET = os.path.join(ROOT, "memory", "MEMORY.md")

ARCH = os.path.join(ROOT, "arch")                     # archive root (the default)
PROVENANCE_MARKS = ("=>", "source", "provenance")


# ---------------------------------------------------------------------------
# These two constants are what the original file was missing. Remove them and
# the gate dies with `NameError: name 'AGENT_MEM' is not defined` — a *runtime*
# fault that compile() structurally cannot see.
# ---------------------------------------------------------------------------
AGENT_MEM = os.path.join(ROOT, "memory")              # memory root
MEMORY_ROOT = ROOT                                    # repo root (runtime layer)


def resolve(p):
    """Resolve one referenced path. Absolute -> as-is. Relative -> try each root."""
    rel = p.replace("/", os.sep)
    candidates = [
        os.path.join(ARCH, rel),                       # archive root
        os.path.join(AGENT_MEM, rel),                  # memory root
        os.path.join(MEMORY_ROOT, rel),                # repo root
        os.path.join(AGENT_MEM, "cases", os.path.basename(rel))
        if rel.startswith("cases" + os.sep) else None,
    ]
    for c in candidates:
        if c and os.path.isfile(c):
            return c
    return os.path.join(ARCH, rel)                     # report the default-root guess


def route_paths(text):
    """Column 2 of every row in the route table."""
    return re.findall(r"^\|[^|]+\|\s*`([^`]+)`\s*\|", text, re.M)


def resident_blocks(text):
    """Resident entries are `### <n> · ...` headings."""
    return re.findall(r"^###\s*\d+\s*·.*$", text, re.M)


def main():
    if not os.path.isfile(TARGET):
        print(f"PROBE_FAULT rc=3 — target not found: {TARGET}")
        return 3

    with open(TARGET, "r", encoding="utf-8") as fh:
        text = fh.read()

    paths = route_paths(text)
    blocks = resident_blocks(text)

    print("=" * 66)
    print("route_gate — is the route layer actually wired?")
    print("=" * 66)
    print(f"target  : {TARGET}")
    print(f"routes  : {len(paths)} declared")
    print(f"resident: {len(blocks)} blocks parsed")
    print("-" * 66)

    fails = []
    for p in paths:
        if not os.path.isfile(resolve(p)):
            fails.append(("ROUTE_PATH_MISSING", f"{p} -> {resolve(p)}"))

    for b in blocks:
        if not any(m in b for m in PROVENANCE_MARKS):
            fails.append(("RESIDENT_NO_PROVENANCE", b))

    # (3) fail closed: if the parser found nothing, checks (1) and (2) were
    #     evaluated over an empty set and this gate has no discriminating power.
    if not blocks:
        fails.append(
            ("NONVACUOUS_SECTION",
             f"parser returned an empty set (routes={len(paths)}, resident=0) "
             f"=> checks (1)(2) ran over nothing; this gate cannot discriminate")
        )

    for name, detail in fails:
        print(f"  [FAIL] {name} :: {detail}")

    if fails:
        print("-" * 66)
        print(f"verdict: RED  rc=2  ({len(fails)} failure(s))")
        return 2

    print("verdict: GREEN  rc=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
