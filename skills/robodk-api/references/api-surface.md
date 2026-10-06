# RoboDK API surface (Python names)

Extracted from [`robolink.py`](https://github.com/RoboDK/RoboDK-API/blob/master/Python/robodk/robolink.py)
and [`robomath.py`](https://github.com/RoboDK/RoboDK-API/blob/master/Python/robodk/robomath.py),
the reference implementation. Method names carry over to every other language except the C#/API
NuGet package (PascalCase) — see `language-notes.md`. This is a scan of signatures for
orientation, not a full argument reference; read the actual docstring in `robolink.py`/
`robomath.py` before relying on an edge case (default values, `None` semantics, blocking
behavior).

Shown as bare names below for brevity. With the recommended `from robodk import robolink,
robomath` import style (see `language-notes.md`), prefix the module-level constants and free
functions as `robolink.X` / `robomath.X` — e.g. `robolink.ITEM_TYPE_ROBOT`, `robomath.Pose(...)`.
`Item`/`Mat` **instance** methods (`item.Pose()`, `robot.MoveJ(...)`) never need a prefix.

## Constants

- **Item types** (`ITEM_TYPE_*`): `STATION, ROBOT, FRAME, TOOL, OBJECT, TARGET, CURVE, PROGRAM,
  INSTRUCTION, PROGRAM_PYTHON, MACHINING, BALLBARVALIDATION, CALIBPROJECT, VALID_ISO9283,
  FOLDER, ROBOT_ARM, CAMERA, GENERIC, ROBOT_AXES, NOTES`.
- **Run modes** (`RUNMODE_*`): `SIMULATE` (1, default), `QUICKVALIDATE` (2),
  `MAKE_ROBOTPROG` (3), `MAKE_ROBOTPROG_AND_UPLOAD` (4), `MAKE_ROBOTPROG_AND_START` (5),
  `RUN_ROBOT` (6, drives the physical robot).
- **Instruction types** (`INS_TYPE_*`): `MOVE, MOVEC, CHANGESPEED, CHANGEFRAME, CHANGETOOL,
  CHANGEROBOT, PAUSE, EVENT, CODE, PRINT, ROUNDING, IO, CUSTOM`.
- **Move types** (`MOVE_TYPE_*`): `JOINT, LINEAR, CIRCULAR, LINEARSEARCH`.
- **Program-call instruction types** (`INSTRUCTION_*`): `CALL_PROGRAM, INSERT_CODE,
  START_THREAD, COMMENT, SHOW_MESSAGE`.
- **Calibration** (`CALIBRATE_*`): `TCP_BY_POINT, TCP_BY_PLANE, TCP_BY_PLANE_SCARA,
  TURNTABLE`, plus frame-calibration methods.
- **Projection** (`PROJECTION_*`): `NONE, CLOSEST, ALONG_NORMAL, ALONG_NORMAL_RECALC,
  CLOSEST_RECALC, RECALC` — used by `AddCurve`/`AddPoints`/`ProjectPoints`.
- **Euler format** (`EULER_*`): `RX_RY_RZ` (Fanuc/KUKA/Motoman/Nachi), `RZ_RY_RX` (CRS),
  `QUEATERNION` (ABB RAPID).
- **Path error flags** (`ERROR_*`): `KINEMATIC, PATH_LIMIT, PATH_SINGULARITY,
  PATH_NEARSINGULARITY, COLLISION` — bitwise-combinable, returned by `MoveJ_Test`/`MoveL_Test`.
- **Window/visibility/flags**: `WINDOWSTATE_*`, `FLAG_ROBODK_*`, `FLAG_ITEM_*`,
  `VISIBLE_ROBOT_*`, `DISPLAY_REF_*`, `SELECT_*`, `SEQUENCE_DISPLAY_*`, `COLLISION_ON/OFF`,
  `SPRAY_ON/OFF`.
- **Exceptions**: `TargetReachError`, `StoppedError`, `InputError`, `LicenseError`.
- **`getLinkableItemTypes(itm_type)`**: free function next to the `ITEM_TYPE_*` constants — returns
  the list of `ITEM_TYPE_*` a given item type can link/parent to (e.g. `ITEM_TYPE_TARGET` ->
  `[ITEM_TYPE_ROBOT]`), empty list if unrestricted. Use this instead of hand-rolling the table.

## `Robolink` (the session — `RDK = Robolink(...)`)

**Connection & lifecycle**
`Connect()`, `Disconnect()`, `Finish()`, `NewLink()`, `isNewInstance()`, `ShowRoboDK()`,
`HideRoboDK()`, `CloseRoboDK()`, `Version()`, `License()`.

**Station / file**
`AddFile(filename, parent=0)`, `Save(filename, itemsave=0)`, `AddStation(name)`,
`CloseStation()`, `getOpenStations()`, `ActiveStation()`, `setActiveStation(stn)`, `Copy(item,
copy_childs=True)`, `Paste(paste_to=0, paste_times=1)`, `Delete(item_list)`.

**Item lookup / tree**
`Item(name, itemtype=None)`, `ItemList(filter=None, list_names=False)`,
`ItemUserPick(message, itemtype_or_list=None)`, `Selection()`, `setSelection(list_items)`.

**Adding items**
`AddShape(triangle_points, add_to=0, override_shapes=False)`, `AddCurve(curve_points,
reference_object=0, add_to_ref=False, projection_type=...)`, `AddPoints(points,
reference_object=0, ...)`, `ProjectPoints(points, object_project, projection_type=..., timeout=30)`,
`AddTarget(name, itemparent=0, itemrobot=0)`, `AddFrame(name, itemparent=0)`,
`AddProgram(name, itemrobot=0)`, `AddMillingProject`/`AddMachiningProject(name, itemrobot=0)`,
`MergeItems(list_items)`.

**Run / simulate**
`setRunMode(run_mode=1)`, `RunMode()`, `RunProgram(fcn_param, wait_for_finished=False)`,
`RunCode(code, code_is_fcn_call=False)`, `RunMessage(message, message_is_comment=False)`,
`Render(always_render=False)`, `Update()`, `setSimulationSpeed(speed)`, `SimulationSpeed()`,
`SimulationTime()`.

**Params & raw commands**
`getParams()`, `getParam(param='PATH_OPENSTATION', str_type=True)`, `setParam(param, value)`,
`Command(cmd, value='', skip_result=False)` — the escape hatch for RoboDK features with no
dedicated method.

**Collisions**
`setCollisionActive(check_state=COLLISION_ON)`, `setCollisionActivePair(check_state, item1,
item2, id1=0, id2=0)`, `setCollisionActivePairList(...)`, `CollisionActivePairList()`,
`Collisions()`, `Collision(item1, item2)`, `CollisionItems()`, `CollisionPairs()`,
`Collision_Line(p1, p2, ref=None)`, `IsInside(object_inside, object)`.

**Batch poses / joints**
`setPoses(items, poses)`, `setPosesAbs(items, poses)`, `Joints(robot_item_list)`,
`setJoints(robot_item_list, joints_list)`.

**Calibration**
`CalibrateTool(poses_xyzwpr, input_format=EULER_RX_RY_RZ, algorithm=CALIBRATE_TCP_BY_POINT,
robot=None, tool=None)`, `CalibrateReference(joints_points, method=..., use_joints=False,
robot=None)`, `LaserTracker_Measure(estimate, search=False)`, `MeasurePose(target=-1,
time_avg_ms=0, tip_xyz=None)`.

**Programs / offline generation**
`ProgramStart(programname, folder='', postprocessor='', robot=None)`.

**View / UI**
`setWindowState(windowstate=WINDOWSTATE_NORMAL)`, `setViewPose(pose)`, `ViewPose()`,
`ShowMessage(message, popup=True)`, `ShowSequence(matrix, display_type=..., timeout=-1)`,
`setFlagsRoboDK(flags=FLAG_ROBODK_ALL)`, `setFlagsItem(item, flags=FLAG_ITEM_ALL)`,
`getFlagsItem(item)`, `setInteractiveMode(mode_type=SELECT_MOVE, ...)`,
`CursorXYZ(x_coord=-1, y_coord=-1)`, `GetPoints(feature_type=FEATURE_HOVER_OBJECT_MESH)`.

**Mechanism / geometry construction**
`BuildMechanism(type, list_obj, parameters, joints_build, joints_home, joints_senses,
joints_lim_low, joints_lim_high, base=eye(4), tool=eye(4), name=..., robot=None)`.

**Cameras & spray simulation**
`Cam2D_Add(item_object=None, cam_params='', camera_item=None)`, `Cam2D_Snapshot(...)`,
`Cam2D_Close(...)`, `Cam2D_SetParams(...)`, `Spray_Add(...)`, `Spray_SetState(...)`,
`Spray_GetStats(...)`, `Spray_Clear(...)`.

**Plugins / embedding**
`PluginLoad(plugin_name='', load=1)`, `PluginCommand(plugin_name, plugin_command='',
value='')`, `EmbedWindow(window_name, docked_name=None, size_w=-1, size_h=-1, pid=0,
area_add=1, area_allowed=15, timeout=500)`.

## `Item` (a node in the station tree)

**Identity & tree**
`equals(item2)`, `RDK()`, `Type()`, `Name()`, `setName(name)`, `Valid(check_deleted=False)`,
`Parent()`, `Childs()`, `setParent(parent)`, `setParentStatic(parent)`, `AttachClosest(keyword='',
tolerance_mm=-1, list_objects=[])`, `DetachClosest(parent=0)`, `DetachAll(parent=0)`,
`Copy(copy_children=True)`, `Paste()`, `AddFile(filename)`, `Save(filename)`, `Delete()`.

**Visibility & appearance**
`Visible()`, `setVisible(visible, visible_frame=None)`, `Recolor(tocolor, fromcolor=None,
tolerance=None)`, `setColor(tocolor)`, `setColorShape(tocolor, shape_id)`,
`setColorCurve(tocolor, curve_id=-1)`, `Color()`, `Scale(scale, pre_mult=None, post_mult=None)`,
`ShowInstructions(show=True)`, `ShowTargets(show=True)`.

**Pose & geometry**
`setPose(pose)` / `Pose()` (local), `setPoseAbs(pose)` / `PoseAbs()` (world), `PoseWrt(item)`,
`setGeometryPose(pose, apply=False)` / `GeometryPose()`, `AddGeometry(fromitem, pose)`,
`AddShape(triangle_points)`, `AddCurve(curve_points, add_to_ref=False, projection_type=...)`,
`AddPoints(points, ...)`, `ProjectPoints(points, projection_type=...)`, `GetCurves()`,
`GetPoints(feature_type=FEATURE_SURFACE, feature_id=0)`, `SelectedFeature()`, `Collision(item)`,
`IsInside(object)`, `setValue(varname, value=None)`.

**Target / joints**
`setAsCartesianTarget()`, `setAsJointTarget()`, `isJointTarget()`, `Joints()` / `setJoints(joints)`,
`SimulatorJoints()`, `JointPoses(joints=None)`, `JointsHome()` / `setJointsHome(joints)`,
`JointLimits()` / `setJointLimits(lower, upper)`, `JointsConfig(joints)`.

**Tool & frame**
`PoseTool()` / `setPoseTool(tool)`, `PoseFrame()` / `setPoseFrame(frame)`, `Tool()`, `Frame()`,
`Htool()` / `setHtool(tool)`, `setTool(tool)`, `setFrame(frame)`, `AddTool(tool_pose,
tool_name='New TCP')`, `setRobot(robot=None)`, `getLink(type_linked=ITEM_TYPE_ROBOT)`,
`getLinks(type_linked=...)`, `setLink(item)`, `ObjectLink(link_id=0)`.

**Motion**
`MoveJ(target, blocking=True)`, `MoveL(target, blocking=True)`, `MoveC(target1, target2,
blocking=True)`, `SearchL(target, blocking=True)`, `MoveJ_Test(j1, j2, minstep_deg=-1)`,
`MoveJ_Test_Blend(j1, j2, j3, blend_deg=5, minstep_deg=-1)`, `MoveL_Test(j1, pose,
minstep_mm=-1)`, `SolveFK(joints, tool=None, reference=None)`, `SolveIK(pose,
joints_approx=None, tool=None, reference=None)`, `SolveIK_All(pose, tool=None,
reference=None)`, `FilterTarget(pose, joints_approx=None)`, `addMoveJ(itemtarget)`,
`addMoveL(itemtarget)`, `addMoveSearch(itemtarget)`, `addMoveC(itemtarget1, itemtarget2)`.

**Speed / accuracy / motion tuning**
`setSpeed(speed_linear, speed_joints=-1, accel_linear=-1, accel_joints=-1)`,
`setAcceleration(accel_linear)`, `setSpeedJoints(speed_joints)`,
`setAccelerationJoints(accel_joints)`, `setRounding(rounding_mm)`, `setZoneData(zonedata)`,
`setAccuracyActive(accurate=1)`, `AccuracyActive()`, `setParamRobotTool(tool_mass=5,
tool_cog=None)`.

**Program / instructions**
`ProgramStart(programname, folder='', postprocessor='')`, `MakeProgram(folder_path='',
run_mode=RUNMODE_MAKE_ROBOTPROG)`, `FilterProgram(filestr)`, `setRunType(program_run_type)`,
`RunType()`, `RunProgram(prog_parameters=None)`, `RunCode(prog_parameters=None)`,
`RunCodeCustom(code, run_type=INSTRUCTION_CALL_PROGRAM)`, `RunInstruction(code,
run_type=...)`, `customInstruction(name, path_run, path_icon='', blocking=1,
cmd_run_on_robot='')`, `Pause(time_ms=-1)`.

**I/O**
`setDO(io_var, io_value)`, `setAO(io_var, io_value)`, `getDI(io_var)`, `getAI(io_var)`,
`waitDI(io_var, io_value, timeout_ms=-1)`.

**Real robot connection**
`Connect(robot_ip='', blocking=True)`, `ConnectSafe(robot_ip='', max_attempts=5,
wait_connection=4, callback_abort=None)`, `ConnectionParams()`, `setConnectionParams(robot_ip,
port, remote_path, ftp_user, ftp_pass)`, `ConnectedState()`, `Disconnect()`.

**Runtime state**
`Busy()`, `Stop()`, `WaitMove(timeout=360000)`, `WaitFinished()`, `ShowSequence(matrix,
display_type=..., timeout=-1)`.

## `Mat` and `robomath` (pose math)

**Building a `Mat`**
`Pose(x, y, z, rxd, ryd, rzd)` — **degrees**. `PosePP(x, y, z, r, p, w)`,
`TxyzRxyz_2_Pose(xyzrpw)`, `xyzrpw_2_pose(xyzrpw)`, `transl(tx, ty, tz)`, `rotx/roty/rotz(rad)`,
`eye(size=4)`, `dh(rz, tx, tz, rx)` / `dhm(...)` (Denavit-Hartenberg row), `point_Xaxis_2_pose`,
`point_Yaxis_2_pose`, `point_Zaxis_2_pose`, `quaternion_2_pose(qin)`.

**Decomposing a `Mat`**
`pose_2_xyzrpw(H)`, `Pose_2_TxyzRxyz(H)` — **radians**, `pose_2_quaternion(Ti)`,
`Pose_Split(pose1, pose2, delta_mm=1.0)`.

**Vendor Euler-convention round-trips** (`Pose_2_X` / `X_2_Pose` pairs — each a distinct
convention, not interchangeable): `Staubli`, `Motoman`, `Fanuc`, `Techman`, `KUKA`, `Adept`,
`Catia` (one-way), `Comau`, `Nachi`, `ABB`, `UR`.

**Matrix/vector ops**
`Mat.copy()`, `.tr()` (transpose), `.inv()`, `.invH()` (homogeneous inverse), `.Pos()`,
`.setPos(newpos)`, `.VX()/.VY()/.VZ()` (axis vectors), `.setVX/VY/VZ(...)`, `.Rot33()`,
`.translationPose()`, `.rotationPose()`, `.isHomogeneous()`, `.RelTool(x,y,z,rx,ry,rz)` (offset
in tool frame), `.Offset(x,y,z,rx,ry,rz)` (offset in reference frame), `.catV`/`.catH`
(concatenate), `.SaveCSV`/`.SaveMat`, `.fromNumpy`/`.toNumpy`. Free functions: `RelTool(pose,
...)`, `Offset(pose, ...)`, `norm`, `normalize3`, `cross`, `dot`, `angle3`, `pose_angle(pose)`,
`pose_angle_between(pose1, pose2)`, `distance(a, b)`, `pose_is_similar(a, b, tolerance=0.1)`,
`intersect_line_2_plane`, `proj_pt_2_plane`, `proj_pt_2_line`, `fitPlane(points)`.

**Joint-angle helpers**
`joints_2_angles(jin, type)`, `angles_2_joints(jin, type)` — convert between raw joint values
and mechanism-specific angle conventions (used for non-serial mechanisms).
