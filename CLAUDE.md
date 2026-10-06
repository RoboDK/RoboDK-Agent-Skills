# CLAUDE.md

This file gives Claude Code guidance for working in this repository.

## What this repo is

A shared library of [Agent Skills](https://code.claude.com/docs/en/skills.md) for automating
RoboDK. See [README.md](README.md) for setup and [CONTRIBUTING.md](CONTRIBUTING.md) for the
`SKILL.md` schema and layout conventions.

## Use the skills that live here

Before improvising a RoboDK workflow from scratch — writing a station-building script, calling
the RoboDK API directly, debugging a post processor, building an Add-in — check whether a skill
in `skills/` already covers it. Each `skills/<name>/SKILL.md` states when it applies, the exact
commands and API calls, and the pitfalls already discovered.

**Prefer invoking these as actual Claude Code skills over reading `SKILL.md` as plain reference
text.** If they're linked into your personal skills directory (`~/.claude/skills/<name>` — see
the README's setup section), the Skill tool picks them up by name directly and loads their
`references/`/`assets/` on demand, which is more reliable than manually paraphrasing the file.
If a relevant skill *isn't* linked yet in the current environment, either run
`scripts/install.sh` / `scripts/install.ps1` first, or fall back to reading
`skills/<name>/SKILL.md` directly — but treat the local link as the first option, not the
fallback.

## Simulation by design

Every skill here works in simulation only, with one exception: `robodk-real-robot-control` can
move a real, physical robot (`robot.Connect()`, `RUNMODE_RUN_ROBOT`). Use it only on an
unambiguous, explicit request to move real hardware, re-confirm before every individual
real-motion action, and never infer real-robot intent from ambiguous phrasing. Generating a
program to transfer to a controller later is a post-processor task, not a real-robot task.

See [SECURITY.md](SECURITY.md) for the full safety framing — these skills are productivity tools,
not safety systems.

## Working on this repo itself

Changes to `skills/**` should follow the schema in [CONTRIBUTING.md](CONTRIBUTING.md) — run
`python scripts/lint_skills.py` before committing (also enforced in CI). In particular: no
hardcoded personal paths (use `~`), `name` in frontmatter must match the directory name, and
avoid duplicating another skill's tooling.

Not everything here is MIT. `skills/robodk-shape-builder/` is proprietary (All Rights Reserved)
and the bundled RoboDK Python SDK under `skills/robodk-api/assets/robodk-api/` is Apache-2.0 —
check [LICENSES.md](LICENSES.md) before copying code out of this repository, and don't relicense
or redistribute either one.
