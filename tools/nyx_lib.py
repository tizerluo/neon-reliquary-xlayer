"""NYX 构建脚本的通用工具：数学、网格生成、材质与程序化贴图。

由 tools/build_nyx.py 在 Blender 5.2 内加载，不单独运行。
"""

from pathlib import Path
import math

import bmesh
import bpy
import numpy as np
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
TEX_DIR = ROOT / "art" / "nyx-textures"
TEX_DIR.mkdir(parents=True, exist_ok=True)
TAU = math.tau
VIOLET = (0.56, 0.30, 1.0)


# ===== 数学 =====
def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def lerp(a, b, t):
    return a + (b - a) * t


def smoothstep(a, b, x):
    t = clamp((x - a) / (b - a))
    return t * t * (3 - 2 * t)


def interp(knots, x):
    """分段线性插值；knots 为按 x 排序的 (x, y) 或 (x, (y1, y2, ...))。"""
    if x <= knots[0][0]:
        return knots[0][1]
    for (x0, y0), (x1, y1) in zip(knots, knots[1:]):
        if x <= x1:
            t = (x - x0) / (x1 - x0)
            if isinstance(y0, tuple):
                return tuple(lerp(a, b, t) for a, b in zip(y0, y1))
            return lerp(y0, y1, t)
    return knots[-1][1]


def catmull(points, radii, per=6):
    """Catmull-Rom 细分折线，半径同步线性插值，使管道平滑。"""
    pts = [Vector(p) for p in points]
    out_p, out_r = [], []
    n = len(pts)
    for i in range(n - 1):
        p0, p1, p2 = pts[max(i - 1, 0)], pts[i], pts[i + 1]
        p3 = pts[min(i + 2, n - 1)]
        for s in range(per):
            t = s / per
            t2, t3 = t * t, t * t * t
            p = 0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2
                       + (-p0 + 3 * p1 - 3 * p2 + p3) * t3)
            out_p.append(p)
            out_r.append(lerp(radii[i], radii[i + 1], t))
    out_p.append(pts[-1])
    out_r.append(radii[-1])
    return out_p, out_r


# ===== 对象与修改器 =====
def link(obj, parent=None):
    bpy.context.scene.collection.objects.link(obj)
    if parent:
        obj.parent = parent
    return obj


def bm_object(name, bm, mats, smooth=True):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for m in mats:
        me.materials.append(m)
    if smooth:
        me.polygons.foreach_set("use_smooth", [True] * len(me.polygons))
    return link(bpy.data.objects.new(name, me))


def apply_all(obj):
    """用求值后的网格替换原网格，等效于依次应用全部修改器。"""
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(obj.evaluated_get(dg), preserve_all_data_layers=True,
                                         depsgraph=dg)
    old = obj.data
    obj.modifiers.clear()
    obj.data = me
    bpy.data.meshes.remove(old)
    return obj


def solidify(obj, thickness, offset=-1.0, inner_offset=0, rim_offset=0):
    mod = obj.modifiers.new("Solidify", "SOLIDIFY")
    mod.thickness = thickness
    mod.offset = offset
    mod.use_even_offset = True
    mod.use_quality_normals = True
    mod.material_offset = inner_offset
    mod.material_offset_rim = rim_offset
    return mod


def subsurf(obj, levels=2):
    mod = obj.modifiers.new("Subdivision", "SUBSURF")
    mod.levels = levels
    mod.render_levels = levels
    return mod


def bevel(obj, width, segments=3, angle=35):
    mod = obj.modifiers.new("Bevel", "BEVEL")
    mod.width = width
    mod.segments = segments
    mod.limit_method = "ANGLE"
    mod.angle_limit = math.radians(angle)
    mod.harden_normals = False
    return mod


# ===== 网格生成 =====
def surface(name, fn, nu, nv, mats, closed_u=False, uvfn=None):
    """参数曲面：fn(u, v) -> Vector，u 横向、v 纵向（v 增大向下时法线朝外）。"""
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.new("UVMap")
    du = nu if closed_u else nu - 1
    rows = [[bm.verts.new(fn(i / du, j / (nv - 1))) for i in range(nu)] for j in range(nv)]
    for j in range(nv - 1):
        for i in range(nu if closed_u else nu - 1):
            i2 = (i + 1) % nu
            try:
                face = bm.faces.new((rows[j][i], rows[j][i2], rows[j + 1][i2], rows[j + 1][i]))
            except ValueError:
                continue
            for loop, (ii, jj) in zip(face.loops, ((i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1))):
                u, v = ii / du, jj / (nv - 1)
                loop[uvl].uv = uvfn(u, v) if uvfn else (u, 1 - v)
    return bm_object(name, bm, mats)


def tube(name, points, radii, mats, n=12, fx=1.0, fy=1.0, up=(0, 0, 1), closed=False,
         cap=True, per=6, twist=0.0):
    """沿折线放样的管道（平行传输标架），首尾半径为 0 时收成尖点。"""
    pts, rad = catmull(points, radii, per) if per > 1 else ([Vector(p) for p in points], list(radii))
    m = len(pts)
    if closed and (pts[0] - pts[-1]).length < 1e-6:
        pts, rad, m = pts[:-1], rad[:-1], m - 1
    tangents = []
    for i in range(m):
        if closed:
            d = pts[(i + 1) % m] - pts[i - 1]
        else:
            d = pts[min(i + 1, m - 1)] - pts[max(i - 1, 0)]
        tangents.append(d.normalized())
    upv = Vector(up)
    n0 = upv - tangents[0] * upv.dot(tangents[0])
    if n0.length < 1e-5:
        n0 = Vector((1, 0, 0)) - tangents[0] * tangents[0].x
    normals = [n0.normalized()]
    for i in range(1, m):
        nn = normals[-1] - tangents[i] * normals[-1].dot(tangents[i])
        normals.append(nn.normalized() if nn.length > 1e-6 else normals[-1])
    bm = bmesh.new()
    rings = []
    for i in range(m):
        if rad[i] <= 1e-6 and not closed and i in (0, m - 1):
            rings.append([bm.verts.new(pts[i])])
            continue
        b = tangents[i].cross(normals[i])
        ring = []
        for k in range(n):
            a = TAU * k / n + twist
            ring.append(bm.verts.new(pts[i] + normals[i] * (math.cos(a) * rad[i] * fx)
                                     + b * (math.sin(a) * rad[i] * fy)))
        rings.append(ring)
    segs = m if closed else m - 1
    for i in range(segs):
        ra, rb = rings[i], rings[(i + 1) % m]
        for k in range(n):
            k2 = (k + 1) % n
            try:
                if len(ra) == 1:
                    bm.faces.new((ra[0], rb[k2], rb[k]))
                elif len(rb) == 1:
                    bm.faces.new((ra[k], ra[k2], rb[0]))
                else:
                    bm.faces.new((ra[k], ra[k2], rb[k2], rb[k]))
            except ValueError:
                pass
            if len(ra) == 1 or len(rb) == 1:
                continue
    if cap and not closed:
        for ring in (rings[0], rings[-1]):
            if len(ring) > 2:
                try:
                    bm.faces.new(ring)
                except ValueError:
                    pass
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return bm_object(name, bm, mats)


def ellipsoid(name, center, radii, mats, segments=32, rings=20):
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=segments, v_segments=rings, radius=1.0)
    for v in bm.verts:
        v.co = Vector((v.co.x * radii[0], v.co.y * radii[1], v.co.z * radii[2])) + Vector(center)
    return bm_object(name, bm, mats)


def boundary_loops(obj):
    """返回网格边界边组成的有序顶点坐标环（用于生成滚边）。"""
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    edges = [e for e in bm.edges if e.is_boundary]
    adj = {}
    for e in edges:
        a, b = e.verts
        adj.setdefault(a.index, []).append(b.index)
        adj.setdefault(b.index, []).append(a.index)
    coords = {v.index: obj.matrix_world @ v.co.copy() for v in bm.verts}
    seen, loops = set(), []
    for start in adj:
        if start in seen:
            continue
        loop, prev, cur = [start], None, start
        seen.add(start)
        while True:
            nxt = [x for x in adj[cur] if x != prev and x not in seen]
            if not nxt:
                break
            prev, cur = cur, nxt[0]
            loop.append(cur)
            seen.add(cur)
        loops.append([coords[i] for i in loop])
    bm.free()
    return loops


# ===== 材质 =====
def material(name, base, metal=0.0, rough=0.5, emit=None, strength=0.0, coat=0.0,
             coat_rough=0.05, sheen=0.0, sheen_tint=(1, 1, 1), spec=0.5):
    m = bpy.data.materials.new(name)
    try:
        m.use_nodes = True
    except AttributeError:
        pass
    p = m.node_tree.nodes["Principled BSDF"]

    def put(key, value):
        if key in p.inputs:
            p.inputs[key].default_value = value

    put("Base Color", (*base, 1))
    put("Metallic", metal)
    put("Roughness", rough)
    put("Specular IOR Level", spec)
    if emit:
        put("Emission Color", (*emit, 1))
        put("Emission Strength", strength)
    if coat:
        put("Coat Weight", coat)
        put("Coat Roughness", coat_rough)
    if sheen:
        put("Sheen Weight", sheen)
        put("Sheen Tint", (*sheen_tint, 1))
        put("Sheen Roughness", 0.42)
    m.diffuse_color = (*base, 1)
    return m


def attach_texture(m, image, socket, strength=1.0):
    nt = m.node_tree
    p = nt.nodes["Principled BSDF"]
    node = nt.nodes.new("ShaderNodeTexImage")
    node.image = image
    if socket == "Normal":
        nm = nt.nodes.new("ShaderNodeNormalMap")
        nm.inputs["Strength"].default_value = strength
        nt.links.new(node.outputs["Color"], nm.inputs["Color"])
        nt.links.new(nm.outputs["Normal"], p.inputs["Normal"])
    else:
        nt.links.new(node.outputs["Color"], p.inputs[socket])
    return node


def image_from_array(name, arr, noncolor=False):
    """numpy (H, W, 3) 0..1 数组 → 打包进 .blend 的 PNG 贴图；第 0 行是图像底边。"""
    h, w = arr.shape[:2]
    rgba = np.concatenate([arr.astype(np.float32), np.ones((h, w, 1), np.float32)], axis=2)
    img = bpy.data.images.new(name, width=w, height=h, alpha=False)
    img.colorspace_settings.name = "Non-Color" if noncolor else "sRGB"
    img.pixels.foreach_set(rgba.ravel())
    img.filepath_raw = str(TEX_DIR / (name.lower().replace(" ", "-") + ".png"))
    img.file_format = "PNG"
    img.save()
    img.pack()
    return img


# ===== 程序化电路织物贴图 =====
def _box_blur(a, r):
    """分离式盒式模糊（两次近似高斯）。"""
    for _ in range(2):
        for axis in (0, 1):
            c = np.cumsum(np.pad(a, [(r + 1, r) if i == axis else (0, 0) for i in range(2)],
                                 mode="edge"), axis=axis)
            if axis == 0:
                a = (c[2 * r + 1:] - c[:-2 * r - 1]) / (2 * r + 1)
            else:
                a = (c[:, 2 * r + 1:] - c[:, :-2 * r - 1]) / (2 * r + 1)
    return a


class Canvas:
    """numpy 位图画笔：线段、圆环、实心圆与矩形框，全部写入同一张遮罩。"""

    def __init__(self, width, height):
        self.w, self.h = width, height
        self.mask = np.zeros((height, width), np.float32)

    def _stamp(self, xs, ys, w):
        for dx in range(-w, w + 1):
            for dy in range(-w, w + 1):
                if dx * dx + dy * dy <= w * w + 1:
                    xi = np.clip(np.round(xs + dx).astype(int), 0, self.w - 1)
                    yi = np.clip(np.round(ys + dy).astype(int), 0, self.h - 1)
                    self.mask[yi, xi] = 1.0

    def line(self, x0, y0, x1, y1, w=2):
        n = int(max(abs(x1 - x0), abs(y1 - y0)) * 1.5) + 2
        self._stamp(np.linspace(x0, x1, n), np.linspace(y0, y1, n), w)

    def ring(self, x, y, rad, w=1):
        t = np.linspace(0, TAU, int(rad * 8) + 16)
        self._stamp(x + np.cos(t) * rad, y + np.sin(t) * rad, w)

    def dot(self, x, y, rad):
        self._stamp(np.array([x]), np.array([y]), int(rad))

    def rect(self, x, y, w, h, lw=1):
        self.line(x, y, x + w, y, lw)
        self.line(x + w, y, x + w, y + h, lw)
        self.line(x + w, y + h, x, y + h, lw)
        self.line(x, y + h, x, y, lw)


def pcb_bus(cv, rng, x, reach, lanes, pitch, w, clip_x=None):
    """一组平行走线从底边向上：同步 45° 折线，末端交错收在过孔或焊盘上。"""
    lo, hi = clip_x or (8, cv.w - 8)
    xs = [x + i * pitch for i in range(lanes)]
    y = 0.0
    ends = sorted(rng.uniform(0.55, 1.0, lanes) * reach, reverse=rng.random() < 0.5)
    while y < max(ends):
        run = rng.uniform(cv.h * 0.035, cv.h * 0.09)
        jog = rng.random() < 0.42
        shift = rng.choice([-1, 1]) * rng.uniform(pitch * 1.5, pitch * 4.5) if jog else 0.0
        if min(xs) + shift < lo or max(xs) + shift > hi:
            shift = -shift
        for i in range(lanes):
            if y >= ends[i]:
                continue
            top = min(y + run, ends[i])
            cv.line(xs[i], y, xs[i], top, w)
            if jog and top < ends[i]:
                cv.line(xs[i], top, xs[i] + shift, top + abs(shift), w)
        y += run + (abs(shift) if jog else 0)
        if jog:
            xs = [v + shift for v in xs]
    for i in range(lanes):
        ex = xs[i]
        ey = min(ends[i], cv.h - 12)
        if rng.random() < 0.7:
            cv.ring(ex, ey, w * 2.2 + 3, 1)
        else:
            cv.rect(ex - 6, ey, 12, 8 + w * 2, 1)
    if rng.random() < 0.5:
        by = rng.uniform(0.25, 0.6) * min(ends)
        bx = xs[-1] + rng.choice([1, -1]) * rng.uniform(40, 110)
        bx = float(np.clip(bx, lo, hi))
        cv.line(xs[-1], by, bx, by + abs(bx - xs[-1]), max(1, w - 1))
        cv.ring(bx, by + abs(bx - xs[-1]), 5, 1)


def finish_maps(mask, fade, rng, base_rgb=(0.010, 0.007, 0.018), line_rgb=(0.07, 0.045, 0.13)):
    """由电路遮罩合成底色、自发光和微凸法线。"""
    size_y, size_x = mask.shape
    halo = _box_blur(mask, 5)
    glow = np.clip(mask + halo * 0.45, 0, 1.3) * (0.10 + 0.90 * fade)
    sparkle = (rng.random(mask.shape) > 0.99972).astype(np.float32) * rng.uniform(0.2, 0.8, mask.shape)
    sparkle = _box_blur(sparkle, 1) * 5.0 * (0.3 + 0.7 * fade)
    emission = np.stack([glow * VIOLET[0] + sparkle * 0.75, glow * VIOLET[1] + sparkle * 0.65,
                         glow * VIOLET[2] + sparkle], axis=2)
    grain = _box_blur(rng.random(mask.shape).astype(np.float32), 24) - 0.5   # 低频明暗起伏，利于压缩
    tone = 1.0 + grain * 3.0
    base = np.stack([base_rgb[0] * tone, base_rgb[1] * tone, base_rgb[2] * tone], axis=2)
    base += mask[..., None] * np.array(line_rgb)[None, None, :] * (0.35 + 0.65 * fade[..., None])
    height = _box_blur(mask, 1)
    gy, gx = np.gradient(height)
    nrm = np.stack([-gx * 2.0, -gy * 2.0, np.ones_like(gx)], axis=2)
    nrm /= np.linalg.norm(nrm, axis=2, keepdims=True)
    return np.clip(base, 0, 1), np.clip(emission, 0, 1), nrm * 0.5 + 0.5


def tabard_maps(width=512, height=2048, seed=5):
    """中央垂饰的对称电路：三线主干 + 向下的人字分支，越往上越淡。"""
    rng = np.random.default_rng(seed)
    cv = Canvas(width, height)
    cx = width / 2
    for dx in (-10, 0, 10):
        cv.line(cx + dx, 0, cx + dx, height * 0.82, 2)
    y = height * 0.06
    while y < height * 0.78:
        span = rng.uniform(width * 0.18, width * 0.40)
        for sgn in (-1, 1):
            x0 = cx + sgn * 14
            x1 = cx + sgn * span
            elbow_y = y + span * 0.6 - (span - 14)
            end_y = max(6, elbow_y - rng.uniform(30, 90))
            cv.line(x0, y + span * 0.6, x1, elbow_y, 2)
            cv.line(x1, elbow_y, x1, end_y, 2)
            cv.ring(x1, end_y, 6, 1)
        cv.dot(cx, y + span * 0.6, 5)
        y += rng.uniform(height * 0.07, height * 0.12)
    cv.ring(cx, height * 0.82 + 10, 9, 2)
    v = np.linspace(0, 1, height)[:, None]
    fade = np.broadcast_to(1.0 - np.clip((v - 0.2) / 0.7, 0, 1) ** 1.2, cv.mask.shape)
    return finish_maps(np.clip(cv.mask, 0, 1), np.ascontiguousarray(fade), rng)


def circuit_cloth_maps(size=2048, seed=11, buses=15, reach=(0.38, 0.95)):
    """织物电路：成组平行总线从下摆（v=0）向上生长，45° 折线，过孔与焊盘收尾。"""
    rng = np.random.default_rng(seed)
    cv = Canvas(size, size)
    slots = np.linspace(40, size - 140, buses) + rng.uniform(-30, 30, buses)
    for x in slots:
        pcb_bus(cv, rng, float(x), rng.uniform(*reach) * size, int(rng.choice([2, 3, 3, 4])),
                float(rng.choice([11, 13, 15])), int(rng.choice([2, 2, 3])))
    for _ in range(10):
        pcb_bus(cv, rng, float(rng.uniform(20, size - 40)), rng.uniform(0.15, 0.35) * size, 1, 12, 2)
    mask = np.clip(cv.mask, 0, 1)
    v = np.linspace(0, 1, size)[:, None]
    fade = np.broadcast_to(1.0 - np.clip((v - 0.15) / 0.65, 0, 1) ** 1.3, mask.shape)
    return finish_maps(mask, np.ascontiguousarray(fade), rng)
