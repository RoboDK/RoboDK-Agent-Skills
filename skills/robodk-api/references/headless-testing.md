# Running RoboDK headless

Two distinct use cases share the same underlying flags: (A) quickly verifying a script against a
real RoboDK instance while developing, and (B) running RoboDK unattended on a server/CI/container
with no display. Both go through the same `-NOUI`/`-SKIPINI`/license mechanism — the difference
is just where you're launching from.

## Rule: never launch the executable/`.app` path yourself

No `open -a RoboDK.app`, no `subprocess`/`os.system` on `getPathRoboDK()`'s path, no polling for
port 20500 in a loop. Always let `Robolink(args=[...])` launch RoboDK — including when debugging
something that looks launch-related (a licensing error, a slow start, ...). If RoboDK is
installed, plain `Robolink()` already auto-launches it from `getPathRoboDK()`.

## (A) Quick script verification — the `ROBODK_AI` environment variable

```python
from robodk import robolink

with robolink.Robolink() as RDK:
    # ... exercise the script against RDK ...
    pass
```

Set `ROBODK_AI=noui` in the process environment before running this script — bash:
`ROBODK_AI=noui python script.py`; PowerShell: `$env:ROBODK_AI = "noui"; python script.py`.
`Robolink.__init__` reads `ROBODK_AI` and fills in `["-NOUI", "-NEWINSTANCE", "-SKIPINI",
"-Settings=LicenseLoad", "-EXIT_LAST_COM", "-API_NODELAY"]` automatically — only args not already
present in an explicit `args=[...]` are added, so passing `args=[...]` yourself still takes
precedence for anything you need to override.

**Prefer `ROBODK_AI` over hardcoding these args in the script.** The script body above is
identical whether it's being run headlessly for verification or normally by the end user — unset
`ROBODK_AI` and it's a plain windowed `Robolink()` that attaches to whatever is already open.
Don't branch script logic on headlessness, and don't write `args=["-NEWINSTANCE", "-NOUI", ...]`
by hand anymore; set the environment variable instead.

What that profile means, flag by flag:

- `-NOUI` — run without an OpenGL window.
- `-NEWINSTANCE` — force a fresh instance (won't attach to one already open). Also what gates
  `Robolink.__exit__` into calling `CloseRoboDK()` on `with`-block exit, so this profile
  self-cleans; `Robolink.__init__` moves it to the front of the argument list itself if it isn't
  already there, so you never need to order it manually.
- `-SKIPINI` — skip the user's saved settings for a faster/cleaner startup.
- `-Settings=LicenseLoad` — load the already-activated license despite `-SKIPINI` skipping the
  rest of the user's settings.
- `-EXIT_LAST_COM` — close RoboDK automatically once the last API client disconnects. **Keep this
  flag, but never rely on it alone** — verified on macOS: when a script raised an exception
  partway through (before reaching a final `CloseRoboDK()` call), the headless `-NOUI` instance
  was left running as an orphaned background process indefinitely, `-EXIT_LAST_COM`
  notwithstanding. The `with robolink.Robolink() as RDK:` form above is what actually covers
  this — `Robolink.__exit__` calls `CloseRoboDK()` even if the body raises. This applies to every
  headless run, not just ones expected to succeed — a crashing script is exactly the case
  `-EXIT_LAST_COM` was observed not to cover. Before assuming a prior run's instance is gone,
  check for leftover processes (e.g. `ps aux | grep '[R]oboDK.*-NOUI'` on macOS/Linux) and close
  any that turn up.
- `-API_NODELAY` — set `TCP_NODELAY` on the API socket at connect time (`robolink.py` reads this
  flag into `self.NODELAY` before opening the socket). Disables Nagle's algorithm, trading a
  little extra resource use for lower per-call latency; the gain is most noticeable when the API
  client is on a different machine from RoboDK, but there's no real downside for a local
  connection either.

### Need a screenshot? Use `ROBODK_AI=snapshot` instead

`-NOUI` disables real rendering at startup, not just window visibility — a screenshot taken
against a `ROBODK_AI=noui` instance comes out blank, and a post-connect `setWindowState()` call
does not recover rendering on an already-running `-NOUI` instance either. Set `ROBODK_AI=snapshot`
instead: same profile as above, but `-HIDDEN` in place of `-NOUI`, plus `-NOSPLASH` so the startup
splash screen doesn't flash visibly before the hidden state takes effect. The script itself still
doesn't change — only the environment variable value does.

**`-HIDDEN` rendering is platform-dependent.** On macOS it keeps real rendering with the window
merely not shown (verified). **On Windows it does not** —
verified on Windows 11 + RoboDK 6.0.0.26413, `Command('Snapshot', path)` against a `-HIDDEN`
instance produces a 120-byte blank PNG at both 0.5 s and 3 s after `Render(True)` (not a timing
issue), while the same station rendered from a visible window produces a real 118 KB image. On
Windows, take screenshots from a visible instance instead: `ROBODK_AI` unset (or
`args=["-NEWINSTANCE"]`), `setWindowState(WINDOWSTATE_MAXIMIZED)`, `Render(True)`,
`Command('FitAll')`, then snapshot. Linux is untested.

Whatever the platform, **verify the snapshot has real content** — check the file size is well
above a few hundred bytes, or decode it and confirm more than one pixel colour. A blank snapshot
is a valid PNG and raises nothing.

If you ever need the explicit args instead of the environment variable (e.g. overriding just one
flag while keeping the rest), the two profiles are:
`args=["-NEWINSTANCE", "-NOUI", "-SKIPINI", "-Settings=LicenseLoad", "-EXIT_LAST_COM", "-API_NODELAY"]`
(noui) and the same with `-NOUI` swapped for `-HIDDEN`, `-NOSPLASH` (snapshot).

**Keep headless testing simulation-only.** None of the flags above touch this: an unattended
headless instance is exactly the wrong place to have `Connect()` reach a physical robot or to
exercise `RUNMODE_RUN_ROBOT` — there's no GUI, no operator watching, and no easy way to e-stop.
Test scripts run this way should stay in `RUNMODE_SIMULATE` (the default) and never call
`Connect()` against a real robot controller.

**Linux doesn't need `--platform minimal` added manually** — the current Python binding
auto-prepends it whenever `-NOUI` is passed without an existing `--platform` argument (see
`robolink.py`'s `Robolink.__init__`).

**Linux-specific caveat: `LD_LIBRARY_PATH` can still be needed even here.** `getPathRoboDK()`
resolves to the raw binary (`~/RoboDK/bin/RoboDK`), not a wrapper script — `Robolink`'s own
auto-launch invokes that binary directly via `subprocess.Popen`, with no environment setup of its
own. `RoboDK-Start.sh` (see (B) below) exists specifically to set `LD_LIBRARY_PATH` and Qt plugin
paths before invoking that same binary — a `Robolink(args=[...])` auto-launch skips that
entirely. If RoboDK fails to start (or crashes silently) under `Robolink(args=[...])` on Linux
with no obvious error, set `LD_LIBRARY_PATH` to `RoboDK/bin/lib` in the environment *before*
running your Python script, the same as you would for a manual launch.

**The `ROBODK_AI` environment variable is how you verify your own scripts — it isn't something to
show the user or write into the script.** Since the script body stays plain `with
robolink.Robolink() as RDK:` either way, there's no code-level distinction to hide anymore; just
don't set `ROBODK_AI` (or mention it) when presenting the script to the user — run it that way
only for your own verification, along with `close_std_out` and printing `RDK.License()` to
confirm the script actually works against a live instance. Only surface headless/licensing
mechanics at all if the user specifically asks about testing or licensing.

## Watching RoboDK's own console output

`close_std_out` defaults to `False` in `Robolink(...)` — RoboDK's console output (startup,
licensing, errors) streams through by default. Read it when something looks wrong instead of
assuming silence or filtering it away; pass `close_std_out=True` only if you deliberately want it
hidden.

`close_std_out` also accepts a **callable** instead of a bool:

```python
RDK = robolink.Robolink(close_std_out=print)  # or your own logging function
```

Each line of RoboDK's console output is routed through the callback instead of inherited stdout
— useful for capturing or filtering it programmatically.

## (B) Server/CI/container headless run (Linux)

RoboDK can run on Linux/Ubuntu x86_64 without a screen or GPU — a server, CI, or container (an
official [Docker image](https://hub.docker.com/r/robodk/robodk) also exists). This is
independent of which language connects to it: once the headless instance is listening on port
20500, `Robolink()` / `RoboDK RDK;` / etc. connect exactly as they would to a windowed instance.
Full current recipe (package list, license flags):
**[`Python/README.md#headless-run`](https://github.com/RoboDK/RoboDK-API/tree/master/Python#headless-run)**.

Key points:

- Install with `./Install-RoboDK install --platform minimal ...` — the `minimal` platform skips
  GPU/X11 deps, but still needs a handful of `libxcb-*` / `libxkbcommon-x11-0` / `libgl1` /
  `libegl1` packages installed first (`apt-get install`).
- Start with `RoboDK --platform minimal -NOUI -SKIPINI ...` — same flags as above, invoked
  directly on the binary rather than through `Robolink(args=[...])`.
- License: `-LCMD=Network:<code>` / `-LCMD=Standalone:<code>` on the command line, a
  `startup.rdklic` file next to the binary (`RoboDK/bin/startup.rdklic`, picked up automatically
  even with `-SKIPINI`), or `-Settings=LicenseLoad` to load an already-activated license despite
  `-SKIPINI`.
- If shared libraries aren't found at startup, set `LD_LIBRARY_PATH` to `RoboDK/bin/lib` — this
  applies to a `Robolink(args=[...])` auto-launch too, not just a manual shell launch; see the
  caveat under (A) above.

For updating an existing Linux install (not just a first-time setup) and the command-line
license-activation gotchas (a logged `OK` doesn't mean the license is actually active), see
**`references/linux-update-and-license.md`**.
