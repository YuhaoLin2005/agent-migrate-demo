# -*- coding: utf-8 -*-
r"""route_gate.fixed.py — the same gate, after the full fix. Ends GREEN.

Getting here took three code/data changes on top of the two constants:

  1. the two dangling constants             (code)  -> see route_gate.py
  2. the resident parser expected `### N ·` while the target writes
     `## <section>` + `1. item`             (code)  -> fixed here
  3. the provenance marks were ASCII-only (`=>`) while the target writes
     `⇒`                                    (code)  -> fixed here
  4. two route entries were simply wrong    (data)  -> see memory/MEMORY.fixed.md
       * `cases.md`        never existed at that path; it is `cases/cases.md`
       * `report-v1.md`    was declared but never created

Points 2 and 3 are the interesting ones: the gate and its target had drifted
apart, and **nothing was watching for that drift**. The gate just reported
0 blocks and moved on — which is exactly why check (3), NONVACUOUS_SECTION,
has to fail closed.

Reads memory/MEMORY.fixed.md by default. Pass --target to point elsewhere.
"""
import argparse
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
DEFAULT_TARGET = os.path.join(ROOT, "memory", "MEMORY.fixed.md")

ARCH = os.path.join(ROOT, "arch")
AGENT_MEM = os.path.join(ROOT, "memory")
MEMORY_ROOT = ROOT

# mark (3): include the mark the target actually uses
PROVENANCE_MARKS = ("⇒", "=>", "source", "provenance")


def resolve(p):
    rel = p.replace("/", os.sep)
    candidates = [
        os.path.join(ARCH, rel),
        os.path.join(AGENT_MEM, rel),
        os.path.join(MEMORY_ROOT, rel),
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
    """mark (2): resident entries live under `## ... · resident` as `N. item`."""
    m = re.search(r"^##\s*[^\n]*resident[^\n]*$(.*?)(?=^##\s|\Z)",
                  text, re.M | re.S)
    if not m:
        return []
    return re.findall(r"^\d+\.\s.*$", m.group(1), re.M)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", default=DEFAULT_TARGET)
    args = ap.parse_args()

    if not os.path.isfile(args.target):
        print(f"PROBE_FAULT rc=3 -- target not found: {args.target}")
        return 3

    with open(args.target, "r", encoding="utf-8") as fh:
        text = fh.read()

    paths = route_paths(text)
    blocks = resident_blocks(text)

    print("=" * 66)
    print("route_gate (fixed) -- is the route layer actually wired?")
    print("=" * 66)
    print(f"target  : {os.path.relpath(args.target, ROOT)}")
    print(f"routes  : {len(paths)} declared")
    print(f"resident: {len(blocks)} blocks parsed")
    print("-" * 66)

    fails = []
    for p in paths:
        if not os.path.isfile(resolve(p)):
            fails.append(("ROUTE_PATH_MISSING", p))

    for b in blocks:
        if not any(m in b for m in PROVENANCE_MARKS):
            fails.append(("RESIDENT_NO_PROVENANCE", b[:60]))

    if not blocks:
        fails.append(("NONVACUOUS_SECTION",
                      f"empty set (routes={len(paths)}, resident=0)"))

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
