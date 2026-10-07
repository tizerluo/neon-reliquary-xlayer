"""伊索尔德第二轮返工的私有辅助：带 UV 的发光冰晶、霜纹雕花 / 织锦 / 冰刃贴图、分段腿甲、处刑大剑、
优雅滑冰步态与“大衣让腿”求解。

只被 tools/chars/isolde.py 引用；不改 tools/kit/ 与 _grace_helpers.py（后者只 import）。
kit 里不够用的地方在这里改写：
- kit shell / limb_plate 的滚边点数与边数固定（滚边材质不参与游戏版减面），这里改为可控点数的 5 边管；
- _grace_helpers.crystal 没有 UV，无法做“根部亮、尖端淡”的内部发光渐变，这里重写 crystal2；
- kit.rig.wind 一次写完整件布料，这里拆成逐链写入，供 coat_clear 按链迭代外掀量。
"""

import math
import os

import bmesh
import numpy as np
from mathutils import Vector

from kit.core import (TAU, Canvas, bm_object, box_blur, clamp, ellipsoid, hash01, height_normal, lerp, loft,
                      smoothstep, trim, tube)
from kit.humanoid import limb_frame, limb_plate, shell
from kit.motion import Legs
from kit.rig import R, X, Y, Z, depth_w

from chars._grace_helpers import cyc_hermite


# ===== 网格 =====
def crystal2(name, base, tip, radius, mats, sides=6, shoulder=0.72, foot=0.70, twist=0.0, seed=0.0,
             up=(0, 0, 1), lean=0.0):
    """刻面晶体（改写 _grace_helpers.crystal）：带 UV，v 从根部 0 到尖端 1，配合 crystal_maps 做内部发光渐变。"""
    b, t = Vector(base), Vector(tip)
    ax = (t - b).normalized()
    length = (t - b).length
    u = Vector(up) - ax * Vector(up).dot(ax)
    if u.length < 1e-5:
        u = ax.orthogonal()
    u.normalize()
    w = ax.cross(u)
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.new("UVMap")

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
        f = bm.faces.new((r0[k], r0[k2], r1[k2], r1[k]))
        for loop, uv in zip(f.loops, ((k / sides, 0.0), ((k + 1) / sides, 0.0), ((k + 1) / sides, shoulder),
                                      (k / sides, shoulder))):
            loop[uvl].uv = uv
        f = bm.faces.new((r1[k], r1[k2], apex))
        for loop, uv in zip(f.loops, ((k / sides, shoulder), ((k + 1) / sides, shoulder), ((k + 0.5) / sides, 1.0))):
            loop[uvl].uv = uv
    cap = bm.faces.new(list(reversed(r0)))
    for loop in cap.loops:
        loop[uvl].uv = (0.5, 0.0)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return bm_object(name, bm, mats, smooth=False)


def rim_pts(pt, v, count, lift, axis_a=None, axis_b=None, closed=False, u0=0.0, u1=1.0):
    """沿参数曲面 pt(u, v) 的一条 v 等值线取点并沿肢体轴径向外推 lift（给 limb_plate 返回的 pt 用）。"""
    n = count if closed else count - 1
    pts = [pt(lerp(u0, u1, i / n), v) for i in range(count)]
    if axis_a is None:
        return pts
    a, b = Vector(axis_a), Vector(axis_b)
    ab = b - a

    def on_axis(p):
        return a + ab * clamp((p - a).dot(ab) / ab.length_squared)
    return [p + (p - on_axis(p)).normalized() * lift for p in pts]


def shell2(ctx, B, name, zt, zb, grow, mat, spec, trim_mat=None, trim_r=0.003, trim_n=56, sides=True, **kw):
    """kit.humanoid.shell 的包装：甲壳本体照旧，滚边改为可控点数的 5 边管（kit 版固定 nu+24 点 6 边）。"""
    pt = shell(ctx, B, name, zt, zb, grow, mat, spec, trims=None, **kw)
    if trim_mat:
        a0, a1 = kw.get("a0", 0.0), kw.get("a1", TAU)
        full = abs(a1 - a0 - TAU) < 1e-6
        center = lambda p: Vector((0, B.torso_r(p.z)[2], p.z))
        for v in (0.0, 1.0):
            n = trim_n
            pts = [pt(i / (n if full else n - 1), v) for i in range(n)]
            pts = [p + (p - center(p)).normalized() * trim_r * 2.2 for p in pts]
            ctx.part(trim(f"{name} trim {v}", pts, trim_r, trim_mat, closed=full, n=3), spec)
        if sides and not full:
            for u in (0.0, 1.0):
                pts = [pt(u, j / 16) for j in range(17)]
                pts = [p + (p - center(p)).normalized() * trim_r * 2.2 for p in pts]
                ctx.part(trim(f"{name} side {u}", pts, trim_r, trim_mat, n=3), spec)
    return pt


def band(ctx, name, a, b, r0, r1, mat, spec, out, trim_mat=None, trim_r=0.0022, rims=(1,), rim_n=24, **kw):
    """limb_plate 的包装：本体照旧，滚边改为可控点数的 5 边管。返回 pt(u, v)。"""
    closed = kw.get("closed", False)
    pt = limb_plate(ctx, name, a, b, r0, r1, mat, spec, out, trim_mat=None, **kw)
    if trim_mat:
        thick = kw.get("thick", 0.005)
        for v in rims:
            pts = rim_pts(pt, v, rim_n, thick * 1.3, a, b, closed=closed)
            ctx.part(trim(f"{name} rim {v}", pts, trim_r, trim_mat, closed=closed, n=3), spec)
    return pt


# ===== 程序化贴图（第 0 行为图像底边，与 kit.core 一致） =====
def frost_plate_maps(base_rgb, groove_rgb, size=2048, seed=31, cells=9, panel=0, width=3):
    """冰白漆甲雕花：卷草涡线 + 六臂霜星 + 细霜枝 + 甲片分缝双刻线；沟槽压成深钢蓝并做法线凹陷。
    kit.filigree_maps 密度高、线细、对比低，远看就是一块白板；这里格子更大、线更粗、沟槽更深。"""
    rng = np.random.default_rng(seed)
    cv = Canvas(size, size)
    cell = size / cells
    sc = size / 2048
    for gx in range(cells):
        for gy in range(cells):
            cx, cy = (gx + 0.5) * cell, (gy + 0.5) * cell
            if (gx + gy) % 2 == 0:
                # 六臂霜星：主臂 + 两对 60° 小枝
                r = cell * 0.36
                rot = rng.uniform(0, math.pi / 3)
                for k in range(6):
                    a = rot + k * math.pi / 3
                    ex, ey = cx + math.cos(a) * r, cy + math.sin(a) * r
                    cv.line(cx, cy, ex, ey, width)
                    for f in (0.45, 0.72):
                        bx, by = cx + math.cos(a) * r * f, cy + math.sin(a) * r * f
                        for sd in (-1, 1):
                            b2 = a + sd * math.pi / 3
                            L = r * (0.34 if f < 0.5 else 0.22)
                            cv.line(bx, by, bx + math.cos(b2) * L, by + math.sin(b2) * L, max(1, width - 1))
                cv.ring(cx, cy, cell * 0.08, max(1, width - 1))
            else:
                # 成对卷草涡线
                for sd in (-1, 1):
                    t = np.linspace(0, rng.uniform(1.2, 1.7) * TAU, 110)
                    rr = cell * 0.30 * np.exp(-0.20 * t)
                    ph = rng.uniform(0, TAU)
                    ox = cx + sd * cell * 0.18
                    xs = ox + sd * rr * np.cos(t + ph)
                    ys = cy + rr * np.sin(t + ph)
                    for i in range(len(t) - 1):
                        cv.line(xs[i], ys[i], xs[i + 1], ys[i + 1], width)
    # 细霜枝：零星的 60° 分叉枝晶，打破格子感
    for _ in range(int(60 * sc) + 20):
        x, y, a = rng.uniform(0, size), rng.uniform(0, size), rng.uniform(0, TAU)
        L = rng.uniform(40, 110) * sc
        cv.line(x, y, x + math.cos(a) * L, y + math.sin(a) * L, max(1, width - 2))
        for f in (0.4, 0.7):
            bx, by = x + math.cos(a) * L * f, y + math.sin(a) * L * f
            sd = rng.choice([-1, 1])
            cv.line(bx, by, bx + math.cos(a + sd * math.pi / 3) * L * 0.3,
                    by + math.sin(a + sd * math.pi / 3) * L * 0.3, 1)
    # 甲片分缝双刻线（小部件的 UV 会把横线压成条纹，默认不画）
    for k in range(0, cells + 1, panel) if panel else ():
        c = k * cell
        for off in (-7 * sc, 7 * sc):
            cv.line(0, c + off, size, c + off, max(1, width - 1))
            cv.line(c + off, 0, c + off, size, max(1, width - 1))
    mask = np.clip(box_blur(cv.mask, 2) * 1.4, 0, 1)
    grain = box_blur(rng.random(mask.shape).astype(np.float32), int(20 * sc) + 2) - 0.5
    tone = (1.0 + grain * 0.5)[..., None]
    base = np.array(base_rgb)[None, None, :] * tone * (1 - mask[..., None]) + \
        np.array(groove_rgb)[None, None, :] * mask[..., None]
    return np.clip(base, 0, 1), None, height_normal(-box_blur(mask, 3), 3.0 * sc)


def panel_plate_maps(frame_rgb, field_rgb, groove_rgb, emit_rgb, size=2048, seed=31, border=0.12, cells=4,
                     width=12, corner=0.06):
    """双色嵌板漆甲：每个甲片自带 0–1 UV，所以每片都读成“冰白外框 + 淡冰蓝雕花内板”，
    内板边缘一道双刻线 + 内侧一道冷光细线，内板里是大号霜星 / 卷草雕花（线宽足够在全身镜头下读出）。"""
    rng = np.random.default_rng(seed)
    sc = size / 2048
    ys, xs = np.mgrid[0:size, 0:size].astype(np.float32) / size

    def box_dist(inset):
        # 到圆角矩形 [inset, 1-inset]² 边界的有符号距离（内部为负）
        qx = np.abs(xs - 0.5) - (0.5 - inset - corner)
        qy = np.abs(ys - 0.5) - (0.5 - inset - corner)
        out = np.sqrt(np.maximum(qx, 0) ** 2 + np.maximum(qy, 0) ** 2) + np.minimum(np.maximum(qx, qy), 0)
        return out - corner
    d = box_dist(border)
    field = np.clip(-d * size / (6 * sc), 0, 1)
    px = 1.0 / size
    groove = np.clip(1 - np.abs(d + 0.012) / (3.5 * sc * px), 0, 1)
    groove = np.maximum(groove, np.clip(1 - np.abs(d - 0.012) / (2.5 * sc * px), 0, 1))
    glow = np.clip(1 - np.abs(d + 0.030) / (3.0 * sc * px), 0, 1)
    cv = Canvas(size, size)
    lo, hi = border + 0.05, 1 - border - 0.05
    cell = (hi - lo) / cells * size
    for gx in range(cells):
        for gy in range(cells):
            cx, cy = lo * size + (gx + 0.5) * cell, lo * size + (gy + 0.5) * cell
            if (gx + gy) % 2 == 0:
                r = cell * 0.40
                rot = rng.uniform(0, math.pi / 3)
                for k in range(6):
                    a = rot + k * math.pi / 3
                    cv.line(cx, cy, cx + math.cos(a) * r, cy + math.sin(a) * r, width)
                    for f in (0.48, 0.76):
                        bx, by = cx + math.cos(a) * r * f, cy + math.sin(a) * r * f
                        for sd in (-1, 1):
                            b2 = a + sd * math.pi / 3
                            L = r * (0.32 if f < 0.6 else 0.20)
                            cv.line(bx, by, bx + math.cos(b2) * L, by + math.sin(b2) * L, max(1, width * 2 // 3))
            else:
                for sd in (-1, 1):
                    t = np.linspace(0, rng.uniform(1.3, 1.7) * TAU, 90)
                    rr = cell * 0.32 * np.exp(-0.21 * t)
                    ph = rng.uniform(0, TAU)
                    ox = cx + sd * cell * 0.17
                    for i in range(len(t) - 1):
                        cv.line(ox + sd * rr[i] * math.cos(t[i] + ph), cy + rr[i] * math.sin(t[i] + ph),
                                ox + sd * rr[i + 1] * math.cos(t[i + 1] + ph), cy + rr[i + 1] * math.sin(t[i + 1] + ph),
                                max(1, width * 2 // 3))
    eng = np.clip(box_blur(cv.mask, int(2 * sc) + 1) * 1.3, 0, 1) * field
    grain = box_blur(rng.random((size, size)).astype(np.float32), int(24 * sc) + 2) - 0.5
    tone = (1.0 + grain * 0.4)[..., None]
    f3 = field[..., None]
    base = (np.array(frame_rgb) * (1 - f3) + np.array(field_rgb) * f3) * tone
    mask = np.clip(np.maximum(eng, groove), 0, 1)[..., None]
    base = base * (1 - mask) + np.array(groove_rgb) * mask
    em = np.stack([(glow * 0.9 + box_blur(glow, int(4 * sc) + 1) * 0.5) * c for c in emit_rgb], axis=2)
    height = -0.35 * field - box_blur(np.maximum(eng, groove), int(2 * sc) + 1)
    return np.clip(base, 0, 1), np.clip(em, 0, 1), height_normal(box_blur(height.astype(np.float32), 2), 3.0 * sc)


def brocade_maps(base_rgb, thread_rgb, size=1024, seed=5, cells=14, width=2):
    """海军蓝织锦：45° 菱格绗缝 + 菱心小霜星 + 交点银珠，线色偏冰蓝（不发绿、不发灰）。"""
    rng = np.random.default_rng(seed)
    cv = Canvas(size, size)
    step = size / cells
    for k in range(-cells, 2 * cells):
        x0 = k * step
        cv.line(x0, 0, x0 + size, size, width)
        cv.line(x0, size, x0 + size, 0, width)
    for gx in range(cells):
        for gy in range(cells):
            cx, cy = (gx + 0.5) * step, gy * step
            cv.dot(gx * step, gy * step, 3 * size / 1024)
            for k in range(6):
                a = k * math.pi / 3
                cv.line(cx, cy, cx + math.cos(a) * step * 0.2, cy + math.sin(a) * step * 0.2, 1)
    mask = np.clip(box_blur(cv.mask, 1) * 1.3, 0, 1)
    grain = box_blur(rng.random(mask.shape).astype(np.float32), 3) - 0.5
    tone = (1.0 + grain * 0.35)[..., None]
    base = np.array(base_rgb)[None, None, :] * tone * (1 - mask[..., None] * 0.6) + \
        np.array(thread_rgb)[None, None, :] * mask[..., None] * 0.6
    return np.clip(base, 0, 1), None, height_normal(box_blur(mask, 1), 1.2)


def crystal_maps(emit_rgb, deep=(0.03, 0.15, 0.34), pale=(0.62, 0.86, 0.96), size=512, seed=5):
    """冰晶内部发光：根部深冰蓝、尖端近白；自发光根部最亮向尖端衰减，内部斜向裂纹更亮（读作光在晶体里走）。"""
    rng = np.random.default_rng(seed)
    cv = Canvas(size, size)
    for _ in range(46):
        x, y = rng.uniform(0, size), rng.uniform(0, size * 0.9)
        a = math.pi / 2 + rng.normal(0, 0.5)
        L = rng.uniform(30, 120)
        cv.line(x, y, x + math.cos(a) * L, y + math.sin(a) * L, 1)
    mask = np.clip(box_blur(cv.mask, 1) * 1.2, 0, 1)
    v = np.linspace(0, 1, size)[:, None] * np.ones((1, size))
    k = v ** 0.8
    base = np.stack([deep[i] * (1 - k) + pale[i] * k + mask * 0.07 for i in range(3)], axis=2)
    glow = (1 - v) ** 1.5 * 1.0 + 0.12 + mask * (0.30 - 0.20 * v)
    em = np.stack([glow * c for c in emit_rgb], axis=2)
    return np.clip(base, 0, 1), np.clip(em, 0, 1), height_normal(box_blur(mask, 1) * 0.6, 1.0)


def blade_maps(emit_rgb, deep=(0.05, 0.18, 0.32), pale=(0.55, 0.80, 0.92), size=1024, seed=17):
    """冰晶处刑剑刃：x 沿刃长（护手 0 → 刃尖 1）、y 绕截面（两面平刃中带各一行发光符文）。"""
    rng = np.random.default_rng(seed)
    rune = Canvas(size, size)
    crack = Canvas(size, size)
    glyphs = [[(0, 0, 0, 1), (0, 1, 1, 1), (1, 1, 1, 0.5)], [(0.5, 0, 0.5, 1), (0, 0.5, 1, 0.5)],
              [(0, 0, 1, 1), (0, 1, 1, 0)], [(0, 1, 0.5, 0), (0.5, 0, 1, 1), (0.25, 0.5, 0.75, 0.5)],
              [(0.5, 0, 0.5, 1), (0, 0.7, 1, 0.7), (0, 0.3, 1, 0.3)], [(0, 0, 1, 0), (1, 0, 0.5, 1), (0.5, 1, 0, 0)]]
    for yc in (0.25, 0.75):
        y0 = yc * size
        h = size * 0.07
        for x in np.arange(size * 0.08, size * 0.80, h * 1.25):
            g = glyphs[int(rng.integers(len(glyphs)))]
            for (a, b, c, d) in g:
                rune.line(x + a * h, y0 - h / 2 + b * h, x + c * h, y0 - h / 2 + d * h, 2)
        for dy in (-h * 0.85, h * 0.85):
            rune.line(size * 0.05, y0 + dy, size * 0.84, y0 + dy, 1)
    for _ in range(70):
        x, y = rng.uniform(0, size), rng.uniform(0, size)
        a = rng.normal(0, 0.6)
        L = rng.uniform(30, 140)
        crack.line(x, y, x + math.cos(a) * L, y + math.sin(a) * L, 1)
    rm = np.clip(box_blur(rune.mask, 1) * 1.4, 0, 1)
    cm = np.clip(box_blur(crack.mask, 1), 0, 1)
    x = np.linspace(0, 1, size)[None, :] * np.ones((size, 1))
    y = np.linspace(0, 1, size)[:, None] * np.ones((1, size))
    face = np.abs(np.sin(y * TAU)) ** 0.7                       # 平刃中带 1，刃口 0
    k = (1 - face) * 0.8 + x * 0.2
    base = np.stack([deep[i] * (1 - k) + pale[i] * k + cm * 0.15 for i in range(3)], axis=2)
    halo = box_blur(rm, 5)
    glow = rm * 1.0 + halo * 0.5 + cm * 0.25 + (1 - x) ** 2 * 0.18
    em = np.stack([glow * c for c in emit_rgb], axis=2)
    return np.clip(base, 0, 1), np.clip(em, 0, 1), height_normal(box_blur(rm + cm * 0.5, 1), 1.4)


# ===== 分段腿甲 =====
def leg_armor(ctx, B, side, label, M, crystal_mat):
    """有造型的腿甲：三段叠压大腿甲 + 冰晶护膝甲杯（上下关节片）+ 三段叠压护胫 + 前脊冷光嵌线。"""
    s = B.s
    sl = s * B.limb
    L = B.legs[label]
    hip, knee, ankle = L["hip"] + Vector((0, 0, 0.03 * s)), L["knee"], L["ankle"]
    thigh_spec = ("rigid", {f"Thigh.{label}": 1.0})
    shin_spec = ("rigid", {f"Shin.{label}": 1.0})
    knee_spec = ("rigid", {f"Thigh.{label}": 0.5, f"Shin.{label}": 0.5})
    out_t = Vector((side * 0.42, 1, 0))
    # 大腿：上片长、下片短，上片下缘略大盖住下片上缘；大腿根粗、近膝收细
    for k, (v0, v1, r0, r1) in enumerate(((0.02, 0.60, 0.104, 0.090), (0.54, 0.88, 0.090, 0.080))):
        band(ctx, f"{ctx.title} cuisse {label}{k}", hip, knee, r0 * sl, r1 * sl, M["plate"], thigh_spec, out_t,
             arc=1.80, v0=v0, v1=v1, bulge=0.005 * s, ridge=0.008 * s, flare1=0.004 * s, thick=0.006 * s,
             nu=20, nv=9, sub=0, trim_mat=M["silver"], trim_r=0.0024 * s, rims=(0, 1) if k == 0 else (1,), rim_n=20)
    axis, o, w = limb_frame(hip, knee, out_t)
    line = [hip.lerp(knee, lerp(0.10, 0.56, i / 10)) + o * (lerp(0.104, 0.092, i / 10) * sl + 0.0125 * s)
            for i in range(11)]
    ctx.part(trim(f"{ctx.title} cuisse inlay {label}", line, 0.0019 * s, M["inlay"], n=3), thigh_spec)
    stud = hip.lerp(knee, 0.64) + o * (0.090 * sl + 0.010 * s)
    ctx.part(crystal2(f"{ctx.title} cuisse stud {label}", stud - axis * 0.016 * s, stud + axis * 0.022 * s,
                      0.010 * s, [crystal_mat], sides=6, shoulder=0.5, foot=0.4), thigh_spec)
    # 护膝：前凸甲杯 + 外侧扇翼 + 上下关节片 + 三枚放射冰晶
    kc = knee + Vector((0, 0.050 * s, 0.006 * s))
    cup = ellipsoid(f"{ctx.title} poleyn {label}", kc, (0.045 * s, 0.032 * s, 0.052 * s), [M["plate"]], 18, 12)
    ctx.part(cup, knee_spec)
    rim = [kc + Vector((math.sin(t) * 0.042 * s, 0.012 * s + 0.008 * s * math.cos(t) ** 2, math.cos(t) * 0.050 * s))
           for t in [i / 26 * TAU for i in range(26)]]
    ctx.part(trim(f"{ctx.title} poleyn rim {label}", rim, 0.0024 * s, M["silver"], closed=True, n=3), knee_spec)
    wing = [kc + Vector((side * 0.030 * s, -0.010 * s, 0.036 * s)), kc + Vector((side * 0.074 * s, -0.030 * s, 0.004 * s)),
            kc + Vector((side * 0.030 * s, -0.012 * s, -0.036 * s))]
    ctx.part(tube(f"{ctx.title} poleyn wing {label}", wing, [0.010 * s, 0.020 * s, 0.010 * s], [M["plate"]], n=6,
                  fx=0.30, up=(side, 0, 0), per=3), knee_spec)
    ctx.part(trim(f"{ctx.title} poleyn wing rim {label}", [p + Vector((side * 0.004 * s, 0.006 * s, 0)) for p in wing],
                  0.0020 * s, M["silver"], n=3, per=3), knee_spec)
    band(ctx, f"{ctx.title} knee lame top {label}", hip, knee, 0.082 * sl, 0.078 * sl, M["plate"], thigh_spec,
         Vector((side * 0.2, 1, 0)), arc=1.25, v0=0.86, v1=0.97, thick=0.005 * s, nu=14, nv=3, sub=0,
         trim_mat=M["silver"], trim_r=0.0018 * s, rims=(0,), rim_n=14)
    band(ctx, f"{ctx.title} knee lame low {label}", knee, ankle, 0.074 * sl, 0.072 * sl, M["plate"], shin_spec,
         Vector((side * 0.2, 1, 0)), arc=1.25, v0=0.04, v1=0.13, thick=0.005 * s, nu=14, nv=3, sub=0,
         trim_mat=M["silver"], trim_r=0.0018 * s, rims=(1,), rim_n=14)
    for k, (dx, dz, L_, r) in enumerate(((0.0, 1.0, 0.060, 0.011), (side * 0.75, 0.55, 0.036, 0.008),
                                          (-side * 0.55, 0.65, 0.030, 0.007))):
        d = Vector((dx, 0.55, dz)).normalized()
        b0 = kc + Vector((dx * 0.020 * s, 0.022 * s, dz * 0.030 * s))
        ctx.part(crystal2(f"{ctx.title} knee crystal {label}{k}", b0 - d * 0.008 * s, b0 + d * L_ * s, r * s,
                          [crystal_mat], sides=5, shoulder=0.6, foot=0.6, seed=k * 2.3 + side), knee_spec)
    ctx.part(ellipsoid(f"{ctx.title} knee gem {label}", kc + Vector((0, 0.033 * s, -0.006 * s)),
                       (0.008 * s, 0.005 * s, 0.011 * s), [M["glow"]], 10, 6), knee_spec)
    # 护胫：两段整圈叠压，上段带小腿肚隆起，下段收细后外扩成踝口
    out_s = Vector((0, 1, 0))
    for k, (v0, v1, r0, r1, f0, f1, bu) in enumerate(((0.10, 0.56, 0.068, 0.061, 0.006, 0.0, 0.007),
                                                      (0.50, 0.95, 0.060, 0.048, 0.004, 0.011, 0.002))):
        band(ctx, f"{ctx.title} greave {label}{k}", knee, ankle, r0 * sl, r1 * sl, M["plate"], shin_spec, out_s,
             closed=True, v0=v0, v1=v1, bulge=bu * s, ridge=0.008 * s, flare0=f0 * s, flare1=f1 * s,
             thick=0.005 * s, nu=24, nv=10, sub=0, trim_mat=M["silver"], trim_r=0.0022 * s, rims=(1,), rim_n=24)
    axis, o, w = limb_frame(knee, ankle, out_s)
    line = [knee.lerp(ankle, lerp(0.14, 0.90, i / 14)) + o * (lerp(0.068, 0.050, i / 14) * sl + 0.0135 * s)
            for i in range(15)]
    ctx.part(trim(f"{ctx.title} greave inlay {label}", line, 0.0019 * s, M["inlay"], n=3), shin_spec)
    for k, t in enumerate((0.30, 0.72)):
        g = knee.lerp(ankle, t) + o * (lerp(0.068, 0.050, (t - 0.14) / 0.76) * sl + 0.0145 * s)
        ctx.part(ellipsoid(f"{ctx.title} greave gem {label}{k}", g, (0.006 * s, 0.004 * s, 0.008 * s), [M["glow"]],
                           8, 6), shin_spec)
    return kc


# ===== 冰晶处刑大剑（刚性挂 Chest，斜背在背后） =====
def blade_section(w, t, bevel=0.42):
    """扁六棱刃截面：刃口 (±w, 0)，平刃面 (±bevel·w, ±t)。"""
    return [(w, 0.0), (bevel * w, t), (-bevel * w, t), (-w, 0.0), (-bevel * w, -t), (bevel * w, -t)]


def executioner_sword(ctx, M, guard, axis, flat_n, spec, clear, blade_len=0.80, width=0.056, s=1.0):
    """处刑剑：宽平刃、圆钝刃头（Richtschwert）、下弯冰晶护手、长握柄、刻面冰晶柄头。
    guard 为护手中心，axis 为由刃尖指向柄头的单位向量，flat_n 为平刃面朝向（贴背时 ≈ ±Y）。"""
    d = Vector(axis).normalized()
    n = (Vector(flat_n) - d * Vector(flat_n).dot(d)).normalized()
    wv = d.cross(n).normalized()
    g = Vector(guard)
    sec = []
    xs = [0.0, 0.03, 0.05] + [0.05 + (blade_len - 0.13) * i / 7 for i in range(1, 8)] + \
         [blade_len - 0.08 + 0.08 * math.sin(math.pi / 2 * i / 5) for i in range(1, 6)]
    for x in xs:
        if x < 0.035:
            w = width * 0.78
        else:
            w = width * (1 - 0.10 * x / blade_len)
        tip0 = blade_len - 0.08
        if x > tip0:
            q = (x - tip0) / 0.08
            w *= math.sqrt(max(0.0, 1 - q * q)) * 0.97 + 0.03
        t = 0.0105 * s * (w / width) ** 0.35
        c = g - d * (x + 0.012) * s
        sec.append([c + wv * px * s + n * py for px, py in blade_section(w, t)])
    bl = loft(f"{ctx.title} executioner blade", sec, [M["blade"]], closed_u=True, cap=True,
              uvfn=lambda u, v: (v, u))
    bl.data.polygons.foreach_set("use_smooth", [False] * len(bl.data.polygons))
    ctx.part(bl, spec)
    # 刃口冷光线 + 平刃中脊嵌线（两面）
    for sd in (-1, 1):
        edge = [row[0 if sd > 0 else 3] + wv * sd * 0.0012 * s for row in sec[2:-2]]
        ctx.part(trim(f"{ctx.title} blade edge {sd}", edge, 0.0020 * s, M["glow"], n=3), spec)
        mid = [g - d * (x + 0.012) * s + n * sd * 0.0112 * s for x in np.linspace(0.07, blade_len - 0.14, 12)]
        ctx.part(trim(f"{ctx.title} blade fuller {sd}", mid, 0.0020 * s, M["inlay"], n=3), spec)
    # 护手：银钢横梁，两端下弯接冰晶尖
    gw = 0.135 * s
    bar = [g + wv * (i / 8 * 2 - 1) * gw - d * (0.028 * s * abs(i / 8 * 2 - 1) ** 2.2) for i in range(9)]
    ctx.part(tube(f"{ctx.title} sword guard", bar, [0.009 * s] + [0.012 * s] * 7 + [0.009 * s], [M["steel"]], n=8,
                  fx=1.0, fy=0.7, up=tuple(n), per=2), spec)
    ctx.part(trim(f"{ctx.title} sword guard trim", [p + n * 0.009 * s for p in bar[1:-1]], 0.0022 * s, M["silver"],
                  n=3, per=2), spec)
    for sd in (-1, 1):
        root = bar[0 if sd < 0 else -1]
        tipd = (wv * sd * 0.55 - d * 0.83).normalized()
        ctx.part(crystal2(f"{ctx.title} quillon {sd}", root - tipd * 0.004 * s, root + tipd * 0.085 * s, 0.013 * s,
                          [M["crystal"]], sides=6, shoulder=0.55, foot=0.8, seed=sd * 1.7), spec)
        clear.point("Chest", root + tipd * 0.085 * s, "sword quillon")
    ctx.part(ellipsoid(f"{ctx.title} guard core", g + n * 0.012 * s, (0.018 * s, 0.009 * s, 0.022 * s), [M["glow"]],
                       10, 6), spec)
    ctx.part(ellipsoid(f"{ctx.title} guard core back", g - n * 0.012 * s, (0.016 * s, 0.008 * s, 0.020 * s),
                       [M["glow"]], 10, 6), spec)
    ring = [g + (wv * math.cos(a) * 0.024 + d * math.sin(a) * 0.028) * s + n * 0.013 * s
            for a in [i / 14 * TAU for i in range(14)]]
    ctx.part(trim(f"{ctx.title} guard ring", ring, 0.0022 * s, M["silver"], closed=True, n=3), spec)
    # 握柄：深蓝皮革缠绕 + 银箍，柄头为刻面冰晶
    grip = [g + d * (0.012 + 0.20 * i / 4) * s for i in range(5)]
    ctx.part(tube(f"{ctx.title} sword grip", grip, [0.021 * s, 0.019 * s, 0.018 * s, 0.019 * s, 0.021 * s], [M["suit"]],
                  n=10, per=2), spec)
    for k, t in enumerate((0.02, 0.08, 0.14, 0.205)):
        c = g + d * t * s
        ctx.part(trim(f"{ctx.title} grip band {k}", [c + (wv * math.cos(a) + n * math.sin(a)) * 0.0225 * s
                                                     for a in [i / 10 * TAU for i in range(10)]],
                      0.0022 * s, M["silver"], closed=True, n=3), spec)
    top = g + d * 0.215 * s
    ctx.part(tube(f"{ctx.title} pommel collar", [top, top + d * 0.024 * s], [0.028 * s, 0.022 * s], [M["steel"]], n=10,
                  per=1), spec)
    ctx.part(crystal2(f"{ctx.title} pommel crystal", top + d * 0.014 * s, top + d * 0.125 * s, 0.032 * s,
                      [M["crystal"]], sides=6, shoulder=0.45, foot=0.7, seed=4.2), spec)
    for tag, p in (("pommel", top + d * 0.12 * s), ("grip", g + d * 0.11 * s), ("guard L", bar[0]),
                   ("guard R", bar[-1]), ("blade mid", g - d * blade_len * 0.5 * s),
                   ("blade tip", g - d * blade_len * s)):
        clear.point("Chest", p, f"sword {tag}")
    return g - d * blade_len * s, top + d * 0.125 * s


# ===== 布料逐链风压与“大衣让腿” =====
DEBUG = bool(os.environ.get("ISOLDE_COAT_DEBUG"))


def wind_chain(rig, pose, g, k, back, flare=0.0, side=0.0, seg=None):
    """kit.rig.wind 的单链版：链 k 向身后飘 back，沿本链切向外掀 flare，绕 Z 侧摆 side。"""
    tang, rad = g.axes(k, seg or rig.SEG)
    for j in range(1, g.J + 1):
        dep = depth_w(j, g.J)
        b = back(k, j) if callable(back) else back
        f = flare(k, j) if callable(flare) else flare
        sd = side(k, j) if callable(side) else side
        m = R((X, -b * dep)) @ R((tang, f * dep))
        if sd:
            m = R((Z, sd * dep)) @ m
        pose[f"{g.prefix}{k}.{j}"] = m


def leg_samples(rig, pose, B):
    """腿部采样球：(世界位置, 半径)，覆盖大腿甲、护膝、护胫、铁靴与冰刃。"""
    s = B.s
    out = []
    cache = {}
    for label in ("L", "R"):
        th, sh, ft = f"Thigh.{label}", f"Shin.{label}", f"Foot.{label}"
        h0, k0 = rig.head(pose, th, cache), rig.tail(pose, th, cache)
        a0, t0 = rig.tail(pose, sh, cache), rig.tail(pose, ft, cache)
        for f, r in ((0.35, 0.122), (0.6, 0.116), (0.85, 0.108)):
            out.append((h0.lerp(k0, f), r * s))
        out.append((k0, 0.096 * s))
        for f, r in ((0.3, 0.084), (0.6, 0.074), (0.9, 0.066)):
            out.append((k0.lerp(a0, f), r * s))
        out.append((a0.lerp(t0, 0.4), 0.064 * s))
        out.append((t0, 0.052 * s))
    return out


def coat_clear(rig, g, pose, B, back, flare, side=None, margin=0.010, step=0.03, max_extra=0.36, report=None):
    """大衣让腿：先按 back/flare 写风压，再逐链检查腿部采样球是否穿出布面；穿出则该链继续外掀，
    直到让开或达到 max_extra。布面近似为骨链折线（链点比布面内收约 1.2 cm，margin 补偿褶皱与厚度）。"""
    samples = leg_samples(rig, pose, B)
    span = (g.a1 - g.a0) / g.K
    worst_all = 0.0

    def violation(k):
        cache = {}
        names = [f"{g.prefix}{k}.{j}" for j in range(1, g.J + 1)]
        pts = [rig.head(pose, names[0], cache)] + [rig.tail(pose, nm, cache) for nm in names]
        o = rig.head(pose, g.parent, cache)
        worst = 0.0
        for p, r in samples:
            c = None
            for a, b in zip(pts, pts[1:]):
                lo, hi = min(a.z, b.z), max(a.z, b.z)
                if lo <= p.z <= hi and hi - lo > 1e-6:
                    c = a.lerp(b, (p.z - a.z) / (b.z - a.z))
                    break
            if c is None:
                continue
            vc = Vector((c.x - o.x, c.y - o.y))
            vp = Vector((p.x - o.x, p.y - o.y))
            if vc.length < 1e-4:
                continue
            # 沿本链扇区内三个方向求采样球在水平面上的最远伸出距离，与布面半径比较
            th = math.atan2(vc.x, vc.y)
            for dth in (-0.5 * span, 0.0, 0.5 * span):
                e = Vector((math.sin(th + dth), math.cos(th + dth)))
                proj = vp.dot(e)
                perp2 = vp.length_squared - proj * proj
                if perp2 >= r * r:
                    continue
                need = proj + math.sqrt(r * r - perp2) + margin - vc.length
                if need > worst:
                    worst = need
                    culprit[0] = samples.index((p, r))
        return worst
    culprit = [-1]
    for k in range(g.K):
        extra = 0.0
        # 前襟两条链只挂一侧布、摆角余量大，允许多掀一些给前送的膝盖让位
        cap = max_extra * (1.25 if k in (0, g.K - 1) else 1.0)
        wind_chain(rig, pose, g, k, back, lambda kk, j: (flare(kk, j) if flare else 0.0) + extra, side)
        v = violation(k)
        while v > 0 and extra < cap:
            extra = min(cap, extra + step)
            wind_chain(rig, pose, g, k, back, lambda kk, j: (flare(kk, j) if flare else 0.0) + extra, side)
            v = violation(k)
        worst_all = max(worst_all, v)
        if DEBUG and (extra > 0 or v > 0):
            print(f"COAT DEBUG chain {k}: extra {extra:.2f} residual {v * 100:.1f} cm sample {culprit[0]}")
    if report is not None:
        report.append(worst_all)
    return worst_all


# ===== 优雅滑冰 =====
# 单脚滑冰轨迹：(相位, (横向外移, 前后, 抬高, 外撇, 脚尖下压))，比 _grace_helpers.SKATE_TRACK 蹬得更靠后、横向更收，
# 让蹬冰腿落在长大衣与两条燕尾之间，而不是横着捅穿衣摆
SKATE2 = [
    (0.00, (0.010, 0.095, 0.000, 0.04, 0.00)),    # 前送落冰
    (0.20, (0.014, 0.020, 0.000, 0.05, 0.00)),    # 长滑行
    (0.40, (0.040, -0.080, 0.000, 0.20, 0.00)),   # 开始蹬冰
    (0.56, (0.120, -0.200, 0.000, 0.40, 0.05)),   # 侧后蹬出
    (0.68, (0.130, -0.320, 0.100, 0.32, 0.55)),   # 离冰，浮足后伸
    (0.80, (0.095, -0.290, 0.125, 0.20, 0.60)),   # 浮足抬高保持
    (0.91, (0.035, -0.060, 0.065, 0.08, 0.30)),   # 收回
]
ON_ICE2 = 0.575


def arm_dir(side, phi, el):
    """手臂方向：phi 为自体侧向前（+）/ 向后（-）的水平角，el 为俯仰（负为下垂）。"""
    return Vector((side * math.cos(el) * math.cos(phi), math.cos(el) * math.sin(phi), math.sin(el)))


def skate2(rig, B, t, lean=0.16, sink=0.080, shift=0.036, pose=None):
    """长滑步 + 侧后蹬冰 + 浮足后伸；双臂与滑行腿反相一前一后舒展（前手在胸腹高度前伸、后手向后下方拉长），
    胸腔与骨盆反向拧转，读作花样滑冰式的平衡与优雅。t∈[0,2π) 左右各一步。"""
    s = B.s
    pose = {} if pose is None else pose
    legs = Legs(rig, B)
    glide_l = math.cos(t - 1.26)                  # 左脚滑行中段 +1，右脚滑行中段 -1
    pose["_hover"] = Vector((-shift * s * glide_l, 0.0, -sink * s + 0.014 * s * math.cos(2 * t - 0.5)))
    pose["Pelvis"] = R((Z, -0.12 * glide_l), (Y, -0.045 * glide_l), (X, -lean))
    pose["Spine"] = R((Z, 0.09 * glide_l), (X, -0.03))
    pose["Chest"] = R((Z, 0.10 * glide_l), (Y, 0.03 * glide_l), (X, 0.012 * math.cos(2 * t)))
    pose["Neck"] = R((X, lean * 0.45), (Z, -0.05 * glide_l))
    pose["Head"] = R((X, lean * 0.35 - 0.03), (Z, -0.04 * glide_l))
    for label, ph in (("L", 0.0), ("R", 0.5)):
        side = -1 if label == "L" else 1
        p = (t / TAU + ph) % 1.0
        dx, dy, dz, yaw, pitch = cyc_hermite(SKATE2, p)
        if p < ON_ICE2:
            dz = 0.0
        base = legs.rest[label]["ankle"]
        a = Vector((base.x + side * dx * s, base.y + dy * s, base.z + max(0.0, dz) * s))
        legs.plant(pose, label, a, pitch=pitch, yaw=-side * yaw, knee_out=0.22)
    for label in ("L", "R"):
        side = -1 if label == "L" else 1
        # 右臂在左脚滑行时向前（对侧协调），左臂相反；smoothstep 让两端停留更久、过渡更快
        f = smoothstep(-0.85, 0.85, glide_l * side)
        # 前手斜向前外方舒展（不是直直前伸），前臂与手腕继续略外展、微微上扬；后手向后下方拉长
        phi = lerp(math.radians(-52), math.radians(48), f)
        el = lerp(math.radians(-42), math.radians(-27), f)
        up = arm_dir(side, phi, el)
        rig.aim(pose, f"UpperArm.{label}", up)
        fore = arm_dir(side, phi + math.radians(lerp(-7, -9, f)), el + math.radians(lerp(-4, 7, f)))
        rig.aim(pose, f"Forearm.{label}", fore)
        hand = arm_dir(side, phi + math.radians(lerp(-12, -16, f)), el + math.radians(lerp(0, 3, f)))
        # 掌心：前手朝下、后手朝后下方，随摆动连续过渡
        palm = Vector((0, -0.7, -0.7)).lerp(Vector((0, 0.15, -1.0)), f)
        rig.aim(pose, f"Hand.{label}", hand, up=tuple(palm), rest_up=B.hands[label]["n"])
    return pose
