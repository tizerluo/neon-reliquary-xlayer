"""Boss 0 特效轮私有审图：按角色实际投影紧凑取景 + 特效特写（王冠火舌 / 塔顶喷口 / 背面）。

沿用 kit.review 的 _setup / _lights（不改 kit）；相机与取景在这里（取景思路同 _b2r2_shots）。
三种用法（输出到 art/review/chars/boss-0/，B0_OUT 可改目录；文件名 boss-0<tag>-<视角>.png）：
1. 造型阶段（不绑骨）：  blender -b --python tools/chars/_b0fx_shots.py -- geo detail-fx,detail-vent
2. 动作阶段（读 .blend）： blender -b art/chars/boss-0/boss-0.blend --python tools/chars/_b0fx_shots.py -- blend \\
       front,three-quarter,game,detail-fx  Enrage:28,Attack:18  detail-fx,three-quarter
3. 导入 GLB 静态 / 动作帧渲染（查游戏版 BLEND 材质与缩放）：B0_GLB 指定文件名（默认 boss-0-game.glb）
       blender -b --python tools/chars/_b0fx_shots.py -- glb detail-fx  Enrage:28  detail-fx
环境变量 CHAR_SAMPLES（默认 32）、CHAR_SIZE（长边像素，默认 960）。
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

CID = "boss-0"
ACCENT = (1.0, 0.52, 0.42)

# 视角：(方位角°（0 为正前方，增大转向 +X）, 仰角°, 焦距 mm, 画幅宽高比 w/h, 边距)
VIEWS = {
    "front": (0, 7, 55, 0.80, 0.07),
    "three-quarter": (36, 13, 50, 1.333, 0.07),
    "side": (90, 6, 55, 1.333, 0.07),
    "rear": (175, 10, 55, 0.80, 0.07),
    "top": (0, 80, 50, 1.0, 0.07),
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
    fx, fy = np.array(fwd), np.array(right),
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
        # 投影包围盒中心偏移 → 把目标点平移到投影中心
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
    out = Path(os.environ["B0_OUT"]) if os.environ.get("B0_OUT") else ROOT / "art" / "review" / "chars" / CID
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
        path = out / f"{CID}{tag}-{name}.png"
        scene.render.filepath = str(path)
        bpy.ops.render.render(write_still=True)
        print("REVIEW", path)


def detail_shots(root):
    """特效特写：目标点按配方常量给定，方向 / 距离手调。
    detail-fx 取王冠 + 炉墙顶（火舌全貌），detail-vent 取右塔喷口，detail-crown 取王冠火舌，detail-rear 取背面。"""
    return {
        "detail-fx": ((0.50, 0.86, 0.22), Vector((0.0, -0.35, 6.05)), 50, 1.333, 9.5),
        "detail-vent": ((0.80, 0.55, 0.30), Vector((1.40, -1.10, 6.10)), 55, 1.333, 4.2),
        "detail-crown": ((0.30, 1.0, 0.22), Vector((0.0, 0.42, 5.40)), 55, 1.333, 4.4),
        "detail-rear": ((0.35, -1.0, 0.30), Vector((0.0, -1.0, 6.10)), 50, 1.333, 9.0),
        "detail-top": ((0.0, 0.25, 1.0), Vector((0.0, -0.3, 6.0)), 50, 1.333, 10.0),
    }


def main():
    args = sys.argv[sys.argv.index("--") + 1:]
    mode = args[0]
    names = (args[1] if len(args) > 1 else "front,three-quarter").split(",")
    poses = args[2].split(",") if len(args) > 2 and args[2] else []
    pose_views = (args[3] if len(args) > 3 else "three-quarter").split(",")
    rig_name = "BOSS_0_RIG"
    if mode == "geo":
        from kit.core import Ctx
        import importlib
        bpy.ops.wm.read_factory_settings(use_empty=True)
        recipe = importlib.import_module("chars.boss_0")
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
        # 导入游戏版 / 展示版 GLB（B0_GLB），可切到导入的动作帧：查 BLEND 材质、减面伤细节与缩放通道
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.ops.import_scene.gltf(filepath=str(ROOT / "visual-lab" / "assets" / "chars" / os.environ.get("B0_GLB", "boss-0-game.glb")))
        root = bpy.data.objects.new("BOSS_0", None)
        bpy.context.scene.collection.objects.link(root)
        for o in list(bpy.data.objects):
            if o.parent is None and o is not root and o.type in ("EMPTY", "MESH", "ARMATURE"):
                o.parent = root
        rig_name = next((o.name for o in bpy.data.objects if o.type == "ARMATURE"), rig_name)
        tag = "-glb"
    else:
        root = bpy.data.objects["BOSS_0"]
        arm = bpy.data.objects[rig_name]
        arm.animation_data.action = bpy.data.actions["Idle"]
        bpy.context.scene.frame_set(1)
        tag = ""
    extra = detail_shots(root)
    render(root, names, tag, extra=extra)
    for spec in poses:
        name, f = spec.split(":")
        bpy.data.objects[rig_name].animation_data.action = bpy.data.actions[name]
        bpy.context.scene.frame_set(int(f))
        render(root, pose_views, f"{tag}-{name.lower()}{f}", extra=extra)


if __name__ == "__main__":
    main()
