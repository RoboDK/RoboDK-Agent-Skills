# The RoboDK ↔ driver protocol

Verified against four real, shipped RoboDK drivers spanning different implementation styles — a
Python wrapper around a vendor SDK (Mecademic), a hand-rolled Python socket protocol (KUKA IIWA),
a compiled C++/Qt driver (KEBA), and a Python driver forwarding to the controller's own native
text command protocol (Dobot V4) — cross-checked against RoboDK's official documentation: the
"Robot Drivers" user guide, and the published protocol reference at
https://robodk.com/doc/en/PythonAPI/driver.html (the authoritative command/response list — when
in doubt, that page is the tie-breaker over anything inferred from example code). All four
drivers implement **the same text protocol** on stdin/stdout; only what happens *inside* each
command handler (how it actually talks to that robot's controller) differs. That protocol, not
any one language, is the real contract this skill is about.

## What a driver is, and what it is not

A driver is a standalone console program — a Python script or a compiled executable — that
RoboDK launches as a child process and talks to over its stdin/stdout. RoboDK writes command
lines to the driver's stdin; the driver writes status/result lines to its stdout, which RoboDK
reads back. The driver's own job is to translate that line protocol into whatever the real robot
controller actually speaks (a vendor Python SDK's function calls, a raw TCP/IP socket with a
proprietary message format, FTP, anything).

- **Not a post processor.** A post processor (see `robodk-post-processor-builder`) generates a
  program file for offline transfer and execution *by the controller itself*. A driver moves the
  robot live, command by command, from the PC — "Online Programming" instead of "Offline
  Programming." Different skill, different problem.
- **Not the same as *using* one.** Operating an already-working driver to move a real robot —
  `Connect()`, the mandatory confirmation protocol, safety checklist — is `robodk-real-robot-control`'s
  job. This skill is about writing, porting, or fixing the driver program itself.

Drivers live in `RoboDK/api/Robot/` in a RoboDK install (older docs and some shipped drivers
also reference `RoboDK/bin/robot/` — check both on an unfamiliar install). RoboDK links a robot
to a specific driver file via **right-click robot → Connect to robot… → More options… → Driver
path**.

## Naming convention

Name new driver files (and their compiled executables) **`Driver<BrandName>`** — e.g.
`DriverMecademic.py`, `DriverKukaIiwa.py`, `DriverKeba` (compiled). The three shipped examples
this reference is grounded in predate this convention and are named `api<brand>.py`
(`apimecademicpy.py`, `apikukaiiwa.py`) — read them as reference implementations, but don't copy
their naming pattern for anything new.

## The command protocol (RoboDK → driver, one line each via stdin)

Every command is a plain-text line, space-separated: a verb followed by numeric/string
arguments. All four reference drivers implement this same vocabulary (a couple of commands are
robot-class-specific, noted below), and it matches RoboDK's own published protocol reference:
https://robodk.com/doc/en/PythonAPI/driver.html.

| Command | Arguments | Meaning |
|---|---|---|
| `CONNECT` | `ip_or_com [port] [dof]` | Connect to the robot. `ip_or_com` is normally an IP, but RoboDK's own docs show a serial port working too (`CONNECT COM4 10000 6`) for drivers that talk over serial instead of TCP/IP. Always disconnect any existing connection first — reconnecting without disconnecting leaves stale state. |
| `DISCONNECT` | — | Disconnect from the robot. Must be handled **immediately**, not queued behind pending motion (see Architecture below). |
| `STOP` | — | Stop robot motion and clear any queued commands. Also immediate, not queued. |
| `QUIT` | — | Disconnect and terminate the driver process. |
| `CJNT` | — | Report the current joints. Response: a `JNTS ...` line. |
| `MOVJ` | `j1..jN x y z w p r` | Joint move. RoboDK sends **both** the joint values and the equivalent cartesian pose in the same line — use whichever your controller wants. The pose's Euler convention is whatever is configured in that robot's **Parameters** panel in RoboDK, not a fixed universal one — confirm it there rather than assuming. |
| `MOVL` | `j1..jN x y z w p r` | Linear move. Same argument shape and Euler-convention caveat as `MOVJ`. |
| `MOVC` | `j1..jN x y z w p r  j1..jN x y z w p r` | Circular move: via point, then end point (only on controllers that support it — KUKA IIWA driver implements this, Mecademic does not). |
| `SPEED` | `lin_speed [joint_speed] [lin_accel] [joint_accel]` | Any argument `<= 0` means "leave unchanged." Convert units/clamp to the controller's range inside the handler — RoboDK always sends its own native units (mm/s, deg/s, mm/s², deg/s²), not the controller's percentage-of-max if it uses one. |
| `SETROUNDING` (aka `SETZONE`) | `value` | Blend/rounding radius in mm. Sub-zero means exact/accurate positioning. If the controller/driver combination can't support blending in synchronous online motion, say so via a status message rather than silently ignoring it. |
| `SETTOOL` | `x y z w p r` | Set the active TCP. |
| `SETDO` | `io_name io_value [var_name var_value]` | Set a digital output. RoboDK sends **both** a numeric IO index/value and a named-variable form in the same line (`SETDO 5 1 5 1`, or `SETDO 0 0 VARNAME VALUE` for a symbolic one) — use whichever addressing style the controller wants; see also the Mecademic driver's `SETDO 0 1 Gripper 1` gripper-as-named-function handling. |
| `SETAO` | `io_name io_value [var_name var_value]` | Set an analog output. Same argument shape as `SETDO`. Easy to miss when porting/reviewing a driver since it's less commonly exercised than `SETDO`. |
| `WAITDI` | `io_name io_value [var_name var_value] [timeout]` | Wait for a digital input to reach a value. Report plainly if unimplemented rather than pretending to wait. |
| `RUNPROG` | `id name` | Run a program stored on the controller, or dispatch to a custom/vendor-specific command (see Custom commands below). |
| `SENDPROG` | `id path` | Upload/save a local program file to the controller under a given slot. |
| `POPUP` | `message` | Display a message (teach pendant or log) — implement or report unimplemented. |

Parse defensively: count the numeric values actually present (`nvalues`) and the whitespace-split
word count (`nwords`) before indexing into them, and guard every branch on the counts your
handler actually needs (`nvalues >= 6 and linecmd.startswith("MOVL")`, not a bare
`startswith("MOVL")`). All four reference drivers do this — a short or malformed line must not
crash the process the robot is depending on to receive its next `STOP`.

## The response protocol (driver → RoboDK, via stdout)

Line-prefixed, and RoboDK color-codes the connection status bar based on these. `assets/driver_template.py`
implements each of these as a named helper — reuse those names verbatim, they match the current
convention (the Dobot V4 driver names them exactly this way; older drivers like Mecademic used
different names for the same prefixes, noted below):

| Prefix | Helper | Meaning |
|---|---|---|
| `SMS:<text>` | `print_message(text)` | Status/log message, shown in **both** the connection log and the connection status bar. RoboDK recognizes specific texts for coloring: `Ready` (green), `Working...` (yellow), `Waiting...` (blue); anything else shows red. Prefer driving this through `UpdateStatus(status_code)` (below) rather than calling it with ad hoc text, so the code↔text mapping lives in one place. |
| `SMS2:<text>` | `show_message(text)` | Status bar message only — a separate channel from the connection log/status bar `print_message` drives. |
| `RE:<text>` | `print_response(text)` | Driver status/response for an API-issued driver command, e.g. what `item.setParam('Driver', some_command)` gets back on the RoboDK API side. Not the same channel as `print_message`. (Mecademic's driver calls the equivalent `set_driver_status`.) |
| `CMDLIST:<cmd\|label\|...>` | `print_commands(cmdlist)` | Sent once at startup to advertise custom/vendor-specific commands RoboDK can offer as instructions — pipe-delimited `c <call>\|<label>\|...` pairs. See `build_custom_commands()` in the template and "Custom/vendor-specific commands" below. |
| `DBG:<text>` | `print_debug(text)` | Debug/log-window message only, not status-bar. |
| `JNTS <j1> <j2> ...` | `print_joints(joints)` | Current joints, high precision (e.g. `%.6f`) — send after any command that settles into a static position (`CJNT`, end of a move). |
| `JNTS_MOVING <j1> <j2> ...` | `print_joints(joints, moving=True)` | Joints while moving, lower precision (e.g. `%.3f`) — only for controllers that support real-time position feedback; this is what makes the RoboDK simulation visibly follow the real robot during a move. Optional: not every driver/controller combination can provide it — if yours can't, just don't send this rather than faking a value. |

Always `flush()` stdout after printing — RoboDK reads these as they arrive, and buffered output
delays status updates the user (and any confirmation-driven operator flow) is relying on. Every
helper above does this already if you use them as-is.

`UpdateStatus(set_status=None)` (also in the template) is the standard way to drive `SMS:` from a
`ROBOTCOM_*` status code instead of hand-writing status text at each call site — call it with no
argument to re-send the last status (useful right after startup to flush the initial state).

## Architecture: two loops, so `STOP`/`DISCONNECT`/`QUIT` are never queued

This is a structural decision three of the four reference drivers share, in three different
languages, and it is load-bearing for safety: **reading the next line from stdin, and executing
the current command, must not be the same blocking loop.** If they were, a `MOVJ` that takes ten
seconds would make a `STOP` sent one second in wait nine seconds to even be read.

- **Mecademic (Python):** `RunConsole()` reads `sys.stdin` in the main thread and intercepts
  `DISCONNECT`/`STOP`/`QUIT` immediately; everything else is appended to a `LISTCMD` queue.
  `RunDriverThread()` starts a **daemon thread** running `RunDriver()`, which pops off `LISTCMD`
  and calls `RunCommand()` — the only place vendor-SDK calls (which block until the robot
  finishes moving) actually happen.
- **KUKA IIWA (Python):** same shape — a stdin-reading loop and a separate command-processing
  path.
- **KEBA (C++/Qt):** a dedicated `StdinThread` (`QThread`) blocks on `std::getline(cin, ...)`.
  It intercepts `QUIT`/`STOP` directly in the thread itself (calling `COM->StopRobot()` without
  going through the queue) and emits a Qt signal (`incomingData`) for everything else, which
  `ComRobot::ProcessCMD` (running on the main/event thread) handles — that's the C++ platform's
  version of the same producer/consumer split.

**Dobot V4 (Python) does not do this**, and it's worth reading as a cautionary counter-example
rather than a pattern to copy: `RunDriver()` is a single `for line in sys.stdin: RunCommand(line)`
loop with no thread/queue split at all, and `STOP`/`QUIT` are handled inside the same `RunCommand`
dispatcher as every motion command. Concretely, that means a `STOP` sent while a `MOVJ` is still
executing sits unread until that `MOVJ`'s SDK call returns — the exact failure mode this
architecture exists to prevent. Match the template/Mecademic/KUKA IIWA/KEBA pattern, not this one.

Port the two-loop pattern to whatever concurrency primitive your language offers (thread + queue,
async task + queue, signal/slot) — don't collapse it into one blocking loop for the sake of
looking simpler, even though it's the easier thing to reach for first.

## Two ways to talk to the actual robot

- **Wrap a vendor SDK** (Mecademic pattern) when the manufacturer ships one (here, the
  `mecademicpy` PyPI package). This is the least code: most command handlers are one or two SDK
  calls plus a joints/status readback. Prefer this whenever an official SDK exists.
- **Hand-roll the wire protocol** (KUKA IIWA pattern) when there's no SDK, only a documented
  message format over a raw socket — message IDs (`MSG_MOVEJ = 10`, ...), manual `struct` packing
  for binary fields, manual response parsing. More code, but sometimes the only option.
- **Compile natively** (KEBA pattern, C++/Qt) when the target platform, a required native client
  library, or performance needs push you off Python. The stdin/stdout protocol and the two-loop
  architecture are identical regardless — only the language and the robot-communication layer
  change.

## Custom/vendor-specific commands (optional, but a common real pattern)

A `c <call>` line (shorthand also reachable via `RUNPROG <id> <call>` on some drivers) lets RoboDK
invoke something outside the standard command set — advertised to the user as an instruction via
the `CMDLIST:` startup message (pipe-delimited `c <call>|<label>|...` pairs). Two real
implementations of the handler side, pick whichever fits the target controller:

- **Native pass-through (Dobot V4 driver).** If the controller already has its own text-based
  command protocol (Dobot's dashboard commands like `EnableRobot()`, `ClearError()`, `User(0)`),
  `send_custom(call)` just forwards the string straight to the controller's own command socket
  (`self.robot.send_data(call)`) and returns its reply. No parsing needed — the controller does
  the work. This is what `assets/driver_template.py`'s `Robot.send_custom()` models.
- **SDK method dispatch (Mecademic driver).** With no native text protocol, `CUSTOM_COMMANDS` is
  built from every public method of the SDK's `Robot` class, and `c <MethodName(args)>` is parsed
  and dispatched via an `eval()`-style call into the SDK. More setup, but exposes the entire
  vendor API surface without a hand-written branch per method.

Either way, the driver ends up executing whatever call string it's handed — safe in RoboDK's own
normal operation (RoboDK is the only writer of these lines), but worth being deliberate about, and
worth keeping the advertised `CMDLIST:` set limited to calls you've actually verified, if a
driver's stdin could ever come from anywhere else.

## `MOVLSEARCH` — touch/contact search moves (opt-in, not part of the default command set)

**Do not implement this by default.** It requires a physical probe/sensor wired to a digital
input, needs per-installation configuration, and most robots/drivers have no use for it. Add it
only when the user explicitly asks for touch-probing, search moves, or contact/interference
detection — `assets/driver_template.py` deliberately does not stub it out.

`MOVLSEARCH` is what `item.SearchL(target, blocking=True)` on the RoboDK API side compiles down
to — a linear move that stops as soon as a configured input condition (contact) is detected,
instead of always running to the target unmodified. Verified against the Epson driver
(`EpsonDriver.py`), the only reference driver of the four that implements it:

- **Argument shape**: identical to `MOVL` — joints then pose (`j1..jN x y z w p r`).
- **Capability query**: the Epson driver handles an incoming `SUPPORTSEARCH` command by replying
  `RE:1` (via `print_response("1")`), implying RoboDK sends it before offering/using
  `MOVLSEARCH`. **This isn't in RoboDK's own published driver protocol reference**
  (https://robodk.com/doc/en/PythonAPI/driver.html lists `MOVLSEARCH` but not `SUPPORTSEARCH`) —
  treat it as real-but-unconfirmed-as-universal behavior rather than a documented guarantee, and
  verify against the target RoboDK version rather than assuming every version sends it. Either
  way, API code should treat an empty/missing status from `item.setParam("Driver", "Status")` as
  "not supported," not as "nothing found" (see the `SearchL` docstring in `robolink.py`).
- **Result**: after the move, reply `RE:1` if contact was detected, `RE:0` if the robot reached
  the target with no contact — via `print_response("1")` / `print_response("0")`. On the API
  side this is read back with `robot.setParam("Driver", "Status")`; the joints/pose at wherever
  the robot actually stopped are then read normally (`robot.Joints()`, `robot.Pose()` — no
  separate "give me the contact point" command exists, the search move itself leaves the robot
  there).
- **Configuration is driver-specific, not part of the RoboDK protocol.** The Epson driver adds
  its own custom command, `SEARCHDI <io_number> [expected_value]`, so the operator can say which
  digital input is wired to the probe and what value on it means "contact" before any
  `MOVLSEARCH` is issued — and refuses `MOVLSEARCH` with a clear message if that hasn't been set
  yet. Expect to need an equivalent per-driver setup command (exposed via `CMDLIST:` like any
  other custom command) for whatever probe/sensor wiring the target controller uses.

If asked to add this to a driver: confirm the robot actually has a probe/touch-sensing input
wired up before writing any code — there's nothing to search for without one.

## Connecting and troubleshooting (operator perspective — also relevant while testing a new driver)

- **Vendor-side socket option.** Most robot controllers require a manufacturer-sold software
  option to allow socket communication at all — often not enabled by default. A `Connect()` that
  times out with an otherwise-healthy network is frequently this, not a driver defect.
- **Connecting from the GUI.** Right-click the robot → **Connect to robot…** → enter IP →
  **Connect**. A green **Ready** message means success; use the **ping** button in that window to
  test reachability first. **Get robot joints** pulls the real robot's current position into the
  simulated one — do this before trusting the simulated pose for planning a move.
- **Ping the robot first.** `ping <robot-ip>` — 0% packet loss before anything else. No response
  means a network problem, not a driver/RoboDK problem.
- **Same subnet / static IP.** The controlling computer and the robot controller need to be on
  the same LAN. On Windows: Control Panel → Network and Internet → Network Connections → the
  active adapter → Properties → Internet Protocol Version 4 (TCP/IPv4) → Properties, then set an
  IP/subnet compatible with the robot's.
- **Firewall.** Windows Firewall commonly blocks the driver's socket. Turn it off (or add a rule)
  while diagnosing — this is a real network security control, not a formality, so treat changing
  it with the same care as any other security-relevant change.
- **Communication port.** Confirm the port the driver expects matches what's configured/available
  on the controller side.
- **Driver process stuck / unresponsive** (typically after a real collision or axis-limit fault).
  Recovery is a **double disconnect**, not a retry loop: double-click **Disconnect** twice in the
  GUI's Robot Connection window, or call `robot.Disconnect()` **twice** from the API — both
  force-kill the driver process, then reconnect. **Warning: if the driver is Python-based, this
  can kill other Python processes/instances riding on that same driver process, not just the
  intended one** — it's a process-kill, not a graceful stop.
- **Administrator privileges** may be required on Windows for some of the above.

## Testing a driver standalone (no RoboDK needed for the first pass)

Every reference driver can run directly as a console program and accept typed commands, exactly
as documented in each file's own header comment:

```text
$ python DriverMecademic.py
CONNECT 192.168.0.100 10000
SMS:Connecting to robot 192.168.0.100
SMS:Ready
MOVJ 10 20 30 40 50 60 0 0 0 0 0 0
SMS:Working...
JNTS 10.000000 20.000000 30.000000 40.000000 50.000000 60.000000
SMS:Ready
CJNT
JNTS 10.000000 20.000000 30.000000 40.000000 50.000000 60.000000
```

This is the fastest loop while writing or debugging a new driver — verify the whole command set
by hand before ever letting RoboDK (and therefore a real robot) drive it. Once standalone testing
passes, hooking it up to RoboDK and testing against real hardware is `robodk-real-robot-control`'s
mandatory confirmation protocol, not a shortcut around it.
