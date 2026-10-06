# AppConfig.ini reference

`AppConfig.ini` is the file the AppLoader reads to turn an Add-in folder's
scripts into menu entries and toolbar buttons — labels, ordering, shortcuts,
checkable behaviour, context-menu placement. RoboDK generates one with
defaults the first time it discovers a new folder, but ship your own so the
labels, ordering and behaviour are yours rather than guessed.

> **Classic Apps status.** A bare `AppConfig.ini` folder with no `manifest.xml`
> next to it still loads — RoboDK will always support it — but it is the
> fallback path (internally `Addin::StandardLegacy`): package identity is
> scraped out of `[General]/MenuName` and `Version`, and there is nowhere to
> put an identifier, keywords, or a dependency/asset list. In practice this
> fallback is rare: every App in RoboDK's own catalogs, old and new (including
> Classic Apps distributed through the AppLoader plugin — RoboDK's open-source
> App Loader shipped September 2019; the closed-source Add-in Manager
> replaced it as the primary way to install Add-ins in February 2023, and
> still loads Classic Apps alongside modern ones), ships a
> `manifest.xml` alongside its `AppConfig.ini` — the two files answer
> different questions, not competing versions of the same one. `AppConfig.ini`
> still owns everything on this page (menus, toolbar, shortcuts, context
> menus); `manifest.xml` owns package identity and distribution metadata —
> see [packaging.md](packaging.md). Ship both. Separately, there is an older
> *packaging* format tied to the AppLoader plugin — a flat zip with no OPC
> container — that is also still readable and distinct from the modern
> `.rdkp`; see [packaging.md](packaging.md#the-classic-apps-package-flat-zip).

The file is read with Qt's `QSettings` INI backend. That means booleans are
`true`/`false` (lowercase), keys are case-sensitive, and a list value is written
as comma-separated (`5, 3`). Values are not quoted.

## Contents

- [Discovery rules](#discovery-rules)
- [\[General\] section](#general-section)
- [Action sections](#action-sections)
- [Item type numbers](#item-type-numbers-for-typeoncontextmenu--typeondoubleclick)
- [AppLink.ini](#applinkini)
- [Worked example](#worked-example)

## Discovery rules

These come from the AppLoader itself, and knowing them prevents most "my button
doesn't appear" problems:

| Rule | Consequence |
| --- | --- |
| One subfolder of `Apps/` = one Add-in | Each gets its own menu and its own toolbar |
| Only **root-level** files become actions | The loader is not recursive; helper modules can live in subfolders and never risk becoming buttons |
| Only `.py` and `.exe` become actions | Everything else is data |
| A leading `_` means "skip" | `_AppUtilities.py` is a shared module, not an action; a folder named `_Draft` is skipped entirely |
| `__init__.py` (exact name) at the root | RoboDK adds the parent `Apps` folder to `PYTHONPATH`, so other scripts can `from MyApp import Action` |
| `requirements.txt` at the root | RoboDK pip-installs the listed packages when the App loads |
| Icon = same basename as the script | `.svg` wins, then `.png`, `.jpg`, `.ico`. `<Name>Checked.svg` is used while a checkable action is checked |

The INI section name for an action is the filename without its extension:
`ExportCsv.py` → `[ExportCsv]`.

## [General] section

| Key | Default | Meaning |
| --- | --- | --- |
| `MenuName` | folder name | Label of the App's menu and toolbar |
| `MenuParent` | *(empty)* | Empty gives the App its own top-level menu. Set to an existing menu id to nest it: `menu-File`, `menu-Edit`, `menu-Program`, `menu-Tools`, `menu-Utilities`, `menu-Connect`, `menu-Help` |
| `MenuPriority` | `50` | Ordering against *other* Apps; lower shows first |
| `MenuVisible` | `true` | `false` hides the menu (useful when the App is toolbar- or context-menu-only) |
| `ToolbarArea` | `2` | Docking area: `1` left, `2` right, `4` top, `8` bottom, `-1` RoboDK default |
| `ToolbarSizeRatio` | `1.5` | Icon size relative to RoboDK's default toolbar |
| `RunCommands` | *(empty)* | RoboDK API commands executed when the toolbar loads |
| `Version` | `1.0.0` | App version shown in the Add-in Manager |
| `GroupContextMenu` | `false` | `true` nests all of this App's context-menu actions under one submenu named after the App instead of listing them flat among every other App's entries |

RoboDK also writes an `Enabled` key here in older versions; leave it out of
source control and let RoboDK manage the enabled state. Some older Apps also
carry a `MenuParentOld` key alongside `MenuParent` — an observed migration
artifact, not something to hand-author.

## Action sections

One section per action script. Every key is optional — these are the loader's
own defaults if you omit them.

| Key | Default | Meaning |
| --- | --- | --- |
| `DisplayName` | filename | Text in the menu and under the toolbar button |
| `Description` | filename | Tooltip on hover |
| `Visible` | `true` | `false` removes the action entirely |
| `Shortcut` | *(empty)* | Keyboard shortcut, e.g. `Ctrl+Shift+P` |
| `Checkable` | `false` | `true` makes the button a toggle — see [actions.md](actions.md) for what your script must do |
| `CheckableGroup` | `-1` | Any value > 0 groups checkable actions into a radio set: checking one unchecks its peers |
| `AddToMenu` | `true` | `false` keeps it off the menu (toolbar/context only) |
| `AddToToolbar` | `true` | `false` keeps it off the toolbar |
| `Priority` | `50` | Ordering *within* this App; lower shows first |
| `TypeOnContextMenu` | *(empty)* | Show in the right-click menu of these item types. `-1` = any type, or a comma-separated list of item type numbers |
| `TypeOnDoubleClick` | *(empty)* | Run when the user double-clicks these item types. Same format |
| `DeveloperOnly` | `false` | `true` hides it unless RoboDK is in developer mode |

A convention worth following: give actions priorities in steps of 10 (`10`, `20`,
`30`…) so you can insert one later without renumbering everything.

## Item type numbers for TypeOnContextMenu / TypeOnDoubleClick

These are the `robolink.ITEM_TYPE_*` constants. Use `-1` for "any item".

| Value | Constant | Item |
| --- | --- | --- |
| `1` | `ITEM_TYPE_STATION` | Station (.rdk) |
| `2` | `ITEM_TYPE_ROBOT` | Robot |
| `3` | `ITEM_TYPE_FRAME` | Reference frame |
| `4` | `ITEM_TYPE_TOOL` | Tool / TCP |
| `5` | `ITEM_TYPE_OBJECT` | Object (mesh) |
| `6` | `ITEM_TYPE_TARGET` | Target |
| `7` | `ITEM_TYPE_CURVE` | Curve |
| `8` | `ITEM_TYPE_PROGRAM` | Program |
| `9` | `ITEM_TYPE_INSTRUCTION` | Program instruction |
| `10` | `ITEM_TYPE_PROGRAM_PYTHON` | Python program / macro |
| `11` | `ITEM_TYPE_MACHINING` | Machining project |
| `12` | `ITEM_TYPE_BALLBARVALIDATION` | Ballbar validation |
| `13` | `ITEM_TYPE_CALIBPROJECT` | Calibration project |
| `17` | `ITEM_TYPE_FOLDER` | Folder |
| `18` | `ITEM_TYPE_ROBOT_ARM` | Robot arm |
| `19` | `ITEM_TYPE_CAMERA` | Camera |
| `20` | `ITEM_TYPE_GENERIC` | Generic item |
| `21` | `ITEM_TYPE_ROBOT_AXES` | External axes |
| `22` | `ITEM_TYPE_NOTES` | Notes |

Example — an action offered when right-clicking a robot or a program:

```ini
TypeOnContextMenu=2, 8
```

## AppLink.ini

For development you usually don't want to keep copying your working tree into
RoboDK's Add-in folder. Create a stub folder containing only an `AppLink.ini`
that points at the real source — **under `C:/RoboDK/Addins/` for a
`manifest.xml`-based Add-in, or `C:/RoboDK/Apps/` for a Classic App**; RoboDK
scans the two as separate roots and only reads `manifest.xml` for folders
found under `Addins/`, so a stub in the wrong one loads your Add-in in the
wrong mode:

```ini
[General]
Path="D:/GitHub/MyAddin"
```

Use forward slashes or escaped backslashes (`D:\\GitHub\\MyAddin`) — a single
backslash is an escape character in this format. If the folder also contains an
`AppConfig.ini` (or a Classic Apps `Settings.ini`), that takes priority and the
`AppLink.ini` is ignored, so the link folder should hold nothing else.

The Add-in Manager's **Create Add-in ➔ Link to an existing Add-in** does the same
thing through the UI.

## Worked example

An App with a top-level menu, one momentary action, one checkable action that
runs a background loop, a pair of mutually exclusive options, and a settings
dialog hidden from the toolbar:

```ini
[General]
MenuName=Weld Utilities
MenuParent=
MenuPriority=40
MenuVisible=true
ToolbarArea=2
ToolbarSizeRatio=1.5
RunCommands=
Version=1.2.0

[GenerateWeldPath]
DisplayName=Generate Weld Path
Description=Create a weld path from the selected curve
Visible=true
Shortcut=Ctrl+Shift+W
Checkable=false
CheckableGroup=-1
AddToMenu=true
AddToToolbar=true
Priority=10
TypeOnContextMenu=7
TypeOnDoubleClick=
DeveloperOnly=false

[MonitorTemperature]
DisplayName=Monitor Temperature
Description=Continuously poll the welder temperature
Visible=true
Shortcut=
Checkable=true
CheckableGroup=-1
AddToMenu=true
AddToToolbar=true
Priority=20
TypeOnContextMenu=
TypeOnDoubleClick=
DeveloperOnly=false

[UnitsMetric]
DisplayName=Metric units
Description=Report distances in millimeters
Visible=true
Shortcut=
Checkable=true
CheckableGroup=1
AddToMenu=true
AddToToolbar=false
Priority=30
TypeOnContextMenu=
TypeOnDoubleClick=
DeveloperOnly=false

[UnitsImperial]
DisplayName=Imperial units
Description=Report distances in inches
Visible=true
Shortcut=
Checkable=true
CheckableGroup=1
AddToMenu=true
AddToToolbar=false
Priority=31
TypeOnContextMenu=
TypeOnDoubleClick=
DeveloperOnly=false

[Settings]
DisplayName=Settings
Description=Edit the Weld Utilities settings
Visible=true
Shortcut=
Checkable=false
CheckableGroup=-1
AddToMenu=true
AddToToolbar=false
Priority=100
TypeOnContextMenu=
TypeOnDoubleClick=
DeveloperOnly=false
```
