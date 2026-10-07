"""Boss 7（灰烬炽天使）第四轮私有审图（在第三轮 _b7r3_shots 上加了圣心 / 颈 / 肘 / 拳套 / 剑柄特写，并让特写跟随姿态）：按角色实际投影紧凑取景（kit.review 按包围盒最大边定距，14 m 翼展的 Boss 只占画面一小块）。

做法同 _b1r3_shots：灯光 / 地面 / 世界沿用 kit.review 的 _setup / _lights（不改 kit），相机与取景在这里：
按每个视角的方位 / 仰角把求值后的网格点投影到相机平面，二分求距离，使角色占画面长边 ~90%，再按投影包围盒居中。
特写取头部 + 光环（detail）、胸甲（detail-chest）、翅膀（detail-wing）、终末之剑（detail-sword）、裙甲（detail-skirt）、肩甲（detail-shoulder）。

三种用法（输出到 art/review/chars/boss-7/boss-7<tag>-<视角>.png，可用环境变量 B7_OUT 改输出目录）：
1. 造型阶段（不绑骨）：  blender -b --python tools/chars/_b7r4_shots.py -- geo front,three-quarter,top
2. 动作阶段（读 .blend）： blender -b art/chars/boss-7/boss-7.blend --python tools/chars/_b7r4_shots.py -- blend \\
       front,three-quarter,rear,side,detail,top,game  Move:5,Attack:15,Enrage:24  three-quarter,front
3. GLB 回读（查半透明 / 减面）： blender -b --python tools/chars/_b7r4_shots.py -- glb front,detail-wing
环境变量 CHAR_SAMPLES（默认 32）、CHAR_SIZE（长边像素，默认 960）、B7_OUT、B7_GLB（glb 模式文件名，默认 boss-7-game.glb）、
B7_TAG（输出文件名附加标签，如 -wip）。
"""

import math
import os
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))
from kit import review  # noqa: E402
from kit.core import ROOT  # noqa: E402

CID = "boss-7"
ACCENT = (1.0, 0.60, 0.49)

# 视角：(方位角°（0 为正前方，增大转向 +X）, 仰角°, 焦距 mm, 画幅宽高比 w/h, 边距)
VIEWS = {
    "front": (0, 6, 50, 1.25, 0.05),
    "three-quarter": (34, 12, 50, 1.25, 0.05),
    "side": (90, 6, 55, 1.0, 0.07),
    "rear": (176, 9, 50, 1.25, 0.05),
    "top": (0, 80, 50, 1.25, 0.05),
    "game": (0, 52, 38, 1.333, 0.10),
}


def world_points(root, step=4):
    """求值后（含骨骼姿态）的可见网格世界坐标，按 step 抽样。"""
    dg = bpy.context.evaluated_depsgraph_get()
    out = []
    for o in [root, *root.children_recursive]:
        if o.type != "MESH" or o.hide_render or o.hide_get():
            continue
        ev = o.evaluated_get(dg)
        me = ev.to_mesh()
        n = len(me.vertices)
        if n:
            co = np.empty(n * 3, np.float32)
            me.vertices.foreach_get("co", co)
            co = co.reshape(n, 3)[::step]
            m = np.array(ev.matrix_world, np.float32)
            out.append(co @ m[:3, :3].T + m[:3, 3])
        ev.to_mesh_clear()
    return np.concatenate(out)


def tan_half(lens, aspect):
    """相机视场的水平 / 垂直 tan(半角)。sensor_fit=AUTO：36 mm 传感器对应画幅长边。"""
    big = 18.0 / lens
    return (big, big / aspect) if aspect >= 1 else (big * aspect, big)


def fit(points, direction, lens, aspect, margin, target=None):
    """二分求相机距离：所有点透视投影后落在画幅内（留 margin）。返回 (相机位置, 目标点)。"""
    d = Vector(direction).normalized()
    fwd = -d
    right = fwd.cross(Vector((0, 0, 1))).normalized()
    up = right.cross(fwd).normalized()
    P = points
    ctr = np.array(target if target is not None else (P.min(axis=0) + P.max(axis=0)) / 2, np.float64)
    tx, ty = tan_half(lens, aspect)
    fwd_a, right_a, up_a = np.array(fwd), np.array(right), np.array(up)
    for _ in range(3):                               # 先居中再收缩：外层 3 轮收敛
        lo, hi = 0.5, 400.0
        for _ in range(40):
            dist = (lo + hi) / 2
            cam = ctr - fwd_a * dist
            rel = P - cam
            z = rel @ fwd_a
            sx = np.abs(rel @ right_a) / np.maximum(z, 1e-3)
            sy = np.abs(rel @ up_a) / np.maximum(z, 1e-3)
            ok = (sx.max() <= tx * (1 - margin)) and (sy.max() <= ty * (1 - margin)) and z.min() > 0.2
            if ok:
                hi = dist
            else:
                lo = dist
        dist = hi
        cam = ctr - fwd_a * dist
        rel = P - cam
        z = np.maximum(rel @ fwd_a, 1e-3)
        px, py = (rel @ right_a) / z, (rel @ up_a) / z
        cx, cy = (px.max() + px.min()) / 2, (py.max() + py.min()) / 2
        zc = float(np.median(z))
        ctr = ctr + right_a * (cx * zc) + up_a * (cy * zc)
    return Vector(ctr - fwd_a * dist), Vector(ctr)


def look(camera, loc, target, lens):
    camera.location = loc
    camera.rotation_euler = (Vector(target) - loc).to_track_quat("-Z", "Y").to_euler()
    camera.data.lens = lens


def prepare(root, samples, size):
    """环境、灯光（按角色整体取一次）。"""
    P = world_points(root, 6)
    lo, hi = P.min(axis=0), P.max(axis=0)
    center = Vector(((lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2, lo[2] + (hi[2] - lo[2]) * 0.6))
    height = float(max(hi - lo))
    print(f"BBOX posed (visible meshes): min {tuple(round(float(c), 2) for c in lo)} max {tuple(round(float(c), 2) for c in hi)} "
          f"size {tuple(round(float(c), 2) for c in (hi - lo))}")
    review._setup(ACCENT, samples, size)
    review._lights(center, height * 0.82, ACCENT)
    return lo, hi


def render(root, names, tag="", samples=None, size=None, extra=None):
    """names 取 VIEWS 键或 extra 里的特写（名 -> (相机方向, 目标点, 焦距, 宽高比, 距离)）。"""
    samples = samples or int(os.environ.get("CHAR_SAMPLES", 32))
    size = size or int(os.environ.get("CHAR_SIZE", 960))
    out = Path(os.environ["B7_OUT"]) if os.environ.get("B7_OUT") else ROOT / "art" / "review" / "chars" / CID
    out.mkdir(parents=True, exist_ok=True)
    lo, hi = prepare(root, samples, size)
    scene = bpy.context.scene
    camera = bpy.data.objects["Review camera"]
    pts = world_points(root, 3)
    for name in names:
        if name in VIEWS:
            az, el, lens, aspect, margin = VIEWS[name]
            a, e = math.radians(az), math.radians(el)
            direction = (math.sin(a) * math.cos(e), math.cos(a) * math.cos(e), math.sin(e))
            loc, tgt = fit(pts, direction, lens, aspect, margin)
        elif extra and name in extra:
            direction, tgt, lens, aspect, dist = extra[name]
            d = Vector(direction).normalized()
            tgt = Vector(tgt)
            loc = tgt + d * dist
        else:
            continue
        scene.render.resolution_x, scene.render.resolution_y = (size, int(size / aspect)) if aspect >= 1 else \
            (int(size * aspect), size)
        look(camera, loc, tgt, lens)
        scene.camera = camera
        path = out / f"{CID}{os.environ.get('B7_TAG', '')}{tag}-{name}.png"
        scene.render.filepath = str(path)
        bpy.ops.render.render(write_still=True)
        print("REVIEW", path)


def pose_point(name, p):
    """把静止姿态下的点 p（世界坐标，挂在骨 name 上）按当前姿态变换；geo / glb 模式没有骨架时原样返回。"""
    arm = bpy.data.objects.get("BOSS_7_RIG")
    if arm is None or name not in arm.pose.bones:
        return Vector(p)
    pb = arm.pose.bones[name]
    return arm.matrix_world @ (pb.matrix @ pb.bone.matrix_local.inverted() @ Vector(p))


def detail_shots():
    """特写：目标点取自配方常量（静止姿态）并按当前姿态变换，方向 / 距离手调。"""
    from chars import boss_7 as R
    B = R.B0
    s = B.s
    head = pose_point("Head", Vector((0.0, 0.1, B.head_c.z)))
    chest = pose_point("Chest", Vector((0.0, 0.3, B.z(1.42))))
    core = pose_point("Chest", B.on_torso(0, B.z(1.515), 0.04 * s))
    neck = pose_point("Neck", Vector((0.0, 0.05, B.z(1.70))))
    sh = B.arms["R"]["shoulder"]
    elbow = {lb: pose_point(f"Forearm.{lb}", B.arms[lb]["elbow"]) for lb in ("L", "R")}
    wing = Vector(R.WINGS[0]["root"]) + Vector((3.2, -0.6, 0.0))
    grip = pose_point("Sword", R.SWORD_GRIP)
    hand = {"R": pose_point("Sword", R.SWORD_GRIP - R.U0 * R.HAND_GAP), "L": pose_point("Sword", R.SWORD_GRIP + R.U0 * R.HAND_GAP)}
    return {
        "detail": ((0.30, 1.0, 0.14), Vector((0.0, -0.2, R.HC.z - 0.3)), 50, 1.333, 9.0),
        "detail-head": ((0.30, 1.0, 0.10), head, 50, 1.0, 5.0),
        "detail-chest": ((0.35, 1.0, 0.18), chest, 50, 1.333, 9.5),
        "detail-core": ((0.25, 1.0, 0.12), core, 50, 1.333, 4.6),
        "detail-core-side": ((0.95, 0.6, 0.10), core, 50, 1.333, 5.0),
        "detail-neck": ((0.75, 0.9, 0.12), neck, 50, 1.333, 4.2),
        "detail-neck-side": ((1.0, 0.1, 0.10), neck, 50, 1.333, 4.2),
        "detail-elbow": ((0.55, 1.0, 0.20), elbow["R"], 50, 1.333, 5.0),
        "detail-elbow-L": ((-0.55, 1.0, 0.20), elbow["L"], 50, 1.333, 5.0),
        "detail-elbow-side": ((1.0, 0.25, 0.20), elbow["R"], 50, 1.333, 5.0),
        "detail-elbow-back": ((0.9, -0.8, 0.15), elbow["R"], 50, 1.333, 5.0),
        "detail-elbow-front": ((0.35, 1.0, -0.10), elbow["R"], 50, 1.333, 4.4),
        "detail-shoulder": ((0.95, 0.65, 0.35), sh + Vector((0.2, 0.0, 0.1)), 50, 1.333, 7.5),
        "detail-wing": ((0.30, -0.55, 0.65), wing, 50, 1.333, 14.0),
        "detail-wing-front": ((0.10, 1.0, 0.20), wing, 50, 1.333, 16.0),
        "detail-sword": ((0.45, 1.0, 0.22), grip, 50, 1.333, 7.0),
        "detail-hand": ((0.55, 1.0, 0.25), grip, 50, 1.333, 3.6),
        "detail-hand-R": ((0.60, 1.0, 0.25), hand["R"], 50, 1.333, 2.2),
        "detail-hand-L": ((-0.60, 1.0, 0.25), hand["L"], 50, 1.333, 2.2),
        "detail-hand-back": ((0.05, 1.0, 0.55), hand["R"], 50, 1.333, 2.6),
        "detail-hand-top": ((0.05, 0.15, 1.0), hand["R"], 50, 1.333, 2.6),
        "detail-hand-side": ((1.0, 0.05, 0.12), hand["R"], 50, 1.333, 2.6),
        "detail-hand-in": ((-1.0, 0.45, 0.12), hand["R"], 50, 1.333, 2.8),
        "detail-hands": ((0.30, 1.0, 0.10), grip, 50, 1.333, 4.2),
        "detail-sword-tip": ((0.55, 1.0, 0.10), grip + R.U0 * 3.2, 50, 1.333, 9.0),
        "detail-skirt": ((0.45, 1.0, 0.16), Vector((0.0, 0.0, B.pelvis_z - 1.5)), 50, 1.0, 10.0),
        "detail-skirt-rear": ((-0.45, -1.0, 0.16), Vector((0.0, -0.4, B.pelvis_z - 1.5)), 50, 1.0, 10.0),
        "detail-back": ((0.0, -1.0, 0.20), Vector((0.0, -0.8, B.z(1.45))), 50, 1.333, 10.5),
    }


def main():
    args = sys.argv[sys.argv.index("--") + 1:]
    mode = args[0]
    names = (args[1] if len(args) > 1 else "front,three-quarter,side,top").split(",")
    poses = args[2].split(",") if len(args) > 2 and args[2] else []
    pose_views = (args[3] if len(args) > 3 else "three-quarter").split(",")
    if mode == "geo":
        from kit.core import Ctx
        import importlib
        bpy.ops.wm.read_factory_settings(use_empty=True)
        recipe = importlib.import_module(os.environ.get("B7_RECIPE", "chars.boss_7"))
        ctx = Ctx(CID, recipe.TITLE)
        recipe.build(ctx)
        root = bpy.data.objects.new(ctx.ID, None)
        bpy.context.scene.collection.objects.link(root)
        for obj, _ in ctx.parts:
            obj.parent = root
        for obj, *_ in ctx.attached:
            obj.parent = root
        for obj in ctx.hidden:
            obj.parent = root
        tag = "-geo"
    elif mode == "glb":
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.ops.import_scene.gltf(filepath=str(ROOT / "visual-lab" / "assets" / "chars" /
                                               os.environ.get("B7_GLB", "boss-7-game.glb")))
        root = bpy.data.objects.new("BOSS_7", None)
        bpy.context.scene.collection.objects.link(root)
        for o in list(bpy.data.objects):
            if o.parent is None and o is not root and o.type in ("EMPTY", "MESH", "ARMATURE"):
                o.parent = root
        tag = "-glb"
    else:
        root = bpy.data.objects["BOSS_7"]
        arm = bpy.data.objects["BOSS_7_RIG"]
        arm.animation_data.action = bpy.data.actions["Idle"]
        bpy.context.scene.frame_set(1)
        tag = ""
    extra = detail_shots()
    render(root, names, tag, extra=extra)
    for spec in poses:
        name, f = spec.split(":")
        bpy.data.objects["BOSS_7_RIG"].animation_data.action = bpy.data.actions[name]
        bpy.context.scene.frame_set(int(f))
        bpy.context.view_layer.update()
        render(root, pose_views, f"-{name.lower()}{f}", extra=detail_shots())    # 特写目标随姿态重算


if __name__ == "__main__":
    main()
