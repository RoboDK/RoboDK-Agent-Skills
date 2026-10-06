# Contributing

This repo holds RoboDK skills for AI coding agents (Claude Code and others that read the same
`SKILL.md` format). It's meant to work as a shared, growing library — please add to it, fix stale
instructions, and generalize anything that's tied to one machine or one agent.

The most valuable contribution is usually a **pitfall**: if a skill's instructions were wrong or
incomplete for your controller, your RoboDK version, or your OS, tell us what actually happened.
That is worth more than a new feature.

## Layout

```
skills/
  <skill-name>/
    SKILL.md            # required — see schema below
    references/         # optional — longer-form background docs, loaded on demand
    scripts/            # optional — runnable tools the skill invokes
    assets/             # optional — templates, fixtures, sample files
    LICENSE.md          # required only if the skill is not MIT
scripts/                # install.sh / install.ps1 — link skills/ into a local agent's skill dir
                        # lint_skills.py — the schema check CI runs
```

Every skill is a **direct child of `skills/`**. Agent-agnostic on purpose: nothing here should
assume it only runs under one agent's runtime. If something is genuinely specific to one agent or
one host (e.g. GUI automation on a Linux agent host), say so explicitly inside the `SKILL.md`
rather than hiding the assumption in a command.

## `SKILL.md` schema

```yaml
---
name: robodk-my-skill              # matches the directory name
description: One or two sentences — this is what an agent's skill router matches on. Be
  specific about when to use it, including indirect phrasings a user might actually type.
version: 1.0.0
author: RoboDK
license: MIT
platforms: [linux, windows, macos]  # omit if truly mixed/uncertain; note per-section exceptions in the body instead of overclaiming here
metadata:
  tags: [robodk, ...]
  category: software-development
  related_skills: [other-skill-name, ...]
---
```

`name` and `description` are the fields agents actually key off. Everything else is metadata —
harmless to omit, but keep it consistent so the repo stays scannable. `description` matters most:
write it the way you'd explain the skill to a teammate who's about to guess whether it applies.

## Adding a new skill

1. Create `skills/<robodk-your-skill-name>/SKILL.md` following the schema above.
2. Write for a reader with no memory of your session: state the workflow, the exact commands and
   API calls, and the pitfalls you actually hit — not just the happy path.
3. Never hardcode a personal absolute path (e.g. `/home/<your-username>/...`) — use `~`
   (home-relative) instead. If a step only works on one OS or one specific host (tools like
   `xdotool`/`scrot`/AT-SPI), say so inline instead of letting it read as universal. Prefer
   OS detection (see `skills/robodk-api/robodk_api/paths.py` for the pattern) over a single
   hardcoded path.
4. Put long reference material in `references/*.md` and link to it from `SKILL.md` rather than
   inlining everything — skills are loaded into an agent's context, so keep the top-level file
   scannable.
5. Avoid duplicating another skill's tooling. RoboDK install-root and library-path resolution,
   for example, lives only in `robodk-api`'s `robodk_api/paths.py`; import it rather than writing
   a second copy.
6. Run `scripts/install.sh` or `scripts/install.ps1` to link your new skill into your local
   agent's skill directory, and sanity-check it end to end against a real RoboDK before opening
   a PR.
7. Run `python scripts/lint_skills.py` before opening a PR — it checks the frontmatter schema and
   flags hardcoded personal paths. CI runs the same check on every PR that touches `skills/`.

## Updating an existing skill

If you hit a real pitfall while using a skill (a command that doesn't work as documented, a wrong
assumption, a better pattern), fix the skill in the same session if you can — that's the whole
point of these files. Add it to the skill's **Common Pitfalls**/**Pitfalls** section with enough
detail that the next agent doesn't repeat it.

## Pull requests

- Keep PRs scoped to one skill (or one clearly-related group of changes) where possible.
- Call out in the PR description whether you tested the change against a real RoboDK instance,
  and on which OS.
- If you're deprecating or merging a skill, remove the old directory in the same PR rather than
  leaving two versions to drift apart.

## Licensing of contributions

Contributions to the MIT-licensed parts of this repository are accepted under the same MIT
license (inbound = outbound). You keep your copyright; you're confirming you have the right to
submit the work and that it may be used under MIT.

**Please do not submit changes to `skills/robodk-shape-builder/`** — it is proprietary, All Rights
Reserved, and not open source. Open an issue instead. See [LICENSES.md](LICENSES.md) for the full
breakdown of which parts of this repo are under which license.

Only contribute material you have the right to share. These skills quote controller syntax and
vendor documentation, so please don't paste in content from a manual or codebase whose license
doesn't allow it.

## Real robots

`skills/robodk-real-robot-control/` is the only skill that can move physical hardware; everything
else is simulation-only by design. If your change touches it, or could cause an agent to reach
real hardware, say so explicitly in the PR. Please report anything that could move a real robot
unexpectedly privately instead of in a public issue — see [SECURITY.md](SECURITY.md).
