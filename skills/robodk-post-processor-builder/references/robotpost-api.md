# RobotPost API reference

Every method RoboDK calls on your post processor, what it receives, and the cases that are
easy to get wrong. RoboDK duck-types the class: it imports the module, instantiates
`RobotPost`, and calls these methods in program order.

## Contents

- [Construction and program structure](#construction-and-program-structure)
- [Motion](#motion)
- [Frames](#frames)
- [Timing and dynamics](#timing-and-dynamics)
- [I/O](#io)
- [Code and messages](#code-and-messages)
- [Class attributes and conventions](#class-attributes-and-conventions)
- [Call order in a real generation](#call-order-in-a-real-generation)

---

## Construction and program structure

### `__init__(self, robotpost=None, robotname=None, robot_axes=6, **kwargs)`

Called once per generation. `robotpost` is the post's display name, `robotname` the robot's
name in the station, `robot_axes` the robot's axis count.

`**kwargs` is mandatory. RoboDK passes version-dependent extras — observed in practice:
`axes_type` (e.g. `['R','R','R','R','R','R']`, `'T'`/`'J'` entries indicate external axes),
`native_name`, `ip_com`, `api_port`, `prog_ptr`, `robot_ptr`. A signature without `**kwargs`
raises `TypeError` before any code is generated.

Re-initialise **every** mutable attribute here (`PROG`, `PROG_LIST`, `PROG_NAMES`,
`PROG_FILES`, `LOG`, `HEADER`, counters). Class-level `[]` defaults are shared state and
leak between generations inside one RoboDK session.

### `ProgStart(self, progname)`

Start of each program. Called again for every subprogram in the same job, so it can fire
several times per generation. Filter the name once (`FilterName`), store the filtered
version, and reuse that everywhere — `ProgFinish`, `ProgSave`, and any subprogram call must
agree or the generated call won't resolve to the generated file.

Emit the per-program header here (`PROC name()`, `.MODULE`, `/JOB` etc.).

### `ProgFinish(self, progname)`

End of each program. Emit the footer, then move the accumulated `self.PROG` into
`self.PROG_LIST` and reset `self.PROG = []` so the next program starts clean.

Order matters and is a common source of subtle bugs: appending `self.PROG` to `PROG_LIST`
stores a *reference*, so lines added afterwards still land in the stored program — it works,
but only by accident. Append the footer first, then store, then reset.

### `ProgSave(self, folder, progname, ask_user=False, show_result=False)`

Writes the file(s). Responsibilities:

- If `ask_user` is true or `folder` doesn't exist, prompt with `robodialogs.getSaveFileName(...)`
  (single file) or `robodialogs.getSaveFolder(...)` (multi-file save) — both return a path
  **string** directly, or `''`/`None` if cancelled; return early in that case. `getSaveFile(...)`
  (returns a file object, use `.name`) still exists but is deprecated since RoboDK 5.5 — don't
  use it in new posts, and don't be misled by older posts that still do.
- Write the global header plus every program in `PROG_LIST`. Decide deliberately between one
  combined file and one file per program; whichever you choose must match how subprogram
  calls are emitted in `RunCode`.
- **Append every written path to `self.PROG_FILES`** — `ProgSendRobot` uploads exactly that
  list, so an unpopulated list means "Send program to robot" transfers nothing.
- `show_result` is either `True` (open with the OS default application) or a string path to
  an editor executable (`subprocess.Popen([show_result, filesave])`). Surface `self.LOG` via
  `mbox` at this point if non-empty — that's how warnings reach the user.

Choose the text encoding on purpose. Many controllers reject UTF-8/BOM and want ASCII or
Latin-1, and some require CRLF line endings.

### `ProgSendRobot(self, robot_ip, remote_path, ftp_user, ftp_pass)`

Called after `ProgSave` when "Send program to robot" is selected. Normally just
`UploadFTP(self.PROG_FILES, robot_ip, remote_path, ftp_user, ftp_pass)`.

---

## Motion

All motion arrives already solved by RoboDK. Do not recompute kinematics.

### `MoveJ(self, pose, joints, conf_RLF=None)`

Joint-interpolated move.

- `joints` — list of floats in **degrees** (prismatic axes in mm). Always provided.
- `pose` — 4×4 `Mat` of the TCP relative to the active reference frame, **or `None`** when
  the RoboDK target is a joint target. Implement `MoveJ` from `joints`; it is the only
  argument you can rely on.
- `conf_RLF` — robot configuration flags `[rear, lower, flip]` as 0/1 ints, or `None`. Only
  needed by controllers that store configuration with cartesian targets.
- `joints` may contain **more values than `nAxes`** when the cell has external axes. Decide
  explicitly whether to slice to `nAxes` or emit all of them.

### `MoveL(self, pose, joints, conf_RLF=None)`

Linear move. Same arguments. `pose is None` is the important case — a joint target used with
a linear move. Guard it: log via `addlog` and emit a comment, or emit the joint-space
equivalent. Dereferencing `None` here crashes generation mid-program.

### `MoveC(self, pose1, joints1, pose2, joints2, conf_RLF_1=None, conf_RLF_2=None)`

Circular move. `pose1`/`joints1` are the **via (intermediate)** point, `pose2`/`joints2` the
**end** point; the start point is the robot's current position. Either pose can be `None`
under the same joint-target condition — guard both.

---

## Frames

### `setFrame(self, pose, frame_id=None, frame_name=None)`

Reference / user / work frame, as a 4×4 `Mat` relative to the robot base.

`frame_id` is the numbered frame index when the station defines one; it is `-1` or `None`
when there isn't one — observed values include `0` and `-1` in the same generation. If the
controller can only select numbered frames, you need a fallback for the unnumbered case
(define the frame inline, or emit a warning through `addlog`).

`frame_name` is the human-readable station name — good material for a comment line, but it
can be empty.

Keep both as class attributes (`FRAME_ID`, `FRAME_NAME`, and the tool equivalents) that
double as the fallback and the live value: overwrite them only when RoboDK supplies
something usable, and read from them everywhere else. Point records that stamp the active
frame/tool number then have a single source of truth, and the unnumbered case resolves to a
value you chose deliberately instead of a `None` leaking into the output.

### `setTool(self, pose, tool_id=None, tool_name=None)`

Tool frame / TCP relative to the robot flange. Same `-1`/`None` caveat as `setFrame`.

---

## Timing and dynamics

### `Pause(self, time_ms)`

Delay in **milliseconds**, as a float. A **negative** value means "stop the program
indefinitely / wait for the operator", not a negative delay — branch on it and emit the
controller's halt instruction. Convert to seconds if the controller expects seconds.

### `setSpeed(self, speed_mms)` — linear speed, mm/s
### `setAcceleration(self, accel_mmss)` — linear acceleration, mm/s²
### `setSpeedJoints(self, speed_degs)` — joint speed, deg/s
### `setAccelerationJoints(self, accel_degss)` — joint acceleration, deg/s²

RoboDK calls these **only when the value changes**, which has two consequences:

1. The class-level default is what the first motion of every program uses. Set it to a value
   the controller accepts, not a placeholder.
2. If the controller wants a **percentage** of maximum rather than an absolute value, you
   need the maximum as a class constant and must convert on assignment, e.g.
   `self.SPEED_DEGSPER = round(speed_degs / self.SPEED_DEGSMAX * 100)`. Clamp the result —
   RoboDK will happily hand you a value above the robot's rated maximum.

### `setZoneData(self, zone_mm)`

Rounding / blending / flyby / zone distance in **mm**. `-1` (or any negative value) means
"stop at the point" — exact positioning. Controllers with named zones (`fine`, `z10`, `CNT`)
need a lookup from mm to the nearest named zone rather than a raw number.

---

## I/O

### `setDO(self, io_var, io_value)`
### `setAO(self, io_var, io_value)`
### `waitDI(self, io_var, io_value, timeout_ms=-1)`

`io_var` and `io_value` may be **integers or strings** — RoboDK allows symbolic I/O names
and symbolic values, so `type(io_value) != int` guards reject valid input. Format through
`str()` and treat non-numeric values as pass-through symbols.

For `setDO`, normalise numeric truthiness to the controller's boolean literals
(`1`/`0`, `TRUE`/`FALSE`, `ON`/`OFF`) while leaving symbolic values untouched.

For `waitDI`, `timeout_ms=-1` means wait indefinitely; a positive value needs the
controller's timeout form, and if the controller has none, say so via `addlog` rather than
silently dropping the timeout.

---

## Code and messages

### `RunCode(self, code, is_function_call=False)`

- `is_function_call=False` — `code` is raw controller source to insert verbatim. Emit it
  unchanged; the user typed it deliberately.
- `is_function_call=True` — `code` is a program/subprogram name to call, and it **may already
  include arguments**, e.g. `MyProg(1,2)`. Filtering the whole string with `FilterName` will
  mangle those parentheses, so split off any argument list before filtering the name.

The emitted call must resolve to whatever `ProgSave` actually wrote, and the exact string
matters. If programs are concatenated into one file, the call takes the program's **name**
as the controller declares it — `sub_prog("Path1()")` against a `PROC Path1()` header. A
file-based call (`sub_prog("Path1.spf")`) is only correct when `ProgSave` really writes a
separate `Path1.spf`. Appending an extension that no file has produces a program that loads
fine and fails when it reaches the call.

Also decide what to do with arguments. A post that unconditionally decorates the name, e.g.
`'sub_prog("' + FilterName(code) + '()")'`, turns `MyProg(1,2)` into `MyProg12()` — the
arguments are stripped by `FilterName` and an empty list is appended. If the controller
supports parameterised calls, split the argument list off before filtering.

### `RunMessage(self, message, iscomment=False)`

- `iscomment=True` — emit as a comment in the controller's comment syntax.
- `iscomment=False` — display on the teach pendant; fall back to a comment if the controller
  has no display instruction.

Watch comment length limits; several controllers truncate or reject long comments.

---

## Class attributes and conventions

Required / near-universal:

| Attribute | Purpose |
|---|---|
| `PROG_EXT` | output file extension, no dot |
| `PROG` | list of lines for the program being built |
| `PROG_LIST` | completed programs, in order |
| `PROG_NAMES` | filtered names, index-aligned with `PROG_LIST` |
| `PROG_FILES` | paths written by `ProgSave`; consumed by `ProgSendRobot` |
| `HEADER` | lines emitted once at the top of the file |
| `LOG` | warnings shown to the user after generation |
| `nAxes` | axis count from `robot_axes` |

Common conventions in shipped posts (not part of the API, but expected by users):
`ROBOT_POST`, `ROBOT_NAME`, `MAX_LINES_X_PROG` (split long programs into numbered parts),
`INCLUDE_SUB_PROGRAMS`, and the private helpers `addline(self, newline)` /
`addlog(self, newline)`.

Helper functions come from `robodk`. Modern layout:
`from robodk import robomath` / `from robodk import robodialogs` (`mbox`, `getSaveFileName`,
`getSaveFolder`) / `from robodk import robofileio` (`FilterName`, `DirExists`, `UploadFTP`),
qualifying calls (`robomath.pose_2_xyzrpw(...)`). The legacy `from robodk import *` still
re-exports all of them and is what older posts use; either is fine, but keep one style within a
file — don't mix `robomath.X()` with a bare `X()` from a wildcard import in the same post.

The pose/joints-to-string helper functions are conventionally named `pose_2_str`/`joints_2_str`
in current posts, but older posts and the official docs also use `angles_2_str` for the joint
one — about a third of shipped posts still do. Don't assume a fixed name when reading an
existing post; grep for whichever helper the motion methods actually call.

---

## Call order in a real generation

From an actual intermediate file — useful for reasoning about state:

```python
r = RobotPost("Siasun", "Siasun SR20A", 6, axes_type=['R','R','R','R','R','R'], ...)
r.ProgStart("Prog2")
r.RunMessage("Program generated by RoboDK ...", True)   # header comments
r.setFrame(p(0,0,0,0,0,0), 0, "Siasun SR20A Base")
r.setTool(p(86,0,451.5,0,36,0), -1, "Fronius MTB500i Welding Gun")   # tool_id == -1
r.MoveJ(None, [0,-30.0072,44.338,0,81.5392,-8.12e-15], None)         # pose is None
r.RunMessage("Start Weld")                              # pendant message, not a comment
r.setDO(5, 1)
r.RunCode("Path1", True)                                # subprogram call
r.setZoneData(5.000)
r.MoveL(p(902.712,150,227.288,0,-45,180), [...], [0,0,0])
r.Pause(500.0)
r.MoveJ(None, [...], None)
r.ProgFinish("Prog2")
r.ProgStart("Path1")                                    # subprogram body follows
r.setZoneData(1.000)
r.setSpeed(1000.000)                                    # first setSpeed of the job
r.setFrame(p(1000,0,80,0,0,0), -1, "part")
...
r.ProgFinish("Path1")
r.ProgSave("C:/.../Programs/", "Prog2", False, "C:/.../VSCodium.exe")
```

Note what this shows: no `setSpeed` before the main program's first `MoveL`, so that move is
emitted at the class default; `tool_id` is `-1`; `MoveJ` poses are `None`; the subprogram is
a second `ProgStart`/`ProgFinish` pair in the same file, and `ProgSave` is called once at the
end for the whole job.
