# Licensing

Most of this repository is MIT. Two parts are not. Check here before copying anything out.

| Path | License | Copyright |
| --- | --- | --- |
| Everything not listed below | [MIT](LICENSE) | RoboDK Global, SLU |
| `skills/robodk-shape-builder/**` | **Proprietary — All Rights Reserved** ([terms](skills/robodk-shape-builder/LICENSE.md)) | RoboDK Global, SLU |
| `skills/robodk-api/assets/robodk-api/robodk/**` | Apache-2.0 (upstream `robodk` package) | RoboDK |

## Per-skill licenses

Every skill declares its license in the `license:` field of its `SKILL.md`, and any skill whose
license is not MIT also carries its own `LICENSE.md` in the skill folder. Check that field first —
it is the authoritative answer for a given skill.

Every skill is MIT except `robodk-shape-builder`. One skill, `robodk-api`, is itself MIT but
bundles an Apache-2.0 copy of the upstream `robodk` package under its `assets/`.

## robodk-shape-builder is proprietary

`skills/robodk-shape-builder/` vendors `shapetools.py` and its `models/*.sld` geometry — the
library behind RoboDK's own Components Add-in. It is **All Rights Reserved** and available for use
together with RoboDK, but it may not be redistributed or published separately from this
repository. See [its LICENSE.md](skills/robodk-shape-builder/LICENSE.md) for the exact terms.

If you are copying skills into another project or redistributing them, leave this one out, or ask
RoboDK first.

## The bundled RoboDK SDK is Apache-2.0

`skills/robodk-api/assets/robodk-api/robodk/` is a verbatim copy of the released `robodk` package
from PyPI, bundled so an agent can read exact API signatures offline. It is licensed Apache-2.0 by
its upstream project, not under this repository's MIT license. See
[`SNAPSHOT.md`](skills/robodk-api/assets/robodk-api/SNAPSHOT.md) for the exact version and how to
refresh it.

## Contributions

Contributions to the MIT-licensed parts of this repository are accepted under the same MIT license
(inbound = outbound). Please do not submit changes to `skills/robodk-shape-builder/` — open an
issue instead, since its terms are not open source.
