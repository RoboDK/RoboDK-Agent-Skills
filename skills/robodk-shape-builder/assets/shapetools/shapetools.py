from dataclasses import dataclass
from pathlib import Path
import json
import os
import sys
import tempfile as _tempfile

from robodk import robolink, robomath

robolink.import_install('pymeshlab')
import pymeshlab as ml


@dataclass
class ModelPaths:
    cube: str
    sph: str
    cyl: str
    prism: str
    cnv_leg: str
    cnv_bar: str
    cnv_bar_w: str
    cnv_bar_l: str
    cnv_bar_cover_1: str
    cnv_bar_cover_2: str
    rail_seg: str
    rail_cr: str
    tbot_seg: str
    tbot_cr: str
    tbot_bm2: str
    tbot_leg: str
    hbot_seg: str
    hbot_bm_y: str
    hbot_bm_z: str
    hbot_cr: str
    hbot_leg: str
    tt_base: str
    tt_base_d: str
    tt_base_u: str
    sc_1: str = ''
    sc_2: str = ''


def new_robolink():
    RDK_ARGUMENTS = []
    if sys.platform.startswith('linux'):
        RDK_ARGUMENTS = ["-NEWINSTANCE", "-EXIT_LAST_COM", "-NOUI"]

    return robolink.Robolink(args=RDK_ARGUMENTS)


def default_paths():
    _d = Path(__file__).resolve().parent
    return ModelPaths(
        cube=str(_d / "models" / "cube.sld"),
        sph=str(_d / "models" / "sph.sld"),
        cyl=str(_d / "models" / "cyl.sld"),
        prism=str(_d / "models" / "prism.sld"),
        cnv_leg=str(_d / "models" / "cnv" / "leg.sld"),
        cnv_bar=str(_d / "models" / "cnv" / "bar.sld"),
        cnv_bar_w=str(_d / "models" / "cnv" / "bar_w.sld"),
        cnv_bar_l=str(_d / "models" / "cnv" / "bar_l.sld"),
        cnv_bar_cover_1=str(_d / "models" / "cnv" / "cover1.sld"),
        cnv_bar_cover_2=str(_d / "models" / "cnv" / "cover2.sld"),
        rail_seg=str(_d / "models" / "rail" / "rail_seg_w1000_h300_1000.sld"),
        rail_cr=str(_d / "models" / "rail" / "rail_cr_w1000_h300.sld"),
        tbot_seg=str(_d / "models" / "tbot" / "tbot_seg_w300_h400_1000.sld"),
        tbot_cr=str(_d / "models" / "tbot" / "tbot_cr_w250_h550_40.sld"),
        tbot_bm2=str(_d / "models" / "tbot" / "tbot_bm_w250_h400_1000.sld"),
        tbot_leg=str(_d / "models" / "tbot" / "tbot_leg_w300_h400_1500.sld"),
        hbot_seg=str(_d / "models" / "hbot" / "hbot_seg_w300_h400_1000.sld"),
        hbot_bm_y=str(_d / "models" / "hbot" / "hbot_bm_y_w350_h250_3000.sld"),
        hbot_bm_z=str(_d / "models" / "hbot" / "hbot_bm_z_w250_h250_1000.sld"),
        hbot_cr=str(_d / "models" / "hbot" / "hbot_cr_w250_h550_40.sld"),
        hbot_leg=str(_d / "models" / "hbot" / "hbot_leg_w300_h400_2000.sld"),
        tt_base=str(_d / "models" / "tt" / "base.sld"),
        tt_base_d=str(_d / "models" / "tt" / "base_d.sld"),
        tt_base_u=str(_d / "models" / "tt" / "base_u.sld"),
        sc_1=str(_d / "scripts" / "side_1.py"),
        sc_2=str(_d / "scripts" / "side_2.py"),
    )


def get_bb(item):
    bb_str = item.setParam("BoundingBox", "Relative")
    bb = json.loads(bb_str)
    return bb["size"]


def _has_ui(RDK):
    """False if this RoboDK instance was launched with -NOUI (headless, no rendering). The
    "Reframe"/"FitAll" view-fitting commands only affect a viewport that doesn't exist in that
    case -- skip them there to save the round-trip rather than issuing a no-op API call."""
    return "-NOUI" not in RDK.ARGUMENTS


def _to_robodk(vertices, triangles, quads=None):
    polys = quads if quads else triangles
    shapes = []
    for face in polys:
        if len(face) == 3:
            v1, v2, v3 = face
            shapes.extend([vertices[v1].tolist(), vertices[v2].tolist(), vertices[v3].tolist()])
        elif len(face) == 4:
            v1, v2, v3, v4 = face
            shapes.extend([vertices[v2].tolist(), vertices[v4].tolist(), vertices[v1].tolist()])
            shapes.extend([vertices[v4].tolist(), vertices[v2].tolist(), vertices[v3].tolist()])
        else:
            raise ValueError(f"Unsupported face with {len(face)} vertices")
    return shapes


def _add_shape(RDK, vertices, triangles, quads=None):
    tris = _to_robodk(vertices, triangles, quads)
    return RDK.AddShape(tris)


def CreateCube(RDK, name, x, y, z, color, parent_frame, is_prism=False):
    paths = default_paths()
    item = RDK.AddFile(paths.prism if is_prism else paths.cube)
    item.setName(name)
    item.setPose(robomath.transl(0.0, 0.0, 0.0))
    item.Scale([x, y, z])
    item.setColor(color)
    item.setPose(robomath.transl(0.0, 0.0, 0.0))

    frame = RDK.AddFrame(name + ' Frame')
    frame.setPose(robomath.transl(0.0, 0.0, 0.0))
    item.setParent(frame)
    frame.setParent(parent_frame)

    item.setVisible(1, 0)
    if _has_ui(RDK):
        item.setParam("Reframe")
        item.setParam("FitAll")
    return frame, item


def CreateSphere(RDK, name, radius, color, parent_frame):
    paths = default_paths()
    item = RDK.AddFile(paths.sph)
    item.setName(name)
    item.setPose(robomath.transl(0.0, 0.0, 0.0))
    item.Scale([radius, radius, radius])
    item.setColor(color)
    item.setPose(robomath.transl(0.0, 0.0, 0.0))

    frame = RDK.AddFrame(name + ' Frame')
    frame.setPose(robomath.transl(0.0, 0.0, 0.0))
    item.setParent(frame)
    frame.setParent(parent_frame)

    item.setVisible(1, 0)
    if _has_ui(RDK):
        item.setParam("Reframe")
        item.setParam("FitAll")
    return frame, item


def CreateCone(RDK, name, r_bottom, r_top, height, quality, color, parent_frame):
    paths = default_paths()
    if r_bottom == r_top:
        item = RDK.AddFile(paths.cyl)
        item.setColor(color)
        item.Scale([r_top, r_top, height])
        item.setGeometryPose(robomath.transl(0.0, 0.0, 0.0))
        item.setName(name)
        item.setPose(robomath.transl(0.0, 0.0, 0.0))
    else:
        ms = ml.MeshSet()
        ms.create_cone(r0=r_bottom, r1=r_top, h=height, subdiv=quality)
        cone = ms.mesh(0)
        item = _add_shape(RDK, cone.vertex_matrix(), cone.face_matrix())
        item.setPose(robomath.transl(0.0, 0.0, 0.0))
        item.setGeometryPose(robomath.transl(0, 0, height / 2) * robomath.rotx(robomath.pi / 2), apply=True)
        item.setColor(color)
        item.setName(name)
        item.setPose(robomath.transl(0.0, 0.0, 0.0))

    frame = RDK.AddFrame(name + ' Frame')
    frame.setPose(robomath.transl(0.0, 0.0, 0.0))
    item.setParent(frame)
    frame.setParent(parent_frame)

    item.setVisible(1, 0)
    if _has_ui(RDK):
        item.setParam("Reframe")
        item.setParam("FitAll")
    return frame, item


def CreateTable(RDK, name, table_x, table_y, table_h1, leg_radius, leg_height,
                main_color, table_color, parent_frame, simple=False):
    paths = default_paths()
    t_plane_item = RDK.AddFile(paths.cube)
    t_plane_item.Scale([table_x, table_y, table_h1])
    t_plane_item.setColor(table_color)

    if simple:
        leg_1_item = RDK.AddFile(paths.cyl)
        leg_1_item.setColor(main_color)
        leg_1_item.Scale([leg_radius, leg_radius, leg_height])
    else:
        leg_1_item = RDK.AddFile(paths.cnv_leg)
        leg_1_item.setPose(robomath.transl(0.0, 0.0, 0.0))
        leg_1_item.setGeometryPose(robomath.transl(-25, -25, 0), True)
        leg_1_item.Scale([leg_radius / 50, leg_radius / 50, leg_height - leg_radius])
        leg_1_item.setGeometryPose(robomath.transl(0, 0, leg_radius), True)
        leg_1_item.setColor(main_color)

        leg_b_clr = [70 / 255, 70 / 255, 70 / 255, 1.0]
        leg_1_bs = RDK.AddFile(paths.cyl)
        leg_1_bs.setPose(robomath.transl(0.0, 0.0, 0.0))
        leg_1_bs.Scale([leg_radius / 2, leg_radius / 2, 10])
        leg_1_bs.setColor(leg_b_clr)

        leg_1_bs2 = RDK.AddFile(paths.cyl)
        leg_1_bs2.setPose(robomath.transl(0.0, 0.0, 0.0))
        leg_1_bs2.Scale([10, 10, leg_radius])
        leg_1_bs2.setColor(leg_b_clr)

        leg_1_item = RDK.MergeItems([leg_1_item, leg_1_bs, leg_1_bs2])

    leg_1_item.Copy()
    leg_2_item = leg_1_item.Parent().Paste()
    leg_3_item = leg_1_item.Parent().Paste()
    leg_4_item = leg_1_item.Parent().Paste()

    leg_1_item.setGeometryPose(robomath.transl(leg_radius, leg_radius, -leg_height), apply=True)
    leg_2_item.setGeometryPose(robomath.transl(table_x - leg_radius, leg_radius, -leg_height), apply=True)
    leg_3_item.setGeometryPose(robomath.transl(leg_radius, table_y - leg_radius, -leg_height), apply=True)
    leg_4_item.setGeometryPose(robomath.transl(table_x - leg_radius, table_y - leg_radius, -leg_height), apply=True)

    final_item = RDK.MergeItems([leg_1_item, leg_2_item, leg_3_item, leg_4_item, t_plane_item])
    final_item.setName(name)
    final_item.setGeometryPose(robomath.transl(0.0, 0.0, 0.0))
    final_item.setGeometryPose(robomath.transl(0.0, 0.0, leg_height), apply=True)

    frame = RDK.AddFrame(name + ' Frame')
    frame.setPose(robomath.transl(0.0, 0.0, 0.0))
    plane_frame = RDK.AddFrame(name + ' Plane Frame')
    plane_frame.setPose(robomath.transl(0.0, 0.0, table_h1 + leg_height))

    plane_frame.setParent(frame)
    final_item.setParent(frame)
    frame.setParent(parent_frame)

    final_item.setVisible(1, 0)
    if _has_ui(RDK):
        final_item.setParam("Reframe")
        final_item.setParam("FitAll")
    return frame, final_item


def CreatePedestal(RDK, name, r1, h1, r2, h2, r3, h3, color, parent_frame, rounded=False):
    paths = default_paths()
    model_path = paths.cyl if rounded else paths.cube

    part_0 = RDK.AddFile(model_path)
    part_0.setColor(color)
    part_0.Copy()
    part_1 = part_0.Parent().Paste()
    part_2 = part_0.Parent().Paste()

    part_0.Scale([r1, r1, h1])
    part_1.Scale([r2, r2, h2])
    part_2.Scale([r3, r3, h3])

    if rounded:
        part_0.setGeometryPose(robomath.transl(0.0, 0.0, 0.0))
        part_1.setGeometryPose(robomath.transl(0.0, 0.0, h1))
        part_2.setGeometryPose(robomath.transl(0.0, 0.0, h1 + h2))
    else:
        part_0.setGeometryPose(robomath.transl(-r1 / 2, -r1 / 2, 0.0))
        part_1.setGeometryPose(robomath.transl(-r2 / 2, -r2 / 2, h1))
        part_2.setGeometryPose(robomath.transl(-r3 / 2, -r3 / 2, h1 + h2))

    final_item = RDK.MergeItems([part_2, part_1, part_0])
    final_item.setName(name)
    final_item.setPose(robomath.transl(0.0, 0.0, 0.0))

    plane_frame = RDK.AddFrame(name + ' Plane Frame')
    plane_frame.setPose(robomath.transl(0.0, 0.0, h1 + h2 + h3))

    frame = RDK.AddFrame(name + ' Frame')
    frame.setPose(robomath.transl(0.0, 0.0, 0.0))
    final_item.setParent(frame)
    plane_frame.setParent(frame)
    frame.setParent(parent_frame)

    final_item.setVisible(1, 0)
    if _has_ui(RDK):
        final_item.setParam("Reframe")
        final_item.setParam("FitAll")
    return frame, final_item


def CreateConveyor(RDK, name, cnv_x, cnv_y, cnv_r, main_color, parent_frame,
                   frame_width=None, frame_height=None, frame_color=None,
                   simple_geometry=False, panel_color=None, create_mechanism=False):
    paths = default_paths()
    cnv_h = 0.0
    cnv_bar_1 = cnv_bar_2 = cnv_bar_3 = cnv_bar_4 = cnv_bar_5 = cnv_bar_6 = None
    cnv_leg_1 = cnv_leg_2 = cnv_leg_3 = cnv_leg_4 = None
    cnv_panels = None

    cnv_plane = RDK.AddFile(paths.cube)
    cnv_plane.setPose(robomath.transl(0.0, 0.0, 0.0))
    cnv_plane.Scale([cnv_x, cnv_y, 2 * cnv_r])
    cnv_plane.setGeometryPose(robomath.transl(0.0, 0.0, -2 * cnv_r))
    cnv_plane.setColor(main_color)

    roll_1 = RDK.AddFile(paths.cyl)
    roll_1.Scale([cnv_r, cnv_r, cnv_y])
    roll_1.setGeometryPose(robomath.transl(0.0, 0.0, -cnv_r) * robomath.rotx(robomath.pi / -2))
    roll_1.setColor(main_color)
    roll_1.Copy()
    roll_2 = roll_1.Parent().Paste()
    roll_2.setPose(robomath.transl(cnv_x, 0, 0))

    has_frame = frame_width is not None and frame_height is not None and frame_color is not None
    if has_frame:
        cnv_w = frame_width
        cnv_h = frame_height
        cnv_bar_th = (cnv_w - cnv_y) / 2

        if simple_geometry:
            cnv_bar_1 = RDK.AddFile(paths.cube)
            cnv_bar_1.setPose(robomath.transl(0.0, 0.0, 0.0))
            cnv_bar_1.Scale([cnv_x + 2 * cnv_r, -cnv_bar_th, 2 * cnv_r])
            cnv_bar_1.setGeometryPose(robomath.transl(-cnv_r, 0.0, -2 * cnv_r), True)
            cnv_bar_1.setColor(frame_color)
        else:
            cnv_bar_1 = RDK.AddFile(paths.cnv_bar)
            cnv_bar_1.setPose(robomath.transl(0.0, 0.0, 0.0))
            cnv_bar_1.Scale([-(cnv_x + 2 * cnv_r), -cnv_bar_th / 50, 2 * cnv_r / 100])
            cnv_bar_1.setGeometryPose(robomath.transl(-cnv_r, 0.0, -2 * cnv_r), True)
            cnv_bar_1.setColor(frame_color)

            c1 = RDK.AddFile(paths.cnv_bar_cover_1)
            c1.setPose(robomath.transl(0.0, 0.0, 0.0))
            c1.Scale([1.0, -cnv_bar_th / 50, 2 * cnv_r / 100])
            c1.setGeometryPose(robomath.transl(-cnv_r - 4, 0.0, -2 * cnv_r), True)

            c2 = RDK.AddFile(paths.cnv_bar_cover_2)
            c2.setPose(robomath.transl(0.0, 0.0, 0.0))
            c2.Scale([1.0, -cnv_bar_th / 50, 2 * cnv_r / 100])
            c2.setGeometryPose(robomath.transl(cnv_x + cnv_r, 0.0, -2 * cnv_r), True)

            cnv_bar_1 = RDK.MergeItems([cnv_bar_1, c1, c2])

        cnv_bar_1.Copy()
        cnv_bar_2 = cnv_bar_1.Paste()
        cnv_bar_2.setGeometryPose(robomath.transl(0.0, cnv_w - cnv_bar_th, 0.0), True)

        if cnv_h > 2 * cnv_r:
            leg_b_clr = [70 / 255, 70 / 255, 70 / 255, 1.0]

            if simple_geometry:
                cnv_leg_1 = RDK.AddFile(paths.cube)
                cnv_leg_1.Scale([-cnv_r, -cnv_bar_th, 3 * cnv_r - cnv_h])
                cnv_leg_1.setGeometryPose(robomath.transl(0.0, 0.0, -2 * cnv_r), True)
            else:
                cnv_leg_1 = RDK.AddFile(paths.cnv_leg)
                cnv_leg_1.Scale([-cnv_r / 50, -cnv_bar_th / 50, 3 * cnv_r - cnv_h])
                cnv_leg_1.setGeometryPose(robomath.transl(0.0, 0.0, -2 * cnv_r), True)

            cnv_leg_1.setColor(frame_color)

            bs1 = RDK.AddFile(paths.cyl)
            bs1.Scale([cnv_r / 2, cnv_r / 2, 10])
            bs1.setGeometryPose(robomath.transl(-cnv_r / 2, -cnv_bar_th / 2, -cnv_h), True)
            bs1.setColor(leg_b_clr)

            bs2 = RDK.AddFile(paths.cyl)
            bs2.Scale([10, 10, cnv_r])
            bs2.setGeometryPose(robomath.transl(-cnv_r / 2, -cnv_bar_th / 2, -cnv_h), True)
            bs2.setColor(leg_b_clr)

            cnv_leg_1 = RDK.MergeItems([cnv_leg_1, bs1, bs2])

            cnv_leg_1.Copy()
            cnv_leg_2 = cnv_leg_1.Paste()
            cnv_leg_2.setGeometryPose(robomath.transl(0.0, cnv_w - cnv_bar_th, 0.0), True)
            cnv_leg_1.Copy()
            cnv_leg_3 = cnv_leg_1.Paste()
            cnv_leg_3.setGeometryPose(robomath.transl(cnv_x + cnv_r, cnv_w - cnv_bar_th, 0.0), True)
            cnv_leg_1.Copy()
            cnv_leg_4 = cnv_leg_1.Paste()
            cnv_leg_4.setGeometryPose(robomath.transl(cnv_x + cnv_r, 0.0, 0.0), True)

        if cnv_h > 5 * cnv_r:
            stp = cnv_x + cnv_r

            if simple_geometry:
                cnv_bar_3 = RDK.AddFile(paths.cube)
                cnv_bar_3.Scale([stp - cnv_r, -cnv_bar_th, cnv_r])
                cnv_bar_3.setGeometryPose(robomath.transl(0.0, 0.0, -cnv_h + 2 * cnv_r), True)
                cnv_bar_5 = RDK.AddFile(paths.cube)
                cnv_bar_5.Scale([-cnv_r, cnv_y, cnv_r])
                cnv_bar_5.setGeometryPose(robomath.transl(0.0, 0.0, -cnv_h + 2 * cnv_r), True)
            else:
                cnv_bar_3 = RDK.AddFile(paths.cnv_bar_l)
                cnv_bar_3.Scale([stp - cnv_r, -cnv_bar_th / 50, cnv_r / 50])
                cnv_bar_3.setGeometryPose(robomath.transl(0.0, 0.0, -cnv_h + 2 * cnv_r), True)
                cnv_bar_5 = RDK.AddFile(paths.cnv_bar_w)
                cnv_bar_5.Scale([-cnv_r / 50, cnv_y, cnv_r / 50])
                cnv_bar_5.setGeometryPose(robomath.transl(0.0, 0.0, -cnv_h + 2 * cnv_r), True)

            cnv_bar_3.setColor(frame_color)
            cnv_bar_5.setColor(frame_color)

            cnv_bar_3.Copy()
            cnv_bar_4 = cnv_bar_3.Paste()
            cnv_bar_4.setGeometryPose(robomath.transl(0.0, cnv_w - cnv_bar_th, 0.0), True)
            cnv_bar_5.Copy()
            cnv_bar_6 = cnv_bar_5.Paste()
            cnv_bar_6.setGeometryPose(robomath.transl(cnv_x + cnv_r, 0.0, 0.0), True)

            if panel_color is not None:
                pn1 = RDK.AddFile(paths.cube)
                pn1.Scale([stp - cnv_r, 10, 5 * cnv_r - cnv_h])
                pn1.setGeometryPose(robomath.transl(0.0, (cnv_y - cnv_w) / 2, -2 * cnv_r), True)
                pn1.setColor(panel_color)
                pn1.Copy()
                pn2 = pn1.Paste()
                pn2.setGeometryPose(robomath.transl(0.0, cnv_w - 10, 0.0), True)
                cnv_panels = RDK.MergeItems([pn1, pn2])

    final_item = RDK.MergeItems([cnv_plane, roll_1, roll_2, cnv_bar_1, cnv_bar_2,
                                  cnv_leg_1, cnv_leg_2, cnv_leg_3, cnv_leg_4,
                                  cnv_bar_3, cnv_bar_4, cnv_bar_5, cnv_bar_6, cnv_panels])
    final_item.setName(name)
    final_item.setPose(robomath.transl(0.0, 0.0, 0.0))

    frame = RDK.AddFrame(name + ' Frame')
    frame.setPose(robomath.transl(0.0, 0.0, cnv_h))
    final_item.setParent(frame)
    frame.setParent(parent_frame)
    final_item.setVisible(1, 0)

    obj_or_robot = final_item
    if create_mechanism:
        robot_name = final_item.Name()
        base_pose = frame.Pose()
        if has_frame:
            base_pose = robomath.Offset(base_pose, -2 * cnv_h, cnv_y / 2, 0, 90, 90, 0)
        else:
            base_pose = robomath.Offset(base_pose, 0, cnv_y / 2, 0, 90, 90, 0)
        tool_pose = frame.Pose()

        new_robot = RDK.BuildMechanism(4, [final_item, None], [], [0], [0], [+1], [0], [cnv_x],
                                        base_pose, tool_pose, robot_name)
        if not new_robot.Valid():
            print("Failed to create the conveyor. Check input values.")
        else:
            print("Conveyor created: " + new_robot.Name())
        new_robot_base = RDK.Item(new_robot.Name() + ' Base')
        new_robot_base.setPose(frame.Pose())
        new_robot_base.setParent(parent_frame)
        frame.Delete()
        frame = new_robot_base
        obj_or_robot = new_robot

    if _has_ui(RDK):
        frame.setParam("Reframe")
        frame.setParam("FitAll")

    return frame, obj_or_robot


def CreateFence(RDK, name, panel_size, panels_x, panels_y, height,
                main_color, panel_color, floor_color, parent_frame,
                sides=(True, True, True, True), include_floor=False, frame_name=None):
    paths = default_paths()
    x_sz = panel_size
    xn = panels_x
    yn = panels_y
    fence_items = []

    if sides[0]:  # D - X1
        col = RDK.AddFile(paths.cube)
        col.Scale([50.0, 50.0, height])
        col.setColor(main_color)
        col.setPose(robomath.transl(0.0, 0.0, 0.0))
        col.Copy()
        fence_items.append(col)
        for i in range(1, xn + 1):
            c = col.Parent().Paste()
            c.setPose(robomath.transl(i * x_sz, 0.0, 0.0))
            fence_items.append(c)

        fp = RDK.AddFile(paths.cube)
        fp.Scale([x_sz, 5.0, height])
        fp.setColor(panel_color)
        fp.setPose(robomath.transl(0.0, 0.0, 0.0))
        fp.setGeometryPose(robomath.transl(25.0, 22.5, 0.0))
        fp.Copy()
        fence_items.append(fp)
        for i in range(1, xn):
            p = fp.Parent().Paste()
            p.setPose(robomath.transl(i * x_sz, 0.0, 0.0))
            fence_items.append(p)

    if sides[1]:  # L - Y1
        col = RDK.AddFile(paths.cube)
        col.Scale([50.0, 50.0, height])
        col.setColor(main_color)
        col.setPose(robomath.transl(0.0, 0.0, 0.0))
        col.Copy()
        fence_items.append(col)
        for i in range(1, yn + 1):
            c = col.Parent().Paste()
            c.setPose(robomath.transl(0.0, i * x_sz, 0.0))
            fence_items.append(c)

        fp = RDK.AddFile(paths.cube)
        fp.Scale([5.0, x_sz, height])
        fp.setColor(panel_color)
        fp.setPose(robomath.transl(0.0, 0.0, 0.0))
        fp.setGeometryPose(robomath.transl(22.5, 25.0, 0.0))
        fp.Copy()
        fence_items.append(fp)
        for i in range(1, yn):
            p = fp.Parent().Paste()
            p.setPose(robomath.transl(0.0, i * x_sz, 0.0))
            fence_items.append(p)

    if sides[2]:  # U - X2
        col = RDK.AddFile(paths.cube)
        col.Scale([50.0, 50.0, height])
        col.setColor(main_color)
        col.setPose(robomath.transl(0.0, yn * x_sz, 0.0))
        col.Copy()
        fence_items.append(col)
        for i in range(1, xn + 1):
            c = col.Parent().Paste()
            c.setPose(robomath.transl(i * x_sz, yn * x_sz, 0.0))
            fence_items.append(c)

        fp = RDK.AddFile(paths.cube)
        fp.Scale([x_sz, 5.0, height])
        fp.setColor(panel_color)
        fp.setPose(robomath.transl(0.0, yn * x_sz, 0.0))
        fp.setGeometryPose(robomath.transl(25.0, 22.5, 0.0))
        fp.Copy()
        fence_items.append(fp)
        for i in range(1, xn):
            p = fp.Parent().Paste()
            p.setPose(robomath.transl(i * x_sz, yn * x_sz, 0.0))
            fence_items.append(p)

    if sides[3]:  # R - Y2
        col = RDK.AddFile(paths.cube)
        col.Scale([50.0, 50.0, height])
        col.setColor(main_color)
        col.setPose(robomath.transl(xn * x_sz, 0.0, 0.0))
        col.Copy()
        fence_items.append(col)
        for i in range(1, yn + 1):
            c = col.Parent().Paste()
            c.setPose(robomath.transl(xn * x_sz, i * x_sz, 0.0))
            fence_items.append(c)

        fp = RDK.AddFile(paths.cube)
        fp.Scale([5.0, x_sz, height])
        fp.setColor(panel_color)
        fp.setPose(robomath.transl(xn * x_sz, 0.0, 0.0))
        fp.setGeometryPose(robomath.transl(25.0, 22.5, 0.0))
        fp.Copy()
        fence_items.append(fp)
        for i in range(1, yn):
            p = fp.Parent().Paste()
            p.setPose(robomath.transl(xn * x_sz, i * x_sz, 0.0))
            fence_items.append(p)

    if include_floor:
        floor = RDK.AddFile(paths.cube)
        floor.setPose(robomath.transl(0.0, 0.0, -10.0))
        floor.Scale([xn * x_sz + 50, yn * x_sz + 50, 10])
        floor.setColor(floor_color)
        fence_items.append(floor)

    if not fence_items:
        return None, None

    final_item = RDK.MergeItems(fence_items)
    final_item.setName(name)

    if include_floor:
        final_item.setGeometryPose(robomath.transl(0.0, 0.0, 0.0))
    else:
        if sides[3]:
            final_item.setGeometryPose(robomath.transl(xn * x_sz, (yn - 1) * x_sz, 0.0))
        elif sides[2]:
            final_item.setGeometryPose(robomath.transl((xn - 1) * x_sz, yn * x_sz, 0.0))
        elif sides[1]:
            final_item.setGeometryPose(robomath.transl(0, (yn - 1) * x_sz, 0.0))
        elif sides[0]:
            final_item.setGeometryPose(robomath.transl((xn - 1) * x_sz, 0, 0.0))

    final_item.setPose(robomath.transl(0.0, 0.0, 0.0))

    frame = RDK.AddFrame(frame_name or (name + ' Frame'))
    frame.setPose(robomath.transl(0.0, 0.0, 0.0))
    final_item.setParent(frame)
    frame.setParent(parent_frame)

    final_item.setVisible(1, 0)
    if _has_ui(RDK):
        final_item.setParam("Reframe")
        final_item.setParam("FitAll")
    return frame, final_item


def CreateRail(RDK, name, rail_x, rail_y, rail_z, rail_x_cr, rail_y_cr, rail_z_cr,
               rail_zero, rail_llim, rail_ulim, main_color, carriage_color, cover_color,
               parent_frame, seg_n=None, seg_sz=None, create_mechanism=False):
    paths = default_paths()
    rail_item_list = []
    rail_cr_item_list = []
    rail_bar_1 = rail_bar_2 = None

    if seg_n is not None and seg_sz is not None:
        rail_seg = RDK.AddFile(paths.rail_seg)
        rail_cr = RDK.AddFile(paths.rail_cr)

        rail_seg.Copy()
        seg_list = RDK.Paste(parent_frame, seg_n - 1)
        rail_seg.setParent(parent_frame)
        seg_list.append(rail_seg)
        for i, sg in enumerate(seg_list):
            sg.setGeometryPose(robomath.transl(i * seg_sz, 0.0, 0.0), True)
            rail_item_list.append(sg)

        rail_cr.setPose(robomath.transl(0.0, 0.0, 0.0))
        rail_cr.setGeometryPose(robomath.transl(rail_zero, 0.0, 0.0), True)
        rail_cr_item_list = [rail_cr]
    else:
        rail_bar_w = (rail_y - rail_y_cr) / 2

        rail_bar_1 = RDK.AddFile(paths.cube)
        rail_bar_1.setPose(robomath.transl(0.0, 0.0, 0.0))
        rail_bar_1.setColor(main_color)

        rail_cv = RDK.AddFile(paths.cube)
        rail_cv.setPose(robomath.transl(0.0, 0.0, 0.0))
        rail_cv.setColor(cover_color)

        rail_cr = RDK.AddFile(paths.cube)
        rail_cr.setPose(robomath.transl(0.0, 0.0, 0.0))
        rail_cr.setColor(carriage_color)

        if rail_bar_w > 0:
            rail_bar_1.Scale([rail_x, rail_bar_w, rail_z])
            rail_bar_1.setGeometryPose(robomath.transl(0.0, 0.0, 0.0), True)
            rail_bar_1.Copy()
            rail_bar_2 = rail_bar_1.Paste()
            rail_bar_2.setGeometryPose(robomath.transl(0.0, rail_y - rail_bar_w, 0.0), True)

            rail_cv.Scale([rail_x, rail_y_cr, rail_z - rail_z_cr])
            rail_cv.setGeometryPose(robomath.transl(0.0, rail_bar_w, 0.0), True)

            rail_cr_h = rail_z - rail_z_cr
            rail_cr.Scale([rail_x_cr, rail_y_cr, rail_z_cr])
            rail_cr.setGeometryPose(robomath.transl(rail_zero - rail_x_cr / 2, rail_bar_w, rail_cr_h), True)

            rail_item_list = [rail_bar_1, rail_bar_2, rail_cv]
            rail_cr_item_list = [rail_cr]
        else:
            rail_bar_1.Scale([rail_x_cr, rail_bar_w, rail_z + rail_z_cr])
            rail_bar_1.setGeometryPose(robomath.transl(rail_zero - rail_x_cr / 2, rail_bar_w, 0.0), True)
            rail_bar_1.setColor(carriage_color)
            rail_bar_1.Copy()
            rail_bar_2 = rail_bar_1.Paste()
            rail_bar_2.setGeometryPose(robomath.transl(0.0, rail_y - rail_bar_w, 0.0), True)
            rail_bar_2.setColor(carriage_color)

            rail_cv.Scale([rail_x, rail_y, rail_z])
            rail_cv.setGeometryPose(robomath.transl(0.0, rail_bar_w, 0.0), True)

            rail_cr_h = rail_z + rail_z_cr
            rail_cr.Scale([rail_x_cr, rail_y_cr - abs(2 * rail_bar_w), rail_z_cr])
            rail_cr.setGeometryPose(robomath.transl(rail_zero - rail_x_cr / 2, rail_bar_w, rail_z), True)

            rail_item_list = [rail_cv]
            rail_cr_item_list = [rail_cr, rail_bar_1, rail_bar_2]

    final_rail = RDK.MergeItems(rail_item_list)
    final_cr = RDK.MergeItems(rail_cr_item_list)
    final_rail.setName(name)
    final_cr.setName(name + ' Carriage')

    frame = RDK.AddFrame(name + ' Frame')
    frame.setPose(robomath.transl(0.0, 0.0, 0.0))
    final_rail.setParent(frame)
    final_cr.setParent(frame)
    frame.setParent(parent_frame)
    final_rail.setVisible(1, 0)

    obj_or_robot = final_rail
    if create_mechanism:
        robot_name = final_rail.Name()
        base_pose = frame.Pose()
        if seg_n is not None and seg_sz is not None:
            base_pose = robomath.Offset(base_pose, rail_zero, rail_y / 2, rail_z, 90, 90, 0)
        else:
            rail_bar_w = (rail_y - rail_y_cr) / 2
            if rail_bar_w > 0:
                base_pose = robomath.Offset(base_pose, rail_zero, rail_y / 2, rail_z, 90, 90, 0)
            else:
                base_pose = robomath.Offset(base_pose, rail_zero, rail_y / 2, rail_z + rail_z_cr, 90, 90, 0)

        tool_pose = frame.Pose()
        tool_pose = robomath.Offset(tool_pose, 0, 0, 0, -90, 0, -90)

        new_robot = RDK.BuildMechanism(4, [final_rail, final_cr], [], [0], [0], [+1],
                                        [rail_llim], [rail_ulim], base_pose, tool_pose, robot_name)
        if not new_robot.Valid():
            print("Failed to create the rail. Check input values.")
        else:
            print("Rail created: " + new_robot.Name())
        new_robot_base = RDK.Item(new_robot.Name() + ' Base')
        new_robot_base.setPose(frame.Pose())
        new_robot_base.setParent(parent_frame)
        frame.Delete()
        frame = new_robot_base
        obj_or_robot = new_robot

    if _has_ui(RDK):
        frame.setParam("Reframe")
        frame.setParam("FitAll")

    return frame, obj_or_robot


def CreateTbot(RDK, name,
               tbot_x, tbot_y, tbot_z,
               tbot_cr_x, tbot_cr_y, tbot_cr_z,
               tbot_beam2_x, tbot_beam2_y, tbot_beam2_z,
               tbot_zero, tbot_llim, tbot_ulim,
               tbot_beam2_zero, tbot_beam2_llim, tbot_beam2_ulim,
               main_color, carriage_color, beam2_color, parent_frame,
               leg_n=None, leg_sz=None, seg_n=None, seg_sz=None,
               create_mechanism=False):
    paths = default_paths()
    tbot_item_list = []
    tbot_cr_item_list = []
    tbot_beam2_item_list = []

    if seg_n is not None and seg_sz is not None:
        tbot_seg = RDK.AddFile(paths.tbot_seg)
        tbot_cr = RDK.AddFile(paths.tbot_cr)
        tbot_beam2 = RDK.AddFile(paths.tbot_bm2)

        tbot_seg.Copy()
        seg_list = RDK.Paste(parent_frame, seg_n - 1)
        tbot_seg.setParent(parent_frame)
        seg_list.append(tbot_seg)
        for i, sg in enumerate(seg_list):
            sg.setGeometryPose(robomath.transl(i * seg_sz, 0.0, 0.0), True)
            tbot_item_list.append(sg)

        tbot_cr.setPose(robomath.transl(0.0, 0.0, 0.0))
        tbot_cr.setGeometryPose(robomath.transl(tbot_zero, 0.0, 0.0), True)
        tbot_cr_item_list = [tbot_cr]

        tbot_beam2.setPose(robomath.transl(0.0, 0.0, 0.0))
        tbot_beam2.setGeometryPose(robomath.transl(tbot_zero, 0.0, 0.0), True)
        tbot_beam2_item_list = [tbot_beam2]

        if leg_n is not None and leg_sz is not None:
            leg1 = RDK.AddFile(paths.tbot_leg)
            leg1.setPose(robomath.transl(0.0, 0.0, 0.0))
            leg1.setGeometryPose(robomath.transl(0.0, 0.0, 0.0), True)
            tbot_item_list.append(leg1)
            leg1.Copy()
            leg2 = RDK.Paste()
            leg2.setGeometryPose(robomath.transl(tbot_x - tbot_z, 0.0, 0.0), True)
            tbot_item_list.append(leg2)
            if leg_n > 2:
                step = (tbot_x - 2 * tbot_z) / (leg_n - 1)
                for i in range(1, leg_n - 1):
                    lx = tbot_z / 2 + i * step
                    li = RDK.Paste()
                    li.setGeometryPose(robomath.transl(lx, 0.0, 0.0), True)
                    tbot_item_list.append(li)
    else:
        tbot_beam = RDK.AddFile(paths.cube)
        tbot_beam.setPose(robomath.transl(0.0, 0.0, 0.0))
        tbot_beam.setColor(main_color)

        tbot_beam2 = RDK.AddFile(paths.cube)
        tbot_beam2.setPose(robomath.transl(0.0, 0.0, 0.0))
        tbot_beam2.setColor(beam2_color)

        tbot_cr = RDK.AddFile(paths.cube)
        tbot_cr.setPose(robomath.transl(0.0, 0.0, 0.0))
        tbot_cr.setColor(carriage_color)

        tbot_beam.Scale([tbot_x, tbot_y, tbot_z])
        tbot_beam.setGeometryPose(robomath.transl(0.0, 0.0, 0.0), True)

        tbot_cr.Scale([tbot_cr_x, tbot_cr_y, tbot_cr_z])
        tbot_cr.setGeometryPose(robomath.transl(tbot_zero - tbot_cr_x / 2, tbot_y, 0), True)

        tbot_beam2.Scale([tbot_beam2_y, tbot_beam2_z, tbot_beam2_x])
        tbot_beam2.setGeometryPose(robomath.transl(tbot_zero - tbot_beam2_y / 2, tbot_y + tbot_cr_y, tbot_beam2_zero), True)

        if leg_n is not None and leg_sz is not None:
            leg1 = RDK.AddFile(paths.cube)
            leg1.setPose(robomath.transl(0.0, 0.0, 0.0))
            leg1.setColor(main_color)
            leg1.Scale([tbot_z, tbot_y, -leg_sz])
            leg1.setGeometryPose(robomath.transl(0.0, 0.0, 0.0), True)
            tbot_item_list.append(leg1)
            leg1.Copy()
            leg2 = RDK.Paste()
            leg2.setGeometryPose(robomath.transl(tbot_x - tbot_z, 0.0, 0.0), True)
            tbot_item_list.append(leg2)
            if leg_n > 2:
                step = (tbot_x - 2 * tbot_z) / (leg_n - 1)
                for i in range(1, leg_n - 1):
                    lx = tbot_z / 2 + i * step
                    li = RDK.Paste()
                    li.setGeometryPose(robomath.transl(lx, 0.0, 0.0), True)
                    tbot_item_list.append(li)

        tbot_item_list.append(tbot_beam)
        tbot_cr_item_list = [tbot_cr]
        tbot_beam2_item_list = [tbot_beam2]

    final_beam = RDK.MergeItems(tbot_item_list)
    final_cr = RDK.MergeItems(tbot_cr_item_list)
    final_beam2 = RDK.MergeItems(tbot_beam2_item_list)

    final_beam.setName(name)
    final_cr.setName(name + ' Carriage')
    final_beam2.setName(name + ' Z axis')

    frame = RDK.AddFrame(name + ' Frame')
    frame.setPose(robomath.transl(0.0, 0.0, 0.0))
    final_beam.setParent(frame)
    final_cr.setParent(frame)
    final_beam2.setParent(frame)
    frame.setParent(parent_frame)
    final_beam.setVisible(1, 0)

    obj_or_robot = final_beam
    if create_mechanism:
        robot_name = final_beam.Name()
        base_pose = frame.Pose()
        base_pose = robomath.Offset(base_pose, tbot_zero, tbot_y + tbot_cr_y + (tbot_beam2_z / 2), tbot_beam2_zero, 90, 90, 0)
        tool_pose = frame.Pose()
        tool_pose = robomath.Offset(tool_pose, 0, 0, 0, 0, 0, 0)

        new_robot = RDK.BuildMechanism(5, [final_beam, final_cr, final_beam2], [0, 0, 0, 0],
                                        [0], [0], [+1, -1],
                                        [tbot_llim, tbot_beam2_llim], [tbot_ulim, tbot_beam2_ulim],
                                        base_pose, tool_pose, robot_name)
        if not new_robot.Valid():
            print("Failed to create the T-bot. Check input values.")
        else:
            print("T-bot created: " + new_robot.Name())
        new_robot_base = RDK.Item(new_robot.Name() + ' Base')
        new_robot_base.setPose(frame.Pose())
        new_robot_base.setParent(parent_frame)
        frame.Delete()
        frame = new_robot_base
        obj_or_robot = new_robot

    if _has_ui(RDK):
        frame.setParam("Reframe")
        frame.setParam("FitAll")

    return frame, obj_or_robot


def CreateHbot(RDK, name,
               hbot_bm1_x, hbot_bm1_y, hbot_bm1_z,
               hbot_bm2_x, hbot_bm2_y, hbot_bm2_z,
               hbot_bm3_x, hbot_bm3_y, hbot_bm3_z,
               hbot_cr_x, hbot_cr_y, hbot_cr_z,
               hbot_bm1_zero, hbot_bm1_llim, hbot_bm1_ulim,
               hbot_bm2_zero, hbot_bm2_llim, hbot_bm2_ulim,
               hbot_bm3_zero, hbot_bm3_llim, hbot_bm3_ulim,
               main_color, beam_y_color, beam_z_color, carriage_color, parent_frame,
               with_sides=False, leg_n=None, leg_sz=None, seg_n=None, seg_sz=None,
               create_mechanism=False):
    paths = default_paths()
    hbot_bm1_item_list = []
    hbot_bm2_item_list = []
    hbot_cr_item_list = []
    hbot_bm3_item_list = []

    if seg_n is not None and seg_sz is not None:
        hbot_seg = RDK.AddFile(paths.hbot_seg)
        hbot_cr = RDK.AddFile(paths.hbot_cr)
        hbot_beam_y = RDK.AddFile(paths.hbot_bm_y)
        hbot_beam_z = RDK.AddFile(paths.hbot_bm_z)

        hbot_seg.Copy()
        seg_list = RDK.Paste(parent_frame, seg_n - 1)
        hbot_seg.setParent(parent_frame)
        seg_list.append(hbot_seg)
        for i, sg in enumerate(seg_list):
            sg.setGeometryPose(robomath.transl(i * seg_sz, 0.0, 0.0), True)
            hbot_bm1_item_list.append(sg)

        if leg_n is not None and leg_sz is not None:
            leg1 = RDK.AddFile(paths.hbot_leg)
            leg1.setPose(robomath.transl(0.0, 0.0, 0.0))
            leg1.setGeometryPose(robomath.transl(0.0, 0.0, 0.0), True)
            hbot_bm1_item_list.append(leg1)
            leg1.Copy()
            leg2 = RDK.Paste()
            leg2.setGeometryPose(robomath.transl(hbot_bm1_x - hbot_bm1_z, 0.0, 0.0), True)
            hbot_bm1_item_list.append(leg2)
            if leg_n > 2:
                step = (hbot_bm1_x - 2 * hbot_bm1_z) / (leg_n - 1)
                for i in range(1, leg_n - 1):
                    lx = hbot_bm1_z / 2 + i * step
                    li = RDK.Paste()
                    li.setGeometryPose(robomath.transl(lx, 0.0, 0.0), True)
                    hbot_bm1_item_list.append(li)

        hbot_cr.setPose(robomath.transl(0.0, 0.0, 0.0))
        hbot_cr.setGeometryPose(robomath.transl(hbot_bm1_zero, hbot_bm2_zero, 0.0), True)
        hbot_cr_item_list = [hbot_cr]

        hbot_beam_y.setPose(robomath.transl(0.0, 0.0, 0.0))
        hbot_beam_y.setGeometryPose(robomath.transl(hbot_bm1_zero, 0.0, 0.0), True)
        hbot_bm2_item_list = [hbot_beam_y]

        hbot_beam_z.setPose(robomath.transl(0.0, 0.0, 0.0))
        hbot_beam_z.setGeometryPose(robomath.transl(hbot_bm1_zero, hbot_bm2_zero, hbot_bm3_zero), True)
        hbot_bm3_item_list = [hbot_beam_z]
    else:
        hbot_beam_x1 = RDK.AddFile(paths.cube)
        hbot_beam_x1.setPose(robomath.transl(0.0, 0.0, 0.0))
        hbot_beam_x1.setColor(main_color)

        hbot_beam_y = RDK.AddFile(paths.cube)
        hbot_beam_y.setPose(robomath.transl(0.0, 0.0, 0.0))
        hbot_beam_y.setColor(beam_y_color)

        hbot_beam_z = RDK.AddFile(paths.cube)
        hbot_beam_z.setPose(robomath.transl(0.0, 0.0, 0.0))
        hbot_beam_z.setColor(beam_z_color)

        hbot_cr = RDK.AddFile(paths.cube)
        hbot_cr.setPose(robomath.transl(0.0, 0.0, 0.0))
        hbot_cr.setColor(carriage_color)

        hbot_beam_x1.Scale([hbot_bm1_x, hbot_bm1_y, hbot_bm1_z])
        hbot_beam_x1.setGeometryPose(robomath.transl(0.0, 0.0, 0.0), True)

        if leg_n is not None and leg_sz is not None:
            leg1 = RDK.AddFile(paths.cube)
            leg1.setPose(robomath.transl(0.0, 0.0, 0.0))
            leg1.setColor(main_color)
            leg1.Scale([hbot_bm1_z, hbot_bm1_y, -leg_sz])
            leg1.setGeometryPose(robomath.transl(0.0, 0.0, 0.0), True)
            hbot_bm1_item_list.append(leg1)
            leg1.Copy()
            leg2 = RDK.Paste()
            leg2.setGeometryPose(robomath.transl(hbot_bm1_x - hbot_bm1_z, 0.0, 0.0), True)
            hbot_bm1_item_list.append(leg2)
            if leg_n > 2:
                step = (hbot_bm1_x - 2 * hbot_bm1_z) / (leg_n - 1)
                for i in range(1, leg_n - 1):
                    lx = hbot_bm1_z / 2 + i * step
                    li = RDK.Paste()
                    li.setGeometryPose(robomath.transl(lx, 0.0, 0.0), True)
                    hbot_bm1_item_list.append(li)

        hbot_beam_y.Scale([hbot_bm2_y, hbot_bm2_x, hbot_bm2_z])
        hbot_beam_y.setGeometryPose(robomath.transl(hbot_bm1_zero - hbot_bm2_y - hbot_cr_x - hbot_bm3_z / 2, hbot_bm1_y, 0), True)

        hbot_cr.Scale([hbot_cr_x, hbot_cr_y, hbot_cr_z])
        hbot_cr.setGeometryPose(robomath.transl(hbot_bm1_zero - hbot_cr_x - hbot_bm3_z / 2, hbot_bm2_zero + hbot_bm1_y - hbot_cr_y / 2, 0), True)

        hbot_beam_z.Scale([hbot_bm3_z, hbot_bm3_y, hbot_bm3_x])
        hbot_beam_z.setGeometryPose(robomath.transl(hbot_bm1_zero - hbot_bm3_z / 2, hbot_bm2_zero + hbot_bm1_y - hbot_bm3_y / 2, hbot_bm3_zero), True)

        hbot_bm1_item_list.append(hbot_beam_x1)
        hbot_cr_item_list = [hbot_cr]
        hbot_bm2_item_list = [hbot_beam_y]
        hbot_bm3_item_list = [hbot_beam_z]

    hbot_beam_x1 = RDK.MergeItems(hbot_bm1_item_list)

    if with_sides:
        hbot_beam_x1.Copy()
        hbot_beam_x2 = RDK.Paste()
        hbot_beam_x2.setGeometryPose(robomath.transl(hbot_bm1_x, hbot_bm2_x + 2 * hbot_bm1_y, 0.0) * robomath.rotz(robomath.pi), True)
    else:
        hbot_beam_x2 = None

    final_bm1 = RDK.MergeItems([hbot_beam_x1, hbot_beam_x2])
    final_cr = RDK.MergeItems(hbot_cr_item_list)
    final_bm2 = RDK.MergeItems(hbot_bm2_item_list)
    final_bm3 = RDK.MergeItems(hbot_bm3_item_list)

    final_bm1.setName(name)
    final_bm2.setName(name + ' Y axis')
    final_cr.setName(name + ' Carriage')
    final_bm3.setName(name + ' Z axis')

    frame = RDK.AddFrame(name + ' Frame')
    frame.setPose(robomath.transl(0.0, 0.0, 0.0))
    final_bm1.setParent(frame)
    final_cr.setParent(frame)
    final_bm2.setParent(frame)
    final_bm3.setParent(frame)
    frame.setParent(parent_frame)

    obj_or_robot = final_bm1
    if create_mechanism:
        robot_name = final_bm1.Name()
        base_pose = frame.Pose()
        base_pose = robomath.Offset(base_pose, hbot_bm1_zero, hbot_bm1_y + hbot_bm2_zero, hbot_bm3_zero, 0, -90, 0)
        tool_pose = frame.Pose()
        tool_pose = robomath.Offset(tool_pose, 0, 0, 0, 180, 0, 180)

        new_robot = RDK.BuildMechanism(6, [final_bm1, final_bm2, final_cr, final_bm3],
                                        [0, 0, 0, 0, 0, 0], [0], [0], [-1, -1, +1],
                                        [hbot_bm1_llim, hbot_bm2_llim, hbot_bm3_llim],
                                        [hbot_bm1_ulim, hbot_bm2_ulim, hbot_bm3_ulim],
                                        base_pose, tool_pose, robot_name)
        if not new_robot.Valid():
            print("Failed to create the H-bot. Check input values.")
        else:
            print("H-bot created: " + new_robot.Name())
        new_robot_base = RDK.Item(new_robot.Name() + ' Base')
        new_robot_base.setPose(frame.Pose())
        new_robot_base.setParent(parent_frame)
        frame.Delete()
        frame = new_robot_base
        obj_or_robot = new_robot

    if _has_ui(RDK):
        frame.setParam("Reframe")
        frame.setParam("FitAll")

    return frame, obj_or_robot


def CreateTurntable(RDK, name, radius, height, base_color, flange_color, parent_frame,
                    with_base=True, horizontal=False, horizontal_cp=False, cp_dist=0,
                    tt_llim=0, tt_ulim=360, create_mechanism=False):
    paths = default_paths()
    tt_h = height if with_base else 10.0
    tt_scale = radius / 50

    tt_base_d = RDK.AddFile(paths.tt_base_d)
    tt_base_d.setPose(robomath.transl(0.0, 0.0, 0.0))
    tt_base_d.Scale([tt_scale, tt_scale, 1.0])
    tt_base_d.setColor(base_color)

    tt_base = None
    tt_base_u = None
    if with_base:
        tt_base = RDK.AddFile(paths.tt_base)
        tt_base.setPose(robomath.transl(0.0, 0.0, 0.0))
        tt_base.Scale([tt_scale, tt_scale, tt_h - 10])
        tt_base.setColor(base_color)

        if horizontal:
            tt_base_u = RDK.AddFile(paths.tt_base_u)
            tt_base_u.setPose(robomath.transl(0.0, 0.0, 0.0))
            tt_base_u.Scale([tt_scale, tt_scale, tt_scale])
            tt_base_u.setGeometryPose(robomath.transl(0.0, 0.0, tt_h - 10.0), True)
            tt_base_u.setColor(flange_color)

    tt_flange = RDK.AddFile(paths.cyl)
    tt_flange.setPose(robomath.transl(0.0, 0.0, 0.0))
    tt_flange.Scale([radius, radius, 10.0])
    tt_flange.setColor(flange_color)

    if horizontal:
        if with_base:
            tt_flange.setGeometryPose(robomath.transl(radius + 10, 0.0, tt_h + radius - 10.0) * robomath.roty(robomath.pi / -2), True)
        else:
            tt_flange.setGeometryPose(robomath.transl(0.0, 0.0, tt_h - 10) * robomath.roty(robomath.pi / -2), True)
    else:
        tt_flange.setGeometryPose(robomath.transl(0.0, 0.0, tt_h - 10), True)

    final_base = RDK.MergeItems([tt_base_d, tt_base, tt_base_u])

    if horizontal_cp and horizontal and with_base:
        final_base.Copy()
        cp2 = final_base.Paste()
        cp2.setPose(robomath.transl(0.0, 0.0, 0.0))
        cp2.setGeometryPose(robomath.transl(radius + cp_dist, 0.0, 0) * robomath.rotz(robomath.pi), True)
        cp2.setColor(base_color)
        final_base = RDK.MergeItems([final_base, cp2])

    final_flange = RDK.MergeItems([tt_flange])
    final_base.setName(name)
    final_flange.setName(name + ' Flange')

    frame = RDK.AddFrame(name + ' Frame')
    frame.setPose(robomath.transl(0.0, 0.0, 0.0))
    final_base.setParent(frame)
    final_flange.setParent(frame)
    frame.setParent(parent_frame)

    if with_base:
        final_base.setVisible(1, 0)
    else:
        final_base.setVisible(0, 0)

    obj_or_robot = final_base
    if create_mechanism:
        robot_name = final_base.Name()
        base_pose = frame.Pose()
        tool_pose = frame.Pose()

        if horizontal:
            tool_pose = robomath.Offset(tool_pose, 0, 0, 0, 0, 0, 180)
            if with_base:
                base_pose = robomath.Offset(base_pose, radius + 10, 0.0, tt_h + radius - 10, 0, 90, 0)
            else:
                base_pose = robomath.Offset(base_pose, 0.0, 0.0, tt_h - 10, 0, 90, 0)
        else:
            tool_pose = robomath.Offset(tool_pose, 0, 0, 0, 0, 0, 0)
            if with_base:
                base_pose = robomath.Offset(base_pose, 0.0, 0.0, tt_h, 0, 0, 0)
            else:
                base_pose = robomath.Offset(base_pose, 0.0, 0.0, 10, 0, 0, 0)

        objects = [final_base if with_base else None, final_flange]
        new_robot = RDK.BuildMechanism(1, objects, [], [0], [0], [+1],
                                        [tt_llim], [tt_ulim], base_pose, tool_pose, robot_name)
        if not new_robot.Valid():
            print("Failed to create the turntable. Check input values.")
        else:
            print("Turntable created: " + new_robot.Name())
        new_robot_base = RDK.Item(new_robot.Name() + ' Base')
        new_robot_base.setPose(frame.Pose())
        new_robot_base.setParent(parent_frame)
        frame.Delete()
        frame = new_robot_base
        obj_or_robot = new_robot

    if _has_ui(RDK):
        frame.setParam("Reframe")
        frame.setParam("FitAll")

    return frame, obj_or_robot


def CreateTurntable2(RDK, name, radius, height, arm_length, vertical_offset, cp_dist,
                     base_color, beam_color, flange_color, parent_frame,
                     with_base=True, with_cp=False,
                     tl_llim=0, tl_ulim=360, trn_llim=0, trn_ulim=360,
                     create_mechanism=False):
    paths = default_paths()
    tt2_scale = radius / 50
    tt2_bm1_th = radius / 2
    tt2_bm2_th = radius / 2

    tt2_base_d = RDK.AddFile(paths.tt_base_d)
    tt2_base_d.setPose(robomath.transl(0.0, 0.0, 0.0))
    tt2_base_d.Scale([tt2_scale, tt2_scale, 1.0])
    tt2_base_d.setColor(base_color)

    tt2_base = RDK.AddFile(paths.tt_base)
    tt2_base.setPose(robomath.transl(0.0, 0.0, 0.0))
    tt2_base.Scale([tt2_scale, tt2_scale, height])
    tt2_base.setColor(base_color)

    tt2_base_u = RDK.AddFile(paths.tt_base_u)
    tt2_base_u.setPose(robomath.transl(0.0, 0.0, 0.0))
    tt2_base_u.Scale([tt2_scale, tt2_scale, tt2_scale])
    tt2_base_u.setGeometryPose(robomath.transl(0.0, 0.0, height), True)
    tt2_base_u.setColor(base_color)

    tt2_bm1 = RDK.AddFile(paths.cube)
    tt2_bm1.setPose(robomath.transl(0.0, 0.0, 0.0))

    if abs(vertical_offset) <= abs(radius - tt2_bm2_th):
        tt2_bm1.Scale([tt2_bm1_th, 2 * radius, 2 * radius])
        tt2_bm1.setGeometryPose(robomath.transl(radius, -radius, height), True)
    else:
        if vertical_offset > 0:
            tt2_bm1.Scale([tt2_bm1_th, 2 * radius, radius + vertical_offset + tt2_bm2_th])
            tt2_bm1.setGeometryPose(robomath.transl(radius, -radius, height + radius - vertical_offset - tt2_bm2_th), True)
        else:
            tt2_bm1.Scale([tt2_bm1_th, 2 * radius, radius - vertical_offset])
            tt2_bm1.setGeometryPose(robomath.transl(radius, -radius, height), True)

    tt2_bm1.setColor(beam_color)

    tt2_bm2 = RDK.AddFile(paths.cube)
    tt2_bm2.setPose(robomath.transl(0.0, 0.0, 0.0))
    if with_cp:
        tt2_bm2.Scale([cp_dist / 2, 2 * radius, tt2_bm2_th])
    else:
        tt2_bm2.Scale([arm_length + radius, 2 * radius, tt2_bm2_th])
    tt2_bm2.setGeometryPose(robomath.transl(radius + tt2_bm1_th, -radius, height + radius - vertical_offset - tt2_bm2_th), True)
    tt2_bm2.setColor(beam_color)

    tt2_flange = RDK.AddFile(paths.cyl)
    tt2_flange.setPose(robomath.transl(0.0, 0.0, 0.0))
    tt2_flange.Scale([radius, radius, -10.0])
    tt2_flange.setColor(flange_color)
    tt2_flange.setGeometryPose(robomath.transl(radius + arm_length + tt2_bm1_th, 0.0, height + radius - vertical_offset + 10), True)

    final_base = RDK.MergeItems([tt2_base_d, tt2_base, tt2_base_u])
    final_bm = RDK.MergeItems([tt2_bm1, tt2_bm2])

    if with_cp:
        final_base.Copy()
        base_cp2 = final_base.Paste()
        base_cp2.setPose(robomath.transl(0.0, 0.0, 0.0))
        base_cp2.setGeometryPose(robomath.transl(-radius + cp_dist, 0.0, 0) * robomath.rotz(robomath.pi), True)
        base_cp2.setColor(base_color)

        final_bm.Copy()
        bm_cp2 = final_bm.Paste()
        bm_cp2.setPose(robomath.transl(0.0, 0.0, 0.0))
        bm_cp2.setGeometryPose(robomath.transl(-radius + cp_dist, 0.0, 0) * robomath.rotz(robomath.pi), True)
        bm_cp2.setColor(beam_color)

        final_base = RDK.MergeItems([final_base, base_cp2])
        final_bm = RDK.MergeItems([final_bm, bm_cp2])

    final_fl = RDK.MergeItems([tt2_flange])

    offset = robomath.transl(-radius - arm_length - tt2_bm1_th, 0.0, 0.0)
    rot = robomath.rotz(robomath.pi / 2)
    final_base.setGeometryPose(offset, True)
    final_fl.setGeometryPose(offset, True)
    final_bm.setGeometryPose(offset, True)
    final_base.setGeometryPose(robomath.transl(0, 0.0, 0.0) * rot, True)
    final_fl.setGeometryPose(robomath.transl(0, 0.0, 0.0) * rot, True)
    final_bm.setGeometryPose(robomath.transl(0, 0.0, 0.0) * rot, True)

    final_base.setName(name)
    final_fl.setName(name + ' Flange')
    final_bm.setName(name + ' Beam')

    frame = RDK.AddFrame(name + ' Frame')
    frame.setPose(robomath.transl(0.0, 0.0, 0.0))
    final_base.setParent(frame)
    final_fl.setParent(frame)
    final_bm.setParent(frame)
    frame.setParent(parent_frame)

    if with_base:
        final_base.setVisible(1, 0)
    else:
        final_base.setVisible(0, 0)

    obj_or_robot = final_base
    if create_mechanism:
        robot_name = final_base.Name()
        base_pose = frame.Pose()
        tool_pose = frame.Pose()
        tool_pose = robomath.Offset(tool_pose, 0, 0, vertical_offset - 10, 180, 0, 180)
        base_pose = robomath.Offset(base_pose, 0.0, 0.0, height + radius, 90, 0, -180)

        objects = [final_base if with_base else None, final_bm, final_fl]
        new_robot = RDK.BuildMechanism(2, objects, [-90, 0.0], [0], [0], [+1, +1],
                                        [tl_llim, trn_llim], [tl_ulim, trn_ulim],
                                        base_pose, tool_pose, robot_name)
        if not new_robot.Valid():
            print("Failed to create the turntable2. Check input values.")
        else:
            print("Turntable2 created: " + new_robot.Name())
        new_robot_base = RDK.Item(new_robot.Name() + ' Base')
        new_robot_base.setPose(frame.Pose())
        new_robot_base.setParent(parent_frame)
        frame.Delete()
        frame = new_robot_base
        obj_or_robot = new_robot

    if _has_ui(RDK):
        frame.setParam("Reframe")
        frame.setParam("FitAll")

    return frame, obj_or_robot


def CreateTurntable3(RDK, name, radius, height, arm_length, vertical_offset,
                     base_color, beam_color, flange_color, parent_frame,
                     tl_llim=0, tl_ulim=360, trn_llim=0, trn_ulim=360,
                     create_mechanism=False, create_scripts=False):
    paths = default_paths()
    if vertical_offset < 3 * radius:
        vertical_offset = 3 * radius

    tt3_scale = radius / 50

    frame = RDK.AddFrame(name + ' Frame')
    frame.setPose(robomath.transl(0.0, 0.0, 0.0))
    frame.setParent(parent_frame)

    tt3_base_d = RDK.AddFile(paths.tt_base_d)
    tt3_base_d.setPose(robomath.transl(0.0, 0.0, 0.0))
    tt3_base_d.Scale([2 * tt3_scale, 2 * tt3_scale, 1.0])
    tt3_base_d.setColor(base_color)

    tt3_base = RDK.AddFile(paths.tt_base)
    tt3_base.setPose(robomath.transl(0.0, 0.0, 0.0))
    tt3_base.Scale([2 * tt3_scale, 2 * tt3_scale, height - radius + radius / 5])
    tt3_base.setColor(base_color)

    final_base = RDK.MergeItems([tt3_base_d, tt3_base])
    final_base.setName(name)
    final_base.setParent(frame)

    if height <= 0.8 * radius:
        final_base.setVisible(0, 0)

    tt3_bm1_1 = RDK.AddFile(paths.cube)
    tt3_bm1_1.setPose(robomath.transl(0.0, 0.0, 0.0))
    tt3_bm1_1.Scale([-arm_length, -2 * radius, 2 * radius - 2 * radius / 5])
    tt3_bm1_1.setGeometryPose(robomath.transl(0, 0, -radius + radius / 5), True)

    tt3_bm1_2 = RDK.AddFile(paths.tt_base)
    tt3_bm1_2.setPose(robomath.transl(0.0, 0.0, 0.0))
    tt3_bm1_2.Scale([tt3_scale, tt3_scale, vertical_offset - radius])
    tt3_bm1_2.setGeometryPose(robomath.transl(-arm_length - radius, 0, 0) * robomath.rotx(robomath.pi / 2), True)

    tt3_bm1_3 = RDK.AddFile(paths.tt_base_u)
    tt3_bm1_3.setPose(robomath.transl(0.0, 0.0, 0.0))
    tt3_bm1_3.Scale([tt3_scale, tt3_scale, tt3_scale])
    tt3_bm1_3.setGeometryPose(robomath.transl(-arm_length - radius, -vertical_offset + radius, 0) * robomath.rotx(robomath.pi / 2), True)

    tt3_bm1 = RDK.MergeItems([tt3_bm1_1, tt3_bm1_2, tt3_bm1_3])
    tt3_bm1.Copy()
    tt3_bm2 = tt3_bm1.Paste()
    tt3_bm2.setGeometryPose(robomath.roty(robomath.pi), True)
    tt3_bm3 = tt3_bm1.Paste()
    tt3_bm3.setGeometryPose(robomath.rotx(robomath.pi), True)
    tt3_bm4 = tt3_bm1.Paste()
    tt3_bm4.setGeometryPose(robomath.roty(robomath.pi) * robomath.rotx(robomath.pi), True)

    final_bm = RDK.MergeItems([tt3_bm1, tt3_bm2, tt3_bm3, tt3_bm4])
    final_bm.setGeometryPose(robomath.transl(0, 0, height), True)
    final_bm.setColor(beam_color)

    tt3_fl1 = RDK.AddFile(paths.cyl)
    tt3_fl1.setPose(robomath.transl(0.0, 0.0, 0.0))
    tt3_fl1.Scale([radius, radius, 10.0])
    tt3_fl1.setColor(flange_color)
    tt3_fl1.setGeometryPose(robomath.transl(-arm_length, -vertical_offset, height) * robomath.roty(robomath.pi / 2), True)

    tt3_fl1.Copy()
    tt3_fl2 = tt3_fl1.Paste()
    tt3_fl2.setGeometryPose(robomath.rotz(robomath.pi), True)

    final_bm.setName(name + ' Beam')
    tt3_fl1.setName(name + ' Flange1')
    tt3_fl2.setName(name + ' Flange2')

    final_bm.setParent(frame)
    tt3_fl1.setParent(frame)
    tt3_fl2.setParent(frame)

    sc_folder = None
    obj_or_robot = final_base
    if create_mechanism:
        base_pose1 = frame.Pose()
        tool_pose1 = frame.Pose()
        base_pose2 = frame.Pose()
        tool_pose2 = frame.Pose()
        base_pose3 = frame.Pose()
        tool_pose3 = frame.Pose()

        tool_pose1 = robomath.Offset(tool_pose1, 0, 0, 0, 0, 0, 0)
        base_pose1 = robomath.Offset(base_pose1, 0.0, 0.0, height, 0, 0, 0)

        tool_pose2 = robomath.Offset(tool_pose2, 0, 0, 10, 0, 0, 0)
        base_pose2 = robomath.Offset(base_pose2, -arm_length, -vertical_offset, height, 0, 90, 180)

        tool_pose3 = robomath.Offset(tool_pose3, 0, 0, 10, 0, 0, 0)
        base_pose3 = robomath.Offset(base_pose3, arm_length, vertical_offset, height, 0, -90, 0)

        obj1 = final_base if height >= 0.8 * radius else None
        new_robot1 = RDK.BuildMechanism(1, [obj1, final_bm], [], [0], [0], [+1],
                                         [tl_llim], [tl_ulim], base_pose1, tool_pose1, final_base.Name())
        new_robot2 = RDK.BuildMechanism(1, [None, tt3_fl1], [], [0], [0], [+1],
                                         [trn_llim], [trn_ulim], base_pose2, tool_pose2, tt3_fl1.Name())
        new_robot3 = RDK.BuildMechanism(1, [None, tt3_fl2], [], [0], [0], [+1],
                                         [trn_llim], [trn_ulim], base_pose3, tool_pose3, tt3_fl2.Name())

        for r, label in [(new_robot1, 'turntable3'), (new_robot2, 'turntable3 flange1'), (new_robot3, 'turntable3 flange2')]:
            if not r.Valid():
                print(f"Failed to create {label}. Check input values.")
            else:
                print(f"Created: {r.Name()}")

        base1 = RDK.Item(new_robot1.Name() + ' Base')
        base1.setPose(frame.Pose())
        base1.setParent(parent_frame)
        new_robot1.setParent(base1)

        base2 = RDK.Item(new_robot2.Name() + ' Base')
        base2.setPose(tt3_fl1.Pose() * robomath.transl(0, 0, -height))
        base2.setParent(new_robot1)

        base3 = RDK.Item(new_robot3.Name() + ' Base')
        base3.setPose(tt3_fl2.Pose() * robomath.transl(0, 0, -height))
        base3.setParent(new_robot1)

        frame.Delete()
        frame = base1
        obj_or_robot = new_robot1

        if create_scripts and paths.sc_1 and paths.sc_2:
            n_str = name.split()[-1] if name.split() else '1'
            RDK.Command("AddFolder", f"Scripts {n_str}")
            sc_folder = RDK.Item(f"Scripts {n_str}")
            sc_1 = RDK.AddFile(paths.sc_1)
            sc_2 = RDK.AddFile(paths.sc_2)
            sc_1.setName(f'Turntable3_{n_str}_side1')
            sc_2.setName(f'Turntable3_{n_str}_side2')
            sc_1.setParent(sc_folder)
            sc_2.setParent(sc_folder)

    if _has_ui(RDK):
        frame.setParam("Reframe")
        frame.setParam("FitAll")

    return frame, obj_or_robot, sc_folder

def SaveItemOnFrame(frame):
    """items that are created using the Create functions return the parnet reference they are attached to"""
    if frame.type == robolink.ITEM_TYPE_FRAME:
        frame_childs = frame.Childs()
        if len(frame_childs) == 0:
            print("Invalid item to save (frame without content)")
            return None
        
        itm_save = frame_childs[0]

    if itm_save.type == robolink.ITEM_TYPE_OBJECT:
        fd, tempfile = _tempfile.mkstemp(suffix='.sld')
        os.close(fd)
        itm_save.Save(tempfile)
        return tempfile

    elif itm_save.type == robolink.ITEM_TYPE_ROBOT:
        fd, tempfile = _tempfile.mkstemp(suffix='.robot')
        os.close(fd)
        itm_save.Save(tempfile)
        return tempfile


    print("Invalid item type to save: " + str(itm_save.type))
    return None

if __name__ == '__main__':
    # Example to create items programmatically
    RDK = new_robolink()

    main_color  = [1/255,   51/255,  86/255,  1.0]
    gray        = [168/255, 176/255, 181/255, 1.0]
    panel_gray  = [168/255, 176/255, 181/255, 100/255]
    floor_color = [240/255, 134/255, 80/255,  1.0]
    red         = [161/255, 0,       0,       1.0]
    lt_gray     = [170/255, 170/255, 170/255, 1.0]

    parent = RDK.Item('Components', robolink.ITEM_TYPE_FRAME)
    if not parent.Valid():
        parent = RDK.AddFrame('Components')
        parent.setPose(robomath.eye(4))

    # Create an object. Every Create* function returns (frame, object_or_robot) --
    # `frame` is what you reposition with one setPose() call, `object_or_robot` is the
    # actual object/mechanism item (no separate RDK.Item(name, ITEM_TYPE_ROBOT) lookup needed).
    frame_cube, cube_obj = CreateCube(RDK, 'Box 1', x=300, y=200, z=100, color=main_color, parent_frame=parent)

    # Example to save an object:
    filestr = SaveItemOnFrame(frame_cube)
    print(filestr)


    frame_rail, rail_robot = CreateRail(RDK, 'Rail 1',
               rail_x=5000, rail_y=1000, rail_z=300,
               rail_x_cr=1000, rail_y_cr=800, rail_z_cr=50,
               rail_zero=2500, rail_llim=-2000, rail_ulim=2000,
               main_color=main_color, carriage_color=red, cover_color=gray, parent_frame=parent,
               create_mechanism=True)
    # rail_robot is the actual mechanism/robot item (create_mechanism=True) -- e.g.
    # rail_robot.setJoints([...]) -- no need to re-fetch it via RDK.Item(name, ITEM_TYPE_ROBOT).

    # Example to save a .robot file:
    filestr = SaveItemOnFrame(frame_rail)
    print(filestr)

    quit()

    # Other examples (do not remove!):

    CreateSphere(RDK, 'Sphere 1', radius=100, color=main_color, parent_frame=parent)
    CreateCone(RDK, 'Cone 1', r_bottom=300, r_top=150, height=400, quality=450, color=main_color, parent_frame=parent)
    CreateTable(RDK, 'Table 1', table_x=1000, table_y=500, table_h1=10, leg_radius=35, leg_height=500,
                main_color=main_color, table_color=gray, parent_frame=parent)
    CreatePedestal(RDK, 'Pedestal 1', r1=500, h1=30, r2=250, h2=500, r3=300, h3=10, color=main_color, parent_frame=parent)
    CreateConveyor(RDK, 'Conveyor 1', cnv_x=1000, cnv_y=300, cnv_r=50, main_color=main_color, parent_frame=parent,
                   frame_width=400, frame_height=750, frame_color=gray,
                   create_mechanism=True)
    CreateFence(RDK, 'Fence 1', panel_size=2000, panels_x=3, panels_y=2, height=1800,
                main_color=main_color, panel_color=panel_gray, floor_color=floor_color, parent_frame=parent,
                sides=(True, True, True, True), include_floor=True, frame_name='Fence 1 Frame')

    CreateTbot(RDK, 'Tbot 1',
               tbot_x=5000, tbot_y=300, tbot_z=400,
               tbot_cr_x=500, tbot_cr_y=140, tbot_cr_z=550,
               tbot_beam2_x=1000, tbot_beam2_y=250, tbot_beam2_z=110,
               tbot_zero=2500, tbot_llim=-2250, tbot_ulim=2250,
               tbot_beam2_zero=0, tbot_beam2_llim=-450, tbot_beam2_ulim=0,
               main_color=main_color, carriage_color=red, beam2_color=red, parent_frame=parent,
               create_mechanism=True)
    CreateHbot(RDK, 'Hbot 1',
               hbot_bm1_x=5000, hbot_bm1_y=300, hbot_bm1_z=400,
               hbot_bm2_x=3000, hbot_bm2_y=350, hbot_bm2_z=250,
               hbot_bm3_x=1000, hbot_bm3_y=250, hbot_bm3_z=250,
               hbot_cr_x=40, hbot_cr_y=250, hbot_cr_z=550,
               hbot_bm1_zero=2500, hbot_bm1_llim=-2000, hbot_bm1_ulim=2000,
               hbot_bm2_zero=1500, hbot_bm2_llim=-1300, hbot_bm2_ulim=1300,
               hbot_bm3_zero=0, hbot_bm3_llim=-650, hbot_bm3_ulim=0,
               main_color=main_color, beam_y_color=red, beam_z_color=red, carriage_color=red, parent_frame=parent,
               with_sides=True, create_mechanism=True)
    CreateTurntable(RDK, 'Turntable 1', radius=250, height=750, base_color=main_color, flange_color=lt_gray, parent_frame=parent,
                    tt_llim=-1000, tt_ulim=1000, create_mechanism=True)
    CreateTurntable2(RDK, 'Turntable2 1', radius=250, height=1000, arm_length=500, vertical_offset=750, cp_dist=2000,
                     base_color=main_color, beam_color=red, flange_color=lt_gray, parent_frame=parent,
                     tl_llim=-180, tl_ulim=180, trn_llim=-1000, trn_ulim=1000, create_mechanism=True)
    CreateTurntable3(RDK, 'Turntable3 1', radius=250, height=1250, arm_length=1500, vertical_offset=1250,
                     base_color=main_color, beam_color=red, flange_color=lt_gray, parent_frame=parent,
                     tl_llim=-180, tl_ulim=180, trn_llim=-720, trn_ulim=720, create_mechanism=True)