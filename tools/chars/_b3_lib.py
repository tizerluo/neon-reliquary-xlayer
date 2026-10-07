"""Boss 3（空壳元帅）私有辅助：程序化贴图、幽火 / 链环网格、燕尾军旗布料、带缩放通道的动作写入与检查。

部分函数改写自 chars/_bossA_common.py（只读参考，复制到本模块以免耦合）。
"""

import math
import random

import bmesh
import bpy
import numpy as np
from mathutils import Vector

from kit.core import (GLYPHS, TAU, Canvas, apply_all, bm_object, box_blur, catmull, clamp, garment, height_normal,
                      interp, lerp, orient, smoothstep, solidify, surface, voronoi)
from kit.garment import Panel, Wrap


# ===== 缓动与参数轨道 =====
def ease_io(t):
    t = clamp(t)
    return t * t * (3 - 2 * t)


def ease_in(t):
    t = clamp(t)
    return t ** 3


def ease_out(t):
    t = clamp(t)
    return 1 - (1 - t) ** 3


def ease_back(t):
    """先略回拉再冲出（蓄力感）。"""
    t = clamp(t)
    return t * t * (2.7 * t - 1.7)


EASE = {"io": ease_io, "in": ease_in, "out": ease_out, "back": ease_back, "lin": clamp}


def lerp_params(a, b, t):
    out = {}
    for k in set(a) | set(b):
        va, vb = a.get(k, b.get(k)), b.get(k, a.get(k))
        if isinstance(va, (int, float)):
            out[k] = lerp(va, vb, t)
        else:
            out[k] = Vector(va).lerp(Vector(vb), t)
    return out


def track(keys, frame):
    """参数轨道：keys 为 [(帧, 参数字典, 缓动名), ...]，缓动作用于“到达该键”的那一段。"""
    if frame <= keys[0][0]:
        return dict(keys[0][1])
    for (f0, p0, _), (f1, p1, e) in zip(keys, keys[1:]):
        if frame <= f1:
            t = (frame - f0) / max(1e-6, f1 - f0)
            return lerp_params(p0, p1, EASE[e](t))
    return dict(keys[-1][1])


def with_defaults(base, keys):
    """把每个关键参数字典补齐为 base 的完整副本，只需写变化量。"""
    return [(f, {**base, **p}, e) for f, p, e in keys]


# ===== 动作写入（带缩放通道：幽火 / 心核在 Enrage 中膨胀） =====
def put(rig, pose, frame):
    rig.put_pose(pose, frame)
    sc = pose.get("_scale", {})
    for name in getattr(rig, "scaled", ()):
        pb = rig.obj.pose.bones[name]
        v = sc.get(name, 1.0)
        pb.scale = (v, v, v)
        pb.keyframe_insert("scale", frame=frame, group=name)


def loop(rig, name, frames, fn, step=1):
    """循环动作：fn(t) 的 t 从 0 走到 2π（首尾同相位）。"""
    rig.new_action(name)
    for f in range(0, frames + 1, step):
        put(rig, fn(TAU * f / frames), f + 1)


def sampled(rig, name, frames, fn, step=1):
    """一次性动作：fn(帧号) 逐帧重算，帧号 1..frames+1。"""
    rig.new_action(name)
    for f in range(1, frames + 2, step):
        put(rig, fn(f), f)


# ===== 步态（复制自 kit.motion.gait，加地面约束：靴子又长又大，kit 默认的脚尖下压角会把趾尖扎进地里） =====
def gait_b3(rig, B, t, stride=0.40, lift=0.10, stance=0.62, bob=0.014, lean=0.06, twist=0.07, arm=0.22, elbow=0.35,
            arm_in=0.10, width=0.012, heel=0.03, knee_out=0.14, head_stab=0.7, sink=0.045, sway=0.012,
            toe_off=0.42, strike=0.10, floor=0.060):
    from mathutils import Matrix
    from kit.motion import Legs, foot_track
    from kit.rig import R, X, Y, Z
    s = B.s
    pose = {}
    legs = Legs(rig, B)
    pose["_hover"] = -sink * s + bob * s * math.cos(2 * t)
    yaw = twist * math.sin(t)
    pose["Pelvis"] = R((Z, yaw), (Y, sway * math.sin(t) * 3), (X, -lean))
    ct = -1.6 * twist
    pose["Spine"] = R((Z, ct * 0.5 * math.sin(t)), (X, -lean * 0.15))
    pose["Chest"] = R((Z, ct * 0.5 * math.sin(t)), (X, 0.02 * math.cos(2 * t)))
    pose["Neck"] = R((Z, -yaw * 0.5), (X, lean * head_stab * 0.5))
    pose["Head"] = R((X, lean * head_stab * 0.5))
    for label, ph in (("L", 0.0), ("R", 0.5)):
        side = -1 if label == "L" else 1
        p = (t / TAU + ph) % 1.0
        dy, dz, pitch = foot_track(p, stride * s, lift * s, stance, heel * s, toe_off, strike)
        base = legs.rest[label]["ankle"]
        a = Vector((base.x + side * width * s, base.y + dy, base.z + dz))
        # 地面约束：趾尖 / 脚跟（靴底中心线）的世界高度不低于 floor（IK 目标是世界坐标）
        L = B.legs[label]
        rot = Matrix.Rotation(-pitch, 3, "X")
        tip_z = a.z + (rot @ (L["toe"] - L["ankle"])).z
        heel_z = a.z + (rot @ Vector((0, -0.05 * s, B.hover + 0.02 * s - L["ankle"].z))).z
        a.z += max(0.0, floor - tip_z, floor - heel_z)
        legs.plant(pose, label, a, pitch=pitch, yaw=-side * 0.06, knee_out=knee_out)
        legs.toe(pose, label, clamp(pitch * 0.5, 0, 0.5) if p < stance else -0.05)
        sw = math.sin(t + (0 if label == "L" else math.pi))
        pose[f"UpperArm.{label}"] = R((Y, side * arm_in), (X, arm * sw))
        pose[f"Forearm.{label}"] = R((X, elbow + 0.25 * max(0.0, sw)))
        pose[f"Hand.{label}"] = R((X, -0.15))
    return pose


# ===== 检查 =====
def ground_check(rig, clips, bones, offset=0.0):
    scene = bpy.context.scene
    for clip in clips:
        act = bpy.data.actions[clip]
        rig.obj.animation_data.action = act
        f0, f1 = map(int, act.frame_range)
        lo = (1e9, "", 0)
        for f in range(f0, f1 + 1):
            scene.frame_set(f)
            for b in bones:
                pb = rig.obj.pose.bones[b]
                z = min(pb.head.z, pb.tail.z) - offset
                if z < lo[0]:
                    lo = (z, b, f)
        print(f"MOTION CHECK+ {clip}: min foot clearance {lo[0]:.3f} m at {lo[1]} frame {lo[2]}")


def seam_check(rig, clips):
    """循环动作首尾帧的最大骨旋转差（度）与位移差（米），应接近 0。"""
    scene = bpy.context.scene
    for clip in clips:
        act = bpy.data.actions[clip]
        rig.obj.animation_data.action = act
        first, last = map(int, act.frame_range)
        snap = []
        for f in (first, last):
            scene.frame_set(f)
            snap.append({pb.name: (pb.matrix.to_quaternion(), pb.matrix.to_translation()) for pb in rig.obj.pose.bones})
        worst, where, move = 0.0, "", 0.0
        for name, (qa, ta) in snap[0].items():
            qb, tb = snap[1][name]
            ang = math.degrees(qa.rotation_difference(qb).angle)
            ang = min(ang, 360 - ang)
            if ang > worst:
                worst, where = ang, name
            move = max(move, (ta - tb).length)
        print(f"MOTION CHECK+ {clip}: loop seam {worst:.2f} deg / {move:.4f} m {where}")


def tri_report(ctx):
    """按材质统计三角面（几何阶段估算展示版面数）。"""
    by = {}
    objs = [o for o, _ in ctx.parts] + [o for o, *_ in ctx.attached] + list(ctx.hidden)
    for o in objs:
        n = sum(len(p.vertices) - 2 for p in o.data.polygons)
        key = o.data.materials[0].name if o.data.materials else "?"
        by[key] = by.get(key, 0) + n
    total = sum(by.values())
    print("TRIS BOSS3 total", total, {k.replace(ctx.title + " ", ""): v for k, v in sorted(by.items(), key=lambda x: -x[1])})
    # 前缀分组的大户（去掉编号 / 左右后缀），便于定位预算
    groups = {}
    for o in objs:
        n = sum(len(p.vertices) - 2 for p in o.data.polygons)
        key = " ".join(w for w in o.name.replace(ctx.title + " ", "").split(" ")[:2] if not any(ch.isdigit() for ch in w))
        groups[key] = groups.get(key, 0) + n
    print("TRIS BOSS3 top", sorted(groups.items(), key=lambda x: -x[1])[:28])
    low = min(objs, key=lambda o: min((o.matrix_world @ v.co).z for v in o.data.vertices) if o.data.vertices else 9)
    print("LOWEST", low.name, min((low.matrix_world @ v.co).z for v in low.data.vertices))
    return total


def bbox_report(tag, objs):
    lo, hi = Vector((1e9,) * 3), Vector((-1e9,) * 3)
    for o in objs:
        if o.type != "MESH":
            continue
        for v in o.data.vertices:
            w = o.matrix_world @ v.co
            lo = Vector(map(min, lo, w))
            hi = Vector(map(max, hi, w))
    size = hi - lo
    print(f"BBOX {tag}: min {tuple(round(c, 2) for c in lo)} max {tuple(round(c, 2) for c in hi)} "
          f"size {tuple(round(c, 2) for c in size)}")
    return lo, hi


# ===== 网格后处理 =====
def thin_trims(ctx, keys=("trim", "hem", "inlay"), angle=8.0, min_tris=160):
    """细管按平面角溶解沿路径方向的冗余环（截面棱角 60° 不受影响），给不减面的滚边 / 嵌线省预算。"""
    saved = 0
    for obj, _ in ctx.parts:
        if not obj.data.materials or not any(k in obj.data.materials[0].name.lower() for k in keys):
            continue
        before = sum(len(p.vertices) - 2 for p in obj.data.polygons)
        if before < min_tris:
            continue
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        bmesh.ops.dissolve_limit(bm, angle_limit=math.radians(angle), verts=bm.verts[:], edges=bm.edges[:],
                                 delimit={"NORMAL"})
        bm.to_mesh(obj.data)
        bm.free()
        saved += before - sum(len(p.vertices) - 2 for p in obj.data.polygons)
    print("TRIM THIN saved", saved, "tris")


def clamp_ground(ctx, word, z=0.004):
    """把名字含 word 的部件低于 z 的顶点抬到 z（kit 铁靴放大到巨人尺寸后鞋底会沉入地面）。"""
    for obj, _ in ctx.parts:
        if word in obj.name:
            for v in obj.data.vertices:
                if v.co.z < z:
                    v.co.z = z
            obj.data.update()


# ===== 半透明幽火（思路同 Boss 2 的 flame_sheets，复制到本模块并改成淡紫配色） =====
def flame_maps(size=128, hot=(0.94, 0.88, 1.0), mid=(0.62, 0.44, 1.0), edge=(0.28, 0.10, 0.78), seed=3, core=1.0):
    """幽火贴图（RGBA）：u 横向、v 纵向（第 0 行为底 v=0）。alpha = 横向软边 × 纵向渐隐 × 纵向条纹；
    颜色随“核心度”在 边缘深紫 → 中段淡紫 → 核心近白 之间渐变。core 越大越偏亮（内焰用）。"""
    rng = np.random.default_rng(seed)
    v = np.linspace(0, 1, size, dtype=np.float32)[:, None] * np.ones((1, size), np.float32)
    u = np.linspace(0, 1, size, dtype=np.float32)[None, :] * np.ones((size, 1), np.float32)
    x = np.abs(2 * u - 1)
    soft = np.clip(1 - x ** 2.4, 0, 1) ** 0.9
    noise = box_blur(rng.random((size, size)).astype(np.float32), 5)
    noise = (noise - noise.min()) / max(1e-6, noise.max() - noise.min())
    streak = 0.72 + 0.28 * np.sin(TAU * (u * 3.0 + v * 1.3 + noise * 0.9)) ** 2
    rise = np.clip(v / 0.06, 0, 1)
    fade = rise * np.clip(1 - v, 0, 1) ** 1.35
    wisp = box_blur(rng.random((size, size)).astype(np.float32), 3)
    wisp = np.clip((wisp - wisp.min()) / max(1e-6, wisp.max() - wisp.min()) * 1.6 - 0.2, 0, 1)
    alpha = np.clip(soft * fade * streak * (0.55 + 0.45 * wisp) * 1.25, 0, 1) * 0.62
    t = np.clip(soft ** 1.6 * np.clip(1 - v * 0.8, 0, 1) * core * (0.7 + 0.3 * streak), 0, 1)
    lo = np.clip(t * 2.0, 0, 1)[..., None]
    hi = np.clip(t * 2.0 - 1.0, 0, 1)[..., None]
    c0, c1, c2 = (np.array(c, np.float32)[None, None, :] for c in (edge, mid, hot))
    rgb = c0 * (1 - lo) + c1 * lo
    rgb = rgb * (1 - hi) + c2 * hi
    return np.concatenate([rgb, alpha[..., None]], axis=2).astype(np.float32)


def flame_material(name, rgba, strength=3.0):
    """半透明自发光材质：同一张 RGBA 贴图接 Base Color / Emission Color / Alpha（glTF 导出只认同图 alpha）。
    Cycles 渲染透明正常；glTF 导出为 alphaMode=BLEND + doubleSided。"""
    h, w = rgba.shape[:2]
    img = bpy.data.images.new(f"{name} rgba", width=w, height=h, alpha=True)
    img.pixels.foreach_set(np.clip(rgba, 0, 1).ravel())
    img.alpha_mode = "STRAIGHT"
    img.pack()
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    p = nt.nodes["Principled BSDF"]
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = img
    tex.extension = "EXTEND"
    nt.links.new(tex.outputs["Color"], p.inputs["Base Color"])
    nt.links.new(tex.outputs["Color"], p.inputs["Emission Color"])
    nt.links.new(tex.outputs["Alpha"], p.inputs["Alpha"])
    p.inputs["Emission Strength"].default_value = strength
    p.inputs["Roughness"].default_value = 1.0
    p.inputs["Specular IOR Level"].default_value = 0.0
    m.use_backface_culling = False
    m.surface_render_method = "BLENDED"
    try:
        m.use_transparent_shadow = True
    except AttributeError:
        pass
    return m


def flame_sheets(name, base, direction, height, width, mats, n=4, seed=0.0, nu=5, nv=13, lean=0.0):
    """一束细长的幽火薄片：n 片绕轴交叉、高度 / 宽度各异，窄而长，路径带轻微摆动与前倾。
    UV：u 横跨薄片、v 自底向尖端 0→1。双面材质，本体不做实心。"""
    b = Vector(base)
    d = Vector(direction).normalized()
    a = d.orthogonal().normalized()
    c = d.cross(a)
    rng = random.Random(int(seed * 1000) + 7)
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.new("UVMap")
    for k in range(n):
        ang = k / n * math.pi + seed * 0.7
        side = a * math.cos(ang) + c * math.sin(ang)
        other = -a * math.sin(ang) + c * math.cos(ang)
        hk = height * (0.62 + 0.38 * rng.random())
        wk = width * (0.75 + 0.5 * rng.random())
        ph = rng.random() * TAU
        rows = []
        for j in range(nv):
            v = j / (nv - 1)
            body = (1 - v) ** 0.8 * (0.55 + 0.45 * math.sin(math.pi * min(1.0, v * 1.5 + 0.25)))
            wob = 0.16 * wk * math.sin(ph + v * 5.2) * v
            curl = (0.10 * hk * v ** 1.6 + lean * hk * v ** 2) * (1 if k % 2 else -0.6)
            cen = b + d * (hk * v) + side * wob + other * curl
            row = []
            for i in range(nu):
                u = i / (nu - 1)
                row.append(bm.verts.new(cen + side * (wk * body * (2 * u - 1))))
            rows.append(row)
        for j in range(nv - 1):
            for i in range(nu - 1):
                f = bm.faces.new((rows[j][i], rows[j][i + 1], rows[j + 1][i + 1], rows[j + 1][i]))
                for loop, (ii, jj) in zip(f.loops, ((i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1))):
                    loop[uvl].uv = (ii / (nu - 1), jj / (nv - 1))
    return bm_object(name, bm, mats, smooth=False)


# ===== 网格：链环、方块 =====
def _frames(pts, up=(0, 0, 1)):
    m = len(pts)
    T = [(pts[min(i + 1, m - 1)] - pts[max(i - 1, 0)]).normalized() for i in range(m)]
    upv = Vector(up)
    n0 = upv - T[0] * upv.dot(T[0])
    if n0.length < 1e-5:
        n0 = Vector((1, 0, 0)) - T[0] * T[0].x
    N = [n0.normalized()]
    for i in range(1, m):
        nn = N[-1] - T[i] * N[-1].dot(T[i])
        N.append(nn.normalized() if nn.length > 1e-6 else N[-1])
    return T, N, [t.cross(n) for t, n in zip(T, N)]


def chain_links(name, path, link_len, wire, mats, seg=10, sides=5):
    """沿路径摆放交替正交的椭圆链环，返回单个网格对象。"""
    pts, _ = catmull([Vector(p) for p in path], [1.0] * len(path), 8)
    acc = [0.0]
    for i in range(1, len(pts)):
        acc.append(acc[-1] + (pts[i] - pts[i - 1]).length)
    total = acc[-1]
    count = max(2, int(total / (link_len * 0.78)))
    T, N, Bn = _frames(pts)
    width = link_len * 0.62
    bm = bmesh.new()

    def at(s):
        for i in range(1, len(acc)):
            if acc[i] >= s:
                t = (s - acc[i - 1]) / max(1e-9, acc[i] - acc[i - 1])
                return pts[i - 1].lerp(pts[i], t), T[i], N[i], Bn[i]
        return pts[-1], T[-1], N[-1], Bn[-1]
    for k in range(count):
        c, t, n, b = at((k + 0.5) * total / count)
        ang = math.pi / 2 if k % 2 else 0.0
        side = n * math.cos(ang) + b * math.sin(ang)
        A, Bw = link_len * 0.5 - wire, width * 0.5 - wire
        rings = []
        for i in range(seg):
            th = TAU * i / seg
            p = c + t * (math.cos(th) * A) + side * (math.sin(th) * Bw)
            tan = (-t * math.sin(th) * A + side * math.cos(th) * Bw).normalized()
            out = (p - c).normalized()
            perp = tan.cross(out).normalized()
            rings.append([bm.verts.new(p + out * math.cos(TAU * j / sides) * wire + perp * math.sin(TAU * j / sides) * wire)
                          for j in range(sides)])
        for i in range(seg):
            i2 = (i + 1) % seg
            for j in range(sides):
                j2 = (j + 1) % sides
                bm.faces.new((rings[i][j], rings[i2][j], rings[i2][j2], rings[i][j2]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return bm_object(name, bm, mats)


def box(name, center, size, mats, axes=None):
    """轴对齐（或按 axes 三列朝向）的小方块：LED、铆块。"""
    c = Vector(center)
    ax = axes or (Vector((1, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1)))
    bm = bmesh.new()
    vs = []
    for dx in (-1, 1):
        for dy in (-1, 1):
            for dz in (-1, 1):
                vs.append(bm.verts.new(c + ax[0] * dx * size[0] / 2 + ax[1] * dy * size[1] / 2 + ax[2] * dz * size[2] / 2))
    for f in ((0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)):
        bm.faces.new([vs[i] for i in f])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return bm_object(name, bm, mats, smooth=False)


def drawer(name, center, size, mats, v0, v1, flip=False, dark_uv=(0.5, 0.01)):
    """机柜抽屉：方盒，前面（+Y）的 UV 取机架贴图的 [v0, v1] 一行（每个抽屉一种灯阵），其余面取一个暗点。"""
    c = Vector(center)
    hx, hy, hz = size[0] / 2, size[1] / 2, size[2] / 2
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.new("UVMap")
    V = {}
    for ix in (-1, 1):
        for iy in (-1, 1):
            for iz in (-1, 1):
                V[(ix, iy, iz)] = bm.verts.new(c + Vector((ix * hx, iy * hy, iz * hz)))
    faces = {
        "front": ((-1, 1, -1), (1, 1, -1), (1, 1, 1), (-1, 1, 1)),
        "back": ((1, -1, -1), (-1, -1, -1), (-1, -1, 1), (1, -1, 1)),
        "left": ((-1, -1, -1), (-1, 1, -1), (-1, 1, 1), (-1, -1, 1)),
        "right": ((1, 1, -1), (1, -1, -1), (1, -1, 1), (1, 1, 1)),
        "top": ((-1, -1, 1), (-1, 1, 1), (1, 1, 1), (1, -1, 1)),
        "bottom": ((-1, 1, -1), (-1, -1, -1), (1, -1, -1), (1, 1, -1)),
    }
    for key, quad in faces.items():
        f = bm.faces.new([V[q] for q in quad])
        for loop, q in zip(f.loops, quad):
            if key == "front":
                u = (q[0] + 1) / 2
                loop[uvl].uv = (1 - u if flip else u, v0 if q[2] < 0 else v1)
            else:
                loop[uvl].uv = (dark_uv[0], dark_uv[1] + v0)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return bm_object(name, bm, mats, smooth=False)


# ===== 破烂幽灵斗篷（kit Wrap 的变体：撕裂条带下摆 + 背中撕缝 + 不规则破洞） =====
def ragged_hem(base_fn, n=14, long=(0.18, 1.0), notch=(0.12, 0.60), seed=7):
    """撕裂下摆：n 条宽窄不一的条带，每条中线向下尖出 L（长短不一），条带之间的缝向上撕开 N。返回 bottom(u)。"""
    rng = random.Random(seed)
    L = [long[0] + (long[1] - long[0]) * rng.random() ** 1.8 for _ in range(n)]      # 多短少长，个别条带特别长
    N = [notch[0] + (notch[1] - notch[0]) * rng.random() ** 1.3 for _ in range(n)]
    W = [rng.uniform(0.5, 1.8) for _ in range(n)]
    edges = [0.0]
    for w in W:
        edges.append(edges[-1] + w)
    edges = [e / edges[-1] for e in edges]

    def bottom(u):
        u = clamp(u)
        i = n - 1
        for k in range(n):
            if u <= edges[k + 1]:
                i = k
                break
        f = (u - edges[i]) / max(1e-6, edges[i + 1] - edges[i])
        tip = 1 - abs(2 * f - 1)
        return base_fn(u) - L[i] * tip ** 0.75 + N[i] * (1 - tip) ** 7
    return bottom


class RaggedCape(Wrap):
    """破烂披风：布面在 (u, v) 上按 cut() 挖掉破洞 / 背中撕缝；解开的边缘（下摆、缝、洞）用实体化的“边缘材质”发淡紫微光。
    UV 的 v 取绝对高度（zlow→ztop），符文带 / 烟缕不会随撕裂的下摆形变。"""

    def __init__(self, *args, holes=(), slit=None, zlow=0.0, ztop=1.0, **kw):
        super().__init__(*args, **kw)
        self.holes, self.slit, self.zlow, self.ztop = holes, slit, zlow, ztop

    def cut(self, u, v):
        if self.slit:
            u0, hw, v1 = self.slit
            if v < v1 and abs(u - u0) < hw * (1 - v / v1) ** 0.65:
                return True
        for hu, hv, ru, rv, ph in self.holes:
            dx, dy = (u - hu) / ru, (v - hv) / rv
            ang = math.atan2(dy, dx)
            jag = 1 + 0.32 * math.sin(3 * ang + ph) + 0.18 * math.sin(7 * ang + 2 * ph)
            if dx * dx + dy * dy < jag * jag:
                return True
        return False

    def build(self, ctx, mats, name, nu=150, nv=70, thickness=0.020, uv_scale=1.4, hem=None, edges=None, extra_spec=None):
        bm = bmesh.new()
        uvl = bm.loops.layers.uv.new("UVMap")
        grid = [[bm.verts.new(self.point(i / (nu - 1), j / (nv - 1))) for i in range(nu)] for j in range(nv)]
        for j in range(nv - 1):
            for i in range(nu - 1):
                if self.cut((i + 0.5) / (nu - 1), (j + 0.5) / (nv - 1)):
                    continue
                f = bm.faces.new((grid[j][i], grid[j][i + 1], grid[j + 1][i + 1], grid[j + 1][i]))
                for loop, (ii, jj) in zip(f.loops, ((i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1))):
                    z = grid[jj][ii].co.z
                    loop[uvl].uv = (ii / (nu - 1) * uv_scale, (z - self.zlow) / (self.ztop - self.zlow))
        bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context="VERTS")
        cloth = bm_object(name, bm, mats)
        orient(cloth, lambda c: Vector((0, self.cy, c.z)))
        solidify(cloth, thickness, 0, inner_offset=1, rim_offset=2 if len(mats) > 2 else 0)
        ctx.part(apply_all(cloth), extra_spec or garment(self))
        return cloth


# ===== 燕尾军旗（kit Panel 的变体：宽度不收尖，底边中部上凹） =====
class Banner(Panel):
    def __init__(self, *args, notch=0.0, **kw):
        super().__init__(*args, **kw)
        self.notch = notch

    def width(self, v):
        return self._width(v) if callable(self._width) else interp(self._width, v)

    def bottom(self, u):
        return self._tip + self.notch * (1 - abs(2 * u - 1)) ** 0.9

    def point(self, u, v):
        w = self.width(v)
        x = (u - 0.5) * w
        y = self.side * (self.depth(v) - self.curve * x * x) + self.flutter * math.sin(u * math.pi * 3 + v * 4) * v
        return Vector((self.cx + x, y, lerp(self._top, self.bottom(u), v)))

    def param(self, p):
        u = clamp((p.x - self.cx) / max(1e-4, self.width(0.5)) + 0.5)
        v = 0.5
        for _ in range(3):
            v = clamp((self._top - p.z) / max(1e-4, self._top - self.bottom(u)))
            u = clamp((p.x - self.cx) / max(1e-4, self.width(v)) + 0.5)
        return u, v


# ===== 程序化贴图（第 0 行为图像底边） =====
def bone_maps(base_rgb=(0.74, 0.70, 0.60), emit_rgb=(0.8, 0.67, 1.0), size=1024, seed=5):
    """骨质：低频斑驳 + 细孔 + 少量细裂（裂缝深处透出极淡的幽光）。"""
    rng = np.random.default_rng(seed)
    blot = box_blur(rng.random((size, size)).astype(np.float32), 36) - 0.5
    blot2 = box_blur(rng.random((size, size)).astype(np.float32), 6) - 0.5
    streak = box_blur(np.repeat(rng.random((size, 1)).astype(np.float32), size, axis=1), 2) - 0.5
    f1, f2, _ = voronoi(size, 6, rng)
    crack = np.clip(1 - (f2 - f1) / 0.030, 0, 1) ** 3
    region = np.clip((box_blur(rng.random((size, size)).astype(np.float32), 48) - 0.5) * 14 + 0.3, 0, 1)
    crack = crack * region
    pores = box_blur((rng.random((size, size)) > 0.9965).astype(np.float32), 1) * 6
    tone = 1 + blot * 1.6 + blot2 * 0.35 + streak * 0.25
    base = np.stack([base_rgb[i] * tone for i in range(3)], axis=2)
    grime = np.clip(pores * 0.5 + crack * 0.8, 0, 1)[..., None]
    base = base * (1 - grime * 0.55) + np.array((0.22, 0.18, 0.16))[None, None, :] * grime * 0.3
    em = np.stack([crack * c * 0.55 for c in emit_rgb], axis=2)
    hgt = blot * 0.5 + blot2 * 0.4 + streak * 0.2 - pores * 0.3 - crack * 0.9
    return np.clip(base, 0, 1), np.clip(em, 0, 1), height_normal(box_blur(hgt.astype(np.float32), 1), 2.2)


def wisp_maps(emit_rgb, base_rgb=(0.030, 0.018, 0.055), size=1024, seed=19, rune_rows=(46, 112)):
    """幽灵斗篷：纵向烟缕自下摆向上渐隐发光，下摆一条符文带。"""
    rng = np.random.default_rng(seed)
    cols = rng.random((40, size)).astype(np.float32)
    yi = np.linspace(0, 39, size)
    i0 = np.minimum(np.floor(yi).astype(int), 38)
    t = (yi - i0)[:, None]
    field = cols[i0] * (1 - t) + cols[i0 + 1] * t
    field = box_blur(field, 3)
    streak = np.clip((field - 0.56) * 4.5, 0, 1) ** 1.3
    v = np.linspace(0, 1, size)[:, None]
    fade = np.clip(1 - v / 0.62, 0, 1) ** 1.7
    cv = Canvas(size, size)
    y0, y1 = rune_rows
    cv.line(0, y0 - 6, size, y0 - 6, 1)
    cv.line(0, y1 + 6, size, y1 + 6, 1)
    cols_n = 16
    cw = size / cols_n
    for c in range(cols_n):
        g = GLYPHS[int(rng.integers(len(GLYPHS)))]
        s = (y1 - y0) * 0.8
        x0 = c * cw + (cw - s) / 2
        for (a, b, cc, d) in g:
            cv.line(x0 + a * s, y0 + 6 + b * s, x0 + cc * s, y0 + 6 + d * s, 2)
    rune = np.clip(cv.mask, 0, 1)
    glow = np.clip(streak * fade * 0.85 + rune * 0.9 + box_blur(rune, 3) * 0.4, 0, 1.2)
    em = np.stack([glow * c for c in emit_rgb], axis=2)
    tone = 0.75 + field * 0.6
    base = np.stack([base_rgb[i] * tone + streak * fade * emit_rgb[i] * 0.10 + rune * emit_rgb[i] * 0.08
                     for i in range(3)], axis=2)
    return np.clip(base, 0, 1), np.clip(em, 0, 1), height_normal(box_blur(field * 0.6 + rune, 2), 1.4)


def _ellipse(cv, cx, cy, rx, ry, w=2, a0=0.0, a1=TAU):
    n = int(max(rx, ry) * 8) + 24
    th = np.linspace(a0, a1, n)
    cv._stamp(cx + np.cos(th) * rx, cy + np.sin(th) * ry, w)


def _poly(cv, pts, w=2, closed=True):
    n = len(pts)
    for i in range(n if closed else n - 1):
        (xa, ya), (xb, yb) = pts[i], pts[(i + 1) % n]
        cv.line(xa, ya, xb, yb, w)


def _fill(cv, pts):
    """扫描线填充多边形（遮罩置 1）。"""
    ys = [q[1] for q in pts]
    n = len(pts)
    for y in range(int(max(0, min(ys))), int(min(cv.h - 1, max(ys))) + 1):
        xs = []
        for i in range(n):
            (xa, ya), (xb, yb) = pts[i], pts[(i + 1) % n]
            if (ya <= y < yb) or (yb <= y < ya):
                xs.append(xa + (y - ya) * (xb - xa) / (yb - ya))
        xs.sort()
        for k in range(0, len(xs) - 1, 2):
            cv.mask[y, int(max(0, xs[k])):int(min(cv.w - 1, xs[k + 1])) + 1] = 1.0


def _emblem(gold, glow, cx, cy, s=1.0, rng=None, crossed=True):
    """王冠骷髅徽记：符文双环 + 五齿王冠（高 / 中 / 低节奏，同头盔）+ 斜眼骷髅 + 机柜小图标 + 交叉旗枪。
    gold / glow 为两张 Canvas（金线 / 发光）。s 为整体缩放。"""
    rng = rng or np.random.default_rng(3)
    R = 170 * s
    _ellipse(gold, cx, cy, R, R, 3)
    _ellipse(gold, cx, cy, R - 20 * s, R - 20 * s, 1)
    for k in range(32):                                              # 刻度
        a = k / 32 * TAU
        gold.line(cx + math.cos(a) * (R - 18 * s), cy + math.sin(a) * (R - 18 * s),
                  cx + math.cos(a) * (R - 6 * s), cy + math.sin(a) * (R - 6 * s), 1)
    _ellipse(glow, cx, cy, R - 40 * s, R - 40 * s, 2)
    for k in range(12):                                              # 环上发光符文点
        a = k / 12 * TAU + 0.26
        x, y = cx + math.cos(a) * (R - 40 * s), cy + math.sin(a) * (R - 40 * s)
        glow.dot(x, y, 7 * s)
        glow.line(x, y, cx + math.cos(a) * (R - 58 * s), cy + math.sin(a) * (R - 58 * s), 2)
    # 王冠
    by = cy + R - 2 * s
    for yy in (by, by + 16 * s):
        gold.line(cx - 120 * s, yy, cx + 120 * s, yy, 3 if yy == by else 2)
    for k, h in zip(range(-2, 3), (46, 78, 122, 78, 46)):
        x = cx + k * 54 * s
        top = by + 16 * s + h * s
        gold.line(x - 20 * s, by + 16 * s, x, top, 3)
        gold.line(x + 20 * s, by + 16 * s, x, top, 3)
        glow.dot(x, top + 12 * s, 8 * s if k == 0 else 6 * s)
    for k in (-2, -1, 0, 1, 2):
        glow.dot(cx + k * 54 * s, by + 8 * s, 4 * s)
    # 骷髅
    hy = cy + 26 * s
    _ellipse(gold, cx, hy + 14 * s, 72 * s, 80 * s, 3, math.radians(-12), math.radians(192))
    gold.line(cx - 70 * s, hy + 6 * s, cx - 52 * s, hy - 28 * s, 3)
    gold.line(cx + 70 * s, hy + 6 * s, cx + 52 * s, hy - 28 * s, 3)
    for sx in (-1, 1):
        eye = [(cx + sx * 12 * s, hy + 12 * s), (cx + sx * 60 * s, hy + 38 * s), (cx + sx * 52 * s, hy + 2 * s),
               (cx + sx * 20 * s, hy - 8 * s)]
        _fill(glow, eye)
        _poly(gold, eye, 2)
    nose = [(cx, hy - 2 * s), (cx - 11 * s, hy - 26 * s), (cx + 11 * s, hy - 26 * s)]
    _fill(glow, nose)
    jaw = [(cx - 52 * s, hy - 28 * s), (cx - 40 * s, hy - 68 * s), (cx, hy - 82 * s), (cx + 40 * s, hy - 68 * s),
           (cx + 52 * s, hy - 28 * s)]
    _poly(gold, jaw, 3, closed=False)
    for k in range(-4, 5):
        gold.line(cx + k * 10 * s, hy - 36 * s, cx + k * 10 * s, hy - 56 * s, 2)
    gold.line(cx - 46 * s, hy - 36 * s, cx + 46 * s, hy - 36 * s, 2)
    # 机柜小图标
    for k in range(3):
        y = cy - 104 * s - k * 22 * s
        gold.rect(cx - 40 * s, y, 80 * s, 16 * s, 1)
        for j in range(4):
            glow.dot(cx + 12 * s + j * 10 * s, y + 8 * s, 2.4 * s)
        gold.line(cx - 32 * s, y + 8 * s, cx - 8 * s, y + 8 * s, 1)
    if crossed:                                                      # 交叉旗枪（环外可见）
        for sx in (-1, 1):
            a = (cx + sx * 260 * s, cy - 250 * s)
            b = (cx - sx * 190 * s, cy + 215 * s)
            for q in np.linspace(0, 1, int(540 * s)):
                x, y = a[0] + (b[0] - a[0]) * q, a[1] + (b[1] - a[1]) * q
                if (x - cx) ** 2 + (y - cy) ** 2 > (R + 8 * s) ** 2:
                    gold.dot(x, y, 1)
            gold.dot(a[0], a[1], 4)


def banner_maps(gold_rgb, emit_rgb, base_rgb=(0.045, 0.020, 0.095), w=512, h=832, seed=23):
    """军旗纹样：金线双边框 + 角饰、上下符文带、侧边发光链点、中央“王冠骷髅 + 机柜 + 交叉旗枪”徽记（徽记 / 符文发光）。
    燕尾缺口约占下沿中间 19% 高度，下符文带放在缺口之上。"""
    rng = np.random.default_rng(seed)
    gold = Canvas(w, h)
    glow = Canvas(w, h)
    for inset, lw in ((12, 3), (26, 1)):
        gold.rect(inset, inset, w - 2 * inset, h - 2 * inset, lw)
    for sx in (0, 1):                                                 # 四角菱饰
        for sy in (0, 1):
            x = 26 + sx * (w - 52)
            y = 26 + sy * (h - 52)
            dx, dy = (1 if sx == 0 else -1), (1 if sy == 0 else -1)
            _poly(gold, [(x, y), (x + dx * 34, y), (x + dx * 34, y + dy * 4), (x + dx * 4, y + dy * 34), (x, y + dy * 34)], 1)
            glow.dot(x + dx * 14, y + dy * 14, 3)
    for yb in (h - 150, 196):                                          # 符文带
        gold.line(44, yb, w - 44, yb, 1)
        gold.line(44, yb + 78, w - 44, yb + 78, 1)
        n = 6
        cw = (w - 88) / n
        for c in range(n):
            g = GLYPHS[int(rng.integers(len(GLYPHS)))]
            sz = 50
            x0 = 44 + c * cw + (cw - sz) / 2
            for (a, b, cc, d) in g:
                glow.line(x0 + a * sz, yb + 14 + b * sz, x0 + cc * sz, yb + 14 + d * sz, 2)
    _emblem(gold, glow, w / 2, h * 0.50, 0.84, rng)
    for x in (58, w - 58):                                            # 侧边链点
        gold.line(x, 270, x, h - 250, 1)
        for y in range(280, h - 250, 34):
            glow.dot(x, y, 3)
    gm = np.clip(gold.mask, 0, 1)
    em_m = np.clip(glow.mask, 0, 1)
    halo = box_blur(em_m, 4)
    grain = box_blur(rng.random((h, w)).astype(np.float32), 10) - 0.5
    weave = 0.5 + 0.5 * np.sin(np.linspace(0, 1, w)[None, :] * 150.0)
    v = np.linspace(0, 1, h)[:, None]
    shade = 0.85 + 0.30 * v
    base = np.stack([base_rgb[i] * (1 + grain * 1.2 + weave * 0.15) * shade for i in range(3)], axis=2)
    base = base * (1 - gm[..., None]) + np.array(gold_rgb)[None, None, :] * gm[..., None]
    base += em_m[..., None] * np.array(emit_rgb)[None, None, :] * 0.25
    em = np.stack([np.clip(em_m + halo * 0.5, 0, 1.2) * c for c in emit_rgb], axis=2)
    return np.clip(base, 0, 1), np.clip(em, 0, 1), height_normal(box_blur(gm + em_m * 0.5, 1), 2.0)


def tabard_maps(gold_rgb, emit_rgb, base_rgb=(0.045, 0.020, 0.095), w=256, h=1024, seed=31):
    """前垂旗（窄长 1:4）：顶部符文带、小王冠骷髅徽记、纵向链点与金线、下段符文 + 尖端宝珠。"""
    rng = np.random.default_rng(seed)
    gold = Canvas(w, h)
    glow = Canvas(w, h)
    gold.rect(8, 8, w - 16, h - 16, 2)
    gold.rect(18, 18, w - 36, h - 36, 1)
    for yb in (h - 128, 520):
        gold.line(26, yb, w - 26, yb, 1)
        gold.line(26, yb + 52, w - 26, yb + 52, 1)
        n = 4
        cw = (w - 52) / n
        for c in range(n):
            g = GLYPHS[int(rng.integers(len(GLYPHS)))]
            sz = 34
            x0 = 26 + c * cw + (cw - sz) / 2
            for (a, b, cc, d) in g:
                glow.line(x0 + a * sz, yb + 9 + b * sz, x0 + cc * sz, yb + 9 + d * sz, 2)
    _emblem(gold, glow, w / 2, 700, 0.50, rng, crossed=False)
    for x in (40, w - 40):
        gold.line(x, 150, x, 560, 1)
        for y in range(160, 560, 30):
            glow.dot(x, y, 2.4)
    for k in range(5):                                                 # 下段纵向光链
        y = 140 + k * 66
        gold.line(w / 2 - 50, y, w / 2, y - 24, 1)
        gold.line(w / 2 + 50, y, w / 2, y - 24, 1)
        glow.dot(w / 2, y - 24, 4)
    gm = np.clip(gold.mask, 0, 1)
    em_m = np.clip(glow.mask, 0, 1)
    halo = box_blur(em_m, 3)
    grain = box_blur(rng.random((h, w)).astype(np.float32), 8) - 0.5
    weave = 0.5 + 0.5 * np.sin(np.linspace(0, 1, w)[None, :] * 90.0)
    base = np.stack([base_rgb[i] * (1 + grain * 1.2 + weave * 0.15) for i in range(3)], axis=2)
    base = base * (1 - gm[..., None]) + np.array(gold_rgb)[None, None, :] * gm[..., None]
    base += em_m[..., None] * np.array(emit_rgb)[None, None, :] * 0.25
    em = np.stack([np.clip(em_m + halo * 0.5, 0, 1.2) * c for c in emit_rgb], axis=2)
    return np.clip(base, 0, 1), np.clip(em, 0, 1), height_normal(box_blur(gm + em_m * 0.5, 1), 2.0)


def rack_maps(emit_rgb, base_rgb=(0.060, 0.058, 0.082), size=512, units=4, seed=29):
    """服务器机柜正面（每个抽屉取其中一行）：左侧散热格栅，右侧两排大指示灯（亮暗随机）、条形图状态光条、盘位方框。
    units 行等高，第 0 行在图像底边。"""
    rng = np.random.default_rng(seed)
    seam = Canvas(size, size)
    vent = Canvas(size, size)
    leds = [Canvas(size, size) for _ in range(3)]
    bar = Canvas(size, size)
    bay = Canvas(size, size)
    uh = size / units
    seam.rect(5, 5, size - 10, size - 10, 2)
    for i in range(units):
        y0 = i * uh
        seam.line(5, y0 + 2, size - 5, y0 + 2, 2)
        for k in range(6):
            vent.line(30, y0 + uh * (0.18 + 0.115 * k), size * 0.36, y0 + uh * (0.18 + 0.115 * k), 2)
        for row, yy in enumerate((0.72, 0.46)):
            for k in range(8):
                leds[int(rng.choice(3, p=[0.45, 0.35, 0.20]))].dot(size * 0.43 + k * 26, y0 + uh * yy, 7)
        bar.line(size * 0.43, y0 + uh * 0.20, size * (0.50 + rng.uniform(0.15, 0.48)), y0 + uh * 0.20, 4)
        bay.rect(size * 0.43, y0 + uh * 0.10, size * 0.50, uh * 0.18, 1)
    em_m = leds[0].mask * 1.0 + leds[1].mask * 0.55 + leds[2].mask * 0.22 + bar.mask * 0.8
    em_m = np.clip(em_m, 0, 1)
    halo = box_blur(em_m, 4)
    grain = box_blur(rng.random((size, size)).astype(np.float32), 6) - 0.5
    dark = np.clip(seam.mask + vent.mask * 0.8, 0, 1)
    base = np.stack([base_rgb[i] * (1 + grain * 0.8) * (1 - dark * 0.7) for i in range(3)], axis=2)
    base += em_m[..., None] * np.array(emit_rgb)[None, None, :] * 0.45
    base += bay.mask[..., None] * 0.05
    em = np.stack([np.clip(em_m + halo * 0.8, 0, 1.3) * c for c in emit_rgb], axis=2)
    return np.clip(base, 0, 1), np.clip(em, 0, 1), height_normal(-box_blur(dark, 1) + bay.mask * 0.3, 2.0)
