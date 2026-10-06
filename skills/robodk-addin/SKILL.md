---
name: robodk-addin
description: Create, edit, validate, package, inspect and extract RoboDK Add-ins (also called RoboDK Apps) — a folder of Python action scripts plus AppConfig.ini that adds menus, toolbar buttons, context-menu entries and settings dialogs to RoboDK, distributed as an .rdkp package. Use this skill whenever the user mentions RoboDK add-ins, RoboDK apps, .rdkp files, AppConfig.ini, the AppLoader or Add-in Manager, roboapps/AppSettings, or wants to add a button, menu, toolbar action, right-click action or custom UI to RoboDK, package/unpack an .rdkp, inspect an existing Add-in, or automate a RoboDK workflow that should be reusable from the RoboDK interface rather than run as a one-off script.
version: 1.0.0
author: RoboDK
license: MIT
platforms: [linux, windows, macos]
metadata:
  tags: [robodk, addin, app, plugin, ui, packaging]
  category: software-development
  related_skills: [robodk-api]
---

# Building RoboDK Add-ins

A RoboDK Add-in (an "App") is a folder that RoboDK turns into UI. Drop it in
RoboDK's `Addins/` directory (RoboDK scans `Addins/` and `Apps/` as two
separate roots — `Addins/` for a `manifest.xml`-based Add-in, the older
`Apps/` for a [Classic App](references/appconfig.md) with no `manifest.xml`;
put it in the wrong one and RoboDK loads it in the wrong mode) and every
root-level Python script becomes a button in its own menu and toolbar;
`AppConfig.ini` controls how each one appears and behaves. Zip the folder and
it becomes an `.rdkp` package anyone can install.

The whole system rests on a few conventions rather than a framework, so most
problems are convention problems: a script in the wrong place, a `Checkable` flag
that disagrees with the script body, a missing `runmain()`. Work through the
structure below and use `scripts/robodk_addin.py check` to catch the rest.

## Anatomy

```
WeldUtilities/                 <- folder name = App name; one menu + one toolbar
├── AppConfig.ini              <- how each action appears (RoboDK generates a default if absent)
├── manifest.xml               <- extra metadata + file list (needed to distribute; `sync` generates it)
├── core_properties.xml        <- title/identifier/version/description (needed to distribute; `sync` generates it)
├── icon.svg                   <- the App's icon; `package` moves it to the package root
├── GenerateWeldPath.py        <- an action: menu entry + toolbar button
├── GenerateWeldPath.svg       <- its icon (same basename; .svg > .png > .jpg > .ico)
├── MonitorTemperature.py      <- a checkable action
├── MonitorTemperatureChecked.svg   <- icon shown while checked
├── Settings.py                <- opens the settings dialog
├── _AppUtilities.py           <- leading "_" = shared module, never a button
├── __init__.py                <- makes the App importable from other scripts (optional)
├── requirements.txt           <- pip dependencies, installed on load (optional)
└── README.md                  <- required to publish on the Marketplace
```

Rules that decide what becomes a button:

- **Root level only.** The loader does not recurse — helper packages in
  subfolders can never accidentally become actions.
- **`.py` and `.exe` only.**
- **A leading `_` means skip.** That applies to folders too.
- The `AppConfig.ini` section name is the filename without its extension.

`manifest.xml` and `core_properties.xml` describe the same package — identity,
version, description — split across two OPC parts for the final `.rdkp`.
RoboDK's loader also accepts a single `manifest.xml` with those fields embedded
directly in a `<coreProperties>` block, so for simplicity you can maintain just
one file by hand during development; `sync`/`package` still split it into the
two-part layout the packaged `.rdkp` format expects. See
[references/packaging.md](references/packaging.md#package-metadata-core_propertiesxml-and-manifestxml)
and [references/manifest.template.xml](references/manifest.template.xml) for a
ready-to-copy starting point.

## Workflow

### 1. Understand the shape before writing code

Two questions decide almost everything:

**What kind of button is each action?** There are four shapes, and the script
body must match the `Checkable` flag in `AppConfig.ini`:

| Shape | Behaviour | `Checkable` | The script must |
| --- | --- | --- | --- |
| Momentary | Runs once per click | `false` | Just do the work |
| Checkable action | Background task running while checked | `true` | Loop on `roboapps.RunApplication().Run()`, call `SkipKill()` |
| Checkable option | Toggles a stored preference, exits | `true` | Call `roboapps.KeepChecked()` |
| Context / double-click | Acts on the tree selection | `false` | Read `RDK.Selection()`, set `TypeOnContextMenu`/`TypeOnDoubleClick` |

**Where does state live?** Every action is a separate process, so nothing
survives in memory between clicks. Persist to the station: `roboapps.AppSettings`
for user-facing configuration (it generates the dialog too), or
`RDK.setParam`/`getParam` for simple flags.

**One button per operation, or one dialog for all of them?** The four shapes
above assume each operation gets its own script and toolbar button — fine for
a handful of independent actions, but it doesn't scale to an App with many
related operations (RoboDK's own `CurveUtilities` went from 14 separate
single-purpose scripts to a single `CurveEditor.py` that opens one dialog with
every operation inside it, plus a `Settings.py`). When the operations share
state, a UI, or are naturally steps of one workflow, prefer one script that
opens a persistent dialog (Qt/tkinter, styled via `roboapps.get_qt_app()` /
`get_tk_app()`) over many small ones — it also sidesteps the "different
process per click" state problem entirely, since the dialog stays open in one
process.

Read [references/actions.md](references/actions.md) for the code shape of each
and the reasoning behind `SkipKill` / `KeepChecked` — getting those two wrong
produces buttons that pop back out or processes that get killed mid-save.

### 2. Scaffold

```bash
python scripts/robodk_addin.py new path/to/WeldUtilities \
  --menu-name "Weld Utilities" \
  --action "GenerateWeldPath=context" \
  --action "MonitorTemperature=checkable" \
  --settings --author "Your Company" --identifier com.yourco.app.weldutilities
```

Action types: `momentary`, `checkable`, `option`, `option-group`, `context`,
`doubleclick`. This writes runnable scripts in the right shape, a complete
`AppConfig.ini`, placeholder icons, `manifest.xml`, `README.md`, `__init__.py`
and `_AppUtilities.py`.

Scaffolding by hand is fine too — but then run `sync` afterwards so
`AppConfig.ini` and `manifest.xml` stay complete.

### 3. Implement the actions

Keep the real work in a plain function that takes `RDK` and settings as optional
arguments, and let `runmain()` be a thin wrapper around it. That single habit is
what makes an action reusable from other Apps and from station programs, and
testable outside RoboDK:

```python
def GenerateWeldPath(RDK=None, S=None):
    if RDK is None:
        RDK = robolink.Robolink()
    if S is None:
        S = Settings(); S.Load(RDK)
    ...

def runmain():
    if roboapps.Unchecked():
        roboapps.Exit()
    else:
        GenerateWeldPath()

if __name__ == '__main__':
    runmain()
```

Name the entry point exactly `runmain()`. RoboDK's compilation step generates a
stub that imports the module and calls it, so a script that only works at import
time breaks when packaged compiled.

[references/robolink.md](references/robolink.md) has the API surface Add-ins
actually use — selection, station parameters, item lookup, poses, and the
`RDK.Render(False)` / `Render(True)` bracket that keeps bulk edits from crawling.

### 4. Tune the UI

Edit `AppConfig.ini` for labels, ordering, shortcuts, toolbar placement and which
item types get a context-menu entry. Full key reference with defaults, the item
type numbers, and a worked example:
[references/appconfig.md](references/appconfig.md).

Give each action an icon named after the script. Checkable actions can have a
second icon suffixed `Checked` for the pressed state.

### 5. Validate

```bash
python scripts/robodk_addin.py check path/to/WeldUtilities
python scripts/robodk_addin.py sync path/to/WeldUtilities   # fill gaps, refresh manifest
```

`check` reports what RoboDK will silently ignore or get wrong: scripts with no
config section, config sections with no script, missing `runmain()`, checkable
actions that never test `Unchecked()`, loops without `SkipKill()`, missing icons,
and a `manifest.xml` that has drifted from the files on disk. `sync` fixes the
mechanical half (add `--prune` to drop orphan sections).

### 6. Test in RoboDK

Put the folder in `Apps/` or link it from **Tools ➔ Add-in Manager ➔ Create
Add-in ➔ Link to an existing Add-in**, enable it, then right-click ➔ **Reload**
after any change to `AppConfig.ini` or when adding a script. RoboDK does not
watch the folder. Script edits alone need no reload, since each click launches a
fresh process.

Actions also run directly from an IDE — `robolink.Robolink()` attaches to the
running RoboDK either way.

### 7. Package

```bash
python scripts/robodk_addin.py package path/to/WeldUtilities
```

An `.rdkp` is an OPC ZIP (like `.docx`/`.xlsx`): `_rels/.rels`,
`[Content_Types].xml` and the package icon sit at the archive root, and the
App's own folder — containing `AppConfig.ini`, `manifest.xml`,
`core_properties.xml` and the scripts — is nested one level down. A package
built without that wrapping folder installs its files loose into `Apps/`; one
missing `_rels/.rels` is not recognized as installable at all, even if every
other file in it is valid. `package` builds all of this correctly; running
`sync` first keeps `manifest.xml`/`core_properties.xml` in step with disk.

[references/packaging.md](references/packaging.md) covers `manifest.xml`/
`core_properties.xml` fields, install locations, dependency gating,
`requirements.txt`, compiled distribution and Marketplace submission.

### 8. Reading an existing package

Handed a `.rdkp` and asked what's inside it, or to extract/modify it:

```bash
python scripts/robodk_addin.py inspect path/to/SomeAddin.rdkp        # metadata + layout, no extraction
python scripts/robodk_addin.py extract path/to/SomeAddin.rdkp [dest] # unzip
```

`inspect` follows the same `_rels/.rels` lookup RoboDK does, so it flags a
package that would actually fail to install rather than just dumping whatever
XML it finds. Both only handle plain-ZIP `.rdkp` files — the format every
openly-sourced and Marketplace Add-in uses. A package wrapped in RoboDK's
proprietary obfuscation layer (a 4-byte `RDKE` signature at the start of the
file) is detected and refused rather than guessed at — open those through
RoboDK's Add-in Manager instead. This tool never writes that layer either:
`package` only ever produces a plain, unencrypted ZIP — see
[references/packaging.md](references/packaging.md#a-note-on-encrypted-packages).

## Traps worth knowing

- **The button does nothing / never appears.** The script is not at the folder
  root, starts with `_`, or `Visible=false`. `check` catches all three.
- **The whole package fails to install, with no clear error.** A file
  anywhere inside it — script, icon, folder — has a space or a URI-reserved
  character in its name (RFC 2396); RoboDK's package format forbids both.
  `GenerateWeldPath.py`, not `Generate Weld Path.py`.
- **A `manifest.xml`-based Add-in behaves like a Classic App during
  development** (or vice versa). It's in the wrong scanned root — see
  [Anatomy](#anatomy) above: `Addins/` only reads `manifest.xml`-based
  folders, `Apps/` only reads bare-`AppConfig.ini` ones.
- **A checkable button pops back out immediately.** The script exited without
  `roboapps.KeepChecked()`.
- **Cleanup code after a `while APP.Run()` loop never runs.** RoboDK kills the
  process ~2 s after the stop request unless the script called
  `roboapps.SkipKill()`.
- **A checkable action repeats its work when unchecked.** RoboDK runs the same
  script again with `Unchecked` in `argv`; the script must branch on
  `roboapps.Unchecked()`.
- **State lost between clicks.** Different processes. Use station parameters or
  `AppSettings`.
- **Bulk edits crawl.** Wrap them in `RDK.Render(False)` … `RDK.Render(True)`,
  and restore in a `finally` so an exception doesn't leave the UI frozen.
- **A settings dialog with stale dropdown contents.** `AppSettings.__init__`
  defines the defaults and is re-run for "restore defaults"; populate
  station-dependent choices in a separate method called from `ShowUI`.
- **A hand-zipped `.rdkp` that RoboDK won't even list.** Zipping the App folder
  directly skips `_rels/.rels`, which RoboDK requires to locate the manifest —
  a missing file, not a malformed one, so nothing in `manifest.xml` itself
  will explain the failure. Use `package`, not a raw `zip`/`Compress-Archive`.

## Reference files

| File | Read it when |
| --- | --- |
| [references/actions.md](references/actions.md) | Writing or fixing an action script: the four shapes, the `roboapps` API, `AppSettings`, dialogs, sharing code, calling actions from station programs, debugging |
| [references/appconfig.md](references/appconfig.md) | Configuring the UI: every `AppConfig.ini` key with its default, item type numbers, `AppLink.ini`, a full example |
| [references/robolink.md](references/robolink.md) | Writing the logic: the RoboDK API calls Add-ins use most, with exact signatures |
| [references/packaging.md](references/packaging.md) | Shipping and reading: `manifest.xml`/`core_properties.xml`, `.rdkp` layout, install locations, dependencies, compiled packages, Marketplace, `inspect`/`extract` |
| [references/manifest.template.xml](references/manifest.template.xml) | Starting a `manifest.xml` from scratch: a copy-pasteable, fully-commented template in the single-file embedded-`coreProperties` form |

Upstream sources: the [Add-ins documentation](https://robodk.com/doc/en/Add-ins.html),
the [App API docs](https://robodk.com/doc/en/PythonAPI/app.html), and the
[AppLoader repository](https://github.com/RoboDK/Plug-In-Interface/tree/master/PluginAppLoader)
whose `Apps/` folder holds `AppTemplate` plus a dozen production Add-ins worth
reading when you need a pattern this skill doesn't cover.
