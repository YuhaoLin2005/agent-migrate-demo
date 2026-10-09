# -*- coding: utf-8 -*-
r"""gate_inventory.py -- "N gates registered" is not a number you can reconcile.

Reporting rule: never report how many gates are *registered* without also
reporting how many of them pass compile(). Registered is a claim; runnable is
a different axis.

This script demonstrates the trap directly: it counts the gates, reports how
many compile, and then runs each one -- to show that compiling and running are
unrelated facts.
"""
import glob
import os
import subprocess
import sys

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

HERE = os.path.dirname(os.path.abspath(__file__))
PY = sys.executable


def compiles(path):
    """compile() -- one step further than ast.parse, still not the last step.

    ast.parse builds an AST but checks no symbol table and no scope: a wrong
    `global` position or a duplicated parameter name slips straight through.
    compile() catches those. Neither checks whether a name exists at runtime --
    which is why route_gate.before.py passes here and still cannot run.
    """
    src = open(path, "rb").read().decode("utf-8", errors="replace")
    try:
        compile(src, path, "exec")
        return True, ""
    except Exception as e:
        return False, f"{type(e).__name__}: {e}"


def main():
    me = os.path.basename(__file__)
    gates = sorted(g for g in glob.glob(os.path.join(HERE, "*.py"))
                   if os.path.basename(g) != me)

    declared, runnable = [], []
    for g in gates:
        declared.append(g)
        if compiles(g)[0]:
            runnable.append(g)

    print("=" * 66)
    print("gate_inventory -- registered vs runnable")
    print("=" * 66)

    for g in gates:
        ok, err = compiles(g)
        # encoding= matters on Windows: text=True alone decodes with the locale
        # codec (gbk here) and dies on UTF-8 gate output.
        r = subprocess.run([PY, g], capture_output=True,
                           encoding="utf-8", errors="replace")
        lines = (r.stdout + r.stderr).strip().splitlines()
        last = lines[-1] if lines else "(no output)"
        print(f"  {os.path.basename(g)}")
        print(f"      compile : {'OK' if ok else 'FAIL ' + err}")
        print(f"      run     : rc={r.returncode}  {last[:88]}")

    print("-" * 66)
    print(f"registered {len(declared)} / compile-ok {len(runnable)} "
          f"-- two different numbers, both must be reported.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
