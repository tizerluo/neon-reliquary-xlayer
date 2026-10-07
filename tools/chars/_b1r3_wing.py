"""Boss 1（苍白巨龙）第三轮私有模块：真正的龙翼。

结构：肩（银甲轴毂 + 冰核）→ 粗壮肱骨 → 肘 → 前臂主翼骨 → 腕（拇指冰爪）→ 5 根长指骨呈扇形展开，
翼膜张在相邻指骨之间，最后一片连到前臂 / 肱骨 / 躯干侧面，后缘做成内凹的“蝙蝠翼”扇边，每根指骨尖带冰晶爪。
- 翼骨：深冰蓝钢芯 + 银甲套筒（背脊棱线）+ 银箍 + 发光关节节点 + 顶面嵌线；前缘一排大小有层次的刻面冰刺。
- 翼膜：半透明冰蓝薄膜（RGBA 贴图，单面薄片 + 双面材质），内有青色发光翼脉自腕部沿扇面分叉、霜花 / 六角冰纹只在局部点缀。
  材质 Alpha 与 Base Color 取自同一张图，glTF 导出为 alphaMode=BLEND + doubleSided（做法同 Boss 2 的半透明火舌）。
- 动作所需的“展开 / 收拢 / 肘弯”轴都在这里算好（wing_axes）。

不改 kit 与 _bossA_common（后者被 Boss 0 / Boss 2 共用）。
"""

import math

import bpy
import numpy as np
from mathutils import Matrix, Vector

from kit.core import TAU, box_blur, clamp, ellipsoid, fn, hex_maps, lerp, rigid, smoothstep, surface
from kit.core import trim as _trim

from chars._bossA_common import KDWeights, blob, sweep
from chars._b1r2_parts import crystals

# ===== 翼型常量（右翼，x 向外；左翼 x 取反） =====
SHOULDER = (0.98, 0.00, 4.15)
ELBOW = (2.25, -0.95, 4.85)       # 肱骨放平：龙首冠角后掠到肩背上方，翼臂上扬时要绕开它
WRIST = (3.55, -0.15, 6.05)
# (方向 x 外 / y 前 / z 上, 长度)：F0 领头向前上，F4 最靠后向下；扇面张角约 110°
FINGERS = [((0.88, 0.42, 0.30), 2.30), ((0.95, -0.15, -0.12), 2.85), ((0.68, -0.55, -0.45), 2.95),
           ((0.42, -0.72, -0.70), 2.80), ((0.16, -0.62, -0.95), 2.30)]
SCALLOP = (0.26, 0.28, 0.28, 0.26, 0.18)      # 各片翼膜后缘内凹深度


def trim(name, points, radius, mat, closed=False, n=None, per=1):
    """控面版滚边：细管（半径 < 3 cm）用 4 边菱形截面，粗管 6 边（本配方所有细管都走这里）。"""
    if n is None:
        n = 4 if radius < 0.030 else 6
    return _trim(name, points, radius, mat, closed, n, per)


def gem(name, center, size, mat, stretch=(1.0, 0.6, 1.4)):
    """低面数宝石（10×6 分段，原版 12×8）。"""
    s = size
    return ellipsoid(name, center, (s * stretch[0], s * stretch[1], s * stretch[2]), [mat], 10, 6)


def _ss(a, b, x):
    t = np.clip((x - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


class WingGeo:
    """单侧翼的静止几何：关节、指骨路径、翼膜参数面。side=-1 左、+1 右。"""

    def __init__(self, side, b0=None):
        self.side = side
        P = lambda p: Vector((side * p[0], p[1], p[2]))   # noqa: E731
        self.S, self.E, self.W = P(SHOULDER), P(ELBOW), P(WRIST)
        self.F = [(P(d).normalized(), L) for d, L in FINGERS]
        self.B0 = b0
        n = self.F[0][0].cross(self.F[-1][0])
        self.n = (n if n.z > 0 else -n).normalized()            # 翼面法向（朝上）
        # 指骨弓弯方向：翼面内、垂直于指骨、指向前缘一侧
        self.bow = []
        for k, (d, L) in enumerate(self.F):
            ref = (self.F[k - 1][0] - d) if k > 0 else (d - self.F[1][0])
            b = ref - d * ref.dot(d)
            self.bow.append(b.normalized())

    # ----- 骨骼路径 -----
    def finger(self, k, t):
        """第 k 根指骨中线上的点（带轻微弓弯，t 从腕 0 到尖 1）。"""
        d, L = self.F[k]
        return self.W + d * (L * t) + self.bow[k] * (0.06 * L * math.sin(math.pi * t))

    def tip(self, k):
        return self.finger(k, 1.0)

    def inner(self, v):
        """内侧翼膜的前缘：腕 → 肘 → 肩 → 躯干附着点。"""
        if v < 0.36:
            return self.W.lerp(self.E, v / 0.36)
        if v < 0.70:
            return self.E.lerp(self.S, (v - 0.36) / 0.34)
        return self.S.lerp(self.B0, (v - 0.70) / 0.30)

    # ----- 翼膜参数面 -----
    def membrane_pt(self, k, u, v):
        """k=0..3 指间翼膜，k=4 末指到前臂 / 肱骨 / 躯干的内侧翼膜。u 横跨、v 从腕到后缘。"""
        a = self.finger(k, v)
        b = self.finger(k + 1, v) if k < 4 else self.inner(v)
        p = a.lerp(b, u)
        ramp = float(_ss(0.30, 1.0, v))
        p = p + (self.W - p) * (SCALLOP[k] * (math.sin(math.pi * u) ** 1.15) * ramp)   # 后缘内凹成扇边
        bulge = 0.16 * (math.sin(math.pi * u) ** 0.8) * (v ** 0.8) * (1.0 - 0.40 * v)    # 翼膜轻微鼓起
        return p + self.n * bulge


def wing_axes(g):
    """动作用的静止空间轴：翼面内开合轴（沿法向）、肘弯轴、各指骨相对 F0 的夹角。"""
    nw = g.F[0][0].cross(g.F[-1][0]).normalized()            # 绕它正转 = F0 向 F4 转（指骨向后张开）
    ang = [math.acos(clamp(g.F[0][0].dot(d))) for d, _ in g.F]
    # 肘弯轴：使前臂向肱骨折回（腕靠近肩）
    ah = (g.E - g.S).normalized()
    af = (g.W - g.E).normalized()
    ax = ah.cross(af).normalized()
    test = (g.E + Matrix.Rotation(0.2, 3, ax) @ (g.W - g.E) - g.S).length
    if test > (g.W - g.S).length:
        ax = -ax
    return nw, ang, ax


# ===== 翼膜贴图 =====
def _seg(canvas, x0, y0, x1, y1, w, val):
    """抗锯齿线段（取最大值叠加）：像素坐标，w 为高斯半宽。"""
    h, ww = canvas.shape
    pad = int(w * 3) + 2
    xa, xb = int(max(0, min(x0, x1) - pad)), int(min(ww - 1, max(x0, x1) + pad))
    ya, yb = int(max(0, min(y0, y1) - pad)), int(min(h - 1, max(y0, y1) + pad))
    if xb < xa or yb < ya:
        return
    ys, xs = np.mgrid[ya:yb + 1, xa:xb + 1].astype(np.float32)
    dx, dy = x1 - x0, y1 - y0
    t = np.clip(((xs - x0) * dx + (ys - y0) * dy) / (dx * dx + dy * dy + 1e-9), 0, 1)
    d2 = (xs - (x0 + t * dx)) ** 2 + (ys - (y0 + t * dy)) ** 2
    sl = canvas[ya:yb + 1, xa:xb + 1]
    np.maximum(sl, val * np.exp(-d2 / (w * w)), out=sl)


def _branch(rng, canvas, size, x, y, ang, length, width, val, depth, step=0.012):
    """一根侧脉：从 (x, y) 沿 ang（0 为 +v，正为向 +u）前进，轻微弯曲、逐渐变细变暗，中途再分一次小叉。"""
    n = int(length / step)
    for i in range(n):
        ang += 0.5 * (rng.random() - 0.5) * 0.12 - 0.015 * ang          # 向 +v 回正
        nx, ny = x + math.sin(ang) * step, y + math.cos(ang) * step
        if nx < 0.015 or nx > 0.985 or ny > 0.99:
            break
        f = 1 - 0.65 * i / max(1, n)
        _seg(canvas, x * size, y * size, nx * size, ny * size, width * size * f, val * (0.55 + 0.45 * f))
        x, y = nx, ny
        if depth < 2 and i == int(n * 0.55):
            sd = 1 if ang >= 0 else -1
            _branch(rng, canvas, size, x, y, ang - sd * rng.uniform(0.45, 0.70), length * 0.45, width * 0.7, val * 0.8,
                    depth + 1, step)


def _frost_arm(rng, canvas, size, x, y, ang, length):
    """霜花一瓣：直枝 + 两对 60° 小分枝。"""
    ex, ey = x + math.cos(ang) * length, y + math.sin(ang) * length
    _seg(canvas, x * size, y * size, ex * size, ey * size, 0.0030 * size, 1.0)
    for t, kk in ((0.45, 0.50), (0.75, 0.32)):
        bx, by = x + (ex - x) * t, y + (ey - y) * t
        for sd in (-1, 1):
            a2 = ang + sd * math.pi / 3
            _seg(canvas, bx * size, by * size, (bx + math.cos(a2) * length * kk) * size,
                 (by + math.sin(a2) * length * kk) * size, 0.0024 * size, 0.9)


def _radial(rng, main, fine, size, x0, curv, ph, w_main=0.0085):
    """一根从腕部辐射到后缘的主脉（缓 S 弯）+ 两侧间隔羽状分出的侧脉。"""
    ys = np.linspace(0.012, 0.985, 80)
    xs = x0 + curv * np.sin(2.4 * ys + ph) * ys
    for i in range(len(ys) - 1):
        f = 1 - 0.30 * ys[i]
        _seg(main, xs[i] * size, ys[i] * size, xs[i + 1] * size, ys[i + 1] * size, w_main * size * f, 1.0)
    sd = 1 if rng.random() < 0.5 else -1
    y = 0.16 + 0.05 * rng.random()
    while y < 0.86:
        j = int(y * (len(ys) - 1))
        sd = -sd
        _branch(rng, fine, size, float(xs[j]), float(ys[j]), sd * rng.uniform(0.50, 0.68), rng.uniform(0.17, 0.26),
                0.0052, 0.85, 0)
        y += 0.115 + 0.04 * rng.random()


def membrane_maps(seed, size=1024, glow=(0.20, 0.80, 1.0)):
    """翼膜贴图（配合 membrane_pt 的 UV：u 横跨两指骨之间、v 腕 0 → 后缘 1，数组第 0 行为 v=0）。
    返回 (rgba, emission)：
    Alpha：薄冰基底 + 翼脉 / 霜花 / 两侧指骨边 / 后缘加厚；颜色：近指骨深冰蓝 → 膜面浅冰青；
    自发光：主脉亮青、细脉半亮、局部六角冰纹 + 霜晶、后缘一道光边。"""
    rng = np.random.default_rng(seed)
    yy, xx = np.mgrid[0:size, 0:size].astype(np.float32) / size
    main = np.zeros((size, size), np.float32)
    fine = np.zeros((size, size), np.float32)
    # 主脉：4 条自腕部辐射到后缘，间隔羽状侧脉；两侧指骨边另有短侧脉
    for x0 in (0.20, 0.40, 0.60, 0.80):
        _radial(rng, main, fine, size, x0 + rng.uniform(-0.03, 0.03), rng.uniform(0.012, 0.03) * rng.choice([-1, 1]),
                rng.uniform(0, TAU))
    for side in (0.03, 0.97):
        for y0 in np.linspace(0.20, 0.82, 5) + rng.uniform(-0.03, 0.03, 5):
            _branch(rng, fine, size, side, float(y0), (1 if side < 0.5 else -1) * rng.uniform(0.35, 0.55),
                    rng.uniform(0.14, 0.24), 0.0045, 0.7, 0)
    # 同心细弧：像翼膜的张力纹，淡淡的虚线
    arcs = np.zeros_like(main)
    for v0 in (0.34, 0.52, 0.70, 0.86):
        for i in range(8, 112):
            if (i // 6) % 3 == 2:
                continue
            ua, ub = i / 120, (i + 1) / 120
            wob = 0.012 * math.sin(ua * 17 + v0 * 9)
            _seg(arcs, ua * size, (v0 + wob) * size, ub * size, (v0 + 0.012 * math.sin(ub * 17 + v0 * 9)) * size,
                 0.0026 * size, 0.55)
    # 霜花：几处小簇 6 瓣枝晶，贴近指骨边与后缘
    frost = np.zeros_like(main)
    for _ in range(3):
        cx = float(rng.choice([rng.uniform(0.07, 0.17), rng.uniform(0.83, 0.93), rng.uniform(0.35, 0.65)]))
        cy = float(rng.uniform(0.50, 0.90))
        for arm in range(int(rng.integers(4, 7))):
            _frost_arm(rng, frost, size, cx, cy, arm * TAU / 5 + rng.uniform(-0.35, 0.35), rng.uniform(0.025, 0.075))
    # 六角冰纹：只在低频噪声挑出的几块里显现
    hb, hem, _ = hex_maps(glow, size=size, cells=11, width=0.06, seed=seed)
    hexmask = np.clip(hem.max(axis=2) / max(1e-6, max(glow)), 0, 1) ** 1.3
    patch = box_blur(rng.random((size, size)).astype(np.float32), size // 7)
    patch = box_blur(patch, size // 9)
    patch = (patch - patch.min()) / max(1e-6, patch.max() - patch.min())
    patch = _ss(0.50, 0.70, patch) * (0.35 + 0.65 * _ss(0.15, 0.9, yy))
    hexv = hexmask * patch
    edge = np.exp(-(np.minimum(xx, 1 - xx) / 0.022) ** 2)
    rim = _ss(0.925, 0.985, yy)
    rimline = np.exp(-((yy - 0.975) / 0.014) ** 2)
    noise = box_blur(rng.random((size, size)).astype(np.float32), 18)
    noise = (noise - noise.min()) / max(1e-6, noise.max() - noise.min())
    soft = box_blur(main, 3)
    alpha = 0.34 + 0.12 * (noise - 0.5) + 0.46 * soft + 0.30 * fine + 0.18 * arcs + 0.34 * frost + 0.26 * hexv + \
        0.42 * edge + 0.30 * rim
    alpha = np.clip(alpha, 0.0, 0.88)
    t = np.clip(0.18 + 0.55 * _ss(0.0, 0.85, yy) + 0.25 * noise + 0.30 * np.maximum(frost, hexv), 0, 1)
    deep, pale = np.array((0.025, 0.12, 0.32), np.float32), np.array((0.26, 0.58, 0.92), np.float32)
    col = deep[None, None, :] * (1 - t[..., None]) + pale[None, None, :] * t[..., None]
    col = col + (edge * 0.15)[..., None]
    rgba = np.concatenate([np.clip(col, 0, 1), alpha[..., None]], axis=2).astype(np.float32)
    em_v = 1.00 * soft + 0.62 * fine + 0.22 * arcs + 0.55 * frost + 0.34 * hexv + 0.60 * rimline + 0.10 * edge + \
        0.05 * _ss(0.2, 1.0, yy)
    em = np.stack([np.clip(em_v, 0, 1.2) * c for c in glow], axis=2).astype(np.float32)
    return rgba, np.clip(em, 0, 1)


def rgba_image(ctx, name, arr, noncolor=False):
    """RGBA 打包贴图（straight alpha）：与 Boss 2 的火舌同样只打包不落盘，导出走 glTF 的 BLEND。"""
    h, w = arr.shape[:2]
    if arr.shape[2] == 3:
        arr = np.concatenate([arr, np.ones((h, w, 1), np.float32)], axis=2)
    img = bpy.data.images.new(f"{ctx.title} {name}", width=w, height=h, alpha=True)
    img.pixels.foreach_set(np.clip(arr, 0, 1).astype(np.float32).ravel())
    img.alpha_mode = "STRAIGHT"
    if noncolor:
        img.colorspace_settings.name = "Non-Color"
    img.pack()
    return img


def membrane_material(ctx, name, rgba, emit, strength=2.2):
    """半透明冰晶膜材质：Base Color / Alpha 同取一张 RGBA 图，Emission 取另一张翼脉图。"""
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    p = nt.nodes["Principled BSDF"]
    t0 = nt.nodes.new("ShaderNodeTexImage")
    t0.image = rgba_image(ctx, f"{name} rgba", rgba)
    t0.extension = "EXTEND"
    t1 = nt.nodes.new("ShaderNodeTexImage")
    t1.image = rgba_image(ctx, f"{name} emit", emit)
    t1.extension = "EXTEND"
    nt.links.new(t0.outputs["Color"], p.inputs["Base Color"])
    nt.links.new(t0.outputs["Alpha"], p.inputs["Alpha"])
    nt.links.new(t1.outputs["Color"], p.inputs["Emission Color"])
    p.inputs["Emission Strength"].default_value = strength
    p.inputs["Metallic"].default_value = 0.0
    p.inputs["Roughness"].default_value = 0.28
    p.inputs["Specular IOR Level"].default_value = 0.6
    if "Coat Weight" in p.inputs:
        p.inputs["Coat Weight"].default_value = 0.35
        p.inputs["Coat Roughness"].default_value = 0.05
    m.use_backface_culling = False
    m.surface_render_method = "BLENDED"
    try:
        m.use_transparent_shadow = True
    except AttributeError:
        pass
    return m


# ===== 翼骨 =====
def spar(ctx, M, name, P, R, bone, up, sleeves, node_every=True, inlay=True, piston=True):
    """一段翼骨：P(t) 路径点、R(t) 半径（t∈[0,1]）。
    深冰蓝钢芯 + 若干银甲套筒（顶部棱线、两端银箍）+ 套筒之间的发光关节节点 + 顶面嵌线 + 下侧液压杆。"""
    N = 8
    core_t = [i / N for i in range(N + 1)]
    ctx.part(sweep(f"{ctx.title} {name} core", [P(t) for t in core_t], [R(t) for t in core_t], [M["under"]], n=10,
                   per=1, up=tuple(up)), rigid(bone))
    ridge = lambda a, t: (1.0 + 0.34 * max(0.0, math.cos(a)) ** 5) * (1.0 + 0.10 * (1 - t))   # noqa: E731
    for q, (t0, t1) in enumerate(sleeves):
        ts = [lerp(t0, t1, i / 3) for i in range(4)]
        ctx.part(sweep(f"{ctx.title} {name} sleeve {q}", [P(t) for t in ts], [R(t) * 1.28 for t in ts], [M["armor"]],
                       n=12, per=1, up=tuple(up), shape=ridge), rigid(bone))
        for tb, kk in ((t0, 1.30),):
            c = P(tb)
            d = (P(min(1.0, tb + 0.02)) - P(max(0.0, tb - 0.02))).normalized()
            a1 = d.orthogonal().normalized()
            a2 = d.cross(a1)
            rad = R(tb) * kk + 0.01
            ring = [c + (a1 * math.cos(x) + a2 * math.sin(x)) * rad for x in [j / 10 * TAU for j in range(10)]]
            ctx.part(trim(f"{ctx.title} {name} band {q}{tb:.2f}", ring, 0.016 + 0.10 * R(tb) * 0.2, M["trim"],
                          closed=True), rigid(bone))
        if inlay:
            pts = [P(t) + up * R(t) * 1.74 for t in (lerp(t0, t1, 0.12), lerp(t0, t1, 0.5), lerp(t0, t1, 0.88))]
            ctx.part(trim(f"{ctx.title} {name} inlay {q}", pts, 0.013, M["glow"], per=2), rigid(bone))
    if node_every:
        for q in range(len(sleeves) - 1):
            tm = (sleeves[q][1] + sleeves[q + 1][0]) / 2
            c = P(tm)
            ctx.part(gem(f"{ctx.title} {name} node {q}", c + up * R(tm) * 0.55, R(tm) * 0.80, M["core"], (1, 1, 0.9)),
                     rigid(bone))
    if piston:
        t0, t1 = sleeves[0][0], sleeves[-1][1]
        lo = lambda t: P(t) - up * R(t) * 1.42   # noqa: E731
        ctx.part(trim(f"{ctx.title} {name} piston", [lo(lerp(t0, t1, 0.12)), lo(lerp(t0, t1, 0.85))], 0.030, M["trim"]),
                 rigid(bone))
        ctx.part(trim(f"{ctx.title} {name} piston glow", [lo(lerp(t0, t1, 0.40)), lo(lerp(t0, t1, 0.60))], 0.040,
                      M["glow"]), rigid(bone))


def hub(ctx, M, name, c, r, bone, up, ring_normal=None, node=True):
    """关节轴毂：银甲球 + 一圈银箍 + 外侧发光冰核。"""
    ctx.part(blob(f"{ctx.title} {name} hub", c, (r, r, r), [M["armor"]], 14, 9, power=2.3), rigid(bone))
    n = (ring_normal or Vector((0, 1, 0))).normalized()
    a1 = n.orthogonal().normalized()
    a2 = n.cross(a1)
    ring = [c + n * (r * 0.30) + (a1 * math.cos(x) + a2 * math.sin(x)) * r * 0.95 for x in [j / 16 * TAU for j in range(16)]]
    ctx.part(trim(f"{ctx.title} {name} hub ring", ring, 0.024 + 0.04 * r, M["trim"], closed=True), rigid(bone))
    if node:
        ctx.part(gem(f"{ctx.title} {name} hub node", c + n * (r * 0.92), r * 0.46, M["core"], (1, 1, 0.55)), rigid(bone))


def build_wing(ctx, M, g, kw_bone=None):
    """建一侧翼（几何 + 蒙皮规格）。g 为 WingGeo。"""
    side = g.side
    L = "L" if side < 0 else "R"
    A, B = f"WingA.{L}", f"WingB.{L}"
    n = g.n
    fwd = Vector((0, 1, 0))
    S, E, W = g.S, g.E, g.W

    # ----- 肩：银甲大轴毂 + 外侧法兰 + 冰核 + 后掠肩刺 -----
    hub(ctx, M, f"shoulder {L}", S, 0.50, A, n, ring_normal=Vector((side, 0.15, 0.2)))
    sh = [(S + Vector((side * 0.20, -0.30, 0.30)), S + Vector((side * 0.45, -0.85, 0.80)), 0.12, 6),
          (S + Vector((side * 0.10, -0.15, 0.40)), S + Vector((side * 0.12, -0.45, 1.05)), 0.10, 6),
          (S + Vector((side * 0.35, -0.10, 0.25)), S + Vector((side * 0.85, -0.25, 0.65)), 0.08, 6)]
    ctx.part(crystals(f"{ctx.title} shoulder spikes {L}", sh, [M["crystal"]], seed=30 + side), rigid(A))

    # ----- 肱骨 S→E -----
    up_h = (n - (E - S).normalized() * n.dot((E - S).normalized())).normalized()
    Ph = lambda t: S.lerp(E, t)       # noqa: E731
    Rh = lambda t: lerp(0.25, 0.20, t)   # noqa: E731
    spar(ctx, M, f"humerus {L}", Ph, Rh, A, up_h, [(0.20, 0.55), (0.60, 0.92)])
    # ----- 肘：大轴毂 + 后伸肘刺 -----
    hub(ctx, M, f"elbow {L}", E, 0.30, B, n, ring_normal=Vector((0, 0.3, 1)))
    ctx.part(crystals(f"{ctx.title} elbow spike {L}", [(E + Vector((0, -0.05, 0.1)), E + Vector((side * 0.10, -0.80, 0.30)),
                                                       0.10, 6),
                                                      (E, E + Vector((side * 0.30, -0.50, -0.30)), 0.06, 6)],
                      [M["crystal"]], seed=34 + side), rigid(B))
    # ----- 前臂 E→W -----
    d_f = (W - E).normalized()
    up_f = (n - d_f * n.dot(d_f)).normalized()
    Pf = lambda t: E.lerp(W, t)       # noqa: E731
    Rf = lambda t: lerp(0.20, 0.145, t)   # noqa: E731
    spar(ctx, M, f"forearm {L}", Pf, Rf, B, up_f, [(0.15, 0.50), (0.56, 0.90)])
    # ----- 腕：轴毂 + 拇指冰爪 -----
    hub(ctx, M, f"wrist {L}", W, 0.26, B, n, ring_normal=Vector((0, 0.5, 1)))
    thumb = [(W + Vector((side * 0.05, 0.10, 0.12)), W + Vector((side * 0.30, 1.00, 0.55)), 0.13, 6),
             (W + Vector((side * 0.10, 0.05, 0.05)), W + Vector((side * 0.62, 0.62, 0.85)), 0.09, 6),
             (W + Vector((side * 0.15, 0.0, 0.0)), W + Vector((side * 0.95, 0.30, 0.38)), 0.07, 6)]
    ctx.part(crystals(f"{ctx.title} thumb claws {L}", thumb, [M["crystal"]], seed=36 + side), rigid(B))

    # ----- 前缘冰刺：前臂 / 肱骨顶缘，大小有层次，间隔插小刺 -----
    spikes = []
    for i, t in enumerate((0.10, 0.22, 0.34, 0.46, 0.58, 0.70, 0.82, 0.93)):
        base = Pf(t) + up_f * Rf(t) * 0.9
        big = 0.30 + 0.34 * smoothstep(0.0, 1.0, t)          # 越近腕越大
        for q, (kk, off) in enumerate(((1.0, 0.0), (0.52, 0.055))):
            d = (up_f * 0.80 + fwd * 0.50 + d_f * (0.28 + 0.22 * q)).normalized()
            b = base + d_f * off - up_f * 0.06
            spikes.append((b, b + d * big * kk, 0.060 + 0.05 * big * kk, 6))
    ctx.part(crystals(f"{ctx.title} forearm spikes {L}", spikes, [M["crystal"]], seed=41 + side), rigid(B))
    spikes = []
    d_h = (E - S).normalized()
    for i, t in enumerate((0.30, 0.55, 0.80)):
        base = Ph(t) + up_h * Rh(t) * 0.9
        big = 0.26 + 0.12 * t
        for kk, off in ((1.0, 0.0), (0.5, 0.06)):
            d = (up_h * 0.85 + fwd * 0.35 + d_h * 0.25).normalized()
            b = base + d_h * off - up_h * 0.05
            spikes.append((b, b + d * big * kk, 0.060 + 0.04 * big * kk, 6))
    ctx.part(crystals(f"{ctx.title} humerus spikes {L}", spikes, [M["crystal"]], seed=44 + side), rigid(A))

    # ----- 5 根指骨：钢芯 + 三段银甲套筒 + 关节发光节点 + 尖端大冰爪 -----
    for k, (d, Lk) in enumerate(g.F):
        bone = f"WingF{k}.{L}"
        Pk = lambda t, k=k: g.finger(k, t)           # noqa: E731
        r0 = 0.115 - 0.010 * k
        Rk = lambda t, r0=r0: lerp(r0, 0.026, t ** 0.85)   # noqa: E731
        up_k = (n - d * n.dot(d)).normalized()
        spar(ctx, M, f"finger {L}{k}", Pk, Rk, bone, up_k, [(0.06, 0.34), (0.38, 0.66), (0.70, 0.93)], piston=False)
        tip = g.tip(k)
        big = (0.80, 0.95, 0.90, 0.78, 0.62)[k]
        td = (d + up_k * 0.22).normalized()
        claws = [(tip - d * 0.12, tip + td * big, 0.075 + 0.015 * (4 - k) * 0.3, 6),
                 (tip - d * 0.10, tip + (d + up_k * 0.55 - g.bow[k] * 0.25).normalized() * big * 0.52, 0.05, 6)]
        ctx.part(crystals(f"{ctx.title} finger claw {L}{k}", claws, [M["crystal"]], seed=50 + k + side * 7), rigid(bone))
        # 指骨上侧一排小冰刺（只在前三根上，前缘感）
        if k < 3:
            sp = []
            for t in (0.28, 0.46, 0.64, 0.80):
                b = Pk(t) + up_k * Rk(t) * 0.9
                dd = (up_k * 0.85 + (fwd if k == 0 else Vector((0, 0.2, 0))) * 0.45 + d * 0.3).normalized()
                ln = (0.30 - 0.10 * t) * (1.0 if k == 0 else 0.7)
                sp.append((b - up_k * 0.04, b + dd * ln, 0.04, 6))
            ctx.part(crystals(f"{ctx.title} finger spikes {L}{k}", sp, [M["crystal"]], seed=60 + k + side * 9), rigid(bone))

    # ----- 翼膜：4 片指间 + 1 片内侧（连到躯干） -----
    kwm = KDWeights()
    panels = []
    nu, nv = 16, 18

    def weights(k, u, v):
        near = 1 - smoothstep(0.0, 0.22, v)
        if k < 4:
            w = {f"WingF{k}.{L}": 1 - u, f"WingF{k + 1}.{L}": u}
        else:
            w = {f"WingF4.{L}": 1 - u}
            body = {B: 1 - smoothstep(0.20, 0.42, v),
                    A: smoothstep(0.20, 0.42, v) * (1 - smoothstep(0.62, 0.86, v)),
                    "Core": smoothstep(0.62, 0.86, v)}
            for nm, x in body.items():
                w[nm] = w.get(nm, 0) + u * x
        out = {nm: x * (1 - near) for nm, x in w.items()}
        out[B] = out.get(B, 0) + near
        return out

    for k in range(5):
        for i in range(nu * 2 + 1):
            for j in range(nv * 2 + 1):
                uu, v = i / (nu * 2), j / (nv * 2)
                kwm.add(g.membrane_pt(k, uu, v), weights(k, uu, v))
    kwm.build()
    for k in range(5):
        mat = M["membrane"] if k % 2 == 0 else M["membrane2"]
        mem = surface(f"{ctx.title} membrane {L}{k}", lambda uu, v, k=k: g.membrane_pt(k, uu, v), nu, nv, [mat],
                      uvfn=lambda uu, v: (uu, v))
        ctx.part(mem, fn(kwm))
        edge = [g.membrane_pt(k, q / 16, 0.998) for q in range(17)]
        ctx.part(trim(f"{ctx.title} membrane edge glow {L}{k}", edge, 0.020, M["glow"]), fn(kwm))
        # 后缘冰晶流苏：沿扇边稀疏几根小冰刺
        fr = []
        for q in (0.30, 0.50, 0.70):
            e0 = g.membrane_pt(k, q, 0.996)
            dn = (e0 - W).normalized()
            fr.append((e0 - dn * 0.05, e0 + dn * (0.20 + 0.10 * math.sin(q * 9 + k)) - n * 0.04, 0.040, 5))
        ctx.part(crystals(f"{ctx.title} membrane fringe {L}{k}", fr, [M["crystal"]], seed=70 + k + side * 5), fn(kwm))
