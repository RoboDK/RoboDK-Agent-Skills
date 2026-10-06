#!/usr/bin/env python3
# ----------------------------------------------------------------------------
# RoboDK ROBOT DRIVER TEMPLATE
#
# A driver is a standalone console program RoboDK launches and talks to over
# stdin/stdout using a fixed line-based text protocol (see
# ../references/driver-protocol.md for the full command/response tables and
# the reasoning behind every design choice below).
#
# Name the finished file "Driver<BrandName>.py" (or the compiled equivalent)
# and place it in RoboDK/api/Robot/. Link it to a robot via:
#   right-click robot -> Connect to robot... -> More options... -> Driver path
#
# Test it standalone first, with no RoboDK involved:
#   python Driver<BrandName>.py
#   CONNECT <robot-ip>
#   CJNT
#   MOVJ 0 0 0 0 0 0  0 0 0 0 0 0
#
# Only after that passes does this belong anywhere near a real robot — and at
# that point, operating it against real hardware is robodk-real-robot-control's job
# (mandatory per-action confirmation), not something to script around here.
# ----------------------------------------------------------------------------

import sys
import threading
import time

DRIVER_VERSION = "1.0.0"

# ---------------------------------------------------------------------------
# Connection status codes RoboDK understands (match robolink's ROBOTCOM_*)
ROBOTCOM_UNKNOWN = -1000
ROBOTCOM_PROBLEMS = -3
ROBOTCOM_DISCONNECTED = -2
ROBOTCOM_NOT_CONNECTED = -1
ROBOTCOM_READY = 0
ROBOTCOM_WORKING = 1
ROBOTCOM_WAITING = 2

STDOUT_LOCK = threading.Lock()

# Note: a plain print() flushes to RoboDK's connection log window, but the
# buffer may not flush to the pipe until it fills unless you flush explicitly
# -- every helper below flushes immediately so RoboDK sees it as fast as
# possible (this matters for anything a human confirmation flow is waiting on).


def print_message(message: str) -> None:
    """Display a message in the connection log window AND the connection status
    bar of RoboDK (SMS:). The status bar has coloring: 'Ready' green, 'Waiting...'
    blue, 'Working...' yellow, anything else red. Keep it a short, single sentence
    -- this is the workhorse status/log channel, and UpdateStatus() below is the
    normal way to drive it rather than calling this directly with ad hoc text."""
    with STDOUT_LOCK:
        print("SMS:" + message)
        sys.stdout.flush()


def show_message(message: str) -> None:
    """Display a message in the status bar of RoboDK's main window (SMS2:) --
    separate from the connection log/status bar that print_message() drives."""
    with STDOUT_LOCK:
        print("SMS2:" + message)
        sys.stdout.flush()


def print_response(message: str) -> None:
    """Report a driver status/response for an API-issued driver command (RE:),
    e.g. what comes back from `item.setParam('Driver', some_command)` on the
    RoboDK API side. Not the same channel as print_message()'s status/log line."""
    with STDOUT_LOCK:
        print("RE:" + message)
        sys.stdout.flush()


def print_commands(cmdlist: str) -> None:
    """Advertise custom commands RoboDK can offer as instructions (CMDLIST:).
    Format is pipe-delimited "c <call>|<label>|..." pairs, e.g.
    "c EnableRobot()|Enable robot|c ClearError()|Clear errors|". Send this once
    at startup -- see build_custom_commands() and the "c " dispatch branch
    in process_command() below for the other half of this mechanism."""
    with STDOUT_LOCK:
        print("CMDLIST:" + cmdlist)
        sys.stdout.flush()


def print_debug(message: str) -> None:
    """Debug/log-window message only -- doesn't touch the status bar."""
    with STDOUT_LOCK:
        print("DBG:" + message)
        sys.stdout.flush()


def print_joints(joints, moving: bool = False) -> None:
    """Report current joints (JNTS or JNTS_MOVING). Use the *_MOVING form (lower
    precision) only if your controller/SDK can give you a live position while the
    robot is in motion -- that's what makes the RoboDK simulation visibly track
    the real robot during a move; plenty of controllers can't provide it, and in
    that case just don't send it rather than faking a value."""
    with STDOUT_LOCK:
        if moving:
            print("JNTS_MOVING " + " ".join(format(v, ".3f") for v in joints))
        else:
            print("JNTS " + " ".join(format(v, ".6f") for v in joints))
        sys.stdout.flush()


# Last reported status, so callers can query current state (e.g. before
# deciding whether a reconnect is even needed).
STATUS = ROBOTCOM_DISCONNECTED


def UpdateStatus(set_status: int = None) -> None:
    """Send the RoboDK-recognized status text for a ROBOTCOM_* code through
    print_message() -- this is the normal way to drive the connection status
    bar; prefer it over calling print_message() with ad hoc status text so the
    code<->text mapping stays in exactly one place. Re-sends the last status
    if called with no argument (useful right after startup)."""
    global STATUS
    if set_status is not None:
        STATUS = set_status

    if STATUS == ROBOTCOM_PROBLEMS:
        print_message("Connection problems")
    elif STATUS == ROBOTCOM_DISCONNECTED:
        print_message("Disconnected")
    elif STATUS == ROBOTCOM_NOT_CONNECTED:
        print_message("Not connected")
    elif STATUS == ROBOTCOM_READY:
        print_message("Ready")
    elif STATUS == ROBOTCOM_WORKING:
        print_message("Working...")
    elif STATUS == ROBOTCOM_WAITING:
        print_message("Waiting...")
    else:
        print_message("Unknown status")


# ---------------------------------------------------------------------------
# Robot-specific communication -- THIS is what changes per controller/vendor.
# Everything above and below this class is the reusable driver skeleton.
class Robot:
    """Fill in with the target robot's SDK calls or raw socket protocol.

    Two ways to implement this, per references/driver-protocol.md:
      - Wrap a vendor SDK if one exists (fewer lines, prefer this).
      - Hand-roll the wire protocol over a raw socket if there's no SDK,
        only a documented message format.
    """

    def __init__(self):
        self.connected = False
        self._status = ROBOTCOM_DISCONNECTED

    def connect(self, ip: str, port: int = 0) -> bool:
        # Always disconnect any prior session first -- reconnecting without
        # disconnecting leaves stale state in most vendor SDKs/sockets.
        self.disconnect()
        print_message(f"Connecting to robot {ip}")
        # TODO: open the real connection here.
        self.connected = True
        return True

    def disconnect(self) -> bool:
        # TODO: close the real connection here. Must be safe to call when
        # already disconnected -- this runs on every STOP/QUIT path too.
        self.connected = False
        return True

    def stop(self) -> None:
        """Stop motion and clear any queued/in-flight motion state. Must return
        promptly -- see the two-loop architecture note below for why this can
        never be stuck behind a long-running move."""
        # TODO: call the SDK's motion-clear/stop equivalent.
        pass

    def move_j(self, joints) -> None:
        # TODO: joint move. RoboDK also sends the equivalent cartesian pose in
        # the same MOVJ line (see driver-protocol.md) -- use whichever this
        # controller wants.
        pass

    def move_l(self, joints, pose) -> None:
        # TODO: linear move.
        pass

    def get_joints(self):
        # TODO: return the current joints as a list of floats.
        return [0.0] * 6

    def set_tool(self, pose) -> None:
        # TODO: set the active TCP.
        pass

    def set_speed(self, lin_speed=None, joint_speed=None, lin_accel=None, joint_accel=None) -> None:
        # TODO: apply speed/acceleration. RoboDK always sends its own native
        # units (mm/s, deg/s, mm/s^2, deg/s^2) -- convert/clamp to whatever
        # this controller expects (often a percentage of a rated maximum).
        pass

    def set_do(self, io_var, io_value) -> None:
        # TODO: set a digital output (or dispatch a named function, e.g. a
        # gripper open/close -- see driver-protocol.md's SETDO example).
        pass

    def set_ao(self, io_var, io_value) -> None:
        # TODO: set an analog output. Same argument shape as set_do() -- don't
        # skip this one just because SETDO gets exercised far more often.
        pass

    def send_custom(self, call: str) -> None:
        """Handle a custom command forwarded via a "c <call>" line (see
        build_custom_commands() and the "c " branch in process_command()).

        Two real patterns, pick whichever fits this controller (see
        references/driver-protocol.md's "Custom/vendor-specific commands"):
          - Pass the string straight through to the controller's own native
            command socket, if it has one that already accepts text commands
            like "EnableRobot()" or "User(0)" -- simplest option when available.
          - Parse a "MethodName(args)" call and dispatch it onto a vendor SDK
            object by name (e.g. getattr(self.sdk, method_name)(*args)) when
            the controller has no native text protocol of its own. Only do
            this against a fixed, known set of method names -- RoboDK is the
            only writer of these lines in normal operation, but don't build a
            dispatcher that would execute arbitrary text from anywhere else.
        """
        # TODO: implement one of the two patterns above for this controller.
        print_debug(f"Custom command not implemented: {call}")


def build_custom_commands() -> str:
    """Build the CMDLIST: payload advertising custom commands as RoboDK
    instructions. Format: pipe-delimited "c <call>|<label>|" pairs. Sent once
    at startup by main() via print_commands(). Keep this list to commands this
    driver's send_custom() actually implements."""
    commands = [
        ("EnableRobot()", "Enable robot"),
        ("ClearError()", "Clear errors"),
    ]
    return "".join(f"c {call}|{label}|" for call, label in commands)


ROBOT = Robot()

# ---------------------------------------------------------------------------
# Command queue + worker thread. Kept separate from the stdin-reading loop
# below so STOP/DISCONNECT/QUIT are handled immediately, never stuck behind a
# queued (possibly long-running, blocking) motion command. This split is the
# one architectural pattern every real driver shares -- see
# references/driver-protocol.md's "Architecture" section for how it looks in
# a compiled/threaded language too.
COMMAND_QUEUE = []


def run_worker() -> None:
    while True:
        if COMMAND_QUEUE:
            process_command(COMMAND_QUEUE.pop(0))
        else:
            time.sleep(0.01)


def process_command(line: str) -> None:
    words = line.split(" ")

    def floats(from_idx=1):
        out = []
        for w in words[from_idx:]:
            try:
                out.append(float(w))
            except ValueError:
                pass
        return out

    try:
        if line == "":
            return

        elif line.startswith("CONNECT"):
            UpdateStatus(ROBOTCOM_WORKING)
            ip = words[1]
            port = int(words[2]) if len(words) > 2 else 0
            if ROBOT.connect(ip, port):
                UpdateStatus(ROBOTCOM_READY)
            else:
                UpdateStatus(ROBOTCOM_PROBLEMS)

        elif line.startswith("CJNT"):
            print_joints(ROBOT.get_joints())
            UpdateStatus(ROBOTCOM_READY)

        elif line.startswith("MOVJ"):
            values = floats()
            if len(values) < 6:
                print_debug(f"MOVJ: not enough values in '{line}'")
                return
            UpdateStatus(ROBOTCOM_WORKING)
            joints = values[:6]
            ROBOT.move_j(joints)
            print_joints(ROBOT.get_joints())
            UpdateStatus(ROBOTCOM_READY)

        elif line.startswith("MOVL"):
            values = floats()
            if len(values) < 12:
                print_debug(f"MOVL: not enough values in '{line}'")
                return
            UpdateStatus(ROBOTCOM_WORKING)
            joints, pose = values[:6], values[6:12]
            ROBOT.move_l(joints, pose)
            print_joints(ROBOT.get_joints())
            UpdateStatus(ROBOTCOM_READY)

        elif line.startswith("SPEED"):
            values = floats()
            UpdateStatus(ROBOTCOM_WORKING)
            ROBOT.set_speed(
                lin_speed=values[0] if len(values) > 0 and values[0] > 0 else None,
                joint_speed=values[1] if len(values) > 1 and values[1] > 0 else None,
                lin_accel=values[2] if len(values) > 2 and values[2] > 0 else None,
                joint_accel=values[3] if len(values) > 3 and values[3] > 0 else None,
            )
            UpdateStatus(ROBOTCOM_READY)

        elif line.startswith("SETTOOL"):
            values = floats()
            if len(values) < 6:
                print_debug(f"SETTOOL: not enough values in '{line}'")
                return
            UpdateStatus(ROBOTCOM_WORKING)
            ROBOT.set_tool(values[:6])
            UpdateStatus(ROBOTCOM_READY)

        elif line.startswith("SETDO"):
            if len(words) < 3:
                print_debug(f"SETDO: not enough arguments in '{line}'")
                return
            UpdateStatus(ROBOTCOM_WORKING)
            ROBOT.set_do(words[1], words[2])
            UpdateStatus(ROBOTCOM_READY)

        elif line.startswith("SETAO"):
            if len(words) < 3:
                print_debug(f"SETAO: not enough arguments in '{line}'")
                return
            UpdateStatus(ROBOTCOM_WORKING)
            ROBOT.set_ao(words[1], words[2])
            UpdateStatus(ROBOTCOM_READY)

        elif line.startswith("WAITDI"):
            print_debug("WAITDI is not implemented")

        elif line.startswith("PAUSE"):
            values = floats()
            UpdateStatus(ROBOTCOM_WAITING)
            if values and values[0] > 0:
                time.sleep(values[0] * 0.001)
            UpdateStatus(ROBOTCOM_READY)

        elif line.startswith("c "):
            # Custom command dispatch -- see build_custom_commands() and
            # Robot.send_custom() above. RoboDK sends exactly what was
            # advertised in the CMDLIST: line printed at startup.
            UpdateStatus(ROBOTCOM_WORKING)
            ROBOT.send_custom(line[2:])
            UpdateStatus(ROBOTCOM_READY)

        else:
            print_debug(f"Unknown command: {line}")

    except Exception as e:
        print_message(f"Error: {e}")
        ROBOT.disconnect()


# ---------------------------------------------------------------------------
# Stdin reader: the only place STOP/DISCONNECT/QUIT are handled -- always
# immediately, never queued behind a pending motion command.
def run_console() -> None:
    for raw_line in sys.stdin:
        line = raw_line.strip()

        if line.startswith("STOP"):
            COMMAND_QUEUE.clear()
            ROBOT.stop()
            UpdateStatus(ROBOTCOM_READY)

        elif line.startswith("DISCONNECT"):
            COMMAND_QUEUE.clear()
            ROBOT.disconnect()
            UpdateStatus(ROBOTCOM_DISCONNECTED)

        elif line.startswith("QUIT"):
            ROBOT.disconnect()
            UpdateStatus(ROBOTCOM_DISCONNECTED)
            break

        else:
            COMMAND_QUEUE.append(line)


def main() -> None:
    print_message(f"RoboDK Driver Template v{DRIVER_VERSION}")

    import atexit
    atexit.register(ROBOT.disconnect)

    # Advertise custom commands once at startup -- see build_custom_commands().
    print_commands(build_custom_commands())

    UpdateStatus()  # flush the initial (disconnected) status

    worker = threading.Thread(target=run_worker, daemon=True)
    worker.start()

    run_console()


if __name__ == "__main__":
    main()
