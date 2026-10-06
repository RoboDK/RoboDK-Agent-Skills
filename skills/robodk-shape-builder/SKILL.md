---
name: robodk-shape-builder
description: Build parametric RoboDK visual components — primitives (box, sphere, cone), fixtures (table, pedestal, fence), and mechanisms (conveyor, linear rail, T-bot/H-bot gantry, 1/2/3-axis turntable/positioner) — using RoboDK's own bundled Components Add-in library instead of hand-rolled mesh geometry. Use whenever a station needs one of these shapes; prefer this over generating raw triangle meshes for anything it covers.
version: 1.1.0
author: RoboDK
license: Proprietary — All Rights Reserved, Copyright RoboDK Global, SLU (see LICENSE.md in this skill folder; NOT MIT like the rest of this repo)
platforms: [linux, windows, macos]
metadata:
  tags: [robodk, geometry, mechanisms, station-building, components]
  category: software-development
  related_skills: [robodk-api, robodk-station-audit]
---

# RoboDK Shape Builder

## Overview

Bundles `shapetools.py` — the library behind RoboDK's own **Components Add-in** (formerly the
"Shape Add-in") — under `assets/shapetools/`, so an agent can call it directly instead of
hand-rolling triangle meshes for common shapes and fixtures. It already implements the
frame-based positioning convention correctly: every `Create*` function creates its own
`"<name> Frame"`, parents every child shape under it, parents that frame under the
`parent_frame` you pass in, and returns `(frame, object_or_robot)` — so the *only* thing you ever
move to reposition a whole component is that returned frame's `setPose(...)`, and
`object_or_robot` is the actual object/mechanism item to drive (`setJoints`, `SolveFK`, ...) —
see API Reference below.

**License note, read before extending this skill:** this whole skill folder — the vendored
`shapetools.py` and its `models/*.sld` assets included — is © RoboDK Global, SLU,
**All Rights Reserved**; see `LICENSE.md` in this folder. That is different from the rest of this
repo (MIT) and from `robodk-api`'s bundled SDK (Apache-2.0). It was vendored deliberately, with
that distinction understood, from `Apps-Private/Public/Shape` — don't assume it's fine to
redistribute elsewhere just because the rest of Agent-Skills is MIT.

## When to Use

Use whenever a station needs any of:

- **Primitives:** box/cube, sphere, cone (or a plain cylinder — a cone with equal top/bottom radius).
- **Fixtures:** table, tiered pedestal, safety fencing.
- **Mechanisms** (optionally built as real, drivable RoboDK mechanisms via `create_mechanism=True`):
  conveyor, linear rail, T-bot gantry (2–3 DOF), H-bot gantry (3 DOF), 1/2/3-axis
  turntable/positioner.

Prefer this over hand-rolled triangle meshes for anything in that list — it produces proper solid
geometry (not low-poly hand-rolled meshes) and already gets frame-based positioning right. Fall
back to generating raw meshes with `RDK.AddShape()` only for bespoke geometry none of these
functions cover (e.g. a custom-shaped machine housing).

## Setup

```python
import sys
# Prepend robodk-api's BUNDLED copy so ITS `robodk` package wins over any pip-installed one.
# This matters more here than anywhere else: shapetools.py does its own
# `from robodk import robolink, robomath` internally, so if the bundled directory is not first
# on sys.path, shapetools loads a DIFFERENT copy than your script does -- two unrelated
# Robolink/Mat classes with the same names, passed across the boundary with no error. Verified.
# The features these skills rely on landed in 6.0.2: 6.0.1 and earlier have no
# `Robolink.__enter__`/`__exit__`, so `with robolink.Robolink() as RDK:` raises TypeError there.
sys.path.insert(0, "<robodk-api skill path>/assets/robodk-api")  # e.g. ~/.claude/skills/robodk-api/assets/robodk-api
sys.path.insert(0, "<this skill's path>/assets/shapetools")  # e.g. ~/.claude/skills/robodk-shape-builder/assets/shapetools
from robodk import robolink, robomath
import shapetools  # picks up the same bundled robodk package via its own `from robodk import ...`

with robolink.Robolink() as RDK:
    ...  # build with the Create* functions below
```

Set the `ROBODK_AI` environment variable before running, rather than passing launch args by hand
(see `robodk-api`'s "Connect" section and `references/headless-testing.md`): `ROBODK_AI=noui` by
default — a screenshot is not a required deliverable for building components, only take one if
the user explicitly asked to see it — or `ROBODK_AI=snapshot` when a screenshot IS wanted this
run (**on Windows `-HIDDEN` renders blank — use a visible instance for screenshots there**; see
`robodk-api`'s `references/headless-testing.md`)
(decide up front: a running `noui` instance can't be switched to real rendering later, see
`robodk-api`'s `references/headless-testing.md`). `ROBODK_AI=noui` implies `-NEWINSTANCE`, so `Robolink()` always launches
its own dedicated RoboDK process — it never attaches to, or interferes with, an already-open
instance the user might have on screen.

Every `Create*` function already checks for `-NOUI` in `RDK.ARGUMENTS` on your `RDK` connection
and skips its final `"Reframe"`/`"FitAll"` view-fitting calls in that case — those only affect a
viewport that doesn't exist under `-NOUI`, so this saves two no-op API round-trips per shape with
no action needed on your part.

**Skip `RDK.CloseStation()` + `RDK.AddStation(...)` when you just launched a fresh
`-NEWINSTANCE`.** A brand-new instance already opens with an empty default station — those two
calls are redundant round-trips in that case (each is a full extra client/server exchange). Only
call them when reusing an *existing* connection across multiple build iterations in the same
process — `RDK.CloseStation()` + `RDK.AddStation(name)` between iterations.

**Do not call `shapetools.new_robolink()`.** It's written for the add-in's own standalone/GUI-
triggered execution (only sets `-NOUI`/`-NEWINSTANCE` on Linux, doesn't read `ROBODK_AI`, no
`-HIDDEN`) — connect the normal agent way shown above instead, then just call the
`Create*` functions against your own `RDK`.

**`pymeshlab` is a hard import-time dependency**, even though it's only actually used inside
`CreateCone`'s non-equal-radius branch — `shapetools.py` unconditionally calls
`robolink.import_install('pymeshlab')` at module load, so `import shapetools` fails outright if
it's missing and can't be installed on the fly. Install it ahead of time:

```bash
pip install pymeshlab
```

Don't rely on the auto-installer succeeding — verified broken in this session (the currently
installed `robodk` package's `import_install` passes `subprocess.Popen` a command *string*
without `shell=True`, where `Popen` expects a list; it may throw `FileNotFoundError` instead of
installing anything). If `import shapetools` fails on `pymeshlab`, install it manually first.

## API Reference

Every function below takes `(RDK, name, ..., color(s), parent_frame, ...)` and returns
**`(frame, object_or_robot)`** — always unpack both.

**`parent_frame` must be a real `Item` — `0` does not mean "station root" here.** RoboDK's own
API uses `itemparent=0` for the station root (`RDK.AddFrame(name, 0)`), so passing `0` is a
natural mistake; in these functions it raises
`Invalid item provided: The item identifier provided is not valid or it does not exist` from an
internal `frame.setParent(parent_frame)`. Verified. Pass `RDK.ActiveStation()` to park a component
at the station root, or better, a frame you made with `RDK.AddFrame(...)`.

**The signatures in the table are complete** — every positional argument shown without a default
is required. Don't infer a shorter call from the shape of a similar function: the gantries and
multi-axis positioners take a lot of required geometry (`CreateTbot` takes 20 required arguments
after `RDK`, `CreateHbot` 27), and omitting one raises
`TypeError: ... missing N required positional arguments` rather than falling back to a default.
Realistic values for every one of them are in the vendored file's `if __name__ == '__main__':`
block (`assets/shapetools/shapetools.py`) — copy from there rather than guessing dimensions.

- `frame` — position the whole component with `frame.setPose(...)`, never touch a child item's
  pose directly. For a `create_mechanism=True` build, `frame` IS that mechanism's base item (not
  a plain frame) but still repositions the whole assembly the same way via `setPose(...)`.
- `object_or_robot` — the actual object item (non-mechanism build) or the actual
  mechanism/robot item (`create_mechanism=True`) — e.g. `object_or_robot.setJoints([...])`,
  `object_or_robot.SolveFK(...)`. **Use this**, not `frame`, whenever you need to drive or query
  the mechanism's kinematics; `frame` itself is a different item (its own base) and does not
  expose `setJoints`/`SolveIK`/etc. — calling those on `frame` fails with a generic "Invalid item
  provided" that gives no hint the real problem is "wrong item, not missing item." Before this
  return contract existed, getting the actual mechanism item required guessing its name and a
  separate `RDK.Item(name, robolink.ITEM_TYPE_ROBOT)` lookup — this is that lookup, done for you.
  `CreateFence` returns `(None, None)` if `sides` selects no sides and `include_floor=False` (no
  geometry to build). `CreateTurntable3` returns a 3-tuple, `(frame, object_or_robot, sc_folder)`
  — see its row below.

| Function | Produces |
|---|---|
| `CreateCube(RDK, name, x, y, z, color, parent_frame, is_prism=False)` | A box (or a prism if `is_prism=True`), size `x`×`y`×`z`. |
| `CreateSphere(RDK, name, radius, color, parent_frame)` | A sphere. |
| `CreateCone(RDK, name, r_bottom, r_top, height, quality, color, parent_frame)` | A cone; a plain cylinder (fast prefab) when `r_bottom == r_top`, otherwise a generated mesh via `pymeshlab` at `quality` subdivisions. |
| `CreateTable(RDK, name, table_x, table_y, table_h1, leg_radius, leg_height, main_color, table_color, parent_frame, simple=False)` | A 4-legged table. Also returns a nested `"<name> Plane Frame"` positioned exactly at tabletop height — use that (not the main frame) to place things on top. |
| `CreatePedestal(RDK, name, r1, h1, r2, h2, r3, h3, color, parent_frame, rounded=False)` | A 3-tier stepped or rounded pedestal. Also returns a nested `"<name> Plane Frame"` at the top surface. |
| `CreateConveyor(RDK, name, cnv_x, cnv_y, cnv_r, main_color, parent_frame, frame_width=None, frame_height=None, frame_color=None, simple_geometry=False, panel_color=None, create_mechanism=False)` | A belt (rollers + plane), optionally with a frame/legs/side panels. `create_mechanism=True` builds a real 1-DOF linear mechanism you can drive with `setJoints([0..cnv_x])`. |
| `CreateFence(RDK, name, panel_size, panels_x, panels_y, height, main_color, panel_color, floor_color, parent_frame, sides=(True,True,True,True), include_floor=False, frame_name=None)` | Safety fencing, per-side toggle (`sides` = which of the 4 sides get built), optional floor panel. |
| `CreateRail(RDK, name, rail_x, rail_y, rail_z, rail_x_cr, rail_y_cr, rail_z_cr, rail_zero, rail_llim, rail_ulim, main_color, carriage_color, cover_color, parent_frame, seg_n=None, seg_sz=None, create_mechanism=False)` | A linear rail + carriage. `create_mechanism=True` builds a real 1-DOF mechanism (an external axis, e.g. to mount a robot on). |
| `CreateTbot(RDK, name, tbot_x, tbot_y, tbot_z, tbot_cr_x, tbot_cr_y, tbot_cr_z, tbot_beam2_x, tbot_beam2_y, tbot_beam2_z, tbot_zero, tbot_llim, tbot_ulim, tbot_beam2_zero, tbot_beam2_llim, tbot_beam2_ulim, main_color, carriage_color, beam2_color, parent_frame, leg_n=None, leg_sz=None, seg_n=None, seg_sz=None, create_mechanism=False)` | A 2–3 DOF T-shaped gantry (X beam + optional Z beam2). See the module's `__main__` block for a fully-worked parameter example. |
| `CreateHbot(RDK, name, hbot_bm1_x, hbot_bm1_y, hbot_bm1_z, hbot_bm2_x, hbot_bm2_y, hbot_bm2_z, hbot_bm3_x, hbot_bm3_y, hbot_bm3_z, hbot_cr_x, hbot_cr_y, hbot_cr_z, hbot_bm1_zero, hbot_bm1_llim, hbot_bm1_ulim, hbot_bm2_zero, hbot_bm2_llim, hbot_bm2_ulim, hbot_bm3_zero, hbot_bm3_llim, hbot_bm3_ulim, main_color, beam_y_color, beam_z_color, carriage_color, parent_frame, with_sides=False, leg_n=None, leg_sz=None, seg_n=None, seg_sz=None, create_mechanism=False)` | A 3 DOF H-bot gantry (X + Y + Z). |
| `CreateTurntable(RDK, name, radius, height, base_color, flange_color, parent_frame, with_base=True, horizontal=False, horizontal_cp=False, cp_dist=0, tt_llim=0, tt_ulim=360, create_mechanism=False)` | A 1-axis positioner/turntable. |
| `CreateTurntable2(RDK, name, radius, height, arm_length, vertical_offset, cp_dist, base_color, beam_color, flange_color, parent_frame, with_base=True, with_cp=False, tl_llim=0, tl_ulim=360, trn_llim=0, trn_ulim=360, create_mechanism=False)` | A 2-axis tilt-turn positioner. |
| `CreateTurntable3(RDK, name, radius, height, arm_length, vertical_offset, base_color, beam_color, flange_color, parent_frame, tl_llim=0, tl_ulim=360, trn_llim=0, trn_ulim=360, create_mechanism=False, create_scripts=False)` | A 3-axis positioner (dual-flange). `create_scripts=True` also imports `scripts/side_1.py`/`side_2.py` — example robot-link-switching scripts for driving a robot from whichever flange is active. Returns a **3-tuple** `(frame, object_or_robot, sc_folder)` — `sc_folder` is the folder item holding the two imported scripts (`None` unless `create_scripts=True`). |
| `get_bb(item)` | `item.setParam("BoundingBox", "Relative")`, parsed — the object's local-frame bounding box `[x, y, z]` size. For an absolute/world bounding box instead, combine this with the item's own pose. |
| `SaveItemOnFrame(frame)` | Saves the first child under a returned frame to a temp `.sld` (object) or `.robot` (mechanism) file and returns the path — useful for turning a built component into a reusable library asset. |

Full worked examples for every function (realistic parameter values) are in the vendored file's
own `if __name__ == '__main__':` block: `assets/shapetools/shapetools.py`.

## Example

```python
parent = RDK.AddFrame("Components")
parent.setPose(robomath.eye(4))

main_color = [1/255, 51/255, 86/255, 1.0]
gray = [168/255, 176/255, 181/255, 1.0]

table_frame, table_obj = shapetools.CreateTable(
    RDK, "Infeed Table", table_x=1000, table_y=600, table_h1=20,
    leg_radius=35, leg_height=750, main_color=main_color, table_color=gray,
    parent_frame=parent,
)
# Reposition the WHOLE table with one call — never touch its child items directly:
table_frame.setPose(robomath.transl(-700, 500, 0))

# "<name> Plane Frame" sits exactly at tabletop height — parent things you place on top to it,
# not to the table frame itself, so their local Z can stay 0 instead of table_h1 + leg_height.
plane = RDK.Item("Infeed Table Plane Frame")

# A create_mechanism=True build's second return value is the real mechanism/robot item —
# drive it directly, no separate RDK.Item(name, ITEM_TYPE_ROBOT) lookup needed:
rail_frame, rail_mech = shapetools.CreateRail(
    RDK, "Track 1", rail_x=4000, rail_y=600, rail_z=300,
    rail_x_cr=500, rail_y_cr=400, rail_z_cr=50,
    rail_zero=2000, rail_llim=-1800, rail_ulim=1800,
    main_color=main_color, carriage_color=gray, cover_color=gray,
    parent_frame=parent, create_mechanism=True,
)
rail_mech.setJoints([500])

# Mount a robot to ride the mechanism: setParent (NOT setParentStatic) snaps the
# robot's base onto the mechanism's tip and keeps it tracking every future
# setJoints(...) call automatically -- see Common Pitfall #4.
robot = RDK.AddFile(robot_path)
robot_base = robot.Parent()
robot_base.setParent(rail_mech)
robot.setPoseFrame(parent)  # world-space poses/targets now resolve correctly
rail_mech.setJoints([1200])  # robot_base.PoseAbs() moves along with this
```

## Common Pitfalls

1. **Missing `pymeshlab` at import time.** See Setup above — install it manually; don't trust
   the auto-installer.
2. **Calling `shapetools.new_robolink()`.** Wrong connection convention for agent use (no
   `-NEWINSTANCE`-first ordering, no `-HIDDEN`, `-NOUI` only on Linux). Connect the
   normal way shown in **Setup** above and call the `Create*` functions against that connection instead.
3. **Calling `setJoints`/`SolveIK`/etc. on the returned `frame` instead of `object_or_robot`.**
   For a `create_mechanism=True` build, `frame` is the mechanism's *base* item (the plain frame
   gets deleted and replaced) — still repositionable with `setPose(...)`, but it does not expose
   joint/kinematics methods. `object_or_robot` (the function's second return value) is the actual
   mechanism/robot item to drive.
4. **Mounting a robot on a mechanism's `object_or_robot` item so it "rides" the mechanism (e.g.
   a robot on a `CreateRail`/`CreateTbot`/`CreateHbot` external axis).** Use
   `robot_base.setParent(mechanism_item)` — **plain `setParent`, not `setParentStatic`** — where
   `robot_base = robot.Parent()`. This snaps the robot's base onto the mechanism's tip and keeps
   it correctly tracking the mechanism's own `setJoints(...)` automatically (verified this
   session: `robot_base.PoseAbs()` after `setParent` moves by exactly the mechanism's joint delta
   on every axis) — no manual per-move frame-sync helper needed, and no need to probe the
   mechanism's joint→world formula yourself.

   An earlier version of this pitfall claimed nesting a robot under a mechanism breaks
   `SolveIK`/`MoveL` outright, even for `SolveIK(robot.Pose())` on the robot's own current pose.
   Re-tested and traced to ground: that failure was the *same* missing-reference bug described in
   `robodk-api`'s "Connect" pitfalls, not a mechanism-parenting limitation — `SolveIK` requires
   the pose to already be flange-relative-to-robot-base unless you pass `tool=`/`reference=`
   explicitly, and a robot mounted anywhere off world-identity (mechanism-parented or not) trips
   this the same way. Once nested via `setParent`, `robot.SolveIK(...)` and live
   `robot.MoveJ(...)`/`MoveL(...)` calls work fine as long as you follow the same rules any
   off-origin robot needs: call `robot.setPoseFrame(a_world_frame)` once so Cartesian pose Mats
   are interpreted in that frame, and if calling `SolveIK` directly (not through `MoveJ`/`MoveL`),
   pass `tool=robot.PoseTool()` and `reference=robomath.invH(robot_base.PoseAbs())` explicitly.

   **One separate, real caveat remains, unrelated to parenting:** a tool held at a constant
   vertical orientation with no roll variation pins a 6-axis wrist at its singular alignment
   (e.g. a UR-style robot's joint 5 sitting at exactly 90°) for an entire multi-point path, and
   `MoveJ`'s nearest-branch-to-current-joints search can then refuse an individual waypoint that
   is still trivially reachable in isolation. If a live verification walk needs to visit several
   such waypoints in sequence, drive it with explicit `SolveIK(pose, tool=.., reference=..)` +
   `robot.setJoints(solution)` per waypoint instead of relying on `MoveJ`/`MoveL` continuity —
   this applies whether the robot rides a mechanism or sits on a plain frame, so don't mistake it
   for a mechanism-mounting problem when it shows up.
5. **Redistributing the vendored assets.** They're proprietary (© RoboDK Global, SLU, All Rights
   Reserved) — see the License note above. Don't copy `assets/shapetools/` elsewhere without the
   same consideration given to vendoring it here.
6. **Assuming every possible shape/fixture is covered.** This library is comprehensive but not
   unlimited — for something genuinely bespoke, generate the mesh yourself with
   `RDK.AddShape()` rather than trying to force-fit one of these functions.

## Verification Checklist

- [ ] `import shapetools` succeeds (implies `pymeshlab` is importable, even if this build never
      uses `CreateCone`'s non-equal-radius path).
- [ ] Each `Create*` call's returned `(frame, object_or_robot)` are both `.Valid()`.
- [ ] Repositioning a component only ever calls `frame.setPose(...)` — never a child item's pose,
      and never regenerates geometry to move something.
- [ ] For `create_mechanism=True` components, drive `object_or_robot.setJoints(...)` (not
      `frame`) — confirm it's a valid robot/mechanism item (`RDK.list_items --item-type robot`
      will show it).
- [ ] If a robot is meant to ride the mechanism (mounted on a rail/gantry/turntable), its base is
      parented directly under `object_or_robot` via `robot_base.setParent(object_or_robot)` (not
      `setParentStatic`), and `robot.setPoseFrame(...)` is set to a world/station frame so
      Cartesian moves resolve correctly (see Common Pitfall #4).
