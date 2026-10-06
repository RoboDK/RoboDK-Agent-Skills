---
name: robodk-station-audit
description: Audit RoboDK stations for common structural mistakes.
version: 1.0.0
author: RoboDK
license: MIT
platforms: [linux, windows, macos]
metadata:
  tags: [robodk, station-audit, robotics, simulation]
  category: software-development
  related_skills: [robodk-api, robodk-shape-builder]
---

# RoboDK Station Audit Skill

Use this skill to inspect an existing RoboDK station for objective structural issues before or after editing it. It is deliberately narrow: the goal is to detect likely mistakes, not to redesign the cell.

This skill is especially useful when an agent may have imported assets multiple times, left poor names in the tree, or created questionable near-overlapping geometry. It should reduce false alarms by treating repeated assets as valid when their roles or poses differ.

## When to Use

Use when the user asks to:

- inspect a station for mistakes,
- check whether a RoboDK build is clean,
- look for duplicate imports or clutter,
- validate the station tree before further automation,
- compare the current open station with a saved `.rdk` file.

## Prerequisites

- RoboDK is installed.
- If auditing the live station, RoboDK should be running and reachable through the RoboDK API bridge.
- If auditing an offline artifact only, export the station to an inspectable form first and use this skill as the live follow-up.
- Use `terminal` for bridge commands and `read_file` / `search_files` for supporting artifacts.

## How to Run

1. Decide whether the audit is **live** (open RoboDK station) or **offline** (saved `.rdk` only).
2. For live audits, collect one station-tree snapshot first; do not repeatedly query the same lists in loops.
3. Group findings into:
   - suspicious duplicates,
   - naming problems,
   - layout/reachability warnings,
   - artifact hygiene issues.
4. Report each finding with evidence and a severity: `info`, `warn`, or `likely bug`.

## Run the bundled auditor first

`scripts/audit_station.py` already implements the whole Procedure below — one inventory pass, the
duplicate/naming/structure/pose checks, and the `info`/`warn`/`likely bug` severities. Start there
instead of re-deriving the checks, and extend it when a station needs something it doesn't cover:

```bash
python scripts/audit_station.py                              # audit the open station
python scripts/audit_station.py --open path/to/station.rdk   # open a file, then audit
python scripts/audit_station.py --json report.json           # machine-readable findings too
```

It exits `1` when anything is a `likely bug`, `0` otherwise, so it works as a build gate. It finds
`robodk-api`'s bundled SDK itself via the sibling-skill layout — no `sys.path` setup needed.

Verified against a station with one planted defect per category: it flags a same-role robot
imported twice 3 mm apart as `likely bug`, leaves a third copy 2.5 m away as `info` (intentional
repeat), warns on placeholder names and on an object left at the world origin, and warns when two
*differently*-named fixtures overlap.

## Quick Reference

- Prefer one inventory pass, not repeated API polling.
- Treat repeated assets as valid when pose or role differs.
- Flag a duplicate only when the same asset has the same parent, nearly the same pose, and the same role.
- Suggest semantic renames instead of deleting valid repeated assets.
- Save the audit result to a text file when the user is iterating on a build.

## Procedure

1. **Inventory once**
   - Use one bridge command or short `terminal` script to gather item name, type, parent, approximate world pose, and source path when available.
   - If a saved station file exists, optionally export and inspect it first, then compare its item names with the live tree.

2. **Check for suspicious duplicates**
   - Do not flag repeated names alone.
   - Use a duplicate key closer to `(asset source, type, parent, approximate pose bucket, semantic role)`.
   - Treat repeated tables, pallets, robots, trays, and fixtures as valid if they have clearly different poses or clearly different station roles.
   - Flag a likely accidental clone only when an item is effectively stacked on top of another copy or is a same-role import beside it with no reason for multiplicity.

3. **Check naming quality**
   - Flag placeholder names like `Object`, `Object 2`, `Frame 1`, or auto-imported robot bases left unchanged.
   - Prefer names that encode side, process step, or function: `Infeed Table`, `Robot Outfeed`, `Fixture B`.

4. **Check tree structure**
   - Look for parts that should be parented to tools, pallets, or fixtures but are still floating under the station root.
   - Look for excessive root-level clutter when related assets could live under a shared frame.

5. **Check pose sanity**
   - Flag near-identical world poses for same-type assets.
   - Flag obviously suspicious placements such as duplicate fixtures occupying the same space, tools at world origin with no robot parent, or targets far from the process zone.
   - For tables, fixtures, and positioners, compare the working frame and workpiece Z height against the supporting surface bounding box. A weld/work frame floating far above the table top is a likely layout bug even when X/Y alignment looks correct.

6. **Check program hygiene**
   - Note missing or ambiguous program names.
   - If multiple programs appear to serve the same role, report them for human review rather than assuming one is stale.

7. **Summarize actions**
   - Separate `safe cleanup suggestions` from `needs user confirmation`.
   - For valid repeated assets, say explicitly that they appear intentional.

## Pitfalls

- Do not treat identical mesh files as automatic errors; a station may legitimately use the same table or fixture multiple times.
- Do not delete anything during the audit unless the user explicitly asks for cleanup.
- Do not confuse a repeated asset with a repeated role; two identical tables can be valid, two stacked imports at the same pose usually are not.
- Do not hammer the API with repeated `ItemList` or pose reads.
- Do not overclaim collisions or reachability unless you actually ran a verification pass.

## Verification

- [ ] The audit distinguishes valid repeated assets from suspicious clones.
- [ ] Each finding includes evidence: name, type, parent, or approximate pose.
- [ ] The report separates warnings from confirmed likely mistakes.
- [ ] No destructive action was taken without explicit user direction.
