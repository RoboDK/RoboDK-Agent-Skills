---
name: robodk-post-processor-builder
description: Read, write, debug, and extend RoboDK post processors — the Python files defining a `RobotPost` class (MoveJ/MoveL/MoveC/setFrame/setTool/setSpeed/setZoneData/setDO/waitDI/RunCode/RunMessage/ProgSave...) that translate a RoboDK simulation program into a real robot controller program. Use this skill whenever the user mentions RoboDK, post processors, "the post", a Posts folder, or generating/fixing robot controller code in any dialect (KRL .src, RAPID .mod, Fanuc .ls, Motoman .jbi, Siasun .spf, URScript, Kawasaki .as, G-code) — including indirect asks like "my robot program comes out wrong", "add an instruction to the post", "make a post for <controller>", "why is the speed wrong in the generated program", or when they hand you a controller program and ask for something that could produce it.
version: 1.0.0
author: RoboDK
license: MIT
platforms: [linux, windows, macos]
metadata:
  tags: [robodk, post-processor, robot-programming, controller-code]
  category: software-development
  related_skills: [robodk-api, robodk-driver-builder]
---

# RoboDK Post Processors

A post processor is the translation layer between RoboDK's simulation and a physical
controller. Get it wrong and a real robot executes wrong motion — so favour reading the
target controller's actual syntax over guessing, and verify by regenerating a program and
diffing it (see **Verify**, below).

## The pipeline

```
RoboDK program
      │  RoboDK flattens the program into an ordered list of API calls
      ▼
PostProg<Name>.py        ← "intermediate file": plain Python, imports your post,
      │                     instantiates RobotPost(), calls methods in execution order,
      │                     ends with r.ProgSave(folder, progname, ...)
      ▼
<YourPost>.py            ← the post processor: each method appends controller
      │                     source lines to self.PROG
      ▼
Prog.<PROG_EXT>          ← the controller program that gets loaded onto the robot
```

Two consequences worth internalising:

1. **The post is a transcriber, not a planner.** RoboDK has already solved the kinematics.
   Every motion call arrives with joint values already computed, and usually the cartesian
   pose too. Never re-solve kinematics, re-order motion, or "improve" the trajectory.
2. **The intermediate file is a complete, runnable test harness.** If the user has one
   (`PostProg*.py`), you can replay it against a modified post and diff the output against
   a known-good controller program. This turns post editing from guesswork into a
   regression test. Use `scripts/replay_intermediate.py`.

## The contract RoboDK relies on

These are load-bearing — RoboDK imports the module and duck-types it:

- The file is a plain Python module; **the class must be named `RobotPost`**.
- `__init__(self, robotpost=None, robotname=None, robot_axes=6, **kwargs)` — the `**kwargs`
  is not optional. RoboDK passes extra keywords (`axes_type`, `native_name`, `ip_com`,
  `api_port`, `prog_ptr`, `robot_ptr`) that vary by version; without `**kwargs` the post
  raises `TypeError` before emitting a single line.
- `PROG_EXT` sets the output file extension.
- Any instruction method the user's programs don't use may be omitted, but a missing method
  that *is* used will crash generation — implement all of them, even as a comment/no-op.

Full signatures and per-argument semantics: **`references/robotpost-api.md`**. Read it
before writing or auditing any method — the argument shapes (a `Mat` pose vs a joint list,
the `None` cases) are where most bugs live.

## Instruction set

| Method | Meaning | Typical implementation |
|---|---|---|
| `MoveJ` | joint move | emit |
| `MoveL` | linear move | emit |
| `MoveC` | circular move (via + end point) | emit |
| `setFrame` | reference/user/work frame | emit, or store |
| `setTool` | tool frame / TCP | emit, or store |
| `Pause` | delay | emit |
| `setSpeed` | linear speed, mm/s | **store** |
| `setAcceleration` | linear accel, mm/s² | **store** |
| `setSpeedJoints` | joint speed, deg/s | **store** |
| `setAccelerationJoints` | joint accel, deg/s² | **store** |
| `setZoneData` | rounding/blend/flyby, mm | **store**, or emit |
| `setDO` | digital output | emit |
| `setAO` | analog output | emit |
| `waitDI` | wait for input | emit |
| `RunCode` | call a program / thread / raw code | emit |
| `RunMessage` | comment or operator message | emit |

**"Emit" vs "store" is the central design decision.** Controllers whose motion statements
carry their own speed/blend arguments (`movel(pose, 1000, 1, 5)`) need the setters to
*store* into instance variables that the next motion line reads. Controllers with modal
state (`SPEED 1000` on its own line, applying until changed) need the setters to *emit*.
Decide this per instruction from the target controller's grammar, and don't do both — a post
that both emits `zone(5)` and passes `5` into every following move line is emitting
redundant, potentially conflicting state.

## Reading an existing post

Work outside-in; the goal is a mapping table you can hand back to the user.

1. **Shape**: `PROG_EXT`, `ROBOT_POST`, class-level defaults, and what `__init__` actually
   re-initialises.
2. **Program structure**: `ProgStart` / `ProgFinish` / `ProgSave`. Answer specifically —
   does a multi-program job become one file or several? How are subprograms *called*
   (`RunCode(..., is_function_call=True)`) versus how are they *written*? These two answers
   must agree, and a mismatch is a classic defect. If `ProgSave` concatenates every program
   into one file, the call has to reference a **name or label** the controller can resolve
   inside that file — emitting a *filename* (`sub_prog("Path1.spf")`) points at a file
   nothing ever wrote. Only emit a file-based call if `ProgSave` genuinely writes that file.
3. **Per-instruction mapping**: for each method, record the exact emitted string and which
   instance variables feed it. Note which setters store vs emit.
4. **State flow**: list every `self.X` a motion line reads, and find where each is
   initialised. Class-level defaults are what the *first* move uses.
5. **Run it.** The `test_post()` at the bottom of most posts is executable
   (`python <post>.py`). Better: replay a real intermediate file (see **Verify**).

When reporting, quote real generated lines rather than describing them abstractly — the
user can check those against their controller manual.

## Writing a new post

1. **Get ground truth for the target syntax before writing code.** Ask for a sample program
   exported from the real controller, or its programming manual. If neither exists, say so
   and write the post against an explicitly stated assumed grammar rather than presenting
   invented syntax as fact. Controller dialects differ in ways that are not guessable
   (argument order, angle convention, whether frames are numbered or inline).

   Sample programs answer what the syntax *is*; the manual answers what it *means* — units,
   ranges, which parameters are modal versus per-line, and the orientation convention. Read
   both. Instructions the samples happen not to use (circular moves and analog outputs are
   the usual gaps) exist only in the manual.

   To search a PDF manual, use `scripts/pdf_text.py` — stdlib only, so it works where the
   built-in PDF reader (needs poppler) and pypdf/fitz are unavailable:

   ```bash
   python scripts/pdf_text.py manual.pdf --find MoveC AO SPEED
   ```

   Decoded text is good enough to locate a section and read its syntax examples, but glyph
   collisions garble the occasional character, so don't quote its prose verbatim.
2. **Agree the mapping first.** Produce the table above filled in with the concrete target
   syntax for each of the 16 instructions, plus the structural answers: file extension, one
   file per program or one combined file, header/footer format, subprogram call syntax,
   decimal precision, line-length or program-length limits, text encoding, and whether
   motion instructions carry coordinates inline or reference separately declared targets.
3. **Emit only what RoboDK asked for.** A post is a translator, not a configurator. If
   RoboDK never calls `setAcceleration`, emit no acceleration line and let the program run
   with whatever the controller is configured for. Three habits to avoid, all of which look
   helpful and all of which silently change machine behaviour:
   - *Priming defaults.* Writing a block of speed/blend/smoothness values at the top of
     every program so it is "self-contained" overrides settings the operator chose.
   - *Filling in neighbours.* Setting deceleration because RoboDK gave you acceleration, or
     circular speed because it gave you linear speed. RoboDK has no such concept, so any
     value you supply is invented.
   - *Decorating.* Extra comments, echoed poses, status messages. A little is useful; a
     line per instruction is noise in a file the operator has to read on a pendant.

   The test: for each line the post can emit, name the RoboDK call that caused it. If there
   isn't one, it probably should not be there.
4. **Start from `assets/post_template.py`** for a genuinely new controller dialect. It is a
   complete, runnable skeleton with every method, correct `__init__` semantics, multi-program
   save handling, and a `test_post()` — a near-verbatim copy of RoboDK's own official sample
   post, so it stays correct as ground truth rather than an invented starting point. Copy it,
   rename, and fill in the emitted strings — don't hand-roll the boilerplate.
5. **Pick the pose conversion deliberately.** See `references/poses-and-units.md`. RoboDK
   gives you a 4×4 homogeneous matrix; which Euler convention you flatten it to is
   controller-specific and silently wrong if guessed.
6. **Keep `test_post()` current** with a program exercising every instruction you changed.

### Small customization of an existing, working post: subclass it

Don't copy the whole post for a request like "add an instruction," "change the reference frame
format," or "cap the speed at 500 mm/s" when a working post for that controller already exists.
RoboDK's own documented pattern is a thin subclass that imports the existing post and overrides
only the method(s) that need to change:

```python
from KUKA_KRC2 import RobotPost as MainPost

class RobotPost(MainPost):
    def setFrame(self, pose, frame_id, frame_name):
        # Optionally fall back to the base implementation for cases you don't want to change:
        # if frame_name != "Frame 4":
        #     return super().setFrame(pose, frame_id, frame_name)
        self.addline('; BASE_DATA[8] = {FRAME: %s}' % self.pose_2_str(pose))
        self.addline('BAS (#BASE,8)')
```

Save it under a **new name** in the Posts folder (e.g. `KUKA_Custom_Post.py`) and select it on
the robot instead of the original. This is smaller, safer (everything not overridden is
guaranteed identical to the working post), and survives a RoboDK update — which brings up the
one hard rule for this whole skill:

**Never edit a post in place inside RoboDK's default `Posts/` folder.** Reinstalling or updating
RoboDK silently resets every default post processor to its shipped version, discarding in-place
edits with no warning. Always save changes — whether a full rewrite or a one-method subclass —
under a new file name, and point the robot at that name.

### Two target models

The template assumes motion lines carry their coordinates inline (`movel([x,y,z,…], …)`).
Many controllers — the Fanuc-descended ones especially — instead **declare targets in a
separate section** and have motion reference them by index:

```
<pos>
P[1]{GP:0,UF:0,UT:1,CFG:[…],LOC:[x,y,z,a,b,c,e1,e2,e3]};   cartesian
P[2]{GP:0,UF:0,UT:1,JNT:[j1…j6,e1,e2,e3]};                 joint
<end>
<program>
L P[1]
J P[2]
```

That changes the post's shape in ways worth planning up front:

- Motion methods **append a point record to a second buffer** and emit only a reference, so
  the class carries `POINTS` alongside `PROG`, and both get stored per program in
  `ProgFinish` and interleaved at save time.
- Point numbering restarts per program when each program is its own file.
- Point records usually **stamp the active frame/tool numbers**, and controllers often
  require the stamped numbers to match the active selection at execution time or they
  alarm. Track the current frame/tool in the post and stamp from that.
- Where a controller supports both a joint and a cartesian record, prefer the **joint**
  record for `MoveJ`. The joint values are exact and already solved, and it sidesteps any
  configuration/turn-number word the cartesian record would need.

## Failure modes that actually bite

- **`pose is None` on a linear or circular move.** When the RoboDK target is a *joint*
  target, `MoveL`/`MoveC` receive `pose=None` and only joints. Guard every pose
  dereference; either emit the joint-space equivalent or log a clear message. `MoveJ`
  frequently gets `pose=None` too — implement `MoveJ` off `joints`, which is always present.
- **First-move defaults.** `setSpeed` and friends are only called when a value *changes*,
  so the very first motion uses the class-level default. A default of `SPEED_MMS = 1` means
  the first linear move in every program is emitted at 1 mm/s. Set defaults to something
  the controller would actually accept — or, if the controller is modal and the value can
  simply be left alone, emit nothing until RoboDK actually asks.
- **Emitting settings RoboDK never mentioned.** See "Emit only what RoboDK asked for"
  above. This is the most common way a technically-correct post annoys the people who have
  to run it, because the generated program quietly overrides the cell's configuration.
- **Mutable class attributes.** `PROG_LIST = []` at class level is shared across instances
  and across generations within one RoboDK session. Re-initialise every list in `__init__`,
  not just `self.PROG`.
- **I/O names are not always integers.** `setDO`/`setAO`/`waitDI` accept symbolic names
  (strings) as well as numbers. Code like `if type(io_value) != int` misclassifies valid
  string I/O. Format with `str()` and handle the non-numeric case.
- **Extra joint values.** `joints` can be longer than `nAxes` when the cell has external
  axes (a 7-value list on a 6-axis robot). Decide explicitly: slice, or emit all.
- **`Pause(time_ms)` with a negative value** means "stop indefinitely / wait for operator",
  not "wait -1 ms". Handle it as a distinct branch.
- **`waitDI(..., timeout_ms=-1)`** means wait forever; a positive value needs the
  controller's timeout syntax.
- **`frame_id` / `tool_id` of `-1` or `None`** mean "not a numbered frame". Controllers that
  require numbered frames need a fallback.
- **`FilterName`** exists because controllers restrict program-name characters and length.
  Use it, and use the *filtered* name consistently in `ProgStart`, `ProgFinish`, `ProgSave`
  and in subprogram calls, or the call won't resolve to its target.
- **Decorating a subprogram name with anything invented.** A file extension, a suffix, a
  changed case — if the string in the call isn't exactly what the controller expects, the
  program fails at run time, not at load time. Take the call syntax from a real exported
  program rather than inferring it from how the post writes files.
- **`PROG_FILES` must be populated in `ProgSave`.** `ProgSendRobot` uploads that list; if
  `ProgSave` never appends to it, "Send program to robot" silently uploads nothing.
- **Editing a post in place inside RoboDK's default `Posts/` folder.** Reinstalling/updating
  RoboDK silently resets every default post to its shipped version, discarding the edit with no
  warning. Always save under a new file name — see **Small customization**, above.
- **A syntactically-correct program still not loading on the controller.** Some vendors need a
  compile/convert step the post can't produce: Panasonic needs G2PC to turn the generated ASCII
  file into a binary the controller reads, and some Fanuc controllers need Roboguide's `maketp`
  utility. A clean diff against a reference program doesn't rule this out — check whether the
  target controller is one of these before declaring success.

## Verify

Prefer regeneration over inspection. From the skill directory:

```bash
python scripts/replay_intermediate.py PostProg2.py --post Siasun.py --out ./out --expect Prog2.spf
```

This rewrites the intermediate file's post path and `ProgSave` call to run against the post
you name, writes the controller program to `--out`, and unified-diffs it against a
known-good reference. Clean diff after an edit means no regression; intended differences
show up as a small, readable patch. Run it before and after every change to an existing
post. `--help` covers the remaining options.

Without an intermediate file, `python <post>.py` runs `test_post()` and prints the program
to stdout — when the post imports cleanly (see the `libspp` caveat above). Details and what to
check by eye: `references/testing.md`.

### Generating through RoboDK instead

When a post can't run standalone, drive it from a station instead — this exercises the real
pipeline, and works headless:

```python
robot.setParam("PostProcessor", "Automata")     # post name, no .py
status = prog.MakeProgram(str(out_dir))
```

Three things to know, all verified on RoboDK 6.0.0:

- **It works fine under `ROBODK_AI=noui`** — a working post generated an 8.6 KB program in 0.3 s
  headless. Headlessness is not a reason for program generation to fail.
- **`MakeProgram` returns a tuple**, e.g. `(True, '', False)` — success is element `0`, not the
  whole value. Don't test the return value directly.
- **It blocks forever if the post raises on import.** With any of the `libspp` posts the call
  never returns and never errors — it hangs inside `_rec_int()` waiting for a reply that isn't
  coming, both headless *and* windowed. There is no timeout. Run it under a watchdog (subprocess
  with a timeout, or a thread you can abandon) rather than calling it inline, or a single bad post
  hangs the whole session.

If `python` isn't on PATH, RoboDK ships its own interpreter with `robodk` already installed
— typically `C:\RoboDK\Python-Embedded\python.exe` on Windows (`C:\RoboDK6\...` for a 6.x
install). Use it rather than asking the user to install anything. Note it does **not** carry
`libspp` either, so it does not rescue the posts above.

If `python` isn't on PATH, RoboDK ships its own interpreter with `robodk` already installed
— typically `C:\RoboDK\Python-Embedded\python.exe` on Windows. Use it rather than asking the
user to install anything.

## Bundled files

- `references/robotpost-api.md` — every method signature, argument semantics, `None` cases,
  class attributes and conventions. Read before writing or auditing methods.
- `references/poses-and-units.md` — units, the 4×4 pose, Euler conventions per controller
  family, conversion helpers, manual fallback.
- `references/testing.md` — the verification loop in detail.
- `assets/post_template.py` — runnable skeleton for a new post.
- `scripts/replay_intermediate.py` — regenerate + diff harness.
- `scripts/pdf_text.py` — stdlib PDF text search, for mining vendor manuals.
