"""Boss 1（苍白巨龙）第三轮私有审图：按角色实际投影紧凑取景（kit.review 以包围盒最大边定距，盘绕体型 + 十几米翼展偏小）。

做法同 _b2r2_shots：灯光 / 地面 / 世界沿用 kit.review 的 _setup / _lights（不改 kit），相机与取景在这里：
按每个视角的方位 / 仰角把求值后的网格点投影到相机平面，二分求距离，使角色占画面长边 ~90%，再按投影包围盒居中。
detail 取龙首特写、detail-wing 取右翼特写、detail-body 取盘身鳞甲特写。

两种用法（输出到 art/review/chars/boss-1/boss-1<tag>-<视角>.png，与 kit 审图同名）：
1. 造型阶段（不绑骨）：  blender -b --python tools/chars/_b1r3_shots.py -- geo front,three-quarter,top
2. 动作阶段（读 .blend）： blender -b art/chars/boss-1/boss-1.blend --python tools/chars/_b1r3_shots.py -- blend \\
       front,three-quarter,rear,side,detail,top,game  Move:40,Attack:18,Enrage:24  three-quarter,front
3. GLB 回读（查半透明 / 减面）： blender -b --python tools/chars/_b1r3_shots.py -- glb front,detail-wing
环境变量 CHAR_SAMPLES（默认 32）、CHAR_SIZE（长边像素，默认 960）、B1_OUT（输出目录）、B1_GLB（glb 模式文件名，默认 boss-1.glb）。
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

CID = "boss-1"
ACCENT = (0.61, 0.94, 1.0)

# 视角：(方位角°（0 为正前方，增大转向 +X）, 仰角°, 焦距 mm, 画幅宽高比 w/h, 边距)
VIEWS = {
    "front": (0, 7, 50, 1.25, 0.06),
    "three-quarter": (36, 13, 50, 1.333, 0.06),
    "side": (90, 6, 55, 1.333, 0.06),
    "rear": (175, 10, 50, 1.25, 0.06),
    "top": (0, 80, 50, 1.2, 0.06),
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
    out = Path(os.environ["B1_OUT"]) if os.environ.get("B1_OUT") else ROOT / "art" / "review" / "chars" / CID
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
        fl = bpy.data.objects.get("Review floor")
        if fl is not None:
            fl.hide_render = "belly" in name           # 从地面以下拍腹板时隐藏地面
        scene.render.resolution_x, scene.render.resolution_y = (size, int(size / aspect)) if aspect >= 1 else \
            (int(size * aspect), size)
        look(camera, loc, tgt, lens)
        scene.camera = camera
        path = out / f"{CID}{tag}-{name}.png"
        scene.render.filepath = str(path)
        bpy.ops.render.render(write_still=True)
        print("REVIEW", path)


def detail_shots(root):
    """特写：龙首 / 右翼 / 盘身。目标点取自 Head 骨或 boss_1 的头部标架。"""
    arm = bpy.data.objects.get("BOSS_1_RIG")
    if arm is not None:
        hb = arm.pose.bones["Head"]
        hc = arm.matrix_world @ ((hb.head + hb.tail) / 2)
    else:
        from chars import boss_1 as R
        hc = R.hk(R.head_axis(0.55))
    return {
        "detail": ((0.55, 0.85, 0.22), hc + Vector((0.0, 0.0, 0.55)), 55, 1.333, 11.5),
        "detail-front": ((0.12, 1.0, 0.20), hc + Vector((0.0, 0.0, 0.55)), 50, 1.0, 11.0),
        "detail-side": ((1.0, 0.25, 0.12), hc + Vector((0.0, 0.0, 0.45)), 50, 1.333, 11.0),
        "detail-wing": ((0.35, -0.25, 1.0), Vector((4.0, -1.2, 5.2)), 50, 1.333, 12.0),
        "detail-wing-top": ((0.35, -0.2, 1.0), Vector((3.7, -1.0, 5.0)), 50, 1.333, 15.0),
        "detail-wing-front": ((0.15, 1.0, 0.25), Vector((3.7, -1.0, 5.0)), 50, 1.333, 16.0),
        "detail-shoulder": ((0.9, -0.8, 0.45), Vector((1.2, -0.2, 4.4)), 50, 1.333, 7.0),
        "detail-body": ((0.7, 0.9, 0.5), Vector((0.3, -1.2, 1.6)), 50, 1.333, 11.5),
        "detail-chest": ((0.4, 1.0, 0.25), Vector((0.0, 0.5, 4.0)), 50, 1.333, 9.5),
        "detail-coil": ((0.9, -0.15, 0.35), Vector((1.9, -0.9, 2.0)), 50, 1.333, 6.5),
        "detail-seg": ((0.8, 0.5, 0.25), Vector((1.75, -1.7, 1.9)), 55, 1.333, 3.4),
        "detail-belly": ((0.2, 0.3, -0.9), Vector((0.2, -1.0, 1.0)), 50, 1.333, 7.0),
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
        recipe = importlib.import_module("chars.boss_1")
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
        bpy.ops.import_scene.gltf(filepath=str(ROOT / "visual-lab" / "assets" / "chars" / os.environ.get("B1_GLB", "boss-1.glb")))
        root = bpy.data.objects.new("BOSS_1", None)
        bpy.context.scene.collection.objects.link(root)
        for o in list(bpy.data.objects):
            if o.parent is None and o is not root and o.type in ("EMPTY", "MESH", "ARMATURE"):
                o.parent = root
        tag = "-glb"
    else:
        root = bpy.data.objects["BOSS_1"]
        arm = bpy.data.objects["BOSS_1_RIG"]
        arm.animation_data.action = bpy.data.actions["Idle"]
        bpy.context.scene.frame_set(1)
        tag = ""
    extra = detail_shots(root)
    render(root, names, tag, extra=extra)
    for spec in poses:
        name, f = spec.split(":")
        bpy.data.objects["BOSS_1_RIG"].animation_data.action = bpy.data.actions[name]
        bpy.context.scene.frame_set(int(f))
        render(root, pose_views, f"-{name.lower()}{f}", extra=extra)


if __name__ == "__main__":
    main()
