"""场地通用构建工具（区域无关）：网格构建器、材质、场景装配、GLB 导出与补丁、散布工具、预算检查。

坐标约定（全部写在“游戏 / glTF 坐标”里，与最终 GLB 一致）：
    Y 向上；+X 东（屏幕右）；+Z 南（屏幕下方、靠近镜头）；−Z 北（屏幕上方）；原点 = 场地中心，地面 y = 0。
转成 Blender（Z 向上）时 (x, y, z)_game → (x, −z, y)_blender，是一个纯旋转，绕序不变；导出器再转回 Y 向上。

区域配方（tools/arenas/<区域>.py）只需要提供：材质表 SPECS、四个构建函数、审图用的少量参数；
网格构建、贴图 / 材质接线、导出、校验、审图渲染都在这里和 review.py / verify.py 里复用。
"""

import json
import math
import random
import struct
import sys
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path

import bpy
import numpy as np

TOOLS = Path(__file__).resolve().parents[1]
ROOT = TOOLS.parent
sys.path.insert(0, str(TOOLS))

from arenas import textures as T  # noqa: E402

# ===== 场地规格（四个区域共用）=====
PLAY_X, PLAY_Z = 44.0, 40.0           # 可活动区域半宽 / 半深
FLOOR_X, FLOOR_Z = 70.0, 66.0         # 地面覆盖范围
CLEAN_R = 18.0                        # 场内道具的“中心空地”半径
PROP_MAX_H = 0.6
SOUTH_MAX_H = 2.0                     # +Z 侧（z > 40）所有东西的最大高度
RAIL_MAX_H = 1.5
LIMITS = dict(tris=150000, prims=40, meshes=40, mats=12, tex=1024, bytes=12 * 1024 * 1024, emit=2.5, shaft_emit=1.5)


# ===== 颜色 =====
def lin(hexcolor):
    h = hexcolor.lstrip("#")
    return tuple(float(T.srgb_to_lin(int(h[i:i + 2], 16) / 255)) for i in (0, 2, 4))


# =====================================================================
# 网格构建器（numpy 顶点表 + 面表，Y 向上）
# =====================================================================
def rot_x(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[1, 0, 0], [0, c, -s], [0, s, c]])


def rot_y(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])


def rot_z(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])


def _newell(P):
    n = np.zeros(3)
    for i in range(len(P)):
        a, b = P[i], P[(i + 1) % len(P)]
        n[0] += (a[1] - b[1]) * (a[2] + b[2])
        n[1] += (a[2] - b[2]) * (a[0] + b[0])
        n[2] += (a[0] - b[0]) * (a[1] + b[1])
    return n


def orient(V, faces, ref):
    """按“内部参考点”把每个面的法线朝外（凸体用）。"""
    ref = np.asarray(ref, dtype=float)
    out = []
    for f in faces:
        P = V[list(f)]
        n = _newell(P)
        if np.dot(n, P.mean(axis=0) - ref) < 0:
            f = list(reversed(f))
        out.append(list(f))
    return out


class Mesh:
    """一个 GLB 网格节点的几何：按材质名分面，顶点自带 RGBA 顶点色（乘到基础色上）。

    placement：with m.at(pos, yaw, pitch, roll, scale): 之内加的几何都会被放置；可嵌套。
    """

    def __init__(self, seed=1):
        self.P, self.C, self.F = [], [], []
        self.n = 0
        self._xf = [(np.eye(3), np.zeros(3))]
        self.rng = random.Random(seed)
        self.nprng = np.random.default_rng(seed)

    # --- 放置 ---
    @contextmanager
    def at(self, pos=(0, 0, 0), yaw=0.0, pitch=0.0, roll=0.0, scale=1.0):
        """pos 为局部原点；yaw 绕 +Y、pitch 绕 +X、roll 绕 +Z（先 roll，再 pitch，再 yaw）。scale 为均匀缩放（>0）。"""
        Mp, tp = self._xf[-1]
        R = rot_y(yaw) @ rot_x(pitch) @ rot_z(roll) * scale
        M = Mp @ R
        t = Mp @ np.asarray(pos, dtype=float) + tp
        self._xf.append((M, t))
        try:
            yield self
        finally:
            self._xf.pop()

    def world(self, p):
        M, t = self._xf[-1]
        return M @ np.asarray(p, dtype=float) + t

    # --- 加几何 ---
    def add(self, V, faces, mat, smooth=False, tint=(1, 1, 1), alpha=1.0, uvoff=None, proj=None):
        """V：(n,3) 局部坐标；faces：局部下标列表（法线朝外，由调用方保证）。返回全局起始下标。"""
        V = np.asarray(V, dtype=float).reshape(-1, 3)
        M, t = self._xf[-1]
        W = V @ M.T + t
        base = self.n
        cols = np.empty((len(V), 4))
        cols[:, :3] = tint
        cols[:, 3] = alpha
        self.P.append(W)
        self.C.append(cols)
        if uvoff is None:
            uvoff = (self.rng.random(), self.rng.random())
        flags = smooth if isinstance(smooth, (list, tuple, np.ndarray)) else [smooth] * len(faces)
        for f, sm in zip(faces, flags):
            if len(set(f)) < 3:
                continue
            self.F.append((mat, [base + i for i in f], bool(sm), uvoff, proj))
        self.n += len(V)
        return base

    def solid(self, mat, V, faces=None, ref=None, smooth=False, **kw):
        """凸多面体：faces 缺省时按给定“面（下标）列表”处理，法线按 ref（缺省 = 重心）朝外。"""
        V = np.asarray(V, dtype=float)
        ref = V.mean(axis=0) if ref is None else ref
        return self.add(V, orient(V, faces, ref), mat, smooth, **kw)

    def poly(self, mat, pts, **kw):
        """单个多边形（已按需要的绕序给出；法线 = 右手定则）。"""
        return self.add(np.asarray(pts, float), [list(range(len(pts)))], mat, **kw)

    def quad_up(self, mat, pts, **kw):
        """四边形 / 多边形，保证法线朝上（+Y）。"""
        P = np.asarray(pts, float)
        f = list(range(len(P)))
        if _newell(P)[1] < 0:
            f.reverse()
        return self.add(P, [f], mat, **kw)

    # --- 圆柱 / 车削 ---
    def lathe(self, mat, profile, sides=12, smooth=True, share=False, rot=0.0, ellipse=(1.0, 1.0),
              rmod=None, cap_bottom=True, cap_top=True, top_jag=None, tint=(1, 1, 1), uvoff=None):
        """绕 Y 轴车削。profile = [(r, y), ...]，按“实体在行进方向左侧”的顺序（自底向上、先向外后向上）。
        r = 0 的端点收成一个点。share=False：每个分段独立顶点（段与段之间是硬边）；share=True：共用环（整体平滑）。
        rmod：半径倍率列表（循环取用，做凹槽柱）。top_jag=(幅度, 种子)：把顶环抬 / 压出锯齿、顶盖变成凹坑（断裂的柱顶）。
        角度：x = r cos a，z = −r sin a（a 增大 = 从上往下看逆时针）。"""
        a = rot + np.arange(sides) * (2 * math.pi / sides)
        mod = np.ones(sides) if rmod is None else np.asarray([rmod[k % len(rmod)] for k in range(sides)], float)
        cs, sn = np.cos(a) * mod * ellipse[0], -np.sin(a) * mod * ellipse[1]
        jag = None
        if top_jag and profile[-1][0] > 1e-9:
            amp, sd = top_jag
            j = (np.random.default_rng(sd).random(sides) - 0.8) * amp
            jag = (j + np.roll(j, 1) * 0.5) / 1.5
        verts, faces, flags = [], [], []
        nv = [0]

        def push(arr):
            verts.append(arr)
            b = nv[0]
            nv[0] += len(arr)
            return b

        def ring(r, y, dy=None):
            ys = np.full(sides, float(y)) if dy is None else y + dy
            return np.stack([r * cs, ys, r * sn], axis=1)

        cache = {}

        def get(i, band, use_jag=False):
            key = (i, None if share else band, use_jag)
            if key not in cache:
                r, y = profile[i]
                cache[key] = (True, push(np.array([[0.0, y, 0.0]]))) if r <= 1e-9 else (False, push(ring(r, y, jag if use_jag else None)))
            return cache[key]

        last = len(profile) - 2
        for k in range(len(profile) - 1):
            lo, hi = get(k, k), get(k + 1, k, use_jag=(k == last and jag is not None))
            if lo[0] and hi[0]:
                continue
            for e in range(sides):
                e2 = (e + 1) % sides
                if lo[0]:
                    faces.append([hi[1] + e2, hi[1] + e, lo[1]])
                elif hi[0]:
                    faces.append([lo[1] + e, lo[1] + e2, hi[1]])
                else:
                    faces.append([lo[1] + e, lo[1] + e2, hi[1] + e2, hi[1] + e])
                flags.append(smooth)
        r0, y0 = profile[0]
        if cap_bottom and r0 > 1e-9:
            b = push(ring(r0, y0))
            faces.append(list(range(b + sides - 1, b - 1, -1)))
            flags.append(False)
        r1, y1 = profile[-1]
        if cap_top and r1 > 1e-9:
            if jag is not None:
                b = push(ring(r1, y1, jag))
                c = push(np.array([[0.0, y1 - abs(jag).mean() * 1.6 - 0.12 * r1, 0.0]]))
                for e in range(sides):
                    faces.append([b + e, b + (e + 1) % sides, c])
                    flags.append(False)
            else:
                b = push(ring(r1, y1))
                faces.append(list(range(b, b + sides)))
                flags.append(False)
        return self.add(np.concatenate(verts), faces, mat, flags, tint, uvoff=uvoff)

    def box(self, mat, size, pos=(0, 0, 0), yaw=0.0, anchor="bottom", bottom=True, taper=0.0, chamfer=0.0,
            pitch=0.0, roll=0.0, tint=(1, 1, 1), uvoff=None):
        """长方体（可顶部收窄 taper∈[0,1)、顶边倒角 chamfer 米）。anchor：'bottom' 底面中心为原点，'center' 体心。"""
        sx, sy, sz = size
        y0 = 0.0 if anchor == "bottom" else -sy / 2
        prof = [(0.0, y0)]
        if chamfer > 0:
            prof += [(0.0, y0 + sy - chamfer), (chamfer, y0 + sy)]
        else:
            prof += [(sx * taper * 0.5, y0 + sy)] if taper else [(0.0, y0 + sy)]
        with self.at(pos, yaw, pitch, roll):
            return self.stack_rect(mat, sx / 2, sz / 2, prof, bottom=bottom, tint=tint, uvoff=uvoff)

    def stack_rect(self, mat, hx, hz, profile, bottom=True, top=True, tint=(1, 1, 1), uvoff=None):
        """矩形截面“叠层”：profile = [(内缩 d, y), ...]，第 k 环的半宽 (hx−d, hz−d)。平直着色。"""
        V, F = [], []
        for d, y in profile:
            ex, ez = max(hx - d, 1e-4), max(hz - d, 1e-4)
            V += [(-ex, y, -ez), (ex, y, -ez), (ex, y, ez), (-ex, y, ez)]
        V = np.array(V)
        for k in range(len(profile) - 1):
            for e in range(4):
                F.append([4 * k + e, 4 * k + (e + 1) % 4, 4 * (k + 1) + (e + 1) % 4, 4 * (k + 1) + e])
        if bottom:
            F.append([0, 1, 2, 3])
        if top:
            t = 4 * (len(profile) - 1)
            F.append([t, t + 1, t + 2, t + 3])
        ref = np.array([0.0, (profile[0][1] + profile[-1][1]) / 2, 0.0])
        return self.add(V, orient(V, F, ref), mat, False, tint, uvoff=uvoff)

    # --- 岩块 ---
    _ICO = {}

    @classmethod
    def _ico(cls, detail):
        if detail in cls._ICO:
            return cls._ICO[detail]
        t = (1 + 5 ** 0.5) / 2
        V = [(-1, t, 0), (1, t, 0), (-1, -t, 0), (1, -t, 0), (0, -1, t), (0, 1, t), (0, -1, -t), (0, 1, -t),
             (t, 0, -1), (t, 0, 1), (-t, 0, -1), (-t, 0, 1)]
        F = [(0, 11, 5), (0, 5, 1), (0, 1, 7), (0, 7, 10), (0, 10, 11), (1, 5, 9), (5, 11, 4), (11, 10, 2), (10, 7, 6),
             (7, 1, 8), (3, 9, 4), (3, 4, 2), (3, 2, 6), (3, 6, 8), (3, 8, 9), (4, 9, 5), (2, 4, 11), (6, 2, 10),
             (8, 6, 7), (9, 8, 1)]
        V = [np.array(v, float) / np.linalg.norm(v) for v in V]
        for _ in range(detail):
            mid, nf = {}, []

            def midpoint(a, b):
                k = (min(a, b), max(a, b))
                if k not in mid:
                    m = (V[a] + V[b]) / 2
                    V.append(m / np.linalg.norm(m))
                    mid[k] = len(V) - 1
                return mid[k]
            for a, b, c in F:
                ab, bc, ca = midpoint(a, b), midpoint(b, c), midpoint(c, a)
                nf += [(a, ab, ca), (b, bc, ab), (c, ca, bc), (ab, bc, ca)]
            F = nf
        cls._ICO[detail] = (np.array(V), F)
        return cls._ICO[detail]

    def rock(self, mat, radii=(0.3, 0.2, 0.3), pos=(0, 0, 0), seed=0, detail=0, jitter=0.28, squash=0.55,
             yaw=0.0, tint=(1, 1, 1), sink=0.3, uvoff=None, smooth=True):
        """低面数岩块（二十面体变形）。底面压平在局部 y = 0；detail=0 → 20 面 / 12 顶点、1 → 80 面。
        smooth=True（默认）：圆润的卵石，顶点数只有平直着色的 1/5（文件小得多）；UV 一律俯视投影（小块，拉伸看不出）。"""
        rng = np.random.default_rng(seed)
        V0, F0 = self._ico(detail)
        V = V0 * (1 + (rng.random(len(V0)) - 0.5) * 2 * jitter)[:, None]
        V = V * np.array(radii)[None, :]
        V[:, 1] = V[:, 1] * squash + radii[1] * sink
        V[:, 1] = np.maximum(V[:, 1], 0.0)
        faces = orient(V, F0, np.array([0.0, radii[1] * 0.3, 0.0]))
        faces = [f for f in faces if not all(V[i, 1] <= 1e-9 for i in f)]       # 压平的底面在地下，不要
        with self.at(pos, yaw):
            return self.add(V, faces, mat, smooth, tint, uvoff=uvoff, proj="top")

    # --- 平面件 ---
    def strip_xz(self, mat, pts, widths, y=0.012, tint=(1, 1, 1), alpha=1.0):
        """沿折线的平铺窄带（朝上，贴地裂缝 / 线）。pts = [(x, z)...]，widths = 各点宽度。"""
        P = np.asarray(pts, float)
        L, R = [], []
        for i in range(len(P)):
            t = P[min(i + 1, len(P) - 1)] - P[max(i - 1, 0)]
            t = t / (np.linalg.norm(t) + 1e-9)
            nrm = np.array([-t[1], t[0]])
            L.append((P[i, 0] + nrm[0] * widths[i] / 2, y, P[i, 1] + nrm[1] * widths[i] / 2))
            R.append((P[i, 0] - nrm[0] * widths[i] / 2, y, P[i, 1] - nrm[1] * widths[i] / 2))
        V = np.array(L + R)
        k = len(P)
        faces = []
        for i in range(k - 1):
            q = [i, i + 1, k + i + 1, k + i]
            if _newell(V[q])[1] < 0:
                q.reverse()
            faces.append(q)
        return self.add(V, faces, mat, False, tint, alpha)

    def absorb(self, other, offset=(0, 0, 0), mats=None):
        """把另一个 Mesh 的几何整体平移后并入（先在草稿 Mesh 里摆好、量好最低点再落地用）。"""
        off = np.asarray(offset, float)
        base = self.n
        for W, C_ in zip(other.P, other.C):
            self.P.append(W + off)
            self.C.append(C_.copy())
        for mat, ids, sm, uo, pj in other.F:
            self.F.append(((mats or {}).get(mat, mat), [i + base for i in ids], sm, uo, pj))
        self.n += other.n

    def min_y(self):
        return min(W[:, 1].min() for W in self.P) if self.P else 0.0

    # --- 顶点色 ---
    def paint(self, fn):
        """fn(P: (n,3) 世界坐标) → (n,3) 乘数，乘进所有顶点的 RGB。"""
        for W, C in zip(self.P, self.C):
            C[:, :3] *= fn(W)

    def tris(self):
        return sum(len(f[1]) - 2 for f in self.F)

    def mats_used(self):
        return sorted({f[0] for f in self.F})


# =====================================================================
# 材质
# =====================================================================
@dataclass
class MatSpec:
    """glTF 材质规格。贴图键：base（sRGB）/ normal / emissive（sRGB）/ mr（G 粗糙度、B 金属度）→ PNG 路径。
    emit 为发光色（sRGB 十六进制）；写进 GLB 的强度 = strength（半透明材质已按透明度预乘）。"""
    name: str
    base: str = "#808080"
    metal: float = 0.0
    rough: float = 0.6
    emit: str = None
    strength: float = 0.0
    alpha: float = 1.0
    tex: dict = field(default_factory=dict)
    normal_strength: float = 1.0
    uv: str = None                 # None / 'floor' / 'box'
    uv_scale: float = 1.0          # 米 / 贴图周期
    uv_offset: tuple = (0.0, 0.0)  # 贴图坐标偏移（纹章：圆心在贴图中心 → 0.5, 0.5）
    double: bool = False
    vcolor_alpha: bool = False     # 透明度由顶点色 A 给出（光柱的渐隐）
    notes: str = ""


def make_material(spec):
    """按规格建 Blender 材质：贴图 → Principled（基础色 × 顶点色）；发光 / 半透明按 spec。"""
    m = bpy.data.materials.new(spec.name)
    try:
        m.use_nodes = True
    except AttributeError:
        pass
    nt = m.node_tree
    nodes, links = nt.nodes, nt.links
    p = nodes["Principled BSDF"]

    def tex_node(path, noncolor, loc):
        n = nodes.new("ShaderNodeTexImage")
        n.image = bpy.data.images.load(str(path), check_existing=True)
        n.image.colorspace_settings.name = "Non-Color" if noncolor else "sRGB"
        n.extension = "REPEAT"
        n.interpolation = "Linear"
        n.location = loc
        return n

    base_rgb = (*lin(spec.base), 1.0)
    vc = nodes.new("ShaderNodeVertexColor")
    vc.layer_name = "Col"
    vc.location = (-700, 300)
    if "base" in spec.tex:
        tb = tex_node(spec.tex["base"], False, (-900, 300))
        mix = nodes.new("ShaderNodeMix")
        mix.data_type = "RGBA"
        mix.blend_type = "MULTIPLY"
        mix.inputs["Factor"].default_value = 1.0
        mix.location = (-500, 300)
        links.new(tb.outputs["Color"], mix.inputs[6])
        links.new(vc.outputs["Color"], mix.inputs[7])
        links.new(mix.outputs[2], p.inputs["Base Color"])
    else:
        mix = nodes.new("ShaderNodeMix")
        mix.data_type = "RGBA"
        mix.blend_type = "MULTIPLY"
        mix.inputs["Factor"].default_value = 1.0
        mix.inputs[6].default_value = base_rgb
        mix.location = (-500, 300)
        links.new(vc.outputs["Color"], mix.inputs[7])
        links.new(mix.outputs[2], p.inputs["Base Color"])
    if "normal" in spec.tex:
        tn = tex_node(spec.tex["normal"], True, (-900, -100))
        nm = nodes.new("ShaderNodeNormalMap")
        nm.inputs["Strength"].default_value = spec.normal_strength
        nm.location = (-500, -100)
        links.new(tn.outputs["Color"], nm.inputs["Color"])
        links.new(nm.outputs["Normal"], p.inputs["Normal"])
    if "mr" in spec.tex:
        tm = tex_node(spec.tex["mr"], True, (-900, -400))
        sep = nodes.new("ShaderNodeSeparateColor")
        sep.location = (-500, -400)
        links.new(tm.outputs["Color"], sep.inputs["Color"])
        links.new(sep.outputs["Green"], p.inputs["Roughness"])
        links.new(sep.outputs["Blue"], p.inputs["Metallic"])
    else:
        p.inputs["Metallic"].default_value = spec.metal
        p.inputs["Roughness"].default_value = spec.rough
    if "Specular IOR Level" in p.inputs:
        p.inputs["Specular IOR Level"].default_value = 0.5
    if "emissive" in spec.tex:
        te = tex_node(spec.tex["emissive"], False, (-900, -700))
        links.new(te.outputs["Color"], p.inputs["Emission Color"])
        p.inputs["Emission Strength"].default_value = spec.strength
    elif spec.emit:
        p.inputs["Emission Color"].default_value = (*lin(spec.emit), 1.0)
        p.inputs["Emission Strength"].default_value = spec.strength
    else:
        p.inputs["Emission Strength"].default_value = 0.0
    if spec.alpha < 1.0 or spec.vcolor_alpha:
        if spec.vcolor_alpha:
            mul = nodes.new("ShaderNodeMath")
            mul.operation = "MULTIPLY"
            mul.inputs[1].default_value = spec.alpha
            links.new(vc.outputs["Alpha"], mul.inputs[0])
            links.new(mul.outputs["Value"], p.inputs["Alpha"])
        else:
            p.inputs["Alpha"].default_value = spec.alpha
        try:
            m.surface_render_method = "BLENDED"
        except (AttributeError, TypeError):
            pass
    m.use_backface_culling = not (spec.double or spec.alpha < 1.0 or spec.vcolor_alpha)
    m.diffuse_color = (*lin(spec.base), 1.0)
    return m


# =====================================================================
# 网格 → Blender 对象
# =====================================================================
def _face_normals(P, faces):
    N = np.zeros((len(faces), 3))
    for i, ids in enumerate(faces):
        N[i] = _newell(P[ids])
    ln = np.linalg.norm(N, axis=1, keepdims=True)
    return N / np.maximum(ln, 1e-12)


def to_blender(mesh, name, mats, specs, collection=None):
    """Mesh → Blender 对象（单个对象、多个材质槽 = 导出后一个 glTF 网格、多个图元）。"""
    P = np.concatenate(mesh.P) if mesh.P else np.zeros((0, 3))
    C = np.concatenate(mesh.C)
    names = mesh.mats_used()
    slot = {n: i for i, n in enumerate(names)}
    faces = [f[1] for f in mesh.F]
    me = bpy.data.meshes.new(name)
    vb = np.stack([P[:, 0], -P[:, 2], P[:, 1]], axis=1)          # 游戏 → Blender
    me.from_pydata(vb.tolist(), [], [list(f) for f in faces])
    me.polygons.foreach_set("material_index", np.array([slot[f[0]] for f in mesh.F], dtype=np.int32))
    me.polygons.foreach_set("use_smooth", np.array([f[2] for f in mesh.F], dtype=bool))
    for n in names:
        me.materials.append(mats[n])
    ca = me.color_attributes.new("Col", "FLOAT_COLOR", "POINT")
    ca.data.foreach_set("color", C.astype(np.float32).ravel())
    # UV（逐面逐角）：floor = 俯视平铺；box = 按法线主轴投影（带每个零件的随机偏移）
    FN = _face_normals(P, faces)
    loops = np.concatenate([np.asarray(f) for f in faces])
    counts = np.array([len(f) for f in faces])
    fidx = np.repeat(np.arange(len(faces)), counts)
    X, Y, Z = P[loops, 0], P[loops, 1], P[loops, 2]
    uv = np.zeros((len(loops), 2))
    offs = np.array([f[3] for f in mesh.F])[fidx]
    topproj = np.array([f[4] == 'top' for f in mesh.F])[fidx]
    for n in names:
        sp = specs[n]
        if not sp.uv:
            continue
        sel = np.array([f[0] == n for f in mesh.F])[fidx]
        s = sp.uv_scale
        if sp.uv == "floor":
            uv[sel, 0] = X[sel] / s + sp.uv_offset[0]
            uv[sel, 1] = -Z[sel] / s + sp.uv_offset[1]
        else:
            nrm = np.abs(FN[fidx])
            top = ((nrm[:, 1] >= nrm[:, 0]) & (nrm[:, 1] >= nrm[:, 2])) | topproj
            ew = (~top) & (nrm[:, 0] >= nrm[:, 2])
            ns = ~(top | ew)
            u = np.where(top, X, np.where(ew, -Z, X)) / s
            v = np.where(top, -Z, Y) / s
            uv[sel, 0] = (u + offs[:, 0] * 4)[sel]
            uv[sel, 1] = (v + offs[:, 1] * 4)[sel]
    uvl = me.uv_layers.new(name="UVMap")
    uvl.data.foreach_set("uv", uv.astype(np.float32).ravel())
    me.update()
    obj = bpy.data.objects.new(name, me)
    (collection or bpy.context.scene.collection).objects.link(obj)
    return obj


def count_tris(obj):
    me = obj.data
    me.calc_loop_triangles()
    return len(me.loop_triangles)


# =====================================================================
# 场景装配
# =====================================================================
@dataclass
class Part:
    """一个 GLB 网格节点：name = 节点名；group = ARENA_FLOOR / ARENA_BOUNDS / ARENA_PROPS / ARENA_LIGHTS。"""
    name: str
    group: str
    mesh: Mesh


GROUPS = ("ARENA_FLOOR", "ARENA_BOUNDS", "ARENA_PROPS", "ARENA_LIGHTS")


def assemble(parts, specs):
    """清空场景，按配方构建全部材质与对象，挂到四个分组空节点下。返回 (groups, objs, mats)。"""
    mats = {n: make_material(s) for n, s in specs.items()}
    groups = {}
    for g in GROUPS:
        e = bpy.data.objects.new(g, None)
        e.empty_display_type = "PLAIN_AXES"
        bpy.context.scene.collection.objects.link(e)
        groups[g] = e
    objs = {}
    for p in parts:
        o = to_blender(p.mesh, p.name, mats, specs)
        o.parent = groups[p.group]
        objs[p.name] = o
    return groups, objs, mats


# =====================================================================
# 导出 + 补丁
# =====================================================================
def export_glb(path, groups, objs):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.object.select_all(action="DESELECT")
    for o in list(groups.values()) + list(objs.values()):
        o.select_set(True)
    bpy.context.view_layer.objects.active = next(iter(objs.values()))
    bpy.ops.export_scene.gltf(filepath=str(path), export_format="GLB", use_selection=True, export_yup=True,
                              export_apply=True, export_animations=False, export_skins=False,
                              export_cameras=False, export_lights=False, export_image_format="AUTO",
                              export_vertex_color="ACTIVE", export_all_vertex_colors=False,
                              export_active_vertex_color_when_no_material=True)


def read_glb(path):
    data = Path(path).read_bytes()
    jlen = struct.unpack_from("<I", data, 12)[0]
    js = json.loads(data[20:20 + jlen])
    return js, data[20 + jlen:]


def write_glb(path, js, rest):
    blob = json.dumps(js, separators=(",", ":")).encode()
    blob += b" " * (-len(blob) % 4)
    out = b"glTF" + struct.pack("<II", 2, 12 + 8 + len(blob) + len(rest)) + struct.pack("<I4s", len(blob), b"JSON") + blob + rest
    Path(path).write_bytes(out)


def patch_glb(path, specs):
    """导出后补丁：按规格写回发光色 / 强度（辐射量不变）、半透明 alphaMode / doubleSided / alpha、材质单双面。"""
    js, rest = read_glb(path)
    used = js.setdefault("extensionsUsed", [])
    for gm in js.get("materials", []):
        sp = specs.get(gm["name"])
        if sp is None:
            continue
        pbr = gm.setdefault("pbrMetallicRoughness", {})
        if sp.alpha < 1.0 or sp.vcolor_alpha:
            gm["alphaMode"] = "BLEND"
            bc = pbr.setdefault("baseColorFactor", [*lin(sp.base), 1.0])
            bc[3] = round(sp.alpha, 4)
        else:
            gm.pop("alphaMode", None)
        if sp.double or sp.alpha < 1.0 or sp.vcolor_alpha:
            gm["doubleSided"] = True
        else:
            gm.pop("doubleSided", None)
        if sp.strength > 0 and (sp.emit or "emissive" in sp.tex):
            gm["emissiveFactor"] = [1.0, 1.0, 1.0] if "emissive" in sp.tex else [round(c, 6) for c in lin(sp.emit)]
            ext = gm.setdefault("extensions", {})
            if sp.strength != 1.0:
                ext["KHR_materials_emissive_strength"] = {"emissiveStrength": round(sp.strength, 4)}
                if "KHR_materials_emissive_strength" not in used:
                    used.append("KHR_materials_emissive_strength")
            elif "KHR_materials_emissive_strength" in ext:
                del ext["KHR_materials_emissive_strength"]
        else:
            gm.pop("emissiveFactor", None)
            gm.get("extensions", {}).pop("KHR_materials_emissive_strength", None)
        if not gm.get("extensions"):
            gm.pop("extensions", None)
    if not used:
        js.pop("extensionsUsed", None)
    js["asset"]["generator"] = js["asset"].get("generator", "") + " + tools/arenas"
    write_glb(path, js, rest)


def slim_glb(path):
    """导出后瘦身（只做 glTF 核心规范允许的事）：
    ① COLOR_0 由 ushort 归一化改成 ubyte 归一化（每顶点 −4 字节；顶点色是低频乘数，8 位够用）；
    ② 没有任何贴图的材质所用的图元去掉 TEXCOORD_0（每顶点 −8 字节）；
    ③ 整理 accessor / bufferView，丢掉没人引用的数据。返回 (原字节, 新字节)。"""
    path = Path(path)
    before = path.stat().st_size
    js, rest = read_glb(path)
    blob = bytearray(rest[8:])                 # 去掉 BIN 块头（长度 + 'BIN\0'）
    acc, views = js["accessors"], js["bufferViews"]
    textured = set()
    for i, m in enumerate(js["materials"]):
        pbr = m.get("pbrMetallicRoughness", {})
        if any(k in m for k in ("normalTexture", "emissiveTexture", "occlusionTexture")) or any(k in pbr for k in ("baseColorTexture", "metallicRoughnessTexture")):
            textured.add(i)
    new_view_data = {}                         # accessor 下标 → 新的字节（COLOR_0 重编码）
    for mesh in js["meshes"]:
        for prim in mesh["primitives"]:
            at = prim["attributes"]
            if "TEXCOORD_0" in at and prim.get("material") not in textured:
                del at["TEXCOORD_0"]
            if "COLOR_0" in at:
                ai = at["COLOR_0"]
                a = acc[ai]
                if a["componentType"] == 5123 and ai not in new_view_data:
                    v = views[a["bufferView"]]
                    off = v.get("byteOffset", 0) + a.get("byteOffset", 0)
                    n = a["count"] * 4
                    arr = np.frombuffer(bytes(blob[off:off + n * 2]), dtype="<u2").astype(np.float64)
                    new_view_data[ai] = np.clip(np.round(arr / 65535.0 * 255.0), 0, 255).astype(np.uint8).tobytes()
    used_acc = sorted({i for m in js["meshes"] for p in m["primitives"] for i in list(p["attributes"].values()) + [p["indices"]]})
    acc_map = {old: new for new, old in enumerate(used_acc)}
    used_views = []
    for ai in used_acc:
        bv = acc[ai]["bufferView"]
        if bv not in used_views:
            used_views.append(bv)
    for im in js.get("images", []):
        if im["bufferView"] not in used_views:
            used_views.append(im["bufferView"])
    used_views.sort()
    out, new_views, view_map = bytearray(), [], {}
    for old in used_views:
        v = views[old]
        data = None
        for ai in used_acc:
            if acc[ai]["bufferView"] == old and ai in new_view_data:
                data = new_view_data[ai]
        if data is None:
            off = v.get("byteOffset", 0)
            data = bytes(blob[off:off + v["byteLength"]])
        while len(out) % 4:
            out.append(0)
        nv = {"buffer": 0, "byteOffset": len(out), "byteLength": len(data)}
        for k in ("target", "byteStride"):
            if k in v:
                nv[k] = v[k]
        out += data
        view_map[old] = len(new_views)
        new_views.append(nv)
    new_acc = []
    for ai in used_acc:
        a = dict(acc[ai])
        a["bufferView"] = view_map[a["bufferView"]]
        a.pop("byteOffset", None)
        if ai in new_view_data:
            a["componentType"], a["normalized"] = 5121, True
        new_acc.append(a)
    for m in js["meshes"]:
        for p in m["primitives"]:
            p["attributes"] = {k: acc_map[v] for k, v in p["attributes"].items()}
            p["indices"] = acc_map[p["indices"]]
    for im in js.get("images", []):
        im["bufferView"] = view_map[im["bufferView"]]
    js["accessors"], js["bufferViews"] = new_acc, new_views
    while len(out) % 4:
        out.append(0)
    js["buffers"] = [{"byteLength": len(out)}]
    rest = struct.pack("<I4s", len(out), b"BIN\x00") + bytes(out)
    write_glb(path, js, rest)
    return before, path.stat().st_size


# =====================================================================
# 通用造景件（四个区域共用；材质名 / 色板由区域传进来）
# =====================================================================
def clear_of_play(x, z, s=0.0):
    """半径 s 的物体放在 (x, z)，是否完全在“可活动区域外扩 1.5 m”之外（边界线两侧 1.5 m 内只留给边界基座 / 栏杆）。"""
    return abs(x) >= PLAY_X + 1.5 + s or abs(z) >= PLAY_Z + 1.5 + s


def up_face(P, f):
    """让多边形（顶点下标 f）的法线朝上（+Y）。"""
    q = list(f)
    if _newell(np.asarray(P)[q])[1] < 0:
        q.reverse()
    return q


def weathered_paint(seed=0, dirt_h=3.2, dirt=0.50, moss=True):
    """建筑 / 石头的顶点色乘数 fn(P)->(n,3)：近地面脏污变暗（dirt_h 米内渐变）+ 低频明暗 + 贴地的青绿苔染。"""
    def fn(P):
        y = P[:, 1]
        base = dirt + (1.0 - dirt) * T.smoothstep(0.0, dirt_h, y)
        v = base * (0.72 + 0.34 * vnoise(P, 0.30, seed) + 0.12 * vnoise(P, 1.10, seed + 3))
        m_ = (1.0 - T.smoothstep(0.0, 1.6, y)) * T.smoothstep(0.55, 0.85, vnoise(P, 0.7, seed + 9)) if moss else 0.0 * y
        return np.stack([v * (1 - 0.10 * m_), v * (1 + 0.05 * m_), v * (1 + 0.02 * m_)], axis=1)
    return fn


def rag(x, seed, amp=1.0):
    """沿 x 的一维值噪声（0..amp）：残墙顶部参差用。"""
    return amp * float(vnoise(np.array([[x * 0.8, 0.0, 0.0]]), 1.0, seed)[0])


def rubble_heap(m, mat, x, z, radius, n, hmax, seed, ymax=None):
    """碎石堆：大块在中心、小块在外圈，底座随堆高抬起；总高 ≤ ymax；落进“可活动区域外扩 1.5 m”的石块直接略过。"""
    rng = random.Random(seed)
    for i in range(n):
        d = radius * (rng.random() ** 0.7)
        a = rng.uniform(0, math.tau)
        prof = hmax * (1.0 - d / radius) ** 1.3
        s = rng.uniform(0.22, 0.65) * (0.55 + 0.7 * (1 - d / radius)) * (1.0 + hmax * 0.12)
        y0 = prof * 0.62
        height = s * 0.62
        if ymax is not None and y0 + height > ymax:
            s *= max(0.25, (ymax - y0) / max(height, 1e-3))
            if y0 + s * 0.62 > ymax:
                y0 = max(0.0, ymax - s * 0.62)
        t = rng.uniform(0.7, 1.1)
        px_, pz_ = x + d * math.cos(a), z + d * math.sin(a)
        if not clear_of_play(px_, pz_, s * 1.25):
            continue
        m.rock(mat, (s, s * 0.85, s * rng.uniform(0.7, 1.2)), (px_, y0, pz_), seed=seed * 131 + i,
               detail=0, yaw=rng.uniform(0, math.tau), tint=(t, t, t))


def wall_strips(m, mat, x0, x1, z, thick, top_fn, hole_fn, seed, strip=0.75):
    """残墙：宽 strip 的竖条砌体，每条再分成 1–1.5 m 的“层”（深度 / 色调略有错动 → 一块一块的石头），
    顶部高度 top_fn(x)（参差不齐），hole_fn(x) → (y_low, y_high) 或 None 给窗洞开口。"""
    rng = random.Random(seed)
    n = max(1, int(round((x1 - x0) / strip)))
    w = (x1 - x0) / n
    for i in range(n):
        xc = x0 + (i + 0.5) * w
        top = top_fn(xc)
        if top <= 0.2:
            continue
        hole = hole_fn(xc) if hole_fn else None
        pieces = []
        if hole and hole[0] < top:
            pieces.append((0.0, hole[0]))
            if hole[1] < top - 0.2:
                pieces.append((hole[1], top))
        else:
            pieces.append((0.0, top))
        for (ya, yb) in pieces:
            y = ya
            while y < yb - 0.1:
                hh = min(rng.uniform(0.95, 1.55), yb - y)
                if yb - (y + hh) < 0.45:
                    hh = yb - y
                t = rng.uniform(0.82, 1.08)
                th = thick * rng.uniform(0.93, 1.0)
                m.box(mat, (w * rng.uniform(0.95, 0.995), hh, th), pos=(xc, y, z + rng.uniform(-0.06, 0.08)),
                      chamfer=0.09 if abs(y + hh - yb) < 1e-6 else 0.0, bottom=False, tint=(t, t, t), yaw=rng.uniform(-0.015, 0.015))
                y += hh


def pointed_hole(cx, y0, half_w, rise, spring):
    """尖拱窗洞：x 处的 (下沿, 上沿)；直边到 y0+spring，之后按尖拱曲线收口，顶点高 y0+spring+rise。"""
    def fn(x):
        dx = abs(x - cx)
        if dx >= half_w:
            return None
        return (y0, y0 + spring + rise * math.sqrt(max(0.0, 1.0 - (dx / half_w) ** 1.8)))
    return fn


def round_hole(cx, cy, R):
    def fn(x):
        dx = abs(x - cx)
        if dx >= R:
            return None
        dy = math.sqrt(R * R - dx * dx)
        return (cy - dy, cy + dy)
    return fn


def steps(m, mat, x0, x1, z, depth, tiers, seed):
    """残破台阶：沿 x 切成几段，每段随机掉高度（从外向里逐级抬高）。"""
    rng = random.Random(seed)
    for k in range(tiers):
        zt = z - k * depth
        x = x0
        while x < x1:
            w = rng.uniform(1.6, 3.6)
            h = 0.28 * (k + 1) * rng.uniform(0.55, 1.0)
            m.box(mat, (min(w, x1 - x), h, depth * 1.01), pos=(x + min(w, x1 - x) / 2, 0, zt - depth / 2), chamfer=0.05,
                  tint=(rng.uniform(0.8, 1.05),) * 3)
            x += w


def macro_color(pct, stops, ref_lum):
    """地面顶点色：贴图是“中性明度图”，色相由低频场的分位数 pct（0..1）按 stops=[(位置, 十六进制)...] 给出。
    顶点色是线性乘数且只能 ≤ 1，所以用 期望的最终颜色 / 贴图中值明度 折算。"""
    pos = np.array([p for p, _ in stops])
    cols = np.stack([lin(h) for _, h in stops])
    out = np.stack([np.interp(pct, pos, cols[:, k]) for k in range(3)], axis=1)
    return np.clip(out / ref_lum, 0.0, 1.0)


def floor_grid(m, mat, cell=3.0):
    """覆盖 x∈±FLOOR_X、z∈±FLOOR_Z 的朝上网格（cell 米一格，供顶点色做低频变化）。返回顶点数组 P（颜色由调用方写进 m.C[-1]）。"""
    nx, nz = int(math.ceil(2 * FLOOR_X / cell)), int(math.ceil(2 * FLOOR_Z / cell))
    xs, zs = np.linspace(-FLOOR_X, FLOOR_X, nx + 1), np.linspace(-FLOOR_Z, FLOOR_Z, nz + 1)
    X, Z = np.meshgrid(xs, zs)
    P = np.stack([X.ravel(), np.zeros(X.size), Z.ravel()], axis=1)
    F = []
    for j in range(nz):
        for i in range(nx):
            a = j * (nx + 1) + i
            F.append([a, a + 1, a + nx + 2, a + nx + 1])
    m.add(P, [up_face(P, f) for f in F], mat, False)
    return P


def disc(m, mat, radius, tint=(1, 1, 1), seg=96, rings=3, y=0.0):
    """朝上的圆盘（中心一圈扇形 + 若干圈环带），圆心在局部原点；纹章 / 贴花用。"""
    V, FF = [(0.0, 0.0, 0.0)], []
    for r in [radius * (k + 1) / rings for k in range(rings)]:
        V += [(r * math.cos(math.tau * k / seg), 0.0, -r * math.sin(math.tau * k / seg)) for k in range(seg)]
    for k in range(seg):
        FF.append([0, 1 + k, 1 + (k + 1) % seg])
    for ring in range(rings - 1):
        a0, a1 = 1 + ring * seg, 1 + (ring + 1) * seg
        for k in range(seg):
            FF.append([a0 + k, a0 + (k + 1) % seg, a1 + (k + 1) % seg, a1 + k])
    V = np.array(V)
    with m.at((0, y, 0)):
        m.add(V, [up_face(V, f) for f in FF], mat, False, tint=tint)


def circuit_ribbons(m, graph, tile_m, mats, walks_per_tile, density_fn, exclude_r=0.0, seed=7000, half_width=0.027, y=0.009,
                    lengths=(5, 14), alt_prob=0.10):
    """地面电路走线：在每块 tile_m 米的地砖上，沿着地砖贴图里的铅条（graph = textures.VoronoiGraph，种子必须和贴图一致）
    随机走几条线（每块地砖的随机种子不同 → 不会像贴图里的亮线那样一格一格重复）；几何是贴地的窄带 + 两端小节点。
    mats = (主材质, 点缀材质)；density_fn(x, z) → 0..1 控制走线集中在哪些区域；exclude_r：中心圆内不放（被纹章盖住）。返回走线条数。"""
    ti0, ti1 = int(math.floor(-FLOOR_X / tile_m)), int(math.ceil(FLOOR_X / tile_m))
    tj0, tj1 = int(math.floor(-FLOOR_Z / tile_m)), int(math.ceil(FLOOR_Z / tile_m))
    count = 0
    for ti in range(ti0, ti1):
        for tj in range(tj0, tj1):
            rng = np.random.default_rng(seed + ti * 101 + tj * 7)
            cx, cz = (ti + 0.5) * tile_m, (tj + 0.5) * tile_m
            dout = max(abs(cx) - PLAY_X, abs(cz) - PLAY_Z, 0.0)
            k = 1.0 - 0.85 * float(T.smoothstep(0.0, 16.0, dout))
            n_walks = int(rng.poisson(walks_per_tile * k))
            done, tries = 0, 0
            while done < n_walks and tries < 60:
                tries += 1
                v = int(rng.integers(len(graph.pos)))
                lx, ly = graph.pos[v]
                if rng.random() > density_fn((ti + lx) * tile_m, (tj + ly) * tile_m):
                    continue
                pts = graph.walk(rng, v, int(rng.integers(lengths[0], lengths[1])))
                W = [((ti + px_) * tile_m, (tj + py_) * tile_m) for px_, py_ in pts]
                if any(abs(x) > FLOOR_X - 0.5 or abs(z) > FLOOR_Z - 0.5 or math.hypot(x, z) < exclude_r for x, z in W):
                    continue
                mat = mats[1] if rng.random() < alt_prob else mats[0]
                hw = half_width
                for (x0, z0), (x1, z1) in zip(W[:-1], W[1:]):
                    d = np.array([x1 - x0, z1 - z0])
                    L = float(np.hypot(*d))
                    if L < 1e-6:
                        continue
                    d /= L
                    nx_, nz_ = -d[1], d[0]
                    ax, az, bx, bz = x0 - d[0] * hw, z0 - d[1] * hw, x1 + d[0] * hw, z1 + d[1] * hw
                    m.quad_up(mat, [(ax + nx_ * hw, y, az + nz_ * hw), (bx + nx_ * hw, y, bz + nz_ * hw),
                                    (bx - nx_ * hw, y, bz - nz_ * hw), (ax - nx_ * hw, y, az - nz_ * hw)])
                for (x, z) in (W[0], W[-1]):
                    m.poly(mat, [(x + 0.07 * math.cos(a), y + 0.001, z - 0.07 * math.sin(a)) for a in np.linspace(0, math.tau, 7)[:-1]])
                done += 1
                count += 1
    return count


def bake_ao(meshes, skip_mats=(), samples=14, dist=4.5, strength=0.6, seed=1):
    """把环境光遮蔽烘进顶点色（场景里没有实时阴影，这是唯一的“落地感”）：对每个顶点沿法线半球发 samples 条射线，
    在所有 meshes 的几何 + 一块无限大的地面（y = 0）里求遮挡，颜色 ×(1 − strength × 遮挡)。skip_mats 里的材质（发光件）不动。"""
    from mathutils import Vector
    from mathutils.bvhtree import BVHTree
    Vs, Fs, off = [], [], 0
    for m in meshes:
        P = np.concatenate(m.P)
        Vs.append(P)
        for f in m.F:
            Fs.append(tuple(i + off for i in f[1]))
        off += len(P)
    Vs.append(np.array([(-300, 0, -300), (300, 0, -300), (300, 0, 300), (-300, 0, 300)], float))
    Fs.append((off, off + 3, off + 2, off + 1))
    allP = np.concatenate(Vs)
    bvh = BVHTree.FromPolygons([tuple(map(float, v)) for v in allP], Fs)
    rng = np.random.default_rng(seed)
    # 余弦加权半球方向（局部 z 向上）
    u1, u2 = rng.random(samples), rng.random(samples)
    r = np.sqrt(u1)
    loc_dirs = np.stack([r * np.cos(math.tau * u2), r * np.sin(math.tau * u2), np.sqrt(1 - u1)], axis=1)
    base = 0
    for m in meshes:
        P = np.concatenate(m.P)
        N = np.zeros_like(P)
        skip = np.zeros(len(P), bool)
        for mat, ids, sm, uo, pj in m.F:
            n = _newell(P[ids])
            np.add.at(N, ids, n)
            if mat in skip_mats:
                skip[ids] = True
        ln = np.linalg.norm(N, axis=1, keepdims=True)
        N = np.where(ln > 1e-12, N / np.maximum(ln, 1e-12), np.array([0.0, 1.0, 0.0]))
        up = np.where(np.abs(N[:, 1:2]) < 0.9, np.array([[0, 1.0, 0]]), np.array([[1.0, 0, 0]]))
        T_ = np.cross(up, N)
        T_ /= np.linalg.norm(T_, axis=1, keepdims=True)
        B_ = np.cross(N, T_)
        occ = np.zeros(len(P))
        for vi in np.nonzero(~skip)[0]:
            o = Vector(tuple(P[vi] + N[vi] * 0.04))
            hits = 0
            for s_ in loc_dirs:
                d = T_[vi] * s_[0] + B_[vi] * s_[1] + N[vi] * s_[2]
                if bvh.ray_cast(o, Vector(tuple(d)), dist)[0] is not None:
                    hits += 1
            occ[vi] = hits / samples
        mult = 1.0 - strength * occ
        start = 0
        for Cc, Wc in zip(m.C, m.P):
            n_ = len(Wc)
            Cc[:, :3] *= mult[start:start + n_, None]
            start += n_
    return True


# =====================================================================
# 散布工具
# =====================================================================
def poisson(rng, n, accept, min_dist, box, tries=60):
    """简单飞镖法：在 box=(x0,x1,z0,z1) 里取最多 n 个点，满足 accept(x,z) 且彼此 ≥ min_dist。"""
    pts = []
    x0, x1, z0, z1 = box
    for _ in range(n * tries):
        if len(pts) >= n:
            break
        x, z = rng.uniform(x0, x1), rng.uniform(z0, z1)
        if not accept(x, z):
            continue
        if all((x - a) ** 2 + (z - b) ** 2 >= min_dist ** 2 for a, b in pts):
            pts.append((x, z))
    return pts


def vnoise(P, freq=1.0, seed=0):
    """3D 值噪声（向量化，0..1），给顶点色 / 位置抖动用。P：(n,3)。"""
    Q = np.asarray(P, float) * freq
    i = np.floor(Q).astype(np.int64)
    f = Q - i
    f = f * f * (3 - 2 * f)
    acc = 0.0
    for dx in (0, 1):
        for dy in (0, 1):
            for dz in (0, 1):
                h = T.rand01(i[:, 0] + dx + seed * 131, i[:, 1] + dy, i[:, 2] + dz)
                w = (f[:, 0] if dx else 1 - f[:, 0]) * (f[:, 1] if dy else 1 - f[:, 1]) * (f[:, 2] if dz else 1 - f[:, 2])
                acc = acc + h * w
    return acc
