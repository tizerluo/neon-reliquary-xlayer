"""Boss 6 毒雾特效轮私有审图：按角色实际投影紧凑取景 + 毒雾特写（思路同 _b4fx_shots / _b0fx_shots）。

沿用 kit.review 的 _setup / _lights（不改 kit）；相机与取景在这里。取景只看“躯体网格 + Spray 骨推算的毒雾范围”，
不看毒雾网格本身，所以新旧两版（实心薄片 / 半透明毒雾）在同一动作帧下机位完全一致，方便做新旧对比。
输出到 art/review/chars/boss-6/（B6_OUT 可改目录；文件名 boss-6<tag>-<视角>.png）。三种用法：
1. 造型阶段（不绑骨）：  blender -b --python tools/chars/_b6fx_shots.py -- geo front,detail-fx
2. 动作阶段（读 .blend）： blender -b art/chars/boss-6/boss-6.blend --python tools/chars/_b6fx_shots.py -- blend \\
       front,three-quarter,game  Attack:14,Attack:21  detail-fx,three-quarter,game
3. 导入 GLB 静态 / 动作帧渲染（查游戏版 BLEND 材质与缩放）：B6_GLB 指定文件名（默认 boss-6-game.glb）
       blender -b --python tools/chars/_b6fx_shots.py -- glb detail-fx  Attack:14  detail-fx
环境变量 CHAR_SAMPLES（默认 32）、CHAR_SIZE（长边像素，默认 960）、B6_PLUME（毒雾长度，默认 4.2 m，只用于取景）。
视角：front / three-quarter / side / rear / top / game 为整体取景；
特写：detail-fx（三束毒雾，左前上方 3/4 机位）、detail-top（三束毒雾，俯视）、detail-mist（中首一束毒雾侧视：
雾团层次 + 毒滴）、detail-mouth（中首口部正前方：喷口与雾根）、detail-head（中首头部 3/4：口中毒膜与雾根）。
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

CID = "boss-6"
ACCENT = (0.55, 0.86, 0.70)
PLUME = float(os.environ.get("B6_PLUME", 4.2))      # 满伸时毒雾沿喷口方向的长度（米）；Spray 骨缩放 50× 对应这个长度
FULL_SCALE = 50.0                                   # Spray 骨满伸缩放（1 / SPRAY_K）

# 视角：(方位角°（0 为正前方，增大转向 +X）, 仰角°, 焦距 mm, 画幅宽高比 w/h, 边距)
VIEWS = {
    "front": (0, 7, 55, 0.80, 0.07),
    "three-quarter": (36, 13, 50, 1.333, 0.07),
    "side": (90, 6, 55, 1.333, 0.07),
    "rear": (175, 10, 55, 0.80, 0.07),
    "top": (0, 80, 50, 1.0, 0.07),
    "game": (0, 52, 38, 1.333, 0.10),
}


def is_fx(o):
    n = o.name.lower()
    return "spray" in n or "mist" in n


def mesh_points(objs, step=2):
    """求值后（含骨骼姿态）的网格世界坐标，按 step 抽样；毒雾网格不参与（取景改用 Spray 骨）。"""
    dg = bpy.context.evaluated_depsgraph_get()
    out = []
    for o in objs:
        if o.type != "MESH" or o.hide_render or o.hide_get() or is_fx(o):
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
    return np.concatenate(out) if out else np.zeros((1, 3), np.float32)


def spray_axes(rig_name, which=None):
    """当前姿态下喷口开火中的毒雾：[(标签, 喷口点, 单位方向, 伸出长度)]。Spray 骨 Y 轴沿喷口方向，缩放 > 3 视为开火。"""
    arm = bpy.data.objects.get(rig_name)
    out = []
    if arm is None or arm.pose is None:
        return out
    for S in "LCR":
        if which is not None and which != S:
            continue
        pb = arm.pose.bones.get(f"Spray{S}")
        if pb is None or pb.scale.y < 3.0:
            continue
        m = arm.matrix_world @ pb.matrix
        head = m.translation.copy()
        ydir = (m.to_3x3() @ Vector((0, 1, 0))).normalized()
        out.append((S, head, ydir, PLUME * pb.scale.y / FULL_SCALE))
    return out


def plume_points(rig_name, which=None, spread=0.95):
    """开火毒雾的取景点：喷口、沿喷口 25 / 60 / 100% 长度处向四周各补一圈（半径随长度展开到 spread 米）。"""
    pts = []
    for S, head, d, length in spray_axes(rig_name, which):
        side = d.cross(Vector((0, 0, 1))).normalized()
        up = side.cross(d).normalized()
        for t in (0.0, 0.25, 0.6, 1.0):
            c = head + d * (length * t)
            r = 0.1 + spread * t * min(1.0, length / PLUME)
            for a in (0, 1, 2, 3):
                v = side * math.cos(a * math.pi / 2) + up * math.sin(a * math.pi / 2)
                p = c + v * r
                pts.append([p.x, p.y, p.z])
    return np.array(pts, np.float64) if pts else None


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


def direction_of(az, el):
    a, e = math.radians(az), math.radians(el)
    return (math.sin(a) * math.cos(e), math.cos(a) * math.cos(e), math.sin(e))


def prepare(root, rig_name, samples, size):
    """环境、灯光（按角色整体取一次：只看躯体 + 满伸毒雾，机位与动作帧无关）。"""
    P = mesh_points([root, *root.children_recursive], 6)
    lo, hi = P.min(axis=0), P.max(axis=0)
    center = Vector(((lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2, lo[2] + (hi[2] - lo[2]) * 0.6))
    height = float(max(hi - lo))
    print(f"BBOX posed (body, no fx): min {tuple(round(float(c), 2) for c in lo)} max {tuple(round(float(c), 2) for c in hi)} "
          f"size {tuple(round(float(c), 2) for c in (hi - lo))}")
    review._setup(ACCENT, samples, size)
    review._lights(center, height * 0.82, ACCENT)
    # 降噪只用颜色（RGB）：默认的 RGB+反照率+法线 会把半透明薄片的“暗基色反照率”泄进降噪，在薄片边缘留下黑线
    dn = os.environ.get("B6_DN", "rgb")
    scene = bpy.context.scene
    # 透明弹射上限默认 8：毒雾由多层壳 + 薄片 + 雾团叠成，视线穿过的层数超限会留下黑洞，调到 64
    scene.cycles.transparent_max_bounces = 64
    if dn == "none":
        scene.cycles.use_denoising = False
    elif dn == "rgb":
        scene.cycles.denoising_input_passes = "RGB"
    return lo, hi


def detail_spec(name, root, rig_name):
    """特写取景：返回 (相机位置, 目标点, 焦距, 宽高比)，取不到数据（没有开火的毒雾）返回 None。"""
    if name in ("detail-fx", "detail-top"):
        P = plume_points(rig_name)
        if P is None:
            return None
        az, el = (28, 20) if name == "detail-fx" else (0, 80)
        loc, tgt = fit(P, direction_of(az, el), 40, 1.333, 0.06)
        return loc, tgt, 40, 1.333
    if name == "detail-mist":
        P = plume_points(rig_name, "C")
        if P is None:
            return None
        ax = spray_axes(rig_name, "C")[0]
        side = ax[2].cross(Vector((0, 0, 1))).normalized()
        d = (side * 3.0 + Vector((0, 0, 0.45))).normalized()     # 垂直于雾轴的侧视，略抬高
        loc, tgt = fit(P, d, 50, 1.333, 0.07)
        return loc, tgt, 50, 1.333
    if name == "detail-mouth":
        ax = spray_axes(rig_name, "C")
        if not ax:
            return None
        _, head, d, length = ax[0]
        side = d.cross(Vector((0, 0, 1))).normalized()
        return head + d * 1.7 + side * 0.9 + Vector((0, 0, 0.5)), head + d * 0.35, 50, 1.333
    if name == "detail-head":
        arm = bpy.data.objects.get(rig_name)
        pb = arm.pose.bones.get("HeadC") if arm is not None else None
        if pb is None:
            return None
        m = arm.matrix_world @ pb.matrix
        head = m.translation.copy()
        d = (m.to_3x3() @ Vector((0, 1, 0))).normalized()
        side = d.cross(Vector((0, 0, 1))).normalized()
        return head + d * 2.3 + side * 1.5 + Vector((0, 0, 0.9)), head + d * 0.55, 50, 1.333
    return None


def render(root, names, tag="", rig_name="BOSS_6_RIG", samples=None, size=None):
    samples = samples or int(os.environ.get("CHAR_SAMPLES", 32))
    size = size or int(os.environ.get("CHAR_SIZE", 960))
    out = Path(os.environ["B6_OUT"]) if os.environ.get("B6_OUT") else ROOT / "art" / "review" / "chars" / CID
    out.mkdir(parents=True, exist_ok=True)
    prepare(root, rig_name, samples, size)
    scene = bpy.context.scene
    camera = bpy.data.objects["Review camera"]
    pts = mesh_points([root, *root.children_recursive], 3)
    plume = plume_points(rig_name)
    if plume is not None:                             # 整体取景把开火中的毒雾也框进去
        pts = np.concatenate([pts, plume])
    for name in names:
        if name in VIEWS:
            az, el, lens, aspect, margin = VIEWS[name]
            loc, tgt = fit(pts, direction_of(az, el), lens, aspect, margin)
        else:
            spec = detail_spec(name, root, rig_name)
            if spec is None:
                print("SKIP", name)
                continue
            loc, tgt, lens, aspect = spec
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
    poses = args[2].split(",") if len(args) > 2 and args[2] else []
    pose_views = (args[3] if len(args) > 3 else "three-quarter").split(",")
    rig_name = "BOSS_6_RIG"
    if mode == "geo":
        from kit.core import Ctx
        import importlib
        bpy.ops.wm.read_factory_settings(use_empty=True)
        recipe = importlib.import_module("chars.boss_6")
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
        # 导入游戏版 / 展示版 GLB（B6_GLB），可切到导入的动作帧：查 BLEND 材质、减面伤细节与缩放通道
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.ops.import_scene.gltf(filepath=str(ROOT / "visual-lab" / "assets" / "chars" / os.environ.get("B6_GLB", "boss-6-game.glb")))
        root = bpy.data.objects.new("BOSS_6", None)
        bpy.context.scene.collection.objects.link(root)
        for o in list(bpy.data.objects):
            if o.parent is None and o is not root and o.type in ("EMPTY", "MESH", "ARMATURE"):
                o.parent = root
        rig_name = next((o.name for o in bpy.data.objects if o.type == "ARMATURE"), rig_name)
        tag = "-glb"
    else:
        root = bpy.data.objects["BOSS_6"]
        arm = bpy.data.objects[rig_name]
        arm.animation_data.action = bpy.data.actions["Idle"]
        bpy.context.scene.frame_set(1)
        tag = os.environ.get("B6_TAG", "")
    render(root, names, tag, rig_name)
    for spec in poses:
        name, f = spec.split(":")
        bpy.data.objects[rig_name].animation_data.action = bpy.data.actions[name]
        bpy.context.scene.frame_set(int(f))
        render(root, pose_views, f"{tag}-{name.lower()}{f}", rig_name)


if __name__ == "__main__":
    main()
