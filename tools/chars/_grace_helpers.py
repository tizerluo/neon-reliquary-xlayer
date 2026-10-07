"""塞拉芙 / 伊索尔德共用的私有辅助：刻面冰晶、刃羽轮廓、额外程序化贴图、动作穿插自检、垂腿与滑冰步态。

只被 tools/chars/seraph.py 与 tools/chars/isolde.py 引用；不改动 tools/kit/ 下的任何东西，
kit 里不够用的函数在这里复制后改写（见各函数注释）。
"""

import math

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Quaternion, Vector
from mathutils.bvhtree import BVHTree

from kit.core import (TAU, Canvas, _finish, bm_object, box_blur, clamp, ellipsoid, finish, garment, hash01,
                      height_normal, invdist, lerp, orient, radial, rigid, surface, trim, tube, vfade, voronoi)
from kit.motion import Legs
from kit.rig import I3, R, X, Y, Z


# ===== 网格 =====
def radial_wrap(objs, center, reach=0.6):
    """沿水平径向把点贴到一组网格的最外层表面（冠带、发箍这类要贴合面甲 + 面纱的环）：返回 hit(a, z, lift)。"""
    dg = bpy.context.evaluated_depsgraph_get()
    trees = [BVHTree.FromObject(o, dg) for o in objs]
    c = Vector(center)

    def hit(a, z, lift=0.0):
        d = Vector((math.sin(a), math.cos(a), 0.0))
        start = Vector((c.x, c.y, z)) + d * reach
        best = None
        for tree in trees:
            loc, _, _, dist = tree.ray_cast(start, -d, reach)
            if loc is not None and (best is None or dist < best[1]):
                best = (loc, dist)
        if best is None:
            return Vector((c.x, c.y, z)) + d * 0.1
        return best[0] + d * lift
    return hit


def flat(obj):
    """整件改为平面着色（刻面宝石 / 冰晶）。"""
    obj.data.polygons.foreach_set("use_smooth", [False] * len(obj.data.polygons))
    return obj


def gem2(name, center, size, mat, stretch=(1.0, 0.6, 1.4), seg=10, rings=6):
    """低面数宝石（kit.core.gem 固定 12×8 段，小宝石用不到那么多面，而发光材质不参与游戏版减面）。"""
    s = size
    return ellipsoid(name, center, (s * stretch[0], s * stretch[1], s * stretch[2]), [mat], seg, rings)


def hem_line(ctx, g, name, radius, mat, count=160, lift=0.005, n=5):
    """布料下摆滚边（kit Wrap.build 的 hem 固定 nu*3 个点、6 边管，发光下摆又不参与减面，这里可控点数与边数）。"""
    pts = [radial(g.point(i / (count - 1), 1.0), lift, g.cy) for i in range(count)]
    return ctx.part(tube(name, pts, [radius] * count, [mat], n=n, per=1), garment(g))


def cloth_edges(ctx, g, name, radius, mat, count=32, n=5, top=False):
    """布料开襟 / 垂饰两侧滚边（kit 的 edges 固定 61 点 6 边管，且滚边材质不参与游戏版减面）。
    Wrap 沿径向外推，Panel 沿前后方向外推；top=True 时 Panel 顶边也加一道。"""
    panel = not hasattr(g, "a0")
    for u in (0.0, 1.0):
        if panel:
            pts = [g.point(u, j / (count - 1)) + Vector((0, g.side * 0.003, 0)) for j in range(count)]
        else:
            pts = [radial(g.point(u, j / (count - 1)), 0.004, g.cy) for j in range(count)]
        ctx.part(trim(f"{name} edge {u}", pts, radius, mat, n=n), garment(g))
    if top and panel:
        pts = [g.point(i / 15, 0.0) + Vector((0, g.side * 0.003, 0.002)) for i in range(16)]
        ctx.part(trim(f"{name} top", pts, radius, mat, n=n), garment(g))


def pauldron2(ctx, B, side, label, mat, trim_mat=None, gem_mat=None, lames=3, radius=0.11, spread=1.32,
              rise=1.18, tilt=0.30, spire=0.0, spire_at=-0.30, spire_dir=(0.28, -0.22, 1.0),
              theta=((0.08, 0.92), (0.70, 1.30), (1.10, 1.66)), shrink=(1.0, 0.955, 0.90), thick=0.007,
              trim_r=0.0026, spec=None, ridge=0.0, mats=None, nu=36, nv=9, sub=0, trim_n=36, k0=0):
    """分层肩甲（改写自 kit.humanoid.pauldron：原版 30×9 + 细分固定，六片甲 2.6 万面；这里可调分段与细分，
    mats 可给每片甲单独指定材质，k0 为起始片序号以便分次叠加）。"""
    s = B.s
    shoulder = B.arms[label]["shoulder"] + Vector((0.0, 0.001, 0.02 * s))
    spec = spec or rigid(("Chest", 0.35), (f"UpperArm.{label}", 0.65))

    def lp(k, u, t):
        th0, th1 = theta[k]
        rr = radius * s * shrink[k]
        phi = u * spread
        taper = 1 - abs(u) ** 2.6
        mid, half = (th0 + th1) / 2, (th1 - th0) / 2
        th = mid + (t - 0.5) * 2 * half * taper
        d = Vector((math.cos(phi) * math.sin(th) * side, math.sin(phi) * math.sin(th) * rise, math.cos(th)))
        p = shoulder + d * rr * (1 + 0.06 * (1 - abs(u)) + ridge * math.exp(-(u / 0.12) ** 2))
        if k == 0 and spire:
            sp = spire * s * math.exp(-((u - spire_at) / 0.20) ** 2) * (1 - t) ** 2.0
            p += Vector((side * spire_dir[0], spire_dir[1], spire_dir[2])).normalized() * sp
        return shoulder + Matrix.Rotation(side * tilt, 3, "Y") @ (p - shoulder)
    for k in range(lames):
        m = mats[k] if mats else mat
        lame = surface(f"{ctx.title} pauldron {label}{k + k0}", lambda u, v, k=k: lp(k, 2 * u - 1, v), nu, nv, [m])
        orient(lame, lambda c: shoulder)
        ctx.part(finish(lame, thick, 0, sub), spec)
        if trim_mat:
            edge = [lp(k, 2 * i / trim_n - 1, 1.0) for i in range(trim_n + 1)]
            edge = [p + (p - shoulder).normalized() * 0.004 * s for p in edge]
            ctx.part(trim(f"{ctx.title} pauldron {label}{k + k0} trim", edge, trim_r * s, trim_mat, n=5), spec)
    if gem_mat:
        g = lp(0, 0.25, 0.55)
        g += (g - shoulder).normalized() * 0.006 * s
        ctx.part(ellipsoid(f"{ctx.title} pauldron gem {label}", g, (0.0075 * s,) * 3, [gem_mat], 10, 6), spec)
    return lp, shoulder


def gorget2(ctx, B, mat, trim_mat=None, layers=((1.645, 1.695, 0.090, 0.070), (1.685, 1.735, 0.072, 0.056)),
            nu=40, sub=0):
    """护喉（改写自 kit.humanoid.gorget：原版 48 段 + 细分固定；这里可调）。"""
    s = B.s
    for k, (z0, z1, r0, r1) in enumerate(layers):
        z0, z1 = B.z(z0), B.z(z1)

        def g(u, v, z0=z0, z1=z1, r0=r0 * s, r1=r1 * s):
            a = u * TAU
            z = lerp(z0, z1, v) - 0.018 * s * max(0.0, math.cos(a)) ** 4 * (1 - v)
            r = lerp(r0, r1, v)
            return Vector((r * math.sin(a), 0.004 * s + 0.006 * s * v + r * math.cos(a) * 0.92, z))
        obj = surface(f"{ctx.title} gorget {k}", g, nu, 6, [mat], closed_u=True)
        orient(obj, lambda c: Vector((0, 0, c.z)))
        ctx.part(finish(obj, 0.004 * s, 1, sub), invdist(["Chest", "Neck"]))
        if trim_mat:
            rim = [g(i / nu, 1.0) for i in range(nu)]
            rim = [p + Vector((p.x, p.y - 0.004 * s, 0)).normalized() * 0.005 * s for p in rim]
            ctx.part(trim(f"{ctx.title} gorget {k} trim", rim, 0.0022 * s, trim_mat, closed=True, n=5),
                     invdist(["Chest", "Neck"]))
def crystal(name, base, tip, radius, mats, sides=6, shoulder=0.72, foot=0.70, twist=0.0, seed=0.0,
            up=(0, 0, 1), lean=0.0):
    """刻面晶体：棱柱身 + 棱锥尖，平面着色保留刻面（kit.core.spike 是平滑锥管，读不出晶体感）。
    foot 为底部半径比例，shoulder 为棱柱段占全长比例，lean 让尖端略微偏离轴线显得天然。"""
    b, t = Vector(base), Vector(tip)
    ax = (t - b).normalized()
    length = (t - b).length
    u = Vector(up) - ax * Vector(up).dot(ax)
    if u.length < 1e-5:
        u = ax.orthogonal()
    u.normalize()
    w = ax.cross(u)
    bm = bmesh.new()

    def ring(c, r, k0):
        out = []
        for k in range(sides):
            a = twist + TAU * k / sides
            jitter = 1 + 0.16 * (hash01(k + k0, seed) - 0.5)
            out.append(bm.verts.new(c + (u * math.cos(a) + w * math.sin(a)) * r * jitter))
        return out
    r0 = ring(b, radius * foot, 0)
    r1 = ring(b + ax * length * shoulder, radius, 7)
    apex = bm.verts.new(t + u * lean * radius)
    for k in range(sides):
        k2 = (k + 1) % sides
        bm.faces.new((r0[k], r0[k2], r1[k2], r1[k]))
        bm.faces.new((r1[k], r1[k2], apex))
    bm.faces.new(list(reversed(r0)))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return bm_object(name, bm, mats, smooth=False)


def feather_outline(length, width, root=0.34, belly=0.30, hook=0.10, lead=0.42, n=7):
    """剑形刃羽的二维轮廓（x 沿羽长 0→length，y 为宽度方向）：根部收窄、前 30% 最宽、尖端向前缘微钩。"""
    def w(x):
        if x <= belly:
            return root + (1 - root) * math.sin(math.pi / 2 * x / belly)
        return max(0.0, 1 - ((x - belly) / (1 - belly)) ** 1.5)
    upper = [(k / n * length, width * lead * w(k / n)) for k in range(n)]
    lower = [(k / n * length, -width * (1 - lead) * w(k / n)) for k in range(n - 1, -1, -1)]
    return upper + [(length, width * hook * 0.5)] + lower


def petal_outline(length, width, n=10, tip=0.0):
    """花瓣形刃（展示武器）：宽腹、尖头，两侧对称。"""
    def w(x):
        return math.sin(math.pi * x ** 0.72) ** 0.9 * (1 - 0.15 * x)
    upper = [(k / n * length, width * 0.5 * w(k / n) + 0.004 * width) for k in range(n)]
    lower = [(k / n * length, -width * 0.5 * w(k / n) - 0.004 * width) for k in range(n - 1, -1, -1)]
    return upper + [(length, tip)] + lower


# ===== 程序化贴图（第 0 行为图像底边，与 kit.core 一致） =====
def craquelure_maps(base_rgb, seam_rgb, size=1024, seed=3, cells=11, width=0.030, fine=0.5):
    """骨瓷开片纹（金缮）：Voronoi 细裂纹填玫瑰金色，块面微微明暗不同，法线做细沟。"""
    rng = np.random.default_rng(seed)
    f1, f2, idx = voronoi(size, cells, rng)
    crack = np.clip(1 - (f2 - f1) / width, 0, 1) ** 1.4
    g1, g2, _ = voronoi(size, cells * 3, rng)
    crack = np.maximum(crack, np.clip(1 - (g2 - g1) / (width * 0.55), 0, 1) ** 2 * fine)
    cellv = (np.sin(idx * 2.3) * 0.5 + 0.5)[..., None]
    grain = (box_blur(rng.random((size, size)).astype(np.float32), 10) - 0.5)[..., None]
    tone = 0.93 + 0.07 * cellv + grain * 0.3
    base = np.array(base_rgb)[None, None, :] * tone
    base = base * (1 - crack[..., None]) + np.array(seam_rgb)[None, None, :] * crack[..., None]
    return np.clip(base, 0, 1), None, height_normal(-box_blur(crack.astype(np.float32), 1), 1.3)


GLYPHS = [
    [(0, 0, 0, 1), (0, 1, 1, 1), (1, 1, 1, 0.5)], [(0.5, 0, 0.5, 1), (0, 0.5, 1, 0.5)],
    [(0, 0, 1, 1), (0, 1, 1, 0)], [(0, 1, 0.5, 0), (0.5, 0, 1, 1), (0.25, 0.5, 0.75, 0.5)],
    [(0.5, 0, 0.5, 1), (0, 0.7, 1, 0.7), (0, 0.3, 1, 0.3)], [(0, 1, 1, 1), (0.5, 1, 0.5, 0), (0.2, 0.2, 0.8, 0.2)],
]


def hem_rune_maps(emit_rgb, base_rgb, line_rgb=None, size=1024, seed=13, band=0.13, cols=16, vines=True):
    """下摆符文刺绣：只在贴图底部 band 高度内排一行字形 + 上下双边线 + 卷草波纹，其余为素面。"""
    rng = np.random.default_rng(seed)
    cv = Canvas(size, size)
    y0, h = 0.035 * size, band * size
    for y in (y0, y0 + 6, y0 + h, y0 + h + 6):
        cv.line(0, y, size, y, 1)
    cw = size / cols
    for c in range(cols):
        g = GLYPHS[int(rng.integers(len(GLYPHS)))]
        x0, gy, s = c * cw + cw * 0.25, y0 + h * 0.22, min(cw, h) * 0.52
        for (a, b, cc, d) in g:
            cv.line(x0 + a * s, gy + b * s, x0 + cc * s, gy + d * s, 2)
        cv.dot(c * cw, y0 + h * 0.5, 3)
    if vines:
        xs = np.linspace(0, size, 400)
        ys = y0 + h + 22 + 10 * np.sin(xs / size * TAU * cols / 2)
        for i in range(len(xs) - 1):
            cv.line(xs[i], ys[i], xs[i + 1], ys[i + 1], 1)
        for c in range(cols):
            x = (c + 0.5) * cw
            cv.ring(x, y0 + h + 22 + 10 * math.sin((x / size) * TAU * cols / 2) + 12, 5, 1)
    mask = np.clip(cv.mask, 0, 1)
    line_rgb = line_rgb or tuple(c * 0.25 for c in emit_rgb)
    return _finish(mask, np.ones_like(mask), rng, emit_rgb, base_rgb, line_rgb, sparkle=False, bump=1.5)


def frost_hem_maps(emit_rgb, base_rgb, line_rgb=(0.20, 0.30, 0.34), size=1024, seed=9, roots=30, reach=0.72,
                   stars=46, width=None, fade=(0.12, 0.7)):
    """霜花自下摆向上生长（改写 kit.core.frost_maps：原版满铺随机、无渐隐）：60° 分叉枝晶 + 零星六角霜星，越往上越淡。"""
    rng = np.random.default_rng(seed)
    cv = Canvas(size, size)
    step = 5.0 * size / 1024
    budget = [26000]                                   # 线段总数上限，防止分叉指数爆炸

    def grow(x, y, a, length, w, depth):
        stack = [(x, y, a, length, w, depth)]
        while stack and budget[0] > 0:
            x, y, a, length, w, depth = stack.pop()
            if depth > 3 or length < step * 1.5:
                continue
            for _ in range(int(length / step)):
                nx, ny = x + math.cos(a) * step, y + math.sin(a) * step
                cv.line(x, y, nx, ny, w)
                budget[0] -= 1
                x, y = nx, ny
                a += rng.normal(0, 0.04)
                if rng.random() < 0.11:
                    stack.append((x, y, a + rng.choice([-1, 1]) * math.pi / 3, length * 0.38, max(1, w - 1),
                                  depth + 1))
    for i in range(roots):
        budget[0] = 26000 // roots
        x = (i + rng.uniform(0.2, 0.8)) / roots * size
        grow(x, 1, math.pi / 2 + rng.normal(0, 0.30), rng.uniform(0.25, reach) * size,
             width or max(2, round(2 * size / 1024)), 0)
    for _ in range(stars):
        x, y = rng.uniform(0, size), size * rng.uniform(0.05, 0.8) ** 1.4
        r = rng.uniform(5, 12) * size / 1024
        for k in range(6):
            a = k * math.pi / 3
            cv.line(x, y, x + math.cos(a) * r, y + math.sin(a) * r, 1)
    mask = np.clip(cv.mask, 0, 1)
    return _finish(mask, vfade(size, size, fade[0], fade[1], 1.2), rng, emit_rgb, base_rgb, line_rgb,
                   glow_halo=0.35, bump=1.4)


# ===== 姿态工具 =====
def blend2(a, b, t):
    """两个姿态逐骨球面插值（kit.motion.blend 的扩展：支持 Vector 位移通道，float 与 Vector 可混用）。"""
    out = {}
    for k in set(a) | set(b):
        va, vb = a.get(k), b.get(k)
        vec = isinstance(va, Vector) or isinstance(vb, Vector)
        num = isinstance(va, (int, float)) or isinstance(vb, (int, float))
        if vec or num:
            def as_v(v):
                if v is None:
                    return Vector((0, 0, 0))
                return Vector((0, 0, v)) if isinstance(v, (int, float)) else Vector(v)
            if vec:
                out[k] = as_v(va).lerp(as_v(vb), t)
            else:
                out[k] = lerp(va if va is not None else 0.0, vb if vb is not None else 0.0, t)
            continue
        qa = (va if va is not None else I3).to_quaternion()
        qb = (vb if vb is not None else I3).to_quaternion()
        if qa.dot(qb) < 0:
            qb.negate()
        out[k] = qa.slerp(qb, t).to_matrix()
    return out


def keyed_samples(keys, per=4):
    """关键姿态序列 → 自检用的采样（关键帧 + 相邻关键帧之间的球面插值）。"""
    out = []
    for (_, a), (_, b) in zip(keys, keys[1:]):
        for i in range(per):
            out.append(blend2(a, b, i / per))
    out.append(keys[-1][1])
    return out


def mat_slerp(m, t):
    """把旋转矩阵 m 按比例 t 缩放（与单位阵球面插值）。"""
    q = m.to_quaternion()
    if q.w < 0:
        q.negate()
    return Quaternion().slerp(q, t).to_matrix()


class Clearance:
    """动作穿插自检：刚性件（翅膀、冰晶）上的采样点与身体胶囊体之间的最小间隙，全部用 pose 数学求值。
    points 登记 (骨, 静止位置, 标签)；capsules 登记 (骨, 静止端点 a, b, 半径, 标签)。"""

    def __init__(self):
        self.points, self.caps = [], []

    def point(self, bone, p, tag):
        self.points.append((bone, Vector(p), tag))

    def capsule(self, bone, a, b, r, tag):
        self.caps.append((bone, Vector(a), Vector(b), r, tag))

    @staticmethod
    def world(rig, pose, bone, p, cache):
        return rig.head(pose, bone, cache) + rig.delta(pose, bone, cache) @ (p - rig.SEG[bone][0])

    def gap(self, rig, pose):
        cache = {}
        caps = [(self.world(rig, pose, b, a, cache), self.world(rig, pose, b, c, cache), r, tag)
                for b, a, c, r, tag in self.caps]
        best = (1e9, "", "")
        for bone, p, tag in self.points:
            w = self.world(rig, pose, bone, p, cache)
            for a, c, r, ctag in caps:
                ab = c - a
                t = clamp((w - a).dot(ab) / max(ab.length_squared, 1e-12))
                g = (w - a.lerp(c, t)).length - r
                if g < best[0]:
                    best = (g, tag, ctag)
        return best

    def report(self, rig, clip, poses):
        worst = (1e9, "", "", 0)
        for i, pose in enumerate(poses):
            g, a, b = self.gap(rig, pose)
            if g < worst[0]:
                worst = (g, a, b, i)
        print(f"MOTION CLEARANCE {clip}: min gap {worst[0] * 100:.1f} cm ({worst[1]} vs {worst[2]}) "
              f"sample {worst[3]}/{len(poses)}")
        return worst


# ===== 动作 =====
def dangle2(B, t, pose, swing=0.07, bend=0.32, point=0.55, trail=0.0, phase=1.3):
    """悬浮垂腿（改自 kit.motion.dangle：原版脚掌上勾，这里脚尖绷直下指）；trail 为整体后摆（滑翔时双腿拖在身后）。"""
    for label, sg in (("L", -1), ("R", 1)):
        ph = 0.0 if sg < 0 else phase
        pose[f"Thigh.{label}"] = R((X, 0.10 - trail + swing * math.sin(t + ph)), (Y, sg * -0.03))
        pose[f"Shin.{label}"] = R((X, -bend - 0.06 * math.sin(t + ph + 0.6)))
        pose[f"Foot.{label}"] = R((X, -point))
        pose[f"Toe.{label}"] = R((X, -0.12))
    return pose


def cyc_hermite(keys, p):
    """周期三次 Hermite（非均匀 Catmull-Rom）：keys 为 [(相位, (值, ...)), ...]，相位 ∈ [0,1) 升序。"""
    n = len(keys)
    ps = [k[0] for k in keys]
    p = p % 1.0
    i = n - 1
    for j in range(n):
        if ps[j] <= p:
            i = j
    i1 = (i + 1) % n
    p0 = ps[i] if p >= ps[i] else ps[i] - 1
    p1 = p0 + ((ps[i1] - ps[i]) % 1.0 or 1.0)
    dt = p1 - p0
    u = (p - p0) / dt

    def tangent(j, pj):
        a, b = keys[(j - 1) % n], keys[(j + 1) % n]
        da = (pj - a[0]) % 1.0 or 1.0
        db = (b[0] - pj) % 1.0 or 1.0
        return [(vb - va) / (da + db) for va, vb in zip(a[1], b[1])]
    m0, m1 = tangent(i, ps[i]), tangent(i1, ps[i1])
    h00, h10 = 2 * u ** 3 - 3 * u ** 2 + 1, u ** 3 - 2 * u ** 2 + u
    h01, h11 = -2 * u ** 3 + 3 * u ** 2, u ** 3 - u ** 2
    return [h00 * a + h10 * dt * ma + h01 * b + h11 * dt * mb
            for a, b, ma, mb in zip(keys[i][1], keys[i1][1], m0, m1)]


# 单脚滑冰轨迹关键点：(相位, (横向外移, 前后, 抬高, 外撇, 脚尖下压))，单位为身高比例 / 弧度
SKATE_TRACK = [
    (0.00, (0.012, 0.085, 0.000, 0.05, 0.00)),    # 前送落冰
    (0.20, (0.018, 0.010, 0.000, 0.06, 0.00)),    # 长滑行
    (0.40, (0.055, -0.085, 0.000, 0.26, 0.00)),   # 开始蹬冰
    (0.56, (0.215, -0.190, 0.000, 0.52, 0.06)),   # 侧后蹬出
    (0.68, (0.235, -0.330, 0.105, 0.42, 0.55)),   # 离冰，浮足后伸
    (0.80, (0.170, -0.300, 0.135, 0.26, 0.60)),   # 浮足抬高保持
    (0.91, (0.055, -0.070, 0.070, 0.10, 0.30)),   # 收回
]
ON_ICE = 0.575


def glide_skate(rig, B, t, lean=0.14, sink=0.075, shift=0.040, arm=0.30, pose=None):
    """优雅冰上滑行（改写 kit.motion.skate：原版蹬冰短促、上身晃动大）：长滑步 + 侧后蹬冰 + 浮足后伸抬起，
    重心横移到滑行脚上方、上身平稳、双臂向体侧后方舒展。t∈[0,2π) 左右各一步。"""
    s = B.s
    pose = {} if pose is None else pose
    legs = Legs(rig, B)
    glide_l = math.cos(t - 1.26)                  # 左脚滑行中段为 +1，右脚滑行中段为 -1
    pose["_hover"] = Vector((-shift * s * glide_l, 0.0, -sink * s + 0.016 * s * math.cos(2 * t - 0.5)))
    pose["Pelvis"] = R((Z, -0.10 * glide_l), (Y, -0.045 * glide_l), (X, -lean))
    pose["Spine"] = R((Z, 0.06 * glide_l), (X, -0.03))
    pose["Chest"] = R((Z, 0.05 * glide_l), (Y, 0.03 * glide_l), (X, 0.015 * math.cos(2 * t)))
    pose["Neck"] = R((X, lean * 0.45), (Z, -0.01 * glide_l))
    pose["Head"] = R((X, lean * 0.35 - 0.02), (Z, 0.0))
    for label, ph in (("L", 0.0), ("R", 0.5)):
        side = -1 if label == "L" else 1
        p = (t / TAU + ph) % 1.0
        dx, dy, dz, yaw, pitch = cyc_hermite(SKATE_TRACK, p)
        if p < ON_ICE:
            dz = 0.0
        base = legs.rest[label]["ankle"]
        a = Vector((base.x + side * dx * s, base.y + dy * s, base.z + max(0.0, dz) * s))
        legs.plant(pose, label, a, pitch=pitch, yaw=-side * yaw, knee_out=0.22)
    for label in ("L", "R"):
        side = -1 if label == "L" else 1
        sw = math.sin(t + (0.0 if label == "L" else math.pi) + 0.6)
        rig.aim(pose, f"UpperArm.{label}", (side * 0.60, -0.22 + arm * 0.35 * sw, -0.77))
        rig.aim(pose, f"Forearm.{label}", (side * 0.52, -0.02 + arm * 0.30 * sw, -0.85))
        rig.aim(pose, f"Hand.{label}", (side * 0.40, 0.10, -0.90))
    return pose
