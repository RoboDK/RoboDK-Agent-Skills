# Packaging, installing and publishing

## Contents

- [Package types](#package-types)
- [Install locations](#install-locations)
- [The development loop](#the-development-loop)
- [Package metadata: core_properties.xml and manifest.xml](#package-metadata-core_propertiesxml-and-manifestxml)
- [Building the .rdkp](#building-the-rdkp)
- [The Classic Apps package (flat zip)](#the-classic-apps-package-flat-zip)
- [Reading and extracting](#reading-and-extracting)
- [A note on encrypted packages](#a-note-on-encrypted-packages)
- [Dependencies](#dependencies)
- [Asset target variables](#asset-target-variables)
- [Python requirements](#python-requirements)
- [Shipping compiled code](#shipping-compiled-code)
- [Publishing to the Marketplace](#publishing-to-the-marketplace)

## Package types

A `.rdkp` isn't only an App. `<cp:category>` (or the bare `<category>` in a
standalone `core_properties.xml`) names which of these it is — these are the
literal strings the loader matches, spaces included:

| `category` string | What it is |
| --- | --- |
| `Application` | An App: Python scripts (and optionally `.exe`) plus `AppConfig.ini`, adding toolbar/menu/context-menu entries — what this skill is mainly about |
| `Plugin` | A native dynamic library (`.dll`/`.so`/`.dylib`) loaded into the RoboDK process itself, for changes an App can't make |
| `Robot Driver` | A Python script or executable connecting RoboDK to a specific robot controller |
| `Post Processor` | A Python script generating robot-specific program code (KRL, RAPID, …) |
| `Language` | A Qt `.qm` translation file |
| `Bundle` | Several add-ins of any of the above types packaged together (e.g. two Apps and a Post Processor in one `.rdkp`) — its assets can themselves be other packages with their own manifests |
| `Deploy` | Arbitrary files unpacked to any location under RoboDK's install root, not necessarily `Apps`/`Addins` — see [Asset target variables](#asset-target-variables) |

## Install locations

RoboDK installs a package into one of two roots, and the folder name differs
by whether the package is modern (`category=Application` with a
`manifest.xml`) or a [Classic App](appconfig.md) — Classic packages always go
under `Apps`, never `Addins`:

| OS | Scope | Standard (`Addins`) | Classic Apps (`Apps`) |
| --- | --- | --- | --- |
| Windows | User | `%APPDATA%/RoboDK/Addins` | `%APPDATA%/RoboDK/Apps` |
| Windows | Global | `<RoboDK Installation Folder>/Addins` | `<RoboDK Installation Folder>/Apps` |
| macOS | User | `~/Library/Application Support/RoboDK/Addins` | `~/Library/Application Support/RoboDK/Apps` |
| Linux | User | `~/.local/share/RoboDK/Addins` | `~/.local/share/RoboDK/Apps` |

- **Global storage** — available to every user of the machine; needs write
  access to the program folder.
- **User storage** — the right choice when RoboDK is installed somewhere the
  user cannot write.

The Add-in Manager decides between these two roots when installing; don't
hardcode a path. `Deploy`-type add-ins are the one exception — their files can
land anywhere under the RoboDK install root, per-asset, via the `target`
attribute (see [Asset target variables](#asset-target-variables)).

> **File naming.** RoboDK packages follow the file-naming rule from the OPC
> spec: no file inside a `.rdkp` — action script, icon, asset, folder — may
> have a space in its name, or a character reserved in a URI (RFC 2396).
> `Generate Weld Path.py` breaks the package; `GenerateWeldPath.py` doesn't.

## The development loop

1. Create the folder (`robodk_addin.py new ...` or by hand).
2. Make RoboDK see it — either put it directly in `Addins/` (see
   [Install locations](#install-locations) — use `Apps/` instead only for a
   [Classic App](appconfig.md) with no `manifest.xml`), or keep it in your own
   repo and link it: **Tools ➔ Add-in Manager ➔ Create Add-in ➔ Link to an
   existing Add-in** (creates the stub in the right root for you), or drop an
   `AppLink.ini` in a stub folder under `Addins/` yourself (see
   [appconfig.md](appconfig.md#applinkini)).
3. Enable it in the Add-in Manager.
4. After editing scripts or `AppConfig.ini`, right-click the App ➔ **Reload**.
   RoboDK does not watch the folder for changes. Reload rebuilds the menu and
   toolbar from the INI; changes to a script body take effect on the next click
   without reloading, since each click launches a fresh process.
5. Right-click ➔ **Terminate** kills a stuck checkable action.

## Package metadata: core_properties.xml and manifest.xml

A `.rdkp` is an OPC package — the same ZIP-based container model `.docx` and
`.xlsx` use. Its metadata is split into two parts and discovered through
`_rels/.rels` rather than by a fixed filename:

- **`core_properties.xml`** — Dublin Core fields: title, identifier, version,
  description, author, category, revision.
- **`manifest.xml`** — RoboDK-specific extras (website, docs, repository,
  company, email, icon) plus the `<assets>` list of installed files.

RoboDK's loader also accepts the `coreProperties` fields embedded directly
inside `manifest.xml` (a `<coreProperties>` element next to `<extraProperties>`
and `<assets>`) instead of a separate `core_properties.xml` — so during
development you can maintain a single `manifest.xml` by hand. The packaged
`.rdkp` still ships them as two separate OPC parts tied together by
`_rels/.rels` (below), and `sync`/`package` always emit both when they build
it. [manifest.template.xml](manifest.template.xml) is a copy-pasteable,
fully-commented starting point in this single-file form.

`robodk_addin.py sync` regenerates both from `AppConfig.ini` and the files on
disk while preserving whatever metadata you have already filled in — worth
running before every release, since a file missing from `<assets>` is a file
that does not get installed:

```xml
<!-- core_properties.xml -->
<?xml version='1.0' encoding='utf-8'?>
<coreProperties xmlns="http://schemas.openxmlformats.org/package/2006/metadata/core-properties"
                xmlns:dc="http://purl.org/dc/elements/1.1/"
                xmlns:dcterms="http://purl.org/dc/terms/"
                xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <category>Application</category>
  <contentStatus>Final</contentStatus>
  <dcterms:created xsi:type="dcterms:W3CDTF">2024-05-02T10:00:00.000000Z</dcterms:created>
  <dc:creator>Your Name</dc:creator>
  <dc:description>One-line description of the Add-in.</dc:description>
  <dc:identifier>com.yourcompany.app.weldutilities</dc:identifier>
  <keywords>welding, path</keywords>
  <dc:language>eng</dc:language>
  <lastModifiedBy>Your Name</lastModifiedBy>
  <dcterms:modified xsi:type="dcterms:W3CDTF">2024-05-02T10:00:00.000000Z</dcterms:modified>
  <revision>1</revision>
  <dc:title>Weld Utilities</dc:title>
  <version>1.2.0</version>
</coreProperties>
```

```xml
<!-- manifest.xml -->
<?xml version='1.0' encoding='utf-8'?>
<packageManifest xmlns="http://schemas.robodk.com/package/2022/manifest" version="1.0">
  <extraProperties>
    <website>https://example.com/</website>
    <documentation>https://example.com/docs</documentation>
    <repository>https://github.com/you/weld-utilities</repository>
    <company>Your Company</company>
    <email>support@example.com</email>
    <icon>/icon.svg</icon>
  </extraProperties>
  <assets>
    <asset cpu="any" system="any" target="$(SourcePath)">/WeldUtilities/AppConfig.ini</asset>
    <asset cpu="any" system="any" target="$(SourcePath)">/WeldUtilities/GenerateWeldPath.py</asset>
    <!-- one entry per file, path prefixed with the App folder name -->
  </assets>
</packageManifest>
```

A real, trimmed example from RoboDK's own `CurveUtilities` App — this is what
you get for free by embedding `coreProperties` in `manifest.xml` rather than
maintaining a separate file, and the exact namespace prefixes (`cp:`, `dc:`)
RoboDK's own writer produces:

```xml
<packageManifest xmlns="http://schemas.robodk.com/package/2022/manifest" version="1.0"
                  xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties"
                  xmlns:dc="http://purl.org/dc/elements/1.1/">
  <cp:coreProperties>
    <cp:category>Application</cp:category>
    <dc:identifier>com.robodk.app.curveutilities</dc:identifier>
    <dc:title>Curve Utilities</dc:title>
    <cp:version>2.2.5</cp:version>
  </cp:coreProperties>
  <extraProperties>
    <website>https://robodk.com/</website>
    <documentation>https://github.com/RoboDK/Plug-In-Interface/tree/master/PluginAppLoader/Apps/CurveUtilities</documentation>
    <company>RoboDK Global, SLU</company>
    <email>info@robodk.com</email>
    <icon>/icon.svg</icon>
  </extraProperties>
</packageManifest>
```

Field notes:

| Field | Notes |
| --- | --- |
| `category` | `Application` for an App — see [Package types](#package-types) for the full list of literal strings (some contain spaces, e.g. `Post Processor`) |
| `dc:identifier` | Reverse-domain and unique: `domain.company.type.name`, letters, digits, `-`, `.`, `_`. This is the package's identity across updates — never change it |
| `version` | Semantic `major.minor.patch`; keep it in step with `Version` in `AppConfig.ini` |
| `revision` | Integer, starts at 1, bumped for a repackage of the same version |
| `extraProperties/icon` | Package-root-relative path to the icon shown in the Add-in Manager — `/icon.svg` means a file sitting next to the App folder inside the ZIP, not inside it (see below) |
| `asset/@target` | `$(SourcePath)` installs the file into the Add-in's own folder — see [Asset target variables](#asset-target-variables) for the rest |
| `asset/@cpu`, `@system` | `any`, or restrict a file to a platform/architecture — real Apps almost always leave both `any`; per-platform assets show up mainly on compiled Plugins (see below) |
| `asset/@type` | Seen as `type="entrypoint"` on the one asset (per `cpu`/`system` pair) that is the actual loadable binary among several platform variants — e.g. a compiled Plugin shipping a `.dll`/`.so`/`.dylib` trio |

A compiled/native package (a RoboDK Plugin rather than a Python App, but the
same `<assets>` mechanism applies to any Add-in that bundles a
platform-specific binary — a helper `.exe`, a vendored `.pyd`/`.so` a script
loads via `ctypes`) targets one binary per platform this way:

```xml
<assets>
  <asset cpu="x86_64" system="windows" type="entrypoint">/PostProcessorEditor.dll</asset>
  <asset cpu="x86_64" system="linux" type="entrypoint">/libPostProcessorEditor.so</asset>
  <asset cpu="any" system="mac" type="entrypoint">/libPostProcessorEditor.dylib</asset>
  <asset cpu="any" system="any">/README.md</asset>
</assets>
```

`_rels/.rels` is what ties the two parts together — and it is required, not
optional. RoboDK finds `core_properties.xml` and `manifest.xml` exclusively by
following its relationships, so a ZIP that has a perfectly valid `manifest.xml`
but no `_rels/.rels` is not recognized as an installable package at all:

```xml
<!-- _rels/.rels -->
<?xml version='1.0' encoding='utf-8'?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties"
               Target="/WeldUtilities/core_properties.xml" Id="rId1"/>
  <Relationship Type="http://schemas.robodk.com/package/2022/relationships/manifest"
               Target="/WeldUtilities/manifest.xml" Id="rId2"/>
  <Relationship Type="http://schemas.robodk.com/package/2022/relationships/appconfig"
               Target="/WeldUtilities/AppConfig.ini" Id="rId3"/>
</Relationships>
```

A `[Content_Types].xml` sibling (per-extension MIME defaults plus an Override
for the core-properties part) rounds out a well-formed OPC package; `sync` and
`package` handle all three files for you.

## Building the .rdkp

An `.rdkp` is a ZIP that mixes OPC container parts at the root with the App's
own folder:

```
WeldUtilities.rdkp
├── _rels/.rels              <- required; points RoboDK at the two parts below
├── [Content_Types].xml
├── icon.svg                 <- the package icon, a sibling of the App folder
└── WeldUtilities/
    ├── AppConfig.ini
    ├── core_properties.xml
    ├── manifest.xml
    ├── GenerateWeldPath.py
    └── ...
```

Two things are worth getting right on purpose here:

- **The App folder wrapping.** An archive that contains the App's files at its
  own root — instead of nested one level down in a folder named after the
  App — installs them loose into the install directory rather than into their
  own folder.
- **The icon's position.** It sits next to the App folder, not inside it,
  because `manifest.xml`'s `<icon>` path is resolved relative to the package
  root; nesting it under the App folder while still writing `/icon.svg` in the
  manifest means RoboDK looks for it in the wrong place.

```bash
python scripts/robodk_addin.py package path/to/WeldUtilities
```

The script builds `_rels/.rels`, `[Content_Types].xml`, `core_properties.xml`
and `manifest.xml`, places the icon at the package root, excludes
`__pycache__`, `*.pyc`, `.git` and editor cruft, and refuses to write the
package inside the App folder. RoboDK's own `Apps/PackageCreate.py` does the
same job from within an `Apps` tree, and can bundle several Apps into one
package by running it with no arguments.

Double-clicking an `.rdkp` opens it with RoboDK, which installs the package.

## The Classic Apps package (flat zip)

Before the Add-in Manager, the (now obsolete) AppLoader plugin shipped Apps —
what RoboDK calls **Classic Apps** — as a **plain zip with no OPC container at
all**: no `_rels/.rels`, no `[Content_Types].xml`, just one or more
`<AppFolder>/AppConfig.ini` (and its siblings) sitting two levels deep in the
archive. RoboDK's own `Apps/PackageCreate.py` / `PackageCreateOne.py` still
build packages this way, and RoboDK still recognizes and installs them — it
detects any entry matching `*/AppConfig.ini` and deploys every file under that
top-level folder loose, independent of whether a `manifest.xml` happens to be
present too.

This is a different axis from the "Classic Apps `AppConfig.ini`-only vs.
modern `manifest.xml`" distinction in [appconfig.md](appconfig.md) — it's
about the **container**, not the metadata. A folder can have a full
`manifest.xml` and still be shipped as a flat zip if it was built with the old
tooling. `scripts/robodk_addin.py package`
only builds the modern OPC layout; if you specifically need to reproduce the
old flat format (e.g. testing against an AppLoader-era installer), zip the App
folder(s) directly instead of using `package`.

## Reading and extracting

```bash
python scripts/robodk_addin.py inspect path/to/WeldUtilities.rdkp        # metadata + layout
python scripts/robodk_addin.py inspect path/to/WeldUtilities.rdkp -l     # + full file listing
python scripts/robodk_addin.py extract path/to/WeldUtilities.rdkp [dest] # unzip
```

`inspect` follows `_rels/.rels` the same way RoboDK does, so it reports a
package that would actually fail to install — a missing `_rels/.rels`, or a
manifest/core-properties part it only found by filename instead of by
relationship — rather than just dumping whatever XML happens to be inside.
Both commands work on any plain-ZIP `.rdkp`, which covers every
openly-sourced and Marketplace package.

Some commercially distributed `.rdkp` files are wrapped in an additional,
proprietary packaging layer instead of a plain ZIP (detectable by a 4-byte
`RDKE` signature at the start of the file). `inspect` and `extract` detect
that and refuse rather than guessing at reversing it — open those through
RoboDK's Add-in Manager directly.

## A note on encrypted packages

`scripts/robodk_addin.py` cannot produce that proprietary encrypted/obfuscated
`.rdkp` format, and that's by construction, not by an unenforced convention:
the script imports nothing but the Python standard library (`argparse`,
`configparser`, `zipfile`, `xml.etree`, …) — there is no cryptography
dependency anywhere in it for an encryption step to use. `package` always
writes a plain `zipfile.ZIP_DEFLATED` archive; `check_not_encrypted()` and the
`RDKE_SIGNATURE` constant exist solely to *detect and refuse* an already-
encrypted input to `inspect`/`extract`, never to produce one. Reproducing
RoboDK's proprietary layer is intentionally out of scope for this tool.

## Dependencies

The Add-in Manager can gate installation on conditions: a `<dependencies>`
block of `<dependency>` elements, each checked at install time. There is no
version-interval syntax — a version check is an **exact match** against one
version number, and every other check is either an exact string match or a
regular expression:

| Attribute | Meaning |
| --- | --- |
| `type` | What to check — `versioncheck`, `cpuarchitecture`, `buildarchitecture`, `buildabi`, `kerneltype`, `system`, `fileversion`, `filemode`, `filecreated`, `filemodified` |
| `scope` | `package` (default) blocks the whole install if unmet; `asset` skips just that one asset |
| `identifier` | For `versioncheck`: which version to read — `com.robodk` (RoboDK app version), `com.robodk.addinmanager` (Add-in Manager version), `io.qt` (Qt version), `sys.kernelversion`. Unused for the other types |
| `version` | For `versioncheck` only: the exact version required (`major.minor.patch`) |
| `value` | For every other `type`: the exact string to match (case-insensitive), e.g. `windows`/`linux`/`osx` for `system`, `x86_64`/`arm64` for `cpuarchitecture`. For `filecreated`/`filemodified`, an ISO date, optionally prefixed `<` (before) or `>` (after) |
| `expression` | Same role as `value` but as a regular expression instead of an exact match — takes priority when present |
| `fileName` | Path checked for `fileversion`/`filemode`/`filecreated`/`filemodified`, e.g. `$(DeployFolder)/helper.dll` |
| `displayName` | Label shown to the user if the check fails |
| `group` | Rows sharing a `group` name are OR'd together instead of all being required |

```xml
<dependencies>
  <dependency type="versioncheck" scope="package" identifier="com.robodk"
              version="5.6.0" displayName="Requires RoboDK 5.6.0 or newer"/>
  <dependency type="system" scope="asset" value="windows"
              displayName="Windows-only helper"/>
</dependencies>
```

Use the Add-in Creator UI to author these rather than hand-editing the XML —
it writes the shape the manager expects, and an Add-in without any dependency
rules is perfectly valid. In practice it's the common case: across RoboDK's
own published App catalog, `<dependencies>` is essentially always empty and
every `<asset>` is `cpu="any" system="any"` — treat dependency gating as an
available escape hatch for a genuinely version- or platform-sensitive Add-in,
not something every package needs.

## Asset target variables

`asset/@target` is used rarely — mostly for `Deploy`-type packages that need
to land somewhere other than their own App folder — but when you need it,
these are every variable it understands. They're computed from the asset's
own path inside the package, so they're always available:

| Variable | Value |
| --- | --- |
| `$(SourcePath)` | The asset's absolute path inside the archive (the default; installs it into the Add-in's own folder) |
| `$(SourceFolder)` | Path to the asset without the file name |
| `$(SourceFileName)` | The file name, with extension |
| `$(SourceBaseName)` | File name without its last extension |
| `$(SourceSuffix)` | The last extension, no dot |
| `$(SourceCompleteBaseName)` | File name without *any* extension (for `archive.tar.gz`, that's `archive`) |
| `$(SourceCompleteSuffix)` | Every extension, no leading dot (`tar.gz`) |
| `$(DeployFolder)` | Where the package installs to; used automatically if no other `$(...Folder)` variable is given |

For `Deploy`-type add-ins only, these resolve to fixed RoboDK folders instead
(Windows paths shown; the Add-in Manager resolves the equivalent on macOS/Linux):

| Variable | Folder |
| --- | --- |
| `$(RdkFolder)` | RoboDK's main install folder — `C:/RoboDK/` |
| `$(DataFolder)` | Per-user app data — `%APPDATA%/RoboDK/` |
| `$(AddinsFolder)` | Global `Addins` folder — `C:/RoboDK/Addins/` |
| `$(AppsFolder)` | Global Classic Apps folder — `C:/RoboDK/Apps/` |
| `$(UserAddinsFolder)` | User `Addins` folder — `%APPDATA%/RoboDK/Addins/` |
| `$(UserAppsFolder)` | User Classic Apps folder — `%APPDATA%/RoboDK/Apps/` |
| `$(DriversFolder)` | Robot drivers — `C:/RoboDK/api/Robot/` |
| `$(BinFolder)` | RoboDK's executable folder — `C:/RoboDK/bin/` |
| `$(PluginsFolder)` | Native Plugins folder — `C:/RoboDK/bin/Plugins/` |
| `$(LangFolder)` | Translation files — `C:/RoboDK/Lang/` |
| `$(PostsFolder)` | Post processors — `C:/RoboDK/Posts/` |

RoboDK will only install a `Deploy` asset into one of these predefined
folders — there's no way to target an arbitrary absolute path on disk.

## Python requirements

If the Add-in needs third-party packages, add a `requirements.txt` at the App
root. RoboDK checks it when the App loads and pip-installs anything missing into
its Python environment. The UI blocks while installing, so keep the list short
and pin ranges rather than exact versions:

```
opencv-python
pyserial
numpy>=1.23
```

Omit the file entirely if you only use the standard library and `robodk` — an
unnecessary requirements check slows down every load.

## Shipping compiled code

To distribute without source, RoboDK's `Apps/CompileApp.py` compiles the scripts
to `.pyc` for each supported Python version, places them under `v37/`, `v310/`
etc., and replaces each root script with a small loader that imports the right
one and calls `runmain()`. This is the reason actions must expose `runmain()`.

It is obfuscation, not protection, and it locks the package to the Python
versions you compiled for. Ship source unless you have a specific reason not to.

## Publishing to the Marketplace

Submit at <https://robodk.com/addins> with:

- `README.md` describing the Add-in (this becomes the listing text)
- an icon (SVG, PNG or JPG)
- `manifest.xml` (the Add-in Creator can generate it)
- optionally the `.rdkp`, screenshots and screen recordings

Sharing the source is optional — a listing without it still reaches users.
