# RoboDK API path resolution

`robodk_api.paths` — the single shared implementation of RoboDK install-root and library-path
resolution: `robodk_root_candidates()`, `resolve_robodk_root()`, `resolve_robodk_library_dir()`.

Other skills in this repo that need to locate a RoboDK install import this module (a normal
package import first, then a fallback that walks up to find this repo's `skills/robodk-api/`
directory, wherever the caller itself lives) instead of keeping their own copies.

## Install

```bash
pip install .
```

## Quick check

```bash
python3 -c "from robodk_api import resolve_robodk_root; print(resolve_robodk_root())"
```

## Env overrides

- `ROBODK_ROOT` / `ROBODK_HOME` — RoboDK install directory.
- `ROBODK_LIBRARY` — RoboDK Library directory (defaults to `<root>/Library`).
