# RoboDK API cheat sheet for Add-ins

The full reference is at <https://robodk.com/doc/en/PythonAPI/robodk.html#robolink-py>.
This page covers the parts Add-in actions reach for constantly, with the exact
signatures from `robodk/robolink.py`.

```python
from robodk import robolink, robomath, robodialogs
RDK = robolink.Robolink()   # attaches to the running RoboDK instance
```

`Robolink()` connects to the RoboDK that launched the action, so there is nothing
to configure. Creating it is cheap but not free — make one per process and pass
it around rather than constructing it in every helper.

## Contents

- [Finding items](#finding-items)
- [Selection](#selection)
- [Messages and dialogs](#messages-and-dialogs)
- [Station parameters](#station-parameters)
- [Creating and modifying items](#creating-and-modifying-items)
- [Item properties](#item-properties)
- [Poses and math](#poses-and-math)
- [Robots, programs and motion](#robots-programs-and-motion)
- [Rendering and performance](#rendering-and-performance)
- [Stations](#stations)
- [Constants](#constants)

## Finding items

```python
RDK.Item(name, itemtype=None) -> Item          # by name; check .Valid() before using
RDK.ItemList(filter=None, list_names=False)    # all items, optionally of one type
RDK.ItemUserPick(message='Pick one item', itemtype_or_list=None) -> Item
```

`Item()` never raises for a missing name — it returns an invalid item, so guard
it:

```python
robot = RDK.Item('UR5e', robolink.ITEM_TYPE_ROBOT)
if not robot.Valid():
    RDK.ShowMessage('No robot named UR5e in this station.', True)
    return
```

Passing `itemtype` matters when names collide across types (a frame and a target
can share a name).

## Selection

Context-menu and double-click actions receive their input this way:

```python
RDK.Selection() -> List[Item]
RDK.setSelection(list_items=[])          # [] clears the selection
```

## Messages and dialogs

```python
RDK.ShowMessage(message, popup=True)     # popup=False writes to the status bar
```

Use `popup=False` for progress inside a loop — a modal popup every iteration is
unusable. For input, use `robodk.robodialogs` (see
[actions.md](actions.md#dialogs)).

## Station parameters

Station parameters are the Add-in's key/value store. They live in the `.rdk`
file, so they follow the station and survive restarts, and they are how separate
action processes communicate.

```python
RDK.getParam(param='PATH_OPENSTATION', str_type=True)
RDK.setParam(param, value)
```

Useful built-ins: `PATH_OPENSTATION` (folder of the open station),
`FILE_OPENSTATION` (full path), `PATH_ROBODK` (install folder),
`PATH_DESKTOP`, `PYTHON_EXEC` (the interpreter RoboDK uses).

For structured settings prefer `roboapps.AppSettings`, which wraps this and adds
a UI.

`Item.setParam(param, value)` / `Item.getParam(param)` do the same per item and
also expose item-specific commands.

## Creating and modifying items

```python
RDK.AddFile(filename, parent=0) -> Item        # .stl, .step, .robot, .rdk, ...
RDK.AddFrame(name, itemparent=0) -> Item
RDK.AddTarget(name, itemparent=0, itemrobot=0) -> Item
RDK.AddProgram(name, itemrobot=0) -> Item
RDK.AddStation(name='New Station') -> Item
RDK.Delete(item_list)                          # one item or a list — one call is much faster
RDK.Copy(item, copy_childs=True); RDK.Paste(paste_to=0, paste_times=1)
RDK.Save(filename, itemsave=0)
```

Geometry: `RDK.AddShape(triangle_points, ...)`, `RDK.AddCurve(curve_points, ...)`,
`RDK.AddPoints(points, ...)`, `RDK.ProjectPoints(points, object_project, ...)`.

## Item properties

```python
item.Name(); item.setName(name)
item.Valid(check_deleted=False)
item.Type()                                    # ITEM_TYPE_* constant
item.Parent(); item.setParent(parent); item.Childs()
item.Visible(); item.setVisible(visible, visible_frame=None)
item.Color(); item.setColor([r, g, b, a])      # components 0..1
item.Delete()
```

`setParent` preserves the item's *relative* pose; use `setParentStatic` when you
want it to stay where it is in absolute terms.

## Poses and math

Poses are 4x4 `robomath.Mat` homogeneous matrices. Distances are millimetres,
angles radians in the API (degrees in the UI).

```python
item.Pose(); item.setPose(pose)                # relative to the parent
item.PoseAbs(); item.setPoseAbs(pose)          # relative to the station origin
item.setGeometryPose(pose, apply=False)        # moves the mesh inside the object

from robodk.robomath import (transl, rotx, roty, rotz, Pose,
                             Pose_2_TxyzRxyz, TxyzRxyz_2_Pose,
                             Pose_2_KUKA, KUKA_2_Pose, distance, pause)

pose = transl(100, 0, 300) * rotz(robomath.pi / 2)
x, y, z, rx, ry, rz = Pose_2_TxyzRxyz(pose)
```

## Robots, programs and motion

```python
robot.Joints(); robot.setJoints(joints)
robot.getLink(robolink.ITEM_TYPE_TOOL)         # active tool; also FRAME, ROBOT
robot.setPoseTool(tool); robot.PoseTool()
robot.MoveJ(target, blocking=True)
robot.MoveL(target, blocking=True)

prog.RunInstruction(code, run_type=robolink.INSTRUCTION_CALL_PROGRAM)
prog.Pause(time_ms=-1)
prog.setDO(io_var, io_value)
prog.InstructionList()                         # instructions as a matrix
prog.Update(check_collisions=robolink.COLLISION_OFF, timeout_sec=3600)
prog.InstructionCount(); prog.Instruction(index)

RDK.setRunMode(robolink.RUNMODE_SIMULATE)
RDK.RunProgram(fcn_param, wait_for_finished=False)
```

`Update()` on a program returns `(valid_instructions, program_time,
program_distance, valid_ratio, readable_msg)` — the basis for cycle-time and
reachability tools.

Wrap moves that can fail: `MoveJ`/`MoveL` raise `robolink.TargetReachError` when
the robot cannot get there, and `Item.Valid()` will not warn you in advance.

## Rendering and performance

```python
RDK.Render(always_render=False)                # False suspends redraws, True resumes+redraws
RDK.Update()
RDK.setSimulationSpeed(speed); RDK.SimulationSpeed(); RDK.SimulationTime()
```

Bulk edits are dominated by redraw cost. Bracket them:

```python
RDK.Render(False)
try:
    for item in items:
        item.setVisible(False)
finally:
    RDK.Render(True)      # always restore, or the UI stays frozen after an error
```

Similarly, prefer `RDK.Delete(list_of_items)` over deleting one at a time, and
`RDK.ItemList(type)` over repeated `RDK.Item(name)` lookups.

## Stations

```python
RDK.ActiveStation(); RDK.setActiveStation(stn)
RDK.getOpenStations()
RDK.CloseStation()
```

Actions run against whatever station is active at launch. If yours takes a while,
capture `RDK.ActiveStation()` at the start rather than assuming it stays put.

## Constants

Item types (`ITEM_TYPE_*`) are listed with their numeric values in
[appconfig.md](appconfig.md#item-type-numbers-for-typeoncontextmenu--typeondoubleclick),
since `AppConfig.ini` needs the numbers.

Run modes:

| Constant | Meaning |
| --- | --- |
| `RUNMODE_SIMULATE` | Simulate the motion (default) |
| `RUNMODE_QUICKVALIDATE` | Fast validation, no motion |
| `RUNMODE_MAKE_ROBOTPROG` | Generate the robot program |
| `RUNMODE_MAKE_ROBOTPROG_AND_UPLOAD` | Generate and upload |
| `RUNMODE_MAKE_ROBOTPROG_AND_START` | Generate, upload and start |
| `RUNMODE_RUN_ROBOT` | Drive the real robot |

Window states: `WINDOWSTATE_HIDDEN`, `_SHOW`, `_MINIMIZED`, `_NORMAL`,
`_MAXIMIZED`, `_FULLSCREEN`, `_CINEMA`, `_FULLSCREEN_CINEMA`, `_VIDEO`.

## Escape hatch

`RDK.Command(cmd, value='', skip_result=False)` sends a command straight to
RoboDK and reaches settings with no dedicated wrapper (for example
`RDK.Command('Trace', 'On')`). Handy, but undocumented commands can change
between versions — prefer a typed API when one exists.
