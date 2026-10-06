"""RoboDK install root / library path resolution — the single canonical location for this logic.

Consolidated here from the skills that each used to keep their own copy (originally identical,
then diverged once one of them was hand-simplified). `robodk-api` is the natural owner: it's the
skill about the RoboDK SDK/install itself, not about any one caller of it. Callers import this
module lazily — a normal package import first, then a fallback that walks up to find this repo's
`skills/robodk-api/` directory — instead of defining these functions themselves.
"""
from __future__ import annotations

import os
import platform
from pathlib import Path
from typing import Iterable


def _dedupe_paths(paths: Iterable[Path]) -> list[Path]:
    seen: set[str] = set()
    out: list[Path] = []
    for path in paths:
        text = str(path.expanduser())
        if text in seen:
            continue
        seen.add(text)
        out.append(Path(text))
    return out


def _env_path(*keys: str, default: Path) -> Path:
    for key in keys:
        value = os.environ.get(key)
        if value:
            return Path(value).expanduser()
    return default


def _windows_registry_root() -> Path | None:
    """Read RoboDK's install directory from the Windows registry (SOFTWARE\\RoboDK, INSTDIR),
    mirroring the lookup robolink.py's getPathRoboDK() does. Returns None off Windows, or if the
    key/value isn't present (RoboDK not installed, or installed without registering itself)."""
    try:
        import winreg
    except ImportError:
        return None
    for key_flag in (winreg.KEY_WOW64_64KEY, winreg.KEY_WOW64_32KEY):
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, "SOFTWARE\\RoboDK", 0, winreg.KEY_READ | key_flag) as hkey:
                value, _ = winreg.QueryValueEx(hkey, "INSTDIR")
                return Path(value)
        except OSError:
            continue
    return None


def _robolink_root_candidate() -> Path | None:
    """If the `robodk` pip package happens to already be importable, prefer its own
    getPathRoboDK("Root") over guessing here — same registry/env-var detection, single source of
    truth, one less place to keep in sync. Returns None (not an error) if `robodk` isn't
    installed, which is expected: this module's whole job is helping locate/bootstrap a RoboDK
    install before `robodk` is necessarily on PYTHONPATH (e.g. `linux_runtime.py` uses
    robodk_root_candidates() to find the install so it can put `<root>/Python` on sys.path in the
    first place — at that point `robodk.robolink` can't be imported yet)."""
    try:
        from robodk import robolink
    except ImportError:
        return None
    try:
        return Path(robolink.getPathRoboDK("Root"))
    except Exception:
        return None


def robodk_root_candidates() -> list[Path]:
    system = platform.system()
    candidates: list[Path] = []
    if os.environ.get("ROBODK_ROOT"):
        candidates.append(Path(os.environ["ROBODK_ROOT"]).expanduser())
    if os.environ.get("ROBODK_HOME"):
        candidates.append(Path(os.environ["ROBODK_HOME"]).expanduser())

    robolink_root = _robolink_root_candidate()
    if robolink_root:
        candidates.append(robolink_root)

    # Fallback guesswork below — kept (not "should not be needed") because this module must still
    # work when `robodk` isn't pip-installed, which is the common case for its own callers.
    if system == "Windows":
        registry_root = _windows_registry_root()
        if registry_root:
            candidates.append(registry_root)
        candidates.append(Path("C:/RoboDK"))
        # Versioned/relocated installs: RoboDK 6 defaults to C:/RoboDK6, and side-by-side
        # installs are common. Glob rather than guessing a version, newest name last so a
        # higher version wins over a bare C:/RoboDK when neither is in the registry.
        for base in (Path("C:/"), Path("C:/Program Files"), Path("C:/Program Files (x86)")):
            try:
                found = sorted((d for d in base.glob("RoboDK*") if d.is_dir()), reverse=True)
            except OSError:
                continue
            candidates.extend(found)
    elif system == "Darwin":
        candidates.extend([
            Path.home() / "RoboDK/RoboDK.app/Contents",
            Path("/Applications/RoboDK.app/Contents"),
        ])
    else:
        candidates.extend([
            Path.home() / "RoboDK",
            Path("/opt/RoboDK"),
            Path("/usr/local/RoboDK"),
        ])
    return _dedupe_paths(candidates)


def resolve_robodk_root() -> Path:
    candidates = robodk_root_candidates()
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return Path.home() / "RoboDK"


def resolve_robodk_library_dir() -> Path:
    return _env_path("ROBODK_LIBRARY", default=resolve_robodk_root() / "Library")


def robodk_documents_dir_candidates() -> list[Path]:
    """Where RoboDK puts assets the user DOWNLOADS from the online library.

    This is a second library location, separate from the install's own `Library/`. RoboDK reports
    it as `PATH_DOCUMENTS` on a live connection (e.g. `<user home>/Documents/RoboDK/`); these
    are the offline equivalents, used when no RoboDK connection is available.
    """
    home = Path.home()
    candidates = [home / "Documents" / "RoboDK", home / "RoboDK"]
    if os.name == "nt":
        # Documents can be redirected (OneDrive, a mapped drive); USERPROFILE-relative is only a
        # default. Honour the shell folder if it is set.
        onedrive = os.environ.get("OneDrive") or os.environ.get("OneDriveConsumer")
        if onedrive:
            candidates.insert(0, Path(onedrive) / "Documents" / "RoboDK")
    return candidates


def resolve_robodk_library_dirs() -> list[Path]:
    """Every local directory worth searching for library assets, highest priority first.

    Prefer this over `resolve_robodk_library_dir()` for *searching*: a user's downloaded assets
    live in the documents library, not the install one, and treating only the install directory
    as "local" makes the resolver re-download files that are already on disk.

    Order: `ROBODK_LIBRARY` override, the install `Library/`, `ROBODK_LIBRARY_EXTRA` entries
    (os.pathsep-separated), then the documents library. Non-existent directories are dropped.
    """
    dirs: list[Path] = [resolve_robodk_library_dir()]

    extra = os.environ.get("ROBODK_LIBRARY_EXTRA")
    if extra:
        dirs.extend(Path(part).expanduser() for part in extra.split(os.pathsep) if part)

    dirs.extend(robodk_documents_dir_candidates())
    return [d for d in _dedupe_paths(dirs) if d.is_dir()]
