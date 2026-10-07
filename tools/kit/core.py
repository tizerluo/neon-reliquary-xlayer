"""角色工具包 · 核心：数学、网格、材质、程序化贴图与部件登记。

在 Blender 5.2 内由 tools/build_char.py 加载，不单独运行。
坐标约定与尼克斯一致：Blender Z 向上，角色正面朝 +Y，单位米（导出 glTF 后正面为 -Z）。
"""

import math
import sys
from pathlib import Path

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))
from nyx_lib import (Canvas, _box_blur, apply_all, attach_texture, bevel, bm_object,  # noqa: E402,F401
                     boundary_loops, catmull, clamp, ellipsoid, interp, lerp, link, material,
                     pcb_bus, smoothstep, solidify, subsurf, surface, tube)

ROOT = TOOLS.parent
TAU = math.tau
box_blur = _box_blur


# ===== 通用数学 =====
def crest(x):
    """|sin|^0.6：圆润外凸的褶峰 + 收紧的内凹褶谷，取值 [-1, 1]。"""
    return abs(math.sin(x)) ** 0.6 * 2 - 1


def hash01(k, seed=0.0):
    return (math.sin(k * 12.9898 + seed * 78.233) * 43758.5453) % 1.0


def rotate(v, axis, angle):
    return Matrix.Rotation(angle, 3, Vector(axis).normalized()) @ Vector(v)


def V(*a):
    return Vector(a[0]) if len(a) == 1 else Vector(a)


def radial(p, d, center_y=0.0):
    """沿水平径向（绕 Z 轴，中心 y=center_y）把点外推 d 米。"""
    r = Vector((p.x, p.y - center_y, 0))
    return p + (r.normalized() * d if r.length > 1e-9 else Vector((0, 0, 0)))


def frame_from(direction, up=(0, 0, 1)):
    """以 direction 为 Y 轴、up 近似为 Z 轴的正交标架（列向量 x, y, z）。"""
    y = Vector(direction).normalized()
    z = Vector(up)
    z = (z - y * z.dot(y))
    if z.length < 1e-6:
        z = Vector((1, 0, 0)) - y * y.x
    z.normalize()
    x = y.cross(z)
    return Matrix((x, y, z)).transposed()


# ===== 部件登记与蒙皮规格 =====
class Ctx:
    """单个角色的构建上下文：材质、部件（含蒙皮规格）、挂骨件、贴图目录与关键点。"""

    def __init__(self, cid, title):
        self.id = cid
        self.ID = cid.upper().replace("-", "_")
        self.title = title
        self.M = {}
        self.parts = []       # (对象, 蒙皮规格)
        self.attached = []    # (对象, 骨名)：刚性挂骨、不蒙皮（光环、翅膀羽片、杂兵部件）
        self.hidden = []      # 只进展示版、不进游戏 LOD 的对象
        self.marks = {}
        self.tex_dir = ROOT / "art" / "chars" / cid / "textures"
        self.tex_dir.mkdir(parents=True, exist_ok=True)

    def part(self, obj, spec):
        self.parts.append((obj, spec))
        return obj

    def attach(self, obj, bone, keep=False):
        """刚性挂骨；keep=True 时保留对象名独立成节点（网页端要按名字驱动旋转的部件）。"""
        self.attached.append((obj, bone, keep))
        return obj

    def mat(self, key, suffix, base, **kw):
        self.M[key] = material(f"{self.title} {suffix}", base, **kw)
        return self.M[key]

    def image(self, name, arr, noncolor=False):
        h, w = arr.shape[:2]
        rgba = np.concatenate([np.clip(arr, 0, 1).astype(np.float32), np.ones((h, w, 1), np.float32)], axis=2)
        img = bpy.data.images.new(f"{self.title} {name}", width=w, height=h, alpha=False)
        img.colorspace_settings.name = "Non-Color" if noncolor else "sRGB"
        img.pixels.foreach_set(rgba.ravel())
        img.filepath_raw = str(self.tex_dir / (f"{self.id}-{name}".lower().replace(" ", "-") + ".png"))
        img.file_format = "PNG"
        img.save()
        img.pack()
        return img

    def texture(self, key, maps, emit_strength=None, normal_strength=0.6):
        """把 (base, emission, normal) 三张图挂到材质 key 上；emission 可为 None。"""
        base, emission, normal = maps
        m = self.M[key]
        attach_texture(m, self.image(f"{key} base", base), "Base Color")
        if emission is not None:
            attach_texture(m, self.image(f"{key} emit", emission), "Emission Color")
            if emit_strength is not None:
                m.node_tree.nodes["Principled BSDF"].inputs["Emission Strength"].default_value = emit_strength
        if normal is not None:
            attach_texture(m, self.image(f"{key} normal", normal, True), "Normal", normal_strength)
        return m


def rigid(*pairs, **named):
    """rigid("Chest") / rigid(("Chest", .4), ("UpperArm.L", .6))。"""
    if len(pairs) == 1 and isinstance(pairs[0], str):
        return ("rigid", {pairs[0]: 1.0})
    w = dict(pairs)
    w.update(named)
    return ("rigid", w)


def chain(bones, parent=None, win=0.05):
    return ("chain", list(bones), parent, win)


def invdist(bones, win=0.05):
    return ("chain", list(bones), None, win)


def bands(levels):
    """按高度分段混合：levels 为自上而下 [(z, 骨名), ...]，相邻两级之间线性过渡。"""
    return ("bands", levels)


def garment(g):
    return ("garment", g)


def fn(callable_):
    return ("fn", callable_)


# ===== 网格工具 =====
def orient(obj, ref):
    """若多数面法线朝向参考点，则整体翻转，保证法线朝外。ref(c) 返回“内部”参考点。"""
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    score = 0.0
    for f in bm.faces:
        c = f.calc_center_median()
        score += f.normal.dot(c - ref(c)) * f.calc_area()
    if score < 0:
        bmesh.ops.reverse_faces(bm, faces=bm.faces[:])
    bm.to_mesh(obj.data)
    bm.free()
    return obj


def axis_ref(c):
    return Vector((0, 0, c.z))


def point_ref(p):
    p = Vector(p)
    return lambda c: p


def transform(obj, matrix):
    obj.data.transform(matrix)
    obj.data.update()
    return obj


def finish(obj, thickness=None, offset=1.0, sub=1, bev=None, inner_offset=0, rim_offset=0):
    """常用收尾：加厚 → 倒角 → 细分，并应用为真实网格。"""
    if thickness:
        solidify(obj, thickness, offset, inner_offset, rim_offset)
    if bev:
        bevel(obj, bev, 2, 30)
    if sub:
        subsurf(obj, sub)
    return apply_all(obj)


def lathe(name, profile, mats, segments=48, center=(0, 0, 0), sx=1.0, sy=1.0, a0=0.0, a1=TAU, closed=None):
    """车削体：profile 为 [(半径, 高度), ...] 自上而下；绕 Z 轴旋转，可局部扇形。"""
    c = Vector(center)
    full = closed if closed is not None else abs(a1 - a0 - TAU) < 1e-6

    def pt(u, v):
        r, z = interp([(i / (len(profile) - 1), (pr, pz)) for i, (pr, pz) in enumerate(profile)], v)
        a = a0 + u * (a1 - a0)
        return c + Vector((math.sin(a) * r * sx, math.cos(a) * r * sy, z))
    nv = max(2, len(profile) * 3)
    obj = surface(name, pt, segments, nv, mats, closed_u=full)
    return orient(obj, lambda q: Vector((c.x, c.y, q.z)))


def loft(name, sections, mats, closed_u=True, cap=False, uvfn=None):
    """按截面放样：sections 为等长点列的列表（自上而下）。"""
    rows = [[Vector(p) for p in s] for s in sections]
    nu, nv = len(rows[0]), len(rows)
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.new("UVMap")
    verts = [[bm.verts.new(p) for p in r] for r in rows]
    du = nu if closed_u else nu - 1
    for j in range(nv - 1):
        for i in range(nu if closed_u else nu - 1):
            i2 = (i + 1) % nu
            try:
                f = bm.faces.new((verts[j][i], verts[j][i2], verts[j + 1][i2], verts[j + 1][i]))
            except ValueError:
                continue
            for loop, (ii, jj) in zip(f.loops, ((i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1))):
                u, v = ii / du, jj / (nv - 1)
                loop[uvl].uv = uvfn(u, v) if uvfn else (u, 1 - v)
    if cap and closed_u:
        for r in (verts[0], verts[-1]):
            try:
                bm.faces.new(r)
            except ValueError:
                pass
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return bm_object(name, bm, mats)


def plate(name, outline, depth, mats, origin=(0, 0, 0), xaxis=(1, 0, 0), yaxis=(0, 0, 1),
          bulge=None, bev=0.0, bev_seg=2, sub=0):
    """二维轮廓挤出的甲片 / 刃片：outline 为局部 (x, y)，沿 x×y 法向挤出 depth。
    bulge(x, y) 返回沿法向的弯曲偏移，用于做出弧面甲片。"""
    o, xa, ya = Vector(origin), Vector(xaxis).normalized(), Vector(yaxis).normalized()
    na = xa.cross(ya).normalized()
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.new("UVMap")
    xs = [p[0] for p in outline]
    ys = [p[1] for p in outline]
    w, h = max(xs) - min(xs) or 1, max(ys) - min(ys) or 1

    def P(x, y, s):
        off = bulge(x, y) if bulge else 0.0
        return o + xa * x + ya * y + na * (off + s * depth * 0.5)
    front = [bm.verts.new(P(x, y, 1)) for x, y in outline]
    back = [bm.verts.new(P(x, y, -1)) for x, y in outline]
    faces = [bm.faces.new(front), bm.faces.new(list(reversed(back)))]
    n = len(outline)
    for i in range(n):
        j = (i + 1) % n
        faces.append(bm.faces.new((front[j], front[i], back[i], back[j])))
    for f in faces:
        for loop in f.loops:
            lo = loop.vert.co - o
            loop[uvl].uv = ((lo.dot(xa) - min(xs)) / w, (lo.dot(ya) - min(ys)) / h)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    obj = bm_object(name, bm, mats, smooth=False)
    if bev:
        mod = obj.modifiers.new("Bevel", "BEVEL")
        mod.width = bev
        mod.segments = bev_seg
        mod.limit_method = "ANGLE"
        mod.angle_limit = math.radians(30)
        mod.harden_normals = False
    if sub:
        subsurf(obj, sub)
    if bev or sub:
        apply_all(obj)
    obj.data.polygons.foreach_set("use_smooth", [True] * len(obj.data.polygons))
    auto_smooth(obj)
    return obj


def auto_smooth(obj, angle=35):
    """按角度拆分法线，硬边保持锐利、弧面保持平滑（Blender 5 用“Smooth by Angle”等效实现）。"""
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    sharp = [e for e in bm.edges if e.is_manifold and e.calc_face_angle(0) > math.radians(angle)]
    if sharp:
        bmesh.ops.split_edges(bm, edges=sharp)
    bm.to_mesh(obj.data)
    bm.free()
    obj.data.polygons.foreach_set("use_smooth", [True] * len(obj.data.polygons))
    return obj


def spike(name, base, tip, radius, mats, sides=6, fx=1.0, fy=1.0, up=(0, 0, 1), bend=0.0, per=1):
    """尖刺 / 角：从 base 到 tip 的锥管，bend 使中段沿 up 方向弯出弧度。"""
    b, t = Vector(base), Vector(tip)
    mid = b.lerp(t, 0.5) + Vector(up).normalized() * bend
    pts = [b, b.lerp(mid, 0.5), mid, mid.lerp(t, 0.5), t] if bend else [b, t]
    rads = [radius, radius * 0.82, radius * 0.6, radius * 0.32, 0.0] if bend else [radius, 0.0]
    return tube(name, pts, rads, mats, n=sides, fx=fx, fy=fy, up=up, per=per if not bend else 3)


def mirror_copy(obj, name=None):
    """沿 X 镜像复制（翻转法线），用于左右对称部件。"""
    me = obj.data.copy()
    me.transform(Matrix.Scale(-1, 4, (1, 0, 0)))
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.reverse_faces(bm, faces=bm.faces[:])
    bm.to_mesh(me)
    bm.free()
    new = bpy.data.objects.new(name or obj.name + " mirror", me)
    return link(new)


def join(objs, name, location=None):
    objs = [o for o in objs if o is not None]
    bpy.ops.object.select_all(action="DESELECT")
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    if len(objs) > 1:
        bpy.ops.object.join()
    obj = objs[0]
    obj.name = name
    if location is not None:
        me = obj.data
        me.transform(Matrix.Translation(-Vector(location)))
        obj.location = location
    return obj


def projector(obj, direction=(0, -1, 0), start=1.5):
    """沿 direction 把点投射到网格表面：project(p, lift) 从 p - direction*start 发射射线。"""
    bvh = BVHTree.FromObject(obj, bpy.context.evaluated_depsgraph_get())
    d = Vector(direction).normalized()

    def project(p, lift=0.0):
        p = Vector(p)
        loc, nrm, _, _ = bvh.ray_cast(p - d * start, d)
        if loc is None:
            return p
        if nrm.dot(d) > 0:
            nrm = -nrm
        return loc + nrm * lift
    return project


def ring_points(center, normal, radius, count, phase=0.0):
    n = Vector(normal).normalized()
    a = n.orthogonal().normalized()
    b = n.cross(a)
    c = Vector(center)
    return [c + (a * math.cos(phase + i / count * TAU) + b * math.sin(phase + i / count * TAU)) * radius
            for i in range(count)]


def trim(name, points, radius, mat, closed=False, n=6, per=1):
    """沿点列的滚边 / 嵌线（细管）。"""
    return tube(name, points, [radius] * len(points), [mat], n=n, closed=closed, per=per)


def gem(name, center, size, mat, stretch=(1.0, 0.6, 1.4)):
    s = size
    return ellipsoid(name, center, (s * stretch[0], s * stretch[1], s * stretch[2]), [mat], 12, 8)


def edge_trim(ctx, obj, radius, mat, spec, lift=0.004, center_y=0.0, min_len=6, name=None):
    """给网格所有边界环加滚边（沿水平径向外推 lift）。"""
    for k, loop in enumerate(boundary_loops(obj)):
        if len(loop) < min_len:
            continue
        pts = [radial(p, lift, center_y) for p in loop]
        closed = (loop[0] - loop[-1]).length < radius * 6
        ctx.part(trim(f"{name or obj.name} trim {k}", pts, radius, mat, closed=closed), spec)


# ===== 程序化贴图（numpy，第 0 行为图像底边） =====
def _finish(mask, fade, rng, emit_rgb, base_rgb, line_rgb, glow_halo=0.45, bump=2.0, sparkle=True):
    halo = box_blur(mask, 5)
    glow = np.clip(mask + halo * glow_halo, 0, 1.3) * (0.10 + 0.90 * fade)
    em = np.stack([glow * c for c in emit_rgb], axis=2)
    if sparkle:
        sp = (rng.random(mask.shape) > 0.99972).astype(np.float32) * rng.uniform(0.2, 0.8, mask.shape)
        sp = box_blur(sp, 1) * 5.0 * (0.3 + 0.7 * fade)
        em += np.stack([sp * (0.6 + 0.4 * c) for c in emit_rgb], axis=2)
    grain = box_blur(rng.random(mask.shape).astype(np.float32), 24) - 0.5
    tone = 1.0 + grain * 3.0
    base = np.stack([base_rgb[i] * tone for i in range(3)], axis=2)
    base += mask[..., None] * np.array(line_rgb)[None, None, :] * (0.35 + 0.65 * fade[..., None])
    return np.clip(base, 0, 1), np.clip(em, 0, 1), height_normal(box_blur(mask, 1), bump)


def height_normal(height, strength=2.0):
    gy, gx = np.gradient(height)
    nrm = np.stack([-gx * strength, -gy * strength, np.ones_like(gx)], axis=2)
    nrm /= np.linalg.norm(nrm, axis=2, keepdims=True)
    return nrm * 0.5 + 0.5


def vfade(h, w, start=0.15, span=0.65, power=1.3, invert=False):
    v = np.linspace(0, 1, h)[:, None]
    f = 1.0 - np.clip((v - start) / span, 0, 1) ** power
    if invert:
        f = f[::-1]
    return np.ascontiguousarray(np.broadcast_to(f, (h, w)))


def circuit_maps(emit_rgb, base_rgb=(0.010, 0.008, 0.016), line_rgb=None, size=2048, seed=11, buses=15,
                 reach=(0.38, 0.95), fade=True):
    """尼克斯同款织物电路：成组平行总线自下而上生长，45° 折线，过孔收尾；颜色可换。"""
    rng = np.random.default_rng(seed)
    cv = Canvas(size, size)
    for x in np.linspace(40, size - 140, buses) + rng.uniform(-30, 30, buses):
        pcb_bus(cv, rng, float(x), rng.uniform(*reach) * size, int(rng.choice([2, 3, 3, 4])),
                float(rng.choice([11, 13, 15])), int(rng.choice([2, 2, 3])))
    for _ in range(10):
        pcb_bus(cv, rng, float(rng.uniform(20, size - 40)), rng.uniform(0.15, 0.35) * size, 1, 12, 2)
    mask = np.clip(cv.mask, 0, 1)
    f = vfade(size, size) if fade else np.ones_like(mask)
    line_rgb = line_rgb or tuple(c * 0.13 for c in emit_rgb)
    return _finish(mask, f, rng, emit_rgb, base_rgb, line_rgb)


def filigree_maps(base_rgb, groove_rgb, emit_rgb=None, size=1024, seed=3, density=9, width=2):
    """金属雕花：成对卷草涡线 + 边框细线；沟槽压暗并做法线凹陷，可选沟槽发光。"""
    rng = np.random.default_rng(seed)
    cv = Canvas(size, size)
    cell = size / density
    for gx in range(density):
        for gy in range(density):
            cx, cy = (gx + 0.5) * cell, (gy + 0.5) * cell
            flip = 1 if (gx + gy) % 2 else -1
            turns = rng.uniform(1.1, 1.6)
            t = np.linspace(0, turns * TAU, 90)
            r = cell * 0.46 * np.exp(-0.22 * t)
            xs = cx + flip * r * np.cos(t + rng.uniform(0, TAU))
            ys = cy + r * np.sin(t)
            for i in range(len(t) - 1):
                cv.line(xs[i], ys[i], xs[i + 1], ys[i + 1], width)
            leaf = rng.uniform(0, TAU)
            cv.line(cx, cy, cx + math.cos(leaf) * cell * 0.3, cy + math.sin(leaf) * cell * 0.3, max(1, width - 1))
    for k in range(0, size, int(cell * 3)):
        cv.line(0, k + 3, size, k + 3, 1)
    mask = np.clip(box_blur(cv.mask, 1) * 1.4, 0, 1)
    grain = box_blur(rng.random(mask.shape).astype(np.float32), 18) - 0.5
    tone = 1.0 + grain * 0.8
    base = np.stack([base_rgb[i] * tone * (1 - mask) + groove_rgb[i] * mask for i in range(3)], axis=2)
    em = None
    if emit_rgb:
        em = np.stack([mask * c for c in emit_rgb], axis=2)
    return np.clip(base, 0, 1), em, height_normal(-mask, 1.6)


def voronoi(size, cells, rng):
    """抖动网格 Voronoi：返回 F1、F2 距离（以单元尺寸归一化）和单元编号。"""
    pts = rng.random((cells, cells, 2))
    ys, xs = np.mgrid[0:size, 0:size].astype(np.float32) / size * cells
    ix, iy = np.floor(xs).astype(int), np.floor(ys).astype(int)
    f1 = np.full((size, size), 9.0, np.float32)
    f2 = np.full((size, size), 9.0, np.float32)
    idx = np.zeros((size, size), np.int32)
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            cx, cy = (ix + dx) % cells, (iy + dy) % cells
            px = ix + dx + pts[cy, cx, 0]
            py = iy + dy + pts[cy, cx, 1]
            d = np.sqrt((xs - px) ** 2 + (ys - py) ** 2)
            closer = d < f1
            f2 = np.where(closer, f1, np.minimum(f2, d))
            idx = np.where(closer, cy * cells + cx, idx)
            f1 = np.where(closer, d, f1)
    return f1, f2, idx


def crack_maps(emit_rgb, base_rgb=(0.030, 0.022, 0.020), size=1024, seed=7, cells=10, width=0.06, heat=1.0):
    """熔岩 / 余烬裂纹：Voronoi 边界发光，裂纹附近底色烧红，块面微凸。"""
    rng = np.random.default_rng(seed)
    f1, f2, idx = voronoi(size, cells, rng)
    edge = f2 - f1
    crack = np.clip(1 - edge / width, 0, 1) ** 2
    fine_f1, fine_f2, _ = voronoi(size, cells * 3, rng)
    crack = np.maximum(crack, np.clip(1 - (fine_f2 - fine_f1) / (width * 0.5), 0, 1) ** 3 * 0.45)
    ember = box_blur(crack, 6)
    em = np.stack([np.clip(crack + ember * 0.5, 0, 1) * c * heat for c in emit_rgb], axis=2)
    cellv = (np.sin(idx * 1.7) * 0.5 + 0.5)[..., None]
    base = np.array(base_rgb)[None, None, :] * (0.7 + 0.6 * cellv)
    base += ember[..., None] * np.array(emit_rgb)[None, None, :] * 0.12
    return np.clip(base, 0, 1), np.clip(em, 0, 1), height_normal(np.clip(f1 * 0.6, 0, 1) - crack, 3.0)


def scale_maps(base_rgb, edge_rgb, emit_rgb=None, size=1024, seed=5, rows=14):
    """鳞片：错位半圆鳞，边缘高光色 + 法线凸起；可选鳞缝发光。"""
    ys, xs = np.mgrid[0:size, 0:size].astype(np.float32) / size
    r = 1.0 / rows
    row = np.floor(ys / (r * 0.75))
    xo = xs + (row % 2) * r * 0.5
    cx = (np.floor(xo / r) + 0.5) * r
    cy = row * r * 0.75
    d = np.sqrt(((xo - cx) / r) ** 2 + ((ys - cy) / r) ** 2)
    inside = (ys >= cy) & (d < 0.62)
    hgt = np.where(inside, 1 - d / 0.62, 0) ** 0.6
    rim = np.clip(1 - np.abs(d - 0.55) / 0.08, 0, 1) * inside
    base = np.stack([base_rgb[i] * (0.6 + 0.4 * hgt) + edge_rgb[i] * rim * 0.6 for i in range(3)], axis=2)
    em = np.stack([rim * c * 0.6 for c in emit_rgb], axis=2) if emit_rgb else None
    return np.clip(base, 0, 1), em, height_normal(box_blur(hgt.astype(np.float32), 1), 4.0)


def frost_maps(emit_rgb, base_rgb=(0.60, 0.72, 0.80), size=1024, seed=9, branches=46):
    """霜花：随机分叉的枝晶线（60° 分支），浅色底上发冷光。"""
    rng = np.random.default_rng(seed)
    cv = Canvas(size, size)

    def grow(x, y, a, length, w, depth):
        if depth > 3 or length < 8:
            return
        steps = int(length / 6)
        for _ in range(steps):
            nx, ny = x + math.cos(a) * 6, y + math.sin(a) * 6
            cv.line(x, y, nx, ny, w)
            x, y = nx, ny
            if rng.random() < 0.18:
                side = rng.choice([-1, 1])
                grow(x, y, a + side * math.pi / 3, length * 0.45, max(1, w - 1), depth + 1)
    for _ in range(branches):
        grow(rng.uniform(0, size), rng.uniform(0, size), rng.uniform(0, TAU), rng.uniform(60, 220), 2, 0)
    mask = np.clip(cv.mask, 0, 1)
    halo = box_blur(mask, 4)
    em = np.stack([np.clip(mask * 0.8 + halo * 0.5, 0, 1) * c for c in emit_rgb], axis=2)
    grain = box_blur(rng.random(mask.shape).astype(np.float32), 12) - 0.5
    base = np.stack([base_rgb[i] * (1 + grain * 0.5) + mask * 0.25 for i in range(3)], axis=2)
    return np.clip(base, 0, 1), np.clip(em, 0, 1), height_normal(box_blur(mask, 1), 1.2)


GLYPHS = [
    [(0, 0, 0, 1), (0, 1, 1, 1), (1, 1, 1, 0.5)], [(0.5, 0, 0.5, 1), (0, 0.5, 1, 0.5)],
    [(0, 0, 1, 1), (0, 1, 1, 0)], [(0, 1, 0.5, 0), (0.5, 0, 1, 1), (0.25, 0.5, 0.75, 0.5)],
    [(0, 0, 0, 1), (1, 0, 1, 1), (0, 0.5, 1, 0.5)], [(0.5, 0, 0.5, 1), (0, 0.7, 1, 0.7), (0, 0.3, 1, 0.3)],
    [(0, 0, 1, 0), (1, 0, 0.5, 1), (0.5, 1, 0, 0)], [(0, 1, 1, 1), (0.5, 1, 0.5, 0), (0.2, 0.2, 0.8, 0.2)],
]


def rune_maps(emit_rgb, base_rgb=(0.02, 0.018, 0.022), line_rgb=None, size=1024, seed=13, rows=6, cols=10):
    """符文带：成行的几何字形 + 上下边线，适合旗帜、祭坛、刃面铭文。"""
    rng = np.random.default_rng(seed)
    cv = Canvas(size, size)
    ch, cw = size / rows, size / cols
    for r in range(rows):
        y0 = r * ch
        cv.line(0, y0 + ch * 0.12, size, y0 + ch * 0.12, 1)
        cv.line(0, y0 + ch * 0.88, size, y0 + ch * 0.88, 1)
        for c in range(cols):
            g = GLYPHS[int(rng.integers(len(GLYPHS)))]
            x0, gy0, s = c * cw + cw * 0.22, y0 + ch * 0.25, min(cw, ch) * 0.5
            for (a, b, cc, d) in g:
                cv.line(x0 + a * s, gy0 + b * s, x0 + cc * s, gy0 + d * s, 2)
    mask = np.clip(cv.mask, 0, 1)
    line_rgb = line_rgb or tuple(c * 0.15 for c in emit_rgb)
    return _finish(mask, np.ones_like(mask), rng, emit_rgb, base_rgb, line_rgb, sparkle=False)


def hex_maps(emit_rgb, base_rgb=(0.02, 0.02, 0.025), size=1024, cells=16, width=0.05, seed=17):
    """六边形能量网格（护盾、机械核心、翼膜）。"""
    ys, xs = np.mgrid[0:size, 0:size].astype(np.float32) / size * cells
    q = xs * 2 / 3
    r = -xs / 3 + math.sqrt(3) / 3 * ys
    def hex_round(q, r):
        x, z = q, r
        y = -x - z
        rx, ry, rz = np.round(x), np.round(y), np.round(z)
        dx, dy, dz = np.abs(rx - x), np.abs(ry - y), np.abs(rz - z)
        rx = np.where((dx > dy) & (dx > dz), -ry - rz, rx)
        rz = np.where(~((dx > dy) & (dx > dz)) & ~(dy > dz), -rx - ry, rz)
        return rx, rz
    hq, hr = hex_round(q, r)
    cx = hq * 1.5
    cy = (hr + hq / 2) * math.sqrt(3)
    d = np.maximum.reduce([np.abs(xs - cx) * 0.866 + np.abs(ys - cy) * 0.5, np.abs(ys - cy)])
    edge = np.clip(1 - (0.866 - d) / width, 0, 1)
    rng = np.random.default_rng(seed)
    return _finish(edge.astype(np.float32), np.ones_like(edge), rng, emit_rgb, base_rgb,
                   tuple(c * 0.1 for c in emit_rgb), sparkle=False)
