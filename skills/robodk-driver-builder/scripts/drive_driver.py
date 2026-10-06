"""Exercise a RoboDK driver over its stdin/stdout protocol, without RoboDK or hardware.

SKILL.md says to test a driver standalone by "typing commands" before RoboDK ever loads it.
That is hard to do from an agent session, and *piping* commands is not equivalent: drivers use a
stdin-reader thread that queues work for a worker thread, so a pipe that reaches EOF immediately
can exit before the worker has drained the queue — the driver looks mute when it is merely
racing. This harness paces the input and reads replies with a timeout, which reproduces what
RoboDK actually does.

Usage:
    python drive_driver.py <driver.py> [--delay 0.3] [--timeout 2.0] \
        --cmd "CONNECT 127.0.0.1 1234" --cmd CJNT --cmd QUIT

    python drive_driver.py <driver.py> --script commands.txt     # one command per line

No network, no robot: a driver template with stubbed TODOs simply reports Disconnected, which is
the expected result. Anything that reaches real hardware is robodk-real-robot-control's job, with
its own confirmation protocol — not this script's.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
import threading
import time
from pathlib import Path
from queue import Empty, Queue


def reader(stream, q: Queue) -> None:
    for line in iter(stream.readline, ""):
        q.put(line.rstrip("\r\n"))
    stream.close()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("driver", help="path to the driver .py (or an executable driver)")
    ap.add_argument("--cmd", action="append", default=[], help="a protocol command (repeatable)")
    ap.add_argument("--script", help="file with one command per line")
    ap.add_argument("--delay", type=float, default=0.3, help="pause after each command (s)")
    ap.add_argument("--timeout", type=float, default=2.0, help="how long to wait for replies (s)")
    ap.add_argument("--python", default=sys.executable, help="interpreter for a .py driver")
    args = ap.parse_args()

    commands = list(args.cmd)
    if args.script:
        commands += [ln.strip() for ln in Path(args.script).read_text().splitlines()
                     if ln.strip() and not ln.startswith("#")]
    if not commands:
        ap.error("give at least one --cmd or a --script")

    driver = Path(args.driver)
    argv = [args.python, "-u", str(driver)] if driver.suffix == ".py" else [str(driver)]

    proc = subprocess.Popen(argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, text=True, bufsize=1)
    q: Queue = Queue()
    threading.Thread(target=reader, args=(proc.stdout, q), daemon=True).start()

    def drain(label: str) -> list[str]:
        got, deadline = [], time.time() + args.timeout
        while time.time() < deadline:
            try:
                got.append(q.get(timeout=0.1))
                deadline = time.time() + 0.4      # keep reading while it is still talking
            except Empty:
                continue
        for line in got:
            print(f"    <- {line}")
        if not got:
            print(f"    <- (no reply within {args.timeout}s)")
        return got

    print("== driver startup ==")
    drain("startup")

    for cmd in commands:
        print(f"\n== {cmd}")
        try:
            proc.stdin.write(cmd + "\n")
            proc.stdin.flush()
        except (BrokenPipeError, OSError):
            print("    !! driver closed its stdin (it probably exited)")
            break
        time.sleep(args.delay)
        drain(cmd)

    try:
        proc.stdin.close()
    except OSError:
        pass
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        print("\n!! driver did not exit after QUIT — kill it and check the reader/worker split")
        proc.kill()
        return 1

    print(f"\ndriver exited with code {proc.returncode}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
