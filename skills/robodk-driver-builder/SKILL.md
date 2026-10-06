---
name: robodk-driver-builder
description: Write, port, or debug a RoboDK robot driver — the standalone console program (Python script or compiled executable) that lets RoboDK move a real robot live over its own stdin/stdout protocol ("Online Programming"), as opposed to a post processor generating an offline program file. Use when asked to "write/add a driver for <robot>", "port this driver to another language", "the robot driver doesn't respond to <command>", "support live/online programming for a new robot", or when handed an existing driver file to fix or extend. Distinct from robodk-real-robot-control, which operates an already-working driver against real hardware under a strict confirmation protocol — this skill authors or modifies the driver program itself and does not require that protocol unless testing actually reaches real hardware.
version: 1.0.0
author: RoboDK
license: MIT
platforms: [linux, windows, macos]
metadata:
  tags: [robodk, robot-drivers, online-programming, real-robot, controller-code]
  category: software-development
  related_skills: [robodk-real-robot-control]
---

# RoboDK Driver Builder

A robot driver is the piece that makes "Online Programming" possible: RoboDK launches it as a
child process and drives it over stdin/stdout using a small, fixed text protocol, and the driver
translates that into whatever the real robot controller actually speaks. This skill is about
**writing, porting, or debugging that program** — not about operating one against real hardware
(that's `robodk-real-robot-control`, with its own mandatory confirmation protocol) and not about
generating an offline program file (that's a post processor — `robodk-post-processor-builder`).

Full protocol reference, verified against four real shipped drivers in different
languages/styles (a Python SDK wrapper, a hand-rolled Python socket protocol, a compiled C++/Qt
driver, and a Python driver forwarding to the controller's own native command protocol):
**`references/driver-protocol.md`**. Read it before writing or auditing a driver — the
command/response line formats and the two-loop architecture are where correctness (and
therefore safety, once this runs against real hardware) actually lives.

## When to use this vs. the neighboring skills

- **This skill**: authoring a new driver, porting an existing one to another language, adding a
  command a driver doesn't yet handle, fixing a driver that misbehaves against RoboDK or against
  the standalone console test.
- **`robodk-real-robot-control`**: the driver already exists and works — now someone wants to actually
  move the real robot with it. That skill's confirmation protocol applies from that point on,
  including if this skill's own work reaches the "let's try it against the real robot" stage.
- **`robodk-post-processor-builder`**: the ask is about generating a program file for offline
  transfer to the controller, not live/online motion.

If a driver-writing session naturally progresses to testing against real hardware, stop and
switch to `robodk-real-robot-control`'s protocol before any motion command reaches an actual robot —
don't fold that safety gate into this skill's own workflow.

## The protocol, in brief

RoboDK writes command lines to the driver's stdin (`CONNECT`, `DISCONNECT`, `STOP`, `QUIT`,
`CJNT`, `MOVJ`, `MOVL`, `MOVC`, `SPEED`, `SETROUNDING`, `SETTOOL`, `SETDO`, `WAITDI`, `RUNPROG`,
`SENDPROG`, `POPUP`); the driver writes prefixed status/result lines to stdout (`SMS:`, `SMS2:`,
`DBG:`, `RE:`, `JNTS`, `JNTS_MOVING`, `CMDLIST:`). Full argument shapes and semantics for every
one of these: `references/driver-protocol.md`.

One command is **deliberately not on that list and not in `assets/driver_template.py`**:
`MOVLSEARCH` (touch/contact search moves, behind the API's `SearchL()`). It needs a physical
probe wired to a digital input and per-driver setup — add it only if the user explicitly asks for
touch-probing/search-move support, never by default. Full semantics if asked:
`references/driver-protocol.md`'s `MOVLSEARCH` section.

**The one architectural rule that matters most:** reading the next line from stdin and executing
the current command must not be the same blocking loop, so `STOP`/`DISCONNECT`/`QUIT` are handled
immediately instead of waiting behind a long-running motion call. Three of the four reference
drivers — in Python with threads, and in C++ with Qt threads/signals — implement this same
producer/consumer split; the fourth (Dobot V4) doesn't, and is documented as the cautionary
counter-example it is (`references/driver-protocol.md`'s Architecture section), not a pattern to
follow. A driver that blocks its stdin reader on the current motion command cannot be stopped
mid-move from RoboDK, which is not an acceptable property for anything that can move a real robot.

## Naming convention

Name the finished driver file (or compiled executable) **`Driver<BrandName>`** — e.g.
`DriverMecademic.py`, `DriverKukaIiwa.py`, `DriverKeba`. This applies to new drivers written from
this skill; the older shipped reference drivers this skill is grounded in predate the convention
and are named `api<brand>.py` — don't copy that naming pattern, just read their implementation.

## Writing a new driver

1. **Get the real protocol/SDK documentation before writing code**, the same principle as post
   processors: ask for the robot controller's remote-control/socket API manual, or confirm a
   vendor Python SDK exists and get its docs. Guessing message formats or SDK method names
   produces a driver that looks plausible and fails against real hardware.
2. **Start from `assets/driver_template.py`.** It's a runnable skeleton implementing the full
   stdin-reader/worker-thread split, the standard command set stubbed with `# TODO` markers at
   exactly the points that are robot-specific, and the `SMS:`/`JNTS` response helpers already
   wired up correctly. Copy it, rename to `Driver<BrandName>.py`, and fill in the `Robot` class.
3. **Pick wrapping-an-SDK vs. hand-rolling-a-socket-protocol deliberately** — see
   `references/driver-protocol.md`'s "Two ways to talk to the actual robot." Prefer an official
   SDK when one exists; it's dramatically less code and less to get wrong.
4. **Implement `stop()` and disconnect-on-exit first, not last.** These are the safety-critical
   paths, and the template's queue-clearing behavior on `STOP`/`DISCONNECT`/`QUIT` only works if
   your `Robot.stop()`/`Robot.disconnect()` actually return promptly and actually halt motion —
   don't leave them as the last thing you get around to filling in.
5. **Test standalone before RoboDK ever sees the file — with `scripts/drive_driver.py`.**

   ```bash
   python scripts/drive_driver.py assets/driver_template.py        --cmd "CONNECT 127.0.0.1 1234" --cmd CJNT        --cmd "MOVJ 0 -20 40 0 60 0  465 0 365 0 0 0" --cmd QUIT
   ```

   It paces commands and reads replies with a timeout, then reports the exit code. **Do not just
   pipe commands in** (`echo ... | python driver.py`): because of the reader/worker split below,
   a pipe reaches EOF and the process can exit before the worker drains its queue, so the driver
   looks completely mute. Verified against the bundled template — piped input produced no reply
   to `CJNT` or `MOVJ` at all, while the same commands paced 0.3 s apart returned
   `SMS:Working...`, `JNTS 0.000000 ...`, `SMS:Ready` and exited 0. A "silent" driver is far more
   often this race than a protocol bug.

   If the harness reports `driver did not exit after QUIT`, that is the reader/worker rule below
   being broken — the stdin reader is blocked on the current motion instead of staying responsive.

   To drive it by hand instead, run it directly and type commands
   interactively (`CONNECT <ip>`, `CJNT`, a small `MOVJ`) — see `references/driver-protocol.md`'s
   testing section for the exact interactive pattern. A driver that hasn't round-tripped a
   `CONNECT`/`CJNT`/`MOVJ`/`STOP` sequence by hand has no business being linked to a robot in
   RoboDK yet.
6. **Link it and verify from RoboDK's side**: right-click the robot → Connect to robot… → More
   options… → set the driver path. Confirm RoboDK shows the same `Ready`/`Working...` states you
   saw in standalone testing before considering the driver done.

## Porting an existing driver to another language

The protocol and the two-loop architecture are language-independent by design — porting is
mechanical for the RoboDK-facing half and robot-specific for the other half:

1. Keep the stdin/stdout line protocol byte-for-byte identical — RoboDK doesn't know or care what
   language wrote it.
2. Re-implement the producer/consumer split using the target language's own concurrency
   primitive (a thread + queue, an async task + queue, a signal/slot pair — see
   `references/driver-protocol.md`'s KEBA C++/Qt example for what this looks like outside Python).
3. Re-implement the `Robot`-equivalent class against whatever SDK/socket protocol is available in
   the target language — this is genuinely new work, not a mechanical translation, if the source
   driver wrapped a language-specific SDK with no equivalent on the target platform.
4. Re-run the standalone interactive test from scratch against the ported driver. Don't assume
   the port is correct because it compiles/runs without crashing.

## Debugging an existing driver

1. **Reproduce standalone first.** Run the driver directly and replay the exact command sequence
   RoboDK sent (visible in RoboDK's connection log) by typing it interactively. If it fails the
   same way standalone, you don't need RoboDK in the loop to keep debugging.
2. **Check the response protocol, not just the robot-side behavior.** A driver that correctly
   moves the robot but never sends the matching `SMS:Ready` (or sends it before the move actually
   finished) will desync RoboDK's understanding of robot state — this class of bug looks like
   "the robot did the right thing but RoboDK reported it wrong."
3. **Check for the queued-vs-immediate mistake.** If `STOP` doesn't actually stop a move in
   progress, the most likely cause is that it got appended to the same command queue as motion
   commands instead of being intercepted in the stdin-reading loop — see the Architecture section
   of `references/driver-protocol.md`.
4. **Check argument-count guards.** A crash on a specific command is often a missing `nvalues`/
   `nwords` check before indexing into a short or malformed line.

## Common pitfalls

- **Blocking the stdin reader on a motion call.** The single most important thing to get right —
  see Architecture above. If in doubt, re-read how the Mecademic/KUKA IIWA/KEBA reference drivers
  split this and match the pattern rather than inventing a different one. The Dobot V4 reference
  driver does *not* split it — that's a real, documented counter-example of the failure mode, not
  a second valid pattern to pick from.
- **Forgetting `SETAO`.** It's easy to implement `SETDO` and stop there since digital outputs
  come up far more often in examples — `SETAO` (analog output) is an equally real, equally
  documented command with the same argument shape.
- **Reconnecting without disconnecting first.** Several vendor SDKs/sockets leave stale state if
  `Connect` is called again without a prior `Disconnect` — always disconnect first inside your
  connect handler, unconditionally.
- **Assuming real-time joint feedback (`JNTS_MOVING`) is always available.** It depends on what
  the specific controller can report while moving. If it can't, don't fake it — just don't send
  `JNTS_MOVING` lines, and report the final `JNTS` when the move completes.
- **Ignoring units.** RoboDK always sends its own native units (mm, deg, mm/s, deg/s, mm/s²,
  deg/s², ms) regardless of what the target controller expects — a controller that wants speed as
  a percentage of a rated maximum needs that conversion done explicitly in the handler, with the
  maximum as a named constant, not a magic number.
- **Trusting a `Connect()` failure to mean the driver is broken.** Most controllers need a
  manufacturer-sold option enabled before socket communication works at all — rule that out (see
  `references/driver-protocol.md`) before assuming the driver code is at fault.
- **Skipping the interactive standalone test.** Every reference driver documents this pattern in
  its own header comment for a reason — it's dramatically faster to iterate on than round-tripping
  through RoboDK's UI for every change, and it's the only way to test before any real hardware
  (or the confirmation protocol that governs it) needs to be involved at all.
- **Adding `MOVLSEARCH` (touch/contact search) support unprompted.** It's the one command that's
  intentionally excluded from the default set — see "The protocol, in brief" above. Only add it
  on an explicit request, and only after confirming the robot actually has a probe/sensor wired
  to a digital input.

## Bundled files

- `references/driver-protocol.md` — the full stdin/stdout command and response protocol, the
  two-loop architecture pattern (with real examples in Python and C++/Qt), naming convention,
  vendor prerequisites, and the standalone testing pattern.
- `assets/driver_template.py` — runnable driver skeleton: stdin-reader/worker-thread split, the
  standard command set stubbed with `# TODO` markers, correct response-protocol helpers.
