# -*- coding: utf-8 -*-
r"""route_gate.before.py -- the SAME file as route_gate.py, before the fix.

The ONLY difference from route_gate.py: `AGENT_MEM` and `MEMORY_ROOT` are never
defined (both are referenced inside `resolve()`). Nothing else changed -- main()
still walks the route table and calls resolve() on every entry, which is exactly
what reaches the missing name.

This file COMPILES cleanly. `compile(src, path, "exec")` returns without error.
It still cannot run:

    $ python harness/route_gate.before.py
    PROBE_FAULT rc=3 -- NameError: name 'AGENT_MEM' is not defined

Fix AGENT_MEM and it moves one line down to `MEMORY_ROOT`. Fix both and it runs
-- and then fails for an entirely different reason. That chain is the point.
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

# --- AGENT_MEM and MEMORY_ROOT are deliberately absent here ------------------


def resolve(p):
    """Resolve one referenced path. Absolute -> as-is. Relative -> try each root."""
    rel = p.replace("/", os.sep)
    candidates = [
        os.path.join(ARCH, rel),                       # archive root
        os.path.join(AGENT_MEM, rel),                  # memory root   <- NameError #1
        os.path.join(MEMORY_ROOT, rel),                # repo root     <- NameError #2
        os.path.join(AGENT_MEM, "cases", os.path.basename(rel))
        if rel.startswith("cases" + os.sep) else None,
    ]
    for c in candidates:
        if c and os.path.isfile(c):
            return c
    return os.path.join(ARCH, rel)


def route_paths(text):
    return re.findall(r"^\|[^|]+\|\s*`([^`]+)`\s*\|", text, re.M)


def resident_blocks(text):
    return re.findall(r"^###\s*\d+\s*·.*$", text, re.M)


def main():
    """Everything below is byte-identical to route_gate.py's main()."""
    if not os.path.isfile(TARGET):
        print(f"PROBE_FAULT rc=3 -- target not found: {TARGET}")
        return 3

    with open(TARGET, "r", encoding="utf-8") as fh:
        text = fh.read()

    paths = route_paths(text)
    blocks = resident_blocks(text)

    fails = []
    for p in paths:
        if not os.path.isfile(resolve(p)):             # <- first resolve() call
            fails.append(("ROUTE_PATH_MISSING", f"{p} -> {resolve(p)}"))

    for b in blocks:
        if not any(m in b for m in ("=>", "source", "provenance")):
            fails.append(("RESIDENT_NO_PROVENANCE", b))

    if not blocks:
        fails.append(("NONVACUOUS_SECTION",
                      f"empty set (routes={len(paths)}, resident=0)"))

    for name, detail in fails:
        print(f"  [FAIL] {name} :: {detail}")
    return 2 if fails else 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except NameError as e:
        print(f"PROBE_FAULT rc=3 -- NameError: {e}")
        raise SystemExit(3)
