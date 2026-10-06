# RoboDK Agent Skills

**From prompt to production cell.** RoboDK Agent Skills for robot manufacturing and automation.

Describe the robot cell you have in mind, and let your AI agent build it, simulate it, and
generate the robot program. This is where robot programming is heading: less clicking,
more telling.

RoboDK Agent Skills teach AI agents such as Claude Code how to work with
[RoboDK](https://robodk.com), so you can:

- **Build cells** by describing the components you need — tables, fencing, conveyors, rails,
  gantries, turntables — and letting the agent place them
- **Write and port code** that uses the RoboDK API
- **Generate robot programs** for controllers from ABB, FANUC, KUKA, Universal Robots, and many more
- **Extend RoboDK itself** with Add-ins: menus, toolbar buttons, and settings dialogs
- **Check your work** by auditing stations for structural mistakes
- **Go live** by moving a real robot, with safety confirmations built in

## The skills

| Skill | What it does |
| --- | --- |
| [`robodk-api`](skills/robodk-api/) | Write, port, or debug code against the RoboDK API — Python, C#, C++, MATLAB, TypeScript, C, Visual Basic. Bundles the `robodk` package so an agent can look up exact signatures offline. |
| [`robodk-shape-builder`](skills/robodk-shape-builder/) | Build parametric components — boxes, spheres, cones, tables, pedestals, fencing, conveyors, linear rails, gantries, turntables — using RoboDK's own Components library. **Proprietary license**, see [LICENSES.md](LICENSES.md). |
| [`robodk-station-audit`](skills/robodk-station-audit/) | Catch structural mistakes in a station before they cost you a rebuild. |
| [`robodk-post-processor-builder`](skills/robodk-post-processor-builder/) | Read, write, and debug post processors — the layer that turns a simulated program into real controller code (KRL, RAPID, Fanuc LS, Motoman JBI, URScript, G-code, and more). |
| [`robodk-driver-builder`](skills/robodk-driver-builder/) | Write, port, or debug a RoboDK robot driver — the program behind Online Programming that drives a real controller live. |
| [`robodk-addin`](skills/robodk-addin/) | Create, validate, and package RoboDK Add-ins (Apps): menus, toolbar buttons, context-menu actions, settings dialogs, `.rdkp` packages. |
| [`robodk-real-robot-control`](skills/robodk-real-robot-control/) | Move a **real, physical robot** through RoboDK's drivers. The only skill here that touches hardware — every other one is simulation-only by design. Read [SECURITY.md](SECURITY.md) first. |

Each skill's `SKILL.md` documents when to use it, the exact commands and API calls, and the
pitfalls worth knowing before you start.

## Requirements

- [RoboDK](https://robodk.com/download) installed
- An AI coding agent that reads the `SKILL.md` format — for example
  [Claude Code](https://claude.com/claude-code)
- Python 3.9+ for the skills that ship runnable scripts

## Setup

Clone the repo and link the skills into your agent's skill directory:

```bash
git clone https://github.com/RoboDK/RoboDK-Agent-Skills.git
cd RoboDK-Agent-Skills

# macOS/Linux
./scripts/install.sh

# Windows
.\scripts\install.ps1
```

This symlinks (junctions on Windows) every `skills/<name>` into `~/.claude/skills/`, so a
`git pull` picks up updates with no re-copying. Pass `--target <path>` / `-Target <path>` to link
into a different agent's skill directory, or `--copy` / `-Copy` if your environment can't use
symlinks.

Prefer to do it by hand? Copy the folders you want:

```bash
cp -r skills/robodk-post-processor-builder ~/.claude/skills/
```

## Using them

You don't invoke these skills directly — your agent picks the right one from what you ask for.
Open your agent in any project with RoboDK installed and describe the work:

> Add a 2 m conveyor and a safety fence around the UR10 in this station, then check the cell for
> structural mistakes.

> This post processor emits the wrong speed for linear moves on our FANUC. Here's the generated
> program and the post — find it.

> Package this Add-in folder as an .rdkp I can send to a customer.

## Safety

These skills are productivity tools, **not safety systems**. Every skill works in simulation only,
with one exception — `robodk-real-robot-control`, which can move physical hardware and asks for
explicit confirmation before each motion.

Always review generated programs and verify them in simulation before running them on a real
robot, and start at reduced speed with the emergency stop within reach. Full detail, including
what we consider in and out of scope: [SECURITY.md](SECURITY.md).

## Contributing

Issues and pull requests are welcome — see [CONTRIBUTING.md](CONTRIBUTING.md) for the `SKILL.md`
schema, layout conventions, and what makes a good skill. The most useful contribution is usually a
pitfall: if a skill's instructions were wrong or incomplete for your controller, your RoboDK
version, or your OS, tell us what actually happened.

Found a security issue, or anything that could move a real robot unexpectedly? Please report it
privately to info@robodk.com rather than opening an issue — see [SECURITY.md](SECURITY.md).

## Learn more

- 🌐 [RoboDK](https://robodk.com): simulation and offline programming for industrial robots
- 📖 [Documentation](https://robodk.com/doc/en/): the RoboDK user guide
- 🐍 [RoboDK API](https://robodk.com/doc/en/RoboDK-API.html): program RoboDK from Python, C#, C++, and more
- 💬 [Forum](https://robodk.com/forum/): questions and discussion with the RoboDK community
- 🔔 [LinkedIn](https://www.linkedin.com/company/robodk/): follow RoboDK for updates

## License

[MIT](LICENSE) © RoboDK Global, SLU — with two exceptions: `robodk-shape-builder` is proprietary
(All Rights Reserved), and the bundled RoboDK Python SDK is Apache-2.0. See
[LICENSES.md](LICENSES.md) before copying anything out of this repository.
