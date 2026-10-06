# Bundled snapshot provenance

This folder is a verbatim copy of the `robodk` package — the reference-implementation Python
package (`pip install robodk`), developed in the [RoboDK-API](https://github.com/RoboDK/RoboDK-API)
repo.

- **Package version:** 6.0.2
- **Source:** the official PyPI release (`robodk-6.0.2-py3-none-any.whl`), extracted verbatim
- **Upstream license:** Apache-2.0 (per the wheel's own metadata) — not this repo's MIT
- **Snapshot date:** 2026-10-05
- **Files:** `__init__.py`, `robolink.py`, `robomath.py`, `robodialogs.py`, `robofileio.py`,
  `roboapps.py`, `robolinkutils.py` — unmodified from source, no build artifacts/tests/examples.

All seven files are byte-identical to the released 6.0.2 wheel. Verify with:

```bash
pip download robodk==6.0.2 --no-deps -d /tmp/rdk && unzip -o -q /tmp/rdk/robodk-*.whl -d /tmp/rdk/x
for f in __init__ robolink robomath robodialogs robofileio roboapps robolinkutils; do
  cmp /tmp/rdk/x/robodk/$f.py robodk/$f.py && echo "OK $f"
done
```

## Why a copy instead of a link

The API changes infrequently, so a local copy trades a small drift risk for guaranteed-available,
guaranteed-current-enough offline reference — no network access or separate RoboDK-API checkout
needed to answer "what's the real signature of `X`."

It also pins a known-good version. An arbitrary environment may have an older `pip install robodk`
first on `sys.path` (6.0.1 and earlier have no `Robolink.__enter__`/`__exit__` and no `ROBODK_AI`
support), which is why the skills prepend this directory rather than importing whatever is
installed.

## Refreshing this snapshot

This copy has **no local modifications** — a straight overwrite from the latest release is correct:

```bash
pip download robodk==<new-version> --no-deps -d /tmp/rdk
unzip -o -q /tmp/rdk/robodk-*.whl -d /tmp/rdk/x
cp /tmp/rdk/x/robodk/{__init__,robolink,robomath,robodialogs,robofileio,roboapps,robolinkutils}.py \
   skills/robodk-api/assets/robodk-api/robodk/
```

Then update the version/source/date fields above. Do this when `references/api-surface.md` /
`references/language-notes.md` are being refreshed anyway, or if you hit a signature mismatch
between this snapshot and a live RoboDK install.

Historical note: before 2026-10-05 this folder carried pre-release changes taken from an unmerged
`ai-skill-improvements` branch (`ROBODK_AI`, context-manager support, extra `robolinkutils`
helpers). Those all shipped in 6.0.2, so the "merge, don't overwrite" caveat that used to live
here no longer applies.
