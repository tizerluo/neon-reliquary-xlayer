"""Boss 私有工具（boss-0 … boss-3 共用，不属于 kit）：

- 带 UV 的扫掠管 / 超椭球 / 火舌 / 锁链 / 铆钉（kit 的 tube、ellipsoid 没有 UV，程序化贴图会糊成一点）
- 姿态混合（kit.motion.blend 不支持 Vector 位移键和缩放键，这里补上）
- 带缩放通道的动作写入（pose["_scale"] = {骨名: 倍率}，用于火焰 / 光环“爆燃”）
- 参数轨道插值（关键参数 + 缓动 → 每帧重算 IK，脚不打滑）
- 自建骨链登记进 MOTION CHECK，外加地面穿插与循环接缝检查
"""

import math

import bmesh
import bpy
from mathutils import Matrix, Quaternion, Vector

from kit.core import TAU, bm_object, catmull, clamp, lerp, smoothstep, surface
from kit.rig import I3, R, X, Y, Z


# ===== 缓动 =====
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


def ease_lin(t):
    return clamp(t)


EASE = {"io": ease_io, "in": ease_in, "out": ease_out, "back": ease_back, "lin": ease_lin}


# ===== 路径与扫掠 =====
def path_frames(pts, up=(0, 0, 1)):
    """折线的平行传输标架：返回 (切向, 法向, 副法向) 三个列表。"""
    m = len(pts)
    T = []
    for i in range(m):
        d = pts[min(i + 1, m - 1)] - pts[max(i - 1, 0)]
        T.append(d.normalized())
    upv = Vector(up)
    n0 = upv - T[0] * upv.dot(T[0])
    if n0.length < 1e-5:
        n0 = Vector((1, 0, 0)) - T[0] * T[0].x
    N = [n0.normalized()]
    for i in range(1, m):
        nn = N[-1] - T[i] * N[-1].dot(T[i])
        N.append(nn.normalized() if nn.length > 1e-6 else N[-1])
    return T, N, [t.cross(n) for t, n in zip(T, N)]


def resample(points, radii=None, per=6):
    pts, rad = catmull([Vector(p) for p in points], radii or [1.0] * len(points), per)
    return pts, rad


def sweep(name, points, radii, mats, n=16, per=4, fx=1.0, fy=1.0, up=(0, 0, 1), tile=None, shape=None,
          twist=0.0):
    """带 UV 的扫掠管（基于 surface，法线朝外）：u 绕截面、v 沿路径。
    tile 为贴图一格对应的米数（None 时 UV 为 0..1）；shape(a, t) 返回截面半径倍率（棱线、凸起）。"""
    pts, rad = catmull([Vector(p) for p in points], list(radii), per) if per > 1 else \
        ([Vector(p) for p in points], list(radii))
    T, N, Bn = path_frames(pts, up)
    m = len(pts)
    acc = [0.0]
    for i in range(1, m):
        acc.append(acc[-1] + (pts[i] - pts[i - 1]).length)
    L = acc[-1] or 1.0

    def idx(v):
        return min(m - 1, int(round(v * (m - 1))))

    def fn(u, v):
        j = idx(v)
        a = u * TAU + twist
        r = rad[j] * (shape(a, acc[j] / L) if shape else 1.0)
        return pts[j] + N[j] * (math.cos(a) * r * fx) + Bn[j] * (math.sin(a) * r * fy)
    uvfn = None
    if tile:
        circ = TAU * max(rad) * (fx + fy) * 0.5
        ru = max(1, round(circ / tile))
        uvfn = lambda u, v: (u * ru, acc[idx(v)] / tile)   # noqa: E731
    return surface(name, fn, n, m, mats, closed_u=True, uvfn=uvfn)


def blob(name, center, radii, mats, nu=32, nv=20, power=2.0, frame=None, shape=None, tile=None):
    """带 UV 的超椭球：power>2 更方、<2 更尖；frame 为 3x3 朝向矩阵（列为局部 x/y/z）；
    shape(p_local) 返回额外的径向外扩（米）。"""
    c = Vector(center)
    M = frame or Matrix.Identity(3)
    e = 2.0 / power

    def sgnpow(x, k):
        return math.copysign(abs(x) ** k, x)

    def fn(u, v):
        a = u * TAU
        phi = math.pi * v
        sx, cx = math.sin(phi), math.cos(phi)
        local = Vector((sgnpow(sx, e) * sgnpow(math.sin(a), e) * radii[0],
                        sgnpow(sx, e) * sgnpow(math.cos(a), e) * radii[1],
                        sgnpow(cx, e) * radii[2]))
        if shape:
            d = local.normalized() if local.length > 1e-9 else Vector((0, 0, 1))
            local = local + d * shape(local)
        return c + M @ local
    uvfn = None
    if tile:
        circ = TAU * max(radii[0], radii[1])
        ru = max(1, round(circ / tile))
        uvfn = lambda u, v: (u * ru, (1 - v) * math.pi * radii[2] / tile)   # noqa: E731
    return surface(name, fn, nu, nv, mats, closed_u=True, uvfn=uvfn)


def flame(name, base, direction, height, radius, mats, lobes=5, twist=1.4, nu=20, nv=12, seed=0.0):
    """火舌 / 冰焰：沿 direction 伸出、扭转的花瓣锥，底部圆、顶端收尖（通常用自发光材质）。"""
    b = Vector(base)
    d = Vector(direction).normalized()
    side = d.orthogonal().normalized()
    other = d.cross(side)

    def fn(u, v):
        a = u * TAU
        body = (1 - v) ** 0.9 * (0.55 + 0.45 * math.sin(math.pi * min(1.0, v * 1.6 + 0.35)))
        petal = 1 + 0.38 * math.sin(lobes * a + twist * v * TAU + seed) * smoothstep(0.1, 0.6, v)
        r = radius * body * petal
        wob = 0.10 * height * v ** 1.5 * math.sin(seed * 1.7 + v * 5.0)
        return b + d * (height * v) + side * (math.cos(a) * r + wob) + other * (math.sin(a) * r)
    return surface(name, fn, nu, nv, mats, closed_u=True)


# ===== 批量小件（一次 bmesh 生成，避免成百上千个对象） =====
def _frame_z(normal):
    n = Vector(normal).normalized()
    a = n.orthogonal().normalized()
    return a, n.cross(a), n


def studs(name, items, mats, seg=8, rings=4, dome=0.55):
    """铆钉 / 宝石钉：items 为 [(中心, 法向, 半径), ...]，半球冠朝法向。"""
    bm = bmesh.new()
    for c, nrm, r in items:
        a, b, n = _frame_z(nrm)
        c = Vector(c)
        top = bm.verts.new(c + n * r * dome)
        ringv = []
        for j in range(1, rings + 1):
            phi = (math.pi / 2) * j / rings
            row = []
            for k in range(seg):
                t = TAU * k / seg
                row.append(bm.verts.new(c + (a * math.cos(t) + b * math.sin(t)) * r * math.sin(phi)
                                        + n * r * dome * math.cos(phi)))
            ringv.append(row)
        for k in range(seg):
            bm.faces.new((top, ringv[0][k], ringv[0][(k + 1) % seg]))
        for j in range(rings - 1):
            for k in range(seg):
                k2 = (k + 1) % seg
                bm.faces.new((ringv[j][k], ringv[j + 1][k], ringv[j + 1][k2], ringv[j][k2]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return bm_object(name, bm, mats)


def chain_links(name, path, link_len, wire, mats, width=None, seg=10, sides=5, phase=0.0):
    """沿路径摆放交替正交的椭圆链环（环面），返回单个网格对象；link_len 为单环外长。"""
    pts, _ = resample(path, per=8)
    acc = [0.0]
    for i in range(1, len(pts)):
        acc.append(acc[-1] + (pts[i] - pts[i - 1]).length)
    total = acc[-1]
    step = link_len * 0.78
    count = max(2, int(total / step))
    T, N, Bn = path_frames(pts, (0, 0, 1) if abs((pts[-1] - pts[0]).normalized().z) < 0.9 else (1, 0, 0))
    width = width or link_len * 0.62
    bm = bmesh.new()

    def at(s):
        for i in range(1, len(acc)):
            if acc[i] >= s:
                t = (s - acc[i - 1]) / max(1e-9, acc[i] - acc[i - 1])
                return pts[i - 1].lerp(pts[i], t), T[i], N[i], Bn[i]
        return pts[-1], T[-1], N[-1], Bn[-1]
    for k in range(count):
        c, t, n, b = at((k + 0.5) * total / count)
        ang = phase + (math.pi / 2 if k % 2 else 0.0)
        side = n * math.cos(ang) + b * math.sin(ang)
        A, Bw = link_len * 0.5 - wire, width * 0.5 - wire
        rings = []
        for i in range(seg):
            th = TAU * i / seg
            # 椭圆主环（沿切向拉长）
            p = c + t * (math.cos(th) * A) + side * (math.sin(th) * Bw)
            tan = (-t * math.sin(th) * A + side * math.cos(th) * Bw).normalized()
            out = (p - c).normalized()
            perp = tan.cross(out).normalized()
            row = [bm.verts.new(p + out * math.cos(TAU * j / sides) * wire + perp * math.sin(TAU * j / sides) * wire)
                   for j in range(sides)]
            rings.append(row)
        for i in range(seg):
            i2 = (i + 1) % seg
            for j in range(sides):
                j2 = (j + 1) % sides
                bm.faces.new((rings[i][j], rings[i2][j], rings[i2][j2], rings[i][j2]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return bm_object(name, bm, mats)


def shards(name, items, mats, sides=4):
    """一批尖晶 / 余烬碎片：items 为 [(底, 尖, 半径), ...]，双锥体。"""
    bm = bmesh.new()
    for base, tip, r in items:
        base, tip = Vector(base), Vector(tip)
        d = tip - base
        a, b, n = _frame_z(d)
        mid = base + d * 0.35
        bot = bm.verts.new(base)
        top = bm.verts.new(tip)
        ring = [bm.verts.new(mid + (a * math.cos(TAU * k / sides) + b * math.sin(TAU * k / sides)) * r)
                for k in range(sides)]
        for k in range(sides):
            k2 = (k + 1) % sides
            bm.faces.new((bot, ring[k2], ring[k]))
            bm.faces.new((top, ring[k], ring[k2]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return bm_object(name, bm, mats, smooth=False)


# ===== 程序化贴图（kit 版本的变体） =====
def magma_maps(emit_rgb, base_rgb=(0.018, 0.016, 0.020), size=1024, seed=7, cells=5, width=0.05, fine=0.22,
               heat=1.0, hot=0.3):
    """黑曜熔岩：比 kit.crack_maps 更大的块面、更少的细裂纹；部分块面内部透出暗红余温。"""
    import numpy as np
    from kit.core import box_blur, height_normal, voronoi
    rng = np.random.default_rng(seed)
    f1, f2, idx = voronoi(size, cells, rng)
    crack = np.clip(1 - (f2 - f1) / width, 0, 1) ** 1.4
    g1, g2, _ = voronoi(size, cells * 2, rng)
    crack = np.maximum(crack, np.clip(1 - (g2 - g1) / (width * 0.32), 0, 1) ** 2 * fine)
    cellh = (np.sin(idx * 12.9898 + seed) * 43758.5453) % 1.0
    warm = np.where(cellh > 1 - hot, 1.0, 0.0) * np.clip(1 - f1 / 0.75, 0, 1) ** 2 * 0.10
    ember = box_blur(crack, 4)
    glow = np.clip(crack + ember * 0.30 + warm, 0, 1.2) * heat
    em = np.stack([glow * c for c in emit_rgb], axis=2)
    tone = (0.75 + 0.5 * ((np.sin(idx * 3.1 + seed) * 0.5 + 0.5)))[..., None]
    base = np.array(base_rgb)[None, None, :] * tone
    base = base + ember[..., None] * np.array(emit_rgb)[None, None, :] * 0.10
    hgt = np.clip(f1 * 0.5, 0, 0.4) * 0 + np.clip((f2 - f1) / 0.25, 0, 1) ** 0.5 - crack * 0.8
    return np.clip(base, 0, 1), np.clip(em, 0, 1), height_normal(box_blur(hgt.astype(np.float32), 1), 2.2)


def streak_maps(emit_rgb, base_rgb=(0.02, 0.06, 0.12), size=512, bands=5, turns=3.0, seed=3, floor=0.18,
                hot_rgb=None):
    """螺旋流光：用于火舌 / 霜息锥（UV 的 u 绕一圈、v 沿长度）。斜向条带在 u 方向首尾相接，
    叠加噪声抖动；尖端（v→1）渐暗。纯自发光锥体在 AgX 下会发成一整块，靠条带拉出层次。
    hot_rgb：条带高亮处渐变到的“炽热色”（火焰：暗处深红橙 → 亮处黄白），None 则单色。"""
    import numpy as np
    from kit.core import box_blur
    rng = np.random.default_rng(seed)
    y, x = np.mgrid[0:size, 0:size].astype(np.float32) / size      # x = u（绕向），y = 1 - v
    v = 1.0 - y
    noise = box_blur(rng.random((size, size)).astype(np.float32), 12)
    noise = (noise - noise.min()) / max(1e-6, noise.max() - noise.min())
    ph = TAU * (x * bands + v * turns) + (noise - 0.5) * 3.0
    band = (0.5 + 0.5 * np.sin(ph)) ** 3
    fine = (0.5 + 0.5 * np.sin(ph * 3.0 + noise * 5.0)) ** 6 * 0.35
    fade = np.clip(1.0 - v * 0.65, 0, 1) * np.clip(v * 8.0, 0, 1) ** 0.5
    glow = np.clip((floor + (1 - floor) * np.clip(band + fine, 0, 1)) * fade, 0, 1)
    if hot_rgb is None:
        em = np.stack([glow * c for c in emit_rgb], axis=2)
    else:
        # 按条带亮度在两色间插值：亮带偏黄白、暗带偏深红，AgX 下仍能保住火焰的色相层次
        w = np.clip((glow - floor * 0.5) / max(1e-6, 1 - floor * 0.5), 0, 1) ** 1.5
        em = np.stack([glow * (c0 * (1 - w) + c1 * w) for c0, c1 in zip(emit_rgb, hot_rgb)], axis=2)
    base = np.array(base_rgb)[None, None, :] * (0.6 + 0.4 * glow[..., None])
    return np.clip(base, 0, 1), np.clip(em, 0, 1), None


def panel_maps(base_rgb, seam_rgb, rivet_rgb, size=1024, cols=3, rows=3, seed=8, seam=0.012, rivet=0.018, per=6):
    """铆接装甲板：错缝矩形板块 + 深色焊缝 + 沿板边一圈亮色铆钉 + 轻微锈蚀 / 磨损斑。"""
    import numpy as np
    from kit.core import box_blur, height_normal
    rng = np.random.default_rng(seed)
    y, x = np.mgrid[0:size, 0:size].astype(np.float32) / size
    gy = y * rows
    row = np.floor(gy)
    gx = x * cols + (row % 2) * 0.5                     # 隔行错缝
    fx, fy = gx % 1.0, gy % 1.0
    cid = (np.floor(gx) % cols) + row * cols
    ex = np.minimum(fx, 1 - fx) / cols                  # 到竖缝距离（贴图单位）
    ey = np.minimum(fy, 1 - fy) / rows
    edge = np.minimum(ex, ey)
    groove = np.clip(1 - edge / seam, 0, 1) ** 1.5
    # 铆钉：距板边 2.2 倍缝宽的一圈，按等距点阵
    inset = seam * 2.4
    rv = np.zeros_like(x)
    for axis in range(2):
        f_along = fy if axis == 0 else fx
        n_along = rows if axis == 0 else cols
        d_edge = ex if axis == 0 else ey
        k = np.round(f_along * per) / per
        d_along = np.abs(f_along - k) / n_along
        d = np.sqrt((d_edge - inset) ** 2 + d_along ** 2)
        rv = np.maximum(rv, np.clip(1 - d / rivet, 0, 1))
    rivets = rv ** 0.7
    grain = box_blur(rng.random((size, size)).astype(np.float32), 20)
    grain = (grain - grain.mean()) / max(1e-6, grain.std())
    tone = 0.85 + 0.30 * ((np.sin(cid * 7.13 + seed) * 43758.5) % 1.0)[..., None] + 0.06 * grain[..., None]
    base = np.array(base_rgb)[None, None, :] * tone
    base = base * (1 - groove[..., None]) + np.array(seam_rgb)[None, None, :] * groove[..., None]
    base = base * (1 - rivets[..., None]) + np.array(rivet_rgb)[None, None, :] * rivets[..., None]
    hgt = 1 - groove + rivets * 0.8 + grain * 0.02
    return np.clip(base, 0, 1), None, height_normal(box_blur(hgt.astype(np.float32), 1), 2.0)


def dial_maps(face_rgb, tick_rgb=(0.08, 0.04, 0.02), size=256, ticks=36, red=(0.62, 0.82)):
    """仪表盘面（UV 以 0.5,0.5 为圆心）：径向渐亮的琥珀底 + 刻度 + 红区弧段 + 中心轴帽。"""
    import numpy as np
    y, x = np.mgrid[0:size, 0:size].astype(np.float32) / size - 0.5
    r = np.sqrt(x * x + y * y) * 2
    a = (np.arctan2(x, y) / TAU) % 1.0
    face = np.clip(1.15 - r * 0.55, 0, 1)
    tick = (np.abs(((a * ticks) % 1.0) - 0.5) > 0.40) & (r > 0.72) & (r < 0.88)
    major = (np.abs(((a * ticks / 4) % 1.0) - 0.5) > 0.47) & (r > 0.62) & (r < 0.90)
    arc = (a > red[0]) & (a < red[1]) & (r > 0.90) & (r < 0.96)
    hub = r < 0.12
    ring = (r > 0.96)
    mark = tick | major | hub | ring
    em = np.stack([face * c for c in face_rgb], axis=2)
    em[mark] = 0.0
    em[arc] = (1.0, 0.12, 0.04)
    base = em * 0.8
    base[mark] = tick_rgb
    return np.clip(base, 0, 1), np.clip(em, 0, 1), None


def hermite(knots, x):
    """非均匀节点的三次 Hermite（Catmull-Rom 切线）插值：knots 为 [(x, v1, v2, ...), ...]，返回各分量。"""
    n = len(knots)
    xs = [k[0] for k in knots]
    if x <= xs[0]:
        return list(knots[0][1:])
    if x >= xs[-1]:
        return list(knots[-1][1:])
    i = max(j for j in range(n - 1) if xs[j] <= x)
    h = xs[i + 1] - xs[i]
    t = (x - xs[i]) / h
    i0, i3 = max(i - 1, 0), min(i + 2, n - 1)
    out = []
    for c in range(1, len(knots[0])):
        p0, p1, p2, p3 = knots[i0][c], knots[i][c], knots[i + 1][c], knots[i3][c]
        m1 = (p2 - p0) / max(1e-9, xs[i + 1] - xs[i0]) * h
        m2 = (p3 - p1) / max(1e-9, xs[i3] - xs[i]) * h
        t2, t3 = t * t, t * t * t
        out.append((2 * t3 - 3 * t2 + 1) * p1 + (t3 - 2 * t2 + t) * m1 + (-2 * t3 + 3 * t2) * p2 + (t3 - t2) * m2)
    return out


# ===== KD 树蒙皮（按最近采样点取预先算好的权重） =====
class KDWeights:
    """采样点 + 权重字典 → 顶点取最近采样点的权重。用于盘绕躯干（按弧长分段）和翼膜（按翼骨插值），
    避免 kit.chain 权重在“双向骨链”或盘绕路径上找错最近骨。"""

    def __init__(self):
        self.pts, self.ws, self.kd = [], [], None

    def add(self, p, w):
        self.pts.append(Vector(p))
        self.ws.append(w)

    def build(self):
        from mathutils.kdtree import KDTree
        self.kd = KDTree(len(self.pts))
        for i, p in enumerate(self.pts):
            self.kd.insert(p, i)
        self.kd.balance()
        return self

    def __call__(self, p):
        if self.kd is None:
            self.build()
        _, i, _ = self.kd.find(p)
        return self.ws[i]


def interval_weights(s, bounds, win):
    """沿弧长 s 的分段权重：bounds 为 [(骨名, s0, s1), ...]，关节两侧 win 内线性混合。"""
    w = {}
    for name, s0, s1 in bounds:
        a = clamp((s - (s0 - win)) / (2 * win)) if s0 > bounds[0][1] + 1e-6 else 1.0
        b = clamp(((s1 + win) - s) / (2 * win)) if s1 < bounds[-1][2] - 1e-6 else 1.0
        v = min(a, b)
        if v > 1e-4:
            w[name] = v
    tot = sum(w.values()) or 1.0
    return {k: v / tot for k, v in w.items()}


# ===== 姿态混合与参数轨道 =====
def mix(a, b, t):
    """两个姿态混合：旋转球面插值，浮点 / Vector 位移线性插值，"_scale" 字典逐骨线性插值。"""
    out = {}
    for k in set(a) | set(b):
        va, vb = a.get(k), b.get(k)
        if k == "_scale":
            da, db = va or {}, vb or {}
            out[k] = {n: lerp(da.get(n, 1.0), db.get(n, 1.0), t) for n in set(da) | set(db)}
        elif isinstance(va, (int, float)) or isinstance(vb, (int, float)):
            out[k] = lerp(va or 0.0, vb or 0.0, t)
        elif isinstance(va, Vector) or isinstance(vb, Vector):
            za = va if va is not None else Vector((0, 0, 0))
            zb = vb if vb is not None else Vector((0, 0, 0))
            out[k] = za.lerp(zb, t)
        else:
            qa = (va or I3).to_quaternion()
            qb = (vb or I3).to_quaternion()
            if qa.dot(qb) < 0:
                qb.negate()
            out[k] = qa.slerp(qb, t).to_matrix()
    return out


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
    """把每个关键参数字典补齐为 base 的完整副本，方便只写变化量。"""
    return [(f, {**base, **p}, e) for f, p, e in keys]


# ===== 动作写入（带缩放通道） =====
def put(rig, pose, frame):
    rig.put_pose(pose, frame)
    sc = pose.get("_scale", {})
    for name in getattr(rig, "scaled", ()):
        pb = rig.obj.pose.bones[name]
        v = sc.get(name, 1.0)
        pb.scale = (v, v, v) if isinstance(v, (int, float)) else tuple(v)
        pb.keyframe_insert("scale", frame=frame, group=name)


def loop(rig, name, frames, fn, step=1):
    """循环动作：fn(t) 的 t 从 0 走到 2π（首尾同相位，接缝无跳变）。"""
    rig.new_action(name)
    for f in range(0, frames + 1, step):
        put(rig, fn(TAU * f / frames), f + 1)


def sampled(rig, name, frames, fn, step=1):
    """一次性动作：fn(帧号) 逐帧重算（帧号从 1 到 frames+1）。"""
    rig.new_action(name)
    for f in range(1, frames + 2, step):
        put(rig, fn(f), f)


# ===== 自建骨链登记（进 kit 的 MOTION CHECK） =====
class ChainSet:
    """kit.rig.motion_check 只看 g.prefix / g.K / g.J：骨名须为 {prefix}{k}.{j}（j 从 1 到 J）。"""

    def __init__(self, prefix, K, J):
        self.prefix, self.K, self.J = prefix, K, J


def register_chains(rig, prefix, K, J):
    rig.garments.append(ChainSet(prefix, K, J))


# ===== 检查 =====
def ground_check(rig, clips, bones, label="ground", offset=0.0):
    """逐帧统计给定骨（头尾两端）的最低高度，offset 为骨到部件底面的距离，用于查地面穿插。"""
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
        print(f"MOTION CHECK+ {clip}: min {label} clearance {lo[0]:.3f} m at {lo[1]} frame {lo[2]}")


def seam_check(rig, clips):
    """循环动作首尾帧的最大骨旋转差（度）与位移差（米），应为 0。"""
    scene = bpy.context.scene
    for clip in clips:
        act = bpy.data.actions[clip]
        rig.obj.animation_data.action = act
        first, last = map(int, act.frame_range)
        snap = []
        for f in (first, last):
            scene.frame_set(f)
            snap.append({pb.name: (pb.matrix.to_quaternion(), pb.matrix.to_translation(), pb.matrix.to_scale())
                         for pb in rig.obj.pose.bones})
        worst, where, move = 0.0, "", 0.0
        for name, (qa, ta, sa) in snap[0].items():
            qb, tb, sb = snap[1][name]
            ang = math.degrees(qa.rotation_difference(qb).angle)
            ang = min(ang, 360 - ang)
            if ang > worst:
                worst, where = ang, name
            move = max(move, (ta - tb).length, (sa - sb).length)
        print(f"MOTION CHECK+ {clip}: loop seam {worst:.2f} deg / {move:.4f} m {where}")


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
