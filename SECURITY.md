# Security Policy

## Reporting a vulnerability

Please **do not** open a public issue for security vulnerabilities.

Instead, report them privately by email to **info@robodk.com**, with "Security" in the subject line.

Please include:

- The affected skill(s) and version or commit
- The agent you were using (for example, Claude Code) and your RoboDK version
- Steps to reproduce, and what happened compared with what you expected
- Whether the issue can affect a **real robot** (not only the simulation)

We will acknowledge your report, investigate it, and keep you informed until it is resolved.
Reports that could lead to unexpected motion of a real robot are handled with top priority.

## Scope

In scope:

- Skill instructions or scripts that could make an agent run unintended commands,
  overwrite or leak files, or bypass the confirmations a skill requires
- Anything that could move a real robot without the user's explicit confirmation
- Prompt-injection paths, for example station files, library assets, or programs
  that could steer an agent into unsafe actions

Out of scope (please report these through RoboDK's usual support channels instead):

- Vulnerabilities in RoboDK itself, robot controllers, or robot drivers not maintained in this repository
- Vulnerabilities in the AI agent or model you run these skills with

## Real robots and safety

Every skill in this repository works in **simulation only**, with one exception: the real-robot
control skill, which can move physical hardware and asks for explicit confirmation first.

These skills are productivity tools, **not safety systems**. They do not replace:

- A risk assessment of the robot cell
- Safety-rated hardware and functions (emergency stops, guarding, safety PLCs, speed and
  separation monitoring)
- Compliance with the standards that apply to you (for example, ISO 10218)
- Qualified personnel supervising any real-robot operation

Always review generated programs and verify them in simulation before running them on a real
robot, and start at reduced speed with the emergency stop within reach.
