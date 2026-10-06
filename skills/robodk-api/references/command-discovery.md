# RoboDK commands, item parameters, and trigger actions

`Robolink.Command()` and `Item.setParam()` are escape hatches: hundreds of RoboDK behaviors
(settings, UI actions, per-item toggles, event wiring) are reachable through these two generic
calls instead of a dedicated method. **The full set is defined by the running RoboDK
application — its version and any loaded plugins — not by the client SDK.** Nothing in
`robolink.py`'s source enumerates it; the docstrings just say "Select **Tools ▸ Run Script ▸
Show Commands** to see all available commands." The tables below are a real captured snapshot
(see provenance at the bottom) — treat them as reliably accurate for the captured version, but
**re-run the capture and diff before depending on an exact match on a different RoboDK version**,
and never invent a name that isn't in these tables or confirmed some other way.

## The three introspection calls

1. **Global commands** — `RDK.Command("", "")` (empty command, empty value) returns every
   command name `Robolink.Command()` currently accepts, with a value hint and description each.
2. **Per-item / station commands** — `item.setParam("", "")` on any `Item` (or
   `RDK.ActiveStation().setParam("", "")` for station-level ones) returns the analogous table for
   `Item.setParam()`. This is a different call from `Robolink.setParam(param, value)`, which
   reads/writes a station-level key-value store rather than listing commands — don't confuse the
   two `setParam`s.
3. **Trigger actions** — `RDK.Command("TriggerAction", "")` returns the valid action strings for
   `RDK.Command("TriggerAction", action_name)` (menu/toolbar actions — same as clicking them in
   the UI). Not documented anywhere else in the SDK.

## Return format (verified against a live capture)

- `RDK.Command("", "")` and `item.setParam("", "")`: rows separated by `<br>`, columns
  (`command`, `value hint`, `description`) separated by `\t`, first row is a header.
- `RDK.Command("TriggerAction", "")`: a **different, `|`-delimited** format — `action||action||...`,
  each `action` itself `name|label` or `name|label|shortcut`. Don't assume it shares the
  `Command()`/`setParam()` table format.

```python
from robodk import robolink

def list_table(raw: str) -> list[list[str]]:
    rows = raw.split("<br>")
    return [r.split("\t") for r in rows if r.strip()]

def list_trigger_actions(raw: str) -> list[list[str]]:
    return [g.split("|") for g in raw.split("||") if g.strip()]

with robolink.Robolink() as RDK:
    global_commands = list_table(RDK.Command("", ""))[1:]        # drop header row
    item_commands = list_table(RDK.ActiveStation().setParam("", ""))[1:]
    trigger_actions = list_trigger_actions(RDK.Command("TriggerAction", ""))
```

## When to reach for this

- Before calling `RDK.Command(name, value)` or `item.setParam(name, value)` with a name not in
  the tables below — check the live table instead of guessing.
- When a user asks "what can I configure on this item" / "what trigger actions are available" /
  "is there a command for X".
- When building on top of this skill (station builders, scene auditors, post-processor tooling)
  and a needed capability isn't covered by a named `Item`/`Robolink` method.

If no live RoboDK connection is available and the name isn't in the tables below, say so
explicitly rather than fabricating a plausible command name — a wrong guess fails silently or
does the wrong thing, since `Command`/`setParam` accept arbitrary strings without validation.

## `RDK.Command(name, value)` — global commands

| Command | Value | Description |
|---|---|---|
| `AddFolder` | (str) | Add a new folder attached to the station root |
| `AddFrame` | (str) | Add a reference frame with the given name |
| `AddNotes` | (str) | Add notes to the station root |
| `AddStationNested` | 1\|0 | Add new RDK station files as nested stations (added to the currently open station) |
| `AllowExternalAPI` | 1\|0 | Allow external API |
| `API_NODELAY` | 1\|0 | Turn On or Off the NoDelay socket for TCP/IP. This option provides faster results when working with the API from a remote PC |
| `API_NonFinite_Behavior` | -1\|0\|1 | How to deal with non finite values provided through the API -> 0=Force values to be 0, 1=Do not allow, -1=Ignore |
| `CAM_APT_AUTOSPLIT` | 1\|0 | Automatically split CAM programs on tool change |
| `CAM_APT_SPLITPROG` | 1\|0 | Automatically split CAM programs on operation change |
| `CAM_AUTOLOADCUTTER` | 1\|0 | Automatically create cutters when loading CAM programs |
| `CAM_ZAXIS_INSIDE` | 1\|0 | Set to 1 if the Tool Z axis points towards the inside of the spindle (CNC standard instead of robot) |
| `CamWinId` |  | Returns the top level window ID. CamID is the pointer returned by Camd2D_Add. |
| `ClearSelection` |  | Clear the selection |
| `CollisideOneStop` | 0\|1 | Stop collision check as soon as one collition is found |
| `CollisionCalcTime` |  | Time it took to calculate collisions during the last udpate event |
| `CollisionHidden` | 1\|0 | Include hidden objects for collision checking |
| `CollisionMap` | All\|None\|Default\|Uncheck\|Off | Set the collision map settings to chack for all interactions, no interactions or the default settings (setting it to Off removes the default collision presets to speed up loading multiple parts) |
| `CollisionMapMaxSize` | (int) | Set the maximum number of objects to remember the collision map (larger is slower when adding new objects) |
| `CollisionMethod` | Default\|Fastest\|CUDA\|CPU | Hardware to use for collision checking |
| `ColorAxisX` | (#AARRGGBB) | Change the color of the X axis |
| `ColorAxisY` | (#AARRGGBB) | Change the color of the Y axis |
| `ColorAxisZ` | (#AARRGGBB) | Change the color of the Z axis |
| `ColorBgBottom` | (#RRGGBB) | Change the color of the background (bottom gradient) |
| `ColorBgTop` | (#RRGGBB) | Change the color of the background (top gradient) |
| `ColorPlaneXY` | (#AARRGGBB) | Change the color of the XY plane |
| `ColorPlaneXZ` | (#AARRGGBB) | Change the color of the XZ plane |
| `ColorPlaneYZ` | (#AARRGGBB) | Change the color of the YZ plane |
| `ColorSelected` | (#AARRGGBB) | Change the color of selected objects |
| `CudaDevice` |  | Name of the CUDA harware being used |
| `CudaThreads` | (int) | Number of threads to use for CUDA GPUs |
| `DisplayCurveNormalsOnSelect` | 1\|0 | Show curve normals when selected |
| `DisplayCurves` | 1\|0 | Display object curves |
| `DisplayPoints` | 1\|0 | Display object points |
| `DisplayThreshold` | (double) | Object smaller than this size won't be displayed (size as a percentage of the screen size). Set to -1 to always display everything |
| `EXIT_LAST_COM` |  | When this command is used, RoboDK will close after the last instance of the API closes |
| `FitAll` |  | Fit all objects in the screen (Fit All action). |
| `FitIsometric` |  | Set Isometric view. |
| `FitSelection` |  | Fit to selection. |
| `Font` | (str) | Set the default text font family by name (eg.: 'Consolas', 'Arial', ...) |
| `FontSize` | (double) | Set the default fext font point size |
| `FrameSizes` | (double) | Set the sizes of coordinate systems as a ratio with respect to the default values (1=default) |
| `FrameSizes-PlaneWidthRatio` | (double) | Apply a ratio to the width of the planes |
| `FrameSizesOther` | (double) | Set the size for other coordinate systems in mm (if no value is provided it will return the current size) |
| `FrameSizesPath` | (double) | Set the size of coordinate systems for paths in mm (if no value is provided it will return the current size) |
| `FrameSizesRef` | (double) | Set the size of coordinate systems for reference frames in mm (if no value is provided it will return the current size) |
| `FrameSizesTarget` | (double) | Set the size of coordinate systems for target items in mm (if no value is provided it will return the current size) |
| `ImportCurvesPoints` | (double) | Import surface edges (Tools-Options-CAD) |
| `ImportSurfaceEdges` | (double) | Import surface edges (Tools-Options-CAD) |
| `KeyEvent` | (str) | Trigger an action given the key shortcut (such as Ctrl+C) |
| `Lang` | (str) | Set the language as a 2-letter ISO language code (eg.: 'en', 'zh', 'ja',...) |
| `LastRender` |  | Returns the time of last display update in ms since epoch |
| `MainProcess_ID` |  | RoboDK's main process ID |
| `MainWindow_ID` |  | Top level window ID |
| `MouseClickLeft` | Select\|Rotate\|Zoom\|Pan\|None | Set the default action for the mouse left click |
| `MouseClickMid` | Select\|Rotate\|Zoom\|Pan\|None | Set the default action for the mouse mid button click |
| `MouseClickRight` | Select\|Rotate\|Zoom\|Pan\|None | Set the default action for the mouse right click |
| `MouseFeedback` | 1\|0 | Enable or disable mouse retroactive feedback in the 3D view |
| `MouseNav` | (int) | Change the 3D navigation type |
| `MoveCSplitDeg` | (double) | Get/set the default step to generate circular movements in deg |
| `MoveCSplitMinMM` | (double) | Get/set the minimum step to generate circular movements in mm |
| `MoveCSplitMM` | (double) | Get/set the default step to generate circular movements in mm |
| `MoveJSplitDeg` | (double) | Get/set the default step to generate joint movements in deg |
| `MoveLSplitDeg` | (double) | Get/set the default step to generate linear movements in deg |
| `MoveLSplitMinMM` | (double) | Get/set the minimum step to generate linear movements in mm |
| `MoveLSplitMM` | (double) | Get/set the default step to generate linear movements in mm |
| `PATH_PROGRAMS` | (folder) | Set the path to save generated programs |
| `PathCheckActiveKin` | 1\|0 | Check paths using active kinematics (accurate or nominal). If the value is set to 0 it will use nominal kinematics |
| `PathPostProcessor` |  | Path to post processors |
| `PathPrograms` | (folder) | Default path to save programs |
| `PathStepCollisionDeg` | (double) | Get/set the movement step for collision detection, in deg |
| `PathStepCollisionMM` | (double) | Get/set the movement step for collision detection, in mm |
| `PathStepMM` | (double) | Get/set the step for simulation in mm |
| `PluginApiEvents` | (All\|) | Allows you to enable feedback for all events while a plugin is loaded |
| `PluginCommand` | (command=value=name) | Send a plugin command, value and name (plugin name is optional) |
| `PluginLoad` | (str) | Load a plugin by name or path to library |
| `PluginReload` | (str) | Reload a plugin |
| `PluginsList` | (str) | List of plugins including pointers |
| `PluginsLoad` |  | Load plugins |
| `PluginsUnload` |  | Unload plugins |
| `Popups` | 1\|0 | Prevent showing any blocking popup messages |
| `ProgMaxLines` | (int) | Number of lines per program |
| `ProgMoveCType` | (int) | Type of targets for circular movements |
| `ProgMoveJType` | (int) | Type of targets for joint movements |
| `ProgMoveLType` | (int) | Type of targets for linear movements |
| `ProgMoveNames` | 1\|0 | Export program names for program generation |
| `ProgramsShow` | 1\|0 | Show programs when they are generated (use the command PATH_PROGRAMS to specify the folder and MAKEPROGS to generate all programs). |
| `ProgRecalc` | 1\|0 | Recalculate targets before program generation |
| `ProgressBar` | (int) | Set the status of the progress bar from 0 to 100 (-1 to hide) |
| `PYTHONPATH` | (folder) | Get or set the Python path |
| `PythonRunCode` | (str) | Run Python code, new lines can be represented as br HTML tags |
| `RunProg` | (str) | Run program name |
| `SetSize3D` | (w x h) | Set the size of the 3D window in pixels as Width x Height (example: [pixels]x[pixels]) |
| `Settings` | Load\|Save\|Defaults | Load, save or reset the settings related to RoboDK |
| `ShowCoords` | 1\|0 | Display coordinate systems |
| `ShowCurveNormals` | 1\|0 | Show curve normals |
| `ShowCurvePoints` | 1\|0 | Show curve points |
| `ShowHiddenSelected` | 1\|0 | Show transparent items when the are hidden and selected |
| `ShowMessage` | (str) | Display a message (blocking popup) |
| `ShowPointNormals` | 1\|0 | Show point normals |
| `ShowRef_NewObjects` | 1\|0 | Display references by default for newly added objects |
| `ShowRef_NewReferences` | 1\|0 | Display references by default for newly added references |
| `ShowSelectedPointNormals` | 1\|0 | Show point normals for selected curves |
| `ShowText` | 1\|0 | Display text on the screen |
| `ShowTextObject` | 1\|0 | Display text on the screen for objects only |
| `SilentMessage` | (str) | Display a message in the toolbar |
| `SimulationSpeed` | (double) | Set the simulation speed (> 0) |
| `SimulationTime` |  | Retrieve the simulation time of the simulation (milliseconds). Starts counting the first time this value is requested. |
| `SizeCurveArrow` | (double) | Curve arrow size |
| `SizeCurvePoints` | (double) | Size of curve points |
| `SizeNormals` | (double) | Normals size |
| `SizeRatioCurves` | (double) | Size of the curves (ratio with respect to the default size). Default value = 1 |
| `Snapshot` | (file) | Save a screenshot (PNG, JPG and other formats supported) |
| `SnapshotWhite` | (file) | Save a screenshot using a white background (PNG, JPG and other formats supported) |
| `Theme` | (int) | Set the theme (0=default, 1=light, 2=dark, 10=high contrast) |
| `Threads` | (int) | Number of threads used for parallel processing |
| `Time` |  | Retrieve the time of the computer since Epoch (seconds) |
| `ToggleWorkspace` |  | Toggle showing workspace |
| `TolerancePickCurve` | (double) | Import surface edges (Tools-Options-Display) |
| `TolerancePickPoint` | (double) | Import surface edges (Tools-Options-Display) |
| `ToleranceSingularityBack` | (double) | Tolerance angle (in deg) to avoid front/back singularity (wrist on axis 1). Same as Tools-Options-Motion-Tolerance to avoid front/back singularity |
| `ToleranceSingularityElbow` | (double) | Tolerance angle (in deg) to avoid elbow singularity (joint 3). Same as Tools-Options-Motion-Tolernace to avoid elbow singularity |
| `ToleranceSingularityWrist` | (double) | Tolerance angle (in deg) to avoid wrist singularity (joint 5). Same as Tools-Options-Motion-Tolerance to avoid wrist singularity |
| `ToleranceTurn180` | (double) | Tolerance to avoid 180 deg rotations (Tools-Options-Motion) |
| `ToolbarLayout` | None\|Basic\|Complete\|Viewer | Set the toolbar layout |
| `Trace` | On\|Off\|Reset | Turn the trace On, Off or Reset/Clear it |
| `TrajectoryTime` | (double) | Returns the simulation time or advance the simulation by a time delta (in seconds). The simulation time used by robots and mechanisms while they are moving. |
| `Tree` | Detach\|Visible\|Hidden | Detach/hide/show the tree from the main screen (the tree can't be attached once detached. Use -SKIPINI command line option on RoboDK startup to ignore user settings) |
| `TriggerAction` | (str) | Trigger an action given the action name (leave empty to retrieve list) |
| `UseGPU` | 1\|0 | Use GPU arrays for rendering |
| `Version` |  | Return the full string of the RoboDK version |
| `ViewPerspective` | 0\|1 | Set the view in perspective mode (1) or orthographic mode (0) |
| `ViewPoseVR` | [x,y,z,rx,ry,rz] | Get or set the view pose of the VR headset (mm and rad) |
| `Window` | Resize | Provoke a resize event |
| `ZoomInvert` | 1\|0 | Invert the sense of the zoom |
| `ZoomSpeed` | (double)\|Auto\|Fixed | Set the zoom speed as a ratio, set to Automatic (default) or fixed |

## `item.setParam(name, value)` — per-item / station commands

| Command | Value | Description |
|---|---|---|
| `(id)` | (dict or JSON string) | For a program, providing the instruction id you can get or set the instruction parameters. |
| `Add` | (dict or JSON string) | Add the new instruction to a program using a dict or JSON format. |
| `Approach` | (Normal\|Tangent\|Side\|XYZ\|NTS\|ArcN\|ArcS A B C) | Set the approach or retract of a robot machining toopath |
| `ApproachRetractAllCurves` | (1\|0) | For curve follow projects: Apply approach and retract to each curve section. |
| `BoundingBox` |  | Returns the bounding box of this object, robot or tool a JSON string, in mm and with respect to station coordinates (absolute) |
| `Clear` | Point\|Curve\|Surf | Delete object points, curves or mesh |
| `ClearanceZ` | (ignored) | Get the clearance distance along the positive Z axis (for tools, objects or coordinate systems). |
| `Close` | (ignored) | Close camera view |
| `Code` | (ignored) | Get the Python code |
| `Convert` | (Object\|Tool) | Convert a tool or geometry to an object or an object to a tool. If the pointer changes it returns the object pointer as a string, otherwise it returns OK. |
| `Cutter` | (1\|0) | Set this tool as a cutter: it is treated accordingly when using a robot machining project. |
| `FilterMesh` | (double double double) | Remove small object triangles given a tolerance [min part size (mm), min triangle surface (mm2), triangle angle (deg)]. |
| `FitAll` | (double) | Fits the screen to the current item and its children. Optionally provide a minimum size to fit. |
| `Form` | (Open\|Close) | Open or close a form or camera linked to an item |
| `HTML` | (string) | Get or set the HTML text of a notes item |
| `IconGet` | (ignored) | Get the item icon as a PNG bytearray in hex format |
| `IconSet` | (image file or hex bytearray representing png data) | Set the icon of an item (see command AddItem) |
| `IsJointTarget` | (ignored) | Returns 1 if the target is a joint target. |
| `IsOpen` | (ignored) | Returns 1 if the view is open, 0 otherwise |
| `JoinCurveTol` | (double) | For curve follow projects: Join curve tolerance (in mm). |
| `Loop` | (1\|0) | Set program to loop |
| `Machining` | (dict or JSON string) | Get or set the robot machining settings (see also: ProgEvents and OptimAxes) |
| `NormalApproach` | (double) | For robot machining projects: Use a normal approach with a given distance. |
| `OffsetRail` | (double) | For robot machining projects: Offset of the rail when optimized (mm). |
| `OffsetTurntable` | (double) | For robot machining projects: Offset of the turntable when optimized (deg). |
| `Open` | (ignored) | Open camera view |
| `OperationSpeed` | (double) | For curve follow projects: Operation speed (in mm/s). |
| `OptimAxes` | (dict or JSON string) | Get or set the robot optimization settings for external axes (settings linked to a robot machining project or robot) |
| `OptimRail` | (0\|1) | For robot machining projects: Use linear rail optimization. |
| `OptimTurntable` | (0\|1) | For robot machining projects: Use turntable optimization. |
| `Orient` | (Teach) | Set the teach action for machining/curve follow projects |
| `PathDisplay` | (Estimated\|Preferred\|Quick\|None) | Preview path for robot machining/curve follow projects. Add the Quick flag to display for a brief moment (about 2 seconds). |
| `PointApproach` | (double) | For point follow projects: Point approach (in mm). |
| `PostProcessor` | (string) | Set the post processor (file or name excluding the path). Leave empty to retrieve current post processor. |
| `ProgEvents` | (dict or JSON string) | Get or set the program events of a robot machining project (use a station to change default settings) |
| `RangeRotZ` | (double 0-180) | For robot machining projects: Tool rotation range around the Z axis (deg). |
| `Reachable` | (ignored) | Returns 1 if the target is reachable with the currently active tool and reference frame, 0 otherwise. |
| `Recalculate` | (ignored) | Recalculate a target. |
| `RecalculateTargets` | (string) | Recalculate all targets of a program. |
| `Reframe` | (ignored) | Reframe on this object |
| `Reset` | (Surf\|Curves\|Points) | Delete the mesh, curves and/or points of an object or tool |
| `Retract` | (Normal\|Tangent\|Side\|XYZ\|NTS\|ArcN\|ArcS A B C) | Set the approach or retract of a robot machining toopath |
| `SaveTableCalib` | (path to csv file) | Save the calibration data as a CSV file. |
| `SaveTableRail` | (path to csv file) | Save the rail data as a CSV file. |
| `SaveTableValid` | (path to csv file) | Save the validation data as a CSV file. |
| `SelectAlgorithm` | (0\|1\|2) | Select the algorithm (0: minimum tool orientation change, 1: Tool orientation follows path, 3: Robot holds object). |
| `Settings` | (1\|0) | Set camera settings |
| `ShowWorkspace` | (0\|1\|2\|3) | Show or hide robot workspace (0: hide, 1: show for wrist center, 2: show for flange, 3: show for active tool). |
| `SimplifyMesh` | (ignored) | Simplify the geometry of an object (it does not change the object appearance). |
| `Start` | (int) | Start a program at a given instruction (0 to start from the beginning) |
| `StatsAccuracy` | (Validation\|Calibration) | Robot calibration statistics |
| `StepRotZ` | (double) | For robot machining projects: Tool rotation steps around the Z axis (deg). |
| `Stop` | (ignored) | Stop a program |
| `Tree` | (expand\|collapse\|isExpanded) | Expand or collapse the item in the tree. |
| `UpdatePath` | (ignored) | Update the operation toolpath (green path). Use this option after changing an approach or retract |
| `Visible` | (1\|0) | Get or set visibility of an item. |
| `VisibleChilds` | (1\|0) | Get or set visibility of an item including children items. |

## `RDK.Command("TriggerAction", name)` — trigger actions

Menu/toolbar actions, triggerable exactly as if clicked in the UI. Format: `name`, `label`,
optional keyboard `shortcut`.

| Action | Label | Shortcut |
|---|---|---|
| `actionSave_Station` | Save Station | Ctrl+S |
| `action-Exit` | Exit | Alt+F4 |
| `actionIsometric` | Isometric | Alt+1 |
| `actionTop` | Top | Alt+2 |
| `actionFront` | Front | Alt+3 |
| `actionRight` | Right | Alt+4 |
| `actionLeft` | Left | Alt+5 |
| `actionBack` | Back | Alt+6 |
| `actionFit_All` | Fit All | Alt+7 |
| `action-Options` | Options | Shift+O |
| `actionOpen` | Open... | Ctrl+O |
| `actionNew_Station` | New Station | Ctrl+N |
| `actionClose_Station` | Close Current Station | Ctrl+F4 |
| `actionSave_Station_as` | Save Station as... | Ctrl+Shift+S |
| `actionAdd_Robot` | Add Robot |  |
| `actionAdd_Tool` | Add Tool |  |
| `actionAdd_Object` | Add Object |  |
| `actionAdd_Frame` | Add Reference Frame |  |
| `actionCollision_Map` | Collision Map | Shift+X |
| `actionCheck_Collisions` | Check Collisions | Shift+C |
| `actionInt_SelectRectangle` | Select Items |  |
| `actionInt_Move_Frame` | Move References (hold ALT) |  |
| `actionInt_Move_Object` | Move Tools (hold ALT+Shift) |  |
| `actionRotation_Aligned` | Align Rotation |  |
| `actionChange_Color_Form` | Change Color | Shift+T |
| `actionTraceActive` | Active | Alt+T |
| `actionTraceReset` | Reset | Alt+X |
| `actionTeach_Target` | Teach Target | Ctrl+T |
| `actionHelp` | Help | F1 |
| `actionLicense` | License |  |
| `action-About` | About |  |
| `actionMake_demo_station` | Make a Demo Station |  |
| `action-AddProgram` | Add Program |  |
| `actionAdd_Move_Joint` | Move Joint Instruction |  |
| `actionAdd_Move_Linear` | Move Linear Instruction |  |
| `actionAdd_Move_Circular` | Move Circular Instruction |  |
| `actionAdd_Tool_Change` | Set Tool Frame Instruction |  |
| `actionAdd_Frame_Change` | Set Reference Frame Instruction |  |
| `actionAdd_Pause` | Pause Instruction |  |
| `actionAdd_Event` | Simulation Event Instruction |  |
| `actionAdd_Speed_Change` | Set Speed Instruction |  |
| `actionAdd_Robot_Change` | Change Selected Robot |  |
| `actionCut` | Cut | Ctrl+X |
| `actionCopy` | Copy | Ctrl+C |
| `actionPaste` | Paste | Ctrl+V |
| `action-AddPython` | Add Python Program |  |
| `actionOpen_weblib` | Open Robot Library | Ctrl+Shift+O |
| `actionTake_screenshot` | Take Screenshot | Ctrl+P |
| `actionInt_Rotate` | Rotate |  |
| `actionInt_Pan` | Pan |  |
| `actionInt_Zoom` | Zoom |  |
| `actionInt_None` | No Selection |  |
| `actionCalibrate_tool` | Define Tool Frame (TCP) |  |
| `actionCalibrate_frame` | Define Reference Frame (User frame) |  |
| `action-MachiningProject` | Robot Machining Project | Ctrl+M |
| `actionBallbar_Validation` | Ballbar Accuracy Test |  |
| `actionFast_simulation` | Fast Simulation |  |
| `actionFrameBigger` | Make Reference Frames Larger | + |
| `actionFrameSmaller` | Make Reference Frames Smaller | - |
| `actionToggleShowText` | Show/Hide Text | / |
| `actionToggleWorkspace` | Show/Hide Robot Workspace | * |
| `actionAdd_Code_Custom` | Program Call Instruction |  |
| `actionCalibrate_Robot` | Calibrate Robot |  |
| `action-ConnectRobot` | Connect Robot |  |
| `actionConnect_C_Track` | Connect Creaform's C-Track Optical CMM |  |
| `actionImport_points` | Import Points |  |
| `actionAdd_Message` | Show Message Instruction |  |
| `actionAdd_empty_tool` | Add Tool (TCP) |  |
| `actionImport_curve` | Import Curve |  |
| `actionConnect_Laser_Tracker` | Connect Faro Laser Tracker |  |
| `actionUpdate_all_Machining_projects` | Update Robot Machining projects | Ctrl+U |
| `actionReorder_item_after` | Reorder Selected Items... |  |
| `actionRun_Program` | Run Program | Ctrl+R |
| `actionGenerate_program` | Generate Program... | Shift+F6 |
| `actionGenerate_program_fast` | Generate Program(s) | F6 |
| `actionShow_hide` | Show/Hide Item | F7 |
| `actionOpen_Notepad` | Open Text Editor |  |
| `actionOpen_FTP_Client` | Open FTP Client |  |
| `actionISO_9283_Accuracy_and_Repeatability_test` | Test Position Accuracy (ISO 9283) |  |
| `actionPath_Accuracy_test` | Test Path Accuracy (ISO 9283) |  |
| `actionModify_target` | Modify Target | F3 |
| `actionChange_target_configuration` | Change Target Configuration | F4 |
| `actionCheck_for_updates` | Check for Updates... |  |
| `actionDraw_curve_on_part` | Draw Curve on Part |  |
| `actionISO_9283_targets_and_path` | Create ISO 9283 cube (targets and path) |  |
| `actionAdd_Zone_change` | Set Rounding Instruction |  |
| `actionTeach_Target_on_Surface` | Teach Target(s) on Surface | Ctrl+Shift+T |
| `action-AddEditPost` | Add/Edit Post Processor |  |
| `actionShow_Hide_reference_frames` | Show/Hide Reference Frames | Alt+/ |
| `actionPauseProgram` | Pause Program | Backspace |
| `actionSyncExternalAxis` | Synchronize External Axes |  |
| `actionAdd_Mechanism_or_Robot` | Model Mechanism or Robot |  |
| `actionExport_3D_Simulation` | Export Simulation | Ctrl+E |
| `actionRename_item` | Rename Item... (F2) |  |
| `actionRestore_default_toolbar` | Default |  |
| `action3D_print_project` | 3D Printing Project |  |
| `actionSlicer_for_3D_print` | Open 3D print slicer |  |
| `actionCurveProject` | Curve Follow Project |  |
| `actionPointProject` | Point Follow Project |  |
| `actionMeasure_tool` | Measure | Shift+M |
| `actionPerspective_view` | Perspective View |  |
| `actionShow_Tree_in_main_Window` | Show Tree Inside the Window |  |
| `actionSimulate_2D_Camera` | Simulate 2D Camera |  |
| `actionAdd_I_O_change` | Set or Wait I/O Instruction |  |
| `actionClose_Windows` | Close Side Windows | Alt+C |
| `actionOpen_DXF_editor` | Open DXF Editor |  |
| `actionShow_Fullscreen` | Show Fullscreen | F11 |
| `actionShow_Cinema_Mode` | Show Cinema Mode | F12 |
| `actionConnect_Leica_Laser_Tracker` | Connect Leica Laser Tracker |  |
| `actionConnect_API_Laser_Tracker` | Connect API OT2 Laser Tracker |  |
| `actionFit_to_Selection` | Fit to Selection | Alt+0 |
| `actionSend_Program_s_to_robot` | Send Program(s) to Robot | Ctrl+F6 |
| `actionBasic_toolbar` | Basic |  |
| `actionComplete` | Complete |  |
| `actionReorder_items_automatically` | Reorder Selected Items Automatically | Shift+R |
| `actionPurchase_License` | Purchase License |  |
| `actionRenew_License` | Renew License |  |
| `actionRequest_Support` | Request Support |  |
| `actionConnect_API_Radian_Laser_Tracker` | Connect API Radian Laser Tracker |  |
| `actionInt_Move_None` | Default Selection |  |
| `actionPreview_Targets` | Preview Targets | F5 |
| `actionTraceReferences` | References |  |
| `actionTracePoints` | Points |  |
| `actionTraceSpheres` | Spheres |  |
| `actionTraceDots` | Dots |  |
| `actionTraceLine` | Line |  |
| `actionNo_Toolbar` | No Toolbar |  |
| `action-Plugins` | Add-ins | Shift+I |
| `actionConnect_HTC_Vive_VR` | Connect VR Headset | Shift+V |
| `actionRun_Script` | Run Script | Shift+S |
| `actionVR_View` | VR View |  |
| `actionSensor_View` | Sensor View |  |
| `actionRun_last_Script` | Run Last Script: ShowCommands | Shift+L |
| `actionReveal_in_the_Tree` | Reveal in the Tree | F8 |
| `actionDefaultView` | Default View |  |
| `actionViewer_Toolbar` | Viewer |  |
| `actionCurveCreate` | Create Curves | Shift+P |
| `actionCurveModify` | Modify Curves |  |
| `actionConnect_SteamVR` | Connect SteamVR System |  |
| `actionRobotWeldingProject` | Robot Welding project |  |
| `actionSimple` | Simple |  |
| `actionPalletizing` | Palletizing |  |
| `actionOpen_examples` | Open Sample Stations |  |
| `actionConnect_OptiTrack_Camera` | Connect OptiTrack Camera |  |
| `actionShow_Tree` | Show Tree |  |
| `actionUndo` | Undo | Ctrl+Z |
| `actionRedo` | Redo | Ctrl+Y |

## Capture provenance

- **RoboDK version:** `RoboDK 64 bit v6.0.7.26935`
- **Capture date:** 2026-09-08
- **Method:** launched RoboDK, connected via `robolink.Robolink()`, and ran the three
  introspection calls above, parsed per the "Return format" section.
- **Counts:** 136 global commands, 58 item/station commands, 147 trigger actions.

### Refreshing this snapshot

From a machine with RoboDK installed — headless, no GUI window, auto-closes when done. Set
`ROBODK_AI=noui` in the environment before running this (see `references/headless-testing.md`)
instead of passing launch args by hand:

```python
from robodk import robolink

with robolink.Robolink() as RDK:
    print(RDK.Command("Version", ""))
    open("global_commands.txt", "w").write(RDK.Command("", ""))
    open("item_commands.txt", "w").write(RDK.ActiveStation().setParam("", ""))
    open("trigger_actions.txt", "w").write(RDK.Command("TriggerAction", ""))
```

Parse each with the functions under "Return format" above, regenerate the three tables, and
update the version/date/counts here. Do this when you hit a command/param that isn't listed, or
periodically alongside `assets/robodk-api/SNAPSHOT.md`'s refresh.
