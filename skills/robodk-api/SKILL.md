---
name: robodk-api
description: Reference for writing, porting, or debugging application code against the RoboDK API — the Robolink/Item/Mat SDK for driving RoboDK from Python, TypeScript, C++, C#, MATLAB, C, or Visual Basic. Use when a user wants to write a script that connects to RoboDK, reads/writes item poses and joints, runs MoveJ/MoveL/MoveC, builds targets/frames/tools/programs, converts between Euler/pose conventions, or ports RoboDK API code from one language to another.
version: 1.2.0
author: RoboDK
license: MIT
platforms: [linux, windows, macos]
metadata:
  tags: [robodk, api, sdk, python, typescript, c++, c#, matlab, offline-programming]
  category: software-development
  related_skills: [robodk-addin, robodk-post-processor-builder, robodk-driver-builder]
---

# RoboDK API Reference

The RoboDK API is a multi-language SDK for controlling RoboDK: build/inspect stations, move
robots in simulation, solve FK/IK, and generate vendor-specific robot programs. It talks to a
running RoboDK instance over a TCP socket (default `localhost:20500`, line-based commands).
Every supported language — Python, TypeScript, C++, C#, MATLAB, C, Visual Basic — independently
re-implements the same wire protocol against the same three abstractions:

- **`Robolink`** (`RoboDK` in C++/C#) — the session/connection object; entry point for
  station-level operations (open/save files, list items, run mode, collisions).
- **`Item`** — any node in the station tree: robot, frame, tool, object, target, curve,
  program, instruction, camera, notes, ...
- **`Mat`** — a 4×4 homogeneous transform representing a pose (position + orientation).

**There is no code generation or shared source of truth between languages.** Each
`/Python`, `/TypeScript`, `/C++`, `/C#`, `/Matlab`, `/C`, `/Visual Basic` folder in this repo
hand-rolls the protocol independently. Naming is consistent across almost all of them (see
below), but always verify a method/constant against the actual file for the language you're
targeting — don't assume parity from the Python source alone.

## Which language, which file

| Language | Entry point(s) | Notes |
|---|---|---|
| **Python** (reference impl) | `assets/robodk-api/robolink.py` (`Robolink`, `Item`), `assets/robodk-api/robomath.py` (`Mat` + pose helpers) — **bundled with this skill**, see below | `pip install robodk`, or RoboDK's bundled interpreter already has it on `PYTHONPATH` |
| **TypeScript/JS** | [`TypeScript/src/robodk.ts`](https://github.com/RoboDK/RoboDK-API/blob/master/TypeScript/src/robodk.ts) (single file: `Mat`, `Robolink`, `Item`) | `npm install @robodk/robodk`. **Every I/O method returns a `Promise` — always `await` it.** Zero dependencies, Node 18+ |
| **C++** | [`C++/robodk_api.h`](https://github.com/RoboDK/RoboDK-API/blob/master/C%2B%2B/robodk_api.h) / [`.cpp`](https://github.com/RoboDK/RoboDK-API/blob/master/C%2B%2B/robodk_api.cpp) (classes `RoboDK`, `Item`, `Mat : public QMatrix4x4`) | Requires Qt (Widgets, GUI, Concurrent, Core, Network). `using namespace RoboDK_API;` or define `RDK_SKIP_NAMESPACE`. Build via CMake or drop the two files into a Qt project |
| **C#** — two incompatible styles, pick one | [`C#/Example/RoboDK.cs`](https://github.com/RoboDK/RoboDK-API/blob/master/C%23/Example/RoboDKSampleProject/RoboDK.cs) (Python-style, `setPose`) **or** [`C#/API/`](https://github.com/RoboDK/RoboDK-API/tree/master/C%23/API) (NuGet `RoboDK API`, interfaces `IRoboDk`/`IItem`, PascalCase `SetPose`) | Don't mix method-casing conventions from the two options in one project |
| **MATLAB** | [`Matlab/Robolink.m`](https://github.com/RoboDK/RoboDK-API/blob/master/Matlab/Robolink.m), [`Matlab/RobolinkItem.m`](https://github.com/RoboDK/RoboDK-API/blob/master/Matlab/RobolinkItem.m) | Standalone `.m` files, no build step — add `/Matlab` to the MATLAB path. `doc Robolink` / `doc RobolinkItem` for inline help |
| **C** | [`C/robodk_api_c.h`](https://github.com/RoboDK/RoboDK-API/blob/master/C/robodk_api_c.h) / [`.c`](https://github.com/RoboDK/RoboDK-API/blob/master/C/robodk_api_c.c) | Plain C: `RoboDK_FunctionName(&rdk, ...)` / `Item_FunctionName(&item, ...)` — first arg is always a pointer to the struct, mirroring `RoboDK::FunctionName()` / `Item::FunctionName()` in C++. Only a subset of the full API is implemented. Winsock-based; byte-swapping assumes little-endian |
| **Visual Basic** | [`Visual Basic/RoboDK_API.vb`](https://github.com/RoboDK/RoboDK-API/blob/master/Visual%20Basic/RoboDK_API.vb) (Python-style) **or** NuGet `RoboDK API` package (more complete) | `.vb` file include has "more limited functionality" per the language README — prefer NuGet unless you need the single-file drop-in |

Full per-language method-naming and quick-start detail: **`references/language-notes.md`**
(bundled with this skill). Full Robolink/Item/Mat method and constant inventory (Python names,
canonical across languages except C#/API): **`references/api-surface.md`** (also bundled).

## Core concepts (Python names — see the table above for per-language casing)

Prefer importing the `robolink`/`robomath` **modules**, not `import *`, and qualify names
(`robolink.Robolink()`, `robolink.ITEM_TYPE_ROBOT`, `robomath.Pose(...)`). It's clearer about
where a name comes from and avoids clobbering builtins (`robomath` exports things like `pi`,
`eye`). The wildcard form (`from robodk.robolink import *`) is still fine for short, one-off
scripts — it's what most of RoboDK's own bundled examples use. The rest of this document uses
bare names (`Pose()`, `ITEM_TYPE_ROBOT`, ...) for brevity; under the qualified style, read
those as `robomath.Pose()` / `robolink.ITEM_TYPE_ROBOT`. `Item`/`Mat` **instance** methods
(`item.Pose()`, `robot.MoveJ(...)`) never need a module prefix — only the bare module-level
functions and constants from `robolink`/`robomath` do.

### Connect

**Always prefer this skill's bundled copy over whatever `robodk` package the environment happens
to have.** A plain `from robodk import robolink` resolves to *whichever* `robodk` package
`sys.path`/`PYTHONPATH` finds first, which is usually a `pip install robodk` that can be an older
or incompatible version. The features these skills rely on landed in **6.0.2** — in 6.0.1 and
earlier `Robolink` has no `__enter__`/`__exit__` at all, so against an older install
`with robolink.Robolink() as RDK:` raises `TypeError: ... does not support the context manager
protocol`. Nothing fails until that `with` line, which makes it easy to misdiagnose.

Prepend the bundled directory to `sys.path` so the bundled `robodk` package wins, then import
normally:

```python
import sys
sys.path.insert(0, "<this skill's path>/assets/robodk-api")  # e.g. ~/.claude/skills/robodk-api/assets/robodk-api
from robodk import robolink, robomath

RDK = robolink.Robolink()   # connects to localhost:20500; launches RoboDK if not already running
```

The bundled files live in `assets/robodk-api/robodk/` — an actual Python package directory, so
the import above is the ordinary one and no path hacks or per-module imports are needed. Insert
the **parent** (`assets/robodk-api`) on `sys.path`, not the `robodk/` folder itself.

**Do not import the modules as bare top-level names** (`import robolink`). The bundled files
import each other as `from robodk import robomath` (see `robodk/robolink.py`), so a bare
`import robolink` only resolves if some *other* `robodk` package is also installed — which
defeats the point. Worse, when a pip `robodk` is present the two forms load *different copies
simultaneously*: your script gets the bundled `robomath` while `robolink` internally uses pip's,
producing two unrelated `Mat`/`Robolink` classes with the same names and no error. Verified.

Inside RoboDK's own bundled Python interpreter, a plain `from robodk import ...` with no
`sys.path` insert is fine — that interpreter always has a matching version on `PYTHONPATH`.

`robolink.Robolink(robodk_ip='localhost', port=None, args=[...], robodk_path=...,
close_std_out=False, quit_on_close=False, com_object=None, skipstatus=False)`. Class constants
worth knowing: `PORT_START = PORT_END = 20500`, `TIMEOUT = 10` (seconds), `SAFE_MODE` /
`AUTO_UPDATE` (leave at defaults unless you're specifically debugging render/validation
behavior).

**Closing the connection:** `Robolink` supports the context-manager protocol — always prefer
`with robolink.Robolink(...) as RDK:` over a manual `try`/`except`/`finally` around
`RDK.CloseRoboDK()`. On exit, it only calls `CloseRoboDK()` when `-NEWINSTANCE` (or
`/NEWINSTANCE`) was passed in `args` (directly or via `ROBODK_AI`, below); without it, exiting the
`with` block leaves RoboDK running (it may be the user's already-open instance, not one this
connection owns).

**Headless/scripted testing:** never launch RoboDK via its executable/`.app` path yourself (no
`open -a RoboDK.app`, no `subprocess` on `getPathRoboDK()`'s path, no polling for the port) — let
`Robolink()` do the launching, even when debugging something that looks launch-related.

**Prefer the `ROBODK_AI` environment variable over hardcoding launch args.** Set it in the process
environment before running the script — `ROBODK_AI=noui` for a normal headless run, `ROBODK_AI=
snapshot` when a screenshot is needed — and write plain `with robolink.Robolink() as RDK:` with no
`args=[...]` at all. `Robolink.__init__` reads `ROBODK_AI` and fills in the right launch profile
automatically (only args not already present in `args=[...]` are added, so explicit args still
take precedence for anything you need to override):

- `ROBODK_AI=noui` → `-NOUI`, `-NEWINSTANCE`, `-SKIPINI`, `-Settings=LicenseLoad`,
  `-EXIT_LAST_COM`, `-API_NODELAY`. The right default for common tasks whenever no screenshot is
  needed. `-NOUI` disables real rendering at startup, not just window visibility, so don't try to
  fix a running `-NOUI` instance in place (a post-connect `setWindowState()` call on it does not
  recover rendering).
- `ROBODK_AI=snapshot` → same profile but `-HIDDEN`/`-NOSPLASH` instead of `-NOUI`, for when a
  screenshot is needed. `-NOSPLASH` stops the startup splash flashing before the hidden state
  takes effect. **Whether `-HIDDEN` still renders is platform-dependent — check before relying
  on it:**
  - **macOS:** `-HIDDEN` keeps real rendering, the window just isn't shown (verified).
  - **Windows: it does not.** Verified on Windows 11 + RoboDK 6.0.0.26413 —
    `Command('Snapshot', path)` against a `-HIDDEN` instance writes a **120-byte blank PNG**, at
    both 0.5 s and 3 s after `Render(True)`, so it is not a timing problem. The same station with
    a visible window writes a real 118 KB image. On Windows, take screenshots from a **visible**
    instance: launch with `ROBODK_AI` unset (or `args=["-NEWINSTANCE"]`), call
    `setWindowState(WINDOWSTATE_MAXIMIZED)`, `Render(True)`, `Command('FitAll')`, then snapshot.
  - **Linux:** untested — treat as unverified and check the output.

  **Always verify a snapshot has real content** (file size well above a few hundred bytes, or
  decode it and confirm more than one pixel colour) before reporting it as evidence. A blank
  snapshot is still a valid PNG and will not raise.

This keeps the script itself identical whether it's exercised headlessly or run normally by the
end user (`ROBODK_AI` unset → plain windowed `Robolink()`, attaches to whatever is already open)
— don't branch script logic on headlessness. Both profiles include `-NEWINSTANCE`, which is also
what the context-manager `__exit__` checks for, so either one self-cleans on `with`-block exit.
`-API_NODELAY` sets `TCP_NODELAY` on the API socket at connect time (disables Nagle's algorithm),
trading a little extra resource use for lower per-call latency — matters most when the API client
isn't on the same machine as RoboDK. Linux doesn't need `--platform minimal` added manually
(auto-prepended when `-NOUI` is present). RoboDK's own console output streams through by default
(`close_std_out=False`) — read it instead of assuming silence. **Keep it simulation-only** — an
unattended headless instance is the wrong place for `Connect()` to a physical robot or
`RUNMODE_RUN_ROBOT`. Full flag rationale, the server/CI/container recipe, and the `close_std_out`
callable form: **`references/headless-testing.md`**.

### Don't leave RoboDK running

`with robolink.Robolink() as RDK:` plus a `ROBODK_AI` profile cleans up reliably. Measured on
Windows + RoboDK 6.0.0, counting surviving processes afterwards:

| How the script ended | RoboDK left running |
|---|---|
| `ROBODK_AI=noui`, normal exit | 0 |
| `ROBODK_AI=noui`, exception raised inside the `with` | 0 |
| `ROBODK_AI=noui`, process hard-killed mid-session | 0 |
| explicit `args=[...]` **without** `-EXIT_LAST_COM` | **1 — leaks** |

`-EXIT_LAST_COM` (in both `ROBODK_AI` profiles) is what does the work: RoboDK exits when the last
API connection drops, which covers crashes and kills too. So the rule is simply **use a
`ROBODK_AI` profile and the context manager, and cleanup takes care of itself.**

Deliberately omitting `-EXIT_LAST_COM` — the only way to keep one instance alive across several
separate processes, which a per-command CLI bridge needs — opts out of all of that. Nothing will
ever close that instance; close it explicitly when the task ends (`RDK.CloseRoboDK()`). A leaked instance keeps its port bound, so the next launch silently picks a
different port and looks unreachable.

Two ways a script can hang that look like RoboDK being slow, both verified:

- **A surviving RoboDK inherits your captured stdout.** Launching it from
  `subprocess.run(..., capture_output=True)` means the pipe never closes, so `communicate()`
  blocks past its timeout even though the launcher script itself finished. Launch with
  `stdout=subprocess.DEVNULL` (and poll the port) whenever RoboDK is meant to outlive the call.
- **A plain `Robolink()` with no context manager can stop your own script exiting**, because the
  connection's stdout-reader thread stays alive. Another reason to prefer the `with` form even
  for a short script.

### Find items

- `RDK.Item(name, itemtype=None)` → `Item` — if `name` isn't unique across item types, pass an
  `ITEM_TYPE_*` filter explicitly or you may get the wrong hit.
- `RDK.ItemList(filter=None, list_names=False)` → list of `Item` (or names).
- Item types (`ITEM_TYPE_*`): `STATION, ROBOT, FRAME, TOOL, OBJECT, TARGET, CURVE, PROGRAM,
  INSTRUCTION, PROGRAM_PYTHON, MACHINING, BALLBARVALIDATION, CALIBPROJECT, VALID_ISO9283, FOLDER,
  ROBOT_ARM, CAMERA, GENERIC, ROBOT_AXES, NOTES`.

### Pose (`Mat`) and Euler conversions

`Mat` is a 4×4 homogeneous transform; `*` composes transforms (`transl(100,0,0) * rotz(pi/2)`).

- Build a translation pose: `transl(x,y,z)` - x,y,z translation in millimeters.
- Build a rotation pose: `rotx(rx)`, `roty(ry)`, `rotz(rz)` - rotation around the X, Y and Z axis respectively. rx,ry,rz rotation in radians.
- Build a generic pose with all parameters, degrees: `Pose(x, y, z, rx, ry, rz)` — six direct
  args, **translation in millimeters, angles in degrees**.
- Build a generic pose with all parameters, radians: `TxyzRxyz_2_Pose([x, y, z, rx, ry, rz])` —
  **one list argument** (not six separate args — `TypeError: takes 1 positional argument but 6
  were given` otherwise, verified), translation in millimeters, angles in **radians**. Both are
  the same as: `transl(x,y,z) * rotx(rx) * roty(ry) * rotz(rz)` (with `rx,ry,rz` in radians either way internally).
- Decompose: `Pose_2_TxyzRxyz(pose)` → **x,y,z in millimeters and rx,ry,rz in radians**. 
- Vendor round-trips exist both ways: `Pose_2_KUKA` / `KUKA_2_Pose`, `_2_Fanuc`, `_2_Motoman`,
  `_2_ABB`, `_2_UR`, `_2_Staubli`, `_2_Adept`, `_2_Nachi`, `_2_Comau`, `_2_Catia`, `_2_Techman`.
  Each encodes a different Euler-angle convention — don't assume they're interchangeable.
- `Mat.Pos()`, `.setPos()`, `.VX()/.VY()/.VZ()` (axis vectors), `.inv()`/`.invH()` (homogeneous
  inverse), `.eye(4)` (identity).
- Relative translations: any frame or item can be translated using its relative coordinate system by [x,y,z] mm using this formula: `frame.setPose(frame.Pose() * transl(x,y,z))`.
- Relative orientation: any frame or item can be rotated using its relative coordinate system, by [rx,ry,rz] rad using this formula:
`frame.setPose(frame.Pose() * rotx(rx) * roty(ry) * rotz(rz))`.

Tip: To build a station, most of the times you simply need to rotate around the Z axis, so a common object can be placed using this formula: `transl(x,y,z) * rotz(rz)`

### Item pose / joints

- `item.Pose()` / `item.setPose(pose)` — **local** pose, relative to the item's parent.
- `item.PoseAbs()` / `item.setPoseAbs(pose)` — **world** pose. Easy to confuse the two once
  frames are nested — pick deliberately.
- `item.Joints()` / `item.setJoints(joints)` — robot/mechanism joint values.
- `item.PoseTool()` / `item.setPoseTool(tool)`, `item.PoseFrame()` / `item.setPoseFrame(frame)` —
  the active TCP and reference frame a robot moves relative to.

### Motion

- `robot.MoveJ(target, blocking=True)` — joint move. `MoveL(target, ...)` — linear.
  `MoveC(target1, target2, ...)` — circular via `target1`, ending at `target2`.
  `target` may be an `Item` (target/frame), a joints list, or a `Mat` pose.
- `robot.SolveFK(joints)` → pose. `robot.SolveIK(pose, joints_approx=None)` → joints.
- `robot.setSpeed(speed_linear, speed_joints=-1, accel_linear=-1, accel_joints=-1)`,
  `setSpeedJoints`, `setAcceleration`, `setAccelerationJoints`, `setRounding`/`setZoneData`
  (blend radius, mm).
- A **joint-only target has no pose** — `MoveL`/`MoveC` against it fail or behave unexpectedly;
  use the joint-space call, or convert with `SolveFK` first.

### Programs and run modes

- `RDK.AddProgram(name, itemrobot=0)` → `Item`; `item.RunProgram(...)` / `RunCode(...)` /
  `RunInstruction(...)`.
- `item.MakeProgram(folder_path='', run_mode=RUNMODE_MAKE_ROBOTPROG)` generates a
  vendor-specific controller program via the active Post Processor for that robot. Post
  processors (the `RobotPost` layer, `.py` files defining `MoveJ`/`MoveL`/`ProgSave`/...) ship
  with the RoboDK installation (`RoboDK/Posts/`), not with this repo — see
  https://robodk.com/doc/en/PythonAPI/postprocessor.html and any post-processor-authoring
  docs/skill you have available.
- `RUNMODE_*`: `SIMULATE` (default), `QUICKVALIDATE`, `MAKE_ROBOTPROG`,
  `MAKE_ROBOTPROG_AND_UPLOAD`, `MAKE_ROBOTPROG_AND_START`, `RUN_ROBOT` (drives the physical
  robot). Set with `RDK.setRunMode(mode)`. **This skill is simulation-only** — if the request is
  actually about moving real hardware, that's `robodk-real-robot-control`'s job, with its own mandatory
  per-action confirmation protocol, not something to wire up here.

### Building a station

`RDK.AddFrame(name, itemparent=0)`, `RDK.AddTarget(name, itemparent=0, itemrobot=0)`,
`robot.AddTool(tool_pose, tool_name)`, `RDK.AddFile(filename, parent=0)` (imports any of `.rdk`,
`.robot`, `.tool`, STEP/IGES/STL, ...), `RDK.AddShape(...)`, `RDK.AddCurve(...)`,
`RDK.AddPoints(...)`, `RDK.Save(filename, itemsave=0)`.

### Discovering commands, item parameters, and trigger actions

`Robolink.Command(cmd, value)` and `Item.setParam(param, value)` are generic escape hatches
covering far more behavior than named methods expose — but their valid names are defined by the
*running RoboDK application* (version + plugins), not by the SDK source, so they can't be fully
listed here once and for all. Query them live instead of guessing a name:

- `RDK.Command("", "")` → table of all global commands with descriptions.
- `item.setParam("", "")` (or `RDK.ActiveStation().setParam("", "")`) → table of all per-item /
  station commands.
- `RDK.Command("TriggerAction", "")` → valid trigger-action strings (undocumented elsewhere).

**`references/command-discovery.md`** has a full captured snapshot of all three tables (136
global commands, 58 item/station commands, 147 trigger actions, as of RoboDK v6.0.7.26935) plus
the parsing recipe and refresh instructions. Reach for it whenever you (or another skill built on
top of this one) need a command/parameter that isn't a named method — check the table first,
query live to confirm on a different RoboDK version, and don't invent a plausible-looking name.

## Examples

**[`Python/Examples/`](https://github.com/RoboDK/RoboDK-API/tree/master/Python/Examples)** is
the largest curated set (57 `Scripts/`, runnable as-is via `Tools ▸ Run Script`; 122 `Macros/`,
usually need adaptation) and the best starting point regardless of target language — port the
Python pattern once it's confirmed working. Its own README has a categorized index by topic
(connecting, motion, programs, curves/geometry, calibration, cameras, cell simulation, cycle
time, UI, vendor-specific).

Smaller per-language samples: [`Matlab/`](https://github.com/RoboDK/RoboDK-API/tree/master/Matlab)
(`Example_RoboDK*.m`), [`C++/Example/`](https://github.com/RoboDK/RoboDK-API/tree/master/C%2B%2B/Example),
[`C/example.c`](https://github.com/RoboDK/RoboDK-API/blob/master/C/example.c),
[`Visual Basic/Example/`](https://github.com/RoboDK/RoboDK-API/tree/master/Visual%20Basic/Example),
[`TypeScript/tests/robodk.test.ts`](https://github.com/RoboDK/RoboDK-API/blob/master/TypeScript/tests/robodk.test.ts).

## Porting checklist (Python → another language)

1. **Get it working in Python first** if you can — it's the reference implementation and the
   examples folder is deepest there. Port from a confirmed-working script, not from memory of
   the API shape.
2. **Method names carry over almost verbatim** (`setPose`, `MoveJ`, `ItemList`, ...) to
   TypeScript, C++, MATLAB, C's `Item_`/`RoboDK_` prefix form, and the C#/VB *Example* files.
   The one deliberate exception is the **C#/API NuGet package**, which renames to PascalCase
   (`SetPose`) behind `IRoboDk`/`IItem` interfaces — check `references/language-notes.md`
   before assuming a name.
3. **TypeScript: add `await` to every call.** A missed `await` silently hands back a `Promise`
   object instead of the value — `robot.Joints()` without `await` is not a joints array.
4. **C++: Qt is a hard dependency**, and Qt containers (`QList`, `QString`) appear in
   signatures — not `std::vector`/`std::string`.
5. **The degrees/radians split in `Pose()` vs `Pose_2_TxyzRxyz()` is a protocol-level fact, not
   a Python quirk** — it holds in every language's binding. Verify units explicitly rather than
   assuming a converted value's scale.
6. **Verify against that language's own tests/examples**, not the Python ones:
   [`Python/tests/`](https://github.com/RoboDK/RoboDK-API/tree/master/Python/tests) (needs a
   live RoboDK + matching `.rdk` station, see the `.cmd` files),
   [`TypeScript/tests/robodk.test.ts`](https://github.com/RoboDK/RoboDK-API/blob/master/TypeScript/tests/robodk.test.ts)
   (`npm test`).
7. **Protocol-level changes need porting by hand, everywhere.** If you're fixing a wire-format
   bug (not just an API convenience method), check whether `/Python`, `/TypeScript`, `/C++`,
   `/C#`, `/Matlab`, `/C`, and `/Visual Basic` all need the same fix — none of them share
   implementation.

## Where to look for more

All of the following are published, public docs — no local checkout needed:

- **Full Python API reference** (Sphinx-generated from docstrings, exhaustive per-method
  detail): https://robodk.com/doc/en/PythonAPI/index.html
  (module reference: https://robodk.com/doc/en/PythonAPI/robodk.html).
- **General, language-agnostic RoboDK API guide** (why/what before how — connecting, the three
  run modes, command-line options): https://robodk.com/doc/en/RoboDK-API.html
- **Post processors** — the separate `RobotPost` layer that turns a RoboDK-simulated program
  into real controller code; ships with the RoboDK installation (`RoboDK/Posts/`), not this
  repo. Reach for it once you're past "the simulation moves correctly" and into "the generated
  `.src`/`.mod`/`.ls` file is wrong." https://robodk.com/doc/en/PythonAPI/postprocessor.html
- **RoboDK Plug-In interface** (distinct from this client API — for code that runs *inside*
  RoboDK rather than connecting to it over the socket):
  [`C++/PluginApiExample/`](https://github.com/RoboDK/RoboDK-API/tree/master/C%2B%2B/PluginApiExample),
  https://robodk.com/doc/en/PlugIns/index.html.

## Common pitfalls

1. **Degrees vs. radians.** `Pose(x,y,z,rx,ry,rz)` takes degrees; `Pose_2_TxyzRxyz(pose)`
   returns radians. Mixing them silently produces a wildly wrong orientation, not an error.
2. **Local vs. absolute pose.** `setPose`/`Pose()` are relative to the item's parent;
   `setPoseAbs`/`PoseAbs()` are world-frame. Reparenting an item changes what `Pose()` means
   without changing `PoseAbs()`.
3. **Ambiguous `RDK.Item(name)` lookups.** Without an `itemtype` filter, a name that collides
   across a target and a program (for instance) resolves to whichever RoboDK finds first — pass
   the `ITEM_TYPE_*` explicitly whenever the name isn't guaranteed unique.
4. **`MoveL`/`MoveC` on a joint-only target.** These need a pose; a target created as
   joint-space-only doesn't have one. Check `item.isJointTarget()` before assuming a pose exists.
5. **`RUNMODE_RUN_ROBOT` moves the physical robot.** It is not the default and should never be
   set implicitly by copy-pasted example code. If the task genuinely calls for real-robot motion,
   hand it to `robodk-real-robot-control` rather than wiring `Connect()`/`RUNMODE_RUN_ROBOT` up here.
6. **TypeScript: unawaited promises.** Every `Robolink`/`Item` method is `async`; forgetting
   `await` is the most common bug when porting a Python script line-for-line.
7. **C#: don't blend the two integration styles.** `RoboDK.cs` (Example, lowercase `setPose`)
   and the NuGet `IRoboDk`/`IItem` package (PascalCase `SetPose`) are separate implementations
   with separate method casing — reference material for one won't compile against the other.
8. **Protocol-level changes need porting by hand, everywhere** — see checklist item 7 above.
9. **Headless Linux startup flags are easy to get wrong.** `-NOUI` alone isn't enough — you also
   need `--platform minimal` and the Qt platform-plugin apt packages, or RoboDK fails to start
   with no obvious error. Follow `references/headless-testing.md` rather than guessing flags.
10. **Inventing `Command()`/`setParam()` names.** These calls accept arbitrary strings and fail
    silently or do the wrong thing on an unrecognized one. Check `references/command-discovery.md`
    (a captured snapshot of every valid name) first, and re-query live if you're on a RoboDK
    version other than the one it was captured against.
11. **Leaking test/debug scaffolding into sample code shown to the user.** Headless
    `args=[...]`, `close_std_out`, and printing `RDK.License()` are how you verify a script works
    against a live instance — not part of the task it's solving. Default sample code to plain
    `RDK = robolink.Robolink()` plus the task logic; surface headless/licensing mechanics only if
    the user is specifically asking about testing or licensing.
12. **`RDK.Save(filename, itemsave=0)` return value is not a success signal.** The Python binding
    has no `return` statement at all — it always yields `None`, whether or not the file was
    actually written (a raised exception is the only in-band failure signal, via
    `_check_status()`). Never gate success on `bool(RDK.Save(...))`; verify by checking that the
    target file exists (`Path(filename).exists()`) and, ideally, recording its size.

## Bundled files

- `references/language-notes.md` — per-language quick-start snippet, install command, and
  naming-convention caveats for all seven languages.
- `references/api-surface.md` — fuller Robolink/Item/Mat method and constant inventory than
  fits in this file, organized by category (connection, item lookup, pose/joints, motion,
  programs, collisions, cameras, calibration, ...).
- `references/command-discovery.md` — captured snapshot of all `Robolink.Command()` global
  commands, `Item.setParam()` per-item/station commands, and `TriggerAction` values, plus how to
  re-capture them from a live RoboDK instance when working against a different version.
- `references/headless-testing.md` — running RoboDK with no display: quick script verification
  via `Robolink(args=[...])`, the full flag rationale, the `close_std_out` callable form, and the
  server/CI/container recipe.
- `references/linux-update-and-license.md` — verified Linux workflow for updating an existing
  RoboDK install via a temporary-directory-and-swap pattern, plus command-line license activation
  (`-LCMD=...`) and the verification gate for it (a logged `OK` doesn't mean the license is
  actually active).
- `assets/robodk-api/robodk/` — a copy of the actual Python `robodk` package source
  (`robolink.py`, `robomath.py`, `robodialogs.py`, `robofileio.py`, `roboapps.py`,
  `robolinkutils.py`), laid out as a real importable package so `sys.path.insert(0,
  ".../assets/robodk-api")` + `from robodk import robolink` resolves here. Read it directly for
  an exact signature/docstring instead of trusting the summary above or `api-surface.md`. See
  `assets/robodk-api/SNAPSHOT.md` for the source version/commit and how to refresh it.
  **This is a live runtime dependency, not just a read-only reference** — it pins a known-good
  release (6.0.2, the first with context-manager support and `ROBODK_AI`) instead of trusting
  whatever `robodk` version an environment happens to have installed. Other skills in this repo
  also fall back to this copy (by walking up to find this repo's `skills/robodk-api/` directory)
  when a found RoboDK install has no `robodk` package of its own. Keep it refreshed rather than
  letting it drift stale.
- `robodk_api/paths.py` — installable Python module (`pip install .` from this skill folder, or
  imported directly by other skills in this repo without installing) holding the single canonical
  implementation of RoboDK install-root/library-path resolution:
  `robodk_root_candidates()`/`resolve_robodk_root()`/`resolve_robodk_library_dir()`. Other skills
  in this repo import this module (a normal package import first, then a fallback that walks up
  to find this repo's `skills/robodk-api/` directory) instead of keeping their own copies — see
  this skill's own `README.md`.

Everything above is self-contained (no dependency on files outside this skill folder) — safe
to move this whole `robodk-api/` folder to another repo, though any other skill that depends on it
then needs `robodk_api/paths.py` (and, for the bundled-`robolink` fallback, `assets/robodk-api/`)
installed or reachable by walking up to a `skills/robodk-api/` directory to keep resolving
RoboDK's install root. Example
*code* still lives only in
the [`Python/Examples/`](https://github.com/RoboDK/RoboDK-API/tree/master/Python/Examples) folder
of the RoboDK-API repo itself (linked above), not duplicated here — only the importable package
source is bundled.
