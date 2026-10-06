---
name: robodk-real-robot-control
description: The ONLY skill in this repo allowed to move a real, physical robot — via robot.Connect() and RUNMODE_RUN_ROBOT/PROGRAM_RUN_ON_ROBOT, using RoboDK's robot drivers (Online Programming). Every other RoboDK skill here is simulation-only by design; redirect here the moment a request is unambiguously about the real robot moving, not the simulated one — phrasings like "move the real robot", "run this on the actual/physical robot", "connect to the robot and jog it", "online programming", "drive the robot live". Do not use for anything that stays in simulation, for generating a program to transfer later (that's a post processor), or when real-vs-simulated intent is unclear — ask first rather than guessing.
version: 1.0.0
author: RoboDK
license: MIT
platforms: [linux, windows, macos]
metadata:
  tags: [robodk, physical-robot, real-robot, robot-drivers, online-programming, safety]
  category: software-development
  related_skills: [robodk-api, robodk-driver-builder]
---

# RoboDK Real Robot Control — moving a real robot

**This is the one place in this repo where code is allowed to move actual hardware.** Every
other RoboDK skill here (`robodk-api` and everything built on it) is
simulation-only by explicit design — their own pitfalls sections say so. If you're in one of
those skills and the user's request turns out to be about the real robot, stop and come here
instead of adding `Connect()`/`RUNMODE_RUN_ROBOT` locally.

A real robot can injure people and damage itself, its tooling, and its environment. Treat every
instruction in this skill as a safety instruction, not a formality.

## When to use this — and when not to

Use this skill **only** when the user's request is unambiguous about wanting the **physical**
robot to move, right now, from this session. Signs it applies: "move the real robot", "run this
on the actual robot", "connect to the robot and jog/move it", "online programming", "drive the
robot live", "the robot in the cell / on the floor", handing you an IP address for a controller.

Do **not** use this skill, and do not call `Connect()` / set `RUNMODE_RUN_ROBOT` /
`setRunType(PROGRAM_RUN_ON_ROBOT)` anywhere else, for:

- Anything that stays in simulation — use `robodk-api` instead.
- Generating a program for later offline transfer to a controller — that's a post processor
  (`robodk-post-processor-builder`) or an `RDK.Save()`/FTP transfer, not this.
- A request you're inferring might be about a real robot but doesn't say so explicitly. **Ask.**
  "Simulate it" and "run it" are not the same sentence as "run it on the real robot" — don't
  treat them as equivalent, and don't treat a robot's real-sounding name (e.g. "the IRB120 in the
  lab") as proof the request is about hardware rather than that robot's simulation model.

## The confirmation protocol (mandatory, every time)

This is not a one-time consent step. **Re-confirm before every individual action that can cause
real motion or hand control of the robot to this session** — a fresh "yes, move the real robot"
earlier in the conversation does not carry forward to the next motion command, even later in the
same turn.

Before calling any of `Connect()` / `ConnectSafe()`, `setRunMode(RUNMODE_RUN_ROBOT)`,
`setRunType(PROGRAM_RUN_ON_ROBOT)`, or any `MoveJ`/`MoveL`/`MoveC`/`RunProgram()` while connected
to real hardware:

1. **State plainly what is about to physically happen** — which robot, what motion (target
   pose/joints, or which program), at what speed — in terms a non-programmer bystander could
   picture. Not "I'll call MoveJ" — "I'm about to move the IRB120 to joint position
   [10,20,30,40,50,60] at 50 mm/s."
2. **Ask for explicit go-ahead for that specific action** — in Claude Code, use `AskUserQuestion`
   rather than assuming a plain "continue" from earlier in the conversation covers it; in any
   agent runtime, the equivalent is: stop and require an unambiguous yes tied to *this* action,
   not a generic earlier approval.
3. **Never batch-confirm a sequence of real moves.** "Run this whole program on the robot" is one
   confirmed action if the user said exactly that about that program; a chain of ad hoc moves you
   are constructing turn-by-turn is not — confirm each one.
4. If the user's confirmation is itself ambiguous ("yeah go" without repeating what "go" refers
   to), restate the action again and ask once more rather than proceeding on a guess.

## Pre-flight safety checklist (before the first `Connect()` of a session)

Ask the user to verify these rather than assuming them — you cannot see the physical cell:

- The workspace around the robot is clear of people and obstacles for the full range of motion
  about to be commanded.
- Someone is present who can reach the robot's **physical emergency stop** and knows to use it.
  A software `Stop()` (below) is not a substitute for this — it depends on the same session,
  network link, and driver process staying healthy.
- The robot's current position, as RoboDK shows it, actually matches reality — call
  `robot.Connect()` then compare, or use the GUI's **Get robot joints** to resync before trusting
  the simulated pose (see `robodk-driver-builder`'s `references/driver-protocol.md`).
- Speed is reduced for the first real move of a session, especially the first move to a new or
  unverified target — don't reuse simulation speeds/accelerations that were never validated on
  hardware. Ramp up only after watching a slow, confirmed-safe move succeed.

## Connecting and moving — the API mechanism

Full connect/disconnect/troubleshooting detail, the driver architecture, and the vendor
socket-option prerequisite now live in `robodk-driver-builder`'s **`references/driver-protocol.md`**
(that skill also covers writing/porting/debugging a driver itself, which is out of scope here).
For everything about `Item`/`Robolink` calls that isn't specific to real-robot motion (pose
conventions, `MoveJ`/`MoveL` argument shapes, FK/IK, station building), see `robodk-api` — don't
re-derive either here.

```python
from robodk import robolink

with robolink.Robolink() as RDK:  # never -NEWINSTANCE here — always attach to the running,
                                   # user-supervised RoboDK, never spawn/close a headless one
    robot = RDK.Item('', robolink.ITEM_TYPE_ROBOT)  # confirm this resolves to the intended robot

    success = robot.Connect()  # sets RUNMODE_RUN_ROBOT for this session automatically
    status, status_msg = robot.ConnectedState()
    if status != robolink.ROBOTCOM_READY:
        raise Exception("Failed to connect: " + status_msg)

    # Only after the confirmation protocol above, for this specific move:
    robot.MoveJ([10, 20, 30, 40, 50, 60])
```

Each real motion is its own separately-confirmed action (see the confirmation protocol above) —
don't treat the `with` block as license to queue up multiple real moves unattended in one script.

To run an existing GUI-built program on the robot instead of issuing motion calls directly (still
inside the same `with` block / connected session):

```python
prog = RDK.Item('MainProgram', robolink.ITEM_TYPE_PROGRAM)
prog.setRunType(robolink.PROGRAM_RUN_ON_ROBOT)
prog.RunProgram()
while prog.Busy() == 1:
    robolink.robomath.pause(0.1)
```

## Stopping and disconnecting

- **`robot.Stop()`** halts the current robot motion/program via the API. Treat it as the first
  response to anything unexpected — an unconfirmed motion about to execute, an obviously wrong
  trajectory, a stalled driver — but it is a software call over the same link everything else
  uses; it is **not** a substitute for the physical e-stop, and don't imply otherwise to the user.
- **`robot.Disconnect()`** ends the driver connection and returns the session out of real-robot
  control. Do this as soon as the confirmed task is done — don't leave a session connected
  "in case," since every motion call after that point targets real hardware until it's
  disconnected or the run mode is explicitly reset.
- If the driver becomes unresponsive (common after a real collision or axis-limit fault), the
  recovery path is a double disconnect, not a retry loop from the API: either double-click
  **Disconnect** in the GUI, or call `robot.Disconnect()` **twice** from the API — both force-kill
  the driver process. **Warning: if the driver is Python-based, this can kill other Python
  processes/instances riding on that same driver process, not just the intended one** — this is a
  process-kill, not a graceful stop; confirm with the user before using it if anything else might
  depend on that process. See `robodk-driver-builder`'s `references/driver-protocol.md` for detail.

## Common pitfalls

- **Forgetting `Connect()` is sticky.** `robot.Connect()` switches the whole `Robolink` session
  to `RUNMODE_RUN_ROBOT`. Every motion call afterward — including ones you or another part of the
  session write believing they're "just testing in sim" — now targets real hardware until you
  `Disconnect()` or call `RDK.setRunMode(RUNMODE_SIMULATE)`. Don't leave a session connected
  across an unrelated request.
- **Trusting the simulated pose without resyncing.** If the robot could have moved since the
  simulation was last opened (manual jogging, a previous session, a fault-recovery move), the
  simulated joints are not necessarily the real ones. Resync (**Get robot joints**, or read
  `robot.Joints()` right after connecting) before planning a move relative to "current position."
  Verify reachability with `robot.SolveIK()` before trusting a target as reachable/safe here too.
- **Reusing simulation-only speeds/accelerations.** Values that looked fine in simulation were
  never validated against the robot's real dynamics, payload, or the actual cell layout.
- **Treating a logged success as proof of a completed, safe motion.** Check `ConnectedState()`
  and `Busy()` / a program's actual return rather than assuming a call returning without
  exception means the robot physically finished where you intended.
- **Assuming socket communication is enabled.** A `Connect()` failure is often a vendor-side
  licensing/option issue (see `robodk-driver-builder`'s `references/driver-protocol.md`), not a bug
  in the call.
- **Silently retrying a failed connect.** `ConnectSafe`'s retry loop is a convenience for flaky
  networks, not a license to loop past a `ROBOTCOM_PROBLEMS`/`ROBOTCOM_DISCONNECTED` state
  without telling the user — report the status message and let them decide whether to keep
  trying.

## Verify and report

- Always report the exact `ConnectedState()` status and message, not just "connected."
- After a move, report what was actually commanded (target/joints/program name, speed) — not a
  generalized "moved the robot successfully."
- If you could not verify a motion actually completed as intended (no camera, no independent
  sensor, relying solely on the API's return value), say so explicitly rather than implying
  visual confirmation you don't have.
- `Disconnect()` and report that the session is back to simulation-only before ending the task.

## Bundled files

This skill has no bundled reference files of its own — the driver architecture, full
connect/disconnect API surface, vendor prerequisites, and network troubleshooting all live in
`robodk-driver-builder`'s `references/driver-protocol.md` (linked throughout above), since that
skill owns everything about drivers, including operating one, not just writing one.
