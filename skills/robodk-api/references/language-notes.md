# Per-language quick start and naming notes

All seven languages talk to the same RoboDK TCP API (default `localhost:20500`). Method names
are consistent across all of them **except** the C#/API NuGet package (PascalCase, see below).
When in doubt, grep the actual source file for the language you're targeting rather than
assuming a signature.

## Python — reference implementation

Files: [`robolink.py`](https://github.com/RoboDK/RoboDK-API/blob/master/Python/robodk/robolink.py)
(`Robolink`, `Item`), [`robomath.py`](https://github.com/RoboDK/RoboDK-API/blob/master/Python/robodk/robomath.py)
(`Mat` + pose helpers), [`robodialogs.py`](https://github.com/RoboDK/RoboDK-API/blob/master/Python/robodk/robodialogs.py)
(open/save/message dialogs), [`robofileio.py`](https://github.com/RoboDK/RoboDK-API/blob/master/Python/robodk/robofileio.py)
(CSV/FTP/file utilities), [`roboapps.py`](https://github.com/RoboDK/RoboDK-API/blob/master/Python/robodk/roboapps.py)
(App Loader plug-in framework), [`robolinkutils.py`](https://github.com/RoboDK/RoboDK-API/blob/master/Python/robodk/robolinkutils.py)
(helpers built on `robolink`) — all under `Python/robodk/` in the RoboDK-API repo.

Install: `pip install robodk` (or `pip install robodk[cv,apps,lint]` for optional extras), or
rely on RoboDK's own `PYTHONPATH` injection of `/RoboDK/Python/` — no install needed when
running a script *from* RoboDK (`Tools ▸ Run Script`).

```python
from robodk import robolink    # RoboDK API
from robodk import robomath    # Robot toolbox

with robolink.Robolink() as RDK:
    robot = RDK.Item('', robolink.ITEM_TYPE_ROBOT)   # first robot in the station
    target = RDK.Item('Target 1')
    robot.MoveJ(target)
    print(robot.Pose().Pos())
```

Prefer this module-qualified form over `from robodk.robolink import *` — it's clearer about
where a name comes from and won't clobber builtins that `robomath` exports (`pi`, `eye`, ...).
The wildcard form is still fine for short, one-off scripts (it's what most of RoboDK's own
bundled examples use); just don't mix both styles for the same module in one file.

## TypeScript / JavaScript

File: [`TypeScript/src/robodk.ts`](https://github.com/RoboDK/RoboDK-API/blob/master/TypeScript/src/robodk.ts)
(single file — `Mat`, `Robolink`, `Item`, all constants). Published as `@robodk/robodk` on npm,
zero runtime dependencies, Node 18+.

```bash
npm install @robodk/robodk
```

```typescript
import { Robolink, ITEM_TYPE_ROBOT } from '@robodk/robodk';

async function main() {
  const rdk = new Robolink();
  await rdk.Connect();                       // explicit Connect() call, unlike Python's Robolink()
  const robot = await rdk.Item('', ITEM_TYPE_ROBOT);
  await robot.MoveJ([0, -90, 90, 0, 90, 0]);
  const pose = await robot.Pose();
  console.log(pose.Pos());
  rdk.Disconnect();
}
main();
```

**Every I/O method is `async` and returns a `Promise` — `await` all of them.** `Mat` composition
uses `.multiply()` rather than Python's `*` operator overload. Custom connection:
`new Robolink(ip, port, args, robodk_path)`.

## C++

Files: [`robodk_api.h`](https://github.com/RoboDK/RoboDK-API/blob/master/C%2B%2B/robodk_api.h) /
[`robodk_api.cpp`](https://github.com/RoboDK/RoboDK-API/blob/master/C%2B%2B/robodk_api.cpp).
Classes `RoboDK`, `Item`, `Mat : public QMatrix4x4`. Requires Qt (Widgets, GUI, Concurrent,
Core, Network — see [`C++/CMakeLists.txt`](https://github.com/RoboDK/RoboDK-API/blob/master/C%2B%2B/CMakeLists.txt)).

```cpp
#include "robodk_api.h"
using namespace RoboDK_API;   // or #define RDK_SKIP_NAMESPACE to avoid it

RoboDK RDK;                                    // RoboDK(ip="", port=-1, args="", path="")
Item robot = RDK.getItem("", ITEM_TYPE_ROBOT);
Mat pose = robot.Pose();
robot.MoveJ(target);
```

Build as a static library via CMake (also via Conan,
[`C++/conanfile.txt`](https://github.com/RoboDK/RoboDK-API/blob/master/C%2B%2B/conanfile.txt)),
or include the two files directly in a Qt project. Note the lookup method is
`RoboDK::getItem(...)`, not `RoboDK::Item(...)` — C++ reserves `Item` for the class name.

## C#

Two integration options with **incompatible method casing** — pick one per project:

**Option A — [`C#/Example/RoboDK.cs`](https://github.com/RoboDK/RoboDK-API/blob/master/C%23/Example/RoboDKSampleProject/RoboDK.cs)**
(Python-style naming, single file):

```csharp
var RDK = new RoboDK();                        // RoboDK(ip="localhost", start_hidden=false, port=-1, args="", path="")
Item robot = RDK.getItem("", ITEM_TYPE_ROBOT);
robot.setPose(pose);
robot.MoveJ(target);
```

**Option B — NuGet package `RoboDK API`**
([`C#/API/`](https://github.com/RoboDK/RoboDK-API/tree/master/C%23/API), interfaces
`IRoboDk`/`IItem`, PascalCase with explicit `Set`/`Get` prefixes):

```csharp
IRoboDk RDK = new RoboDK();
IItem robot = RDK.GetItemByName("", ITEM_TYPE.Robot);
robot.SetPose(pose);
robot.MoveJ(target);
```

Reference material written against one option will not compile against the other — confirm
which the project uses before pasting a snippet in.

## MATLAB

Files: [`Matlab/Robolink.m`](https://github.com/RoboDK/RoboDK-API/blob/master/Matlab/Robolink.m),
[`Matlab/RobolinkItem.m`](https://github.com/RoboDK/RoboDK-API/blob/master/Matlab/RobolinkItem.m),
plus standalone pose-math helper files (`rotx.m`, `roty.m`, `rotz.m`, `transl.m`,
`Pose_2_KUKA.m`, `KUKA_2_Pose.m`, `Pose_2_Fanuc.m`, `Fanuc_2_Pose.m`, ...) in the same
[`Matlab/`](https://github.com/RoboDK/RoboDK-API/tree/master/Matlab) folder. No build step —
add `/Matlab` to the MATLAB path.

```matlab
RDK = Robolink;
robot = RDK.Item('', 'Robot');
target = RDK.Item('Target 1');
robot.MoveJ(target);
```

`doc Robolink` / `doc RobolinkItem` for inline reference; `showdemo Example_RoboDK` for a live
walkthrough. Example scripts (same folder): `Example_RoboDK.m`, `Example_RoboDK_DrawHexagon.m`,
`Example_RoboDK_ModifyProgram.m`, `Example_RoboDK_SelectRobot.m`, `API_Demo.m`.

## C

Files: [`C/robodk_api_c.h`](https://github.com/RoboDK/RoboDK-API/blob/master/C/robodk_api_c.h) /
[`robodk_api_c.c`](https://github.com/RoboDK/RoboDK-API/blob/master/C/robodk_api_c.c).
Plain-C bindings over the same protocol; only a subset of the full API is implemented.
Winsock-based (`WSAStartup` required on Windows); the low-level socket layer is isolated so
another transport could be substituted. Byte-swapping assumes a little-endian host.

Naming convention: `RoboDK_FunctionName(&rdk, ...)` mirrors `RoboDK::FunctionName()`, and
`Item_FunctionName(&item, ...)` mirrors `Item::FunctionName()` — the struct pointer is always
the first argument, standing in for the implicit `this` in C++.

```c
#include "robodk_api_c.h"

struct RoboDK_t rdk;
RoboDK_Connect_default(&rdk);
struct Item_t robot = RoboDK_getItem(&rdk, "", ITEM_TYPE_ROBOT);
struct Mat_t pose = Item_Pose(&robot);
struct Joints_t joints = Joints_create(6);
Item_MoveJ_joints(&robot, &joints, true);
```

Build via the provided [`C/RoboDK_C_API.pro`](https://github.com/RoboDK/RoboDK-API/blob/master/C/RoboDK_C_API.pro)
(qmake) or [`C/RoboDK_C_API.sln`](https://github.com/RoboDK/RoboDK-API/blob/master/C/RoboDK_C_API.sln)/`.vcxproj`
(Visual Studio 2017) project files.

## Visual Basic

File: [`Visual Basic/RoboDK_API.vb`](https://github.com/RoboDK/RoboDK-API/blob/master/Visual%20Basic/RoboDK_API.vb)
(Python-style naming, single file — "more limited functionality" than the NuGet option per the
language README), or the NuGet package `RoboDK API` (same one C# uses; richer). Requires .NET
Framework ≥ 2.0.

```vb
Dim RDK As New RoboDK()
Dim robot As Item = RDK.getItem("", ITEM_TYPE_ROBOT)
robot.setPose(pose)
robot.MoveJ(target)
```

See [`Visual Basic/Example/`](https://github.com/RoboDK/RoboDK-API/tree/master/Visual%20Basic/Example)
and [`Visual Basic/RoboDKVBAPIDemo/`](https://github.com/RoboDK/RoboDK-API/tree/master/Visual%20Basic/RoboDKVBAPIDemo)
for full worked examples.
