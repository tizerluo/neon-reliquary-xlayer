"""塞拉芙第二轮私有部件：斜挎圣带、腰封下的短甲裙、腰间垂链与圣徽垂片、刃羽的羽根护套与羽脉。

只被 tools/chars/seraph.py 引用；不改 tools/kit/ 与 _grace_helpers.py（后者只读引用）。
"""

import math

import numpy as np
from mathutils import Vector

from kit.core import (GLYPHS, TAU, Canvas, _finish, circuit_maps, clamp, ellipsoid, finish, garment, lerp, orient,
                      plate, spike, surface, trim)
from chars._grace_helpers import gem2, hem_rune_maps


# ===== 省面工具 =====
def gem_lo(name, center, size, mat, stretch=(1.0, 0.6, 1.4)):
    """8×5 段小宝石（发光材质不参与游戏版减面，小宝石用最少的段数）。"""
    return gem2(name, center, size, mat, stretch, seg=8, rings=5)


def rims(ctx, pt, name, radius, mat, spec, vs=(0.0, 1.0), count=48, closed=True, n=4, out=None, lift=0.0):
    """给 u×v 参数面（shell / limb_plate 返回的 pt）沿 v 边加滚边：kit 版固定 6 边管、nu+24 个点，
    滚边材质又不参与减面，这里控制点数与边数。out(p) 返回外推方向。"""
    for v in vs:
        pts = []
        for i in range(count):
            p = pt(i / (count if closed else count - 1), v)
            pts.append(p + (out(p) * lift if out else Vector()))
        ctx.part(trim(f"{name} rim {v}", pts, radius, mat, closed=closed, n=n), spec)


def axis_out(a, b):
    """肢体甲片的外推方向：点相对于 a→b 轴线的垂直方向。"""
    a, b = Vector(a), Vector(b)
    ab = b - a

    def out(p):
        t = clamp((p - a).dot(ab) / max(ab.length_squared, 1e-12))
        d = p - a.lerp(b, t)
        return d.normalized() if d.length > 1e-9 else Vector((0, 0, 1))
    return out


# ===== 贴图 =====
def embroidered_silk_maps(emit_rgb, base_rgb, line_rgb, size=1024, seed=17, buses=11):
    """象牙内裙：下摆一行符文刺绣（hem_rune_maps）叠加自下摆向上渐隐的绯红电路刺绣（circuit_maps），
    底色取两者较暗者（线条压在象牙底上），发光取两者较亮者。"""
    b1, e1, n1 = hem_rune_maps(emit_rgb, base_rgb, line_rgb=line_rgb, size=size, seed=seed)
    b2, e2, n2 = circuit_maps(emit_rgb, base_rgb=base_rgb, line_rgb=line_rgb, size=size, seed=seed + 7, buses=buses,
                              reach=(0.30, 0.72))
    base = np.minimum(b1, b2)
    emit = np.maximum(e1, e2 * 0.85)
    nrm = (n1 + n2) * 0.5
    nrm = (nrm - 0.5)
    nrm /= np.maximum(np.linalg.norm(nrm, axis=2, keepdims=True), 1e-6)
    return base, emit, nrm * 0.5 + 0.5


def stole_maps(emit_rgb, base_rgb, line_rgb, size=512, cols=3, seed=31):
    """圣带符文：上下双边线 + 一行居中的大字形（kit rune_maps 的字形受单元宽度限制、偏在下半格，这里居中放大）。
    图像 x 沿带长、y 横跨带宽。"""
    rng = np.random.default_rng(seed)
    cv = Canvas(size, size)
    for y in (0.08, 0.13, 0.87, 0.92):
        cv.line(0, y * size, size, y * size, 2)
    cw = size / cols
    for c in range(cols):
        g = GLYPHS[int(rng.integers(len(GLYPHS)))]
        gw, gh = cw * 0.55, size * 0.46
        x0, y0 = c * cw + (cw - gw) / 2, (size - gh) / 2
        for (a, b, cc, d) in g:
            cv.line(x0 + a * gw, y0 + b * gh, x0 + cc * gw, y0 + d * gh, 4)
        cv.dot(c * cw, size * 0.5, 5)
    mask = np.clip(cv.mask, 0, 1)
    return _finish(mask, np.ones_like(mask), rng, emit_rgb, base_rgb, line_rgb, sparkle=False, bump=1.5)


# ===== 布料基准半径（不含褶皱）：部件贴着长袍 / 内裙外侧摆放时用 =====
def wrap_base(g, a, z, margin=0.0):
    """Wrap 布料在角度 a、高度 z 处的基准外轮廓点（按 Wrap.point 的公式去掉褶皱与飘带），再径向外推 margin。"""
    top = g.top(0.5)
    bot = g._bottom(0.5) if callable(g._bottom) else g._bottom
    v = clamp((top - z) / max(1e-4, top - bot))
    e = v ** g.flare_exp
    rx = lerp(g.r_top[0], g.r_bot[0], e) * (1 + g.widen * v) + margin
    ry = lerp(g.r_top[1], g.r_bot[1], e) + margin
    return Vector((rx * math.sin(a), ry * math.cos(a) + g.cy + g.flow(v), z))


def fold_room(g, z):
    """该高度处褶皱的最大外凸量（Wrap 的褶皱振幅 amp0 + amp1·v）。"""
    top = g.top(0.5)
    bot = g._bottom(0.5) if callable(g._bottom) else g._bottom
    v = clamp((top - z) / max(1e-4, top - bot))
    return g.amp0 + g.amp1 * v


# ===== 斜挎圣带 =====
def stole(ctx, B, name, path, width, mat, trim_mat, grow, spec, rep=9.0, n=40, medal=None, medal_at=(0.36, 0.78)):
    """贴合躯干正面的斜挎圣带：path 为 [(x, z)...]（米，躯干正面坐标），grow(z) 给出离躯干表面的距离。
    uv 的 u 沿带长重复 rep 次、v 横跨带宽（配 rune_maps(rows=1) 的一行符文）。medal=(托材质, 宝石材质)。"""
    pts = [Vector((x, 0.0, z)) for x, z in path]
    seg = [(b - a).length for a, b in zip(pts, pts[1:])]
    total = sum(seg)

    def center(t):
        d = t * total
        for i, L in enumerate(seg):
            if d <= L or i == len(seg) - 1:
                return pts[i].lerp(pts[i + 1], clamp(d / max(L, 1e-9))), (pts[i + 1] - pts[i]).normalized()
            d -= L

    def smooth_center(t):
        # 相邻采样平均，让折线路径转角圆滑
        acc, dacc = Vector(), Vector()
        for dt in (-0.04, -0.02, 0.0, 0.02, 0.04):
            c, d = center(clamp(t + dt))
            acc += c
            dacc += d
        return acc / 5, dacc.normalized()

    def pt(u, v, lift=0.0):
        c, d = smooth_center(v)
        perp = Vector((-d.z, 0, d.x))
        q = c + perp * (u - 0.5) * width
        return B.on_torso(q.x, q.z, grow(q.z) + lift)
    band = surface(name, lambda u, v: pt(u, v), 6, n, [mat], uvfn=lambda u, v: (v * rep, u))
    orient(band, lambda c: Vector((0, 0, c.z)))
    ctx.part(finish(band, 0.004, 1, 0), spec)
    for u in (0.0, 1.0):
        edge = [pt(u, j / 27, 0.0045) for j in range(28)]
        ctx.part(trim(f"{name} edge {u}", edge, 0.0024, trim_mat, n=4), spec)
    if medal:
        for k, t in enumerate(medal_at):
            c = pt(0.5, t, 0.006)
            nrm = (pt(0.5, t, 0.02) - c).normalized()
            ctx.part(ellipsoid(f"{name} medal {k}", c, (0.020, 0.020, 0.020), [medal[0]], 14, 7), spec)
            ctx.part(gem_lo(f"{name} medal gem {k}", c + nrm * 0.010, 0.0095, medal[1], (1, 1, 1)), spec)
    return pt


# ===== 腰封下的短甲裙（挂在外袍上，随外袍骨链摆动） =====
def tassets(ctx, g, name, angles, half, top, length, mat, trim_mat, gem_mat=None, margin=0.016, flare=0.030,
            nu=10, nv=7, thick=0.006):
    """沿外袍外侧的一圈盾形甲片：angles 为中心角，half 为半张角，底边中间最长（盾尖）。"""
    spec = garment(g)
    out = []
    for k, a0 in enumerate(angles):
        def L(u):
            return length * (1 - 0.38 * abs(2 * u - 1) ** 1.8)

        def pt(u, v, lift=0.0, a0=a0):
            a = a0 + (2 * u - 1) * half
            z = top - v * L(u)
            m = margin + fold_room(g, z) + flare * v ** 1.4 + lift
            return wrap_base(g, a, z, m)
        lame = surface(f"{name} {k}", pt, nu, nv, [mat])
        orient(lame, lambda c: Vector((0, g.cy, c.z)))
        ctx.part(finish(lame, thick, 1, 0), spec)
        rim = [pt(0.0, j / 5, 0.004) for j in range(6)] + [pt(i / 8, 1.0, 0.004) for i in range(1, 8)] + \
              [pt(1.0, 1 - j / 5, 0.004) for j in range(6)]
        ctx.part(trim(f"{name} {k} trim", rim, 0.0028, trim_mat, n=4), spec)
        # 中脊：一道玫瑰金细棱，从顶到盾尖
        ridge = [pt(0.5, j / 4, 0.005) for j in range(1, 5)]
        ctx.part(trim(f"{name} {k} ridge", ridge, 0.0022, trim_mat, n=4), spec)
        if gem_mat:
            ctx.part(gem_lo(f"{name} {k} gem", pt(0.5, 0.16, 0.008), 0.0065, gem_mat, (0.9, 0.7, 1.2)), spec)
        out.append(pt)
    return out


# ===== 腰间垂链与圣徽垂片（挂在内裙上） =====
def swag(g_front, a0, a1, z_end, z_sag, margin, count=28):
    """两端挂在腰封、中间下垂的弧形链路径（悬链线近似为余弦）。"""
    pts = []
    for i in range(count):
        t = i / (count - 1)
        a = lerp(a0, a1, t)
        z = lerp(z_end, z_sag, math.sin(math.pi * t) ** 1.3)
        pts.append(wrap_base(g_front, a, z, margin + fold_room(g_front, z)))
    return pts


def chain_links(ctx, name, pts, mat, spec, radius=0.0022, bead=0.0042, every=3):
    """链条：细管 + 每隔几个点一颗扁珠，远看读作一串链环。"""
    ctx.part(trim(name, pts, radius, mat, n=4), spec)
    for i in range(every // 2, len(pts), every):
        ctx.part(ellipsoid(f"{name} bead {i}", pts[i], (bead, bead, bead * 1.3), [mat], 6, 4), spec)


def sunburst(ctx, name, c, mat, gem_mat, trim_mat, spec, r=0.028, rays=12):
    """圣徽垂片：玫瑰金圆牌 + 放射尖芒 + 中心玫红宝石，牌面朝 +Y。"""
    ctx.part(ellipsoid(f"{name} disc", c, (r, 0.007, r), [mat], 20, 8), spec)
    ring = [c + Vector((math.sin(i / 24 * TAU) * r * 0.78, 0.0068, math.cos(i / 24 * TAU) * r * 0.78))
            for i in range(24)]
    ctx.part(trim(f"{name} ring", ring, 0.0016, trim_mat, closed=True, n=4), spec)
    for k in range(rays):
        a = k / rays * TAU
        d = Vector((math.sin(a), 0, math.cos(a)))
        L = (0.030 if k % 2 == 0 else 0.016) * (1.35 if k == rays // 2 else 1.0)
        ctx.part(spike(f"{name} ray {k}", c + d * r * 0.85, c + d * (r + L), 0.0055, [mat], sides=4, fx=1.0,
                       fy=0.4, up=(0, 1, 0)), spec)
    ctx.part(gem_lo(f"{name} gem", c + Vector((0, 0.008, 0)), 0.012, gem_mat, (0.85, 0.5, 1.15)), spec)


# ===== 刃羽附件 =====
def feather_width(outline, x):
    """从 feather_outline 轮廓里插值出 x 处的上下沿 y。"""
    n = (len(outline) - 1) // 2
    upper = outline[:n]
    lower = outline[n + 1:][::-1]

    def at(side):
        for (x0, y0), (x1, y1) in zip(side, side[1:]):
            if x0 <= x <= x1:
                return lerp(y0, y1, (x - x0) / max(1e-9, x1 - x0))
        return side[-1][1]
    return at(upper), at(lower)


def root_sheath(name, outline, L, frac, depth, mat, origin, xaxis, yaxis, bulge, grow=1.12):
    """羽根护套：包住刃羽根部的一片更厚的绯红甲，末端收成 V 形尖。"""
    xs = [frac * L * k / 5 for k in range(6)]
    up = [feather_width(outline, x)[0] * grow + 0.0006 for x in xs]
    lo = [feather_width(outline, x)[1] * grow - 0.0006 for x in xs]
    mid = (up[-1] + lo[-1]) / 2
    shape = [(xs[i], up[i]) for i in range(6)] + [(frac * L * 1.28, mid)] + [(xs[i], lo[i]) for i in range(5, -1, -1)]
    shape = [(max(-0.004, x - 0.004) if i in (0, len(shape) - 1) else x, y) for i, (x, y) in enumerate(shape)]
    return plate(name, shape, depth, [mat], origin=origin, xaxis=xaxis, yaxis=yaxis, bulge=bulge)


def vein(name, origin, xaxis, yaxis, bulge, L, y0, half_w, depth, mat, x0=0.30, x1=0.86):
    """刃羽中线上的发光羽脉：一条比刃羽略厚的细长针形片，正反两面各露出一道细光（比管子省面）。"""
    a, b = x0 * L, x1 * L
    shape = [(a, y0), (a + 0.08 * L, y0 + half_w), (b - 0.10 * L, y0 + half_w * 0.7), (b, y0),
             (b - 0.10 * L, y0 - half_w * 0.7), (a + 0.08 * L, y0 - half_w)]
    return plate(name, shape, depth, [mat], origin=origin, xaxis=xaxis, yaxis=yaxis, bulge=bulge)
