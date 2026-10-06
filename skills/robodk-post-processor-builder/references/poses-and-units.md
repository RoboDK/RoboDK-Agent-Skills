# Poses, Euler conventions and units

The single most common way a post processor is wrong-but-plausible: the numbers look
reasonable, the program loads, and the robot goes to a rotated version of the intended pose.
That is almost always an Euler convention mismatch. Decide the convention from the
controller's documentation or a real exported program — never from what looks familiar.

## Units RoboDK hands you

| Quantity | Unit |
|---|---|
| Translation (pose, zone) | mm |
| Rotary joint values | degrees |
| Prismatic joint / external linear axis values | mm |
| `setSpeed` | mm/s |
| `setAcceleration` | mm/s² |
| `setSpeedJoints` | deg/s |
| `setAccelerationJoints` | deg/s² |
| `setZoneData` | mm |
| `Pause` | milliseconds |

Convert on the way out if the controller differs — UR wants metres and radians, some
controllers want seconds for delays, many want speed as a percentage of maximum. Do the
conversion in the setter or the formatter, in one place, not scattered through the move
methods.

**Percentages need a reference maximum, and that maximum is an assumption.** Controllers
frequently take joint speed and both accelerations as a percentage while RoboDK always
supplies absolute units, so the post must divide by some nominal maximum. That constant is
a guess unless it comes from the robot's datasheet. Put each one in a named class attribute
with a comment saying what it represents, rather than burying a literal in the arithmetic —
it is the first thing to correct when speeds come out wrong on the real machine. Clamp the
result to the controller's documented range; RoboDK will hand over values above the robot's
rating without complaint.

## What a pose actually is

A `Mat`: a 4×4 homogeneous transform. Rotation in the upper-left 3×3, translation in the
fourth column in mm. Indexable as `pose[row, col]`.

`setFrame` gives the frame relative to the robot base. `setTool` gives the tool relative to
the flange. Move poses are the TCP relative to the **active reference frame** — meaning the
same physical point produces different pose numbers after a `setFrame` call. If your post
stores frames rather than emitting them, you must apply that transform yourself.

## Conversion helpers

`robodk.robomath` ships per-brand converters. Names and return shapes commonly available:

| Function | Returns | Used by |
|---|---|---|
| `pose_2_xyzrpw(H)` | `[x,y,z,r,p,w]`, degrees | RoboDK's generic convention |
| `xyzrpw_2_pose(xyzrpw)` | `Mat` | inverse of the above |
| `Pose_2_KUKA(H)` | `[X,Y,Z,A,B,C]`, degrees | KUKA (ZYX Euler) |
| `KUKA_2_Pose(xyzabc)` | `Mat` | KUKA |
| `Pose_2_ABB(H)` | `[x,y,z,q1,q2,q3,q4]` | ABB (quaternion) |
| `Pose_2_Fanuc(H)` | `[x,y,z,w,p,r]`, degrees | Fanuc |
| `Pose_2_Motoman(H)` | `[x,y,z,rx,ry,rz]`, degrees | Motoman/Yaskawa |
| `Pose_2_Nachi(H)` | `[x,y,z,rx,ry,rz]` | Nachi |
| `Pose_2_Staubli(H)` | `[x,y,z,rx,ry,rz]` | Stäubli |
| `Pose_2_UR(H)` | `[x,y,z,rx,ry,rz]` axis-angle | Universal Robots |
| `Pose_2_TxyzRxyz(H)` | `[x,y,z,rx,ry,rz]`, radians | generic |
| `pose_2_quaternion(H)` | `[q1,q2,q3,q4]` | any quaternion controller |

**Do not pick the converter from the syntax family.** A controller that looks like a Fanuc
is not necessarily a Fanuc in orientation. A worked case: Huashu (HSR) controllers use
`P[n]` point records, `UTOOL_NUM`, `CNT` and `DO[n]=ON` — Fanuc-shaped in every visible
respect — but the manual specifies ZYX intrinsic Euler, which is the *KUKA* A/B/C
convention. `Pose_2_Fanuc` and `Pose_2_KUKA` return the same three angles in opposite
order, so the plausible-looking choice produces programs that load cleanly and put the tool
at the wrong orientation on every cartesian target.

Find the sentence in the manual that names the convention, then verify numerically before
building on it: run a known pose through the candidate converter and through an independent
implementation of the manual's definition, and check they agree.

Availability varies with the installed `robodk` version. Confirm the function exists before
relying on it (`python -c "from robodk.robomath import Pose_2_Fanuc"`), and fall back to
extracting the matrix by hand if it doesn't:

```python
import math

def pose_2_zyx_deg(H):
    """X,Y,Z + ZYX (yaw-pitch-roll) Euler angles in degrees, from a 4x4 pose."""
    x, y, z = H[0, 3], H[1, 3], H[2, 3]
    if abs(H[2, 0]) < 1.0 - 1e-9:
        b = math.atan2(-H[2, 0], math.sqrt(H[0, 0] ** 2 + H[1, 0] ** 2))
        a = math.atan2(H[1, 0], H[0, 0])
        c = math.atan2(H[2, 1], H[2, 2])
    else:  # gimbal lock
        b = math.copysign(math.pi / 2.0, -H[2, 0])
        a = 0.0
        c = math.atan2(-H[0, 1], H[1, 1])
    r2d = 180.0 / math.pi
    return [x, y, z, a * r2d, b * r2d, c * r2d]
```

Handle the gimbal-lock branch. Without it, a tool pointing straight down — the single most
common orientation in real programs — produces `nan` or a wild angle pair.

## `PosePP` in intermediate files

Intermediate files build poses with `PosePP`, aliased to `p`:

```python
from robodk.robomath import PosePP as p
r.MoveL(p(902.712, 150, 227.288, 0, -45, 180), [...], [0,0,0])
```

The angle triplet is **not** in the same order as `pose_2_xyzrpw` returns. In the paired
example files, `p(902.712, 150, 227.288, 0, -45, 180)` passed through `pose_2_xyzrpw`
produces `[902.712, 150.000, 227.288, 180.000, -45.000, 0.000]` — the three angles reversed.

Practical consequence: when you diff an intermediate file against generated output to check
a pose survived the round trip, don't expect the digits in the same columns. Compare through
the conversion, or compare the reconstructed matrices.

## Formatting

Use fixed-point formatting with an explicit precision (`'%.3f'`), never `str(float)` or
`repr`. Two reasons: RoboDK produces values like `-8.12093e-15` for a joint that is exactly
zero, and scientific notation is a syntax error in most controller languages; and trailing
float noise (`44.33800000000001`) makes generated programs impossible to diff.

Match the controller's own precision — usually 2–3 decimals for mm, 3–4 for degrees. More
precision than the controller stores just creates diff noise.

Guard against `-0.000` if the controller's parser dislikes it: `x = x + 0.0` won't do it, so
normalise explicitly when it matters.
