"""Boss 3 私有审图：按角色实际投影紧凑取景（kit.review 以包围盒最大边定距，对 5.5 m 人形 + 7 m 军旗偏小）。

灯光、地面、世界沿用 kit.review 的 _setup / _lights（不改 kit），相机与取景在这里（思路同 _b2r2_shots.py）：
- 标准视角：按方位 / 仰角把求值后的网格点投影到相机平面，二分求距离使角色占画面 ~90%，再按投影包围盒居中。
- 特写：给“锚点（骨名或世界点）+ 半径”，只取半径内的网格点自动取框，头 / 心核 / 肩 / 腿 / 旗架 / 斗篷都靠它。

两种用法（输出 art/review/chars/boss-3/boss-3<tag>-<视角>.png，与 kit 审图同名，覆盖其粗取景版本）：
1. 造型阶段（不绑骨，旗枪处于静止横握姿态）：
     blender -b --python tools/chars/_b3_shots.py -- geo front,three-quarter,head
2. GLB 模式：B3_GLB=boss-3-game.glb blender -b --python tools/chars/_b3_shots.py -- glb front,detail
3. 动作阶段（读 .blend，姿态下取点）：
     blender -b art/chars/boss-3/boss-3.blend --python tools/chars/_b3_shots.py -- blend \\
         front,three-quarter,rear,side,detail,core,game  Move:5,Attack:14,Enrage:24  three-quarter,front
环境变量：CHAR_SAMPLES（默认 32）、CHAR_SIZE（长边像素，默认 960）、B3_OUT（输出目录）、B3_TAG（文件名附加标记）。
"""

import importlib
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

CID = "boss-3"
ACCENT = (0.80, 0.67, 1.0)

# 标准视角：(方位角°（0 为正前方，增大转向 +X）, 仰角°, 焦距 mm, 画幅宽高比 w/h, 边距)
VIEWS = {
    "front": (0, 6, 55, 0.80, 0.06),
    "three-quarter": (34, 12, 50, 0.90, 0.06),
    "side": (90, 6, 55, 0.90, 0.06),
    "rear": (176, 9, 55, 0.80, 0.06),
    "top": (0, 80, 50, 1.0, 0.07),
    "game": (0, 52, 38, 1.333, 0.10),
}

# 特写：名 -> (相机方向（自目标指向相机）, 锚点, 取点半径 m, 焦距, 宽高比, 边距)
# 锚点为骨名（取骨中点）或世界坐标元组；半径内的网格点参与自动取框。
CLOSEUPS = {
    "detail": ((0.50, 0.82, 0.16), "Head", 1.15, 70, 1.0, 0.05),          # 头部（王冠 + 颅骨）
    "face": ((0.06, 1.0, 0.06), "Head", 0.62, 85, 1.0, 0.06),             # 正面脸
    "head-side": ((1.0, 0.18, 0.10), "Head", 1.15, 70, 1.0, 0.05),
    "core": ((0.18, 1.0, 0.10), (0.0, 0.06, 3.92), 1.25, 60, 1.0, 0.05),   # 肋笼 + 心核
    "torso": ((0.45, 1.0, 0.18), (0.0, 0.0, 3.95), 2.3, 55, 1.0, 0.05),
    "shoulder": ((-0.70, 0.75, 0.30), "UpperArm.L", 1.25, 60, 1.0, 0.05),
    "hand": ((0.55, 1.0, 0.15), "Hand.L", 0.85, 70, 1.0, 0.05),
    "hand-back": ((-0.45, -1.0, 0.25), "Hand.L", 0.85, 70, 1.0, 0.05),
    "legs": ((0.45, 1.0, 0.12), (0.0, 0.0, 1.6), 2.0, 50, 1.0, 0.05),
    "rack": ((0.45, -1.0, 0.32), (0.0, -0.62, 5.4), 2.6, 50, 1.0, 0.05),    # 军旗架（背面）
    "cape": ((0.20, -1.0, 0.10), (0.0, -0.5, 2.2), 2.8, 50, 0.9, 0.05),
    "spear": ((0.50, 0.85, 0.20), "Hand.R", 1.8, 50, 1.0, 0.05),
    "top-head": ((0.0, 0.35, 1.0), "Head", 1.3, 60, 1.0, 0.05),
}


def world_points(root, step=4, only=None):
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
    dist = 10.0
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


def anchor_point(anchor):
    """锚点：骨名（姿态下取骨中点，世界坐标）或世界坐标元组。"""
    if isinstance(anchor, str):
        rig = bpy.data.objects.get("BOSS_3_RIG")
        if rig is not None and anchor in rig.pose.bones:
            pb = rig.pose.bones[anchor]
            return rig.matrix_world @ ((pb.head + pb.tail) / 2)
        from chars import boss_3 as R
        B = R.marshal_body()
        s = B.s
        table = {"Head": Vector((0, 0.02 * s, B.z(1.87))), "UpperArm.R": B.arms["R"]["shoulder"],
                 "UpperArm.L": B.arms["L"]["shoulder"], "Hand.L": B.arms["L"]["wrist"], "Hand.R": B.arms["R"]["wrist"]}
        return table[anchor]
    return Vector(anchor)


def render(root, names, tag="", samples=None, size=None):
    """names 取 VIEWS / CLOSEUPS 的键。"""
    samples = samples or int(os.environ.get("CHAR_SAMPLES", 32))
    size = size or int(os.environ.get("CHAR_SIZE", 960))
    out = Path(os.environ["B3_OUT"]) if os.environ.get("B3_OUT") else ROOT / "art" / "review" / "chars" / CID
    out.mkdir(parents=True, exist_ok=True)
    tag = os.environ.get("B3_TAG", "") + tag
    prepare(root, samples, size)
    scene = bpy.context.scene
    camera = bpy.data.objects["Review camera"]
    pts = world_points(root, 3)
    pts_dense = None
    for name in names:
        if name in VIEWS:
            az, el, lens, aspect, margin = VIEWS[name]
            a, e = math.radians(az), math.radians(el)
            direction = (math.sin(a) * math.cos(e), math.cos(a) * math.cos(e), math.sin(e))
            loc, tgt = fit(pts, direction, lens, aspect, margin)
        elif name in CLOSEUPS:
            direction, anchor, radius, lens, aspect, margin = CLOSEUPS[name]
            ap = anchor_point(anchor)
            if pts_dense is None:
                pts_dense = world_points(root, 1)
            sel = pts_dense[np.linalg.norm(pts_dense - np.array(ap), axis=1) <= radius]
            if len(sel) < 20:
                sel = pts
            loc, tgt = fit(sel, direction, lens, aspect, margin, target=ap)
        else:
            continue
        scene.render.resolution_x, scene.render.resolution_y = (size, int(size / aspect)) if aspect >= 1 else \
            (int(size * aspect), size)
        look(camera, loc, tgt, lens)
        scene.camera = camera
        path = out / f"{CID}{tag}-{name}.png"
        scene.render.filepath = str(path)
        bpy.ops.render.render(write_still=True)
        print("REVIEW", path)


def main():
    args = sys.argv[sys.argv.index("--") + 1:]
    mode = args[0]
    names = (args[1] if len(args) > 1 else "front,three-quarter").split(",")
    poses = [p for p in (args[2].split(",") if len(args) > 2 else []) if p]
    pose_views = (args[3] if len(args) > 3 else "three-quarter").split(",")
    if mode == "geo":
        from kit.core import Ctx
        bpy.ops.wm.read_factory_settings(use_empty=True)
        recipe = importlib.import_module("chars.boss_3")
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
        # 导入游戏版 / 展示版 GLB 静态渲染（查减面伤细节与半透明火焰）：B3_GLB 指定文件名，默认游戏版
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.ops.import_scene.gltf(filepath=str(ROOT / "visual-lab" / "assets" / "chars" / os.environ.get("B3_GLB", "boss-3-game.glb")))
        root = bpy.data.objects.new("BOSS_3", None)
        bpy.context.scene.collection.objects.link(root)
        for o in list(bpy.data.objects):
            if o.parent is None and o is not root and o.type in ("EMPTY", "MESH", "ARMATURE"):
                o.parent = root
        tag = "-glb"
    else:
        root = bpy.data.objects["BOSS_3"]
        rig = bpy.data.objects["BOSS_3_RIG"]
        rig.animation_data.action = bpy.data.actions["Idle"]
        bpy.context.scene.frame_set(1)
        tag = ""
    render(root, names, tag)
    for spec in poses:
        name, f = spec.split(":")
        bpy.data.objects["BOSS_3_RIG"].animation_data.action = bpy.data.actions[name]
        bpy.context.scene.frame_set(int(f))
        render(root, pose_views, f"-{name.lower()}{f}")


if __name__ == "__main__":
    main()
