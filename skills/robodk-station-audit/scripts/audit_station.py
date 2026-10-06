"""Structural audit of a RoboDK station — one inventory pass, then offline analysis.

Implements this skill's Procedure so it doesn't have to be re-derived per session. Every check
matches a numbered step in SKILL.md.

Usage:
    python audit_station.py                     # audit the station already open
    python audit_station.py --open path.rdk     # open a .rdk first, then audit it
    python audit_station.py --json report.json  # also write machine-readable findings

Severities: "info", "warn", "likely bug" — same vocabulary as SKILL.md step 4.

Requires robodk-api's bundled copy on sys.path (see that skill's Connect section); it is found
automatically when this file stays in its normal sibling-skill layout.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import defaultdict
from pathlib import Path


def _bootstrap_api():
    """Put robodk-api's bundled `robodk` package on sys.path (sibling-skill lookup)."""
    here = Path(__file__).resolve()
    for parent in here.parents:
        candidate = parent / "robodk-api" / "assets" / "robodk-api"
        if (candidate / "robodk" / "robolink.py").exists():
            sys.path.insert(0, str(candidate))
            return
    # Not found: fall through and let the import raise a normal ImportError.


_bootstrap_api()
from robodk import robolink, robomath  # noqa: E402

# Names that carry no meaning — SKILL.md step 3.
PLACEHOLDER_PREFIXES = ("object", "frame", "part", "target", "tool", "program", "shape", "item")

# Two same-type items closer than this (mm) are "effectively the same place" — step 2/5.
STACK_TOLERANCE_MM = 25.0


def world_xyz(item) -> tuple[float, float, float] | None:
    try:
        return tuple(round(v, 3) for v in item.PoseAbs().Pos())
    except Exception:
        return None


def inventory(RDK) -> list[dict]:
    """ONE pass over the tree (SKILL.md step 1: inventory once, no polling loops)."""
    type_names = {
        robolink.ITEM_TYPE_STATION: "station", robolink.ITEM_TYPE_ROBOT: "robot",
        robolink.ITEM_TYPE_FRAME: "frame", robolink.ITEM_TYPE_TOOL: "tool",
        robolink.ITEM_TYPE_OBJECT: "object", robolink.ITEM_TYPE_TARGET: "target",
        robolink.ITEM_TYPE_PROGRAM: "program", robolink.ITEM_TYPE_MACHINING: "machining",
    }
    rows = []
    for item in RDK.ItemList():
        try:
            itype = item.Type()
        except Exception:
            continue
        parent_name = None
        try:
            parent = item.Parent()
            parent_name = parent.Name() if parent.Valid() else None
        except Exception:
            pass
        rows.append({
            "name": item.Name(),
            "type": type_names.get(itype, str(itype)),
            "type_id": itype,
            "parent": parent_name,
            "world": world_xyz(item),
        })
    return rows


COPY_SUFFIX = re.compile(r"[\s_-]*(?:\(\d+\)|\d+|copy|clone)$", re.I)


def role_stem(name: str) -> str:
    """Approximate an item's semantic role: its name minus any copy/index suffix.

    'Fanuc LR Mate 200iD' and 'Fanuc LR Mate 200iD 2' share a role; 'Pedestal A' and
    'Pedestal B' deliberately do not (they are named for distinct roles, which is the
    pattern this skill recommends)."""
    stem = name.strip()
    for _ in range(2):
        stem = COPY_SUFFIX.sub("", stem).strip()
    return stem.lower()


def dist(a, b) -> float:
    return sum((x - y) ** 2 for x, y in zip(a, b)) ** 0.5


def audit(rows: list[dict]) -> list[dict]:
    findings: list[dict] = []

    def add(severity, category, message, evidence=None):
        findings.append({"severity": severity, "category": category,
                         "message": message, "evidence": evidence or []})

    # -- step 2: suspicious duplicates ------------------------------------
    # SKILL.md: the duplicate key is (asset source, type, parent, pose bucket, semantic role) --
    # never name alone, and never proximity alone. Proximity alone pairs unrelated items that
    # merely sit near the origin; name alone flags intentional twins. Require BOTH: the same
    # role (approximated by the name with any copy-suffix stripped) AND near-coincident poses.
    by_role = defaultdict(list)
    for r in rows:
        if r["type"] in {"station", "target"} or r["world"] is None:
            continue
        by_role[(r["type"], role_stem(r["name"]))].append(r)

    for (itype, role), group in by_role.items():
        if len(group) < 2:
            continue
        flagged = False
        for i, a in enumerate(group):
            for b in group[i + 1:]:
                d = dist(a["world"], b["world"])
                if d <= STACK_TOLERANCE_MM:
                    add("likely bug", "duplicate",
                        f"two {itype}s with the same role ({role!r}) sit {d:.1f} mm apart — "
                        f"'{a['name']}' and '{b['name']}' are effectively stacked",
                        [a["name"], b["name"]])
                    flagged = True
        if not flagged:
            # Repeated asset, clearly separated: valid. Report as info, and suggest the
            # semantic-rename pattern rather than deletion (SKILL.md step 2).
            add("info", "duplicate",
                f"{len(group)} {itype}s share the role {role!r} but are clearly separated — "
                f"treat as intentional; consider semantic names (Left/Right, A/B)",
                [r["name"] for r in group])

    # -- step 3: naming quality -------------------------------------------
    for r in rows:
        if r["type"] == "station":
            continue
        stem = r["name"].strip().lower()
        bare = stem.rstrip("0123456789 ").strip()
        if bare in PLACEHOLDER_PREFIXES:
            add("warn", "naming",
                f"{r['type']} named {r['name']!r} is a placeholder — rename it for its role "
                f"(e.g. 'Infeed Table', 'Fixture B')", [r["name"]])

    # -- step 4: tree structure -------------------------------------------
    station_names = {r["name"] for r in rows if r["type"] == "station"}
    root_objects = [r for r in rows
                    if r["type"] == "object" and (r["parent"] in station_names or r["parent"] is None)]
    if len(root_objects) > 3:
        add("info", "structure",
            f"{len(root_objects)} objects sit directly under the station root — consider grouping "
            f"related assets under shared frames", [r["name"] for r in root_objects])

    # -- step 5: pose sanity ----------------------------------------------
    # Distinctly-named items are not duplicates, but two fixtures occupying the same space is
    # still a layout bug ("duplicate fixtures occupying the same space", SKILL.md step 5).
    placed = [r for r in rows if r["world"] and r["type"] in {"object", "frame", "robot", "tool"}]
    reported: set[tuple[str, str]] = set()
    for i, a in enumerate(placed):
        for b in placed[i + 1:]:
            if a["type"] != b["type"] or role_stem(a["name"]) == role_stem(b["name"]):
                continue                      # same role is the duplicate check's job, above
            if a["parent"] != b["parent"]:
                continue                      # unrelated branches overlapping is usually fine
            d = dist(a["world"], b["world"])
            if d <= STACK_TOLERANCE_MM:
                key = tuple(sorted((a["name"], b["name"])))
                if key in reported:
                    continue
                reported.add(key)
                add("warn", "pose",
                    f"{a['type']}s {a['name']!r} and {b['name']!r} have different roles but sit "
                    f"{d:.1f} mm apart — overlapping placement", [a["name"], b["name"]])

    for r in rows:
        if r["type"] in {"object", "tool"} and r["world"] and dist(r["world"], (0, 0, 0)) < 1e-6:
            add("warn", "pose",
                f"{r['type']} {r['name']!r} sits exactly at the world origin — usually an "
                f"unplaced item", [r["name"]])

    return findings


def main() -> int:
    ap = argparse.ArgumentParser(description="Structural audit of a RoboDK station.")
    ap.add_argument("--open", dest="station", help="open this .rdk before auditing")
    ap.add_argument("--json", dest="json_out", help="also write findings as JSON here")
    args = ap.parse_args()

    os.environ.setdefault("ROBODK_AI", "noui")
    with robolink.Robolink() as RDK:
        if args.station:
            RDK.AddFile(str(Path(args.station).resolve()))
        rows = inventory(RDK)
        findings = audit(rows)

    order = {"likely bug": 0, "warn": 1, "info": 2}
    findings.sort(key=lambda f: order.get(f["severity"], 9))

    print(f"inventory: {len(rows)} items")
    if not findings:
        print("no structural issues found")
    for f in findings:
        print(f"  [{f['severity']:<10}] {f['category']:<9} {f['message']}")

    if args.json_out:
        Path(args.json_out).write_text(
            json.dumps({"items": rows, "findings": findings}, indent=2), encoding="utf-8")
        print(f"\nwrote {args.json_out}")

    return 1 if any(f["severity"] == "likely bug" for f in findings) else 0


if __name__ == "__main__":
    raise SystemExit(main())
