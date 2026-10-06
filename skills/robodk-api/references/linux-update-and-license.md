# RoboDK Linux Update and License Activation Notes

Session learning from updating RoboDK on Ubuntu/Linux and attempting license activation through RoboDK's command-line/API surfaces.

## Update pattern

1. Check the current API state before making changes:

   ```bash
   ss -ltnp 'sport = :20500'
   python3 - <<'PY'
   import json
   from robodk import robolink
   with robolink.Robolink() as RDK:
       lic = RDK.License()
       print(json.dumps({'version': RDK.Version(), 'license_name': lic[0], 'computer_id': lic[1]}, indent=2))
   PY
   ```

2. Prefer the current Linux installer from the official CDN/download page. The Linux installer may be an offline Qt Installer Framework binary inside `Install-RoboDK.tar.gz`:

   ```bash
   mkdir -p /tmp/robodk-installer
   tar -xzf ~/Downloads/Install-RoboDK.tar.gz -C /tmp/robodk-installer
   chmod +x /tmp/robodk-installer/Install-RoboDK
   /tmp/robodk-installer/Install-RoboDK --version
   /tmp/robodk-installer/Install-RoboDK --accept-licenses --default-answer --confirm-command search '.*' --asset-type package
   ```

3. Existing RoboDK installs can block direct headless install into the same directory with `TargetDirectoryInUse`. A safe workflow is:

   ```bash
   rm -rf ~/RoboDK-new
   /tmp/robodk-installer/Install-RoboDK \
     --accept-licenses --default-answer --confirm-command \
     --root ~/RoboDK-new install com.robodk.software
   # verify ~/RoboDK-new launches/API works, then atomically swap:
   mv ~/RoboDK ~/RoboDK-backup-$(date -u +%Y%m%dT%H%M%SZ)
   mv ~/RoboDK-new ~/RoboDK
   ```

4. Newer Qt builds on Ubuntu may require the xcb cursor package before the GUI/API can start:

   ```bash
   sudo apt-get update
   sudo apt-get install -y libxcb-cursor0
   ```

## License activation pattern

RoboDK's advanced license FAQ documents command-line activation as:

```bash
RoboDK -NOUI -LCMD=Network:<license-code> -QUIT
# or hidden form:
RoboDK -NOUI -LCMD=Network:H<license-code> -QUIT
```

On Linux, run it through RoboDK's bundled library environment. Avoid writing license keys into shell history or tool logs when possible; feed the key via stdin/PTY and expand it inside the child process:

```bash
bash -lc 'read -rs KEY; cd ${ROBODK_ROOT:-/path/to/RoboDK}/bin && \
  DISPLAY=:0 LD_LIBRARY_PATH=$PWD/lib QT_PLUGIN_PATH=$PWD/plugins \
  QT_QPA_PLATFORM_PLUGIN_PATH=$PWD/plugins \
  ./RoboDK -NOUI -LCMD=Network:$KEY -QUIT'
```

Alternative API attempt:

```python
RDK.Command('LCMD', 'Network:' + key)
```

Important: `RDK.Command('LCMD', ...)` and the command-line activation path may return/log `OK` or `Applying license command` even when the license is not actually active. Do **not** claim success until a fresh RoboDK process reports a paid license through `RDK.License()`.

If the license is already activated on this machine (no key needed), `-Settings=LicenseLoad` is
simpler than replaying `-LCMD` — see `references/headless-testing.md`.

## Verification gate

After activation, restart RoboDK and verify with the API:

```bash
env DISPLAY=:0 ${ROBODK_ROOT:-/path/to/RoboDK}/RoboDK-Start.sh
python3 - <<'PY'
import json
from robodk import robolink
with robolink.Robolink() as RDK:
    lic = RDK.License()
    print(json.dumps({'version': RDK.Version(), 'license_name': lic[0], 'computer_id': lic[1]}, indent=2))
PY
```

A license status of `Free` or `Free (Trial)` means activation is not verified. Escalate to visible GUI Help → License or RoboDK support with the Computer ID and version. Network connectivity to `robodk.com:80/443` can be checked, but connectivity alone does not prove license validity.
