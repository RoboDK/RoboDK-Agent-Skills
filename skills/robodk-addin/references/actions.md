# Writing action scripts (`robodk.roboapps`)

Every action is a standalone Python process. RoboDK launches
`python MyAction.py` (adding `Checked` or `Unchecked` to `argv` for checkable
actions), reads its stdout for control keywords, and may kill it. The
`robodk.roboapps` module is the thin protocol layer over that arrangement —
these functions mostly *print keywords* or *read argv*, which is why calling them
in the wrong order or from the wrong process silently does nothing.

## Contents

- [The four action shapes](#the-four-action-shapes)
- [Why `runmain()`](#why-runmain)
- [roboapps API](#roboapps-api)
- [Persistent settings with AppSettings](#persistent-settings-with-appsettings)
- [Live IPC between running actions](#live-ipc-between-running-actions)
- [Dialogs](#dialogs)
- [Sharing code between actions](#sharing-code-between-actions)
- [Calling an action from a station program](#calling-an-action-from-a-station-program)
- [Debugging](#debugging)

## The four action shapes

Pick the shape from how the button should behave, then set `Checkable` in
`AppConfig.ini` to match. A mismatch between the two is the most common bug in
Add-ins: RoboDK decides whether to pass `Checked`/`Unchecked` from the INI, and
the script decides what to do with them.

### 1. Momentary — runs once per click

```python
def runmain():
    if roboapps.Unchecked():
        roboapps.Exit()
    else:
        MyAction()
```

`Checkable=false`. The `Unchecked()` guard costs nothing and keeps the script
correct if someone later makes the action checkable.

### 2. Checkable action — a background task that runs while checked

```python
def ActionChecked():
    RDK = robolink.Robolink()
    APP = roboapps.RunApplication()
    while APP.Run():          # False as soon as RoboDK asks the action to stop
        do_one_iteration()
        robomath.pause(0.05)
    cleanup()                 # only reached because of SkipKill()

def ActionUnchecked():
    pass                      # separate process; keep it short

def runmain():
    if roboapps.Unchecked():
        ActionUnchecked()
    else:
        roboapps.SkipKill()   # otherwise RoboDK kills the process ~2 s after the stop request
        ActionChecked()
```

`Checkable=true`. Two details matter:

- The checked run and the unchecked run are **different processes**. Anything you
  want to survive between them belongs in a station parameter or the station
  itself, not in a module-level variable.
- Without `SkipKill()`, RoboDK terminates the process shortly after the user
  unchecks, so code after the `while` loop may never run. Call it when you need
  to save a file, close a device, or ask the user something on the way out.

### 3. Checkable option — a toggle that stores a state and exits

```python
def runmain():
    if roboapps.Unchecked():
        RDK.setParam('MY_OPTION', 0.0)
    else:
        roboapps.KeepChecked()  # without this the button pops back out when the script exits
        RDK.setParam('MY_OPTION', 1.0)
```

`Checkable=true`, usually `AddToToolbar=false`. Give several options the same
`CheckableGroup` number to make them mutually exclusive, like radio buttons.

The distinction from shape 2: an *action* keeps running while checked, an
*option* records a preference and exits immediately. `KeepChecked()` is what
tells RoboDK "I'm done, but leave the button pressed".

### 4. Context / double-click — operates on the tree selection

```python
def OnContextAction():
    RDK = robolink.Robolink()
    selected = RDK.Selection()
    if not selected:
        RDK.ShowMessage("Nothing selected!", True)
        return
    for item in selected:
        ...
```

Same `runmain()` as a momentary action; what makes it contextual is
`TypeOnContextMenu` / `TypeOnDoubleClick` in `AppConfig.ini`. RoboDK sets the
selection before launching the script, so `RDK.Selection()` is how you receive
the argument. Still handle the empty case — the user can also reach the action
from the menu.

## Why `runmain()`

Put the body in a function named exactly `runmain()` and call it from a
`if __name__ == '__main__':` guard. RoboDK's compilation step (used to ship
`.pyc`-only packages) generates a loader stub that imports your module and calls
`runmain()`; a script that only works at import time breaks when compiled. It
also makes the action importable and testable from other scripts.

## roboapps API

```python
from robodk import roboapps
```

| Call | What it actually does |
| --- | --- |
| `roboapps.Checked()` | `True` if `"Checked"` is in `sys.argv` |
| `roboapps.Unchecked()` | `True` if `"Unchecked"` is in `sys.argv` |
| `roboapps.KeepChecked()` | Prints `App Setting: Keep checked` — RoboDK leaves the button checked after the process exits |
| `roboapps.SkipKill()` | Prints `App Setting: Skip kill` — RoboDK won't force-terminate this process |
| `roboapps.Exit(code=0)` | `sys.exit(code)`; a non-zero code makes RoboDK show a trace |
| `roboapps.RunApplication(rdk=None)` | Stop-signal watcher; `.Run()` returns `False` when RoboDK requests a stop |
| `roboapps.AppSettings(param)` | Saved settings with a generated UI — see below |
| `roboapps.Str2FloatList(s, n)` | Parse a string of numbers, `None` if fewer than `n` |
| `roboapps.get_robodk_theme(RDK)` | RoboDK's current theme name, for matching custom Qt/tkinter UI |
| `roboapps.get_qt_app(...)` / `get_tk_app(...)` | A `QApplication` / `Tk` root already styled like RoboDK |

`RunApplication` works by setting a station parameter named
`<scriptname>_<foldername>` to `1` on start; RoboDK sets it to `0` to request a
stop, and `.Run()` polls it (at most every 0.1 s). Two consequences: the loop
must reach `.Run()` regularly to stay responsive, and you can trigger a stop
yourself with `RDK.setParam('MyAction_MyApp', 0)`.

## Persistent settings with AppSettings

`AppSettings` saves values into the **station**, so each `.rdk` file carries its
own configuration, and builds a dialog automatically from the attributes.

```python
from robodk import roboapps

class Settings(roboapps.AppSettings):

    def __init__(self, settings_param='My-App-Settings'):
        super().__init__(settings_param)

        from collections import OrderedDict
        self._FIELDS_UI = OrderedDict()

        self._FIELDS_UI['SECTION_PATH'] = '$Path generation$'   # $...$ renders as a header

        self._FIELDS_UI['STEP_MM'] = 'Step size (mm)'
        self.STEP_MM = 5.0

        self._FIELDS_UI['APPROACH'] = 'Approach direction'
        self.APPROACH = [0, ['Normal', 'Tangent', 'Custom']]     # [index, choices] -> dropdown

        self._FIELDS_UI['REVERSE'] = 'Reverse the path'
        self.REVERSE = False
```

Rules that come from the implementation:

- Public attributes are saved; anything starting with `_` is not.
- Supported types: `bool`, `int`, `float`, `str`, lists and tuples of those,
  `dict`, and the `[index, [choices]]` dropdown form.
- `_FIELDS_UI` is optional. When present it controls both the labels and the
  order shown; when absent, all attributes appear with their raw names.
- The defaults live in `__init__`, so "Restore defaults" works by constructing a
  fresh instance. Keep `__init__` free of side effects for that reason — if you
  need to populate a dropdown from the station (a list of frames, say), do it in
  a separate method and override `ShowUI`/`SetDefaults` to call it.

Usage from a settings action and from other actions:

```python
# Settings.py — the action that opens the dialog
S = Settings()
S.Load()
S.ShowUI('My App Settings')

# any other action — read the saved values
S = Settings()
S.Load(RDK)
step = S.STEP_MM
```

`Save(rdk)`, `Load(rdk)`, `Erase(rdk)`, `SetDefaults()` and `CopyFrom(other)` are
also available. `ShowUI` saves on OK. Give each settings class a distinct
`settings_param` string; two classes sharing one name overwrite each other.

## Live IPC between running actions

`AppSettings`/`RDK.setParam` cover a saved preference, but a checkable
service action (shape 2) sometimes needs to exchange *live* data with other,
short-lived actions in the same App while it's running — e.g. a background
"sound emitter" service that other one-shot actions send commands to.
Station parameters work but are polling-only and string/number-limited; a
named `multiprocessing.shared_memory.ShareableList` is a lighter-weight
alternative for a small fixed-shape message:

```python
# the checkable service action
from multiprocessing import shared_memory
request = shared_memory.ShareableList([" " * 20, " " * 260, 0, 0, 0.0, 0.0], name="rdk_myapp_request")
response = shared_memory.ShareableList([" " * 20, " " * 260], name="rdk_myapp_response")
while APP.Run():
    command = request[0]
    ...

# a separate one-shot action, sending a command to the running service
from multiprocessing import shared_memory
request = shared_memory.ShareableList(name="rdk_myapp_request")   # attaches, doesn't create
request[0] = "PLAY"
```

Same rule as everywhere else in this file: these are different processes, so
this only works while the checkable action's loop is actually running to read
the other side.

## Dialogs

`robodk.robodialogs` works with or without Qt (it falls back to tkinter), so
prefer it over rolling your own:

```python
from robodk import robodialogs

robodialogs.ShowMessage('Done', 'My App')
if robodialogs.ShowMessageYesNo('Overwrite the program?'):
    ...
count = robodialogs.InputDialog('How many passes?', 3)         # type follows the default
path = robodialogs.getOpenFileName(strtitle='Select a CSV', defaultextension='.csv')
folder = robodialogs.getOpenFolder(strtitle='Select an output folder')
save_path = robodialogs.getSaveFileName(strtitle='Save settings', strfile='config',
    defaultextension='.ini', filetypes=[('INI files', '*.ini'), ('All files', '*.*')])
```

For non-blocking feedback inside the RoboDK window, use
`RDK.ShowMessage(text, popup=False)` — it writes to the status bar instead of
interrupting the user.

## Sharing code between actions

Two mechanisms, for two different situations:

**Within the App** — prefix the module with an underscore so the loader ignores
it: `_AppUtilities.py`, imported as `from _AppUtilities import ShowMessage`.
Subfolders also work for helper packages, since only the root is scanned.

**From outside the App** — add an empty `__init__.py` at the App root. RoboDK
then puts the `Apps` folder on `PYTHONPATH`, so a station script or another App
can do `from MyApp import GenerateWeldPath`. Actions written to be importable
handle both cases:

```python
try:
    from MyApp import Settings   # when imported as a package from elsewhere
except ImportError:
    import Settings              # when run as an action inside the App folder
```

Keep the real work in a plain function with `RDK` and settings as optional
parameters, and let `runmain()` be a thin wrapper. That is what makes an action
reusable rather than click-only.

## Calling an action from a station program

A RoboDK Program instruction can call the action with arguments, e.g.
`DeleteObjects(2)`. Read them from `sys.argv`:

```python
import sys
zone_id = int(sys.argv[1]) if len(sys.argv) > 1 else 0
```

Watch out for the overlap with checkable actions, where `sys.argv[1]` is
`Checked` or `Unchecked` — check `roboapps.Unchecked()`/`Checked()` first.

## Debugging

- Run the script directly in your IDE. `robolink.Robolink()` attaches to a
  running RoboDK, so actions work outside the Add-in framework; only
  `Checked`/`Unchecked` argv differ.
- Add your `Apps` folder to the system `PYTHONPATH` while developing — the system
  variable takes precedence over the one RoboDK injects.
- Print freely: RoboDK captures stdout for the App. Avoid printing lines
  containing `App Setting: Skip kill` or `App Setting: Keep checked` unless you
  mean them, since those strings *are* the control protocol.
- After changing `AppConfig.ini` or adding a script, right-click the App in the
  Add-in Manager and choose **Reload**; RoboDK does not watch the folder.
