# Verifying a post processor

You cannot compile a controller program locally, so verification rests on two things:
regenerating real output and diffing it against something known good, and reading the
generated lines against the controller's grammar. Do both.

## 1. Replay a real intermediate file (strongest signal)

RoboDK leaves a `PostProg<Name>.py` next to the generated program. It is ordinary runnable
Python that calls your post exactly the way RoboDK does — same call order, same argument
shapes, same `None`s. Replaying it exercises far more of the post than any hand-written test.

```bash
python scripts/replay_intermediate.py PostProg2.py --post Siasun.py --out ./out --expect Prog2.spf
```

What the script does: copies the post to a temp directory, rewrites the intermediate file's
`sys.path` line, its `from <Post> import *`, and its final `ProgSave(...)` call so output
lands in `--out` without opening a dialog or an editor, runs it, prints the generated
program, and unified-diffs it against `--expect`.

Use it as a regression test around every edit:

1. Run it **before** changing anything, with `--expect` pointing at the user's known-good
   controller program. A clean diff confirms the harness reproduces reality; a dirty diff
   means the reference is stale or the post already changed — resolve that before editing,
   or you'll misattribute the difference to your own work.
2. Make the change.
3. Run it again. Every line in the diff should be a change you intended. Anything else is a
   regression.

Requires the `robodk` package. If import fails the script reports it rather than producing
an empty result.

**Finding an interpreter.** A RoboDK install ships one with `robodk` already present, so
don't install anything before checking for it — on Windows it is normally
`C:\RoboDK\Python-Embedded\python.exe`. A bare `python` on PATH usually won't have `robodk`.

## 2. `test_post()`

Most posts end with a `test_post()` that builds a small program and prints it:

```bash
python Siasun.py
```

This needs no RoboDK station, so it is the fastest loop while drafting a new post — but it
only covers the instructions the test function happens to call. When you add or change an
instruction, add a line to `test_post()` exercising it, including the awkward cases:

- a `MoveL`/`MoveC` with `pose=None` (joint target on a linear move)
- `Pause` with a negative value
- `setDO` with a string I/O name
- `waitDI` with and without a timeout
- `setZoneData(-1)` for exact positioning
- `RunCode` both as raw code and as a function call with arguments
- a second `ProgStart`/`ProgFinish` pair, so subprogram handling is covered
- more joint values than `nAxes`, if external axes are in scope

A post that survives all of those without a traceback is unlikely to crash mid-generation on
a real station, which is the failure users hate most.

## 3. Read the generated program

Automation won't catch a syntactically valid program that means the wrong thing. Check by
eye:

- **First motion of each program.** Speed, acceleration and zone come from class defaults
  until RoboDK calls a setter. Are those defaults values the controller accepts?
- **Every subprogram call resolves.** If the program calls `Path1`, did `ProgSave` write
  something that call can reach — a separate file with exactly that name, or a program
  header in the same file? Compare the call string against the header string character for
  character: a file extension, a suffix, or different name filtering on the two paths all
  produce a program that loads cleanly and fails at the call.
- **No scientific notation, no `nan`, no `inf`** anywhere in the output.
- **Frame and tool changes land before the moves that depend on them**, and the pose numbers
  change as expected when the reference frame changes.
- **Numbers are in the controller's units** — spot-check one value per unit type against the
  station rather than trusting the whole file because one line looks right.
- **Line endings and encoding** match what the controller expects.

## 4. Report honestly

State what was actually verified. "Replayed `PostProg2.py`; output matches `Prog2.spf`
except the three intended zone lines" is useful. "Should work" is not. If you could not run
anything — no `robodk` package, no intermediate file — say that plainly and list what the
user should check on the controller before running the program on real hardware.
