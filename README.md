# agent-migrate-demo

A runnable reproduction of a failure mode I hit during a real Agent migration —
the one where **every self-check gate looks wired, and none of them can run.**

Clone it, run four commands, watch it move through three different exit codes.

```bash
python harness/route_gate.before.py   # rc=3  it cannot run at all
python harness/route_gate.py          # rc=2  runs, reports RED
python harness/route_gate.fixed.py    # rc=0  runs, reports GREEN
python harness/gate_inventory.py      # the summary that matters
```

---

## Quick start

```bash
git clone https://github.com/YuhaoLin2005/agent-migrate-demo
cd agent-migrate-demo
python harness/gate_inventory.py
```

No dependencies. Python 3.8+. No network.

---

## What actually came out

*(Verbatim output, with two disclosed edits: the absolute path prefix of this
checkout is shortened to `<repo>`, and the `$ …` prompt lines and trailing
`rc=N` lines are added — the scripts print neither of those themselves.)*

### 1 · It does not run

```
$ python harness/route_gate.before.py
PROBE_FAULT rc=3 -- NameError: name 'AGENT_MEM' is not defined
rc=3
```

Fix `AGENT_MEM` — the obvious fix — and you land on the next name. This state
has no file of its own; delete `MEMORY_ROOT = ROOT` from `route_gate.py` to
produce it:

```
$ python harness/route_gate.py   # after defining AGENT_MEM only
PROBE_FAULT rc=3 -- NameError: name 'MEMORY_ROOT' is not defined
rc=3
```

### 2 · It runs, and reports RED

Define **both** constants:

```
==================================================================
route_gate — is the route layer actually wired?
==================================================================
target  : <repo>/memory/MEMORY.md
routes  : 3 declared
resident: 0 blocks parsed
------------------------------------------------------------------
  [FAIL] ROUTE_PATH_MISSING :: cases.md -> <repo>/arch/cases.md
  [FAIL] NONVACUOUS_SECTION :: parser returned an empty set (routes=3, resident=0) => checks (1)(2) ran over nothing; this gate cannot discriminate
------------------------------------------------------------------
verdict: RED  rc=2  (2 failure(s))
```

### 3 · After the full fix, GREEN

```
$ python harness/route_gate.fixed.py
==================================================================
route_gate (fixed) -- is the route layer actually wired?
==================================================================
target  : memory\MEMORY.fixed.md
routes  : 3 declared
resident: 2 blocks parsed
------------------------------------------------------------------
verdict: GREEN  rc=0
```

### 4 · The summary

```
$ python harness/gate_inventory.py
==================================================================
gate_inventory -- registered vs runnable
==================================================================
  route_gate.before.py
      compile : OK
      run     : rc=3  PROBE_FAULT rc=3 -- NameError: name 'AGENT_MEM' is not defined
  route_gate.fixed.py
      compile : OK
      run     : rc=0  verdict: GREEN  rc=0
  route_gate.py
      compile : OK
      run     : rc=2  verdict: RED  rc=2  (2 failure(s))
------------------------------------------------------------------
registered 3 / compile-ok 3 -- two different numbers, both must be reported.
```

Three files. All three compile. Three different exit codes.

---

## The three layers

**Layer 1 — it does not run, and `compile()` says it does.**

`route_gate.before.py` passes `compile(src, path, "exec")` cleanly. A dangling
name is a *runtime* fault: no parser can see it. If your "can this gate run?"
check is `compile()` or `ast.parse`, it will tell you this file is fine. It
isn't.

**Layer 2 — the fix you think is the fix is only half of it.**

`AGENT_MEM` fails first because it comes first in the candidate list. Fix it and
you hit `MEMORY_ROOT` on the next line. The error message names one problem; the
file has two. Anything that reports the first failure as "the" failure will send
you round the loop twice.

**Layer 3 — once it runs, it reports something you didn't expect.**

`cases.md` is reported missing. It isn't missing — it's at
`memory/cases/cases.md`, and the resolver's fourth candidate root only applies
when the reference is written with a `cases/` prefix.

And the resident parser finds **0 blocks** in a file that plainly has two, so the
gate fails closed on itself (`NONVACUOUS_SECTION`): it refuses to claim green on
checks it evaluated over an empty set.

That last one is the useful part. A gate that has silently stopped
discriminating is more dangerous than no gate, because it still prints a verdict.

---

## After the three layers: going green took five changes

Three in code, two in data, and all five were necessary:

| # | What was wrong | Where | Kind |
|---|---|---|---|
| 1 | two constants referenced but never defined | `harness/route_gate.py` | code |
| 2 | resident parser expected `### N ·`; the target writes `## <section>` + `1. item` | `harness/route_gate.fixed.py` | code |
| 3 | provenance marks were ASCII (`=>`); the target writes `⇒` | `harness/route_gate.fixed.py` | code |
| 4 | `cases.md` never existed at that path; it is `cases/cases.md` | `memory/MEMORY.fixed.md` | data |
| 5 | `report-v1.md` was declared in the route table but never created | `projects/report-v1.md` | data |

Fixes 2 and 3 are the interesting ones: **the gate and its target had drifted
apart, and nothing was watching for that drift.** The gate reported 0 blocks and
moved on. That is precisely why check 3 has to fail closed.

---

## Why the migration "finished" and the system still didn't work

The migration had already run. Files were on disk, byte counts were sane,
markdown rendered, the per-turn context injection "succeeded" every time.

None of that touches any of the five defects above. **Copying is not wiring.**
The gate existed; nothing had ever executed it; and nothing was watching for
the case where nobody had.

---

## Layout

```
agent-migrate-demo/
├── harness/
│   ├── route_gate.before.py    # compiles, cannot run                 (rc=3)
│   ├── route_gate.py           # runs, RED                            (rc=2)
│   ├── route_gate.fixed.py     # runs, GREEN                          (rc=0)
│   └── gate_inventory.py       # registered vs runnable
├── memory/
│   ├── MEMORY.md               # the target, with its real defects
│   ├── MEMORY.fixed.md         # the same target, data defects corrected
│   ├── identity.md
│   ├── voice.md
│   ├── grades.md
│   └── cases/cases.md          # the file the gate says is missing
└── projects/
    └── report-v1.md            # declared by the route table; created as part of the fix
```

---

## Scope and limitations

- This is a **reconstruction**, not the original file. The original ran against
  private data and is not public; this repo rebuilds the smallest thing that
  reproduces the same failure layers, and every output above is from *this*
  repo, not from the original system.
- The gate is deliberately narrow: path existence, provenance marks, and a
  fail-closed self-check. It is a demonstration, not a framework.
- "GREEN" here means *this* gate passes on *this* sample. It is not a claim that
  the underlying system is correct — `route_gate.fixed.py` still uses a
  multi-root guessing resolver, which is itself the design smell that produced
  defect 4.

## License

MIT
